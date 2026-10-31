# !/usr/bin/python
# coding=utf-8
"""Slots for the WebXR Preview panel — the single UI for the live preview.

One panel serves every source. Standalone it previews files on disk, driven by
:class:`pythontk.FilePreviewBridge`, and there is no Source combo -- one entry
is no choice, so it hides. A host that opened it injects its own bridge
(:attr:`WebXrPreviewSlots.engine` — ``mtk.WebXrPreview`` / ``btk.WebXrPreview``)
and the combo appears with that host's scopes above File on Disk. Which source
is active changes *which bridge produces the payload* and nothing else: the
build, the texture pass, the version bump and the page are one chain either
way, which is why the panel body carries no per-host branch. The rows follow
what the push will build (:meth:`WebXrPreviewSlots._relevant_param_keys`), so
the hosted panel is the standalone one plus the rows a scene answers.

**Lookdev, not validation.** A push is the hand-off mixin's FBX write -- fast,
no export tasks or checks -- but the GLB is built by ``pythontk.GlbPipeline``,
the SAME chain a Scene Exporter's GLB goes through. What the page shows is what
the target platform receives for everything that lives in the file. To check an
exporter's whole run, export the GLB and pick it as the Source File.

The host injection point is the pattern uitk documents for this
(``ExternalAppHandler.launch(..., show=False)`` returns the widget so a caller
can set context before it is shown) and that the Map Converter panel already
uses: the panel owns the Source picker, the host owns what each scope means.
"""

from __future__ import annotations

import os
import traceback
import webbrowser
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pythontk as ptk
from qtpy import QtCore

from tentacle import Slots

from ._webxr_preview import parameters as _params


#: Source key for "publish a file already on disk". Not a scope in the shared
#: sense -- it resolves no host objects and no other hand-off could honour it --
#: which is exactly why it is NOT pushed into ``Parameters.scope_spec``.
FILE_SOURCE = "file"

#: Where the pipeline is documented, channel by channel. Deliberately NOT built
#: from ``extapps.DOCS_BASE_URL`` the way every other panel's docs link is: this
#: panel is a UI over an engine that lives in pythontk, and the document that
#: explains what survives the trip lives with that engine. Pointing at an
#: extapps path would mean either a stub to maintain or a broken link.
_DOCS_URL = "https://github.com/m3trik/pythontk/blob/main/docs/webxr_preview.md"


class _Scene:
    """One scene the panel publishes -- and shares, at a link of its own.

    The first is the panel's own bridge and the Source Files row; each one the
    row's + adds (:meth:`WebXrPreviewSlots.add_scene`) is a file bridge with a
    deliverer of its own -- its own server, port, page and share -- and *row*,
    ``(container, files field, label)``. A share being opened is per scene:
    *pending*, the row *choice*, *provider* and *private* it was opened for,
    the provider's *step* it waits on, and *stops*, so a wait a stop ended
    ends quietly. *reach* is the last link check's answer (``None``
    unchecked); *recheck* the timer checking a link that did not open.
    """

    def __init__(self, bridge, row: Optional[tuple] = None):
        self.bridge = bridge
        self.row = row
        self.stops = 0
        self.reach: Optional[Dict[str, Any]] = None
        self.recheck = None
        self.clear_wait()

    def clear_wait(self) -> None:
        """No share opening: not pending, and nothing it was opened for."""
        self.pending = False
        self.choice: Optional[str] = None
        self.provider: Optional[str] = None
        self.private: Optional[bool] = None
        self.step = None

    def end_wait(self) -> bool:
        """Forget a share still opening, which the stop about to run ends
        (its outcome then stays silent), and the link's checks; whether one
        was opening."""
        opening = self.pending
        self.stops += 1
        self.clear_wait()
        self.reach = None
        self.stop_recheck()
        return opening

    def stop_recheck(self, timer=None) -> None:
        """End the link's re-checks -- only *timer*'s, when named."""
        current = self.recheck
        if current is None or (timer is not None and current is not timer):
            return
        self.recheck = None
        current.stop()
        current.deleteLater()

    @property
    def server(self):
        """The scene's server, or ``None`` before anything started one."""
        deliverer = getattr(self.bridge, "deliverer", None)
        return getattr(deliverer, "server", None) if deliverer else None

    def share_info(self) -> Optional[Dict[str, Any]]:
        server = self.server
        return server.share_info() if server is not None else None


