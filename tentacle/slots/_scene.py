# !/usr/bin/python
# coding=utf-8
"""Behavior shared by the Maya and Blender ``scene`` panels.

Currently the **Fix Non-Orthogonal Axes** header entry (``tb002``): the scan,
the report, the confirmation and the result summary are identical on both
sides because both engines expose the same
``Diagnostics.get_non_orthogonal`` / ``.fix_non_orthogonal_axes`` contract
(``mayatk.core_utils.diagnostics.transform_diag`` /
``blendertk.core_utils.diagnostics.transform_diag``) returning the same
``{object: {"skew": float, "cause": str}}`` diagnosis. Only the engine handle,
the scope resolvers and the wording of what the fix *does* to the object are
DCC-specific — those are the hooks below.
"""

import html


class SceneMixin:
    """Shared ``scene`` panel behavior. Mixed in ahead of the DCC Slots base."""

    # ------------------------------------------------------------------ hooks
    def _diagnostics(self):
        """Return the DCC engine's ``Diagnostics`` namespace."""
        raise NotImplementedError

    def _scene_objects(self):
        """Return every object in the scene eligible for a transform check."""
        raise NotImplementedError

    def _selected_objects(self):
        """Return the current selection."""
        raise NotImplementedError

    # What freezing/baking actually does to the object in this DCC — shown in
    # the confirmation so the user knows the side effect before committing.
    NON_ORTHOGONAL_FIX_EFFECT = ""

    # --------------------------------------------------- tb002  fix non-orthogonal
    _TB002_SCOPES = (
        ("Selected Objects", "selection"),
        ("Entire Scene", "all"),
    )

    # Rows rendered in the report before it is truncated. The dialog is a
    # triage aid, not a data dump — but the cut is always stated, never silent.
    _TB002_REPORT_LIMIT = 200

    def tb002_init(self, widget):
        """Fix Non-Orthogonal Axes — option box."""
        widget.option_box.menu.setTitle("Fix Non-Orthogonal Axes")

        cmb_scope = widget.option_box.menu.add(
            "QComboBox",
            # NOT cmb_scope / cmb_scope1 — those are the Export (tb003) and
            # Get Scene Info (tb001) scope combos on this same panel.
            setObjectName="cmb_scope2",
            setToolTip=(
                "Selected Objects: check only what is selected.\n"
                "Entire Scene: check every object — this is what FBX export "
                "sees, so use it when chasing the export warning."
            ),
        )
        for label, data in self._TB002_SCOPES:
            cmb_scope.addItem(label, data)

        widget.option_box.menu.add(
            "QCheckBox",
            setText="Report Only (Dry Run)",
            setObjectName="chk_dry_run",
            setChecked=False,
            setToolTip=(
                "List the offending objects without changing anything.\n"
                "Run this first to see what would be touched."
            ),
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Break Driving Connections",
            setObjectName="chk_break_connections",
            setChecked=False,
            setToolTip=(
                "Objects whose transform is DRIVEN (constraints, animation, "
                "expressions) are skipped by default — the fix and the driver "
                "would fight over the same channels, so there is no accurate "
                "way to keep both.\n"
                "Tick to permanently remove those drivers and fix the objects "
                "anyway. Position-only drivers never block the fix and are "
                "always kept."
            ),
        )

    def tb002(self, widget):
        """Fix Non-Orthogonal Axes.

        The FBX plug-in's "Non-orthogonal matrix support" warning fires when an
        object's evaluated axes are not perpendicular — either it carries shear
        itself, or it sits under a non-uniformly scaled, rotated ancestor and
        inherits the shear. Both are detected; the fix bakes the transform so
        the object looks identical but exports correctly.
        """
        menu = widget.option_box.menu
        scope = menu.cmb_scope2.currentData() or "selection"
        dry_run = menu.chk_dry_run.isChecked()
        break_connections = menu.chk_break_connections.isChecked()
        diagnostics = self._diagnostics()

        if scope == "all":
            objects = self._scene_objects()
            if not objects:
                self.sb.message_box("<hl>Empty scene</hl> — nothing to check.")
                return
        else:
            objects = self._selected_objects()
            if not objects:
                self.sb.message_box(
                    "<hl>Nothing selected</hl>. Select objects, or pick "
                    "'Entire Scene' from the option menu."
                )
                return

        with self.sb.progress(text="Checking for non-orthogonal axes…") as tick:
            tick()
            found = diagnostics.get_non_orthogonal(objects, detailed=True)

        if not found:
            self.sb.message_box(
                "No <hl>non-orthogonal axes</hl> found — nothing to fix."
            )
            return

        if dry_run:
            self.sb.text_view_dialog(
                self._format_non_orthogonal(found),
                "Ok",
                title="Non-Orthogonal Axes (Report Only)",
                size=(620, 440),
                monospace=True,
                word_wrap=False,
            )
            return

        inherited = sum(1 for i in found.values() if i["cause"] == "inherited")
        driven = sum(1 for i in found.values() if i.get("driven"))
        text = f"<hl>{len(found)}</hl> object(s) have non-orthogonal axes"
        if inherited:
            text += f" ({inherited} inheriting it from a parent)"
        text += f".<br><br>{self.NON_ORTHOGONAL_FIX_EFFECT}"
        if driven:
            text += (
                f"<br><br><hl>{driven}</hl> of them are DRIVEN (constraints/"
                "animation) and will be "
                + (
                    "fixed by removing their drivers."
                    if break_connections
                    else "skipped — enable <hl>Break Driving Connections</hl> "
                    "to include them."
                )
            )
        # message_box buttons must be Qt standard-button names ("Yes",
        # "Cancel", ...) — anything else is dropped, leaving a Cancel-only box.
        choice = self.sb.message_box(text + "<br><br>Fix them?", "Yes", "Cancel")
        if choice != "Yes":
            return

        with self.sb.progress(text="Fixing non-orthogonal axes…") as tick:
            tick()
            fixed = diagnostics.fix_non_orthogonal_axes(
                objects, quiet=True, break_connections=break_connections
            )
            tick(text="Verifying…")
            # Re-resolve for the verify: a fix can rename objects (Maya
            # uninstances before freezing), so the pre-fix name list may be
            # stale. Selection scope keeps the original list — the selection
            # itself may have been consumed by the fix.
            remaining = diagnostics.get_non_orthogonal(
                self._scene_objects() if scope == "all" else objects
            )

        message = f"Fixed <hl>{len(fixed)}</hl> of <hl>{len(found)}</hl> object(s)."
        if remaining:
            message += (
                f"<br><br><hl>{len(remaining)}</hl> could not be fixed — see "
                "the script editor. Driven objects need <hl>Break Driving "
                "Connections</hl> (or bake the animation first); referenced "
                "objects must be fixed in their source file."
            )
        self.sb.message_box(message)

    def _format_non_orthogonal(self, found):
        """Render a ``get_non_orthogonal(detailed=True)`` diagnosis as report HTML.

        Skew is the worst axis-pair cosine: 0 is perpendicular, and the larger
        it gets the further the object is from something FBX can represent.
        """
        rows = sorted(found.items(), key=lambda kv: kv[1]["skew"], reverse=True)
        shown, dropped = rows[: self._TB002_REPORT_LIMIT], rows[self._TB002_REPORT_LIMIT :]

        lines = [
            f"{len(found)} object(s) with non-orthogonal axes",
            "",
            f"{'SKEW':<10}{'CAUSE':<12}{'OBJECT':<26}DRIVEN BY",
            f"{'-' * 10}{'-' * 12}{'-' * 26}{'-' * 20}",
        ]
        for obj, info in shown:
            name = getattr(obj, "name", None) or str(obj)
            driven = ", ".join(info.get("driven") or [])
            lines.append(
                f"{info['skew']:<10.5f}{info['cause']:<12}"
                f"{name.split('|')[-1]:<26}{driven}"
            )
        if dropped:
            lines.append(f"... and {len(dropped)} more (report truncated)")
        lines += [
            "",
            "cause 'shear'     - the object carries shear on its own transform",
            "cause 'inherited' - a non-uniformly scaled, rotated ancestor shears it",
            "DRIVEN BY         - the fix skips these unless Break Driving",
            "                    Connections is enabled (drivers and the fix",
            "                    fight over the same channels)",
        ]
        return "<pre>{}</pre>".format(html.escape("\n".join(lines)))
