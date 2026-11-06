"""The AI breakdown: a short executive summary that cannot invent numbers.

How hallucination is designed out, not just reduced:

1. The deterministic engine computes every number. The AI computes nothing.
2. The model receives facts WITHOUT values (fact.for_model). To mention a number
   it writes a placeholder such as {F3}; the app inserts the engine's value. A
   model that never sees a digit cannot copy a wrong one.
3. Regulatory basis comes only from retrieved SBP excerpts (RAG). The model
   cites them by id ([S2]); the interface shows the excerpt word for word.
4. Every reply is validated before anyone sees it:
   - no digits outside placeholders (a short allow list covers names such as
     "Tier 1" and "IFRS 9")
   - placeholders must belong to facts the point cites
   - cited facts and sources must exist, and a source must relate to a cited fact
   - wording must agree with status ("meets", "within" cannot describe a FAIL;
     "breach", "below the minimum" cannot describe only PASS facts)
   - every FAIL must be covered; anything the model leaves out is added by
     Daleel from a template and labelled as such
5. One retry with the list of problems; if it still fails, a fully deterministic
   template summary is used instead, and the screen says so.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field

from daleel.ai.facts import Fact, FactSheet, build_fact_sheet
from daleel.ai.gateway import AIUnavailable, complete_json
from daleel.ai.sources import Excerpt, retrieve_for_rules

PROMPT_VERSION = "breakdown-v1"
PLACEHOLDER = re.compile(r"\{(F\d+)\}")
ALLOWED_DIGIT_TERMS = re.compile(
    r"\b(CET1|AT1|Tier [12]|Stages? [123](?:,? (?:and )?[123])*|IFRS 9|Basel III)\b", re.IGNORECASE)
NEGATIVE = re.compile(r"\b(breach|breaches|breached|below the minimum|fails?|failed|shortfall|non.?compliant|"
                      r"violat\w*|exceeds? the (?:maximum|limit|cap)|above the (?:maximum|limit|cap))\b", re.IGNORECASE)
POSITIVE = re.compile(r"\b(meets|met|compliant|within the (?:limit|requirement|cap)|comfortably|passes|"
                      r"healthy|well above)\b", re.IGNORECASE)

SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["headline", "points"],
    "properties": {
        "headline": {"type": "string"},
        "points": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["kind", "text", "fact_ids", "source_ids"],
                "properties": {
                    "kind": {"type": "string", "enum": ["strength", "concern", "breach", "action"]},
                    "text": {"type": "string"},
                    "fact_ids": {"type": "array", "items": {"type": "string"}},
                    "source_ids": {"type": "array", "items": {"type": "string"}},
                },
            },
        },
    },
}

SYSTEM = """You are a regulatory reporting analyst writing for the compliance head of an Islamic bank in Pakistan.
Write a short, accurate breakdown of the results you are given.

Strict rules:
1. Never write any digit. To mention a figure, write its placeholder exactly, for example {F3}. The application
   replaces each placeholder with a full verified phrase such as "9.10%, 0.45 percentage points below the 9.55%
   minimum", so write sentences like "The lowest savings tier rate is {F3}." and do not repeat the limit.
2. Use only the facts provided. Do not add numbers, causes, history, forecasts or rules that are not given.
3. Every point must list the fact ids it relies on in fact_ids, and every placeholder in its text must be one of them.
4. When a point explains the regulatory basis, cite the excerpt ids in source_ids (only excerpts listed as related to
   a fact you cite). Do not quote excerpts and do not restate their numbers.
