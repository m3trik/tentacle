"""Claude Code SessionStart hook, written by pythontk's AgentInstructions.sync
(edit its template, not this copy): adds this codebase's agent packs to a session
rooted here, but none a CLAUDE.md above already imports (a workspace root's stub
imports its own, and Claude Code loads it in every session below it).

Claude Code runs it as `python`, with no shell: a virtual environment provides
one, as does python-is-python3 on Debian and Ubuntu. Without one the packs are
not added, and AGENTS.md still links them. A file it cannot read is skipped, and
it never fails the session."""
import json
from pathlib import Path

LIMIT = 10000


def read(path, errors="strict"):
    """*path*'s text, or None when it cannot be read (locked, gone, not UTF-8)."""
    try:
        return path.read_text(encoding="utf-8-sig", errors=errors)
    except (OSError, UnicodeError):
        return None


try:
    here = Path(__file__).resolve().parent
    provided = set()
    for parent in here.parent.parents:
        for line in (read(parent / "CLAUDE.md", "replace") or "").splitlines():
            ref = Path(line.strip()[1:])
            if line.startswith("@") and ref.parent.as_posix().endswith(".agents/packs"):
                provided.add(ref.name)
    packs = sorted((here / "packs").glob("*.md"))
    texts = [read(p) for p in packs if p.name not in provided]
    text = "\n\n".join(t for t in texts if t and t.strip())
    if text:
        out = {"hookEventName": "SessionStart", "additionalContext": text[:LIMIT]}
        print(json.dumps({"hookSpecificOutput": out}))
except Exception:  # a hook that fails costs the session its packs, nothing more
    pass
