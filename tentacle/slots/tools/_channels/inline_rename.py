# !/usr/bin/python
# coding=utf-8
"""Rename the panel's target in place: the target field, and the footer in
compact view."""

from qtpy import QtCore, QtWidgets


class InlineRename:
    """Double-click-to-rename on a read-only line edit.

    The field shows the target's name read-only. A double-click (when there is
    a target) makes it editable; Enter commits through *on_rename*, Escape puts
    the name back. Committing an unchanged name renames nothing.

    Parameters:
        line_edit (QLineEdit): The field (the panel's ``txt001``).
        target_name (callable): ``(full=False) -> str | None``: the target's
            name (leaf, or full path with *full*); ``None`` for no target.
        on_rename (callable): Called with the new name.
    """

    IDLE_TIP = "Double-click to rename."

    def __init__(self, line_edit, target_name, on_rename):
        self.field = line_edit
        self._target_name = target_name
        self._on_rename = on_rename
        line_edit.setPlaceholderText("No selection")
        line_edit.setToolTip(self.IDLE_TIP)
        line_edit.setReadOnly(True)
        line_edit.editingFinished.connect(self._finished)
        self._orig_double_click = line_edit.mouseDoubleClickEvent
        self._orig_key_press = line_edit.keyPressEvent
        line_edit.mouseDoubleClickEvent = self._double_click
        line_edit.keyPressEvent = self._key_press

    def _double_click(self, event):
        field = self.field
        full = self._target_name(full=True)
        if field.isReadOnly() and full is not None:
            field.setReadOnly(False)
            field.setToolTip(f"{full}\n\n(Type a new name and press Enter to rename.)")
            field.selectAll()
            field.setFocus()
            return
        self._orig_double_click(event)

    def _key_press(self, event):
        field = self.field
        if event.key() == QtCore.Qt.Key_Escape and not field.isReadOnly():
            name = self._target_name()
            if name is not None:
                was_blocked = field.blockSignals(True)
                field.setText(name)
                field.blockSignals(was_blocked)
            field.setReadOnly(True)
            field.setToolTip(self.IDLE_TIP)
            return
        self._orig_key_press(event)

    def _finished(self):
        field = self.field
        # Back to display mode first: Enter and the focus loss after it both
        # emit editingFinished, and only the first may rename.
        was_editing = not field.isReadOnly()
        field.setReadOnly(True)
        field.setToolTip(self.IDLE_TIP)
        if not was_editing:
            return
        old = self._target_name()
        new = field.text().strip()
        if old is None or not new or new == old:
            return
        self._on_rename(new)


class FooterRename:
    """An inline rename page on a uitk ``Footer``.

    Compact view hides the target field and shows the name in the footer; a
    double-click on the footer's label (when *can_edit*) swaps in a line edit,
    Enter renames through *on_rename*, Escape (or an unchanged name) goes back
    to the label. Touches the footer's private stack and label, so a uitk
    change there degrades to no footer rename rather than an error.

    Parameters:
        footer: The panel's footer.
        can_edit (callable): ``() -> bool``: whether a double-click renames.
        target_name (callable): ``() -> str | None``: the name to edit.
        on_rename (callable): Called with the new name.
        on_unchanged (callable): Called when the edit ends with no change
            (the footer's label shows its text again).
    """

    def __init__(self, footer, can_edit, target_name, on_rename, on_unchanged):
        self.footer = footer
        self._can_edit = can_edit
        self._target_name = target_name
        self._on_rename = on_rename
        self._on_unchanged = on_unchanged
        self.line_edit = QtWidgets.QLineEdit()
        self.line_edit.setFrame(False)
        self.line_edit.setStyleSheet(
            "QLineEdit { background: transparent; border: none; }"
        )
        stack = footer._stacked_widget
        stack.addWidget(self.line_edit)
        self.page = stack.indexOf(self.line_edit)
        self.line_edit.editingFinished.connect(self._finished)
        self._orig_key_press = self.line_edit.keyPressEvent
        self.line_edit.keyPressEvent = self._key_press
        label = footer._status_label
        self._orig_double_click = label.mouseDoubleClickEvent
        label.mouseDoubleClickEvent = self._double_click

    def _show_label(self):
        try:
            self.footer._stacked_widget.setCurrentIndex(0)
        except Exception:  # noqa: BLE001 -- the footer is going away
            pass

    def _double_click(self, event):
        if self._can_edit():
            self.edit()
            return
        self._orig_double_click(event)

    def edit(self):
        """Swap the footer's label for the line edit, holding the name."""
        le = self.line_edit
        was_blocked = le.blockSignals(True)
        le.setText(self._target_name() or "")
        le.blockSignals(was_blocked)
        self.footer._stacked_widget.setCurrentIndex(self.page)
        le.selectAll()
        le.setFocus()

    def _key_press(self, event):
        le = self.line_edit
        if event.key() == QtCore.Qt.Key_Escape:
            # Blocked, so the focus loss does not emit editingFinished and
            # commit the very rename Escape cancels.
            le.blockSignals(True)
            self._show_label()
            le.clearFocus()
            le.blockSignals(False)
            return
        self._orig_key_press(event)

    def _finished(self):
        self._show_label()
        old = self._target_name()
        if old is None:
            return
        new = self.line_edit.text().strip()
        if not new or new == old:
            self._on_unchanged()
            return
        self._on_rename(new)
