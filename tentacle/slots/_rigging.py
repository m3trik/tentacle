# !/usr/bin/python
# coding=utf-8
"""Behavior shared by the Maya and Blender ``rigging`` panels."""


class RiggingMixin:
    """Shared ``rigging`` panel behavior. Mixed in ahead of the DCC Slots base."""

    @staticmethod
    def _affix_arg(field):
        """``(text, mode)`` for an affix field, as the engine wants them.

        Scene mode reports ``(None, "auto")``: ``None`` is how the host's
        ``RigUtils.create_locator_at_object`` is told to take the shared
        convention's entry for that node type -- spelling AND placement -- so
        the mode argument beside it is moot. Every other state is the user's
        literal text placed as the picker says.
        """
        mode = field.option_box.affix_mode
        return (None, "auto") if mode == "convention" else (field.text(), mode)
