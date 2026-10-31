#!/usr/bin/python
# coding=utf-8
"""Regression tests for tentacle.slots.animation, the one Animation Slots class.

It reaches its host only through ``self.tk``. The key logic (curve scaling,
stepping, snapping, transfer, the shot claims) lives in mayatk and blendertk
and is tested there (mayatk ``test_anim_utils.py`` / ``test_scale_keys.py`` /
``test_stagger_keys.py``; blendertk ``test_anim_*.py``). What is pinned here:

1. Tooltip and option-box claims, by AST + XML over the module and the shared
   ``.ui``: every control documented, every name read exists, every combo
   tooltip names every option, host-only options tagged ``requires``.
2. What each slot asks of the toolkit, over a fake toolkit (plain Python): the
   option-box translations (-1 sentinels, combo data, scopes) and the reports.
3. In a fresh Maya, the same class over the real ``mtk``: tb021's repair scope,
   and the shot claims every key edit carries (the Blender twin of those is
   ``test/blender/deepened_slots_check.py``).
"""

import ast
import contextlib
import re
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from _host import MAYA_AVAILABLE as _MAYA_AVAILABLE, maya_module
from tentacle.slots._slots import Slots
from tentacle.slots.animation import AnimationSlots

cmds = maya_module("maya.cmds")

ROOT = Path(__file__).resolve().parent.parent
PKG = ROOT / "tentacle"
SLOT_MODULE = PKG / "slots" / "animation.py"
UI_FILES = {
    "panel": PKG / "ui" / "animation.ui",
    "submenu": PKG / "ui" / "animation#submenu.ui",
}

#: An option-box control's objectName: ``chk021`` / ``cmb_align`` / ``d001``.
_WIDGET_NAME = re.compile(r"^(?:chk|cmb|s|d|lbl|spn|list|tb|b)(?:\d{3}|_[a-z0-9_]+)$")
#: A panel action widget in a .ui: ``tb000`` / ``b005`` / ``list000``.
_PANEL_WIDGET = re.compile(r"^(?:tb|b|list)\d{3}$")
#: Widgets whose tooltip belongs in the .ui (a list's text lives on its rows).
_UI_BUTTON = re.compile(r"^(?:tb|b)\d{3}$")

#: Vocabulary that belongs to ONE host. Both hosts load the .ui, so a tooltip
#: there naming any of these describes a control the other does not have.
_HOST_SPECIFIC_TERMS = (
    "channel box",
    "dope sheet",
    "fcurve",
    "attribute editor",
    "maya",
    "blender",
)

#: Options only Maya serves: each is tagged ``requires="maya"`` (hidden in
#: Blender, CODE_STANDARD section 15) rather than offered as a stub there.
_MAYA_ONLY = {
    "tb003_init": "chk024",  # Channel Box Attrs Only
    "tb004_init": "chk007",  # Tangents: a Blender action copy carries its handles
    "tb006_init": "chk033",  # Channel Box Only
    "tb010_init": "chk020",  # Channel Box Only
    "tb013_init": "chk034",  # Channel Box Only
    "tb014_init": "chk_channel_box",  # Channel Box Attrs Only
    "tb016_init": "cmb_traversal",  # dependency-graph traversal
    "tb017_init": "cmb040",  # tangent side: Blender's is the segment leaving a key
}


def _parse(path=SLOT_MODULE):
    return ast.parse(path.read_text(encoding="utf-8"))


def _functions(tree):
    return {n.name: n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}


def _init_pairs():
    """Yield ``(base, init_fn, slot_fn_or_None)`` for each ``*_init``."""
    funcs = _functions(_parse())
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


def _is_add(node):
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "add"
    )


def _added_widgets(fn):
    """``{objectName: has_tooltip}`` for every ``menu.add()`` inside *fn*."""
    found = {}
    for call in (n for n in ast.walk(fn) if _is_add(n)):
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
    """The ``menu.add()`` Call that created *object_name*, plus the variable
    it was bound to -- directly or through a wrapper (``self.requires(...)``).

    Returns ``(call, var_name_or_None)``.
    """
    for node in ast.walk(fn):
        if isinstance(node, (ast.Assign, ast.Expr)):
            for call in (n for n in ast.walk(node.value) if _is_add(n)):
                if _object_name(call) == object_name:
                    var = None
                    if isinstance(node, ast.Assign) and isinstance(
                        node.targets[0], ast.Name
                    ):
                        var = node.targets[0].id
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


def _class_attr(tree, attr):
    """The value node assigned to class attribute *attr*."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == attr for t in node.targets
        ):
            return node.value
    return None


def _resolve_pairs(fn, tree, node):
    """``[(label, data)]`` from whatever a combo-populating loop iterates."""
    if isinstance(node, ast.Name):
        node = _local_assign(fn, node.id)
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
        if node.func.attr == "items" and isinstance(node.func.value, ast.Attribute):
            mapping = _class_attr(tree, node.func.value.attr)
            if isinstance(mapping, ast.Dict):
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
    if call is None or var is None:
        return []

    def _targets_var(node, attr):
        return (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == attr
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == var
        )

    pairs = []
    for node in ast.walk(fn):
        if _targets_var(node, "addItems") and node.args:
            pairs += _resolve_pairs(fn, tree, node.args[0])
        elif isinstance(node, ast.For) and any(
            _targets_var(c, "addItem") for c in ast.walk(node)
        ):
            pairs += _resolve_pairs(fn, tree, node.iter)
    return pairs


def _tooltip_src(fn, tree, object_name):
    """Source text of the ``setToolTip=`` expression for *object_name*,
    following a local built earlier and a ``self.TIP_*`` class constant."""
    call, _var = _find_add(fn, object_name)
    if call is None:
        return ""
    for kw in call.keywords:
        if kw.arg != "setToolTip":
            continue
        value = kw.value
        if isinstance(value, ast.Name):
            value = _local_assign(fn, value.id) or value
        for node in ast.walk(value):
            if (
                isinstance(node, ast.Attribute)
                and isinstance(node.value, ast.Name)
                and node.value.id == "self"
                and node.attr.startswith("TIP_")
            ):
                shared = _class_attr(tree, node.attr)
                if shared is not None:
                    return ast.unparse(shared)
        return ast.unparse(value)
    return ""


def _add_kwarg(fn, object_name, kwarg):
    """Literal ``kwarg`` on the ``menu.add()`` that made *object_name*;
    ``"__type__"`` reads the widget class name (the first positional)."""
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
    out = {}
    for widget in ET.parse(path).getroot().iter("widget"):
        for prop in widget.findall("property"):
            if prop.get("name") == "toolTip":
                string = prop.find("string")
                out[widget.get("name")] = (
                    (string.text or "") if string is not None else ""
                )
    return out


def _ui_buttons(path):
    """objectNames of the panel's action widgets (tb###/b###)."""
    return {
        w.get("name")
        for w in ET.parse(path).getroot().iter("widget")
        if _UI_BUTTON.match(w.get("name") or "")
    }


