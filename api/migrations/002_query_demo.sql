ALTER TABLE source_versions ADD COLUMN external_label text;

CREATE UNIQUE INDEX source_external_label_unique
    ON source_versions (tenant_id, external_label)
    WHERE external_label IS NOT NULL;

CREATE TABLE query_requests (
    actor_id text NOT NULL,
    idempotency_key text NOT NULL,
    request_sha256 char(64) NOT NULL,
    answer jsonb NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (actor_id, idempotency_key)
);
