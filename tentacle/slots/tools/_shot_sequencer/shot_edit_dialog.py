# !/usr/bin/python
# coding=utf-8
"""The Shot Sequencer's small shot dialog: :class:`ShotEditDialog`.

Plain Qt widgets, no host and no uitk: a name / start / end / description form
that refuses a name the target store would refuse.
"""

import pythontk as ptk
from qtpy import QtWidgets


class ShotEditDialog:
    """Lightweight dialog for creating or editing a shot.

    Returns ``(name, start, end, description)`` on accept, ``None`` on cancel.
    """

    @staticmethod
    def show(
        parent=None,
        name: str = "",
        start: float = 1.0,
        end: float = 100.0,
        description: str = "",
        title: str = "Shot",
        validate=None,
    ):
        """Show a modal dialog and return the result tuple or ``None``.

        Parameters:
            parent: The dialog's parent widget.
            name: The name field's initial text.
            start: The start field's initial frame.
            end: The end field's initial frame.
            description: The description field's initial text.
            title: The window title.
            validate: ``(name) -> reason or None`` -- the target store's
                :meth:`~pythontk.ShotStore.name_error`: while it has a reason
                the dialog shows it and will not accept, so a name the export
                would respell or a taken one never reaches the store.  Without
                it the dialog still enforces the clip-name rule (an empty
                store's ``name_error``); only a store can refuse a taken name.

        Returns:
            ``(name, start, end, description)`` -- the name as typed, the
            description stripped -- or ``None`` when cancelled.
        """
        if validate is None:
            validate = ptk.ShotStore().name_error
        dlg = QtWidgets.QDialog(parent)
        dlg.setWindowTitle(title)
        dlg.setMinimumWidth(280)

        layout = QtWidgets.QFormLayout(dlg)
        layout.setContentsMargins(12, 12, 12, 12)

        name_edit = QtWidgets.QLineEdit(name)
        name_edit.setPlaceholderText("Shot name")
        name_edit.setToolTip(
            f"Exported as the clip name: {ptk.ShotStore.NAME_RULE}, "
            "unique ignoring case."
        )
        layout.addRow("Name:", name_edit)
        name_error = QtWidgets.QLabel()
        name_error.setWordWrap(True)
        name_error.setStyleSheet(f"color: {ptk.SHOT_PALETTE['error'][0]};")
        layout.addRow(name_error)

        start_spin = QtWidgets.QDoubleSpinBox()
        start_spin.setDecimals(1)
        start_spin.setRange(-1e6, 1e6)
        start_spin.setValue(start)
        layout.addRow("Start:", start_spin)

        end_spin = QtWidgets.QDoubleSpinBox()
        end_spin.setDecimals(1)
        end_spin.setRange(-1e6, 1e6)
        end_spin.setValue(end)
        layout.addRow("End:", end_spin)

        desc_edit = QtWidgets.QLineEdit(description)
        desc_edit.setPlaceholderText("Optional description")
        layout.addRow("Description:", desc_edit)

        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)
        layout.addRow(buttons)
        ok_button = buttons.button(QtWidgets.QDialogButtonBox.Ok)

        def _check_name(text):
            error = validate(text)
            name_error.setText(error or "")
            name_error.setVisible(bool(error))
            ok_button.setEnabled(not error)

        name_edit.textChanged.connect(_check_name)
        _check_name(name_edit.text())

        if dlg.exec_() != QtWidgets.QDialog.Accepted:
            return None

        return (
            name_edit.text(),
            start_spin.value(),
            end_spin.value(),
            desc_edit.text().strip(),
        )
