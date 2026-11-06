-- Four eyes approval (maker checker), enforced by the database.
--
-- Rules, all checked in triggers so no application bug can skip them:
-- 1. Only a PREPARER (or ADMIN) can submit, and only when every breach (FAIL)
--    has a written explanation.
-- 2. Only an APPROVER (or ADMIN) can approve or reject, and never someone who
--    uploaded or submitted this submission. This is the four eyes rule.
-- 3. A rejection needs a reason.
-- 4. Approval is bound to a fingerprint (SHA-256) of the exact results that were
--    submitted. If the results changed after submission, approval is refused.
-- 5. An approved submission is locked: its results can no longer change.
-- 6. Approval actions and review notes are append only.

CREATE TABLE workspace_member (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id  uuid NOT NULL REFERENCES workspace(id) ON DELETE CASCADE,
  display_name  text NOT NULL,
  title         text NOT NULL,
  role          text NOT NULL CHECK (role IN ('PREPARER', 'APPROVER', 'ADMIN')),
  created_at    timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE submission
  ADD COLUMN created_by       uuid REFERENCES workspace_member(id),
  ADD COLUMN workflow_status  text NOT NULL DEFAULT 'DRAFT'
                              CHECK (workflow_status IN ('DRAFT', 'SUBMITTED', 'APPROVED', 'REJECTED')),
  ADD COLUMN submitted_by     uuid REFERENCES workspace_member(id),
  ADD COLUMN submitted_at     timestamptz,
  ADD COLUMN decided_by       uuid REFERENCES workspace_member(id),
  ADD COLUMN decided_at       timestamptz,
  ADD COLUMN locked           boolean NOT NULL DEFAULT false;

CREATE TABLE review_note (
  id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id   uuid NOT NULL REFERENCES workspace(id) ON DELETE CASCADE,
  submission_id  uuid NOT NULL REFERENCES submission(id) ON DELETE CASCADE,
  author_id      uuid NOT NULL REFERENCES workspace_member(id),
  item_id        text,            -- a metric or check id, or NULL for a general comment
  kind           text NOT NULL CHECK (kind IN ('explanation', 'comment')),
  body           text NOT NULL CHECK (length(trim(body)) BETWEEN 3 AND 4000),
  created_at     timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE INDEX review_note_sub_idx ON review_note (submission_id, created_at);

CREATE TABLE approval (
  id              bigserial PRIMARY KEY,
  workspace_id    uuid NOT NULL REFERENCES workspace(id) ON DELETE CASCADE,
  submission_id   uuid NOT NULL REFERENCES submission(id) ON DELETE CASCADE,
  action          text NOT NULL CHECK (action IN ('SUBMIT', 'APPROVE', 'REJECT')),
  actor_id        uuid NOT NULL REFERENCES workspace_member(id),
  actor_role      text,
  comment         text,
  results_digest  text,
  created_at      timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE INDEX approval_sub_idx ON approval (submission_id, id);

-- Fingerprint of the results a decision is about: every metric value and status,
-- every check status, and the uploaded file's own fingerprint.
CREATE OR REPLACE FUNCTION submission_results_digest(sub uuid) RETURNS text
LANGUAGE sql STABLE AS $$
  SELECT encode(sha256(convert_to(
    coalesce((SELECT string_agg(metric_id || '=' || coalesce(value::text, 'null') || ':' || status, '|'
                                ORDER BY metric_id) FROM metric_result WHERE submission_id = sub), '')
    || '#' ||
    coalesce((SELECT string_agg(check_id || ':' || status, '|' ORDER BY check_id)
              FROM validation_result WHERE submission_id = sub), '')
    || '#' ||
    coalesce((SELECT sha256 FROM upload WHERE submission_id = sub LIMIT 1), ''),
  'UTF8')), 'hex')
$$;

CREATE OR REPLACE FUNCTION approval_guard() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
  s submission;
  m workspace_member;
  missing integer;
  submitted_digest text;
BEGIN
  SELECT * INTO s FROM submission WHERE id = NEW.submission_id FOR UPDATE;
  IF s.id IS NULL THEN
    RAISE EXCEPTION 'Submission not found.';
  END IF;
  SELECT * INTO m FROM workspace_member WHERE id = NEW.actor_id AND workspace_id = NEW.workspace_id;
  IF m.id IS NULL THEN
    RAISE EXCEPTION 'Unknown reviewer.';
  END IF;
  IF s.status <> 'READY' THEN
    RAISE EXCEPTION 'The results are not ready yet.';
  END IF;
  NEW.actor_role := m.role;
  NEW.results_digest := submission_results_digest(NEW.submission_id);
  NEW.created_at := clock_timestamp();

  IF NEW.action = 'SUBMIT' THEN
    IF m.role NOT IN ('PREPARER', 'ADMIN') THEN
      RAISE EXCEPTION 'Only a preparer can submit for approval.';
    END IF;
    IF s.workflow_status NOT IN ('DRAFT', 'REJECTED') THEN
      RAISE EXCEPTION 'This submission is already %.', lower(s.workflow_status);
    END IF;
    SELECT count(*) INTO missing FROM (
      SELECT metric_id AS item FROM metric_result WHERE submission_id = s.id AND status = 'FAIL'
      UNION ALL
      SELECT check_id FROM validation_result WHERE submission_id = s.id AND status = 'FAIL'
    ) f
    WHERE NOT EXISTS (SELECT 1 FROM review_note n
                      WHERE n.submission_id = s.id AND n.item_id = f.item AND n.kind = 'explanation');
    IF missing > 0 THEN
      RAISE EXCEPTION 'Every breach needs a written explanation before submission (% still missing).', missing;
    END IF;
    UPDATE submission SET workflow_status = 'SUBMITTED', submitted_by = NEW.actor_id, submitted_at = now(),
                          decided_by = NULL, decided_at = NULL
     WHERE id = s.id;

  ELSIF NEW.action IN ('APPROVE', 'REJECT') THEN
    IF m.role NOT IN ('APPROVER', 'ADMIN') THEN
      RAISE EXCEPTION 'Only an approver can approve or reject.';
    END IF;
    IF s.workflow_status <> 'SUBMITTED' THEN
      RAISE EXCEPTION 'Only a submitted submission can be decided (it is %).', lower(s.workflow_status);
    END IF;
    IF NEW.actor_id = s.submitted_by OR NEW.actor_id = s.created_by THEN
      RAISE EXCEPTION 'Four eyes rule: the person who prepared or submitted this cannot approve or reject it.';
    END IF;
    IF NEW.action = 'REJECT' AND coalesce(length(trim(NEW.comment)), 0) < 3 THEN
      RAISE EXCEPTION 'A rejection needs a reason.';
    END IF;
    IF NEW.action = 'APPROVE' THEN
      SELECT results_digest INTO submitted_digest FROM approval
       WHERE submission_id = s.id AND action = 'SUBMIT' ORDER BY id DESC LIMIT 1;
      IF submitted_digest IS DISTINCT FROM NEW.results_digest THEN
        RAISE EXCEPTION 'The results changed after they were submitted. They must be submitted again.';
      END IF;
    END IF;
    UPDATE submission SET workflow_status = CASE NEW.action WHEN 'APPROVE' THEN 'APPROVED' ELSE 'REJECTED' END,
                          decided_by = NEW.actor_id, decided_at = now(),
                          locked = (NEW.action = 'APPROVE')
     WHERE id = s.id;
  END IF;
  RETURN NEW;
END $$;

CREATE TRIGGER approval_guard_trg BEFORE INSERT ON approval
  FOR EACH ROW EXECUTE FUNCTION approval_guard();

-- Append only, except when a whole workspace is deleted (demo expiry).
CREATE OR REPLACE FUNCTION append_only() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
  IF TG_OP = 'DELETE' AND NOT EXISTS (SELECT 1 FROM workspace WHERE id = OLD.workspace_id) THEN
    RETURN OLD;
  END IF;
  RAISE EXCEPTION '% is append only', TG_TABLE_NAME;
END $$;

CREATE TRIGGER approval_append_only BEFORE UPDATE OR DELETE ON approval
  FOR EACH ROW EXECUTE FUNCTION append_only();
CREATE TRIGGER review_note_append_only BEFORE UPDATE OR DELETE ON review_note
  FOR EACH ROW EXECUTE FUNCTION append_only();

-- Notes can only be added while the submission is open (not submitted, not approved).
CREATE OR REPLACE FUNCTION review_note_guard() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
  s submission;
BEGIN
  SELECT * INTO s FROM submission WHERE id = NEW.submission_id;
  IF s.locked THEN
    RAISE EXCEPTION 'This submission is approved and locked.';
  END IF;
  IF NEW.kind = 'explanation' AND s.workflow_status = 'SUBMITTED' THEN
    RAISE EXCEPTION 'Explanations cannot change while the submission is with the approver.';
  END IF;
  NEW.created_at := clock_timestamp();
  RETURN NEW;
END $$;

CREATE TRIGGER review_note_guard_trg BEFORE INSERT ON review_note
  FOR EACH ROW EXECUTE FUNCTION review_note_guard();

-- Once approved, the results and the data behind them cannot change.
CREATE OR REPLACE FUNCTION locked_guard() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
  sub uuid := CASE WHEN TG_OP = 'DELETE' THEN OLD.submission_id ELSE NEW.submission_id END;
BEGIN
  -- Deleting a whole expired demo workspace is allowed (its row is already gone).
  IF TG_OP = 'DELETE' AND NOT EXISTS (SELECT 1 FROM workspace WHERE id = OLD.workspace_id) THEN
    RETURN OLD;
  END IF;
  IF EXISTS (SELECT 1 FROM submission WHERE id = sub AND locked) THEN
    RAISE EXCEPTION 'This submission is approved and locked; its % cannot change.', TG_TABLE_NAME;
  END IF;
  RETURN CASE WHEN TG_OP = 'DELETE' THEN OLD ELSE NEW END;
END $$;

DO $$
DECLARE t text;
BEGIN
  FOREACH t IN ARRAY ARRAY['metric_result', 'validation_result', 'gold_balance', 'dataset', 'upload'] LOOP
    EXECUTE format('CREATE TRIGGER %I BEFORE INSERT OR UPDATE OR DELETE ON %I '
                   'FOR EACH ROW EXECUTE FUNCTION locked_guard()', t || '_locked_guard', t);
  END LOOP;
END $$;

CREATE OR REPLACE FUNCTION submission_lock_guard() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
  IF OLD.locked AND (NEW.locked IS DISTINCT FROM OLD.locked
                     OR NEW.status IS DISTINCT FROM OLD.status
                     OR NEW.period_end IS DISTINCT FROM OLD.period_end
                     OR NEW.institution IS DISTINCT FROM OLD.institution
                     OR NEW.workflow_status IS DISTINCT FROM OLD.workflow_status) THEN
    RAISE EXCEPTION 'This submission is approved and locked.';
  END IF;
  RETURN NEW;
END $$;

CREATE TRIGGER submission_lock_guard_trg BEFORE UPDATE ON submission
  FOR EACH ROW EXECUTE FUNCTION submission_lock_guard();

-- Row level security for the new tables.
DO $$
DECLARE t text;
BEGIN
  FOREACH t IN ARRAY ARRAY['workspace_member', 'review_note', 'approval'] LOOP
    EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', t);
    EXECUTE format('ALTER TABLE %I FORCE ROW LEVEL SECURITY', t);
    EXECUTE format(
      'CREATE POLICY workspace_isolation ON %I USING (workspace_id = current_workspace()) '
      'WITH CHECK (workspace_id = current_workspace())', t);
  END LOOP;
END $$;
