#!/usr/bin/python
# coding=utf-8
"""Regression tests for tentacle.slots.maya.transform.

transform.py is 538 lines of UI plumbing over mtk.drop_to_grid /
mtk.freeze_transforms / mtk.move_to / mtk.match_scale. The units worth
pinning at this layer:

- tb002 (Freeze Transforms): the cmb_connection_strategy index → string
  mapping (0="preserve", 1="disconnect", 2="delete"). Index drift
  silently switches strategies.
- tb005 (Move To): ≥2 ordered-selection gate + routing between
  move-all-to-last vs first-to-rest.
- b001 (Match Scale): ≥2 selection gate, forwards (frm, to[]).
- setTransformSnap: state 0/1/2 → snap on/off + snapRelative true/false
  routing across move/scale/rotate contexts.
"""
import unittest
from pathlib import Path

from _host import MAYA_AVAILABLE as _MAYA_AVAILABLE, maya_module

ROOT = Path(__file__).resolve().parent.parent

cmds = maya_module("maya.cmds")
transform_module = maya_module("tentacle.slots.maya.transform")


class _FakeChk:
    def __init__(self, state):
        self._state = state

    def isChecked(self):
        return self._state


class _FakeCombo:
    def __init__(self, current_index=0, data=None):
        self._i = current_index
        self._data = data

    def currentIndex(self):
        return self._i

    def currentData(self):
        return self._data


class _FakeMenu:
    def __init__(self, **attrs):
        for k, v in attrs.items():
            setattr(self, k, v)


class _FakeOptionBox:
    def __init__(self, menu):
        self.menu = menu


class _FakeWidget:
    def __init__(self, menu):
        self.option_box = _FakeOptionBox(menu)


class _RecordedSb:
    def __init__(self):
        self.messages = []

    def message_box(self, *args, **kwargs):
        self.messages.append((args, kwargs))


