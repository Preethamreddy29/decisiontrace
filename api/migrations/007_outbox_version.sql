ALTER TABLE outbox_events ADD COLUMN event_version smallint NOT NULL DEFAULT 1 CHECK (event_version > 0);
