#!/usr/bin/python
# coding=utf-8
"""The Material Updater panel's one Slots class, shared by both hosts.

It reaches its host only through ``self.tk`` (the toolkit the entry point set)
and composes the host's ``MatUpdater`` engine, so a fake toolkit stands in for
``mtk`` / ``btk`` here and records what the panel asks of it: plain pytest, no
DCC, no widgets loaded. In Maya, the same class drives the real ``mtk``. The
scope resolvers and choices it calls (``selected_materials``,
``materials_using_textures``, ``shader_type_choices``, ``TRANSFER_MODES``,
``texture_root``) are tested in mayatk's ``test_mat_updater.py`` and
blendertk's ``test_mat_anim_utils.py``.

The dry run / Apply suite moved here from mayatk's ``test_mat_updater.py``
with the panel.
"""

import unittest
from unittest import mock

import pythontk as ptk

from _host import MAYA_AVAILABLE, maya_module
from tentacle.slots._slots import Slots
from tentacle.slots.tools.mat_updater import MatUpdaterSlots

#: mayatk's retype targets; Blender's engine has none.
MAYA_TARGETS = [
    ("Stingray PBS", "stingray"),
    ("Standard Surface", "standard_surface"),
    ("OpenPBR", "open_pbr"),
]


class _FakeButton:
    """Enough QPushButton for the footer's Apply affordance."""

    def __init__(self):
        self._visible = True
        self.callback = None

    def setVisible(self, state):
        self._visible = bool(state)

    def isVisible(self):
        return self._visible

    def click(self):
        if self.callback is not None:
            self.callback()


class _FakeFooter:
    def __init__(self):
        self.button = None
        self.status = None

    def add_action_button(self, text="", icon_name=None, tooltip="", callback=None):
        self.button = _FakeButton()
        self.button.callback = callback
        return self.button

    def setText(self, text, level=None):
        self.status = (text, level)


def _panel(
    mode="All Scene Materials",
    dry_run=True,
    raises=False,
    shader_types=MAYA_TARGETS,
    transfer_modes=("copy", "move"),
    shader_type=None,
    transfer="none",
    move_to="",
    scope=("mat_a",),
    tk=None,
):
    """A Slots instance over a mock ui and a mock toolkit (or *tk*, handed over
    before the panel is built, as ``Slots.tk`` is); returns it and the
    switchboard. ``slots.calls`` records each ``update_materials`` call."""
    sb = mock.MagicMock()
    if tk is not None:
        sb.tk = tk
    else:
        engine = sb.tk.MatUpdater.return_value
        engine.shader_type_choices.return_value = list(shader_types)
        engine.TRANSFER_MODES = tuple(transfer_modes)
        engine.texture_root.return_value = "C:/proj/sourceimages"
        engine.selected_materials.return_value = list(scope)
        engine.materials_using_textures.return_value = list(scope)
    ui = sb.loaded_ui.mat_updater
    ui.footer = _FakeFooter()
    ui.b001 = _FakeButton()
    ui.cmb001.currentText.return_value = "PBR Metallic/Roughness"
    menu = ui.header.menu
    menu.cmb_selection_mode.currentText.return_value = mode
    menu.txt_move_to.text.return_value = move_to
    menu.chk_dry_run.isChecked.return_value = dry_run
    menu.cmb_shader_type.currentData.return_value = shader_type
    menu.cmb_transfer_mode.currentData.return_value = transfer
    menu.cmb_missing_maps.currentData.return_value = ptk.MapRegistry.MISSING_SKIP
    menu.chk_input_fallbacks.isChecked.return_value = True
    menu.chk_output_fallbacks.isChecked.return_value = True
    menu.chk_discover_sourceimages.isChecked.return_value = False

    slots = MatUpdaterSlots(sb)
    ui.b001.callback = slots.b001  # what the dispatcher runs on a click
    slots.calls = []

    def _update(**kwargs):
        slots.calls.append(kwargs)
        if raises:
            raise RuntimeError("boom")
        return {}

    # An instance attribute: shadows the real engine's classmethod too.
    slots.engine.update_materials = _update
    return slots, sb


