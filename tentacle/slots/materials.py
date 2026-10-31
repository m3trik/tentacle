# !/usr/bin/python
# coding=utf-8
"""Materials: one Slots class for both hosts.

Every scene operation is the host toolkit's ``MatUtils`` (``self.tk``), called
with material NAMES (a stored Blender datablock goes stale on undo; a name
re-resolves), each one undo step in its host. A material that vanished since
the list was read raises ``ValueError`` there; this panel says so and refills.

**The panel is a material table** (``tbl000``), filtered by ``txt000`` with ``b006`` (+, a
new material on the selection) beside it. One row per scene material: its swatch and name,
optional Type / Users / Textures columns (header right-click), then three icon columns --

- **Status**, empty unless something needs attention: a missing texture, a duplicate of
  another material, or a material nothing uses. Clicking it fixes that (open the Texture
  Path Editor, merge into the original, delete), one Undo.
- **Select** the objects using the material (Shift adds to the selection).
- **Assign** it to the selection.

So every common action is one click, several materials can be acted on at once (the row
context menu), and what needs cleaning up is visible without asking. Renaming is a
double-click on the name. Names and swatches paint first; the details pass (type, users,
textures, status: ``MatUtils.get_mat_facts``) runs right after, so the panel opens without
waiting on it. Which materials the selection uses is marked (bold) when the panel shows or
its window is activated (``MainWindow.on_activated``: a click anywhere in it) -- a mark,
never a change to the highlight, so it can't fight the user mid-assign.

**The current material** is the last one highlighted, assigned or adopted
(:meth:`_current_mat`): what ``select_by_mat``, rename, Show Attributes, Open in Editor and
the submenu's Assign row act on. A name, never a widget, so it exists before the table does.

The header menu holds the Tools list (``list001``, its categories as roots -- a header menu
needs no "Tools" row above them) and the scene-wide verbs: Objects Without Material, Remove
Duplicate Materials, Delete All Unused Materials. A new random-colored material is an
Alt-click on + (``b006``) or on any Assign icon. The submenu keeps its own compact surface:
the Assign list (``list000``), Get + Select (``b003``) and Tools.

Options only one host serves are tagged ``requires`` and hidden on the other: the list
filters and Exclude Default Materials (Maya's built-in defaults and Arnold shaders; Blender
has neither), Enable Viewport Opacity and the Arnold Preview Shader (Maya's Viewport 2.0 and
Arnold).

**Keeping up with the scene:** the table refills on show, after its own actions, on a
scene opened or new and on Undo / Redo while it shows (a burst of them -- a held Ctrl+Z --
refills once, when it settles); the selection's bold mark follows SelectionChanged
(``self.tk.ScriptJobManager``: Maya-named events in both hosts). What another tool does
meanwhile (a material made in the shader editor, a reassignment from the viewport) is
caught when the window is activated: a changed material set refills, otherwise the details
and the mark re-read in place, the rows unmoved (the click that activated the window lands
on the row it aimed at). A uitk menu hands activation back as it closes, so an activation
right after a refill (its details pass still queued) reads nothing, and the re-read keeps
an action's report in the footer. The header's refresh button refills on demand.
"""
import pythontk as ptk

from tentacle import Slots


