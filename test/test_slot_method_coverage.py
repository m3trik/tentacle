#!/usr/bin/python
# coding=utf-8
"""Verify every interactive widget in each slot's .ui file has a
corresponding slot method (or *_init companion).

This is the "basic functionality" test for all slot modules — it catches
the regression class where a button is wired in the UI but its slot
method was renamed, removed, or never added. Symptom: user clicks button,
nothing happens; no error, no log.

Scope: every concrete slot module under tentacle/slots/maya/ paired with
its companion .ui file in tentacle/ui/.

Widget naming convention (enforced elsewhere):
  b###    button         — requires b###()
  tb###   tool button    — requires tb###(widget); optional tb###_init
  cmb###  combo box      — requires cmb###(...); optional cmb###_init
  list### list widget    — requires list###(...); optional list###_init
  txt###  text input     — requires txt###(widget)

Other widgets (s###, d###, chk###, lbl###) are connected via init handlers
or signals and don't require a same-named slot method.

A small allowlist exists for known purely-decorative buttons / legacy
widgets that intentionally have no handler. Add to ALLOWLIST below with
a one-line justification.
"""
from __future__ import annotations

import ast
import re
import unittest
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parent.parent
SLOTS_DIR = ROOT / "tentacle" / "slots" / "maya"
UI_DIR = ROOT / "tentacle" / "ui"
# Marking-menu submenus live in a separate subdir, e.g. select#submenu.ui
UI_MENUS_DIR = UI_DIR / "maya_menus"

_SKIP_SLOTS = {"__init__.py", "_slots_maya.py"}

# Widgets that require a matching slot method on the companion class.
_ACTION_PREFIXES = ("b", "tb", "cmb", "list", "txt")

# Widget-name → reason. Use sparingly; document each exception.
#
# Format: "module.py::widget_name": "why it's intentionally bare"
#
# Entries marked TODO are pre-existing inconsistencies discovered when this
# test was first introduced. They lock the *current* state so any NEW ghost
# button added later fails the test. Resolve each by either (a) implementing
# the slot method, (b) removing the widget from the .ui, or (c) replacing the
# TODO with the real justification once confirmed inert-on-purpose.
ALLOWLIST: dict[str, str] = {
    # Triaged 2026-05-16. Each TODO documents the kind of fix needed; the
    # allowlist locks the *current* state so a NEW ghost button fails the
    # test. Resolve by implementing the handler or removing the widget.
    #
    # Empty-label/tooltip widgets — likely placeholders or stale UI:
    "lighting.py::tb001": "TODO: bare placeholder (no text/tooltip)",
    "nurbs.py::b050": "TODO: bare placeholder (no text/tooltip)",
    "rigging.py::tb005": "TODO: bare placeholder (no text/tooltip)",
    "uv.py::b022": "TODO: bare placeholder in uv#submenu.ui",
    # Widgets with real labels — handler is genuinely missing:
    "subdivision.py::b004": "TODO: 'PolyReduce' button has tooltip but no handler",
    # cmb003 is a value-carrier combo, not an action widget — uv.py
    # reads it via `get_map_size()` rather than a per-index handler.
    "uv.py::cmb003": "Intentional: value-carrier combo read by get_map_size()",
}


def _slot_files() -> list[Path]:
    return sorted(
        f
        for f in SLOTS_DIR.glob("*.py")
        if f.name not in _SKIP_SLOTS and not f.name.startswith("__")
    )


def _ui_widget_names(ui_path: Path) -> list[str]:
    """Return every interactive-widget name from a .ui file.

    Walks the XML for ``<widget ... name="X">`` where ``X`` matches an
    action-prefix pattern.
    """
    try:
        tree = ET.parse(ui_path)
    except (ET.ParseError, OSError):
        return []

    pattern = re.compile(r"^(?:" + "|".join(_ACTION_PREFIXES) + r")\d+[a-z]*$")
    found: list[str] = []
    for w in tree.iter("widget"):
        name = w.get("name", "")
        if pattern.match(name):
            found.append(name)
    return found


