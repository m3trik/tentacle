# !/usr/bin/python
# coding=utf-8
"""The Shot Manifest tree's rows: populating them (``ShotPairing.rows``: steps,
the members of their shots, the shots no step pairs with), formatting, colour
tags, assessment colouring and the behavior-label widgets.  The Start / End
cells are :mod:`.range_column`'s.

Mixed into :class:`~.shot_manifest_controller.ShotManifestController`.

One copy for both hosts: every host call goes through the controller's
``manifest_host``, the host library's ``ManifestHost`` (from ``Slots.tk``).
"""

import html
from typing import Optional

import pythontk as ptk
from pythontk import BuilderObject, BuilderStep, StepStatus

from .behavior_chips import BehaviorChips, Chip
from .manifest_data import (
    COL_BEHAVIORS,
    COL_DESC,
    COL_END,
    COL_START,
    COL_STATUS,
    COL_STEP,
    ERROR_COLOR,
    HEADERS,
    STEP_ICON_COLOR,
    ManifestData,
)

#: Tooltip line for an object the sheet's asset column did not list
#: (``BuilderObject.origin``).
_ORIGIN_NOTES = {
    "description": "Named in the step's description -- the asset column lists none.",
    "shot": "Auto-filled from the scene -- not listed in the sheet.",
    # The members of a shot shown under its row (``_add_member_rows``).
    "member": "In the step's shot, not listed in the manifest.",
}

#: Object statuses about a behavior, and the word the step's Behaviors cell
#: counts each by ("2 missing, 1 to re-key").
_BEHAVIOR_WORDS = {
    "missing_behavior": "missing",
    "behavior_conflict": "in conflict",
    "unknown_behavior": "unknown",
    "stale_behavior": "to re-key",
}
_BEHAVIOR_ISSUES = tuple(_BEHAVIOR_WORDS)