# ====================================================================== static claims
class TestAnimationOptionBoxTooltips(unittest.TestCase):
    """Every option-box control is documented, and every name resolves."""

    def test_every_option_box_control_has_a_tooltip(self):
        undocumented = [
            f"{base}.{obj}"
            for base, init, _slot in _init_pairs()
            for obj, has_tip in _added_widgets(init).items()
            if not has_tip
        ]
        self.assertEqual(sorted(undocumented), [], f"no setToolTip: {undocumented}")

    def test_slot_reads_only_controls_its_init_creates(self):
        """A renamed control reads back as None and the slot misfires silently."""
        missing = [
            f"{base} reads .{ref}, which no add() creates"
            for base, init, slot in _init_pairs()
            for ref in _widget_refs(slot)
            if ref not in _added_widgets(init) and not _PANEL_WIDGET.match(ref)
        ]
        self.assertEqual(sorted(missing), [], f"dangling reads: {missing}")

    def test_no_orphaned_controls(self):
        """A control nothing reads is a promise the tool never keeps (driving an
        ``enable_when`` counts as being read; being its target does not)."""
        orphans = []
        for base, init, slot in _init_pairs():
            used = _widget_refs(init) | _widget_refs(slot)
            for _targets, triggers in _enable_when_names(init):
                used.update(triggers)
            orphans += [
                f"{base}.{obj}" for obj in _added_widgets(init) if obj not in used
            ]
        self.assertEqual(sorted(orphans), [], f"created but never read: {orphans}")

    def test_enable_when_rules_name_real_controls(self):
        bad = []
        for base, init, _slot in _init_pairs():
            made = set(_added_widgets(init))
            for targets, triggers in _enable_when_names(init):
                bad += [
                    f"{base}: {n}" for n in targets + triggers if n and n not in made
                ]
        self.assertEqual(sorted(bad), [], f"enable_when naming unknowns: {bad}")

    def test_maya_only_options_are_tagged_requires_maya(self):
        """A Maya-only option is hidden in Blender, never a dead control there."""
        funcs = _functions(_parse())

        def builds(arg, func, obj):
            """Whether *arg* is (or names a local bound to) the add() of *obj*."""
            if isinstance(arg, ast.Name):
                arg = next(
                    (
                        n.value
                        for n in ast.walk(func)
                        if isinstance(n, ast.Assign)
                        and any(
                            isinstance(t, ast.Name) and t.id == arg.id
                            for t in n.targets
                        )
                    ),
                    arg,
                )
            return any(_is_add(c) and _object_name(c) == obj for c in ast.walk(arg))

        for init_name, obj in _MAYA_ONLY.items():
            with self.subTest(option=obj):
                func = funcs[init_name]
                tagged = any(
                    isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                    and node.func.attr == "requires"  # Slots.requires
                    and len(node.args) == 2
                    and builds(node.args[0], func, obj)
                    and isinstance(node.args[1], ast.Constant)
                    and node.args[1].value == "maya"
                    for node in ast.walk(func)
                )
                self.assertTrue(tagged, f"{init_name}.{obj} is not requires='maya'")


class TestAnimationPanelTooltips(unittest.TestCase):
    """The shared .ui carries a tooltip for every button, true in both hosts."""

    def test_every_panel_button_has_a_tooltip(self):
        for kind, path in UI_FILES.items():
            with self.subTest(ui=kind):
                tips = _ui_tooltips(path)
                blank = sorted(
                    n for n in _ui_buttons(path) if not (tips.get(n) or "").strip()
                )
                self.assertEqual(blank, [], f"{path.name}: untooltipped: {blank}")

    def test_shared_ui_tooltips_stay_dcc_neutral(self):
        offenders = [
            f"{path.name}:{name} says {term!r}"
            for path in UI_FILES.values()
            for name, tip in _ui_tooltips(path).items()
            for term in _HOST_SPECIFIC_TERMS
            if term in (tip or "").lower()
        ]
        self.assertEqual(sorted(offenders), [], f"host-specific text: {offenders}")

    def test_panel_and_submenu_agree_on_a_shared_button(self):
        panel = _ui_tooltips(UI_FILES["panel"])
        submenu = _ui_tooltips(UI_FILES["submenu"])
        mismatched = sorted(
            n
            for n in set(panel) & set(submenu)
            if (panel[n] or "").strip() != (submenu[n] or "").strip()
        )
        self.assertEqual(mismatched, [], f"same button, two tooltips: {mismatched}")

    def test_tools_list_rows_are_documented_and_dispatchable(self):
        """Every Tools row needs a tooltip, a slot, and a known host tag."""
        problems = [
            f"{label}: {problem}"
            for rows in AnimationSlots._TOOLS_ITEMS.values()
            for label, slot, tip, requires in rows
            for problem in (
                "no tooltip" if not tip.strip() else None,
                f"no slot {slot}"
                if not callable(getattr(AnimationSlots, slot, None))
                else None,
                f"unknown host {requires!r}"
                if requires not in (None, "maya", "blender")
                else None,
            )
            if problem
        ]
        self.assertEqual(problems, [], f"Tools list: {problems}")

    def test_repair_visibility_tangents_is_maya_only(self):
        rows = {
            slot: requires
            for _l, slot, _t, requires in AnimationSlots._TOOLS_ITEMS["Repair"]
        }
        self.assertEqual(rows.get("b001"), "maya")


class TestComposition(unittest.TestCase):
    """One class for both hosts: no forks, no host imports, no host branches."""

    def test_the_forks_and_the_mixin_are_gone(self):
        for rel in ("_animation.py", "maya/animation.py", "blender/animation.py"):
            with self.subTest(module=rel):
                self.assertFalse((PKG / "slots" / rel).exists())

    def test_the_module_imports_no_host(self):
        source = SLOT_MODULE.read_text(encoding="utf-8")
        for host in ("maya", "bpy", "mayatk", "blendertk", "uitk"):
            with self.subTest(host=host):
                self.assertIsNone(
                    re.search(rf"^\s*(?:import|from)\s+{host}\b", source, re.MULTILINE)
                )

    def test_every_key_edit_runs_under_the_claims_wrapper(self):
        source = SLOT_MODULE.read_text(encoding="utf-8")
        self.assertNotIn("ShotStore.active().key_edit", source)
        self.assertIn("self.tk.ShotStore.active()", source)


class TestAnimationClaimRegressions(unittest.TestCase):
    """Claims an option box made that its controls could not keep."""

    def setUp(self):
        self.tree = _parse()
        self.funcs = _functions(self.tree)

    def test_go_to_frame_offers_the_snap_modes_invert_can_flip(self):
        data = [
            d for _l, d in _combo_pairs(self.funcs["tb000_init"], self.tree, "cmb001")
        ]
        for mode in ("floor", "ceil"):
            self.assertIn(mode, data)

    def test_stagger_spacing_can_express_a_duration_fraction(self):
        self.assertEqual(
            _add_kwarg(self.funcs["tb003_init"], "s004", "__type__"), "QDoubleSpinBox"
        )

    def test_scale_factor_can_express_an_absolute_duration(self):
        ceiling = _add_kwarg(self.funcs["tb014_init"], "d001", "setMaximum")
        self.assertGreater(ceiling, 100.0)

    def test_combo_tooltips_name_every_option_the_combo_offers(self):
        checks = [
            ("tb000_init", "cmb001"),
            ("tb010_init", "cmb004"),
            ("tb012_init", "cmb038"),
            ("tb014_init", "cmb033"),
            ("tb014_init", "cmb034"),
            ("tb014_init", "cmb_scale_pivot"),
            ("tb008_init", "cmb002"),
            ("tb017_init", "cmb037"),
            ("tb017_init", "cmb_interp"),
        ]
        for init_name, combo in checks:
            with self.subTest(combo=combo):
                init = self.funcs[init_name]
                tip = _tooltip_src(init, self.tree, combo)
                labels = [
                    lab for lab, _d in _combo_pairs(init, self.tree, combo) if lab
                ]
                self.assertTrue(labels, f"{combo}: parsed no combo items")
                missing = [
                    lab
                    for lab in labels
                    if lab.split(": ")[-1].replace("&", "&amp;") not in tip
                ]
                self.assertEqual(
                    missing, [], f"{init_name}.{combo} never mentions {missing}"
                )

    def test_combo_item_orders_are_the_saved_ones(self):
        """Combos persist by INDEX: the composed class keeps each fork's order
        (Blender's appended items last)."""
        expected = {
            ("tb008_init", "cmb002"): [
                "start",
                "end",
                "both",
                "before_start",
                "after_end",
                "current",
            ],
            ("tb012_init", "cmb038"): [
                "auto",
                "current_frame",
                "selected",
                "channel_box",
                "copy_paste",
            ],
            ("tb017_init", "cmb037"): ["auto", "current_time", "selected", "all"],
            ("tb017_init", "cmb_interp"): ["stepped", "linear", "smooth"],
            ("tb014_init", "cmb_scale_pivot"): ["first_key", "current"],
        }
        for (init_name, combo), data in expected.items():
            with self.subTest(combo=combo):
                pairs = _combo_pairs(self.funcs[init_name], self.tree, combo)
                self.assertEqual([d for _l, d in pairs], data)


