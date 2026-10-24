CREATE TABLE tenants (
    id uuid PRIMARY KEY,
    name text NOT NULL UNIQUE
);

CREATE TABLE source_versions (
    id uuid PRIMARY KEY,
    source_id uuid NOT NULL,
    tenant_id uuid NOT NULL REFERENCES tenants(id),
    version integer NOT NULL CHECK (version > 0),
    kind text NOT NULL,
    recorded_at timestamptz NOT NULL,
    valid_from date NOT NULL,
    valid_to date,
    status text NOT NULL,
    content_sha256 char(64) NOT NULL,
    content text NOT NULL,
    roles text[] NOT NULL,
    revoked_at timestamptz,
    superseded_at timestamptz,
    CONSTRAINT source_valid_interval CHECK (valid_to IS NULL OR valid_to > valid_from),
    CONSTRAINT source_version_unique UNIQUE (tenant_id, source_id, version),
    CONSTRAINT source_version_tenant_identity UNIQUE (tenant_id, id)
);

CREATE TABLE decision_versions (
    id uuid PRIMARY KEY,
    decision_id uuid NOT NULL,
    tenant_id uuid NOT NULL REFERENCES tenants(id),
    version integer NOT NULL CHECK (version > 0),
    status text NOT NULL CHECK (status IN ('draft', 'in_review', 'approved', 'rejected', 'superseded')),
    valid_from date NOT NULL,
    valid_to date,
    recorded_at timestamptz NOT NULL,
    owner_id uuid NOT NULL,
    approver_id uuid,
    evidence_version_ids uuid[] NOT NULL,
    CONSTRAINT decision_valid_interval CHECK (valid_to IS NULL OR valid_to > valid_from),
    CONSTRAINT decision_version_unique UNIQUE (tenant_id, decision_id, version)
);

CREATE TABLE ingestion_jobs (
    id uuid PRIMARY KEY,
    tenant_id uuid NOT NULL REFERENCES tenants(id),
    source_version_id uuid NOT NULL,
    status text NOT NULL,
    failure_code text,
    updated_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT ingestion_source_tenant_fk FOREIGN KEY (tenant_id, source_version_id)
        REFERENCES source_versions(tenant_id, id)
);

CREATE TABLE audit_events (
    id uuid PRIMARY KEY,
    tenant_id uuid NOT NULL REFERENCES tenants(id),
    actor_id uuid,
    action text NOT NULL,
    subject_id uuid NOT NULL,
    occurred_at timestamptz NOT NULL DEFAULT now(),
    detail jsonb NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE outbox_events (
    id uuid PRIMARY KEY,
    tenant_id uuid NOT NULL REFERENCES tenants(id),
    event_type text NOT NULL,
    payload jsonb NOT NULL,
    state text NOT NULL DEFAULT 'pending' CHECK (state IN ('pending', 'leased', 'done', 'dead_letter')),
    attempts integer NOT NULL DEFAULT 0 CHECK (attempts >= 0),
    lease_until timestamptz,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX outbox_claim_idx ON outbox_events (state, lease_until, created_at);
