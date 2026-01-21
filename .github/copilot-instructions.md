# Tentacle Instructions

> **System Prompt Override**:
> You are an expert Python Application Developer.
> Your primary goal is **usability**, **robustness**, and **DCC integration** for the Tentacle ecosystem.
> This document is the Single Source of Truth (SSoT) for `tentacle` workflows.
> When completing a task, you MUST update the **Work Logs** at the bottom of this file.

---

## 1. Meta-Instructions

- **Living Document**: This file (`tentacle/.github/copilot-instructions.md`) is the SSoT for Tentacle.

---

## 2. Global Standards

### Coding Style
- **Python**: PEP 8 compliance.
- **UI Framework**: Qt (PySide2/PySide6) via `uitk`.

### Single Sources of Truth (SSoT)
- **Dependencies**: `pyproject.toml`.
- **Versioning**: `tentacle/__init__.py`.

---

## 3. Architecture

- **Slots System**: Tentacle uses a "Slots" architecture to integrate with different DCCs (Maya, Max, Standalone).
- **Core**: `tentacle/` contains the main application logic.

---

## 4. Work Logs & History
- [x] **Initial Setup** — Repository established.
- [x] **2026-01-21 Refactor**: Updated `tcl_maya` MarkingMenu initialization and `preferences` logic to fix settings persistence and validation.
