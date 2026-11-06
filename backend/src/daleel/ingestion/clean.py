"""Cleans one detected sheet into its canonical dataset, in DuckDB SQL.

Each cell goes through a SQL macro for its field type. Every macro returns the
clean value and, separately, a label for any fix it made, so the user sees
exactly what changed ("thousands separator removed: 2,340 cells"). A cell that
cannot be read gives an error, and its row goes to the rejects list with the
reason. Nothing unreadable is ever turned into zero (BUG-004).

Rules worth knowing:
- money: "1,234.50", "(500)", "500 CR", "500 DR", "PKR 500", "1.5E+3" are all
  understood. A dash or blank means zero only in trial balance debit and credit
  columns (accounting exports print "-" for zero); elsewhere a missing amount is
  an error.
- rates: "2.5%" and "0.025" both mean 2.5%. A bare number above 1 is read as a
  percentage and the fix is recorded.
- dates: day first (dd/mm/yyyy), the convention in Pakistan.
- enums: spellings are translated through the schema's aliases; unknown values
  are errors (they could be translated by AI as a proposal, never silently).
"""

from __future__ import annotations

from dataclasses import dataclass, field

import duckdb

from daleel.datasets.schemas import DatasetSchema, Field
from daleel.ingestion.detect import Detection
from daleel.ingestion.reader import norm_header

AMOUNT = "DECIMAL(38,4)"
RATE = "DECIMAL(18,10)"

MACROS = f"""
CREATE OR REPLACE MACRO d_blank(s) AS s IS NULL OR trim(s) IN ('', '-', '--', 'NIL', 'nil', 'Nil');
CREATE OR REPLACE MACRO d_empty(s) AS s IS NULL OR trim(s) = '';
CREATE OR REPLACE MACRO d_money_text(s) AS
  replace(replace(
    regexp_replace(regexp_replace(regexp_replace(trim(s), '(?i)\\s*(DR|CR)$', ''),
                   '^\\((.*)\\)$', '\\1'),
                   '(?i)^(PKR|RS\\.?)\\s*', ''),
  ',', ''), ' ', '');
CREATE OR REPLACE MACRO d_money_sign(s) AS
  CASE WHEN regexp_matches(trim(s), '^\\(.*\\)$') OR regexp_matches(trim(s), '(?i)CR$') THEN -1 ELSE 1 END;
CREATE OR REPLACE MACRO d_money(s) AS
  CAST(try_cast(d_money_text(s) AS {AMOUNT}) * d_money_sign(s) AS {AMOUNT});
CREATE OR REPLACE MACRO d_money_fix(s) AS CASE
  WHEN s IS NULL OR trim(s) = '' THEN NULL
  WHEN trim(s) IN ('-', '--', 'NIL', 'nil', 'Nil') THEN 'dash_as_zero'
  WHEN regexp_matches(trim(s), '(?i)(DR|CR)$') THEN 'dr_cr_suffix'
  WHEN regexp_matches(trim(s), '^\\(.*\\)$') THEN 'brackets_as_negative'
  WHEN regexp_matches(trim(s), '[0-9][eE][+-]?[0-9]') THEN 'scientific_notation'
  WHEN regexp_matches(trim(s), '(?i)^(PKR|RS)') THEN 'currency_prefix'
  WHEN contains(s, ',') THEN 'thousands_separator'
  ELSE NULL END;
CREATE OR REPLACE MACRO d_rate_raw(s) AS try_cast(replace(replace(trim(s), '%', ''), ',', '') AS DECIMAL(24,10));
CREATE OR REPLACE MACRO d_rate(s) AS CAST(CASE
  WHEN d_blank(s) THEN NULL
  WHEN contains(s, '%') THEN d_rate_raw(s) / 100
  WHEN d_rate_raw(s) > 1 THEN d_rate_raw(s) / 100
  ELSE d_rate_raw(s) END AS {RATE});
CREATE OR REPLACE MACRO d_rate_fix(s) AS CASE
  WHEN d_blank(s) THEN NULL
  WHEN contains(s, '%') THEN 'percent_sign'
  WHEN d_rate_raw(s) > 1 THEN 'number_read_as_percent'
  ELSE NULL END;
CREATE OR REPLACE MACRO d_date(s) AS CAST(coalesce(
  try_strptime(trim(s), '%Y-%m-%d'), try_strptime(trim(s), '%d/%m/%Y'), try_strptime(trim(s), '%d-%m-%Y'),
  try_strptime(trim(s), '%d.%m.%Y'), try_strptime(trim(s), '%Y%m%d'), try_strptime(trim(s), '%d-%b-%Y'),
  try_strptime(trim(s), '%d %b %Y'), try_strptime(trim(s), '%Y-%m-%d %H:%M:%S')) AS DATE);
CREATE OR REPLACE MACRO d_date_fix(s) AS CASE
  WHEN d_blank(s) THEN NULL
  WHEN try_strptime(trim(s), '%Y-%m-%d') IS NOT NULL THEN NULL
  WHEN try_strptime(trim(s), '%d/%m/%Y') IS NOT NULL THEN 'date_dd/mm/yyyy'
  WHEN try_strptime(trim(s), '%d-%m-%Y') IS NOT NULL THEN 'date_dd-mm-yyyy'
  ELSE 'date_other_format' END;
CREATE OR REPLACE MACRO d_int(s) AS try_cast(try_cast(replace(trim(s), ',', '') AS DECIMAL(18,4)) AS INTEGER);
"""

