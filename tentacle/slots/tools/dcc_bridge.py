# !/usr/bin/python
# coding=utf-8
"""DCC Bridge: send the selection to a fresh copy of the other DCC through an
import template, or run a template in a headless one and wait for its result.

One Slots class for both hosts. Each library ships the cross-DCC bridge named
after its TARGET app -- mayatk's ``BlenderBridge`` sends to Blender, blendertk's
``MayaBridge`` to Maya -- and the panel's engine is the host's
(``self.tk.EnvUtils.foreign_scene_bridge()``), so it is the Blender Bridge in
Maya and the Maya Bridge in Blender: its title, button and help name the target
app (the engine's ``spec.app.name``). On the bridge panels' shared base
(:class:`HostBridge`: parameter rows, presets, log pane, Scope); the parameter
registry, template folder and ``(template, mode)`` list are the engine's.

Two routes off one export, chosen by the template's mode:

* ``send_to`` launches an interactive target app on the rendered template.
* The engine's blocking modes (its ``run_spec``) run a headless target and wait:
  ``save_as`` writes a file the artist names (a ``.blend``), and ``round_trip``
  (Maya's lightmap bake in Blender) brings its result back into this scene
  through the engine's return leg.

``REQUIRE_OUTPUT_DIR = False``: a send goes through a temp FBX the engine
manages, so there is no artifact to point the panel at.
"""

import traceback
from pathlib import Path

from pythontk import ROUND_TRIP

from ._app_bridge.host_bridge import HostBridge


