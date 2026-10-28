#!/usr/bin/python
# coding=utf-8
"""The Render Effects panel's one Slots class, shared by both hosts.

It reaches its host only through ``self.tk``, so a fake toolkit stands in for
``mtk`` / ``btk`` and records what the panel asks of ``RenderEffects`` -- the
selection and channels it reads, the keys and colours it writes, the overlay it
pushes -- with each page's fields stubbed: plain Python, no DCC. The ``.ui`` is
read as XML. ``TestRenderEffectsPanelLoaded`` builds the real pages through a
real Switchboard over a fake toolkit holding a pure ``ptk.ShotStore`` (offscreen
Qt): the recipe binding, the folds, the window fit, the focus. In Maya the same
class drives the real ``mtk`` against a scene. The host side
(``selected_objects``, ``has_channel``, ``select_objects``) is the libraries':
mayatk's and blendertk's ``test_render_opacity.py``.
"""

import os
import re
import types
import unittest
import xml.etree.ElementTree as ET
from unittest import mock

import pythontk as ptk

import tentacle
from _host import MAYA_AVAILABLE, maya_module, qt_widgets_available
from tentacle.slots._slots import Slots
from tentacle.slots.tools.render_effects import CREATE, REVISE, RenderEffectsSlots

cmds = maya_module("maya.cmds")
mtk = maya_module("mayatk")

UI_PATH = os.path.join(
    os.path.dirname(tentacle.__file__), "ui", "tools", "render_effects.ui"
)

#: The colour row's stand-in: what a decided pair reads back (bright, dim).
DECIDED = ((0.2, 0.5, 1.0), (0.0, 0.0, 0.0))


def _panel(tk=None, shown=1):
    """A Slots instance over a mock ui and a fake toolkit (or *tk*, handed over
    before the panel is built, as ``Slots.tk`` is), showing page *shown*. The
    fake host sees an empty scene, the default recipe, 30 fps, frame 10."""
    sb = mock.MagicMock()
    if tk is not None:
        sb.tk = tk
    else:
        effects = sb.tk.RenderEffects
        effects.selected_objects.return_value = []
        effects.has_channel.return_value = False
        effects.scene_recipe.return_value = ptk.EffectRecipe()
        effects.objects_with_channel.return_value = []
        effects.channel_color_stops.return_value = {}
        sb.tk.AudioUtils.get_fps.return_value = 30.0
        sb.tk.AnimUtils.get_current_frame.return_value = 10.0
    # Real widgets take a real tooltip.
    sb.tooltip.fmt = lambda **_kwargs: "tip"
    ui = sb.loaded_ui.render_effects
    ui.header.menu.chk_last_selected.isChecked.return_value = False
    stack = ui.stk_effects
    stack.count.return_value = len(RenderEffectsSlots.PAGES)
    stack.currentIndex.return_value = shown
    # The stack shows what it is set to, as a QStackedWidget does.
    stack.setCurrentIndex.side_effect = lambda index: setattr(
        stack.currentIndex, "return_value", index
    )
    ui.footer.statusText.return_value = ""
    slots = RenderEffectsSlots(sb)
    # The colour row is the tool's only colour editor; stubbed rather than
    # built: what belongs here is the panel's READING of it.
    slots._pulse_ramp = mock.MagicMock()
    slots._pulse_ramp.decided.return_value = DECIDED
    return slots, sb, ui


def _select(sb, objects, carrying=None):
    """Have the fake host report *objects* selected (the lead last) and the
    ones in ``carrying[channel]`` carrying that channel."""
    carrying = carrying or {}
    effects = sb.tk.RenderEffects
    effects.selected_objects.side_effect = lambda last_only=False: list(
        objects[-1:] if last_only else objects
    )
    effects.has_channel.side_effect = lambda obj, channel: (
        obj in carrying.get(channel, ())
    )


def _set_mode(slots, mode, channels=("opacity", "highlight")):
    """Put *channels*' pages in *mode* without building them: the layout IS
    the mode, so this states it where the panel reads it."""
    for channel in channels:
        slots._mode_fields[channel] = types.SimpleNamespace(mode=mode)


def _fade_page(slots, ends_at_cursor=False, direction="in", delete_vis=False):
    """The fade page's own fields; the length is the recipe's."""
    page = types.SimpleNamespace(
        chk000=mock.MagicMock(),
        cmb_direction=mock.MagicMock(),
        chk_delete_vis_keys=mock.MagicMock(),
    )
    page.chk000.isChecked.return_value = ends_at_cursor
    page.cmb_direction.currentData.return_value = direction
    page.chk_delete_vis_keys.isChecked.return_value = delete_vis
    slots._pages["opacity"] = page
    return page


def _pulse_page(slots, seconds=4.0, ends_at_cursor=False):
    """The pulse page's own fields (SECONDS); the cadence is the recipe's."""
    page = types.SimpleNamespace(s001=mock.MagicMock(), chk001=mock.MagicMock())
    page.s001.value.return_value = seconds
    page.chk001.isChecked.return_value = ends_at_cursor
    slots._pages["highlight"] = page
    return page


def _said(text):
    """*text* as read: tags dropped."""
    return re.sub(r"<[^>]+>", "", text)


def _resting(ui):
    """The footer's resting line, as read."""
    return _said(ui.footer.setDefaultStatusText.call_args.args[0])


class _PanelCase(unittest.TestCase):
    def setUp(self):
        migrated = Slots._legacy_repeat_last_migrated
        Slots._legacy_repeat_last_migrated = True  # no migration under test
        self.addCleanup(setattr, Slots, "_legacy_repeat_last_migrated", migrated)


# ---------------------------------------------------------------------------
# The fake toolkit
# ---------------------------------------------------------------------------


class TestRenderEffectsPanelSetup(_PanelCase):
    def test_the_selection_job_lives_with_the_window(self):
        """An ephemeral subscription is pruned by the next scene open, which
        left the panel deaf to the selection for the rest of the session."""
        slots, sb, ui = _panel()
        jobs = sb.tk.ScriptJobManager.instance.return_value
        jobs.subscribe.assert_called_once_with(
            "SelectionChanged", slots._on_scene_selection, owner=slots
        )
        self.assertNotIn("ephemeral", jobs.subscribe.call_args.kwargs)
        jobs.connect_cleanup.assert_called_once_with(ui, owner=slots)
        self.assertIs(slots._sel_token, jobs.subscribe.return_value)

    def test_hiding_ends_the_focus_and_showing_refits(self):
        slots, sb, ui = _panel()
        ui.on_hide.connect.assert_called_once_with(slots.unfocus)
        ui.on_show.connect.assert_called_once_with(slots._refit)
        ui.destroyed.connect.assert_called_once()

    def test_the_picker_lists_one_page_per_effect_in_order(self):
        """The picker's index is the stack's: its order is the pages'."""
        slots, sb, ui = _panel()
        widget = mock.MagicMock()
        slots.cmb_effect_init(widget)
        self.assertEqual(
            [c.args for c in widget.addItem.call_args_list],
            [("Opacity Fade", "opacity"), ("Highlight Pulse", "highlight")],
        )
        self.assertEqual(
            [(p[0], p[2], p[3], p[4]) for p in RenderEffectsSlots.PAGES],
            [
                ("opacity", "page_fade", "_key_fade_page", "Key Opacity Fade"),
                ("highlight", "page_pulse", "_key_pulse_page", "Key Highlight Pulse"),
            ],
        )

    def test_the_recipe_fields_are_named(self):
        """Saved names: each recipe field's widget, and its scale."""
        self.assertEqual(
            RenderEffectsSlots.RECIPE_FIELDS,
            (
                ("fade_frames", "s000", 1),
                ("pulse_period", "s002", 1),
                ("pulse_duty", "s003", 100),
                ("pulse_lead_in", "s004", 1),
                ("pulse_lead_out", "s005", 1),
            ),
        )

    def test_the_header_holds_last_selected_only_and_no_colour_window(self):
        """The header button opened a colour window that no longer exists."""
        slots, sb, ui = _panel()
        header = mock.MagicMock()
        slots.header_init(header)
        names = [c.kwargs.get("setObjectName") for c in header.menu.add.call_args_list]
        self.assertIn("chk_last_selected", names)
        self.assertNotIn("b_highlight_color", names)
        header.set_help_text.assert_called_once()

    def test_the_seed_colours_are_the_recipes(self):
        """The colours a pulse seeds from are declared ONCE, in the recipe --
        what create writes too (the libraries' test_render_opacity)."""
        recipe = ptk.EffectRecipe()
        self.assertEqual(RenderEffectsSlots.DEFAULT_BRIGHT, recipe.pulse_bright)
        self.assertEqual(RenderEffectsSlots.DEFAULT_DIM, recipe.pulse_dim)

    def test_the_seed_colours_survive_the_editors_own_round_trip(self):
        """The editor is 8-bit sRGB and the channel linear light, so a seed the
        picker cannot represent comes BACK changed: opening the pulse page in
        Revise and keying would rewrite an authored colour nobody touched. Each
        default is the linear value of its own 8-bit display colour, to the 6
        decimals this tool compares colours to (moved from mayatk's
        ``TestDefaultHighlightColour``)."""
        for name in ("DEFAULT_BRIGHT", "DEFAULT_DIM"):
            seed = getattr(RenderEffectsSlots, name)
            shown = tuple(
                round(c * 255) / 255 for c in ptk.Color.srgb_from_linear(seed)[:3]
            )
            self.assertEqual(
                [round(c, 6) for c in ptk.Color.linear_from_srgb(shown)],
                [round(float(c), 6) for c in seed],
                name,
            )

    def test_a_whole_number_box_takes_the_nearest_whole_number(self):
        """``setValue`` truncates a float: a 0.57 duty is 56.99... percent."""
        box = types.SimpleNamespace
        self.assertEqual(
            RenderEffectsSlots._spin_value(box(value=lambda: 59), 57.0 - 1e-9), 57
        )
        self.assertEqual(
            RenderEffectsSlots._spin_value(box(value=lambda: 15), 12.6), 13
        )
        self.assertEqual(
            RenderEffectsSlots._spin_value(box(value=lambda: 2.86), 2.5), 2.5
        )


