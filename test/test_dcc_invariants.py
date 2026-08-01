#!/usr/bin/python
# coding=utf-8
"""DCC-agnostic structural invariants, parametrized over every slot package (plan M1).

One source of truth for the checks every DCC slot layer must hold — package/base wiring,
exactly one base-subclass per slot file, unique widget objectNames per slot. The per-DCC
files keep only what is genuinely DCC-specific (``test_slot_integrity``: pymel ban + cmds
perf; ``test_blender_slots``: launcher/add-on surface, cross-DCC objectName semantics, the
M2 shared-UI contract). AST-based: no DCC runtime needed. A new DCC slot package is covered
by adding one entry to ``DCCS``.
"""
import ast
import collections
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SLOTS_ROOT = ROOT / "tentacle" / "slots"

# dcc package dir -> required base class. Maya is the established baseline and is
# ALWAYS enforced (a missing slots/maya/ is a real regression these invariants must
# catch). The Blender slot layer is built on dev but deliberately held off main
# while under construction, so it is covered only on checkouts where its slot dir
# is present — keeping main green without weakening the Maya guarantee. Add a
# stable DCC to DCCS directly; gate an under-construction one on its dir.
DCCS = {"maya": "SlotsMaya"}
# Detect via the base FILE, not the dir: a leftover __pycache__/ keeps the dir
# present after the slot sources are removed, which would wrongly include Blender.
if (SLOTS_ROOT / "blender" / "_slots_blender.py").is_file():
    DCCS["blender"] = "SlotsBlender"


def _slot_files(dcc):
    """Concrete slot modules for a DCC (excludes the package marker + base)."""
    d = SLOTS_ROOT / dcc
    skip = {"__init__.py", f"_slots_{dcc}.py"}
    return sorted(
        f
        for f in d.glob("*.py")
        if f.name not in skip and not f.name.startswith("__")
    )


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


class TestDccSlotInvariants(unittest.TestCase):
    """The invariants shared by every DCC slot package."""

    def test_package_and_base_wiring(self):
        """Slot dir + __init__ + base file exist; the base inherits Slots."""
        for dcc, base in DCCS.items():
            with self.subTest(dcc=dcc):
                d = SLOTS_ROOT / dcc
                self.assertTrue(d.is_dir(), f"Missing directory: {d}")
                self.assertTrue((d / "__init__.py").exists(), "Missing __init__.py")
                base_file = d / f"_slots_{dcc}.py"
                self.assertTrue(base_file.exists(), f"Missing {base_file.name}")
                classes = _parse_classes(base_file.read_text(encoding="utf-8"))
                self.assertTrue(
                    any(name == base and "Slots" in bases for name, bases in classes),
                    f"{base} must inherit from Slots",
                )

    def test_exactly_one_base_subclass_per_file(self):
        """Every slot module defines exactly one <SlotsDcc> subclass."""
        offenders = {}
        for dcc, base in DCCS.items():
            for f in _slot_files(dcc):
                found = [
                    name
                    for name, bases in _parse_classes(f.read_text(encoding="utf-8"))
                    if base in bases
                ]
                if len(found) != 1:
                    offenders[f"{dcc}/{f.name}"] = found
        self.assertEqual(
            offenders, {}, f"Slot files without exactly one base subclass: {offenders}"
        )

    def test_unique_object_names_per_slot(self):
        """Widget objectNames a slot adds must be unique within that slot — duplicates
        collide the StateManager/QSettings key ``<name>/<signal>`` and the cross-UI sync
        lookup ("edit one field, another field changes")."""
        offenders = {}
        for dcc in DCCS:
            for f in _slot_files(dcc):
                names = _set_object_names(f.read_text(encoding="utf-8"))
                dupes = {n: c for n, c in collections.Counter(names).items() if c > 1}
                if dupes:
                    offenders[f"{dcc}/{f.name}"] = dupes
        self.assertEqual(
            offenders,
            {},
            "Slot files add duplicate widget objectNames (each collides its StateManager "
            f"key + cross-UI sync — give the later one a free name): {offenders}",
        )


# Every module in the slots layer: the concrete per-DCC panels plus the shared
# ``slots/_<panel>.py`` mixins (the import rules below apply to both).
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
       (``from tentacle import SceneMixin``).
    """

    #: Only this module may import uitk directly — see rule 1.
    _UITK_IMPORT_EXEMPT = {"_slots.py"}

    #: ``bootstrap_package`` installs the resolver, so it cannot come through it.
    _DEEP_IMPORT_EXEMPT = {("pythontk.core_utils.module_resolver", "bootstrap_package")}

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


if __name__ == "__main__":
    unittest.main()
