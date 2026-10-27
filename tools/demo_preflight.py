"""Build, seed, and verify the local fictional demo before manual testing."""

import subprocess
import sys
from pathlib import Path
from shutil import which


ROOT = Path(__file__).resolve().parents[1]
COMPOSE = (which("docker") or "docker", "compose", "--env-file", ".env.example")


def run(*command: str) -> None:
    print("Running:", " ".join(command), flush=True)
    subprocess.run(command, cwd=ROOT, check=True)


def main() -> None:
    run(sys.executable, "tools/check_all.py")
    run(*COMPOSE, "up", "--build", "-d", "--quiet-build")
    for module in (
        "api.app.seed", "api.app.smoke", "tools.eval_demo", "tools.eval_v02",
        "tools.eval_v03", "tools.eval_v04", "tools.eval_v05",
        "tools.eval_holdout_v05", "tools.eval_demo_readiness", "tools.eval_oidc_route",
        "tools.eval_v06_revocation", "tools.eval_v06_watches", "tools.eval_v07_outbox",
        "tools.eval_v07_concurrency", "tools.eval_v08_search",
        "tools.eval_v10_rebuild",
    ):
        run(*COMPOSE, "exec", "-T", "api", "python", "-m", module)
    run(sys.executable, "tools/verify_backup_restore.py")
    print("Demo preflight passed. Open http://127.0.0.1:5174/ and follow docs/release/demo-test-guide.md.")


if __name__ == "__main__":
    main()