class TestSnapMethodVocabulary(unittest.TestCase):
    """The rounding vocabulary: one table, two entry points."""

    SNAP_COMBOS = (("tb009_init", "cmb003"), ("tb021_init", "cmb042"))

    def test_every_mode_is_one_round_value_accepts(self):
        import pythontk as ptk

        for label, mode in AnimationSlots.SNAP_METHODS.items():
            with self.subTest(label=label):
                ptk.MathUtils.round_value(1.5, mode=mode)

    def test_both_entry_points_offer_the_whole_table(self):
        tree = _parse()
        funcs = _functions(tree)
        expected = list(AnimationSlots.SNAP_METHODS.items())
        for init_name, combo in self.SNAP_COMBOS:
            with self.subTest(combo=combo):
                self.assertEqual(_combo_pairs(funcs[init_name], tree, combo), expected)


class TestRepairSectionCoverage(unittest.TestCase):
    def test_repair_offers_a_fix_for_fractional_key_times(self):
        slots = [slot for _l, slot, _t, _r in AnimationSlots._TOOLS_ITEMS["Repair"]]
        self.assertIn("tb021", slots)

    def test_the_repair_passes_run_without_a_selection(self):
        """Every Repair row reads its selection as a NARROWING (``... or None``)."""
        funcs = _functions(_parse())
        for name in ("tb015", "tb021", "b001"):
            with self.subTest(slot=name):
                self.assertTrue(
                    any(
                        isinstance(n, ast.BoolOp)
                        and isinstance(n.op, ast.Or)
                        and isinstance(n.values[-1], ast.Constant)
                        and n.values[-1].value is None
                        for n in ast.walk(funcs[name])
                    ),
                    f"{name} no longer degrades an empty selection to the scene",
                )


# ====================================================================== fake toolkit
def _menu(**values):
    """An option-box menu of fakes: a bool is a checkbox, a number a spinbox, a
    str or None a combo's data (``text=`` pairs give a combo its text)."""
    menu = SimpleNamespace()
    for name, value in values.items():
        if isinstance(value, tuple):  # (data, text)
            data, text = value
            setattr(
                menu,
                name,
                SimpleNamespace(
                    currentData=lambda d=data: d, currentText=lambda t=text: t
                ),
            )
        elif isinstance(value, bool):
            setattr(menu, name, SimpleNamespace(isChecked=lambda v=value: v))
        elif isinstance(value, (int, float)):
            setattr(menu, name, SimpleNamespace(value=lambda v=value: v))
        else:
            setattr(
                menu,
                name,
                SimpleNamespace(
                    currentData=lambda v=value: v, currentText=lambda v=value: v
                ),
            )
    return SimpleNamespace(option_box=SimpleNamespace(menu=menu))


class _FakeStore:
    """A shot store class: ``active()`` is the store, or raises *error*."""

    def __init__(self, claims=True, error=None):
        self.edit_ledger = ["claim"] if claims else []
        self.error = error
        self.edits = []

    def active(self):
        if self.error is not None:
            raise self.error
        return self

    @contextlib.contextmanager
    def key_edit(self, label, objects=None):
        self.edits.append((label, objects))
        yield "on_replace", "on_move"


class _ToolkitCase(unittest.TestCase):
    """The composed class over a fake toolkit (``sb.tk``)."""

    SELECTION = ["obj"]

    def setUp(self):
        migrated = Slots._legacy_repeat_last_migrated
        Slots._legacy_repeat_last_migrated = True  # no migration under test
        self.addCleanup(setattr, Slots, "_legacy_repeat_last_migrated", migrated)
        self.sb = mock.MagicMock()
        self.tk = self.sb.tk
        self.tk.ShotStore.active.return_value = None  # no shot record: no hooks
        self.tk.CoreUtils.selected_objects.return_value = list(self.SELECTION)
        self.tk.AnimUtils.get_current_frame.return_value = 12.0
        self.anim = self.tk.AnimUtils
        self.slots = AnimationSlots(self.sb)

    def message(self):
        (text, *_), _kw = self.sb.message_box.call_args
        return text


class TestKeyEdit(_ToolkitCase):
    """``_key_edit``: the wrapper every key edit runs under, so the shot claims
    of the keys it touches follow them."""

    def test_claims_ride_the_store_s_key_edit(self):
        store = _FakeStore()
        self.tk.ShotStore = store
        with self.slots._key_edit("Align Keys", ["a"]) as hooks:
            pass
        self.assertEqual(hooks, ("on_replace", "on_move"))
        self.assertEqual(store.edits, [("Align Keys", ["a"])])

    def test_an_unreadable_shot_record_still_runs_the_edit_unhooked(self):
        self.tk.ShotStore = _FakeStore(error=ValueError("not a readable record"))
        with self.assertLogs("tentacle.slots.animation", "WARNING"):
            with self.slots._key_edit("Align Keys") as hooks:
                pass
        self.assertEqual(hooks, (None, None))

    def test_the_edit_s_own_error_is_not_swallowed(self):
        """Only the store's unreadable record is caught, never the edit's."""
        for store in (_FakeStore(), _FakeStore(error=ValueError("bad"))):
            with self.subTest(readable=store.error is None):
                self.tk.ShotStore = store
                with self.assertRaises(KeyError):
                    with self.slots._key_edit("x"):
                        raise KeyError("the edit's own")

    def test_claimed_only_hands_no_hooks_to_a_store_that_claims_nothing(self):
        store = _FakeStore(claims=False)
        self.tk.ShotStore = store
        with self.slots._key_edit("Optimize Keys", claimed_only=True) as hooks:
            pass
        self.assertEqual((hooks, store.edits), ((None, None), []))

    def test_a_slot_hands_the_hooks_to_its_operation(self):
        self.tk.ShotStore = _FakeStore()
        self.slots.tb007(_menu(chk013=True, spn000=-1))
        kwargs = self.anim.align_selected_keyframes.call_args.kwargs
        self.assertEqual(
            (kwargs["on_replace"], kwargs["on_move"]), ("on_replace", "on_move")
        )


class TestTimeAndSelection(_ToolkitCase):
    def test_tb000_moves_the_playhead_by_the_frame(self):
        self.slots.tb000(
            _menu(cmb001="none", s000=5, cmb000="Relative", chk001=False, chk011=False)
        )
        self.anim.set_current_frame.assert_called_once_with(
            time=5, update=False, relative=True, snap_mode="none", invert_snap=False
        )

    def test_tb000_snap_rounds_the_current_frame_in_place(self):
        self.slots.tb000(
            _menu(cmb001="floor", s000=5, cmb000="Relative", chk001=True, chk011=True)
        )
        self.anim.set_current_frame.assert_called_once_with(
            time=None, update=True, relative=False, snap_mode="floor", invert_snap=True
        )

    def test_tb013_maps_the_scope_to_a_time(self):
        self.anim.select_keys.return_value = 3
        for scope, time in (("all", None), ("before", "before"), ("range", (2, 9))):
            with self.subTest(scope=scope):
                self.slots.tb013(
                    _menu(cmb041=scope, s012=2, s013=9, chk034=True, chk039=False)
                )
                self.anim.select_keys.assert_called_with(
                    ["obj"], time=time, channel_box_only=True, add_to_selection=False
                )
        self.assertIn("Selected 3", self.message())

    def test_an_empty_selection_refuses_without_calling_the_host(self):
        self.tk.CoreUtils.selected_objects.return_value = []
        self.slots.tb013(
            _menu(cmb041="all", s012=1, s013=2, chk034=False, chk039=False)
        )
        self.anim.select_keys.assert_not_called()
        self.assertIn("requires a selection", self.message())


