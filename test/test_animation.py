#!/usr/bin/python
# coding=utf-8
"""Regression / smoke tests for tentacle.slots.maya.animation.

This module is 1700 lines of UI orchestration — the actual animation
logic (curve scaling, stepping, baking, audio-shift, manifest) lives in
mayatk and is covered by:

    test_anim_utils.py · test_scale_keys.py · test_stagger_keys.py ·
    test_smart_bake.py · test_segment_keys.py ·
    test_audio_utils_*.py · test_shot_*.py · test_blendshape_animator.py

What's worth pinning at this layer:

1. Structural completeness — every advertised slot method is present.
   Catches accidental removal that the audit-style smoke test in
   test_slot_integrity does not catch (it does shape, not method roster).

2. Module import — Animation imports a long list of mayatk symbols at
   module top. A broken import would break the entire animation toolbar.

3. tb017's mode-string -> keys-argument translation — the only branching
   pure-Python logic in the file that isn't a thin mtk wrapper.

4. Tooltip claims. The panel's promises live in three places — the shared
   ``.ui``, each fork's option-box ``setToolTip``, and the ``_TOOLS_ITEMS``
   roster — and nothing at runtime notices when one of them describes a
   control that no longer exists, an option the combo never offers, or a value
   the widget cannot hold. These checks are pure AST + XML, so unlike the rest
   of this file they cover the BLENDER fork too, with no DCC present.
"""

import ast
import re
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from _host import MAYA_AVAILABLE as _MAYA_AVAILABLE, maya_module

cmds = maya_module("maya.cmds")
animation_module = maya_module("tentacle.slots.maya.animation")

ROOT = Path(__file__).resolve().parent.parent
PKG = ROOT / "tentacle"
SLOT_MODULES = {
    "maya": PKG / "slots" / "maya" / "animation.py",
    "blender": PKG / "slots" / "blender" / "animation.py",
}
#: Text both forks say identically, hoisted out of them (see its docstring).
MIXIN_MODULE = PKG / "slots" / "_animation.py"
UI_FILES = {
    "panel": PKG / "ui" / "animation.ui",
    "submenu": PKG / "ui" / "animation#submenu.ui",
}

#: An option-box control's objectName: ``chk021`` / ``cmb_align`` / ``d001``.
_WIDGET_NAME = re.compile(r"^(?:chk|cmb|s|d|lbl|spn|list|tb|b)(?:\d{3}|_[a-z0-9_]+)$")
#: A panel action widget in a .ui: ``tb000`` / ``b005`` / ``list000``.
_PANEL_WIDGET = re.compile(r"^(?:tb|b|list)\d{3}$")
#: Widgets whose tooltip belongs in the .ui. ``list###`` is excluded: an
#: ExpandableList's text lives on its rows, built in ``list000_init`` from
#: ``_TOOLS_ITEMS`` — covered by ``test_tools_list_rows_are_documented...``.
_UI_BUTTON = re.compile(r"^(?:tb|b)\d{3}$")

#: Vocabulary that belongs to ONE host. The .ui is loaded by both forks, so a
#: tooltip there naming any of these describes a control the other DCC does not
#: have. Such text belongs in that fork's option box, or in a
#: ``widget.setToolTip`` override inside its ``_init`` (see tb004 / tb017).
_HOST_SPECIFIC_TERMS = (
    "channel box",
    "dope sheet",
    "fcurve",
    "attribute editor",
    "maya",
    "blender",
)


def _parse(path):
    return ast.parse(path.read_text(encoding="utf-8"))


def _functions(tree):
    return {n.name: n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}


def _init_pairs(path):
    """Yield ``(base, init_fn, slot_fn_or_None)`` for each ``tb###_init``."""
    funcs = _functions(_parse(path))
    for name, fn in funcs.items():
        if name.endswith("_init"):
            base = name[: -len("_init")]
            yield base, fn, funcs.get(base)


def _object_name(call):
    """The ``setObjectName=`` literal on a ``menu.add()`` call, if any."""
    for kw in call.keywords:
        if kw.arg == "setObjectName" and isinstance(kw.value, ast.Constant):
            return kw.value.value
    return None


