# !/usr/bin/python
# coding=utf-8
"""Behavior shared by the Maya and Blender ``duplicate`` panels.

The header menu of tool-panel launchers.
"""


class DuplicateMixin:
    """Shared ``duplicate`` panel behavior. Mixed in ahead of the DCC Slots base."""

    def header_init(self, widget):
        """Header menu: the Mirror / Duplicate Linear / Radial / Grid launchers
        (each a ``b###`` the fork opens its host's tool panel from)."""
        # Every entry is a one-shot action — dismiss the menu once one is triggered.
        widget.menu.hide_on_trigger = True
        widget.menu.add(
            "QPushButton",
            setText="Mirror",
            setObjectName="b000",
            setToolTip="Open the mirror window.",
        )
        widget.menu.add(
            "QPushButton",
            setText="Duplicate Linear",
            setObjectName="b006",
            setToolTip="Open the duplicate linear window.",
        )
        widget.menu.add(
            "QPushButton",
            setText="Duplicate Radial",
            setObjectName="b007",
            setToolTip="Open the duplicate radial window.",
        )
        widget.menu.add(
            "QPushButton",
            setText="Duplicate Grid",
            setObjectName="b008",
            setToolTip="Open the duplicate grid window.",
        )