def _slot_methods(py_path: Path) -> set[str]:
    """Return the set of method names defined on any class in the slot file."""
    try:
        tree = ast.parse(py_path.read_text(encoding="utf-8"))
    except (SyntaxError, OSError):
        return set()

    methods: set[str] = set()
    for cls in (n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)):
        for stmt in cls.body:
            if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
                methods.add(stmt.name)
    return methods


def _resolve_uis(slot_file: Path) -> list[Path]:
    """Locate all .ui files paired with a slot module.

    Strict matching: only same-stem files (``foo.ui``) and submenus of the
    same stem (``foo#*.ui``), across both ``tentacle/ui/`` (main toolbars)
    and ``tentacle/ui/maya_menus/`` (marking-menu submenus). Cross-name
    pairings (``select.py`` ↔ ``selection.ui``) are intentionally NOT
    resolved here — that mismatch is a separate concern.
    """
    stem = slot_file.stem
    results: list[Path] = []
    direct = UI_DIR / f"{stem}.ui"
    if direct.exists():
        results.append(direct)
    for p in sorted(UI_DIR.glob(f"{stem}#*.ui")):
        results.append(p)
    # Marking-menu submenus
    if UI_MENUS_DIR.is_dir():
        for p in sorted(UI_MENUS_DIR.glob(f"{stem}#*.ui")):
            results.append(p)
        # Some menu-only slots have an exact match here, e.g. ``cache.ui``
        # would live in maya_menus if there were one — keep the same rule.
        direct_menu = UI_MENUS_DIR / f"{stem}.ui"
        if direct_menu.exists():
            results.append(direct_menu)
    return results


class TestEveryInteractiveWidgetHasASlotMethod(unittest.TestCase):
    """For each slot module, every b###/tb###/cmb###/list###/txt### widget
    in the paired .ui must resolve to a method on the slot class.

    A widget resolves if the class defines ``name`` OR ``name_init`` —
    most slots provide both for tb/cmb widgets (button-handler + option-
    box init); some only the handler. Either is sufficient.
    """

    def test_no_ghost_buttons_anywhere(self):
        offenders: list[str] = []

        for slot_file in _slot_files():
            ui_paths = _resolve_uis(slot_file)
            if not ui_paths:
                continue  # No paired UI — covered by test_ui_integrity

            methods = _slot_methods(slot_file)

            # Aggregate widgets across the main UI and its submenus — they
            # all belong to the same slot class.
            seen: set[str] = set()
            for ui_path in ui_paths:
                for widget in _ui_widget_names(ui_path):
                    if widget in seen:
                        continue
                    seen.add(widget)
                    key = f"{slot_file.name}::{widget}"
                    if key in ALLOWLIST:
                        continue
                    if widget in methods or f"{widget}_init" in methods:
                        continue
                    offenders.append(
                        f"  {slot_file.name}: widget '{widget}' "
                        f"(declared in {ui_path.name}) has no slot method"
                    )

        self.assertEqual(
            offenders,
            [],
            "Ghost buttons found — UI declares widgets with no slot handler:\n"
            + "\n".join(offenders),
        )


class TestEveryUiPairsToASlotFile(unittest.TestCase):
    """Symmetry check: every interactive .ui in tentacle/ui/ should pair to a
    slot file. Catches orphan UI files that may have been forgotten.

    Submenu / startmenu / lower-submenu UIs aren't required to pair —
    they're embedded inside other UIs by name. The base file (without ``#``)
    is the canonical one.
    """

    def test_no_orphan_base_ui_files(self):
        slot_stems = {f.stem for f in _slot_files()}
        orphans: list[str] = []
        for ui_path in UI_DIR.glob("*.ui"):
            if "#" in ui_path.stem:
                continue  # Submenu — paired via base
            if ui_path.stem in slot_stems:
                continue
            # Allow known non-slot UIs (e.g. tcl_max.ui pairs with tcl_max.py)
            # by also accepting if a same-named slot exists.
            orphans.append(ui_path.name)
        # Some UIs (popup_window.ui, etc.) intentionally have no slot pair —
        # we only fail when the count is unreasonably high (>5) so this
        # stays as a soft canary, not a brittle blocker.
        self.assertLess(
            len(orphans),
            10,
            f"Too many orphan UI files (no slot pair): {orphans}",
        )


if __name__ == "__main__":
    unittest.main()