class TestSelfLabellingButtonsWireToTheOptionBoxMenu(unittest.TestCase):
    """tb003 (Constrain) / tb004 (Snap) rename themselves from their own checkboxes.

    DCC-free source pins, because the failure they guard has no exception to catch.
    Both forks used to hand-wire this and both got it wrong: the connection named
    ``widget.menu`` while the checkboxes were added to ``widget.option_box.menu``,
    and those are two different Menus by design (uitk's option box deliberately does
    not reuse the ``MenuMixin`` context menu). ``connect_multi`` resolves its pattern
    against whatever menu it is handed and iterates the result, so an empty
    resolution connected nothing and warned about nothing — the button simply kept
    whatever text it was last given. Probed live offscreen to be sure:
    ``PushButton().menu is not PushButton().option_box.menu``, and a checkbox added
    to the option box is absent from the context menu.

    Both are now ``sb.text_from`` rules, which take the menu as an explicit argument
    and apply at wire time by construction — so what is pinned here is that neither
    fork drifts back to hand-wiring. The rule's own behaviour is uitk's
    (``test_switchboard_toggle.TestTextFrom``), including the warning a rule now
    raises when it resolves nothing against a container that can never deliver more
    — the diagnostic whose absence let this survive.

    The third defect, Snap's ``get_items("CheckBox")`` (a type NAME resolved against
    QtWidgets, so it matched nothing and filtered every item out), has no pin here:
    the migration removed the state read entirely, so a pin would assert the absence
    of a string this code can no longer produce. It is guarded where it can actually
    recur — ``Menu.get_items`` now reports an unresolvable type name
    (``test_menu.TestMenuGetItems``).
    """

    FORKS = (
        ROOT / "tentacle" / "slots" / "maya" / "transform.py",
        ROOT / "tentacle" / "slots" / "blender" / "transform.py",
    )

    #: Wrapping is a formatter's business, so the source is matched with every run
    #: of whitespace flattened AND the padding inside parens removed — the same call
    #: reads identically whether ruff kept it on one line or split it. The MENU is
    #: matched only in the negative: pinning the positive spelling would fail the
    #: moment a fork adopts the panel-wide ``m = widget.option_box.menu`` idiom.
    CONTEXT_MENU = "widget.menu"
    RULE = "text_from("
    #: Self-labelling buttons per fork: Maya has Constrain + Snap, Blender Constrain.
    EXPECTED = {"maya": 2, "blender": 1}
    #: Same forks, addressable by name for the per-fork assertions below.
    FORKS_BY_NAME = {p.parent.name: p for p in FORKS}

    @staticmethod
    def _flat(path):
        flat = " ".join(path.read_text(encoding="utf-8").split())
        return flat.replace("( ", "(").replace(" )", ")")

    def test_each_fork_declares_every_self_labeller_as_a_rule(self):
        for path in self.FORKS:
            with self.subTest(fork=path.name):
                expected = self.EXPECTED[path.parent.name]
                self.assertEqual(self._flat(path).count(self.RULE), expected)

    def test_no_fork_hand_wires_a_label_off_the_context_menu(self):
        for path in self.FORKS:
            with self.subTest(fork=path.name):
                flat = self._flat(path)
                for call in ("connect_multi(", "text_from("):
                    self.assertFalse(
                        call + self.CONTEXT_MENU in flat,
                        f"{path.name}: {call}{self.CONTEXT_MENU} — that is the "
                        "MenuMixin context menu, an empty Menu here, so the wiring "
                        "binds nothing",
                    )


    def test_no_constraint_checkbox_is_seeded_from_a_literal(self):
        """Every Constrain box must be seeded from the HOST, not a constant.

        A self-labelling button derives its text from these three, so a hardcoded
        seed makes the label lie about the scene: "Make Live" was literal True, so
        a fresh Maya with no constraint and nothing live still read "Constrain: ON",
        and could not read OFF until the box was toggled by hand. The Blender fork
        reads real state for all three; this pins that Maya does too.
        """
        flat = self._flat(self.FORKS_BY_NAME["maya"])
        for name in ("chk024", "chk025", "chk026"):
            seed = flat.split(f'("{name}", "', 1)[1].split(")", 1)[0]
            self.assertFalse(
                seed.rstrip().endswith("True") or seed.rstrip().endswith("False"),
                f"{name} is seeded from a literal ({seed!r}) rather than the host",
            )

