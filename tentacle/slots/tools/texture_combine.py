# !/usr/bin/python
# coding=utf-8
"""Texture Combine: several materials into one atlas and one material, in
place -- or UVs / textures moved between meshes.

One Slots class for both hosts over the host toolkit (``self.tk``). Two modes
over one window, picked by the Mode combo and shown by uitk's
``FieldVisibility`` -- each mode its own groups, the Output and Material
groups shared:

* **Combine** -- the selected meshes' materials into one atlas and one
  material, in place (the host's ``TextureCombine``). The Combined Set picker
  re-opens a stored combine (its option box selects, re-combines revised maps,
  restores or forgets it); the Sources table shows each source material's
  share of the atlas and the resolution it keeps, live, and takes scale
  overrides per material, mesh or island.
* **Transfer** -- UVs or textures from a source mesh onto targets
  (:class:`~tentacle.slots.tools._texture_combine.transfer_mode.TransferMode`,
  composed here), over the host's ``TextureTransfer``.

A thin driver: every decision about the scene is the host's -- which meshes a
selection names, which faces a row covers, how it selects them (Maya: the
selection; Blender: faces in Edit Mode).
"""

import os
from typing import Any, Dict, List, Optional

import pythontk as ptk

from tentacle import Slots

from ._texture_combine.transfer_mode import TransferMode


