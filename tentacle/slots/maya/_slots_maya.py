# !/usr/bin/python
# coding=utf-8
import mayatk as mtk

from tentacle import Slots


class SlotsMaya(Slots):
    """App specific methods inherited by all other app specific slot classes.

    What is left of it delegates to mayatk until the last Maya fork merges into
    a composed category class (``slots/<category>.py``), which calls the same
    operations through ``self.tk``. It reaches ``mtk`` directly rather than
    through ``self.tk`` so a fork behaves the same under a test's switchboard.
    """

    def __init__(self, switchboard):
        super().__init__(switchboard)

    def require_selection(self, message=None, **kwargs):
        """The current selection, or ``None`` -- after a message box -- when it is empty.

        The guard every selection-driven command needs. Maya answers an empty
        selection with a raw Script Editor error, and its MEL wrappers
        (``texOrientShells``, ``texCheckSelection``) raise ``RuntimeError``
        outright -- which reaches the user as a traceback instead of as feedback
        from the tool. Call this first and bail on ``None``. The composed
        classes' form is :meth:`Slots.require_selection` (no ``cmds.ls`` filters:
        it reads the selection both hosts answer).

        Parameters:
            message (str, optional): HTML shown when nothing is selected.
                Defaults to :attr:`NOTHING_SELECTED`.
            **kwargs: ``cmds.ls`` filters (``objectsOnly``, ``flatten``,
                ``type``, ...), through ``mtk.CoreUtils.selected_objects``.

        Returns:
            list | None: The selection, or ``None`` when it is empty.
        """
        selection = mtk.CoreUtils.selected_objects(**kwargs)
        if not selection:
            self.sb.message_box(message or self.NOTHING_SELECTED)
            return None
        return selection