def _add_calls(fn):
    """Every ``menu.add(...)`` Call inside *fn*."""
    return [
        n
        for n in ast.walk(fn)
        if isinstance(n, ast.Call)
        and isinstance(n.func, ast.Attribute)
        and n.func.attr == "add"
    ]


def _added_widgets(fn):
    """``{objectName: has_tooltip}`` for every ``menu.add()`` inside *fn*."""
    found = {}
    for call in _add_calls(fn):
        name = _object_name(call)
        if name:
            found[name] = any(kw.arg == "setToolTip" for kw in call.keywords)
    return found


def _widget_refs(fn):
    """Every option-box objectName read as an attribute inside *fn*."""
    if fn is None:
        return set()
    return {
        n.attr
        for n in ast.walk(fn)
        if isinstance(n, ast.Attribute) and _WIDGET_NAME.match(n.attr or "")
    }


def _enable_when_names(fn):
    """``[(targets, triggers)]`` objectNames from each ``sb.enable_when()``."""

    def _names(arg):
        if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
            return [p.strip() for p in arg.value.split(",")]
        if isinstance(arg, (ast.List, ast.Tuple)):
            return [
                e.value
                for e in arg.elts
                if isinstance(e, ast.Constant) and isinstance(e.value, str)
            ]
        return []

    return [
        (_names(n.args[1]), _names(n.args[2]))
        for n in ast.walk(fn)
        if isinstance(n, ast.Call)
        and isinstance(n.func, ast.Attribute)
        and n.func.attr == "enable_when"
        and len(n.args) >= 3
    ]


def _find_add(fn, object_name):
    """The ``menu.add()`` Call that created *object_name*, plus its variable.

    Returns ``(call, var_name_or_None)``; the variable is how later
    ``addItem`` calls refer to the widget.
    """
    for node in ast.walk(fn):
        call = var = None
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
            call = node.value
            target = node.targets[0]
            var = target.id if isinstance(target, ast.Name) else None
        elif isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
            call = node.value
        if (
            call is not None
            and isinstance(call.func, ast.Attribute)
            and call.func.attr == "add"
            and _object_name(call) == object_name
        ):
            return call, var
    return None, None


def _local_assign(fn, name):
    """The value node last assigned to local *name* inside *fn*."""
    found = None
    for node in ast.walk(fn):
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == name for t in node.targets
        ):
            found = node.value
    return found