class DccBridgeSlots(HostBridge):
    UI_NAME = "dcc_bridge"
    LOG_TAG = "dcc_bridge"
    REQUIRE_OUTPUT_DIR = False

    #: Help for a template only some engines ship, shown where the engine lists
    #: it: ``{template: (section title, [paragraph, ...])}``.
    TEMPLATE_HELP = {
        "bake_lightmaps": (
            "bake_lightmaps (round_trip) — send to bake",
            [
                "Bakes Cycles lightmaps in a <b>headless</b> Blender and brings them "
                "<b>back into this scene</b>. One click, no save dialog; Maya blocks "
                "until it finishes (a real bake takes minutes).",
                "Blender does the whole lightmap job — UVs, bake, denoise, atlas — and "
                "on return the layout is written onto your meshes and the maps wired in "
                "<b>alongside your existing materials</b>: material and UV0 untouched, "
                "lightmap on UV1. Undo with <b>Revert Selected</b> on the Lightmap "
                "Baker's Manage page.",
                "<b>The bake targets no platform.</b> Once committed, every export "
                "ships it on its own: FBX → Unity (native lightmap binding) and "
                "GLB → web viewer — neither needs to know the bake happened.",
                "<b>The Maya viewport will not show it</b>, by design: the commit is "
                "non-destructive and builds no file node, so your material is exactly "
                "as you left it. What lands in the scene is the lightmap UV set on "
                "channel 1 plus a marker on each transform. To see it lit, click "
                "<b>WebXR Preview</b> in the <b>Rendering</b> panel — it reads the "
                "committed bake on its own, no bake-time setting needed — or open "
                "the EXR in <b>Lightmap Folder</b>.",
                "<b>Instances are fully supported</b> — and preserved. Every copy is "
                "baked separately (each stands in different light) and gets its own "
                "patch of the atlas via a per-instance rect, exactly Unity's native "
                "<i>lightmapScaleOffset</i> model; the shared mesh and your scene's "
                "instancing are untouched.",
                "<b>Quality</b> is a preset tier (Preview / Mobile / Desktop / Hero); "
                "<b>Lightmap Folder</b> defaults to the project's sourceimages.",
                "<b>Your scene's lighting is what gets baked.</b> <b>Include Lights</b> "
                "(on) exports the Maya lights and bakes with them; <b>Scene Light "
                "Strength</b> rebalances their power, since Maya intensity and Cycles "
                "watts are different units and the FBX crossing translates through "
                "both — the bake log prints each light's final wattage, so tune from "
                "that rather than guessing.",
                "Your lights ride <i>beside</i> the FBX rather than inside it and are "
                "rebuilt in Blender — an FBX light crashes Blender 5.1's importer, and "
                "FBX can't represent Arnold lights at any version, so this route is "
                "the one that carries <i>aiAreaLight</i> too. Ambient and volume lights "
                "have no Cycles equivalent and are skipped.",
                "A <b>StingrayPBS IBL</b> is not a light object at all, so it can't come "
                "across — use <b>Environment HDRI</b> and/or real scene lights. The two "
                "sources compose. With neither the bake comes out black — and says so in "
                "the log rather than leaving you to wonder.",
                "Need lights for a scene that has none? <b>Lights From Geometry</b> in the "
                "<b>Lighting</b> panel builds real, artist-owned area lights from your "
                "light-fixture meshes (or their selected lens faces) — they then bake here "
                "like any other light. An emissive <i>map</i> is only an appearance — it is "
                "not the room's light source.",
            ],
        ),
    }

    def __init__(self, switchboard):
        super().__init__(switchboard)
        self._name_the_target()

    # ------------------------------------------------------------------ engine
    @property
    def bridge_class(self):
        """The host's bridge to the other DCC (``EnvUtils.foreign_scene_bridge``):
        mayatk's ``BlenderBridge`` in Maya, blendertk's ``MayaBridge`` in Blender."""
        return self.tk.EnvUtils.foreign_scene_bridge()

    @property
    def target_app(self) -> str:
        """The other DCC's name, the engine's: "Blender" in Maya, "Maya" in Blender."""
        return self.bridge_class.spec.app.name

    @property
    def PRESETS_ROOT(self):  # noqa: N802 - the uitk hook's name
        """``<host library>/<target>_bridge``: each host's presets stay under the
        panel name it had before the bridges merged (``mayatk/blender_bridge``,
        ``blendertk/maya_bridge``; saved names keep their spelling)."""
        return (
            Path(self.tk.__name__.split(".")[0]) / f"{self.target_app.lower()}_bridge"
        )

    def _name_the_target(self):
        """Name the target app on the panel's chrome: the title, the template
        combo and the Send button (the ``.ui`` carries the neutral wording)."""
        app, library = self.target_app, self.tk.__name__.split(".")[0]
        self.ui.header.setText(f"{app.upper()} BRIDGE")
        self.ui.cmb000.setToolTip(
            f"Select a {app} import template bundled with {library}'s {app} bridge."
        )
        self.ui.b000.setText(f"Send to {app}")
        self.ui.b000.setToolTip(
            f"Export the selected object(s) and open them in a fresh {app} "
            "using the chosen template."
        )

    def help_spec(self) -> dict:
        """The header help, naming the target app; a template only some engines
        ship (:attr:`TEMPLATE_HELP`) adds its section where the engine lists it."""
        app = self.target_app
        listed = {template for template, _mode in self.list_template_modes()}
        return {
            "title": f"{app} Bridge",
            "body": f"Send the selected objects to a fresh {app}. This scene exports "
            f"the selection as FBX; {app} runs the chosen import template with your "
            "parameter values substituted in.",
            "steps": [
                "Select one or more objects.",
                "Toggle the import options (clear scene, frame in view, materials, …).",
                f"Click <b>Send to {app}</b>.",
            ],
            "sections": [
                (
                    "import (send_to) — options",
                    [
                        f"<b>Clear Scene First</b> — start {app} from an empty scene "
                        "before importing (clean slate). Off imports additively.",
                        "<b>Frame in View</b> — after import, select &amp; frame the "
                        "new objects.",
                    ],
                ),
            ]
            + [
                section
                for name, section in self.TEMPLATE_HELP.items()
                if name in listed
            ],
            "notes": [
                "Each template exposes only its own options, so the panel changes when "
                "you switch entries. The dropdown also picks up custom templates dropped "
                "into the templates folder (use <code>__KEY__</code> tokens from "
                "<i>parameters.py</i>), then click <b>Refresh Templates</b>.",
                f"A fresh {app} is launched every time; your running {app} is never "
                "touched.",
            ],
        }

    def _blocking_modes(self) -> tuple:
        """The modes that run a headless target and wait: the engine's run spec's.

        Read off the run spec rather than listed here: a mode added there but
        missed here would fall through to ``send()`` and launch a GUI target on
        a script with no ``__OUT_FILE__``. Only an engine that reads a template's
        output declarations (``template_output_mode``: mayatk's ``BlenderBridge``)
        runs them; blendertk's ``MayaBridge`` does not yet (BACKLOG "the Maya
        Bridge has no blocking route"), so there every template sends.
        """
        engine = self.bridge_class
        if not hasattr(engine, "template_output_mode"):
            return ()
        return tuple(engine.run_spec.modes)

    # ------------------------------------------------------------- b000: send
    def b000(self):
        """Send the selected objects to the other DCC with the chosen template."""
        # The base logs the scope-aware reason when the Scope is empty.
        params = self.collect_param_values()
        selection = self.scoped_objects(params)
        if not selection:
            return

        pair = self._selected_template_mode()
        if not pair:
            self.bridge.logger.warning(
                "No template chosen. Pick one from the dropdown above."
            )
            return
        template, mode = pair

        if not self.bridge.app_path:
            self.bridge.logger.error(self.bridge.app_spec.not_found_message)
            return

        # A blocking template writes a FILE, so it needs a destination send() has
        # no way to supply. ``auto`` templates derive it (their artifact is
        # pipeline plumbing, like the bake's return manifest); only artist-named
        # artifacts get the save dialog.
        engine = self.bridge_class
        blocking = mode in self._blocking_modes()
        auto_output = False
        if blocking:
            template_file = engine.template_path(template)
            auto_output = engine.template_output_mode(template_file) == "auto"
            out_path = (
                self.bridge.default_output_path(template)
                if auto_output
                else self._prompt_save_path(template)
            )
            if not out_path:
                self.bridge.logger.info("Cancelled.")
                return

        self.bridge.logger.info(
            f"--- {template} ({mode}) on {len(selection)} object(s) ---"
        )
        try:
            if blocking:
                self._run_blocking(
                    template, mode, selection, params, out_path, auto_output
                )
                return
            with self.sb.progress(
                text=f"Working: Send to {self.target_app} ({template})"
            ):
                self.bridge.send(
                    objects=selection,
                    template=template,
                    mode=mode,
                    params=params,
                )
        except Exception:
            self.bridge.logger.error("Bridge raised:\n" + traceback.format_exc())

    def _run_blocking(self, template, mode, selection, params, out_path, auto_output):
        """Run a blocking template headlessly and report its artifact.

        The artist waits on a bake, so the progress says so, and the result is
        reported rather than left to guess. The timeout is the template's: the
        shared 600 s default is shorter than a real bake, and a timeout kill
        leaves no artifact, so it would read as a silent bake failure. The two
        modes differ only in what becomes of the artifact: ``round_trip`` feeds
        it to the engine's return leg (``_ingest``), ``save_as`` stops at the
        written file; dispatching on the mode keeps that the template's call.
        """
        engine = self.bridge_class
        common = dict(
            objects=selection,
            template=template,
            params=params,
            timeout=engine.template_timeout(engine.template_path(template)),
        )
        with self.sb.progress(text=f"Working: {template} (this can take minutes)"):
            result = (
                self.bridge.round_trip(out=out_path, **common)
                if mode == ROUND_TRIP
                else self.bridge.save_as(out_path, **common)
            )
        if not (result and result.get("output")):
            self.bridge.logger.error(
                f"{template} produced no file -- see the log above."
            )
            return
        if auto_output:
            # A derived artifact is plumbing in tracked temp storage; announcing
            # it as written invites the artist to go looking for a deliverable
            # that is not one. What the run produced is reported below.
            self.bridge.logger.info(f"Artifact: {result['output']}")
        else:
            self.bridge.logger.success(f"Wrote {result['output']}")
        # The return leg (reassembly onto the scene) already ran inside the
        # engine's _ingest hook; the panel only reports it.
        wired = result.get("reassembled")
        if wired:
            self.bridge.logger.success(
                f"{len(wired)} lightmap binding(s) wired into the scene."
            )

    def _prompt_save_path(self, template: str) -> str:
        """Ask where a ``save_as`` template should write, seeded from the scene name.

        The template declares its own artifact format (``BRIDGE_OUTPUT_EXT``);
        the engine's accepted extensions drive the filter, so the dialog cannot
        offer a format ``resolve_save_path`` would then rewrite.
        """
        engine = self.bridge_class
        extensions = list(engine.save_extensions) or [".blend"]
        preferred = engine.template_output_ext(engine.template_path(template))
        # A declared artifact name may carry a compound suffix (".lightmaps.json"),
        # which the engine validates on its FINAL extension: compare on that.
        final = Path(preferred).suffix or preferred
        if final in extensions:  # show the likely one first
            extensions.remove(final)
            extensions.insert(0, final)
        else:
            # resolve_save_path APPENDS save_extensions[0] to anything it does not
            # recognise, so offering it anyway would turn "room.usd" into
            # "room.usd.blend". A declaration the engine cannot accept is a bug in
            # the template: say so and fall back.
            self.bridge.logger.warning(
                f"{template} declares BRIDGE_OUTPUT_EXT {preferred!r}, which is not in "
                f"{engine.__name__}.save_extensions {engine.save_extensions}; "
                f"offering {extensions[0]} instead."
            )
            preferred = extensions[0]

        scene = self.tk.EnvUtils.saved_scene_path() or ""  # both hosts answer it
        stem = Path(scene).stem or "untitled"
        start_dir = self.resolved_output_dir() or (
            str(Path(scene).parent) if scene else str(Path.home())
        )
        return (
            self.sb.save_file_dialog(
                title=f"Save {template} output",
                start_dir=str(Path(start_dir) / f"{stem}{preferred}"),
                file_types=[f"*{ext}" for ext in extensions],
                filter_description=f"{self.target_app} bridge output",
            )
            or ""
        )
