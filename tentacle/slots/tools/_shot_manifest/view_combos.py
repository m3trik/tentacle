# !/usr/bin/python
# coding=utf-8
"""The Shot Manifest's view row, above the table: Select, Expand, Collapse,
Hide and Show -- a combobox each, every action of its kind in one place.

Each lists its actions afresh as it opens -- with counts, those with nothing
to act on disabled -- and shows its title again after a pick.  An action
names the rows it acts on, never holds them: a redraw while the list is open
(a store edit, the deferred Assess) draws new rows, and the pick finds those.
A mouse wheel over a closed combo picks nothing (uitk ``wheel_selects``).

One copy for both hosts: every host call goes through the controller's
``manifest_host``, the host library's ``ManifestHost`` (from ``Slots.tk``).
"""

from typing import Callable, List, Optional, Tuple

import pythontk as ptk
from pythontk import BuilderObject, BuilderStep

from .manifest_data import COL_BEHAVIORS, COL_DESC, COL_STATUS, COL_STEP, ManifestData

#: One row of a view combo: (label, action, enabled, tooltip).
ViewAction = Tuple[str, Callable[[], None], bool, str]


class ViewCombosMixin:
    """The view row, mixed into ``ShotManifestController``.

    Uses the controller's ``ui`` (``cmb_select`` ... ``cmb_show``,
    ``tbl_steps``), ``_steps``, ``_last_results``, ``_editor``,
    ``_pairing()``, ``_hide_missing`` / ``_set_hide_missing()``,
    ``_show_in_outliner()``, the table's ``_step_items()`` /
    ``_issue_ids()`` / ``_extra_rows()`` / ``expand_missing()`` /
    ``expand_extra()``, and ``_set_footer()``.
    """

    #: The view row: each combo's objectName, title and the method listing
    #: its actions.
    VIEW_COMBOS = (
        ("cmb_select", "Select", "_select_actions"),
        ("cmb_expand", "Expand", "_expand_actions"),
        ("cmb_collapse", "Collapse", "_collapse_actions"),
        ("cmb_hide", "Hide", "_hide_actions"),
        ("cmb_show", "Show", "_show_actions"),
    )

    def _setup_view_combos(self) -> None:
        """Fill the view row's combos and run the action a pick names -- a
        pick from the open list only: a wheel turned over a closed one ran
        its first enabled action, unseen."""
        for name, title, lister in self.VIEW_COMBOS:
            cmb = getattr(self.ui, name, None)
            if cmb is None:
                continue
            cmb.wheel_selects = False
            self._fill_view_combo(cmb, title, lister)
            cmb.before_popup_shown.connect(
                lambda c=cmb, t=title, f=lister: self._fill_view_combo(c, t, f)
            )
            cmb.currentIndexChanged.connect(
                lambda index, c=cmb: self._run_view_action(c, index)
            )

    def _setup_search(self) -> None:
        """The view row's search field, at its right end (as the Unity manifest's): only the steps
        whose words match every word typed show -- the step's ID, name and Status, and its objects'
        names, behaviors and statuses. A view alone: Assess and Build still take every step.

        The field is the ``.ui``'s ``txt_search``, the view row's last. Its text
        is never kept (a filter forgotten in a closed panel would hide steps on
        the next open), and a clear button empties it."""
        field = self.ui.txt_search
        field.restore_state = False
        field.option_box.clear_option = True
        field.textChanged.connect(lambda _text: self._apply_issues_filter())
        self._search_field = field

    def _setup_detail(self) -> None:
        """The detail of the selection, under the table (as the Unity manifest's): the selected
        row's step or object, its words, its behaviors with their states and every issue -- what
        its tooltips say, kept in view. In a splitter with the table, so it folds away."""
        from qtpy import QtCore, QtWidgets

        tree = self.ui.tbl_steps
        detail = QtWidgets.QTextBrowser()
        detail.setObjectName("txt_detail")
        detail.setOpenLinks(False)
        detail.setMinimumHeight(0)
        detail.setToolTip(
            "The selected row: its words, its behaviors' states and every issue."
        )
        self._detail = detail
        parent = tree.parentWidget() if hasattr(tree, "parentWidget") else None
        layout = parent.layout() if parent is not None else None
        index = layout.indexOf(tree) if layout is not None else -1
        if index >= 0:
            splitter = QtWidgets.QSplitter(QtCore.Qt.Vertical)
            splitter.setObjectName("split_detail")
            stretch = layout.stretch(index)
            layout.insertWidget(index, splitter, stretch)
            splitter.addWidget(tree)  # out of the layout, into the splitter
            splitter.addWidget(detail)
            splitter.setStretchFactor(0, 4)
            splitter.setStretchFactor(1, 1)
            splitter.setCollapsible(1, True)
        tree.itemSelectionChanged.connect(self._show_detail)
        self._show_detail()

    def _show_detail(self) -> None:
        """Fill the detail with the selected row (:meth:`_setup_detail`): a step's ID, name and
        words, or an object's name, step and behaviors; then its status and its issues."""
        import html

        from qtpy.QtCore import Qt

        detail = getattr(self, "_detail", None)
        if detail is None:
            return
        tree = self.ui.tbl_steps
        chosen = tree.selectedItems()
        if not chosen:
            detail.setHtml(
                "<span style='color:gray'>Select a row: its words, its behaviors' states and "
                "every issue show here.</span>"
            )
            return
        item = chosen[0]
        data = item.data(0, Qt.UserRole)
        lines = []
        if isinstance(data, BuilderStep):
            name = getattr(data, "name", "") or ""
            lines.append(
                f"<b>{html.escape(data.step_id)}</b>&nbsp; {html.escape(name)}"
            )
            if data.description:
                lines.append(html.escape(data.description))
        elif isinstance(data, BuilderObject):
            parent = item.parent()
            step = parent.data(0, Qt.UserRole) if parent is not None else None
            where = (
                f" &nbsp;<span style='color:gray'>in {html.escape(step.step_id)}</span>"
                if isinstance(step, BuilderStep)
                else ""
            )
            lines.append(f"<b>{html.escape(data.name or '')}</b>{where}")
            # Its behaviors as its chips say them: each one's state line, in its colour.
            cell = tree.itemWidget(item, COL_BEHAVIORS)
            for chip in getattr(cell, "shown", ()):
                color = ManifestData.chip_look(chip.state)[0]
                line = html.escape(chip.line)
                lines.append(
                    f"<span style='color:{color}'>{line}</span>" if color else line
                )
        else:
            lines.append(html.escape(item.text(COL_DESC) or item.text(COL_STEP)))
        status = item.text(COL_STATUS)
        if status:
            lines.append(f"<i>{html.escape(status)}</i>")
        # The row's issues as its tooltip lists them (TreeWidget.set_row_tooltip).
        issues = tree.row_tooltip(item)
        if issues:
            lines.append(str(issues))
        if len(chosen) > 1:
            lines.append(
                f"<span style='color:gray'>(+{len(chosen) - 1} more selected)</span>"
            )
        detail.setHtml("<br>".join(lines))

    def _search_words(self) -> List[str]:
        """The words typed in the view row's search field, lower case; none when it is empty."""
        field = getattr(self, "_search_field", None)
        return field.text().lower().split() if field is not None else []

    @staticmethod
    def _row_words(item, columns: int) -> str:
        """Everything a search reads of a step row: its cells and its objects' cells, and the
        step and objects it holds (the Behaviors cell is a widget, so its behaviors come from them)."""
        from qtpy.QtCore import Qt

        words = []
        rows = [item] + [item.child(j) for j in range(item.childCount())]
        for row in rows:
            words.extend(row.text(c) for c in range(columns))
            data = row.data(0, Qt.UserRole)
            if isinstance(data, BuilderStep):
                words.extend(
                    (
                        data.step_id,
                        data.shot_name or "",
                        getattr(data, "name", "") or "",
                    )
                )
            elif isinstance(data, BuilderObject):
                words.append(data.name or "")
                words.extend(data.behaviors or ())
        return " ".join(w for w in words if w).lower()

    def _fill_view_combo(self, cmb, title: str, lister: str) -> None:
        """List *lister*'s actions in *cmb* under *title*: each row's action
        its data, a row with nothing to act on disabled, its tooltip its own."""
        from qtpy.QtCore import Qt

        actions: List[ViewAction] = getattr(self, lister)()
        cmb.add([(label, action) for label, action, _on, _tip in actions], header=title)
        model = cmb.model()
        for row, (_label, _action, enabled, tip) in enumerate(actions):
            item = model.item(row) if hasattr(model, "item") else None
            if item is not None:
                item.setEnabled(enabled)
            cmb.setItemData(row, tip, Qt.ToolTipRole)

    @staticmethod
    def _run_view_action(cmb, index: int) -> None:
        """Run the action of the row picked in *cmb* (its item data)."""
        if index < 0:
            return  # the title again, after a pick
        action = cmb.itemData(index)
        if callable(action):
            action()

    # ---- what the rows are ---------------------------------------------------

    def _top_rows(self, selected: bool = False) -> list:
        """The table's top-level rows -- only the selected ones, or the rows of
        the selected object rows, with *selected*."""
        tree = self.ui.tbl_steps
        if not selected:
            return [tree.topLevelItem(i) for i in range(tree.topLevelItemCount())]
        rows = []
        for item in tree.selectedItems():
            row = item.parent() or item
            if row not in rows:
                rows.append(row)
        return rows

    @staticmethod
    def _row_step(item):
        """The step a row shows, or ``None`` (a "not in doc" shot)."""
        from qtpy.QtCore import Qt

        data = item.data(0, Qt.UserRole)
        return data if isinstance(data, BuilderStep) else None

    @staticmethod
    def _view_key(item) -> Optional[tuple]:
        """What a row shows -- ``("step", step_id)`` or ``("shot",
        shot_id)`` -- by which a view action finds it again after a redraw.
        Its own name: ``ManifestTableMixin._row_key`` (a step's ID, else the
        row's text) comes first in the controller's bases and would shadow
        it, keying a shot row by its text."""
        from qtpy.QtCore import Qt

        data = item.data(0, Qt.UserRole)
        if isinstance(data, BuilderStep):
            return ("step", data.step_id)
        shot_id = getattr(data, "shot_id", None)
        return None if shot_id is None else ("shot", shot_id)

    def _rows_now(self, keys) -> list:
        """The rows showing *keys* (:meth:`_view_key`) as the table is drawn
        now, in table order."""
        wanted = set(keys)
        return [row for row in self._top_rows() if self._view_key(row) in wanted]

    def _keys(self, rows) -> List[tuple]:
        """*rows*' keys (:meth:`_view_key`), for an action to find them by."""
        return [key for key in map(self._view_key, rows) if key is not None]

    def _selected_step_ids(self) -> List[str]:
        """The steps of the selected rows, in table order."""
        steps = (self._row_step(row) for row in self._top_rows(selected=True))
        return [step.step_id for step in steps if step is not None]

    @staticmethod
    def _object_names(rows) -> List[str]:
        """The objects under *rows*, each once, in table order."""
        from qtpy.QtCore import Qt

        names = []
        for row in rows:
            for j in range(row.childCount()):
                data = row.child(j).data(0, Qt.UserRole)
                if isinstance(data, BuilderObject) and data.name not in names:
                    names.append(data.name)
        return names

    def _unlisted_object_names(self) -> List[str]:
        """The objects in the steps' shots that no step lists: the shots'
        own members and, once assessed, what animates in their ranges."""
        from qtpy.QtCore import Qt

        listed = [o.name for step in self._steps for o in step.objects]
        names = []
        for row in self._top_rows():
            for j in range(row.childCount()):
                data = row.child(j).data(0, Qt.UserRole)
                if isinstance(data, BuilderObject) and data.origin == "member":
                    names.append(data.name)
        for r in self._last_results or ():
            names.extend(r.additional_objects)
        names = list(dict.fromkeys(names))
        named = {m for _n, m in ptk.ShotStore.name_pairs(listed, names)}  # PANEL|LATCH: never DOOR|LATCH
        return [n for n in names if n not in named]

    def _select_rows(self, rows) -> None:
        """Make *rows* the table's selection, the first scrolled to."""
        tree = self.ui.tbl_steps
        tree.clearSelection()
        for row in rows:
            row.setSelected(True)
        if rows:
            tree.scrollToItem(rows[0])
        self._set_footer(f"{len(rows)} row(s) selected.")

    @staticmethod
    def _counted(label: str, n: int) -> str:
        return f"{label} ({n})" if n else label

    # ---- the combos' actions ---------------------------------------------------

    def _select_actions(self) -> List[ViewAction]:
        """Select: rows in the table, or the rows' objects in the scene."""
        tree = self.ui.tbl_steps
        built = self._pairing().shots
        rows = self._top_rows()
        steps = [row for row in rows if self._row_step(row) is not None]
        issues = self._keys(self._step_items(self._issue_ids()))
        unbuilt = self._keys(r for r in steps if self._row_step(r).step_id not in built)
        every = self._keys(steps)
        chosen = self._object_names(self._top_rows(selected=True))
        listed = self._object_names(steps)
        unlisted = self._unlisted_object_names()
        assessed = bool(self._last_results)
        return [
            (
                self._counted("Rows with Issues", len(issues)),
                lambda: self._select_rows(self._rows_now(issues)),
                bool(issues),
                "Select the step rows the last Assess found something in."
                if assessed
                else "Assess first: it finds the issues.",
            ),
            (
                self._counted("Unbuilt Steps", len(unbuilt)),
                lambda: self._select_rows(self._rows_now(unbuilt)),
                bool(unbuilt),
                "Select the steps that have no shot yet.",
            ),
            (
                self._counted("All Steps", len(every)),
                lambda: self._select_rows(self._rows_now(every)),
                bool(every),
                "Select every step row.",
            ),
            (
                "None",
                tree.clearSelection,
                bool(tree.selectedItems()),
                "Clear the table's selection.",
            ),
            (
                self._counted("Scene: Objects of Selected Rows", len(chosen)),
                lambda: self._show_in_outliner(chosen),
                bool(chosen),
                "Select the selected rows' objects in the scene, and show them "
                "in the Outliner.",
            ),
            (
                self._counted("Scene: Every Listed Object", len(listed)),
                lambda: self._show_in_outliner(listed),
                bool(listed),
                "Select every object the steps list in the scene.",
            ),
            (
                self._counted("Scene: Objects Not in the Manifest", len(unlisted)),
                lambda: self._show_in_outliner(unlisted),
                bool(unlisted),
                "Select in the scene what the shots hold or animate that no "
                "step lists.",
            ),
        ]

    def _expand_actions(self) -> List[ViewAction]:
        """Expand: every row, those with issues or objects not in the
        manifest, or the selected ones."""
        tree = self.ui.tbl_steps
        selected = self._keys(self._top_rows(selected=True))
        assessed = bool(self._last_results)

        def expand(keys):
            for row in self._rows_now(keys):
                row.setExpanded(True)

        return [
            ("All", tree.expandAll, tree.topLevelItemCount() > 0, "Expand every row."),
            (
                "Rows with Issues",
                self.expand_missing,
                assessed,
                "Expand the step rows the last Assess found something in."
                if assessed
                else "Assess first: it finds the issues.",
            ),
            (
                "Rows with Objects Not in the Manifest",
                self.expand_extra,
                bool(self._extra_rows()),
                "Expand the step rows whose shot holds or animates objects the "
                "step does not list.",
            ),
            (
                self._counted("Selected Rows", len(selected)),
                lambda: expand(selected),
                bool(selected),
                "Expand the selected rows.",
            ),
        ]

    def _collapse_actions(self) -> List[ViewAction]:
        """Collapse: every row, those without issues, or the selected ones."""
        tree = self.ui.tbl_steps
        selected = self._keys(self._top_rows(selected=True))
        assessed = bool(self._last_results)
        issues = self._issue_ids()

        def collapse(rows):
            for row in rows:
                row.setExpanded(False)

        def clean():
            return [
                row
                for row in self._top_rows()
                if self._row_step(row) is not None
                and self._row_step(row).step_id not in issues
            ]

        return [
            (
                "All",
                tree.collapseAll,
                tree.topLevelItemCount() > 0,
                "Collapse every row.",
            ),
            (
                "Rows Without Issues",
                lambda: collapse(clean()),
                assessed,
                "Collapse the step rows the last Assess found nothing in."
                if assessed
                else "Assess first: it finds the issues.",
            ),
            (
                self._counted("Selected Rows", len(selected)),
                lambda: collapse(self._rows_now(selected)),
                bool(selected),
                "Collapse the selected rows.",
            ),
        ]

    def _hide_actions(self) -> List[ViewAction]:
        """Hide: the selected steps or their sections (Local Edits), or every
        step without a shot (a view)."""
        editor = self._editor
        built = self._pairing().shots
        chosen = self._selected_step_ids()
        sections = {s.section for s in self._steps if s.step_id in chosen and s.section}
        in_sections = [s.step_id for s in self._steps if s.section in sections]
        hideable = [sid for sid in chosen if sid not in built]
        section_hideable = [sid for sid in in_sections if sid not in built]
        why = (
            "Comparing to the original sheet: Local Edits are off."
            if not editor.enabled
            else "A built step stays: Build never removes a shot."
        )
        return [
            (
                self._counted("Selected Steps", len(hideable)),
                lambda: editor.hide_steps(hideable),
                editor.enabled and bool(hideable),
                "Leave the selected steps out (a Local Edit; a built one stays)."
                if hideable
                else why,
            ),
            (
                self._counted("Sections of Selected Steps", len(section_hideable)),
                lambda: editor.hide_steps(section_hideable),
                editor.enabled and bool(section_hideable),
                "Leave out every step of the selected steps' sections (a Local "
                "Edit; a built one stays)."
                if section_hideable
                else why,
            ),
            (
                "Steps Without a Shot",
                lambda: self._set_hide_missing(True),
                not self._hide_missing and bool(built),
                "Leave out every step that has no shot, once any step has one. "
                "A view, not an edit: Assess and Build skip them, and Show "
                "brings them back.",
            ),
            (
                self._counted("Steps With Nothing to Do", len(self._quiet_rows())),
                lambda: self._set_issues_only(True),
                not self._issues_only and bool(self._last_results),
                "Show only the rows that need something: an issue, a build to "
                "do, a Local Edit, a shot the sheet lacks. A view alone: Assess "
                "and Build still take every step."
                if self._last_results
                else "Assess first: it says which steps need something.",
            ),
        ]

    def _show_actions(self) -> List[ViewAction]:
        """Show: the steps and objects Local Edits hid, or the steps without
        a shot the view hides."""
        editor = self._editor
        steps = editor.edits.hidden_steps()
        objects = editor.unlocked_hidden_objects()
        return [
            (
                self._counted("Hidden Steps", len(steps)),
                lambda: editor.hide_steps(steps, False),
                editor.enabled and bool(steps),
                "Show every step Local Edits hid.",
            ),
            (
                self._counted("Hidden Objects", len(objects)),
                editor.show_hidden_objects,
                editor.enabled and bool(objects),
                "Show every object Local Edits hid (a locked step's stay).",
            ),
            (
                "Steps Without a Shot",
                lambda: self._set_hide_missing(False),
                self._hide_missing,
                "Show the steps that have no shot again.",
            ),
            (
                "Steps With Nothing to Do",
                lambda: self._set_issues_only(False),
                self._issues_only,
                "Show every step again.",
            ),
        ]
