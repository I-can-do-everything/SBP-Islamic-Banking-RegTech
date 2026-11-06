"""Works out what each sheet is, which system produced it, and maps its columns.

Column mapping happens in three passes, each recorded so the user can see why a
column was mapped:

1. exact: the normalised header is a known name for the field
2. fuzzy: close spelling (rapidfuzz score of at least 88), for typos and variants
3. ai: only for required fields still missing. A language model proposes a
   column, and the proposal is accepted only if that column's values actually
   parse as the field's type. The model never sees amounts, only headers and a
   few example cells.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from rapidfuzz import fuzz

from daleel.datasets.schemas import SCHEMAS, DatasetSchema
from daleel.ingestion.reader import Sheet, norm_header

FUZZY_MIN = 88

T24_HINTS = {"GL_ACCOUNT_CODE", "CO_CODE", "DR_BAL", "CR_BAL", "LD_ID", "ARRANGEMENT_ID"}
FLEXCUBE_HINTS = {"CONTRACT_NO", "OS_BALANCE", "AC_NO", "DR_AMT", "CR_AMT", "CUSTOMER_NO", "FCUBS"}


@dataclass
class ColumnMatch:
    source: str
    field: str
    method: str
    score: int

    def as_dict(self) -> dict:
        return {"source": self.source, "field": self.field, "method": self.method, "score": self.score}


@dataclass
class Detection:
    schema: DatasetSchema
    layout: str
    layout_evidence: list[str]
    matches: list[ColumnMatch] = field(default_factory=list)
    ignored: list[str] = field(default_factory=list)
    missing_required: list[str] = field(default_factory=list)
    confidence: float = 0.0

    def column_for(self, field_name: str) -> str | None:
        for m in self.matches:
            if m.field == field_name:
                return m.source
        return None


def _match_columns(schema: DatasetSchema, header: list[str]) -> tuple[list[ColumnMatch], list[str]]:
    used: set[int] = set()
    matches: list[ColumnMatch] = []
    normalised = [norm_header(h) for h in header]
    for f in schema.fields:
        names = {norm_header(a) for a in (*f.aliases, f.name)}
        for i, h in enumerate(normalised):
            if i not in used and h in names:
                matches.append(ColumnMatch(header[i], f.name, "exact", 100))
                used.add(i)
                break
    matched_fields = {m.field for m in matches}
    for f in schema.fields:
        if f.name in matched_fields:
            continue
        best = (0, -1)
        for i, h in enumerate(normalised):
            if i in used or not h:
                continue
            for alias in (*f.aliases, f.name):
                score = int(fuzz.ratio(h, norm_header(alias)))
                if score > best[0]:
                    best = (score, i)
        if best[0] >= FUZZY_MIN:
            matches.append(ColumnMatch(header[best[1]], f.name, "fuzzy", best[0]))
            used.add(best[1])
    ignored = [header[i] for i in range(len(header)) if i not in used and header[i]]
    return matches, ignored


def _layout(header: list[str], sheet_name: str) -> tuple[str, list[str]]:
    keys = {norm_header(h) for h in header} | {norm_header(sheet_name)}
    dotted = [h for h in header if "." in h]
    t24 = sorted(keys & T24_HINTS)
    fcubs = sorted(keys & FLEXCUBE_HINTS)
    if dotted or len(t24) >= 2:
        return "T24", ([f"dotted headers such as {dotted[0]}"] if dotted else []) + t24
    if fcubs:
        return "FLEXCUBE", fcubs
    return "GENERIC", []


def detect(sheet: Sheet) -> Detection | None:
    """Pick the dataset whose fields best match this sheet's header."""
    if sheet.header_index < 0:
        return None
    best: Detection | None = None
    for schema in SCHEMAS.values():
        matches, ignored = _match_columns(schema, sheet.header)
        required = [f.name for f in schema.fields if f.required]
        found = {m.field for m in matches}
        missing = [r for r in required if r not in found]
        confidence = (len(required) - len(missing)) / len(required)
        # Prefer schemas whose required fields are all present, then the most matched fields.
        rank = (confidence, len(matches))
        if best is None or rank > (best.confidence, len(best.matches)):
            layout, evidence = _layout(sheet.header, sheet.name)
            best = Detection(schema, layout, evidence, matches, ignored, missing, confidence)
    if best is None or best.confidence < 0.5:
        return None
    return best
