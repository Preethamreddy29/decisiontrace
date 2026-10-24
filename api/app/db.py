"""Small PostgreSQL boundary shared by the API and foundation commands."""

import psycopg


def connect(database_url: str):
    return psycopg.connect(database_url, connect_timeout=3)


def is_ready(database_url: str) -> bool:
    with connect(database_url) as connection:
        connection.execute("SELECT 1").fetchone()
        row = connection.execute("SELECT count(*) FROM schema_migrations").fetchone()
        return row is not None and row[0] >= 1
