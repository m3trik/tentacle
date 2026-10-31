#!/usr/bin/python
# coding=utf-8
"""Host-agnostic structural invariants of the slots layer.

One Slots class per category, shared by every host (``slots/<category>.py``), and no
per-host slot package beside them: the chord menus' native-menu pages need no Slots
class (each host's UI handler builds its own menus). Plus the layer's import
discipline. AST-based: no DCC runtime needed.
"""

import ast
import collections
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SLOTS_ROOT = ROOT / "tentacle" / "slots"

#: The hosts, none of which keeps a slot package of its own (``slots/<host>/``).
HOSTS = ("maya", "blender", "max")


def _parse_classes(source):
    """[(class_name, [base_names])] from source."""
    classes = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.ClassDef):
            bases = [
                b.id if isinstance(b, ast.Name) else b.attr
                for b in node.bases
                if isinstance(b, (ast.Name, ast.Attribute))
            ]
            classes.append((node.name, bases))
    return classes


def _set_object_names(source):
    """All ``setObjectName="..."`` string literals (AST — comments can't false-positive)."""
    return [
        kw.value.value
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.Call)
        for kw in node.keywords
        if kw.arg == "setObjectName"
        and isinstance(kw.value, ast.Constant)
        and isinstance(kw.value.value, str)
    ]


class TestNoPerHostSlotPackage(unittest.TestCase):
    """No host keeps a slot package: a category is one composed class every host
    shares (``TestComposedSlots``), a tool's Slots class lives in ``slots/tools/``,
    and the chord menus' native-menu pages (``ui/maya_menus``, ``ui/blender_menus``)
    carry no Slots class at all -- the switchboard resolves each page's target
    through the host's UI handler, which builds the host's own menu."""

    def test_no_host_keeps_a_slot_package(self):
        present = [host for host in HOSTS if (SLOTS_ROOT / host).exists()]
        self.assertEqual(present, [], f"a per-host slot package is back: {present}")


# Every module in the slots layer: the composed categories, the shared tools and
# their helpers (the import rules below apply to all of them).
def _all_slot_modules():
    return sorted(
        f
        for f in SLOTS_ROOT.rglob("*.py")
        if f.name != "__init__.py" and "__pycache__" not in f.parts
    )


def _imports(source):
    """[(module, imported_name)] for every ``from X import Y`` (absolute only)."""
    out = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.ImportFrom) and node.module and not node.level:
            out.extend((node.module, a.name) for a in node.names)
        elif isinstance(node, ast.Import):
            out.extend((a.name, None) for a in node.names)
    return out


def _composed_files():
    """The composed Slots modules: ``slots/<category>.py``, one class every host shares."""
    return sorted(f for f in SLOTS_ROOT.glob("*.py") if not f.name.startswith("_"))


class TestComposedSlots(unittest.TestCase):
    """A composed ``slots/<category>.py`` is that category's one Slots class: one
    ``<Base>Slots(Slots)`` (the name uitk binds and shortcut overrides key on); no
    per-host fork is left beside it (``TestNoPerHostSlotPackage``: two classes of one
    name break the Slots lookup)."""

    def test_each_defines_one_slots_subclass_named_base_slots(self):
        offenders = {}
        for f in _composed_files():
            found = [
                name
                for name, bases in _parse_classes(f.read_text(encoding="utf-8"))
                if "Slots" in bases
            ]
            if found != [f.stem.title().replace("_", "") + "Slots"]:
                offenders[f.name] = found
        self.assertEqual(offenders, {}, f"Composed modules off the rule: {offenders}")

    def test_unique_object_names(self):
        offenders = {}
        for f in _composed_files():
            names = _set_object_names(f.read_text(encoding="utf-8"))
            dupes = {n: c for n, c in collections.Counter(names).items() if c > 1}
            if dupes:
                offenders[f.name] = dupes
        self.assertEqual(offenders, {}, f"duplicate widget objectNames: {offenders}")

    def test_a_tool_panel_names_each_widget_once(self):
        """An option-box item registers with its window, whose saved state is keyed
        ``<objectName>/<signal>``: two boxes each building a ``chk002`` share one
        saved value. Naming's Rename and Suffix By Location boxes did (``chk002``,
        ``chk007``), so a toggle in one came back in the other."""
        offenders = {}
        for f in sorted((SLOTS_ROOT / "tools").glob("*.py")):
            names = _set_object_names(f.read_text(encoding="utf-8"))
            dupes = {n: c for n, c in collections.Counter(names).items() if c > 1}
            if dupes:
                offenders[f.name] = dupes
        self.assertEqual(offenders, {}, f"duplicate widget objectNames: {offenders}")

    def test_the_composed_checks_are_not_vacuous(self):
        self.assertTrue(_composed_files(), f"no composed Slots module in {SLOTS_ROOT}")


