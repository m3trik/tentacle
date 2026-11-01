#!/usr/bin/python
# coding=utf-8
"""The Blendshape Animator panel's one Slots class, shared by both hosts.

It reaches its host only through ``self.tk`` (the toolkit the entry point set),
so a fake toolkit stands in for ``mtk`` / ``btk`` here and records what the
panel asks of it: plain pytest, no DCC, no widgets loaded. In Maya, the same
class drives the real ``mtk``. The engine API it reads (``has_setup``,
``selected_base``, ``tween_topology``, ``apply_tweens``, ``delete_tweens``,
``select_tweens``) is the libraries': mayatk's ``test_blendshape_animator.py``
(``TestPanelApi``), blendertk's ``test_blendshape_animator.py``.
"""

import inspect
import re
import types
import unittest
from types import SimpleNamespace
from unittest import mock

from _host import MAYA_AVAILABLE, maya_module
from tentacle.slots._slots import Slots
from tentacle.slots.tools.blendshape_animator import (
    COL_STATUS,
    COL_TOPOLOGY,
    BlendshapeAnimatorSlots,
)


def _status(value):
    """An ``ApplyStatus``-like result (both hosts' enum carries ``.value``)."""
    return SimpleNamespace(value=value)


def _tween(mesh, weight=0.5, frame=None):
    return SimpleNamespace(mesh=mesh, weight=weight, target_frame=frame)


def _panel(tk=None, has_setup=True):
    """A Slots instance over a mock ui and a mock toolkit (or *tk*, handed over
    before the panel is built, as ``Slots.tk`` is); the mock toolkit's animator
    is bound to ``base`` -> ``target`` unless *has_setup* is False."""
    sb = mock.MagicMock()
    if tk is not None:
        sb.tk = tk
    else:
        cls = sb.tk.BlendshapeAnimator
        cls.TWEEN_GROUP = "_morphInbetweens_GRP"
        cls.selected_base.return_value = None
        engine = cls.return_value
        engine.has_setup.return_value = has_setup
        engine.base_mesh, engine.target_mesh, engine.blendshape = (
            "base",
            "target",
            "morph_BS",
        )
        # a setup loaded with from_existing is the same kind of engine
        for animator in (engine, cls.from_existing.return_value):
            animator.tween_topology.return_value = (None, [])
            animator.apply_tweens.return_value = []
    return BlendshapeAnimatorSlots(sb), sb


def _option_box(**values):
    """A button whose option-box menu holds *values* (``count`` -> value,
    the line edits -> text, the check boxes -> state)."""
    widget = mock.MagicMock()
    menu = widget.option_box.menu
    for name, value in values.items():
        child = getattr(menu, name)
        child.value.return_value = value
        child.text.return_value = value
        child.isChecked.return_value = value
    return widget


class _PanelCase(unittest.TestCase):
    def setUp(self):
        migrated = Slots._legacy_repeat_last_migrated
        Slots._legacy_repeat_last_migrated = True  # no migration under test
        self.addCleanup(setattr, Slots, "_legacy_repeat_last_migrated", migrated)

    @staticmethod
    def status(sb):
        """The last footer message and its level."""
        call = sb.loaded_ui.blendshape_animator.footer.setText.call_args
        return call.args[0], call.kwargs.get("level", "info")


