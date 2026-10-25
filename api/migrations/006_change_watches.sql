CREATE TABLE change_watches (
    id uuid PRIMARY KEY,
    tenant_id uuid NOT NULL REFERENCES tenants(id),
    decision_version_id uuid NOT NULL REFERENCES decision_versions(id),
    decision_evidence_version_id uuid NOT NULL,
    downstream_source_id uuid NOT NULL,
    baseline_source_version_id uuid NOT NULL,
    relation_type text NOT NULL CHECK (relation_type IN ('implements', 'tests', 'measures')),
    created_by text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, decision_version_id, downstream_source_id, relation_type)
);
CREATE INDEX change_watches_tenant_idx ON change_watches (tenant_id, created_at);
CREATE TABLE change_watch_reviews (
    id uuid PRIMARY KEY,
    watch_id uuid NOT NULL REFERENCES change_watches(id) ON DELETE CASCADE,
    observed_source_version_id uuid NOT NULL REFERENCES source_versions(id),
    outcome text NOT NULL CHECK (outcome IN ('drift', 'aligned')),
    reason text NOT NULL,
    reviewed_by text NOT NULL,
    reviewed_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (watch_id, observed_source_version_id)
);
