# !/usr/bin/python
# coding=utf-8
"""Behavior shared by the Maya and Blender ``scene`` panels.

Three subsystems live here:

* the **Fix Non-Orthogonal Axes** header entry (``tb002``): the scan, the
  report, the confirmation and the result summary are identical on both sides
  because both engines expose the same ``Diagnostics.get_non_orthogonal`` /
  ``.fix_non_orthogonal_axes`` contract
  (``mayatk.core_utils.diagnostics.transform_diag`` /
  ``blendertk.core_utils.diagnostics.transform_diag``) returning the same
  ``{object: {"skew": float, "cause": str}}`` diagnosis; and
* the **workspace status footer**: identical wiring on both sides — subscribe
  the engine's ``ScriptJobManager`` to the DCC's scene events, own the
  controller, refresh on each event; and
* **Save As <other DCC> Scene** (the Export list's cross-DCC entry): pick a
  destination, run the blocking hand-off, report. Identical on both sides
  because the bridges are mirrors (``mtk.BlenderBridge`` ↔ ``btk.MayaBridge``)
  and the bridge itself carries everything that differs — its target app's
  display name and the scene extensions it writes.

Only the engine handle, the scope resolvers, the wording of what the fix *does*
to the object, which events signal a workspace change, the open scene's path and
the foreign-format bridge are DCC-specific — those are the hooks below.
"""

import os
import html