class TestKeyTiming(_ToolkitCase):
    def test_tb001_inverts_the_selection_with_auto_time_as_none(self):
        self.slots.tb001(
            _menu(cmb035="vertical", s001=-1, d000=2.0, chk002=True, chk005=False)
        )
        args, kwargs = self.anim.invert_keys.call_args
        self.assertEqual(args, (["obj"],))
        self.assertEqual(
            (kwargs["time"], kwargs["mode"], kwargs["value_pivot"]),
            (None, "vertical", 2.0),
        )

    def test_tb001_shows_the_host_s_refusal(self):
        self.anim.invert_keys.side_effect = RuntimeError(
            "no keys belong to the selection"
        )
        self.slots.tb001(
            _menu(cmb035="horizontal", s001=4, d000=0.0, chk002=True, chk005=True)
        )
        self.assertEqual(self.message(), "no keys belong to the selection")

    def test_tb002_scene_scope_passes_none_without_a_selection(self):
        self.tk.CoreUtils.selected_objects.return_value = []
        self.slots.tb002(
            _menu(
                cmb036="scene", s002=-1, s003=4, chk004=True, chk003=True, chk021=False
            )
        )
        args, kwargs = self.anim.adjust_key_spacing.call_args
        self.assertEqual((args, kwargs["time"], kwargs["spacing"]), ((None,), None, 4))
        self.assertFalse(kwargs["selected_keys_only"])

    def test_tb002_keys_scope_narrows_to_selected_keys(self):
        self.anim.adjust_key_spacing.return_value = 0
        self.slots.tb002(
            _menu(
                cmb036="keys", s002=7, s003=1, chk004=False, chk003=False, chk021=True
            )
        )
        kwargs = self.anim.adjust_key_spacing.call_args.kwargs
        self.assertEqual((kwargs["time"], kwargs["selected_keys_only"]), (7, True))
        self.assertIn("No keys at or after", self.message())

    def test_tb003_staggers_with_maya_s_overlap_rule_and_auto_start(self):
        self.slots.tb003(
            _menu(
                s004=0.5,
                s005=-1,
                chk025=False,
                chk008=True,
                chk009=False,
                chk014=False,
                chk029=True,
                chk024=False,
            )
        )
        args, kwargs = self.tk.StaggerKeys.stagger_keys.call_args
        self.assertEqual(args, (["obj"],))
        self.assertEqual(
            (kwargs["start_frame"], kwargs["spacing"], kwargs["avoid_overlap"]),
            (None, 0.5, True),
        )
        self.assertTrue(kwargs["merge_touching"])

    def test_tb004_lets_the_host_pick_source_and_targets(self):
        self.slots.tb004(_menu(chk006=True, chk007=False, chk035=True))
        args, kwargs = self.anim.transfer_keyframes.call_args
        self.assertEqual(args, (None,))
        self.assertEqual(
            (kwargs["relative"], kwargs["transfer_tangents"], kwargs["optimize"]),
            (True, False, True),
        )

    def test_tb004_words_a_refusal_and_a_source_without_keys(self):
        self.anim.transfer_keyframes.side_effect = ValueError("select a source")
        self.slots.tb004(_menu(chk006=True, chk007=True, chk035=False))
        self.assertEqual(self.message(), "select a source")
        self.anim.transfer_keyframes.side_effect = None
        self.anim.transfer_keyframes.return_value = []
        self.slots.tb004(_menu(chk006=True, chk007=True, chk035=False))
        self.assertIn("no keys to transfer", self.message())

    def test_tb005_maps_auto_bounds_to_open_range_ends(self):
        cases = (
            ((-1, -1), None),
            ((5, -1), (5, None)),
            ((-1, 20), (None, 20)),
            ((5, 20), (5, 20)),
        )
        for (start, end), time_range in cases:
            with self.subTest(start=start, end=end):
                self.slots.tb005(
                    _menu(s021=start, s006=end, s007=50, chk028=True, chk027=False)
                )
                kwargs = self.anim.add_intermediate_keys.call_args.kwargs
                self.assertEqual(
                    (kwargs["time_range"], kwargs["ignore"], kwargs["percent"]),
                    (time_range, "visibility", 50),
                )

    def test_tb005_remove_reports_the_count(self):
        self.anim.remove_intermediate_keys.return_value = 4
        self.slots.tb005(_menu(s021=-1, s006=-1, s007=5, chk028=False, chk027=True))
        self.assertIsNone(self.anim.remove_intermediate_keys.call_args.kwargs["ignore"])
        self.assertIn("Removed 4", self.message())

    def test_tb006_and_tb007_report_nothing_moved(self):
        self.anim.move_keys_to_frame.return_value = False
        self.slots.tb006(_menu(chk031=True, chk012=True, chk033=False, cmb_align="end"))
        self.assertIn("Nothing keyed", self.message())
        self.anim.align_selected_keyframes.return_value = []
        self.slots.tb007(_menu(chk013=False, spn000=30))
        self.assertEqual(
            self.anim.align_selected_keyframes.call_args.kwargs["target_frame"], 30
        )
        self.assertIn("No selected keyframes", self.message())

    def test_tb008_keys_visibility(self):
        self.anim.set_visibility_keys.return_value = 2
        self.slots.tb008(
            _menu(
                cmb_visibility=(None, "Hidden"), cmb002="current", s008=1, chk016=False
            )
        )
        kwargs = self.anim.set_visibility_keys.call_args.kwargs
        self.assertEqual(
            (kwargs["visible"], kwargs["when"], kwargs["offset"]), (False, "current", 1)
        )
        self.sb.message_box.assert_not_called()

    def test_tb009_reads_the_playback_range_when_asked(self):
        self.tk.EnvUtils.scene_settings.return_value = {
            "frame_start": 1,
            "frame_end": 48,
        }
        self.anim.snap_keys_to_frames.return_value = 3
        self.slots.tb009(_menu(cmb003="ceil", chk017=True, chk018=True))
        kwargs = self.anim.snap_keys_to_frames.call_args.kwargs
        self.assertEqual(
            (kwargs["time_range"], kwargs["method"], kwargs["selected_only"]),
            ((1, 48), "ceil", True),
        )
        self.assertIn("Snapped 3", self.message())

    def test_tb010_deletes_over_the_scope(self):
        self.slots.tb010(_menu(cmb004="all", chk020=True))
        kwargs = self.anim.delete_keys.call_args.kwargs
        self.assertEqual((kwargs["time"], kwargs["channel_box_only"]), (None, True))
        self.slots.tb010(_menu(cmb004="after|current", chk020=False))
        self.assertEqual(
            self.anim.delete_keys.call_args.kwargs["time"], "after|current"
        )

    def test_tb011_ties_the_scene_when_nothing_is_selected(self):
        self.tk.CoreUtils.selected_objects.return_value = []
        self.anim.tie_keyframes.return_value = 4
        self.slots.tb011(_menu(cmb_tie=(None, "Tie"), chk023=True))
        self.anim.tie_keyframes.assert_called_once_with(None, absolute=True)
        self.assertIn("Tied <hl>4</hl>", self.message())

    def test_tb011_untie_counts_the_keys_a_mapping_names(self):
        self.anim.untie_keyframes.return_value = {"obj": {"crv": [1.0, 20.0]}}
        self.slots.tb011(_menu(cmb_tie=(None, "Untie"), chk023=True))
        self.anim.untie_keyframes.assert_called_once_with(["obj"], on_delete=None)
        self.assertIn("Untied <hl>2</hl>", self.message())

    def test_tb014_maps_the_mode_and_pivot(self):
        self.anim.get_current_frame.return_value = 33.0
        self.tk.ScaleKeys.scale_keys.return_value = 6
        self.slots.tb014(
            _menu(
                cmb014="speed_rotation",
                d001=5.0,
                chk_channel_box=False,
                cmb_scale_mode=(None, "Absolute"),
                chk_split_static=True,
                chk_merge_touching=False,
                cmb033="per_object",
                cmb034="nearest",
                s014=64,
                cmb_scale_pivot="current",
            )
        )
        kwargs = self.tk.ScaleKeys.scale_keys.call_args.kwargs
        self.assertEqual(
            (
                kwargs["mode"],
                kwargs["include_rotation"],
                kwargs["pivot"],
                kwargs["keys"],
            ),
            ("speed", "only", 33.0, "auto"),
        )
        self.assertTrue(kwargs["absolute"] and kwargs["prevent_overlap"])
        self.assertIn("Scaled 6 keyframe(s) 5.00 units/frame", self.message())