5. Describe status faithfully: FAIL means a breach, WARNING means attention needed, PASS means within requirements.
6. Cover every FAIL fact. Then the most important WARNING facts, then key strengths. At most eight points.
7. Plain, calm, professional English. No markdown. Each point one or two sentences, about one topic.
8. The headline is one sentence stating the overall position (for example how many breaches need action).
Kinds: "breach" for FAIL items, "concern" for WARNING items, "strength" for PASS items, "action" for a next step
that follows directly from a FAIL or WARNING (for example: review the mapping, correct the profit rate)."""


STATUS_WORDS = {"pass", "fail", "warning", "info"}
GENERIC = {"highest", "lowest", "ratio", "rate", "share", "across", "pools", "pool", "contribution", "profit",
           "percent", "eligible", "depositors", "after", "every", "all", "the", "and", "for", "its", "own",
           "shortest", "including", "period", "net", "income", "balance", "general", "ledger", "agrees", "account",
           "accounts", "could", "read", "row", "rows", "sit", "sits", "their", "normal", "side", "has", "have"}


def _keywords(label: str) -> set[str]:
    """Distinctive words of a fact label (acronyms and specific terms) used for the fidelity check."""
    words = re.findall(r"[A-Za-z][A-Za-z0-9]+", _model_label(label))
    return {w.lower() for w in words if w.lower() not in GENERIC and (len(w) >= 4 or w.isupper())}


def _model_label(label: str) -> str:
    """Remove digit bearing brackets from labels shown to the model."""
    return re.sub(r"\s*\([^)]*\d[^)]*\)", "", label)


@dataclass
class Breakdown:
    source: str  # "ai" or "template"
    headline: str
    points: list[dict]
    facts: list[dict]
    excerpts: list[dict]
    grounding: dict
    provider: str | None = None
    model: str | None = None
    usage: dict = field(default_factory=dict)
    prompt_version: str = PROMPT_VERSION
    input_sha256: str = ""

    def as_dict(self) -> dict:
        return self.__dict__.copy()


def _collect_excerpts(metrics: list[dict], checks: list[dict], sheet: FactSheet) -> tuple[list[Excerpt], dict]:
    """Retrieve SBP excerpts for each metric fact that has rules; return excerpts and fact->source links."""
    excerpts: list[Excerpt] = []
    links: dict[str, list[str]] = {}
    by_metric = {m["id"]: m for m in metrics}
    by_check = {c["id"]: c for c in checks}
    for fact in sheet.facts:
        if fact.kind not in ("metric", "check"):
            continue
        source = by_metric.get(fact.ref) or by_check.get(fact.ref)
        rules = (source.get("detail") or {}).get("rules") if "detail" in source else source.get("rule_refs")
        rules = [r for r in (rules or []) if r.get("source", {}).get("verification") != "assumption"]
        if not rules or (fact.status == "PASS" and fact.ref not in ("cap.car", "pool.savings_lowest_rate")):
            continue
        for e in retrieve_for_rules(rules, fact.label, limit=1):
            existing = next((x for x in excerpts if x.id == e.id), None)
            if existing is None:
                excerpts.append(e)
                existing = e
            links.setdefault(fact.id, []).append(existing.id)
    return excerpts, links


def _validate(reply: dict, facts: dict[str, Fact], source_ids: dict[str, str], links: dict[str, list[str]]
              ) -> list[str]:
    problems = []
    headline = reply.get("headline", "")
    if re.search(r"\d", ALLOWED_DIGIT_TERMS.sub("", PLACEHOLDER.sub("", headline))):
        problems.append("The headline contains a digit; use placeholders only.")
    for f_id in PLACEHOLDER.findall(headline):
        if f_id not in facts:
            problems.append(f"The headline uses unknown placeholder {{{f_id}}}.")
    for i, p in enumerate(reply.get("points", []), start=1):
        text = p.get("text", "")
        cited = set(p.get("fact_ids", []))
        unknown = [f for f in cited if f not in facts]
        if unknown:
            problems.append(f"Point {i} cites unknown facts {unknown}.")
        if not cited:
            problems.append(f"Point {i} cites no facts.")
        stripped = ALLOWED_DIGIT_TERMS.sub("", PLACEHOLDER.sub("", text))
        if re.search(r"\d", stripped):
            problems.append(f"Point {i} contains a digit outside a placeholder: {text!r}.")
        for f_id in PLACEHOLDER.findall(text):
            if f_id not in cited:
                problems.append(f"Point {i} uses {{{f_id}}} but does not cite {f_id}.")
        allowed_sources = {s for f in cited for s in links.get(f, [])}
        for s in p.get("source_ids", []):
            if s not in source_ids:
                problems.append(f"Point {i} cites unknown source {s}.")
            elif s not in allowed_sources:
                problems.append(f"Point {i} cites {s}, which does not relate to the facts it cites.")
        for f_id in cited:
            fact = facts.get(f_id)
            if fact is None:
                continue
            if fact.display not in STATUS_WORDS and f"{{{f_id}}}" not in text:
                problems.append(f"Point {i} cites {f_id} but does not show it; write {{{f_id}}} in the text.")
            keywords = _keywords(fact.label)
            if keywords and not any(k in text.lower() for k in keywords):
                problems.append(f"Point {i} cites {f_id} ({_model_label(fact.label)}) without naming it; "
                                f"use its own words, for example one of: {', '.join(sorted(keywords)[:4])}.")
        statuses = {facts[f].status for f in cited if f in facts}
        if NEGATIVE.search(text) and not statuses & {"FAIL", "WARNING"}:
            problems.append(f"Point {i} describes a breach but cites no FAIL or WARNING fact.")
        if POSITIVE.search(text) and statuses and statuses <= {"FAIL"}:
            problems.append(f"Point {i} describes a failing item as compliant.")
    return problems


def _render(text: str, facts: dict[str, Fact]) -> tuple[str, list[dict]]:
    segments, pos, out = [], 0, []
    for m in PLACEHOLDER.finditer(text):
        if m.start() > pos:
            segments.append({"type": "text", "value": text[pos:m.start()]})
        fact = facts.get(m.group(1))
        value = fact.display if fact else "[unknown]"
        segments.append({"type": "fact", "value": value, "fact_id": m.group(1),
                         "status": fact.status if fact else "INFO", "ref": fact.ref if fact else None})
        pos = m.end()
    if pos < len(text):
        segments.append({"type": "text", "value": text[pos:]})
    out = "".join(s["value"] for s in segments)
    return out, segments


def _template_point(fact: Fact, sheet: FactSheet) -> dict:
    if fact.kind == "check":
        text = f"{fact.label}: {fact.note} ({{{fact.id}}})." if fact.display not in ("fail", "warning", "info", "pass") \
            else f"{fact.label}: {fact.note}."
    else:
        text = f"{fact.label} is {{{fact.id}}}."
    ids = [fact.id]
    kind = {"FAIL": "breach", "WARNING": "concern"}.get(fact.status, "strength")
    return {"kind": kind, "text": _model_label(text), "fact_ids": ids, "source_ids": [], "added_by": "daleel"}


def _template(sheet: FactSheet) -> dict:
    fails = [f for f in sheet.facts if f.status == "FAIL" and f.kind in ("metric", "check")]
    warns = [f for f in sheet.facts if f.status == "WARNING" and f.kind in ("metric", "check")]
    strengths = [f for f in sheet.facts if f.kind == "metric" and f.status == "PASS"
                 and f.ref in ("cap.car", "cap.cet1_ratio", "pool.savings_lowest_rate", "aq.npf_ratio")]
    if fails:
        headline = "Breaches need action before this submission can be approved."
    elif warns:
        headline = "No breaches found; some items need attention."
    else:
        headline = "All checked requirements are met."
    points = [_template_point(f, sheet) for f in (fails + warns + strengths)[:8]]
    return {"headline": headline, "points": points}


def _user_prompt(sheet: FactSheet, excerpts: list[Excerpt], links: dict, problems: list[str] | None) -> str:
    facts = []
    for f in sheet.facts:
        item = f.for_model()
        item["label"] = _model_label(item["label"])
        if f.id in links:
            item["related_sources"] = links[f.id]
        facts.append(item)
    sources = [{"id": e.id, "document": _model_label(e.doc_title), "section": e.section} for e in excerpts]
    prompt = ("FACTS (values are hidden; refer to them with placeholders like {F1}):\n"
              + json.dumps(facts, indent=1)
              + "\n\nSBP EXCERPTS AVAILABLE TO CITE (by id only):\n" + json.dumps(sources, indent=1)
              + "\n\nWrite the breakdown as JSON.")
    if problems:
        prompt += ("\n\nYour previous answer was rejected for these reasons. Fix every one:\n- "
                   + "\n- ".join(problems[:15]))
    return prompt


def generate_breakdown(metrics: list[dict], checks: list[dict], use_ai: bool = True) -> Breakdown:
    sheet = build_fact_sheet(metrics, checks)
    facts = sheet.by_id()
    excerpts, links = _collect_excerpts(metrics, checks, sheet)
    excerpt_ids = {e.id: e.doc_id for e in excerpts}
    input_hash = hashlib.sha256(json.dumps([f.__dict__ for f in sheet.facts], sort_keys=True,
                                           default=str).encode()).hexdigest()
    reply, problems, attempts, provider, model, usage = None, [], 0, None, None, {}
    error = None
    for attempt in range(2 if use_ai else 0):
        attempts += 1
        try:
            result = complete_json(SYSTEM, _user_prompt(sheet, excerpts, links, problems or None),
                                   SCHEMA, "breakdown")
        except AIUnavailable as exc:
            error = str(exc)
            break
        provider, model, usage = result.provider, result.model, result.usage
        problems = _validate(result.content, facts, excerpt_ids, links)
        if not problems:
            reply = result.content
            break
    source = "ai" if reply is not None else "template"
    final = reply if reply is not None else _template(sheet)
    # Coverage: every FAIL must appear. Anything left out is added and labelled.
    cited = {f for p in final["points"] for f in p.get("fact_ids", [])}
    omitted = [f for f in sheet.facts if f.status == "FAIL" and f.kind in ("metric", "check") and f.id not in cited]
    for f in omitted:
        final["points"].insert(0, _template_point(f, sheet))
    points = []
    for p in final["points"]:
        rendered, segments = _render(p["text"], facts)
        points.append({**p, "rendered": rendered, "segments": segments,
                       "added_by": p.get("added_by", "ai" if source == "ai" else "daleel")})
    headline, _ = _render(final["headline"], facts)
    grounding = {
        "status": "passed" if source == "ai" else ("pending" if not use_ai else
                                                    ("fallback" if error is None else "unavailable")),
        "attempts": attempts,
        "problems_last_attempt": problems if source == "template" else [],
        "ai_error": error,
        "placeholders_filled": sum(len(PLACEHOLDER.findall(p["text"])) for p in final["points"]),
        "fails_total": sum(1 for f in sheet.facts if f.status == "FAIL" and f.kind in ("metric", "check")),
        "fails_added_by_daleel": len(omitted),
        "rules": ["no digits from the model", "placeholders filled from the engine", "citations checked",
                  "status wording checked", "every breach covered"],
    }
    return Breakdown(source, headline, points, [f.__dict__ for f in sheet.facts],
                     [e.as_dict() for e in excerpts], grounding, provider, model, usage,
                     PROMPT_VERSION, input_hash)
