"""`make dev`: run the FastAPI backend (:8000) and the Vite frontend (:5173) together.

A small Python launcher instead of shell tricks, so it behaves the same under cmd, PowerShell and bash.
On Windows the children are put in a Job Object that is closed when this launcher exits, even if it is
killed hard; otherwise uvicorn's reload worker keeps serving a stale app on :8000.
"""

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _kill_children_with_me():
    """Windows: return a job handle; every process assigned to it dies when this process exits."""
    if sys.platform != "win32":
        return None
    import ctypes
    from ctypes import wintypes

    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.CreateJobObjectW.restype = wintypes.HANDLE
    job = k32.CreateJobObjectW(None, None)

    class IoCounters(ctypes.Structure):
        _fields_ = [(n, ctypes.c_ulonglong) for n in ("r", "w", "o", "rb", "wb", "ob")]

    class BasicLimits(ctypes.Structure):
        _fields_ = [("PerProcessUserTimeLimit", ctypes.c_int64), ("PerJobUserTimeLimit", ctypes.c_int64),
                    ("LimitFlags", wintypes.DWORD), ("MinimumWorkingSetSize", ctypes.c_size_t),
                    ("MaximumWorkingSetSize", ctypes.c_size_t), ("ActiveProcessLimit", wintypes.DWORD),
                    ("Affinity", ctypes.c_size_t), ("PriorityClass", wintypes.DWORD), ("SchedulingClass", wintypes.DWORD)]

    class ExtendedLimits(ctypes.Structure):
        _fields_ = [("Basic", BasicLimits), ("Io", IoCounters), ("ProcessMemoryLimit", ctypes.c_size_t),
                    ("JobMemoryLimit", ctypes.c_size_t), ("PeakProcessMemoryUsed", ctypes.c_size_t),
                    ("PeakJobMemoryUsed", ctypes.c_size_t)]

    info = ExtendedLimits()
    info.Basic.LimitFlags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
    k32.SetInformationJobObject(job, 9, ctypes.byref(info), ctypes.sizeof(info))  # ExtendedLimitInformation
    # Children inherit the job from this process, so assigning ourselves covers uv, uvicorn and its workers.
    k32.AssignProcessToJobObject(job, k32.GetCurrentProcess())
    return job


def main() -> int:
    uv = shutil.which("uv")
    pnpm = shutil.which("pnpm")
    if not uv or not pnpm:
        print("dev: need both `uv` and `pnpm` on PATH", file=sys.stderr)
        return 1
    job = _kill_children_with_me()  # noqa: F841 - must stay referenced for the launcher's lifetime
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
