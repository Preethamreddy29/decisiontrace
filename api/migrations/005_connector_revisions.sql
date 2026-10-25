CREATE TABLE connector_revisions (
    tenant_id uuid NOT NULL REFERENCES tenants(id),
    connector_id text NOT NULL,
    external_id text NOT NULL,
    remote_version text NOT NULL,
    source_version_id uuid NOT NULL,
    PRIMARY KEY (tenant_id, connector_id, external_id, remote_version),
    CONSTRAINT connector_revision_source_fk FOREIGN KEY (tenant_id, source_version_id)
        REFERENCES source_versions(tenant_id, id) ON DELETE CASCADE
);
