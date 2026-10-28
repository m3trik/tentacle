# !/usr/bin/python
# coding=utf-8
"""Channels: the selected objects' attributes in one editable table.

One Slots class for both hosts over the host toolkit's ``Channels`` engine
(``self.tk``): Maya's node attributes, Blender's transform channels and custom
properties. One row per attribute the selection shares -- Name | Lock | Key |
Value | Type -- with a filter combo, a wildcard name filter, the target's name
(double-click to rename) and a single-object toggle. Rows are keyed by
attribute name; every host call takes those names.

* **Lock / Key icons**: a click toggles that row, a drag sets every row it
  crosses (Alt clears, Ctrl breaks what drives it), as one undo step.
* **Value cells**: typed edits, MMB scrub and wheel steps, each one undo step
  across the selection; enum attributes get a combobox.
* **Live**: the engine reports scene events (``watch_scene``) and, where the
  host has them, per-node attribute callbacks (``watch_nodes``); the panel
  coalesces them into one rebuild or one in-place values pass.

What one host lacks is gated on the engine class
(``getattr(self.tk.Channels, name, None)``): Maya's channel-box sync
(``link_channel_box``), its keyable and channel-box-visibility flags
(``toggle_keyable``, ``hide_attrs`` ...), the footer's Shape / History
selection (``get_shape_nodes``), enum attributes (``get_enum_fields``) and the
per-node callbacks (``watch_nodes``). Blender has no channel box, no keyable or
visibility flag on a property, no shape or history node and no enum custom
property, so those controls are not built there; its per-object live callbacks
are the one gap still to build (see ``_register_attr_change_callbacks``).

The Qt helpers (the Create Attribute form, the enum cell, the inline renames)
are in :mod:`._channels`.
"""

import logging

import pythontk as ptk
from qtpy import QtCore, QtWidgets

from tentacle import Slots

from ._channels.attribute_form import AttributeForm
from ._channels.enum_cell import EnumCell
from ._channels.inline_rename import FooterRename, InlineRename

_log = logging.getLogger(__name__)