def _header(slots):
    """Run ``header_init`` over a mock header; returns ``{objectName: widget}``
    for what it added, and the header."""
    header = mock.MagicMock()
    added = {}

    def _add(kind, **kwargs):
        widget = mock.MagicMock()
        added[kwargs.get("setObjectName") or kind] = widget
        return widget

    header.menu.add.side_effect = _add
    slots.header_init(header)
    return added, header


def _menu_kwargs(header, object_name):
    """The keyword arguments ``header.menu.add`` was given for *object_name*."""
    for call in header.menu.add.call_args_list:
        if call.kwargs.get("setObjectName") == object_name:
            return call.kwargs
    raise AssertionError(f"no {object_name} in the header menu")


class _PanelCase(unittest.TestCase):
    def setUp(self):
        migrated = Slots._legacy_repeat_last_migrated
        Slots._legacy_repeat_last_migrated = True  # no migration under test
        self.addCleanup(setattr, Slots, "_legacy_repeat_last_migrated", migrated)


class TestMatUpdaterComposition(_PanelCase):
    def test_the_engine_is_composed_and_its_log_streams_into_the_panel(self):
        """Composed, not inherited. ``update_materials`` is a classmethod that
        logs through the engine's class logger, so that is the one mirrored."""
        slots, sb = _panel()
        sb.tk.MatUpdater.assert_called_once_with()
        self.assertIs(slots.logger, slots.engine.logger)
        slots.logger.setup_logging_redirect.assert_called_once_with(
            sb.loaded_ui.mat_updater.txt001
        )
        self.assertFalse(hasattr(MatUpdaterSlots, "update_materials"))

    def test_the_intro_names_the_texture_folder(self):
        slots, sb = _panel()
        intro = sb.loaded_ui.mat_updater.txt001.setText.call_args.args[0]
        self.assertTrue(intro.startswith(MatUpdaterSlots.msg_intro))
        self.assertIn("C:/proj/sourceimages", intro)

    def test_no_texture_folder_is_just_the_intro(self):
        for answer in ("", RuntimeError("no project")):
            with self.subTest(answer=answer):
                sb = mock.MagicMock()
                engine = sb.tk.MatUpdater.return_value
                if isinstance(answer, Exception):
                    engine.texture_root.side_effect = answer
                else:
                    engine.texture_root.return_value = answer
                MatUpdaterSlots(sb)
                sb.loaded_ui.mat_updater.txt001.setText.assert_called_with(
                    MatUpdaterSlots.msg_intro
                )

    def test_log_links_dispatch_through_the_host(self):
        slots, sb = _panel()
        slots._on_log_link_clicked("action://select?node=mat_a")
        sb.tk.UiUtils.dispatch_log_link.assert_called_once_with(
            "action://select?node=mat_a", slots.logger
        )


