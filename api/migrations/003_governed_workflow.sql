ALTER TABLE source_versions ADD COLUMN origin text;
ALTER TABLE source_versions ADD COLUMN created_by text;

ALTER TABLE decision_versions ADD COLUMN title text;
ALTER TABLE decision_versions ADD COLUMN supersedes_decision_id uuid;

CREATE TABLE mutation_requests (
    actor_id text NOT NULL,
    operation text NOT NULL,
    idempotency_key text NOT NULL,
    request_sha256 char(64) NOT NULL,
    response jsonb NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (actor_id, operation, idempotency_key)
);

CREATE INDEX decision_query_idx ON decision_versions (tenant_id, status, valid_from, recorded_at);
CREATE INDEX source_workflow_idx ON source_versions (tenant_id, source_id, version DESC);