class ChannelsSlots(Slots):
    """Switchboard slots for the ``channels.ui`` panel."""

    # Column indices -- Name | Lock | Key (connection) | Value | Type
    COL_NAME = 0
    COL_LOCK = 1
    COL_CONN = 2
    COL_VALUE = 3
    COL_TYPE = 4
    HEADERS = ["Name", "", "", "Value", "Type"]

    _ROW_SELECTION_COLUMNS = {"name": 0, "value": 3, "type": 4}

    #: Every icon / state colour. Desaturated channel-box scheme: pink for a
    #: plain incoming connection, reds for animation (lighter: keyed, deeper: a
    #: key on this frame, lightest: a keyed value moved off its curve).
    ACTION_COLOR_MAP = {
        "off": "#555555",  # dim grey -- inactive / default
        "active": "#6898b8",  # desat blue -- toggle on (not red: keys are red)
        "locked": "#8a9bb0",  # bluish grey -- lock icon
        "connected": "#c89c9c",  # desat pink -- generic connection
        "keyframe": "#c86464",  # desat red -- keyed (no key at current time)
        "keyframe_active": "#a83838",  # deeper red -- key at current time
        "keyframe_changed": "#f08080",  # lighter red -- changed, not keyed
        "expression": "#b478c8",  # desat purple -- expression-driven
        "driven_key": "#6898b8",  # desat light-blue -- driven key / driver
        "constraint": "#5878b8",  # desat blue -- constraint
        "muted": "#888850",  # olive -- muted channel
    }

    #: The Key column's states, ``(state, label)``; the engine's
    #: ``KEYABLE_STATES`` says which of them a plain click keys.
    _CONN_STATES = (
        ("none", "Not connected"),
        ("keyframe", "Animated"),
        ("keyframe_active", "Key set at current time"),
        (
            "keyframe_changed",
            "Value changed but not keyed — the next frame change discards it",
        ),
        ("connected", "Connected"),
        ("expression", "Expression"),
        ("driven_key", "Driven"),
        ("constraint", "Constraint"),
        ("muted", "Muted"),
    )

    #: The table's right-click menu: a section ``(title, None)`` or an item
    #: ``(label, objectName, tooltip, handler, engine method it needs)``. An
    #: item whose engine method the host lacks is not built: Blender has no
    #: channel box, so no keyable or channel-box visibility flag to set.
    _CONTEXT_ITEMS = (
        ("Edit", None),
        ("Lock", "ctx_lock", "Lock the selected attribute(s).", "_ctx_lock", None),
        (
            "Unlock",
            "ctx_unlock",
            "Unlock the selected attribute(s).",
            "_ctx_unlock",
            None,
        ),
        (
            "Lock and Hide",
            "ctx_lock_and_hide",
            "Lock the attribute and hide it from the channel box.",
            "_ctx_lock_and_hide",
            "lock_and_hide_attrs",
        ),
        (
            "Hide Selected",
            "ctx_hide",
            "Hide the attribute from the channel box.",
            "_ctx_hide",
            "hide_attrs",
        ),
        (
            "Show Selected",
            "ctx_show",
            "Show (unhide) the attribute in the channel box.",
            "_ctx_show",
            "show_attrs",
        ),
        (
            "Reset to Default",
            "ctx_reset_default",
            "Reset the attribute to its default value.",
            "_ctx_reset_default",
            None,
        ),
        (
            "Toggle Keyable",
            "ctx_toggle_keyable",
            "Toggle the keyable state of the attribute.",
            "_ctx_toggle_keyable",
            "toggle_keyable",
        ),
        ("Values", None),
        (
            "Copy Values",
            "ctx_copy_values",
            "Copy the selected attributes' values.",
            "_ctx_copy_values",
            None,
        ),
        (
            "Paste Values",
            "ctx_paste_values",
            "Paste copied values onto the selected object(s).",
            "_ctx_paste_values",
            None,
        ),
        ("Animation", None),
        (
            "Breakdown",
            "ctx_breakdown",
            "Set a breakdown key on the selected attribute(s).",
            "_ctx_breakdown",
            None,
        ),
        (
            "Mute",
            "ctx_mute",
            "Mute the selected attribute(s): suppress their animation.",
            "_ctx_mute",
            None,
        ),
        (
            "Unmute",
            "ctx_unmute",
            "Unmute the selected attribute(s).",
            "_ctx_unmute",
            None,
        ),
        (
            "Select Connection",
            "ctx_select_connection",
            "Select what drives this attribute (its source node, or a driver's "
            "or constraint's target).",
            "_ctx_select_connection",
            None,
        ),
        (
            "Break Connection",
            "ctx_break_connection",
            "Break what drives the selected attribute(s): a connection, "
            "animation or driver.",
            "_ctx_break_connection",
            None,
        ),
        ("Transform", None),
        (
            "Freeze Transforms",
            "ctx_freeze_transforms",
            "Freeze transforms on the selected object(s), storing the original "
            "so the freeze can be reversed.",
            "_ctx_freeze_transforms",
            None,
        ),
        (
            "Unfreeze Transforms",
            "ctx_unfreeze_transforms",
            "Restore previously frozen transforms on the selected object(s).",
            "_ctx_unfreeze_transforms",
            None,
        ),
        ("Manage", None),
        (
            "Delete Attribute",
            "ctx_delete",
            "Delete the selected custom attribute(s).",
            "_ctx_delete",
            None,
        ),
    )

    #: Menu items that act on the selected objects with no row highlighted.
    _NODE_LEVEL_ACTIONS = frozenset(
        {"ctx_freeze_transforms", "ctx_unfreeze_transforms", "ctx_paste_values"}
    )

    _FREEZE_TIP_ENABLED = (
        "Freeze the selected transform(s).\nStores the pre-freeze transforms so "
        "the operation can be reversed with Unfreeze Transforms."
    )
    _FREEZE_TIP_DISABLED = (
        "Freeze unavailable — a freeze applies whole groups (move, rotate, "
        "scale).\nSelect either nothing (to freeze everything) or every axis of "
        "the group(s) to freeze. Other attributes in the selection also "
        "disable this."
    )
    _UNFREEZE_TIP_ENABLED = (
        "Restore the selected channel group(s) from the stored pre-freeze "
        "transforms.\nWith no row selection, every transform channel is restored."
    )
    _UNFREEZE_TIP_BAD_SELECTION = (
        "Unfreeze unavailable — restore follows the same group rules as "
        "Freeze.\nSelect either nothing (to restore everything) or every axis "
        "of the group(s) to restore."
    )
    _UNFREEZE_TIP_NO_STORED = (
        "Unfreeze unavailable — no stored freeze data on the selected "
        "object(s). Use Freeze Transforms first."
    )

    # MMB scrub: a float moves this much per pixel, an int one unit per this
    # many pixels; Ctrl x0.1 (fine), Shift x10 (coarse), read live mid-drag.
    _SCRUB_FLOAT_STEP = 0.01
    _SCRUB_INT_PIXELS_PER_UNIT = 4

    # Wheel step per notch -- uitk's WheelStepMixin ladder: Ctrl scales up
    # (x10, x100 with Shift), Alt down (/10; smallest with Ctrl). The float
    # smallest is the engines' display precision (4 decimals), so the visible
    # last digit steps. An int has no sub-1 step: Alt consumes the notch.
    _WHEEL_FLOAT_STEP = 0.1  # plain
    _WHEEL_FLOAT_COARSE = 1.0  # Ctrl         (x10)
    _WHEEL_FLOAT_VERY_COARSE = 10.0  # Ctrl+Shift   (x100)
    _WHEEL_FLOAT_FINE = 0.01  # Alt          (/10)
    _WHEEL_FLOAT_SMALLEST = 0.0001  # Ctrl+Alt     (smallest shown)
    _WHEEL_INT_COARSE = 10  # Ctrl on int
    _WHEEL_INT_VERY_COARSE = 100  # Ctrl+Shift on int
    _WHEEL_INT_SMALLEST = 1  # Ctrl+Alt on int
    _WHEEL_INT_FINE = 0  # Alt on int: nothing finer than 1

    def __init__(self, switchboard):
        super().__init__(switchboard)
        self.ui = self.sb.loaded_ui.channels
        self.controller = self.tk.Channels()
        self._compact_view = False
        self._base_row_height = None  # snapshotted on first _apply_row_height
        self._current_target = None
        self._filter_invert = False
        self._filter_enabled = True
        self._footer_compact_btn = None
        self._footer_rename = None
        self._combo_setting = False

        # Live-update state. Bursts of scene events (value drags, batch edits,
        # playback) are coalesced: names collect in the pending sets and one
        # deferred pass drains them; a rebuild or values pass already pending
        # absorbs the next request.
        self._refresh_pending = False
        self._values_refresh_pending = False
        self._pending_value_attrs = set()
        self._pending_lock_attrs = set()
        self._attr_flush_pending = False
        self._attr_change_tokens = []
        self._destroyed = False
        self._watching = False
        # Hops a callback from a host's worker thread (Maya's Evaluation
        # Manager fires the matrix callback there) onto the GUI thread.
        self._gui_thread = ptk.MainThreadMarshaller()

        # Re-entry guards for _refresh_table: a rebuild that pumps the event
        # loop (cell-widget teardown, a queued combo signal) must not start a
        # second one over the half-torn rows.
        self._refreshing = False
        self._refresh_queued = False

        # Channel-box sync (hosts with one): the last selection either side
        # reported, and a guard against the two echoing each other.
        self._last_cb_selection = set()
        self._syncing_selection = False

        # MMB scrub state (_on_scrub_started) and the undo chunk a drag-fill
        # holds open (_on_edit_batch_started).
        self._scrub_state = None
        self._edit_chunk = None

        self._footer_controller = self._create_footer_controller()
        # A first pass; tbl000_init re-wires on every init, since the table
        # can outlive a slots instance and keep bindings to a dead one.
        self._wire_table_signals(self.ui.tbl000)

        # Name filter: a debounced refresh, and an on/off action on its option
        # box (its callback runs before the cycle advances, so it sets the NEXT
        # state; no settings_key, so it cannot drift from _filter_enabled).
        self._filter_timer = QtCore.QTimer()
        self._filter_timer.setSingleShot(True)
        self._filter_timer.setInterval(200)
        self._filter_timer.timeout.connect(lambda: self._refresh_table(self.ui.tbl000))
        self.ui.txt000.textChanged.connect(lambda *_: self._filter_timer.start())
        self.ui.txt000.option_box.clear_option = True
        clr = self.ACTION_COLOR_MAP
        self.ui.txt000.option_box.add_action(
            icon="filter",
            tooltip="Toggle name filter",
            states=[
                {
                    "icon": "filter",
                    "tooltip": "Filter ON — click to disable",
                    "color": clr["active"],
                    "callback": lambda: self._set_filter_enabled(False),
                },
                {
                    "icon": "filter",
                    "tooltip": "Filter OFF — click to enable",
                    "color": clr["off"],
                    "callback": lambda: self._set_filter_enabled(True),
                },
            ],
            settings_key=False,
        )
        self.ui.destroyed.connect(self._filter_timer.stop)

        # txt001: the target's name, double-click to rename; its option box
        # carries the single-object toggle ("target", not "pin": no clash with
        # the PinValuesOption plugin).
        self._target_rename = InlineRename(
            self.ui.txt001, self._target_label, self._rename_target
        )
        self._target_action = self.ui.txt001.option_box.add_action(
            icon="target",
            tooltip="Single-object mode",
            states=self._target_toggle_states(),
            settings_key=False,
        )

        self._setup_compact_footer()

    # ------------------------------------------------------------------
    # Launch
    # ------------------------------------------------------------------

    @staticmethod
    def launch(sb, targets=None, filter=None, search=None):
        """Open the panel, optionally pre-targeted (:meth:`apply_launch_config`).

        Parameters:
            sb (Switchboard): The caller's switchboard (``self.sb``).
            targets (list | None): Objects to pin; ``None`` clears a pin.
            filter (str | None): A ``Channels.FILTER_MAP`` key to show.
            search (str | None): The name-filter pattern (``""`` clears it).

        Returns:
            The shown ``channels`` window.
        """
        ui = sb.handlers.marking_menu.show("channels")
        slots = sb.get_slots_instance(ui)
        if slots is not None:
            slots.apply_launch_config(targets=targets, filter=filter, search=search)
        return ui

    def apply_launch_config(self, targets=None, filter=None, search=None):
        """Pin *targets*, pick *filter* and set the *search* pattern, then refresh.

        Safe to call repeatedly. ``targets=None`` clears a pin; an unknown
        *filter* is logged and ignored.
        """
        self.controller.pin_targets(targets)
        if filter:
            if filter in self.controller.FILTER_MAP:
                self.ui.cmb000.setCurrentText(filter)
            else:
                _log.warning(
                    "launch(filter=%r) ignored — not a FILTER_MAP key. Valid: %s",
                    filter,
                    sorted(self.controller.FILTER_MAP),
                )
        if search is not None:
            self.ui.txt000.setText(search)
        self._refresh_table(self.ui.tbl000)

    def _host_has(self, name):
        """Whether the host engine offers *name* (a capability one host lacks)."""
        return callable(getattr(self.tk.Channels, name, None))

    # ------------------------------------------------------------------
    # Header
    # ------------------------------------------------------------------

    def header_init(self, widget):
        """Create Attribute, the view toggles and the host's own editors."""
        widget.menu.add("Separator", setTitle="Create")
        widget.menu.add(
            "QPushButton",
            setText="Create Attribute …",
            setToolTip="Add a new custom attribute to the selected objects.",
            setObjectName="show_create_menu",
        )

        widget.menu.add("Separator", setTitle="Visibility")
        self._chk_show_type = widget.menu.add(
            "QCheckBox",
            setText="Show Type",
            setChecked=False,
            setToolTip="Toggle the Type column in the attribute table.",
            setObjectName="chk_show_type",
        )
        self._chk_show_type.toggled.connect(self._on_toggle_type_column)
        self._chk_compact = widget.menu.add(
            "QCheckBox",
            setText="Compact View",
            setChecked=True,
            setToolTip="Reduce row height, hide the column header and move the "
            "object name into the footer.",
            setObjectName="chk_compact_view",
        )
        self._chk_compact.toggled.connect(self._on_toggle_compact_view)
        self._chk_auto_fit = widget.menu.add(
            "QCheckBox",
            setText="Auto-fit Window",
            setChecked=True,
            setToolTip="Resize columns to fit contents and grow/shrink the "
            "window to match on every refresh.",
            setObjectName="chk_auto_fit",
        )
        self._chk_auto_fit.toggled.connect(self._on_toggle_auto_fit)
        # Compact view is push-only: reconcile it with the (possibly restored)
        # box now, or a first launch leaves it checked but unapplied (a restore
        # re-emits toggled only when the stored value differs from the default).
        self._sync_compact_default()

        # The host's own channel editors (Maya: Channel Control, Connection
        # Editor; Blender: Properties, Drivers, Graph).
        editors = dict(self.controller.EDITORS)
        if editors:
            widget.menu.add("Separator", setTitle="Editors")
        for key, (label, tooltip) in editors.items():
            button = widget.menu.add(
                "QPushButton",
                setText=f"{label} …",
                setObjectName=f"hdr_{key}",
                setToolTip=tooltip,
            )
            button.clicked.connect(lambda *_, k=key, n=label: self._open_editor(k, n))

        widget.set_help_text(self._help_text())

    def _help_text(self):
        kbd = self.sb.tooltip.kbd
        sections = [
            (
                "Table",
                [
                    "Each row is one attribute the selection shares; an edit "
                    "applies to every selected object.",
                    "Edit a value in place, or wheel-scrub / middle-drag over a "
                    "value cell.",
                    "Click a lock / key icon to toggle that row.",
                    "Drag down a column to lock / key every row it crosses; "
                    f"{kbd('Alt')}+drag to unlock / remove those keys.",
                    f"{kbd('Ctrl')}+click or drag the key column to break what "
                    "drives the attribute.",
                    "Double-click a custom attribute's name to rename it.",
                    "Right-click rows for lock, reset, copy / paste, mute and "
                    "freeze actions.",
                ],
            ),
            (
                "Wheel-scrub modifiers",
                [
                    "plain &mdash; ×1",
                    f"{kbd('Ctrl')} &mdash; ×10 (coarse)",
                    f"{kbd('Ctrl', 'Shift')} &mdash; ×100 (very coarse)",
                    f"{kbd('Alt')} &mdash; ÷10 (fine)",
                    f"{kbd('Ctrl', 'Alt')} &mdash; smallest representable step",
                ],
            ),
            (
                "Filter and target",
                [
                    "The combo picks which attributes show (<b>Custom</b>, "
                    "<b>Keyable</b>, <b>Locked</b> …); its option box inverts it.",
                    "The name field filters by wildcard; its option box turns it off.",
                    "The field below names the target: double-click to rename. "
                    "Its target icon shows and edits only the active object.",
                ],
            ),
            (
                "Header menu",
                [
                    "<b>Create Attribute …</b> — add a custom attribute.",
                    "<b>Compact View</b> — shorter rows; the object name moves to "
                    "the footer.",
                    "<b>Auto-fit Window</b> — resize columns and grow/shrink the "
                    "window to match contents on every refresh.",
                    "<b>Editors</b> — open the application's own channel editors.",
                ],
            ),
        ]
        if self._host_has("get_shape_nodes"):
            sections.append(
                (
                    "Selection helpers (footer)",
                    [
                        "<b>Shape</b> (cube icon) — select the shape node(s) of "
                        "the current selection.",
                        "<b>History</b> (history icon) — select the "
                        "construction-history node(s).",
                    ],
                )
            )
        return self.sb.tooltip.fmt(
            title="Channels",
            body="Inspect, edit, lock and key the selected objects' attributes "
            "in a spreadsheet-style table, with bulk operations and wheel-scrub "
            "editing (Blender: transform channels and custom properties).",
            sections=sections,
        )

    def _open_editor(self, key, label):
        """Open the host's *key* editor; say so when it cannot."""
        if not self.controller.open_editor(key):
            self.sb.message_box(f"Could not open {label}.")

    def show_create_menu(self, *args):
        """Show the Create Attribute form."""
        AttributeForm.show(
            self.sb,
            self.ui,
            self.controller.CREATE_TYPES,
            self._create_attribute,
            keyable=self._host_has("toggle_keyable"),
        )

    def _create_attribute(self, name, attr_type, **options):
        """The form's Create: True when the attribute was made (the form closes)."""
        if not name:
            self.sb.message_box("Warning: Attribute name cannot be empty.")
            return False
        # The panel's targets (pins, single-object mode), not the raw selection.
        nodes = self._selected_nodes()
        if not nodes:
            self.sb.message_box("Warning: Nothing selected.")
            return False
        try:
            self.controller.create_attribute(nodes, name, attr_type, **options)
        except RuntimeError as error:
            self.sb.message_box(f"Error: {error}")
            return False
        self._refresh_table(self.ui.tbl000)
        return True

    def _on_toggle_type_column(self, visible):
        self.ui.tbl000.setColumnHidden(self.COL_TYPE, not visible)

    def _on_toggle_auto_fit(self, _enabled):
        """Re-apply column sizing when the auto-fit toggle changes."""
        self._refresh_table(self.ui.tbl000)

    # ------------------------------------------------------------------
    # Compact view, target display, footer
    # ------------------------------------------------------------------

    def _sync_compact_default(self):
        """Apply the Compact View box's state when it differs from the panel's.

        Pull model for a push-only toggle: idempotent and cheap, so every
        refresh calls it (a restore may land after the first refresh).
        """
        chk = getattr(self, "_chk_compact", None)
        if chk is None:
            return
        checked = chk.isChecked()
        if checked != self._compact_view:
            self._on_toggle_compact_view(checked)

    def _on_toggle_compact_view(self, enabled):
        """Shorter rows, no column header, the target's name in the footer."""
        leaving_compact = self._compact_view and not enabled
        self._compact_view = bool(enabled)
        tbl = self.ui.tbl000
        if self._is_widget_alive(tbl):
            # The table's column-label strip, not the window's header.
            tbl.horizontalHeader().setVisible(not self._compact_view)
            self._apply_row_height(tbl)
        txt1 = self.ui.txt001
        try:
            (getattr(txt1, "container", None) or txt1).setVisible(
                not self._compact_view
            )
        except Exception:  # noqa: BLE001 -- the field is going away
            pass
        if self._footer_compact_btn is not None:
            try:
                self._footer_compact_btn.setVisible(self._compact_view)
            except Exception:  # noqa: BLE001
                pass
        # Single-object mode is a compact-footer affordance: drop it with
        # compact view, through the toggle so every widget re-syncs.
        if leaving_compact and self.controller.single_object_mode:
            self._on_toggle_single_object(False)
        self._update_footer()

    def _apply_row_height(self, widget):
        """Normal rows at the table's natural height, compact ones at 80% (>=12px).

        The natural height is snapshotted on the first call so toggling always
        returns to it. ``Fixed`` sections, so rows shrink below their content's
        preferred height and the default size governs every row.
        """
        vh = widget.verticalHeader()
        vh.setSectionResizeMode(QtWidgets.QHeaderView.Fixed)
        if self._base_row_height is None:
            self._base_row_height = max(vh.defaultSectionSize(), 18)
        base = self._base_row_height
        height = max(int(base * 0.8), 12) if self._compact_view else base
        # The style's minimumSectionSize (~20px) silently clamps the default.
        vh.setMinimumSectionSize(min(height, vh.minimumSectionSize()))
        vh.setDefaultSectionSize(height)
        for row in range(widget.rowCount()):
            widget.setRowHeight(row, height)
        # Re-fit the icon columns to the row height, or icons clip.
        try:
            widget.actions.update_for_row_height()
        except AttributeError:
            pass

    def _target_toggle_states(self):
        """The single / multi-object toggle's states (txt001 and the footer).

        0 = multi-object (off tint), 1 = single-object (active tint). A state's
        callback sets the NEXT mode; _on_toggle_single_object then syncs every
        toggle explicitly.
        """
        clr = self.ACTION_COLOR_MAP
        return [
            {
                "icon": "target",
                "tooltip": "Multi-object mode — click to switch to single-object.\n"
                "Edits apply to every selected object.",
                "color": clr["off"],
                "callback": lambda: self._on_toggle_single_object(True),
            },
            {
                "icon": "target",
                "tooltip": "Single-object mode — click to switch to multi-object.\n"
                "Only the active (last selected) object is shown and edited.",
                "color": clr["active"],
                "callback": lambda: self._on_toggle_single_object(False),
            },
        ]

    def _on_toggle_single_object(self, enabled):
        self.controller.single_object_mode = bool(enabled)
        self._sync_target_toggles()
        self._refresh_table(self.ui.tbl000)

    def _sync_target_toggles(self):
        """Point both single / multi toggles at the engine's mode."""
        idx = 1 if self.controller.single_object_mode else 0
        action = getattr(self, "_target_action", None)
        if action is not None:
            action.current_state = idx
        cycle = getattr(self._footer_compact_btn, "icon_states", None)
        if cycle is not None:
            cycle.current_state = idx

    def _set_filter_enabled(self, enabled):
        self._filter_enabled = bool(enabled)
        self._refresh_table(self.ui.tbl000)

    def _target_label(self, full=False):
        """The target's name (its full path with *full*); ``None`` for none.

        A target the host no longer has (a deleted object) is dropped.
        """
        target = self._current_target
        if target is None:
            return None
        name = self.controller.node_name(target, full=full)
        if name is None:
            self._current_target = None
        return name

    def _update_target_display(self, nodes):
        """Show the target(s) in txt001."""
        txt = self.ui.txt001
        was_blocked = txt.blockSignals(True)
        try:
            names = [self.controller.node_name(n) for n in nodes]
            if not nodes:
                self._current_target = None
                txt.setText("")
                txt.setToolTip("No selection")
            elif len(nodes) == 1:
                self._current_target = nodes[0]
                txt.setText(names[0] or "")
                full = self.controller.node_name(nodes[0], full=True)
                txt.setToolTip(f"{full}\n\n(Double-click to rename.)")
            else:
                self._current_target = None
                txt.setText(f"Multi-selection ({len(nodes)})")
                listed = "\n".join(f"  • {n}" for n in names)
                txt.setToolTip(f"Selected objects:\n{listed}")
            txt.setReadOnly(True)
        finally:
            txt.blockSignals(was_blocked)

    def _rename_target(self, new_name):
        """Rename the single target (txt001 or the footer), keeping a pin on it."""
        old = self._current_target
        if old is None:
            return
        new = self.controller.rename_node(old, new_name)
        if new is not None and new != old:
            self._current_target = new
            if self.controller.is_pinned:
                self.controller.pin_targets([new])
        self._refresh_table(self.ui.tbl000)

    def _update_footer(self):
        if self._footer_controller is not None:
            try:
                self._footer_controller.update()
            except Exception:  # noqa: BLE001 -- the footer is going away
                pass

    def _create_footer_controller(self):
        footer = getattr(self.ui, "footer", None)
        if not footer:
            return None
        return footer.status_controller(
            resolver=self._resolve_footer_text,
            default_text="",
            truncate_kwargs={"length": 96, "mode": "middle"},
        )

    def _resolve_footer_text(self):
        """In compact view, the target's name as txt001 shows it."""
        if self._compact_view:
            try:
                return self.ui.txt001.text()
            except Exception:  # noqa: BLE001
                pass
        return ""

    def _setup_compact_footer(self):
        """The footer's inline rename, Shape / History buttons and target toggle."""
        footer = getattr(self.ui, "footer", None)
        if not footer:
            return
        try:
            self._footer_rename = FooterRename(
                footer,
                can_edit=lambda: (
                    self._compact_view and self._target_label() is not None
                ),
                target_name=self._target_label,
                on_rename=self._rename_target,
                on_unchanged=self._update_footer,
            )
        except Exception:  # noqa: BLE001 -- the footer's private stack changed
            self._footer_rename = None
        try:
            # Shape / History selection: Maya's DAG split. A Blender object
            # owns its data directly and modifiers are no scene nodes, so
            # blendertk has no get_shape_nodes and the buttons are not built
            # there. Added before the target toggle so they sit to its left.
            if self._host_has("get_shape_nodes"):
                footer.add_action_button(
                    icon_name="cube",
                    tooltip="Select the shape node(s) of the current selection.",
                    callback=self._select_shape_nodes,
                )
                footer.add_action_button(
                    icon_name="history",
                    tooltip="Select the construction-history node(s) of the "
                    "current selection.",
                    callback=self._select_history_nodes,
                )
            # Mirrors txt001's target action (same states), shown in compact
            # view only.
            self._footer_compact_btn = footer.add_action_button(
                states=self._target_toggle_states()
            )
            self._footer_compact_btn.setVisible(False)
        except Exception:  # noqa: BLE001 -- a footer without action buttons
            self._footer_compact_btn = None

    def _select_shape_nodes(self):
        self._select_related(self.controller.get_shape_nodes, "shape")

    def _select_history_nodes(self):
        self._select_related(self.controller.get_history_nodes, "history")

    def _select_related(self, resolve, noun):
        nodes = self._selected_nodes()
        if not nodes:
            return
        related = resolve(nodes)
        if not related:
            self.sb.message_box(f"Warning: No {noun} nodes found.")
            return
        self.controller.select_nodes(related)
        self._refresh_table(self.ui.tbl000)

    # ------------------------------------------------------------------
    # Filter combo
    # ------------------------------------------------------------------

    def cmb000_init(self, widget):
        """The host's filters, and an invert action on the combo's option box."""
        widget.addItems(
            [k for k in self.controller.FILTER_MAP if not str(k).startswith("_")]
        )
        clr = self.ACTION_COLOR_MAP
        widget.option_box.add_action(
            icon="invert",
            tooltip="Invert filter",
            states=[
                {
                    "icon": "invert",
                    "tooltip": "Invert OFF — click to show the complement of "
                    "the filter",
                    "color": clr["off"],
                    "callback": lambda: self._set_filter_invert(True),
                },
                {
                    "icon": "invert",
                    "tooltip": "Invert ON — click to show the normal filter set",
                    "color": clr["active"],
                    "callback": lambda: self._set_filter_invert(False),
                },
            ],
            settings_key=False,
        )

    def cmb000(self, index):
        """Filter changed: refresh."""
        self._refresh_table(self.ui.tbl000)

    def _set_filter_invert(self, enabled):
        self._filter_invert = bool(enabled)
        self._refresh_table(self.ui.tbl000)

    def _filter_name(self):
        cmb = getattr(self.ui, "cmb000", None)
        return cmb.currentText() if cmb is not None else "Custom"

    # ------------------------------------------------------------------
    # Table setup
    # ------------------------------------------------------------------

    def tbl000_init(self, widget):
        """Wire the table, build its menu once, start watching the scene, refresh.

        The table can outlive a slots instance (a UI reload keeps the widget
        and its ``is_initialized`` stamp), so everything that names this
        instance -- signals, icon actions, menu handlers -- is bound on every
        init; only what lives on the widget alone is built once.
        """
        self._wire_table_signals(widget)
        if not widget.is_initialized:
            widget.refresh_on_show = True
            self._build_context_menu(widget)
            self._setup_value_input(widget)
        self._setup_action_columns(widget)
        self._register_menu_actions(widget)
        if not self._watching:
            self._setup_scene_change_callbacks(widget)
        widget.horizontalHeader().setVisible(not self._compact_view)
        self._refresh_table(widget)

    def _wire_table_signals(self, widget):
        """Bind every table signal this panel handles to this instance, once.

        Disconnect-then-connect, so a binding left by a dead slots instance
        goes. The scrub / wheel / batch signals carry only our handlers, so
        their old bindings are dropped by tracked reference: a blanket
        ``disconnect()`` on a signal with nothing attached makes PySide warn.
        """
        for signal, slot in (
            (widget.cellChanged, self._handle_cell_edit),
            (widget.itemSelectionChanged, self._on_table_selection_changed),
        ):
            try:
                signal.disconnect()
            except (RuntimeError, TypeError):
                pass
            signal.connect(slot)

        conns = getattr(widget, "_ch_scrub_conns", None)
        if conns is None:
            conns = {}
            widget._ch_scrub_conns = conns
        for name, slot in (
            ("cellScrubStarted", self._on_scrub_started),
            ("cellScrubMoved", self._on_scrub_moved),
            ("cellScrubFinished", self._on_scrub_finished),
            ("cellWheelScrolled", self._on_wheel_scrolled),
            ("editBatchStarted", self._on_edit_batch_started),
            ("editBatchFinished", self._on_edit_batch_finished),
        ):
            sig = getattr(widget, name, None)
            if sig is None:
                continue  # an older TableWidget without the signal
            old = conns.get(name)
            # A Connection goes falsy once it breaks; the STATIC
            # QObject.disconnect is the API that takes one.
            if old:
                try:
                    QtCore.QObject.disconnect(old)
                except (RuntimeError, TypeError):
                    pass
            conns[name] = sig.connect(slot)
        if self._footer_controller is not None:
            widget.itemSelectionChanged.connect(self._footer_controller.update)

        # The context menu: our enable/disable pass first, then the table's
        # own popup (Qt fires slots in connection order).
        try:
            widget.customContextMenuRequested.disconnect()
        except (RuntimeError, TypeError):
            pass
        widget.customContextMenuRequested.connect(self._update_context_menu_state)
        show = getattr(widget, "_show_context_menu", None)
        if show is not None:
            widget.customContextMenuRequested.connect(show)

    def _setup_action_columns(self, widget):
        """The Lock and Key columns: icon toggles, drag-set, color-coded."""
        clr = self.ACTION_COLOR_MAP
        drag_tip = "Drag: lock a range · Alt+drag: unlock a range."
        widget.actions.add(
            self.COL_LOCK,
            drag_action=self._on_icon_cells_dragged,
            states={
                "locked": {
                    "icon": "lock",
                    "color": clr["locked"],
                    "tooltip": f"Locked — click to unlock.\n{drag_tip}",
                    "action": self._on_icon_cell_clicked,
                },
                "unlocked": {
                    "icon": "unlock",
                    "color": clr["off"],
                    "tooltip": f"Unlocked — click to lock.\n{drag_tip}",
                    "action": self._on_icon_cell_clicked,
                },
            },
        )
        keyable = self.controller.KEYABLE_STATES
        states = {
            state: {
                "icon": "disconnect" if state == "none" else "connect",
                "color": clr.get(state, clr["connected"]),
                "tooltip": self._conn_tooltip(state, label, state in keyable),
                "action": self._on_icon_cell_clicked,
            }
            for state, label in self._CONN_STATES
        }
        widget.actions.add(
            self.COL_CONN, states=states, drag_action=self._on_icon_cells_dragged
        )

    @staticmethod
    def _conn_tooltip(state, label, keyable):
        """A Key-column state's tooltip: what a click, a drag and Ctrl do there."""
        if not keyable:
            return f"{label} — Ctrl+click to break the connection."
        if state == "keyframe_active":
            click = "click to remove it."
        elif state == "keyframe_changed":
            click = "click to key it."
        else:
            click = "click to key the current time."
        lines = [
            f"{label} — {click}",
            "Drag: key a range · Alt+drag: remove those keys.",
        ]
        if state != "none":
            lines.append("Ctrl+click / Ctrl+drag: break the connection.")
        return "\n".join(lines)

    def _build_context_menu(self, widget):
        """The right-click menu's items (once per table; see _CONTEXT_ITEMS)."""
        menu = widget.menu
        for item in self._CONTEXT_ITEMS:
            if item[1] is None:
                menu.add("Separator", setTitle=item[0])
                continue
            label, name, tooltip, _handler, needs = item
            if needs and not self._host_has(needs):
                continue
            menu.add(
                "QPushButton", setText=label, setObjectName=name, setToolTip=tooltip
            )

    def _register_menu_actions(self, widget):
        """Point every menu item at this instance's handler (replaces by name)."""
        for item in self._CONTEXT_ITEMS:
            if item[1] is None:
                continue
            _label, name, _tooltip, handler, needs = item
            if needs and not self._host_has(needs):
                continue
            widget.register_menu_action(
                name,
                lambda sel, fn=getattr(self, handler): fn(sel),
                columns=self._ROW_SELECTION_COLUMNS,
                allow_empty=name in self._NODE_LEVEL_ACTIONS,
            )

    def _setup_value_input(self, widget):
        """The Value column: MMB scrub, wheel scrub and single-click edit.

        Settings on the widget, so once per table; the signals are
        :meth:`_wire_table_signals`'.
        """
        widget.set_scrub_columns([self.COL_VALUE])
        widget.set_wheel_scrub_columns([self.COL_VALUE])
        widget.set_single_click_edit_columns([self.COL_VALUE])
        # An enum's combobox can end up narrower than its cell: a click on the
        # rest of the cell opens it rather than reading as dead space.
        widget.set_cell_widget_click_columns([self.COL_VALUE])

    def _update_context_menu_state(self, _position=None):
        """Enable Freeze / Unfreeze for what the row selection can do.

        Freeze takes whole groups (all three axes of a move, rotate or scale)
        or nothing (everything); Unfreeze the same, and stored freeze data on a
        selected object. The tooltip says which condition failed.
        """
        tbl = self.ui.tbl000
        menu = getattr(tbl, "menu", None)
        if menu is None or not self._is_widget_alive(tbl):
            return
        nodes = self._selected_nodes()
        try:
            selection = tbl.get_selection(
                columns=self._ROW_SELECTION_COLUMNS, include_current=True
            )
        except RuntimeError:
            return
        names = [s["name"] for s in (selection or []) if s.get("name")]
        groups_ok = bool(nodes) and self.controller.can_freeze_selection(names)

        freeze = getattr(menu, "ctx_freeze_transforms", None)
        if freeze is not None:
            freeze.setEnabled(groups_ok)
            freeze.setToolTip(
                self._FREEZE_TIP_ENABLED if groups_ok else self._FREEZE_TIP_DISABLED
            )
        unfreeze = getattr(menu, "ctx_unfreeze_transforms", None)
        if unfreeze is not None:
            stored = bool(nodes) and self.controller.has_unfreeze_info(nodes)
            unfreeze.setEnabled(groups_ok and stored)
            if groups_ok and stored:
                tip = self._UNFREEZE_TIP_ENABLED
            elif not groups_ok:
                tip = self._UNFREEZE_TIP_BAD_SELECTION
            else:
                tip = self._UNFREEZE_TIP_NO_STORED
            unfreeze.setToolTip(tip)

    # ------------------------------------------------------------------
    # Table data
    # ------------------------------------------------------------------

    def _selected_nodes(self):
        """The engine's targets; none when the host cannot answer.

        A panel loads before there is a scene to read (Blender's handler
        without ``bpy``), and a refresh must not take it down then.
        """
        try:
            return list(self.controller.get_selected_nodes() or [])
        except Exception:  # noqa: BLE001
            _log.debug("channels: no targets to read", exc_info=True)
            return []

    def _refresh_table(self, widget):
        """Rebuild the table from the targets and the filters.

        Re-entry safe: a refresh asked for during one (a queued combo signal
        firing while cell widgets are torn down) marks itself queued, and the
        running one schedules ONE follow-up when it ends.
        """
        if self._destroyed:
            return
        if self._refreshing:
            self._refresh_queued = True
            return
        self._refreshing = True
        # Channel-box -> table sync stays out of a rebuild: its handler is a
        # slot on a signal we don't own, so blocking the table's signals does
        # not stop it mutating rows mid-teardown.
        prev_syncing = self._syncing_selection
        self._syncing_selection = True
        try:
            with self.sb.busy_cursor():
                self._rebuild(widget)
        except RuntimeError:
            # The widget (or a child) died mid-refresh.
            self.cleanup_scene_callbacks()
            return
        except Exception:  # noqa: BLE001 -- the next refresh may recover
            _log.debug("channels refresh failed", exc_info=True)
        finally:
            self._syncing_selection = prev_syncing
            self._refreshing = False
            if self._refresh_queued and not self._destroyed:
                self._refresh_queued = False
                self.controller.defer(lambda w=widget: self._deferred_refresh(w))

        chk = getattr(self, "_chk_show_type", None)
        if chk is not None:
            try:
                widget.setColumnHidden(self.COL_TYPE, not chk.isChecked())
            except RuntimeError:
                pass
        self._update_footer()
        self._autofit_window(widget)

    def _rebuild(self, widget):
        if not self._is_widget_alive(widget):
            return
        # The Compact View state first (pull model), so row height and the
        # header / footer swap are right even before the header's restore.
        self._sync_compact_default()
        widget.setUpdatesEnabled(False)
        widget.blockSignals(True)
        try:
            # Re-selected after the rebuild when the channel box has none to
            # restore (Maya empties it while it is tabbed away).
            kept_rows = self._selected_row_names(widget)
            self._teardown_cell_widgets(widget)
            widget.clear()
            nodes = self._selected_nodes()
            self._update_target_display(nodes)
            if not nodes:
                widget.add([["No selection", "", "", "", ""]], headers=self.HEADERS)
                self._configure_columns(widget)
                self._apply_row_height(widget)
                return
            filter_kwargs = self.controller.get_filter_kwargs(
                self._filter_name(), self._filter_invert
            )
            rows, states = self.controller.build_table_data(nodes, filter_kwargs)
            rows, states = self._apply_name_filter(rows, states)
            widget.add(rows, headers=self.HEADERS)
            self._configure_columns(widget)
            for row, (locked, conn_type) in enumerate(states):
                widget.actions.set(
                    row, self.COL_LOCK, "locked" if locked else "unlocked"
                )
                widget.actions.set(row, self.COL_CONN, conn_type)
            self._set_name_editability(widget, nodes)
            self._apply_row_height(widget)
            self._setup_enum_combos(widget, nodes)
            self._last_cb_selection = self._channel_box_selection()
            self._select_rows(widget, self._last_cb_selection or set(kept_rows))
        finally:
            try:
                widget.blockSignals(False)
                widget.setUpdatesEnabled(True)
            except RuntimeError:
                pass

    def _apply_name_filter(self, rows, states):
        """Keep the rows the name filter's wildcards match (when it is on)."""
        field = getattr(self.ui, "txt000", None)
        text = field.text().strip() if field is not None else ""
        if not (self._filter_enabled and text):
            return rows, states
        keep = set(
            ptk.IterUtils.filter_list([r[0] for r in rows], inc=text, ignore_case=True)
        )
        kept = [(r, s) for r, s in zip(rows, states) if r[0] in keep]
        return [r for r, _ in kept], [s for _, s in kept]

    def _teardown_cell_widgets(self, widget):
        """Detach the Value column's enum comboboxes and delete them later.

        ``clear()`` would destroy them at once, and a combo with a queued
        ``activated`` would then fire into a half-destroyed object. The icon
        columns' widgets are uitk's ``actions`` (it caches them): not touched.
        """
        try:
            row_count = widget.rowCount()
        except RuntimeError:
            return
        for row in range(row_count):
            try:
                cell = widget.cellWidget(row, self.COL_VALUE)
            except RuntimeError:
                return
            if cell is None:
                continue
            try:
                cell.blockSignals(True)
                widget.removeCellWidget(row, self.COL_VALUE)
                cell.deleteLater()
            except Exception:  # noqa: BLE001
                pass

    def _deferred_refresh(self, widget):
        """A scheduled refresh, unless the panel or table is gone by then."""
        if self._destroyed or not self._is_widget_alive(widget):
            return
        self._refresh_table(widget)

    def _configure_columns(self, widget):
        """Name fits its content; with Auto-fit, Value and Type do too."""
        header = widget.horizontalHeader()
        header.setSectionsMovable(False)
        QHV = QtWidgets.QHeaderView
        chk = getattr(self, "_chk_auto_fit", None)
        header.setSectionResizeMode(self.COL_NAME, QHV.ResizeToContents)
        if chk is not None and chk.isChecked():
            header.setSectionResizeMode(self.COL_VALUE, QHV.ResizeToContents)
            header.setSectionResizeMode(self.COL_TYPE, QHV.ResizeToContents)
        else:
            header.setSectionResizeMode(self.COL_VALUE, QHV.Stretch)
            header.setSectionResizeMode(self.COL_TYPE, QHV.Interactive)
            widget.setColumnWidth(self.COL_TYPE, 80)

    def _autofit_window(self, widget):
        """Fit the window to the table when Auto-fit Window is on (uitk's
        :meth:`TableWidget.fit_window_to_contents` owns the sizing rules)."""
        chk = getattr(self, "_chk_auto_fit", None)
        if chk is None or not chk.isChecked() or not self._is_widget_alive(widget):
            return
        widget.fit_window_to_contents()

    def _set_name_editability(self, widget, nodes):
        """Right-align names; a custom attribute's name is editable (rename)
        with one target: a rename across several has no single outcome. The
        name is kept under ``UserRole`` to detect the rename."""
        Qt = QtCore.Qt
        custom = (
            set(self.controller.get_custom_attrs(nodes[0]))
            if len(nodes) == 1
            else set()
        )
        for row in range(widget.rowCount()):
            item = widget.item(row, self.COL_NAME)
            if not item:
                continue
            item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            name = item.text().strip()
            item.setData(Qt.UserRole, name)
            if name in custom:
                item.setFlags(item.flags() | Qt.ItemIsEditable)
            else:
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)

    def _selected_row_names(self, widget):
        """The attribute names of the selected rows, in table order."""
        names = []
        for item in widget.selectedItems():
            if item.column() == self.COL_NAME:
                name = item.text().strip()
                if name and name not in names:
                    names.append(name)
        return names

    def _select_rows(self, widget, names):
        """Select the rows named *names* (nothing to select clears nothing).

        An empty set is no intent: Maya empties its channel box on focus
        shifts, which must not wipe a deliberate row selection.
        """
        if not names:
            return
        was_blocked = widget.blockSignals(True)
        try:
            widget.clearSelection()
            sel_model = widget.selectionModel()
            model = widget.model()
            QSel = QtCore.QItemSelectionModel
            for row in range(widget.rowCount()):
                item = widget.item(row, self.COL_NAME)
                if item and item.text().strip() in names:
                    sel_model.select(model.index(row, 0), QSel.Select | QSel.Rows)
        finally:
            widget.blockSignals(was_blocked)

    # ------------------------------------------------------------------
    # Channel-box sync (Maya; Blender has no channel box)
    # ------------------------------------------------------------------

    def _channel_box_selection(self):
        if not self._host_has("link_channel_box"):
            return set()
        try:
            return set(self.controller.channel_box_selection())
        except Exception:  # noqa: BLE001
            return set()

    def _link_channel_box(self):
        """(Re)link to the host's channel box: its selection drives the rows,
        and the rows stand in for it while the host has it emptied."""
        if not self._host_has("link_channel_box"):
            return
        try:
            self.controller.link_channel_box(
                self._on_cb_selection_changed, self._selected_channel_rows
            )
        except Exception:  # noqa: BLE001 -- no box to link yet
            _log.debug("channels: channel box not linked", exc_info=True)

    def _selected_channel_rows(self):
        """The rows standing in for the channel box: none while not shown."""
        tbl = self.ui.tbl000
        if self._destroyed or not self._is_widget_alive(tbl) or not tbl.isVisible():
            return []
        return self._selected_row_names(tbl)

    def _on_table_selection_changed(self):
        """Push the selected rows to the host's channel box."""
        if self.ui.tbl000.signalsBlocked() or self._syncing_selection:
            return
        if not self._host_has("select_in_channel_box"):
            return
        names = self._selected_row_names(self.ui.tbl000)
        self._syncing_selection = True
        try:
            self.controller.select_in_channel_box(names)
            self._last_cb_selection = set(names)
        except Exception:  # noqa: BLE001
            pass
        finally:
            self._syncing_selection = False

    def _on_cb_selection_changed(self, names):
        """The channel box's selection changed: select those rows."""
        if self._syncing_selection or self._destroyed:
            return
        current = set(names or ())
        if current == self._last_cb_selection:
            return
        self._syncing_selection = True
        try:
            tbl = self.ui.tbl000
            if self._is_widget_alive(tbl):
                self._last_cb_selection = current
                self._select_rows(tbl, current)
        except RuntimeError:
            self.cleanup_scene_callbacks()
        except Exception:  # noqa: BLE001
            pass
        finally:
            self._syncing_selection = False

    # ------------------------------------------------------------------
    # Icon cells (Lock / Key)
    # ------------------------------------------------------------------

    @staticmethod
    def _keyboard_modifiers():
        """The live modifiers: a cell click or drag carries none."""
        return QtWidgets.QApplication.keyboardModifiers()

    def _on_icon_cell_clicked(self, row, col):
        """A click on a Lock / Key icon: toggle that row, then refresh."""
        if self._apply_icon_cell(row, col, toggle=True):
            self._refresh_table(self.ui.tbl000)

    def _on_icon_cells_dragged(self, rows, col):
        """A drag down the Lock / Key column: every crossed row in ONE undo
        step and one refresh (dispatched as clicks, each row was its own)."""
        with self.tk.CoreUtils.undo_chunk("Channels Drag"):
            changed = [self._apply_icon_cell(row, col) for row in rows]
        if any(changed):
            self._refresh_table(self.ui.tbl000)

    def _apply_icon_cell(self, row, col, toggle=False):
        """Apply a click, or one row of a drag, on the Lock / Key columns.

        A click toggles its row; a drag sets, so a range ends uniform: it locks
        / keys every row, ``Alt`` unlocks / removes those keys, ``Ctrl`` on the
        Key column breaks what drives the row. Only the engine's
        ``KEYABLE_STATES`` take a key from a plain click.

        Returns:
            bool: True if anything was applied (the caller refreshes).
        """
        tbl = self.ui.tbl000
        name_item = tbl.item(row, self.COL_NAME)
        if not name_item or not name_item.text():
            return False
        attr_name = name_item.text().strip()
        nodes = self._selected_nodes()
        if not nodes or col not in (self.COL_LOCK, self.COL_CONN):
            return False
        Qt = QtCore.Qt
        modifiers = self._keyboard_modifiers()
        clear = bool(modifiers & Qt.AltModifier)
        state = tbl.actions.get(row, col)

        if col == self.COL_LOCK:
            if clear:
                lock = False
            elif toggle:
                lock = state != "locked"
            else:
                lock = True
            self.controller.set_lock(nodes, [attr_name], lock)
            return True

        if modifiers & Qt.ControlModifier:
            if state and state != "none":
                self.controller.break_connections(nodes, attr_name)
                return True
            return False

        if state is None or state in self.controller.KEYABLE_STATES:
            if clear:
                keyed = False
            elif toggle:
                keyed = state != "keyframe_active"
            else:
                keyed = True
            self.controller.set_key_at_current_time(nodes, attr_name, keyed=keyed)
            return True
        return False

    # ------------------------------------------------------------------
    # Inline editing
    # ------------------------------------------------------------------

    def _handle_cell_edit(self, row, col):
        """A Name edit renames a custom attribute; a Value edit sets it on
        every target, then shows what the host stored (clamped or refused)."""
        tbl = self.ui.tbl000
        nodes = self._selected_nodes()
        if not nodes:
            return
        if col == self.COL_NAME:
            item = tbl.item(row, col)
            if not item:
                return
            old = item.data(QtCore.Qt.UserRole)
            new = item.text().strip()
            if not old or not new or new == old:
                return
            try:
                self.controller.rename_attribute(nodes, old, new)
            except Exception as error:  # noqa: BLE001 -- reported to the user
                self.sb.message_box(f"Warning: Cannot rename '{old}': {error}")
            self._refresh_table(tbl)
            return
        if col != self.COL_VALUE:
            return
        name_item = tbl.item(row, self.COL_NAME)
        attr_name = name_item.text().strip() if name_item else ""
        value_item = tbl.item(row, col)
        # A persistent cell widget is an enum combobox (its own handler); a
        # delegate editor also comes back from cellWidget() under PySide6.
        if (
            not attr_name
            or value_item is None
            or isinstance(tbl.cellWidget(row, col), QtWidgets.QComboBox)
        ):
            return
        self.controller.set_attribute_value(nodes, attr_name, value_item.text().strip())
        self._on_attr_value_set(tbl, attr_name)

    def _on_edit_batch_started(self):
        """Open one undo chunk around a multi-cell edit (a drag-fill): the
        table writes each filled cell as its own ``cellChanged``."""
        if self._edit_chunk is not None:
            return
        chunk = self.tk.CoreUtils.undo_chunk("Channels Edit")
        chunk.__enter__()
        self._edit_chunk = chunk

    def _on_edit_batch_finished(self):
        """Close the chunk :meth:`_on_edit_batch_started` opened (if any)."""
        chunk, self._edit_chunk = self._edit_chunk, None
        if chunk is not None:
            chunk.__exit__(None, None, None)

    # ------------------------------------------------------------------
    # Enum value cells (hosts with enum attributes: Maya)
    # ------------------------------------------------------------------

    def _setup_enum_combos(self, widget, nodes):
        """Put a combobox in each enum row's Value cell."""
        if not nodes or not self._host_has("get_enum_fields"):
            return
        primary = nodes[0]
        for row in range(widget.rowCount()):
            type_item = widget.item(row, self.COL_TYPE)
            name_item = widget.item(row, self.COL_NAME)
            if not type_item or type_item.text() != "enum" or not name_item:
                continue
            attr_name = name_item.text().strip()
            labels = self.controller.get_enum_fields(primary, attr_name)
            if not labels:
                continue
            indices = [i for _, i in self.controller.parse_enum_def(primary, attr_name)]
            combo = EnumCell.build(
                self.sb,
                attr_name,
                labels,
                indices,
                self.controller.get_attr_value(primary, attr_name),
                on_activated=self._on_enum_combo_activated,
                on_action=self._on_enum_action,
            )
            # The text item under it must not open an editor behind the combo.
            value_item = widget.item(row, self.COL_VALUE)
            if value_item:
                value_item.setFlags(value_item.flags() & ~QtCore.Qt.ItemIsEditable)
            widget.setCellWidget(row, self.COL_VALUE, combo)

    def _on_enum_combo_activated(self, combo, position):
        """The user picked a label: store its index on every target."""
        attr_name = combo.property("_attr_name")
        indices = combo.property("_enum_indices") or []
        nodes = self._selected_nodes()
        if not nodes or not attr_name:
            return
        index = indices[position] if position < len(indices) else position
        self._combo_setting = True  # our own write: no echo into the combo
        try:
            self.controller.set_attribute_value(nodes, attr_name, str(index))
        finally:
            self._combo_setting = False

    def _on_enum_action(self, combo, action):
        """Rename / Add / Delete an enum field (a dialog, after the popup closes)."""
        attr_name = combo.property("_attr_name")
        nodes = self._selected_nodes()
        if not nodes or not attr_name:
            return
        if action == "Add":
            self.controller.defer(lambda: self._enum_add_dialog(nodes, attr_name))
            return
        label = self.controller.get_enum_label(nodes[0], attr_name)
        if not label:
            return
        if action == "Rename":
            self.controller.defer(
                lambda: self._enum_rename_dialog(nodes, attr_name, label)
            )
        elif action == "Delete":
            self.controller.defer(
                lambda: self._delete_enum_field(nodes, attr_name, label)
            )

    def _enum_rename_dialog(self, nodes, attr_name, old_label):
        new_label = self.sb.input_dialog(
            title="Rename Enum Value",
            label=f"Rename '{old_label}' to:",
            text=old_label,
            parent=self.ui.tbl000,
        )
        if new_label and new_label != old_label:
            self.controller.rename_enum_field(nodes, attr_name, old_label, new_label)
            self._refresh_table(self.ui.tbl000)

    def _enum_add_dialog(self, nodes, attr_name):
        new_label = self.sb.input_dialog(
            title="Add Enum Value",
            label="New enum label:",
            placeholder="e.g. Footstep",
            parent=self.ui.tbl000,
        )
        if new_label:
            self.controller.add_enum_field(nodes, attr_name, new_label)
            self._refresh_table(self.ui.tbl000)

    def _delete_enum_field(self, nodes, attr_name, label):
        self.controller.delete_enum_field(nodes, attr_name, label)
        self._refresh_table(self.ui.tbl000)

    # ------------------------------------------------------------------
    # Context-menu handlers (a selection payload from register_menu_action)
    # ------------------------------------------------------------------

    def _selected_attrs_and_nodes(self, selection):
        """``(attribute names, targets)``, or ``(None, None)`` if either is empty."""
        names = [s["name"] for s in (selection or []) if s.get("name")]
        nodes = self._selected_nodes()
        if not nodes or not names:
            return None, None
        return names, nodes

    def _run_on_rows(self, selection, method, *args, refresh=True):
        """``engine.method(targets, names, *args)`` for the selected rows."""
        names, nodes = self._selected_attrs_and_nodes(selection)
        if not names:
            return None
        result = getattr(self.controller, method)(nodes, names, *args)
        if refresh:
            self._refresh_table(self.ui.tbl000)
        return result

    def _ctx_lock(self, selection):
        self._run_on_rows(selection, "set_lock", True)

    def _ctx_unlock(self, selection):
        self._run_on_rows(selection, "set_lock", False)

    def _ctx_reset_default(self, selection):
        self._run_on_rows(selection, "reset_to_default")

    def _ctx_toggle_keyable(self, selection):
        self._run_on_rows(selection, "toggle_keyable")

    def _ctx_hide(self, selection):
        self._run_on_rows(selection, "hide_attrs")

    def _ctx_show(self, selection):
        self._run_on_rows(selection, "show_attrs")

    def _ctx_lock_and_hide(self, selection):
        self._run_on_rows(selection, "lock_and_hide_attrs")

    def _ctx_breakdown(self, selection):
        self._run_on_rows(selection, "set_breakdown_key")

    def _ctx_mute(self, selection):
        self._run_on_rows(selection, "mute_attrs")

    def _ctx_unmute(self, selection):
        self._run_on_rows(selection, "unmute_attrs")

    def _ctx_delete(self, selection):
        self._run_on_rows(selection, "delete_attributes")

    def _ctx_copy_values(self, selection):
        copied = self._run_on_rows(selection, "copy_attr_values", refresh=False)
        if copied:
            self.sb.message_box(f"Result: Copied {len(copied)} attribute value(s).")

    def _ctx_paste_values(self, selection):
        nodes = self._selected_nodes()
        if not nodes:
            return
        self.controller.paste_attr_values(nodes)
        self._refresh_table(self.ui.tbl000)

    def _ctx_select_connection(self, selection):
        names, nodes = self._selected_attrs_and_nodes(selection)
        if not names:
            return
        if not self.controller.select_connections(nodes, names[0]):
            self.sb.message_box(f"Warning: Nothing drives '{names[0]}'.")

    def _ctx_break_connection(self, selection):
        names, nodes = self._selected_attrs_and_nodes(selection)
        if not names:
            return
        # A list, not a generator: any() would stop at the first broken one.
        if any([self.controller.break_connections(nodes, n) for n in names]):
            self._refresh_table(self.ui.tbl000)
        else:
            self.sb.message_box("Warning: No connections to break.")

    def _ctx_freeze_transforms(self, selection):
        """Freeze the targets' transforms: whole groups, or everything with no
        row selected (:meth:`_update_context_menu_state` gates the item)."""
        nodes = self._selected_nodes()
        if not nodes:
            self.sb.message_box("Warning: No object(s) selected.")
            return
        names = [s["name"] for s in (selection or []) if s.get("name")]
        if not self.controller.freeze_transforms(nodes, attrs=names or None):
            # Only a programmatic trigger reaches this: the item is disabled.
            self.sb.message_box(
                "Warning: Selection is not a valid freeze target — select "
                "complete transform group(s) or nothing."
            )
            return
        self._refresh_table(self.ui.tbl000)

    def _ctx_unfreeze_transforms(self, selection):
        """Restore the targets' frozen transforms: the selected whole groups,
        or every channel with no row selected."""
        nodes = self._selected_nodes()
        if not nodes:
            self.sb.message_box("Warning: No object(s) selected.")
            return
        names = [s["name"] for s in (selection or []) if s.get("name")]
        if not self.controller.unfreeze_transforms(nodes, attrs=names or None):
            self.sb.message_box(
                "Warning: No stored freeze data on the selected object(s)."
            )
        self._refresh_table(self.ui.tbl000)

    # ------------------------------------------------------------------
    # Value input: MMB scrub and wheel steps
    # ------------------------------------------------------------------

    def _numeric_row(self, row):
        """``(attribute, targets, is_int)`` for a numeric row, else None."""
        name_item = self.ui.tbl000.item(row, self.COL_NAME)
        attr_name = name_item.text().strip() if name_item else ""
        nodes = self._selected_nodes()
        if not attr_name or not nodes:
            return None
        attr_type = self.controller.get_attr_type(nodes[0], attr_name)
        if attr_type not in self.controller.SCRUBBABLE_TYPES:
            return None
        return attr_name, nodes, attr_type in self.controller.INTEGER_TYPES

    def _on_scrub_started(self, row, col):
        """Snapshot each target's value for an MMB scrub on a numeric row."""
        # A press whose release never came (focus lost mid-drag) left its
        # undo chunk open: close it on ANY press.
        self._end_scrub()
        if self._destroyed or col != self.COL_VALUE:
            return
        numeric = self._numeric_row(row)
        if numeric is None:
            return
        attr_name, nodes, is_int = numeric
        # start + delta each step, so rounding never accumulates.
        starts = self.controller.get_numeric_values(nodes, attr_name)
        if not starts:
            return
        self._scrub_state = {
            "row": row,
            "attr": attr_name,
            "starts": starts,
            "is_int": is_int,
            "chunk": None,
        }

    def _on_scrub_moved(self, row, col, dx, dy):
        """Apply the drag's delta to every snapshotted target."""
        state = self._scrub_state
        if not state or self._destroyed:
            return
        Qt = QtCore.Qt
        mods = self._keyboard_modifiers()
        scale = 1.0
        if mods & Qt.ControlModifier:
            scale *= 0.1
        if mods & Qt.ShiftModifier:
            scale *= 10.0
        if state["is_int"]:
            delta = int(dx / self._SCRUB_INT_PIXELS_PER_UNIT * scale)
        else:
            delta = dx * self._SCRUB_FLOAT_STEP * scale
        values = {
            node: (int(round(start + delta)) if state["is_int"] else start + delta)
            for node, start in state["starts"].items()
        }
        if state["chunk"] is None:
            # Opened at the first write, so a press that never moves pushes no
            # undo step; held to the release, so the drag is one step.
            state["chunk"] = self.tk.CoreUtils.undo_chunk(f"Scrub {state['attr']}")
            state["chunk"].__enter__()
        self.controller.set_numeric_values(values, state["attr"])
        # Live feedback in the cell, no rebuild mid-drag.
        self._set_value_cell_text(
            state["row"], self.controller.format_value(next(iter(values.values())))
        )

    def _on_scrub_finished(self, row, col):
        """Close the scrub's undo step; show what the host stored."""
        state = self._scrub_state
        if self._end_scrub() and state.get("chunk") is not None:
            self._on_attr_value_set(self.ui.tbl000, state["attr"])

    def _end_scrub(self):
        """Close the active scrub's undo chunk; True if a scrub was active."""
        state, self._scrub_state = self._scrub_state, None
        if state is None:
            return False
        chunk = state.get("chunk")
        if chunk is not None:
            chunk.__exit__(None, None, None)
        return True

    def _set_value_cell_text(self, row, text):
        """Set a Value cell's text in place (no edit handler re-entry)."""
        widget = self.ui.tbl000
        if not self._is_widget_alive(widget):
            return
        item = widget.item(row, self.COL_VALUE)
        if item is None:
            return
        was_blocked = widget.blockSignals(True)
        try:
            item.setText(text)
        finally:
            widget.blockSignals(was_blocked)

    def _wheel_step(self, mods, is_int):
        """The per-notch step for *mods* (the ladder in the class constants).

        ``bool(mods & SPECIFIC)`` per modifier: ``(mods & MASK) == MASK`` can
        be False under PySide6 for a live ``KeyboardModifiers`` set.
        """
        Qt = QtCore.Qt
        ctrl = bool(mods & Qt.ControlModifier)
        alt = bool(mods & Qt.AltModifier)
        shift = bool(mods & Qt.ShiftModifier)
        if ctrl and alt:
            return self._WHEEL_INT_SMALLEST if is_int else self._WHEEL_FLOAT_SMALLEST
        if ctrl and shift:
            return (
                self._WHEEL_INT_VERY_COARSE if is_int else self._WHEEL_FLOAT_VERY_COARSE
            )
        if ctrl:
            return self._WHEEL_INT_COARSE if is_int else self._WHEEL_FLOAT_COARSE
        if alt:
            return self._WHEEL_INT_FINE if is_int else self._WHEEL_FLOAT_FINE
        return 1 if is_int else self._WHEEL_FLOAT_STEP

    def _cell_editor(self, row, col):
        """The line edit open on cell (*row*, *col*), else None."""
        widget = self.ui.tbl000
        if not hasattr(widget, "active_editor"):
            return None
        editor = widget.active_editor()
        index = widget.currentIndex()
        if (
            isinstance(editor, QtWidgets.QLineEdit)
            and index.isValid()
            and index.row() == row
            and index.column() == col
        ):
            return editor
        return None

    def _on_wheel_scrolled(self, row, col, steps, mods):
        """Step a numeric row by *steps* notches (signed) on every target.

        *mods* is the wheel event's own (no race with the application's
        state). With an editor open on the cell its text is the target's value
        (it may hold an uncommitted edit) and shows the result; the other
        targets step their own values, so a mixed selection stays mixed.
        Locked and non-numeric targets are skipped; one notch is one undo step.
        """
        if self._destroyed or steps == 0 or col != self.COL_VALUE:
            return
        numeric = self._numeric_row(row)
        if numeric is None:
            return
        attr_name, nodes, is_int = numeric
        step = self._wheel_step(mods, is_int)
        if step == 0:
            return  # Alt on an int: nothing finer than 1
        delta = step * steps

        def stepped(value):
            value += delta
            return int(round(value)) if is_int else value

        current = self.controller.get_numeric_values(nodes, attr_name)
        values = {node: stepped(value) for node, value in current.items()}
        editor = self._cell_editor(row, col)
        if editor is not None:
            try:
                primary = float(editor.text())
            except (TypeError, ValueError):  # mid-typing: the host's value
                primary = current.get(nodes[0], 0.0)
            new_primary = stepped(primary)
            if nodes[0] in values:
                values[nodes[0]] = new_primary
            text = self.controller.format_value(new_primary)
            cursor_from_end = len(editor.text()) - editor.cursorPosition()
            was_blocked = editor.blockSignals(True)
            try:
                editor.setText(text)
            finally:
                editor.blockSignals(was_blocked)
            editor.setCursorPosition(max(0, len(text) - cursor_from_end))
        if not values:
            return
        with self.tk.CoreUtils.undo_chunk(f"Wheel {attr_name}"):
            self.controller.set_numeric_values(values, attr_name)
        if editor is None:
            # Now, not on the next idle the host's callbacks would take.
            self._on_attr_value_set(self.ui.tbl000, attr_name)

    # ------------------------------------------------------------------
    # Live updates
    # ------------------------------------------------------------------

    def _setup_scene_change_callbacks(self, widget):
        """Watch the scene for this instance (the engine's ``watch_scene``),
        link the channel box, and watch the targets' attributes."""
        self.cleanup_scene_callbacks()
        # cleanup raised the guard so in-flight deferreds stop; re-arm it.
        self._destroyed = False
        # Build the marshaller's relay here, on the GUI thread: its first post
        # could otherwise come from a host worker thread.
        self._gui_thread.post(lambda: None)
        try:
            self.controller.watch_scene(
                self,
                lambda w=widget: self._on_scene_change(w),
                lambda w=widget: self._schedule_values_only_refresh(w),
                widget=widget,
            )
        except Exception:  # noqa: BLE001 -- no scene to watch (no bpy)
            _log.debug("channels: scene not watched", exc_info=True)
        self._link_channel_box()
        self._register_attr_change_callbacks(widget)
        self._watching = True
        try:
            widget.destroyed.connect(self.cleanup_scene_callbacks)
        except Exception:  # noqa: BLE001
            pass

    def _register_attr_change_callbacks(self, widget):
        """Watch the targets' attributes (re-done after every selection change).

        Gated: blendertk has no per-object attribute callbacks yet, so a value
        edited outside the panel (a viewport move, the N panel) shows at the
        next selection, frame or undo change rather than live (backlog:
        ``watch_nodes`` over Blender's depsgraph updates).
        """
        self._cleanup_attr_change_callbacks()
        if not self._host_has("watch_nodes"):
            return
        nodes = self._selected_nodes()
        if not nodes:
            return
        try:
            self._attr_change_tokens = list(
                self.controller.watch_nodes(
                    self,
                    nodes,
                    lambda w=widget: self._on_scene_change(w),
                    lambda name, locked, valued, w=widget: self._on_attr_changed(
                        w, name, locked, valued
                    ),
                    lambda w=widget: self._schedule_values_only_refresh(w),
                )
                or []
            )
        except Exception:  # noqa: BLE001
            _log.debug("channels: attributes not watched", exc_info=True)

    def _cleanup_attr_change_callbacks(self):
        tokens, self._attr_change_tokens = self._attr_change_tokens, []
        if tokens:
            try:
                self.controller.unwatch(tokens=tokens)
            except Exception:  # noqa: BLE001
                pass

    def _on_attr_changed(self, widget, attr_name, locked, valued):
        """An attribute was locked / unlocked and/or set: queue it for one
        coalesced pass (Qt is never touched from inside a host callback)."""
        if self._destroyed:
            return
        if locked:
            self._pending_lock_attrs.add(attr_name)
        if valued:
            self._pending_value_attrs.add(attr_name)
        if locked or valued:
            self._schedule_attr_flush(widget)

    def _schedule_attr_flush(self, widget):
        """One deferred flush for any number of queued attribute changes."""
        if self._attr_flush_pending or self._destroyed:
            return
        self._attr_flush_pending = True
        self.controller.defer(lambda w=widget: self._flush_attr_updates(w))

    def _flush_attr_updates(self, widget):
        """Drain the queued lock / value changes into their rows.

        A rebuild running now reads every row fresh: the queue is dropped.
        """
        self._attr_flush_pending = False
        if self._destroyed:
            return
        if self._refreshing:
            self._pending_value_attrs.clear()
            self._pending_lock_attrs.clear()
            return
        if not self._is_widget_alive(widget):
            self.cleanup_scene_callbacks()
            return
        lock_attrs = list(self._pending_lock_attrs)
        self._pending_lock_attrs.clear()
        value_attrs = list(self._pending_value_attrs)
        self._pending_value_attrs.clear()
        for update, names in (
            (self._on_attr_lock_changed, lock_attrs),
            (self._on_attr_value_set, value_attrs),
        ):
            for name in names:
                try:
                    update(widget, name)
                except RuntimeError:
                    self.cleanup_scene_callbacks()
                    return
                except Exception:  # noqa: BLE001
                    pass

    def _rows_named(self, widget, attr_name):
        """The table rows showing *attr_name*."""
        return [
            row
            for row in range(widget.rowCount())
            if (item := widget.item(row, self.COL_NAME))
            and item.text().strip() == attr_name
        ]

    def _on_attr_value_set(self, widget, attr_name):
        """Show *attr_name*'s current value and key state in its row, in place."""
        if self._combo_setting:
            return  # our own enum write
        nodes = self._selected_nodes()
        if not nodes:
            return
        try:
            rows = self._rows_named(widget, attr_name)
            if not rows:
                return
            data = self.controller.collect_value_strings(nodes, [attr_name])
            if attr_name not in data:
                return
            value_str, conn_type = data[attr_name]
            row = rows[0]
            cell_widget = widget.cellWidget(row, self.COL_VALUE)
            if isinstance(cell_widget, QtWidgets.QComboBox):
                EnumCell.show_index(
                    cell_widget, self.controller.get_attr_value(nodes[0], attr_name)
                )
            else:
                cell = widget.item(row, self.COL_VALUE)
                if cell and cell.text() != value_str:
                    was_blocked = widget.blockSignals(True)
                    cell.setText(value_str)
                    widget.blockSignals(was_blocked)
            # A keyed value set off its curve turns "changed" (and back).
            if widget.actions.get(row, self.COL_CONN) != conn_type:
                widget.actions.set(row, self.COL_CONN, conn_type)
        except RuntimeError:
            self.cleanup_scene_callbacks()

    def _on_attr_lock_changed(self, widget, attr_name):
        """Show *attr_name*'s lock state in its row (a lock set elsewhere)."""
        nodes = self._selected_nodes()
        if not nodes:
            return
        state = (
            "locked" if self.controller.is_locked(nodes[0], attr_name) else "unlocked"
        )
        try:
            for row in self._rows_named(widget, attr_name)[:1]:
                if widget.actions.get(row, self.COL_LOCK) != state:
                    widget.actions.set(row, self.COL_LOCK, state)
        except RuntimeError:
            self.cleanup_scene_callbacks()

    def _schedule_values_only_refresh(self, widget):
        """One in-place values pass for any burst of time / key / move events.

        Safe from any thread: posted to the GUI thread's event loop, which
        ticks during a host's interactive drags (Maya's idle queue does not)
        and from a worker thread (where a ``QTimer`` never fires).
        """
        if self._values_refresh_pending or self._destroyed:
            return
        self._values_refresh_pending = True

        def run():
            self._values_refresh_pending = False
            if self._destroyed:
                return
            if not self._is_widget_alive(widget):
                self.cleanup_scene_callbacks()
                return
            try:
                self._update_values_only(widget)
            except Exception:  # noqa: BLE001
                pass

        self._gui_thread.post(run)

    def _update_values_only(self, widget):
        """Refresh every row's value text and key icon in place (selection and
        scroll kept). Enum comboboxes follow the attribute callbacks instead."""
        try:
            row_count = widget.rowCount()
        except RuntimeError:
            self.cleanup_scene_callbacks()
            return
        nodes = self._selected_nodes()
        if not nodes or row_count == 0:
            return
        try:
            names = {}
            for row in range(row_count):
                item = widget.item(row, self.COL_NAME)
                name = item.text().strip() if item else ""
                if name:
                    names[row] = name
            if not names:
                return
            data = self.controller.collect_value_strings(nodes, list(names.values()))
            was_blocked = widget.blockSignals(True)
            try:
                for row, name in names.items():
                    if name not in data:
                        continue
                    value_str, conn_type = data[name]
                    if widget.cellWidget(row, self.COL_VALUE) is None:
                        cell = widget.item(row, self.COL_VALUE)
                        if cell and cell.text() != value_str:
                            cell.setText(value_str)
                    if widget.actions.get(row, self.COL_CONN) != conn_type:
                        widget.actions.set(row, self.COL_CONN, conn_type)
            finally:
                widget.blockSignals(was_blocked)
        except RuntimeError:
            self.cleanup_scene_callbacks()

    def _on_scene_change(self, widget):
        """One deferred rebuild for any burst of scene events (the engine's
        ``defer``: after the host's own work, never mid-command)."""
        if self._refresh_pending or self._destroyed:
            return
        self._refresh_pending = True

        def run():
            self._refresh_pending = False
            if self._destroyed:
                return
            if not self._is_widget_alive(widget):
                self.cleanup_scene_callbacks()
                return
            try:
                self._refresh_table(widget)
                # The (maybe new) targets' attributes, and the channel box,
                # whose widget a scene change can replace.
                self._register_attr_change_callbacks(widget)
                self._link_channel_box()
            except RuntimeError:
                self.cleanup_scene_callbacks()
            except Exception:  # noqa: BLE001 -- nothing useful to report here
                pass

        self.controller.defer(run)

    def cleanup_scene_callbacks(self):
        """End every subscription this instance holds (scene, attributes,
        channel box). Raises the guard first, so a deferred callback landing
        meanwhile returns at once."""
        self._destroyed = True
        self._watching = False
        if self._host_has("unlink_channel_box"):
            try:
                self.controller.unlink_channel_box()
            except Exception:  # noqa: BLE001
                pass
        self._attr_change_tokens = []
        self._pending_value_attrs.clear()
        self._pending_lock_attrs.clear()
        try:
            self.controller.unwatch(owner=self)
        except Exception:  # noqa: BLE001
            pass

    def __del__(self):
        try:
            self.cleanup_scene_callbacks()
        except Exception:  # noqa: BLE001 -- interpreter teardown
            pass

    @staticmethod
    def _is_widget_alive(widget):
        """True while *widget*'s C++ object exists (a dead wrapper raises)."""
        if widget is None:
            return False
        try:
            widget.rowCount()
            return True
        except Exception:  # noqa: BLE001 -- RuntimeError, or no table at all
            return False
