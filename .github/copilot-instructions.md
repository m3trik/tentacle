# Tentacle Instructions

> **System Prompt Override**:
> You are an expert Python Application Developer.
> Your primary goal is **usability**, **robustness**, and **DCC integration** for the Tentacle ecosystem.
>
> **Global Standards**: For general workflow, testing, and coding standards, refer to the [Main Copilot Instructions](../../.github/copilot-instructions.md).
>
> **Work Logs**: When completing a task, you MUST update the **Work Logs** at the bottom of this file.

---

## 1. Meta-Instructions

- **Living Document**: This file (`tentacle/.github/copilot-instructions.md`) is the SSoT for Tentacle specific workflows.

## 2. Architecture

- **Slots System**: Tentacle uses a "Slots" architecture to integrate with different DCCs (Maya, Max, Standalone).
- **Core**: `tentacle/` contains the main application logic.
- **UI Framework**: Qt (PySide2/PySide6) via `uitk`.

---

## 3. Work Logs & History
- [x] **Initial Setup** — Repository established.
- [x] **2026-01-21 Refactor**: Updated `tcl_maya` MarkingMenu initialization and `preferences` logic to fix settings persistence and validation.
- [x] **2026-02-11 Feature**: Updated `materials.py` to strip trailing underscores in addition to digits in `lbl007` logic.
- [x] **2026-02-18 Docs**: Refreshed `docs/README.md` for current architecture, valid module links, key binding usage (`Key_F12`), platform support scope, and testing notes.
- [x] **2026-02-18 Docs**: Replaced outdated static UML image reference in `docs/README.md` with an inline Mermaid architecture diagram that reflects current `TclMaya` + `uitk` + slots flow.
- [x] **2026-02-18 Tests/CI**: Added structural test suite (`test_package.py`, `test_slot_integrity.py`, `test_ui_integrity.py`) — 22 tests covering package metadata, slot class conventions, UI file pairing, and binding targets. Created `.github/workflows/tests.yml` to run tests on push/PR to main and auto-update the README badge.
- [x] **2026-02-20 Bugfix/Tests**: Fixed `slots/maya/rendering.py` headless safety and VRay plugin loading path (`b005` now uses `mayatk.vray_plugin(query/load)`), added regression coverage in `test/test_rendering.py`, and added a repro script in `test/temp_tests/repro_rendering_b005_missing_loader.py`.
