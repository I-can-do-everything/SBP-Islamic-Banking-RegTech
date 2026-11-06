// API client for the Daleel backend.
// Every visitor gets an anonymous demo workspace. Its token is kept in browser
// storage so a refresh keeps the same workspace; if storage is blocked the app
// still works, it simply starts a new workspace on the next visit.

const BASE = (import.meta.env.VITE_API_URL as string | undefined)?.replace(/\/$/, "") ?? "";
const KEY = "daleel.session";

export type Status = "PASS" | "WARNING" | "FAIL" | "INFO" | "NOT_AVAILABLE";

export interface Submission {
  id: string;
  institution: string;
  period_end: string | null;
  period_days: number | null;
  status: "UPLOADED" | "INGESTING" | "INGESTED" | "PROCESSING" | "READY" | "FAILED";
  stage: string | null;
  error: { stage: string; message: string } | null;
  filename: string | null;
  sha256: string | null;
  size_bytes: number | null;
  created_at: string;
  workflow_status?: WorkflowStatus;
  locked?: boolean;
}

export type WorkflowStatus = "DRAFT" | "SUBMITTED" | "APPROVED" | "REJECTED";
export type Role = "PREPARER" | "APPROVER" | "ADMIN";

export interface Member { id: string; display_name: string; title: string; role: Role }
export interface Me { member_id: string; name: string; role: Role; demo_personas: boolean; members: Member[] }
export interface Person { id: string; name: string; role: Role }

export interface Review {
  workflow_status: WorkflowStatus;
  locked: boolean;
  results_ready: boolean;
  created_by: Person | null;
  submitted_by: Person | null;
  submitted_at: string | null;
  decided_by: Person | null;
  decided_at: string | null;
  results_digest: string;
  submitted_digest: string | null;
  you: Person;
  breaches: { id: string; label: string; category: string; kind: string; explanation: { body: string; author: Person; at: string } | null }[];
  notes: { id: string; item_id: string | null; kind: "explanation" | "comment"; body: string; author: Person; at: string }[];
  history: { id: number; action: "SUBMIT" | "APPROVE" | "REJECT"; actor: Person; comment: string | null; results_digest: string; at: string }[];
  allowed: { submit: boolean; approve: boolean; reject: boolean; note: boolean };
  blocked_reason: { submit: string | null; approve: string | null; reject: string | null; note: string | null };
}

export interface Sample { name: string; title: string; description: string; filename: string }

export interface RuleRef {
  rule_id: string;
  title: string;
  value: string | null;
  unit: string;
  effective_from: string;
  source: { ref?: string; doc?: string; section?: string; verification?: string };
}

export interface Table { columns: string[]; rows: (string | null)[][] }

export interface Metric {
  id: string;
  category: string;
  label: string;
  unit: string;
  value: string | null;
  status: Status;
  formula: string;
  explanation: string;
  threshold: { type: "min" | "max"; value: string; buffer?: string; with_buffer?: string; kind?: string } | null;
  inputs: { id?: string; label: string; value: string | null; unit: string }[];
  rules: RuleRef[];
  table: Table | null;
  notes: string[];
}

export interface Check {
  id: string;
  category: string;
  label: string;
  status: Status;
  message: string;
  evidence: Record<string, unknown>;
  rules: RuleRef[];
}

export interface Results {
  submission: Submission;
  metrics: Metric[];
  checks: Check[];
  gold: { code: string; label: string; normal_side: string; signed_amount: string; presented: string }[];
  mapping: { version: string; unmapped: { gl_code: string; gl_name: string; signed_amount: string }[] } | null;
}

export interface Fix { field: string; fix: string; cells: number; examples: (string | null)[] }

export interface IngestedDataset {
  kind: string;
  source_name: string;
  layout: string;
  row_count: number;
  rejected_count: number;
  canonical_sha256: string;
  header_map: { source: string; field: string; method: string; score: number }[];
  fixes: Fix[];
  translations: { field: string; from: string; to: string; rows: number }[];
  structural: Record<string, number>;
  before: { columns: string[]; rows: string[][]; source_rows: number[] };
  after: { columns: string[]; rows: (string | null)[][] };
  detail: string[] | null;
  ignored_columns: string[] | null;
  rejects_sample: { source_row: number; reason: string }[] | null;
}

export interface Ingestion {
  submission: Submission;
  template_version: string;
  meta: Record<string, string>;
  skipped_sheets: { sheet: string; reason: string }[];
  missing_datasets: string[];
  datasets: IngestedDataset[];
}

export interface Segment { type: "text" | "fact"; value: string; fact_id?: string; status?: Status; ref?: string }

export interface BreakdownPoint {
  kind: "strength" | "concern" | "breach" | "action";
  text: string;
  rendered: string;
  segments: Segment[];
  fact_ids: string[];
  source_ids: string[];
  added_by: "ai" | "daleel";
}

export interface Excerpt {
  id: string;
  doc_id: string;
  doc_title: string;
  url: string | null;
  section: string | null;
  page: number | null;
  verification: string;
  text: string;
}

