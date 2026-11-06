// Number formatting. Amounts arrive as exact decimal strings; they are only
// rounded here, for display. Negative amounts use brackets, as accountants write them.

export type AmountMode = "compact" | "full";

export function pkr(value: string | null | undefined, mode: AmountMode = "compact"): string {
  if (value === null || value === undefined) return "n/a";
  const n = Number(value);
  if (!Number.isFinite(n)) return value;
  const abs = Math.abs(n);
  let text: string;
  if (mode === "compact" && abs >= 1e9) text = `${(abs / 1e9).toLocaleString("en-PK", { minimumFractionDigits: 2, maximumFractionDigits: 2 })} bn`;
  else if (mode === "compact" && abs >= 1e6) text = `${(abs / 1e6).toLocaleString("en-PK", { minimumFractionDigits: 2, maximumFractionDigits: 2 })} m`;
  else text = abs.toLocaleString("en-PK", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  return n < 0 ? `(${text})` : text;
}

export function metricValue(value: string | null, unit: string, mode: AmountMode = "compact"): string {
  if (value === null) return "n/a";
  const n = Number(value);
  switch (unit) {
    case "percent":
      return `${n.toFixed(2)}%`;
    case "pkr":
      return `PKR ${pkr(value, mode)}`;
    case "days":
      return `${n.toFixed(0)} days`;
    case "count":
      return n.toLocaleString("en-PK");
    default:
      return value;
  }
}

export function cell(value: string | null, column: string): string {
  if (value === null || value === undefined || value === "") return "";
  if (/\(PKR\)|amount|balance|outstanding|income|expense|profit|exposure|rwa|ecl|provision/i.test(column)) {
    const n = Number(value);
    if (Number.isFinite(n) && /^-?\d+(\.\d+)?$/.test(value)) return pkr(value, "full");
  }
  if (/^(accounts|contracts|rows|working days)$/i.test(column) && /^\d+$/.test(value)) return Number(value).toLocaleString("en-PK");
  if (/%/.test(column)) {
    const n = Number(value);
    if (Number.isFinite(n)) return `${n.toFixed(2)}`;
  }
  return value;
}

export function shortHash(hash: string | null | undefined, n = 10): string {
  return hash ? `${hash.slice(0, n)}…` : "";
}

export function dateLabel(iso: string | null): string {
  if (!iso) return "unknown date";
  return new Date(`${iso}T00:00:00`).toLocaleDateString("en-GB", { day: "numeric", month: "long", year: "numeric" });
}

export const FIX_LABEL: Record<string, string> = {
  thousands_separator: "Thousands separators removed",
  dash_as_zero: "Dash or NIL read as zero",
  dr_cr_suffix: "DR or CR suffix applied as the sign",
  brackets_as_negative: "Brackets read as negative",
  scientific_notation: "Scientific notation expanded",
  currency_prefix: "Currency prefix removed",
  percent_sign: "Percentage converted to a fraction",
  number_read_as_percent: "Number above 1 read as a percentage",
  "date_dd/mm/yyyy": "Day first dates (dd/mm/yyyy) converted",
  "date_dd-mm-yyyy": "Day first dates (dd-mm-yyyy) converted",
  date_other_format: "Other date format converted",
  netted_to_one_side: "Balance moved to its correct side",
};

export const STRUCTURAL_LABEL: Record<string, string> = {
  title_rows_skipped: "Title rows above the header skipped",
  blank_rows: "Blank rows removed",
  repeated_headers: "Repeated header rows removed",
  total_rows: "TOTAL rows removed (totals are recomputed)",
};

export const DATASET_LABEL: Record<string, string> = {
  TRIAL_BALANCE: "Trial balance",
  FINANCING: "Financing portfolio",
  DEPOSITS: "Deposits",
  POOLS: "Investment pools",
  CAPITAL: "Capital memo",
};