class TextureCombineSlots(Slots, ptk.LoggingMixin):
    """Switchboard slots for the ``texture_combine.ui`` panel."""

    HELP_URL = "https://github.com/m3trik/mayatk/blob/main/docs/texture_combine.md"
    MODE_COMBINE = "combine"
    MODE_TRANSFER = "transfer"
    #: Material row data for Overwrite target (``TextureTransfer``'s
    #: ``assign_from="in_place"``).
    SHADER_IN_PLACE = "in_place"
    COLUMNS = ("Source", "Maps", "Scale", "Share", "Res")
    SCALE_COL = 2
    ATLAS_SIZES = (1024, 2048, 4096, 8192)
    #: A source that keeps less than this share of its resolution is flagged
    #: (four maps into one map of their size keep half each -- expected).
    SQUEEZE_WARN = 0.35
    #: Above this many selected meshes the table stops re-reading on every
    #: selection change (Combine still reads them, on demand).
    AUTO_FOLLOW_MAX = 200
    #: Wheel notch -> scale factor on the Scale column (Shift: coarse).
    WHEEL_STEP, WHEEL_STEP_COARSE = 1.05, 1.25

    def __init__(self, switchboard):
        super().__init__(switchboard)
        self.logger.setLevel("WARNING")
        self.ui = self.sb.loaded_ui.texture_combine
        self.engine = self.tk.TextureCombine(log_level="WARNING")
        #: The shader types the host can rebuild a material on (Maya's
        #: ShaderConverter targets; Blender: none -- a material is one graph).
        self._shader_types: Dict[str, str] = dict(
            self.tk.TextureTransfer.shader_types()
        )
        self.transfer = TransferMode(self)
        self._inputs = None
        self._rows: List[Dict[str, Any]] = []
        self._plan = None
        self._error = ""
        self._table_rows: List[tuple] = []
        self._updating = False
        self._fields = None
        self._name_recent = None
        self._timer = None
        # Deferred: the switchboard builds this instance mid-load, before every
        # child widget is wired onto self.ui.
        self.sb.QtCore.QTimer.singleShot(0, self._initialize_ui)

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------
    def _initialize_ui(self) -> None:
        """Wire what reads several widgets at once, once all of them exist."""
        ui = self.ui
        self._refresh_sets()
        # on_change also fires for the first application, so binding the combo
        # is what brings the panel up in its persisted mode.
        self._fields = self.sb.FieldVisibility(
            on_change=lambda mode: self._on_mode(mode)
        )
        shared = [ui.grp_output, ui.t_affix]
        # The Material row: Transfer always reads it; a combine reads it only
        # for a shader type to rebuild on. A host with none (Blender) shows it
        # in Transfer alone, where in Combine it would offer choices that do
        # nothing.
        combine_material = [ui.cmb_shader] if self._shader_types else []
        self._fields.define(
            self.MODE_COMBINE,
            [ui.cmb_set, ui.grp_sources, ui.grp_layout, *shared, *combine_material],
        ).define(
            self.MODE_TRANSFER,
            [ui.grp_transfer, ui.grp_textures, ui.chk_assign, ui.cmb_shader, *shared],
        ).group(ui.grp_material).bind(ui.cmb_mode)

        # A debounced re-read: SelectionChanged fires per click of a drag.
        self._timer = self.sb.QtCore.QTimer(ui)
        self._timer.setSingleShot(True)
        self._timer.setInterval(250)
        self._timer.timeout.connect(self._follow_selection)

        jobs = self.tk.ScriptJobManager.instance()
        for event, handler in (
            ("SelectionChanged", self._timer.start),
            ("SceneOpened", self._scene_changed),
            ("NewSceneOpened", self._scene_changed),
            ("Undo", self._scene_changed),
            ("Redo", self._scene_changed),
        ):
            try:
                jobs.subscribe(event, handler, owner=self)
            except Exception as error:  # noqa: BLE001 -- never block the panel
                self.logger.debug(f"scene event {event!r} unavailable ({error})")
        jobs.connect_cleanup(ui, owner=self)

    def _on_mode(self, mode) -> None:
        if self._fields is None:
            return
        combine = mode == self.MODE_COMBINE
        self.ui.b000.setText(self._run_label() if combine else "Transfer")
        if combine:
            # Transfer mode greys the shared rows with its texture pass
            # (sync_shared); Combine always writes and assigns.
            for name in ("t_output", "cmb_quality", "s_padding", "t_affix"):
                getattr(self.ui, name).setEnabled(True)
            self.ui.cmb_shader.setEnabled(True)
            self._on_set()
        else:
            self.transfer.sync()

    def _run_label(self) -> str:
        return "Update" if self._current_set() else "Combine"

    def _scene_changed(self, *_) -> None:
        self._refresh_sets()
        self._on_set()

    # ------------------------------------------------------------------
    # Header + mode
    # ------------------------------------------------------------------
    def header_init(self, widget) -> None:
        widget.config_buttons("menu", "collapse", "hide")
        widget.menu.add(
            "QPushButton",
            setText="Open Output Folder",
            setObjectName="open_output_folder",
            setToolTip="Open the folder the maps are written to.",
        )
        uv = self.tk.TextureTransfer.TERMS["uv"]
        widget.set_help_text(
            self.sb.tooltip.fmt(
                title="Texture Combine",
                body="Merge several materials into one atlas and one material, in "
                "place -- or move UVs / textures between meshes.",
                steps=[
                    "<b>Combine</b>: select the meshes. The table lists each source "
                    "material with the share of the atlas it gets and the "
                    "resolution it keeps; edit <b>Scale</b> (or add a mesh or "
                    "island override) to rebalance, then <b>Combine</b>.",
                    "<b>Sizing</b>: equal texel density, or keep each map's own "
                    "island proportions. Stacked islands stay stacked.",
                    "A stored combine re-opens from the <b>Combined Set</b> picker: "
                    "<b>Update</b> re-packs it; its option box re-combines revised "
                    "maps into the same layout, restores the originals, or forgets it.",
                    f"<b>Transfer</b>: the source's {uv} onto the targets, or its "
                    "textures into each target's own layout.",
                ],
                notes=[
                    "Nothing is duplicated, and the originals are recorded in the scene."
                ],
            ),
            url=self.HELP_URL,
        )

    def cmb_mode_init(self, widget) -> None:
        widget.setToolTip(
            self.sb.tooltip.fmt(
                title="Mode",
                bullets=[
                    "<b>Combine</b> -- the selected meshes' materials into one atlas "
                    "and one material, in place.",
                    "<b>Transfer</b> -- UVs or textures from a source mesh onto targets.",
                ],
            )
        )
        widget.addItem("Mode: Combine", self.MODE_COMBINE)
        widget.addItem("Mode: Transfer", self.MODE_TRANSFER)

    def open_output_folder(self) -> None:
        entry = self.ui.t_output.text().strip()
        try:
            path = self.tk.TextureTransfer.resolve_output_dir(entry or None)
        except ValueError:
            return self.status(
                "Save the scene first: the output folder is the project's."
            )
        if not os.path.isdir(path):
            return self.status(f"Nothing written yet: {path}")
        ptk.FileUtils.open_explorer(path, logger=self.logger)

    # ------------------------------------------------------------------
    # Combined Set picker
    # ------------------------------------------------------------------
    def cmb_set_init(self, widget) -> None:
        widget.setToolTip(
            self.sb.tooltip.fmt(
                title="Combined Set",
                body="<b>New Combine</b> follows the selection; a stored combine "
                "re-opens its settings and overrides (<b>Update</b> re-packs it).",
                bullets=[
                    "<b>Select</b> -- its meshes.",
                    "<b>Re-combine</b> -- re-read revised source maps into the SAME "
                    "layout (no re-pack).",
                    "<b>Restore</b> -- the original UVs and materials, exactly.",
                    "<b>Forget</b> -- drop the record, keeping the scene as it is.",
                ],
            )
        )
        widget.restore_state = False  # the scene's sets, not a preference
        box = widget.option_box
        self._set_actions = [
            box.add_action(
                callback=self.select_set,
                icon="select",
                tooltip="Select the combine's meshes.",
            ),
            box.add_action(
                callback=self.recombine_set,
                icon="refresh",
                tooltip="Re-combine: re-read revised source maps into the same layout.",
            ),
            box.add_action(
                callback=self.restore_set,
                icon="restore",
                tooltip="Restore the original UVs and materials (undoable).",
            ),
            box.add_action(
                callback=self.forget_set,
                icon="trash",
                tooltip="Forget the combine's record; the scene stays as it is.",
            ),
        ]
        widget.currentIndexChanged.connect(lambda *_: self._on_set())

    def _current_set(self) -> str:
        widget = getattr(self.ui, "cmb_set", None)
        return (widget.currentData() or "") if widget is not None else ""

    def _refresh_sets(self, select: Optional[str] = None) -> None:
        combines = self.tk.TextureCombine
        widget = self.ui.cmb_set
        keep = select if select is not None else self._current_set()
        widget.blockSignals(True)
        try:
            widget.clear()
            widget.addItem("New Combine", "")
            for name in combines.names():
                revised = len(combines.stale(name))
                label = f"{name}  ({revised} map(s) revised)" if revised else name
                widget.addItem(label, name)
            index = widget.findData(keep)
            widget.setCurrentIndex(max(index, 0))
        finally:
            widget.blockSignals(False)

    def _on_set(self) -> None:
        name = self._current_set()
        for action in getattr(self, "_set_actions", ()):
            action.widget.setEnabled(bool(name))
        self.ui.t_name.setEnabled(not name)
        if self._fields is None or self._fields.mode != self.MODE_COMBINE:
            return
        self.ui.b000.setText(self._run_label())
        if not name:
            self._rows = []
            self._follow_selection(force=True)
            return
        entry = self.tk.TextureCombine.entry(name) or {}
        self._apply_settings(entry.get("settings") or {})
        self.ui.t_name.setText(name)
        self._rows = [dict(r) for r in entry.get("rows") or []]
        try:
            self._inputs, self._error = self.engine.inputs_for(name), ""
        except ValueError as error:
            self._inputs, self._error = None, str(error)
        self._replan()

    def _apply_settings(self, settings: Dict[str, Any]) -> None:
        ui = self.ui
        pairs = [
            (ui.cmb_sizing, settings.get("sizing")),
            (ui.cmb_normalize, settings.get("normalize")),
            (ui.cmb_atlas, settings.get("map_size")),
            (ui.cmb_quality, settings.get("supersample")),
        ]
        if self._shader_types:  # the Material row is a combine's only then
            pairs.append(
                (ui.cmb_shader, settings.get("assign_shader_type") or "source")
            )
        for combo, value in pairs:
            index = combo.findData(value) if value is not None else -1
            if index >= 0:
                combo.blockSignals(True)
                combo.setCurrentIndex(index)
                combo.blockSignals(False)
        if "padding" in settings:  # None: Auto (-1), scaled to the atlas
            padding = settings["padding"]
            ui.s_spacing.setValue(-1 if padding is None else int(padding))
        if settings.get("texture_padding") is not None:
            ui.s_padding.setValue(int(settings["texture_padding"]))
        ui.chk_rotate.setChecked(bool(settings.get("rotate", True)))
        ui.chk_lightmaps.setChecked(bool(settings.get("lightmaps", True)))
        ui.t_output.setText(settings.get("output_dir") or "")
        affix = (settings.get("assign_prefix") or "") or (
            settings.get("assign_suffix") or ""
        )
        ui.t_affix.setText(affix)
        self._sync_layout()

    def select_set(self) -> None:
        name = self._current_set()
        combines = self.tk.TextureCombine
        members = combines.members(name) if name else []
        if not members:
            return self.status(f"{name}: none of its meshes are in the scene.")
        combines.select(members)
        self.status(f"Selected {len(members)} mesh(es) of {name}.")

    def recombine_set(self) -> None:
        name = self._current_set()
        if not name:
            return
        with self.sb.progress(text=f"Working: Re-combine {name}") as tick:
            tick()
            try:
                result = self.engine.recombine(name)
            except ValueError as error:
                return self.sb.message_box(f"<b>Re-combine:</b><br>{error}")
        self._refresh_sets(select=name)
        self.sb.message_box(
            f"Re-combined <b>{name}</b>: <b>{len(result['maps'])}</b> map(s) re-read "
            f"for <b>{result['meshes']}</b> mesh(es), layout unchanged."
            + self._folder_link(result["maps"])
        )

    def restore_set(self) -> None:
        name = self._current_set()
        if not name:
            return
        try:
            restored = self.engine.restore(name, forget=True)
        except ValueError as error:
            return self.sb.message_box(f"<b>Restore:</b><br>{error}")
        self._refresh_sets(select="")
        self._on_set()
        self.sb.message_box(
            f"Restored <b>{len(restored)}</b> mesh(es) of <b>{name}</b>: original UVs "
            "and materials. The combined maps stay on disk; Ctrl+Z undoes."
        )

    def forget_set(self) -> None:
        name = self._current_set()
        if name and self.tk.TextureCombine.forget(name):
            self._refresh_sets(select="")
            self._on_set()
            self.status(f"Forgot {name}; the scene is unchanged.")

    # ------------------------------------------------------------------
    # Sources table
    # ------------------------------------------------------------------
    def tbl_sources_init(self, widget) -> None:
        if not widget.is_initialized:
            widget.is_initialized = True
            widget.setMinimumHeight(120)
            widget.setColumnCount(len(self.COLUMNS))
            widget.setHorizontalHeaderLabels(list(self.COLUMNS))
            QHeaderView = self.sb.QtWidgets.QHeaderView
            header = widget.horizontalHeader()
            header.setStretchLastSection(False)
            header.setSectionResizeMode(0, QHeaderView.Stretch)
            for col in range(1, len(self.COLUMNS)):
                header.setSectionResizeMode(col, QHeaderView.ResizeToContents)
            widget.verticalHeader().setVisible(False)
            widget.setSelectionBehavior(self.sb.QtWidgets.QAbstractItemView.SelectRows)
            widget.set_single_click_edit_columns([self.SCALE_COL])
            widget.set_wheel_scrub_columns([self.SCALE_COL])
            widget.menu.add(
                "QPushButton",
                setText="Select Members",
                setObjectName="select_row_members",
                setToolTip="Select the meshes (or faces) the highlighted row covers.",
            )
            widget.menu.add(
                "QPushButton",
                setText="Remove Override",
                setObjectName="remove_override",
                setToolTip="Remove the highlighted mesh / island override row.",
            )
            widget.menu.add(
                "QPushButton",
                setText="Reset Scales",
                setObjectName="reset_scales",
                setToolTip="Every scale back to 1 and every override removed.",
            )
        previous = getattr(widget, "_texture_combine_handlers", {})
        handlers = {
            "cellChanged": self._on_cell_changed,
            "cellWheelScrolled": self._on_cell_wheel,
        }
        for signal_name, handler in handlers.items():
            signal = getattr(widget, signal_name)
            prior = previous.get(signal_name)
            if prior is not None:
                try:
                    signal.disconnect(prior)
                except (TypeError, RuntimeError):
                    pass
            signal.connect(handler)
        widget._texture_combine_handlers = handlers

    @staticmethod
    def parse_scale(text: str) -> Optional[float]:
        """``0.33``, ``1/3`` or ``33%`` as a float, ``None`` when unreadable."""
        text = (text or "").strip().replace(",", ".")
        try:
            if text.endswith("%"):
                value = float(text[:-1]) / 100.0
            elif "/" in text:
                num, den = text.split("/", 1)
                value = float(num) / float(den)
            else:
                value = float(text)
        except (ValueError, ZeroDivisionError):
            return None
        return value if value > 0 else None

    @staticmethod
    def _res_label(px: float) -> str:
        return f"{px / 1024:.1f}K" if px >= 1024 else f"{int(round(px))}"

    def _scale_of(self, kind: str, target) -> float:
        for row in self._rows:
            if row.get("kind") == kind and row.get("target") == target:
                return float(row.get("scale", 1.0))
        return 1.0

    def _set_scale(self, table_row: int, value: float) -> None:
        if not (0 <= table_row < len(self._table_rows)):
            return
        kind, ref = self._table_rows[table_row]
        value = max(0.01, min(100.0, float(value)))
        if kind == "material":
            self._rows = [
                r
                for r in self._rows
                if not (r.get("kind") == "material" and r.get("target") == ref)
            ]
            if abs(value - 1.0) > 1e-6:
                self._rows.insert(
                    0, {"kind": "material", "target": ref, "scale": value}
                )
        else:
            self._rows[ref]["scale"] = value
        self._replan()

    def _on_cell_changed(self, row: int, col: int) -> None:
        if self._updating or col != self.SCALE_COL:
            return
        item = self.ui.tbl_sources.item(row, col)
        value = self.parse_scale(item.text() if item else "")
        if value is None:
            self.status("Scale: type 0.33, 1/3 or 33%.")
            return self._fill_table()
        self._set_scale(row, value)

    def _on_cell_wheel(self, row: int, col: int, steps: int, modifiers) -> None:
        if col != self.SCALE_COL or not (0 <= row < len(self._table_rows)):
            return
        coarse = bool(modifiers & self.sb.QtCore.Qt.ShiftModifier)
        step = self.WHEEL_STEP_COARSE if coarse else self.WHEEL_STEP
        kind, ref = self._table_rows[row]
        current = (
            self._scale_of("material", ref)
            if kind == "material"
            else self._rows[ref]["scale"]
        )
        self._set_scale(row, current * step**steps)

    def _follow_selection(self, force: bool = False) -> None:
        """Re-read the selection into the table (New Combine only)."""
        if self._fields is None or self._fields.mode != self.MODE_COMBINE:
            return
        if self._current_set():
            return
        if not force and not self.ui.isVisible():
            return
        # A scene event must not raise: an unreadable selection reads as none.
        try:
            count = len(self.tk.TextureCombine.resolve_meshes(None))
            if count > self.AUTO_FOLLOW_MAX:
                self._inputs = None
                self._error = (
                    f"{count} meshes selected -- too many to follow live; Combine "
                    "reads them when it runs."
                )
                return self._replan()
            self._inputs, self._error = self.engine.gather(None), ""
        except Exception as error:  # noqa: BLE001
            self._inputs, self._error = None, str(error)
        self._replan()

    def _settings(self) -> Dict[str, Any]:
        ui = self.ui
        return {
            "sizing": ui.cmb_sizing.currentData() or "proportional",
            "normalize": ui.cmb_normalize.currentData() or "resolution",
        }

    def _replan(self) -> None:
        self._plan = None
        if self._inputs is not None:
            try:
                self.engine.apply_rows(self._inputs, self._rows)
                self._plan = self.engine.plan(self._inputs, **self._settings())
            except ValueError as error:
                self._error = str(error)
        self._fill_table()
        self._summarize()

    def _fill_table(self) -> None:
        table = self.ui.tbl_sources
        QtWidgets, Qt = self.sb.QtWidgets, self.sb.QtCore.Qt
        self._updating = True
        try:
            self._table_rows = []
            rows: List[List[Any]] = []
            groups = self._plan.groups if self._plan is not None else {}
            atlas = self.ui.cmb_atlas.currentData() or 4096
            sources = self._inputs.sources if self._inputs is not None else {}
            for mat in sorted(sources, key=lambda m: (m is None, str(m))):
                src = sources[mat]
                stats = groups.get(mat)
                res = int(src.get("resolution") or 0)
                keeps = stats.resolution(atlas) if stats else 0.0
                tip = f"Keeps the detail of a {int(keeps)} px map" + (
                    f" (its source is {res} px: {keeps / res:.0%})." if res else "."
                )
                rows.append(
                    [
                        mat or "(no material)",
                        f"{self._res_label(res)} ({len(src.get('maps') or {})})"
                        if res
                        else "--",
                        f"{self._scale_of('material', mat):.2f}",
                        f"{stats.share:.0%}" if stats else "",
                        (
                            self._res_label(keeps) if stats else "",
                            tip,
                            bool(res and keeps < res * self.SQUEEZE_WARN),
                        ),
                    ]
                )
                self._table_rows.append(("material", mat))
            for index, row in enumerate(self._rows):
                if row.get("kind") == "material":
                    continue
                targets = ptk.make_iterable(row.get("target"))
                leaf = self.tk.TextureCombine.leaf_name(targets[0]) if targets else "?"
                label = (
                    f"   mesh: {leaf}"
                    if row["kind"] == "mesh"
                    else f"   islands: {leaf}"
                )
                rows.append(
                    [
                        label,
                        "",
                        f"{float(row.get('scale', 1)):.2f}",
                        "",
                        ("", "", False),
                    ]
                )
                self._table_rows.append((row["kind"], index))
            table.setRowCount(len(rows))
            flags_ro = Qt.ItemIsSelectable | Qt.ItemIsEnabled
            for r, values in enumerate(rows):
                for c, value in enumerate(values):
                    tip = ""
                    warn = False
                    if isinstance(value, tuple):
                        value, tip, warn = value
                    item = QtWidgets.QTableWidgetItem(str(value))
                    if c != self.SCALE_COL:
                        item.setFlags(flags_ro)
                    if c:
                        item.setTextAlignment(Qt.AlignCenter)
                    if tip:
                        item.setToolTip(tip)
                    if warn:
                        item.setForeground(self.sb.QtGui.QColor("#d8a24a"))
                    table.setItem(r, c, item)
            if not rows and self._error:
                table.setRowCount(1)
                item = QtWidgets.QTableWidgetItem(self._error)
                item.setFlags(Qt.ItemIsEnabled)
                table.setItem(0, 0, item)
                table.setSpan(0, 0, 1, len(self.COLUMNS))
            else:
                table.clearSpans()
        finally:
            self._updating = False

    def _summarize(self) -> None:
        name = self._current_set()
        if self._inputs is None:
            return self.status(self._error or "Select the meshes to combine.")
        mats = [m for m in self._inputs.sources if m]
        meshes = len(self._inputs.transforms)
        stacks = sum(g.stacks for g in self._plan.groups.values()) if self._plan else 0
        atlas = self.ui.cmb_atlas.currentData() or 4096
        text = f"{meshes} mesh(es) · {len(mats)} material(s) -> {atlas} px"
        if stacks:
            text += f" · {stacks} stack(s) kept"
        if name:
            revised = self.tk.TextureCombine.stale(name)
            if revised:
                text = f"{len(revised)} source map(s) revised -- Re-combine. " + text
        else:
            owner = self.tk.TextureCombine.owner(self._inputs.transforms)
            if owner:
                text = f"Already in '{owner}' -- pick it to update. " + text
        self.status(text)

    def select_row_members(self) -> None:
        row = self.ui.tbl_sources.currentRow()
        if not (0 <= row < len(self._table_rows)) or self._inputs is None:
            return
        combines = self.tk.TextureCombine
        kind, ref = self._table_rows[row]
        if kind == "material":
            faces = combines.material_faces(self._inputs, ref)
            if faces:
                combines.select(faces)
        else:
            combines.select(ptk.make_iterable(self._rows[ref]["target"]))

    def remove_override(self) -> None:
        row = self.ui.tbl_sources.currentRow()
        if 0 <= row < len(self._table_rows) and self._table_rows[row][0] != "material":
            del self._rows[self._table_rows[row][1]]
            self._replan()

    def reset_scales(self) -> None:
        self._rows = []
        self._replan()

    def b001(self) -> None:
        """Add the selected meshes as one mesh override row each."""
        meshes = self.tk.TextureCombine.resolve_meshes(None)
        if not meshes:
            return self.status("Select the meshes to override.")
        for mesh in meshes:
            self._rows.append({"kind": "mesh", "target": mesh, "scale": 1.0})
        self._replan()

    def b002(self) -> None:
        """Add the islands under the selected faces as an override row."""
        faces = self.tk.TextureCombine.selected_faces()
        if not faces:
            return self.status(
                "Select faces (or UVs) of the islands to override (Blender: "
                "faces in Edit Mode)."
            )
        self._rows.append({"kind": "faces", "target": faces, "scale": 1.0})
        self._replan()

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------
    def cmb_sizing_init(self, widget) -> None:
        widget.setToolTip(
            self.sb.tooltip.fmt(
                title="Sizing",
                bullets=[
                    "<b>Keep Map Proportions</b> (default) -- each source map's "
                    "islands keep the sizes they have relative to each other in "
                    "that map: the texel-density choices made there survive. The "
                    "maps are then sized against each other by <b>Normalize</b>.",
                    "<b>Texel Density</b> -- every island at the same world texel "
                    "density (times its Scale). A small prop that owned a whole "
                    "map then gets a small share of the atlas.",
                ],
                notes=["Stacked islands (shared texels) stay stacked either way."],
            )
        )
        widget.addItem("Sizing: Keep Map Proportions", "proportional")
        widget.addItem("Sizing: Texel Density", "density")
        widget.currentIndexChanged.connect(
            lambda *_: (self._sync_layout(), self._replan())
        )

    def cmb_normalize_init(self, widget) -> None:
        widget.setToolTip(
            self.sb.tooltip.fmt(
                title="Normalize",
                body="How <b>Keep Map Proportions</b> sizes the maps against each other.",
                bullets=[
                    "<b>Map Resolution</b> (default) -- by source map size: every "
                    "map shrinks by the same factor, a 4K map's islands twice the "
                    "linear size of a 2K map's -- each map's authored texel budget "
                    "kept.",
                    "<b>Texel Density</b> -- each map at the same AVERAGE world texel "
                    "density; its islands keep their ratios around it.",
                ],
            )
        )
        widget.addItem("Normalize: Map Resolution", "resolution")
        widget.addItem("Normalize: Texel Density", "density")
        widget.currentIndexChanged.connect(lambda *_: self._replan())

    def _sync_layout(self) -> None:
        self.ui.cmb_normalize.setEnabled(
            self.ui.cmb_sizing.currentData() == "proportional"
        )

    def cmb_atlas_init(self, widget) -> None:
        widget.setToolTip(
            self.sb.tooltip.fmt(
                title="Atlas",
                body="The combined map size. The <b>Res</b> column shows what each "
                "source keeps at it.",
            )
        )
        for n in self.ATLAS_SIZES:
            widget.addItem(f"Atlas: {n}", n)
        widget.setCurrentIndex(self.ATLAS_SIZES.index(4096))
        widget.currentIndexChanged.connect(
            lambda *_: (self._fill_table(), self._summarize())
        )

    def s_spacing_init(self, widget) -> None:
        widget.setPrefix("Spacing: ")
        widget.setRange(-1, 64)
        widget.setValue(-1)
        widget.setCustomDisplayValues({-1: "Auto"})
        widget.setToolTip(
            self.sb.tooltip.fmt(
                title="Spacing",
                body="Gutter between islands in the atlas, in texels.",
                bullets=["<b>Auto</b> -- scaled to the atlas size (8 px at 2K)."],
            )
        )

    def chk_rotate_init(self, widget) -> None:
        widget.setChecked(True)

    def chk_lightmaps_init(self, widget) -> None:
        widget.setChecked(True)
        widget.setToolTip(
            self.sb.tooltip.fmt(
                title="Lightmaps",
                body="Bring the combined objects' committed lightmaps under the new "
                "material: their atlas is renamed after the combine when they own "
                "it, or their cells are re-packed into one atlas otherwise.",
                notes=[
                    "A lightmap is bound per object, so leaving this off never "
                    "breaks one; objects with none are listed in the report."
                ],
            )
        )

    # ------------------------------------------------------------------
    # Transfer widgets (the controller owns them)
    # ------------------------------------------------------------------
    def cmb_tt_transfer_init(self, widget) -> None:
        self.transfer.init_transfer(widget)

    def cmb_tt_source_init(self, widget) -> None:
        self.transfer.init_source(widget)

    def cmb_tt_targets_init(self, widget) -> None:
        self.transfer.init_targets(widget)

    def cmb_tt_resolution_init(self, widget) -> None:
        self.transfer.init_resolution(widget)

    def t_tt_dst_uvset_init(self, widget) -> None:
        self.transfer.init_uv_sets(self.ui.t_tt_src_uvset, widget)

    def chk_tt_lightmaps_init(self, widget) -> None:
        self.transfer.init_lightmaps(widget)

    # ------------------------------------------------------------------
    # Shared: Output + Material
    # ------------------------------------------------------------------
    def t_name_init(self, widget) -> None:
        widget.setToolTip(
            self.sb.tooltip.fmt(
                title="Output Name",
                body="Names the result: the material and every map wired to it "
                "(<i>&lt;name&gt;_&lt;Channel&gt;.png</i>). In Combine it is also the "
                "combine's name.",
                bullets=["<b>Blank</b> -- the meshes' (or source's) common name."],
                notes=[
                    "Never restored from the last session: it names one deliverable."
                ],
            )
        )
        widget.restore_state = False
        widget.option_box.clear_option = True
        widget.option_box.recent(
            settings_key="uv_transfer_output_names", text_align="left"
        )
        self._name_recent = widget.option_box.find_option(self.sb.RecentValuesOption)

    def record_name(self, name: str) -> None:
        if self._name_recent is not None:
            self._name_recent.record(name)

    def t_output_init(self, widget) -> None:
        widget.setToolTip(
            self.sb.tooltip.fmt(
                title="Output Folder",
                body="Where the maps are written.",
                bullets=[
                    "<b>Blank</b> -- <i>uv_transfer</i> in the project's texture "
                    "folder (Maya: sourceimages; Blender: //textures).",
                    "<b>Relative</b> -- under the project's texture folder (portable).",
                    "<b>Full path</b> -- used as-is.",
                ],
            )
        )
        widget.option_box.clear_option = True
        transfers = self.tk.TextureTransfer

        def start_dir(w=widget):
            try:
                return transfers.resolve_output_dir(w.text().strip() or None) or ""
            except ValueError:
                return ""

        widget.option_box.browse(
            mode="directory",
            title="Output folder",
            tooltip="Browse for the output folder...",
            start_dir=start_dir,
            callback=lambda picked, w=widget: w.setText(
                ptk.FileUtils.relativize_output_dir(picked, transfers.output_base_dir())
            ),
        )

    def cmb_quality_init(self, widget) -> None:
        widget.setToolTip(
            self.sb.tooltip.fmt(
                title="Quality",
                body="Sub-samples per texel axis.",
                bullets=[
                    "<b>Fast</b> (1) -- point sampling; exact for 1:1 layouts.",
                    "<b>Standard</b> (2) -- anti-aliased edges and a box filter for "
                    "islands packed smaller than their source.",
                    "<b>High</b> (3) -- for heavy downscaling.",
                ],
                notes=[
                    "Memory: 8 bytes x quality² x resolution². 4K Standard ~ 540 MB."
                ],
            )
        )
        for label, data in (
            ("Quality: Fast", 1),
            ("Quality: Standard", 2),
            ("Quality: High", 3),
        ):
            widget.addItem(label, data)
        widget.setCurrentIndex(1)

    def s_padding_init(self, widget) -> None:
        widget.setPrefix("Fill: ")
        widget.setRange(-1, 256)
        widget.setValue(-1)
        widget.setCustomDisplayValues({-1: "All"})
        widget.setToolTip(
            self.sb.tooltip.fmt(
                title="Gutter Fill",
                body="How far each island's edge texels are extended into the empty "
                "map around it, in texels.",
                bullets=[
                    "<b>All</b> -- every empty texel (mip-safe, the usual choice)."
                ],
            )
        )

    def chk_assign_init(self, widget) -> None:
        widget.setChecked(True)
        widget.toggled.connect(lambda *_: self.transfer.sync())

    def t_affix_init(self, widget) -> None:
        widget.setToolTip(
            self.sb.tooltip.fmt(
                title="Material Affix",
                body="Affixes the ASSIGNED MATERIAL's name; the maps keep the "
                "Output Name.",
                bullets=[
                    "<b>_MAT</b> -- <i>hero_MAT</i>; <b>MAT_</b> -- <i>MAT_hero</i>.",
                    "The icon pins the side: Auto -> Suffix -> Prefix.",
                ],
            )
        )
        widget.option_box.clear_option = True
        widget.option_box.set_affix(default="auto", convention_key="material")

    def material_affix(self):
        """``(assign_prefix, assign_suffix)`` from the affix row (blank: Auto).

        Blank too while the Material row overwrites the target: the target's
        own material keeps its name, and the row is greyed (:meth:`sync_shared`).
        """
        widget = self.ui.t_affix
        text = (widget.text() or "").strip()
        if not text or self.overwrites_target():
            return "", None
        return widget.option_box.resolve_affix(text, default="suffix")

    def cmb_shader_init(self, widget) -> None:
        bullets = [
            "<b>Same as source</b> -- the source material covering most of "
            "the layout, pointed at the new maps.",
            "<b>Same as target</b> -- the target's own material (Transfer).",
        ]
        if self._shader_types:
            bullets.append("<b>A named type</b> -- rebuilt on that shader.")
        bullets.append(
            "<b>Overwrite target</b> -- no copy (Transfer): each target "
            "material is re-used and keeps its name, and the maps it "
            "reads are overwritten where they are, in their own format. "
            "A channel it has no map for is written fresh and wired in."
        )
        widget.setToolTip(
            self.sb.tooltip.fmt(
                title="Material",
                body="What the targets wear once the maps are written.",
                bullets=bullets,
                notes=[
                    "Overwrite target never creates, copies or reassigns a "
                    "material: one it cannot re-use (the host's default "
                    "material, faces with no material, one another object "
                    "wears) is skipped and named. A map another material or "
                    "the source reads, one read through tiling (Blender: a "
                    "Mapping node) or one packed into the file gets a fresh file.",
                    "Ctrl+Z restores the scene, not the overwritten files.",
                ],
            )
        )
        widget.addItem("Material: Same as source", "source")
        widget.addItem("Material: Same as target", "target")
        for name, label in self._shader_types.items():
            widget.addItem(f"Material: {label}", name)
        # Last: the row persists by INDEX, so an item placed earlier would
        # turn a stored shader type into an overwrite (a host with no shader
        # types keeps the same three).
        widget.addItem("Material: Overwrite target", self.SHADER_IN_PLACE)
        widget.currentIndexChanged.connect(lambda *_: self._on_shader())

    def _on_shader(self) -> None:
        if self._fields is not None and self._fields.mode == self.MODE_TRANSFER:
            self.transfer.sync()

    def overwrites_target(self) -> bool:
        """Whether the Material row re-uses the target's material in place --
        Transfer mode only: a combine always builds its material."""
        return (
            self._fields is not None
            and self._fields.mode == self.MODE_TRANSFER
            and self.ui.cmb_shader.currentData() == self.SHADER_IN_PLACE
        )

    def assign_options(self) -> Dict[str, Any]:
        data = self.ui.cmb_shader.currentData() or "source"
        if data in self.tk.TextureTransfer.ASSIGN_FROM:
            return {"assign_from": data}
        return {"assign_from": "source", "assign_shader_type": data}

    def sync_shared(self, textures: bool = True) -> None:
        """Transfer mode: the Output / Material rows follow the texture pass."""
        ui = self.ui
        for name in ("t_name", "t_output", "cmb_quality", "s_padding"):
            getattr(ui, name).setEnabled(textures)
        assigning = textures and ui.chk_assign.isChecked()
        ui.t_affix.setEnabled(assigning and not self.overwrites_target())
        ui.cmb_shader.setEnabled(assigning)

    # ------------------------------------------------------------------
    # Run
    # ------------------------------------------------------------------
    def status(self, text: str) -> None:
        footer = getattr(self.ui, "footer", None)
        if footer is not None:
            footer.setText(text)

    @staticmethod
    def _folder_link(maps: Dict[str, str]) -> str:
        folder = os.path.dirname(next(iter(maps.values()))) if maps else ""
        return (
            f'<br><a href="action://open?path={folder}">{folder}</a>' if folder else ""
        )

    def b000(self) -> None:
        """Run the current mode."""
        if self._fields is not None and self._fields.mode == self.MODE_TRANSFER:
            return self.transfer.run()
        self.combine()

    def combine(self) -> None:
        ui = self.ui
        name = self._current_set()
        prefix, suffix = self.material_affix()
        spacing = ui.s_spacing.value()
        settings = dict(
            rows=list(self._rows),
            map_size=ui.cmb_atlas.currentData() or 4096,
            padding=None if spacing < 0 else spacing,
            rotate=ui.chk_rotate.isChecked(),
            supersample=ui.cmb_quality.currentData() or 2,
            texture_padding=ui.s_padding.value(),
            output_dir=ui.t_output.text().strip() or None,
            assign_prefix=prefix,
            assign_suffix=suffix,
            assign_shader_type=self.assign_options().get("assign_shader_type"),
            lightmaps=ui.chk_lightmaps.isChecked(),
            **self._settings(),
        )
        verb = "Update" if name else "Combine"
        with self.sb.progress(text=f"Working: {verb}") as tick:
            tick()
            try:
                if name:
                    result = self.engine.update(name, **settings)
                else:
                    # Read the meshes NOW, not the table's cached read: a UV
                    # edit since the selection would otherwise be packed stale.
                    objects = (
                        self._inputs.transforms if self._inputs is not None else None
                    )
                    try:
                        inputs = self.engine.gather(objects)
                    except ValueError as error:
                        return self.sb.message_box(
                            f"<b>Nothing to combine.</b><br>{error}"
                        )
                    typed = ui.t_name.text().strip()
                    result = self.engine.combine(
                        name=typed or None, inputs=inputs, **settings
                    )
                    if typed:
                        self.record_name(typed)
            except (ValueError, RuntimeError) as error:
                return self.sb.message_box(f"<b>{verb}:</b><br>{error}")
        self._refresh_sets(select=result["name"])
        self._on_set()
        self.sb.message_box(self._report(result))

    def _report(self, result: Dict[str, Any]) -> str:
        lines = [
            f"Combined <b>{result['meshes']}</b> mesh(es) into <b>{result['material']}</b>: "
            f"<b>{len(result['maps'])}</b> map(s) at {result['map_size']} px, "
            f"{result['utilization']:.0%} of the atlas filled."
        ]
        sources = self._inputs.sources if self._inputs is not None else {}
        squeezed = []
        for g, stats in result["groups"].items():
            res = int((sources.get(g) or {}).get("resolution") or 0)
            keeps = stats.resolution(result["map_size"])
            if g and res and keeps < res * self.SQUEEZE_WARN:
                squeezed.append(f"{g} keeps {keeps:.0f} of {res} px")
        if squeezed:
            lines.append("Heavily downscaled: " + "; ".join(squeezed) + ".")
        lm = result.get("lightmaps") or {}
        how = lm.get("how")
        if how == "renamed":
            lines.append(f"Lightmaps: their atlas is now <b>{lm['map']}</b>.")
        elif how == "repacked":
            lines.append(
                f"Lightmaps: re-packed into <b>{', '.join(lm['map'])}</b>; maps "
                "nobody reads any more were set aside."
            )
        elif how == "kept":
            lines.append(f"Lightmaps: already in <b>{lm['map']}</b>.")
        unbaked = lm.get("unbaked") or []
        if how and unbaked:
            lines.append(
                f"{len(unbaked)} combined object(s) have no lightmap -- the next bake "
                "gives them one in the same atlas."
            )
        return "<br><br>".join(lines) + self._folder_link(result["maps"])
