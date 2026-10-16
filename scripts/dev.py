"""`make dev`: run the FastAPI backend (:8000) and the Vite frontend (:5173) together.

A small Python launcher instead of shell tricks, so it behaves the same under cmd, PowerShell and bash.
"""

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    uv = shutil.which("uv")
    pnpm = shutil.which("pnpm")
    if not uv or not pnpm:
        print("dev: need both `uv` and `pnpm` on PATH", file=sys.stderr)
        return 1
    procs = [
        subprocess.Popen(
            [uv, "run", "uvicorn", "domino.api.main:app", "--reload", "--host", "127.0.0.1", "--port", "8000"],
            cwd=ROOT / "backend",
        ),
        subprocess.Popen([pnpm, "dev"], cwd=ROOT / "frontend"),
    ]
    try:
        for p in procs:
            p.wait()
    except KeyboardInterrupt:
        pass
    finally:
        for p in procs:
            if p.poll() is None:
                p.terminate()
    return 0


if __name__ == "__main__":
    sys.exit(main())
