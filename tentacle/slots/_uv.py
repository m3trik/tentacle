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

    # ------------------------------------------------------------------ b030  Stack
    # Modes of the Stack button (option-box combo data). Both DCC engines
    # implement the pair with the same semantics: ``similar`` stacks shells of
    # the same topology + shape onto the first matching one, rotated (and
    # scaled) to overlap exactly, leaving unmatched shells where they are;
    # ``center`` (labelled "All shells") translates every targeted shell onto
    # one shared center regardless of shape -- the plain Stack.
    STACK_MODE_SIMILAR = "similar"
    STACK_MODE_CENTER = "center"

    def b030_init(self, widget):
        """Stack button — non-checkable text button with the stack option box.

        Defensively clears any ``checkable`` property a Qt Designer round-trip
        may have re-added (the button's "Stack" label lives in the .ui). The
        option box (Mode / Tolerance / Pin) is one shared surface: each DCC
        fork's ``b030`` reads it through :meth:`_stack_options`.
        """
        widget.setCheckable(False)
        menu = widget.option_box.menu
        menu.setTitle("Stack Shells")
        cmb020 = menu.add(
            "QComboBox",
            setObjectName="cmb020",
            setToolTip=self.sb.tooltip.fmt(
                title="Mode",
                body="How the selected shells are stacked. Click again to "
                "Unstack (restore the pre-stack positions).",
                bullets=[
                    "<b>Similar</b> — shells with the same topology and shape "
                    "stack onto the first matching shell, rotated (and scaled) "
                    "to overlap exactly. Shells with no match stay put. Use "
                    "this to share texture space between identical parts.",
                    "<b>All shells</b> — the basic stack: every selected shell "
                    "is translated onto one shared center regardless of shape "
                    "(no rotation).",
                ],
            ),
        )
        for text, data in [
            ("Mode: Similar (rotate to match)", self.STACK_MODE_SIMILAR),
            ("Mode: All shells (center, no rotation)", self.STACK_MODE_CENTER),
        ]:
            cmb020.addItem(text, data)
        menu.add(
            "QDoubleSpinBox",
            setPrefix="Tolerance: ",
            setObjectName="s024",
            set_limits=[0, 10, 0.1, 1],
            setValue=1.0,
            setToolTip=self.sb.tooltip.fmt(
                title="Tolerance",
                body="Similar mode only: how much two shells' shapes may differ "
                "and still count as the same shell.",
                notes=[
                    "0 = practically identical; higher = looser. Identical "
                    "duplicates match at any value; 1.0 also tolerates the "
                    "small drift two separately unfolded copies pick up.",
                ],
            ),
        )
        menu.add(
            "QCheckBox",
            setText="Pin after stack",
            setObjectName="chk047",
            setChecked=False,
            setToolTip=self.sb.tooltip.fmt(
                title="Pin after stack",
                body="Pin the selected shells' UVs once stacked so a later "
                "Unfold / Optimize / Layout leaves them in place. Unstack "
                "puts the pins back as they were.",
                notes=[
                    "Pins are DCC-side only — they do not travel through the "
                    "RizomUV bridge. To keep a stack together in a Rizom pack, "
                    "turn on <b>Keep Stacked</b> in the bridge's pack options "
                    "instead (it detects the overlapping shells itself).",
                ],
            ),
        )

    def _stack_options(self, widget):
        """``(mode, tolerance, pin)`` from the Stack option box (see :meth:`b030_init`)."""
        menu = widget.option_box.menu
        return (
            menu.cmb020.currentData() or self.STACK_MODE_SIMILAR,
            float(menu.s024.value()),
            bool(menu.chk047.isChecked()),
        )

    def _report_no_similar_shells(self):
        """Similar mode found nothing to stack — say so (both DCC forks)."""
        self.sb.message_box(
            "<b>No similar shells found.</b><br>"
            "Similar mode stacks shells that share topology and shape (within "
            "the tolerance) — raise the tolerance, or switch to <b>All shells</b> to "
            "stack regardless of shape."
        )

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