def _class_dict(tree, attr):
    """The ``ast.Dict`` assigned to class attribute *attr* anywhere in *tree*."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == attr for t in node.targets
        ):
            if isinstance(node.value, ast.Dict):
                return node.value
    return None


def _resolve_pairs(fn, tree, node):
    """``[(label, data)]`` from whatever a combo-populating loop iterates.

    Three shapes appear across the two forks: a literal list of pairs, a local
    name bound to one (``snap_items``, ``items``), and ``self._MAP.items()``
    over a class-level dict (Blender's ``_COPY_MODES``).
    """
    if isinstance(node, ast.Name):
        node = _local_assign(fn, node.id)
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
        if node.func.attr == "items" and isinstance(node.func.value, ast.Attribute):
            mapping = _class_dict(tree, node.func.value.attr)
            if mapping is not None:
                return [
                    (k.value, v.value)
                    for k, v in zip(mapping.keys, mapping.values)
                    if isinstance(k, ast.Constant) and isinstance(v, ast.Constant)
                ]
        return []
    if not isinstance(node, ast.List):
        return []
    pairs = []
    for elt in node.elts:
        if isinstance(elt, ast.Constant):  # a bare addItems([...]) label list
            pairs.append((elt.value, None))
        elif isinstance(elt, ast.Tuple) and elt.elts:
            label = elt.elts[0]
            data = elt.elts[1] if len(elt.elts) > 1 else None
            pairs.append(
                (
                    label.value if isinstance(label, ast.Constant) else None,
                    data.value if isinstance(data, ast.Constant) else None,
                )
            )
    return pairs


def _combo_pairs(fn, tree, object_name):
    """``[(label, data)]`` for every item the combo *object_name* offers."""
    call, var = _find_add(fn, object_name)
    if call is None:
        return []
    pairs = []
    for kw in call.keywords:
        if kw.arg == "addItems":
            pairs += _resolve_pairs(fn, tree, kw.value)
    if var is None:
        return pairs

    def _targets_var(node, attr):
        return (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == attr
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == var
        )

    for node in ast.walk(fn):
        if _targets_var(node, "addItems") and node.args:
            pairs += _resolve_pairs(fn, tree, node.args[0])
        elif isinstance(node, ast.For) and any(
            _targets_var(c, "addItem") for c in ast.walk(node)
        ):
            pairs += _resolve_pairs(fn, tree, node.iter)
    return pairs


def _combo_labels(fn, tree, object_name):
    return [lab for lab, _data in _combo_pairs(fn, tree, object_name) if lab]


def _combo_item_data(fn, tree, object_name):
    return [data for _lab, data in _combo_pairs(fn, tree, object_name) if data]


def _mixin_constant(name):
    """Source of ``AnimationMixin.<name>``, or "" when there is no such name.

    The value is a ``fmt`` keyword spec (or, for the one-liners, a plain
    string); either way its unparsed source carries the text the option-check
    below searches.
    """
    for node in ast.walk(_parse(MIXIN_MODULE)):
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == name for t in node.targets
        ):
            return ast.unparse(node.value)
    return ""


def _tooltip_src(fn, object_name):
    """Source text of the ``setToolTip=`` expression for *object_name*.

    Follows the two indirections a tooltip can take before it reaches the
    control — a local built earlier in the same ``_init``, and a
    ``self.TIP_*`` constant on ``AnimationMixin`` — so the "does the tooltip
    name every option?" check reads the TEXT rather than a variable name.
    """
    call, _var = _find_add(fn, object_name)
    if call is None:
        return ""
    for kw in call.keywords:
        if kw.arg != "setToolTip":
            continue
        value = kw.value
        if isinstance(value, ast.Name):
            value = _local_assign(fn, value.id) or value
        for shared in _shared_spec_names(value):
            return _mixin_constant(shared) or ast.unparse(value)
        return ast.unparse(value)
    return ""


def _shared_spec_names(node):
    """``TIP_*`` names *node* pulls from the mixin, in either shape.

    A shared entry reaches a control as ``self.sb.tooltip.fmt(**self.TIP_X)``
    (a spec) or as ``self.TIP_X`` (the three one-line strings).
    """
    return [
        n.attr
        for n in ast.walk(node)
        if isinstance(n, ast.Attribute)
        and isinstance(n.value, ast.Name)
        and n.value.id == "self"
        and n.attr.startswith("TIP_")
    ]


def _add_kwarg(fn, object_name, kwarg):
    """Literal ``kwarg`` on the ``menu.add()`` that made *object_name*.

    ``"__type__"`` reads the first positional argument instead — the widget
    class name (``"QSpinBox"``, ``"QDoubleSpinBox"``, …).
    """
    call, _var = _find_add(fn, object_name)
    if call is None:
        return None
    if kwarg == "__type__":
        first = call.args[0] if call.args else None
        return first.value if isinstance(first, ast.Constant) else None
    for kw in call.keywords:
        if kw.arg == kwarg and isinstance(kw.value, ast.Constant):
            return kw.value.value
    return None


def _ui_tooltips(path):
    """``{objectName: tooltip}`` for every widget in a .ui carrying one."""
    root = ET.parse(path).getroot()
    out = {}
    for widget in root.iter("widget"):
        for prop in widget.findall("property"):
            if prop.get("name") != "toolTip":
                continue
            string = prop.find("string")
            out[widget.get("name")] = (string.text or "") if string is not None else ""
    return out


def _ui_buttons(path):
    """objectNames of the panel's action widgets (tb###/b###/list###)."""
    root = ET.parse(path).getroot()
    return {
        w.get("name")
        for w in root.iter("widget")
        if _UI_BUTTON.match(w.get("name") or "")
    }


def _tools_items(path):
    """``[(label, objectName, tooltip)]`` from the module's ``_TOOLS_ITEMS``."""
    roster = None
    for node in ast.walk(_parse(path)):
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == "_TOOLS_ITEMS" for t in node.targets
        ):
            roster = node.value
    if roster is None:
        return None
    rows = []
    for entries in roster.values:
        for entry in entries.elts:
            # (label, objectName, tooltip) — list000 unpacks the first two, so
            # a shorter row is a malformed roster, not a missing tooltip.
            parts = [
                e.value if isinstance(e, ast.Constant) else None for e in entry.elts
            ]
            parts += [None] * (3 - len(parts))
            rows.append((parts[0], parts[1], parts[2] or ""))
    return rows