class TestBlendshapeSetup(_PanelCase):
    def test_the_panel_holds_one_host_animator(self):
        slots, sb = _panel()
        sb.tk.BlendshapeAnimator.assert_called_once_with()
        self.assertIs(slots.animator, sb.tk.BlendshapeAnimator.return_value)

    def test_the_first_bind_waits_for_the_window(self):
        """The selection is read when the window is ready, never while the
        panel loads (a load without a scene, as Blender's handler test does)."""
        slots, sb = _panel()
        sb.loaded_ui.blendshape_animator.run_when_ready.assert_called_once_with(
            slots._on_first_show
        )
        sb.tk.BlendshapeAnimator.selected_base.assert_not_called()

    def test_first_show_follows_the_selection(self):
        slots, sb = _panel(has_setup=False)
        slots._on_first_show()
        mgr = sb.tk.ScriptJobManager.instance.return_value
        mgr.subscribe.assert_called_once_with(
            "SelectionChanged", slots._on_selection_changed, owner=slots
        )
        mgr.connect_cleanup.assert_called_once_with(
            sb.loaded_ui.blendshape_animator, owner=slots
        )
        self.assertIn("Ready.", self.status(sb)[0])

    def test_the_gated_groups_follow_the_setup(self):
        for bound in (True, False):
            with self.subTest(bound=bound):
                slots, sb = _panel(has_setup=bound)
                slots._update_setup_active()
                ui = sb.loaded_ui.blendshape_animator
                for group in ("edit_group", "diagnostics_group", "export_group"):
                    getattr(ui, group).setEnabled.assert_called_once_with(bound)

    def test_a_selected_base_loads_its_setup_once(self):
        slots, sb = _panel()
        cls = sb.tk.BlendshapeAnimator
        self.assertFalse(slots._try_bind_from_selection())  # nothing selected

        cls.selected_base.return_value = "base"  # the setup already bound
        self.assertFalse(slots._try_bind_from_selection())
        cls.from_existing.assert_not_called()

        cls.selected_base.return_value = "other"
        self.assertTrue(slots._try_bind_from_selection())
        cls.from_existing.assert_called_once_with("other")
        self.assertIs(slots.animator, cls.from_existing.return_value)

    def test_a_failed_load_keeps_the_bound_setup(self):
        slots, sb = _panel()
        bound = slots.animator
        sb.tk.BlendshapeAnimator.selected_base.return_value = "other"
        sb.tk.BlendshapeAnimator.from_existing.return_value = None
        self.assertFalse(slots._try_bind_from_selection())
        self.assertIs(slots.animator, bound)

    def test_a_tree_click_does_not_rebind_the_panel(self):
        """Selecting a row selects its tween mesh, which fires the selection
        sync: it must not rebind to the tween (a target, not a base)."""
        slots, sb = _panel()
        seen = []
        sb.tk.BlendshapeAnimator.select_tweens.side_effect = lambda tweens: (
            seen.append(slots._syncing_selection),
            slots._on_selection_changed(),
        )
        tree = sb.loaded_ui.blendshape_animator.tree000
        row = mock.MagicMock()
        row.data.return_value = _tween("tween_w500")
        tree.selectedItems.return_value = [row]
        slots._on_tree_selection_changed()
        self.assertEqual(seen, [True])
        sb.tk.BlendshapeAnimator.selected_base.assert_not_called()
        self.assertFalse(slots._syncing_selection)

    def test_create_setup_reads_the_page(self):
        slots, sb = _panel()
        ui = sb.loaded_ui.blendshape_animator
        ui.s000.value.return_value = 1
        ui.s001.value.return_value = 40
        ui.le000.text.return_value = ""
        slots.animator.create.return_value = True
        slots.b000(None)
        slots.animator.create.assert_called_once_with(
            start_frame=1, end_frame=40, name="morph", test_setup=False
        )
        self.assertEqual(self.status(sb), ("Setup created: base -> target", "success"))

    def test_load_from_existing_replaces_the_animator(self):
        slots, sb = _panel()
        loaded = sb.tk.BlendshapeAnimator.from_existing.return_value
        slots._action_from_existing()
        sb.tk.BlendshapeAnimator.from_existing.assert_called_once_with()
        self.assertIs(slots.animator, loaded)

    def test_recover_setup_is_offered_only_where_the_host_has_it(self):
        slots, sb = _panel()
        for host_has_it in (True, False):
            with self.subTest(host_has_it=host_has_it):
                if not host_has_it:
                    del (
                        sb.tk.BlendshapeAnimator.recover_setup
                    )  # Blender: no node to rebuild
                widget = mock.MagicMock()
                slots.b000_init(widget)
                names = [
                    c.kwargs["setObjectName"]
                    for c in widget.option_box.menu.add.call_args_list
                ]
                expected = ["btn_from_existing"] + (
                    ["btn_recover_setup"] if host_has_it else []
                )
                self.assertEqual(names, expected)


