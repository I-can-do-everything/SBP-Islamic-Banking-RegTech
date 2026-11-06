"""The Daleel Standard Template: the ideal shape of every input dataset.

Banks export data in many layouts (Temenos T24, Oracle Flexcube, home grown
spreadsheets). Ingestion turns any of them into these canonical datasets. The
same definitions drive four things, so they can never disagree:

1. header recognition (each field lists the header names systems use for it)
2. cleaning and type checks
3. the downloadable "ideal ingestion document" (an Excel workbook)
4. the synthetic data generator

Types:
  text    free text, trimmed
  code    identifier, trimmed, case kept
  money   exact decimal amount (PKR), DR/CR suffixes and brackets understood
  rate    a fraction: "2.5%", "2.5" (read as percent when above 1) or "0.025"
  int     whole number
  date    calendar date in any common format
  enum    one of a fixed list of values; common spellings are translated
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Field:
    name: str
    type: str
    required: bool
    description: str
    aliases: tuple[str, ...] = ()
    values: tuple[str, ...] = ()
    value_aliases: dict[str, str] = field(default_factory=dict)
    default: str | None = None


@dataclass(frozen=True)
class DatasetSchema:
    kind: str
    title: str
    sheet: str
    description: str
    fields: tuple[Field, ...]
    required_for: str

    @property
    def field_names(self) -> list[str]:
        return [f.name for f in self.fields]

    def field(self, name: str) -> Field:
        for f in self.fields:
            if f.name == name:
                return f
        raise KeyError(name)


MODES = ("MURABAHA", "IJARAH", "DIMINISHING_MUSHARAKAH", "MUSHARAKAH", "RUNNING_MUSHARAKAH",
         "ISTISNA", "SALAM", "TIJARAH", "OTHER")
MODE_ALIASES = {
    "MUR": "MURABAHA", "MURABAHAH": "MURABAHA", "IJA": "IJARAH", "IJARA": "IJARAH",
    "DM": "DIMINISHING_MUSHARAKAH", "DIMINISHING MUSHARAKA": "DIMINISHING_MUSHARAKAH",
    "DIMINISHING MUSHARAKAH": "DIMINISHING_MUSHARAKAH", "MUSHARAKA": "MUSHARAKAH",
    "RM": "RUNNING_MUSHARAKAH", "RUNNING MUSHARAKAH": "RUNNING_MUSHARAKAH", "IST": "ISTISNA",
    "ISTISNAA": "ISTISNA", "ISTISNA'A": "ISTISNA", "SAL": "SALAM", "TIJ": "TIJARAH", "TIJARA": "TIJARAH",
}
PORTFOLIOS = ("CORPORATE", "SME_SMALL", "SME_MEDIUM", "CONSUMER_AUTO", "CONSUMER_PERSONAL",
              "CREDIT_CARD", "HOUSING", "AGRI_PRODUCTION", "AGRI_DEVELOPMENT", "INFRASTRUCTURE")
PORTFOLIO_ALIASES = {
    "CORP": "CORPORATE", "COMMERCIAL": "CORPORATE", "SMALL ENTERPRISE": "SME_SMALL", "SE": "SME_SMALL",
    "MEDIUM ENTERPRISE": "SME_MEDIUM", "ME": "SME_MEDIUM", "AUTO": "CONSUMER_AUTO",
    "AUTO FINANCE": "CONSUMER_AUTO", "PERSONAL": "CONSUMER_PERSONAL", "CARD": "CREDIT_CARD",
    "MORTGAGE": "HOUSING", "HOME FINANCE": "HOUSING", "AGRI": "AGRI_PRODUCTION",
    "AGRICULTURE": "AGRI_PRODUCTION", "INFRA": "INFRASTRUCTURE",
}
COUNTERPARTIES = ("SOVEREIGN_PKR", "BANK", "CORPORATE", "SME", "RETAIL", "MORTGAGE")

TRIAL_BALANCE = DatasetSchema(
    kind="TRIAL_BALANCE",
    title="General ledger trial balance",
    sheet="TrialBalance",
    description="Closing balance of every GL account at the period end. Total debits must equal total credits.",
    required_for="Balance sheet, capital, reconciliation",
    fields=(
        Field("gl_code", "code", True, "General ledger account code",
              ("GL_ACCOUNT_CODE", "ACCOUNT_CODE", "GL_CODE", "ACCOUNT_NO", "AC_NO", "GL", "ACCOUNT", "LEAF_GL")),
        Field("gl_name", "text", False, "Account name",
              ("ACCOUNT_DESC", "DESCRIPTION", "ACCOUNT_NAME", "AC_NAME", "GL_NAME", "GL_DESCRIPTION", "NAME")),
        Field("branch_code", "code", False, "Branch code", ("BRANCH", "BRANCH_CODE", "BR_CODE", "CO_CODE", "COMPANY")),
        Field("currency", "code", False, "Currency (ISO code)", ("CCY", "CURRENCY", "CURR"), default="PKR"),
        Field("debit", "money", True, "Debit balance",
              ("DR_BAL", "DEBIT_BAL", "DR_AMT", "DEBIT_AMOUNT", "DEBIT", "DR", "DEBIT_BALANCE")),
        Field("credit", "money", True, "Credit balance",
              ("CR_BAL", "CREDIT_BAL", "CR_AMT", "CREDIT_AMOUNT", "CREDIT", "CR", "CREDIT_BALANCE")),
    ),
)

FINANCING = DatasetSchema(
    kind="FINANCING",
    title="Financing portfolio (contract level)",
    sheet="Financing",
    description="One row per Islamic financing contract at the period end.",
    required_for="Classification, NPF, provisioning, ECL, credit RWA",
    fields=(
        Field("contract_id", "code", True, "Contract reference",
              ("CONTRACT_ID", "CONTRACT_NO", "FACILITY_ID", "LD_ID", "ARRANGEMENT_ID", "LOAN_ID", "DEAL_NO")),
        Field("customer_ref", "code", False, "Customer reference (pseudonymised)",
              ("CUSTOMER_ID", "CUSTOMER_NO", "CIF", "CUST_ID", "CUSTOMER")),
        Field("mode", "enum", True, "Islamic mode of financing",
              ("MODE", "PRODUCT", "PRODUCT_TYPE", "FINANCING_MODE", "CONTRACT_TYPE"),
              MODES, MODE_ALIASES),
        Field("portfolio", "enum", True, "Prudential Regulations portfolio",
              ("PORTFOLIO", "SEGMENT", "PR_CATEGORY", "BUSINESS_SEGMENT", "CATEGORY"),
              PORTFOLIOS, PORTFOLIO_ALIASES),
        Field("counterparty_type", "enum", True, "Counterparty type for risk weighting",
              ("COUNTERPARTY_TYPE", "EXPOSURE_CLASS", "ASSET_CLASS", "BORROWER_TYPE"),
              COUNTERPARTIES, {"SOVEREIGN": "SOVEREIGN_PKR", "GOP": "SOVEREIGN_PKR", "CORP": "CORPORATE",
                               "INDIVIDUAL": "RETAIL", "HOUSING": "MORTGAGE"}),
        Field("currency", "code", False, "Currency", ("CCY", "CURRENCY"), default="PKR"),
        Field("outstanding", "money", True, "Gross outstanding amount",
              ("OUTSTANDING", "OS_BALANCE", "PRINCIPAL_OS", "OUTSTANDING_AMOUNT", "BALANCE", "EXPOSURE", "AMOUNT")),
        Field("days_past_due", "int", True, "Days past due", ("DPD", "DAYS_PAST_DUE", "OVERDUE_DAYS", "DAYS_OVERDUE")),
        Field("collateral_fsv", "money", False, "Forced sale value of eligible collateral",
              ("FSV", "COLLATERAL_FSV", "COLLATERAL_VALUE", "SECURITY_VALUE"), default="0"),
        Field("pd_12m", "rate", False, "12 month probability of default", ("PD_12M", "PD12", "PD", "PD_12_MONTH")),
        Field("pd_lifetime", "rate", False, "Lifetime probability of default", ("PD_LIFETIME", "LIFETIME_PD", "PD_LT")),
        Field("lgd", "rate", False, "Loss given default", ("LGD", "LOSS_GIVEN_DEFAULT")),
        Field("pool_id", "code", False, "Pool the asset is allocated to", ("POOL", "POOL_ID", "POOL_CODE")),
        Field("branch_code", "code", False, "Branch code", ("BRANCH", "BRANCH_CODE", "CO_CODE")),
        Field("maturity_date", "date", False, "Contract maturity date", ("MATURITY_DATE", "MATURITY", "EXPIRY_DATE")),
    ),
)

DEPOSITS = DatasetSchema(
    kind="DEPOSITS",
    title="Deposits (account level)",
    sheet="Deposits",
    description="One row per deposit account for the period, with average balance and profit paid.",
    required_for="75% savings profit test, reconciliation",
    fields=(
        Field("account_id", "code", True, "Account reference (pseudonymised)",
              ("ACCOUNT_ID", "ACCOUNT_NO", "AC_NO", "ACCOUNT", "IBAN")),
        Field("product", "enum", True, "Deposit product",
              ("PRODUCT", "PRODUCT_TYPE", "ACCOUNT_TYPE", "CATEGORY"),
              ("CURRENT", "SAVINGS", "TERM"),
              {"CA": "CURRENT", "CURRENT ACCOUNT": "CURRENT", "SA": "SAVINGS", "SAVING": "SAVINGS",
               "SAVINGS ACCOUNT": "SAVINGS", "TD": "TERM", "TDR": "TERM", "TERM DEPOSIT": "TERM", "FIXED": "TERM"}),
        Field("contract", "enum", True, "Shariah contract",
              ("CONTRACT", "CONTRACT_BASIS", "SHARIAH_CONTRACT", "BASIS"),
              ("QARD", "MUDARABAH", "WAKALA"),
              {"QARD-E-HASAN": "QARD", "QARD HASAN": "QARD", "MUDARABA": "MUDARABAH", "WAKALAH": "WAKALA"}),
        Field("depositor_type", "enum", True, "Type of depositor",
              ("DEPOSITOR_TYPE", "CUSTOMER_TYPE", "CUSTOMER_SEGMENT", "SEGMENT"),
              ("INDIVIDUAL", "FI", "PSE", "PLC", "OTHER"),
              {"RETAIL": "INDIVIDUAL", "PERSONAL": "INDIVIDUAL", "FINANCIAL INSTITUTION": "FI", "BANK": "FI",
               "PUBLIC SECTOR": "PSE", "PUBLIC SECTOR ENTERPRISE": "PSE", "PUBLIC LIMITED": "PLC",
               "PUBLIC LIMITED COMPANY": "PLC", "CORPORATE": "OTHER", "SOLE PROPRIETOR": "INDIVIDUAL"}),
        Field("tier", "code", False, "Profit tier or weightage category", ("TIER", "SLAB", "WEIGHTAGE_CATEGORY", "BAND")),
        Field("currency", "code", False, "Currency", ("CCY", "CURRENCY"), default="PKR"),
        Field("average_balance", "money", True, "Average balance for the period",
              ("AVG_BALANCE", "AVERAGE_BALANCE", "AVG_BAL", "MONTHLY_AVG_BALANCE")),
        Field("closing_balance", "money", True, "Balance at the period end",
              ("CLOSING_BALANCE", "BALANCE", "LEDGER_BALANCE", "CLOSING_BAL", "CURRENT_BALANCE")),
        Field("profit_paid", "money", True, "Profit paid or accrued for the period",
              ("PROFIT_PAID", "PROFIT", "PROFIT_AMOUNT", "RETURN_PAID", "PROFIT_ACCRUED")),
        Field("pool_id", "code", False, "Pool", ("POOL", "POOL_ID", "POOL_CODE")),
    ),
)

POOLS = DatasetSchema(
    kind="POOLS",
    title="Investment pools",
    sheet="Pools",
    description="One row per pool for the period: assets, income, sharing and reserves.",
    required_for="Weighted average gross yield, Mudarib share, PER and IRR checks",
    fields=(
        Field("pool_id", "code", True, "Pool code", ("POOL", "POOL_ID", "POOL_CODE")),
        Field("pool_name", "text", False, "Pool name", ("POOL_NAME", "NAME", "DESCRIPTION")),
        Field("pool_type", "enum", True, "Pool type",
              ("POOL_TYPE", "TYPE"), ("GENERAL", "SPECIAL", "SCF", "OMO"),
              {"GENERAL POOL": "GENERAL", "SPECIAL POOL": "SPECIAL", "STANDING CEILING FACILITY": "SCF",
               "OPEN MARKET OPERATIONS": "OMO", "OMO POOL": "OMO"}),
        Field("currency", "code", False, "Currency", ("CCY", "CURRENCY"), default="PKR"),
        Field("average_assets", "money", True, "Average pool assets for the period",
              ("AVG_ASSETS", "AVERAGE_ASSETS", "AVG_POOL_ASSETS", "MONTHLY_AVERAGE_ASSETS")),
        Field("fixed_assets_in_pool", "money", False, "Fixed assets within average pool assets",
              ("FIXED_ASSETS", "FIXED_ASSETS_IN_POOL"), default="0"),
        Field("gross_income", "money", True, "Gross income of the pool for the period",
              ("GROSS_INCOME", "GROSS_EARNINGS", "POOL_INCOME", "GROSS_PROFIT")),
        Field("direct_expenses", "money", False, "Direct expenses charged to the pool",
              ("DIRECT_EXPENSES", "POOL_EXPENSES", "EXPENSES"), default="0"),
        Field("mudarib_share", "rate", True, "Mudarib share of distributable profit",
              ("MUDARIB_SHARE", "MUDARIB_SHARE_PCT", "BANK_SHARE", "PSR_BANK")),
        Field("per_contribution", "money", False, "PER contribution this period", ("PER_CONTRIBUTION", "PER_TRANSFER"), default="0"),
        Field("per_balance", "money", False, "PER balance at the period end", ("PER_BALANCE", "PER_CLOSING"), default="0"),
        Field("irr_contribution", "money", False, "IRR contribution this period", ("IRR_CONTRIBUTION", "IRR_TRANSFER"), default="0"),
        Field("irr_balance", "money", False, "IRR balance at the period end", ("IRR_BALANCE", "IRR_CLOSING"), default="0"),
        Field("weightages_announced_on", "date", False, "Date weightages were announced",
              ("WEIGHTAGES_ANNOUNCED_ON", "ANNOUNCEMENT_DATE", "WEIGHTAGE_DATE")),
        Field("period_start", "date", False, "First day of the profit period", ("PERIOD_START", "START_DATE", "FROM_DATE")),
    ),
)

CAPITAL = DatasetSchema(
    kind="CAPITAL",
    title="Capital memorandum items",
    sheet="CapitalMemo",
    description="Items needed for capital adequacy that a trial balance does not show.",
    required_for="CAR, leverage ratio",
    fields=(
        Field("item", "enum", True, "Memorandum item",
              ("ITEM", "MEMO_ITEM", "DESCRIPTION", "LINE"),
              ("CET1_OTHER_DEDUCTIONS", "AT1_INSTRUMENTS", "MARKET_RISK_RWA", "OPERATIONAL_RISK_RWA",
               "OFF_BALANCE_EXPOSURE", "NEW_STAGE12_PROVISIONS_NET_OF_TAX", "ECL_TRANSITION_YEAR"),
              {}),
        Field("amount", "money", True, "Amount", ("AMOUNT", "VALUE", "PKR")),
    ),
)

SCHEMAS: dict[str, DatasetSchema] = {s.kind: s for s in (TRIAL_BALANCE, FINANCING, DEPOSITS, POOLS, CAPITAL)}
TEMPLATE_VERSION = "DST-1.0"
