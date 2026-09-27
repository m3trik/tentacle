# !/usr/bin/python
# coding=utf-8
"""Behavior shared by the Maya and Blender ``transform`` panels.

The Scale Connected Edges option box.
"""


class TransformMixin:
    """Shared ``transform`` panel behavior. Mixed in ahead of the DCC Slots base."""

    def tb001_init(self, widget):
        """Initialize Scale Connected Edges (the scale factor option)."""
        widget.option_box.menu.add(
            "QDoubleSpinBox",
            setObjectName="s001",
            setPrefix="Scale Factor:",
            setValue=1.1,
            set_limits=[-999, 999, 0.1],
            setToolTip="Scale factor to apply to scaling by as a percentage.",
        )