@unittest.skipUnless(_MAYA_AVAILABLE, "Requires maya.cmds")
class TestTb002FreezeConnectionStrategy(unittest.TestCase):
    """tb002 maps cmb_connection_strategy.currentIndex() to a string. The
    list order MUST be preserved; an off-by-one would silently switch the
    behavior on any object with connections."""

    def setUp(self):
        cmds.file(new=True, force=True)
        self.instance = transform_module.TransformSlots.__new__(
            transform_module.TransformSlots
        )
        self.instance.sb = _RecordedSb()

        import mayatk as mtk
        self._orig_freeze = mtk.freeze_transforms
        self._orig_store = mtk.store_transforms
        self._orig_restore = mtk.restore_rig_anchors
        self.freeze_calls = []
        mtk.freeze_transforms = lambda *a, **kw: self.freeze_calls.append((a, kw))
        mtk.store_transforms = lambda *a, **kw: None
        mtk.restore_rig_anchors = lambda *a, **kw: None

    def tearDown(self):
        import mayatk as mtk
        mtk.freeze_transforms = self._orig_freeze
        mtk.store_transforms = self._orig_store
        mtk.restore_rig_anchors = self._orig_restore
        cmds.file(new=True, force=True)

    def _widget(self, strategy_index, instance_index=1):
        return _FakeWidget(
            _FakeMenu(
                chk032=_FakeChk(True),
                chk033=_FakeChk(False),
                chk034=_FakeChk(True),
                chk038=_FakeChk(False),  # delete_history
                chk039=_FakeChk(False),  # freeze_children
                chk040=_FakeChk(False),  # from_channel_box
                chk_restore_rig_anchors=_FakeChk(False),
                cmb_center_pivot=_FakeCombo(0),
                cmb_connection_strategy=_FakeCombo(strategy_index),
                cmb_instance_strategy=_FakeCombo(instance_index),
            )
        )

    def _run_with_one_cube(self, widget):
        cube = cmds.polyCube(name="freeze_strat")[0]
        cmds.select(cube)
        self.instance.tb002(widget)

    def test_no_selection_warns(self):
        """tb002 with empty selection warns and doesn't call freeze."""
        cmds.select(clear=True)
        self.instance.tb002(self._widget(0))
        self.assertEqual(self.freeze_calls, [])
        self.assertTrue(self.instance.sb.messages)

    def test_index_0_preserves(self):
        self._run_with_one_cube(self._widget(0))
        self.assertEqual(len(self.freeze_calls), 1)
        self.assertEqual(self.freeze_calls[0][1]["connection_strategy"], "preserve")

    def test_index_1_disconnects(self):
        self._run_with_one_cube(self._widget(1))
        self.assertEqual(self.freeze_calls[0][1]["connection_strategy"], "disconnect")

    def test_index_2_deletes(self):
        self._run_with_one_cube(self._widget(2))
        self.assertEqual(self.freeze_calls[0][1]["connection_strategy"], "delete")

    def test_instance_strategy_routes_by_index(self):
        for index, expected in enumerate(("skip", "preserve", "uninstance")):
            self.freeze_calls.clear()
            self._run_with_one_cube(self._widget(0, instance_index=index))
            self.assertEqual(
                self.freeze_calls[0][1]["instance_strategy"], expected
            )

    def test_store_is_never_disabled(self):
        """Store is no longer optional — the bake history it stamps is what
        Un-Freeze reads back, so an un-checkable option only ever broke it."""
        self._run_with_one_cube(self._widget(0))
        self.assertNotEqual(self.freeze_calls[0][1].get("store", True), False)

    def test_freeze_stamps_bake_history_once(self):
        """End-to-end with the real engine: tb002 leaves restorable bake attrs.

        The panel must NOT call store_transforms alongside the freeze —
        mtk.freeze_transforms stamps the history itself (store=True), and
        doing both double-composes it so Un-Freeze overshoots.
        """
        import mayatk as mtk

        mtk.freeze_transforms = self._orig_freeze  # tearDown restores either way
        cube = cmds.polyCube(name="freeze_store")[0]
        cmds.move(3, 0, 0, cube)
        cmds.select(cube)

        self.instance.tb002(self._widget(0))

        # The widget freezes translate + scale (not rotate), so only those
        # two channels are stamped.
        self.assertTrue(cmds.attributeQuery("original_T_bake", node=cube, exists=True))
        self.assertTrue(cmds.attributeQuery("original_S_bake", node=cube, exists=True))
        self.assertAlmostEqual(
            cmds.getAttr(f"{cube}.original_T_bake")[0][0], 3.0, delta=1e-4
        )


