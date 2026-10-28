# Slot tests (Maya-required)

Migration validation for `tentacle/slots/maya/*.py` after the PyMEL → `maya.cmds` / `maya.mel` migration.

These tests **require a Maya runtime** (mayapy or running inside Maya) because
they import `maya.cmds` and `maya.mel`. They are skipped automatically when
Maya is unavailable, so they don't break the regular `python run_tests.py`
on a workstation without Maya.

## What's covered

| File | Validates |
|:---|:---|
| `test_slot_modules_import.py` | Each slot module under `tentacle.slots.maya.*` imports cleanly inside a Maya runtime. Catches missing imports, broken module-level code, syntax issues that AST parse missed. |
| `test_cmds_references.py` | Every `cmds.X(...)` call site in the slots resolves (`hasattr(maya.cmds, "X")` is `True`). Catches typos like `cmds.displayInfo` (doesn't exist). |
| `test_mel_references.py` | First token of every `mel.eval("Y …")` literal string resolves via `whatIs`. Reports unknowns as failures so missing MEL procs surface immediately. |
| `test_fstring_mel_references.py` | First token of every `mel.eval(f"Y …{expr}…")` static prefix resolves via `whatIs`. Same class of typo as above but for f-string forms (`manipPivotReset`, `texStraightenUVs`, etc.). |
| `test_dynamic_mel_commands.py` | MEL strings stored in module/class-level constant tables (e.g. a MEL dispatch table in a `slots/maya/` fork) are scanned for first-token resolvability. Catches typos in dispatch tables that the call-site scanner can't follow. |
| `test_namespace_references.py` | Every `mtk.X(.Y)?` and `ptk.X(.Y)?` chain in the slots resolves against the actual `mayatk` / `pythontk` package. Both use a dynamic attribute resolver, so missing names don't fail at import — only at click time. |

The tests deliberately **do not** instantiate slot classes or run their
button handlers — those depend on the full tentacle UI / switchboard / Qt
setup, which is integration-test territory. The point of this suite is to
catch the typo class of regression introduced by the migration.

## Running

Three modes, picked via flags on the main tentacle runner:

| Mode | Invocation | Total | Pass | Skip | Use when |
|:---|:---|---:|---:|---:|:---|
| Plain Python | `python run_tests.py` | 38 | 29 | 9 | No Maya available; quick syntax / structural check |
| mayapy.standalone | `mayapy.exe run_tests.py --include-slots` | 41 | 40 | 1 | Fast Maya iteration; widget test skips (batch-mode Qt stub) |
| **Real Maya GUI** | **`python run_tests.py --in-maya`** | **41** | **41** | **0** | **Canonical 100% — required before sign-off** |

### `--in-maya` (canonical)

```powershell
python o:\Cloud\Code\_scripts\tentacle\test\run_tests.py --in-maya
```

Uses `mayatk.MayaConnection` to launch a **fresh** Maya instance on an
unused port, dispatches the full suite (main + slots) over the command
port, polls for completion, then closes Maya. Per the monorepo hard
rule (`mayatk/CLAUDE.md`), this always uses `force_new_instance=True` —
existing Maya sessions are never touched. There is no `--reuse` path.

Optional: `--keep-maya` keeps the launched Maya open after tests for
inspection.

### `--include-slots` (fast / CI)

```powershell
& "C:\Program Files\Autodesk\Maya2025\bin\mayapy.exe" `
    tentacle\test\run_tests.py --include-slots
```

Initializes `maya.standalone` in-process — much faster startup than
launching a full GUI, but `test_overlay_safety` skips because
`mayapy.standalone`'s Qt is a headless stub: even with a `QApplication`
promoted via other imports, `QtWidgets.QWidget()` aborts the interpreter
with no Python-level traceback. This is a Maya 2025 batch-mode Qt
limitation, not a code bug. Use `--in-maya` to actually run that test.

`run_in_maya.py` still exists as a slot-only entry point if you need to
run just this subdirectory; the main runner is preferred for the full
suite.
