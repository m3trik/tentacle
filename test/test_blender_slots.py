#!/usr/bin/python
# coding=utf-8
"""Blender-specific structural guards.

Covers what only applies to the Blender layer: the consolidated ``tcl_blender`` entry point
(Qt host + keymap bridge + launcher + add-on surface), the cross-DCC objectName semantics
rule, and the M2 shared-UI contract. The DCC-agnostic slot invariants (package/base wiring,
one base-subclass per file, unique objectNames) live in the parametrized
``test_dcc_invariants.py`` (plan M1) — not here. AST-based: no Blender runtime needed.
"""
import ast
import re
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PKG = ROOT / "tentacle"
SLOTS_DIR = PKG / "slots" / "blender"
MAYA_SLOTS_DIR = PKG / "slots" / "maya"
_SKIP = {"__init__.py", "_slots_blender.py"}


def _slot_files():
    """Concrete Blender slot modules (excludes package marker + base)."""
    return sorted(
        f
        for f in SLOTS_DIR.glob("*.py")
        if f.name not in _SKIP and not f.name.startswith("__")
    )


def _created_widget_texts(path):
    """{objectName: setText} for widgets created via menu.add(..., setObjectName=..., setText=...)."""
    out = {}
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if not isinstance(node, ast.Call):
            continue
        kwargs = {
            kw.arg: kw.value.value
            for kw in node.keywords
            if kw.arg in ("setObjectName", "setText")
            and isinstance(kw.value, ast.Constant)
            and isinstance(kw.value.value, str)
        }
        if "setObjectName" in kwargs:
            out[kwargs["setObjectName"]] = kwargs.get("setText")
    return out


class TestCrossDccObjectNameSemantics(unittest.TestCase):
    """A Blender slot may only reuse a Maya objectName for the SAME option.

    Widget state persists per loaded UI: ``MainWindow`` builds ``SettingsManager(app=<ui name>)``
    and ``StateManager`` keys entries ``<objectName>/<signal>``. Both DCCs load the same shared
    ``.ui``, so they read/write the SAME store — a name carrying a different meaning (e.g. Maya
    ``chk025`` = "Overlapping Faces" vs Blender ``chk025`` = "Delete Loose") silently bleeds
    checkbox state across DCCs. New Blender-only options must take numbers unused by the Maya
    counterpart file (different domains have separate stores and don't collide).
    """

    # Intentional, documented divergences where a shared objectName legitimately carries a
    # different label per DCC. The cross-DCC object-send button is a *counterpart pair* named
    # after its TARGET app (Blender's menu → "Maya Bridge", Maya's menu → "Blender Bridge"); same
    # objectName, same store key, same concept (open the bridge to the OTHER app), opposite label
    # by design. See blendertk/docs/STRUCTURE.md (display_utils row, cross-DCC object send).
    _ALLOWED_DIVERGENCE = {"scene.py:b010"}

    def test_shared_object_names_mean_the_same_thing(self):
        conflicts = {}
        for bl_file in _slot_files():
            maya_file = MAYA_SLOTS_DIR / bl_file.name
            if not maya_file.exists():
                continue
            bl = _created_widget_texts(bl_file)
            my = _created_widget_texts(maya_file)
            for name in sorted(set(bl) & set(my)):
                key = f"{bl_file.name}:{name}"
                if key in self._ALLOWED_DIVERGENCE:
                    continue
                bl_text, my_text = bl[name], my[name]
                if bl_text and my_text and bl_text.casefold() != my_text.casefold():
                    conflicts[key] = (bl_text, my_text)
        self.assertEqual(
            conflicts,
            {},
            f"objectName reused with different semantics (blender vs maya): {conflicts}",
        )


UI_DIR = PKG / "ui"
# Widget-name shapes the slot layer is contractually bound to (option-box/header widgets the
# slots create themselves are out of scope here — covered by the semantics test above).
_INTERACTIVE = re.compile(r"^(tb|b|chk|cmb|s|list|txt)\d")


def _ui_interactive_widgets(domain):
    """Interactive widget objectNames across the domain's shared .ui files
    (``<domain>.ui`` + ``<domain>#*.ui``; never the maya_menus overlay)."""
    names = set()
    for f in UI_DIR.glob(f"{domain}*.ui"):
        if not (f.stem == domain or f.stem.startswith(domain + "#")):
            continue
        for w in ET.parse(f).iter("widget"):
            n = w.get("name") or ""
            if _INTERACTIVE.match(n):
                names.add(n)
    return names


