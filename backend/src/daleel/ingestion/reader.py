"""Reads uploaded files into plain text grids and finds where the real data is.

Supported: .xlsx (each sheet), .csv / .txt (auto detected encoding and delimiter)
and .parquet. Everything is read as text first, so nothing is lost or rounded
before cleaning (DEC-007).

Structural clean up done here, and counted for the fix report:
- title rows above the header are skipped (the header is the row that matches
  the most known column names)
- blank rows are dropped
- repeated header rows (page breaks in exports) are dropped
- TOTAL / GRAND TOTAL rows are dropped (totals are recomputed, never trusted)
"""

from __future__ import annotations

import csv
import io
import re
import zipfile
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal

from openpyxl import load_workbook

from daleel.core.errors import InvalidInput
from daleel.datasets.schemas import SCHEMAS

ENCODINGS = ("utf-8-sig", "utf-8", "cp1252", "latin-1")  # BUG-005: the correct names
TOTAL_RE = re.compile(r"^(grand\s+)?(sub\s*)?totals?\b", re.IGNORECASE)
MAX_HEADER_SCAN = 30


def norm_header(text: str) -> str:
    """GL.ACCOUNT.CODE, 'gl account code' and GL_Account_Code all become GL_ACCOUNT_CODE."""
    return re.sub(r"[^A-Z0-9]+", "_", str(text).upper()).strip("_")


KNOWN_HEADERS = {norm_header(a) for s in SCHEMAS.values() for f in s.fields
                 for a in (*f.aliases, f.name)}


@dataclass
class Sheet:
    name: str
    rows: list[list[str]]
    header_index: int = -1
    header: list[str] = field(default_factory=list)
    data: list[list[str]] = field(default_factory=list)
    data_row_numbers: list[int] = field(default_factory=list)
    structural: dict[str, int] = field(default_factory=dict)
    encoding: str | None = None


def cell_text(value: object) -> str:
    """Turn a spreadsheet cell into text without passing money through float rounding."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, datetime):
        return value.date().isoformat() if value.time() == datetime.min.time() else value.isoformat(" ")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, float):
        # repr gives the shortest text that reads back as the same float, which is
        # what the person typed into Excel.
        text = repr(value)
        return text[:-2] if text.endswith(".0") else text
    if isinstance(value, (int, Decimal)):
        return str(value)
    return str(value).strip()


def _read_xlsx(data: bytes) -> list[Sheet]:
    # An XLSX file is a ZIP holding [Content_Types].xml and xl/workbook.xml (BUG-012).
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            names = set(zf.namelist())
    except zipfile.BadZipFile as exc:
        raise InvalidInput("not_xlsx", "This file is not a valid Excel workbook.") from exc
    if "[Content_Types].xml" not in names or "xl/workbook.xml" not in names:
        raise InvalidInput("not_xlsx", "This file is not a valid Excel workbook.")
    wb = load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    sheets = []
    for ws in wb.worksheets:
        rows = [[cell_text(v) for v in row] for row in ws.iter_rows(values_only=True)]
        sheets.append(Sheet(ws.title, rows))
    wb.close()
    return sheets


def _decode(data: bytes) -> tuple[str, str]:
    if b"\x00" in data[:4096]:
        raise InvalidInput("binary", "This file looks like binary data, not a CSV text file.")
    for enc in ENCODINGS:
        try:
            return data.decode(enc), enc
        except UnicodeDecodeError:
            continue
    raise InvalidInput("encoding", "Could not read the text encoding of this file.")


def _read_csv(data: bytes, name: str) -> list[Sheet]:
    text, encoding = _decode(data)
    sample = text[:20000]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
        delimiter = dialect.delimiter
    except csv.Error:
        delimiter = ","
    rows = [[c.strip() for c in r] for r in csv.reader(io.StringIO(text), delimiter=delimiter)]
    return [Sheet(name, rows, encoding=encoding)]


def _read_parquet(data: bytes, name: str) -> list[Sheet]:
    import tempfile

    import duckdb

    con = duckdb.connect()
    with tempfile.NamedTemporaryFile(suffix=".parquet") as tmp:
        tmp.write(data)
        tmp.flush()
        rel = con.execute(f"SELECT * FROM read_parquet('{tmp.name}')")
        header = [d[0] for d in rel.description]
        rows = [header] + [[cell_text(v) for v in r] for r in rel.fetchall()]
    return [Sheet(name, rows)]


def read_file(data: bytes, filename: str) -> list[Sheet]:
    lower = filename.lower()
    if lower.endswith((".xlsx", ".xlsm")):
        sheets = _read_xlsx(data)
    elif lower.endswith((".csv", ".txt", ".tsv")):
        sheets = _read_csv(data, filename.rsplit(".", 1)[0])
    elif lower.endswith(".parquet"):
        sheets = _read_parquet(data, filename.rsplit(".", 1)[0])
    else:
        raise InvalidInput("file_type", "Please upload an .xlsx, .csv or .parquet file.")
    for sheet in sheets:
        locate_table(sheet)
    return sheets


def locate_table(sheet: Sheet) -> None:
    """Find the header row and keep only real data rows below it."""
    best_index, best_score = -1, 0
    for i, row in enumerate(sheet.rows[:MAX_HEADER_SCAN]):
        score = sum(1 for c in row if c and norm_header(c) in KNOWN_HEADERS)
        if score > best_score:
            best_index, best_score = i, score
    if best_index < 0 or best_score < 2:
        return
    header = sheet.rows[best_index]
    while header and not header[-1]:
        header = header[:-1]
    sheet.header_index = best_index
    sheet.header = header
    header_key = [norm_header(h) for h in header]
    counts = {"title_rows_skipped": best_index, "blank_rows": 0, "repeated_headers": 0, "total_rows": 0}
    width = len(header)
    for offset, row in enumerate(sheet.rows[best_index + 1:], start=best_index + 2):
        cells = (row + [""] * width)[:width]
        if not any(cells):
            counts["blank_rows"] += 1
            continue
        if [norm_header(c) for c in cells] == header_key:
            counts["repeated_headers"] += 1
            continue
        first = next((c for c in cells if c), "")
        if TOTAL_RE.match(first):
            counts["total_rows"] += 1
            continue
        sheet.data.append(cells)
        sheet.data_row_numbers.append(offset)
    sheet.structural = {k: v for k, v in counts.items() if v}


def read_meta(sheets: list[Sheet]) -> dict:
    """Pick up institution and period from a key/value sheet such as INFO, if present."""
    meta: dict = {}
    for sheet in sheets:
        for row in sheet.rows[:40]:
            cells = [c for c in row if c]
            if len(cells) < 2:
                continue
            key, value = norm_header(cells[0]), cells[1]
            if key in ("INSTITUTION", "BANK", "BANK_NAME", "INSTITUTION_NAME"):
                meta["institution"] = value
            elif key in ("PERIOD_END", "AS_AT", "AS_OF", "REPORTING_DATE", "PERIOD_END_DATE"):
                parsed = parse_date_text(value)
                if parsed:
                    meta["period_end"] = parsed
            elif key in ("PERIOD_DAYS", "DAYS_IN_PERIOD"):
                try:
                    meta["period_days"] = int(Decimal(value))
                except Exception:  # noqa: BLE001
                    pass
    return meta


DATE_FORMATS = ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y", "%Y%m%d", "%d-%b-%Y", "%d %b %Y",
                "%Y-%m-%d %H:%M:%S")


def parse_date_text(text: str) -> date | None:
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(text.strip(), fmt).date()
        except ValueError:
            continue
    return None