class TestRenderEffectsPanelPages(_PanelCase):
    """Each page's build, read off the calls it makes (no widgets)."""

    def _build(self, channel):
        slots, sb, ui = _panel()
        rows = mock.MagicMock()
        slots._pages[channel] = rows
        getattr(slots, slots.BUILDERS[channel])(rows)
        return slots, sb, rows

    def test_each_page_opens_on_create_and_never_restores_its_mode(self):
        for channel in ("opacity", "highlight"):
            with self.subTest(channel=channel):
                slots, sb, rows = self._build(channel)
                mode = rows.add.return_value
                self.assertEqual(
                    rows.add.call_args.kwargs["setObjectName"], f"cmb_mode_{channel}"
                )
                self.assertEqual(
                    [c.args for c in mode.addItem.call_args_list],
                    [("Create", CREATE), ("Revise", REVISE)],
                )
                self.assertIs(mode.restore_state, False)
                rows.add_section.assert_called_once_with(
                    "Settings", setObjectName=f"grp_settings_{channel}"
                )

    def test_the_fade_page_keeps_its_names_and_its_direction_order(self):
        slots, sb, rows = self._build("opacity")
        settings = rows.add_section.return_value
        names = [c.kwargs.get("setObjectName") for c in settings.add.call_args_list]
        self.assertEqual(
            [n for n in names if n],
            ["s000", "chk000", "cmb_direction", "chk_delete_vis_keys"],
        )
        self.assertEqual(
            [c.args for c in settings.add.return_value.addItem.call_args_list],
            [("Fade In", "in"), ("Fade Out", "out"), ("Auto", "auto")],
        )

    def test_revise_hides_only_what_creates_the_channel(self):
        """A fade IS its keys: Revise hides only Delete Visibility Keys, which
        acts when Key GIVES an object the channel."""
        slots, sb, rows = self._build("opacity")
        visibility = sb.FieldVisibility.return_value
        self.assertEqual(
            [c.args for c in visibility.define.call_args_list],
            [(CREATE, ("chk_delete_vis_keys",)), (REVISE, ())],
        )
        visibility.bind.assert_called_once_with(slots._mode_combos["opacity"])

    def test_revise_shows_the_colours_alone(self):
        """Re-timing IS re-keying, and that is Create."""
        slots, sb, rows = self._build("highlight")
        visibility = sb.FieldVisibility.return_value
        defined = dict(c.args for c in visibility.define.call_args_list)
        self.assertEqual(defined[REVISE], ("pulse_colors",))
        self.assertIn("s001", defined[CREATE])
        self.assertIn("pulse_colors", defined[CREATE])
        self.assertEqual(slots._mode_hooks["highlight"], slots._sync_highlight_mode)

    def test_the_previews_run_the_exporters_own_arithmetic(self):
        """The previews cannot drift from what ships: each runs the glTF
        channel's own ``values`` function."""
        channels = ptk.GlbFades.CHANNELS
        slots, sb, rows = self._build("opacity")
        self.assertEqual(
            sb.RampPreview.call_args.kwargs["values"], channels["opacity"].values
        )
        self.assertTrue(sb.RampPreview.call_args.kwargs["linear"])
        slots, sb, rows = self._build("highlight")
        kwargs = sb.ColorRampEditor.call_args.kwargs
        self.assertEqual(kwargs["values"], channels["highlight"].values)
        self.assertEqual(kwargs["labels"], ("Bright", "Dim"))
        self.assertTrue(kwargs["linear"] and kwargs["additive"])
        sb.ColorRampEditor.return_value.stopCommitted.connect.assert_called_once_with(
            slots._on_pulse_color_committed
        )

    def test_the_two_leads_are_linked(self):
        slots, sb, rows = self._build("highlight")
        args, kwargs = sb.link_spinboxes.call_args
        self.assertIs(args[0], slots.ui)
        self.assertEqual(len(args[1]), 2)
        self.assertEqual(kwargs, {"initial": True})


class TestRenderEffectsPanelSelection(_PanelCase):
    def test_last_selected_only_asks_the_host_for_the_lead(self):
        """Maya's lead is the last selected, Blender's the active object: the
        host answers, the panel only says which it wants."""
        slots, sb, ui = _panel()
        ui.header.menu.chk_last_selected.isChecked.return_value = True
        slots._get_selected()
        sb.tk.RenderEffects.selected_objects.assert_called_with(last_only=True)

    def test_what_carries_a_channel_is_the_hosts_answer(self):
        slots, sb, ui = _panel()
        _select(sb, ["lid", "box"], {"highlight": {"lid"}})
        self.assertEqual(slots._carrying("highlight", ["lid", "box"]), ["lid"])
        sb.tk.RenderEffects.has_channel.assert_any_call("box", "highlight")

    def test_the_selection_is_read_once_per_change(self):
        """Every consumer on the selection path asked the same question
        separately: a scene read and a per-object query, several times over."""
        slots, sb, ui = _panel()
        ui.isVisible.return_value = True
        _select(sb, ["lid"])
        slots._mode_combos = {"highlight": mock.MagicMock()}
        _set_mode(slots, REVISE)
        slots._on_selection_changed()
        self.assertEqual(sb.tk.RenderEffects.selected_objects.call_count, 1)

    def test_a_hidden_panel_reads_nothing(self):
        slots, sb, ui = _panel()
        ui.isVisible.return_value = False
        slots._on_selection_changed()
        sb.tk.RenderEffects.selected_objects.assert_not_called()

    def test_a_pick_ends_the_last_report(self):
        slots, sb, ui = _panel()
        ui.isVisible.return_value = True
        ui.footer.statusText.return_value = "Opacity removed from 2 object(s)"
        slots._on_scene_selection()
        ui.footer.setText.assert_called_with("")


class TestRenderEffectsPanelActionRow(_PanelCase):
    def test_key_runs_the_shown_pages_keyer(self):
        for index, keyer in ((0, "_key_fade_page"), (1, "_key_pulse_page")):
            slots, sb, ui = _panel(shown=index)
            setattr(slots, keyer, mock.MagicMock())
            slots.b000()
            getattr(slots, keyer).assert_called_once_with()

    def test_the_action_row_follows_the_shown_page(self):
        """Key's text and Remove's gate are the page on show's -- and the
        manifest's text while focused on that effect."""
        slots, sb, ui = _panel(shown=0)
        _select(sb, ["lid"], {"opacity": {"lid"}})
        slots._sync_actions()
        ui.b000.setText.assert_called_with("Key Opacity Fade")
        ui.btn_remove.setEnabled.assert_called_with(True)

        ui.stk_effects.currentIndex.return_value = 1
        slots._sync_actions()
        ui.b000.setText.assert_called_with("Key Highlight Pulse")
        ui.btn_remove.setEnabled.assert_called_with(False)

        slots._focus = {
            "channel": "highlight",
            "objects": [],
            "apply": lambda: "",
            "apply_text": "Apply to 'Lid' in S01",
            "title": "Lid · S01",
        }
        slots._sync_actions()
        ui.b000.setText.assert_called_with("Apply to 'Lid' in S01")

    def test_a_focused_highlights_key_says_what_each_mode_does(self):
        """In Revise a focused highlight's Key re-colours -- the manifest's
        re-key serves Create only -- yet a mode switch never re-labelled it."""
        slots, sb, ui = _panel()
        slots._focus = {
            "channel": "highlight",
            "objects": [],
            "apply": lambda: "",
            "apply_text": "Apply to 'Lid' in S01",
            "title": "Lid · S01",
        }
        _set_mode(slots, CREATE)
        slots._on_mode_changed("highlight")
        ui.b000.setText.assert_called_with("Apply to 'Lid' in S01")
        _set_mode(slots, REVISE)
        slots._on_mode_changed("highlight")
        ui.b000.setText.assert_called_with("Key Highlight Pulse")


class TestRenderEffectsPanelReadout(_PanelCase):
    """The footer's resting line: what Key is about to do, and to how many."""

    def test_create_counts_the_selection(self):
        slots, sb, ui = _panel()
        _set_mode(slots, CREATE)
        _select(sb, ["lid", "box"])
        slots._update_apply_readout("highlight")
        self.assertEqual(_resting(ui), "Keys a pulse on 2 selected")
        _select(sb, [])
        slots._update_apply_readout("highlight")
        self.assertEqual(_resting(ui), "Needs a selection")

    def test_revise_counts_what_carries_the_channel(self):
        slots, sb, ui = _panel()
        _set_mode(slots, REVISE)
        _select(sb, ["lid", "box"], {"highlight": {"lid"}})
        slots._update_apply_readout("highlight")
        self.assertEqual(_resting(ui), "Re-colours 1 of 2 selected")
        _select(sb, ["box"])
        slots._update_apply_readout("highlight")
        self.assertEqual(_resting(ui), "None of the 1 selected carry highlight")
        _select(sb, [])
        slots._update_apply_readout("highlight")
        self.assertEqual(_resting(ui), "Re-colours every highlight object in the scene")

    def test_the_fade_readout_admits_that_revise_re_keys(self):
        slots, sb, ui = _panel(shown=0)
        _set_mode(slots, REVISE)
        _select(sb, ["lid"], {"opacity": {"lid"}})
        slots._update_apply_readout("opacity")
        self.assertTrue(_resting(ui).startswith("Re-keys the fade"), _resting(ui))

    def test_only_the_shown_page_writes_the_footer(self):
        slots, sb, ui = _panel(shown=0)
        slots._update_apply_readout("highlight")
        ui.footer.setDefaultStatusText.assert_not_called()

    def test_a_focus_rests_on_the_manifests_placement(self):
        slots, sb, ui = _panel()
        slots._focus = {
            "channel": "highlight",
            "objects": [],
            "apply": lambda: "",
            "apply_text": "",
            "title": "Lid <S01>",
        }
        slots._update_apply_readout("highlight")
        said = ui.footer.setDefaultStatusText.call_args.args[0]
        self.assertIn("Lid &lt;S01&gt;", said, "the title is escaped")
        self.assertTrue(_said(said).startswith("Re-keys Lid"))


class TestRenderEffectsPanelTargets(_PanelCase):
    def test_create_reaches_the_whole_selection(self):
        slots, sb, ui = _panel()
        _set_mode(slots, CREATE)
        _select(sb, ["lid", "box"], {"highlight": {"lid"}})
        self.assertEqual(slots._targets("highlight"), ["lid", "box"])

    def test_create_needs_a_selection(self):
        slots, sb, ui = _panel()
        _set_mode(slots, CREATE)
        self.assertIsNone(slots._targets("highlight"))
        self.assertIn("Nothing selected", sb.message_box.call_args.args[0])

    def test_revise_reaches_only_objects_that_carry_the_channel(self):
        """The point of the mode: change this, do not spread it."""
        slots, sb, ui = _panel()
        _set_mode(slots, REVISE)
        _select(sb, ["lid", "box"], {"highlight": {"lid"}})
        self.assertEqual(slots._targets("highlight"), ["lid"])
        _select(sb, ["box"])
        self.assertIsNone(slots._targets("highlight"))
        self.assertIn("Nothing to revise", sb.message_box.call_args.args[0])

    def test_revise_confirms_before_the_whole_scene(self):
        slots, sb, ui = _panel()
        _set_mode(slots, REVISE)
        sb.tk.RenderEffects.objects_with_channel.return_value = ["|lid", "|box"]
        sb.message_box.return_value = "No"
        self.assertIsNone(slots._targets("highlight"))
        self.assertIn("(2)", sb.message_box.call_args.args[0])
        self.assertEqual(sb.message_box.call_args.args[1:], ("Yes", "No"))
        sb.message_box.return_value = "Yes"
        self.assertEqual(slots._targets("highlight"), ["|lid", "|box"])
        sb.tk.RenderEffects.objects_with_channel.assert_called_with("highlight")