class TestMatUpdaterRun(_PanelCase):
    def test_the_config_carries_the_panels_options(self):
        slots, sb = _panel(dry_run=False, transfer="copy", move_to="optimized")
        slots.b001()
        self.assertEqual(len(slots.calls), 1)
        call = slots.calls[0]
        self.assertEqual(
            call["config"],
            {
                "preset": "PBR Metallic/Roughness",
                "move_to_folder": "optimized",
                "missing_map_rule": ptk.MapRegistry.MISSING_SKIP,
                "use_input_fallbacks": True,
                "use_output_fallbacks": True,
                "discover_sourceimages": False,
                "transfer_mode": "copy",
                "dry_run": False,
            },
        )
        self.assertIsNone(call["materials"])  # All Scene Materials
        self.assertIs(call["verbose"], True)
        self.assertIsNone(call["shader_type"])
        self.assertIs(call["progress_callback"], sb.progress_adapter.return_value)

    def test_use_existing_folders_writes_nowhere_new(self):
        slots, _ = _panel(dry_run=False, transfer="none", move_to="optimized")
        slots.b001()
        config = slots.calls[0]["config"]
        self.assertEqual(config["transfer_mode"], "none")
        self.assertIsNone(config["move_to_folder"])

    def test_a_host_without_a_transfer_step_writes_to_the_output_folder(self):
        """Blender: no transfer mode is passed, and a stale "Use Existing
        Folders" setting cannot blank the Output Folder."""
        slots, _ = _panel(
            dry_run=False, transfer_modes=(), transfer="none", move_to="optimized"
        )
        slots.b001()
        config = slots.calls[0]["config"]
        self.assertNotIn("transfer_mode", config)
        self.assertEqual(config["move_to_folder"], "optimized")

    def test_selected_objects_is_the_engines_scope(self):
        slots, sb = _panel(mode="Selected Objects", shader_type="stingray")
        slots.b001()
        engine = sb.tk.MatUpdater.return_value
        engine.selected_materials.assert_called_once_with(shader_type="stingray")
        self.assertEqual(slots.calls[0]["materials"], ["mat_a"])
        self.assertEqual(slots.calls[0]["shader_type"], "stingray")

    def test_an_empty_scope_runs_nothing(self):
        """The engine said why (nothing selected, no supported type)."""
        slots, _ = _panel(mode="Selected Objects", scope=())
        slots.b001()
        self.assertEqual(slots.calls, [])

    def test_browse_picks_textures_starting_in_the_texture_folder(self):
        slots, sb = _panel(mode="Browse...")
        sb.file_dialog.return_value = ["C:/textures/wall_Base_Color.png"]
        slots.b001()
        kwargs = sb.file_dialog.call_args.kwargs
        self.assertEqual(kwargs["start_dir"], "C:/proj/sourceimages")
        self.assertIs(kwargs["allow_multiple"], True)
        sb.tk.MatUpdater.return_value.materials_using_textures.assert_called_once_with(
            ["C:/textures/wall_Base_Color.png"], shader_type=None
        )
        self.assertEqual(slots.calls[0]["materials"], ["mat_a"])

    def test_browse_cancelled_or_unused_textures_run_nothing(self):
        slots, sb = _panel(mode="Browse...")
        sb.file_dialog.return_value = []
        slots.b001()
        self.assertEqual(slots.calls, [])
        sb.tk.MatUpdater.return_value.materials_using_textures.assert_not_called()

        slots, sb = _panel(mode="Browse...", scope=())
        sb.file_dialog.return_value = ["C:/textures/ghost.png"]
        slots.b001()
        self.assertEqual(slots.calls, [])
        self.assertIn("No supported materials", slots.logger.warning.call_args.args[0])

    def test_a_host_with_nothing_to_retype_never_passes_a_shader_type(self):
        """Blender: no targets, so even a stale combo value stays out."""
        slots, sb = _panel(
            mode="Selected Objects", shader_types=[], shader_type="stingray"
        )
        slots.b001()
        sb.tk.MatUpdater.return_value.selected_materials.assert_called_once_with(
            shader_type=None
        )
        self.assertIsNone(slots.calls[0]["shader_type"])

    def test_a_failed_run_is_reported_not_raised(self):
        slots, _ = _panel(dry_run=False, raises=True)
        slots.b001()
        self.assertIn("Material update failed", slots.logger.error.call_args.args[0])

    def test_update_is_cancelable(self):
        """Its own Esc / stall dialog: the dispatcher reads this mark."""
        self.assertEqual(MatUpdaterSlots.b001._cancelable_meta["timeout"], 300)


