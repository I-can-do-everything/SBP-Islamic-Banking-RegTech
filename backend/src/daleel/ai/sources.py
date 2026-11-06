"""Retrieval over SBP source documents (the R in RAG).

Why full text search and not embeddings: regulatory wording is precise ("Mudarib
share", "weightages", "Annexure C"), and lexical search finds those exact terms
reliably, costs nothing, runs inside PostgreSQL (Supabase includes it) and gives
the same answer every time. Retrieval is also "structured first": a metric's
rules already name the circular they come from, so excerpts from that circular
are preferred before any general search.

The excerpts are shown to the user word for word with their document, section
and page. The AI can only point at an excerpt by its id; it cannot quote or
paraphrase it as fact, so it cannot invent regulation.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import yaml

from daleel.core.config import get_settings
from daleel.db.database import system_tx

HEADING = re.compile(r"^\s*(\d+(?:\.\d+){0,3})[\.\)]?\s+\S")
CHUNK_CHARS = 1100


@dataclass
class Excerpt:
    id: str
    doc_id: str
    doc_title: str
    url: str | None
    section: str | None
    page: int | None
    verification: str
    text: str

    def as_dict(self) -> dict:
        return self.__dict__.copy()


def _chunks(doc_id: str, text: str) -> list[tuple[str, int, str]]:
    """Split into (section, page, text) chunks along paragraph boundaries."""
    out: list[tuple[str, int, str]] = []
    for page_no, page in enumerate(text.split("\f"), start=1):
        section, buffer = "", []
        paragraphs = re.split(r"\n\s*\n", page)
        for para in paragraphs:
            # pdftotext breaks lines at the page width; join them back into running text.
            clean = re.sub(r"\s+", " ", para).strip()
            if not clean:
                continue
            match = HEADING.match(clean)
            if match and buffer and sum(len(b) for b in buffer) > 300:
                out.append((section, page_no, "\n\n".join(buffer)))
                buffer = []
            if match:
                section = match.group(1)
            buffer.append(clean)
            if sum(len(b) for b in buffer) > CHUNK_CHARS:
                out.append((section, page_no, "\n\n".join(buffer)))
                buffer = []
        if buffer:
            out.append((section, page_no, "\n\n".join(buffer)))
    return out


def build_index() -> int:
    """(Re)load every registered source document into source_chunk."""
    base = get_settings().sources_dir
    registry = yaml.safe_load((base / "sources.yaml").read_text())
    rows = []
    for doc in registry["documents"]:
        path = base / doc["file"]
        if not path.exists():
            continue
        for i, (section, page, text) in enumerate(_chunks(doc["id"], path.read_text(errors="ignore"))):
            rows.append((f"{doc['id']}#{i + 1}", doc["id"], doc["title"], doc.get("url"), section or None,
                         page, "en", doc["verification"], text))
    with system_tx() as conn:
        conn.execute("DELETE FROM source_chunk")
        with conn.cursor() as cur:
            cur.executemany(
                "INSERT INTO source_chunk (id, doc_id, doc_title, url, section, page, lang, verification, text)"
                " VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)", rows)
    return len(rows)


DOC_PATTERNS = [
    (re.compile(r"IFPD Circular No\. 09 of 2024", re.IGNORECASE), "IFPD-C09-2024"),
    (re.compile(r"IBD Circular No\. 03 of 2012", re.IGNORECASE), "IBD-C03-2012"),
    (re.compile(r"Annexure B", re.IGNORECASE), "BPRD-C03-2022-ANNEX-B"),
    (re.compile(r"Annexure C", re.IGNORECASE), "BPRD-C03-2022-ANNEX-C"),
    (re.compile(r"BPRD Circular No\. 03 of 2022", re.IGNORECASE), "BPRD-C03-2022"),
    (re.compile(r"BPRD Circular No\. 06 of 2013", re.IGNORECASE), "BPRD-C06-2013"),
    (re.compile(r"IFPD Circular No\. 08 of 2024", re.IGNORECASE), "IFPD-C08-2024"),
]
STOP = {"the", "and", "of", "a", "an", "to", "in", "for", "by", "as", "is", "on", "or", "x", "with", "per"}


def doc_ids_for_rules(rules: list[dict]) -> list[str]:
    ids: list[str] = []
    for r in rules:
        text = f"{r.get('source', {}).get('doc', '')} {r.get('source', {}).get('section', '')}"
        for pattern, doc_id in DOC_PATTERNS:
            if pattern.search(text) and doc_id not in ids:
                ids.append(doc_id)
    return ids


def _tsquery(text: str) -> str:
    words = [w for w in re.findall(r"[A-Za-z]{3,}", text.lower()) if w not in STOP]
    return " | ".join(dict.fromkeys(words))


def retrieve(query: str, doc_ids: list[str] | None = None, limit: int = 2) -> list[Excerpt]:
    tsq = _tsquery(query)
    if not tsq:
        return []
    sql = ("SELECT id, doc_id, doc_title, url, section, page, verification, text,"
           " ts_rank_cd(tsv, to_tsquery('english', %s)) AS rank FROM source_chunk"
           " WHERE tsv @@ to_tsquery('english', %s)")
    params: list = [tsq, tsq]
    if doc_ids:
        sql += " AND doc_id = ANY(%s)"
        params.append(doc_ids)
    sql += " ORDER BY rank DESC, id LIMIT %s"
    params.append(limit)
    with system_tx() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [Excerpt(r["id"], r["doc_id"], r["doc_title"], r["url"], r["section"], r["page"],
                    r["verification"], r["text"]) for r in rows]


SECTION_TOKEN = re.compile(r"\b(\d+\.\d+(?:\.\d+)*)\b")


def retrieve_for_rules(rules: list[dict], query: str, limit: int = 2) -> list[Excerpt]:
    """Structured first: the exact clause a rule cites, then keyword search in its document."""
    found: list[Excerpt] = []
    with system_tx() as conn:
        for rule in rules:
            source = rule.get("source", {})
            doc_ids = doc_ids_for_rules([rule])
            for token in SECTION_TOKEN.findall(str(source.get("section", ""))):
                if not doc_ids:
                    break
                row = conn.execute(
                    "SELECT id, doc_id, doc_title, url, section, page, verification, text FROM source_chunk"
                    " WHERE doc_id = ANY(%s) AND text ~ %s ORDER BY length(text) LIMIT 1",
                    (doc_ids, r"(^|\n)\s*" + re.escape(token) + r"[\.\)]?\s")).fetchone()
                if row and all(e.id != row["id"] for e in found):
                    found.append(Excerpt(row["id"], row["doc_id"], row["doc_title"], row["url"], row["section"],
                                         row["page"], row["verification"], row["text"]))
    # Then keyword search, but only inside the documents the rules name, in the order
    # they are named. A fact whose rules name no document in the corpus gets no citation:
    # no citation is better than a loosely related one.
    for doc_id in doc_ids_for_rules(rules):
        if len(found) >= limit:
            break
        for e in retrieve(query, [doc_id], limit):
            if all(f.id != e.id for f in found):
                found.append(e)
    return found[:limit]