class TestRenderEffectsPanelKeying(_PanelCase):
    def _jobs(self, sb):
        return sb.tk.ScriptJobManager.instance.return_value

    def test_key_fade_keys_through_the_host_in_one_undo_step(self):
        slots, sb, ui = _panel(shown=0)
        _set_mode(slots, CREATE)
        _select(sb, ["lid"])
        _fade_page(slots, ends_at_cursor=True, direction="auto", delete_vis=True)
        sb.tk.RenderEffects.scene_recipe.return_value = ptk.EffectRecipe(fade_frames=12)
        sb.tk.AnimUtils.get_current_frame.return_value = 30.0
        sb.tk.RenderEffects.key_fade.return_value = [("lid", "out")]
        slots._key_fade_page()
        sb.tk.RenderEffects.key_fade.assert_called_once_with(
            ["lid"],
            start=18.0,
            end=30.0,
            direction="auto",
            channel="opacity",
            delete_visibility_keys=True,
        )
        sb.tk.CoreUtils.undo_chunk.assert_called_once_with("Key Opacity Fade")
        self._jobs(sb).suppressed.assert_called_with(slots._sel_token)
        ui.footer.setText.assert_called_with("Fade Out: 1 object(s), frames 18–30")

    def test_nothing_selected_opens_no_undo_step(self):
        """The targets (and any confirmation) are settled before the write's
        undo step opens: a refusal leaves nothing in the host's history."""
        slots, sb, ui = _panel(shown=0)
        _set_mode(slots, CREATE)
        _fade_page(slots)
        slots._key_fade_page()
        sb.tk.RenderEffects.key_fade.assert_not_called()
        sb.tk.CoreUtils.undo_chunk.assert_not_called()
        sb.message_box.assert_called_once()

    def test_the_range_starts_on_the_whole_frame_nearest_the_playhead(self):
        slots, sb, ui = _panel()
        sb.tk.AnimUtils.get_current_frame.return_value = 10.5
        self.assertEqual(slots._key_range(12, False), (11.0, 23.0))
        self.assertEqual(slots._key_range(12, True), (-1.0, 11.0))

    def test_a_host_error_is_reported_not_raised(self):
        slots, sb, ui = _panel(shown=0)
        _set_mode(slots, CREATE)
        _select(sb, ["lid"])
        _fade_page(slots)
        sb.tk.RenderEffects.key_fade.side_effect = RuntimeError("locked")
        slots._key_fade_page()
        self.assertEqual(sb.message_box.call_args.args[0], "Error: locked")

    def test_key_pulse_keys_the_recipe_over_the_length(self):
        slots, sb, ui = _panel()
        _set_mode(slots, CREATE)
        _select(sb, ["lid"])
        _pulse_page(slots, seconds=4.0)
        recipe = ptk.EffectRecipe()
        sb.tk.RenderEffects.scene_recipe.return_value = recipe
        sb.tk.RenderEffects.key_pulse.return_value = ["lid"]
        slots._key_pulse_page()
        sb.tk.RenderEffects.key_pulse.assert_called_once_with(
            ["lid"],
            start=10.0,
            end=130.0,
            color=DECIDED[0],
            dim_color=DECIDED[1],
            channel="highlight",
            recipe=recipe,
        )
        sb.tk.CoreUtils.undo_chunk.assert_called_once_with("Key Highlight Pulse")
        self.assertIn(
            "Highlight pulse: 1 object(s), frames 10–130",
            ui.footer.setText.call_args.args[0],
        )

    def test_revise_writes_only_the_ends_decided(self):
        """An artist who only touched Bright must not flatten every Dim."""
        slots, sb, ui = _panel()
        _set_mode(slots, REVISE)
        _select(sb, ["lid"], {"highlight": {"lid"}})
        slots._pulse_ramp.decided.return_value = ((1.0, 0.0, 0.0), None)
        sb.tk.RenderEffects.set_channel_color.return_value = ["lid"]
        slots._key_pulse_page()
        sb.tk.RenderEffects.set_channel_color.assert_called_once_with(
            ["lid"], color=(1.0, 0.0, 0.0), channel="highlight", stop="hi"
        )
        sb.tk.CoreUtils.undo_chunk.assert_called_once_with("Highlight Colour")
        sb.tk.RenderEffects.key_pulse.assert_not_called()

    def test_revise_with_nothing_decided_writes_nothing(self):
        slots, sb, ui = _panel()
        _set_mode(slots, REVISE)
        _select(sb, ["lid"], {"highlight": {"lid"}})
        slots._pulse_ramp.decided.return_value = (None, None)
        slots._key_pulse_page()
        sb.tk.RenderEffects.set_channel_color.assert_not_called()
        self.assertIn("Nothing decided", sb.message_box.call_args.args[0])

    def test_remove_strips_the_shown_channel_in_one_undo_step(self):
        slots, sb, ui = _panel(shown=0)
        _select(sb, ["lid", "box"])
        slots.btn_remove()
        sb.tk.RenderEffects.remove.assert_called_once_with(
            ["lid", "box"], channel="opacity"
        )
        sb.tk.CoreUtils.undo_chunk.assert_called_once_with("Remove Opacity")
        ui.footer.setText.assert_called_with(
            "Opacity removed from 2 object(s): lid, box"
        )

    def test_remove_needs_a_selection(self):
        slots, sb, ui = _panel(shown=0)
        slots.btn_remove()
        sb.tk.RenderEffects.remove.assert_not_called()
        sb.message_box.assert_called_once()

    def test_a_focused_key_runs_the_manifests_re_key(self):
        """From a manifest row Key re-keys where the build places the effect;
        the page's own playhead keying never runs."""
        slots, sb, ui = _panel()
        _set_mode(slots, CREATE)
        apply = mock.MagicMock(return_value="Re-applied Lid's behaviors in S01.")
        slots._focus = {
            "channel": "highlight",
            "objects": ["|Lid"],
            "apply": apply,
            "apply_text": "Apply",
            "title": "Lid · S01",
        }
        slots._key_pulse_page()
        apply.assert_called_once_with()
        sb.tk.RenderEffects.key_pulse.assert_not_called()
        ui.footer.setText.assert_called_with("Re-applied Lid's behaviors in S01.")

    def test_a_focused_revise_still_recolours(self):
        """A highlight's Revise writes colours, not keys: the manifest's re-key
        is not what it means."""
        slots, sb, ui = _panel()
        _set_mode(slots, REVISE)
        _select(sb, ["|Lid"], {"highlight": {"|Lid"}})
        apply = mock.MagicMock()
        slots._focus = {
            "channel": "highlight",
            "objects": ["|Lid"],
            "apply": apply,
            "apply_text": "Apply",
            "title": "Lid · S01",
        }
        slots._key_pulse_page()
        apply.assert_not_called()
        sb.tk.RenderEffects.set_channel_color.assert_called()


class TestRenderEffectsPanelFocus(_PanelCase):
    def _focused(self, carrying=True):
        slots, sb, ui = _panel(shown=0)
        sb.tk.RenderEffects.select_objects.return_value = ["|Red_Door"]
        sb.tk.RenderEffects.has_channel.return_value = carrying
        combo = mock.MagicMock()
        combo.findData.side_effect = lambda mode: {CREATE: 0, REVISE: 1}[mode]
        slots._mode_combos["highlight"] = combo
        slots.focus(
            "highlight",
            ["Red_Door"],
            title="Red_Door · S03",
            apply=lambda: "",
            apply_text="Apply to 'Red_Door' in S03",
        )
        return slots, sb, ui, combo

    def test_focus_selects_through_the_host_and_names_the_object(self):
        """A view of the object, not an edit: the host selects it with no
        undo step (Maya: under undo_disabled; Blender: CoreUtils.select)."""
        slots, sb, ui, combo = self._focused()
        sb.tk.RenderEffects.select_objects.assert_called_once_with(["Red_Door"])
        ui.cmb_effect.setCurrentIndex.assert_called_with(1)
        ui.cmb_effect.setVisible.assert_called_with(False)
        ui.header.setText.assert_called_with("HIGHLIGHT PULSE · RED_DOOR · S03")
        self.assertEqual(slots._focus["objects"], ["|Red_Door"])

    def test_focus_opens_in_revise_only_when_every_object_carries_it(self):
        slots, sb, ui, combo = self._focused(carrying=True)
        combo.setCurrentIndex.assert_called_with(1)
        slots, sb, ui, combo = self._focused(carrying=False)
        combo.setCurrentIndex.assert_called_with(0)

    def test_a_channel_with_no_page_is_refused(self):
        slots, sb, ui = _panel()
        with self.assertRaises(ValueError):
            slots.focus("glow", [])

    def test_unfocus_brings_the_picker_back(self):
        slots, sb, ui, combo = self._focused()
        slots.unfocus()
        self.assertIsNone(slots._focus)
        ui.cmb_effect.setVisible.assert_called_with(True)
        ui.header.setText.assert_called_with("RENDER EFFECTS")
        ui.header.setText.reset_mock()
        slots.unfocus()  # a second hide: nothing to end
        ui.header.setText.assert_not_called()


class TestRenderEffectsPanelWebXr(_PanelCase):
    def _result(self, applied=True):
        return {
            "version": 3,
            "url": "http://127.0.0.1:0/",
            "data_export": [ptk.SceneRecords.VISIBILITY.key] if applied else [],
        }

    def test_the_preview_needs_a_selection(self):
        slots, sb, ui = _panel(shown=0)
        slots.btn_webxr()
        sb.tk.WebXrPreview.assert_not_called()
        self.assertIn("Nothing selected", sb.message_box.call_args.args[0])

    def test_the_fade_is_pushed_as_the_page_stands_and_nothing_is_written(self):
        slots, sb, ui = _panel(shown=0)
        _select(sb, ["lid"])
        _fade_page(slots, direction="in")
        sb.tk.RenderEffects.scene_recipe.return_value = ptk.EffectRecipe(fade_frames=15)
        push = sb.tk.WebXrPreview.return_value.push
        push.return_value = self._result()
        slots.btn_webxr()
        expected = ptk.RampKeys.fade_loop(
            15, hold=RenderEffectsSlots.PREVIEW_HOLD_SECONDS * 30.0, direction="in"
        )
        sb.tk.RenderEffects.preview_channels.assert_called_once_with(
            ["lid"], channel="opacity", keys=expected, colors=None, fps=30.0
        )
        kwargs = push.call_args.kwargs
        self.assertEqual(kwargs["objects"], ["lid"])
        self.assertEqual(kwargs["open_browser"], "auto")
        self.assertIs(
            kwargs["data_export"], sb.tk.RenderEffects.preview_channels.return_value
        )
        sb.tk.ScriptJobManager.instance.return_value.suppressed.assert_called_with(
            slots._sel_token
        )
        for writer in ("key_fade", "key_pulse", "set_channel_color", "remove"):
            getattr(sb.tk.RenderEffects, writer).assert_not_called()
        sb.tk.CoreUtils.undo_chunk.assert_not_called()
        ui.footer.setText.assert_called_with(
            "Opacity preview v3: lid at http://127.0.0.1:0/"
        )

    def test_an_undecided_end_previews_as_the_recipes(self):
        slots, sb, ui = _panel()
        _select(sb, ["lid"])
        _pulse_page(slots, seconds=4.0)
        recipe = ptk.EffectRecipe()
        sb.tk.RenderEffects.scene_recipe.return_value = recipe
        slots._pulse_ramp.decided.return_value = ((1.0, 0.0, 0.0), None)
        sb.tk.WebXrPreview.return_value.push.return_value = self._result()
        slots.btn_webxr()
        kwargs = sb.tk.RenderEffects.preview_channels.call_args.kwargs
        self.assertEqual(kwargs["keys"], recipe.plan("pulse", 0.0, 120.0, 30.0))
        self.assertEqual(kwargs["colors"], ((1.0, 0.0, 0.0), recipe.pulse_dim))

    def test_a_push_that_dropped_the_overlay_is_reported_not_claimed(self):
        """Live report (2026-09-13): every push looked the same whatever the
        page said -- a bridge predating the overlay knob publishes the scene
        with no error anywhere, so the panel reads the result and says so."""
        slots, sb, ui = _panel(shown=0)
        _select(sb, ["lid"])
        _fade_page(slots)
        sb.tk.WebXrPreview.return_value.push.return_value = self._result(applied=False)
        slots.btn_webxr()
        self.assertIn("without the opacity overlay", sb.message_box.call_args.args[0])
        self.assertIn("not the opacity settings", ui.footer.setText.call_args.args[0])

    def test_a_failed_push_says_so(self):
        slots, sb, ui = _panel(shown=0)
        _select(sb, ["lid"])
        _fade_page(slots)
        sb.tk.WebXrPreview.return_value.push.return_value = None
        slots.btn_webxr()
        self.assertIn("failed", ui.footer.setText.call_args.args[0])