class TestMatUpdaterDryRunArmsApply(_PanelCase):
    """The footer's Apply button: what arms it, and what it commits.

    The value the button carries is that the applied run is the *preview's own
    call* with ``dry_run`` off -- same materials, same options -- so what the
    report on screen describes is what gets written. These pin that, plus the
    three ways a plan must go stale: a failed preview, a new run, and a change
    of selection mode.
    """

    def test_a_dry_run_arms_the_footer_button(self):
        slots, _ = _panel(dry_run=True)
        slots.b001()

        self.assertEqual(len(slots.calls), 1)
        self.assertIs(slots.calls[0]["config"]["dry_run"], True)
        self.assertTrue(slots._apply_btn.isVisible())
        self.assertIsNotNone(slots._pending)
        self.assertEqual(slots.ui.footer.status[1], "warning")

    def test_a_live_run_never_arms(self):
        slots, _ = _panel(dry_run=False)
        slots.b001()

        self.assertEqual(len(slots.calls), 1)
        self.assertIs(slots.calls[0]["config"]["dry_run"], False)
        self.assertFalse(slots._apply_btn.isVisible())
        self.assertIsNone(slots._pending)

    def test_apply_commits_the_previewed_call_with_dry_run_off(self):
        slots, _ = _panel(dry_run=True)
        slots.b001()
        slots._apply_dry_run()

        self.assertEqual(len(slots.calls), 2)
        preview, commit = slots.calls
        self.assertIs(preview["config"]["dry_run"], True)
        self.assertIs(commit["config"]["dry_run"], False)
        # Everything BUT dry_run is the preview's, so the commit is the plan
        # that was reported rather than a fresh read of the panel.
        self.assertEqual(
            {k: v for k, v in preview["config"].items() if k != "dry_run"},
            {k: v for k, v in commit["config"].items() if k != "dry_run"},
        )
        self.assertEqual(preview["materials"], commit["materials"])
        # And it disarms: the plan has been spent.
        self.assertFalse(slots._apply_btn.isVisible())
        self.assertIsNone(slots._pending)
        self.assertIsNone(slots._committing)
        self.assertEqual(slots.ui.footer.status, ("", None))

    def test_a_press_during_the_commit_starts_a_new_run(self):
        """The commit pumps the event loop, so a second press re-enters b001.

        ``_apply_dry_run`` clears the carrier in a ``finally`` that has not run
        while the commit is in flight, so the carrier has to be consumed where
        ``b001`` READS it -- otherwise the re-entrant press replays the plan
        that is already running instead of starting a run of its own.
        """
        slots, _ = _panel(dry_run=True)
        slots.b001()  # arm

        reentered = []

        def _reenter(**kwargs):
            slots.calls.append(kwargs)
            if len(slots.calls) == 2:  # we are inside the commit
                reentered.append(True)
                slots.b001()
            return {}

        slots.engine.update_materials = _reenter
        slots._apply_dry_run()

        self.assertTrue(reentered, "the probe never re-entered b001")
        self.assertEqual(len(slots.calls), 3, "expected preview, commit, new run")
        self.assertIs(slots.calls[1]["config"]["dry_run"], False, "the commit")
        # Dry Run is still ticked, so a FRESH read of the panel previews again.
        # A replay of the committed plan would read False here.
        self.assertIs(slots.calls[2]["config"]["dry_run"], True, "a new preview")

    def test_apply_commits_the_selection_as_it_was_previewed(self):
        """The frozen list, not a re-read -- the selection may have moved on."""
        slots, sb = _panel(mode="Selected Objects", dry_run=True)
        engine = sb.tk.MatUpdater.return_value
        engine.selected_materials.side_effect = [["previewed_mat"], ["other_mat"]]
        slots.b001()
        self.assertEqual(slots.calls[0]["materials"], ["previewed_mat"])

        slots._apply_dry_run()  # the artist has moved on meanwhile

        self.assertEqual(slots.calls[1]["materials"], ["previewed_mat"])
        self.assertEqual(engine.selected_materials.call_count, 1)

    def test_a_failed_preview_leaves_the_button_disarmed(self):
        """A run that raised must not offer to commit itself."""
        slots, _ = _panel(dry_run=True, raises=True)
        slots.b001()  # the panel reports the failure; it must not propagate

        self.assertEqual(len(slots.calls), 1)
        self.assertFalse(slots._apply_btn.isVisible())
        self.assertIsNone(slots._pending)

    def test_a_new_run_supersedes_the_armed_plan(self):
        slots, _ = _panel(dry_run=True)
        slots.b001()
        self.assertTrue(slots._apply_btn.isVisible())

        slots.ui.header.menu.chk_dry_run.isChecked.return_value = False
        slots.b001()  # a live run of its own, not the armed plan

        self.assertEqual(len(slots.calls), 2)
        self.assertIs(slots.calls[1]["config"]["dry_run"], False)
        self.assertFalse(slots._apply_btn.isVisible())
        self.assertIsNone(slots._pending)

    def test_an_aborted_run_clears_the_report_and_the_plan(self):
        """An empty scope ("Nothing selected.") is a new run: it supersedes the
        last preview."""
        slots, sb = _panel(dry_run=True)
        slots.b001()
        txt001 = sb.loaded_ui.mat_updater.txt001
        cleared_after_preview = txt001.clear.call_count

        menu = slots.ui.header.menu
        menu.cmb_selection_mode.currentText.return_value = "Selected Objects"
        sb.tk.MatUpdater.return_value.selected_materials.return_value = []
        slots.b001()  # aborts before the engine runs

        self.assertEqual(len(slots.calls), 1)  # nothing ran
        self.assertGreater(txt001.clear.call_count, cleared_after_preview)
        self.assertFalse(slots._apply_btn.isVisible())
        self.assertIsNone(slots._pending)

    def test_changing_the_selection_mode_disarms(self):
        """The plan was built over the old mode's material set."""
        slots, _ = _panel(dry_run=True)
        slots.b001()
        self.assertTrue(slots._apply_btn.isVisible())

        slots._disarm_apply("Selected Objects")  # what the combo's signal calls

        self.assertFalse(slots._apply_btn.isVisible())
        self.assertIsNone(slots._pending)

    def test_apply_without_a_plan_is_a_no_op(self):
        slots, _ = _panel(dry_run=True)
        slots._apply_dry_run()
        self.assertEqual(slots.calls, [])