class TestBlendshapeEdit(_PanelCase):
    def test_the_tween_group_default_is_the_hosts(self):
        slots, sb = _panel()
        widget = mock.MagicMock()
        slots.b001_init(widget)
        group = next(
            c
            for c in widget.option_box.menu.add.call_args_list
            if c.kwargs.get("setObjectName") == "group_name"
        )
        self.assertEqual(group.kwargs["setText"], "_morphInbetweens_GRP")

    def test_weights_from_the_csv_field(self):
        slots, sb = _panel()
        ui = sb.loaded_ui.blendshape_animator
        ui.cmb000.currentText.return_value = "Weight-based"
        ui.le001.text.return_value = "0.25, 0.5"
        slots.animator.edit_weight_based.return_value = [_tween("a"), _tween("b")]
        slots.b001(_option_box(group_name="", name_prefix="morph_ib", count=5))
        slots.animator.edit_weight_based.assert_called_once_with(
            weights=[0.25, 0.5], count=3, group_name=None, name_prefix="morph_ib"
        )
        self.assertEqual(
            self.status(sb), ("Added 2/2 weight-based tween(s).", "success")
        )

    def test_an_empty_csv_takes_the_count(self):
        slots, sb = _panel()
        ui = sb.loaded_ui.blendshape_animator
        ui.cmb000.currentText.return_value = "Weight-based"
        ui.le001.text.return_value = ""
        slots.animator.edit_weight_based.return_value = []
        slots.b001(_option_box(group_name="grp", name_prefix="", count=5))
        slots.animator.edit_weight_based.assert_called_once_with(
            weights=None, count=5, group_name="grp", name_prefix=None
        )
        self.assertEqual(self.status(sb)[1], "error")

    def test_an_invalid_csv_warns_and_adds_nothing(self):
        slots, sb = _panel()
        ui = sb.loaded_ui.blendshape_animator
        ui.cmb000.currentText.return_value = "Weight-based"
        ui.le001.text.return_value = "0.25, half"
        slots.b001(_option_box())
        slots.animator.edit_weight_based.assert_not_called()
        self.assertEqual(self.status(sb)[1], "warning")

    def test_a_frame_based_tween(self):
        slots, sb = _panel()
        ui = sb.loaded_ui.blendshape_animator
        ui.cmb000.currentText.return_value = "Frame-based"
        ui.s003.value.return_value = 12
        slots.animator.edit_frame_based.return_value = [_tween("f", frame=12)]
        slots.b001(_option_box(group_name="", name_prefix=""))
        slots.animator.edit_frame_based.assert_called_once_with(
            target_frame=12, group_name=None, name_prefix=None
        )
        self.assertEqual(self.status(sb)[0], "Added frame-based tween at frame 12")

    def test_every_operation_needs_a_setup(self):
        slots, sb = _panel(has_setup=False)
        for name in ("b001", "b003", "b004", "b005", "b006", "b007", "b008"):
            with self.subTest(button=name):
                getattr(slots, name)(_option_box())
                self.assertEqual(
                    self.status(sb),
                    ("Setup not complete — Create or Load first.", "warning"),
                )
        for method in (
            "edit_weight_based",
            "edit_frame_based",
            "diagnose_topology_issues",
            "cleanup_topology_mismatches",
            "recover_animation",
            "apply_tweens",
            "remove_target_for_export",
            "finalize_for_export",
        ):
            getattr(slots.animator, method).assert_not_called()


class TestBlendshapeExport(_PanelCase):
    def test_apply_all_reports_each_status(self):
        slots, sb = _panel()
        slots.animator.apply_tweens.return_value = [
            (_tween("a"), _status("applied")),
            (_tween("b"), _status("skipped_duplicate")),
            (_tween("c"), _status("error")),
        ]
        slots.b006(_option_box(skip_duplicates=False, validate_topology=True))
        slots.animator.apply_tweens.assert_called_once_with(
            None, skip_duplicates=False, validate_topology=True
        )
        self.assertEqual(
            self.status(sb), ("Applied 1/3 — skipped 1, errors 1", "warning")
        )
        self.assertEqual(
            slots._row_status, {"a": "applied", "b": "skipped_duplicate", "c": "error"}
        )

    def test_cleanup_and_finalize_take_the_option_box_flags(self):
        slots, _ = _panel()
        slots.b004(_option_box(delete_mismatched=False, apply_valid_only=True))
        slots.animator.cleanup_topology_mismatches.assert_called_once_with(
            delete_mismatched=False, apply_valid_only=True
        )
        slots.b008(
            _option_box(
                cleanup_scene=True,
                delete_construction_history=False,
                hide_target_mesh=True,
                delete_inbetween_meshes=False,
            )
        )
        slots.animator.finalize_for_export.assert_called_once_with(
            cleanup_scene=True,
            delete_construction_history=False,
            hide_target_mesh=True,
            delete_inbetween_meshes=False,
        )


class TestBlendshapeTree(_PanelCase):
    def _rows(self, slots, sb, rows, base_count=8):
        slots.animator.tween_topology.return_value = (base_count, rows)
        tree = sb.loaded_ui.blendshape_animator.tree000
        tree.reset_mock()
        slots._refresh_tree()
        return [c.args[0] for c in tree.addTopLevelItem.call_args_list]

    def test_each_tween_shows_its_topology_and_status(self):
        slots, sb = _panel()
        slots._row_status["c"] = "error"
        items = self._rows(
            slots,
            sb,
            [
                (_tween("a", 0.25), 8),
                (_tween("b", 0.5, 12), 6),
                (_tween("c", 0.75), None),
            ],
        )
        self.assertEqual(
            [(i.text(0), i.text(1), i.text(2)) for i in items],
            [("a", "0.250", ""), ("b", "0.500", "12"), ("c", "0.750", "")],
        )
        self.assertEqual(
            [i.text(COL_TOPOLOGY) for i in items],
            ["Match", "Mismatch (6 vs 8)", "Unknown"],
        )
        self.assertEqual(
            [i.text(COL_STATUS) for i in items], ["Pending", "Pending", "Error"]
        )

    def test_the_filter_shows_only_mismatches(self):
        slots, sb = _panel()
        slots._show_only_mismatches = True
        items = self._rows(slots, sb, [(_tween("a"), 8), (_tween("b"), 6)])
        self.assertEqual([i.text(0) for i in items], ["b"])

    def test_the_tooltip_counts_the_mismatches(self):
        slots, _ = _panel()
        slots.animator.tween_topology.return_value = (
            8,
            [(_tween("a"), 8), (_tween("b"), 6), (_tween("c"), None)],
        )
        self.assertEqual(
            slots._tree_tooltip_provider(), "3 tween(s), 2 topology mismatch(es)"
        )


