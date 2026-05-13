# tentacle — Changelog

## 2026

- **2026-05-11 Bugfix** — `edit.py tb001` (Delete History → Delete Unused Nodes) was deleting instanced objects. Empty-group sweep used `cmds.ls` without `allPaths=True`, so only one DAG path per instanced node was listed; sibling instance transforms then appeared in `groups` but not in `dag_parents` and were deleted. Added `dag=True, allPaths=True` to the three `cmds.ls` calls that build `all_dag`, `exact_transforms`, and `shape_parents`. Regression test in `test/test_edit.py` (shape instance, transform instance, truly-empty group).
- **2026-03-26 Bugfix** — `ExpandableList list000` (Create Primitive) double-execution. `eventFilter` wasn't consuming `MouseButtonRelease` after emitting `on_item_interacted`, allowing re-trigger. Added `return True` after emission in `uitk/widgets/expandableList.py`.
- **2026-03-03 Perf** — `edit.py tb001` (Delete History) optimized for heavy scenes. Replaced PyMEL bulk queries with `maya.cmds`, batch-extracted shapes via `cmds.listRelatives`, DAG path-parsing with `exactType` for empty-group detection, filtered intermediate shapes, suspended viewport refresh, moved `message_box` outside the suspend block. Added AST regression tests in `test_slot_integrity.py`.
- **2026-02-26 Feature** — Animation Copy Keys button (`b001`) gained `copy_keys` / `paste_keys` modes: current frame, selected keys (Graph Editor), channel box. Core logic added as `AnimUtils.copy_keys` / `paste_keys` in mayatk.
- **2026-02-20 Bugfix/Tests** — `slots/maya/rendering.py` headless safety + VRay plugin loading (`b005` uses `mayatk.vray_plugin(query/load)`). Added regression coverage in `test/test_rendering.py` and repro in `test/temp_tests/repro_rendering_b005_missing_loader.py`.
- **2026-02-18 Tests/CI** — Structural suite (`test_package.py`, `test_slot_integrity.py`, `test_ui_integrity.py`) — 22 tests covering package metadata, slot conventions, UI pairing, binding targets. Added `.github/workflows/tests.yml` with README badge auto-update.
- **2026-02-18 Docs** — Refreshed `docs/README.md` for current architecture, module links, key binding usage (`Key_F12`), platform scope, testing notes.
- **2026-02-18 Docs** — Replaced outdated static UML image with inline Mermaid diagram reflecting `TclMaya` + `uitk` + slots flow.
- **2026-02-11 Feature** — `materials.py` strips trailing underscores in addition to digits in `lbl007` logic.
- **2026-01-21 Refactor** — Updated `tcl_maya` MarkingMenu init and `preferences` logic; fixed settings persistence + validation.