class TestCopyPaste(_ToolkitCase):
    def test_tb012_copies_from_the_selection_and_reports_the_counts(self):
        self.anim.copy_keys.return_value = {"obj": {"tx": [1, 2]}}
        self.anim.copied_key_counts.return_value = {
            "keys": 2,
            "attributes": 1,
            "objects": 1,
        }
        self.slots.tb012(_menu(cmb038="selected"))
        self.anim.copy_keys.assert_called_once_with(None, mode="selected")
        self.assertEqual(self.slots._copied_frame, 12.0)
        self.assertIn(
            "Copied 2 key(s) across 1 attribute(s) from 1 object(s)", self.message()
        )

    def test_tb012_nothing_to_copy_is_said_per_mode(self):
        self.anim.copy_keys.return_value = None
        self.slots.tb012(_menu(cmb038="channel_box"))
        self.assertIn("No channels selected", self.message())
        self.assertIsNone(self.slots._copied)

    def test_tb012_copy_paste_pastes_at_the_playhead_onto_the_selection(self):
        self.anim.copy_keys.return_value = {"obj": {"tx": 1.0}}
        self.anim.paste_keys.return_value = 1
        self.slots.tb012(_menu(cmb038="copy_paste"))
        self.anim.copy_keys.assert_called_once_with(None, mode="auto")
        args, kwargs = self.anim.paste_keys.call_args
        self.assertEqual(
            (args, kwargs["target_time"]), ((["obj"], {"obj": {"tx": 1.0}}), 12.0)
        )
        self.assertIn("Copied and pasted keys onto 1 object(s)", self.message())

    def test_tb018_pastes_at_the_copy_frame_or_the_playhead(self):
        self.slots._copied, self.slots._copied_frame = {"obj": {"tx": 1.0}}, 4.0
        self.anim.paste_keys.return_value = ["obj"]  # Blender answers the objects
        self.slots.tb018(_menu(cmb039="source"))
        self.assertEqual(self.anim.paste_keys.call_args.kwargs["target_time"], 4.0)
        self.slots.tb018(_menu(cmb039="playhead"))
        self.assertEqual(self.anim.paste_keys.call_args.kwargs["target_time"], 12.0)
        self.assertIn("Pasted keys onto 1 object(s)", self.message())

    def test_tb018_with_nothing_copied_says_so(self):
        self.slots.tb018(_menu(cmb039="playhead"))
        self.anim.paste_keys.assert_not_called()
        self.assertIn("Copy Keys", self.message())


class TestRepairAndInfo(_ToolkitCase):
    def test_tb015_repairs_the_scene_when_nothing_is_selected(self):
        self.tk.CoreUtils.selected_objects.return_value = []
        self.anim.repair_corrupted_curves.return_value = {
            "corrupted_found": 2,
            "curves_repaired": 1,
            "curves_deleted": 1,
            "keys_fixed": 3,
            "details": ["a", "b", "c", "d"],
        }
        self.slots.tb015(
            _menu(chk036=True, chk037=True, chk038=False, d015=1e5, d016=1e6)
        )
        args, kwargs = self.anim.repair_corrupted_curves.call_args
        self.assertEqual(args, (None,))
        self.assertEqual(
            (
                kwargs["delete_corrupted"],
                kwargs["fix_invalid_times"],
                kwargs["time_range_threshold"],
            ),
            (True, False, 1e5),
        )
        self.assertIn("Found 2 corrupted curve(s) on the scene", self.message())
        self.assertIn("and 1 more", self.message())

    def test_tb021_reports_each_outcome(self):
        cases = (
            ({"curves": 0, "snapped": 0, "off_frame": 0}, "No animation curves found"),
            ({"curves": 2, "snapped": 0, "off_frame": 0}, "sit on a fractional frame"),
            ({"curves": 2, "snapped": 3, "off_frame": 1}, "still off-frame"),
        )
        for report, words in cases:
            with self.subTest(words=words):
                self.anim.repair_fractional_keys.return_value = report
                self.slots.tb021(_menu(cmb042="half_up"))
                self.assertIn(words, self.message())
        args, kwargs = self.anim.repair_fractional_keys.call_args
        self.assertEqual((args, kwargs["method"]), ((["obj"],), "half_up"))

    def test_tb016_widens_only_a_selected_scope(self):
        self.sb.progress.return_value.__enter__.return_value = lambda *a: True
        self.tk.SegmentKeys.format_scene_info_html.return_value = "a,b"
        self.slots.tb016(
            _menu(
                cmb_scope="all",
                cmb_traversal="upstream",
                chk_sort_time=True,
                chk_csv_output=True,
                chk_ignore_holds=False,
            )
        )
        kwargs = self.tk.SegmentKeys.format_scene_info_html.call_args.kwargs
        self.assertEqual((kwargs["objects"], kwargs["traversal"]), (None, None))
        self.assertTrue(self.sb.text_view_dialog.call_args.kwargs["monospace"])

    def test_tb016_with_no_animation_says_so(self):
        self.tk.SegmentKeys.format_scene_info_html.return_value = ""
        self.slots.tb016(
            _menu(
                cmb_scope="selected",
                cmb_traversal="both",
                chk_sort_time=False,
                chk_csv_output=False,
                chk_ignore_holds=True,
            )
        )
        kwargs = self.tk.SegmentKeys.format_scene_info_html.call_args.kwargs
        self.assertEqual((kwargs["objects"], kwargs["traversal"]), (["obj"], "both"))
        self.assertIn("No animation", self.message())
        self.sb.text_view_dialog.assert_not_called()

    def test_tb017_hands_the_combos_to_the_host(self):
        self.anim.set_key_interpolation.return_value = {"curves": 2, "objects": 1}
        self.slots.tb017(_menu(cmb037="current_time", cmb040="in", cmb_interp="linear"))
        self.anim.set_key_interpolation.assert_called_once_with(
            None, interpolation="linear", keys="current_time", tangent="in"
        )
        self.assertIn("Set 2 curve(s)", self.message())

    def test_tb017_shows_the_host_s_refusal(self):
        self.anim.set_key_interpolation.side_effect = ValueError("No keys selected.")
        self.slots.tb017(_menu(cmb037="selected", cmb040="out", cmb_interp="stepped"))
        self.assertEqual(self.message(), "No keys selected.")

    def test_tb019_uses_the_extremes_sentinel_and_reports_the_stats(self):
        self.sb.progress.return_value.__enter__.return_value = lambda *a: True

        def optimize(objects, stats=None, **_kw):
            stats.update(
                curves_before=4, curves_after=3, keys_before=100, keys_after=40
            )

        self.anim.optimize_keys.side_effect = optimize
        self.slots.tb019(
            _menu(chk000=True, chk030=True, chk032=True, chk040=True, d017=0.01)
        )
        args, kwargs = self.anim.optimize_keys.call_args
        self.assertEqual((args, kwargs["value_tolerance"]), ((["obj"],), -1))
        self.assertIn("Keys: 100 → 40", self.message())
        self.assertIn("60.0% reduction", self.message())

    def test_b005_fits_the_selection_and_says_the_range(self):
        self.anim.fit_playback_range.return_value = (1.0, 120.0)
        self.slots.b005()
        self.anim.fit_playback_range.assert_called_once_with(["obj"])
        self.assertIn("1-120", self.message())
        self.anim.fit_playback_range.return_value = None
        self.slots.b005()
        self.assertIn("Nothing keyed", self.message())

    def test_b001_repairs_visibility_tangents_on_the_selection(self):
        self.slots.b001()
        self.tk.Diagnostics.repair_visibility_tangents.assert_called_once_with(
            objects=["obj"]
        )

    def test_the_tool_rows_open_the_composed_tools(self):
        for slot, tool in (
            ("b000", "shot_sequencer"),
            ("b004", "shot_manifest"),
            ("b006", "key_stash"),
        ):
            with self.subTest(slot=slot):
                getattr(self.slots, slot)()
                self.sb.handlers.marking_menu.show.assert_called_with(tool)
        self.slots.tb020(None)
        self.sb.handlers.marking_menu.show.assert_called_with("smart_bake")


