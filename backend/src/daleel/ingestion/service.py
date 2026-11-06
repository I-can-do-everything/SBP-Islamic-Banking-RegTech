"""Ingestion: from an uploaded file to trusted canonical datasets.

Steps for each sheet:
1. read as text and find the real table (reader.py)
2. detect which dataset it is and map its columns (detect.py)
3. load into DuckDB as text, clean with SQL macros (clean.py)
4. write the canonical rows to Parquet (the silver layer, DEC-002) and the
   rejects with reasons
5. keep a small before and after preview for the interface

The result also produces the "ideal ingestion document": the same data laid out
in the Daleel Standard Template, which a bank could send next time instead of
its raw export (template.py).
"""

from __future__ import annotations

import csv
import tempfile
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import duckdb

from daleel.core.errors import InvalidInput
from daleel.datasets.schemas import SCHEMAS, TEMPLATE_VERSION
from daleel.ingestion.clean import clean, install_macros
from daleel.ingestion.detect import Detection, detect
from daleel.ingestion.reader import Sheet, read_file, read_meta

PREVIEW_ROWS = 8


@dataclass
class DatasetReport:
    kind: str
    title: str
    source_name: str
    layout: str
    layout_evidence: list[str]
    header_map: list[dict]
    ignored_columns: list[str]
    structural: dict
    row_count: int
    rejected_count: int
    fixes: list[dict]
    translations: list[dict]
    rejects_sample: list[dict]
    preview_before: dict
    preview_after: dict
    parquet_path: str
    rejects_path: str

    def as_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items() if k not in ("parquet_path", "rejects_path")}


@dataclass
class IngestionResult:
    meta: dict
    datasets: dict[str, DatasetReport] = field(default_factory=dict)
    skipped_sheets: list[dict] = field(default_factory=list)
    template_version: str = TEMPLATE_VERSION

    def summary(self) -> dict:
        return {
            "template_version": self.template_version,
            "meta": {k: (v.isoformat() if isinstance(v, date) else v) for k, v in self.meta.items()},
            "datasets": {k: v.as_dict() for k, v in self.datasets.items()},
            "skipped_sheets": self.skipped_sheets,
            "missing_datasets": [k for k in SCHEMAS if k not in self.datasets],
        }


def _unique(names: list[str]) -> list[str]:
    seen: dict[str, int] = {}
    out = []
    for n in names:
        n = n or "column"
        if n in seen:
            seen[n] += 1
            out.append(f"{n}_{seen[n]}")
        else:
            seen[n] = 0
            out.append(n)
    return out


def _load_raw(con: duckdb.DuckDBPyConnection, sheet: Sheet, table: str, workdir: Path) -> None:
    header = _unique(sheet.header)
    path = workdir / f"{table}.csv"
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["_row", *header])
        for number, row in zip(sheet.data_row_numbers, sheet.data):
            writer.writerow([number, *row[: len(header)]])
    columns = {"_row": "INTEGER", **{h: "VARCHAR" for h in header}}
    con.execute(
        f"CREATE OR REPLACE TABLE {table} AS SELECT * FROM read_csv(?, header=true, columns=?, "
        f"delim=',', quote='\"', escape='\"', strict_mode=false)",
        [str(path), columns],
    )
    sheet.header = header


def _skip_reason(sheet: Sheet, meta: dict) -> str:
    keys = ("INSTITUTION", "PERIOD END", "PERIOD DAYS")
    if meta and any(any(c.upper() in keys for c in row) for row in sheet.rows[:40]):
        return "read as report details (institution and reporting period), not as a dataset"
    return "another sheet supplies the same dataset more completely"


def ingest_file(data: bytes, filename: str, out_dir: Path) -> IngestionResult:
    sheets = read_file(data, filename)
    result = IngestionResult(meta=read_meta(sheets))
    out_dir.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    install_macros(con)
    chosen: dict[str, tuple[Sheet, Detection]] = {}
    for sheet in sheets:
        det = detect(sheet)
        if det is None:
            if sheet.rows and any(any(r) for r in sheet.rows):
                result.skipped_sheets.append({"sheet": sheet.name, "reason": "not recognised as a dataset"})
            continue
        current = chosen.get(det.schema.kind)
        if current and (current[1].confidence, len(current[1].matches)) >= (det.confidence, len(det.matches)):
            result.skipped_sheets.append({"sheet": sheet.name, "reason": _skip_reason(sheet, result.meta)})
            continue
        if current:
            result.skipped_sheets.append({"sheet": current[0].name, "reason": _skip_reason(current[0], result.meta)})
        chosen[det.schema.kind] = (sheet, det)
    if not chosen:
        raise InvalidInput("no_datasets", "No recognisable dataset was found in this file. "
                           "Check that each sheet has a header row with column names.")
    with tempfile.TemporaryDirectory() as tmp:
        workdir = Path(tmp)
        for kind, (sheet, det) in chosen.items():
            raw_table, target = f"raw_{kind.lower()}", kind.lower()
            before = {"columns": list(sheet.header), "rows": sheet.data[:PREVIEW_ROWS],
                      "source_rows": sheet.data_row_numbers[:PREVIEW_ROWS]}
            _load_raw(con, sheet, raw_table, workdir)
            cleaned = clean(con, raw_table, det, target)
            parquet = out_dir / f"{target}.parquet"
            rejects = out_dir / f"{target}_rejects.parquet"
            con.execute(f"COPY {target} TO '{parquet}' (FORMAT parquet, COMPRESSION zstd)")
            con.execute(f"COPY {target}_rejects TO '{rejects}' (FORMAT parquet)")
            after_rel = con.execute(f"SELECT * FROM {target} LIMIT {PREVIEW_ROWS}")
            after = {"columns": [d[0] for d in after_rel.description],
                     "rows": [[None if v is None else str(v) for v in r] for r in after_rel.fetchall()]}
            result.datasets[kind] = DatasetReport(
                kind=kind, title=det.schema.title, source_name=sheet.name, layout=det.layout,
                layout_evidence=det.layout_evidence, header_map=[m.as_dict() for m in det.matches],
                ignored_columns=det.ignored, structural=sheet.structural,
                row_count=cleaned.row_count, rejected_count=cleaned.rejected_count,
                fixes=cleaned.fixes, translations=cleaned.translations,
                rejects_sample=cleaned.rejects_sample, preview_before=before, preview_after=after,
                parquet_path=str(parquet), rejects_path=str(rejects),
            )
    return result