def _class_method_names(path):
    methods = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.ClassDef):
            for x in node.body:
                if isinstance(x, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    methods.add(x.name)
    return methods


class TestSharedUiContract(unittest.TestCase):
    """M2 — the shared-.ui safety net (BLENDER_PORT_PLAN §6).

    For every ported Blender domain, each interactive widget in the shared ``.ui`` that the
    *Maya* slot implements must be either implemented by the Blender slot (a deferred-message
    stub counts — the widget then says so instead of dying silently) or explicitly handled in
    a ``<name>_init`` (the hide-until-ported mechanism). Catches a renamed/dropped widget that
    would otherwise become a silent dead button in one DCC.
    """

    def test_maya_implemented_widgets_covered_or_hidden(self):
        gaps = {}
        for bl_file in _slot_files():
            maya_file = MAYA_SLOTS_DIR / bl_file.name
            if not maya_file.exists():
                continue
            domain = bl_file.stem
            ui_widgets = _ui_interactive_widgets(domain)
            if not ui_widgets:
                continue
            maya_methods = _class_method_names(maya_file)
            blender_methods = _class_method_names(bl_file)
            missing = sorted(
                w
                for w in ui_widgets
                if w in maya_methods
                and w not in blender_methods
                and f"{w}_init" not in blender_methods
            )
            if missing:
                gaps[domain] = missing
        self.assertEqual(
            gaps,
            {},
            "Shared-.ui widgets implemented in Maya but neither implemented nor hidden "
            f"(via <name>_init) in the Blender slot: {gaps}",
        )


class TestBlenderPlumbingParses(unittest.TestCase):
    """The consolidated Blender entry point parses cleanly (deferred bpy import keeps it valid
    outside a Blender runtime; qtpy/uitk load only after ``_bootstrap_paths`` runs)."""

    def test_launcher_parses(self):
        path = PKG / "tcl_blender.py"
        self.assertTrue(path.exists(), "Missing tcl_blender.py")
        ast.parse(path.read_text(encoding="utf-8"))  # raises SyntaxError on failure

    def test_addon_surface_present(self):
        """The add-on/launcher surface folded in from blender_host/blender_addon is intact."""
        source = (PKG / "tcl_blender.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        funcs = {n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
        self.assertTrue(
            {"launch", "register", "unregister", "ensure_qapp", "start_event_pump", "diagnose"}
            <= funcs,
            f"Consolidated entry point missing host/add-on functions: have {sorted(funcs)}",
        )
        self.assertTrue(
            any(isinstance(n, ast.Assign)
                and any(getattr(t, "id", None) == "bl_info" for t in n.targets)
                for n in tree.body),
            "tcl_blender.py must define bl_info (add-on surface)",
        )


def _attr_chain(node):
    """Dotted name for an attribute/name chain (``bpy.ops.wm.tool_set_by_id``), else ""."""
    parts = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
        return ".".join(reversed(parts))
    return ""


class TestViewportToolUsesOverride(unittest.TestCase):
    """Activating a builtin viewport tool must go through ``set_viewport_tool``.

    A bare ``bpy.ops.wm.tool_set_by_id`` invoked from the Qt marking menu runs in a
    restricted context (``context.space_data is None``): it returns success but the tool
    silently never changes — the "Multi-Cut does nothing" bug. ``SlotsBlender.set_viewport_tool``
    wraps it in a VIEW_3D ``temp_override`` so it lands on the real viewport. The base class is
    the only place allowed to call the op directly; concrete slots route through the helper.
    """

    def test_no_concrete_slot_calls_tool_set_by_id_directly(self):
        offenders = {}
        for f in _slot_files():
            for node in ast.walk(ast.parse(f.read_text(encoding="utf-8"))):
                if isinstance(node, ast.Call) and _attr_chain(node.func).endswith(
                    "ops.wm.tool_set_by_id"
                ):
                    offenders.setdefault(f.name, []).append(getattr(node, "lineno", "?"))
        self.assertEqual(
            offenders,
            {},
            "Concrete Blender slots must call self.set_viewport_tool(...) rather than "
            f"bpy.ops.wm.tool_set_by_id directly (silently no-ops from the marking menu): {offenders}",
        )


class TestModeGatedViewportTools(unittest.TestCase):
    """A tool that only exists in a component mode must declare ``edit_type``.

    Blender resolves a workspace tool by (space_type, *context mode*), so activating one of
    these from Object Mode raises "Tool 'builtin.knife' not found for space 'VIEW_3D'" instead
    of doing anything. ``edit_type`` makes ``set_viewport_tool`` enter the mode first, the way
    Maya's counterparts do implicitly. Availability probed against Blender 5.1 by enumerating
    ``ToolSelectPanelHelper.tools_from_context`` per mode: measure / annotate / select_* exist
    in every mode and correctly pass no ``edit_type``.
    """

    _EDIT_ONLY = {
        "builtin.knife": "MESH",
        "builtin.loop_cut": "MESH",
        "builtin.poly_build": "MESH",
        "builtin.pen": "CURVE",
        "builtin.draw": "CURVE",
    }

    def test_edit_mode_only_tools_declare_edit_type(self):
        offenders = []
        for f in _slot_files():
            for node in ast.walk(ast.parse(f.read_text(encoding="utf-8"))):
                if not (
                    isinstance(node, ast.Call)
                    and _attr_chain(node.func).endswith("set_viewport_tool")
                    and node.args
                    and isinstance(node.args[0], ast.Constant)
                ):
                    continue
                expected = self._EDIT_ONLY.get(node.args[0].value)
                if not expected:
                    continue
                declared = next(
                    (
                        kw.value.value
                        for kw in node.keywords
                        if kw.arg == "edit_type" and isinstance(kw.value, ast.Constant)
                    ),
                    None,
                )
                if declared != expected:
                    offenders.append(
                        f"{f.name}:{node.lineno} {node.args[0].value} "
                        f"declares edit_type={declared!r}, expected {expected!r}"
                    )
        self.assertEqual(
            offenders,
            [],
            "Edit-Mode-only viewport tools must pass edit_type so set_viewport_tool enters "
            f"component mode first (else Blender reports 'not found for space'): {offenders}",
        )


if __name__ == "__main__":
    unittest.main()