class TestToolsList(_ToolkitCase):
    def test_a_maya_only_row_is_tagged_for_the_visibility_policy(self):
        widget = mock.MagicMock()
        rows = []
        widget.add.return_value.sublist.add.return_value.sublist.add.side_effect = (
            lambda label, **_kw: rows.append(mock.MagicMock(label=label)) or rows[-1]
        )
        self.slots.list000_init(widget)
        tagged = [r.label for r in rows if r.setProperty.called]
        self.assertEqual(tagged, ["Repair Visibility Tangents"])
        rows[
            [r.label for r in rows].index("Repair Visibility Tangents")
        ].setProperty.assert_called_with("requires", "maya")

    def test_a_row_dispatches_to_its_slot(self):
        item = mock.MagicMock()
        item.sublist.get_items.return_value = []
        item.item_text.return_value = "Key Stash"
        item.parent_item_text.return_value = "Stash"
        self.slots.list000(item)
        self.sb.handlers.marking_menu.show.assert_called_with("key_stash")


# ====================================================================== in Maya
class _RecordedSb:
    def __init__(self, tk):
        self.tk = tk
        self.messages = []

    def message_box(self, *args, **kwargs):
        self.messages.append((args, kwargs))


def _maya_instance():
    """The composed class over the real ``mtk``, without the UI-loading __init__."""
    instance = AnimationSlots.__new__(AnimationSlots)
    instance.sb = _RecordedSb(maya_module("mayatk"))
    instance._copied = None
    instance._copied_frame = None
    return instance


def _chk(state):
    return SimpleNamespace(isChecked=lambda: state)


def _val(value):
    return SimpleNamespace(value=lambda: value)


def _combo(data, text=""):
    return SimpleNamespace(
        currentData=lambda: data,
        currentText=lambda: text,
        currentIndex=lambda: 0,
        itemData=lambda _i: data,
    )


def _widget(**controls):
    return SimpleNamespace(option_box=SimpleNamespace(menu=SimpleNamespace(**controls)))


@unittest.skipUnless(_MAYA_AVAILABLE, "drives the real mtk; runs in a fresh Maya")
class TestTb021RepairScope(unittest.TestCase):
    """tb021's scope IS its reason to exist beside tb009 -- so pin it live: a
    selection reaches its DESCENDANTS, nothing selected is the scene, and an
    unanimated selection must not fall through to the scene."""

    def setUp(self):
        cmds.file(new=True, force=True)
        self.instance = _maya_instance()

    def tearDown(self):
        cmds.file(new=True, force=True)

    @staticmethod
    def _keyed(name, attr, times, parent=None):
        obj = cmds.polyCube(name=name)[0]
        if parent:
            obj = cmds.parent(obj, parent)[0]
        for t in times:
            cmds.setKeyframe(obj, attribute=attr, time=t, value=t)
        return obj

    @staticmethod
    def _times(obj, attr):
        return sorted(
            cmds.keyframe(obj, attribute=attr, query=True, timeChange=True) or []
        )

    def _run(self, method="nearest"):
        self.instance.tb021(_widget(cmb042=_combo(method)))
        return self.instance.sb.messages[-1][0][0]

    def test_a_selection_carries_its_descendants(self):
        root = self._keyed("scope_root", "translateX", [1.3, 4.8])
        child = self._keyed("scope_child", "translateY", [2.2, 9.7], parent=root)
        outside = self._keyed("scope_outside", "translateZ", [3.4])
        cmds.select(root, replace=True)
        self._run()
        self.assertEqual(self._times(root, "translateX"), [1.0, 5.0])
        self.assertEqual(self._times(child, "translateY"), [2.0, 10.0])
        self.assertEqual(
            self._times(outside, "translateZ"), [3.4], "an outsider swept in"
        )

    def test_no_selection_is_the_whole_scene(self):
        a = self._keyed("scope_a", "translateX", [1.3])
        b = self._keyed("scope_b", "translateZ", [3.4])
        cmds.select(clear=True)
        self._run()
        self.assertEqual(self._times(a, "translateX"), [1.0])
        self.assertEqual(self._times(b, "translateZ"), [3.0])

    def test_an_unanimated_selection_does_not_fall_through_to_the_scene(self):
        elsewhere = self._keyed("scope_elsewhere", "translateX", [1.3])
        bare = cmds.polyCube(name="scope_bare")[0]
        cmds.select(bare, replace=True)
        message = self._run()
        self.assertEqual(self._times(elsewhere, "translateX"), [1.3])
        self.assertIn("No animation curves found", message)

    def test_a_driven_key_is_not_snapped_as_if_it_were_a_frame(self):
        driver = cmds.polyCube(name="scope_driver")[0]
        driven = cmds.polyCube(name="scope_driven")[0]
        for driver_value, value in ((0.0, 0.0), (2.5, 10.0)):
            cmds.setDrivenKeyframe(
                f"{driven}.translateY",
                currentDriver=f"{driver}.translateX",
                driverValue=driver_value,
                value=value,
            )
        cmds.select(clear=True)
        self._run()
        cmds.setAttr(f"{driver}.translateX", 2.5)
        self.assertAlmostEqual(cmds.getAttr(f"{driven}.translateY"), 10.0, places=4)

    def test_a_blocked_key_is_disclosed_rather_than_merged_over(self):
        obj = self._keyed("scope_blocked", "translateX", [])
        cmds.setKeyframe(obj, attribute="translateX", time=10, value=100.0)
        cmds.setKeyframe(obj, attribute="translateX", time=10.4, value=42.0)
        cmds.setKeyframe(obj, attribute="translateX", time=20.4, value=7.0)
        cmds.select(obj, replace=True)
        message = self._run()
        self.assertEqual(
            cmds.keyframe(
                obj, attribute="translateX", query=True, time=(10, 10), valueChange=True
            ),
            [100.0],
        )
        self.assertIn("still off-frame", message)


@unittest.skipUnless(_MAYA_AVAILABLE, "drives the real mtk; runs in a fresh Maya")
class TestAnimationInMaya(unittest.TestCase):
    """The composed slots over the real ``mtk``."""

    def setUp(self):
        cmds.file(new=True, force=True)
        self.addCleanup(cmds.file, new=True, force=True)
        self.instance = _maya_instance()
        self.cube = cmds.polyCube(name="anim_cube")[0]
        for t, v in ((1, 0.0), (10, 5.0)):
            cmds.setKeyframe(self.cube, attribute="translateX", time=t, value=v)
        cmds.select(self.cube, replace=True)

    def _message(self):
        return self.instance.sb.messages[-1][0][0]

    def test_tb017_all_steps_every_key_on_the_selection(self):
        cmds.selectKey(clear=True)
        self.instance.tb017(
            _widget(
                cmb037=_combo("all"), cmb040=_combo("out"), cmb_interp=_combo("stepped")
            )
        )
        crv = cmds.listConnections(f"{self.cube}.translateX", type="animCurve")[0]
        self.assertEqual(
            set(cmds.keyTangent(crv, query=True, outTangentType=True)), {"step"}
        )

    def test_tb017_selected_with_no_keys_picked_is_refused(self):
        cmds.selectKey(clear=True)
        self.instance.tb017(
            _widget(
                cmb037=_combo("selected"),
                cmb040=_combo("out"),
                cmb_interp=_combo("stepped"),
            )
        )
        self.assertIn("No keys selected", self._message())

    def test_b005_fits_the_playback_range_to_the_selection(self):
        self.instance.b005()
        self.assertEqual(
            (
                cmds.playbackOptions(q=True, minTime=True),
                cmds.playbackOptions(q=True, maxTime=True),
            ),
            (1.0, 10.0),
        )
        self.assertIn("1-10", self._message())

    def test_tb012_then_tb018_round_trips_a_value(self):
        cmds.currentTime(10)
        self.instance.tb012(_widget(cmb038=_combo("current_frame")))
        self.assertIn("Copied 1 key(s)", self._message())
        cmds.currentTime(20)
        self.instance.tb018(_widget(cmb039=_combo("playhead")))
        self.assertEqual(
            cmds.keyframe(
                self.cube,
                attribute="translateX",
                query=True,
                time=(20, 20),
                valueChange=True,
            ),
            [5.0],
        )


