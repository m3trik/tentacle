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
