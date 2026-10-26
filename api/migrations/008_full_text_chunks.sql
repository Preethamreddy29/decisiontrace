ALTER TABLE source_chunks ADD COLUMN content_text text;
UPDATE source_chunks c
SET content_text = substring(s.content from c.start_char + 1 for c.end_char - c.start_char)
FROM source_versions s
WHERE s.tenant_id = c.tenant_id AND s.id = c.source_version_id;
ALTER TABLE source_chunks ALTER COLUMN content_text SET NOT NULL;
ALTER TABLE source_chunks ADD COLUMN search_vector tsvector
    GENERATED ALWAYS AS (to_tsvector('english'::regconfig, content_text)) STORED;
CREATE INDEX source_chunks_fts_idx ON source_chunks USING gin (search_vector);