class ManifestTableMixin:
    """Presentation methods for the manifest tree widget.

    Expects the host class to provide:

    - ``self.ui``  – the loaded UI with ``tbl_steps`` tree widget.
    - ``self._steps`` / ``self._sheet_steps``  – the steps shown, and the
      source's own.
    - ``self._last_results``  – last assessment result list.
    - ``self._is_built``  – whether shots have been built.
    - ``self._update_build_button()``  – button-state refresh.
    - ``self._set_footer(text, *, color)``  – footer label helper.
    - ``self._settings``  – :class:`SettingsManager` instance.
    - ``self._editor``  – the :class:`ManifestEditor` (Local Edits).
    - ``self._row_tags``  – the tree's ``RowTags`` (colour strip).
    - ``self._active_store()`` / ``self._active_mapping``  – the scene's
      store and the effective mapping template.
    - ``self._rows()``  – the table's ``(step, shot)`` rows (``ShotPairing.rows``).
    - ``self._locked_step_ids()``  – the steps whose shot is locked.
    - the Start / End column's ``_restore_user_ranges()`` /
      ``_refresh_timing()`` (``RangeColumnMixin`` / ``StoreFollowMixin``).
    - the header menu's ``_marked_behaviors()`` / ``_disabled_behaviors()``
      / ``_sync_behavior_modes()`` and the view row's ``_show_detail()`` /
      ``_search_words()``.
    """

    @property
    def _use_short_names(self) -> bool:
        """Whether to display leaf-only names instead of full DAG paths."""
        settings = getattr(self, "_settings", None)
        if settings is None:
            return True
        return not settings.value("long_names", False)

    def _show_name(self, tree, item, name: str, note: str = "") -> None:
        """Show object *name* in *item*'s Description cell: its leaf alone,
        plain, or (Long Names) its whole path, read by its end -- the parents
        faded and cut from the left when narrow, the leaf whole and semi-bold
        (``TreeWidget.set_cell_tail``). Its tooltip names it whole, with
        *note* (why the row is here) under it, where either says more than
        the cell."""
        leaf = self.manifest_host.leaf_name(name)
        display = leaf if self._use_short_names else name
        item.setText(COL_DESC, display)
        start = len(display) - len(leaf) if display.endswith(leaf) else 0
        # Emphasis only against a faded lead: a leaf alone reads plain.
        tree.set_cell_tail(item, COL_DESC, start or None)
        if name != leaf or note:
            item.setToolTip(COL_DESC, self._name_tip(name, leaf, note))

    def _step_text(self, step) -> str:
        """*step*'s Description as shown: with short names (Long Names off),
        each of its objects' paths in it reads as the object's leaf, as its
        rows do -- the longest first, so no path is cut inside another."""
        text = step.display_text or ""
        if not self._use_short_names:
            return text
        leaf_name = self.manifest_host.leaf_name
        for name in sorted({o.name for o in step.objects if o.name}, key=len, reverse=True):
            leaf = leaf_name(name)
            if leaf != name:
                text = text.replace(name, leaf)
        return text

    @staticmethod
    def _name_tip(name: str, leaf: str, note: str = "") -> str:
        """An object's tooltip: its leaf, its whole name where that differs,
        and *note*."""
        # One line: Qt broke a path after each "|" (a break opportunity, even
        # in <nobr>); a word joiner after each forbids it.
        path = html.escape(name).replace("|", "|" + chr(0x2060))
        rows = [("Path", path)] if name != leaf else None
        return ptk.TooltipFormat.fmt(
            title=html.escape(leaf), rows=rows, body=html.escape(note) if note else None
        )

    @staticmethod
    def _row_key(item):
        """What a top-level row is across redraws: its step's ID (a rename
        changes the text, never the ID), else its text."""
        from qtpy.QtCore import Qt

        data = item.data(0, Qt.UserRole)
        return data.step_id if isinstance(data, BuilderStep) else item.text(0)

    def _row_icon(self, item) -> Optional[str]:
        """The icon a top-level row has whatever it says: a lock for a step
        whose shot is locked (final: Build leaves it, Local Edits refuse it).
        ``None`` for every other row: its icon is its state's
        (:meth:`_set_row_status`), a shape per state, never one shape for
        every step with its colour the only sign."""
        from qtpy.QtCore import Qt

        data = item.data(0, Qt.UserRole)
        locked = getattr(self, "_locked_rows", ())
        if isinstance(data, BuilderStep) and data.step_id in locked:
            return "lock"
        return None

    def _blank_icon(self):
        """A transparent icon of a row icon's size: a top-level row with no
        state to show keeps its text in line with its neighbours'."""
        from qtpy import QtCore, QtGui

        blank = getattr(self, "_blank_row_icon", None)
        if blank is None:
            pixmap = QtGui.QPixmap(16, 16)
            pixmap.fill(QtCore.Qt.transparent)
            blank = self._blank_row_icon = QtGui.QIcon(pixmap)
        return blank

    def _item_key(self, item):
        """What any row is across redraws: a top-level row's :meth:`_row_key`,
        an object row's with its object's name."""
        from qtpy.QtCore import Qt

        parent = item.parent()
        if parent is None:
            return (self._row_key(item),)
        data = item.data(0, Qt.UserRole)
        name = data.name if isinstance(data, BuilderObject) else item.text(COL_DESC)
        return (self._row_key(parent), name)

    def _save_tree_state(self):
        """Return the expanded rows, the selected ones and the scroll
        position, each row by what it shows (:meth:`_item_key`), for
        :meth:`_restore_tree_state` after a redraw."""
        tree = self.ui.tbl_steps
        expanded = set()
        for i in range(tree.topLevelItemCount()):
            item = tree.topLevelItem(i)
            if item.isExpanded():
                expanded.add(self._row_key(item))
        selected = {self._item_key(item) for item in tree.selectedItems()}
        scroll_val = tree.verticalScrollBar().value()
        return expanded, selected, scroll_val

    def _restore_tree_state(self, state):
        """Re-expand and re-select the rows of *state* that are still drawn,
        restore its scroll position, and show the selection's detail as the
        rows now say it (a redraw drew them anew)."""
        from qtpy import QtCore

        expanded, selected, scroll_val = state
        tree = self.ui.tbl_steps
        chosen = QtCore.QItemSelection()
        for i in range(tree.topLevelItemCount()):
            item = tree.topLevelItem(i)
            if self._row_key(item) in expanded:
                item.setExpanded(True)
            rows = [item] + [item.child(j) for j in range(item.childCount())]
            for row in rows if selected else ():
                if self._item_key(row) in selected:
                    index = tree.indexFromItem(row)
                    chosen.select(index, index)
        if not chosen.isEmpty():  # one selection change, not one per row
            flags = QtCore.QItemSelectionModel.Select | QtCore.QItemSelectionModel.Rows
            tree.selectionModel().select(chosen, flags)
        tree.verticalScrollBar().setValue(scroll_val)
        self._show_detail()

    #: What a chip's click offers, below its state in its tooltip.
    _CHIP_CLICK = "Click: turn it off or on here, its mode for every row, its editor."

    def _behavior_chips(self, obj, step_id: str = None) -> list:
        """*obj*'s Behaviors cell in *step_id*, a :class:`Chip` per behavior
        (the Unity manifest's design: coloured by its state, its own tooltip):
        each behavior's state as pythontk judges it from the shown assessment
        (``StepStatus.behavior_states``), led by its state's glyph and, set to
        Marker, the marker's (``ManifestData.MARKED_GLYPH``); one not in force
        here struck through.

        Parameters:
            step_id: Only that step's assessment is consulted -- the same
                object can appear in several steps with different statuses.
        """
        step = next(
            (r for r in self._last_results or () if r.step_id == step_id), None
        )
        marked = self._marked_behaviors()
        states = StepStatus.behavior_states(
            step,
            obj.name,
            obj.behaviors,
            sheet=(obj.sheet or {}).get("behaviors"),
            off=self._disabled_behaviors(),
            marked=marked,
        )
        chips = []
        for raw, state, words in states:
            color, mark, struck = ManifestData.chip_look(state)
            lead = [mark] if mark else []
            if raw in marked and not struck:
                lead.append(ManifestData.MARKED_GLYPH)
            text = " ".join(lead + [ManifestData.fmt_behavior(raw)])
            line = f"{text}  ({words})" if words else text
            tip = self._chip_tip(raw, text, color, words)
            chips.append(Chip(raw, text, state, line, tip, struck))
        return chips

    def _chip_tip(self, raw: str, text: str, color: Optional[str], words: str) -> str:
        """A chip's tooltip: the behavior as its chip says it, its state here
        in its colour, what Build does with it on every row, and what a click
        offers."""
        state = html.escape(words) if words else "not assessed yet (Assess shows it)"
        if color:
            state = f"<span style='color:{color}'>{state}</span>"
        modes = {value: label for label, value in self.BEHAVIOR_MODES}
        return ptk.TooltipFormat.fmt(
            title=html.escape(text),
            rows=[("Here", state), ("Every row", modes.get(self._behavior_mode(raw), ""))],
            hint=self._CHIP_CLICK,
        )

    def _make_behavior_chips(
        self, obj, tree, child_item, choices, step_id: str = None
    ) -> None:
        """The Behaviors cell of *obj*'s row as chips (:class:`BehaviorChips`):
        a click on one opens its own menu, ``+`` offers what *choices* (the
        object's kind's behaviors) it lacks. Every chip works alike."""
        chips = BehaviorChips()
        chips.setProperty("choices", list(choices))
        chips.chip_clicked.connect(
            lambda raw, pos, o=obj, s=step_id, w=chips: self._chip_menu(o, s, raw, pos, w)
        )
        chips.plus_clicked.connect(
            lambda pos, o=obj, s=step_id, w=chips: self._add_menu(o, s, pos, w)
        )
        self._color_behavior_chips(obj, chips, step_id=step_id)
        tree.setItemWidget(child_item, COL_BEHAVIORS, chips)

    def _color_behavior_chips(self, obj, chips, step_id: str = None) -> None:
        """Show *obj*'s chips by the latest assessment (:meth:`_behavior_chips`),
        in place; the ``+`` only while its kind has a behavior it lacks."""
        addable = [b for b in chips.property("choices") or () if b not in obj.behaviors]
        chips.set_chips(
            self._behavior_chips(obj, step_id),
            plus=bool(addable),
            plus_tip=ptk.TooltipFormat.fmt(
                title="Add a Behavior",
                body=f"Give <b>{html.escape(self.manifest_host.leaf_name(obj.name))}</b> a behavior "
                "the sheet does not.",
                hint="A Local Edit: kept with the scene, marked, reverted in one click.",
            ),
        )

    def _style_chips(self, tree) -> None:
        """The Behaviors cells' look (``BehaviorChips.style_sheet``), the
        Unity manifest's: each state's colour and border in this panel's
        palette as it is now (the Colors... editor's), the ``+`` in the
        locked grey until hovered, then the theme's text -- one style sheet
        on the cells' parent, the tree's viewport, set again only when it
        changed."""
        states = StepStatus.BEHAVIOR_STATES
        sheet = BehaviorChips.style_sheet(
            {s: ManifestData.chip_look(s)[0] for s in states},
            lines={s: ManifestData.chip_line(s) for s in states},
            quiet=ManifestData.status_color("locked") or "",
            text=self.sb.StyleSheet.resolve_variable("TEXT_COLOR", tree, ""),
        )
        viewport = tree.viewport()
        if viewport.styleSheet() != sheet:
            viewport.setStyleSheet(sheet)

    @staticmethod
    def _style_rows(tree) -> None:
        """The rows' grounds, the Unity manifest's: the step rows alternate,
        so a run of closed steps reads as bands; an object's row is darker,
        one flat band under its step (a row colour does not alternate); the
        Step and Behaviors columns stand a little darker still, the eye's two
        anchors across a row."""
        from qtpy.QtGui import QColor

        tree.set_row_height(20)  # even rows, a 16 px chip on each with room
        tree.setAlternatingRowColors(True)
        tree.setChildRowColor(QColor(0, 0, 0, 56))
        tree.clear_column_tints()
        tree.set_column_tint(COL_STEP, QColor(0, 0, 0, 36))
        tree.set_column_tint(COL_BEHAVIORS, QColor(0, 0, 0, 36))

    #: The Behaviors column's width bounds: its chips' width within them, a
    #: chip past the upper one elided.
    BEHAVIORS_WIDTH = (110, 320)

    def _behaviors_width(self, tree) -> int:
        """The Behaviors column's width: the widest cell's chips whole
        (``BehaviorChips.preferred_width``), within :attr:`BEHAVIORS_WIDTH`."""
        low, high = self.BEHAVIORS_WIDTH
        widest = 0
        for i in range(tree.topLevelItemCount()):
            parent = tree.topLevelItem(i)
            for j in range(parent.childCount()):
                cell = tree.itemWidget(parent.child(j), COL_BEHAVIORS)
                if isinstance(cell, BehaviorChips):
                    widest = max(widest, cell.preferred_width())
        return min(max(widest, low), high)

    def _refused(self, step_id: str) -> bool:
        """Whether a behavior edit of *step_id* is refused (the original sheet viewed, or the step locked)."""
        if self._editor.refuse_viewing():
            return True
        step = next((s for s in self._steps if s.step_id == step_id), None)
        return self._editor.refuse_locked(step)

    def _chip_menu(self, obj, step_id: str, raw: str, pos, parent) -> None:
        """One behavior's menu, the same for every chip: on or off for this
        object (a Local Edit), its mode for every row (Key / Marker / Off, kept
        with the scene), and the panel that edits how it is keyed.

        The Unity manifest's menu: a type Off for every row offers no
        per-object toggle (it would change nothing the chip shows); its mode
        is a build option, never a step edit, so a locked step or the original
        sheet refuses only the object's own items, when picked."""
        from qtpy import QtWidgets

        menu = QtWidgets.QMenu(parent)
        menu.setToolTipsVisible(True)
        self.sb.StyleSheet.cast_shadow(menu)
        leaf = self.manifest_host.leaf_name(obj.name)
        # Its mode is its family's (Fade for Fade · in): one choice sets them all.
        label = ManifestData.fmt_behavior(self.behaviors.family_of(raw))
        mode = self._behavior_mode(raw)
        if mode != "off":
            self._menu_section(menu, f"{ManifestData.fmt_behavior(raw)} on {leaf}")
            has = raw in obj.behaviors
            toggle = menu.addAction("Turn Off" if has else "Turn On")
            toggle.setToolTip(
                f"Leave it out for '{leaf}', or give it back: a Local Edit, kept, "
                "marked and reverted in one click."
            )
            want = [b for b in obj.behaviors if b != raw] if has else list(obj.behaviors) + [raw]
            toggle.triggered.connect(
                lambda _c=False: self._refused(step_id) or self._editor.set_behaviors(step_id, obj, want)
            )
        self._menu_section(menu, f"{label} on every row")
        choice = QtWidgets.QActionGroup(menu)
        for text, value in self.BEHAVIOR_MODES:
            act = menu.addAction(text)
            act.setCheckable(True)
            act.setChecked(value == mode)
            choice.addAction(act)
            act.setToolTip(self.BEHAVIOR_MODE_TIPS[value].format(label=label))
            act.triggered.connect(lambda _c=False, v=value: self._set_behavior_mode(raw, v))
        page = self.EFFECT_PAGES.get(self.behaviors.effect_of(raw))
        if page is not None:
            channel, verb = page
            menu.addSeparator()
            edit = menu.addAction(
                f"Edit {verb}\u2026",
                lambda _c=False: self._refused(step_id) or self._open_effect(step_id, obj, channel),
            )
            edit.setToolTip(f"Render Effects' {verb} page, on '{leaf}' alone: how Build keys it.")
        menu.aboutToHide.connect(menu.deleteLater)
        menu.popup(pos)

    def _behavior_about(self, raw: str) -> str:
        """What behavior *raw* does, as its template describes it (``""``:
        no template of that name)."""
        try:
            return str(self.behaviors.load_behavior(raw).get("description") or "")
        except (FileNotFoundError, OSError, ValueError):
            return ""

    def _add_menu(self, obj, step_id: str, pos, parent) -> None:
        """What *obj* can be given beyond what it has: its kind's behaviors,
        ticked as a checkbox list that stays open; what was ticked is one Local
        Edit as it closes."""
        if self._refused(step_id):
            return
        choices = [b for b in (parent.property("choices") or []) if b and b not in obj.behaviors]
        menu = self.sb.Menu(
            parent=parent,
            position="cursorPos",
            add_header=False,
            add_footer=False,
            hide_on_leave=True,
            fixed_item_height=20,
            match_parent_width=False,
        )
        menu.add("Separator", setTitle=f"Add to {self.manifest_host.leaf_name(obj.name)}")
        boxes = []  # the + shows only while there is one (_color_behavior_chips)
        for raw in choices:
            box = menu.add(
                "QCheckBox",
                setText=ManifestData.fmt_behavior(raw),
                setToolTip=self._behavior_about(raw),
            )
            box.setProperty("behavior_raw", raw)
            boxes.append(box)

        def _apply():
            added = [b.property("behavior_raw") for b in boxes if b.isChecked()]
            if added:
                self._editor.set_behaviors(step_id, obj, list(obj.behaviors) + added)

        menu.on_hidden.connect(_apply)
        # One menu per click, parented to the cell: else every click left a hidden menu behind.
        menu.on_hidden.connect(menu.deleteLater)
        menu.show()

    def _reapply_behavior(
        self, step_id: str, obj: BuilderObject, raise_errors: bool = False
    ) -> bool:
        """Re-apply every behavior of one object on its paired shot, as one
        undo step -- ``ShotManifest.reapply_object``: its previous keys out,
        the new ones recorded as the manifest's own.

        Parameters:
            raise_errors: Also raise why nothing was re-applied, for a caller
                that reports it itself (Render Effects' focused Key).

        Returns:
            Whether it was re-applied.  Why not goes on the footer: no shot
            pairs with the step yet, the scene holds no object of that name
            (or several), or an error.
        """
        try:
            store = self._active_store()
            shot = self._pairing().shots.get(step_id)
            if store is None or shot is None:
                problem = f"No shot pairs with '{step_id}' yet -- build first."
            else:
                with store.scene_edit("manifest_reapply"):
                    applied = self._manifest(store).reapply_object(shot, obj)
                if applied:
                    problem = None
                elif store.resolve_member(obj.name)[1] == "ambiguous":
                    problem = (
                        "Nothing re-applied: several scene objects are named "
                        f"'{obj.name}'."
                    )
                else:
                    problem = f"Nothing re-applied: '{obj.name}' is not in the scene."
            if problem is None:
                # Re-assess so the UI reflects the fixed state.  Skip the
                # selected-keys guard -- we just applied known behaviors and
                # only need a status refresh.
                self.assess(skip_key_check=True)
                return True
        except Exception as exc:
            self.logger.error("Apply behavior failed: %s", exc)
            self._set_footer(f"Error: {exc}", color=ERROR_COLOR)
            if raise_errors:
                raise
            return False
        self._set_footer(problem, color=ERROR_COLOR)
        if raise_errors:
            raise RuntimeError(problem)
        return False

    def _populate_table(self) -> None:
        """Fill the tree with the manifest's rows (``ShotPairing.rows``): a
        step row per step -- its objects, then the members of its shot it does
        not list -- and a "not in doc" row per shot no step pairs with, its
        members under it, where the timeline has it."""
        tree = self.ui.tbl_steps
        tree.clear()
        tree.setHeaderLabels(HEADERS)
        tree.setColumnCount(len(HEADERS))
        self._style_chips(tree)  # before the cells: each polishes once
        pairing = self._pairing()
        # The steps whose shot is locked: their rows draw a lock (_row_icon).
        self._locked_rows = self._locked_step_ids(pairing)

        _kind_cache: dict = {}
        steps_by_id = {s.step_id: s for s in self._steps}

        for step, shot in self._rows(pairing):
            if step is None:
                # A shot split off a step's shot shows that step's section.
                linked = steps_by_id.get(pairing.links.get(shot.shot_id))
                self._add_shot_row(tree, shot, section=self._section_text(linked))
                continue
            section = self._section_text(step)

            parent = tree.create_item(
                [step.shot_name, section, self._step_text(step), "", "", "", ""],
                data=step,
            )
            if pairing.how.get(step.step_id) == "order":
                parent.setToolTip(
                    COL_STEP,
                    f"Paired by timeline order with shot "
                    f"'{pairing.shots[step.step_id].name}'; Build records the pairing.",
                )
            # Child rows: object name in Description column, behavior label
            for obj in step.objects:
                child = tree.create_item(["", "", "", "", "", "", ""], data=obj, parent=parent)
                if obj.kind == "audio":
                    font = child.font(COL_DESC)
                    font.setItalic(True)
                    for c in range(tree.columnCount()):
                        child.setFont(c, font)
                self._show_name(tree, child, obj.name, _ORIGIN_NOTES.get(obj.origin, ""))
                if obj.kind not in _kind_cache:
                    _kind_cache[obj.kind] = list(
                        self.behaviors.list_behaviors(kind=obj.kind)
                    )
                self._make_behavior_chips(
                    obj, tree, child, _kind_cache[obj.kind], step.step_id
                )
            if shot is not None:
                self._add_member_rows(
                    tree, parent, shot, listed=[o.name for o in step.objects]
                )

        # Restrict editability: only Range column on parent rows, and only
        # for steps that aren't built yet — per row, not all-or-nothing,
        # so new steps added to a partially built CSV stay editable.
        from qtpy.QtCore import Qt as _Qt

        for i in range(tree.topLevelItemCount()):
            parent = tree.topLevelItem(i)
            step = parent.data(0, _Qt.UserRole)
            editable = (
                isinstance(step, BuilderStep) and step.step_id not in pairing.shots
            )
            if editable:
                parent.setFlags(parent.flags() | _Qt.ItemIsEditable)
            else:
                parent.setFlags(parent.flags() & ~_Qt.ItemIsEditable)
            for j in range(parent.childCount()):
                child = parent.child(j)
                child.setFlags(child.flags() & ~_Qt.ItemIsEditable)

        self._shown_pairing = self._pairing_key(pairing)

        # Restore user-entered range values that survive table rebuilds,
        # then the built rows' live ranges: the store is their truth.
        self._restore_user_ranges(tree)
        self._refresh_timing()
        for i in range(tree.topLevelItemCount()):
            parent = tree.topLevelItem(i)
            step = parent.data(0, _Qt.UserRole)
            if isinstance(step, BuilderStep) and not step.animated and step.step_id not in pairing.shots:
                self._draw_no_shot(parent)

        self._apply_formatting(tree)
        self._apply_row_tags(tree)
        tree.set_stretch_column(2)  # Stretch "Description" column
        tree.restore_column_state()  # Persist user header changes
        self._editor.decorate()
        # The header menu's Behaviors say the modes these rows are drawn by:
        # a sheet or a scene that keeps other ones changed them.
        self._sync_behavior_modes()
        if not self._last_results and any(self._sheet_issues(s) for s in self._steps or ()):
            self._mark_step_rows()  # what the sheet's own check found shows as it loads
        self._refresh_export_preview()  # an open one shows these rows

    @staticmethod
    def _section_text(step) -> str:
        """*step*'s Section cell -- ``"A: Title"``, or the bare section --
        ``""`` for no step."""
        if step is None:
            return ""
        if step.section_title:
            return f"{step.section}: {step.section_title}"
        return step.section

    def _add_shot_row(self, tree, shot, section: str = ""):
        """An italic, non-editable "not in doc" row for *shot* -- a shot no
        step pairs with -- its members under it; its context menu adds it to
        the manifest, pairs it with a step, or removes it.  *section*: the
        section of the step it was split off (``ShotPairing.links``).  Its
        status is marked with the rest (:meth:`_apply_formatting`)."""
        from qtpy.QtCore import Qt

        row = tree.create_item(
            [
                shot.name,
                section,
                shot.description or "",
                "",
                f"{shot.start:.0f}",
                f"{shot.end:.0f}",
                "",
            ],
            data=shot,
        )
        row.setFlags(row.flags() & ~Qt.ItemIsEditable)
        font = row.font(COL_STEP)
        font.setItalic(True)
        for c in range(tree.columnCount()):
            row.setFont(c, font)
        self._add_member_rows(tree, row, shot, in_step=False)
        return row

    def _add_member_rows(self, tree, parent, shot, listed=(), in_step=True) -> None:
        """A child row under *parent* per member of *shot* not among *listed*
        (names, compared by ``ShotStore.name_pairs``: ``PANEL|LATCH`` names
        its own latch, never ``DOOR|LATCH``): the shot's own
        objects, shown before any Assess -- italic, never editable; under a
        step (*in_step*) marked ``additional`` (:meth:`_set_row_status`): in
        the shot, not in the step.

        Each row's data is a ``BuilderObject`` of origin ``"member"``: the
        object rows' own actions (Outliner, Copy) reach it, Local Edits do
        not -- the sheet does not list it.
        """
        from qtpy.QtCore import Qt

        named = {member for _name, member in ptk.ShotStore.name_pairs(listed, shot.objects)}
        issues = [("additional", _ORIGIN_NOTES["member"])] if in_step else []
        for name in dict.fromkeys(shot.objects):
            if name in named:
                continue
            child = tree.create_item(
                ["", "", "", "", "", "", ""],
                data=BuilderObject(name=name, origin="member"),
                parent=parent,
            )
            child.setFlags(child.flags() & ~Qt.ItemIsEditable)
            font = child.font(COL_DESC)
            font.setItalic(True)
            for c in range(tree.columnCount()):
                child.setFont(c, font)
            self._show_name(tree, child, name)
            if issues:
                self._set_row_status(child, issues)

    def _step_items(self, step_ids) -> list:
        """The step rows of *step_ids*, in table order."""
        from qtpy.QtCore import Qt

        wanted = set(step_ids)
        tree = self.ui.tbl_steps
        items = []
        for i in range(tree.topLevelItemCount()):
            item = tree.topLevelItem(i)
            step = item.data(0, Qt.UserRole)
            if isinstance(step, BuilderStep) and step.step_id in wanted:
                items.append(item)
        return items

    def _apply_row_tags(self, tree) -> None:
        """Colour the step rows: the user's tags (the scene's, for the loaded
        sheet) over the template's automatic ``color_by``; an object row
        shows its step's (``RowTags`` inheritance).  A "not in doc" row takes
        the automatic colour of the step row above it: it sits inside that
        span of the timeline, and a gap in the strip there read as a section
        boundary."""
        from qtpy.QtCore import Qt

        tags = self._row_tags
        user = ptk.ManifestTags.read(self._active_store(), self._editor.source_key)
        rule = (self._active_mapping or {}).get("color_by", "none")
        auto = ptk.ManifestTags.auto(
            [*self._sheet_steps, *self._steps], rule, tags.slots
        )
        above = None
        for i in range(tree.topLevelItemCount()):
            item = tree.topLevelItem(i)
            step = item.data(0, Qt.UserRole)
            if not isinstance(step, BuilderStep):
                if above:
                    tags.set_tag([item], above, auto=True)
                continue
            if step.step_id in user:
                tags.set_tag([item], user[step.step_id])
            above = auto.get(step.step_id)
            if above:
                tags.set_tag([item], above, auto=True)

    def _apply_formatting(self, tree) -> None:
        """Set column/row tints, behavior colors, icons, and column widths."""
        from qtpy.QtCore import Qt

        content_col = COL_DESC

        # Row tints via delegate (fillRect bypasses the host's QSS stripping).
        self._style_rows(tree)

        # Icons: none yet on a step (its state's, once assessed; a lock where
        # locked) -- a "not in doc" row's marked as such
        # -- and a type-coded icon on child Content column.
        not_in_doc = [("not_in_doc", StepStatus.HELP["not_in_doc"])]
        for i in range(tree.topLevelItemCount()):
            parent = tree.topLevelItem(i)
            step = parent.data(0, Qt.UserRole)
            self._set_row_status(
                parent,
                [] if isinstance(step, BuilderStep) else not_in_doc,
                icon=self._row_icon(parent),
                top=True,
            )
            for j in range(parent.childCount()):
                child = parent.child(j)
                obj_name = child.text(content_col)
                if not obj_name:
                    continue
                obj_data = child.data(0, Qt.UserRole)
                icon = self.manifest_host.object_icon(obj_data, obj_name)
                if icon is not None:
                    child.setIcon(content_col, icon)
                else:
                    # Neutral grey before assessment; assessment will repaint
                    # with the actual status color if there's a problem.
                    tree.set_item_type_icon(
                        child, "close", column=content_col, color=STEP_ICON_COLOR
                    )

        # Column widths
        header = tree.header()
        header.setMinimumSectionSize(60)
        header.resizeSection(COL_STEP, 140)
        header.resizeSection(COL_BEHAVIORS, self._behaviors_width(tree))
        header.resizeSection(COL_START, 55)
        header.resizeSection(COL_END, 55)
        header.resizeSection(COL_STATUS, 110)

        # Run registered formatters
        tree.apply_formatting()

    def _set_row_status(
        self, item, issues, icon=None, label=None, quiet=None, top=False
    ) -> None:
        """Mark *item*'s row with its *issues* -- ``(status, text)`` pairs --
        the one status signal a row carries: its icon in the Step column, the
        worst issue's shape in its colour (``ManifestData.LEVEL_ICONS``;
        *icon*: a shape the row has whatever it says, a lock), that issue in
        a few words in the Status column (*label*, else
        ``StepStatus.LABELS``'; plain text: the icon alone carries the
        colour, nothing is tinted), and a row tooltip on every cell listing
        them all, a coloured glyph before each
        (``TreeWidget.set_row_tooltip``).  No issues: *quiet*'s icon, neutral
        (a row judged and found in order), else none -- a *top*-level row
        keeps an icon's place, so the steps' text stays in line -- no words
        and no row tooltip."""
        from qtpy import QtCore, QtGui

        tree = self.ui.tbl_steps
        worst = ManifestData.worst(status for status, _text in issues)
        if icon is None:
            icon = (
                ManifestData.LEVEL_ICONS.get(ManifestData.level(worst))
                if worst is not None
                else quiet
            )
        if icon:  # uitk's icon of that name (IconManager), in the state's colour
            color = ManifestData.status_color(worst) if worst else None
            if color is None:  # judged and in order: the check's green
                color = ManifestData.status_color("success") if icon == "check" else STEP_ICON_COLOR
            tree.set_item_icon(item, icon, color=color)
        else:
            item.setIcon(COL_STEP, self._blank_icon() if top else QtGui.QIcon())
            # And the icon a theme change would draw again, which uitk keeps
            # under this role (TreeWidget.set_item_icon) and has no public
            # call to clear.
            item.setData(COL_STEP, QtCore.Qt.UserRole + 100, None)
        tree.set_row_tooltip(item, ManifestData.issues_html(issues) or None)
        words = (label or ManifestData.label(worst)) if worst else ""
        blocked = tree.blockSignals(True)  # a mark, never an edit of the row
        try:
            item.setText(COL_STATUS, words)
        finally:
            tree.blockSignals(blocked)

    def _mark_step_row(self, item, step_status=None) -> None:
        """Mark a step row (:meth:`_set_row_status`) with what the shown
        assessment found (*step_status*; ``None``: none) and with its
        range's collisions (``_range_issues``, the Start / End column's)."""
        from qtpy.QtCore import Qt

        step = item.data(0, Qt.UserRole)
        # Not assessed yet: what the sheet's own check found is known as the sheet loads.
        issues = self._step_issues(step_status) if step_status is not None else self._sheet_issues(step)
        ranges = self._range_issues.get(step.step_id, [])
        # The step's own words ("2 not in scene") unless its range collides:
        # that is the row's worst then, and says so.
        own = step_status.label if step_status is not None and not ranges else ""
        self._set_row_status(
            item,
            issues + ranges,
            icon=self._row_icon(item),
            label=own or None,
            # Judged and nothing to say: a check; not judged yet, or a step
            # with no shot (nothing to judge but its objects): no state.
            quiet=(
                "check"
                if step_status is not None and step_status.status != "no_shot"
                else None
            ),
            top=True,
        )

    def _mark_step_rows(self) -> None:
        """Mark every step row (:meth:`_mark_step_row`) from the shown
        assessment and the range collisions."""
        from qtpy.QtCore import Qt

        tree = self.ui.tbl_steps
        results = {r.step_id: r for r in self._last_results or ()}
        for i in range(tree.topLevelItemCount()):
            item = tree.topLevelItem(i)
            step = item.data(0, Qt.UserRole)
            if isinstance(step, BuilderStep):
                self._mark_step_row(item, results.get(step.step_id))
        self._show_detail()  # a selected row says what it says now

    @staticmethod
    def _behavior_names(names) -> str:
        return ", ".join(ManifestData.fmt_behavior(b) for b in names)

    @staticmethod
    def _sheet_issues(step) -> list:
        """What the sheet's own check found in *step* (``BuilderStep.sheet_issues``), as a row's
        ``(status, text)`` issues; none for a row that is no sheet step's."""
        said = getattr(step, "sheet_issues", None)
        return list(said()) if callable(said) else []

    def _sheet_issue_note(self) -> str:
        """What the loaded sheet's check found, counted for the footer (``""``: nothing)."""
        found = [status for step in self._steps or () for status, _text in self._sheet_issues(step)]
        errors, warnings = found.count("sheet"), found.count("sheet_warning")
        parts = [f"{n} {word}{'s' if n != 1 else ''}" for n, word in ((errors, "issue"), (warnings, "warning")) if n]
        return f"The sheet has {' and '.join(parts)}: hover a marked step." if parts else ""

    def _step_issues(self, step_status) -> list:
        """A step row's ``(status, text)`` issues (:meth:`_set_row_status`):
        its own status, then each object with a behavior issue, and what a
        Build changes besides."""
        r = step_status
        issues = []
        groups: dict = {}  # an object status -> the objects at it
        for o in r.objects:
            if o.status != "valid" and o.status not in _BEHAVIOR_ISSUES:
                groups.setdefault(o.status, []).append(o.name)
        if (
            r.status in StepStatus.HELP
            and r.status not in groups
            and r.status not in _BEHAVIOR_ISSUES
        ):
            issues.append((r.status, StepStatus.HELP[r.status]))  # the step's own
        issues.extend(r.sheet)  # each cell the sheet's check names, with its fix
        for status, names in groups.items():
            if status in StepStatus.HELP:
                issues.append(
                    (status, f"{', '.join(names)}: {StepStatus.HELP[status]}")
                )
        for o in r.objects:
            if o.status not in _BEHAVIOR_ISSUES:
                continue
            names = o.broken_behaviors or o.stale_behaviors or o.behaviors
            word = _BEHAVIOR_WORDS[o.status]
            issues.append((o.status, f"{o.name}: {self._behavior_names(names)} {word}"))
        if r.dropped_behaviors:
            dropped = ", ".join(
                f"{name} \u2192 {ManifestData.fmt_behavior(b)}"
                for name, b in r.dropped_behaviors
            )
            issues.append(
                (
                    "dropped_behavior",
                    f"Keys of dropped behaviors -- Build removes them: {dropped}",
                )
            )
        if r.additional_objects:
            extra = ", ".join(r.additional_objects)
            issues.append(("additional", f"In the shot, not in the manifest: {extra}"))
        if r.updates:
            done = " and ".join(StepStatus.UPDATES[u] for u in r.updates)
            issues.append(("shot_update", f"Build {done}."))
        if r.shrinkable_frames > 0:
            issues.append(("valid", f"{r.shrinkable_frames:.0f}f unused"))
        return issues

    def _object_issues(self, obj_st) -> list:
        """An object row's ``(status, text)`` issues (:meth:`_set_row_status`)."""
        status = obj_st.status
        if status == "missing_object":
            return [
                (
                    status,
                    f"Not found in {self.manifest_host.APP} -- an artist's to add; "
                    "Build never creates objects.",
                )
            ]
        if status == "missing_behavior":
            lines = []
            for b in obj_st.broken_behaviors or obj_st.behaviors:
                entry = ManifestData.fmt_behavior(b)
                try:
                    desc = self.behaviors.load_behavior(b).get("description", "")
                except Exception:
                    desc = ""
                lines.append(f"{entry} \u2014 {desc}" if desc else entry)
            return [(status, "Not verified:\n" + "\n".join(lines))]
        if status == "user_animated" and obj_st.key_range:
            lo, hi = obj_st.key_range
            return [(status, f"User-animated: keys {lo:.0f}-{hi:.0f}")]
        if status in StepStatus.HELP:
            return [(status, StepStatus.HELP[status])]
        return []

    def _apply_assessment(self, results: list) -> None:
        """Mark each row with what the assessment found (:meth:`_set_row_status`:
        an icon and a row tooltip, nothing tinted), count the step's behavior
        issues in its Behaviors cell, and add the objects animating in a
        step's shot that it neither lists nor holds."""
        from qtpy.QtCore import Qt

        tree = self.ui.tbl_steps
        col_count = tree.columnCount()
        content_col = COL_DESC
        beh_col = COL_BEHAVIORS

        status_map = {r.step_id: r for r in results}
        for i in range(tree.topLevelItemCount()):
            parent = tree.topLevelItem(i)
            step_data = parent.data(0, Qt.UserRole)
            if not isinstance(step_data, BuilderStep):
                continue
            step_status = status_map.get(step_data.step_id)
            # Every step row, once: one this assessment did not judge (shown
            # since) still says its range's collisions.
            self._mark_step_row(parent, step_status)
            if step_status is None:
                continue

            # The Behaviors cell counts the objects with a behavior issue.
            counts: dict = {}
            for o in step_status.objects:
                if o.status in _BEHAVIOR_ISSUES:
                    word = _BEHAVIOR_WORDS[o.status]
                    counts[word] = counts.get(word, 0) + 1
            if counts:
                parent.setText(
                    beh_col, ", ".join(f"{n} {word}" for word, n in counts.items())
                )

            obj_status_map = {o.name: o for o in step_status.objects}
            for j in range(parent.childCount()):
                child = parent.child(j)
                child_data = child.data(0, Qt.UserRole)
                if not isinstance(child_data, BuilderObject):
                    continue
                obj_st = obj_status_map.get(child_data.name)
                if obj_st is None:
                    continue
                if obj_st.behaviors:
                    beh_widget = tree.itemWidget(child, beh_col)
                    if beh_widget is not None:
                        self._color_behavior_chips(
                            child_data, beh_widget, step_id=step_status.step_id
                        )
                if obj_st.status == "valid":
                    # Re-resolve icon: initial formatting may have set a
                    # fallback X because the node didn't exist yet
                    # (common for audio clips before build).
                    icon = self.manifest_host.object_icon(child_data, child.text(content_col))
                    if icon is not None:
                        child.setIcon(content_col, icon)
                self._set_row_status(child, self._object_issues(obj_st))

            # Additional objects (in shot but not in CSV): the shot's members
            # are listed already (_add_member_rows); what animates in its
            # range without being one is added.
            listed = [
                parent.child(j).data(0, Qt.UserRole).name
                for j in range(parent.childCount())
                if isinstance(parent.child(j).data(0, Qt.UserRole), BuilderObject)
            ]
            named = {m for _n, m in ptk.ShotStore.name_pairs(listed, step_status.additional_objects)}
            extras = [n for n in step_status.additional_objects if n not in named]
            for extra_name in extras:
                extra_item = tree.create_item(["", "", "", "", "", "", ""], parent=parent)
                self._show_name(tree, extra_item, extra_name)
                font = extra_item.font(content_col)
                font.setItalic(True)  # not the manifest's: set apart, untinted
                for c in range(col_count):
                    extra_item.setFont(c, font)
                icon = self.manifest_host.object_icon(None, extra_name)
                if icon is not None:
                    extra_item.setIcon(content_col, icon)
                self._set_row_status(
                    extra_item,
                    [
                        (
                            "additional",
                            "Animates in the shot's range, but neither the "
                            "manifest nor the shot lists it.",
                        )
                    ],
                )

        self._editor.decorate()
        self._apply_issues_filter()
        self._refresh_export_preview()  # an open one shows these rows
        self._show_detail()  # a selected row says what it says now

    def _quiet_rows(self) -> list:
        """The step rows with nothing to say -- what the Issues view hides
        (:meth:`_apply_issues_filter`), none before an Assess: the assessment
        reports nothing of the step (``StepStatus.quiet``), its range
        collides with none, its shot holds no member it does not list, and no
        Local Edit changed it. What the row says decides, not whether Build
        has work: an unlisted object says something."""
        from qtpy.QtCore import Qt

        results = {r.step_id: r for r in self._last_results or ()}
        tree = self.ui.tbl_steps
        quiet = []
        for i in range(tree.topLevelItemCount()):
            item = tree.topLevelItem(i)
            step = item.data(0, Qt.UserRole)
            if not isinstance(step, BuilderStep):
                continue  # a shot the sheet lacks always shows
            judged = results.get(step.step_id)
            if judged is None or not judged.quiet:
                continue
            if self._range_issues.get(step.step_id):
                continue
            members = (item.child(j).data(0, Qt.UserRole) for j in range(item.childCount()))
            if any(isinstance(m, BuilderObject) and m.origin == "member" for m in members):
                continue  # in its shot, not in the step: marked
            if self._editor.is_edited(step):
                continue  # a redline shows
            quiet.append(item)
        return quiet

    def _apply_issues_filter(self) -> int:
        """Hide the rows with nothing to say while the Issues view is on (Hide
        > Steps With Nothing to Do), and those the search field's words do not
        match; show every row otherwise. The number the Issues view hid. A view
        alone: no step leaves Assess or Build for it."""
        tree = self.ui.tbl_steps
        quiet = self._quiet_rows() if self._issues_only else []
        hidden = {id(item) for item in quiet}
        words = self._search_words()
        columns = tree.columnCount()
        for i in range(tree.topLevelItemCount()):
            item = tree.topLevelItem(i)
            found = not words or all(w in self._row_words(item, columns) for w in words)
            item.setHidden(id(item) in hidden or not found)
        return len(quiet)

    def _issue_ids(self) -> set:
        """The steps the shown assessment found something in: Build has work
        there, or its status is not valid."""
        return {
            r.step_id
            for r in self._last_results or ()
            if r.needs_build or r.status not in ("valid", "locked")
        }

    def _extra_rows(self) -> list:
        """The step rows holding an object the step does not list -- a member
        of its shot, or one animating in its range (once assessed)."""
        from qtpy.QtCore import Qt

        tree = self.ui.tbl_steps
        rows = []
        for i in range(tree.topLevelItemCount()):
            row = tree.topLevelItem(i)
            if not isinstance(row.data(0, Qt.UserRole), BuilderStep):
                continue
            for j in range(row.childCount()):
                data = row.child(j).data(0, Qt.UserRole)
                if not isinstance(data, BuilderObject) or data.origin == "member":
                    rows.append(row)
                    break
        return rows

    def expand_missing(self) -> None:
        """Expand the step rows the shown assessment found something in
        (Expand > Rows with Issues); what it found goes to the log."""
        if not self._last_results:
            self._set_footer("Assess first to find the issues.")
            return
        ids = self._issue_ids()
        if not ids:
            self._set_footer("No issues found.")
            return
        lines = [
            f"  {r.step_id}: {'; '.join(text for _s, text in self._step_issues(r))}"
            for r in self._last_results
            if r.step_id in ids
        ]
        self.logger.info("Expand Missing (%d steps):\n%s", len(lines), "\n".join(lines))
        self._set_footer(f"{len(ids)} step(s) with issues expanded.")
        for item in self._step_items(ids):
            item.setExpanded(True)

    def expand_extra(self) -> None:
        """Expand the step rows holding an object the step does not list
        (Expand > Rows with Objects Not in the Manifest)."""
        rows = self._extra_rows()
        if not rows:
            self._set_footer("No step's shot holds an object it does not list.")
            return
        for row in rows:
            row.setExpanded(True)
        self._set_footer(
            f"{len(rows)} step(s) with objects not in the manifest expanded."
        )