@unittest.skipUnless(_MAYA_AVAILABLE, "drives the real mtk; runs in a fresh Maya")
class TestAlignInvertReleaseShotClaims(unittest.TestCase):
    """The key edits carry the shot claims of the keys they touch: a key one
    REPLACES takes its claims with it (``ShotStore.release_replaced``) and a key
    one MOVES carries them along (``ShotStore.remap_moved``), both handed over by
    the store's ``key_edit``. The Blender twin is
    ``blender/deepened_slots_check.py``.
    """

    def setUp(self):
        import mayatk as mtk

        self.mtk = mtk
        cmds.file(new=True, force=True)
        self.addCleanup(cmds.file, new=True, force=True)
        self.instance = _maya_instance()
        self.store = mtk.ShotStore()
        mtk.ShotStore.set_active(self.store)
        self.addCleanup(mtk.ShotStore.clear_active)

    def _claimed(self, name, frames, at=20.0):
        """A selected cube keyed on *frames* (value = frame), a fade claiming its
        key at *at* (none when ``None``)."""
        obj = cmds.polyCube(name=name)[0]
        for t in frames:
            cmds.setKeyframe(obj, attribute="translateX", time=t, value=t)
        crv = cmds.keyframe(obj, attribute="translateX", query=True, name=True)[0]
        if at is not None:
            self.store.edit_ledger.record_authored(crv, at, 0, "fade_in", obj)
        cmds.select(obj, replace=True)
        return crv

    def _claimed_frames(self):
        return [round(t, 3) for _crv, t in self.store.edit_ledger.authored()]

    @staticmethod
    def _select_keys(crv, *times):
        cmds.selectKey(clear=True)
        for t in times:
            cmds.selectKey(crv, time=(t, t), add=True)

    def _align(self, frame):
        self.instance.tb007(_widget(chk013=_chk(True), spn000=_val(frame)))

    def _invert(self):
        self.instance.tb001(
            _widget(
                cmb035=_combo("horizontal"),
                s001=_val(-1),
                d000=_val(0.0),
                chk002=_chk(True),
                chk005=_chk(False),
            )
        )

    def test_align_releases_the_claims_of_the_key_it_lands_on(self):
        crv = self._claimed("claim_align", (10, 20, 30))
        self._select_keys(crv, 10)
        self._align(20)
        led = self.store.edit_ledger
        self.assertFalse(led.owns_any(crv, 20.0), led.to_dict())
        self.assertEqual(
            sorted(cmds.keyframe(crv, query=True, timeChange=True)), [20.0, 30.0]
        )

    def test_invert_releases_the_claims_of_the_key_it_lands_on(self):
        crv = self._claimed("claim_invert", (10, 15, 20, 25))
        self._select_keys(crv, 10, 15, 25)  # over [10, 25]: 15 lands on 20
        self._invert()
        self.assertFalse(self.store.edit_ledger.owns_any(crv, 20.0))
        self.assertEqual(
            sorted(cmds.keyframe(crv, query=True, timeChange=True)), [10.0, 20.0, 25.0]
        )

    def test_invert_carries_the_claims_of_a_key_it_moves(self):
        self._claimed("claim_moved", (10, 15, 25, 30), at=15.0)
        cmds.selectKey(clear=True)
        self._invert()
        self.assertEqual(self._claimed_frames(), [25.0])

    def test_adjust_spacing_carries_the_claims_of_the_keys_it_moves(self):
        self._claimed("claim_spacing", (1, 10), at=10.0)
        self.instance.tb002(
            _widget(
                s003=_val(5),
                s002=_val(6),
                chk004=_chk(False),
                chk003=_chk(False),
                cmb036=_combo("objects"),
                chk021=_chk(False),
            )
        )
        self.assertEqual(self._claimed_frames(), [15.0])

    def test_transfer_releases_the_claims_of_a_target_key_it_replaces(self):
        source = cmds.polyCube(name="xfer_source")[0]
        for t, v in ((1, 0.0), (10, 10.0)):
            cmds.setKeyframe(source, attribute="translateX", time=t, value=v)
        target = self._claimed("xfer_target", (1, 10), at=1.0)  # 1 holds 1.0
        cmds.select([source, "xfer_target"], replace=True)
        cmds.selectKey(clear=True)
        self.instance.tb004(
            _widget(chk006=_chk(False), chk007=_chk(False), chk035=_chk(False))
        )
        self.assertFalse(self.store.edit_ledger.owns_any(target, 1.0))

    def test_move_keys_releases_the_claims_of_a_key_it_lands_on(self):
        crv = self._claimed("claim_move", (1, 5, 10), at=5.0)
        self._select_keys(crv, 1)
        cmds.currentTime(5)
        self.instance.tb006(
            _widget(
                chk031=_chk(True),
                chk012=_chk(False),
                chk033=_chk(False),
                cmb_align=_combo("start"),
            )
        )
        self.assertFalse(self.store.edit_ledger.owns_any(crv, 5.0))
        self.assertEqual(
            sorted(cmds.keyframe(crv, query=True, timeChange=True)), [5.0, 10.0]
        )

    def test_visibility_keys_release_the_claims_of_a_key_they_replace(self):
        obj = cmds.polyCube(name="claim_vis")[0]
        cmds.setKeyframe(obj, attribute="translateX", time=1, value=0)
        cmds.setKeyframe(obj, attribute="translateX", time=10, value=1)
        cmds.setKeyframe(obj, attribute="visibility", time=1, value=1)
        crv = cmds.keyframe(obj, attribute="visibility", query=True, name=True)[0]
        self.store.edit_ledger.record_authored(crv, 1.0, 0, "fade_in", obj)
        cmds.select(obj, replace=True)
        self.instance.tb008(
            _widget(
                cmb_visibility=_combo(None, "Hidden"),
                cmb002=_combo("start"),
                s008=_val(0),
                chk016=_chk(False),
            )
        )
        self.assertFalse(self.store.edit_ledger.owns_any(crv, 1.0))

    def test_snap_carries_the_claims_of_the_keys_it_moves(self):
        crv = self._claimed("claim_snap", (1, 10), at=None)
        cmds.setKeyframe("claim_snap", attribute="translateX", time=4.4, value=4)
        self.store.edit_ledger.record_authored(crv, 4.4, 0, "fade_in", "claim_snap")
        self.instance.tb009(
            _widget(cmb003=_combo("nearest"), chk017=_chk(False), chk018=_chk(False))
        )
        self.assertEqual(self._claimed_frames(), [4.0])

    def test_paste_releases_the_claims_of_a_key_it_replaces(self):
        crv = self._claimed("claim_paste", (1, 10, 20), at=10.0)
        self._select_keys(crv, 20)
        self.instance._copied = self.mtk.AnimUtils.copy_keys(
            ["claim_paste"], mode="selected"
        )
        cmds.currentTime(10)
        self.instance.tb018(_widget(cmb039=_combo("playhead")))
        self.assertEqual(
            cmds.keyframe(crv, query=True, time=(10, 10), valueChange=True), [20.0]
        )
        self.assertFalse(self.store.edit_ledger.owns_any(crv, 10.0))

    def test_scale_carries_the_claims_of_the_keys_it_moves(self):
        self._claimed("claim_scale", (0, 10), at=10.0)
        cmds.selectKey(clear=True)
        self.instance.tb014(
            _widget(
                cmb014=_combo("uniform"),
                d001=_val(2.0),
                chk_channel_box=_chk(False),
                cmb_scale_mode=_combo(None, "Relative"),
                chk_split_static=_chk(True),
                chk_merge_touching=_chk(False),
                cmb033=_combo("single_group"),
                cmb034=_combo("nearest"),
                s014=_val(64),
                cmb_scale_pivot=_combo("first_key"),
            )
        )
        self.assertEqual(self._claimed_frames(), [20.0])

    def test_stagger_carries_the_claims_of_the_keys_it_moves(self):
        lead = cmds.polyCube(name="stagger_lead")[0]
        for t in (0, 10):
            cmds.setKeyframe(lead, attribute="translateX", time=t, value=t)
        self._claimed("claim_stagger", (5, 15), at=15.0)  # starts after the lead
        cmds.select([lead, "claim_stagger"], replace=True)
        cmds.selectKey(clear=True)
        self.instance.tb003(
            _widget(
                s004=_val(0),
                s005=_val(-1),
                chk025=_chk(False),
                chk008=_chk(False),
                chk009=_chk(False),
                chk014=_chk(False),
                chk029=_chk(False),
                chk024=_chk(False),
            )
        )
        self.assertEqual(self._claimed_frames(), [20.0])

    def test_delete_keys_releases_the_claims_of_the_keys_it_deletes(self):
        crv = self._claimed("claim_delete", (1, 10, 20), at=10.0)
        cmds.currentTime(10)
        self.instance.tb010(_widget(cmb004=_combo("current"), chk020=_chk(False)))
        self.assertEqual(
            sorted(cmds.keyframe(crv, query=True, timeChange=True)), [1.0, 20.0]
        )
        self.assertFalse(self.store.edit_ledger.owns_any(crv, 10.0))

    def test_remove_intermediate_keys_releases_the_claims_of_the_keys_it_deletes(self):
        crv = self._claimed("claim_thin", (1, 10, 20), at=10.0)
        self.instance.tb005(
            _widget(
                chk027=_chk(True),
                chk028=_chk(False),
                s021=_val(-1),
                s006=_val(-1),
                s007=_val(0),
            )
        )
        self.assertEqual(
            sorted(cmds.keyframe(crv, query=True, timeChange=True)), [1.0, 20.0]
        )
        self.assertFalse(self.store.edit_ledger.owns_any(crv, 10.0))

    def test_untie_releases_the_claims_of_the_bookends_it_deletes(self):
        crv = self._claimed("claim_untie", (5, 10), at=None)
        cmds.playbackOptions(minTime=1, maxTime=20)
        self.mtk.AnimUtils.tie_keyframes(["claim_untie"])  # bookends at 1 and 20
        self.store.edit_ledger.record_authored(crv, 20.0, 0, "fade_out", "claim_untie")
        self.instance.tb011(_widget(cmb_tie=_combo(None, "Untie"), chk023=_chk(False)))
        self.assertEqual(
            sorted(cmds.keyframe(crv, query=True, timeChange=True)), [5.0, 10.0]
        )
        self.assertFalse(self.store.edit_ledger.owns_any(crv, 20.0))

    def test_optimize_releases_the_claims_of_the_keys_and_curves_it_deletes(self):
        obj = cmds.polyCube(name="claim_optimize")[0]
        for t, v in ((0, 1), (10, 1), (20, 1), (30, 5)):
            cmds.setKeyframe(obj, attribute="translateX", time=t, value=v)
        for t in (0, 10):  # held at its default: static, so deleted (lossless)
            cmds.setKeyframe(obj, attribute="translateY", time=t, value=0)
        tx = cmds.keyframe(obj, attribute="translateX", query=True, name=True)[0]
        ty = cmds.keyframe(obj, attribute="translateY", query=True, name=True)[0]
        led = self.store.edit_ledger
        led.record_authored(tx, 10.0, 0, "fade_in", obj)  # a flat key
        led.record_authored(ty, 0.0, 0, "fade_in", obj)  # on a static curve
        cmds.select(obj, replace=True)
        self.instance.sb.progress = contextlib.contextmanager(
            lambda **_kw: (yield lambda *a, **k: None)
        )
        self.instance.sb.progress_adapter = lambda update: update
        self.instance.tb019(
            _widget(
                chk000=_chk(True),
                chk030=_chk(True),
                chk032=_chk(False),
                chk040=_chk(False),
                d017=_val(0.001),
            )
        )
        self.assertFalse(cmds.objExists(ty))
        self.assertEqual(led.authored(), [], led.to_dict())

    def test_repair_releases_the_claims_of_the_keys_it_deletes(self):
        crv = self._claimed("claim_repair", (1, 10, 20), at=1.0)
        cmds.keyframe(crv, edit=True, valueChange=1e9, index=(0, 0))
        self.instance.tb015(
            _widget(
                chk036=_chk(False),
                chk037=_chk(True),
                chk038=_chk(True),
                d015=_val(1e6),
                d016=_val(1e6),
            )
        )
        self.assertEqual(
            sorted(cmds.keyframe(crv, query=True, timeChange=True)), [10.0, 20.0]
        )
        self.assertFalse(self.store.edit_ledger.owns_any(crv, 1.0))

    def test_undoing_a_panel_align_puts_back_the_claim_it_released(self):
        """With claims the edit runs inside the store's ``scene_edit``: one undo
        step paired with a restore point taken BEFORE it, so Maya's own undo of
        that step brings the released claim back with its key."""
        cmds.undoInfo(state=True, infinity=True)
        crv = self._claimed("claim_undo", (10, 20, 30))
        self._select_keys(crv, 10)
        self._align(20)
        self.assertFalse(self.store.edit_ledger.owns_any(crv, 20.0))
        paired, marker = self.store.peek_boundary_tag()
        self.assertTrue(paired, "the restore point is not paired with Maya's step")
        cmds.undo()
        self.assertEqual(self.mtk.MayaShotsHost.undo_queue_top(redo=True), marker)
        self.assertFalse(self.store.has_boundary_snapshot(), "the undo applied it")
        self.assertTrue(self.store.edit_ledger.owns_authored(crv, 20.0))
        self.assertEqual(
            sorted(cmds.keyframe(crv, query=True, timeChange=True)), [10.0, 20.0, 30.0]
        )

    def test_a_no_op_snap_between_does_not_block_the_aligns_undo(self):
        cmds.undoInfo(state=True, infinity=True)
        crv = self._claimed("claim_noop", (10, 20, 30))
        self.store.edit_ledger.record_authored(crv, 30.0, 0, "fade_out", "claim_noop")
        self._select_keys(crv, 10)
        self._align(20)
        self.instance.tb021(_widget(cmb042=_combo("nearest")))  # all whole
        self.assertEqual(len(self.store._boundary_undo), 1, "the Align's alone")
        cmds.undo()
        self.assertTrue(self.store.edit_ledger.owns_authored(crv, 20.0))
        self.assertTrue(self.store.edit_ledger.owns_authored(crv, 30.0))
        self.assertEqual(
            sorted(cmds.keyframe(crv, query=True, timeChange=True)), [10.0, 20.0, 30.0]
        )

    def test_snap_fractional_carries_the_claims_of_the_keys_it_moves(self):
        crv = self._claimed("claim_snap_frac", (1, 10), at=None)
        cmds.setKeyframe("claim_snap_frac", attribute="translateX", time=4.4, value=4)
        self.store.edit_ledger.record_authored(
            crv, 4.4, 0, "fade_in", "claim_snap_frac"
        )
        self.instance.tb021(_widget(cmb042=_combo("nearest")))
        self.assertEqual(self._claimed_frames(), [4.0])

    def test_copy_paste_releases_the_claims_of_a_key_it_replaces(self):
        """Copy + Paste: Auto copies the picked key (20's) and pastes it at the
        playhead onto the same selection, replacing the key on 10."""
        crv = self._claimed("claim_copy_paste", (1, 10, 20), at=10.0)
        self._select_keys(crv, 20)
        cmds.currentTime(10)
        self.instance.tb012(_widget(cmb038=_combo("copy_paste")))
        self.assertEqual(
            cmds.keyframe(crv, query=True, time=(10, 10), valueChange=True), [20.0]
        )
        self.assertFalse(self.store.edit_ledger.owns_any(crv, 10.0))

    def test_a_scene_with_no_claims_gets_no_restore_point(self):
        crv = self._claimed("no_claims", (10, 20, 30), at=None)
        self._select_keys(crv, 10)
        self._align(20)
        self.assertEqual(
            sorted(cmds.keyframe(crv, query=True, timeChange=True)), [20.0, 30.0]
        )
        self.assertFalse(self.store.has_boundary_snapshot())


if __name__ == "__main__":
    unittest.main()
