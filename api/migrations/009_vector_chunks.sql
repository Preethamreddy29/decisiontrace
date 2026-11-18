CREATE EXTENSION IF NOT EXISTS vector;
ALTER TABLE source_chunks ADD COLUMN embedding vector(64);
ALTER TABLE source_chunks ADD COLUMN embedding_profile text;
ALTER TABLE source_chunks ADD COLUMN embedding_sha256 char(64);
CREATE INDEX source_chunks_vector_scope_idx ON source_chunks (tenant_id, embedding_profile);
