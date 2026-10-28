# !/usr/bin/python
# coding=utf-8
"""Articulated Rig: rig a prop of rigid parts on hinges, swivels, balls and
slides (a desk lamp, a magnifier arm, a boom), in three groups:

- **Setup**: analyze the selection into a plan (the joints table), correct a
  joint's type, limits or give in the table, build -- with or without the end
  control;
- **Pose**: the viewport grab, switching the end control's IK on and off
  without a jump, and the rest pose;
- **Edit**: split a link off with a new joint, fold one back, limits from the
  pose, adjust the pivots (a handle per joint and on the end control; the
  rig rebuilds on them when the box is cleared), rebuild, remove.

The table shows the plan before a build and the rig after one; an edit made
there changes the plan, or the built rig in place (a type change rebuilds it
with its animation carried across). Clicking a row selects that joint's
control (before the build, its part).

One Slots class for both hosts over the host toolkit's ``ArticulatedRig`` and
``ArticulatedRigGrab`` (``self.tk``), which also own the scene glue: what the
panel acts on (:meth:`ArticulatedRig.selection` -- Maya's selected transforms;
Blender's objects in pick order plus the selected bones of a rig in Pose
Mode), selecting a row's nodes (:meth:`ArticulatedRig.select` -- Blender puts
a control bone's armature in Pose Mode) and the parts a pick names
(:meth:`ArticulatedRig.parts_of`).
"""

import contextlib
from typing import Dict, List, Optional, Sequence, Tuple

import pythontk as ptk
from qtpy import QtCore, QtWidgets

from tentacle import Slots


