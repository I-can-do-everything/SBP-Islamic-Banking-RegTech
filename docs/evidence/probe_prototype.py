"""
Runtime probe for the prototype at commit e96988c.

What it does:
Calls each function in the backend with small, realistic inputs and prints
what happens. It is the evidence behind method M3 in docs/02-bug-register.md.

How to run it:
Use run_probe.sh in this folder. That script copies the backend to a
temporary folder, fixes only BUG-001 in the copy (so the files can load),
and runs this probe there. The real code is never changed.

Each printed line starts with the bug ID it demonstrates.
"""

import io
import re
from decimal import Decimal


def run(label, fn):
    """Run one probe and print either the result or the error, never stop."""
    try:
        print(f"[{label}] OK -> {fn()}")
    except Exception as error:
        print(f"[{label}] {type(error).__name__}: {error}")


from app.layers.ingestion import file_reader as fr
from app.layers.ingestion import format_detector as fd

# Balance parsing
run("control: plain", lambda: fr._parse_balance("1,234.50"))
run("control: brackets", lambda: fr._parse_balance("(500.00)"))
run("control: CR suffix", lambda: fr._parse_balance("100.00 CR"))
run("BUG-002 DR suffix", lambda: fr._parse_balance("100.00 DR"))
run("BUG-003 scientific 1.5E+3", lambda: fr._parse_balance("1.5E+3"))
run("BUG-004 unreadable 'abc'", lambda: fr._parse_balance("abc"))
run("control: compute_hash('abc')", lambda: fd.compute_hash(b"abc"))

# Excel handling
import openpyxl
workbook = openpyxl.Workbook()
sheet = workbook.active
sheet.append(["ACCOUNT_NO", "ACCOUNT_NAME", "DR_AMT", "CR_AMT"])
sheet.append(["3590-MUR-001", "Murabaha", 1000, 0])
buffer = io.BytesIO()
workbook.save(buffer)
xlsx_bytes = buffer.getvalue()
run("BUG-012 detect real XLSX", lambda: fd.detect_format(xlsx_bytes, "tb.xlsx"))
run("BUG-011 read XLSX directly", lambda: fr._read_xlsx(xlsx_bytes))

# CSV handling
t24_csv = (
    b"GL_ACCOUNT_CODE,ACCOUNT_DESC,DR_BAL,CR_BAL,PERIOD\n"
    b"3590-MUR-001,Murabaha,1000.00,0,2025-06-30\n"
    b"2150-MUD-001,Mudarabah Deposits,0,800.00,2025-06-30\n"
)
generic_csv = b"account_code,balance,description\nA1,100,x\n"
run("control: detect T24 CSV", lambda: fd.detect_format(t24_csv, "tb.csv"))
run("BUG-010 read_file on CSV", lambda: fr.read_file(t24_csv, "tb.csv"))
run("BUG-005 _read_csv", lambda: fr._read_csv(t24_csv, fd.CBSFormat.T24))

# Patch BUG-005 in memory only, to see the next bug behind it.
source = open("app/layers/ingestion/file_reader.py").read().replace("'utr-8-sig'", "'utf-8-sig'")
patched = {}
exec(compile(source, "file_reader_with_BUG-005_patched", "exec"), patched)
run("BUG-006 T24 CSV after BUG-005 patch", lambda: patched["_read_csv"](t24_csv, fd.CBSFormat.T24))
run("BUG-006 generic CSV after BUG-005 patch", lambda: patched["_read_csv"](generic_csv, fd.CBSFormat.GENERIC_CSV))

# Normalisation
from app.layers.normalisation import get_balance
from app.layers.normalisation.mapper import MappingRule, RCOAMapper
run("BUG-017 get_balance missing account", lambda: get_balance({}, "X"))
run("BUG-017 sum of two missing accounts", lambda: sum(get_balance({}, c) for c in ["A", "B"]))
rule = MappingRule("3590-MUR", "3590-MUR", "Murabaha")
run("BUG-018 '3590-MUR' matches '3590-MUR-NPF-001'", lambda: rule.matches("3590-MUR-NPF-001"))
split = MappingRule("X.*", "", "d", "APPORTIONMENT", {"A": 33.33, "B": 33.33, "C": 33.33})
run("BUG-019 split 100.00 into thirds, total", lambda: sum(r[3] for r in split.apply("X1", Decimal("100.00"))))
run("BUG-021 RCOAMapper.load('MEEZ')", lambda: RCOAMapper.load("MEEZ"))

# Calculations, with every account present so BUG-017 does not interfere
from app.layers.calculations import ratios as R
codes = {
    "3590-MUR": "1000", "3590-IJA": "0", "3590-DM": "0", "3590-SAL": "0", "3590-IST": "0",
    "3595-MUR-NPF": "50", "3595-IJA-NPF": "0", "3595-DM-NPF": "0", "3595-SAL-NPF": "0", "3595-IST-NPF": "0",
    "1100-PUC": "100", "1200-SR": "10", "1300-RE": "5",
    "4100-MUR-INC": "100", "4100-IJA-INC": "0",
    "2150-MUD": "1000", "2150-WAK": "0", "2500-PER": "5", "2501-IRR": "2",
}
balances = {k: Decimal(v) for k, v in codes.items()}
run("BUG-024 NPF ratio", lambda: R.calculate_npf_ratio(balances))
run("BUG-025/026 CAR to_dict", lambda: R.calculate_car(balances).to_dict())
run("BUG-027 pool ratios (name, value, breach)",
    lambda: [(x.ratio_name, str(x.ratio_value), x.breach_flag) for x in R.calculate_pool_ratios(balances)])
credit_negative = dict(balances, **{"1100-PUC": Decimal("-100"), "1200-SR": Decimal("-10"), "1300-RE": Decimal("-5")})
run("BUG-015 CAR with capital as credit (negative)", lambda: str(R.calculate_car(credit_negative).ratio_value))
run("BUG-017 CAR with Salam/Istisna missing",
    lambda: R.calculate_car({"1100-PUC": Decimal(1), "1200-SR": Decimal(1), "1300-RE": Decimal(1), "3590-MUR": Decimal(10)}))

# Schemas and models
from app.schemas import submission as S
from app.models.submission import RawSubmission
run("BUG-043 26 character passphrase",
    lambda: S.UserCreate(username="abc", email="a@b.c", password="a-very-long-passphrase-123", institution_code="MEEZ"))
run("BUG-041 RawSubmission(id='1').to_dict()", lambda: RawSubmission(id="1").to_dict())
