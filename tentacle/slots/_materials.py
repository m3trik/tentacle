# !/usr/bin/python
# coding=utf-8
"""Shared, DCC-agnostic behavior for the ``materials`` panel.

The per-panel home for logic the Maya and Blender ``MaterialsSlots`` forks share (mixed in
ahead of their ``SlotsMaya`` / ``SlotsBlender`` base). Grow this class rather than adding a
new module per feature — see the convention in ``tentacle/CLAUDE.md``.

**The panel is a material table** (``tbl000``), filtered by ``txt000`` with ``b006`` (+, a
new material on the selection) beside it. One row per scene material: its swatch and name,
optional Type / Users / Textures columns (header right-click), then three icon columns —

- **Status**, empty unless something needs attention: a missing texture, a duplicate of
  another material, or a material nothing uses. Clicking it fixes that (open the Texture
  Path Editor, merge into the original, delete), one Undo.
- **Select** the objects using the material (Shift adds to the selection).
- **Assign** it to the selection.

So every common action is one click, several materials can be acted on at once (the row
context menu), and what needs cleaning up is visible without asking. Renaming is a
double-click on the name. Names and swatches paint first; the details pass (type, users,
textures, status) runs right after, so the panel opens without waiting on it. Which
materials the selection uses is marked (bold) when the panel shows or its window is
activated (``MainWindow.on_activated``: a click anywhere in it) — a mark, never a change
to the highlight, so it can't fight the user mid-assign.

**The current material** is the last one highlighted, assigned or adopted
(:meth:`_current_mat`): what ``select_by_mat``, rename, Select Node, Open in Editor and the
submenu's Assign row act on. A name, never a widget, so it exists before the table does.

The header menu holds the Tools list (``list001``, its categories as roots — a header menu
needs no "Tools" row above them) and the scene-wide verbs: Objects Without Material, Remove
Duplicate Materials, Delete All Unused Materials. A new random-colored material is an
Alt-click on + (``b006``) or on any Assign icon. The submenu keeps its own
compact surface: the Assign list (``list000``), Get + Select (``b003``) and Tools.

Hooks each ``<Panel>Slots`` fork supplies:

- ``_material_rows()`` -> ``[{"name", "label"}]``, the list filters applied (cheap: the
  table compares it with its rows to tell whether the set changed);
  ``_material_icon(name)`` -> its swatch, or None.
- ``_material_facts(names)`` -> ``{name: {"type", "users", "textures", "missing",
  "duplicate_of", "unused"}}``: raw facts -- the missing texture files' names, the
  material it duplicates (or None), and whether nothing uses it (what counts as a use,
  and what is kept on purpose, is the DCC's call). The mixin judges the one issue to show
  (:meth:`_material_issue`) and words it, the same in both DCCs.
- ``_duplicate_pairs(names=None)`` -> ``{duplicate: original}``, verified, over *names*
  (None: every material in the scene).
- ``_selected_mat_names()`` -> the names of the materials on the selection.
- ``_selection_mats()`` -> the first selected object's material names, or ``None`` when
  nothing is selected.
- ``_new_mat()``: + (``b006``) without Alt, a new material onto the selection.
- ``_assign_named(name)``, ``_delete_materials(names)``, ``_merge_duplicates(pairs)``,
  ``_rename_current(text)``, ``select_by_mat(...)``, and the ``b010`` Texture Path Editor.
- ``_script_job_manager()`` -> the engine's ``ScriptJobManager`` class (Maya-named
  events in both DCCs).

**Keeping up with the scene:** the table refills on show, after its own actions, on a
scene opened or new and on Undo / Redo while it shows (a burst of them -- a held Ctrl+Z
-- refills once, when it settles); the selection's bold mark follows SelectionChanged.
What another tool does meanwhile (a material made in the Hypershade, a reassignment from
the viewport) is caught when the window is activated: a changed material set refills,
otherwise the details and the mark re-read in place, the rows unmoved (the click that
activated the window lands on the row it aimed at). A uitk menu hands activation back as
it closes, so an activation right after a refill (its details pass still queued) reads
nothing, and the re-read keeps an action's report in the footer. The header's refresh
button refills on demand.
"""
import pythontk as ptk


