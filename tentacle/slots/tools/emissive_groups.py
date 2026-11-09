# !/usr/bin/python
# coding=utf-8
"""Emissive Groups: named face groups whose glow a game engine plays, as materials.

One Slots class for both hosts; the engine is the host library's
``EmissiveGroups`` (pythontk's model over that host's half), reached from
``self.tk``.
"""

from typing import Optional

from tentacle import Slots


class EmissiveGroupsSlots(Slots):
    """Switchboard slots for the ``emissive_groups.ui`` panel.

    Composition over inheritance: a thin driver over the Emissive Groups tool
    (``self.engine``) -- no authoring logic lives here. A group's faces wear a
    copy of their material made for the group; the table lists groups by name,
    and the **Weight** column is scrub- and click-editable (Maya channel-box
    idiom), setting the weight a group rests at. **Sync** (``tb000``) keeps
    each copy in step with its base material.
    """

    COLUMNS = ("Group", "Weight", "Materials", "Faces")
    WEIGHT_COL = 1
    #: pixels of horizontal scrub per full 0-1 weight sweep
    SCRUB_PX_PER_UNIT = 150.0

    def __init__(self, switchboard):
        super().__init__(switchboard)
        self.ui = self.sb.loaded_ui.emissive_groups
        self.engine = self.tk.EmissiveGroups
        self._updating = False
        self._scrub_start = None
        self._scrub_value = None

    # ------------------------------------------------------------------
    # Init
    # ------------------------------------------------------------------

    def header_init(self, widget) -> None:
        widget.config_buttons("menu", "collapse", "hide")
        widget.menu.add(
            "QPushButton",
            setText="Convert Old Groups",
            setObjectName="convert_legacy",
            setToolTip=self.sb.tooltip.fmt(
                title="Convert Old Groups",
                body="Turn groups the old tool made (masks over slots) into "
                "material copies, in one action and one undo step.",
                notes=[
                    "Face-level groups convert exactly, their default and keyed "
                    "weights kept.",
                    "A face in two groups, and a region painted inside a face "
                    "in a mask texture, are reported by name with their fix: "
                    "cut those faces at the source.",
                ],
            ),
        )
        widget.set_help_text(
            self.sb.tooltip.fmt(
                title="Emissive Groups",
                body=(
                    "Group faces into regions whose glow plays on its own: each "
                    "group's faces wear a copy of their material made for the "
                    "group, its emission keyed by the group's weight, so the "
                    "viewport shows what the engine plays."
                ),
                steps=[
                    "Select faces (or meshes), name the group, press Add.",
                    "Set each group's Weight in the table (0 = off, 1 = the "
                    "base material's own glow).",
                    "Key it: table menu &gt; Key Weights @ Current Frame.",
                    "Export as usual: each keyed copy's weight rides the file.",
                ],
                notes=[
                    "A copy shares its base's maps; after changing a base, "
                    "press Sync (an export says which copies are out of step).",
                    "One material per group and material: a face is in one "
                    "group, and a region is whole faces -- cut a face to "
                    "split it.",
                    "The material needs an emission weight to key (Standard "
                    "Surface, Principled BSDF).",
                ],
            )
        )

    def txt000_init(self, widget) -> None:
        """Group-name field -- clearable back to the auto-derived name."""
        widget.option_box.clear_option = True

    def tbl000_init(self, widget) -> None:
        """Table setup: one-time construction, then (re)wire signals and populate.

        The signal wiring runs unconditionally because the ``tbl000`` QWidget
        can outlive this slots instance -- a reload builds a NEW slots object
        on the SAME persisted widget, which already carries
        ``is_initialized``; without the re-wire the handlers stay bound to
        the orphaned instance and silently no-op. The context-menu ITEMS
        stay in the one-time block since they mutate the persisting widget
        (building them twice duplicates the entries).
        """
        if not widget.is_initialized:
            widget.is_initialized = True
            widget.refresh_on_show = True
            widget.setColumnCount(len(self.COLUMNS))
            widget.setHorizontalHeaderLabels(list(self.COLUMNS))

            QHeaderView = self.sb.QtWidgets.QHeaderView
            header = widget.horizontalHeader()
            header.setStretchLastSection(False)
            header.setSectionResizeMode(0, QHeaderView.Stretch)
            for col in range(1, len(self.COLUMNS)):
                header.setSectionResizeMode(col, QHeaderView.ResizeToContents)

            widget.setSelectionBehavior(self.sb.QtWidgets.QAbstractItemView.SelectRows)
            widget.setSelectionMode(self.sb.QtWidgets.QAbstractItemView.SingleSelection)
            # Weight edits like a Maya channel-box field: MMB-drag to scrub,
            # single click to type.
            widget.set_scrub_columns([self.WEIGHT_COL])
            widget.set_single_click_edit_columns([self.WEIGHT_COL])

            widget.menu.add("Separator", setTitle="Group")
            widget.menu.add(
                "QPushButton",
                setText="Select Members",
                setObjectName="select_members",
                setToolTip=self.sb.tooltip.fmt(
                    title="Select Members",
                    body="Select the faces of the highlighted group.",
                ),
            )
            widget.menu.add(
                "QPushButton",
                setText="Remove Group",
                setObjectName="remove_group",
                setToolTip=self.sb.tooltip.fmt(
                    title="Remove Group",
                    body="Give the highlighted group's faces their base material "
                    "back and delete its copies.",
                ),
            )
            widget.menu.add(
                "QPushButton",
                setText="Remove Selected Faces",
                setObjectName="remove_faces",
                setToolTip=self.sb.tooltip.fmt(
                    title="Remove Selected Faces",
                    body="Take the selected faces out of their groups: they wear "
                    "their base material again.",
                ),
            )
            widget.menu.add("Separator", setTitle="Weights")
            widget.menu.add(
                "QPushButton",
                setText="All On",
                setObjectName="weights_all_on",
                setToolTip=self.sb.tooltip.fmt(
                    title="All On",
                    body="Rest every un-keyed group at weight <b>1</b>.",
                ),
            )
            widget.menu.add(
                "QPushButton",
                setText="All Off",
                setObjectName="weights_all_off",
                setToolTip=self.sb.tooltip.fmt(
                    title="All Off",
                    body="Rest every un-keyed group at weight <b>0</b>.",
                ),
            )
            widget.menu.add("Separator", setTitle="Keys")
            widget.menu.add(
                "QPushButton",
                setText="Key Weights @ Current Frame",
                setObjectName="key_weights",
                setToolTip=self.sb.tooltip.fmt(
                    title="Key Weights @ Current Frame",
                    body="Key every group's weight, at its current value and the "
                    "current frame, on each of its copies.",
                ),
            )
            widget.menu.add(
                "QPushButton",
                setText="Remove Keys",
                setObjectName="remove_keys",
                setToolTip=self.sb.tooltip.fmt(
                    title="Remove Keys",
                    body="Delete the highlighted group's weight keys, keeping "
                    "its weight now.",
                ),
            )

        self._wire_table_signals(widget)
        self._refresh_table()

    #: Table signal -> handler name. Bound in :meth:`_wire_table_signals`.
    _TABLE_SIGNALS = {
        "cellChanged": "_on_cell_changed",
        "cellScrubStarted": "_on_scrub_started",
        "cellScrubMoved": "_on_scrub_moved",
        "cellScrubFinished": "_on_scrub_finished",
    }

    def _wire_table_signals(self, widget) -> None:
        """Bind table signals to THIS instance, replacing only OUR bindings.

        Idempotent (see :meth:`tbl000_init`), and deliberately NOT a blanket
        ``signal.disconnect()``: that would also tear out the widget's own
        internal connections -- uitk's ``TableWidget`` wires ``cellChanged``
        to its cell formats' ``on_cell_edited`` in its constructor -- and PySide warns
        ("Failed to disconnect (None) from signal ...") whenever a signal
        has nothing attached. The previous binding is tracked on the widget
        instead and disconnected by reference; holding that reference also
        keeps the receiving slots instance alive for as long as the widget
        points at it.
        """
        previous = getattr(widget, "_emissive_group_handlers", {})
        handlers = {
            name: getattr(self, attr) for name, attr in self._TABLE_SIGNALS.items()
        }
        for name, handler in handlers.items():
            signal = getattr(widget, name)
            prior = previous.get(name)
            if prior is not None:
                try:
                    signal.disconnect(prior)
                except (TypeError, RuntimeError):
                    pass  # already gone (widget or receiver torn down)
            signal.connect(handler)
        widget._emissive_group_handlers = handlers

    # ------------------------------------------------------------------
    # Table
    # ------------------------------------------------------------------

    def _refresh_table(self) -> None:
        table = self.ui.tbl000
        self._updating = True
        try:
            groups = self.engine.list_groups()
            table.setRowCount(len(groups))
            QtWidgets = self.sb.QtWidgets
            Qt = self.sb.QtCore.Qt
            flags_ro = Qt.ItemIsSelectable | Qt.ItemIsEnabled
            for row, (name, data) in enumerate(groups.items()):
                weight = data["weight"]
                values = (
                    name,
                    "" if weight is None else f"{weight:g}",
                    str(len(data["materials"])),
                    str(data["faces"]),
                )
                for col, value in enumerate(values):
                    item = QtWidgets.QTableWidgetItem(value)
                    if col != self.WEIGHT_COL or data["keyed"]:
                        item.setFlags(flags_ro)  # a keyed weight is the animation's
                    if col:
                        item.setTextAlignment(Qt.AlignCenter)
                    table.setItem(row, col, item)
        finally:
            self._updating = False

    def _group_at(self, row: int) -> Optional[str]:
        item = self.ui.tbl000.item(row, 0)
        return item.text() if item else None

    def _selected_group(self) -> Optional[str]:
        row = self.ui.tbl000.currentRow()
        return self._group_at(row) if row >= 0 else None

    def _set_weight(self, row: int, weight: float) -> None:
        name = self._group_at(row)
        if not name:
            return
        self.engine.set_weight(name, weight)
        self._refresh_table()

    def _on_cell_changed(self, row, col) -> None:
        if self._updating or col != self.WEIGHT_COL:
            return
        try:
            weight = float(self.ui.tbl000.item(row, col).text())
        except (TypeError, ValueError):
            self._refresh_table()  # revert an unparseable entry
            return
        self._set_weight(row, weight)

    # Scrub-edit (MMB drag over the Weight cell) --------------------------
    #
    # A drag emits a move per mouse event, so the scene write is deferred to
    # release: the moves only repaint the cell (each ``set_weight`` writes
    # every copy of the group -- doing that per pixel would spam the undo
    # queue and stall the drag).

    def _on_scrub_started(self, row, col) -> None:
        name = self._group_at(row)
        groups = self.engine.list_groups()
        self._scrub_start = groups[name]["weight"] if name in groups else None
        self._scrub_value = None

    def _on_scrub_moved(self, row, col, dx, dy) -> None:
        if self._scrub_start is None:
            return
        weight = self._scrub_start + (dx / self.SCRUB_PX_PER_UNIT)
        self._scrub_value = max(0.0, min(1.0, weight))
        item = self.ui.tbl000.item(row, self.WEIGHT_COL)
        if item is None:
            return
        self._updating = True  # preview only -- don't round-trip through the engine
        try:
            item.setText(f"{self._scrub_value:g}")
        finally:
            self._updating = False

    def _on_scrub_finished(self, row, col) -> None:
        if self._scrub_start is not None and self._scrub_value is not None:
            self._set_weight(row, self._scrub_value)
        self._scrub_start = None
        self._scrub_value = None

    # ------------------------------------------------------------------
    # Buttons
    # ------------------------------------------------------------------

    def b000(self) -> None:
        """Add (or extend) a group from the selection."""
        name = self.ui.txt000.text().strip()
        if not name:
            name = f"group_{len(self.engine.list_groups())}"
        try:
            self.engine.add_group(name)
        except ValueError as error:
            self.sb.message_box(str(error))
            return
        self.ui.txt000.clear()
        self._refresh_table()

    def b001(self) -> None:
        """Remove the selected group (its faces get their base material back)."""
        self.remove_group()

    def b002(self) -> None:
        """Select the group's faces."""
        self.select_members()

    def b003(self) -> None:
        """Check: copies out of step with their base, old-style groups."""
        warnings = self.engine.validate()
        self.sb.message_box(
            "<br>".join(warnings) if warnings else "Emissive groups: clean."
        )
        self._refresh_table()

    # Sync (option box) ----------------------------------------------------

    def tb000_init(self, widget) -> None:
        """Initialize Sync."""
        widget.option_box.menu.setTitle("Sync")
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Report Only",
            setObjectName="chk001",
            setToolTip=self.sb.tooltip.fmt(
                title="Report Only",
                body="Say which copies are out of step with their base, and "
                "change nothing.",
            ),
        )

    def tb000(self, widget) -> None:
        """Keep every copy in step with its base material."""
        report_only = widget.option_box.menu.chk001.isChecked()
        found = self.engine.sync(check_only=report_only)
        if not found:
            message = "Every copy is in step with its base."
        else:
            verb = "Out of step" if report_only else "Synced"
            message = f"{verb}:<br>" + "<br>".join(found)
        self.sb.message_box(message)
        self._refresh_table()

    # Table context menu ---------------------------------------------------

    def select_members(self) -> None:
        name = self._selected_group()
        if not name:
            self.sb.message_box("Select a group row first.")
            return
        try:
            self.engine.select_group(name)
        except ValueError as error:
            self.sb.message_box(str(error))

    def remove_group(self) -> None:
        name = self._selected_group()
        if not name:
            self.sb.message_box("Select a group row first.")
            return
        self.engine.remove_group(name)
        self._refresh_table()

    def remove_faces(self) -> None:
        left = self.engine.remove_faces()
        if not left:
            self.sb.message_box("No selected face is in a group.")
        self._refresh_table()

    def weights_all_on(self) -> None:
        self._set_all_weights(1.0)

    def weights_all_off(self) -> None:
        self._set_all_weights(0.0)

    def _set_all_weights(self, weight: float) -> None:
        for name in self.engine.list_groups():
            self.engine.set_weight(name, weight)
        self._refresh_table()

    def key_weights(self) -> None:
        groups = self.engine.list_groups()
        if not groups:
            self.sb.message_box("No groups to key.")
            return
        for name in groups:
            self.engine.key_weight(name)
        self.sb.message_box(f"Keyed {len(groups)} group weight(s) at the current frame.")
        self._refresh_table()

    def remove_keys(self) -> None:
        name = self._selected_group()
        if not name:
            self.sb.message_box("Select a group row first.")
            return
        cleared = self.engine.remove_keys(name)
        self.sb.message_box(
            f"Removed the weight keys of {', '.join(cleared)}." if cleared else "No keys."
        )
        self._refresh_table()

    # Header menu ----------------------------------------------------------

    def convert_legacy(self) -> None:
        report = self.engine.convert_legacy()
        converted = report["converted"]
        lines = [
            f"Converted {len(converted)} group(s): "
            + ", ".join(f"{n} ({c} faces)" for n, c in converted.items())
            if converted
            else "No old-style groups to convert."
        ]
        lines += report["reported"]
        self.sb.message_box("<br>".join(lines))
        self._refresh_table()