class TestMatUpdaterHeader(_PanelCase):
    def test_the_selection_modes_in_order_and_a_change_disarms(self):
        """The combo saves its index; a new mode stales an armed preview."""
        slots, _ = _panel()
        added, header = _header(slots)
        self.assertEqual(
            _menu_kwargs(header, "cmb_selection_mode")["addItems"],
            ["Selected Objects", "All Scene Materials", "Browse..."],
        )
        added["cmb_selection_mode"].currentTextChanged.connect.assert_called_once_with(
            slots._disarm_apply
        )

    def test_the_shader_type_combo_lists_the_hosts_retype_targets(self):
        slots, _ = _panel()
        added, _ = _header(slots)
        self.assertEqual(
            [c.args for c in added["cmb_shader_type"].addItem.call_args_list],
            [("Shader: Keep Current Type", None)]
            + [(f"Shader: {label}", key) for label, key in MAYA_TARGETS],
        )

    def test_no_shader_type_where_there_is_nothing_to_retype_to(self):
        slots, _ = _panel(shader_types=[])
        added, _ = _header(slots)
        self.assertNotIn("cmb_shader_type", added)

    def test_transfer_mode_is_offered_where_the_host_transfers_source_files(self):
        for modes, enabled in ((("copy", "move"), True), ((), False)):
            with self.subTest(modes=modes):
                slots, _ = _panel(transfer_modes=modes)
                added, header = _header(slots)
                transfer = added["cmb_transfer_mode"]
                # The items stay on both hosts: the saved index means the same.
                self.assertEqual(
                    [c.args for c in transfer.addItem.call_args_list],
                    [
                        ("Copy All to Output", "copy"),
                        ("Move All to Output", "move"),
                        ("Use Existing Folders", "none"),
                    ],
                )
                transfer.setEnabled.assert_called_once_with(enabled)
                self.assertEqual(transfer.currentIndexChanged.connect.called, enabled)

    def test_the_options_keep_their_saved_names(self):
        slots, _ = _panel()
        added, header = _header(slots)
        for name in (
            "cmb_selection_mode",
            "chk_dry_run",
            "cmb_shader_type",
            "cmb_missing_maps",
            "chk_input_fallbacks",
            "chk_output_fallbacks",
            "chk_discover_sourceimages",
            "cmb_transfer_mode",
            "txt_move_to",
        ):
            self.assertIn(name, added)
        header.set_help_text.assert_called_once()