@unittest.skipUnless(_MAYA_AVAILABLE, "Requires maya.cmds")
class TestTb005MoveTo(unittest.TestCase):
    """tb005 Move To: ≥2 ordered selection gate, then routes between
    move-all-to-last and first-to-rest."""

    def setUp(self):
        cmds.file(new=True, force=True)
        self.instance = transform_module.TransformSlots.__new__(
            transform_module.TransformSlots
        )
        self.instance.sb = _RecordedSb()

        import mayatk as mtk
        self._orig = mtk.move_to
        self._orig_scale = mtk.match_scale
        self.calls = []
        self.scale_calls = []
        mtk.move_to = lambda source, target, pivot="center": self.calls.append(
            (source, target, pivot)
        )
        mtk.match_scale = lambda a, b, *args, **kw: self.scale_calls.append((a, b, kw))

    def tearDown(self):
        import mayatk as mtk
        mtk.move_to = self._orig
        mtk.match_scale = self._orig_scale
        cmds.file(new=True, force=True)

    def _menu(self, move_all_to_last, pivot="center", match_scale=False):
        return _FakeMenu(
            chk036=_FakeChk(move_all_to_last),
            cmb005=_FakeCombo(data=pivot),
            chk_match_scale=_FakeChk(match_scale),
        )

    def test_one_object_warns(self):
        """Single selection → message, no move_to call."""
        cube = cmds.polyCube(name="mv_one")[0]
        cmds.select(cube)
        widget = _FakeWidget(self._menu(True))
        self.instance.tb005(widget)
        self.assertEqual(self.calls, [])
        self.assertTrue(self.instance.sb.messages)

    def test_move_all_to_last(self):
        """chk036=True → first N-1 objects move to last."""
        a = cmds.polyCube(name="mv_a")[0]
        b = cmds.polyCube(name="mv_b")[0]
        c = cmds.polyCube(name="mv_c")[0]
        cmds.select([a, b, c])
        widget = _FakeWidget(self._menu(True))
        self.instance.tb005(widget)

        self.assertEqual(len(self.calls), 1)
        source, target, pivot = self.calls[0]
        # source should be [a, b], target = c
        self.assertEqual(list(source), [a, b])
        self.assertEqual(target, c)
        self.assertEqual(pivot, "center")

    def test_first_to_rest(self):
        """chk036=False → first moves to rest (as bounding-box target list)."""
        a = cmds.polyCube(name="mv_a2")[0]
        b = cmds.polyCube(name="mv_b2")[0]
        c = cmds.polyCube(name="mv_c2")[0]
        cmds.select([a, b, c])
        widget = _FakeWidget(self._menu(False))
        self.instance.tb005(widget)

        self.assertEqual(len(self.calls), 1)
        source, target, pivot = self.calls[0]
        # source = a, target = [b, c]
        self.assertEqual(source, a)
        self.assertEqual(list(target), [b, c])

    def test_pivot_forwarded(self):
        """cmb005.currentData() is forwarded to move_to as the pivot option."""
        a = cmds.polyCube(name="mv_pa")[0]
        b = cmds.polyCube(name="mv_pb")[0]
        cmds.select([a, b])
        widget = _FakeWidget(self._menu(True, pivot="xmax"))
        self.instance.tb005(widget)

        self.assertEqual(len(self.calls), 1)
        _source, _target, pivot = self.calls[0]
        self.assertEqual(pivot, "xmax")

    def test_match_scale_off_by_default(self):
        """Unchecked Match Scale → move only, no match_scale call."""
        a = cmds.polyCube(name="mv_da")[0]
        b = cmds.polyCube(name="mv_db")[0]
        cmds.select([a, b])
        widget = _FakeWidget(self._menu(True))
        self.instance.tb005(widget)
        self.assertEqual(self.scale_calls, [])
        self.assertEqual(len(self.calls), 1)

    def test_match_scale_enabled(self):
        """Checked Match Scale → match_scale(source, target) runs alongside the move."""
        a = cmds.polyCube(name="mv_sa")[0]
        b = cmds.polyCube(name="mv_sb")[0]
        cmds.select([a, b])
        widget = _FakeWidget(self._menu(True, match_scale=True))
        self.instance.tb005(widget)

        self.assertEqual(len(self.scale_calls), 1)
        src, tgt, kw = self.scale_calls[0]
        self.assertEqual(list(src), [a])  # source = sel[:-1]
        self.assertEqual(tgt, b)  # target = sel[-1]
        self.assertTrue(kw.get("average"))  # uniform scale, no per-axis distortion
        self.assertEqual(len(self.calls), 1)  # the move still happens


