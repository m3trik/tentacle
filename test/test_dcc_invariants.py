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

# dcc package dir -> required base class.
DCCS = {"maya": "SlotsMaya", "blender": "SlotsBlender"}


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


if __name__ == "__main__":
    unittest.main()