@unittest.skipUnless(MAYA_AVAILABLE, "drives the real mtk; runs in a fresh Maya")
class TestMatUpdaterPanelInMaya(_PanelCase):
    def setUp(self):
        super().setUp()
        self.cmds = maya_module("maya.cmds")
        self.cmds.file(new=True, force=True)
        self.mtk = maya_module("mayatk")

    def _assigned_standard_surface(self, name):
        """A standardSurface on its own plane -- a material the run accepts."""
        cmds = self.cmds
        mat = cmds.shadingNode("standardSurface", asShader=True, name=name)
        sg = cmds.sets(
            renderable=True, noSurfaceShader=True, empty=True, name=f"{name}SG"
        )
        cmds.connectAttr(f"{mat}.outColor", f"{sg}.surfaceShader", force=True)
        plane = cmds.polyPlane(name=f"{name}_geo", constructionHistory=False)[0]
        cmds.sets(plane, edit=True, forceElement=sg)
        return mat, plane

    def test_the_real_engine_is_composed(self):
        slots, _ = _panel(tk=self.mtk)
        self.assertIsInstance(slots.engine, self.mtk.MatUpdater)
        self.assertIs(slots.logger, self.mtk.MatUpdater.logger)

    def test_the_header_offers_the_converters_targets_and_the_transfer(self):
        slots, _ = _panel(tk=self.mtk)
        added, _ = _header(slots)
        self.assertEqual(
            [c.args[1] for c in added["cmb_shader_type"].addItem.call_args_list],
            [None] + list(self.mtk.ShaderConverter.TARGETS),
        )
        added["cmb_transfer_mode"].setEnabled.assert_called_once_with(True)

    def test_apply_commits_the_selection_as_it_was_previewed(self):
        """The frozen list, not a re-read -- the selection may have moved on."""
        first, first_geo = self._assigned_standard_surface("previewed_mat")
        second, second_geo = self._assigned_standard_surface("other_mat")

        slots, _ = _panel(mode="Selected Objects", dry_run=True, tk=self.mtk)
        self.cmds.select(first_geo, replace=True)
        slots.b001()
        previewed = list(slots.calls[0]["materials"])
        self.assertEqual(previewed, [first])

        self.cmds.select(second_geo, replace=True)  # the artist moves on
        slots._apply_dry_run()

        self.assertEqual(slots.calls[1]["materials"], previewed)
        self.assertNotIn(second, slots.calls[1]["materials"])

    def test_nothing_selected_aborts_before_the_engine_runs(self):
        slots, _ = _panel(mode="Selected Objects", dry_run=False, tk=self.mtk)
        self.cmds.select(clear=True)
        with self.assertLogs(self.mtk.MatUpdater.logger, level="WARNING") as logs:
            slots.b001()
        self.assertEqual(slots.calls, [])
        self.assertIn("Nothing selected", logs.output[0])


if __name__ == "__main__":
    unittest.main()
