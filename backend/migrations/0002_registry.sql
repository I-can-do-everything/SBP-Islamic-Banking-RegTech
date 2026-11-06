-- A list of workspaces and their expiry dates, readable without a workspace session,
-- so the cleanup job can find expired demo workspaces. It holds no bank data.
CREATE TABLE workspace_registry (
  id          uuid PRIMARY KEY,
  expires_at  timestamptz NOT NULL
);

-- Summary written by the AI step is stored per submission; keep only the latest version easy to find.
CREATE INDEX ai_narrative_sub_idx ON ai_narrative (submission_id, created_at DESC);