class TestAnimationOptionBoxTooltips(unittest.TestCase):
    """Every option-box control is documented, and every name resolves."""

    def test_every_option_box_control_has_a_tooltip(self):
        undocumented = []
        for dcc, path in SLOT_MODULES.items():
            for base, init, _slot in _init_pairs(path):
                undocumented += [
                    f"{dcc}.{base}.{obj}"
                    for obj, has_tip in _added_widgets(init).items()
                    if not has_tip
                ]
        self.assertEqual(
            sorted(undocumented),
            [],
            "option-box control(s) with no setToolTip — a live dial the user "
            f"is given no explanation for: {sorted(undocumented)}",
        )

    def test_slot_reads_only_controls_its_init_creates(self):
        """A renamed control reads back as None and the slot misfires silently."""
        missing = []
        for dcc, path in SLOT_MODULES.items():
            for base, init, slot in _init_pairs(path):
                made = set(_added_widgets(init))
                missing += [
                    f"{dcc}.{base} reads .{ref}, which no add() creates"
                    for ref in _widget_refs(slot)
                    if ref not in made and not _PANEL_WIDGET.match(ref)
                ]
        self.assertEqual(sorted(missing), [], f"dangling reads: {sorted(missing)}")

    def test_no_orphaned_controls(self):
        """A control nothing reads is a promise the tool never keeps.

        Driving an ``enable_when`` counts as being read; being its TARGET does
        not — a dial that only greys other things out still does nothing.
        """
        orphans = []
        for dcc, path in SLOT_MODULES.items():
            for base, init, slot in _init_pairs(path):
                used = _widget_refs(init) | _widget_refs(slot)
                for _targets, triggers in _enable_when_names(init):
                    used.update(triggers)
                orphans += [
                    f"{dcc}.{base}.{obj}"
                    for obj in _added_widgets(init)
                    if obj not in used
                ]
        self.assertEqual(
            sorted(orphans), [], f"created but never read: {sorted(orphans)}"
        )

    def test_enable_when_rules_name_real_controls(self):
        """A typo'd name greys out nothing — the control stays live and ignored."""
        bad = []
        for dcc, path in SLOT_MODULES.items():
            for base, init, _slot in _init_pairs(path):
                made = set(_added_widgets(init))
                for targets, triggers in _enable_when_names(init):
                    bad += [
                        f"{dcc}.{base}: {n}"
                        for n in targets + triggers
                        if n and "-" not in n and n not in made
                    ]
        self.assertEqual(sorted(bad), [], f"enable_when naming unknowns: {sorted(bad)}")


class TestAnimationPanelTooltips(unittest.TestCase):
    """The shared .ui carries a tooltip for every button, true in both hosts."""

    def test_every_panel_button_has_a_tooltip(self):
        for kind, path in UI_FILES.items():
            with self.subTest(ui=kind):
                tips = _ui_tooltips(path)
                blank = sorted(
                    name
                    for name in _ui_buttons(path)
                    if not (tips.get(name) or "").strip()
                )
                self.assertEqual(blank, [], f"{path.name}: untooltipped: {blank}")

    def test_shared_ui_tooltips_stay_dcc_neutral(self):
        """Both forks load this .ui, so a host-only claim is false in the other.

        Regression: tb010 advertised a Channel Box scope only the Maya fork
        offers, and tb019 described Maya's "equal to the attribute default"
        rule for a pass Blender applies to any constant curve.
        """
        offenders = []
        for _kind, path in UI_FILES.items():
            for name, tip in _ui_tooltips(path).items():
                lowered = (tip or "").lower()
                offenders += [
                    f"{path.name}:{name} says {term!r}"
                    for term in _HOST_SPECIFIC_TERMS
                    if term in lowered
                ]
        self.assertEqual(
            sorted(offenders), [], f"host-specific text: {sorted(offenders)}"
        )

    def test_tools_list_rows_are_documented_and_dispatchable(self):
        """Every ``_TOOLS_ITEMS`` row needs a tooltip and a slot to dispatch to."""
        for dcc, path in SLOT_MODULES.items():
            with self.subTest(dcc=dcc):
                rows = _tools_items(path)
                self.assertIsNotNone(rows, f"{dcc}: _TOOLS_ITEMS not found")
                slots = set(_functions(_parse(path)))
                problems = [
                    f"{label}: {'no tooltip' if not tip.strip() else 'no slot ' + str(obj)}"
                    for label, obj, tip in rows
                    if not tip.strip() or obj not in slots
                ]
                self.assertEqual(problems, [], f"{dcc} Tools list: {problems}")


