# !/usr/bin/python
# coding=utf-8
"""Shared, DCC-agnostic behavior for the ``rendering`` panel.

The per-panel home for logic the Maya and Blender ``Rendering`` forks share
(mixed in ahead of their ``SlotsMaya`` / ``SlotsBlender`` base). Grow this
class rather than adding a new module per feature — see the convention in
``tentacle/CLAUDE.md``.

Currently: the playblast encoder guard. The WebXR Preview slot used to live
here too — an option box and a push flow, duplicated per fork until they
drifted. Both are gone: the preview is now one panel (``extapps``'s
``webxr_preview``), launched by each fork's ``tb002`` and handed that DCC's
bridge, so the settings, the push and the live status have a single
implementation that a host does not own. What is left here is the one guard
the playblast still shares.
"""


class RenderingMixin:
    """DCC-agnostic ``rendering`` slot behavior (the playblast encoder guard)."""

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
