# !/usr/bin/python
# coding=utf-8
"""Rename the panel's target in place: the target field, and the footer in
compact view."""

from qtpy import QtCore


class InlineRename(QtCore.QObject):
    """Double-click-to-rename on a read-only line edit.

    The field shows the target's name read-only. A double-click (when there is
    a target) makes it editable; Enter commits through *on_rename*, Escape puts
    the name back. Committing an unchanged name renames nothing. Watches the
    field as an event filter, so the field's own handlers stay its own.

    Parameters:
        line_edit (QLineEdit): The field (the panel's ``txt001``).
        target_name (callable): ``(full=False) -> str | None``: the target's
            name (leaf, or full path with *full*); ``None`` for no target.
        on_rename (callable): Called with the new name.
    """

    IDLE_TIP = "Double-click to rename."

    def __init__(self, line_edit, target_name, on_rename):
        super().__init__()
        self.field = line_edit
        self._target_name = target_name
        self._on_rename = on_rename
        line_edit.setPlaceholderText("No selection")
        line_edit.setToolTip(self.IDLE_TIP)
        line_edit.setReadOnly(True)
        line_edit.editingFinished.connect(self._finished)
        line_edit.installEventFilter(self)

    def eventFilter(self, watched, event) -> bool:
        """The field's double-click (start an edit) and Escape (end one)."""
        if watched is self.field:
            etype = event.type()
            if etype == QtCore.QEvent.MouseButtonDblClick:
                return self._double_click()
            if etype == QtCore.QEvent.KeyPress and event.key() == QtCore.Qt.Key_Escape:
                return self._escape()
        return super().eventFilter(watched, event)

    def _double_click(self) -> bool:
        """Make the field editable when there is a target; True when it did
        (the field's own double-click is then skipped)."""
        field = self.field
        full = self._target_name(full=True)
        if not field.isReadOnly() or full is None:
            return False
        field.setReadOnly(False)
        field.setToolTip(f"{full}\n\n(Type a new name and press Enter to rename.)")
        field.selectAll()
        field.setFocus()
        return True

    def _escape(self) -> bool:
        """Put the name back and leave editing; True when an edit was under way."""
        field = self.field
        if field.isReadOnly():
            return False
        name = self._target_name()
        if name is not None:
            was_blocked = field.blockSignals(True)
            field.setText(name)
            field.blockSignals(was_blocked)
        field.setReadOnly(True)
        field.setToolTip(self.IDLE_TIP)
        return True

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
    """An inline rename on a uitk ``Footer``, through its public in-place edit.

    Compact view hides the target field and shows the name in the footer; a
    double-click on the footer's text (``Footer.status_double_clicked``, when
    *can_edit*) edits the name there (``Footer.edit_status``): Enter renames
    through *on_rename*, an unchanged name calls *on_unchanged*, Escape puts the
    footer's text back.

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
        footer.status_double_clicked.connect(self._double_clicked)

    def _double_clicked(self):
        if self._can_edit():
            self.edit()

    def edit(self):
        """Edit the target's name in the footer; returns the footer's field."""
        return self.footer.edit_status(
            self._target_name() or "", on_commit=self._finished
        )

    def _finished(self, text):
        old = self._target_name()
        if old is None:
            return
        new = text.strip()
        if not new or new == old:
            self._on_unchanged()
            return
        self._on_rename(new)