class TestBlendshapeStatusFooter(unittest.TestCase):
    """``_set_status`` calls uitk Footer's real API (``setText``) with a valid
    level, and never swallows a wrong-API AttributeError (both libraries'
    panels once called a nonexistent ``footer.set_status`` and downgraded the
    error to a log line, so no status message ever reached the panel)."""

    class _RecordingFooter:
        def __init__(self):
            self.calls = []

        def setText(self, text, level=None):
            self.calls.append((text, level))

    @staticmethod
    def _host(footer):
        return types.SimpleNamespace(
            ui=types.SimpleNamespace(footer=footer),
            animator=types.SimpleNamespace(logger=mock.MagicMock()),
        )

    def test_set_status_calls_settext_with_a_valid_level(self):
        from uitk.widgets.footer import Footer

        host = self._host(self._RecordingFooter())
        BlendshapeAnimatorSlots._set_status(host, "hello")
        self.assertEqual(len(host.ui.footer.calls), 1)
        text, level = host.ui.footer.calls[0]
        self.assertEqual(text, "hello")
        self.assertIn(level, Footer.LEVEL_COLORS)

    def test_set_status_forwards_the_level(self):
        host = self._host(self._RecordingFooter())
        BlendshapeAnimatorSlots._set_status(host, "boom", level="error")
        self.assertEqual(host.ui.footer.calls, [("boom", "error")])

    def test_a_wrong_api_attributeerror_is_not_swallowed(self):
        class _NoSetText:
            pass

        with self.assertRaises(AttributeError):
            BlendshapeAnimatorSlots._set_status(self._host(_NoSetText()), "lost")

    def test_a_deleted_footer_falls_back_to_the_log(self):
        class _Dead:
            def setText(self, text, level=None):
                raise RuntimeError("Internal C++ object already deleted.")

        host = self._host(_Dead())
        BlendshapeAnimatorSlots._set_status(host, "teardown")
        host.animator.logger.info.assert_called_once_with("teardown")

    def test_call_site_levels_are_footer_vocabulary(self):
        from uitk.widgets.footer import Footer

        from tentacle.slots.tools import blendshape_animator

        levels = set(
            re.findall(r'level="(\w+)"', inspect.getsource(blendshape_animator))
        )
        self.assertTrue(levels, "no levelled call sites found")
        self.assertTrue(
            levels.issubset(set(Footer.LEVEL_COLORS)),
            f"unknown footer levels: {levels - set(Footer.LEVEL_COLORS)}",
        )
        self.assertNotIn("footer.set_status", inspect.getsource(blendshape_animator))


@unittest.skipUnless(MAYA_AVAILABLE, "drives the real mtk; runs in a fresh Maya")
class TestBlendshapeAnimatorPanelInMaya(_PanelCase):
    def setUp(self):
        super().setUp()
        self.cmds = maya_module("maya.cmds")
        self.cmds.file(new=True, force=True)
        self.mtk = maya_module("mayatk")

    def test_create_add_apply_and_rebind_from_the_selection(self):
        cmds = self.cmds
        base = cmds.polySphere(name="bpBase")[0]
        target = cmds.polySphere(name="bpTarget")[0]
        cmds.move(2, 0, 0, target)
        cmds.select(base, target)

        slots, sb = _panel(tk=self.mtk)
        ui = sb.loaded_ui.blendshape_animator
        ui.s000.value.return_value = 1
        ui.s001.value.return_value = 20
        ui.le000.text.return_value = ""
        slots.b000(None)
        self.assertTrue(slots.animator.has_setup(), self.status(sb))

        ui.cmb000.currentText.return_value = "Weight-based"
        ui.le001.text.return_value = "0.5"
        slots.b001(_option_box(group_name="", name_prefix=""))
        base_count, rows = slots.animator.tween_topology()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][1], base_count)

        slots.b006(_option_box(skip_duplicates=True, validate_topology=False))
        self.assertNotEqual(self.status(sb)[1], "error")

        # A fresh panel picks the setup up from the selected base mesh.
        cmds.select(base)
        fresh, _ = _panel(tk=self.mtk)
        self.assertTrue(fresh._try_bind_from_selection())
        self.assertEqual(fresh.animator.base_mesh, base)
        self.assertTrue(fresh.animator.has_setup())


if __name__ == "__main__":
    unittest.main()
