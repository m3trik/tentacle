# !/usr/bin/python
# coding=utf-8
"""The value cell of an enum attribute: its labels in a combobox, plus Rename /
Add / Delete actions on its fields."""


class EnumCell:
    """Builds an enum row's value-cell combobox.

    The combobox carries what its handlers need as Qt properties:
    ``_attr_name`` (the row's attribute) and ``_enum_indices`` (the stored
    index behind each label, which need not run 0, 1, 2 ...).
    """

    #: The persistent actions under the labels: (label, icon).
    ACTIONS = (("Rename", "edit"), ("Add", "add"), ("Delete", "trash"))

    @classmethod
    def build(cls, sb, attr_name, labels, indices, current, on_activated, on_action):
        """A combobox showing *labels* with *current* (a stored index) chosen.

        Parameters:
            sb: The switchboard (``WidgetComboBox``, ``IconManager``).
            attr_name (str): The row's attribute.
            labels (list[str]): The enum's labels, in order.
            indices (list[int]): The stored index behind each label.
            current: The attribute's stored index now.
            on_activated (callable): ``(combo, position)`` when the user picks a
                label (``activated``: never a programmatic index change).
            on_action (callable): ``(combo, action)`` for Rename / Add / Delete.

        Returns:
            The combobox.
        """
        combo = sb.WidgetComboBox()
        combo.setSizeAdjustPolicy(combo.SizeAdjustPolicy.AdjustToContents)
        combo.setStyleSheet(
            "QComboBox { padding: 0; margin: 0; border: none; }"
            "QComboBox::drop-down { subcontrol-position: right center; }"
        )
        combo.add(labels)
        actions = combo.actions.add(
            {
                label: (lambda checked=False, a=label: on_action(combo, a))
                for label, _icon in cls.ACTIONS
            }
        )
        try:
            for action, (_label, icon) in zip(actions, cls.ACTIONS):
                action.setIcon(sb.IconManager.get(icon, size=(14, 14)))
            combo.actions.refresh()  # the buttons show the icons set after add
        except Exception:  # noqa: BLE001 -- icons are cosmetic
            pass
        indices = list(indices)
        combo.setCurrentIndex(indices.index(current) if current in indices else 0)
        combo.setProperty("_attr_name", attr_name)
        combo.setProperty("_enum_indices", indices)
        # ``activated`` (user picks only), not ``currentIndexChanged``: a
        # programmatic change or the widget's removal must not re-enter.
        combo.activated.connect(lambda position: on_activated(combo, position))
        return combo

    @staticmethod
    def show_index(combo, index):
        """Show stored *index* in *combo* without firing its handlers."""
        indices = combo.property("_enum_indices") or []
        was_blocked = combo.blockSignals(True)
        try:
            combo.setCurrentIndex(indices.index(index) if index in indices else 0)
        finally:
            combo.blockSignals(was_blocked)