@unittest.skipUnless(_MAYA_AVAILABLE, "Requires maya.cmds")
class TestB001MatchScale(unittest.TestCase):
    """b001 Match Scale requires ≥1 selected object."""

    def setUp(self):
        cmds.file(new=True, force=True)
        self.instance = transform_module.TransformSlots.__new__(
            transform_module.TransformSlots
        )
        self.instance.sb = _RecordedSb()

        import mayatk as mtk
        self._orig = mtk.match_scale
        self.calls = []
        mtk.match_scale = lambda frm, to: self.calls.append((frm, list(to)))

    def tearDown(self):
        import mayatk as mtk
        mtk.match_scale = self._orig
        cmds.file(new=True, force=True)

    def test_no_selection_warns(self):
        cmds.select(clear=True)
        self.instance.b001()
        self.assertEqual(self.calls, [])
        self.assertTrue(self.instance.sb.messages)

    def test_two_objects_dispatches(self):
        a = cmds.polyCube(name="ms_a")[0]
        b = cmds.polyCube(name="ms_b")[0]
        cmds.select([a, b])
        self.instance.b001()
        self.assertEqual(len(self.calls), 1)
        frm, to = self.calls[0]
        self.assertEqual(frm, a)
        self.assertEqual(to, [b])


@unittest.skipUnless(_MAYA_AVAILABLE, "Requires maya.cmds")
class TestSetTransformSnap(unittest.TestCase):
    """setTransformSnap maps state to (snap, snapRelative) booleans across
    move/scale/rotate. Pin the 0/1/2 contract."""

    def setUp(self):
        cmds.file(new=True, force=True)
        self.instance = transform_module.TransformSlots.__new__(
            transform_module.TransformSlots
        )

        self._orig_move = cmds.manipMoveContext
        self._orig_scale = cmds.manipScaleContext
        self._orig_rotate = cmds.manipRotateContext
        self._orig_tex_move = cmds.texMoveContext
        self._orig_tex_scale = cmds.texScaleContext
        self._orig_tex_rotate = cmds.texRotateContext

        self.captured = []

        def fake_move(*a, **kw):
            self.captured.append(("move", a, kw))

        def fake_scale(*a, **kw):
            self.captured.append(("scale", a, kw))

        def fake_rotate(*a, **kw):
            self.captured.append(("rotate", a, kw))

        cmds.manipMoveContext = fake_move
        cmds.manipScaleContext = fake_scale
        cmds.manipRotateContext = fake_rotate
        cmds.texMoveContext = lambda *a, **kw: None
        cmds.texScaleContext = lambda *a, **kw: None
        cmds.texRotateContext = lambda *a, **kw: None

    def tearDown(self):
        cmds.manipMoveContext = self._orig_move
        cmds.manipScaleContext = self._orig_scale
        cmds.manipRotateContext = self._orig_rotate
        cmds.texMoveContext = self._orig_tex_move
        cmds.texScaleContext = self._orig_tex_scale
        cmds.texRotateContext = self._orig_tex_rotate
        cmds.file(new=True, force=True)

    def test_state_0_disables_snap(self):
        """state=0 → snap=False, snapRelative=False."""
        self.instance.setTransformSnap("move", 0)
        kw = self.captured[0][2]
        self.assertFalse(kw["snap"])
        self.assertFalse(kw["snapRelative"])

    def test_state_1_enables_relative(self):
        """state=1 → snap=True, snapRelative=True."""
        self.instance.setTransformSnap("scale", 1)
        kw = self.captured[0][2]
        self.assertTrue(kw["snap"])
        self.assertTrue(kw["snapRelative"])

    def test_state_2_enables_absolute(self):
        """state=2 → snap=True, snapRelative=False."""
        self.instance.setTransformSnap("rotate", 2)
        kw = self.captured[0][2]
        self.assertTrue(kw["snap"])
        self.assertFalse(kw["snapRelative"])

    def test_routes_to_correct_context(self):
        """Each ctx string routes to the matching maya context cmd."""
        self.instance.setTransformSnap("move", 1)
        self.instance.setTransformSnap("scale", 1)
        self.instance.setTransformSnap("rotate", 1)
        # captured[0] = move, [1] = scale, [2] = rotate (one entry each — UV ones
        # are silent stubs).
        self.assertEqual(self.captured[0][0], "move")
        self.assertEqual(self.captured[1][0], "scale")
        self.assertEqual(self.captured[2][0], "rotate")


if __name__ == "__main__":
    unittest.main()
