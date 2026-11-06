"""Writes the "ideal ingestion document": the Daleel Standard Template workbook.

It contains, for one submission:
- README: what the file is, its source file hash, the template version
- Dictionary: every field of every dataset with its type and meaning
- one sheet per dataset in canonical columns and types
- Fixes: every change made to the raw export, with counts and examples
- Rejected: every row that could not be used, with the reason

A bank can send this layout directly next time and skip most cleaning. The
canonical Parquet files remain the source of truth for calculations; Excel
stores numbers as binary floating point, so this workbook is for people.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import duckdb
import xlsxwriter

from daleel.datasets.schemas import SCHEMAS, TEMPLATE_VERSION

FIX_TEXT = {
    "thousands_separator": "Thousands separators removed",
    "dash_as_zero": "Dash or NIL read as zero",
    "dr_cr_suffix": "DR or CR suffix applied as the sign",
    "brackets_as_negative": "Brackets read as a negative amount",
    "scientific_notation": "Scientific notation expanded",
    "currency_prefix": "Currency prefix removed",
    "percent_sign": "Percentage converted to a fraction",
    "number_read_as_percent": "Number above 1 read as a percentage",
    "date_dd/mm/yyyy": "Day first date (dd/mm/yyyy) converted",
    "date_dd-mm-yyyy": "Day first date (dd-mm-yyyy) converted",
    "date_other_format": "Date in another format converted",
    "netted_to_one_side": "Negative or two sided balance moved to the correct side",
}
STRUCTURAL_TEXT = {
    "title_rows_skipped": "Title rows above the header skipped",
    "blank_rows": "Blank rows removed",
    "repeated_headers": "Repeated header rows (page breaks) removed",
    "total_rows": "TOTAL rows removed (totals are recomputed)",
}


def write_template(path: Path, summary: dict, parquet_paths: dict[str, str], source: dict) -> None:
    wb = xlsxwriter.Workbook(str(path), {"constant_memory": True})
    h = wb.add_format({"bold": True, "bg_color": "#0f3d33", "font_color": "#ffffff", "border": 1})
    b = wb.add_format({"bold": True})
    wrap = wb.add_format({"text_wrap": True, "valign": "top"})
    money = wb.add_format({"num_format": "#,##0.00"})
    rate = wb.add_format({"num_format": "0.0000%"})
    datef = wb.add_format({"num_format": "yyyy-mm-dd"})

    ws = wb.add_worksheet("README")
    ws.set_column(0, 0, 28)
    ws.set_column(1, 1, 90)
    meta = summary.get("meta", {})
    lines = [
        ("Document", "Daleel Standard Template (the ideal ingestion document)"),
        ("Template version", TEMPLATE_VERSION),
        ("Institution", meta.get("institution", "")),
        ("Period end", meta.get("period_end", "")),
        ("Source file", source.get("filename", "")),
        ("Source SHA-256", source.get("sha256", "")),
        ("Generated (UTC)", datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")),
        ("How to use", "Send next period's data in this layout: one sheet per dataset, these column "
                       "names, plain numbers (no separators or suffixes), ISO dates (yyyy-mm-dd), "
                       "rates as fractions (0.025 means 2.5%)."),
        ("Note", "Synthetic demo data for a fictional bank. Not real."),
    ]
    for i, (k, v) in enumerate(lines):
        ws.write(i, 0, k, b)
        ws.write(i, 1, v, wrap)

    ws = wb.add_worksheet("Dictionary")
    ws.write_row(0, 0, ["Sheet", "Field", "Type", "Required", "Allowed values", "Meaning"], h)
    ws.set_column(0, 1, 22)
    ws.set_column(2, 3, 10)
    ws.set_column(4, 4, 50)
    ws.set_column(5, 5, 50)
    r = 1
    for schema in SCHEMAS.values():
        for f in schema.fields:
            ws.write_row(r, 0, [schema.sheet, f.name, f.type, "yes" if f.required else "no",
                                ", ".join(f.values), f.description])
            r += 1

    con = duckdb.connect()
    for kind, schema in SCHEMAS.items():
        if kind not in parquet_paths:
            continue
        ws = wb.add_worksheet(schema.sheet)
        ws.write_row(0, 0, schema.field_names, h)
        types = [f.type for f in schema.fields]
        for c, t in enumerate(types):
            ws.set_column(c, c, 18 if t in ("money", "text") else 14)
        rel = con.execute(f"SELECT * FROM read_parquet('{parquet_paths[kind]}')")
        row_index = 1
        while True:
            batch = rel.fetchmany(5000)
            if not batch:
                break
            for record in batch:
                for c, value in enumerate(record):
                    if value is None:
                        continue
                    t = types[c]
                    if t == "money":
                        ws.write_number(row_index, c, float(value), money)
                    elif t == "rate":
                        ws.write_number(row_index, c, float(value), rate)
                    elif t == "date":
                        ws.write_datetime(row_index, c, datetime(value.year, value.month, value.day), datef)
                    elif t == "int" or isinstance(value, Decimal):
                        ws.write_number(row_index, c, float(value))
                    else:
                        ws.write_string(row_index, c, str(value))
                row_index += 1

    ws = wb.add_worksheet("Fixes")
    ws.write_row(0, 0, ["Dataset", "Source sheet", "Field", "Change", "Cells or rows", "Examples (raw)"], h)
    ws.set_column(0, 2, 20)
    ws.set_column(3, 3, 48)
    ws.set_column(5, 5, 60)
    r = 1
    for kind, d in summary.get("datasets", {}).items():
        for key, n in d.get("structural", {}).items():
            ws.write_row(r, 0, [kind, d["source_name"], "(rows)", STRUCTURAL_TEXT.get(key, key), n, ""])
            r += 1
        for f in d.get("fixes", []):
            ws.write_row(r, 0, [kind, d["source_name"], f["field"], FIX_TEXT.get(f["fix"], f["fix"]),
                                f["cells"], " | ".join(str(e) for e in f.get("examples", []))])
            r += 1
        for t in d.get("translations", []):
            ws.write_row(r, 0, [kind, d["source_name"], t["field"], f"Value translated to {t['to']}",
                                t["rows"], t["from"]])
            r += 1

    ws = wb.add_worksheet("Rejected")
    ws.write_row(0, 0, ["Dataset", "Source sheet", "Source row", "Reason"], h)
    ws.set_column(3, 3, 80)
    r = 1
    for kind, d in summary.get("datasets", {}).items():
        for rej in d.get("rejects_sample", []):
            ws.write_row(r, 0, [kind, d["source_name"], rej["source_row"], rej["reason"]])
            r += 1
    if r == 1:
        ws.write(1, 0, "No rows were rejected.")
    wb.close()