export interface Breakdown {
  status: "pending" | "ready";
  source?: "ai" | "template";
  provider?: string | null;
  model?: string | null;
  headline?: string;
  points?: BreakdownPoint[];
  facts?: { id: string; label: string; display: string; status: Status; kind: string; ref: string }[];
  excerpts?: Excerpt[];
  grounding?: {
    status: string;
    attempts: number;
    placeholders_filled: number;
    fails_total: number;
    fails_added_by_daleel: number;
    figures_attached_by_daleel?: number;
    ai_error: string | null;
    rules: string[];
  };
  created_at?: string;
}

export interface AuditEvent {
  id: number;
  occurred_at: string;
  actor: string;
  action: string;
  resource: string | null;
  details: Record<string, unknown>;
  prev_hash: string | null;
  hash: string;
}

export class ApiError extends Error {
  constructor(public status: number, public code: string, message: string) {
    super(message);
  }
}

function readToken(): string | null {
  try {
    return localStorage.getItem(KEY);
  } catch {
    return memoryToken;
  }
}

let memoryToken: string | null = null;

function writeToken(token: string | null) {
  memoryToken = token;
  try {
    if (token) localStorage.setItem(KEY, token);
    else localStorage.removeItem(KEY);
  } catch {
    /* storage blocked: keep the token in memory only */
  }
}

async function startSession(): Promise<string> {
  const res = await fetch(`${BASE}/api/v1/session`, { method: "POST" });
  if (!res.ok) throw await toError(res);
  const body = (await res.json()) as { token: string };
  writeToken(body.token);
  return body.token;
}

export async function token(): Promise<string> {
  return readToken() ?? startSession();
}

async function toError(res: Response): Promise<ApiError> {
  try {
    const body = await res.json();
    return new ApiError(res.status, body.code ?? "error", body.title ?? res.statusText);
  } catch {
    return new ApiError(res.status, "error", res.statusText);
  }
}

async function request<T>(path: string, init: RequestInit = {}, retry = true): Promise<T> {
  const t = await token();
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: { ...(init.headers ?? {}), Authorization: `Bearer ${t}` },
  });
  if (res.status === 403 && retry) {
    writeToken(null);
    await startSession();
    return request<T>(path, init, false);
  }
  if (!res.ok) throw await toError(res);
  return (await res.json()) as T;
}

async function post<T>(path: string, body: unknown): Promise<T> {
  return request<T>(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
}

export const api = {
  me: () => request<Me>("/api/v1/me"),
  switchPerson: async (memberId: string) => {
    const res = await post<{ token: string; member: Member }>("/api/v1/session/switch", { member_id: memberId });
    writeToken(res.token);
    return res.member;
  },
  review: (id: string) => request<Review>(`/api/v1/submissions/${id}/review`),
  addNote: (id: string, body: { kind: "explanation" | "comment"; item_id?: string | null; body: string }) =>
    post<{ id: string }>(`/api/v1/submissions/${id}/notes`, body),
  submitForApproval: (id: string, comment?: string) => post<{ ok: boolean }>(`/api/v1/submissions/${id}/submit`, { comment }),
  approve: (id: string, comment?: string) => post<{ ok: boolean }>(`/api/v1/submissions/${id}/approve`, { confirm: true, comment }),
  reject: (id: string, comment: string) => post<{ ok: boolean }>(`/api/v1/submissions/${id}/reject`, { comment }),
  samples: () => fetch(`${BASE}/api/v1/samples`).then((r) => r.json() as Promise<Sample[]>),
  sampleUrl: (name: string) => `${BASE}/api/v1/samples/${name}/download`,
  submit: (form: FormData) => request<{ id: string; sha256: string }>("/api/v1/submissions", { method: "POST", body: form }),
  submissions: () => request<Submission[]>("/api/v1/submissions"),
  submission: (id: string) => request<Submission>(`/api/v1/submissions/${id}`),
  ingestion: (id: string) => request<Ingestion>(`/api/v1/submissions/${id}/ingestion`),
  results: (id: string) => request<Results>(`/api/v1/submissions/${id}/results`),
  breakdown: (id: string) => request<Breakdown>(`/api/v1/submissions/${id}/breakdown`),
  audit: () => request<AuditEvent[]>("/api/v1/audit"),
  verifyAudit: () => request<{ valid: boolean; events: number; head?: string; broken_at?: number }>("/api/v1/audit/verify"),
  rulebook: (asOf?: string) =>
    fetch(`${BASE}/api/v1/rulebook${asOf ? `?as_of=${asOf}` : ""}`).then((r) => r.json() as Promise<(RuleRef & { notes?: string; table?: Record<string, unknown>; list?: string[] })[]>),
  source: (id: string) => fetch(`${BASE}/api/v1/sources/${encodeURIComponent(id)}`).then((r) => r.json() as Promise<Excerpt>),
  templateUrl: async (id: string) => `${BASE}/api/v1/submissions/${id}/template.xlsx?token=${encodeURIComponent(await token())}`,
  eventsUrl: async (id: string) => `${BASE}/api/v1/submissions/${id}/events?token=${encodeURIComponent(await token())}`,
  health: () => fetch(`${BASE}/health`).then((r) => r.json() as Promise<{ ai_provider: string; ai_configured: boolean; allow_uploads: boolean; demo_personas: boolean }>),
};
