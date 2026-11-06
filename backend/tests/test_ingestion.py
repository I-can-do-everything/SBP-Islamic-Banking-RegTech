"""Ingestion regression tests. Each test names the prototype bug it guards (docs/02-bug-register.md)."""

from __future__ import annotations

import io
from decimal import Decimal

import openpyxl
import pytest
from hypothesis import given
from hypothesis import strategies as st

from daleel.core.errors import InvalidInput
from daleel.ingestion.reader import read_file
from daleel.ingestion.service import ingest_file


def money(duck, text):
    return duck.execute("SELECT d_money(?)", [text]).fetchone()[0]


@pytest.mark.parametrize("text,expected", [
    ("1,234.50", Decimal("1234.5")),        # thousands separator
    ("(500.00)", Decimal(-500)),          # brackets mean negative
    ("100.00 CR", Decimal(-100)),         # CR suffix
    ("100.00 DR", Decimal(100)),          # BUG-002: DR suffix used to crash
    ("1.5E+3", Decimal(1500)),            # BUG-003: used to read as 1.53
    ("PKR 2,000", Decimal(2000)),         # currency prefix
])
def test_money_parsing(duck, text, expected):
    assert money(duck, text) == expected


def test_bug004_unreadable_is_not_zero(duck):
    assert money(duck, "abc") is None
    assert money(duck, "#REF!") is None


@given(st.decimals(min_value=Decimal("-1e12"), max_value=Decimal("1e12"), places=2, allow_nan=False))
def test_money_text_round_trip(value):
    """Property: any amount written the way exports write it reads back exactly."""
    import duckdb

    from daleel.ingestion.clean import install_macros
    con = duckdb.connect()
    install_macros(con)
    for text in (f"{value:,.2f}", f"({abs(value):,.2f})" if value < 0 else f"{value:,.2f}",
                 f"{abs(value):,.2f} {'CR' if value < 0 else 'DR'}"):
        assert con.execute("SELECT d_money(?)", [text]).fetchone()[0] == value


def test_rates_and_dates(duck):
    assert duck.execute("SELECT d_rate('2.5%')").fetchone()[0] == Decimal("0.025")
    assert duck.execute("SELECT d_rate('45')").fetchone()[0] == Decimal("0.45")
    assert duck.execute("SELECT d_rate('0.012')").fetchone()[0] == Decimal("0.012")
    # BUG-009: day first dates used to crash
    assert str(duck.execute("SELECT d_date('30/09/2026')").fetchone()[0]) == "2026-09-30"


MESSY_CSV = (
    "EXAMPLE BANK\r\nTRIAL BALANCE AS AT 30/09/2026\r\n\r\n"
    "CO.CODE,GL.ACCOUNT.CODE,ACCOUNT.DESC,CCY,DR.BAL,CR.BAL\r\n"
    "PK0001,1000-001,Cash Caf\xe9,PKR,\"1,000.00\",-\r\n"
    "PK0001,2000-001,Deposits,PKR,-,\"900.00\"\r\n"
    "CO.CODE,GL.ACCOUNT.CODE,ACCOUNT.DESC,CCY,DR.BAL,CR.BAL\r\n"
    "PK0001,3000-001,Capital,PKR,-,100.00 \r\n"
    "PK0001,1700-001,Other,PKR,(50.00),-\r\n"
    "PK0001,3400-001,Profit,PKR,50.00 DR,-\r\n"
    ",TOTAL,,,\"1,000.00\",\"1,000.00\"\r\n"
).encode("cp1252")


def test_bug005_to_010_messy_t24_csv(tmp_path):
    """Windows-1252 text, title rows, repeated header, TOTAL row, dashes, brackets and suffixes."""
    result = ingest_file(MESSY_CSV, "tb.csv", tmp_path)
    tb = result.datasets["TRIAL_BALANCE"]
    assert tb.layout == "T24"
    assert tb.row_count == 5 and tb.rejected_count == 0          # BUG-006: rows used to be thrown away
    assert tb.structural == {"title_rows_skipped": 3, "repeated_headers": 1, "total_rows": 1}
    import duckdb
    rows = duckdb.connect().execute(
        f"SELECT gl_code, debit, credit FROM read_parquet('{tb.parquet_path}') ORDER BY gl_code").fetchall()
    as_dict = {g: (d, c) for g, d, c in rows}
    assert as_dict["1700-001"] == (0, Decimal(50))             # negative debit moved to credit
    assert sum(d for _, d, _ in rows) == sum(c for _, _, c in rows)  # still balances


def _xlsx(rows) -> bytes:
    wb = openpyxl.Workbook()
    ws = wb.active
    for r in rows:
        ws.append(r)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def test_bug011_bug012_xlsx_name_does_not_overwrite_code(tmp_path):
    data = _xlsx([["ACCOUNT_NO", "ACCOUNT_NAME", "DR_AMT", "CR_AMT"], ["3590-MUR-001", "Murabaha", 1000, 0],
                  ["2000-001", "Deposits", 0, 1000]])
    result = ingest_file(data, "x.xlsx", tmp_path)                # BUG-012: every xlsx used to be rejected
    import duckdb
    codes = [r[0] for r in duckdb.connect().execute(
        f"SELECT gl_code FROM read_parquet('{result.datasets['TRIAL_BALANCE'].parquet_path}')").fetchall()]
    assert "3590-MUR-001" in codes and "Murabaha" not in codes  # BUG-011


def test_renamed_binary_is_rejected():
    with pytest.raises(InvalidInput):
        read_file(b"\x00\x01binary,stuff", "fake.csv")
    with pytest.raises(InvalidInput):
        read_file(b"PK\x03\x04not a zip", "fake.xlsx")


def test_unreadable_row_rejected_with_reason(stressed):
    ingestion, _ = stressed
    deposits = ingestion.datasets["DEPOSITS"]
    assert deposits.rejected_count == 1
    assert "unreadable amount '#REF!'" in deposits.rejects_sample[0]["reason"]