import pythontk as ptk


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

    def _script_job_manager(self):
        """Return the DCC engine's ``ScriptJobManager`` class (``mtk``/``btk``)."""
        raise NotImplementedError

    def _resolve_workspace_text(self) -> str:
        """Return the current workspace path — the footer's status text."""
        raise NotImplementedError

    def _current_scene_path(self) -> str:
        """Return the open scene's path, or ``""`` when it has never been saved."""
        raise NotImplementedError

    def _foreign_scene_bridge(self):
        """Return the hand-off bridge that writes the OTHER DCC's native format.

        ``mtk.BlenderBridge()`` from the Maya fork, ``btk.MayaBridge()`` from the
        Blender fork. The instance carries everything the foreign-export path needs
        beyond the destination — the target app's display name and the scene
        extensions it writes — so this is the only hook that direction requires.
        """
        raise NotImplementedError

    # --------------------------------------------------- export: formats + paths
    #: ``(label, data)`` for the Export Scene format combo — the formats BOTH DCCs
    #: write. The fork's foreign twin is appended from :attr:`FOREIGN_FORMAT_LABEL`,
    #: so the combo is "the portable three plus the other DCC" on either side and the
    #: dispatch below is shared. ``"glb"`` matches ``SceneExporter``'s own
    #: ``output_format`` vocabulary — one word for the same thing in both engines.
    EXPORT_FORMATS = (("FBX", "fbx"), ("OBJ", "obj"), ("GLB", "glb"))
    #: Output extension per portable format (``"foreign"`` resolves from the bridge).
    EXPORT_EXTENSIONS = {"fbx": ".fbx", "obj": ".obj", "glb": ".glb"}
    #: Combo label for the OTHER DCC's native format — "Blend" / "MA" per fork.
    FOREIGN_FORMAT_LABEL = "Foreign"

    def _export_format_items(self):
        """``[(label, data), ...]`` for the ``cmb_format`` combo, foreign twin last."""
        return [*self.EXPORT_FORMATS, (self.FOREIGN_FORMAT_LABEL, "foreign")]

    def _export_extension(self, export_format: str) -> str:
        """Output extension for a ``cmb_format`` data value.

        The foreign one comes off the bridge rather than a second table here: it is
        already declared there (``save_extensions``), and two lists of the same fact
        drift.
        """
        if export_format == "foreign":
            return self._foreign_scene_bridge().save_extensions[0]
        return self.EXPORT_EXTENSIONS[export_format]

    def _resolve_export_path(self, save_mode: str, extension: str):
        """Output path for *save_mode*, or ``None`` to cancel (reported to the user).

        ``"scene_dir"`` writes beside the open scene under its own name;
        ``"prompt"`` asks, pre-filled with exactly that path so the two modes agree
        on the default. An unsaved scene has no directory to write beside, so that
        combination is the one hard error — the prompt falls back to the workspace.
        """
        scene_path = self._current_scene_path()
        base = os.path.splitext(os.path.basename(scene_path))[0] or "untitled"
        label = extension.lstrip(".").upper()

        if save_mode == "prompt":
            start_dir = os.path.dirname(scene_path) or self._resolve_workspace_text()
            picked = self.sb.save_file_dialog(
                file_types=[f"*{extension}"],
                title=f"Export {label} As",
                # A FILE path, not a directory: it pre-fills the name box.
                start_dir=os.path.join(start_dir, base + extension),
                filter_description=f"{label} Files",
            )
            if not picked:
                return None
            # Qt does not reliably append the filter's suffix when the user types a
            # bare name, and the writer picks its translator off the extension.
            return picked if picked.lower().endswith(extension) else picked + extension

        if not scene_path:
            self.sb.message_box(
                "Scene has not been saved yet.<br>Save the scene first, or choose "
                "<hl>Prompt for File</hl> in the export options."
            )
            return None
        return os.path.splitext(scene_path)[0] + extension

    def _export_scene_native(self, export_format, out_path, options, tick):
        """Write *out_path* in a NATIVE format — ``"fbx"`` / ``"obj"`` / ``"glb"``.

        The one genuinely DCC-specific step of :meth:`tb003`: everything around it
        (reading the options, the guards, resolving the path, the foreign route, the
        reporting) is identical on both sides. Raise on failure — the caller reports.

        *options* is the option box's booleans: ``selection_only``,
        ``include_cameras`` / ``include_lights`` / ``include_skins`` /
        ``include_tangents``, ``embed_textures``. *tick* paints a progress status
        (Maya's GLB route uses it for the conversion leg).
        """
        raise NotImplementedError

    # ------------------------------------------------------------ tb003 Export Scene
    def tb003(self, widget):
        """Export Scene in the chosen format, using the configured options.

        Every trigger is a tb003 PushButton carrying its own option-box gear
        (``list002_init`` builds one per surface), so the options come off the widget
        that was clicked — the same idiom as every other tb slot. The panel and
        submenu forks stay in agreement because uitk mirrors a value into every
        related surface's store on change (``MainWindow.sync_widget_values``).
        """
        menu = widget.option_box.menu
        export_format = menu.cmb_format.currentData()
        selection_only = menu.cmb_scope.currentData() == "selected"
        options = {
            "selection_only": selection_only,
            # Cameras/lights are inert in Selected Only mode (see tb003_init); coerce
            # to False so a stale checked-but-disabled box can't leak through.
            "include_cameras": menu.chk_cameras.isChecked() and not selection_only,
            "include_lights": menu.chk_lights.isChecked() and not selection_only,
            "include_skins": menu.chk_skins.isChecked(),
            "include_tangents": menu.chk_tangents.isChecked(),
            "embed_textures": menu.chk_embed.isChecked(),
        }

        if selection_only and not self._selected_objects():
            self.sb.message_box("No objects selected.")
            return

        # OBJ carries no tangent channel, so the cost that warning is about is not
        # paid there — asking about it would be noise.
        if not self._confirm_dense_export(
            selection_only, options["include_tangents"] and export_format != "obj"
        ):
            return

        extension = self._export_extension(export_format)
        out_path = self._resolve_export_path(menu.cmb_save.currentData(), extension)
        if not out_path:
            return

        if export_format == "foreign":
            # The bridge owns its own wait cursor and reporting — it is a
            # multi-second app launch, not a DCC-side write, so it does not belong
            # under the progress context below.
            result = self._run_foreign_export(
                out_path, self._selected_objects() if selection_only else None
            )
            if result:
                self.sb.message_box(
                    f"Exported <hl>{ptk.format_path(result['output'], 'file')}</hl> "
                    f"({result['duration']:.1f}s)."
                )
            return

        # Every native writer is a single blocking call that scales with poly count,
        # so on dense scenes the UI sits frozen with no feedback. Run inside the
        # footer progress context, painting a status before the blocking step
        # (``tick()`` pumps the event loop) so it reads as working, not hung. Let
        # failures propagate out of the context so it suppresses its "Complete" flash
        # on a non-clean exit.
        try:
            with self.sb.progress(
                text=f"Exporting {extension.lstrip('.').upper()}… "
                "dense scenes can take a while"
            ) as tick:
                tick()  # paint the status before the blocking export
                self._export_scene_native(export_format, out_path, options, tick)
        except Exception as error:  # noqa: BLE001 - every writer, one report
            self.sb.message_box(f"Export failed:<br>{error}")
            return

        self.sb.message_box(f"Exported <hl>{ptk.format_path(out_path, 'file')}</hl>.")

    # ------------------------------------------------ export: the foreign format
    def _run_foreign_export(self, out_path, objects=None):
        """Run the blocking bridge hand-off; return its result dict, or ``None``.

        Blocking by nature — a fresh headless target app starts up, imports the
        exported FBX and saves — so a wait cursor covers the run and the destination
        is always chosen BEFORE it starts. The bridge reports a handled failure by
        returning ``None`` (having logged the reason, e.g. the target app not being
        installed), so both that and a raised exception have to reach the artist:
        a silent no-op after a ten-second wait is the worst outcome here.
        """
        bridge = self._foreign_scene_bridge()
        app = bridge.spec.app.name  # "Maya" / "Blender" -- the TARGET, from the spec
        qapp = self.sb.QtWidgets.QApplication
        qapp.setOverrideCursor(self.sb.QtCore.Qt.WaitCursor)
        try:
            result = bridge.save_as(out_path, objects)
        except Exception as error:
            self.sb.message_box(f"Export to {app} failed: <hl>{error}</hl>")
            return None
        finally:
            qapp.restoreOverrideCursor()

        if not result:  # handled failure -- the bridge already logged the reason
            self.sb.message_box(
                f"Export to {app} <hl>failed</hl>.<br>See the script output for the "
                f"reason (a local {app} install is required)."
            )
        return result

    def _export_foreign_scene(self):
        """Write the WHOLE scene in the other DCC's native format (Export list entry).

        The push mirror of the Import list's "Import <other DCC> Scene", and the one
        direction the pair could not previously go. The whole scene rather than the
        selection, and its own destination prompt — the Export list's entries are
        one-shots that carry no options of their own (Export Scene's format combo is
        the configured route to the same place).
        """
        bridge = self._foreign_scene_bridge()
        app = bridge.spec.app.name
        extensions = bridge.save_extensions
        scene_path = self._current_scene_path()
        base = os.path.splitext(os.path.basename(scene_path))[0] or "untitled"

        dest = self.sb.save_file_dialog(
            file_types=[f"*{ext}" for ext in extensions],
            title=f"Export {app} Scene",
            start_dir=os.path.join(
                os.path.dirname(scene_path) or self._resolve_workspace_text(),
                base + extensions[0],
            ),
            filter_description=f"{app} Scenes",
        )
        if not dest:
            return
        result = self._run_foreign_export(dest)
        if result:
            self.sb.message_box(
                f"Exported <hl>{ptk.format_path(result['output'], 'file')}</hl> "
                f"({result['duration']:.1f}s)."
            )

    # ------------------------------------------------- workspace status footer
    FOOTER_DEFAULT_TEXT = "No workspace set"
    FOOTER_TRUNCATE = {"length": 96, "mode": "middle"}

    #: Set by the fork's ``__init__`` from :meth:`_create_footer_controller`.
    #: Declared here because the handler below reads it, and the subscription is
    #: live from inside that call — before the assignment lands.
    _footer_controller = None

    def _create_footer_controller(self):
        """Bind the panel footer to the workspace resolver and return the controller.

        Each fork must declare ``FOOTER_EVENTS`` — the engine event names whose
        firing means the workspace may have changed. Maya has a real
        ``workspaceChanged``; Blender has none, so it settles for scene open/save
        (a session-pin change shows on the next file event). There is deliberately
        no default: an empty one would build a footer subscribed to nothing, which
        never refreshes — the exact silent failure this wiring was moved off a
        widget ``_init`` to avoid. A fork that forgets it raises here instead.

        That move is the other half of the story: the subscription previously rode
        the Workspace-Scenes combo's ``_init``, which went dead when that widget
        left scene.ui. The footer is owned by the MainWindow, so it outlives every
        widget ``_init``.

        The controller comes off the footer widget itself
        (:meth:`uitk.Footer.status_controller`) rather than an imported class: a slot's
        uitk access goes through the Switchboard — ``self.ui`` here — and nothing else.
        """
        footer = getattr(self.ui, "footer", None)
        if not footer:
            return None
        mgr = self._script_job_manager().instance()
        for event in self.FOOTER_EVENTS:
            mgr.subscribe(event, self._on_workspace_changed, owner=footer)
        mgr.connect_cleanup(footer, owner=footer)
        return footer.status_controller(
            resolver=self._resolve_workspace_text,
            default_text=self.FOOTER_DEFAULT_TEXT,
            truncate_kwargs=self.FOOTER_TRUNCATE,
        )

    def _on_workspace_changed(self):
        """Engine event handler — refresh the footer's workspace status."""
        if self._footer_controller:
            self._footer_controller.update()

    # ------------------------------------------------------- list003  Tools list
    #: Tooltip for the Tools list's root row. Fork-set, because the forks stock
    #: different categories (only Maya has Recover) and the row should name what
    #: is actually under it.
    TOOLS_ROOT_TOOLTIP = ""

    def _tools_items(self):
        """``{category: [(label, objectName, tooltip), ...]}`` for the Tools list.

        A method rather than a class attribute because some tooltips are built
        with the switchboard's formatter, which needs a live ``self.sb``.
        """
        raise NotImplementedError

    def list003_init(self, widget):
        """Tools list: the scene actions that used to sit loose in the header
        menu (Bridges / Manage / Fix / Diagnostics, plus Recover on Maya),
        grouped into one expandable row.

        Every leaf is a real slot-wired widget carrying the objectName its header
        entry used, so its slot, tooltip, option box (``tb001`` / ``tb002``) and
        QSettings identity are unchanged — only the location moved. Maya's
        ``b014`` keeps its stateful ``b014_init`` (enabled state and destination
        label track the open scene) for the same reason.

        The submenu's trigger row is a narrow strip near the right edge of an
        absolutely-positioned layout, so its flyout opens ON TOP of that row
        (top-right corner to top-right corner) and the category fan-out runs
        LEFT, back across the submenu instead of off its right side. The panel's
        row is a layout-managed header menu and fans right on hover as usual.
        """
        submenu = widget.ui.has_tags("submenu")
        widget.fixed_item_height = 18
        widget.apply_preset("expand_overlay_left" if submenu else "hover_menu")
        root = widget.add("Tools", setToolTip=self.TOOLS_ROOT_TOOLTIP)
        for category, entries in self._tools_items().items():
            cat = root.sublist.add(category)
            for label, name, tooltip in entries:
                self.add_slot_widget(
                    cat.sublist,
                    setObjectName=name,
                    setText=label,
                    setToolTip=tooltip,
                )

    def _dispatch_tools_item(self, item):
        """Dispatch a Tools leaf to its own slot (the forks' ``list003`` body).

        Category rows are navigation only. Leaves are slot-wired widgets, so
        ``call_slot`` routes through the switchboard's wrapper — which injects
        the ``widget`` argument for the slots that declare it, so both signatures
        work without a lookup table here. An option-box-wrapped leaf never
        arrives: the wrap leaves it out of the list's item set and its own
        ``clicked`` drives it (see ``Slots.add_slot_widget``).

        The forks keep the ``list003`` method itself: its ``@Signals`` decorator
        is evaluated in the class body, and the decorator is re-exposed on the
        DCC ``Slots`` base precisely so the slots layer never imports uitk
        directly (see ``slots/_slots.py``).
        """
        if getattr(item, "sublist", None) and item.sublist.get_items():
            return
        call = getattr(item, "call_slot", None)
        if callable(call):
            call()

    # --------------------------------------------------- tb002  fix non-orthogonal
    # What freezing/baking actually does to the object in this DCC — shown in
    # the confirmation so the user knows the side effect before committing.
    NON_ORTHOGONAL_FIX_EFFECT = ""

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
        shown, dropped = (
            rows[: self._TB002_REPORT_LIMIT],
            rows[self._TB002_REPORT_LIMIT :],
        )

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
