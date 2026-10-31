# !/usr/bin/python
# coding=utf-8
"""The Reference Manager panel's controller: the browsed workspace, the table
of its scene files, and every action the panel runs on them.

One copy for both hosts: every host call goes through :attr:`engine`, the host
library's ``ReferenceManager`` (``Slots.tk``), built here with this panel's
progress, bake and report collaborators. The table's SELECTION is the scene's
reference set: selecting a row references its file, deselecting it removes the
reference; foreign and current-scene rows are non-selectable and toggle by their
link icon. The row context menu acts on the right-clicked row, never on the
selection.
"""

import contextlib
import html
import os
from typing import List

import pythontk as ptk

from .references import ReferenceActions
from .scene_files import SceneFiles
from .workspaces import WorkspaceBrowser


class ReferenceManagerController(ptk.LoggingMixin):
    """State and behavior behind ``reference_manager.ui`` (see the module docstring)."""

    # Table columns: FILES | reference toggle | open | display mode | NOTES.
    COL_NAME, COL_REF, COL_OPEN, COL_DISPLAY, COL_NOTES = range(5)
    #: On-screen order (logical indices): FILES, NOTES, Display, Reference, Open.
    VISUAL_COLUMN_ORDER = (COL_NAME, COL_NOTES, COL_DISPLAY, COL_REF, COL_OPEN)
    #: Row data roles on the name cell: the path, the full file name (what an inline
    #: rename edits) and the label shown.
    ROLE_PATH, ROLE_FILE_NAME, ROLE_LABEL = 0, 1, 2
    #: Marks a name cell styled as the current scene, so a reused item resets.
    ROLE_CURRENT = 10

    #: The Include Types row, in column order (one checkbox per type; both hosts).
    INCLUDE_TYPES = ("ma", "mb", "fbx", "usd", "blend")
    #: An include type that lists more than its own spelling.
    _INCLUDE_TYPE_EXTENSIONS = {"usd": ptk.USD_EXTENSIONS}
    _INCLUDE_TYPE_NAMES = {
        "ma": "Maya ASCII scenes (.ma)",
        "mb": "Maya binary scenes (.mb)",
        "fbx": "FBX files (.fbx)",
        "usd": "USD layers and packages (.usd / .usda / .usdc / .usdz)",
        "blend": "Blender scenes (.blend)",
    }
    #: The Naming case styles: exactly the tokens ``ptk.StrUtils.set_case`` honors
    #: (the combo saves its index, so the order is append-only).
    CASE_STYLES = ("None", "camel", "pascal", "title", "upper", "lower", "capitalize")

    def __init__(self, slots, log_level="WARNING"):
        super().__init__()
        self.set_log_level(log_level)
        self.slots = slots
        self.sb = slots.sb
        self.ui = slots.ui
        #: The collaborators: the Root Directory / Workspaces fields, the scene-file
        #: actions, and the reference actions.
        self.workspaces = WorkspaceBrowser(self)
        self.files = SceneFiles(self)
        self.references = ReferenceActions(self)
        #: The host's engine, asking through this panel: its long reads run in the
        #: footer progress, a bake it needs runs through the panel's bake (the
        #: route and rig questions, the progress, its errors shown), and an outcome
        #: the user must see lands in a message box.
        self.engine = slots.tk.ReferenceManager(
            progress=self.files.conversion_progress,
            bake_for_reference=self.files.bake_foreign_path,
            report=self.report,
        )
        self.filter_enabled = True
        self.filter_text = ""
        self.context_menu_row = None  # the right-clicked row the menu acts on
        self.editing_item = None  # the name cell an inline rename is editing
        self._prefiltered = 0  # files the suffix / structure filters left out
        self._active_filter = ("", True, True, True)
        self._scene_notes = None

    @property
    def tk(self):
        """The host toolkit (``Slots.tk``)."""
        return self.slots.tk

    # ------------------------------------------------------------------ small helpers
    @staticmethod
    def norm(path) -> str:
        """The panel's comparison key for a path: normalized, case-folded only where
        the file system folds case."""
        return os.path.normcase(os.path.normpath(path)) if path else ""

    def role(self, offset: int):
        """``Qt.UserRole + offset`` (the row data roles above)."""
        return self.sb.QtCore.Qt.UserRole + offset

    @contextlib.contextmanager
    def table_signals_blocked(self):
        """Run a table rebuild without its signals: a programmatic change must not
        read as the user's selection -> reference edit."""
        table = self.ui.tbl000
        blocked = table.blockSignals(True)
        try:
            yield table
        finally:
            table.blockSignals(blocked)

    def message(self, text, *buttons):
        """The panel's message box (``sb.message_box``)."""
        return self.sb.message_box(text, *buttons)

    def report(self, message: str) -> None:
        """The engine's ``report``: its plain-text outcome, in a message box."""
        self.message(html.escape(str(message), quote=False).replace("\n", "<br>"))

    def error_box(self, lead: str, name: str, error) -> None:
        """Report *error* for the scene file *name*. Escaped: an error's own text is
        not markup -- pxr quotes prim paths as ``</>`` -- and unescaped, the part that
        named the problem vanished."""
        self.message(
            f"{lead} <hl>{html.escape(name, quote=False)}</hl>:<br>{html.escape(str(error), quote=False)}"
        )

    def footer_status(self, text, level="warning"):
        """Leave *text* in the footer's status label (no-op without a footer)."""
        footer = getattr(self.ui, "footer", None)
        if footer is not None:
            footer.setText(text, level=level)

    # ------------------------------------------------------------------ header menu reads
    def header_menu(self):
        """The header menu -- home of the naming, filter and include options. None
        until the header is built (a sibling ``*_init`` may run first)."""
        header = getattr(self.ui, "header", None)
        return getattr(header, "menu", None) if header is not None else None

    def _checked(self, name, default=False, menu=None):
        menu = menu if menu is not None else self.header_menu()
        widget = getattr(menu, name, None) if menu is not None else None
        return widget.isChecked() if widget is not None else default

    def naming_options(self):
        """``(case_style, suffix, structure_pattern)`` from the header menu's Naming
        section -- the one read Save, Rename, Delete, the filters and both previews go
        through; defaults until the menu is built. Text fields come back trimmed."""
        menu = self.header_menu()
        case_w = getattr(menu, "cmb_case_style", None) if menu is not None else None
        suffix_w = getattr(menu, "txt_suffix", None) if menu is not None else None
        txt = (
            getattr(menu, "txt_subfolder_structure", None) if menu is not None else None
        )
        return (
            case_w.currentText() if case_w is not None else "None",
            suffix_w.text().strip() if suffix_w is not None else "",
            txt.text().strip() if txt is not None else "",
        )

    @classmethod
    def type_extensions(cls, include_type):
        """Every extension the Include Types toggle *include_type* lists (``usd`` ->
        the four USD spellings; any other -> ``.<type>``)."""
        return tuple(
            cls._INCLUDE_TYPE_EXTENSIONS.get(include_type, (f".{include_type}",))
        )

    def include_type_checked_by_default(self, include_type) -> bool:
        """True for the host's own scene types (the engine's ``INCLUDE_DEFAULTS``)."""
        return bool(
            set(self.type_extensions(include_type)) & set(self.engine.INCLUDE_DEFAULTS)
        )

    def include_type_tooltip(self, include_type) -> str:
        """What the Include Types toggle lists, and how a row of it references."""
        exts = self.type_extensions(include_type)
        how = (
            "referenced natively"
            if set(exts) & set(self.engine.NATIVE_EXTENSIONS)
            else "baked to a cached scene, then referenced"
        )
        return f"List the workspace's {self._INCLUDE_TYPE_NAMES[include_type]} — {how}."

    def included_extensions(self):
        """The extensions whose Include Types checkbox is checked; the engine's
        defaults until the header menu is built."""
        menu = self.header_menu()
        if menu is None:
            return set(self.engine.INCLUDE_DEFAULTS)
        included = set()
        for t in self.INCLUDE_TYPES:
            chk = getattr(menu, f"chk_include_{t}", None)
            if chk is not None and chk.isChecked():
                included.update(self.type_extensions(t))
        return included

    def is_importable(self, path) -> bool:
        """True if Unlink and Import can bring *path*'s row in with no reference
        behind it (the engine's ``IMPORT_EXTENSIONS``)."""
        return (
            bool(path)
            and os.path.splitext(path)[1].lower() in self.engine.IMPORT_EXTENSIONS
        )

    def foreign_route(self):
        """The conversion route from the header menu: ``"fbx"`` (default) / ``"usd"``.
        USD only when explicitly selected, so an unbuilt menu falls back to the route
        the engine defaults to."""
        menu = self.header_menu()
        combo = (
            getattr(menu, "cmb_conversion_route", None) if menu is not None else None
        )
        if combo is not None and "USD" in combo.currentText():
            return "usd"
        return "fbx"

    def filter_menu(self):
        """The Filter field's option menu (ignore case, target); None until built."""
        field = getattr(self.ui, "txt001", None)
        box = getattr(field, "option_box", None) if field is not None else None
        return getattr(box, "menu", None) if box is not None else None

    # ------------------------------------------------------------------ notes
    @property
    def scene_notes(self) -> "ptk.SceneNotes":
        """The Notes column's store (``ptk.SceneNotes``: one file per project, shared
        by both hosts' panels), its unmarked projects resolved under the workspace
        being browsed."""
        if self._scene_notes is None:
            self._scene_notes = ptk.SceneNotes()
        self._scene_notes.session_root = self.workspaces.workspace_dir() or None
        return self._scene_notes

    def note(self, path) -> str:
        """*path*'s note ('' without one; never raises into a listing)."""
        try:
            return self.scene_notes.get(path)
        except Exception:  # noqa: BLE001 - a note never fails the listing
            return ""

    def migrate_settings_notes(self):
        """Move notes a panel kept in its settings (keyed by path, before 2026-10-13)
        into each scene's project store; one whose project cannot be written stays.
        Run by the listing, under the session root it reads its notes with."""
        settings = getattr(self.ui, "settings", None)
        if settings is None:
            return
        try:
            legacy = dict(settings.value("reference_notes") or {})
        except (TypeError, ValueError):
            return
        if not legacy:
            return
        kept = self.scene_notes.import_notes(legacy)
        settings.setValue("reference_notes", kept)

    def set_note(self, path, text) -> None:
        """Save *text* as *path*'s note; a store that cannot be written is said so."""
        try:
            self.scene_notes.set(path, text)
            self.logger.info(f"Updated the note for {path}")
        except OSError as e:
            store = self.scene_notes.store_path(path)
            msg = f"Cannot save the note to {store or path}: {e}"
            if isinstance(e, PermissionError):
                msg += (
                    " -- the file or folder may be read-only (a shared team folder "
                    "on a synced drive with restricted permissions)."
                )
            self.logger.warning(msg)
            self.footer_status(msg)

    # ------------------------------------------------------------------ workspace

    # ------------------------------------------------------------------ naming

    # ------------------------------------------------------------------ listing
    def refresh_file_list(self, invalidate=False):
        """Rebuild the table for the browsed workspace, then re-select its
        references. A bake-backed reference follows its source first (re-baked and
        repointed, or moved out of temp: ``follow_bake_sources``) -- outside the
        signal block, as a re-bake reports into the footer."""
        self.context_menu_row = None  # row indices change
        try:
            self.engine.follow_bake_sources()
        except Exception as e:  # noqa: BLE001 - a listing never fails on a follow
            self.logger.warning(f"Could not follow the bakes' sources: {e}")
        self.migrate_settings_notes()
        with self.table_signals_blocked():
            self._refresh_file_list_internal(invalidate)
        self.sync_selection_to_references()

    def _reference_rows(self) -> List[str]:
        """The rows the scene's references stand for: a bake-backed one (a foreign
        row, a multi-take FBX) by the scene it was baked from, never the bake."""
        rows = []
        for ref in self.engine.current_references:
            try:
                rows.append(self.engine.bake_source(ref.path) or ref.path)
            except Exception:  # noqa: BLE001 - a broken reference has no row
                continue
        return rows

    def _refresh_file_list_internal(self, invalidate=False):
        if invalidate:
            self.engine.invalidate_workspace_files()
        combo = self.ui.cmb000
        workspace_path = combo.itemData(combo.currentIndex())
        if workspace_path is None:
            if combo.currentIndex() == -1 and combo.count() > 0:
                return  # repopulated, nothing selected yet
            self.logger.debug("No workspace selected in the combo box.")
            return
        if not os.path.isdir(workspace_path):
            self.logger.warning(f"Invalid workspace: {workspace_path}")
            return

        included = self.included_extensions()
        file_list = [
            f
            for f in self.engine.workspace_files.get(workspace_path, [])
            if os.path.splitext(f)[1].lower() in included
        ]
        unfiltered = len(file_list)
        _case, suffix, structure = self.naming_options()
        menu = self.header_menu()
        if self._checked("chk_filter_suffix", menu=menu) and suffix:
            file_list = [
                f
                for f in file_list
                if os.path.splitext(os.path.basename(f))[0].endswith(suffix)
            ]
        if self._checked("chk_filter_folder_structure", menu=menu):
            pattern = self.files.normalize_structure_pattern(structure)
            if pattern:
                file_list = ptk.SceneListing.filter_by_folder_structure(
                    file_list,
                    workspace_path,
                    pattern,
                    suffix,
                    ptk.SceneListing.scenes_folder(workspace_path),
                )
        self._prefiltered = unfiltered - len(file_list)

        fmenu = self.filter_menu()
        ignore_case = self._checked("chk_ignore_case", default=True, menu=fmenu)
        target_w = (
            getattr(fmenu, "cmb_filter_target", None) if fmenu is not None else None
        )
        target = target_w.currentText() if target_w is not None else "Filter: All"
        self._active_filter = (
            self.filter_text if self.filter_enabled else "",
            ignore_case,
            target in ("Filter: All", "Filter: Files"),
            target in ("Filter: All", "Filter: Notes"),
        )

        # External references -- a reference whose row is not this workspace's -- are
        # listed first, each by the row it stands for.
        ref_rows = self._reference_rows()
        listed = {
            self.norm(f) for f in self.engine.workspace_files.get(workspace_path, [])
        }
        foreign_ext = {e for e in self.engine.FOREIGN_EXTENSIONS if e in included}
        foreign_found = []
        if foreign_ext or any(self.engine.is_foreign(r) for r in ref_rows):
            foreign_found = self.engine.find_foreign_scenes(
                workspace_path,
                recursive=self.engine.recursive_search,
                extensions=sorted(foreign_ext) or None,
            )
            listed.update(self.norm(p) for p in foreign_found)
        external, seen = [], set()
        for row in ref_rows:
            key = self.norm(row)
            if key not in listed and key not in seen:
                seen.add(key)
                external.append(row)
        file_list = external + file_list

        # The workspace's foreign scenes of each checked foreign type: a foreign row's
        # reference icon bakes it and references the result.
        if foreign_ext:
            existing = {self.norm(p) for p in file_list}
            for p in foreign_found:
                if (
                    os.path.splitext(p)[1].lower() in foreign_ext
                    and self.norm(p) not in existing
                ):
                    file_list.append(p)

        hide_suffix = suffix if self._checked("chk_hide_suffix", menu=menu) else ""
        hide_extension = self._checked("chk_hide_extension", menu=menu)
        file_names = []
        for f in file_list:
            name = ptk.SceneListing.display_name(f, hide_extension, hide_suffix)
            if f in external:
                home = ptk.Workspace.find_containing(f)
                name = (
                    f"{name} ({os.path.basename(home.root)})"
                    if home
                    else f"{name} (External)"
                )
            file_names.append(name)
        if not file_list:
            self.logger.debug(f"No scene files found in workspace: {workspace_path}")
        self.update_table(file_names, file_list)

    def update_table(self, file_names, file_list):
        """(Re)fill the table with *file_list* labelled *file_names*: items reused
        across refreshes, the action icons and notes set per row, then the text
        filter applied to the rows (it reads the notes, so it runs last)."""
        Qt = self.sb.QtCore.Qt
        table = self.ui.tbl000
        table.setUpdatesEnabled(False)
        sorting = table.isSortingEnabled()
        table.setSortingEnabled(False)
        try:
            table.setRowCount(len(file_names))
            scene = self.engine.current_scene()
            current = self.norm(scene) if scene else ""
            refs_by_row, modes = self._references_by_row()
            for row, (label, file_path) in enumerate(zip(file_names, file_list)):
                item = table.item(row, self.COL_NAME)
                if not item:
                    item = self.sb.QtWidgets.QTableWidgetItem(label)
                    item.setFlags(item.flags() | Qt.ItemIsEditable)
                    table.setItem(row, self.COL_NAME, item)
                item.setText(label)
                item.setData(self.role(self.ROLE_PATH), file_path)
                item.setData(
                    self.role(self.ROLE_FILE_NAME), os.path.basename(file_path)
                )
                item.setData(self.role(self.ROLE_LABEL), label)
                # The label can hide the suffix/extension and elides in the column, so
                # the tooltip names the file in full (items are reused: reset each time).
                item.setToolTip(os.path.basename(file_path))
                is_current = bool(current) and self.engine.is_current(
                    file_path, current
                )
                if self.engine.is_foreign(file_path):
                    # A foreign row references through a BAKE, so it carries the same
                    # icon states as a native row, but it stays out of the selection ->
                    # reference sync (that would reference the row's own path, which
                    # the host cannot read) and is not renamed inline (renaming the
                    # source would orphan its bake's record).
                    item.setFlags(
                        (item.flags() | Qt.ItemIsEnabled)
                        & ~Qt.ItemIsSelectable
                        & ~Qt.ItemIsEditable
                    )
                else:
                    self.format_table_item(item, file_path, is_current)
                    item.setFlags(item.flags() | Qt.ItemIsEditable)
                key = self.norm(file_path)
                referenced = key in refs_by_row
                table.actions.set(
                    row, self.COL_REF, "referenced" if referenced else "unreferenced"
                )
                table.actions.set(
                    row, self.COL_OPEN, "current" if is_current else "default"
                )
                table.actions.set(
                    row,
                    self.COL_DISPLAY,
                    modes.get(key, "off") if referenced else "unavailable",
                )
                notes_item = table.item(row, self.COL_NOTES)
                if not notes_item:
                    notes_item = self.sb.QtWidgets.QTableWidgetItem()
                    notes_item.setFlags(notes_item.flags() | Qt.ItemIsEditable)
                    table.setItem(row, self.COL_NOTES, notes_item)
                notes_item.setData(self.role(self.ROLE_PATH), file_path)
                comment = self.note(file_path)
                if notes_item.text() != comment:
                    notes_item.setText(comment)
            table.apply_formatting()
            self._apply_text_filter(table)
        finally:
            table.setSortingEnabled(sorting)
            table.setUpdatesEnabled(True)
        self.update_listing_footer(len(file_list), len(refs_by_row))

    def _apply_text_filter(self, table):
        """Hide the rows whose file name and note both miss the filter text."""
        text, ignore_case, include_files, include_notes = self._active_filter
        patterns = ptk.SceneListing.split_patterns(text) if text else []
        for row in range(table.rowCount()):
            if not text:
                table.setRowHidden(row, False)
                continue
            item = table.item(row, self.COL_NAME)
            notes_item = table.item(row, self.COL_NOTES)
            path = item.data(self.role(self.ROLE_PATH)) if item else ""
            name_match = include_files and ptk.SceneListing.text_matches_filter(
                os.path.basename(path or ""), patterns, ignore_case
            )
            notes_match = include_notes and ptk.SceneListing.matches_notes_filter(
                notes_item.text() if notes_item else "", text, ignore_case
            )
            table.setRowHidden(row, not (name_match or notes_match))

    def update_listing_footer(self, listed: int, referenced: int):
        """The footer's listing summary -- files shown, rows referenced, files the
        filters hid -- so a filter (or a restored preset) that hides everything never
        reads as an empty workspace."""
        footer = getattr(self.ui, "footer", None)
        if footer is None:
            return
        table = self.ui.tbl000
        hidden_rows = sum(
            1 for row in range(table.rowCount()) if table.isRowHidden(row)
        )
        hidden = hidden_rows + self._prefiltered
        msg = f"{listed - hidden_rows} file(s); {referenced} referenced."
        if hidden:
            msg += f" ({hidden} hidden by the filters)"
        footer.setText(msg)

    def format_table_item(self, item, file_path, is_current):
        """The current scene's name cell: enabled (rename / delete / open) but not
        selectable -- a scene cannot be referenced into itself -- italic and
        highlighted; any other row selectable, its highlight reset."""
        Qt = self.sb.QtCore.Qt
        marker = self.role(self.ROLE_CURRENT)
        if is_current:
            item.setFlags((item.flags() | Qt.ItemIsEnabled) & ~Qt.ItemIsSelectable)
            item.setToolTip(
                f"{os.path.basename(file_path)}\n"
                f"Current scene file - cannot be referenced\n{file_path}"
            )
            self.ui.tbl000.format_item(item, key="current", italic=True)
            item.setData(marker, True)
        else:
            item.setFlags(item.flags() | (Qt.ItemIsSelectable | Qt.ItemIsEnabled))
            if item.data(marker):
                self.ui.tbl000.format_item(item, key="reset", italic=False)
                item.setData(marker, False)

    def _references_by_row(self, with_modes=True):
        """``({row key: [references]}, {row key: display mode})`` -- each reference
        keyed by the ROW it stands for (a bake-backed one by its source), a row's mode
        any non-off one its references report (not read without *with_modes*)."""
        refs_by_row, modes = {}, {}
        for ref in self.engine.current_references:
            try:
                key = self.engine.row_key(ref.path)
            except Exception:  # noqa: BLE001 - a broken reference has no row
                continue
            refs_by_row.setdefault(key, []).append(ref)
            if not with_modes:
                continue
            mode = self.engine.get_reference_display_mode(ref)
            if mode != "off" or key not in modes:
                modes[key] = mode
        return refs_by_row, modes

    def row_references(self, path) -> list:
        """The references a row stands for -- through the bake standing in for it too."""
        key = self.norm(path)
        refs = []
        for ref in self.engine.current_references:
            try:
                if self.engine.row_key(ref.path) == key:
                    refs.append(ref)
            except Exception:  # noqa: BLE001 - a broken reference has no row
                continue
        return refs

    def sync_reference_icons(self):
        """The reference and display-mode icons of every row, from the live references."""
        table = self.ui.tbl000
        refs_by_row, modes = self._references_by_row()
        for row in range(table.rowCount()):
            path = self.row_path(row)
            if not path:
                continue
            key = self.norm(path)
            if key in refs_by_row:
                table.actions.set(row, self.COL_REF, "referenced")
                table.actions.set(row, self.COL_DISPLAY, modes.get(key, "off"))
            else:
                table.actions.set(row, self.COL_REF, "unreferenced")
                table.actions.set(row, self.COL_DISPLAY, "unavailable")
        self.update_listing_footer(table.rowCount(), len(refs_by_row))

    def sync_selection_to_references(self):
        """Select exactly the rows the scene references (selectable rows only)."""
        Qt = self.sb.QtCore.Qt
        with self.table_signals_blocked() as table:
            table.clearSelection()
            refs_by_row, _modes = self._references_by_row(with_modes=False)
            for row in range(table.rowCount()):
                item = table.item(row, self.COL_NAME)
                path = item.data(self.role(self.ROLE_PATH)) if item else None
                if (
                    path
                    and self.norm(path) in refs_by_row
                    and (item.flags() & Qt.ItemIsSelectable)
                ):
                    item.setSelected(True)

    def handle_item_selection(self):
        """The selection changed: reference the newly selected rows, remove the
        references of the rows deselected -- diffed by path over the rows listed, so a
        reference whose file is no row here (another workspace, a filtered-out type)
        is never touched by a click on an unrelated row."""
        Qt = self.sb.QtCore.Qt
        table = self.ui.tbl000
        selected = {}
        for idx in table.selectedIndexes():
            if idx.column() != self.COL_NAME:
                continue
            item = table.item(idx.row(), self.COL_NAME)
            if item is None:
                continue
            path = item.data(self.role(self.ROLE_PATH))
            if not (item.flags() & Qt.ItemIsSelectable) or self.engine.is_current(path):
                item.setSelected(False)  # the current scene / a foreign row
                continue
            if path:
                selected[self.norm(path)] = (item.text(), path, item)
        refs_by_row, _modes = self._references_by_row(with_modes=False)
        listed = {
            self.norm(p) for p in map(self.row_path, range(table.rowCount())) if p
        }
        to_remove = [
            key
            for key in (set(refs_by_row) & listed) - set(selected)
            if not self.engine.is_foreign(key)
        ]
        for key in to_remove:
            self.engine.remove_references([ref.namespace for ref in refs_by_row[key]])
        for key in set(selected) - set(refs_by_row):
            # The label seeds the namespace (sanitized; the host makes it unique).
            label, path, item = selected[key]
            try:
                ok = self.engine.add_reference(label, path)
            except (RuntimeError, OSError) as e:
                self.error_box("Reference failed for", os.path.basename(path), e)
                ok = False
            if not ok:
                item.setSelected(False)
        self.sync_reference_icons()

    def apply_notes_column_visibility(self):
        """Show the Notes column only while Show Notes Column is checked (view-only:
        the notes are still read and filterable while it is hidden)."""
        self.ui.tbl000.setColumnHidden(
            self.COL_NOTES, not self._checked("chk_show_notes_column")
        )

    def refilter_on_naming_change(self):
        """Re-filter when a naming field changes while a filter / display option
        that reads it is on."""
        for name in (
            "chk_hide_suffix",
            "chk_filter_suffix",
            "chk_filter_folder_structure",
        ):
            if self._checked(name):
                self.refresh_file_list(invalidate=False)
                return

    # ------------------------------------------------------------------ rows
    def row_path(self, row):
        """The path on *row*'s name cell (None for no row)."""
        item = self.ui.tbl000.item(row, self.COL_NAME) if row is not None else None
        return item.data(self.role(self.ROLE_PATH)) if item else None

    def capture_context_row(self, pos):
        """Store the right-clicked row (the menu acts on it, not the selection) and
        label its Open action. Same event-loop tick as the menu's own show, so the
        relabel lands before the popup's first paint."""
        idx = self.ui.tbl000.indexAt(pos)
        self.context_menu_row = idx.row() if idx.isValid() and idx.row() >= 0 else None
        self.label_open_action()

    def context_row(self):
        """The right-clicked row, validated against the row count, or None."""
        row = self.context_menu_row
        if row is None or not 0 <= row < self.ui.tbl000.rowCount():
            return None
        return row

    def label_open_action(self):
        """Read the context menu's Open as 'Reopen' on the open scene's row: opening
        it again is a reload from disk, the one signal the click drops unsaved work.
        Guarded on ``has_menu``: uitk builds a menu lazily on first ``.menu`` read."""
        table = self.ui.tbl000
        if not getattr(table, "has_menu", False):
            return
        btn = getattr(table.menu, "btn_open_scene", None)
        if btn is None:
            return
        path = self.row_path(self.context_row())
        btn.setText("Reopen" if path and self.engine.is_current(path) else "Open")

    def select_item_silently(self, item, selected: bool) -> None:
        """Set *item*'s selection without firing the selection -> reference sync."""
        table = self.ui.tbl000
        blocked = table.blockSignals(True)
        try:
            item.setSelected(selected)
        finally:
            table.blockSignals(blocked)

    # ------------------------------------------------------------------ inline edits
    def prepare_item_for_edit(self, item):
        """Show the full file name in the name cell an inline rename edits."""
        if item.column() != self.COL_NAME:
            return
        self.editing_item = item
        full = item.data(self.role(self.ROLE_FILE_NAME))
        if full:
            item.setText(full)

    def restore_item_display(self, item):
        """Restore the name cell's label after an edit."""
        if item.column() != self.COL_NAME:
            return
        if self.editing_item is item:
            self.editing_item = None
        label = item.data(self.role(self.ROLE_LABEL))
        if label:
            item.setText(label)

    def item_double_clicked(self, item):
        """Double-click a name to rename it inline (editable rows only: never a
        foreign one), a note to edit it."""
        if item is None:
            return
        Qt = self.sb.QtCore.Qt
        if item.column() == self.COL_NAME and (item.flags() & Qt.ItemIsEditable):
            self.prepare_item_for_edit(item)
            self.ui.tbl000.editItem(item)
        elif item.column() == self.COL_NOTES:
            self.ui.tbl000.editItem(item)

    def item_changed(self, item):
        """Commit an inline rename (the name column) or a note (the Notes column)."""
        if item.column() == self.COL_NOTES:
            path = item.data(self.role(self.ROLE_PATH))
            if path:
                self.set_note(path, item.text().strip())
            return
        if item.column() != self.COL_NAME or self.editing_item is not item:
            return
        new_name = item.text().strip()
        old_path = item.data(self.role(self.ROLE_PATH))
        if not new_name or not old_path or not os.path.exists(old_path):
            self.restore_item_display(item)
            return
        old_name = os.path.basename(old_path)
        if new_name == old_name:
            self.restore_item_display(item)
            return
        if not os.path.splitext(new_name)[1]:
            new_name += os.path.splitext(old_name)[1]
        new_path = os.path.join(os.path.dirname(old_path), new_name)
        # A case-only rename's target "exists" on a case-insensitive file system.
        if os.path.exists(new_path) and not ptk.FileUtils.is_same_file(
            new_path, old_path
        ):
            self.message(
                f"Target file already exists:<br>{html.escape(new_name, quote=False)}"
            )
            self.restore_item_display(item)
            return
        # Cleared up front: renaming the OPEN scene reopens it, and the rebuild that
        # follows reuses these items -- a still-set editing item would read its setText
        # as another inline rename.
        self.editing_item = None
        # A per-scene folder ({name} in the structure) follows under the typed name
        # less the suffix -- the literal edit applies no case convention.
        _case, suffix, structure = self.naming_options()
        folder = (
            ptk.StrUtils.strip_suffix(os.path.splitext(new_name)[0], [suffix])
            if "{name}" in structure
            else None
        )
        self.files.rename_path(old_path, new_path, folder, item)

    def editor_closed(self, *_args):
        """The inline editor closed: the name cell shows its label again."""
        item = self.ui.tbl000.currentItem()
        if item is not None and item.column() == self.COL_NAME:
            self.restore_item_display(item)

    # ------------------------------------------------------------------ scene files

    # ------------------------------------------------------------------ foreign scenes

    # ------------------------------------------------------------------ references, in bulk