class TestSlotImportDiscipline(unittest.TestCase):
    """The slots layer reaches upstream packages through their namespaces only.

    Two rules, both silent-erosion-prone and so pinned here rather than in a doc:

    1. **uitk comes off the Switchboard**, never a bare import. Every slot instance
       is handed ``self.sb``, which resolves the whole uitk namespace
       (``self.sb.IconManager``), the short names (``self.sb.style``,
       ``self.sb.registered_widgets.X``) and its children's APIs
       (``self.ui.footer.status_controller(...)``). The sole exemption is
       ``_slots.py``, where ``Signals`` / ``Cancelable`` are re-exposed on the base:
       they are class-body decorators, evaluated before any instance — and so before
       any ``self.sb`` — exists.
    2. **No deep module paths** into an upstream package. ``mtk.ScriptJobManager``,
       not ``mayatk.core_utils.script_job_manager``; a deep path hard-codes a layout
       that is not the package's contract. Applies to tentacle's own namespace too
       (``from tentacle import Slots``).
    """

    #: Only this module may import uitk directly — see rule 1.
    _UITK_IMPORT_EXEMPT = {"_slots.py"}

    #: ``bootstrap_package`` installs the resolver, so it cannot come through it.
    #: pythontk publishes ``Mapping`` and ``Behaviors`` by module path on purpose
    #: (generic names kept off its top level): that path is their contract.
    _DEEP_IMPORT_EXEMPT = {
        ("pythontk.core_utils.module_resolver", "bootstrap_package"),
        ("pythontk.core_utils.engines.shots.manifest.mapping", "Mapping"),
        ("pythontk.core_utils.engines.shots.manifest.behaviors", "Behaviors"),
    }

    _NAMESPACED = ("pythontk", "uitk", "mayatk", "blendertk", "tentacle")

    def test_uitk_is_reached_through_the_switchboard(self):
        offenders = {}
        for f in _all_slot_modules():
            if f.name in self._UITK_IMPORT_EXEMPT:
                continue
            hits = [
                f"{mod}{'.' + name if name else ''}"
                for mod, name in _imports(f.read_text(encoding="utf-8"))
                if mod.split(".")[0] == "uitk"
            ]
            if hits:
                offenders[str(f.relative_to(SLOTS_ROOT))] = hits
        self.assertEqual(
            offenders,
            {},
            "Slot modules must reach uitk through self.sb (self.sb.IconManager, "
            "self.sb.style, self.sb.registered_widgets.X, self.ui.footer...), not by "
            f"importing it: {offenders}",
        )

    def test_upstream_packages_are_reached_by_namespace(self):
        offenders = {}
        for f in _all_slot_modules():
            hits = [
                f"from {mod} import {name}"
                for mod, name in _imports(f.read_text(encoding="utf-8"))
                if name
                and mod.split(".")[0] in self._NAMESPACED
                and "." in mod
                and (mod, name) not in self._DEEP_IMPORT_EXEMPT
            ]
            if hits:
                offenders[str(f.relative_to(SLOTS_ROOT))] = hits
        self.assertEqual(
            offenders,
            {},
            "Slot modules must import from the package namespace (mtk.X / btk.X / "
            f"`from tentacle import XMixin`), not a deep module path: {offenders}",
        )

    def test_a_maya_plugin_loads_through_mayatks_door(self):
        """``mtk.Plugins.load`` loads by name, never into GUI Maya's untrusted-plug-in
        prompt; mayatk's own guard (``mock_tests/test_plugins.py``) covers mayatk."""
        offenders = [
            f"{f.relative_to(SLOTS_ROOT)}:{node.lineno}"
            for f in _all_slot_modules()
            for node in ast.walk(ast.parse(f.read_text(encoding="utf-8")))
            if isinstance(node, ast.Call)
            and getattr(node.func, "attr", None) == "loadPlugin"
        ]
        self.assertEqual(offenders, [], "load plug-ins through mtk.Plugins.load")


if __name__ == "__main__":
    unittest.main()