class TestAnimationSharedText(unittest.TestCase):
    """One command, one description — wherever that description is written."""

    def test_both_forks_mix_in_the_shared_tooltip_table(self):
        """A fork that stops inheriting it silently forks the text again.

        ``AnimationMixin`` exists because 30 tooltips were maintained in two
        copies and had already drifted (the Scale Keys speed text said "one
        shared pace" in one fork and "one pace" in the other).
        """
        for dcc, path in SLOT_MODULES.items():
            with self.subTest(dcc=dcc):
                bases = [
                    b.id
                    for node in ast.walk(_parse(path))
                    if isinstance(node, ast.ClassDef) and node.name == "Animation"
                    for b in node.bases
                    if isinstance(b, ast.Name)
                ]
                self.assertIn(
                    "AnimationMixin",
                    bases,
                    f"{dcc} Animation no longer mixes in the shared tooltip "
                    f"table (bases: {bases})",
                )

    def test_every_shared_tooltip_is_used_by_both_forks(self):
        """An unreferenced constant is text that has quietly gone stale."""
        defined = {
            t.id
            for node in ast.walk(_parse(MIXIN_MODULE))
            if isinstance(node, ast.Assign)
            for t in node.targets
            if isinstance(t, ast.Name) and t.id.startswith("TIP_")
        }
        self.assertTrue(defined, "the shared tooltip table is empty")
        for dcc, path in SLOT_MODULES.items():
            with self.subTest(dcc=dcc):
                used = {
                    n.attr
                    for n in ast.walk(_parse(path))
                    if isinstance(n, ast.Attribute) and n.attr.startswith("TIP_")
                }
                self.assertEqual(
                    sorted(defined - used),
                    [],
                    f"{dcc} never uses these shared tooltips: {sorted(defined - used)}",
                )
                self.assertEqual(
                    sorted(used - defined),
                    [],
                    f"{dcc} references tooltips the mixin does not define: "
                    f"{sorted(used - defined)}",
                )

    def test_panel_and_submenu_agree_on_a_shared_button(self):
        """The two surfaces show the SAME button; two texts means one is stale.

        Regression: Fit Playback Range carried one description on the submenu
        button and a different one in the Tools list.
        """
        panel = _ui_tooltips(UI_FILES["panel"])
        submenu = _ui_tooltips(UI_FILES["submenu"])
        mismatched = sorted(
            name
            for name in set(panel) & set(submenu)
            if (panel[name] or "").strip() != (submenu[name] or "").strip()
        )
        self.assertEqual(
            mismatched,
            [],
            f"same button, different tooltip on panel vs submenu: {mismatched}",
        )