class MaterialsMixin:
    """DCC-agnostic ``materials`` slot behavior: the material table, the current
    material, the header menu, and the submenu's Get + Select."""

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
                    "Select Node",
                    "lbl004",
                    "Select the material itself and show its attributes.",
                ),
                ("Open in Editor", "lbl006", "Graph the material in the node editor."),
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

    #: Scene events after which the table refills (when it shows).
    _REFILL_EVENTS = ("SceneOpened", "NewSceneOpened", "Undo", "Redo")

    def _follow_scene(self, table):
        """Subscribe the table to the scene's events, owned by the table:
        the subscriptions go with it, and a reloaded slots instance replaces
        the last one's."""
        mgr = self._script_job_manager().instance()
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

    def _fill_materials(self, widget=None, note=None):
        """Refill the table from ``_material_rows()``: names and swatches now,
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
                icon = self._material_icon(row["name"])
                if icon is not None:
                    name.setIcon(icon)
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
        """``_material_facts(names)``, each with the ``issue`` judged from its
        facts (:meth:`_material_issue`)."""
        details = self._material_facts(names)
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
        commits — the rename refills the table this signal comes from)."""
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
        n = self._merge_duplicates(pairs)
        self._refresh_material_lists(
            f"Merged {n} duplicate{'s' if n != 1 else ''} into "
            + ", ".join(sorted(set(pairs.values())))
            + " (Undo restores)."
            if n
            else "Nothing merged: on a closer look the textures differ."
        )

    def _delete_and_report(self, names):
        self._delete_materials(names)
        n = len(names)
        self._refresh_material_lists(
            f"Deleted {n} material{'s' if n != 1 else ''} (Undo restores)."
        )

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

    # ------------------------------------------------------------------ filter / new
    def txt000_init(self, widget):
        """The filter field: hides the rows whose name does not hold its text.
        Its option box holds the DCC's list filters (:meth:`_list_filters`),
        when it has any: an empty option box would be a dead button."""
        self._rewire(widget, "textChanged", self._apply_filter)
        filters = self._list_filters()
        if not filters or getattr(widget, "_list_filters_built", False):
            return
        widget._list_filters_built = True
        menu = widget.option_box.menu
        menu.setTitle("Material List Options")
        for name, text, tip in filters:
            chk = menu.add(
                "QCheckBox", setText=text, setObjectName=name, setChecked=False,
                setToolTip=tip,
            )
            self._rewire(chk, "toggled", self._on_list_filter)

    def _list_filters(self):
        """DCC hook: ``[(objectName, label, tooltip)]`` of checkboxes that
        narrow the list (read back by :meth:`_list_option`). None by default."""
        return ()

    def _on_list_filter(self, *_):
        self._refresh_material_lists()

    def _list_option(self, name):
        """Whether the named list filter is on; False before it is built (each
        filter's off state is the unfiltered one)."""
        option_box = getattr(getattr(self.ui, "txt000", None), "option_box", None)
        menu = option_box.get_menu(create=False) if option_box else None
        chk = getattr(menu, name, None) if menu else None
        return bool(chk and chk.isChecked())

    def b006_init(self, widget):
        self.sb.IconManager.set_icon(widget, "add")

    def b006(self, widget=None):
        """New material onto the selection (:meth:`_new_mat`); with Alt held,
        a new random-colored one (b004)."""
        if self._random_held():
            return self._call_slot(self.b004)
        return self._new_mat()

    def b033(self, widget=None):
        """Select the objects carrying no material."""
        return self.select_by_mat(unassigned=True)

    def b014(self, widget=None):
        """Remove Duplicate Materials: merge every duplicate in the scene into
        its original (the verified merge, one Undo), and say how many went --
        counted after the merge, which can refuse a pair the finder offered."""
        pairs = self._duplicate_pairs()
        if not pairs:
            self.sb.message_box("No duplicate-texture materials found.")
            return
        removed = self._merge_duplicates(pairs)
        self._refresh_material_lists()
        self.sb.message_box(self._duplicates_removed(removed))

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

    # ------------------------------------------------------------------ submenu Assign list
    def _assign_root_text(self, widget):
        """The submenu Assign list's root row: it floats free of the panel, so
        it names what a release assigns, by the material's leaf name."""
        current = self._current_mat()
        return f"Assign: {ptk.HierarchyPath.leaf(str(current))}" if current else "Assign"

    @staticmethod
    def _duplicates_removed(removed: int) -> str:
        """Remove Duplicate Materials' result: how many went. Lightmaps need
        no step: the Lightmap Baker groups a duplicate's atlas with the one it
        duplicates, so the merge leaves every object in the atlas it had."""
        return f"Removed <hl>{removed}</hl> duplicate material{'s' if removed != 1 else ''}."

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

    def b003(self, widget=None):
        """Get + Select (submenu): adopt the selection's material, then select its users.

        A fixed one-shot — whole objects, whole scene, replacing the selection —
        so the submenu button does the same thing every time.

        A selection with NO material takes the analogous branch rather than
        failing: "everything that matches this selection, material-wise" becomes
        every object that also has no material. Only a genuinely materialless
        selection routes there — an empty or multi-material selection still
        reports through the normal adopt path.

        Returns:
            list: whatever ``select_by_mat`` selected (see the DCC slot's hook).
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
                if slot_name and hasattr(self, f"{slot_name}_init"):
                    item = self.add_slot_widget(
                        cat.sublist,
                        setObjectName=slot_name,
                        setText=label,
                        setToolTip=tooltip,
                    )
                else:
                    item = cat.sublist.add(label, setToolTip=tooltip)
                resolve_spec = self._EXTERNAL_APP_GATES.get(slot_name)
                if resolve_spec is not None:
                    self.gate_on_app(item, resolve_spec)
