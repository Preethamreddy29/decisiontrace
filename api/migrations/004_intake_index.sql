ALTER TABLE query_requests ADD COLUMN tenant_id uuid REFERENCES tenants(id);
CREATE INDEX query_requests_tenant_idx ON query_requests (tenant_id);

CREATE TABLE source_chunks (
    tenant_id uuid NOT NULL REFERENCES tenants(id),
    source_version_id uuid NOT NULL,
    chunk_id text NOT NULL,
    section_id text NOT NULL,
    start_char integer NOT NULL CHECK (start_char >= 0),
    end_char integer NOT NULL CHECK (end_char > start_char),
    content_sha256 char(64) NOT NULL,
    chunker_version text NOT NULL,
    PRIMARY KEY (source_version_id, chunk_id),
    CONSTRAINT source_chunks_source_fk FOREIGN KEY (tenant_id, source_version_id)
        REFERENCES source_versions(tenant_id, id) ON DELETE CASCADE
);
CREATE INDEX source_chunks_tenant_idx ON source_chunks (tenant_id, source_version_id);

CREATE TABLE connector_objects (
    tenant_id uuid NOT NULL REFERENCES tenants(id),
    connector_id text NOT NULL,
    external_id text NOT NULL,
    source_id uuid NOT NULL,
    remote_version text NOT NULL,
    source_version_id uuid NOT NULL,
    PRIMARY KEY (tenant_id, connector_id, external_id),
    CONSTRAINT connector_source_fk FOREIGN KEY (tenant_id, source_version_id)
        REFERENCES source_versions(tenant_id, id)
);