class TestAnimationClaimRegressions(unittest.TestCase):
    """Claims an option box made that its controls could not actually keep."""

    def test_go_to_frame_offers_the_snap_modes_invert_can_flip(self):
        """``invert_snap`` only ever swaps floor <-> ceil.

        The Snap combo used to offer none/preferred/aggressive alone, so the
        Invert checkbox fed a parameter with nothing to act on.
        """
        for dcc, path in SLOT_MODULES.items():
            with self.subTest(dcc=dcc):
                tree = _parse(path)
                init = _functions(tree)["tb000_init"]
                data = _combo_item_data(init, tree, "cmb001")
                for mode in ("floor", "ceil"):
                    self.assertIn(
                        mode,
                        data,
                        f"{dcc} tb000: Invert advertises swapping the snap "
                        f"direction, but the combo offers no {mode!r} to swap",
                    )

    def test_stagger_spacing_can_express_a_duration_fraction(self):
        """mtk reads |spacing| < 1 as a fraction of each block's duration.

        An integer spinbox made that documented mode unreachable.
        """
        init = _functions(_parse(SLOT_MODULES["maya"]))["tb003_init"]
        self.assertEqual(
            _add_kwarg(init, "s004", "__type__"),
            "QDoubleSpinBox",
            "tb003 Spacing documents a fractional percent-of-duration mode, so "
            "the control has to be able to hold a fraction",
        )

    def test_scale_factor_can_express_an_absolute_duration(self):
        """Absolute uniform mode reads Factor as a target duration in FRAMES.

        The old 100.0 ceiling capped that at a 100-frame block.
        """
        for dcc, path in SLOT_MODULES.items():
            with self.subTest(dcc=dcc):
                init = _functions(_parse(path))["tb014_init"]
                ceiling = _add_kwarg(init, "d001", "setMaximum")
                self.assertIsNotNone(ceiling, f"{dcc} tb014: d001 has no setMaximum")
                self.assertGreater(
                    ceiling,
                    100.0,
                    f"{dcc} tb014: Factor is documented as an absolute frame "
                    f"count but cannot exceed {ceiling}",
                )

    def test_combo_tooltips_name_every_option_the_combo_offers(self):
        """A tooltip that enumerates options has to enumerate all of them.

        Regressions: tb014's grouping tooltip named a "Group All Objects" the
        combo never had, and tb012's list omitted the Copy + Paste mode.
        """
        checks = [
            ("maya", "tb000_init", "cmb001"),
            ("maya", "tb010_init", "cmb004"),
            ("maya", "tb012_init", "cmb038"),
            ("maya", "tb014_init", "cmb033"),
            ("maya", "tb014_init", "cmb034"),
            ("blender", "tb000_init", "cmb001"),
            ("blender", "tb010_init", "cmb004"),
            ("blender", "tb012_init", "cmb038"),
            ("blender", "tb014_init", "cmb033"),
        ]
        for dcc, init_name, combo in checks:
            with self.subTest(dcc=dcc, combo=combo):
                tree = _parse(SLOT_MODULES[dcc])
                init = _functions(tree)[init_name]
                tip = _tooltip_src(init, combo)
                labels = _combo_labels(init, tree, combo)
                self.assertTrue(labels, f"{dcc}.{combo}: parsed no combo items")
                # Items are labelled "<Group>: <Option>"; the tooltip names the
                # option, the group being the tooltip's own title.
                missing = [
                    lab
                    for lab in labels
                    if lab.split(": ")[-1].replace("&", "&amp;") not in tip
                ]
                self.assertEqual(
                    missing,
                    [],
                    f"{dcc}.{init_name}.{combo} tooltip never mentions {missing}",
                )


class _FakeCombo:
    def __init__(self, value):
        self._v = value

    def currentData(self):
        return self._v


class _FakeMenu:
    def __init__(self, cmb037_value, cmb040_value):
        self.cmb037 = _FakeCombo(cmb037_value)
        self.cmb040 = _FakeCombo(cmb040_value)


class _FakeOptionBox:
    def __init__(self, cmb037_value, cmb040_value):
        self.menu = _FakeMenu(cmb037_value, cmb040_value)


class _FakeWidget:
    def __init__(self, cmb037_value, cmb040_value):
        self.option_box = _FakeOptionBox(cmb037_value, cmb040_value)


class _RecordedSb:
    def __init__(self):
        self.messages = []

    def message_box(self, *args, **kwargs):
        self.messages.append((args, kwargs))


@unittest.skipUnless(_MAYA_AVAILABLE, "Requires tentacle import path")
class TestAnimationModuleImport(unittest.TestCase):
    """Catch import-time breakage. Module-top imports a long mayatk list."""

    def test_module_imports_cleanly(self):
        self.assertIsNotNone(animation_module)
        self.assertTrue(hasattr(animation_module, "Animation"))


