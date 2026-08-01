# !/usr/bin/python
# coding=utf-8
import maya.cmds as cmds

from tentacle import Slots


class SlotsMaya(Slots):
    """App specific methods inherited by all other app specific slot classes."""

    #: Default body for the empty-selection message box (see :meth:`require_selection`).
    NOTHING_SELECTED = (
        "<b>Nothing selected.</b><br>"
        "The operation requires at least one selected object."
    )

    def __init__(self, switchboard):
        super().__init__(switchboard)

    def require_selection(self, message=None, **kwargs):
        """The current selection, or ``None`` — after a message box — when it is empty.

        The guard every selection-driven command needs. Maya answers an empty
        selection with a raw Script Editor error, and its MEL wrappers
        (``texOrientShells``, ``texCheckSelection``) raise ``RuntimeError``
        outright — which reaches the user as a traceback instead of as feedback
        from the tool. Call this first and bail on ``None``.

        Parameters:
            message (str, optional): HTML shown when nothing is selected.
                Defaults to :attr:`NOTHING_SELECTED`.
            **kwargs: Forwarded to ``cmds.ls`` (``objectsOnly``, ``flatten``,
                ``type``, ...). ``sl=True`` is always applied.

        Returns:
            list | None: The selection, or ``None`` when it is empty.
        """
        selection = cmds.ls(sl=True, **kwargs) or []
        if not selection:
            self.sb.message_box(message or self.NOTHING_SELECTED)
            return None
        return selection
