# !/usr/bin/python
# coding=utf-8
"""Emissive Groups: named face groups whose emissive regions a game engine gates.

One Slots class for both hosts; the engine is the host toolkit's
``EmissiveGroups`` (``self.tk``).
"""

from typing import Optional

from tentacle import Slots


class EmissiveGroupsSlots(Slots):
    """Switchboard slots for the ``emissive_groups.ui`` panel.

    Composition over inheritance: a thin driver over the host's ``EmissiveGroups``
    (``self.tk``)
    — no authoring or bake logic lives here. The table lists groups in slot
    order; the **Weight** column is scrub- and click-editable (Maya
    channel-box idiom) and writes each group's default gate weight. **Bake**
    (``tb000``) runs the encoding chosen in its option box: *Vertex Color*
    (rides the FBX) or *Mask Texture* (an ``_EMask`` image for sub-face
    emissive detail).
    """

    COLUMNS = ("Group", "Slot", "Weight", "Faces")
    WEIGHT_COL = 2
    #: pixels of horizontal scrub per full 0-1 weight sweep
    SCRUB_PX_PER_UNIT = 150.0

    def __init__(self, switchboard):
        super().__init__(switchboard)
        self.ui = self.sb.loaded_ui.emissive_groups
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
            setText="Compact Retired Slots",
            setObjectName="compact_slots",
            setToolTip=self.sb.tooltip.fmt(
                title="Compact Retired Slots",
                body="Reclaim the channel slots left behind by removed groups.",
                notes=[
                    "Breaks any existing engine binding against those slots — "
                    "re-bake and re-export afterward.",
                ],
            ),
        )
        widget.menu.add(
            "QPushButton",
            setText="Republish Export Data",
            setObjectName="republish_export",
            setToolTip=self.sb.tooltip.fmt(
                title="Republish Export Data",
                body="Rewrite the <code>emissive_groups</code> channel on the "
                "<code>data_export</code> node from the current registry.",
                notes=["Runs automatically before every FBX export."],
            ),
        )
        widget.set_help_text(
            self.sb.tooltip.fmt(
                title="Emissive Groups",
                body=(
                    "Author named face groups whose emissive regions the "
                    "game engine can toggle or dim independently, sharing "
                    "one all-on emissive map."
                ),
                steps=[
                    "Select faces (or meshes), name the group, press Add.",
                    "Repeat per independently-controlled region (max 4).",
                    "Set each group's default Weight in the table.",
                    "Bake (option box picks Vertex Color or Mask Texture).",
                    "Export FBX as usual — the manifest rides along.",
                ],
                sections=[
                    (
                        "Encodings",
                        [
                            "<b>Vertex Color</b> — rides the FBX; claims "
                            "the mesh's single engine color stream.",
                            "<b>Mask Texture</b> — an _EMask image; use it "
                            "for emissive detail painted inside a face.",
                        ],
                    )
                ],
                notes=[
                    "Regions in no group keep glowing as baked — only "
                    "group what you intend to control.",
                    "Topology edits can shift face membership; re-run "
                    "Validate after modeling changes.",
                    "Baked-GI bounce light ignores runtime toggles.",
                    "Table menu &gt; Make Weights Keyable adds keyable "
                    "0-1 weights on the data_export carrier. Keyed curves "
                    "drive the Unity controller from both DCCs (Maya: FBX "
                    "custom-property curves; Blender: Scene Exporter "
                    "curve proxies).",
                ],
            )
        )

    def txt000_init(self, widget) -> None:
        """Group-name field — clearable back to the auto-derived name."""
        widget.option_box.clear_option = True

    def tbl000_init(self, widget) -> None:
        """Table setup: one-time construction, then (re)wire signals and populate.

        The signal wiring runs unconditionally because the ``tbl000`` QWidget
        can outlive this slots instance — a reload builds a NEW slots object
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
            for col in (1, self.WEIGHT_COL, 3):
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
                    body="Select the faces belonging to the highlighted group.",
                ),
            )
            widget.menu.add(
                "QPushButton",
                setText="Remove Group",
                setObjectName="remove_group",
                setToolTip=self.sb.tooltip.fmt(
                    title="Remove Group",
                    body="Delete the highlighted group.",
                    notes=[
                        "Its channel slot is <b>retired</b>, never reused, so every "
                        "existing engine binding stays valid.",
                    ],
                ),
            )
            widget.menu.add("Separator", setTitle="Weights")
            widget.menu.add(
                "QPushButton",
                setText="All On",
                setObjectName="weights_all_on",
                setToolTip=self.sb.tooltip.fmt(
                    title="All On",
                    body="Set every group's default weight to <b>1</b>.",
                ),
            )
            widget.menu.add(
                "QPushButton",
                setText="All Off",
                setObjectName="weights_all_off",
                setToolTip=self.sb.tooltip.fmt(
                    title="All Off",
                    body="Set every group's default weight to <b>0</b>.",
                ),
            )
            widget.menu.add("Separator", setTitle="Keyable")
            widget.menu.add(
                "QPushButton",
                setText="Make Weights Keyable",
                setObjectName="make_weights_keyable",
                setToolTip=self.sb.tooltip.fmt(
                    title="Make Weights Keyable",
                    body="Add one keyable 0–1 weight per group on the "
                    "<code>data_export</code> carrier, then publish the manifest.",
                    sections=[
                        (
                            "How the curves travel",
                            [
                                "<b>Maya</b> — shipped natively as FBX "
                                "custom-property curves.",
                                "<b>Blender</b> — shipped by the Scene Exporter as "
                                "transient curve proxies.",
                            ],
                        )
                    ],
                    notes=[
                        "This is the one authoring action that creates the export "
                        "carrier — it is opt-in for that reason.",
                    ],
                ),
            )
            widget.menu.add(
                "QPushButton",
                setText="Key Weights @ Current Frame",
                setObjectName="key_weights",
                setToolTip=self.sb.tooltip.fmt(
                    title="Key Weights @ Current Frame",
                    body="Set a key on every keyable group's weight, at its current "
                    "value and the current frame.",
                ),
            )
            widget.menu.add(
                "QPushButton",
                setText="Remove Keyable Weights",
                setObjectName="remove_keyable_weights",
                setToolTip=self.sb.tooltip.fmt(
                    title="Remove Keyable Weights",
                    body="Delete the keyable weight attributes, <b>including any "
                    "animation on them</b>.",
                    notes=["Groups, slots and default weights are left untouched."],
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
        internal connections — uitk's ``TableWidget`` wires ``cellChanged``
        to its ``_on_cell_edited`` in its constructor — and PySide warns
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
            groups = self.tk.EmissiveGroups.list_groups()
            table.setRowCount(len(groups))
            QtWidgets = self.sb.QtWidgets
            Qt = self.sb.QtCore.Qt
            flags_ro = Qt.ItemIsSelectable | Qt.ItemIsEnabled
            for row, (name, data) in enumerate(groups.items()):
                label = f"{name} (missing)" if data["missing"] else name
                values = (
                    label,
                    str(data["slot"]),
                    f"{data['default']:g}",
                    str(data["faces"]),
                )
                for col, value in enumerate(values):
                    item = QtWidgets.QTableWidgetItem(value)
                    if col != self.WEIGHT_COL:
                        item.setFlags(flags_ro)
                    if col in (1, self.WEIGHT_COL, 3):
                        item.setTextAlignment(Qt.AlignCenter)
                    table.setItem(row, col, item)
        finally:
            self._updating = False

    def _group_at(self, row: int) -> Optional[str]:
        item = self.ui.tbl000.item(row, 0)
        return item.text().replace(" (missing)", "") if item else None

    def _selected_group(self) -> Optional[str]:
        row = self.ui.tbl000.currentRow()
        return self._group_at(row) if row >= 0 else None

    def _set_weight(self, row: int, weight: float) -> None:
        name = self._group_at(row)
        if not name:
            return
        self.tk.EmissiveGroups.set_default(name, weight)
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
    # release: the moves only repaint the cell (each ``set_default`` writes
    # the registry node AND republishes the export manifest — doing that per
    # pixel would spam the undo queue and stall the drag).

    def _on_scrub_started(self, row, col) -> None:
        name = self._group_at(row)
        groups = self.tk.EmissiveGroups.list_groups()
        self._scrub_start = groups[name]["default"] if name in groups else None
        self._scrub_value = None

    def _on_scrub_moved(self, row, col, dx, dy) -> None:
        if self._scrub_start is None:
            return
        weight = self._scrub_start + (dx / self.SCRUB_PX_PER_UNIT)
        self._scrub_value = max(0.0, min(1.0, weight))
        item = self.ui.tbl000.item(row, self.WEIGHT_COL)
        if item is None:
            return
        self._updating = True  # preview only — don't round-trip through the engine
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
            name = f"group_{len(self.tk.EmissiveGroups.list_groups())}"
        try:
            self.tk.EmissiveGroups.add_group(name)
        except ValueError as error:
            self.sb.message_box(str(error))
            return
        self.ui.txt000.clear()
        self._refresh_table()

    def b001(self) -> None:
        """Remove the selected group (retires its slot)."""
        self.remove_group()

    def b002(self) -> None:
        """Select the group's member faces."""
        self.select_members()

    def b003(self) -> None:
        """Validate authoring state."""
        warnings = self.tk.EmissiveGroups.validate()
        self.sb.message_box(
            "<br>".join(warnings) if warnings else "Emissive groups: clean."
        )
        self._refresh_table()

    # Bake (option box) ----------------------------------------------------

    def tb000_init(self, widget) -> None:
        """Initialize Bake."""
        widget.option_box.menu.setTitle("Bake")
        # Qt class name + addItems on the returned widget — passing a uitk
        # class name here silently yields a QLabel.
        cmb = widget.option_box.menu.add(
            "QComboBox",
            setObjectName="cmb000",
            setToolTip=self.sb.tooltip.fmt(
                title="Encoding",
                body="How group membership is carried to the engine.",
                bullets=[
                    "<b>Vertex Color</b> — membership rides the FBX in a color "
                    "set. No textures, but it claims the mesh's single engine "
                    "color stream.",
                    "<b>Mask Texture</b> — membership is rasterized into an "
                    "<code>_EMask</code> image. Use it for emissive detail "
                    "painted inside a face.",
                ],
                notes=[
                    "Either way a group occupies one RGBA channel, so a model "
                    "carries at most 4 of them.",
                ],
            ),
        )
        cmb.addItems(["Vertex Color", "Mask Texture"])
        widget.option_box.menu.add(
            "QSpinBox",
            setPrefix="Resolution: ",
            setObjectName="s000",
            set_limits=[64, 8192],
            setValue=512,
            setToolTip=self.sb.tooltip.fmt(
                title="Resolution",
                body="Pixel size of the baked <code>_EMask</code> image.",
                notes=[
                    "Masks are chunky — 512 usually suffices, independent of "
                    "the emissive map's own resolution.",
                    "<b>Mask Texture</b> encoding only.",
                ],
            ),
        )
        widget.option_box.menu.add(
            "QSpinBox",
            setPrefix="Padding: ",
            setObjectName="s001",
            set_limits=[0, 64],
            setValue=4,
            setToolTip=self.sb.tooltip.fmt(
                title="Padding",
                body="Edge padding, in pixels, bled outside each region.",
                notes=[
                    "Keep it at or above the emissive bake's own padding, or "
                    "seams darken under mipping.",
                    "<b>Mask Texture</b> encoding only.",
                ],
            ),
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Force Over Foreign Color Set",
            setObjectName="chk000",
            setToolTip=self.sb.tooltip.fmt(
                title="Force Over Foreign Color Set",
                body="Bake even when a mesh already carries an unrelated color set.",
                notes=[
                    "The engine imports a single color stream, so the groups may "
                    "not survive the import.",
                    "<b>Vertex Color</b> encoding only.",
                ],
            ),
        )

    def tb000(self, widget) -> None:
        """Bake membership and publish the export manifest."""
        menu = widget.option_box.menu
        try:
            if menu.cmb000.currentIndex() == 0:
                self.tk.EmissiveGroups.bake_vertex_colors(force=menu.chk000.isChecked())
                message = "Vertex colors baked and manifest published."
            else:
                manifest = self.tk.EmissiveGroups.bake_mask(
                    resolution=menu.s000.value(), padding_px=menu.s001.value()
                )
                message = f"Mask baked: {manifest.get('mask', '')}"
        except ValueError as error:
            self.sb.message_box(str(error))
            return
        self.sb.message_box(message)

    # Table context menu ---------------------------------------------------

    def select_members(self) -> None:
        name = self._selected_group()
        if not name:
            self.sb.message_box("Select a group row first.")
            return
        try:
            self.tk.EmissiveGroups.select_group(name)
        except ValueError as error:
            self.sb.message_box(str(error))

    def remove_group(self) -> None:
        name = self._selected_group()
        if not name:
            self.sb.message_box("Select a group row first.")
            return
        self.tk.EmissiveGroups.remove_group(name)
        self._refresh_table()

    def weights_all_on(self) -> None:
        self._set_all_weights(1.0)

    def weights_all_off(self) -> None:
        self._set_all_weights(0.0)

    def _set_all_weights(self, weight: float) -> None:
        for name in self.tk.EmissiveGroups.list_groups():
            self.tk.EmissiveGroups.set_default(name, weight)
        self._refresh_table()

    def make_weights_keyable(self) -> None:
        try:
            plugs = self.tk.EmissiveGroups.make_weights_keyable()
        except ValueError as error:
            self.sb.message_box(str(error))
            return
        self.sb.message_box(
            f"Keyable weight(s) added for {len(plugs)} group(s) on the "
            "data_export carrier; manifest published."
        )

    def key_weights(self) -> None:
        keyable = [
            name
            for name, data in self.tk.EmissiveGroups.list_groups().items()
            if data.get("attr")
        ]
        if not keyable:
            self.sb.message_box("No keyable weights — run Make Weights Keyable first.")
            return
        for name in keyable:
            self.tk.EmissiveGroups.key_weight(name)
        self.sb.message_box(f"Keyed {len(keyable)} weight(s) at the current frame.")

    def remove_keyable_weights(self) -> None:
        removed = self.tk.EmissiveGroups.remove_keyable_weights()
        self.sb.message_box(
            f"Removed keyable weight(s): {', '.join(removed)}."
            if removed
            else "No keyable weights."
        )

    # Header menu ----------------------------------------------------------

    def compact_slots(self) -> None:
        reclaimed = self.tk.EmissiveGroups.compact_slots()
        self.sb.message_box(
            f"Reclaimed slot(s): {reclaimed}. Re-bake and re-export."
            if reclaimed
            else "No retired slots."
        )
        self._refresh_table()

    def republish_export(self) -> None:
        payload = self.tk.EmissiveGroups.refresh_export_metadata()
        self.sb.message_box(
            "Manifest republished." if payload else "No groups; carrier cleared."
        )
