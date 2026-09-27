# !/usr/bin/python
# coding=utf-8
"""Behavior shared by the Maya and Blender ``nurbs`` panels.

The Nurbs expandable list's tree build (each fork's ``_LIST000_COMMANDS``).
"""


class NurbsMixin:
    """Shared ``nurbs`` panel behavior. Mixed in ahead of the DCC Slots base."""

    def list000_init(self, widget):
        """Initialize the Nurbs expandable list (root -> category -> curve action),
        from the fork's ``_LIST000_COMMANDS`` (MEL strings in Maya, bpy ops in
        Blender)."""
        widget.fixed_item_height = 18
        widget.apply_preset(
            "expand_overlay" if widget.ui.has_tags("submenu") else "hover_menu"
        )

        root = widget.add("Nurbs")

        for category, items in self._LIST000_COMMANDS.items():
            cat = root.sublist.add(category)
            cat.sublist.add([label for label, _ in items])