class TestRenderEffectsPanelColours(_PanelCase):
    def test_disagreeing_ends_read_mixed_and_seed_the_default(self):
        """The old reader took the first object's colour, so a multi-object
        edit showed ONE look and the first drag wrote it to all of them."""
        slots, sb, ui = _panel()
        sb.tk.RenderEffects.channel_color_stops.return_value = {
            "lid": ((1.0, 0.0, 0.0), (0.0, 0.0, 0.0)),
            "box": ((0.0, 1.0, 0.0), (0.0, 0.0, 0.0)),
        }
        (bright, dim), mixed = slots._authored_stops(["lid", "box"])
        sb.tk.RenderEffects.channel_color_stops.assert_called_once_with(
            ["lid", "box"], channel="highlight"
        )
        self.assertEqual(mixed, (True, False))
        self.assertEqual(bright, RenderEffectsSlots.DEFAULT_BRIGHT)
        self.assertEqual(dim, (0.0, 0.0, 0.0))

    def test_an_hdr_colour_seeds_clamped(self):
        slots, sb, ui = _panel()
        sb.tk.RenderEffects.channel_color_stops.return_value = {
            "lid": ((2.0, 0.5, 0.0), None)
        }
        (bright, _dim), _mixed = slots._authored_stops(["lid"])
        self.assertEqual(bright, (1.0, 0.5, 0.0))

    def test_create_shows_the_recipes_colours(self):
        slots, sb, ui = _panel()
        _set_mode(slots, CREATE)
        slots._pulse_ramp.editors = ()
        slots._sync_highlight_mode()
        slots._pulse_ramp.set_colors.assert_called_once_with(ptk.EffectRecipe().colors)
        slots._pulse_ramp.set_reference.assert_called_with(None)

    def test_revise_seeds_from_what_is_authored(self):
        slots, sb, ui = _panel()
        _set_mode(slots, REVISE)
        _select(sb, ["lid"], {"highlight": {"lid"}})
        authored = ((0.02, 0.17, 0.43), (0.5, 0.0, 0.0))
        sb.tk.RenderEffects.channel_color_stops.return_value = {"lid": authored}
        slots._sync_highlight_mode()
        slots._pulse_ramp.set_colors.assert_called_once_with(authored)
        slots._pulse_ramp.set_reference.assert_called_with(authored)

    def test_the_selection_path_never_scans_the_scene(self):
        """The scene-wide read happens on the switch INTO Revise (deep), never
        on every selection change."""
        slots, sb, ui = _panel()
        _set_mode(slots, REVISE)
        slots._sync_highlight_mode()
        sb.tk.RenderEffects.objects_with_channel.assert_not_called()
        slots._pulse_ramp.set_colors.assert_not_called()
        sb.tk.RenderEffects.objects_with_channel.return_value = ["|lid"]
        sb.tk.RenderEffects.channel_color_stops.return_value = {
            "|lid": ((1.0, 0.0, 0.0), (0.0, 0.0, 0.0))
        }
        slots._sync_highlight_mode(deep=True)
        sb.tk.RenderEffects.objects_with_channel.assert_called_once_with("highlight")
        slots._pulse_ramp.set_colors.assert_called_once()

    def test_a_create_colour_is_the_recipes_and_a_revise_one_is_not(self):
        slots, sb, ui = _panel()
        store = sb.tk.RenderEffects.scene_store.return_value
        slots._pulse_ramp.decided.return_value = ((0.0, 0.0, 1.0), None)
        _set_mode(slots, REVISE)
        slots._on_pulse_color_committed(0, None)
        store.active.return_value.update_effect_recipe.assert_not_called()
        _set_mode(slots, CREATE)
        slots._on_pulse_color_committed(0, None)
        store.active.return_value.update_effect_recipe.assert_called_once_with(
            pulse_bright=(0.0, 0.0, 1.0)
        )
        slots._on_pulse_color_committed(1, None)  # an undecided end: nothing
        store.active.return_value.update_effect_recipe.assert_called_once()

    def test_the_cycle_readout_names_a_cut_tail(self):
        """A length that is not a whole multiple of the period ends mid-cycle;
        the leads come out of the length."""
        slots, sb, ui = _panel()
        slots._cycle_readout = mock.MagicMock()
        page = _pulse_page(slots, seconds=4.0)
        recipe = ptk.EffectRecipe(
            pulse_period=2.0, pulse_lead_in=0.0, pulse_lead_out=0.0
        )
        sb.tk.RenderEffects.scene_recipe.return_value = recipe
        slots._update_cycle_readout()
        self.assertNotIn("cut", slots._cycle_readout.setText.call_args.args[0])
        page.s001.value.return_value = 5.0
        slots._update_cycle_readout()
        self.assertIn("cut", slots._cycle_readout.setText.call_args.args[0])
        sb.tk.RenderEffects.scene_recipe.return_value = ptk.EffectRecipe(
            pulse_period=2.0, pulse_lead_in=0.5, pulse_lead_out=0.5
        )
        slots._update_cycle_readout()
        self.assertNotIn("cut", slots._cycle_readout.setText.call_args.args[0])


# ---------------------------------------------------------------------------
# The .ui
# ---------------------------------------------------------------------------


class TestRenderEffectsPanelUi(unittest.TestCase):
    """The ``.ui``: one action row under the pages, set apart."""

    @classmethod
    def setUpClass(cls):
        cls.root = ET.parse(UI_PATH).getroot()
        cls.widgets = {w.get("name"): w for w in cls.root.iter("widget")}
        cls.layouts = {lay.get("name"): lay for lay in cls.root.iter("layout")}

    def _height(self, name):
        node = self.widgets[name].find("property[@name='maximumSize']")
        return int(node.findtext("size/height"))

    def test_every_widget_the_panel_uses_exists(self):
        for name in (
            "header", "cmb_effect", "stk_effects", "page_fade", "page_pulse",
            "b000", "btn_webxr", "btn_remove", "footer",
        ):  # fmt: skip
            self.assertIn(name, self.widgets, name)

    def test_the_header_is_declared_as_tentacles_tools_declare_it(self):
        header = next(
            c for c in self.root.iter("customwidget") if c.findtext("class") == "Header"
        )
        self.assertEqual(header.findtext("extends"), "QLabel")
        self.assertEqual(header.findtext("header"), "uitk.widgets.header.Header.h")

    def test_key_is_twice_a_row_with_webxr_over_remove_beside_it(self):
        """Key reads as the panel's one action: twice the picker's height, and
        WebXR over Remove is exactly Key's height."""
        self.assertEqual(self._height("b000"), 2 * self._height("cmb_effect"))
        side = self.layouts["sideActionsLayout"]
        self.assertEqual(
            [w.get("name") for w in side.iter("widget")], ["btn_webxr", "btn_remove"]
        )
        self.assertEqual(side.find("property[@name='spacing']").findtext("number"), "0")
        self.assertEqual(
            self._height("btn_webxr") + self._height("btn_remove"), self._height("b000")
        )

    def test_the_pages_and_the_actions_are_set_apart_alike(self):
        gaps = {
            s.get("name"): int(
                s.find("property[@name='sizeHint']").findtext("size/height")
            )
            for s in self.root.iter("spacer")
            if s.find("property[@name='sizeType']") is not None
            and s.find("property[@name='sizeType']").findtext("enum")
            == "QSizePolicy::Fixed"
        }
        self.assertEqual(gaps, {"effectGap": 10, "actionsGap": 10})


# ---------------------------------------------------------------------------
# The real pages (offscreen Qt, plain Python)
# ---------------------------------------------------------------------------


def _loaded_toolkit(store):
    """A toolkit whose ``RenderEffects`` keeps the recipe on the pure *store*
    and sees an empty scene."""
    tk = mock.MagicMock()
    effects = tk.RenderEffects
    effects.scene_store.return_value = store
    effects.scene_recipe.side_effect = lambda: store.active().effect_recipe
    effects.selected_objects.side_effect = lambda last_only=False: []
    effects.has_channel.return_value = False
    effects.select_objects.side_effect = lambda objects: list(objects)
    effects.objects_with_channel.return_value = []
    effects.channel_color_stops.return_value = {}
    tk.AudioUtils.get_fps.return_value = 30.0
    tk.AnimUtils.get_current_frame.return_value = 1.0
    return tk


