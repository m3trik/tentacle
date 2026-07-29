# !/usr/bin/python
# coding=utf-8
"""Behavior shared by the Maya and Blender UV panels."""


class UvMixin:
    """Shared UV-panel behavior (see ``slots/maya/uv.py``, ``slots/blender/uv.py``)."""

    # Auto Unwrap modes handled by an external unwrapping engine rather than the
    # DCC's own projection. Values are the ``method`` names understood by both
    # engines' ``UvUtils.auto_unwrap``.
    AUTO_UNWRAP_ENGINE_MODES = ("hard", "organic")

    @staticmethod
    def _engine_label(engine):
        """The engine's display name, read from its own spec (not a second copy)."""
        try:
            import pythontk as ptk

            return ptk.UvUnwrap.ENGINES[engine].label
        except (ImportError, KeyError):
            return engine

    def _run_auto_unwrap(self, engine, objects, method, map_size):
        """Run ``UvUtils.auto_unwrap`` and report the outcome.

        Parameters:
            engine: The DCC toolkit module (``mayatk`` / ``blendertk``).
            objects: Meshes to unwrap.
            method (str): ``"hard"`` or ``"organic"``.
            map_size (int): Texture size driving island spacing.
        """
        try:
            result = engine.UvUtils.auto_unwrap(
                objects, method=method, map_size=map_size
            )
        except Exception as error:  # noqa: BLE001 - surfaced to the user, not swallowed
            # A missing engine reports its download URL in the message.
            self.sb.message_box(f"<b>Auto Unwrap failed.</b><br><br>{error}")
            return None
        self._report_auto_unwrap(result)
        return result

    def _report_auto_unwrap(self, result):
        """Summarize an ``AutoUnwrapResult``; stay quiet on a clean single run."""
        label = self._engine_label(result.engine)

        if result.failed:
            failed_list = "<br>".join(
                f"• <b>{name}</b>: {reason}" for name, reason in result.failed
            )
            self.sb.message_box(
                f"<b>Auto Unwrap Complete</b><br><br>"
                f"<b>Engine:</b> {label}<br>"
                f"✓ Unwrapped: {len(result.succeeded)} mesh(es)<br>"
                f"✗ Failed: {len(result.failed)} mesh(es)<br><br>"
                f"<b>Failed meshes:</b><br>{failed_list}"
            )
        elif len(result.succeeded) > 1:
            self.sb.message_box(
                f"<b>Auto Unwrap Complete</b><br><br>"
                f"<b>Engine:</b> {label}<br>"
                f"✓ Unwrapped {len(result.succeeded)} mesh(es)."
            )
