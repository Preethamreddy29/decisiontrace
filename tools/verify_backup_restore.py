"""Back up and restore the running local stack into a disposable database."""

import secrets
import subprocess
import tempfile
from pathlib import Path
from shutil import which


ROOT = Path(__file__).resolve().parents[1]
COMPOSE = [which("docker") or "docker", "compose", "--env-file", ".env.example"]


def run(*args: str, stdin=None, stdout=None) -> None:
    subprocess.run([*COMPOSE, *args], cwd=ROOT, stdin=stdin, stdout=stdout, check=True)


def db_command(script: str, database_name: str, stdin=None, stdout=None) -> None:
    run("exec", "-T", "db", "sh", "-c", script, "_", database_name, stdin=stdin, stdout=stdout)


def api_command(module: str, database_name: str) -> None:
    command = f'DATABASE_URL="${{DATABASE_URL%/*}}/{database_name}" python -m {module}'
    run("exec", "-T", "api", "sh", "-c", command)


def main() -> None:
    database_name = "dt_restore_" + secrets.token_hex(6)
    created = False
    with tempfile.TemporaryFile() as snapshot:
        db_command(
            'PGPASSWORD="$POSTGRES_PASSWORD" pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc',
            database_name, stdout=snapshot,
        )
        snapshot.seek(0)
        try:
            db_command(
                'PGPASSWORD="$POSTGRES_PASSWORD" createdb -U "$POSTGRES_USER" "$1"',
                database_name,
            )
            created = True
            db_command(
                'PGPASSWORD="$POSTGRES_PASSWORD" pg_restore --exit-on-error --no-owner --no-acl '
                '-U "$POSTGRES_USER" -d "$1"',
                database_name, stdin=snapshot,
            )
            api_command("api.app.migrate", database_name)
            api_command("tools.eval_restore_snapshot", database_name)
        finally:
            if created:
                db_command(
                    'PGPASSWORD="$POSTGRES_PASSWORD" dropdb --if-exists -U "$POSTGRES_USER" "$1"',
                    database_name,
                )


if __name__ == "__main__":
    main()