@unittest.skipIf(MAYA_AVAILABLE, "plain Python; in Maya the InMaya case drives mtk")
@unittest.skipUnless(qt_widgets_available(), "builds real widgets")
class TestRenderEffectsPanelLoaded(unittest.TestCase):
    """The panel loaded the way a host opens it -- a real Switchboard with
    tentacle's shared roots -- over a fake toolkit: what a stub UI cannot see,
    the pages the init slots build, how their fields bind to the scene's effect
    recipe, the readouts they keep, the folds and the window fit, and the focus
    the Shot Manifest opens. Moved from mayatk's
    ``mock_tests/test_render_effects_panel.py`` (and the page-building half of
    its ``TestRenderEffectsSlots``)."""

    @classmethod
    def setUpClass(cls):
        try:
            from qtpy import QtWidgets
        except Exception:  # pragma: no cover - Qt absent
            raise unittest.SkipTest("Qt not available")
        from uitk import Switchboard

        from tentacle.tcl import Tcl

        migrated = Slots._legacy_repeat_last_migrated
        Slots._legacy_repeat_last_migrated = True
        cls.addClassCleanup(setattr, Slots, "_legacy_repeat_last_migrated", migrated)

        # The scene's recipe on a pure store of its own (class-level ``_active``).
        class Store(ptk.ShotStore):
            _active = None
            _persistence = None
            _invalidation_listeners = []

        cls.Store = Store
        cls.QtWidgets = QtWidgets
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        sb = Switchboard()
        Tcl.register_shared(sb)
        sb.tk = _loaded_toolkit(Store)
        cls.sb = sb
        cls.ui = sb.get_ui("render_effects")
        cls.slots = sb.get_slots_instance(cls.ui)
        for _ in range(5):
            cls.app.processEvents()

    def setUp(self):
        self.Store.active().update_effect_recipe(**self.Store().effect_recipe.to_dict())

    # -- the pages -----------------------------------------------------------

    def test_the_picker_shows_one_page_per_effect(self):
        self.assertIsInstance(self.slots, RenderEffectsSlots)
        self.assertEqual(
            [self.ui.cmb_effect.itemText(i) for i in range(self.ui.cmb_effect.count())],
            ["Opacity Fade", "Highlight Pulse"],
        )
        self.ui.cmb_effect.setCurrentIndex(1)
        self.addCleanup(self.ui.cmb_effect.setCurrentIndex, 0)
        self.assertIs(self.ui.stk_effects.currentWidget(), self.ui.page_pulse)

    def test_each_page_opens_on_create(self):
        """The help promises each page opens on Create: a mode restored from
        the user's settings would reopen a page in Revise."""
        for name in ("cmb_mode_opacity", "cmb_mode_highlight"):
            combo = getattr(self.ui, name)
            self.assertFalse(combo.restore_state, name)
            self.assertEqual(combo.itemData(0), CREATE, name)
            self.assertEqual(combo.currentData(), CREATE, name)

    def test_the_pages_hold_settings_and_the_window_holds_the_actions(self):
        """Key, the remove and WebXR are one row under the pages, not a row
        per page. A field's own option-box buttons (uitk's ``OptionButton``,
        e.g. a spin box's toggle) are the field's chrome, not an action."""
        for channel in ("opacity", "highlight"):
            rows = self.slots._pages[channel]
            actions = [
                button
                for button in rows.findChildren(self.QtWidgets.QPushButton)
                if type(button).__name__ != "OptionButton"
            ]
            self.assertEqual(actions, [], channel)

    def test_revise_hides_the_fields_it_cannot_write(self):
        """A page offering to re-time a signed-off pulse under the word
        'revise' would be offering to re-key it."""
        fields = self.slots._mode_fields["highlight"]
        self.ui.cmb_mode_highlight.setCurrentIndex(1)  # Revise
        self.addCleanup(self.ui.cmb_mode_highlight.setCurrentIndex, 0)
        self.assertNotIn("s001", fields.visible, "the cadence lives in keys")
        self.assertIn("pulse_colors", fields.visible)
        self.ui.cmb_mode_highlight.setCurrentIndex(0)
        self.assertIn("s001", fields.visible, "Create keys, so it may re-time")

    def test_revise_hides_only_what_creates_the_channel(self):
        fields = self.slots._mode_fields["opacity"]
        self.assertEqual(fields.keys, ("chk_delete_vis_keys",))
        self.assertEqual(fields.visible, ("chk_delete_vis_keys",))
        self.ui.cmb_mode_opacity.setCurrentIndex(1)  # Revise
        self.addCleanup(self.ui.cmb_mode_opacity.setCurrentIndex, 0)
        self.assertEqual(fields.visible, ())
        option = self.slots.ui_field("chk_delete_vis_keys")
        self.assertTrue(option.isHidden())

    def test_the_pulse_page_carries_one_colour_editor(self):
        """Regression: the tool had TWO colour sections that disagreed about
        what they could show. The page's row is the only one."""
        from uitk import ColorRampEditor

        rows = self.slots._pages["highlight"]
        self.assertEqual(len(rows.findChildren(ColorRampEditor)), 1)

    def test_the_fade_page_previews_the_exporters_own_alpha(self):
        preview = self.slots._fade_preview
        self.assertEqual(preview._values, ptk.GlbFades.CHANNELS["opacity"].values)
        self.assertEqual(len(preview.composite(0.5)), 4, "alpha rides the fourth lane")

    def test_the_fade_preview_tracks_the_recipe(self):
        """A preview animating at some other length than the one being keyed
        gives away the only thing it is there to show."""
        direction = self.slots.ui_field("cmb_direction")
        self.addCleanup(direction.setCurrentIndex, direction.currentIndex())
        self.Store.active().update_effect_recipe(fade_frames=60)
        direction.setCurrentIndex(direction.findData("out"))
        self.slots._sync_fade_shape()
        shape = self.slots._fade_preview.shape
        self.assertAlmostEqual(shape["duration"], 60 / 30.0, places=5)
        self.assertEqual(shape["direction"], "out")

    # -- the scene's recipe ----------------------------------------------------

    def test_the_fields_are_the_scenes_recipe(self):
        """The fade's frames and the pulse's cadence show the scene's recipe,
        and an edit writes it -- what the manifest's Build keys with."""
        self.assertEqual(self.ui.s000.value(), 15)
        self.assertAlmostEqual(self.ui.s002.value(), 2.86)
        self.assertEqual(self.ui.s003.value(), 59)
        self.ui.s002.setValue(2.0)
        self.ui.s003.setValue(40)
        recipe = self.Store.active().effect_recipe
        self.assertEqual((recipe.pulse_period, recipe.pulse_duty), (2.0, 0.4))

    def test_a_recipe_changed_elsewhere_shows_here(self):
        self.Store.active().update_effect_recipe(fade_frames=24, pulse_lead_in=0.5)
        self.assertEqual(self.ui.s000.value(), 24)
        self.assertAlmostEqual(self.ui.s004.value(), 0.5)

    def test_a_whole_number_box_shows_the_nearest_whole_number(self):
        """``setValue`` truncates a float on an integer box: a 0.57 duty is
        56.99... percent and showed 56 (0.29 and 0.58 too)."""
        for duty in (0.29, 0.57, 0.58):
            self.Store.active().update_effect_recipe(pulse_duty=duty)
            self.assertEqual(self.ui.s003.value(), round(duty * 100), duty)
        self.Store.active().update_effect_recipe(fade_frames=12.6)
        self.assertEqual(self.ui.s000.value(), 13)
        self.Store.active().update_effect_recipe(pulse_period=2.86)
        self.assertAlmostEqual(self.ui.s002.value(), 2.86, msg="decimals stay")

    def test_recipe_fields_never_restore_from_qsettings(self):
        """A restore lands after the recipe was read and would write the last
        value set in ANY scene over this one's."""
        for name in ("s000", "s002", "s003", "s004", "s005"):
            self.assertFalse(getattr(self.ui, name).restore_state, name)
        # The panel's own fields still persist per user.
        self.assertTrue(self.ui.s001.restore_state)

    def test_the_cycle_readout_counts_the_train_between_the_leads(self):
        """The leads come out of the length. At the defaults (4 s, a 2.86 s
        period, 0.72 s leads) the keys hold ONE bright beat; the readout,
        dividing the whole length by the period, said 1.4."""
        self.assertIn("0.9", self.ui.lbl_cycles.text())
        self.ui.s004.setValue(0.0)  # the two leads move together
        self.app.processEvents()
        self.assertEqual(self.ui.s005.value(), 0.0, "the leads are linked")
        self.assertIn("1.4", self.ui.lbl_cycles.text())

    def test_create_shows_the_recipe_colours(self):
        self.Store.active().update_effect_recipe(pulse_dim=(0.2, 0.0, 0.0))
        _bright, dim = self.slots._pulse_ramp.decided()
        self.assertEqual(tuple(round(c, 3) for c in dim), (0.2, 0.0, 0.0))

    # -- the focus ---------------------------------------------------------------

    def test_focus_names_the_object_and_keys_through_the_manifest(self):
        calls = []

        def apply():
            calls.append("apply")
            return "Re-applied Red_Door's behaviors in S03."

        self.slots.focus(
            "highlight",
            [],
            title="Red_Door · S03",
            apply=apply,
            apply_text="Apply to 'Red_Door' in S03",
        )
        self.addCleanup(self.slots.unfocus)
        self.assertTrue(self.ui.cmb_effect.isHidden())
        self.assertIs(self.ui.stk_effects.currentWidget(), self.ui.page_pulse)
        self.assertIn("RED_DOOR", self.ui.header.title())
        self.assertEqual(self.ui.b000.text(), "Apply to 'Red_Door' in S03")

        self.slots.b000()
        self.assertEqual(calls, ["apply"])
        self.assertIn("Red_Door", self.ui.footer.statusText())

        self.slots.unfocus()
        self.assertFalse(self.ui.cmb_effect.isHidden())
        self.assertEqual(self.ui.b000.text(), "Key Highlight Pulse")

    def test_a_focused_highlights_key_says_what_each_mode_does(self):
        self.slots.focus(
            "highlight",
            [],
            title="Red_Door · S03",
            apply=lambda: "",
            apply_text="Apply to 'Red_Door' in S03",
        )
        self.addCleanup(self.slots.unfocus)
        self.addCleanup(self.ui.cmb_mode_highlight.setCurrentIndex, 0)
        self.assertEqual(self.ui.b000.text(), "Apply to 'Red_Door' in S03")
        self.ui.cmb_mode_highlight.setCurrentIndex(1)  # Revise
        self.assertEqual(self.ui.b000.text(), "Key Highlight Pulse")
        self.ui.cmb_mode_highlight.setCurrentIndex(0)  # Create
        self.assertEqual(self.ui.b000.text(), "Apply to 'Red_Door' in S03")

    def test_a_focus_that_opens_in_revise_labels_key_for_revise(self):
        """Every object already carrying the highlight opens the page in
        Revise, where Key re-colours -- not the manifest's "Apply to ..."."""
        effects = self.sb.tk.RenderEffects
        effects.select_objects.side_effect = lambda objects: ["|Red_Door"]
        effects.has_channel.return_value = True
        self.addCleanup(setattr, effects.has_channel, "return_value", False)
        self.addCleanup(
            setattr,
            effects.select_objects,
            "side_effect",
            lambda objects: list(objects),
        )
        self.slots.focus(
            "highlight",
            ["Red_Door"],
            title="Red_Door · S03",
            apply=lambda: "",
            apply_text="Apply to 'Red_Door' in S03",
        )
        self.addCleanup(self.slots.unfocus)
        self.addCleanup(self.ui.cmb_mode_highlight.setCurrentIndex, 0)
        self.assertEqual(self.ui.cmb_mode_highlight.currentData(), REVISE)
        self.assertEqual(self.ui.b000.text(), "Key Highlight Pulse")

    def test_hiding_the_panel_ends_the_focus(self):
        self.slots.focus("opacity", [], title="Lid · S01", apply=lambda: "")
        self.ui.on_hide.emit()
        self.assertIsNone(self.slots._focus)
        self.assertFalse(self.ui.cmb_effect.isHidden())

    # -- one action row, and only shared options in the header -------------------

    def test_one_action_row_serves_whichever_page_shows(self):
        for index, text in ((0, "Key Opacity Fade"), (1, "Key Highlight Pulse")):
            self.ui.cmb_effect.setCurrentIndex(index)
            self.assertEqual(self.ui.b000.text(), text)
            self.assertIsNone(
                self.ui.stk_effects.currentWidget().findChild(
                    self.QtWidgets.QPushButton, "b000"
                )
            )
        self.ui.cmb_effect.setCurrentIndex(0)
        self.assertEqual(self.ui.btn_remove.text(), "Remove")

    def test_the_header_holds_only_options_every_effect_shares(self):
        """Delete Visibility Keys acts only when a fade first makes the opacity
        channel, so it is the Fade page's."""
        menu = self.ui.header.menu
        self.assertIsNotNone(getattr(menu, "chk_last_selected", None))
        self.assertIsNone(getattr(menu, "chk_delete_vis_keys", None))
        option = self.slots.ui_field("chk_delete_vis_keys")
        self.assertTrue(self.ui.page_fade.isAncestorOf(option))

    # -- the window follows what the panel shows ---------------------------------

    def _shown(self, page=0):
        """The panel on screen at *page* (a hidden window is left to the fit
        its show makes)."""
        self.ui.cmb_effect.setCurrentIndex(page)
        self.addCleanup(self.ui.cmb_effect.setCurrentIndex, 0)
        self.ui.show()
        self.addCleanup(self.ui.hide)
        self._turn()

    def _turn(self):
        """Long enough for a deferred window fit to land."""
        from qtpy import QtCore

        loop = QtCore.QEventLoop()
        QtCore.QTimer.singleShot(30, loop.quit)
        loop.exec_() if hasattr(loop, "exec_") else loop.exec()

    def test_the_window_follows_the_page_it_shows(self):
        """A stack is as tall as its tallest page, so the Fade page sat in a
        window sized for the Pulse page, whichever was picked."""
        self._shown(page=0)
        fade = self.ui.height()
        self.ui.cmb_effect.setCurrentIndex(1)
        self._turn()
        self.assertGreater(self.ui.height(), fade)
        self.ui.cmb_effect.setCurrentIndex(0)
        self._turn()
        self.assertEqual(self.ui.height(), fade)

    def _fold(self, channel):
        """*channel*'s Settings fold, opened again when the test ends."""
        group = getattr(self.slots._pages[channel], f"grp_settings_{channel}")
        self.addCleanup(group.setChecked, True)
        return group

    def test_a_page_folds_to_its_mode_and_key(self):
        """Live report (2026-10-03): set once, a page's fields still stood
        between its mode and Key for every keying after."""
        self._shown(page=1)
        opened = self.ui.height()
        fold = self._fold("highlight")
        fold.setChecked(False)
        self._turn()
        self.assertLess(self.ui.height(), opened)
        self.assertFalse(self.ui.s001.isVisible())
        self.assertTrue(self.ui.cmb_mode_highlight.isVisible(), "the mode stays")
        self.assertTrue(self.ui.b000.isVisible())
        fold.setChecked(True)
        self._turn()
        self.assertEqual(self.ui.height(), opened)

    def test_a_folded_page_stays_folded_through_a_mode_switch(self):
        """A mode shows its fields INSIDE the fold: folded, the page shows
        none of them, and opening it shows that mode's, at that mode's height."""
        from uitk import WindowHeight

        self._shown(page=1)
        fold = self._fold("highlight")
        fold.setChecked(False)
        self._turn()
        folded = self.ui.height()
        colours = self.slots.ui_field("pulse_colors")
        self.ui.cmb_mode_highlight.setCurrentIndex(1)  # Revise
        self.addCleanup(self.ui.cmb_mode_highlight.setCurrentIndex, 0)
        self._turn()
        self.assertFalse(colours.isVisible())
        self.assertEqual(self.ui.height(), folded)
        fold.setChecked(True)
        self._turn()
        self.assertTrue(colours.isVisible())
        self.assertFalse(self.ui.s001.isVisible(), "Revise's fields, not Create's")
        opened = self.ui.height()
        WindowHeight.fit_host(self.ui)
        self.assertEqual(self.ui.height(), opened, "already fitted")

    def test_the_colours_open_their_advanced_rows_inside_the_fold(self):
        """One Advanced across both ends, folded inside Settings -- not a fold
        per colour column."""
        from uitk.widgets.separator import Separator

        ramp = self.slots._pulse_ramp
        folds = [s for s in ramp.findChildren(Separator) if s.isCheckable()]
        self.assertEqual(folds, [ramp._disclosure])
        fold = self.slots._pages["highlight"].grp_settings_highlight
        self.assertTrue(fold.isAncestorOf(ramp._disclosure))

    def test_ending_the_focus_puts_back_the_readout_and_the_height(self):
        """A hide ends the focus and the selection job skips a hidden panel,
        so the manifest's line outlived it."""
        self._shown(page=1)
        before = self.ui.height()
        self.slots.focus("highlight", [], title="Red_Door · S03", apply=lambda: "")
        self.addCleanup(self.slots.unfocus)
        self._turn()
        self.assertIn("Re-keys", self.ui.footer.getDefaultStatusText())

        self.ui.on_hide.emit()
        self._turn()
        self.assertNotIn("Re-keys", self.ui.footer.getDefaultStatusText())
        self.assertEqual(self.ui.height(), before)

    # -- the footer says what Key will do ----------------------------------------

    def test_the_footer_rests_on_what_the_shown_pages_key_will_do(self):
        """One short line in the footer, its counts in bold -- for the page on
        show only."""
        self._shown(page=1)
        self.assertEqual(self.ui.footer.getDefaultStatusText(), "Needs a selection")
        self.ui.cmb_mode_highlight.setCurrentIndex(1)  # Revise
        self.addCleanup(self.ui.cmb_mode_highlight.setCurrentIndex, 0)
        self.assertEqual(
            self.ui.footer.getDefaultStatusText(),
            "Re-colours <b>every</b> highlight object in the scene",
        )
        self.assertIsNone(getattr(self.ui, "lbl_apply_highlight", None))

    def test_a_report_stands_until_the_next_page_or_mode(self):
        """A report is about the action that made it; switching page or mode
        is a new question, which the resting line answers."""
        self._shown(page=0)
        self.ui.footer.setText("Fade In: 2 object(s), frames 10-25")
        self.slots._on_selection_changed()  # what a tool runs after its write
        self.assertEqual(
            self.ui.footer.statusText(), "Fade In: 2 object(s), frames 10-25"
        )
        self.ui.cmb_effect.setCurrentIndex(1)
        self.assertEqual(self.ui.footer.statusText(), "")
        self.ui.footer.setText("Highlight pulse: 2 object(s)")
        self.ui.cmb_mode_highlight.setCurrentIndex(1)
        self.addCleanup(self.ui.cmb_mode_highlight.setCurrentIndex, 0)
        self.assertEqual(self.ui.footer.statusText(), "")

    def test_a_pick_in_the_scene_ends_the_report(self):
        self._shown(page=0)
        self.ui.footer.setText("Opacity removed from 2 object(s)")
        self.slots._on_scene_selection()  # the selection job
        self.assertEqual(self.ui.footer.statusText(), "")
        self.assertEqual(self.ui.footer.text(), "Needs a selection")


