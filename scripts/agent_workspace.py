r"""`make agent-workspace`: create C:\dev\domino-agent (a sibling of the repo) for Claude Code as the agent.

The folder sits outside the repo on purpose: Claude Code loads CLAUDE.md files from parent folders, and
the repo's CLAUDE.md holds build instructions, not the agent's job. Re-running refreshes the three files.
"""

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "demo" / "claude-code-agent"
DST = ROOT.parent / "domino-agent"


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    # The agent's instructions live with the MCP server (it serves them to remote clients too).
    files = {"CLAUDE.md": ROOT / "backend" / "domino" / "mcp" / "playbook.md",
             ".mcp.json": SRC / ".mcp.json", ".claude/settings.json": SRC / ".claude" / "settings.json"}
    for rel, src in files.items():
        target = DST / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, target)
    print(f"Agent workspace ready: {DST}")
    print("1. Start DOMINO:  make dev   (the MCP server is http://127.0.0.1:8000/mcp/)")
    print("2. In the war room choose 'Claude Code · MCP' and press 'Watch Claude Code'.")
    print(f"3. Open Claude Code in {DST}, allow the 'domino' MCP server when asked, and paste the prompt.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
