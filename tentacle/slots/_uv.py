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

    # ------------------------------------------------------------------
    # Transfer tool: enablement of the option box's mode-dependent rows
    # ------------------------------------------------------------------
    # Both forks build the same option box and drive it from the same state, so
    # this pair lives here rather than twice: the bodies were byte-identical and
    # only the fork-specific *labels* differ, which are the panel's business
    # (they are what `docs/parity_map.py` ledgers), not this logic's.
    #
    # Contract with each fork's ``b000_init``: it sets ``_tt_ctl`` -- the
    # ``{role: widget}`` map named below -- plus ``_tt_src_button`` /
    # ``_tt_clear_action`` for the Set Source row and ``_tt_sources`` for the
    # captured meshes. Every lookup is defensive so a panel that has not built
    # its option box yet (or a fork that grows a row later) is a no-op, not an
    # AttributeError from inside a signal handler.

    # Modes of the Transfer combo (option-box combo data), and the one place
    # that turns the chosen mode into the passes ``b000`` runs. One combo
    # rather than two toggles because the two are alternatives, not options
    # that compose: the texture pass writes the maps FOR THE TARGET'S OWN
    # layout, so a source layout copied alongside them would land in a UV set
    # nothing references. (The combined operation that IS useful reads the
    # TARGET's own textures -- "adopt a new layout on a textured mesh"; see
    # .claude/BACKLOG.md.)
    TRANSFER_UVS = "uvs"
    TRANSFER_TEXTURES = "textures"

    @classmethod
    def _tt_passes(cls, source_mode, transfer_mode):
        """``(do_uvs, do_textures)`` for a Source / Transfer mode pair.

        The UV pass is dropped for the *same mesh, other UV set* source: there
        is no second mesh to read a layout from, only two layouts of one mesh.
        """
        textures = (transfer_mode or cls.TRANSFER_UVS) == cls.TRANSFER_TEXTURES
        return not textures and source_mode != "uvset", textures

    def _tt_clear_source(self):
        """Forget the stored source meshes (the geometry is untouched)."""
        self._tt_sources = []
        self._tt_sync_controls()

    def _tt_sync_controls(self):
        """Grey every option that the current mode makes meaningless.

        Greying (not hiding) keeps the panel's shape stable, so each row is its
        own readout: the Set Source row follows the Source combo (capture only
        feeds the *stored sources* mode; Clear only once something is stored),
        Scope + Similarity follow the *single source mesh* mode (the Similar
        scopes additionally need the UV pass, which is what finds their
        targets), and the texture rows follow the Transfer combo -- which the
        *same mesh, other UV set* source pins to Textures, having no second
        mesh for a UV pass to read from.
        """
        ctl = getattr(self, "_tt_ctl", None)
        if ctl is None:
            return
        # ``.get``, per the contract above: a fork that has not built every
        # row yet must be a no-op here, not an AttributeError raised from
        # inside a signal handler.
        source, transfer = ctl.get("source"), ctl.get("transfer")
        if source is None:
            return
        mode = source.currentData() or "first"
        # The same-mesh source moves textures between two of ONE mesh's
        # layouts, so a UV pass has no second mesh to read from: the combo is
        # pinned to Textures rather than left offering a mode that cannot run.
        # Pinned BEFORE the passes are read -- ``setCurrentIndex`` re-enters
        # this method through the combo's signal, and computing first would
        # leave the outer call finishing with the pre-pin flags, re-greying
        # every texture row the re-entrant call had just enabled.
        same_mesh = mode == "uvset"
        if transfer is not None:
            index = transfer.findData(self.TRANSFER_TEXTURES)
            if same_mesh and index >= 0 and transfer.currentIndex() != index:
                transfer.setCurrentIndex(index)
            transfer.setEnabled(not same_mesh)
        uvs, textures = self._tt_passes(
            mode, transfer.currentData() if transfer is not None else None
        )
        stored_mode = mode == "stored"
        button = getattr(self, "_tt_src_button", None)
        if button is not None:
            button.setEnabled(stored_mode)
        action = getattr(self, "_tt_clear_action", None)
        if action is not None:
            action.widget.setEnabled(stored_mode and bool(self._tt_sources))
        scope = ctl.get("scope")
        if scope is not None:
            scope.setEnabled(mode == "first")
        similarity = ctl.get("similarity")
        if similarity is not None:
            in_scope = (
                (scope.currentData() or "order") if scope is not None else "order"
            )
            similarity.setEnabled(mode == "first" and uvs and in_scope != "order")
        for w in ctl.get("texture_controls") or ():
            w.setEnabled(textures)

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
