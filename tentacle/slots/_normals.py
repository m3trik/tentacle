# !/usr/bin/python
# coding=utf-8
"""Behavior shared by the Maya and Blender ``normals`` panels.

The Reverse Normals option box (Maya's five ``polyNormal`` modes, 1:1).
"""


class NormalsMixin:
    """Shared ``normals`` panel behavior. Mixed in ahead of the DCC Slots base."""

    def tb010_init(self, widget):
        """Initialize Reverse Normals: Maya's five ``polyNormal`` modes, 1:1 in
        both hosts (same items, same default index); the Blender fork runs
        Propagate / Conform / Extract through ``btk.EditUtils`` shell walks."""
        if not widget.is_initialized:
            widget.option_box.menu.setTitle("Reverse Normals")
            widget.option_box.menu.add(
                "QComboBox",
                setObjectName="cmb000",
                addItems=[
                    "Reverse",
                    "Propagate",
                    "Conform",
                    "Reverse and Extract",
                    "Reverse and Propagate",
                ],
                setCurrentIndex=3,
                setToolTip="Normal operation mode.",
            )