class WebXrPreviewSlots(Slots.BridgeSlotsBase):
    """Switchboard slots wired to ``webxr_preview.ui``."""

    UI_NAME = "webxr_preview"
    #: Saved data: the folder the panel's presets have always been kept in.
    PRESETS_ROOT = Path("extapps/webxr_preview")
    LOG_TAG = "webxr_preview"

    # There is no user-facing artifact directory: the deliverable is served
    # from the preview's own root and the FBX is scratch the push consumes.
    REQUIRE_OUTPUT_DIR = False

    # The combo picks a MODE, not a template file, and ``template_dir`` is
    # this package's own directory -- so the template-management rows would
    # offer to re-scan nothing and to reveal source code.
    TEMPLATE_MENU = False

    DOCS_URL = _DOCS_URL
    DOCS_LABEL = "How the preview pipeline works"

    #: How often the footer re-reads who is watching while the panel shows.
    STATUS_REFRESH_MS = 2000

    HEADER_MENU_ITEMS = (
        (
            "Open Preview Page",
            "btn_open_page",
            "Open the preview in a browser tab.\n\n"
            "A push opens one for you when nothing is watching, so this is for "
            "getting a second view -- or getting the page back after closing "
            "it without paying for another push.",
            "open_preview_page",
        ),
        (
            "Stop Server",
            "btn_stop_server",
            "Stop serving and release the port.\n\n"
            "The server outlives every push on purpose, so a page left open in "
            "a headset keeps receiving them. Stop it only to free the port; "
            "the next push starts a new one. A page left open says the server "
            "is unreachable until then, and resumes if its server returns on "
            "the same port: the first scene's usually does, an added scene's "
            "does not.",
            "stop_server",
        ),
        ("Clear Log", "btn_clear_log", "Clear the log panel below.", "clear_log"),
    )

    # One card for both launches: a DCC-only line says so, since standalone
    # (and a host left on File on Disk) is files only. Detail lives in the
    # DOCS_URL page the card links.
    HELP_SPEC = {
        "title": "WebXR Preview",
        "body": "Publish a model to a live browser page and keep pushing: an "
        "open tab -- one in a PC-tethered headset too -- swaps to each new "
        "version on its next poll, with no reload. On its own it previews "
        "<b>FBX</b> and <b>GLB</b> files; opened from Maya or Blender it can "
        "push the scene as well.",
        "steps": [
            "Choose the <b>Source Files</b> (or leave the field empty and Push "
            "asks). Several files are the parts of one scene; the page's "
            "<b>View</b> menu can hide each.",
            "<i>From Maya or Blender:</i> the <b>Source</b> list on top offers "
            "Selected, Entire Scene or Visible Only, then File on Disk.",
            "Click <b>Push to Preview</b>. A tab opens when none is watching; "
            "after that, push and look up.",
        ],
        "sections": [
            (
                "Rows",
                [
                    "A row shows only when the push reads it. The "
                    "<b>Textures</b> rows need an FBX (a GLB is published "
                    "exactly as authored) or a scene pushed with its textures.",
                    "<i>Scene push only:</i> <b>Delivery</b> and <b>Include "
                    "Textures</b>. Set the texture rows as the Scene "
                    "Exporter's are set and the preview matches the export.",
                    "<b>+</b> beside Source Files adds another scene with its "
                    "own page and link; <b>\u2212</b> removes one. Push "
                    "publishes them all.",
                ],
            ),
            (
                "Sharing",
                [
                    "<b>Sharing</b> (Auto or a provider) publishes a view-only "
                    "HTTPS link anyone can open in a browser -- a standalone "
                    "headset too -- except the tailnet-only Tailscale option. "
                    "It stays up across pushes; <b>Off</b> takes it down, and "
                    "its option box copies and tests the link.",
                    "A link no one else can open yet shows in <b>red</b> and is "
                    "re-checked for 15 minutes: a new Tailscale Funnel link "
                    "takes minutes to open, a Cloudflare one seconds.",
                    "A guest can save the GLB: stop sharing when the review is over.",
                ],
            ),
        ],
        "notes": [
            "The page is served on 127.0.0.1, so any other device needs a share.",
            "<i>Scene push:</i> lookdev, not an export -- no export tasks or "
            "checks. To check an export, push the GLB it wrote from File on "
            "Disk.",
            "Closed the tab? <b>Open Preview Page</b> in the header menu "
            "brings it back without a push.",
        ],
    }

    # ------------------------------------------------------------------ init
    def __init__(self, switchboard, **kwargs):
        #: The host's bridge CLASS, injected by whoever opened this panel.
        #: A class rather than an instance so construction stays lazy -- and so
        #: a host that opens the panel eagerly at startup pays nothing.
        self._engine = kwargs.get("engine", None)
        self._host_bridge = None
        self._status = None
        #: Every scene this panel publishes, the first the panel's own bridge
        #: (:class:`_Scene`); the Source Files row's + adds the rest.
        self._scenes: List[_Scene] = []
        self._scene_serial = 0
        self._initial_source_file: str = kwargs.get("source_file", "") or ""
        super().__init__(switchboard)
        self._scenes.append(_Scene(self.bridge))
        # The added scenes' servers are this panel's alone: they go with it.
        scenes = self._scenes
        self.ui.destroyed.connect(lambda *_: [s.bridge.stop() for s in scenes[1:]])
        # By LABEL, not position. The list is host-dependent -- File on Disk is
        # entry 0 without a host and entry 3 with one -- so a stored index means
        # a different source in each, and the host's scopes arrive only after
        # this combo has already restored (see _populate_sources).
        self.ui.cmb000.restore_by = "text"
        # A hand-off, not a preference: a path restored from last session would
        # be pushed by the press that is meant to ask for a file, and it would
        # outrank a host's ``source_file``. Explicit, because registration
        # defaults every widget without the attribute to restoring.
        self._source_edit().restore_state = False
        self.sb.KindFactory.connect_changed(
            self._param_widgets["LOCOMOTION"], self._apply_locomotion
        )
        # The rows follow what the push will build (_relevant_param_keys): the
        # files chosen, whether a scene's images ride, and the container the
        # KTX2-only rows need. A refresh that changes no row is a no-op.
        for key in (
            "SOURCE_FILE",
            "EMBED_TEXTURES",
            "TEXTURE_FILE_TYPE",
        ):
            self.sb.KindFactory.connect_changed(
                self._param_widgets[key],
                lambda _value: self._refresh_param_visibility(),
            )
        self._build_sharing_row()
        self._build_scene_controls()
        self.sb.KindFactory.connect_changed(
            self._param_widgets["SHARE_PRIVATE"], self._private_changed
        )
        self._adopt_host_deliverer()
        self._restore_sharing()  # after: a live share's row wins
        self._build_status_row()
        if self._initial_source_file:
            self.set_source_file(self._initial_source_file)

    # ------------------------------------------------------------------ base hooks
    @property
    def params_module(self):
        return _params.Parameters

    @property
    def template_dir(self) -> Path:
        # No script templates -- this bridge renders nothing. The package dir
        # is a harmless stand-in for the (no-op) per-template description
        # lookup, matching the Unity panel's treatment of the same hook.
        return Path(__file__).resolve().parent

    def make_bridge(self):
        """The panel's own, host-free engine.

        Deliberately the FILE bridge rather than the host's, for two reasons.
        It is always constructible, so ``self.bridge`` is valid the moment the
        panel opens and the base's log redirect binds to a real logger. And it
        is the one bridge that exists in every host, so the panel's own plumbing
        never has to ask whether a DCC is present.

        The host's bridge is built separately (:meth:`_host`), on first use.
        """
        return ptk.FilePreviewBridge()

    # ------------------------------------------------------------------ sources
    @property
    def engine(self):
        """The host bridge class this panel pushes scopes through, or ``None``.

        The injection point for a host: launch the app with ``show=False``, set
        this, then show. Assigning it re-populates the Source combo, so a host
        can hand the panel its bridge at any point in the panel's life.
        """
        return self._engine

    @engine.setter
    def engine(self, value) -> None:
        if value is self._engine:
            return
        self._engine = value
        # Drop any bridge built from the previous engine -- keeping it would
        # push through the old host after the panel was re-pointed.
        self._host_bridge = None
        self._adopt_host_deliverer()
        self._populate_sources()
        self._refresh_status()

    def _host(self):
        """The host bridge, built once, or ``None`` when running host-free.

        Lazily constructed so the panel costs a DCC nothing until a scope is
        actually pushed, and kept for the panel's life so the host's own
        deliverer -- and therefore the port and the open tab -- survive.
        """
        if self._engine is None:
            return None
        if self._host_bridge is None:
            self._host_bridge = self._engine()
            self._bind_logger(self._host_bridge)
        return self._host_bridge

    def _adopt_host_deliverer(self) -> None:
        """Point the file bridge at the host's deliverer, so ONE server serves
        the panel.

        Done the moment the engine is known rather than when a scope is first
        pushed, and the difference is not cosmetic. Deferring it to the lazy
        host-bridge build was the first implementation and it was measurably
        wrong: a FILE push never reaches that build, so each source started its
        own server -- the file landed on one port while the footer, and the
        user's open tab, were still on the first. A push that reports success
        onto a page nobody is looking at is worse than one that fails.

        The HOST's deliverer wins rather than the reverse because it is a class
        attribute on its bridge, so it outlives this panel: that is what keeps
        the port and the open tab alive across panel reopens for the whole DCC
        session. Read off the CLASS, so no bridge is constructed to do it.
        """
        deliverer = getattr(self._engine, "deliverer", None) if self._engine else None
        if deliverer is not None:
            # An INSTANCE attribute, shadowing FilePreviewBridge's class-level
            # one: this panel's file bridge follows the host, and every other
            # user of that class keeps its own.
            self.bridge.deliverer = deliverer
        else:
            # Symmetric on the way out. A panel re-pointed at no host (or at
            # one with no deliverer) would otherwise keep publishing through
            # the PREVIOUS host's server -- the same disagreement between the
            # footer and the push, arrived at from the other direction.
            # Deleting the instance attribute re-exposes the class default
            # rather than inventing a new deliverer, so a server this panel
            # already started stays the one it uses.
            self.bridge.__dict__.pop("deliverer", None)
        # The Locomotion row follows the deliverer it now publishes through,
        # and the Sharing row shows a share that deliverer's server already has.
        self._apply_locomotion(
            self.sb.KindFactory.read_value(self._param_widgets["LOCOMOTION"])
        )
        self._show_live_share()

    def _apply_locomotion(self, on) -> None:
        """The Locomotion row, applied at once rather than at the next push.

        The switch is the page's, read on every poll (``manifest.locomotion``),
        so a headset mid-session -- a share's guests included -- stops or
        starts going anywhere a second after the box changes, with no
        re-export: the running server takes it now, and the deliverer keeps it
        for every later publish, which re-applies it.
        """
        added = [scene.bridge.deliverer for scene in getattr(self, "_scenes", [])[1:]]
        for deliverer in [self._deliverer(), *added]:
            if deliverer is None:
                continue
            deliverer.locomotion = bool(on)
            server = getattr(deliverer, "server", None)
            if server is not None:
                server.locomotion = bool(on)

    def _deliverer(self):
        """The one deliverer this panel's pushes land on, whatever the source.

        A single read, not a choice: :meth:`_adopt_host_deliverer` has already
        made the file bridge share the host's. Anything that picked a deliverer
        a second way here could disagree with the push, which is precisely the
        failure that made the footer describe a different server than the one
        being written to.
        """
        return getattr(self.bridge, "deliverer", None)

    def _server(self):
        """That deliverer's server, or ``None`` before anything started one."""
        deliverer = self._deliverer()
        return getattr(deliverer, "server", None) if deliverer else None

    def _bind_logger(self, bridge) -> None:
        """Route *bridge*'s logger into the panel's log pane.

        The base binds only ``self.bridge``'s logger, once, in its constructor.
        The host bridge is built later and is a different logger, so without
        this everything a scope push reports -- the sidecar outcome, the
        lightmap misses, the conversion's own errors -- would go to the DCC's
        script editor and the panel would look like it did nothing.
        """
        try:
            handler_cls = self.sb.registered_widgets.TextEditLogHandler
            logger = bridge.logger
            logger.hide_logger_name(True)
            logger.set_text_handler(handler_cls)
            logger.setup_logging_redirect(self.ui.txt000)
        except (AttributeError, RuntimeError):  # no redirect available
            pass

    def _sources(self) -> List[Tuple[str, str]]:
        """``(key, label)`` for every source this panel can offer right now.

        The host scopes come off the SHARED spec rather than a list written
        here: scope is the same control every other hand-off bridge offers, so
        reading the spec means this panel's vocabulary cannot fork from theirs.
        File on Disk is appended last -- alone without a host, where the combo
        hides (one entry is no choice). The combo persists by label, so neither
        the order nor a host's presence changes what a stored choice means.
        """
        entries: List[Tuple[str, str]] = []
        if self._engine is not None:
            for label, value in self.sb.Parameters.scope_spec().choices:
                entries.append((value, label))
        entries.append((FILE_SOURCE, "File on Disk"))
        return entries

    def list_template_modes(self) -> List[Tuple[str, str]]:
        """Sources, in the ``(template, mode)`` shape the base's combo reads."""
        return [(key, "") for key, _label in self._sources()]

    def _format_combo_label(self, template: str, mode: str) -> str:
        return dict(self._sources()).get(template, template)

    def _populate_sources(self) -> None:
        """Rebuild the Source combo after the host bridge changed.

        ``refresh_templates``, NOT ``cmb000_init``. The init hook is a
        Switchboard one-shot: it connects ``currentIndexChanged`` and adds the
        combo's menu chrome, so calling it again stacks a second connection and
        a second set of menu buttons. Measured before the fix -- one index
        change fired the change handler five times, and it would have grown
        with every host that re-pointed the panel. The base's own refresh does
        the repopulate half alone, which is all that changed here.

        The stored choice is re-applied afterwards, because it could not be
        before: the combo restores when the panel is built, and a host injects
        its scopes only after that (``launch(show=False)``, then ``engine =``).
        A stored scope missing from the list is skipped, and this repopulate
        then reset the combo to its first entry -- every session opened on
        Selected whatever was last picked. Every change is saved as it happens,
        so the store IS the last deliberate choice.
        """
        try:
            self.refresh_templates()
            restore = getattr(self.ui.cmb000, "perform_restore_state", None)
            if restore is not None:  # a combo not registered with a window
                restore(force=True)
        except Exception:  # noqa: BLE001 - a repopulate must never take the panel down
            self.sb.logger.debug("source combo repopulate failed", exc_info=True)

    def _active_source(self) -> str:
        pair = self._selected_template_mode()
        return pair[0] if pair else FILE_SOURCE

    def _relevant_param_keys(self) -> Optional[set]:
        """Which rows the push the panel would make now actually reads.

        Explicit rather than file-driven: this panel renders no templates, and
        visibility must never depend on the absence of a file in the package
        dir. A file source exports nothing, so the export rows are not merely
        unused -- they would be lying. The same holds a level down: no texture
        row is read by a push that re-encodes no image, and KTX2 RDO means
        nothing without a KTX2 container.
        """
        # Only the rows built so far: visibility is asked during construction.
        values = self.collect_param_values()
        keys = set(self.params_module.PARAMS)
        if not self._texture_pass_runs(values):
            keys -= _params.TEXTURE_KEYS
        elif not self._encodes_ktx2(self._glb_options(values)):
            keys -= _params.KTX2_KEYS
        if self._active_source() == FILE_SOURCE:
            return keys - _params.EXPORT_KEYS
        return keys - _params.FILE_KEYS

    def _texture_pass_runs(self, values: Dict[str, Any]) -> bool:
        """Whether a push of the active source with *values* re-encodes an
        image -- the work the texture rows set.

        A scope's images ride its export only with Include Textures on. A file
        source re-encodes only an FBX among its files: a GLB is published as
        authored, and an empty field shows no texture row -- the rows come
        with the FBX that reads them, and a push gates on the files it was
        actually handed (:meth:`b000` resolves them first).
        """
        if self._active_source() != FILE_SOURCE:
            return bool(values.get("EMBED_TEXTURES", True))
        paths = list(values.get("SOURCE_FILE") or [])
        for scene in getattr(self, "_scenes", [])[1:]:
            paths += self._row_paths(scene.row[1])
        return any(
            Path(path).suffix.lower() != _params.AUTHORED_EXTENSION for path in paths
        )

    @staticmethod
    def _encodes_ktx2(glb_options: Dict[str, Any]) -> bool:
        """Whether *glb_options* resolve to the KTX2 container -- read the way
        the push reads them (``ExportRun.for_glb``), so both KTX2 entries,
        alone and with its twin, answer yes and nothing else does."""
        run, _notes = ptk.ExportRun.for_glb(glb_options)
        return run.texture_file_type == "ktx2"

    # ------------------------------------------------------------------ status row
    def _build_status_row(self) -> None:
        """Bind the footer to a live description of what the page is showing.

        A push reports its outcome in the log, but the *standing* facts -- is
        anything watching, which version is live, on what port -- are state,
        not events, and an option box had nowhere to put them. This is the
        half of the feature that was previously invisible: 'no bake', 'bake
        not found' and 'nothing is watching' all render as the same dark room.
        """
        try:
            self._status = self.ui.footer.status_controller(
                resolver=self._status_text,
                default_text="No preview server running.",
            )
        except (AttributeError, RuntimeError):
            return  # a UI without a footer still works, it just says less
        # Who is watching changes with nothing done in the panel -- a guest
        # opens the link, the owner closes the tab -- so the line is re-read
        # while the panel shows. All of it is in memory.
        self._status_timer = QtCore.QTimer(self.ui)
        self._status_timer.setInterval(self.STATUS_REFRESH_MS)
        self._status_timer.timeout.connect(self._refresh_shown_status)
        self._status_timer.start()

    def _refresh_shown_status(self) -> None:
        if self.ui.isVisible():
            self._refresh_status()

    def _status_text(self) -> str:
        """One line describing the live preview -- every scene's, in order."""
        parts = [self._scene_status(scene) for scene in self._scenes]
        if len(parts) == 1:
            return parts[0]
        return " | ".join(f"Scene {i}: {part}" for i, part in enumerate(parts, 1))

    def _unreachable_scenes(self) -> List[_Scene]:
        """Scenes shared at a link whose last check found it closed to guests."""
        return [
            scene
            for scene in self._scenes
            if scene.reach is not None
            and not scene.reach.get("ok")
            and scene.share_info() is not None
        ]

    def _scene_status(self, scene: _Scene) -> str:
        server = scene.server
        # A Sharing row that is on with no link up and none opening -- a
        # remembered row before the first push, a share that dropped -- is
        # armed: the next push brings the link up, and the footer says so.
        armed = self._sharing_choice() != "off" and not scene.pending
        if server is None or not getattr(server, "url", ""):
            note = " · shares with the first push" if armed else ""
            return f"No preview server running{note}."
        try:
            # Not manifest(): that reads the OpenXR runtime from the registry,
            # every time -- and the footer re-reads this every few seconds.
            version = server.version
            share = server.share_info()
        except Exception:  # noqa: BLE001 - the footer must never raise
            version, share = "?", None
        watching = "watching" if server.has_viewer() else "nothing watching"
        text = f"v{version} · {watching} · {server.url}"
        if share:
            guests = share["guests"]
            text += f" · shared at {share['url']} ({guests} guest{'s' * (guests != 1)})"
            if scene.reach is not None and not scene.reach.get("ok"):
                text += " -- NOT reachable from outside"
        elif scene.step is not None:
            text += f" · sharing once {scene.step.label} is enabled"
        elif armed:
            text += " · shares with the next push"
        return text

    def _refresh_status(self) -> None:
        """Re-run the footer resolver; a no-op on a UI without a footer."""
        if self._status is not None:
            try:
                self._status.update()
                # Red while a link is up that no one else can open; the
                # update above clears it otherwise.
                if self._unreachable_scenes():
                    footer = self.ui.footer
                    footer.setStatusText(footer.statusText(), "error")
            except RuntimeError:  # the widget went away under us
                pass

    # ------------------------------------------------------------------ header actions
    def open_preview_page(self) -> None:
        """Open the live page in a browser, without paying for a push."""
        server = self._serving()
        if server is not None:
            webbrowser.open(server.url)

    def _serving(self):
        """The running server, or ``None`` -- said in the log: an action that
        needs one has nothing to act on before the first push."""
        server = self._server()
        if server is not None and getattr(server, "url", None):
            return server
        self.panel_log(
            "Nothing is being served yet — push once to start the server.",
            "warning",
        )
        return None

    def stop_server(self) -> None:
        """Stop serving and release the port -- every scene's -- ending any share."""
        running = [scene for scene in self._scenes if scene.server is not None]
        if not running:
            self.panel_log("No preview server is running.", "warning")
            return
        for scene in running:
            scene.end_wait()  # the stop ends the share too
            scene.server.stop()
        if len(running) == 1:
            self.panel_log("Preview server stopped; the port is released.")
        else:
            self.panel_log(
                f"{len(running)} preview servers stopped; their ports are released."
            )
        self._refresh_status()

    # ------------------------------------------------------------------ scenes
    #: The Source Files row's + : what it adds.
    ADD_SCENE_TIP = (
        "Add a scene: another set of files with its own page, its own server "
        "and -- while Sharing is on -- its own link, all live at once. Push "
        "publishes every scene; the rows above it apply to them all."
    )

    def _build_scene_controls(self) -> None:
        """The + on the Source Files row, which adds a scene below it."""
        from qtpy import QtWidgets

        row = self._param_rows.get("SOURCE_FILE")
        if row is None or row.layout() is None:
            return
        button = QtWidgets.QPushButton("+", row)
        button.setObjectName("btn_add_scene")
        button.setFixedSize(19, 19)
        button.setToolTip(self.ADD_SCENE_TIP)
        button.clicked.connect(lambda *_: self.add_scene())
        row.layout().addWidget(button)
        self._add_scene_button = button

    def add_scene(self, paths: Optional[List[str]] = None) -> _Scene:
        """Another scene: a Source Files row of its own under the last one,
        published by its own server -- its own page, port and share link.

        Parameters:
            paths: Files to fill its row with; empty asks nothing until a
                push (an empty added scene is left out of it).

        Returns:
            The scene.
        """
        from qtpy import QtWidgets

        spec = self.params_module.PARAMS["SOURCE_FILE"]
        group = self._param_group
        container = QtWidgets.QWidget(group)
        hbox = QtWidgets.QHBoxLayout(container)
        hbox.setContentsMargins(0, 0, 0, 0)
        hbox.setSpacing(2)
        label = QtWidgets.QLabel("", container)
        label.setMinimumWidth(self.LABEL_MIN_WIDTH)
        label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        field = self.sb.KindFactory.make_widget(spec, container)
        self._scene_serial += 1
        field.setObjectName(f"param_scene_{self._scene_serial}")
        field.setToolTip(self.format_param_tooltip(spec))
        # A hand-off, like the first row's: never restored from last session.
        field.restore_state = False
        remove = QtWidgets.QPushButton("−", container)
        remove.setObjectName(f"btn_remove_scene_{self._scene_serial}")
        remove.setFixedSize(19, 19)
        remove.setToolTip("Remove this scene: its page stops and its link closes.")
        hbox.addWidget(label)
        hbox.addWidget(field, 1)
        hbox.addWidget(remove)

        layout = group.layout()
        anchor = (
            self._scenes[-1].row[0]
            if len(self._scenes) > 1
            else self._param_rows["SOURCE_FILE"]
        )
        layout.insertWidget(layout.indexOf(anchor) + 1, container)

        bridge = ptk.FilePreviewBridge()
        # An INSTANCE deliverer: a server of its own, apart from the first
        # scene's (the class's -- or the host's, adopted).
        bridge.deliverer = ptk.PreviewDeliverer(
            title="Preview",
            locomotion=bool(self.sb.KindFactory.read_value(self._param_widgets["LOCOMOTION"])),
        )
        scene = _Scene(bridge, row=(container, field, label))
        self._scenes.append(scene)
        remove.clicked.connect(lambda *_: self.remove_scene(scene))
        self.sb.KindFactory.connect_changed(
            field, lambda _value: self._refresh_param_visibility()
        )
        if paths:
            self.sb.KindFactory.set_value(field, [str(path) for path in paths])
        self._renumber_scenes()
        self._sync_scene_rows()
        self._refresh_status()
        self.sb.WindowHeight.fit_host_later(group)
        return scene

    def remove_scene(self, scene: _Scene) -> None:
        """Take an added scene away: its server stops, and its link with it."""
        if scene not in self._scenes[1:]:
            return
        tag = self._tag(scene)
        shared = scene.share_info() is not None
        scene.end_wait()
        if scene.server is not None:
            scene.server.stop()
        self._scenes.remove(scene)
        container = scene.row[0]
        container.setParent(None)
        container.deleteLater()
        self._renumber_scenes()
        self.panel_log(
            f"{tag}removed{' -- its link no longer opens' if shared else ''}."
        )
        self._refresh_param_visibility()
        self._refresh_status()
        self.sb.WindowHeight.fit_host_later(self._param_group)

    def _renumber_scenes(self) -> None:
        """Scene N labels, in order; the first row is Source Files when alone."""
        first = self._param_labels.get("SOURCE_FILE")
        if first is not None:
            spec = self.params_module.PARAMS["SOURCE_FILE"]
            alone = len(self._scenes) < 2
            first.setText(f"{spec.display_label}:" if alone else "Scene 1:")
        for number, scene in enumerate(self._scenes[1:], 2):
            scene.row[2].setText(f"Scene {number}:")

    def _sync_scene_rows(self) -> None:
        """Added scene rows show exactly when the Source Files row does --
        for the file source, with its section unfolded."""
        first = self._param_rows.get("SOURCE_FILE")
        shown = first is not None and not first.isHidden()
        for scene in self._scenes[1:]:
            self.sb.FieldVisibility.set_widget_visible(scene.row[0], shown)

    def _refresh_param_visibility(self) -> None:
        super()._refresh_param_visibility()
        if getattr(self, "_scenes", None):
            self._sync_scene_rows()

    def _fold_section(self, section: str, folded: bool) -> None:
        super()._fold_section(section, folded)
        self._sync_scene_rows()

    def _added_scene_files(self) -> List[Tuple[_Scene, List[str]]]:
        """``(scene, files)`` for each added scene a push publishes: one with
        files, all of them on disk -- an empty row is left out, and one naming
        a missing file is said and left out."""
        chosen = []
        for scene in self._scenes[1:]:
            paths = self._row_paths(scene.row[1])
            if paths and not self._missing_files(paths, self._tag(scene)):
                chosen.append((scene, paths))
        return chosen

    def _tag(self, scene: _Scene) -> str:
        """``"Scene N: "`` before a scene's lines while there are several;
        ``""`` for the one scene of a panel without added ones."""
        if len(self._scenes) < 2 or scene not in self._scenes:
            return ""
        return f"Scene {self._scenes.index(scene) + 1}: "

    # ------------------------------------------------------------------ sharing
    #: The Sharing row's option-box actions: ``(label, objectName, tooltip,
    #: handler)``. On the row rather than in the header menu, beside the switch
    #: they act on.
    SHARING_ACTIONS = (
        (
            "Share Now",
            "btn_share_now",
            "Bring the link up now, without a push -- and try again after a "
            "share failed. Picks Auto when the row is Off.",
            "share_link",
        ),
        (
            "Copy Link",
            "btn_copy_share_link",
            "Copy the live link to the clipboard -- every scene's, one per line "
            "-- bringing it up first when the row is on and it is not up.",
            "copy_share_link",
        ),
        (
            "Test Link",
            "btn_test_share_link",
            "Ask the live link for the page the way a guest's browser does -- "
            "through public DNS, to the provider's public door -- and say whether "
            "it answers, and how fast. A link no one else can open is said in red.",
            "check_share_link",
        ),
        (
            "Copy Scene Link",
            "btn_copy_scene_link",
            "Copy the link to this scene as data (scene.json): its glTF and "
            "the lighting it renders with, for a developer's tools or AI agent "
            "to compare with their own scene. View-only, like the share; while "
            "nothing is shared, this machine's own.",
            "copy_scene_link",
        ),
        (
            "Stop Sharing",
            "btn_stop_sharing",
            "Take the link down and set the row to Off. Your own page and the "
            "server are untouched.",
            "stop_sharing",
        ),
    )

    #: Custom-store keys (``StateManager.save_custom``): whether the Sharing
    #: row is remembered across sessions, and the row it remembers. The
    #: window's store, so every host's panel -- and the standalone one --
    #: shares the one answer.
    _REMEMBER_SHARING_KEY = "remember_sharing"
    _SHARING_KEY = "sharing"

    #: How long a link that does not open from outside is checked again, and
    #: how often. A new Tailscale Funnel name reached public DNS 5.5 minutes
    #: after its share began on one run, and on two others was not published
    #: within 8 and 25 (ts.net's own authoritative servers said NXDOMAIN;
    #: measured 2026-10-15, Tailscale 1.102.2); it leaves within a minute of
    #: the share ending, so every Funnel share opens that way. A Cloudflare
    #: quick tunnel's name answers in 6-18 s.
    RECHECK_FOR_S = 900.0
    RECHECK_MS = 15000

    def _build_sharing_row(self) -> None:
        """The Sharing row as the switch, with its actions on its option box.

        Not restored by the widget store: a link is a door to this machine,
        and a session opens it only when asked -- a switch left on yesterday
        would otherwise share the first push of the next day unprompted.
        **Remember Sharing** on the option box keeps the row anyway, as a
        preference (:meth:`_restore_sharing`): it comes back as left and the
        link opens with the first push, never with the panel.
        """
        row = self._param_widgets["SHARE_VIA"]
        row.restore_state = False
        menu = row.option_box.menu
        menu.setTitle("Sharing")
        menu.add_defaults_button = False
        for text, name, tip, handler in self.SHARING_ACTIONS:
            button = menu.add(
                "QPushButton", setText=text, setObjectName=name, setToolTip=tip
            )
            button.clicked.connect(getattr(self, handler))
        menu.add("QSeparator")
        remember = menu.add(
            "QCheckBox",
            setText="Remember Sharing",
            setObjectName="chk_remember_sharing",
            setToolTip="Keep the Sharing row across sessions, here and in every "
            "app that opens this panel. It comes back as you left it and the "
            "link opens with the first push (or Share Now), never when the "
            "panel opens. Private Link is always kept.",
        )
        # Its own store, read now: the widget store restores a menu's items
        # only once the menu registers, after this panel is built.
        remember.restore_state = False
        remember.setChecked(self._remember_sharing())
        remember.toggled.connect(self._remember_sharing_changed)
        self.sb.KindFactory.connect_changed(row, self._sharing_changed)

    def _state(self):
        """The window's state store (widget values and custom keys), or
        ``None`` on a UI without one."""
        return getattr(self.ui, "state", None)

    def _remember_sharing(self) -> bool:
        store = self._state()
        return bool(store and store.load_custom(self._REMEMBER_SHARING_KEY, False))

    def _remember_sharing_changed(self, on: bool) -> None:
        """Remember Sharing: keep the row from now on, or forget it."""
        store = self._state()
        if store is None:
            return
        store.save_custom(self._REMEMBER_SHARING_KEY, bool(on))
        store.save_custom(self._SHARING_KEY, self._sharing_choice() if on else "off")
        self._refresh_status()

    def _restore_sharing(self) -> None:
        """Put back the remembered row -- with its change silenced, so the link
        waits for a push (:meth:`_share_after_push`) or Share Now. A row a live
        share already set (:meth:`_show_live_share`) wins."""
        if not self._remember_sharing() or self._sharing_choice() != "off":
            return
        choice = self._state().load_custom(self._SHARING_KEY, "off") or "off"
        if choice == "off":
            return
        row = self._param_widgets["SHARE_VIA"]
        was_blocked = row.blockSignals(True)
        try:
            self.sb.KindFactory.set_value(row, choice)
        finally:
            row.blockSignals(was_blocked)
        self._refresh_status()

    def _sharing_choice(self) -> str:
        """The Sharing row: ``"off"``, ``"auto"`` or a provider."""
        return self.sb.KindFactory.read_value(self._param_widgets["SHARE_VIA"]) or "off"

    def _share_private(self) -> bool:
        """The Private Link row: a fresh random link per share."""
        return bool(self.sb.KindFactory.read_value(self._param_widgets["SHARE_PRIVATE"]))

    def _sharing_scenes(self) -> List[_Scene]:
        """The scenes the row shares now: the first always -- a link can go
        out before its first model -- and each added one once it serves; an
        added scene not pushed yet shares with its first push."""
        return [
            scene
            for index, scene in enumerate(self._scenes)
            if index == 0 or scene.server is not None
        ]

    def _private_changed(self, _on) -> None:
        """The Private Link row, applied at once: a share up -- or asked for
        -- is shared again the new way, with a new link."""
        choice = self._sharing_choice()
        if choice != "off":
            for scene in self._sharing_scenes():
                self._share(choice, interactive=True, scene=scene)

    def _show_live_share(self) -> None:
        """A share already up shows on the row, never Off beside a live link.

        The server outlives the panel -- a panel reopened in the same session,
        or a host bringing its own deliverer, can find one sharing. The row's
        change then reports it rather than sharing again. Private Link is set
        to the share's first: a row still at its default would read as the
        other kind of link and share again, under a new one -- the guest
        holding the private link locked out by a panel merely reopened.
        """
        server = self._server()
        info = server.share_info() if server is not None else None
        if info is not None and self._sharing_choice() == "off":
            self._write_param("SHARE_PRIVATE", bool(info.get("private")))
            self._write_param("SHARE_VIA", info["provider"])

    def _sharing_changed(self, choice) -> None:
        """The row, applied at once: a provider shares now, Off stops -- and
        a remembered row keeps the change."""
        if self._remember_sharing():
            self._state().save_custom(self._SHARING_KEY, choice or "off")
        if (choice or "off") == "off":
            self._unshare(announce_idle=False)
        else:
            for scene in self._sharing_scenes():
                self._share(choice, interactive=True, scene=scene)

    def share_link(self) -> None:
        """Share Now: bring the link up without a push, or retry a failed one.

        With the row Off it picks Auto, which shares through the row's own
        change -- the row stays the one switch, and says what is shared.
        """
        choice = self._sharing_choice()
        if choice == "off":
            self._write_param("SHARE_VIA", "auto")
        else:
            for scene in self._sharing_scenes():
                self._share(choice, interactive=True, scene=scene)

    def copy_share_link(self) -> None:
        """Copy Link: the live links to the clipboard -- one per line, scene
        by scene -- and to the log.

        With the row on and a scene's link not up -- a share that failed, or
        one still waiting on a step -- that scene shares instead, which copies
        the link as it arrives or says what it waits on. Only Off has nothing
        to copy.
        """
        live = [
            (scene, info)
            for scene in self._scenes
            for info in (scene.share_info(),)
            if info is not None
        ]
        choice = self._sharing_choice()
        if live:
            copied = self._copy("\n".join(info["url"] for _scene, info in live))
            for index, (scene, info) in enumerate(live, 1):
                note = copied if index == len(live) else ""
                link = self._launch_link(info["url"])
                self.panel_log(f"{self._tag(scene)}Share link: {link}{note}.")
            if choice != "off":
                for scene in self._sharing_scenes():
                    if scene.share_info() is None:
                        self._share(choice, interactive=True, scene=scene)
            return
        if choice == "off":
            self.panel_log(
                "Nothing is being shared -- pick a provider in the Sharing row.",
                "warning",
            )
            return
        for scene in self._sharing_scenes():
            self._share(choice, interactive=True, scene=scene)

    def copy_scene_link(self) -> None:
        """Copy Scene Link: where the published scene is described as data.

        The share's ``scene.json`` -- what to send a developer whose agent or
        tools compare this scene with their own -- or, while nothing is
        shared, this machine's, for a reader on it. Every served scene's, one
        per line. It never shares by itself: a link to hand out is Copy
        Link's to bring up.
        """
        served = [
            scene
            for scene in self._scenes
            if scene.server is not None and getattr(scene.server, "url", None)
        ]
        if not served:
            self._serving()  # says to push once
            return
        lines = []
        for scene in served:
            info = scene.server.share_info()
            url = info["scene_url"] if info is not None else None
            lines.append((scene, url or scene.server.scene_url, bool(url)))
        copied = self._copy("\n".join(url for _scene, url, _shared in lines))
        for index, (scene, url, shared) in enumerate(lines, 1):
            note = copied if index == len(lines) else ""
            if shared:
                self.panel_log(f"{self._tag(scene)}Scene as data: {url}{note}.")
            else:
                self.panel_log(
                    f"{self._tag(scene)}Scene as data, on this machine only: "
                    f"{url}{note}. Share to send it to someone else."
                )

    @staticmethod
    def _launch_link(url: str) -> str:
        """*url* followed by a [copy] link -- every page address the log gives
        (the log pane's ``copy`` action puts it on the clipboard)."""
        return f"{url} {ptk.LoggingMixin.log_link('[copy]', 'copy', text=url)}"

    @staticmethod
    def _copy(text: str) -> str:
        """*text* on the clipboard; the phrase to log after it, or ``""``."""
        try:
            from qtpy import QtWidgets

            QtWidgets.QApplication.clipboard().setText(text)
            return " -- copied to the clipboard"
        except Exception:  # noqa: BLE001 - no clipboard is not a failed share
            return ""

    def _share_after_push(self, scene: _Scene) -> None:
        """With sharing on, a push keeps *scene*'s link up and says where it is.

        The same link each time -- a guest's page picks the push up by itself,
        and a new link per push would strand everyone holding the last one. A
        share that dropped (its client exited) is brought back up. A share that
        cannot come up is logged, not put in a dialog: a push is not the moment
        to interrupt, and the next push tries again.
        """
        choice = self._sharing_choice()
        if choice == "off":
            return
        info = scene.share_info()
        if info is not None:
            # The guest tabs open right now (polled within the viewer timeout)
            # -- a push resets nothing, so a bare "0" only read as stuck.
            guests = info["guests"]
            watching = (
                f"{guests} guest{'s' * (guests != 1)} watching"
                if guests
                else "no guest has it open right now"
            )
            self.panel_log(
                f"{self._tag(scene)}Share link: {self._launch_link(info['url'])} "
                f"-- {watching}."
            )
            return
        self._share(choice, interactive=False, scene=scene)

    def _share(
        self, choice: str, interactive: bool, scene: Optional[_Scene] = None
    ) -> None:
        """Share *scene* (the first by default) through *choice*, and report
        the link.

        The provider is settled first, the way a KTX2 push settles its
        encoder: a missing tunnel client is OFFERED (cloudflared downloads),
        never a dead end in a log line -- when *interactive*; a push's share
        asks nothing and logs what is missing instead. A provider that cannot
        produce a link -- a firewall that blocks the client -- says so, first
        line the next step, in a dialog when *interactive*; the client's own
        output follows in the log. A share already up through a fitting
        provider is reported, not restarted; one through another provider is
        replaced. Each scene is its own share: Tailscale gives each its own
        HTTPS port, Cloudflare its own name.

        The share runs off the UI thread (:class:`uitk.BackgroundTask`): a provider takes
        seconds to bring a link up, and a quick tunnel's new name 6-18 s more
        to resolve, which on the UI thread froze the panel -- and the DCC
        hosting it -- for the whole wait. A provider that stops on a one-time
        step in a browser (Tailscale, until the tailnet enables Funnel) is
        offered (:meth:`_offer_step`) and waited on in the background, the
        panel free meanwhile: the step is a person's, and once it is taken the
        link arrives by itself (:meth:`_share_done`). Asked again while it
        waits, the panel names the step again; asked for another provider, it
        ends that wait and shares through the one asked for -- as it does when
        Private Link changed since the wait began, which would otherwise bring
        up the other kind of link once the step is taken.
        """
        scene = scene or self._scenes[0]
        tag = self._tag(scene)
        private = self._share_private()
        if scene.pending:
            if scene.step is None:
                if interactive:
                    self.panel_log(f"{tag}A link is already being opened.", "warning")
                return
            if choice in (scene.choice, scene.provider) and private == scene.private:
                self._offer_step(scene.step, interactive, waiting=True, scene=scene)
                return
            # Another provider, or the other kind of link: that wait ends.
            self._unshare(announce_idle=False, scenes=[scene])
        info = scene.share_info()
        if info is not None:
            fits = choice == "auto" or info["provider"] == choice
            if fits and bool(info.get("private")) == private:
                link = self._launch_link(info["url"])
                self.panel_log(f"{tag}Already shared at {link}.")
                return
            scene.server.unshare()
        provider = ptk.ShareTunnel.settle(
            choice,
            prompt=self.sb.confirm if interactive else (lambda _question: False),
            refused=lambda text: self._refused(f"{tag}Not shared: {text}", interactive),
            installed=lambda path: self.sb.message_box(
                f"Installed the tunnel client: <hl>{path}</hl>"
            ),
        )
        if provider is None:
            return
        scene.pending = True
        scene.choice, scene.provider = choice, provider
        scene.private = private
        stops = scene.stops
        reported = {}  # the provider's step, set on the share's own thread
        # The stable alias (PYTHONTK_PREVIEW_ALIAS) is the first scene's: a
        # second share writing it would take it from the first, whose stop
        # would then say the share ended while this one is live.
        alias = None if scene is self._scenes[0] else False
        job = self.sb.BackgroundTask(
            lambda: scene.bridge.share(
                provider=provider,
                alias=alias,
                on_step=lambda step: reported.setdefault("step", step),
                private=private,
            ),
            name="webxr-preview-share",
        )
        # The tick pumps the host's loop by the host's own input policy -- a
        # DCC admits no clicks mid-slot -- so the panel repaints and the host
        # stays responsive without a raw processEvents bypassing that policy.
        with self.sb.progress(text=f"{tag}Sharing: opening the link…") as tick:
            while not job.done and "step" not in reported:
                tick()
                job.wait(0.05)
        if job.done:
            self._share_done(scene, job, stops, interactive, waited=False)
            return
        scene.step = reported["step"]
        self._refresh_status()
        self._offer_step(scene.step, interactive, waiting=True, scene=scene)
        job.when_done(
            self.ui,
            lambda: self._share_done(scene, job, stops, interactive, waited=True),
        )

    def _share_done(
        self, scene: _Scene, job, stops: int, interactive: bool, waited: bool
    ) -> None:
        """Report a share's outcome on the UI thread -- at once, or when one
        that *waited* on a step in the background ends.

        Silent when a stop ended it (*stops* is the count it began with): the
        stop has already said so, and a later share may be under way -- and
        when its scene was removed meanwhile.
        """
        if scene not in self._scenes or scene.stops != stops:
            return
        tag = self._tag(scene)
        scene.clear_wait()
        self._refresh_status()
        try:
            info = job.result()
        except ptk.ShareTunnel.StepRequired as step:
            if not waited:  # stopped at the step at once: offer it
                self._offer_step(step, interactive, waiting=False, scene=scene)
                return
            # Ran out, or the client stopped waiting: either way, not taken.
            self.panel_log(
                f"{tag}Sharing stopped waiting on {step.label}'s one-time step. "
                f"Enable it at {step.url}, then Share Now -- or just push again.",
                "warning",
            )
            return
        except (OSError, RuntimeError) as error:  # incl. TimeoutError
            detail = str(error)
            self.panel_log(f"{tag}Sharing failed:\n{detail}", "error")
            if interactive:
                self.sb.message_box(detail.splitlines()[0])
            return
        scene.reach = None  # a new link: unchecked
        copied = self._copy(info["url"])
        reach = "anyone with the link" if info["public"] else "your tailnet only"
        self.panel_log(
            f"{tag}Shared at {self._launch_link(info['url'])}{copied}. View-only, "
            f"open to {reach}; every push updates it."
        )
        if info.get("alias_error"):
            self.panel_log(
                f"{tag}The stable alias was not updated ({info['alias_error']}); "
                f"send the link above instead.",
                "warning",
            )
        self._verify_share(scene, follow=True)

    def check_share_link(self) -> None:
        """Test Link: whether a guest can reach each share now."""
        shared = [scene for scene in self._scenes if scene.share_info() is not None]
        if not shared:
            self.panel_log(
                "Nothing is being shared -- pick a provider in the Sharing row.",
                "warning",
            )
            return
        for scene in shared:
            self._verify_share(scene, follow=False)

    def _verify_share(self, scene: _Scene, follow: bool) -> None:
        """Ask *scene*'s live link for its page the way a guest's browser does
        -- off the UI thread, a round trip through the provider taking a second
        or more -- and log whether someone else can open it
        (:meth:`pythontk.PreviewServer.ping_share`: public DNS, then the
        provider's public door).

        A link the provider reports up can still not open: its name not yet in
        public DNS (a new Tailscale Funnel name took 5.5 minutes), a tunnel
        that dropped as it came up, a provider page in its place. Said in the
        log in red, never a dialog -- and the footer turns red with it -- since
        the share is up and the cause is usually minutes from clearing; with
        *follow* (a new link) the panel keeps checking (:meth:`_recheck_share`)
        and says when it opens. Announced only when asked (Test Link): a new
        link's own line is already there, and its answer follows in a second.
        """
        info = scene.share_info()
        if info is None:
            return
        link = info["tunnel_url"]
        if not follow:
            self.panel_log(f"{self._tag(scene)}Checking the link opens from outside…")
        job = self.sb.BackgroundTask(scene.bridge.ping_share, name="webxr-preview-ping")

        def report() -> None:
            ping = self._ping_result(job)
            if not self._still_shared(scene, link):
                return  # removed, stopped, or another link by now
            scene.reach = ping
            self._refresh_status()
            if ping.get("ok"):
                scene.stop_recheck()
                self._log_reachable(scene, ping)
                return
            self.panel_log(self._unreachable_text(scene, ping, follow), "critical")
            if follow:
                self._recheck_share(scene, link)

        job.when_done(self.ui, report)

    @staticmethod
    def _ping_result(job) -> Dict[str, Any]:
        try:
            return job.result()
        except Exception as error:  # noqa: BLE001 - a check never fails a share
            return {"ok": False, "error": str(error) or type(error).__name__}

    def _still_shared(self, scene: _Scene, link: Optional[str]) -> bool:
        """Whether *scene* is still shared at *link* -- a check answering after
        a stop, a new share or a removal has nothing left to say."""
        if scene not in self._scenes:
            return False
        info = scene.share_info()
        return info is not None and info["tunnel_url"] == link

    def _log_reachable(self, scene: _Scene, ping: Dict[str, Any], now=False) -> None:
        """A link that opens from outside, said in green."""
        when = " now" if now else ""
        route = (
            ", via public DNS -- the same lookup their browser makes"
            if ping.get("route") == "public"
            else ""
        )
        text = (
            f"{self._tag(scene)}Link checked: a guest can{when} reach it "
            f"({ping.get('ms') or 0:.0f} ms{route})."
        )
        if ping.get("verified") is False:
            text += (
                " This machine could not verify the link's certificate (its "
                "store lacks the provider's root); a guest's browser checks it "
                "with its own."
            )
        self.panel_log(text, "success")

    def _unreachable_text(
        self, scene: _Scene, ping: Dict[str, Any], follow: bool
    ) -> str:
        """Why no one else can open *scene*'s link, and what happens next."""
        error = ping.get("error") or "no answer"
        url = (scene.share_info() or {}).get("url") or ping.get("url") or "The link"
        text = (
            f"{self._tag(scene)}NOT REACHABLE FROM OUTSIDE: {url} did not answer "
            f"as a guest's browser asks it ({error}). No one else can open it "
            "right now."
        )
        if "public DNS" in error:
            text += (
                " A new link's name takes time to reach public DNS: minutes for "
                "Tailscale Funnel -- sometimes far longer -- every share. For a "
                "link that opens in seconds, pick Cloudflare quick tunnel in the "
                "Sharing row."
            )
        if follow:
            minutes = round(self.RECHECK_FOR_S / 60)
            text += (
                f" The panel keeps checking for {minutes} minutes and says when "
                "it opens; Test Link asks now."
            )
        else:
            text += " Test Link asks again."
        return text

    def _recheck_share(self, scene: _Scene, link: str) -> None:
        """Check *scene*'s link again every :attr:`RECHECK_MS`, quietly, until it
        opens (said in green) or :attr:`RECHECK_FOR_S` runs out (said in red).
        Ends by itself when the share stops, changes or its scene goes."""
        import time

        scene.stop_recheck()
        deadline = time.monotonic() + self.RECHECK_FOR_S
        timer = QtCore.QTimer(self.ui)
        timer.setInterval(self.RECHECK_MS)
        running: Dict[str, Any] = {}

        def tick() -> None:
            if scene.recheck is not timer or not self._still_shared(scene, link):
                scene.stop_recheck(timer)
                return
            job = running.pop("job", None)
            if job is not None and not job.done:
                running["job"] = job  # still asking
                return
            if job is not None:
                ping = self._ping_result(job)
                if ping.get("ok"):
                    scene.reach = ping
                    scene.stop_recheck(timer)
                    self._log_reachable(scene, ping, now=True)
                    self._refresh_status()
                    return
                scene.reach = ping
                if time.monotonic() > deadline:
                    scene.stop_recheck(timer)
                    minutes = round(self.RECHECK_FOR_S / 60)
                    self.panel_log(
                        f"{self._tag(scene)}STILL NOT REACHABLE FROM OUTSIDE after "
                        f"{minutes} minutes ({ping.get('error') or 'no answer'}). "
                        "Share again (Stop Sharing, then Share Now), or pick "
                        "another provider in the Sharing row.",
                        "critical",
                    )
                    self._refresh_status()
                    return
            running["job"] = self.sb.BackgroundTask(
                lambda: scene.bridge.ping_share(attempts=1),
                name="webxr-preview-recheck",
            )

        timer.timeout.connect(tick)
        scene.recheck = timer
        timer.start()

    def _offer_step(
        self, step, interactive: bool, waiting: bool, scene: _Scene
    ) -> None:
        """A provider stopped on a one-time step in a browser -- Tailscale,
        before the tailnet enables Funnel -- offered, never a dead end.

        *waiting*: the share still waits on the step, so the link comes up by
        itself once it is taken; otherwise Share Now, or the next push, tries
        again. The page opens on a yes; a push's share asks nothing and logs
        the page instead.
        """
        then = (
            "the link comes up by itself once it is enabled"
            if waiting
            else "then Share Now -- or just push again"
        )
        self.panel_log(
            f"{self._tag(scene)}{step.label} needs a one-time "
            f"step first: enable it at {step.url} -- {then}.",
            "warning",
        )
        follows = ", and the link follows by itself" if waiting else ""
        if interactive and self.sb.confirm(
            f"{step.label} is not enabled for your network yet -- it takes one "
            f"step in your browser{follows}. Open that page now?",
            yes="Open Page",
            no="Not Now",
        ):
            webbrowser.open(step.url)

    def _refused(self, text: str, interactive: bool = True) -> None:
        """A tool is missing and was not installed: the fix-shaped message in
        the log -- where its install page stays, as a link -- and, when
        *interactive*, in a dialog too, which is gone in seconds."""
        self.panel_log(text, "warning")
        if interactive:
            self.sb.message_box(text)

    def stop_sharing(self) -> None:
        """Stop Sharing: the row to Off, which takes every link down."""
        if self._sharing_choice() != "off":
            self._write_param("SHARE_VIA", "off")  # its change unshares
        else:
            self._unshare()

    def _unshare(
        self, announce_idle: bool = True, scenes: Optional[List[_Scene]] = None
    ) -> None:
        """Take the links of *scenes* (every scene by default) down; the
        owner's pages and servers are untouched.

        Unshares even when nothing reads as shared: a share whose client died
        on its own reads that way while it still holds its guest listener and
        an alias sending guests to the dead link; and a share still opening --
        waiting on a step, above all -- ends now. *announce_idle* says so when
        there was nothing to stop -- right for Stop Sharing pressed, noise for
        the row turned Off.
        """
        shared = opening = False
        for scene in self._scenes if scenes is None else scenes:
            opening = scene.end_wait() or opening
            server = scene.server
            shared = (server is not None and server.share_info() is not None) or shared
            if server is not None:
                server.unshare()
        if shared:
            self.panel_log("Stopped sharing; the link no longer opens.")
        elif opening:
            self.panel_log("Stopped the link being opened.")
        elif announce_idle:
            self.panel_log("Nothing is being shared.", "warning")
        self._refresh_status()

    # ------------------------------------------------------------------ public hand-off
    def set_source_file(self, path: str) -> None:
        """Pre-fill Source Files with *path* and select the file source.

        The hand-off point for a host that already has a file to show -- an
        exporter that just wrote a GLB, say. Selecting the source too, because
        filling a field the active source does not read would look like the
        panel ignored the request.
        """
        self.set_source_files([path] if path else [])

    def set_source_files(self, paths: List[str]) -> None:
        """Pre-fill Source Files with *paths* -- the parts of one scene, shown
        together -- and select the file source (see :meth:`set_source_file`).
        """
        row = self._param_widgets.get("SOURCE_FILE")
        if row is not None:
            self.sb.KindFactory.set_value(row, [str(path) for path in paths or []])
        self._select_source(FILE_SOURCE)

    def _prompt_for_source(self) -> List[str]:
        """Ask for the files to preview, and remember the answer; ``[]`` if
        declined.

        An empty field is not an error state, it is the first push -- the
        panel opens with nothing chosen. Answering that with "pick a file
        first" makes the user go and do the dialog's job by hand, on the one
        press where what they want is unambiguous. The choice is written back
        into the field, so the next push is the one-press loop this panel is
        for and the file is visible rather than remembered.
        """
        edit = self._source_edit()
        option = edit.option_box.find_option(self.sb.BrowseOption) if edit else None
        if option is None:  # a row built without its browse button
            self.panel_log("Pick the Source Files first.", "warning")
            return []
        # The ROW's own browse, not a second dialog beside it: the filter, the
        # title and the folder it opens on are declared once, on the field, so
        # the two ways into the same choice cannot answer differently. It
        # writes the pick back into the field itself.
        option.browse()
        return self._source_paths()

    def _source_edit(self):
        """The Source File field's inner line edit; None before it is built."""
        return getattr(self._param_widgets.get("SOURCE_FILE"), "_line_edit", None)

    def _source_paths(self) -> List[str]:
        """The files that field names, in order; ``[]`` when empty."""
        return self._row_paths(self._param_widgets.get("SOURCE_FILE"))

    def _row_paths(self, row) -> List[str]:
        """The files a Source Files field names, in order; ``[]`` when empty."""
        return list(self.sb.KindFactory.read_value(row) or []) if row is not None else []

    def _missing_files(self, paths: List[str], tag: str = "") -> bool:
        """Whether any of *paths* is not on disk -- each one said."""
        missing = [path for path in paths if not os.path.isfile(path)]
        for path in missing:
            self.panel_log(f"{tag}Source file not found: {path}", "error")
        return bool(missing)

    def _select_source(self, key: str) -> None:
        combo = self.ui.cmb000
        for i in range(combo.count()):
            data = combo.itemData(i)
            if isinstance(data, (tuple, list)) and data and data[0] == key:
                combo.setCurrentIndex(i)
                # Saved even when the index did not move -- File on Disk is
                # the only entry before a host arrives, so selecting it emits
                # nothing. Unsaved, the host's repopulate would re-apply last
                # session's scope over a file this call just handed over.
                state = self._state()
                if state is not None:
                    state.save(combo)
                return

    # ------------------------------------------------------------------ GLB rows
    @staticmethod
    def _glb_options(values: Dict[str, Any]) -> Dict[str, Any]:
        """The Scene Exporter rows of collected *values*, keyed as the push
        takes them.

        ``{row key: combo value}`` (:attr:`pythontk.ExportProfile.GLB_ROWS`) --
        handed to ``push(glb_options=...)``, which resolves them with the Scene
        Exporters' own methods. Nothing is interpreted here.
        """
        return {
            row: values[key] for key, row in _params.GLB_KEYS.items() if key in values
        }

    # ------------------------------------------------------------------ preflight
    def _texture_tool_ready(self, glb_options: Dict[str, Any]) -> bool:
        """Settle a missing KTX2 encoder BEFORE the push, offering the install.

        Only KTX2 needs an external tool. The bridge already refuses a KTX2
        push without ``toktx``, eagerly, before it pays for the export -- but it
        refuses by RAISING with an install URL, and a panel control that
        dead-ends in a URL is what the Scene Exporter's own KTX2 row stopped
        doing. A missing tool means *offer the managed install*, never *abort
        and go read a log*.

        Gated on the resolved container (:meth:`_encodes_ktx2`), so both KTX2
        entries ask and nothing else does: WebP needs no tool, and probing for
        one the push will not use would ask about a control the user never
        touched. The push asks only when it re-encodes an image at all
        (:meth:`_texture_pass_runs`) -- a GLB published as authored, or a scene
        pushed without its textures, needs no encoder whatever the row says.
        """
        if not self._encodes_ktx2(glb_options):
            return True
        # Declined, or the install failed: the refusal is the fix-shaped
        # message naming the manual install, so it IS the dialog -- and stays
        # in the log, where its install page is a link.
        return ptk.ImgUtils.settle_ktx2_encoder(
            prompt=self.sb.confirm,
            refused=self._refused,
            installed=lambda path: self.sb.message_box(
                f"Installed KTX-Software (toktx): <hl>{path}</hl>"
            ),
        )

    # ------------------------------------------------------------------ b000 — the push
    def b000(self) -> None:
        """Build the deliverable for the active source and publish it -- for
        the file source, every scene's, each on its own page."""
        values = self.collect_param_values()
        source = self._active_source()
        # The files first: the encoder gate below asks only for a push that
        # re-encodes an image, and that depends on what is being pushed.
        added: List[Tuple[_Scene, List[str]]] = []
        if source == FILE_SOURCE:
            values["SOURCE_FILE"] = self._chosen_files(values)
            if not values["SOURCE_FILE"]:
                return  # dismissed, or refused and already said why
            added = self._added_scene_files()

        # Every row, every push: the panel IS the answer, so an untouched row
        # says "the Scene Exporter's default" rather than leaving the
        # deliverer's own setting in force.
        glb_options = self._glb_options(values)
        if self._texture_pass_runs(values) and not self._texture_tool_ready(
            glb_options
        ):
            return

        # An explicit list every push, never None: the checkboxes ARE the
        # answer, and None means "leave the server's set alone" -- which would
        # make an unticked box unable to turn a script back off.
        scripts = list(values.get("VIEWER_SCRIPTS") or [])
        # The panel is the answer for the switch too, whatever set it last.
        self._apply_locomotion(values.get("LOCOMOTION", True))

        first = self._scenes[0]
        try:
            if source == FILE_SOURCE:
                outcome = self._push_file(values["SOURCE_FILE"], glb_options, scripts)
            else:
                outcome = self._push_scope(source, values, glb_options, scripts)
        except Exception:
            self.bridge.logger.error("Preview raised:\n" + traceback.format_exc())
            outcome = None
        else:
            if outcome is not None:  # None: the step settled it and said why
                self._report(*outcome, scene=first)
                self._share_after_push(first)
        # Each added scene on its own: one that fails costs only its page.
        for scene, paths in added:
            try:
                outcome = self._push_file(paths, glb_options, scripts, scene=scene)
            except Exception:
                self.bridge.logger.error(
                    f"{self._tag(scene)}preview raised:\n" + traceback.format_exc()
                )
                continue
            self._report(*outcome, scene=scene)
            self._share_after_push(scene)

    def _chosen_files(self, values) -> List[str]:
        """The files to push -- asked for when the field is empty -- or ``[]``
        when the run was settled here (dismissed, or a file is missing)."""
        # A list already: the row reads its field as one (uitk ``files``). An
        # empty one asks; dismissed, that is [] and there is nothing to say.
        paths = list(values.get("SOURCE_FILE") or []) or self._prompt_for_source()
        return [] if self._missing_files(paths) else paths

    def _push_file(self, paths, glb_options, scripts, scene=None):
        """Push the chosen files -- one, or the parts of one scene -- through
        *scene*'s bridge (the first scene's by default).

        No export params: Include Textures is the host's FBX export switch,
        and a file's FBX already chose what it embeds.
        """
        bridge = scene.bridge if scene is not None else self.bridge
        tag = self._tag(scene) if scene is not None else ""
        with self.sb.progress(text=f"{tag}Preview: publishing…") as tick:
            result = bridge.push(
                objects=paths,
                scope=FILE_SOURCE,
                open_browser="auto",
                glb_options=glb_options,
                scripts=scripts,
                progress=lambda message: tick(text=message),
            )
        names = ", ".join(os.path.basename(path) for path in paths)
        return result, [
            (
                f"Sources ({len(paths)} parts): {names}"
                if len(paths) > 1
                else f"Source: {names}"
            ),
            self._timing_line(bridge, result),
        ]

    def _push_scope(self, scope, values, glb_options, scripts):
        """Export *scope* from the host and push it."""
        bridge = self._host()
        if bridge is None:
            self.panel_log(
                "No host is connected, so there is no scene to read. Pick "
                "'File on Disk' as the Source.",
                "warning",
            )
            return None

        # Resolved here rather than left to push(), so an empty result can be
        # REPORTED. Pushing blind collapses "nothing selected", "the scene is
        # empty" and "the export failed" into one message, and the first two
        # are the user's own next action.
        objects = bridge.scope_objects(scope)
        if not objects:
            self.panel_log(self.empty_scope_message(scope), "warning")
            return None

        with self.sb.progress(text="Preview: exporting…") as tick:
            result = bridge.push(
                objects=objects,
                scope=scope,
                open_browser="auto",
                glb_options=glb_options,
                scripts=scripts,
                progress=lambda message: tick(text=message),
                EMBED_TEXTURES=bool(values.get("EMBED_TEXTURES", True)),
                INCLUDE_ANIMATION=bool(values.get("INCLUDE_ANIMATION", False)),
            )
        # Reported, not left to the log: a map the materials record names but
        # the push could not find renders as a flat colour, and a bake whose
        # maps were not found renders exactly like no bake. Without these the
        # preview cannot be debugged from the panel.
        return result, [
            bridge.materials_summary(result),
            bridge.lightmap_summary(result),
            self._timing_line(bridge, result),
        ]

    @staticmethod
    def _timing_line(bridge, result) -> str:
        """Where the push's time went (``PreviewBridge.timing_summary``).

        The question after every slow push, answered by the push: FBX2glTF's
        share is moved by what the scene exports, the rest by the build. Read
        through ``getattr`` because it is a report rather than the push -- a
        pythontk that predates it costs the line, never the preview.
        """
        summary = getattr(bridge, "timing_summary", None)
        return summary(result) if callable(summary) else ""

    def _report(
        self,
        result: Optional[Dict[str, Any]],
        extra: List[str],
        scene: Optional[_Scene] = None,
    ) -> None:
        """Say what *scene*'s page is showing now, or why it is not."""
        tag = self._tag(scene) if scene is not None else ""
        if not result:
            self.panel_log(
                f"{tag}Preview failed — see the log above for details.", "error"
            )
            return
        lines = [
            f"{tag}Preview v{result['version']} live at "
            f"{self._launch_link(result['url'])}",
            *extra,
        ]
        for line in lines:
            if line:
                self.panel_log(line)
        self._refresh_status()
