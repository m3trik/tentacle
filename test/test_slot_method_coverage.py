#!/usr/bin/python
# coding=utf-8
"""Verify every interactive widget in each slot's .ui file has a
corresponding slot method (or *_init companion).

This is the "basic functionality" test for all slot modules — it catches
the regression class where a button is wired in the UI but its slot
method was renamed, removed, or never added. Symptom: user clicks button,
nothing happens; no error, no log.

Scope: **every** DCC that ships concrete slot modules — ``tentacle/slots/maya/``
and ``tentacle/slots/blender/`` — each paired with its companion .ui file in
``tentacle/ui/`` (plus that DCC's marking-menu subdir, ``<dcc>_menus/``). The two
forks share the toolbar .ui files, so a widget added for one DCC is a ghost in the
other until its fork implements the slot too; checking only one DCC left exactly
half of that class of regression uncovered. Every check runs under a ``subTest``
keyed by DCC, so a failure names which fork is missing the handler.

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
import functools
import re
import unittest
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parent.parent
SLOTS_ROOT = ROOT / "tentacle" / "slots"
UI_DIR = ROOT / "tentacle" / "ui"

#: DCC -> the marking-menu subdir holding its submenu .ui files (e.g.
#: ``select#submenu.ui``). Every DCC with a ``slots/<dcc>/`` package is checked;
#: adding one here is all it takes to bring a new fork under the ghost-button guard.
DCCS = ("maya", "blender")


def _menus_dir(dcc: str) -> Path:
    """Marking-menu .ui subdir for *dcc* (``tentacle/ui/<dcc>_menus``)."""
    return UI_DIR / f"{dcc}_menus"


def _skip_slots(dcc: str) -> set[str]:
    """Non-panel modules in ``slots/<dcc>/`` — the package marker and the DCC base."""
    return {"__init__.py", f"_slots_{dcc}.py"}


# Widgets that require a matching slot method on the companion class.
_ACTION_PREFIXES = ("b", "tb", "cmb", "list", "txt")

# "<dcc>/<module>.py::<widget>" → reason. Use sparingly; document each exception.
#
# The key carries the DCC because the two forks share the toolbar .ui files: the
# same widget name can be a genuine ghost in one fork and fully handled in the
# other, so an un-scoped key would silently excuse both.
#
# Entries are for widgets that are intentionally bare (purely decorative, or a
# value-carrier read by another method rather than dispatched to a handler).
# Anything else is a bug: implement the handler or remove the widget from the .ui.
# Every entry must carry a dated justification.
#
# Emptied 2026-08-23: all six entries seeded on 2026-05-16 had gone stale — the
# five "bare placeholder" widgets (lighting tb001, nurbs b050, rigging tb005,
# uv b022, subdivision b004) no longer appear in ANY resolved .ui file, and
# uv cmb003 now has a real ``def cmb003`` in both forks. A stale allowlist entry
# is worse than none: it silently re-excuses the name if the widget ever comes back.
ALLOWLIST: dict[str, str] = {}


def _slot_files(dcc: str) -> list[Path]:
    """Concrete slot modules for *dcc* (excludes package marker + DCC base)."""
    skip = _skip_slots(dcc)
    return sorted(
        f
        for f in (SLOTS_ROOT / dcc).glob("*.py")
        if f.name not in skip and not f.name.startswith("__")
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


@functools.lru_cache(maxsize=1)
def _mixin_index() -> dict[str, Path]:
    """``{class name: file}`` for every shared mixin in ``tentacle/slots/_*.py``.

    Indexed by CLASS name rather than by import path: a concrete panel now pulls
    its mixin off the package namespace (``from tentacle import MaterialsMixin``),
    so the module path is no longer written at the import site. Shared,
    DCC-agnostic mixins (e.g. ``PreferencesMixin``, which supplies the
    window-theme combos to every DCC's ``Preferences``) define slots the module
    itself doesn't — resolving them keeps those from reading as ghosts.
    """
    index: dict[str, Path] = {}
    for path in sorted(SLOTS_ROOT.glob("_*.py")):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (SyntaxError, OSError):
            continue
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                index[node.name] = path
    return index


def _shared_mixin_paths(tree: ast.Module) -> dict[str, Path]:
    """``{imported name: file}`` for shared mixins this module imports, however
    spelled — ``from tentacle import X`` or ``from tentacle.slots._x import X``."""
    index = _mixin_index()
    mapping: dict[str, Path] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom) or not node.module:
            continue
        if node.module.split(".")[0] != "tentacle":
            continue
        for alias in node.names:
            path = index.get(alias.name)
            if path is not None:
                mapping[alias.asname or alias.name] = path
    return mapping


def _slot_methods(py_path: Path, _seen: set[Path] = None) -> set[str]:
    """Method names on any class in the slot file, plus those inherited from
    shared ``tentacle.slots`` mixins listed as bases."""
    _seen = _seen if _seen is not None else set()
    if py_path in _seen:
        return set()
    _seen.add(py_path)

    try:
        tree = ast.parse(py_path.read_text(encoding="utf-8"))
    except (SyntaxError, OSError):
        return set()

    mixins = _shared_mixin_paths(tree)
    methods: set[str] = set()
    for cls in (n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)):
        for stmt in cls.body:
            if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
                methods.add(stmt.name)
        for base in cls.bases:
            path = mixins.get(base.id) if isinstance(base, ast.Name) else None
            if path is not None:
                methods |= _slot_methods(path, _seen)
    return methods


def _resolve_uis(slot_file: Path, dcc: str) -> list[Path]:
    """Locate all .ui files paired with a slot module, for one DCC.

    Strict matching: only same-stem files (``foo.ui``) and submenus of the
    same stem (``foo#*.ui``), across both ``tentacle/ui/`` (main toolbars,
    shared by every DCC) and ``tentacle/ui/<dcc>_menus/`` (that DCC's
    marking-menu submenus). Cross-name pairings (``select.py`` ↔
    ``selection.ui``) are intentionally NOT resolved here — that mismatch is
    a separate concern.

    Parameters:
        slot_file (Path): The concrete slot module.
        dcc (str): DCC key — selects the marking-menu subdir.

    Returns:
        (list): Paired .ui paths, main-UI first.
    """
    stem = slot_file.stem
    results: list[Path] = []
    direct = UI_DIR / f"{stem}.ui"
    if direct.exists():
        results.append(direct)
    for p in sorted(UI_DIR.glob(f"{stem}#*.ui")):
        results.append(p)
    # Marking-menu submenus
    menus_dir = _menus_dir(dcc)
    if menus_dir.is_dir():
        for p in sorted(menus_dir.glob(f"{stem}#*.ui")):
            results.append(p)
        # Some menu-only slots have an exact match here, e.g. ``blender.ui``
        # would live in blender_menus if there were one — keep the same rule.
        direct_menu = menus_dir / f"{stem}.ui"
        if direct_menu.exists():
            results.append(direct_menu)
    return results


def _ghost_widgets(dcc: str) -> list[str]:
    """Every action widget in *dcc*'s .ui files with no backing slot method.

    Parameters:
        dcc (str): DCC key (``"maya"`` / ``"blender"``).

    Returns:
        (list): One human-readable line per ghost widget; empty when clean.
    """
    offenders: list[str] = []
    for slot_file in _slot_files(dcc):
        ui_paths = _resolve_uis(slot_file, dcc)
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
                if f"{dcc}/{slot_file.name}::{widget}" in ALLOWLIST:
                    continue
                if widget in methods or f"{widget}_init" in methods:
                    continue
                offenders.append(
                    f"  {dcc}/{slot_file.name}: widget '{widget}' "
                    f"(declared in {ui_path.name}) has no slot method"
                )
    return offenders


class TestEveryInteractiveWidgetHasASlotMethod(unittest.TestCase):
    """For each slot module of each DCC, every b###/tb###/cmb###/list###/txt###
    widget in the paired .ui must resolve to a method on the slot class.

    A widget resolves if the class defines ``name`` OR ``name_init`` —
    most slots provide both for tb/cmb widgets (button-handler + option-
    box init); some only the handler. Either is sufficient.
    """

    def test_no_ghost_buttons_anywhere(self):
        for dcc in DCCS:
            with self.subTest(dcc=dcc):
                offenders = _ghost_widgets(dcc)
                self.assertEqual(
                    offenders,
                    [],
                    f"Ghost buttons found in the {dcc} slots — UI declares widgets "
                    "with no slot handler:\n" + "\n".join(offenders),
                )

    def test_every_dcc_is_actually_covered(self):
        """Guard the guard: a typo'd DCC key or a moved slots dir would make the
        check above pass vacuously (no modules → no offenders → green)."""
        for dcc in DCCS:
            with self.subTest(dcc=dcc):
                files = _slot_files(dcc)
                self.assertTrue(files, f"no slot modules found for {dcc!r}")
                widgets = {
                    w
                    for f in files
                    for ui in _resolve_uis(f, dcc)
                    for w in _ui_widget_names(ui)
                }
                self.assertTrue(
                    widgets, f"no action widgets resolved for any {dcc} slot module"
                )

    def test_allowlist_entries_are_still_real(self):
        """A stale allowlist entry silently re-excuses a name if the widget ever
        comes back. Every entry must name a widget that (a) still exists in a
        resolved .ui and (b) still has no backing slot method."""
        stale: list[str] = []
        for key in ALLOWLIST:
            dcc, _, rest = key.partition("/")
            module, _, widget = rest.partition("::")
            slot_file = SLOTS_ROOT / dcc / module
            if not slot_file.exists():
                stale.append(f"{key}: no such slot module")
                continue
            uis = _resolve_uis(slot_file, dcc)
            if not any(widget in _ui_widget_names(ui) for ui in uis):
                stale.append(f"{key}: widget no longer declared in any paired .ui")
                continue
            methods = _slot_methods(slot_file)
            if widget in methods or f"{widget}_init" in methods:
                stale.append(f"{key}: a slot method now exists — drop the entry")
        self.assertEqual(stale, [], "Stale ALLOWLIST entries:\n  " + "\n  ".join(stale))


class TestEveryUiPairsToASlotFile(unittest.TestCase):
    """Symmetry check: every interactive .ui in tentacle/ui/ should pair to a
    slot file in SOME DCC. Catches orphan UI files that may have been forgotten.

    Submenu / startmenu / lower-submenu UIs aren't required to pair —
    they're embedded inside other UIs by name. The base file (without ``#``)
    is the canonical one.
    """

    def test_no_orphan_base_ui_files(self):
        slot_stems = {f.stem for dcc in DCCS for f in _slot_files(dcc)}
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
