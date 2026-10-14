# !/usr/bin/python
# coding=utf-8
"""Shared, DCC-agnostic behavior for the ``rendering`` panel.

The per-panel home for logic the Maya and Blender ``RenderingSlots`` forks share
(mixed in ahead of their ``SlotsMaya`` / ``SlotsBlender`` base). Grow this
class rather than adding a new module per feature — see the convention in
``tentacle/CLAUDE.md``.

Currently: the playblast encoder guard and the playblast's default output
path (the scene project's movie folder). The WebXR Preview slot used to live
here too — an option box and a push flow, duplicated per fork until they
drifted. Both are gone: the preview is now one panel (``extapps``'s
``webxr_preview``), launched by each fork's ``tb002`` and handed that DCC's
bridge, so the settings, the push and the live status have a single
implementation that a host does not own. What is left here is what the
playblast still shares.
"""

import os


class RenderingMixin:
    """DCC-agnostic ``rendering`` slot behavior (the playblast encoder guard and
    default output path)."""

    # ------------------------------------------------------------------ hooks
    def _scene_workspace(self):
        """Return the open scene's project as a ``ptk.Workspace``, or ``None``:
        ``mtk.EnvUtils.scene_workspace()`` / ``btk.EnvUtils.scene_workspace()``."""
        raise NotImplementedError

    def _scene_base_name(self) -> str:
        """Return the name a playblast of the open scene is written under."""
        raise NotImplementedError

    # ------------------------------------------------------- playblast defaults
    def _default_playblast_path(self) -> str:
        """The playblast's default output base: ``<movie folder>/<scene name>``.

        The scene project's movie folder (``ptk.Workspace.movie_dir``: the
        ``movie`` rule, else ``movies/``) -- the same folder in both DCCs, and
        the scene's own project rather than merely the active one. The Desktop
        only when no project resolves (an unsaved file with no session
        project). Asking creates nothing: the writer makes the folder.
        """
        ws = self._scene_workspace()
        if ws is not None:
            folder = ws.movie_dir()
        else:
            folder = os.path.expanduser(os.path.join("~", "Desktop"))
        return os.path.normpath(os.path.join(folder, self._scene_base_name()))

    def _show_playblast_default(self, field) -> None:
        """Show the default output base as *field*'s placeholder (``t000``).

        The field itself stays empty unless the user types a path: a value
        written into it would persist and pin the panel to the scene it was
        built in. Each fork re-runs this on every panel show, and resolves a
        blank field to the same default when it playblasts.
        """
        field.setPlaceholderText(self._default_playblast_path())

    def _ffmpeg_ready(self) -> bool:
        """Guarantee ffmpeg for an encoded playblast output, offering the
        managed install when it is missing (``rendering.tb000``).

        MP4/MOV are encoded by ffmpeg from a viewport capture that takes
        minutes, and the engine's own pre-flight can only *refuse* -- a panel
        must *offer*. One primitive (``ptk.VidUtils.ensure_ffmpeg``) answers
        the environment the same way for every host; only the modal differs.
        The WebXR panel applies the identical rule to its KTX2 encoder.

        Returns:
            True when an encode can proceed; False after the user declined or
            the install failed (the reason has been shown).
        """
        import pythontk as ptk

        try:
            installed = ptk.VidUtils.ensure_ffmpeg(
                prompt=lambda question: (
                    self.sb.message_box(question, "Yes", "No") == "Yes"
                )
            )
        except FileNotFoundError as e:
            self.sb.message_box(str(e))
            return False
        if installed:
            self.sb.message_box(f"Installed FFmpeg: <hl>{installed}</hl>")
        return True