# ---------------------------------------------------------------------------
# The real host
# ---------------------------------------------------------------------------


@unittest.skipUnless(MAYA_AVAILABLE, "drives the real mtk; runs in a fresh Maya")
class TestRenderEffectsPanelInMaya(_PanelCase):
    """The panel over the real ``mtk`` and a scene: its two pages key their
    channel on demand, each with its Key / remove / WebXR row; the fields that
    say HOW an effect is keyed are the scene's effect recipe. The pages' own
    fields are stubs (``_fade_page`` / ``_pulse_page``) and the colour row a
    mock -- the real widgets are ``TestRenderEffectsPanelLoaded``'s. Moved from
    mayatk's ``test_render_opacity.TestRenderEffectsSlots``.

    Regression kept from 2026-05-07: the panel must accept the plain string
    node names ``cmds.ls(selection=True)`` returns (a PyMEL ``.name()`` idiom
    once raised here).
    """

    def setUp(self):
        super().setUp()
        cmds.file(new=True, force=True)
        self.cube = cmds.polyCube(name="slot_cube")[0]
        cmds.select(self.cube, replace=True)
        self.slot, self.sb, self.ui = _panel(tk=mtk)
        self.addCleanup(mtk.ScriptJobManager.instance().unsubscribe_all, self.slot)
        self.slot._on_selection_changed = mock.MagicMock()

    # ---- harness ---------------------------------------------------------

    def _recipe(self, **fields):
        """Set the scene's effect recipe for this test (restored after)."""
        import mayatk as mtk

        store = mtk.RenderEffects.scene_store().active()
        before = store.effect_recipe
        self.addCleanup(setattr, store, "effect_recipe", before)
        store.update_effect_recipe(**fields)
        return store

    def _set_mode(self, mode):
        """Put both pages in *mode*, without building either.

        The layout IS the mode, so this states it where the tool reads it.
        """
        from uitk import FieldVisibility

        for channel in ("opacity", "highlight"):
            fields = self.slot._mode_fields.setdefault(channel, FieldVisibility())
            fields.define(mode, ())
            fields.mode = mode

    def _fade_page(
        self, frames=10, ends_at_cursor=False, direction="in", delete_vis=False
    ):
        """The fade page's own fields; the length is the recipe's."""
        from types import SimpleNamespace
        from unittest.mock import MagicMock

        page = SimpleNamespace(
            chk000=MagicMock(),
            cmb_direction=MagicMock(),
            chk_delete_vis_keys=MagicMock(),
        )
        page.chk000.isChecked.return_value = ends_at_cursor
        page.cmb_direction.currentData.return_value = direction
        page.chk_delete_vis_keys.isChecked.return_value = delete_vis
        self.slot._pages["opacity"] = page
        self._recipe(fade_frames=frames)
        return page

    def _pulse_page(self, seconds=4.0, period=2.0, duty=50, gaps=(0.72, 0.72)):
        """The pulse page's own fields (SECONDS); the cadence is the recipe's."""
        from types import SimpleNamespace
        from unittest.mock import MagicMock

        page = SimpleNamespace(s001=MagicMock(), chk001=MagicMock())
        page.s001.value.return_value = seconds
        page.chk001.isChecked.return_value = False
        self.slot._pages["highlight"] = page
        self._recipe(
            pulse_period=period,
            pulse_duty=duty / 100.0,
            pulse_lead_in=gaps[0],
            pulse_lead_out=gaps[1],
        )
        return page

    # ---- pages -----------------------------------------------------------

    def test_the_action_row_follows_the_shown_page(self):
        """Key's text and the remove's gate are the page on show's -- and the
        manifest's text while focused on that effect."""
        mtk.RenderEffects.create([self.cube], mode="attribute", channel="opacity")
        cmds.select(self.cube, replace=True)
        self.slot._focus = None
        self.slot.ui.stk_effects.currentIndex.return_value = 0
        self.slot._sync_actions()
        self.slot.ui.b000.setText.assert_called_with("Key Opacity Fade")
        self.slot.ui.btn_remove.setEnabled.assert_called_with(True)

        self.slot.ui.stk_effects.currentIndex.return_value = 1
        self.slot._sync_actions()
        self.slot.ui.b000.setText.assert_called_with("Key Highlight Pulse")
        self.slot.ui.btn_remove.setEnabled.assert_called_with(False)

        self.slot._focus = {
            "channel": "highlight",
            "objects": [],
            "apply": lambda: "",
            "apply_text": "Apply to 'Lid' in S01",
            "title": "Lid · S01",
        }
        self.slot._sync_actions()
        self.slot.ui.b000.setText.assert_called_with("Apply to 'Lid' in S01")

    # ---- WebXR -----------------------------------------------------------

    def _push_preview(self, spec, applied=True):
        """Run the preview action with the bridge stubbed; return its ``push``.

        *applied* is what the stubbed result says landed: the overlay's channel
        (a bridge that honoured the knob) or nothing (one that predates it).
        """
        from unittest.mock import patch

        import pythontk as ptk
        import mayatk as mtk

        with patch.object(mtk, "WebXrPreview") as bridge:
            bridge.return_value.push.return_value = {
                "version": 3,
                "url": "http://127.0.0.1:0/",
                "data_export": ([ptk.SceneRecords.VISIBILITY.key] if applied else []),
            }
            self.slot._preview_webxr(spec)
        return bridge.return_value.push

    @staticmethod
    def _published_ramp(keys):
        """*keys* as the visibility channel publishes them: every float
        rounded to ``MeshConvert.VISIBILITY_TRACK_DIGITS`` places."""
        import pythontk as ptk

        digits = ptk.MeshConvert.VISIBILITY_TRACK_DIGITS
        return [[round(float(f), digits), round(float(v), digits)] for f, v in keys]

    def test_the_webxr_preview_pushes_the_fade_as_set_and_writes_nothing(self):
        import pythontk as ptk
        import mayatk as mtk

        self._fade_page(frames=15, direction="auto")
        push = self._push_preview("opacity")

        self.slot.sb.message_box.assert_not_called()
        push.assert_called_once()
        kwargs = push.call_args.kwargs
        self.assertEqual(kwargs["objects"], [self.cube])
        overlay = kwargs["data_export"]
        tracks = overlay[ptk.SceneRecords.VISIBILITY.key]["tracks"]
        self.assertEqual([t["node"] for t in tracks], [self.cube])
        fps = float(mtk.AudioUtils.get_fps() or 30.0)
        expected = ptk.RampKeys.fade_loop(
            15, hold=self.slot.PREVIEW_HOLD_SECONDS * fps, direction="auto"
        )
        self.assertEqual(tracks[0]["opacity"], self._published_ramp(expected))
        # No shot cuts it: the shot record carries the takes (each clip its
        # range).
        self.assertIsNone(overlay[ptk.SceneRecords.SHOTS.key], "no shot cuts it")
        self.assertFalse(
            cmds.attributeQuery("opacity", node=self.cube, exists=True),
            "nothing created",
        )
        self.assertFalse(cmds.keyframe(self.cube, q=True, kc=True), "nothing keyed")

    def test_the_webxr_preview_shows_the_pulse_alone_over_an_existing_effect(self):
        """The preview has nothing to do with existing keys or effects: an object
        that already fades previews the pulse as the page is set, with no trace
        of its fade in the push, and its fade keys are exactly as they were."""
        import pythontk as ptk
        import mayatk as mtk

        mtk.RenderEffects.key_fade([self.cube], start=1, end=15)
        before = cmds.keyframe(f"{self.cube}.opacity", q=True, kc=True)
        self._pulse_page(seconds=4.0, period=2.0, duty=50, gaps=(0.5, 0.25))
        self.slot._pulse_ramp.decided.return_value = ((1.0, 0.0, 0.0), None)
        push = self._push_preview("highlight")

        self.slot.sb.message_box.assert_not_called()
        overlay = push.call_args.kwargs["data_export"]
        (track,) = overlay[ptk.SceneRecords.VISIBILITY.key]["tracks"]
        fps = float(mtk.AudioUtils.get_fps() or 30.0)
        expected = ptk.RampKeys.pulse(
            0.0,
            4.0 * fps,
            period=2.0 * fps,
            bright_fraction=0.5,
            lead_in=0.5 * fps,
            lead_out=0.25 * fps,
        )
        self.assertEqual(track["highlight"], self._published_ramp(expected))
        self.assertEqual(track["highlight_color"], [1.0, 0.0, 0.0])
        self.assertEqual(track["highlight_color_dim"], list(self.slot.DEFAULT_DIM))
        self.assertNotIn("opacity", track, "the object's own fade is left out")
        self.assertFalse(cmds.attributeQuery("highlight", node=self.cube, exists=True))
        self.assertEqual(cmds.keyframe(f"{self.cube}.opacity", q=True, kc=True), before)

    def test_the_webxr_preview_needs_a_selection(self):
        cmds.select(clear=True)
        push = self._push_preview("opacity")
        push.assert_not_called()
        self.slot.sb.message_box.assert_called_once()

    def test_a_push_that_dropped_the_overlay_is_reported_not_claimed(self):
        """Live report (2026-09-13): every push looked the same whatever the
        page said. A bridge that predates the overlay knob publishes the scene
        as it stands with no error anywhere -- so the slot reads the result's
        ``data_export`` and says so."""
        self._fade_page()
        push = self._push_preview("opacity", applied=False)

        push.assert_called_once()
        self.slot.sb.message_box.assert_called_once()
        self.assertIn(
            "without the opacity overlay", self.slot.sb.message_box.call_args.args[0]
        )
        self.assertIn(
            "not the opacity settings", self.slot.ui.footer.setText.call_args.args[0]
        )

    # ---- keying ------------------------------------------------------------

    def test_key_fade_creates_the_opacity_channel_on_demand(self):
        self._fade_page()
        self.slot._key_fade_page()

        self.assertTrue(cmds.attributeQuery("opacity", node=self.cube, exists=True))
        self.assertEqual(cmds.keyframe(f"{self.cube}.opacity", q=True, kc=True), 2)
        self.slot.sb.message_box.assert_not_called()

    def test_the_fade_page_owns_delete_visibility_keys(self):
        """An option only the fade reads lives on the fade page, not in the
        header every effect shares."""
        self._fade_page(delete_vis=True)
        with mock.patch.object(
            mtk.RenderEffects, "key_fade", return_value=[]
        ) as key_fade:
            self.slot._key_fade_page()
        self.assertTrue(key_fade.call_args.kwargs["delete_visibility_keys"])

    def test_the_fade_is_as_long_as_the_recipe_says(self):
        """The page's Frames field IS the scene's recipe -- the length the
        manifest's fades key too."""
        cmds.currentTime(30)
        self._fade_page(frames=12, ends_at_cursor=True)
        self.slot._key_fade_page()
        self.assertEqual(
            cmds.keyframe(f"{self.cube}.opacity", q=True, tc=True), [18.0, 30.0]
        )

    def test_the_recipe_leads_reach_the_keys(self):
        """The two leads are the recipe's seconds; the slot hands them to the
        writer in frames. A hard cut on one side and a one-second lead on the
        other are both readable straight off the curve."""
        import mayatk as mtk

        fps = float(mtk.AudioUtils.get_fps() or 30.0)
        cmds.currentTime(10)
        self._pulse_page(seconds=200 / 30.0, period=2.0, gaps=(1.0, 0.0))
        self.slot._key_pulse_page()
        plug = f"{self.cube}.highlight"
        keys = list(
            zip(
                cmds.keyframe(plug, q=True, tc=True),
                cmds.keyframe(plug, q=True, vc=True),
            )
        )
        self.assertEqual(keys[0], (10.0, 0.0), "opens dim at the playhead")
        self.assertEqual(keys[1], (10.0 + fps, 1.0), "one second up")
        self.assertEqual(keys[-1][1], 0.0, "ends dim")
        self.assertEqual(
            keys[-1][0] - keys[-2][0], 1.0, "a hard cut on the way out: one frame"
        )

    def test_key_pulse_creates_the_highlight_channel_on_demand(self):
        self._pulse_page()
        self.slot._pulse_ramp.decided.return_value = ((1.0, 0.0, 0.0), None)
        self.slot._key_pulse_page()

        self.assertTrue(cmds.attributeQuery("highlight", node=self.cube, exists=True))
        self.assertGreater(cmds.keyframe(f"{self.cube}.highlight", q=True, kc=True), 4)
        self.assertEqual(
            [round(c, 3) for c in cmds.getAttr(f"{self.cube}.highlightColor")[0]],
            [1.0, 0.0, 0.0],
        )
        self.slot.sb.message_box.assert_not_called()

    def test_revise_re_keys_only_objects_that_already_fade(self):
        """Opacity's Revise rewrites keys, which is the whole of what a fade
        is -- but it must not give the channel to anything new."""
        plain = cmds.polyCube(name="slot_never_faded")[0]
        mtk.RenderEffects.create([self.cube], mode="attribute", channel="opacity")
        cmds.select([self.cube, plain], replace=True)
        self._set_mode(REVISE)
        self._fade_page(frames=20)

        self.slot._key_fade_page()

        self.assertGreater(cmds.keyframe(f"{self.cube}.opacity", q=True, kc=True), 0)
        self.assertFalse(
            cmds.attributeQuery("opacity", node=plain, exists=True),
            "Revise must not spread the channel to an object that lacked it",
        )

    # ---- focus -------------------------------------------------------------

    def test_focused_key_runs_the_manifests_re_key_not_the_playhead(self):
        """From a manifest row, Key re-keys the object's behaviors where the
        build places them; the page's own playhead keying never runs."""
        calls = []
        self._pulse_page()
        self.slot._focus = {
            "channel": "highlight",
            "objects": [self.cube],
            "apply": lambda: calls.append("apply") or "re-keyed",
            "apply_text": "Apply",
            "title": "slot_cube",
        }
        self.slot._key_pulse_page()
        self.assertEqual(calls, ["apply"])
        self.assertFalse(cmds.attributeQuery("highlight", node=self.cube, exists=True))
        self.assertEqual(self.slot.ui.footer.setText.call_args.args[0], "re-keyed")

    def test_a_focused_revise_still_recolours(self):
        """A highlight's Revise writes colours, not keys -- the manifest's
        re-key is not what it means."""
        calls = []
        mtk.RenderEffects.create([self.cube], mode="attribute", channel="highlight")
        self._set_mode(REVISE)
        self.slot._focus = {
            "channel": "highlight",
            "objects": [self.cube],
            "apply": lambda: calls.append("apply"),
            "apply_text": "Apply",
            "title": "slot_cube",
        }
        self.slot._pulse_ramp.decided.return_value = ((0.02, 0.17, 0.43), None)
        self.slot._key_pulse_page()
        self.assertEqual(calls, [])
        self.assertEqual(
            [round(c, 3) for c in cmds.getAttr(f"{self.cube}.highlightColor")[0]],
            [0.02, 0.17, 0.43],
        )

    # ---- the selection job -----------------------------------------------

    def test_the_remove_action_is_gated_on_what_it_would_act_on(self):
        """Pre-existing: the action was gated on the RAW selection while
        ``_remove_channel`` operates on the Last-Selected-Only subset, so
        picking a highlighted object and then a plain one left the action live
        over a target with nothing to remove."""
        plain = cmds.polyCube(name="slot_gate_plain")[0]
        mtk.RenderEffects.create([self.cube], mode="attribute", channel="highlight")
        cmds.select([self.cube, plain], replace=True)
        self.slot.ui.header.menu.chk_last_selected.isChecked.return_value = True
        self.slot._focus = None
        self.slot.ui.isVisible.return_value = True
        del self.slot._on_selection_changed  # use the real one, not the stub

        self.slot._on_selection_changed()

        self.slot.ui.btn_remove.setEnabled.assert_called_with(False)

    def test_the_selection_is_read_once_per_change(self):
        """Four consumers asked the same question separately, so picking
        objects cost a scene read and a per-object query four times over."""
        from unittest.mock import MagicMock

        mtk.RenderEffects.create([self.cube], mode="attribute", channel="highlight")
        cmds.select(self.cube, replace=True)
        self.slot._focus = None
        self.slot._mode_combos = {"highlight": MagicMock()}
        self.slot.ui.isVisible.return_value = True
        del self.slot._on_selection_changed

        reads = []
        real = self.slot._get_selected
        self.slot._get_selected = lambda: (reads.append(1), real())[1]
        self.slot._on_selection_changed()

        self.assertEqual(len(reads), 1, "the selection was read more than once")

    def _footer_said(self):
        """The footer's resting line, as read (tags dropped)."""
        import re

        said = self.slot.ui.footer.setDefaultStatusText.call_args.args[0]
        return re.sub(r"<[^>]+>", "", said)

    def test_the_readout_says_what_key_will_do(self):
        """The Key button's label cannot say WHO it is about to act on, and
        that is the whole difference between the two modes."""
        mtk.RenderEffects.create([self.cube], mode="attribute", channel="highlight")
        plain = cmds.polyCube(name="slot_plain")[0]
        cmds.select([self.cube, plain], replace=True)

        self._set_mode(CREATE)
        self.slot._update_apply_readout("highlight")
        self.assertIn("2 selected", self._footer_said())

        self._set_mode(REVISE)
        self.slot._update_apply_readout("highlight")
        said = self._footer_said()
        self.assertIn("1 of 2 selected", said, "only one of them carries it")
        self.assertTrue(said.startswith("Re-colours"), said)

    def test_the_fade_readout_admits_that_revise_re_keys(self):
        """Opacity's Revise rewrites keys and the highlight's does not; the
        verb says which. The difference is invisible until it has cost
        something."""
        self.slot.ui.stk_effects.currentIndex.return_value = 0  # the Fade page
        self._set_mode(REVISE)
        mtk.RenderEffects.create([self.cube], mode="attribute", channel="opacity")
        cmds.select(self.cube, replace=True)

        self.slot._update_apply_readout("opacity")

        self.assertTrue(self._footer_said().startswith("Re-keys the fade"))

    def test_only_the_shown_page_writes_the_footer(self):
        self.slot.ui.stk_effects.currentIndex.return_value = 0  # the Fade page
        self.slot._update_apply_readout("highlight")
        self.slot.ui.footer.setDefaultStatusText.assert_not_called()

    def test_revise_reaches_only_objects_that_already_carry_the_channel(self):
        """The point of the mode: change this, do not spread it."""
        plain = cmds.polyCube(name="slot_unkeyed")[0]
        mtk.RenderEffects.create([self.cube], mode="attribute", channel="highlight")
        cmds.select([self.cube, plain], replace=True)
        self._set_mode(REVISE)

        self.assertEqual(self.slot._targets("highlight"), [self.cube])

    def test_create_reaches_the_whole_selection(self):
        plain = cmds.polyCube(name="slot_unkeyed2")[0]
        cmds.select([self.cube, plain], replace=True)
        self._set_mode(CREATE)

        self.assertEqual(
            sorted(self.slot._targets("highlight")), sorted([self.cube, plain])
        )

    # ---- the colour row ------------------------------------------------------

    def test_revise_seeds_the_row_from_what_is_authored(self):
        """Seeding from the authored value is what makes this a revision
        rather than a guess -- and the same read decides the before/after."""
        mtk.RenderEffects.create([self.cube], mode="attribute", channel="highlight")
        mtk.RenderEffects.set_channel_color([self.cube], color=(0.02, 0.17, 0.43))
        cmds.select(self.cube, replace=True)
        self._set_mode(REVISE)

        self.slot._sync_highlight_mode()

        seeded = self.slot._pulse_ramp.set_colors.call_args.args[0]
        self.assertEqual([round(c, 2) for c in seeded[0]], [0.02, 0.17, 0.43])
        reference = self.slot._pulse_ramp.set_reference.call_args.args[0]
        self.assertIsNotNone(reference, "one agreed look is a look to hold up")

    def test_a_disagreement_shows_no_before(self):
        """Picking one of them to show would be a lie about what is there."""
        other = cmds.polyCube(name="slot_other3")[0]
        for node in (self.cube, other):
            mtk.RenderEffects.create([node], mode="attribute", channel="highlight")
        mtk.RenderEffects.set_channel_color([self.cube], color=(1.0, 0.0, 0.0))
        mtk.RenderEffects.set_channel_color([other], color=(0.0, 1.0, 0.0))
        cmds.select([self.cube, other], replace=True)
        self._set_mode(REVISE)

        self.slot._sync_highlight_mode()

        self.assertIsNone(self.slot._pulse_ramp.set_reference.call_args.args[0])

    def test_switching_into_revise_reads_the_scene_when_nothing_is_selected(self):
        """The hole this closes: with no selection the row showed colours
        nobody had read off these objects, and Key -- whose scope here is
        every highlighted object -- would have written them over all of them."""
        mtk.RenderEffects.create([self.cube], mode="attribute", channel="highlight")
        mtk.RenderEffects.set_channel_color([self.cube], color=(0.02, 0.17, 0.43))
        cmds.select(clear=True)
        self._set_mode(REVISE)

        self.slot._sync_highlight_mode(deep=True)

        seeded = self.slot._pulse_ramp.set_colors.call_args.args[0]
        self.assertEqual([round(c, 2) for c in seeded[0]], [0.02, 0.17, 0.43])

    def test_the_selection_path_never_scans_the_scene(self):
        """That scan is one pass over every object; on the selection-changed
        signal it would make picking objects cost a pass per click."""
        mtk.RenderEffects.create([self.cube], mode="attribute", channel="highlight")
        cmds.select(clear=True)
        self._set_mode(REVISE)

        self.slot._sync_highlight_mode()  # shallow: what the signal does

        self.slot._pulse_ramp.set_colors.assert_not_called()

    def test_create_shows_the_recipes_colours(self):
        """Create keys with the scene's recipe, so the row shows its colours --
        not the clicked object's, and not a seed the recipe never had."""
        mtk.RenderEffects.create([self.cube], mode="attribute", channel="highlight")
        mtk.RenderEffects.set_channel_color([self.cube], color=(1.0, 0.0, 0.0))
        cmds.select(self.cube, replace=True)
        self._recipe(pulse_bright=(0.0, 1.0, 0.0), pulse_dim=(0.1, 0.0, 0.0))
        self._set_mode(CREATE)
        self.slot._pulse_ramp.editors = ()

        self.slot._sync_highlight_mode()

        seeded = self.slot._pulse_ramp.set_colors.call_args.args[0]
        self.assertEqual(seeded, ((0.0, 1.0, 0.0), (0.1, 0.0, 0.0)))
        self.assertIsNone(self.slot._pulse_ramp.set_reference.call_args.args[0])

    def test_a_create_colour_is_the_recipes_and_no_objects(self):
        """In Create a committed colour is what the next pulse -- and a
        channel the manifest's Build creates -- is coloured with. It writes
        the scene's recipe, never the selection."""
        mtk.RenderEffects.create([self.cube], mode="attribute", channel="highlight")
        mtk.RenderEffects.set_channel_color([self.cube], color=(0.9, 0.1, 0.1))
        cmds.select(self.cube, replace=True)
        store = self._recipe()
        self._set_mode(CREATE)
        self.slot._pulse_ramp.decided.return_value = ((0.0, 0.0, 1.0), None)

        self.slot._on_pulse_color_committed(0, None)

        self.assertEqual(store.effect_recipe.pulse_bright, (0.0, 0.0, 1.0))
        self.assertEqual(
            [round(c, 3) for c in cmds.getAttr(f"{self.cube}.highlightColor")[0]],
            [0.9, 0.1, 0.1],
            "the page stages a look; only Key writes the objects",
        )

    def test_a_revise_colour_is_never_the_recipes(self):
        store = self._recipe()
        before = store.effect_recipe.pulse_bright
        self._set_mode(REVISE)
        self.slot._pulse_ramp.decided.return_value = ((0.0, 0.0, 1.0), None)
        self.slot._on_pulse_color_committed(0, None)
        self.assertEqual(store.effect_recipe.pulse_bright, before)

    def test_revise_writes_the_selection(self):
        mtk.RenderEffects.create([self.cube], mode="attribute", channel="highlight")
        cmds.select(self.cube, replace=True)
        self._set_mode(REVISE)
        self.slot._pulse_ramp.decided.return_value = ((0.02, 0.17, 0.43), None)

        self.slot._key_pulse_page()

        self.assertEqual(
            [round(c, 3) for c in cmds.getAttr(f"{self.cube}.highlightColor")[0]],
            [0.02, 0.17, 0.43],
        )
        # A selection is unambiguous: it must not ask.
        self.slot.sb.message_box.assert_not_called()

    def test_revise_confirms_before_the_whole_scene(self):
        mtk.RenderEffects.create([self.cube], mode="attribute", channel="highlight")
        cmds.select(clear=True)
        self._set_mode(REVISE)
        self.slot._pulse_ramp.decided.return_value = ((1.0, 0.0, 0.0), None)
        self.slot.sb.message_box.return_value = "No"

        self.slot._key_pulse_page()

        self.assertEqual(
            [round(c, 6) for c in cmds.getAttr(f"{self.cube}.highlightColor")[0]],
            [0.0, 0.088656, 0.723055],
            "declining the confirm must write nothing",
        )

        self.slot.sb.message_box.return_value = "Yes"
        self.slot._key_pulse_page()

        self.assertEqual(
            [round(c, 3) for c in cmds.getAttr(f"{self.cube}.highlightColor")[0]],
            [1.0, 0.0, 0.0],
        )

    def test_the_editor_is_seeded_from_the_authored_colour(self):
        """Opening on the last PICK rather than what the objects carry would make
        this a guess; the revision has to start from the authored value."""
        mtk.RenderEffects.create([self.cube], mode="attribute", channel="highlight")
        mtk.RenderEffects.set_channel_color([self.cube], color=(0.02, 0.17, 0.43))
        mtk.RenderEffects.set_channel_color(
            [self.cube], color=(0.5, 0.0, 0.0), stop="lo"
        )

        (bright, dim), mixed = self.slot._authored_stops([self.cube])

        self.assertEqual([round(c, 2) for c in bright], [0.02, 0.17, 0.43])
        self.assertEqual([round(c, 2) for c in dim], [0.5, 0.0, 0.0])
        self.assertEqual(mixed, (False, False))

    def test_a_selection_that_disagrees_reports_mixed(self):
        """The old reader took ``next(iter(...))``, so a multi-object edit
        showed ONE object's colour and the first drag wrote it to all of them."""
        other = cmds.polyCube(name="slot_other")[0]
        for node in (self.cube, other):
            mtk.RenderEffects.create([node], mode="attribute", channel="highlight")
        mtk.RenderEffects.set_channel_color([self.cube], color=(1.0, 0.0, 0.0))
        mtk.RenderEffects.set_channel_color([other], color=(0.0, 1.0, 0.0))

        _seeds, mixed = self.slot._authored_stops([self.cube, other])

        self.assertTrue(mixed[0], "the bright end disagrees and must say so")
        self.assertFalse(mixed[1], "both dim ends are still the seeded black")

    def test_an_end_left_mixed_is_not_written(self):
        """An artist who only touched Bright must not flatten every Dim."""
        other = cmds.polyCube(name="slot_other2")[0]
        for node in (self.cube, other):
            mtk.RenderEffects.create([node], mode="attribute", channel="highlight")
        mtk.RenderEffects.set_channel_color(
            [self.cube], color=(0.1, 0.1, 0.1), stop="lo"
        )
        cmds.select([self.cube, other], replace=True)
        self._set_mode(REVISE)
        self.slot._pulse_ramp.decided.return_value = ((1.0, 0.0, 0.0), None)

        self.slot._key_pulse_page()

        self.assertEqual(
            [round(c, 3) for c in cmds.getAttr(f"{self.cube}.highlightColorDim")[0]],
            [0.1, 0.1, 0.1],
            "an unstated end must be left exactly as authored",
        )

    def test_revise_with_nothing_decided_writes_nothing(self):
        """Both ends mixed means the artist decided nothing; writing would
        flatten a disagreement into whatever the row happened to show."""
        other = cmds.polyCube(name="slot_other4")[0]
        for node in (self.cube, other):
            mtk.RenderEffects.create([node], mode="attribute", channel="highlight")
        mtk.RenderEffects.set_channel_color([self.cube], color=(1.0, 0.0, 0.0))
        mtk.RenderEffects.set_channel_color([other], color=(0.0, 1.0, 0.0))
        cmds.select([self.cube, other], replace=True)
        self._set_mode(REVISE)
        self.slot._pulse_ramp.decided.return_value = (None, None)

        self.slot._key_pulse_page()

        self.assertEqual(
            [round(c, 3) for c in cmds.getAttr(f"{self.cube}.highlightColor")[0]],
            [1.0, 0.0, 0.0],
            "an undecided revision must write nothing",
        )
        self.slot.sb.message_box.assert_called()

    def test_the_cycle_readout_names_a_cut_tail(self):
        """A length that is not a whole multiple of the period ends mid-cycle.
        Nothing is wrong with that; it is invisible without a number."""
        from unittest.mock import MagicMock

        self.slot._cycle_readout = MagicMock()
        page = self._pulse_page(seconds=4.0, period=2.0, gaps=(0.0, 0.0))
        self.slot._update_cycle_readout()
        self.assertNotIn("cut", self.slot._cycle_readout.setText.call_args.args[0])

        page.s001.value.return_value = 5.0
        self.slot._update_cycle_readout()
        self.assertIn("cut", self.slot._cycle_readout.setText.call_args.args[0])

        # The leads come out of the length: 5 s less two 0.5 s leads is a
        # train of exactly two 2 s cycles.
        self._recipe(pulse_lead_in=0.5, pulse_lead_out=0.5)
        self.slot._update_cycle_readout()
        self.assertNotIn("cut", self.slot._cycle_readout.setText.call_args.args[0])

    def test_remove_action_strips_one_channel_and_leaves_the_other(self):
        self._fade_page()
        self._pulse_page()
        self.slot._key_fade_page()
        self.slot._key_pulse_page()

        self.slot._remove_channel("opacity")

        self.assertFalse(cmds.attributeQuery("opacity", node=self.cube, exists=True))
        self.assertTrue(cmds.attributeQuery("highlight", node=self.cube, exists=True))
        self.slot.sb.message_box.assert_not_called()


if __name__ == "__main__":
    unittest.main()
