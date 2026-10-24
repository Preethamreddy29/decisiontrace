"""One-command local static checks; Docker smoke is a separate integration gate."""

import subprocess
import sys
from os import name as os_name
from pathlib import Path
from shutil import which


ROOT = Path(__file__).resolve().parents[1]


def run(*command: str, cwd: Path = ROOT) -> None:
    executable = command[0]
    if os_name == "nt" and executable == "npm":
        executable = which("npm.cmd") or executable
    elif os_name == "nt" and executable == "docker":
        executable = which("docker.exe") or executable
    resolved = (executable, *command[1:])
    print("Running:", " ".join(command), flush=True)
    subprocess.run(resolved, cwd=cwd, check=True)


def main() -> None:
    run(sys.executable, "tools/validate_corpus.py")
    run(sys.executable, "tools/validate_contracts.py")
    run(sys.executable, "tools/check_secrets.py", "--self-test")
    if not (ROOT / "web" / "node_modules").exists():
        run("npm", "ci", cwd=ROOT / "web")
    run("npm", "run", "build", cwd=ROOT / "web")
    run("docker", "compose", "--env-file", ".env.example", "config", "--quiet")
    print("Static checks passed. Run the Docker smoke command for live integration evidence.")


if __name__ == "__main__":
    main()
