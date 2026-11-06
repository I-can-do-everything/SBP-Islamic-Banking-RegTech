-- Daleel database schema, version 1.
--
-- Design notes (see docs/06-system-design.md):
-- * Every row that belongs to a demo workspace carries workspace_id, and row level
--   security (RLS) only shows rows whose workspace_id matches the session setting
--   app.workspace_id. FORCE makes the rule apply even to the table owner, so an
--   application bug cannot leak another workspace's data (DEC-012).
-- * The audit log is hash chained by a trigger and refuses UPDATE and DELETE (DEC-010).
-- * The job queue is a plain table read with FOR UPDATE SKIP LOCKED (DEC-003).
-- * source_chunk holds SBP source text for retrieval (RAG) with full text search.

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- The workspace id of the current transaction, or NULL when none is set.
CREATE OR REPLACE FUNCTION current_workspace() RETURNS uuid
LANGUAGE sql STABLE AS $$
  SELECT nullif(current_setting('app.workspace_id', true), '')::uuid
$$;

CREATE TABLE workspace (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  label       text NOT NULL DEFAULT 'Demo workspace',
  created_at  timestamptz NOT NULL DEFAULT now(),
  expires_at  timestamptz NOT NULL DEFAULT now() + interval '7 days'
);

CREATE TABLE submission (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id    uuid NOT NULL REFERENCES workspace(id) ON DELETE CASCADE,
  institution     text NOT NULL,
  period_end      date,
  period_days     integer,
  status          text NOT NULL DEFAULT 'UPLOADED'
                  CHECK (status IN ('UPLOADED','INGESTING','INGESTED','PROCESSING','READY','FAILED')),
  stage           text,
  error           jsonb,
  ingestion       jsonb,
  created_at      timestamptz NOT NULL DEFAULT now(),
  updated_at      timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX submission_ws_idx ON submission (workspace_id, created_at DESC);

CREATE TABLE upload (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id  uuid NOT NULL REFERENCES workspace(id) ON DELETE CASCADE,
  submission_id uuid NOT NULL REFERENCES submission(id) ON DELETE CASCADE,
  filename      text NOT NULL,
  sha256        text NOT NULL,
  size_bytes    bigint NOT NULL,
  storage_key   text NOT NULL,
  created_at    timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE dataset (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id    uuid NOT NULL REFERENCES workspace(id) ON DELETE CASCADE,
  submission_id   uuid NOT NULL REFERENCES submission(id) ON DELETE CASCADE,
  kind            text NOT NULL,
  source_name     text NOT NULL,
  layout          text NOT NULL,
  row_count       integer NOT NULL,
  rejected_count  integer NOT NULL DEFAULT 0,
  canonical_key   text NOT NULL,
  canonical_sha256 text NOT NULL,
  header_map      jsonb NOT NULL,
  fixes           jsonb NOT NULL,
  preview         jsonb NOT NULL,
  created_at      timestamptz NOT NULL DEFAULT now(),
  UNIQUE (submission_id, kind)
);

CREATE TABLE gold_balance (
  workspace_id   uuid NOT NULL REFERENCES workspace(id) ON DELETE CASCADE,
  submission_id  uuid NOT NULL REFERENCES submission(id) ON DELETE CASCADE,
  code           text NOT NULL,
  label          text NOT NULL,
  normal_side    text NOT NULL CHECK (normal_side IN ('DEBIT','CREDIT')),
  signed_amount  numeric(38,4) NOT NULL,
  presented      numeric(38,4) NOT NULL,
  source_count   integer NOT NULL,
  PRIMARY KEY (submission_id, code)
);

CREATE TABLE metric_result (
  workspace_id   uuid NOT NULL REFERENCES workspace(id) ON DELETE CASCADE,
  submission_id  uuid NOT NULL REFERENCES submission(id) ON DELETE CASCADE,
  metric_id      text NOT NULL,
  category       text NOT NULL,
  label          text NOT NULL,
  unit           text NOT NULL,
  value          numeric(38,8),
  status         text NOT NULL CHECK (status IN ('PASS','WARNING','FAIL','INFO','NOT_AVAILABLE')),
  detail         jsonb NOT NULL,
  sort_order     integer NOT NULL,
  PRIMARY KEY (submission_id, metric_id)
);

CREATE TABLE validation_result (
  workspace_id   uuid NOT NULL REFERENCES workspace(id) ON DELETE CASCADE,
  submission_id  uuid NOT NULL REFERENCES submission(id) ON DELETE CASCADE,
  check_id       text NOT NULL,
  category       text NOT NULL,
  label          text NOT NULL,
  status         text NOT NULL CHECK (status IN ('PASS','WARNING','FAIL','INFO')),
  message        text NOT NULL,
  evidence       jsonb NOT NULL,
  rule_refs      jsonb NOT NULL,
  sort_order     integer NOT NULL,
  PRIMARY KEY (submission_id, check_id)
);

CREATE TABLE ai_narrative (
  id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id   uuid NOT NULL REFERENCES workspace(id) ON DELETE CASCADE,
  submission_id  uuid NOT NULL REFERENCES submission(id) ON DELETE CASCADE,
  source         text NOT NULL CHECK (source IN ('ai','template')),
  provider       text,
  model          text,
  prompt_version text NOT NULL,
  input_sha256   text NOT NULL,
  output         jsonb NOT NULL,
  grounding      jsonb NOT NULL,
  usage          jsonb,
  created_at     timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE submission_event (
  id             bigserial PRIMARY KEY,
  workspace_id   uuid NOT NULL REFERENCES workspace(id) ON DELETE CASCADE,
  submission_id  uuid NOT NULL REFERENCES submission(id) ON DELETE CASCADE,
  at             timestamptz NOT NULL DEFAULT clock_timestamp(),
  stage          text NOT NULL,
  status         text NOT NULL,
  message        text NOT NULL,
  data           jsonb
);
CREATE INDEX submission_event_idx ON submission_event (submission_id, id);

-- Tamper evident audit log (DEC-010).
CREATE TABLE audit_event (
  id            bigserial PRIMARY KEY,
  workspace_id  uuid NOT NULL REFERENCES workspace(id) ON DELETE CASCADE,
  occurred_at   timestamptz NOT NULL DEFAULT clock_timestamp(),
  actor         text NOT NULL,
  action        text NOT NULL,
  resource      text,
  details       jsonb NOT NULL DEFAULT '{}'::jsonb,
  prev_hash     text,
  hash          text NOT NULL
);
CREATE INDEX audit_event_ws_idx ON audit_event (workspace_id, id);

-- Computes the chain: hash = sha256(previous hash | fields of this event).
-- An advisory lock per workspace makes concurrent inserts take turns, so the
-- chain never forks.
CREATE OR REPLACE FUNCTION audit_event_chain() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
  last_hash text;
BEGIN
  PERFORM pg_advisory_xact_lock(hashtextextended(NEW.workspace_id::text, 0));
  SELECT hash INTO last_hash FROM audit_event
   WHERE workspace_id = NEW.workspace_id ORDER BY id DESC LIMIT 1;
  NEW.occurred_at := clock_timestamp();
  NEW.prev_hash := last_hash;
  NEW.hash := encode(digest(
      coalesce(last_hash, 'GENESIS') || '|' || NEW.workspace_id::text || '|' ||
      to_char(NEW.occurred_at AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.US') || '|' ||
      NEW.actor || '|' || NEW.action || '|' || coalesce(NEW.resource, '') || '|' ||
      NEW.details::text, 'sha256'), 'hex');
  RETURN NEW;
END $$;

CREATE TRIGGER audit_event_chain_trg BEFORE INSERT ON audit_event
  FOR EACH ROW EXECUTE FUNCTION audit_event_chain();

CREATE OR REPLACE FUNCTION audit_event_immutable() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
  -- Deleting a whole workspace (cascade) is allowed when a demo expires.
  IF TG_OP = 'DELETE' AND NOT EXISTS (SELECT 1 FROM workspace WHERE id = OLD.workspace_id) THEN
    RETURN OLD;
  END IF;
  RAISE EXCEPTION 'audit_event is append only';
END $$;

CREATE TRIGGER audit_event_no_update BEFORE UPDATE OR DELETE ON audit_event
  FOR EACH ROW EXECUTE FUNCTION audit_event_immutable();

-- Job queue (no workspace RLS: only the system reads it).
CREATE TABLE job (
  id          bigserial PRIMARY KEY,
  kind        text NOT NULL,
  workspace_id uuid NOT NULL,
  payload     jsonb NOT NULL,
  status      text NOT NULL DEFAULT 'queued' CHECK (status IN ('queued','running','done','failed')),
  attempts    integer NOT NULL DEFAULT 0,
  run_after   timestamptz NOT NULL DEFAULT now(),
  locked_at   timestamptz,
  error       text,
  created_at  timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX job_ready_idx ON job (status, run_after) WHERE status = 'queued';

-- Regulatory source text for retrieval augmented generation.
CREATE TABLE source_chunk (
  id          text PRIMARY KEY,
  doc_id      text NOT NULL,
  doc_title   text NOT NULL,
  url         text,
  section     text,
  page        integer,
  lang        text NOT NULL DEFAULT 'en',
  verification text NOT NULL,
  text        text NOT NULL,
  tsv         tsvector GENERATED ALWAYS AS (to_tsvector('english', coalesce(section,'') || ' ' || text)) STORED
);
CREATE INDEX source_chunk_tsv_idx ON source_chunk USING gin (tsv);

-- Row level security on every workspace table.
DO $$
DECLARE t text;
BEGIN
  FOREACH t IN ARRAY ARRAY['submission','upload','dataset','gold_balance','metric_result',
                           'validation_result','ai_narrative','submission_event','audit_event']
  LOOP
    EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', t);
    EXECUTE format('ALTER TABLE %I FORCE ROW LEVEL SECURITY', t);
    EXECUTE format(
      'CREATE POLICY workspace_isolation ON %I USING (workspace_id = current_workspace()) '
      'WITH CHECK (workspace_id = current_workspace())', t);
  END LOOP;
END $$;

ALTER TABLE workspace ENABLE ROW LEVEL SECURITY;
ALTER TABLE workspace FORCE ROW LEVEL SECURITY;
-- A workspace row is visible to its own session. Creating one is allowed when the
-- session declares that id first (the API does this for new demo sessions).
CREATE POLICY workspace_self ON workspace USING (id = current_workspace())
  WITH CHECK (id = current_workspace());