@unittest.skipUnless(_MAYA_AVAILABLE, "Requires tentacle import path")
class TestAnimationSlotRoster(unittest.TestCase):
    """Pin the public slot roster — accidental removal of any tb###/b###
    silently breaks the corresponding toolbar button at runtime, with no
    error until the user clicks it. Test catches it at build time.
    """

    EXPECTED_TB_SLOTS = [f"tb{i:03d}" for i in range(0, 20)]
    EXPECTED_B_SLOTS = ["b000", "b004", "b005"]

    def test_all_tb_slots_present(self):
        cls = animation_module.Animation
        missing = [name for name in self.EXPECTED_TB_SLOTS if not hasattr(cls, name)]
        self.assertEqual(missing, [], f"Animation is missing tb slots: {missing}")

    def test_all_tb_slot_inits_present(self):
        cls = animation_module.Animation
        missing = [
            f"{name}_init"
            for name in self.EXPECTED_TB_SLOTS
            if not hasattr(cls, f"{name}_init")
        ]
        self.assertEqual(missing, [], f"Animation is missing init handlers: {missing}")

    def test_all_b_slots_present(self):
        cls = animation_module.Animation
        missing = [name for name in self.EXPECTED_B_SLOTS if not hasattr(cls, name)]
        self.assertEqual(missing, [], f"Animation is missing b slots: {missing}")

    def test_tools_list_present(self):
        """The panel's entry surface is the Tools list, not a header menu.

        ``header_init`` was retired when the loose header entries moved into a
        single expandable body row: ``list000_init`` builds it from
        ``_TOOLS_ITEMS`` and ``list000`` dispatches its leaves. Pinning both
        (plus a non-empty roster) catches an accidental removal the same way
        the old header assertion did.
        """
        cls = animation_module.Animation
        self.assertTrue(hasattr(cls, "list000_init"))
        self.assertTrue(hasattr(cls, "list000"))
        self.assertTrue(cls._TOOLS_ITEMS, "the Tools list roster must not be empty")


@unittest.skipUnless(_MAYA_AVAILABLE, "Requires maya.cmds")
class TestTb017StepKeysModeTranslation(unittest.TestCase):
    """tb017 translates the cmb037 'mode' string to step_keys' `keys` arg.

    The mapping is:
        "auto"          -> "auto"
        "current_time"  -> current frame number
        "selected"      -> list of selected key names (bails if empty)
        "all"           -> None  (default to all)

    Regression: a broken branch here causes step_keys to bake the wrong
    set of frames. The mtk-side logic is tested separately; here we pin
    the translation surface.
    """

    def setUp(self):
        cmds.file(new=True, force=True)
        # Bypass __init__; just need the method bound.
        self.instance = animation_module.Animation.__new__(animation_module.Animation)
        self.instance.sb = _RecordedSb()

        # Patch out the mtk call so we can capture its `keys` argument.
        import mayatk as mtk

        self._original_step_keys = mtk.AnimUtils.step_keys
        self.recorded_keys = []

        def fake_step_keys(keys=None, tangent="out"):
            self.recorded_keys.append(keys)
            return {"curves": 1, "keys": 1}

        mtk.AnimUtils.step_keys = staticmethod(fake_step_keys)

    def tearDown(self):
        import mayatk as mtk

        mtk.AnimUtils.step_keys = self._original_step_keys
        cmds.file(new=True, force=True)

    def test_mode_auto_passes_auto_string(self):
        widget = _FakeWidget(cmb037_value="auto", cmb040_value="out")
        self.instance.tb017(widget)
        self.assertEqual(self.recorded_keys, ["auto"])

    def test_mode_all_passes_none(self):
        widget = _FakeWidget(cmb037_value="all", cmb040_value="out")
        self.instance.tb017(widget)
        self.assertEqual(self.recorded_keys, [None])

    def test_mode_current_time_passes_current_frame(self):
        cmds.currentTime(42)
        widget = _FakeWidget(cmb037_value="current_time", cmb040_value="out")
        self.instance.tb017(widget)
        self.assertEqual(self.recorded_keys, [42.0])

    def test_mode_selected_with_no_selection_bails_with_message(self):
        """No keys selected in Graph Editor — must NOT call step_keys."""
        widget = _FakeWidget(cmb037_value="selected", cmb040_value="out")
        self.instance.tb017(widget)
        self.assertEqual(self.recorded_keys, [])  # never called
        self.assertTrue(self.instance.sb.messages, "User must be told why nothing ran")


if __name__ == "__main__":
    unittest.main()