class MaterialsSlots(Slots):
    """The material table, the current material, the header menu, the submenu's
    Assign list and Get + Select, and the material and texture tools."""

    #: tbl000's columns. The three icon columns sit right, where the eye ends a row.
    _MAT_HEADERS = ("Material", "Type", "Users", "Textures", "", "", "")
    COL_NAME, COL_TYPE, COL_USERS, COL_TEXTURES, COL_STATUS, COL_SELECT, COL_ASSIGN = range(7)
    #: Off until the user turns them on (header right-click).
    _OPTIONAL_COLUMNS = (1, 2, 3)
    #: The icon columns' names: their header tooltips, which the header's
    #: column menu lists them by.
    _ICON_HEADERS = {4: "Status", 5: "Select", 6: "Assign"}
    #: The name cell's role holding the label the row was filled with: an edit
    #: is a rename only when the text no longer matches it.
    _LABEL_ROLE = 0x0100 + 1  # Qt.UserRole + 1

    _current = None
    #: What the last action did, shown in place of the next summary.
    _note = None
    #: The note the footer shows, until a refill replaces it with the summary.
    _shown_note = None
    #: Set by a refill until its queued details pass runs.
    _details_pending = False
    #: ``{name: (kind, detail, other)}`` from the last details pass.
    _issues = {}
    #: How long a burst of scene events (a held Ctrl+Z) settles before its one refill.
    _REFILL_DELAY_MS = 100
    #: Scene events after which the table refills (when it shows).
    _REFILL_EVENTS = ("SceneOpened", "NewSceneOpened", "Undo", "Redo")

    #: The material list's filters, in the filter field's option box:
    #: ``(objectName, label, tooltip, the MatUtils.get_scene_mat_names keywords
    #: it sets, the host that serves it)``. A host serving none gets no option
    #: box: an empty one would be a dead button.
    _LIST_FILTERS = (
        (
            "chk_hide_defaults",
            "Hide Default Materials",
            "Hide Maya's built-in default materials (lambert1, standardSurface1, "
            "particleCloud1, ...) from the list.",
            {"exclude_defaults": True},
            "maya",
        ),
        (
            "chk_hide_arnold",
            "Hide Arnold Shaders",
            "Hide Arnold shaders (aiStandardSurface, aiToon, ...) from the list: "
            "useful when every game material carries a parallel Arnold preview "
            "shader (Tools > Arnold Preview Shader).",
            {"exc_renderer": "arnold"},
            "maya",
        ),
    )

    # Tools list: categories group tools by *what they act on*, so the
    # similarly-named texture tools stop reading as interchangeable:
    #   "Materials (scene)"    -- mutate the live shading network.
    #   "Texture Maps (files)" -- operate on texture files on disk.
    # Each row is ``(label, slot_name, tooltip[, requires])``: the slot stays on
    # this class so marking-menu and other entry points can still reach it;
    # *requires* names the one host that serves the row (hidden elsewhere).
    _TOOLS_ITEMS = {
        "Setup": [
            ("Image to Plane", "b021", ""),
            ("Shader Templates", "b011", ""),
            ("Texture Path Editor", "b010", ""),
        ],
        "Materials (scene)": [
            (
                "Mat Updater",
                "b018",
                "Reprocess the textures on selected (or all) scene materials "
                "and re-wire the results back into their shading networks. Works "
                "in-scene: it modifies materials. For per-file work on the "
                "textures themselves, use Map Converter under Texture Maps.",
            ),
            (
                "Game Shader",
                "b009",
                "Build a game-shader material network from texture maps "
                "(Maya: StingrayPBS; Blender: Principled BSDF).",
            ),
            (
                "Arnold Preview Shader",
                "b026",
                "Create a parallel aiStandardSurface so materials preview "
                "correctly under Arnold in Maya.",
                "maya",
            ),
            (
                "Emissive Groups",
                "b027",
                "Author named face groups whose emissive regions a game "
                "engine can toggle or dim independently, sharing one all-on "
                "emissive map. Bakes membership into a vertex color set "
                "(Blender: a color attribute; it rides the FBX) or an _EMask "
                "texture, and publishes the manifest Unity's "
                "EmissiveGroupController reads.",
            ),
        ],
        "Texture Maps (files)": [
            (
                "Map Converter",
                "b016",
                "Standalone texture-file toolbox: convert formats, resize / "
                "optimize, normal-map DirectX↔OpenGL, spec-gloss→PBR, "
                "and pack / unpack ORM · MRAO · MSAO. Operates on files "
                "on disk (or the selection's textures): it does not modify "
                "materials.",
            ),
            (
                "Map Packer",
                "b008",
                "Pack up to four separate channel maps into combined RGBA "
                "textures (ORM, mask maps, …) across texture sets.",
            ),
        ],
        "External": [
            ("Marmoset Bridge", "b019", ""),
            ("Substance Bridge", "b020", ""),
            ("Map Compositor", "b022", ""),
            ("Metashape Workflow", "b023", ""),
            ("RealityCapture Workflow", "b024", ""),
            ("Brush Splat Workflow", "b025", ""),
        ],
        "Utilities": [
            (
                "Reload Scene Textures",
                "b013",
                "Reload file textures for all scene materials, then reset the "
                "viewport.",
            ),
            (
                "Get Material Info",
                "tb001",
                "Show a formatted report of textures, sizes, bit depth, "
                "file size, and optimization recommendations. Scope "
                "(textures, current material, all materials, selected "
                "objects), material filters, and which fields to include "
                "are set via the option box.",
            ),
            (
                "Enable Viewport Opacity",
                "tb002",
                "Wire each material's opacity map into the slot its shader "
                "type uses, so transparency shows in the viewport. Materials "
                "without an opacity map are left alone. Scope (selected, "
                "visible, scene) and the viewport transparency mode are set "
                "via the option box.",
                "maya",
            ),
            (
                "Shader Editor",
                "b007",
                "Open the shader editor (Maya: the Hypershade; Blender: the "
                "Shader Editor).",
            ),
        ],
    }

    #: ``{slot name: (tk) -> AppSpec}`` for Tools entries whose external app may be
    #: absent. Callables rather than specs, because reaching a bridge's ``APP``
    #: imports its engine module and this class body executes for EVERY panel when
    #: the Switchboard builds its slot registry -- the import has to wait until the
    #: list is actually built. ``Slots.gate_on_app`` calls them and tolerates a
    #: failure, so a broken engine costs its own entry a gate, not the whole list.
    #:
    #: ``b022``-``b025`` (Map Compositor and the photogrammetry workflows) are
    #: deliberately absent: those are standalone panels (``tcl_standalone.py``)
    #: that open without their app and say what is missing (Brush offers its
    #: download), so a gate would hide the very panel that explains it.
    _EXTERNAL_APP_GATES = {
        "b019": lambda tk: tk.MarmosetBridge.APP,
        "b020": lambda tk: tk.SubstanceBridge.APP,
    }

    def __init__(self, switchboard):
        super().__init__(switchboard)
        self.ui = self.sb.loaded_ui.materials
        self.submenu = self.sb.loaded_ui.materials_submenu
        #: The material the last Assign Random made (a name): the next one
        #: replaces it when nothing uses it any more.
        self.last_random_material = None

    # ------------------------------------------------------------------ current material
    def _current_mat(self):
        """The current material's name, or None: the last one highlighted,
        assigned or adopted."""
        return self._current

    def _set_current(self, name):
        """Make *name* the current material, and highlight its row when the
        table shows it (signals blocked: this IS the highlight's effect)."""
        self._current = str(name) if name else None
        table = getattr(self.ui, "tbl000", None)
        row = self._row_of(self._current) if table is not None else None
        if row is None:
            return
        blocked = table.blockSignals(True)
        table.selectRow(row)
        table.blockSignals(blocked)

    def _highlighted_mats(self):
        """The highlighted rows' material names, top to bottom."""
        table = self.ui.tbl000
        rows = sorted({index.row() for index in table.selectedIndexes()})
        return [self._row_name(row) for row in rows if not table.isRowHidden(row)]

    def _row_name(self, row):
        item = self.ui.tbl000.item(row, self.COL_NAME)
        return item.data(self.sb.QtCore.Qt.UserRole) if item is not None else None

    def _row_of(self, name):
        table = self.ui.tbl000
        for row in range(table.rowCount()):
            if self._row_name(row) == name:
                return row
        return None

    def _material_gone(self, name):
        """*name* no longer resolves (undone, deleted or renamed meanwhile): say
        so and refill, rather than act on a stale row."""
        self.sb.message_box(
            f"Material <hl>{name}</hl> no longer exists (undone, deleted or "
            "renamed): refreshing the material list."
        )
        self._refresh_material_lists()

    # ------------------------------------------------------------------ the table
    def tbl000_init(self, widget):
        """The material table: built once, re-wired and refilled on every show."""
        if not widget.is_initialized:
            widget.is_initialized = True
            widget.refresh_on_show = True
            QtWidgets = self.sb.QtWidgets
            view = QtWidgets.QAbstractItemView
            widget.verticalHeader().setVisible(False)
            widget.setSelectionBehavior(view.SelectRows)
            widget.setSelectionMode(view.ExtendedSelection)
            widget.setEditTriggers(view.DoubleClicked | view.EditKeyPressed)
            widget.enable_column_config(
                settings_key="tentacle_materials_columns",
                locked=(self.COL_NAME, self.COL_ASSIGN),
                hidden_by_default=self._OPTIONAL_COLUMNS,
            )
            menu = widget.menu
            menu.hide_on_trigger = True
            for text, name, tip in (
                ("Assign", "b028", "Assign the highlighted material to the selection."),
                (
                    "Select Users",
                    "b029",
                    "Select what uses the highlighted material, as assigned: "
                    "faces where it is assigned per face.",
                ),
                (
                    "Select Whole Objects",
                    "b030",
                    "Select every object using the highlighted material.",
                ),
                (
                    "Select Within Selection",
                    "b031",
                    "Narrow the selection to what uses the highlighted material.",
                ),
                (
                    "Show Attributes",
                    "lbl004",
                    "Show the material's attributes (Maya: selects its node for "
                    "the Attribute Editor; Blender: an object using it becomes "
                    "active on its slot, for the Material Properties).",
                ),
                (
                    "Open in Editor",
                    "lbl006",
                    "Graph the material in the shader editor (Maya: the "
                    "Hypershade; Blender: the Shader Editor).",
                ),
                (
                    "Merge Duplicates",
                    "b032",
                    "Merge the highlighted duplicates into the materials they "
                    "duplicate (one Undo).",
                ),
                ("Delete", "lbl002", "Delete the highlighted materials (one Undo)."),
            ):
                menu.add("QPushButton", setText=text, setObjectName=name, setToolTip=tip)
        self._wire_material_table(widget)
        self._fill_materials(widget)

    def _wire_material_table(self, widget):
        """(Re)wire the icon columns and signals to this instance: the table
        outlives a reloaded slots instance, so every init re-wires (each
        handler disconnected by the connection stored for it)."""
        colors = ptk.Palette.status()
        muted = "#555555"
        widget.actions.add(
            self.COL_STATUS,
            states={
                "missing": {
                    "icon": "warning",
                    "color": colors["error"][0],
                    "tooltip": "A texture is missing: click to fix its path.",
                    "action": self._fix_row_issue,
                },
                "duplicate": {
                    "icon": "merge",
                    "color": colors["warn"][0],
                    "tooltip": "A duplicate: click to merge it into the original.",
                    "action": self._fix_row_issue,
                },
                "unused": {
                    "icon": "trash",
                    "color": "#8a8a8a",
                    "tooltip": "Nothing uses it: click to delete it.",
                    "action": self._fix_row_issue,
                },
            },
            header_icon="warning",
        )
        widget.actions.add(
            self.COL_SELECT,
            states={
                "select": {
                    "icon": "select",
                    "color": muted,
                    "tooltip": "Select what uses it (Shift adds to the selection).",
                    "action": self._select_row_users,
                }
            },
            header_icon="select",
        )
        widget.actions.add(
            self.COL_ASSIGN,
            states={
                "assign": {
                    "icon": "import",
                    "color": muted,
                    "tooltip": "Assign it to the selection (Alt: a new random "
                    "material instead).",
                    "action": self._assign_row,
                }
            },
            header_icon="import",
        )
        window = self.ui
        for owner, signal, handler in (
            (widget, "itemSelectionChanged", self._on_material_highlight),
            (widget, "itemChanged", self._on_material_edited),
            (widget, "context_menu_about_to_show", self._fit_material_menu),
            (window, "on_activated", self._sync_with_scene),
        ):
            self._rewire(owner, signal, handler)
        self._follow_scene(widget)

    def _follow_scene(self, table):
        """Subscribe the table to the scene's events, owned by the table:
        the subscriptions go with it, and a reloaded slots instance replaces
        the last one's."""
        mgr = self.tk.ScriptJobManager.instance()
        mgr.unsubscribe_all(table)
        for event in self._REFILL_EVENTS:
            mgr.subscribe(event, self._on_scene_changed, owner=table)
        mgr.subscribe("SelectionChanged", self._on_selection_changed, owner=table)
        if not getattr(table, "_materials_cleanup", False):
            table._materials_cleanup = True
            mgr.connect_cleanup(table, owner=table)
        timer = getattr(table, "_materials_refill_timer", None)
        if timer is None:  # the table's, like the subscriptions
            timer = self.sb.QtCore.QTimer(table)
            timer.setSingleShot(True)
            table._materials_refill_timer = timer
        timer.setInterval(self._REFILL_DELAY_MS)
        self._rewire(timer, "timeout", self._on_refill_due)

    def _on_scene_changed(self, *_):
        """A scene event: refill once the burst settles (each event restarts
        the wait, so a held Ctrl+Z rebuilds the table once, not per step)."""
        if self.ui.isVisible():
            self.ui.tbl000._materials_refill_timer.start()

    def _on_refill_due(self):
        if self.ui.isVisible():
            self._refresh_material_lists()

    def _on_selection_changed(self, *_):
        if self.ui.isVisible():
            self._mark_selection()

    def _sync_with_scene(self, *_):
        """The window was activated: refill if the material set changed since,
        else re-read the details and the mark in place (rows unmoved).

        Nothing to read while a refill's details pass is queued: the refill
        just read the scene (a uitk menu hands activation back as it closes,
        right after the action it ran refilled the table). The re-read keeps
        an action's report in the footer."""
        table = getattr(self.ui, "tbl000", None)
        if table is None or not getattr(table, "is_initialized", False):
            return
        if self._details_pending:
            return
        names = [row["name"] for row in self._material_rows()]
        if names != [self._row_name(r) for r in range(table.rowCount())]:
            self._refresh_material_lists()
            return
        self._mark_selection()
        self._fill_details(keep_note=True)

    @staticmethod
    def _rewire(owner, signal_name, handler):
        """Connect *owner*'s *signal_name* to *handler*, dropping the one an
        earlier slots instance connected (stored on *owner* per signal)."""
        signal = getattr(owner, signal_name, None)
        if signal is None:
            return
        wired = owner.__dict__.setdefault("_materials_wired", {})
        prior = wired.get(signal_name)
        if prior is not None:
            try:
                signal.disconnect(prior)
            except (TypeError, RuntimeError):
                pass
        signal.connect(handler)
        wired[signal_name] = handler

    def _material_rows(self):
        """The scene's materials, the list filters applied: ``[{"name", "label"}]``
        (cheap: the table compares it with its rows to tell whether the set
        changed). A material's name is its label in both hosts."""
        names = self.tk.MatUtils.get_scene_mat_names(**self._list_filter_options())
        return [{"name": name, "label": name} for name in names]

    #: A name cell's swatch, in pixels.
    _SWATCH_SIZE = 20

    def _swatch_icon(self, color):
        """The name cell's swatch: *color* (``(r, g, b)`` in 0..1, the host's
        ``MatUtils.get_mat_swatch_color``) filled, or blank for ``None`` so every
        name keeps the same indent."""
        QtGui = self.sb.QtGui
        pixmap = QtGui.QPixmap(self._SWATCH_SIZE, self._SWATCH_SIZE)
        pixmap.fill(
            QtGui.QColor.fromRgbF(*color) if color else QtGui.QColor(255, 255, 255, 0)
        )
        return QtGui.QIcon(pixmap)

    def _fill_materials(self, widget=None, note=None):
        """Refill the table from :meth:`_material_rows`: names and swatches now,
        the details pass (:meth:`_fill_details`) right after. *note* (what an
        action just did) takes the footer in place of that pass's summary."""
        table = widget or self.ui.tbl000
        Qt = self.sb.QtCore.Qt
        rows = self._material_rows()
        blank = [""] * (len(self._MAT_HEADERS) - 1)
        blocked = table.blockSignals(True)
        try:
            table.add(
                [[(row["label"], row["name"]), *blank] for row in rows],
                headers=list(self._MAT_HEADERS),
            )
            header = table.horizontalHeader()
            header.setStretchLastSection(False)
            for col, label in self._ICON_HEADERS.items():
                table.horizontalHeaderItem(col).setToolTip(label)
            QHeaderView = self.sb.QtWidgets.QHeaderView
            header.setSectionResizeMode(self.COL_NAME, QHeaderView.Stretch)
            for col in self._OPTIONAL_COLUMNS:
                header.setSectionResizeMode(col, QHeaderView.ResizeToContents)
            table.restore_column_state()
            editable = Qt.ItemIsSelectable | Qt.ItemIsEnabled | Qt.ItemIsEditable
            fixed = Qt.ItemIsSelectable | Qt.ItemIsEnabled
            for r, row in enumerate(rows):
                name = table.item(r, self.COL_NAME)
                name.setFlags(editable)
                name.setToolTip(row["name"])
                name.setData(self._LABEL_ROLE, row["label"])
                name.setIcon(
                    self._swatch_icon(self.tk.MatUtils.get_mat_swatch_color(row["name"]))
                )
                for col in self._OPTIONAL_COLUMNS:
                    table.item(r, col).setFlags(fixed)
                    table.item(r, col).setTextAlignment(Qt.AlignCenter)
                table.actions.set(r, self.COL_SELECT, "select")
                table.actions.set(r, self.COL_ASSIGN, "assign")
            self._issues = {}
            self._apply_filter()
            current = self._row_of(self._current)
            if current is not None:
                table.selectRow(current)
        finally:
            table.blockSignals(blocked)
        self._mark_selection()
        self._note = note
        self._details_pending = True
        self.sb.QtCore.QTimer.singleShot(0, self._fill_details)

    def _fill_details(self, keep_note=False):
        """The details pass: each row's type, users, textures and status, then
        the footer's summary. Read after the names paint (a scene read per
        material), against the rows the table holds by then.

        Parameters:
            keep_note (bool): Leave an action's report in the footer when it
                still shows one (the activation re-read); otherwise the
                summary replaces it.
        """
        self._details_pending = False
        table = getattr(self.ui, "tbl000", None)
        if table is None:
            return
        names = [self._row_name(r) for r in range(table.rowCount())]
        try:
            details = self._material_details([n for n in names if n])
        except Exception as error:  # noqa: BLE001 -- the list stands without them
            self.ui.footer.setText(f"Could not read the materials: {error}", "error")
            return
        issues = {}
        blocked = table.blockSignals(True)
        try:
            for r, name in enumerate(names):
                info = details.get(name) or {}
                for col, key in (
                    (self.COL_TYPE, "type"),
                    (self.COL_USERS, "users"),
                    (self.COL_TEXTURES, "textures"),
                ):
                    value = info.get(key)
                    table.item(r, col).setText("" if value is None else str(value))
                issue = info.get("issue")
                if not issue:  # fixed meanwhile, or never wrong
                    table.actions.clear(r, self.COL_STATUS)
                    continue
                issues[name] = issue
                table.actions.set(r, self.COL_STATUS, issue[0])
                table.item(r, self.COL_STATUS).setToolTip(
                    f"{issue[1]}: click to {self._FIX_WORDS[issue[0]]}."
                )
        finally:
            table.blockSignals(blocked)
        self._issues = issues
        note, self._note = self._note, None
        footer = self.ui.footer
        if note:
            self._shown_note = note
            footer.setText(note)
        elif not (
            keep_note and self._shown_note and footer.statusText() == self._shown_note
        ):
            self._shown_note = None
            self._show_summary(len(names))

    def _material_details(self, names):
        """``MatUtils.get_mat_facts(names)``, each with the ``issue`` judged
        from its facts (:meth:`_material_issue`)."""
        details = self.tk.MatUtils.get_mat_facts(names)
        for info in details.values():
            info["issue"] = self._material_issue(info)
        return details

    @staticmethod
    def _material_issue(facts):
        """The one issue to show for a material's *facts*, or None: a missing
        texture first, then a duplicate, then nothing using it.

        Returns:
            tuple | None: ``(kind, detail, other)`` -- *other* is the material a
            duplicate duplicates, else None.
        """
        missing = facts.get("missing") or ()
        if missing:
            more = f" (and {len(missing) - 1} more)" if len(missing) > 1 else ""
            return ("missing", f"{missing[0]} is missing{more}", None)
        original = facts.get("duplicate_of")
        if original:
            return ("duplicate", f"A duplicate of {original}", original)
        if facts.get("unused"):
            return ("unused", "Nothing uses it", None)
        return None

    #: What clicking a status icon does, per issue, for its tooltip.
    _FIX_WORDS = {
        "missing": "fix its path in the Texture Path Editor",
        "duplicate": "merge it into the original",
        "unused": "delete it",
    }

    def _show_summary(self, count):
        """The footer: how many materials, and what needs attention."""
        kinds = [issue[0] for issue in self._issues.values()]
        parts = [f"{count} material{'s' if count != 1 else ''}"]
        for kind, word in (
            ("missing", "missing"),
            ("duplicate", "duplicate"),
            ("unused", "unused"),
        ):
            n = kinds.count(kind)
            if n:
                parts.append(f"{n} {word}")
        level = (
            "error" if "missing" in kinds else "warning" if "duplicate" in kinds else None
        )
        self.ui.footer.setText(" · ".join(parts), level)

    def _apply_filter(self, *_):
        """Hide the rows whose name does not hold the filter text."""
        table = self.ui.tbl000
        text = self.ui.txt000.text().strip().lower()
        for r in range(table.rowCount()):
            label = table.item(r, self.COL_NAME).text().lower()
            table.setRowHidden(r, bool(text) and text not in label)

    def _selected_mat_names(self):
        """The materials on the whole selection (the table's bold mark)."""
        return self.tk.MatUtils.get_mat_names(None)

    def _mark_selection(self, *_):
        """Bold the materials the selection uses: a mark, never the highlight."""
        table = getattr(self.ui, "tbl000", None)
        if table is None or not table.rowCount():
            return
        try:
            on = set(self._selected_mat_names())
        except Exception:  # noqa: BLE001 -- a stale selection reads as none
            on = set()
        blocked = table.blockSignals(True)  # a font is no edit
        try:
            for r in range(table.rowCount()):
                item = table.item(r, self.COL_NAME)
                font = item.font()
                if font.bold() != (self._row_name(r) in on):
                    font.setBold(not font.bold())
                    item.setFont(font)
        finally:
            table.blockSignals(blocked)

    def _on_material_highlight(self):
        names = self._highlighted_mats()
        if names:
            self._current = names[0]

    def _on_material_edited(self, item):
        """A name edited in place: rename that material (after the edit
        commits -- the rename refills the table this signal comes from)."""
        if item.column() != self.COL_NAME:
            return
        old = item.data(self.sb.QtCore.Qt.UserRole)
        new = item.text().strip()
        if not old or not new or new == item.data(self._LABEL_ROLE):
            return
        self._current = old
        self.sb.QtCore.QTimer.singleShot(0, lambda: self._rename_current(new))

    def _fit_material_menu(self):
        """Fit the row menu to the highlighted rows just before it opens: Merge
        Duplicates only when one is a duplicate, the rest only with a row."""
        names = self._highlighted_mats()
        QPushButton = self.sb.QtWidgets.QPushButton
        menu = self.ui.tbl000.menu
        for name in ("b028", "b029", "b030", "b031", "lbl004", "lbl006", "lbl002"):
            button = menu.findChild(QPushButton, name)
            if button is not None:
                button.setEnabled(bool(names))
        merge = menu.findChild(QPushButton, "b032")
        if merge is not None:
            merge.setVisible(
                any((self._issues.get(n) or ("",))[0] == "duplicate" for n in names)
            )

    # ------------------------------------------------------------------ row actions
    def _fix_row_issue(self, row, _col=None):
        """A status icon: fix what it flags."""
        name = self._row_name(row)
        issue = self._issues.get(name)
        if not issue:
            return
        kind = issue[0]
        if kind == "missing":
            self._set_current(name)
            self._call_slot(self.b010)
        elif kind == "duplicate":
            self._merge_and_report({name: issue[2]})
        elif kind == "unused":
            self._delete_and_report([name])

    def _select_row_users(self, row, _col=None):
        """The Select icon: select what uses the row's material; Shift adds."""
        QtCore = self.sb.QtCore
        modifiers = self.sb.QtWidgets.QApplication.keyboardModifiers()
        self._set_current(self._row_name(row))
        self.select_by_mat(add=bool(modifiers & QtCore.Qt.ShiftModifier))

    def _random_held(self):
        """Whether Alt is held: it turns an assign into a new random-colored
        material (b004), on + and on every Assign icon alike."""
        modifiers = self.sb.QtWidgets.QApplication.keyboardModifiers()
        return bool(modifiers & self.sb.QtCore.Qt.AltModifier)

    def _assign_row(self, row, _col=None):
        """The Assign icon: the row's material onto the selection; with Alt
        held, a new random-colored material instead (b004)."""
        if self._random_held():
            self._call_slot(self.b004)
        else:
            self._assign_named(self._row_name(row))

    def _merge_and_report(self, pairs):
        """Merge each ``{duplicate: original}`` pair (the host's verified merge,
        one Undo) and say how many went: a merge can refuse a pair the details
        offered (the textures differ on a closer look)."""
        n = self.tk.MatUtils.merge_duplicate_materials(pairs)
        self._refresh_material_lists(
            f"Merged {n} duplicate{'s' if n != 1 else ''} into "
            + ", ".join(sorted(set(pairs.values())))
            + " (Undo restores)."
            if n
            else "Nothing merged: on a closer look the textures differ."
        )

    def _delete_and_report(self, names):
        """Delete the named materials (one Undo) and say how many went."""
        n = len(self.tk.MatUtils.delete_mats(names))
        self._refresh_material_lists(
            f"Deleted {n} material{'s' if n != 1 else ''} (Undo restores)."
        )

    def _assign_named(self, name):
        """Assign *name* to the selection (one Undo), make it current, and say
        so: what every assign (an Assign icon, the row menu, the Assign list)
        comes down to."""
        selection = self.require_selection(
            "<hl>Nothing selected</hl><br>Select object(s) before assigning a material."
        )
        if not selection:
            return
        try:
            with self.tk.CoreUtils.undo_chunk("Assign Material"):
                self.tk.MatUtils.assign_mat(selection, name, create=False)
        except ValueError:  # gone since the list was read
            self._material_gone(name)
            return
        except RuntimeError as error:  # the host refused (a locked node ...)
            self.sb.message_box(f"<hl>Assign failed</hl><br>{name}: {error}")
            return
        self._set_current(name)
        self.sb.message_box(
            f"Assigned <hl>{name}</hl> to <hl>{len(selection)}</hl> object(s)."
        )

    def _rename_current(self, text):
        """Rename the current material to *text* (a name edited in the table).

        Refills the table afterward so each row reflects the actual result:
        the host may adjust the requested name (Maya: invalid characters or a
        clash; Blender: a ``.001`` suffix).

        Returns:
            str | None: The resulting name, or None when nothing was renamed (no
            current material, an empty or unchanged name, or the host refused).
        """
        old = self._current_mat()
        if not (old and text) or text == old:
            return None
        try:
            new = self.tk.MatUtils.rename_mat(old, text)
        except ValueError:  # gone since the list was read
            self._material_gone(old)
            return None
        except RuntimeError as error:
            self.sb.message_box(f"<hl>Rename failed</hl><br>{old}: {error}")
            # The cell already carries the typed name: re-sync it with the
            # scene so a failed rename isn't displayed as done.
            self._refresh_material_lists()
            return None
        self._current = new
        self._refresh_material_lists()
        return new

    # ------------------------------------------------------------------ row-menu slots
    def _first_highlighted(self):
        """The first highlighted material, made current; None (said) when none."""
        names = self._highlighted_mats()
        if not names:
            self.ui.footer.setText("Highlight a material first.", "warning")
            return None
        self._set_current(names[0])
        return names[0]

    def b028(self, widget=None):
        """Assign the highlighted material to the selection."""
        name = self._first_highlighted()
        if name:
            self._assign_named(name)

    def b029(self, widget=None):
        """Select what uses the highlighted material, as assigned."""
        if self._first_highlighted():
            self.select_by_mat()

    def b030(self, widget=None):
        """Select every object using the highlighted material."""
        if self._first_highlighted():
            self.select_by_mat(shell=True)

    def b031(self, widget=None):
        """Narrow the selection to what uses the highlighted material."""
        if self._first_highlighted():
            self.select_by_mat(in_selection=True)

    def b032(self, widget=None):
        """Merge the highlighted duplicates into the materials they duplicate."""
        pairs = {
            name: self._issues[name][2]
            for name in self._highlighted_mats()
            if (self._issues.get(name) or ("",))[0] == "duplicate"
        }
        if pairs:
            self._merge_and_report(pairs)

    def lbl002(self, widget=None):
        """Delete the highlighted materials."""
        names = self._highlighted_mats()
        if names:
            self._delete_and_report(names)

    def lbl004(self, widget=None):
        """Show Attributes: the current material in the host's attribute view
        (Maya: its node in the Attribute Editor; Blender: an object using it,
        active on its slot, for the Material Properties)."""
        name = self._current_mat()
        if not name:
            self.sb.message_box("No current material: highlight one in the list.")
            return
        try:
            shown = self.tk.MatUtils.show_mat_attributes(name)
        except ValueError:
            self._material_gone(name)
            return
        except RuntimeError as error:  # every user out of reach
            self.sb.message_box(str(error))
            return
        if not shown:
            self.sb.message_box(f"No objects use <hl>{name}</hl>: nothing shows it.")

    def lbl006(self, widget=None):
        """Open in Editor: graph the current material in the shader editor."""
        name = self._current_mat()
        if not name:
            self.sb.message_box("No current material: highlight one in the list.")
            return
        self.tk.MatUtils.graph_materials(name)

    # ------------------------------------------------------------------ filter / new
    def txt000_init(self, widget):
        """The filter field: hides the rows whose name does not hold its text.
        Its option box holds the list filters this host serves
        (:attr:`_LIST_FILTERS`); with none, no option box: an empty one would
        be a dead button."""
        self._rewire(widget, "textChanged", self._apply_filter)
        if getattr(widget, "_list_filters_built", False):
            return
        widget._list_filters_built = True
        menu = None
        for name, text, tip, _options, requires in self._LIST_FILTERS:
            chk = self.sb.QtWidgets.QCheckBox(text)
            if not self.requires(chk, requires):  # a filter this host lacks
                chk.deleteLater()
                continue
            if menu is None:
                menu = widget.option_box.menu
                menu.setTitle("Material List Options")
            menu.add(chk, setObjectName=name, setChecked=False, setToolTip=tip)
            self._rewire(chk, "toggled", self._on_list_filter)

    def _on_list_filter(self, *_):
        self._refresh_material_lists()

    def _list_option(self, name):
        """Whether the named list filter is on; False before it is built, and
        on a host that does not serve it (each filter's off state is the
        unfiltered one)."""
        option_box = getattr(getattr(self.ui, "txt000", None), "option_box", None)
        menu = option_box.get_menu(create=False) if option_box else None
        chk = getattr(menu, name, None) if menu else None
        return bool(chk and chk.isChecked())

    def _list_filter_options(self):
        """The ``MatUtils.get_scene_mat_names`` keywords the list filters set."""
        options = {}
        for name, _text, _tip, keywords, _requires in self._LIST_FILTERS:
            if self._list_option(name):
                options.update(keywords)
        return options

    def b006_init(self, widget):
        self.sb.IconManager.set_icon(widget, "add")

    def b006(self, widget=None):
        """New material onto the selection (:meth:`_new_mat`); with Alt held,
        a new random-colored one (b004)."""
        if self._random_held():
            return self._call_slot(self.b004)
        return self._new_mat()

    def _new_mat(self):
        """Assign New Material, the host's way: Maya opens its Assign New
        Material window; Blender makes a ``Material`` and assigns it."""
        try:
            name = self.tk.MatUtils.assign_new_mat(None)
        except ValueError as error:  # nothing that can carry one is selected
            self.sb.message_box(str(error))
            return
        if name:  # None: the host's own window takes it from here
            self._current = name
            self._refresh_material_lists()

    def b004(self, widget=None):
        """Assign Random: a new random-colored material onto the selection; the
        one the last click made goes when nothing uses it any more."""
        try:
            name = self.tk.MatUtils.assign_random_mat(
                None, previous=self.last_random_material
            )
        except ValueError as error:  # nothing selected
            self.sb.message_box(str(error))
            return
        self.last_random_material = name
        self._current = name
        self._refresh_material_lists()

    def b033(self, widget=None):
        """Select the objects carrying no material."""
        return self.select_by_mat(unassigned=True)

    def b014(self, widget=None):
        """Remove Duplicate Materials: merge every duplicate in the scene into
        its original (the verified merge, one Undo), and say how many went --
        counted after the merge, which can refuse a pair the finder offered."""
        pairs = self.tk.MatUtils.find_duplicate_materials()
        if not pairs:
            self.sb.message_box("No duplicate-texture materials found.")
            return
        removed = self.tk.MatUtils.merge_duplicate_materials(pairs)
        self._refresh_material_lists()
        self.sb.message_box(self._duplicates_removed(removed))

    def b015(self, widget=None):
        """Delete All Unused Materials (one Undo; Maya's is its Delete Unused
        Nodes, which takes their unused textures along)."""
        removed = self.tk.MatUtils.delete_unused_materials()
        self._refresh_material_lists()
        n = len(removed)
        self.sb.message_box(
            f"Deleted <hl>{n}</hl> unused material{'s' if n != 1 else ''}."
        )

    def _refresh_material_lists(self, note=None):
        """Refill the material table: call it after anything that creates,
        deletes or renames a material, with *note* saying what that did. (The
        submenu's Assign list rebuilds itself on every show.)"""
        table = getattr(self.ui, "tbl000", None)
        if table is not None and getattr(table, "is_initialized", False):
            self._fill_materials(table, note=note)
        elif note:
            self.ui.footer.setText(note)

    # ------------------------------------------------------------------ header
    def header_init(self, widget):
        """The header: a refresh button, and a menu of the Tools list then
        the scene-wide verbs."""
        widget.config_buttons("refresh", "menu", "collapse", "pin")
        self._rewire(widget, "refresh_requested", self._on_refresh_requested)
        menu = widget.menu
        menu.hide_on_trigger = True
        menu.add(self.sb.registered_widgets.ExpandableList, setObjectName="list001")
        menu.add("Separator", setTitle="Select")
        menu.add(
            "QPushButton",
            setText="Objects Without Material",
            setObjectName="b033",
            setToolTip="Select the objects carrying no material.",
        )
        menu.add("Separator", setTitle="Cleanup")
        menu.add(
            "QPushButton",
            setText="Remove Duplicate Materials",
            setObjectName="b014",
            setToolTip="Merge every duplicate material in the scene into its "
            "original (the same textures and settings), one Undo.",
        )
        menu.add(
            "QPushButton",
            setText="Delete All Unused Materials",
            setObjectName="b015",
            setToolTip="Delete every material nothing uses.",
        )

    def _on_refresh_requested(self, *_):
        self._refresh_material_lists()

    @staticmethod
    def _duplicates_removed(removed: int) -> str:
        """Remove Duplicate Materials' result: how many went. Lightmaps need
        no step: the Lightmap Baker groups a duplicate's atlas with the one it
        duplicates, so the merge leaves every object in the atlas it had."""
        return f"Removed <hl>{removed}</hl> duplicate material{'s' if removed != 1 else ''}."

    # ------------------------------------------------------------------ submenu Assign list
    def _assign_root_text(self, widget):
        """The submenu Assign list's root row: it floats free of the panel, so
        it names what a release assigns, by the material's leaf name."""
        current = self._current_mat()
        return f"Assign: {ptk.HierarchyPath.leaf(str(current))}" if current else "Assign"

    def list000_init(self, widget):
        """Assign list: the current material at the root, then New, Random and
        the scene's materials (built-in defaults left out).

        The submenu's: re-populated on every show so it reflects the scene's
        materials and the current one (the panel's is the material table).
        Releasing on the root assigns the current material
        (:meth:`_assign_root_text` names it).
        """
        if not getattr(widget, "_assign_list_configured", False):
            widget.refresh_on_show = True
            widget.fixed_item_height = 18
            widget.apply_preset("expand_right")
            widget._assign_list_configured = True

        widget.clear()
        root = widget.add(self._assign_root_text(widget))
        root.sublist.add("New")
        root.sublist.add("Random")
        for name in self.tk.MatUtils.get_scene_mat_names(exclude_defaults=True):
            root.sublist.add(name)

    @Slots.Signals("on_item_interacted")
    def list000(self, item):
        """Dispatch an Assign list release.

        - Releasing on the root assigns the current material.
        - 'New' / 'Random' route to b006 / b004 (Alt on 'New' is random too).
        - Any other leaf is a material name, assigned directly.
        """
        text = item.item_text()
        if item.parent_item_text() is None:  # the root
            current = self._current_mat()
            if not current:
                self.sb.message_box(
                    "<hl>No current material</hl><br>"
                    "Pick a material in the main UI first."
                )
                return
            self._assign_named(current)
            return
        if text == "New":
            self.b006(item)
        elif text == "Random":
            self.b004(item)
        else:
            self._assign_named(text)

    # ------------------------------------------------------------------ get + select
    #: Why the selection can't yield one material -> (title, body) for the message box.
    _GET_MAT_FAILURES = {
        "empty": (
            "Nothing selected",
            "Select mesh object(s) or face(s) to get the material from.",
        ),
        "none": (
            "No material found",
            "The selected object has no material assigned.",
        ),
        "multiple": (
            "Multiple materials found",
            "The selected object has multiple materials assigned, so a single "
            "current material can't be determined.",
        ),
    }

    def _selection_mats(self):
        """The first selected object's material names, or None when nothing is
        selected."""
        selection = self.tk.CoreUtils.selected_objects()
        if not selection:
            return None
        return self.tk.MatUtils.get_mat_names(selection[:1])

    def _adopt_selection_mat(self, on_failure=""):
        """Make the selection's one material current (``select_by_mat``'s
        ``get_first``, the submenu's Get + Select).

        The current material is a name, not a list entry, so a material the
        table filters out is adopted all the same.

        Parameters:
            on_failure (str): Text appended to the failure message (what the
                caller does next).

        Returns:
            str | None: The adopted material name, or None (a message was shown).
        """
        mats = self._selection_mats()
        if mats and len(mats) == 1:
            self._set_current(mats[0])
            return mats[0]
        reason = "empty" if mats is None else "none" if not mats else "multiple"
        title, body = self._GET_MAT_FAILURES[reason]
        self.sb.message_box(f"<hl>{title}</hl><br>{body}{on_failure}")
        return None

    def select_by_mat(
        self,
        shell=False,
        in_selection=False,
        get_first=False,
        add=False,
        unassigned=False,
    ):
        """Select the geometry carrying the current material.

        The parameterized primitive behind every select-by-material entry point
        (the table's Select icon and row menu, the header's Objects Without
        Material, the submenu's one-shot ``b003``). Takes plain values so
        callers don't have to reach into -- or temporarily mutate -- another
        widget's state. The search is the host's ``MatUtils.select_by_mat`` /
        ``select_unassigned``.

        Parameters:
            shell (bool): Select whole objects instead of the matching faces
                (Blender: in Edit Mode). Ignored when ``unassigned``.
            in_selection (bool): Search within the current selection only
                (the whole scene when nothing is selected).
            get_first (bool): Adopt the selection's material as the current
                material before searching. Ignored when ``unassigned``.
            add (bool): Add the matches to the selection instead of replacing it.
            unassigned (bool): Select the objects carrying NO material instead.
                "No material" is not a material, so it never becomes current.

        Returns:
            list: What was selected (empty when nothing matched or no current
            material was resolved).
        """
        if get_first and not unassigned:  # adopt the selection's material first
            self._adopt_selection_mat(" Proceeding with current material.")
        pool = (self.tk.CoreUtils.selected_objects() or None) if in_selection else None
        name = None
        try:
            if unassigned:
                matches = self.tk.MatUtils.select_unassigned(pool, add=add)
                # Scope-neutral wording: "everything is assigned" would be a lie
                # under Selection Only, which only looked at part of the scene.
                empty = "<hl>No matches</hl><br>No objects without a material were found."
            else:
                name = self._current_mat()
                if not name:
                    if not get_first:  # the adopt path has said why already
                        self.sb.message_box(
                            "No current material: highlight one in the list."
                        )
                    return []
                matches = self.tk.MatUtils.select_by_mat(
                    name, pool, shell=shell, add=add
                )
                empty = (
                    "<hl>No matches</hl><br>No objects found with material "
                    f"'<strong>{name}</strong>'."
                )
        except ValueError:  # the current material is gone
            self._material_gone(name)
            return []
        except RuntimeError as error:  # users found, none of them selectable
            self.sb.message_box(str(error))
            return []
        if not matches:
            self.sb.message_box(empty)
            return []
        return list(matches)

    def b003(self, widget=None):
        """Get + Select (submenu): adopt the selection's material, then select its users.

        A fixed one-shot -- whole objects, whole scene, replacing the selection --
        so the submenu button does the same thing every time.

        A selection with NO material takes the analogous branch rather than
        failing: "everything that matches this selection, material-wise" becomes
        every object that also has no material. Only a genuinely materialless
        selection routes there -- an empty or multi-material selection still
        reports through the normal adopt path.

        Returns:
            list: whatever :meth:`select_by_mat` selected.
        """
        if self._selection_mats() == []:  # selected, but nothing assigned
            self.sb.message_box(
                "<hl>No material on the selection</hl><br>"
                "Selecting the objects that have no material assigned."
            )
            return self.select_by_mat(shell=True, unassigned=True)
        return self.select_by_mat(shell=True, get_first=True)

    # ------------------------------------------------------------------ Tools list
    def list001_init(self, widget):
        """Tools list: Setup / Materials / Texture Maps / External / Utilities.

        In the header menu the categories ARE the roots, each flying out on
        hover (``hover_menu``): a "Tools" row above them would be one more
        hover for nothing, the menu already being the panel's tools. The
        submenu keeps a "Tools" root (``expand_up``: the categories overlay
        its lower-left corner, items fan right).

        Rows are plain labels dispatched by ``list001``, EXCEPT entries whose
        slot defines an ``*_init``: that init builds the option box (tb001's
        report scope/filters, tb002's scope + transparency mode), which is
        lost on a plain label, so those are added as real slot-wired widgets.
        A row one host serves is hidden on the other (its ``requires``).
        """
        widget.fixed_item_height = 18
        submenu = widget.ui.has_tags("submenu")
        widget.apply_preset("expand_up" if submenu else "hover_menu")
        widget.clear()
        root = widget.add("Tools").sublist if submenu else widget

        for category, items in self._TOOLS_ITEMS.items():
            cat = root.add(category)
            for label, slot_name, *rest in items:
                tooltip = rest[0] if rest else ""
                requires = rest[1] if len(rest) > 1 else None
                if slot_name and hasattr(self, f"{slot_name}_init"):
                    item = self.add_slot_widget(
                        cat.sublist,
                        setObjectName=slot_name,
                        setText=label,
                        setToolTip=tooltip,
                    )
                else:
                    item = cat.sublist.add(label, setToolTip=tooltip)
                self.requires(item, requires)
                gate = self._EXTERNAL_APP_GATES.get(slot_name)
                if gate is not None:
                    self.gate_on_app(item, lambda gate=gate: gate(self.tk))

    @Slots.Signals("on_item_interacted")
    def list001(self, item):
        """Dispatch a Tools-list selection to its slot method."""
        self._dispatch_tools_row(item)

    # ------------------------------------------------------------------ Utilities
    def b007(self, widget=None):
        """Shader Editor: the host's (Maya: the Hypershade; Blender: the Shader
        Editor, in a new window)."""
        if self.tk.UiUtils.open_editor("Hypershade") is None:
            self.sb.message_box("Could not open the shader editor.")

    def b013(self, widget=None):
        """Reload Scene Textures, then reset the viewport."""
        self.tk.MatUtils.reload_textures(reset_viewport=True)
        self.sb.message_box("<hl>Textures reloaded</hl> and the viewport reset.")

    _TB001_SCOPES = (
        ("Textures", "textures"),
        ("Current Material", "current"),
        ("All Materials", "all"),
        ("Selected Objects", "selected"),
    )

    def tb001_init(self, widget):
        """Get Material Info: its option box."""
        menu = widget.option_box.menu
        menu.setTitle("Get Material Info")
        cmb = menu.add(
            "QComboBox",
            setObjectName="cmb_scope",
            setToolTip=(
                "Textures: every scene texture file.\n"
                "Current Material: the material last highlighted in the list.\n"
                "All Materials: every scene material.\n"
                "Selected Objects: materials assigned to the current "
                "viewport selection."
            ),
        )
        for label, data in self._TB001_SCOPES:
            cmb.addItem(label, data)
        # Scope filters: they apply to the scopes that gather more than one material.
        defaults = menu.add(
            "QCheckBox",
            setText="Exclude Default Materials",
            setObjectName="chk_exclude_defaults",
            setChecked=True,
            setToolTip=(
                "Drop Maya's built-in defaults (lambert1, standardSurface1, …) "
                "from the report. Has no effect on the Current Material scope."
            ),
        )
        self.requires(defaults, "maya")  # Blender has no built-in defaults
        menu.add(
            "QCheckBox",
            setText="Exclude Unassigned Materials",
            setObjectName="chk_exclude_unassigned",
            setChecked=False,
            setToolTip=(
                "Drop the materials no geometry uses. Most useful on the All "
                "Materials scope: the selection-derived and Current scopes are "
                "already assigned."
            ),
        )
        # Field toggles: how much each material record carries.
        menu.add(
            "QCheckBox",
            setText="Include Textures",
            setObjectName="chk_include_textures",
            setChecked=True,
            setToolTip=(
                "Include the per-texture list. Uncheck for a lightweight "
                "name + type report."
            ),
        )
        menu.add(
            "QCheckBox",
            setText="Include Image Metadata",
            setObjectName="chk_include_metadata",
            setChecked=True,
            setToolTip="Include resolution, mode, format, and bit depth per texture.",
        )
        menu.add(
            "QCheckBox",
            setText="Include Optimization Analysis",
            setObjectName="chk_include_optimization",
            setChecked=True,
            setToolTip=(
                "Run the texture optimizer per texture and report whether "
                "a resize, mode change, or bit-depth change is recommended "
                "(Blender installs Pillow for it on first use)."
            ),
        )

    def tb001(self, widget):
        """Get Material Info: render a formatted report to the viewer dialog.

        Validates scope inputs *before* opening the footer progress so a quick
        bail-out (no current material, empty selection, ...) doesn't trigger the
        misleading "Complete" flash the progress context emits on exit.
        """
        menu = widget.option_box.menu
        cmb = menu.cmb_scope
        scope = cmb.currentData() or "current"
        scope_label = cmb.currentText() or scope
        filters = {
            "exclude_defaults": menu.chk_exclude_defaults.isChecked(),
            "exclude_unassigned": menu.chk_exclude_unassigned.isChecked(),
        }

        scoped, title = {}, ""
        if scope == "current":
            mat = self._current_mat()
            if not mat:
                self.sb.message_box(
                    "<hl>No current material</hl><br>Pick a material first."
                )
                return
            # One material, picked: the scope-wide filters would only drop it.
            scoped, filters = {"materials": [mat]}, {}
            title = f"Material Info — {mat}"
        elif scope == "selected":
            selection = self.tk.CoreUtils.selected_objects()
            if not selection:
                self.sb.message_box(
                    "<hl>Nothing selected</hl><br>"
                    "Select object(s) to report their assigned materials."
                )
                return
            scoped = {"objects": selection}
            title = f"Material Info — {len(selection)} selected object(s)"

        mat_utils = self.tk.MatUtils
        with self.sb.progress(text=f"Working: Get Material Info ({scope_label})") as update:
            if scope == "textures":
                info = mat_utils.get_texture_info(**filters)
                html = mat_utils.format_texture_info_html(info) if info else None
                title = f"Texture Info — {len(info)} texture(s)"
            else:
                records = mat_utils.get_mat_info(
                    optimize_check=menu.chk_include_optimization.isChecked(),
                    allow_palette=True,
                    progress_callback=self.sb.progress_adapter(update),
                    include_textures=menu.chk_include_textures.isChecked(),
                    include_image_metadata=menu.chk_include_metadata.isChecked(),
                    **filters,
                    **scoped,
                )
                if scope == "all":
                    title = f"Material Info — all ({len(records)} material(s))"
                html = mat_utils.format_mat_info_html(records) if records else None

        if html is None:
            if scope == "textures":
                self.sb.message_box("<hl>No textures</hl> found in scene.")
            else:
                self.sb.message_box(f"<hl>No materials</hl> for scope: {scope_label}.")
            return
        # Non-modal: the host stays responsive while the user reads the report.
        self.sb.text_view_dialog(html, "Ok", title=title, size=(760, 520), monospace=False)

    # Scope choices for tb002: label, value passed to get_mats_by_scope.
    _TB002_SCOPES = (
        ("Selected Objects", "selected"),
        ("Visible Objects", "visible"),
        ("All Scene Materials", "scene"),
    )

    def tb002_init(self, widget):
        """Enable Viewport Opacity (Maya: its Tools row is ``requires="maya"``):
        the option box."""
        menu = widget.option_box.menu
        menu.setTitle("Enable Viewport Opacity")
        # NOT "cmb_scope": tb001's option box already owns that name, and a widget
        # objectName is the StateManager key (plus the cross-surface sync key) -- the
        # two scope combos would overwrite each other's persisted choice.
        cmb = menu.add(
            "QComboBox",
            setObjectName="cmb_opacity_scope",
            setToolTip=(
                "Selected Objects: materials on the current selection.\n"
                "Visible Objects: materials on visible geometry.\n"
                "All Scene Materials: every material, assigned or not."
            ),
        )
        for label, data in self._TB002_SCOPES:
            cmb.addItem(label, data)
        menu.add(
            "QCheckBox",
            setText="Depth Peeling",
            setObjectName="chk_depth_peeling",
            setChecked=False,
            setToolTip=(
                "Switch Viewport 2.0 to depth-peeled transparency so "
                "overlapping transparent faces (decals, foliage) sort "
                "correctly. Costs viewport performance; off leaves the "
                "current transparency mode alone."
            ),
        )

    def tb002(self, widget):
        """Enable Viewport Opacity: wire opacity maps for the chosen scope."""
        menu = widget.option_box.menu
        scope = menu.cmb_opacity_scope.currentData() or "selected"
        scope_label = menu.cmb_opacity_scope.currentText() or scope

        materials = self.tk.MatUtils.get_mats_by_scope(scope)
        if not materials:
            self.sb.message_box(
                f"<hl>No materials</hl><br>Nothing found for scope: {scope_label}."
            )
            return

        results = self.tk.MatUtils.enable_viewport_opacity(
            materials,
            transparency_algorithm=(
                "depth_peeling" if menu.chk_depth_peeling.isChecked() else None
            ),
        )

        enabled = [m for m, s in results.items() if s == "enabled"]
        already = [m for m, s in results.items() if s == "already enabled"]
        skipped = [m for m, s in results.items() if s == "no opacity map"]
        failed = {m: s for m, s in results.items() if s.startswith("unsupported")}

        lines = [
            f"<hl>Viewport opacity</hl> — {scope_label}<br>",
            f"Enabled: <strong>{len(enabled)}</strong><br>",
            f"Already enabled: <strong>{len(already)}</strong><br>",
            f"No opacity map: <strong>{len(skipped)}</strong>",
        ]
        if failed:
            lines.append(
                "<br>Unsupported: <strong>"
                + ", ".join(f"{m} ({s})" for m, s in failed.items())
                + "</strong>"
            )
        self.sb.message_box("".join(lines))

    # ------------------------------------------------------------------ tool panels
    def b009(self, widget=None):
        """Game Shader."""
        self.sb.handlers.marking_menu.show("game_shader")

    def b010(self, widget=None):
        """Texture Path Editor."""
        self.sb.handlers.marking_menu.show("texture_path_editor")

    def b011(self, widget=None):
        """Shader Templates."""
        self.sb.handlers.marking_menu.show("shader_templates")

    def b018(self, widget=None):
        """Mat Updater: reprocess scene materials' textures and re-wire them."""
        self.sb.handlers.marking_menu.show("mat_updater")

    def b019(self, widget=None):
        """Marmoset Bridge."""
        self.sb.handlers.marking_menu.show("marmoset_bridge")

    def b020(self, widget=None):
        """Substance Bridge."""
        self.sb.handlers.marking_menu.show("substance_bridge")

    def b021(self, widget=None):
        """Image to Plane."""
        self.sb.handlers.marking_menu.show("image_to_plane")

    def b026(self, widget=None):
        """Arnold Preview Shader (Maya: a parallel aiStandardSurface for in-Maya
        Arnold preview; its Tools row is ``requires="maya"``)."""
        self.sb.handlers.marking_menu.show("arnold_bridge")

    def b027(self, widget=None):
        """Emissive Groups."""
        self.sb.handlers.marking_menu.show("emissive_groups")

    # ------------------------------------------------------------------ standalone panels
    def _launch_extapp(self, app, show=True):
        """Launch the standalone panel *app* (``tcl_standalone.py``) in-process
        through the external-app handler; a failure (a package that will not
        install or import) is a message, never a traceback.

        Returns:
            The panel's window, or None.
        """
        try:
            return self.sb.handlers.external_app.launch(app, show=show)
        except Exception as error:  # noqa: BLE001 -- said, for the user to act on
            self.sb.message_box(
                f"<hl>Couldn't open {app.replace('_', ' ').title()}</hl><br>{error}"
            )
            return None

    def _open_texture_app(self, app, scopes=False):
        """Open a texture-file panel (Map Packer, Map Converter) on the project's
        texture folder, with the host's selection scopes when *scopes*."""
        ui = self._launch_extapp(app, show=False)
        if ui is None:
            return
        slots = getattr(ui, "slots", None)
        if slots is not None:
            folder = self.tk.EnvUtils.source_images_dir()
            if folder:
                slots.source_dir = folder
            if scopes:
                self._register_texture_scopes(slots)
        self.sb.handlers.marking_menu.show(ui)

    def _register_texture_scopes(self, slots):
        """Offer the host's texture scopes in the panel's Scope picker: the
        panel owns the picker, the host what each scope means
        (``MatUtils.get_texture_scopes``), and a material picker over the
        scene. Providers run at tool time, so they read the CURRENT selection."""
        for label, provider in self.tk.MatUtils.get_texture_scopes().items():
            slots.register_scope(label, provider)
        slots.register_scope("Choose Materials...", self._chosen_material_textures)

    def _chosen_material_textures(self):
        """The texture files of the materials picked in a dialog; [] on cancel."""
        names = self._choose_scene_materials()
        if not names:
            return []
        return self.tk.MatUtils.get_texture_paths(materials=names, exclude_bundled=True)

    def _choose_scene_materials(self):
        """Multi-select picker over the scene's materials. Returns [] on cancel."""
        materials = self.tk.MatUtils.get_scene_mat_names(exclude_defaults=True)
        if not materials:
            self.sb.message_box("<hl>No materials</hl><br>The scene has none.")
            return []
        return self.sb.list_input_dialog(
            materials,
            title="Choose Materials",
            label="Select the material(s) to pull textures from:",
            parent=self.sb.parent(),
        )

    def b008(self, widget=None):
        """Map Packer."""
        self._open_texture_app("packer")

    def b016(self, widget=None):
        """Map Converter."""
        self._open_texture_app("converter", scopes=True)

    def b022(self, widget=None):
        """Map Compositor."""
        self._launch_extapp("compositor")

    def b023(self, widget=None):
        """Metashape Workflow."""
        self._launch_extapp("metashape_workflow")

    def b024(self, widget=None):
        """RealityCapture Workflow."""
        self._launch_extapp("realityscan_workflow")

    def b025(self, widget=None):
        """Brush Splat Workflow."""
        self._launch_extapp("gaussian_splat_workflow")


# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