class ArticulatedRigSlots(Slots, ptk.LoggingMixin):
    """Slots for the Articulated Rig panel."""

    #: The joint types a table row offers.
    TYPES = ("hinge", "swivel", "universal", "ball", "slide")
    #: ``cmb_insert_type``'s entries, by index (None: what the geometry says).
    INSERT_TYPES = (None, "slide", "hinge", "swivel", "universal", "ball")
    COLUMNS = ["Part", "Type", "Hangs Off", "Limits", "Give", "Why"]
    #: The table's columns a user acts on: the type combo, and the two cells
    #: typed into (double-click; the wheel steps a give).
    TYPE_COLUMN, LIMITS_COLUMN, GIVE_COLUMN = 1, 3, 4
    #: A give's wheel step (Shift: ten of them).
    GIVE_STEP = 0.1
    #: The tool's full reference (mayatk's doc, which covers both hosts),
    #: linked at the foot of the panel's help card.
    HELP_URL = "https://github.com/m3trik/mayatk/blob/main/docs/articulated_rig.md"

    def __init__(self, switchboard):
        super().__init__(switchboard)
        self.ui = self.sb.loaded_ui.articulated_rig
        #: The proposal the table shows before a build, or None.
        self.plan: Optional[dict] = None
        #: The rig the table shows after one, or None.
        self.rig = None
        #: The table is being refilled: its signals are not the user's.
        self._refreshing = False

        # The engine's warnings (animation dropped with a channel, keys left
        # about a moved end control) belong in this log too.
        for logger in (self.logger, self.tk.ArticulatedRig.logger):
            logger.hide_logger_name(True)
            logger.set_text_handler(self.sb.registered_widgets.TextEditLogHandler)
            logger.setup_logging_redirect(self.ui.txt003)
        if hasattr(self.ui.txt003, "anchorClicked"):
            self.ui.txt003.anchorClicked.connect(self._on_log_link_clicked)

        # Each ``btn_*`` method is the slot of the button it is named after:
        # the switchboard connects it. Connecting it here as well ran every
        # click twice (Switch IK / FK flipped and flipped back).
        self.ui.chk_end_control.toggled.connect(self._on_end_control_toggled)
        # Adjust Pivots shows a live state -- whether the rig in the table is
        # adjusting -- not a setting: restored, an adjust that ended any way
        # but by clearing the box began again on the next panel open, on
        # whatever rig the selection touched.
        self.ui.chk_adjust.restore_state = False
        self.ui.chk_adjust.toggled.connect(self._on_adjust_toggled)
        self._init_table()
        self._init_tooltips()
        # An end control with no solve (Maya: a rig an earlier mayatk solved
        # with a plug-in node; Blender: a file opened before blendertk
        # installed its solve) moves nothing until it gets one; the panel
        # opening is asking.
        with self._reporting("Restoring the end controls"):
            self.tk.ArticulatedRig.repair_scene()

    def _on_log_link_clicked(self, url) -> None:
        """Dispatch clickable ``action://`` links from the log panel."""
        self.tk.UiUtils.dispatch_log_link(url, self.logger)

    @contextlib.contextmanager
    def _reporting(self, what: str):
        """Run a panel action, logging a failure instead of raising it: a
        panel reports, never raises."""
        try:
            yield
        except Exception as error:  # noqa: BLE001 -- see the docstring
            self.logger.error(f"{what} failed: {error}")

    def header_init(self, widget):
        widget.set_help_text(
            self.sb.tooltip.fmt(
                title="Articulated Rig",
                body="Rig a prop of rigid parts on hinges, swivels, balls and "
                "slides -- a desk lamp, a magnifier arm, a boom -- as a skeleton "
                "that ships: Unity and the WebXR preview pose it, and a hand can "
                "grab it there.",
                sections=[
                    (
                        "Build",
                        [
                            "Select the prop's group (or its parts, root first, "
                            "with <b>Selection Order</b>).",
                            "<b>Analyze Selection</b>: the table proposes one "
                            "joint per moving part -- where the parts meet, and "
                            "how.",
                            "Correct any joint's <b>Type</b>, <b>Limits</b> or "
                            "<b>Give</b> in the table, then <b>Build Rig</b>.",
                        ],
                    ),
                    (
                        "Pose",
                        [
                            "Move the red <b>end control</b> (the box around the "
                            "end part -- the magnifier's lens): the stand "
                            "follows, the way a hand would move it. Rotate it to "
                            "turn a ball-mounted head.",
                            "The FK controls are the base layer: with the end "
                            "control's IK on they reshape the arm under it; "
                            "<b>Switch IK / FK</b> hands the pose over without a "
                            "jump.",
                            "<b>Grab Tool</b>: drag any part in the viewport "
                            "(in Blender, Esc or right-click ends it).",
                        ],
                    ),
                ],
                notes=[
                    "A slide is found where one tube runs inside another; its "
                    "travel comes from their overlap.",
                    "<b>Give</b> is how readily a joint moves when the end "
                    "control or a grab pulls the arm -- lower it to stiffen a "
                    "joint. Unity and the WebXR grab read the same numbers.",
                    "<b>Split Off Selected</b> adds a joint to a built rig (a "
                    "telescope you left out) -- at 0 it changes no pose, so your "
                    "keys hold.",
                    "<b>Adjust Pivots</b>: move and turn where each part turns, "
                    "and how the end control sits; clear the box to rebuild on "
                    "them.",
                    "Blender: blendertk solves the end control and bakes it into "
                    "the file at every save, so a file opened without blendertk "
                    "plays its IK, but moving the end control there moves nothing.",
                    "Every build and edit is one undo step.",
                ],
            ),
            url=self.HELP_URL,
        )

    def btn_ik_fk_init(self, widget):
        """Switch IK / FK's option box: put the end control back on the end
        part without switching."""
        menu = widget.option_box.menu
        if hasattr(menu, "btn_match_end"):
            return
        menu.setTitle("End Control")
        menu.add(
            "QPushButton",
            setText="Match End Control",
            setObjectName="btn_match_end",
            setToolTip=self.sb.tooltip.fmt(
                title="Match End Control",
                body="Put the end control where the end part is now -- after "
                "posing the FK controls, or when it was left out of reach -- so "
                "nothing moves when IK comes on.",
            ),
        )
        menu.btn_match_end.clicked.connect(self.match_end_control)

    def _init_tooltips(self):
        tip = self.sb.tooltip.fmt
        ui = self.ui
        ui.cmb_source.setToolTip(
            tip(
                title="Parts",
                body="How the selection becomes the rig's links.",
                notes=[
                    "<b>Auto</b>: each part (a group picked expands to its parts) "
                    "is a link; the chain is walked from the lowest part through "
                    "the parts that touch.",
                    "<b>Selection Order</b>: the parts as selected, root first.",
                ],
            )
        )
        ui.tbl_joints.setToolTip(
            tip(
                title="Joints",
                body="One joint per moving part: the plan before the build, the "
                "rig after it. Click a row to select that joint's control (in "
                "Blender a bone: the rig goes into Pose Mode) -- its part, before "
                "the build.",
                notes=[
                    "<b>Type</b>: pick from the list; a built joint is rebuilt "
                    "with its animation kept.",
                    "<b>Limits</b>: double-click and type, e.g. <b>rz -30..95</b> "
                    "(<b>-</b> or nothing for a free side; <b>free</b> for none). "
                    "Degrees; a slide's travel in the rig's units.",
                    "<b>Give</b>: double-click to type, or scroll the wheel over "
                    "it (Shift: faster). 1 is even; 0 holds the joint still.",
                ],
            )
        )
        ui.chk_end_control.setToolTip(
            tip(
                title="End Control",
                body="Give the rig an end control: a box around the end part "
                "that the stand follows when it is moved.",
                notes=[
                    "With a rig shown in the table, toggling adds or drops it "
                    "there (a rebuild; the animation is kept).",
                    "On the control: <b>IK Blend</b> fades the solve over FK; "
                    "<b>Follow Rotation</b> (a ball-mounted end) lets the end "
                    "part keep its own turn.",
                ],
            )
        )
        ui.btn_grab.setToolTip(
            tip(
                title="Grab Tool",
                body="Drag a rigged part in the viewport; the rig follows, "
                "solved as Unity and the WebXR preview solve a hand's grab.",
                notes=[
                    "One undo step per drag; keyed on release when auto-keying "
                    "is on.",
                    "With IK on, dragging the end part moves the end control; "
                    "dragging a part above it reshapes the arm under it.",
                    "In Blender, Esc or right-click ends the tool.",
                ],
            )
        )
        ui.btn_ik_fk.setToolTip(
            tip(
                title="Switch IK / FK",
                body="Turn the selected rig's end control on or off without the "
                "pose jumping.",
                notes=[
                    "To IK: the end control first moves onto the end part.",
                    "To FK: the FK controls first take the pose the solve made.",
                    "Keyed when auto-keying is on.",
                ],
            )
        )
        ui.btn_rest.setToolTip(
            tip(
                title="Rest Pose",
                body="Every control of the selected rig back to rest: FK at 0, "
                "the end control on its rest place. Keyed when auto-keying is on.",
            )
        )
        ui.btn_insert.setToolTip(
            tip(
                title="Split Off Selected",
                body="Give the selected parts a joint of their own, hung off "
                "the link they rode -- a slide for a tube inside a tube.",
                notes=[
                    "The new joint starts at 0: every key already made still holds."
                ],
            )
        )
        ui.btn_fold.setToolTip(
            tip(
                title="Fold Into Parent",
                body="Fold the selected part's joint away: its parts ride the "
                "joint above again. That joint's own animation is dropped.",
            )
        )
        ui.btn_limits_from_pose.setToolTip(
            tip(
                title="Set Limits From Pose",
                body="Pose a joint to where it physically stops -- by its control, "
                "the end control or the Grab Tool -- select its control or part, "
                "press: each channel's value becomes its limit on that side.",
            )
        )
        ui.chk_adjust.setToolTip(
            tip(
                title="Adjust Pivots",
                body="Check to put the selected rig's pivots out as handles: one "
                "where each joint turns, riding the part it hangs off, and one "
                "on the end control. Move and turn them; clear the box to "
                "rebuild the rig on them.",
                notes=[
                    "A handle's X runs along its part; Z is a hinge's axis, X a "
                    "swivel's and a slide's.",
                    "The animation is carried across: each joint's keys turn its "
                    "part about the new pivot.",
                    "Moving nothing changes nothing; Ctrl+Z undoes the rebuild.",
                ],
            )
        )
        ui.btn_rebuild.setToolTip(
            tip(
                title="Rebuild",
                body="Rebuild the selected rig from its plan, animation kept.",
            )
        )
        ui.btn_remove.setToolTip(
            tip(
                title="Remove Rig",
                body="Remove the selected rig and hand every part back exactly "
                "as it was.",
            )
        )

    # ================================================================ table
    def _init_table(self):
        table = self.ui.tbl_joints
        table.setColumnCount(len(self.COLUMNS))
        table.setHorizontalHeaderLabels(self.COLUMNS)
        table.verticalHeader().setVisible(False)
        table.set_cell_widget_click_columns([self.TYPE_COLUMN])
        table.set_wheel_scrub_columns([self.GIVE_COLUMN])
        table.cellWheelScrolled.connect(self._on_give_wheel)
        table.itemChanged.connect(self._on_item_changed)
        table.itemSelectionChanged.connect(self._on_rows_selected)

    def _name(self, node) -> str:
        """*node* as the table and the log name it (Maya: a DAG path's leaf;
        Blender: an object's name)."""
        return self.tk.CoreUtils.leaf_name(node)

    def _rows(self) -> List[dict]:
        """``{"id", "index", "part", "type", "parent", "limits", "give",
        "why"}`` per joint of the plan or of the rig."""
        if self.plan is not None:
            links = self.plan["links"]
            return [
                {
                    "id": None,
                    "index": i,
                    "part": self._name(links[j["link"]][0]),
                    "type": j["type"],
                    "parent": self._name(links[j["parent"]][0]),
                    "limits": j.get("limits") or {},
                    "give": ptk.ArticulationPlan.give_of(j),
                    "why": j.get("reason", ""),
                }
                for i, j in enumerate(self.plan["joints"])
            ]
        if self.rig is not None:
            spec = self.rig.spec
            links = spec["links"]
            return [
                {
                    "id": j["id"],
                    "index": i,
                    "part": links[j["link"]][0]["name"],
                    "type": j["type"],
                    "parent": links[j["parent"]][0]["name"],
                    "limits": j.get("limits") or {},
                    "give": ptk.ArticulationPlan.give_of(j),
                    "why": j.get("reason", ""),
                }
                for i, j in enumerate(spec["joints"])
            ]
        return []

    @staticmethod
    def parse_limits(
        text: str, channels: Sequence[str]
    ) -> Dict[str, Tuple[Optional[float], Optional[float]]]:
        """The limits typed into a Limits cell (``ptk.ArticulationPlan.
        parse_limits``): ``rz -30..95`` per channel, commas between (a
        one-channel joint may drop the name: ``-30..95``), ``-`` or nothing
        for a free side, ``free`` (or nothing) for none. Every channel of
        *channels* gets an entry; one not named is free.

        Raises:
            ValueError: A channel the joint lacks, or a part that is no
                ``min..max``.
        """
        return ptk.ArticulationPlan.parse_limits(text, channels)

    def refresh_table(self):
        table = self.ui.tbl_joints
        rows = self._rows()
        self._refreshing = True
        try:
            self._sync_adjust()
            if self.rig is not None and self.plan is None:
                self.ui.chk_end_control.setChecked(self.rig.end_control is not None)
            if not rows:
                # ``add`` of nothing is a one-column table with no headers.
                table.setRowCount(0)
                return
            table.add(
                [
                    [
                        r["part"],
                        r["type"],
                        r["parent"],
                        ptk.ArticulationPlan.limits_text(r["limits"]),
                        f"{r['give']:g}",
                        r["why"],
                    ]
                    for r in rows
                ],
                headers=self.COLUMNS,
            )
            editable = {self.LIMITS_COLUMN, self.GIVE_COLUMN}
            for row, entry in enumerate(rows):
                for col in range(table.columnCount()):
                    item = table.item(row, col)
                    if item is not None and col not in editable:
                        item.setFlags(item.flags() & ~QtCore.Qt.ItemIsEditable)
                combo = QtWidgets.QComboBox()
                combo.addItems(self.TYPES)
                combo.setCurrentText(entry["type"])
                combo.currentTextChanged.connect(
                    lambda kind, e=entry: self._retype(e, kind)
                )
                table.setCellWidget(row, self.TYPE_COLUMN, combo)
            table.resizeColumnsToContents()
        finally:
            self._refreshing = False

    def _sync_adjust(self) -> None:
        """Adjust Pivots shows whether the rig in the table is adjusting."""
        on = False
        if self.rig is not None and self.plan is None:
            try:
                on = self.rig.adjusting
            except RuntimeError:  # the rig is gone
                on = False
        box = self.ui.chk_adjust
        if box.isChecked() != on:
            blocked = box.blockSignals(True)
            box.setChecked(on)
            box.blockSignals(blocked)

    def _refresh_later(self) -> None:
        """Refresh after the current signal: a refresh replaces the cell
        widgets and items, and the sender may be one of them."""
        QtCore.QTimer.singleShot(0, self.refresh_table)

    def _entry(self, row: int) -> Optional[dict]:
        rows = self._rows()
        return rows[row] if 0 <= row < len(rows) else None

    def _retype(self, entry: dict, kind: str) -> None:
        with self._reporting(f"Retyping {entry['part']}"):
            if self.plan is not None:
                # A type's own limits only: a slide's travel means nothing to a hinge.
                ptk.ArticulationPlan.retype(self.plan["joints"][entry["index"]], kind)
                self.logger.info(f"{entry['part']}: planned as a {kind}.")
            elif self.rig is not None:
                self.rig.edit_joint(entry["id"], type=kind)
                self.logger.info(
                    f"{entry['part']}: rebuilt as a {kind}, animation kept."
                )
        self._refresh_later()

    def _on_item_changed(self, item) -> None:
        if self._refreshing or item is None:
            return
        entry = self._entry(item.row())
        if entry is None:
            return
        if item.column() == self.LIMITS_COLUMN:
            self._set_limits(entry, item.text())
        elif item.column() == self.GIVE_COLUMN:
            with self._reporting(f"Setting {entry['part']}'s give"):
                self._set_give(entry, float(item.text()))
        else:
            return
        self._refresh_later()

    def _set_limits(self, entry: dict, text: str) -> None:
        with self._reporting(f"Setting {entry['part']}'s limits"):
            channels = self.tk.ArticulatedRig.JOINT_TYPES[entry["type"]][0]
            limits = self.parse_limits(text, channels)
            if self.plan is not None:
                self.plan["joints"][entry["index"]]["limits"] = {
                    c: list(v) for c, v in limits.items() if v != (None, None)
                }
            elif self.rig is not None:
                with self.tk.CoreUtils.undo_chunk("Articulated Rig: Set Limits"):
                    for channel, (lo, hi) in limits.items():
                        self.rig.set_limits(entry["id"], channel, lo, hi)
            self.logger.info(
                f"{entry['part']}: limits {ptk.ArticulationPlan.limits_text(limits)}."
            )

    def _set_give(self, entry: dict, give: float) -> None:
        give = max(0.0, give)
        if self.plan is not None:
            joint = self.plan["joints"][entry["index"]]
            joint["weights"] = {
                c: give for c in self.tk.ArticulatedRig.JOINT_TYPES[joint["type"]][0]
            }
        elif self.rig is not None:
            self.rig.set_weight(entry["id"], give)

    def _on_give_wheel(self, row: int, col: int, steps: int, modifiers) -> None:
        entry = self._entry(row)
        if entry is None or col != self.GIVE_COLUMN:
            return
        fast = bool(modifiers & QtCore.Qt.ShiftModifier)
        step = self.GIVE_STEP * (10 if fast else 1)
        with self._reporting(f"Setting {entry['part']}'s give"):
            self._set_give(entry, round(entry["give"] + steps * step, 6))
        self._refresh_later()

    def _on_rows_selected(self) -> None:
        if self._refreshing:
            return
        table = self.ui.tbl_joints
        rows = sorted({index.row() for index in table.selectedIndexes()})
        nodes = []
        with self._reporting("Selecting"):
            for row in rows:
                entry = self._entry(row)
                if entry is None:
                    continue
                if self.plan is not None:
                    joint = self.plan["joints"][entry["index"]]
                    nodes += self.plan["links"][joint["link"]]
                elif self.rig is not None:
                    nodes.append(self.rig.control(entry["id"]))
            if nodes:
                self.tk.ArticulatedRig.select(nodes)

    # ============================================================== actions
    def _selection(self) -> list:
        """What the actions act on: the host's read of the selection (see the
        module docstring)."""
        return self.tk.ArticulatedRig.selection()

    def _selected_rig(self):
        """The rig the selection touches, else the one the table shows; the
        table then shows it (a plan left from an analysis gives way)."""
        rig = None
        for node in self._selection():
            rig = self.tk.ArticulatedRig.for_node(node)
            if rig is not None:
                break
        if rig is None and self.rig is not None:
            try:
                _ = self.rig.group
                rig = self.rig
            except RuntimeError:
                self.rig = None
        if rig is None:
            self.logger.error("Select a part or control of an articulated rig.")
            return None
        shown = self.plan is None and self.rig is not None
        changed = not shown or self.rig.group_uuid != rig.group_uuid
        self.rig, self.plan = rig, None
        rig.ensure_solver()
        if changed:
            self.refresh_table()
        return rig

    def _selected_joints(self, rig) -> List[str]:
        return sorted({rig.joint_id_of(n) for n in self._selection()} - {None})

    def btn_analyze(self):
        selection = self._selection()
        if not selection:
            self.logger.error("Select the prop (its group, or its parts).")
            return
        ordered = self.ui.cmb_source.currentIndex() == 1
        plan = None
        with self._reporting("Analysis"):
            plan = self.tk.ArticulatedRig.analyze(selection, ordered=ordered)
        if plan is None:
            return
        self.plan, self.rig = plan, None
        lines = [
            f"{self._name(plan['links'][j['link']][0])}: {j['type']} ({j['reason']})"
            for j in plan["joints"]
        ]
        self.logger.log_group("Proposed joints", lines)
        for part in plan["unreached"]:
            self.logger.warning(f"{self._name(part)} touches nothing; left out.")
        self.refresh_table()

    def btn_build(self):
        if self.plan is None:
            self.btn_analyze()
        if self.plan is None:
            return
        name = self.ui.txt_name.text().strip() or None
        end_control = self.ui.chk_end_control.isChecked()
        try:
            self.rig = self.tk.ArticulatedRig.create(
                self.plan["links"],
                self.plan["joints"],
                name=name,
                end_control=end_control,
            )
        except Exception as error:  # noqa: BLE001 -- a panel reports, never raises
            self.logger.error(f"Build failed: {error}")
            self.sb.message_box(f"Build failed:<br>{error}")
            return
        self.plan = None
        # The rig group's name is unique (the build numbers past any taken one).
        link = self.logger.log_link(
            self.rig.name, "select", node=self._name(self.rig.group)
        )
        self.logger.info(f"Built {link}: {len(self.rig.joint_ids())} joints.")
        if self.rig.end_control:
            self.logger.info(
                "Move the red end control: the stand follows. The FK controls "
                "shape the arm under it."
            )
        self.refresh_table()

    def _on_end_control_toggled(self, checked: bool) -> None:
        """With a built rig shown, the checkbox adds or drops its end control;
        before a build it is only the build's option."""
        if self._refreshing or self.rig is None or self.plan is not None:
            return
        with self._reporting("The end control"):
            if bool(self.rig.end_control) != checked:
                self.rig.set_end_control(checked)
                self.logger.info(
                    f"{self.rig.name}: end control {'added' if checked else 'dropped'}."
                )
        self._refresh_later()

    def _on_adjust_toggled(self, checked: bool) -> None:
        """Checked: the selected rig's pivots come out as handles. Cleared:
        the rig is rebuilt on them."""
        if self._refreshing:
            return
        rig = self._selected_rig()
        if rig is not None:
            with self._reporting("Adjusting the pivots"):
                if checked:
                    handles = rig.begin_adjust()
                    self.tk.ArticulatedRig.select(list(handles.values()))
                    self.logger.info(
                        f"{rig.name}: move and turn the pivot handles, then clear "
                        "Adjust Pivots to rebuild on them."
                    )
                elif rig.end_adjust():
                    self.logger.info(
                        f"{rig.name}: rebuilt on the adjusted pivots; animation "
                        "carried across."
                    )
                else:
                    self.logger.info(f"{rig.name}: no pivot moved; nothing changed.")
        self._refresh_later()

    def btn_grab(self):
        with self._reporting("The Grab Tool"):
            self.tk.ArticulatedRigGrab.activate()
            self.logger.info("Grab Tool: drag a rigged part in the viewport.")

    def btn_ik_fk(self):
        rig = self._selected_rig()
        if rig is None:
            return
        with self._reporting("Switching IK / FK"):
            if not rig.end_control:
                self.logger.error(
                    f"{rig.name} has no end control: tick End Control to add one."
                )
                return
            on = rig.switch_ik()
            self.logger.info(
                f"{rig.name}: IK on -- the end control places the end part."
                if on
                else f"{rig.name}: FK -- the controls pose the joints directly."
            )

    def match_end_control(self):
        rig = self._selected_rig()
        if rig is None:
            return
        with self._reporting("Matching the end control"):
            rig.match_end_control()
            self.logger.info(f"{rig.name}: the end control is on the end part.")

    def btn_rest(self):
        rig = self._selected_rig()
        if rig is None:
            return
        with self._reporting("The rest pose"):
            rig.reset_pose()
            self.logger.info(f"{rig.name}: at rest.")

    def btn_insert(self):
        rig = self._selected_rig()
        if rig is None:
            return
        parts = rig.parts_of(self._selection())
        if not parts:
            self.logger.error("Select the parts to split off (not their controls).")
            return
        kind = self.INSERT_TYPES[self.ui.cmb_insert_type.currentIndex()]
        with self._reporting("Split"):
            rig.insert_joint(parts, joint_type=kind)
            self.logger.info(f"Split off {', '.join(self._name(p) for p in parts)}.")
        self.refresh_table()

    def btn_fold(self):
        rig = self._selected_rig()
        if rig is None:
            return
        with self.tk.CoreUtils.undo_chunk("Articulated Rig: Fold"):
            for joint_id in self._selected_joints(rig):
                with self._reporting(f"Folding {joint_id}"):
                    rig.remove_joint(joint_id)
                    self.logger.info(
                        f"Folded {joint_id} back into the link it hung off."
                    )
        self.refresh_table()

    def btn_limits_from_pose(self):
        rig = self._selected_rig()
        if rig is None:
            return
        joint_types = self.tk.ArticulatedRig.JOINT_TYPES
        with self._reporting("Limits from the pose"), self.tk.CoreUtils.undo_chunk(
            "Articulated Rig: Limits From Pose"
        ):
            for joint_id in self._selected_joints(rig):
                joint = next(j for j in rig.spec["joints"] if j["id"] == joint_id)
                for channel in joint_types[joint["type"]][0]:
                    value = rig.channel_value(joint_id, channel)
                    if abs(value) < 1.0e-6:
                        continue  # at rest: this channel says nothing about a stop
                    side = "min" if value < 0 else "max"
                    rig.set_limit_from_pose(joint_id, channel, side)
                    self.logger.info(f"{joint_id}.{channel} {side} = {value:.3g}")
        self.refresh_table()

    def btn_clear_limits(self):
        rig = self._selected_rig()
        if rig is None:
            return
        joint_types = self.tk.ArticulatedRig.JOINT_TYPES
        with self._reporting("Clearing limits"), self.tk.CoreUtils.undo_chunk(
            "Articulated Rig: Clear Limits"
        ):
            for joint_id in self._selected_joints(rig):
                joint = next(j for j in rig.spec["joints"] if j["id"] == joint_id)
                for channel in joint_types[joint["type"]][0]:
                    rig.set_limits(joint_id, channel, None, None)
                self.logger.info(f"{joint_id}: limits cleared.")
        self.refresh_table()

    def btn_rebuild(self):
        rig = self._selected_rig()
        if rig is None:
            return
        with self._reporting("Rebuild"):
            rig.rebuild()
            self.logger.info(f"Rebuilt {rig.name}; animation carried across.")
        self.refresh_table()

    def btn_remove(self):
        rig = self._selected_rig()
        if rig is None:
            return
        name = rig.name
        with self._reporting("Remove"):
            rig.teardown()
            self.rig = None
            self.logger.info(f"Removed {name}; every part is back as it was.")
        self.refresh_table()