BLANK_IS_ZERO = {("TRIAL_BALANCE", "debit"), ("TRIAL_BALANCE", "credit")}
KEYS = {"TRIAL_BALANCE": ["branch_code", "gl_code", "currency"], "FINANCING": ["contract_id"],
        "DEPOSITS": ["account_id"], "POOLS": ["pool_id"], "CAPITAL": ["item"]}
SQL_TYPE = {"money": AMOUNT, "rate": RATE, "int": "INTEGER", "date": "DATE", "text": "VARCHAR",
            "code": "VARCHAR", "enum": "VARCHAR"}


def install_macros(con: duckdb.DuckDBPyConnection) -> None:
    con.execute(MACROS)


@dataclass
class CleanResult:
    kind: str
    row_count: int
    rejected_count: int
    fixes: list[dict] = field(default_factory=list)
    translations: list[dict] = field(default_factory=list)
    rejects_sample: list[dict] = field(default_factory=list)


def q(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def _enum_table(con: duckdb.DuckDBPyConnection, raw_table: str, col: str, f: Field, table: str) -> list[dict]:
    """Translate distinct raw values to allowed values; returns the translation report."""
    distinct = con.execute(
        f"SELECT trim({q(col)}) AS v, count(*) AS n FROM {raw_table} GROUP BY 1").fetchall()
    allowed = set(f.values)
    aliases = {norm_header(k): v for k, v in f.value_aliases.items()}
    rows, report = [], []
    for raw, n in distinct:
        if raw is None or raw == "":
            continue
        key = norm_header(raw)
        if key in allowed:
            value = key
        elif key in aliases:
            value = aliases[key]
        elif key.replace("_", " ") in f.value_aliases:
            value = f.value_aliases[key.replace("_", " ")]
        else:
            value = None
        rows.append((raw, value))
        if value is not None and raw != value:
            report.append({"field": f.name, "from": raw, "to": value, "rows": n})
    con.execute(f"CREATE OR REPLACE TEMP TABLE {table} (raw VARCHAR, value VARCHAR)")
    if rows:
        con.executemany(f"INSERT INTO {table} VALUES (?, ?)", rows)
    return report


def clean(con: duckdb.DuckDBPyConnection, raw_table: str, det: Detection, target: str) -> CleanResult:
    """Build `target` (canonical rows) and `{target}_rejects` from `raw_table` (all VARCHAR)."""
    schema: DatasetSchema = det.schema
    selects, fix_cols, err_cols, joins = ["r._row AS _row"], [], [], []
    translations: list[dict] = []
    for f in schema.fields:
        col = det.column_for(f.name)
        name = q(f.name)
        if col is None:
            default = "NULL" if f.default is None else f"'{f.default}'"
            selects.append(f"CAST({default} AS {SQL_TYPE[f.type]}) AS {name}")
            if f.required:
                err_cols.append(f"'missing column for {f.name}'")
            continue
        src = f"r.{q(col)}"
        label = col.replace("'", "")
        blank_zero = (schema.kind, f.name) in BLANK_IS_ZERO
        if f.type == "money":
            # A dash or NIL is an accountant's zero. An empty cell is zero only where the
            # export leaves one side of a balance empty, or the field defaults to zero.
            empty_value = "0" if blank_zero or f.default == "0" else "NULL"
            value = (f"CASE WHEN d_empty({src}) THEN {empty_value} WHEN d_blank({src}) THEN 0 "
                     f"ELSE d_money({src}) END")
            selects.append(f"CAST({value} AS {AMOUNT}) AS {name}")
            fix_cols.append((f.name, f"d_money_fix({src})", src))
            missing = "" if (blank_zero or not f.required) else f"WHEN d_empty({src}) THEN 'missing {label}' "
            err_cols.append(
                f"CASE {missing}WHEN NOT d_blank({src}) AND d_money({src}) IS NULL "
                f"THEN 'unreadable amount ''' || {src} || ''' in {label}' END")
        elif f.type == "rate":
            selects.append(f"d_rate({src}) AS {name}")
            fix_cols.append((f.name, f"d_rate_fix({src})", src))
            err_cols.append(
                f"CASE WHEN NOT d_blank({src}) AND (d_rate({src}) IS NULL OR d_rate({src}) < 0 OR d_rate({src}) > 1) "
                f"THEN 'unreadable rate ''' || {src} || ''' in {label}' END")
        elif f.type == "int":
            selects.append(f"d_int({src}) AS {name}")
            req = f"WHEN d_blank({src}) THEN 'missing {label}' " if f.required else ""
            err_cols.append(f"CASE {req}WHEN NOT d_blank({src}) AND d_int({src}) IS NULL "
                            f"THEN 'unreadable number ''' || {src} || ''' in {label}' END")
        elif f.type == "date":
            selects.append(f"d_date({src}) AS {name}")
            fix_cols.append((f.name, f"d_date_fix({src})", src))
            err_cols.append(f"CASE WHEN NOT d_blank({src}) AND d_date({src}) IS NULL "
                            f"THEN 'unreadable date ''' || {src} || ''' in {label}' END")
        elif f.type == "enum":
            table = f"enum_{target}_{f.name}"
            translations += _enum_table(con, raw_table, col, f, table)
            alias = f"e_{f.name}"
            joins.append(f"LEFT JOIN {table} {alias} ON {alias}.raw = trim({src})")
            default = f"'{f.default}'" if f.default else "NULL"
            selects.append(f"coalesce({alias}.value, CASE WHEN d_blank({src}) THEN {default} END) AS {name}")
            req = f"WHEN d_blank({src}) THEN 'missing {label}' " if f.required and not f.default else ""
            err_cols.append(f"CASE {req}WHEN NOT d_blank({src}) AND {alias}.value IS NULL "
                            f"THEN 'unknown {f.name} ''' || {src} || '''' END")
        else:
            default = f"'{f.default}'" if f.default else "NULL"
            selects.append(f"coalesce(nullif(trim({src}), ''), {default}) AS {name}")
            if f.required:
                err_cols.append(f"CASE WHEN d_blank({src}) THEN 'missing {label}' END")
    fix_select = ", ".join(f"{expr} AS {q('fix__' + fname)}" for fname, expr, _ in fix_cols) or "NULL AS fix__none"
    raw_select = ", ".join(f"{src} AS {q('raw__' + fname)}" for fname, _, src in fix_cols) or "NULL AS raw__none"
    error_expr = f"concat_ws('; ', {', '.join(err_cols)})" if err_cols else "''"
    con.execute(f"""
        CREATE OR REPLACE TEMP TABLE {target}_stage AS
        SELECT {', '.join(selects)}, {fix_select}, {raw_select}, nullif({error_expr}, '') AS _error
        FROM {raw_table} r {' '.join(joins)}
    """)
    # Duplicate keys: keep the first occurrence and reject the rest with a reason.
    keys = [k for k in KEYS[schema.kind] if k in schema.field_names]
    key_expr = ", ".join(q(k) for k in keys)
    con.execute(f"""
        CREATE OR REPLACE TEMP TABLE {target}_stage2 AS
        SELECT *, CASE WHEN _error IS NULL AND row_number() OVER (PARTITION BY {key_expr} ORDER BY _row) > 1
                       THEN 'duplicate of an earlier row' END AS _dup
        FROM {target}_stage
    """)
    cols = ", ".join(q(n) for n in schema.field_names)
    con.execute(f"CREATE OR REPLACE TABLE {target} AS SELECT {cols} FROM {target}_stage2 "
                f"WHERE _error IS NULL AND _dup IS NULL ORDER BY _row")
    con.execute(f"CREATE OR REPLACE TABLE {target}_rejects AS SELECT _row AS source_row, "
                f"coalesce(_error, _dup) AS reason FROM {target}_stage2 "
                f"WHERE _error IS NOT NULL OR _dup IS NOT NULL ORDER BY _row")

    if schema.kind == "TRIAL_BALANCE":
        # One row with both sides, or a negative amount, is netted onto the right side.
        fixed = con.execute(f"SELECT count(*) FROM {target} WHERE debit < 0 OR credit < 0 "
                            f"OR (debit > 0 AND credit > 0)").fetchone()[0]
        con.execute(f"""UPDATE {target} SET
            debit = CASE WHEN debit - credit > 0 THEN debit - credit ELSE 0 END,
            credit = CASE WHEN credit - debit > 0 THEN credit - debit ELSE 0 END""")
    else:
        fixed = 0

    fixes = []
    for fname, _, _ in fix_cols:
        rows = con.execute(f"""
            SELECT {q('fix__' + fname)} AS fix, count(*) AS n,
                   list({q('raw__' + fname)} ORDER BY _row)[1:3] AS examples
            FROM {target}_stage2 WHERE {q('fix__' + fname)} IS NOT NULL GROUP BY 1 ORDER BY 2 DESC
        """).fetchall()
        for fix, n, examples in rows:
            fixes.append({"field": fname, "fix": fix, "cells": n, "examples": examples})
    if fixed:
        fixes.append({"field": "debit/credit", "fix": "netted_to_one_side", "cells": fixed, "examples": []})
    row_count = con.execute(f"SELECT count(*) FROM {target}").fetchone()[0]
    rejected = con.execute(f"SELECT count(*) FROM {target}_rejects").fetchone()[0]
    sample = [{"source_row": r, "reason": reason} for r, reason in
              con.execute(f"SELECT * FROM {target}_rejects LIMIT 20").fetchall()]
    return CleanResult(schema.kind, row_count, rejected, fixes, translations, sample)
