# !/usr/bin/python
# coding=utf-8
"""Substance Bridge: run a script in Substance Painter on the selection or a project.

One Slots class for both hosts, on the bridge panels' shared base
(:class:`HostBridge`: parameter rows, presets, log pane, Output Dir row, Scope and
the Bake Source row). The engine is the host toolkit's ``SubstanceBridge``
(``self.tk.SubstanceBridge``): it exports the selection when the script works on a
mesh, finds the Painter the script runs in (by its instance record, or a launch)
and queues it there over the ``substance_rpc`` plugin. Its parameter registry,
script folders, ``(script, mode)`` list and script headers are the engine's. This
module owns the help text, the preferred script, the Painter row's live entries,
the Output Dir row's clear button, the Texture Affix row's greying, the ``b000``
send and the wait on Painter's answer (off the host's main thread).
"""

import traceback
from pathlib import Path

import pythontk as ptk

from ._app_bridge.host_bridge import HostBridge


class SubstanceBridgeSlots(HostBridge):
    UI_NAME = "substance_bridge"
    LOG_TAG = "substance_bridge"
    # A blank field is never filled in by the panel, in either mode: the
    # bridge puts the mesh Painter's project is built from (and an Update
    # Mesh overwrites) in the scene project's cache/substance, and the
    # manifest + staged texture copies in a fresh temp folder per send.
    TRANSIENT_OUTPUT_MODES = (ptk.SEND_TO, ptk.ROUND_TRIP)

    # The Output Dir is a per-run hand-off location, not durable config: leaving
    # it blank leaves the destinations to the bridge (above), which is right
    # far more often than whatever was typed in some earlier session. A
    # restored path silently outranks that per-run default, so the field starts
    # blank each session -- the recent-values button still holds the history.
    OUTPUT_DIR_PERSISTS = False

    #: The scripts that replaced the old templates (their presets carried
    #: once): ``import`` -> New Project, ``reimport`` -> Update Mesh; ``render``
    #: (an unverified JS body) has no successor.
    FORMER_TEMPLATES = {"import": "new_project", "reimport": "update_mesh", "render": None}

    # Install in Painter / Uninstall from Painter: uitk's, from the engine's RPC_PLUGIN.
    HEADER_MENU_ITEMS = HostBridge.HEADER_MENU_ITEMS + (
        (
            "Cancel Script",
            "btn_cancel_script",
            "Ask Painter to stop the running script: a queued one never starts, a bake "
            "under way stops.",
            "cancel_script",
        ),
    )

    HELP_SPEC = {
        "title": "Substance Bridge",
        "body": "Run a script in Substance Painter: a built-in one or your own, "
        "each a Python file Painter runs as written. A script on a mesh exports "
        "the selection first (FBX, or USD per <b>Format</b>); a script on a "
        "project runs on the one named in <b>Project</b>, else the one open in "
        "Painter.",
        "steps": [
            "Pick a script from the dropdown (its description is logged).",
            "Select the objects for a script on a mesh (New Project, Update Mesh).",
            "Set its rows; <b>Painter</b> picks where it runs (Auto finds the "
            "Painter holding the project).",
            "Click <b>Run in Painter</b>: the log follows the script to its end.",
        ],
        "sections": [
            (
                "Scripts",
                [
                    "<b>New Project</b> — a project from the selection, its mesh "
                    "maps on their own texture sets.",
                    "<b>Update Mesh</b> — the selection re-exported over the mesh the "
                    "last send recorded, reloaded in the Painter holding that "
                    "project (paint kept where UVs match).",
                    "<b>Bake Lighting to Diffuse</b>, <b>Bake Mesh Maps</b>, "
                    "<b>Export Textures</b> — on a project.",
                ],
            ),
        ],
        "notes": [
            "<b>Your Painter</b>: <i>Install in Painter</i> (Utilities) puts the "
            "<i>substance_rpc</i> plugin in Painter's plugins folder, ticked in "
            "Painter's <i>Python</i> menu; a Painter you open then runs a script "
            "only when you click Run, and its edits are in Painter's undo history, an entry per step named for the script. "
            "Untick it there to switch it off. A Painter this panel launches "
            "loads the plugin on its own.",
            "<b>Bake Source</b> — define the set once with <b>Set From "
            "Selection</b> and every New Project / Update Mesh ships it as a "
            "companion <i>&lt;name&gt;_source.fbx</i>, set as Painter's "
            "<i>Hipoly Mesh</i>. The set's contents ARE the switch. It lives in "
            "the scene, so it survives saves and restarts and is independent of "
            "the <b>Scope</b>.",
            "Your own scripts: <i>Copy to My Scripts</i> on the dropdown's menu "
            "copies the selected one into your folder to edit; a script reads its "
            "values from <code>args</code>, shows panel rows with "
            "<code>__KEY__</code> tokens in a <code># Rows:</code> line and "
            "declares its own with <code># Row: __KEY__ int 4 \"Label\"</code>.",
        ],
    }

    def __init__(self, switchboard):
        self._running = None  # the send whose job the panel follows
        self._starting = False  # a send waiting on Painter (starting, opening the project)
        super().__init__(switchboard)
        self._carry_former_presets()
        self._wire_texture_affix_dependency()
        self.refresh_painters()

    # ------------------------------------------------------------------ engine
    @property
    def bridge_class(self):
        return self.tk.SubstanceBridge

    def select_initial_template_index(self, pairs):
        """Default the panel to ``new_project (send_to)`` when it is available."""
        pref = ("new_project", ptk.SEND_TO)
        return pairs.index(pref) if pref in pairs else 0

    def cmb000_init(self, widget) -> None:
        """The base's script combo, which reads a row saved before the scripts
        replaced the templates by that row's old script, never the new list's
        script at that row (``legacy_items``: the old list, each to its
        successor)."""
        super().cmb000_init(widget)
        old = ("bake_lighting", "import", "reimport", "render")  # the list it saved a row of
        widget.legacy_items = tuple(
            None if self.FORMER_TEMPLATES.get(t, t) is None else f"{self.FORMER_TEMPLATES.get(t, t)} ({ptk.SEND_TO})"
            for t in old
        )

    #: Marks the preset folder whose former templates' presets were carried
    #: (a dotfile, which ``carry_presets`` never copies as a preset).
    FORMER_CARRIED_MARKER = ".former_templates_carried"

    def _carry_former_presets(self) -> None:
        """Copy presets saved under a former template's name to its script
        (:attr:`FORMER_TEMPLATES`), once: one already there wins, and the marker
        written after keeps a preset the person deletes later deleted."""
        try:
            manager = self.sb.PresetManager
            root = Path(self.PRESETS_ROOT)
            folder = root if root.is_absolute() else Path(manager.get_presets_root()) / root
            marker = folder / self.FORMER_CARRIED_MARKER
            if marker.exists():
                return
            manager.carry_presets(self.PRESETS_ROOT, self.PRESETS_ROOT, self.FORMER_TEMPLATES)
            folder.mkdir(parents=True, exist_ok=True)
            marker.write_text("", encoding="utf-8")
        except Exception:  # noqa: BLE001 -- a preset left behind never blocks the panel
            pass

    def _on_template_changed(self) -> None:
        super()._on_template_changed()
        self.refresh_painters()

    # ----------------------------------------------------------------- Painters
    def refresh_painters(self) -> None:
        """The Painter row's entries: Auto, New Painter, and every running
        Painter serving the plugin, by the project it holds."""
        widget = self._param_widgets.get("PAINTER")
        if widget is not None:
            # By the Painter's id, never its row: the list is the Painters
            # running now, so a saved row would land on another one.
            widget.restore_by = "data"
            self._set_param_choices("PAINTER", self.bridge_class.painter_choices())

    def cancel_script(self) -> None:
        """Ask Painter to stop the script this panel is following."""
        if self._running is None:
            self.bridge.logger.info("No script is running in Painter.")
            return
        self.bridge.cancel(self._running)

    # -------------------------------------------------------------- output dir
    def _configure_output_dir_options(self, edit) -> None:
        """Base buttons (recent history + browse) plus a clear button.

        Blank is a *meaningful* state for this field -- ``require_output_dir``
        reads it as "the bridge decides" (the project cache for the mesh, temp
        for the rest) -- so unlike a browse-only path field the clear button
        reaches a real setting rather than just breaking the value. Pairs with
        ``OUTPUT_DIR_PERSISTS = False``: clearing it is how the user gets back
        to the per-run default within a session, and the next session starts
        there anyway.
        """
        super()._configure_output_dir_options(edit)
        edit.option_box.clear_option = True

    # ----------------------------------------------------------- texture affix
    #: Why ``Texture Affix`` greys out: one string, not one per call site.
    _AFFIX_DISABLED_REASON = (
        "Only applies to textures the send stages — turn <b>Include Textures</b> on."
    )

    def _wire_texture_affix_dependency(self) -> None:
        """Grey out ``Texture Affix`` while ``Include Textures`` is off.

        The affix only renames files the staging step copies, so it means
        nothing with staging off. Routed through ``set_param_enabled`` rather
        than the widget's own ``setEnabled``: the affix row is a text field
        WRAPPED in an option box, so disabling the field alone leaves its two
        icon buttons (the mode cycle, the clear) live beside a greyed-out
        value -- and gives the row no reason for the state. The base walks the
        row instead, which covers the whole cell.

        Either row is skipped when the registry does not build it, so a panel
        over a registry without them stays usable.
        """
        include_widget = self._param_widgets.get("PAINTER_INCLUDE_TEXTURES")
        if include_widget is None or "PAINTER_TEXTURE_AFFIX" not in self._param_widgets:
            return
        kinds = self.sb.KindFactory

        def _sync(_value=None):
            enabled = bool(kinds.read_value(include_widget))
            self.set_param_enabled(
                "PAINTER_TEXTURE_AFFIX",
                enabled,
                "" if enabled else self._AFFIX_DISABLED_REASON,
            )

        kinds.connect_changed(include_widget, _sync)
        _sync()

    # ------------------------------------------------------------- b000: send
    def b000(self):
        """Run the chosen script: export the Scope's objects first when it
        works on a mesh, then follow its job in Painter off the main thread."""
        pair = self._selected_template_mode()
        if not pair:
            self.bridge.logger.warning("No script chosen. Pick one from the dropdown above.")
            return
        template, mode = pair
        if self._starting:
            self.bridge.logger.warning("Painter is still starting or opening the project: Run again once the script is queued.")
            return None
        if self._running is not None:
            # The panel follows one job: a second would take its place, and
            # Cancel Script would reach the wrong one.
            self.bridge.logger.warning(
                "A script is still running in Painter: Run again when it ends, or stop it first (Cancel Script)."
            )
            return None

        # A script on a project works on one Painter already holds (or the
        # Project row's): no selection needed, and no warning for its absence.
        meta = self.bridge_class.parse_template(self.template_path(template))
        needs_selection = meta.get("WORKS_ON") in ("new", "mesh")
        params = self.collect_param_values()
        selection = self.scoped_objects(params, warn=needs_selection) if needs_selection else []
        if needs_selection and not selection:
            return

        if not self.bridge.painter_path:
            # The spec's sentence, not a panel-local copy: the engine's ``APP``
            # owns it, and the menu gate that greys this tool's entry shows
            # the same one.
            self.bridge.logger.error(self.bridge.APP.not_found_message)
            return

        output_dir = self.require_output_dir(mode)
        if output_dir is None:
            return

        label = self.bridge_class.label(template)
        # The log accumulates across runs (the header menu's Clear Log resets
        # it); this line separates one operation from the next.
        self.bridge.logger.info(f"--- {label} ({mode}) on {len(selection)} object(s) ---")
        try:
            with self.sb.progress(text=f"Working: {label}"):
                result = self.bridge.send(
                    objects=selection,
                    template=template,
                    mode=ptk.SEND_TO,  # queued here; the wait below is off the main thread
                    target=params.get("PAINTER") or "auto",
                    output_dir=output_dir,
                    params=params,
                    background=self._in_background,
                    on_queued=lambda queued: self._queued(queued, label),
                )
        except Exception:
            self.bridge.logger.error("Bridge raised:\n" + traceback.format_exc())
            return
        if result and result.get("pending"):
            self._starting = True  # until _queued
            return None  # Painter is starting or opening the project: _queued follows
        return self._queued(result, label)

    def _in_background(self, work, then):
        """The engine's waits (a launched Painter serving, a project opening)
        off the UI thread; *then* gets what *work* returned, on it."""
        task = self.sb.BackgroundTask(work, "substance-deliver")
        task.when_done(self.ui, lambda: then(task.result()))

    def _queued(self, result, label):
        """Follow the queued script's job, when there is one."""
        self._starting = False
        if result and result.get("job"):
            return self._watch(result, label)
        return None

    def _watch(self, result, label):
        """Follow the script's job in Painter off the UI thread (a bake runs for
        minutes; the engine's ``follow`` says nothing there), then let the
        engine say how it ended, on the UI thread. The panel and its host stay
        live."""
        footer = getattr(self.ui, "footer", None)
        task = self.sb.BackgroundTask(lambda: self.bridge_class.follow(result), "substance-script")

        def done() -> None:
            if self._running is result:
                self._running = None
            status = self.bridge.conclude(task, job=result.get("job"))
            if footer is not None:
                footer.finish_progress(f"{label}: {status.get('state', 'failed')} in Painter.")
            self.refresh_painters()

        self._running = result
        try:
            if footer is not None:
                footer.start_progress(text=f"{label}: running in Painter…")
            task.when_done(self.ui, done)
        except Exception:
            # Nothing follows the job now: the panel must not go on waiting for
            # it, nor its footer say it is running.
            self._running = None
            if footer is not None:
                footer.finish_progress(f"{label}: queued in Painter, not followed.")
            raise
        return task
