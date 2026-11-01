# !/usr/bin/python
# coding=utf-8
"""Shadow Rig: a ground plane carrying the targets' projected shadow, built for
engine export (Unity, WebXR).

One Slots class for both hosts, a thin driver over the host toolkit's
``ShadowRig`` and ``ShadowPreview`` (``self.tk``), with its live preview the
toolkit's ``Preview``. The rig types the panel offers are the
:attr:`ShadowRigSlots.RIG_BUILDERS` strategy table. What the hosts read
differently -- the casters in a selection, a source by name, the selection as
sources (Maya: selected faces are a fixture; Blender: a mesh in Edit Mode) --
the toolkit answers (``ShadowRig.shadow_targets`` / ``find_source`` /
``source_selection``).
"""

import contextlib
import math
import os

import pythontk as ptk

from tentacle import Slots


class ShadowRigSlots(Slots, ptk.LoggingMixin):
    #: Rig types the panel offers, keyed by the ``Rig:`` combo's label -> the
    #: name of the host engine's builder, ``ShadowRig.<builder>(targets,
    #: source_names, **options) -> [rigs]``. The strategy seam a new rig type
    #: lands in: one row here, one combo item, no branching in
    #: :meth:`perform_operation`.
    RIG_BUILDERS = {
        "Projected": "create_for_sources",
        "Horizon": "create_horizon_for_sources",
    }
    #: A combo item carrying this suffix is a rig type only planned for --
    #: listed so the panel shows the direction, disabled until it lands.
    PLANNED_SUFFIX = "(planned)"
    #: ``Atlas:`` combo -> whether to pack the built rigs' tiles: Auto packs
    #: once two rigs exist in the scene.
    ATLAS_MODES = ("Auto", "Off", "On")
    # Maya's Preview: the rig never edits or deletes the selected targets, so
    # the selection needs no duplicate-and-hide before each pass (costly on a
    # 10k-node hierarchy). Blender's Preview snapshots every operated object
    # regardless.
    MUTATES_SELECTION = False
    PRESERVE_GEOMETRY = False

    def __init__(self, switchboard):
        super().__init__(switchboard)
        self.ui = self.sb.loaded_ui.shadow_rig
        self.logger.set_log_prefix("[shadow_rig] ")

        #: The source names the live preview was built from.
        self._built_sources = None
        #: The rigs the last pass built: the commit hook packs them.
        self._built_rigs = []
        #: Every PNG a pass wrote (each rig's own, never the shared atlas):
        #: what a discard -- or a later pass that renamed the plane -- leaves.
        self._preview_textures = []
        # Create Shadow (b000) commits. The commit hook packs and previews what
        # the commit built; the discard hook repairs what no rollback reaches:
        # the data_export carrier's shadows record and the PNGs on disk.
        self.preview = self.tk.Preview(
            self,
            self.ui.chk_preview,
            self.ui.b000,
            finalize_func=self._after_commit,
            restore_func=self._after_discard,
            message_func=self.sb.message_box,
            undo_message="Shadow Rig",
        )

        # Any option change re-bakes the previewed rig.
        self.ui.cmb_type.currentIndexChanged.connect(self.preview.refresh)
        self.ui.cmb_planes.currentIndexChanged.connect(self.preview.refresh)
        self.ui.cmb_atlas.currentIndexChanged.connect(self.preview.refresh)
        self.ui.chk_combine.toggled.connect(self.preview.refresh)
        self.ui.s000.currentIndexChanged.connect(self.preview.refresh)
        # A renamed source must exist BEFORE the refresh rebuilds against it,
        # and outside the preview's rollback (see prepare_operation).
        self.ui.txt_source.editingFinished.connect(self._on_sources_edited)
        # b000-b003 and b009-b010 are auto-wired by the switchboard (method
        # name == objectName); a raw connect here on one of those stacked a
        # second connection -> double-fire. The deeper Utility actions (Apply
        # Source, Rebuild Rig, Restore Expression, Detach to Plane) hang off
        # b003's / b002's / b009's option boxes, and the actions about the
        # source (Source From Selection, Reproject) off Source Name's.

        self._init_tooltips()

    def header_init(self, widget):
        """Configure header help text."""
        widget.set_help_text(
            self.sb.tooltip.fmt(
                title="Shadow Rig",
                body="Create a projected-shadow plane rig that exports cleanly "
                "for game engines (Unity, WebXR). The plane carries the "
                "target's shadow as a PNG -- its geometry projected onto the "
                "ground through the source, the way a real shadow forms: an "
                "overhead source draws the footprint, a low one the long "
                "stretched shape, an area light a penumbra that softens away "
                "from the contact. A live expression (Blender: drivers) keeps "
                "the plane's direction, reach and fade tracking the source and "
                "the target.",
                steps=[
                    "Select one or more target meshes.",
                    "Pick the <b>Rig</b> type -- <b>Projected</b> (one silhouette "
                    "the model re-places) or <b>Horizon</b> (also bakes a "
                    "horizon map the engine samples per frame, so the outline "
                    "follows a runtime light).",
                    "Pick <b>Planes</b> -- <b>Combined</b> builds one plane for "
                    "the whole selection, <b>Per object</b> one per object -- and "
                    "<b>Atlas</b>: <b>Auto</b> packs the planes' tiles into one "
                    "texture per kind once two rigs exist, so the engines batch "
                    "and instance them.",
                    "Enable <b>Preview</b> to build the rig live. The source (a "
                    "locator; in Blender an Empty) is created once and survives "
                    "every refresh -- move it to place the light, or pick a real "
                    "light with <b>Source From Selection</b> (the pick icon "
                    "beside Source Name).",
                    "Tweak <b>Resolution</b> and <b>Include Children</b>; the "
                    "preview refreshes on each change.",
                    "Press <b>Create Shadow</b> to commit, or disable Preview "
                    "to discard.",
                    "Move the source, or the target under it: <b>Follow "
                    "Source</b> (on by default) re-renders every silhouette as "
                    "soon as either has moved -- the plane already follows "
                    "both, but the drawn shape is one direction's projection. "
                    "Off, or after a geometry edit (which it does not watch), "
                    "press <b>Reproject</b> (the refresh icon beside Source "
                    "Name) or <b>Recalculate Silhouette</b>.",
                    "<b>Softness</b> is the diameter the shadow gives the "
                    "source (world units; a directional light: degrees). It "
                    "lives on the source, so every rig it lights, Unity and "
                    "the viewer share one penumbra; 0 is sharp.",
                    "<b>Intensity</b> (overall darkness, 0-1) and <b>Ground "
                    "Y</b> (the floor's height -- Blender's Z -- when it is not "
                    "at 0) build into a new rig, and apply at once to the "
                    "rig(s) the selection touches -- a baked or unlinked plane "
                    "too.",
                    "A committed <b>Horizon</b> rig shows its live preview at "
                    "once, so its outline morphs as the light moves; the "
                    "<b>Live Horizon Preview</b> box mirrors what stands.",
                    "Export through the <b>Scene Exporter</b>: the rig's "
                    "<i>shadows</i> record rides the data_export carrier (in "
                    "Maya its smart bake also bakes the expression). For a "
                    "plain FBX export or a bridge, press <b>Bake to "
                    "Keyframes</b> first.",
                ],
                sections=[
                    (
                        "Sources",
                        [
                            "<b>Source Name</b> -- one or more object names, "
                            "comma-separated; one shadow plane is built per source.",
                            "<b>Source From Selection</b> -- use the selected "
                            "object(s), lights included, as the source(s). A "
                            "directional light (Blender: a Sun) projects along "
                            "its direction, like the sun. A fixture -- its "
                            "selected <b>faces</b> in Maya, a mesh in <b>Edit "
                            "Mode</b> in Blender -- gets a real area light per "
                            "shape, the way the Lighting panel builds them, and "
                            "that light becomes the source.",
                            "<b>Reproject</b> -- re-render the silhouette of every "
                            "rig the named source(s) light, from where the source "
                            "and the target are now: the manual form of Follow "
                            "Source, and the one to press after a geometry edit. "
                            "A Horizon rig's live map follows the light on its "
                            "own; its fallback silhouette is redrawn like the rest.",
                        ],
                    ),
                    (
                        "Utility",
                        [
                            "Every Utility button acts on the rig(s) the "
                            "selection touches -- the plane, its group, a target, "
                            "the source, or any other part of the rig -- also on "
                            "rigs built in an earlier session.",
                            "<b>Recalculate Silhouette</b> re-renders the PNG; "
                            "its option box holds the deeper updates: <b>Apply "
                            "Source</b> (re-point the rig at the Source Name "
                            "field) and <b>Rebuild Rig</b> (re-create it from the "
                            "target's current geometry with the panel's options). "
                            "<b>Bake to Keyframes</b>' option box holds <b>Restore "
                            "Expression</b>, its inverse; <b>Delete Rig</b> tears "
                            "the rig down.",
                        ],
                    ),
                    (
                        "Plane attributes",
                        [
                            "<b>shadowIntensity</b> / <b>falloffPower</b> -- overall "
                            "strength (the panel's Intensity) and how fast an "
                            "elongated shadow lightens.",
                            "<b>maxStretch</b> -- cap on the shadow's reach, in "
                            "object heights.",
                            "<b>fadeHeight</b> -- rise off the ground at which the "
                            "shadow has fully faded.",
                            "<b>groundHeight</b> -- world height (Maya's Y, "
                            "Blender's Z) of the ground the shadow lies on (the "
                            "panel's Ground Y).",
                        ],
                    ),
                ],
                notes=[
                    "Unity plug-and-play: deploy unitytk's C# templates once "
                    "(<i>unitytk.TemplateDeployer.deploy_package</i>) and export "
                    "via the Scene Exporter (in Maya with Embed Textures on) -- "
                    "the import sets up the unlit-transparent material and "
                    "shadow flags automatically. Other engines: assign an "
                    "unlit/transparent shader with the PNG by hand.",
                    "The fade is the plane's keyable <i>opacity</i>: it bakes "
                    "with the transform and rides the FBX as an animated "
                    "custom attribute.",
                ],
            )
        )

    def _init_tooltips(self):
        """Set the polished (uitk ``fmt``) tooltips for every option and action."""
        ui = self.ui
        tip = self.sb.tooltip.fmt

        ui.cmb_type.setToolTip(
            tip(
                title="Rig Type",
                body="Which shadow rig to build.",
                sections=[
                    (
                        "Types",
                        [
                            "<b>Projected</b> -- one silhouette, the target's "
                            "projection through the source, re-placed live by the "
                            "projection model; <b>Recalculate Silhouette</b> "
                            "re-renders it when the source has moved.",
                            "<b>Horizon</b> -- the projected rig plus a "
                            "coverage-aware horizon map (<i>&lt;name&gt;_horizon.png</i>) "
                            "baked in the target's own frame: the engine samples "
                            "it per frame from the source, so the outline "
                            "follows a moving light -- and a moved prop carries its "
                            "shadow -- without a re-render. The silhouette stays as "
                            "the fallback and the viewport preview. Design: "
                            "<i>mayatk/docs/shadow_rig_morphing.md</i>.",
                        ],
                    )
                ],
            )
        )
        ui.cmb_planes.setToolTip(
            tip(
                title="Planes",
                body="How many shadow planes the selection builds.",
                sections=[
                    (
                        "Modes",
                        [
                            "<b>Combined</b> -- one plane for the whole selection "
                            "(a table with the props on it casts one shadow). One "
                            "rigid caster: its anchor rides the parent the objects "
                            "share; moving one alone re-fits it here, but at "
                            "runtime it stays where it was drawn.",
                            "<b>Per object</b> -- one plane per selected object, "
                            "each with its own contact, tile and record; the "
                            "planes share an atlas and the engines instance them. "
                            "For objects that move independently.",
                        ],
                    )
                ],
                notes=["Either way, one plane is built per source."],
            )
        )
        ui.cmb_atlas.setToolTip(
            tip(
                title="Atlas",
                body="Pack the planes' tiles into one texture per kind -- the "
                "silhouettes into <i>shadow_atlas_projected.png</i>, the horizon "
                "maps into <i>shadow_atlas_horizon.png</i> -- so the engines draw "
                "every plane of a kind with one material and instance them.",
                sections=[
                    (
                        "Modes",
                        [
                            "<b>Auto</b> -- pack once the scene holds two rigs.",
                            "<b>Off</b> -- every plane keeps its own texture.",
                            "<b>On</b> -- always pack.",
                        ],
                    )
                ],
                notes=[
                    "Each plane keeps its own PNG: Recalculate rewrites its "
                    "tile in place, and a fallback viewer samples the atlas "
                    "through the plane's own UVs with no transform at all.",
                    "<b>Pack Atlas</b> in the Utility section packs or "
                    "repacks every rig in the scene.",
                ],
            )
        )
        ui.b010.setToolTip(
            tip(
                title="Pack Atlas",
                body="Pack (or repack) every shadow rig's tiles into the "
                "scene's atlases -- see the <b>Atlas</b> option.",
                notes=[
                    "Acts on the whole scene: the atlas is one file, so a "
                    "partial repack would move rects out from under the "
                    "other planes.",
                ],
            )
        )
        ui.chk_combine.setToolTip(
            tip(
                title="Include Children",
                body="Include the selected objects' descendant meshes in the "
                "baked silhouette.",
                notes=[
                    "The selection always shares a single combined shadow plane.",
                    "Off -- only the selected meshes themselves are rasterized.",
                ],
            )
        )
        ui.txt_source.setToolTip(
            tip(
                title="Source Name",
                body="The shadow source(s) the projection is cast from -- any "
                "object name (a light included), comma-separated for several. A "
                "missing name is created as a locator (Blender: an Empty) when "
                "the preview starts.",
                notes=[
                    "Reuse a name to share one source across rigs; one shadow "
                    "plane is built per source.",
                    "A directional light (Blender: a Sun) projects along its "
                    "direction; anything else casts from where it sits.",
                    "Move the source in the viewport -- the preview keeps it.",
                    "Its option box holds <b>Source From Selection</b> (the "
                    "pick icon) and <b>Reproject</b> (the refresh icon).",
                ],
            )
        )
        ui.s000.setToolTip(
            tip(
                title="Texture Resolution",
                body="Pixel resolution of the baked silhouette PNG carried by "
                "the shadow plane.",
                notes=[
                    "Higher = crisper shadow edge, but a larger texture on disk.",
                ],
            )
        )
        ui.chk_horizon_preview.setToolTip(
            tip(
                title="Live Horizon Preview",
                body="Shows a Horizon rig's shadow the way the engines will: "
                "the baked map evaluated in the viewport from the live source, "
                "so the outline morphs as you move the light.",
                notes=[
                    "Acts on the Horizon rig(s) the selection touches, or all "
                    "when nothing is selected.",
                    "Display only: nothing about the rig or its export changes, "
                    "and the preview is stood down before any FBX export.",
                    "Needs a hardware viewport: in Maya, Viewport 2.0 on DirectX "
                    "11 or OpenGL Core Profile; in Blender, a windowed session "
                    "(the GPU module has no backend headless).",
                ],
            )
        )
        ui.chk_preview.setToolTip(
            tip(
                title="Preview",
                body="Builds the shadow rig live so you can judge it before "
                "committing.",
                notes=[
                    "Tweaking any option refreshes the preview; the source "
                    "keeps its position.",
                    "<b>Create Shadow</b> commits it; disabling Preview discards it.",
                ],
            )
        )
        ui.b000.setToolTip(
            tip(
                title="Create Shadow",
                body="Commits the previewed shadow rig for the selected target(s), "
                "or builds one straight from the selection.",
                steps=[
                    "Select one or more target meshes.",
                    "Enable <b>Preview</b> and dial in the options.",
                    "Press <b>Create Shadow</b>.",
                ],
            )
        )
        ui.b002.setToolTip(
            tip(
                title="Bake to Keyframes",
                body="Bakes the shadow plane's driven motion and fade to "
                "keyframes over the playback range and removes the live rig -- "
                "leaving an FBX-ready plane.",
                notes=[
                    "Applies to the rig(s) the selection touches, or all planes "
                    "if nothing is selected.",
                    "In Maya the Scene Exporter's smart bake does this for you; "
                    "bake here before File > Export, the Game Exporter, or a "
                    "bridge.",
                    "Its option box holds <b>Restore Expression</b>, which "
                    "reverses it.",
                ],
            )
        )
        ui.b003.setToolTip(
            tip(
                title="Recalculate Silhouette",
                body="Re-renders the silhouette PNG from the source's current "
                "position and the target's current geometry, overwriting the "
                "plane's texture in place.",
                notes=[
                    "Applies to the rig(s) the selection touches, or all planes "
                    "if nothing is selected.",
                    "Works on a baked rig -- the PNG is drawn into the canvas "
                    "its keys describe.",
                    "Its option box holds the deeper updates: <b>Apply "
                    "Source</b> and <b>Rebuild Rig</b>.",
                ],
            )
        )
        ui.b009.setToolTip(
            tip(
                title="Delete Rig",
                body="Tears down the rig(s) the selection touches -- plane, "
                "group, expression (Blender: drivers), material and contact "
                "locator. The targets and the source are kept. Its option box "
                "holds <b>Detach to Plane</b>: keep the plane, drop the rig.",
            )
        )

    # -------------------------------------------------------- option boxes
    def cmb_type_init(self, widget):
        """A rig type the panel only plans for is listed but not selectable."""
        model = widget.model()
        for i in range(widget.count()):
            if widget.itemText(i).strip().endswith(self.PLANNED_SUFFIX):
                model.item(i).setEnabled(False)

    def txt_source_init(self, widget):
        """Source Name's option box: the two actions about the source --
        Source From Selection (the pick icon) and Reproject (the refresh
        icon). Idempotent: the switchboard runs an ``_init`` once per
        widget, but a test may run it by hand."""
        if getattr(widget, "_source_actions", None):
            return
        box = widget.option_box
        pick = box.add_action(
            callback=self.source_from_selection,
            icon="select",
            tooltip=self.sb.tooltip.fmt(
                title="Source From Selection",
                body="Uses the selected object(s) -- lights included -- as the "
                "shadow source(s), writing their names into Source Name.",
                notes=[
                    "Several selected objects build one shadow plane each.",
                    "A fixture -- its selected <b>faces</b> in Maya, a mesh in "
                    "<b>Edit Mode</b> in Blender -- gets a real area light per "
                    "shape (the Lighting panel's <i>Lights From Geometry</i>), "
                    "and that light becomes the source; its size draws the "
                    "shadow's penumbra.",
                    "With the preview running, the previewed targets are "
                    "rebuilt against the new source(s) at once.",
                ],
            ),
        )
        reproject = box.add_action(
            callback=self.reproject_sources,
            icon="refresh",
            tooltip=self.sb.tooltip.fmt(
                title="Reproject",
                body="Re-renders the silhouette of every rig the named "
                "source(s) light, from where the source and the target are "
                "now -- the manual form of Follow Source.",
                notes=[
                    "Press it with Follow Source off, or after editing the "
                    "target's geometry, which Follow Source does not watch.",
                    "A Horizon rig's live map follows the light on its own; "
                    "its fallback silhouette is redrawn like the rest.",
                    "<b>Recalculate Silhouette</b> in Utility does the same "
                    "for the rigs the selection touches.",
                ],
            ),
        )
        pick.widget.setObjectName("btn_source_from_selection")
        reproject.widget.setObjectName("btn_reproject")
        widget._source_actions = (pick, reproject)

    def b003_init(self, widget):
        """Recalculate Silhouette's option box: the deeper updates of an
        existing rig -- Apply Source and Rebuild Rig."""
        self._add_option_actions(
            widget,
            "Update Rig",
            [
                (
                    "btn_apply_source",
                    "Apply Source",
                    self.apply_source,
                    self.sb.tooltip.fmt(
                        title="Apply Source",
                        body="Re-points the rig(s) the selection touches at the "
                        "first Source Name, re-rendering their silhouettes from "
                        "there.",
                        notes=[
                            "A baked rig has its live expression (Blender: "
                            "drivers) restored first.",
                            "Select the plane, its group, a target, the old "
                            "source, or any other part of the rig.",
                        ],
                    ),
                ),
                (
                    "btn_rebuild",
                    "Rebuild Rig",
                    self.rebuild_rig,
                    self.sb.tooltip.fmt(
                        title="Rebuild Rig",
                        body="Re-creates the rig(s) the selection touches from "
                        "the target's current geometry, keeping their targets, "
                        "source and ground, with this panel's Resolution and "
                        "Include Children.",
                        notes=[
                            "The plane keeps its name, so an engine-side join "
                            "survives.",
                        ],
                    ),
                ),
            ],
        )

    def b002_init(self, widget):
        """Bake to Keyframes' option box: Restore Expression, its inverse."""
        self._add_option_actions(
            widget,
            "Bake",
            [
                (
                    "btn_restore",
                    "Restore Expression",
                    self.restore_expression,
                    self.sb.tooltip.fmt(
                        title="Restore Expression",
                        body="Un-bakes the rig(s) the selection touches: removes the "
                        "baked keys and rebuilds the live expression (Blender: "
                        "drivers) from the rig's stamped source and targets.",
                    ),
                ),
            ],
        )

    def b009_init(self, widget):
        """Delete Rig's option box: Detach to Plane, the teardown that keeps
        the plane."""
        self._add_option_actions(
            widget,
            "Delete",
            [
                (
                    "btn_detach",
                    "Detach to Plane",
                    self.detach_to_plane,
                    self.sb.tooltip.fmt(
                        title="Detach to Plane",
                        body="Turns the rig(s) the selection touches into plain "
                        "textured planes where they stand: one unlit material "
                        "and one PNG (the current fade baked into its alpha). "
                        "The live expression (Blender: drivers), the contact "
                        "locator and every rig attribute go, so nothing extra "
                        "exports -- for a shadow that no longer moves. Exports "
                        "unlit to WebXR.",
                    ),
                ),
            ],
        )

    @staticmethod
    def _add_option_actions(widget, title, actions):
        """Fill *widget*'s option box with push-button *actions* -- the rarer,
        deeper operations behind a Utility button -- from ``(objectName, text,
        handler, tooltip)`` rows. Idempotent -- the menu exposes its items as
        attributes by objectName, so a built menu is detectable: the switchboard
        runs an ``_init`` once per widget, but a test may run it by hand."""
        menu = widget.option_box.menu
        if getattr(menu, actions[0][0], None) is not None:
            return
        menu.setTitle(title)
        for name, text, handler, tooltip in actions:
            button = menu.add(
                "QPushButton", setText=text, setObjectName=name, setToolTip=tooltip
            )
            button.clicked.connect(handler)

    def b001_init(self, widget):
        """Reset to Defaults, on uitk's shared reset grammar (Shift+Click saves the
        current values as the defaults, Ctrl+Shift+Click forgets them)."""
        self._reset_gesture = self.sb.ResetGesture(widget)

    # ------------------------------------------------------------- helpers
    @contextlib.contextmanager
    def _one_step(self, name):
        """A button's work as ONE undo step named *name*, the viewport held
        still meanwhile (Maya redraws per command; Blender never mid-script)."""
        core = self.tk.CoreUtils
        with core.undo_chunk(name), core.suspended_refresh():
            yield

    def _name(self, node) -> str:
        """*node* as a message names it (Maya: a DAG path's leaf)."""
        return self.tk.CoreUtils.leaf_name(node)

    @staticmethod
    def _summary(what, done, failed):
        lines = []
        if done:
            lines.append(f"{what}: {', '.join(done)}")
        if failed:
            lines.append("Failed:\n  " + "\n  ".join(failed))
        return "\n".join(lines) or "Nothing done."

    # ------------------------------------------------------------- sources
    def _source_names(self):
        """The source names typed into the panel (comma-separated), or the default."""
        text = self.ui.txt_source.text() or ""
        names = [n.strip() for n in text.replace(";", ",").split(",")]
        names = list(dict.fromkeys(n for n in names if n))
        return names or [self.tk.ShadowRig.DEFAULT_SOURCE_NAME]

    def _set_source_names(self, names):
        self.ui.txt_source.setText(", ".join(names))

    def _ensure_sources(self):
        """Every named source exists (a missing one is created at the default
        position: a locator in Maya, an Empty in Blender). Runs OUTSIDE the
        preview's rollback -- see :meth:`prepare_operation`."""
        for name in self._source_names():
            self.tk.ShadowRig.ensure_source(name)

    def _on_sources_edited(self):
        """Source Name edited: create any new name first (outside the
        rollback), then refresh the preview against it. ``editingFinished``
        also fires on focus loss, so an unchanged field rebuilds nothing."""
        if self.preview.is_enabled:
            if self._source_names() == self._built_sources:
                self._sync_softness_box()
                return
            try:
                self._ensure_sources()
            except ValueError as e:  # Maya: the name is taken by a non-transform
                self.sb.message_box(str(e))
                return
        self._sync_softness_box()
        self.preview.refresh()

    def prepare_operation(self, objects):
        """Preview's one-shot precondition, run at enable outside any
        rollback: the source(s) exist before the rig is built.

        Built inside :meth:`perform_operation` the source was a created node
        of every preview pass -- each refresh and the commit rolled it back
        and recreated it at the default position, discarding wherever the
        user had placed it.
        """
        self._ensure_sources()

    def source_from_selection(self):
        """Source From Selection (Source Name's option box): the selected
        object(s) -- lights included -- become the source(s). A selected
        fixture (Maya: faces; Blender: a mesh in Edit Mode) gets a real area
        light per shape (``LightUtils.lights_from_geometry``, the Lighting
        panel's Lights From Geometry), and those lights become the sources."""
        names, fixtures = self.tk.ShadowRig.source_selection()
        if fixtures:
            created = self.tk.LightUtils.lights_from_geometry(fixtures)
            if not created:
                self.sb.message_box(
                    "No area light could be built from the selected fixture."
                )
                return
            self._set_source_names(list(created))
            self.sb.message_box(
                f"Built {len(created)} area light(s) from the selected fixture; "
                "they are now the shadow source(s). Select the target(s) and "
                "enable Preview."
            )
            self._on_sources_edited()
            return
        if not names:
            self.sb.message_box(
                "Select the object(s) to use as shadow source(s) -- or a "
                "fixture to build area lights from (Maya: its faces; Blender: "
                "the mesh in Edit Mode)."
            )
            return
        self._set_source_names(names)
        self._on_sources_edited()

    def reproject_sources(self):
        """Reproject (Source Name's option box): re-render the silhouette of
        every plane the named source(s) light, from where the source and the
        target are now -- the manual form of Follow Source, and the one to
        press after a geometry edit it does not watch. A Horizon rig's live
        map follows the light on its own; its fallback silhouette is redrawn
        like the rest."""
        engine = self.tk.ShadowRig
        names = self._source_names()
        planes, missing = [], []
        for name in names:
            source = engine.find_source(name)
            if source is None:
                missing.append(name)
                continue
            for plane in engine.planes_lit_by(source):
                if plane not in planes:
                    planes.append(plane)
        if not planes:
            self.sb.message_box(
                f"No shadow rig is lit by {', '.join(names)}."
                + (f" Missing: {', '.join(missing)}." if missing else "")
                + " Build one with Preview and Create Shadow, or name a "
                "rig's source."
            )
            return
        with self._one_step("Shadow Rig: Reproject"):
            refreshed = engine.refresh_silhouette(planes)
        self.sb.message_box(
            f"Reprojected {len(refreshed)} silhouette(s) from {', '.join(names)}."
        )

    # ------------------------------------------------------------ options
    def _rig_builder(self):
        """The host engine's builder for the ``Rig:`` combo's type.

        Raises:
            ValueError: the type is only planned for (its item is disabled, so
                this is a programmatic selection) -- the Preview reports it and
                turns itself off.
        """
        label = self.ui.cmb_type.currentText().split(":", 1)[-1].strip()
        key = label.replace(self.PLANNED_SUFFIX, "").strip()
        builder = self.RIG_BUILDERS.get(key)
        if builder is None:
            raise ValueError(
                f"The {key} rig is not available yet: a planned rig type "
                "(see mayatk/docs/shadow_rig_morphing.md)."
            )
        return getattr(self.tk.ShadowRig, builder)

    def _resolution(self):
        """The Resolution combo's value (``"Resolution: 512"`` -> 512)."""
        res_text = self.ui.s000.currentText()
        try:
            return int(res_text.replace("Resolution: ", "").strip())
        except (ValueError, AttributeError):
            return 512

    def _per_object(self):
        """True when the ``Planes:`` combo says one rig per selected object."""
        return "per object" in self.ui.cmb_planes.currentText().lower()

    def _atlas_mode(self):
        """The ``Atlas:`` combo's mode (``Auto`` / ``Off`` / ``On``)."""
        label = self.ui.cmb_atlas.currentText().split(":", 1)[-1].strip()
        return label if label in self.ATLAS_MODES else self.ATLAS_MODES[0]

    def _pack_if_wanted(self, rigs):
        """Pack the scene's tiles per the ``Atlas:`` combo: ``On`` always,
        ``Auto`` once the scene holds two rigs (a lone plane gains nothing
        from an atlas), ``Off`` never. Returns the atlas paths. Every rig
        carries a silhouette, so two rigs always fill the projected atlas;
        the horizon atlas takes the horizon rigs among them.

        The whole scene, not just the rigs this build made: there is one atlas
        per rig type, so a second rig has to join the first rather than start
        an atlas of its own -- and repacking is what gives every plane a rect
        that agrees with the file.

        Committed rigs only (:meth:`_after_commit`) -- an atlas is a file the
        rigs already in the scene sample, so packing during a preview pass
        would rewrite theirs (and a discard would take it away with the
        pass's own files). The preview shows the same shadow either way: the
        tile is reached through the plane's own UVs.
        """
        mode = self._atlas_mode()
        planes = self.tk.ShadowRig.find_shadow_planes()
        if mode == "Off" or not rigs or not planes:
            return {}
        if mode == "Auto" and len(planes) < 2:
            return {}
        return self.tk.ShadowRig.pack_atlas(planes)

    # ------------------------------------------------------------- preview
    def perform_operation(self, objects, contract=None):
        """Build one shadow rig per source for the selected target(s).

        Run by the Preview on every pass and on the commit (Maya's Preview
        passes a contract during a pass, Blender's none; neither is needed:
        what a pass leaves outside the rollback, :meth:`_after_discard`
        repairs).
        """
        recursive = self.ui.chk_combine.isChecked()
        names = self._source_names()
        targets = self.tk.ShadowRig.shadow_targets(objects, names, recursive=recursive)
        builder = self._rig_builder()
        groups = [[t] for t in targets] if self._per_object() else [targets]
        rigs = []
        for group in groups:
            rigs.extend(
                builder(
                    group,
                    names,
                    texture_res=self._resolution(),
                    recursive=recursive,
                    ground_height=self.ui.s003.value(),
                )
            )
        intensity = self.ui.s002.value()
        if intensity < 1.0:
            self.tk.ShadowRig.set_intensity([rig.shadow_plane for rig in rigs], intensity)
        self._built_sources = names
        # Packing and the horizon preview wait for the commit (_after_commit).
        self._built_rigs = rigs
        # Each rig's OWN PNGs, never the atlas: a shared file the rigs already
        # in the scene sample.
        for rig in rigs:
            for path in (rig.texture_path, rig.horizon_path):
                if path and path not in self._preview_textures:
                    self._preview_textures.append(path)

    def _alive(self, rigs):
        """The *rigs* whose plane still exists (Blender: a pass the preview
        rolled back leaves a dead reference)."""
        alive = []
        for rig in rigs:
            try:
                if rig.shadow_plane is not None and self._name(rig.shadow_plane):
                    alive.append(rig)
            except ReferenceError:
                continue
        return alive

    def _after_commit(self):
        """The Preview's commit hook (both commit paths, never a discard):
        pack the scene's tiles, show a new Horizon rig's live preview, and
        remove the PNGs of passes the commit superseded."""
        rigs = self._alive(self._built_rigs)
        textures = self._preview_textures
        self._built_rigs, self._preview_textures = [], []
        self._pack_if_wanted(rigs)
        self._preview_new_horizon(rigs)
        # The committed planes' own PNGs are in use, so they stay.
        self.tk.ShadowRig.delete_orphaned_textures(textures)
        # A committed Horizon rig is something the preview box can act on.
        self._sync_preview_box()

    def _after_discard(self):
        """The Preview's discard hook (un-check or a failed pass, never a
        commit), after its rollback: republish the data_export carrier's
        shadows record from the planes left, and remove the PNGs no plane
        uses any more (a committed rig's are kept)."""
        textures = self._preview_textures
        self._built_rigs, self._preview_textures = [], []
        self.tk.ShadowRig.refresh_export_metadata()
        self.tk.ShadowRig.delete_orphaned_textures(textures)

    def _preview_new_horizon(self, rigs):
        """A committed Horizon rig shows its live preview at once, where the
        session can draw it: the morphing outline IS the rig, and a horizon
        plane without its preview is indistinguishable from a Projected one.
        A refusal only informs (the box's tooltip carries the reason); the
        box mirrors what stands either way."""
        planes = [
            rig.shadow_plane
            for rig in rigs
            if rig.rig_type == "horizon" and rig.shadow_plane is not None
        ]
        if not planes:
            return
        preview = self.tk.ShadowPreview
        language, refusal = preview.language()
        if language is None:
            self.logger.info(f"Horizon preview not shown: {refusal}")
            return
        done, failed = preview.toggle(planes, on=True)
        if failed:
            self.logger.warning(self._summary("Horizon preview on", done, failed))

    # ------------------------------------------------------------- utility
    def _selected_planes(self, action, allow_all=False):
        """The shadow planes the selection touches for a Utility *action*;
        with *allow_all*, every plane when nothing is selected. Reports and
        returns an empty list when there is nothing to act on."""
        engine = self.tk.ShadowRig
        sel = self.tk.CoreUtils.selected_objects()
        if not sel:
            if allow_all:
                planes = engine.find_shadow_planes()
                if not planes:
                    self.sb.message_box("No shadow planes in the scene.")
                return planes
            self.sb.message_box(
                f"Select the shadow plane(s) to {action} -- or the rig's group, a "
                "target, or its source."
            )
            return []
        planes = engine.planes_for_nodes(sel)
        if not planes:
            self.sb.message_box(
                "The selection touches no shadow rig. Select the plane(s) to "
                f"{action}, the rig's group, a target, or its source"
                + (", or clear the selection to act on all." if allow_all else ".")
            )
        return planes

    def chk_follow_init(self, widget):
        """Follow Source arms the engine's watcher from the box's (saved)
        state on every show, so a reopened panel and a restored setting
        agree with what the scene does."""
        widget.refresh_on_show = True
        self.tk.ShadowRig.auto_recalculate(widget.isChecked())

    def chk_follow(self, checked):
        """Follow Source: re-render a silhouette as soon as its source -- or
        its target -- has moved: the drawn shape is one direction's
        projection, and only the plane's placement followed them before.
        Off leaves Reproject and Recalculate Silhouette as the manual ways."""
        self.tk.ShadowRig.auto_recalculate(checked)
        if checked:
            done = self.tk.ShadowRig.recalculate_stale()
            if done:
                self.logger.info(f"Follow Source recalculated {len(done)} plane(s).")

    def s001_init(self, widget):
        """Softness shows the scene's value for the first Source Name -- its
        Softness when set, else the light's physical size -- never a saved
        setting; re-read on every show and whenever the names change."""
        widget.restore_state = False
        widget.refresh_on_show = True
        self._softness_tip = widget.toolTip()
        self._sync_softness_box()

    def s001(self, value):
        """Softness: the diameter the shadow gives the source(s) named in
        Source Name (world units; a directional light: degrees of angular
        diameter), set on the source itself so every rig it lights shares
        it, in Unity and the viewer too. A missing source is created, as
        Preview would; the planes it lights are Recalculated at once."""
        engine = self.tk.ShadowRig
        with self._one_step("Shadow Rig: Softness"):
            planes = []
            try:
                for name in self._source_names():
                    source = engine.ensure_source(name)
                    for plane in engine.set_source_softness(source, value):
                        if plane not in planes:
                            planes.append(plane)
            except ValueError as e:  # Maya: the name is taken by a non-transform
                self.sb.message_box(str(e))
                return
            if planes:
                engine.refresh_silhouette(planes)

    def _sync_softness_box(self):
        """Put the first named source's effective size in the box, in the
        box's units, with the source and the units on the tooltip."""
        engine = self.tk.ShadowRig
        box = self.ui.s001
        name = self._source_names()[0]
        source = engine.find_source(name)
        value, units, origin = 0.0, "world units", "no source yet"
        if source is not None:
            directional = engine.source_is_directional(source)
            units = "degrees" if directional else "world units"
            softness = engine.source_softness(source)
            if softness is not None:
                value, origin = softness, "its Softness"
            else:
                value = engine.source_size(source)
                if directional:
                    value = math.degrees(value)
                origin = "its physical size"
        box.blockSignals(True)
        try:
            box.setValue(float(value))
        finally:
            box.blockSignals(False)
        box.setToolTip(
            self.sb.tooltip.fmt(
                title="Softness",
                body=f"{getattr(self, '_softness_tip', '')}<br>"
                f"<b>{name}</b>: {value:.3g} {units} ({origin}).",
            )
        )

    def s002(self, value):
        """Intensity: the overall darkness a new rig builds with, applied at
        once to the rig(s) the selection touches (``ShadowRig.set_intensity``
        -- a baked or unlinked plane's own fade is rescaled; one undo step of
        its own). Under Preview it rebuilds the previewed rig instead."""
        self._retune_selected(self.tk.ShadowRig.set_intensity, value)

    def s003(self, value):
        """Ground Y: the floor's world height (Blender's Z) a new rig builds
        on, applied at once to the rig(s) the selection touches
        (``ShadowRig.set_ground_height``; one undo step of its own)."""
        self._retune_selected(self.tk.ShadowRig.set_ground_height, value)

    def _retune_selected(self, setter, value):
        """Hand *value* to *setter* for the selection's planes; with nothing
        selected (or no rig in it) the box is only the next build's value."""
        if self.preview.is_enabled:
            self.preview.refresh()
            return
        sel = self.tk.CoreUtils.selected_objects()
        planes = self.tk.ShadowRig.planes_for_nodes(sel) if sel else []
        if planes:
            setter(planes, value)

    def chk_horizon_preview_init(self, widget):
        """The box mirrors the SCENE, never a saved setting: checked while a
        preview stands, enabled only where one can stand -- a Horizon rig in
        the scene and a session that can draw it. A restored "checked" with
        nothing attached is what made the box need a second toggle before it
        did anything."""
        widget.restore_state = False  # never read back from QSettings
        widget.refresh_on_show = True  # re-synced every time the panel shows
        self._preview_tip = widget.toolTip()
        self._install_scene_sync()
        self._sync_preview_box()

    def _install_scene_sync(self):
        """Re-sync the box after a scene open / new (a fresh scene has no
        previews; a saved one may carry them). Once per panel instance; the
        subscriptions die with the panel widget."""
        if getattr(self, "_scene_sync_installed", False):
            return
        self._scene_sync_installed = True
        try:
            mgr = self.tk.ScriptJobManager.instance()
            for event in ("SceneOpened", "NewSceneOpened"):
                mgr.subscribe(event, self._sync_preview_box, owner=self)
            mgr.connect_cleanup(self.ui, owner=self)
        except RuntimeError:
            pass  # no event hooks here (batch): the show-time sync still runs

    def _sync_preview_box(self):
        """Checked = a preview stands on some horizon plane; enabled = the
        scene has a Horizon rig and this session can draw its preview, with
        the reason on the tooltip when it cannot."""
        engine = self.tk.ShadowRig
        box = self.ui.chk_horizon_preview
        horizon = [
            p for p in engine.find_shadow_planes() if engine.plane_type(p) == "horizon"
        ]
        attached = []
        if not horizon:
            reason = "No Horizon rig in the scene to preview."
        else:
            language, refusal = self.tk.ShadowPreview.language()
            reason = "" if language is not None else refusal
            attached = self.tk.ShadowPreview.attached_planes()
        box.blockSignals(True)
        try:
            box.setChecked(bool(attached))
            box.setEnabled(not reason)
        finally:
            box.blockSignals(False)
        tip = getattr(self, "_preview_tip", box.toolTip())
        box.setToolTip(
            tip
            if not reason
            else self.sb.tooltip.fmt(title="Live Horizon Preview", body=reason)
        )

    def chk_horizon_preview(self, checked):
        """Live Horizon Preview: the horizon plane(s) the selection touches
        (or all) shown the way the engines will -- the baked map evaluated
        from the live source, so the outline morphs as the light moves.
        Display state only: the rig and its export are untouched, and every
        preview is stood down before an FBX export."""
        planes = self._selected_planes("preview", allow_all=True)
        horizon = [p for p in planes if self.tk.ShadowRig.plane_type(p) == "horizon"]
        if not horizon:
            if planes:
                self.sb.message_box(
                    "The selection touches no <b>Horizon</b> rig. The live "
                    "preview evaluates a baked horizon map; a Projected rig's "
                    "silhouette already is its preview."
                )
            self._sync_preview_box()
            return
        if checked:
            language, refusal = self.tk.ShadowPreview.language()
            if language is None:
                self.sb.message_box(refusal)
                self._sync_preview_box()
                return
        done, failed = self.tk.ShadowPreview.toggle(horizon, on=checked)
        if failed:
            self.sb.message_box(
                self._summary(
                    "Horizon preview " + ("on" if checked else "off"), done, failed
                )
            )
        # The box shows what stands, not what was asked for.
        self._sync_preview_box()

    def b002(self):
        """Bake to Keyframes: bake the rig(s) the selection touches (or all)
        to keys over the playback range and remove the live rig."""
        planes = self._selected_planes("bake", allow_all=True)
        if not planes:
            return
        with self._one_step("Shadow Rig: Bake"):
            baked = self.tk.ShadowRig.bake_planes(planes)
        if baked:
            self.sb.message_box(f"Baked {len(baked)} shadow plane(s) to keyframes.")
        else:
            self.sb.message_box("No shadow planes with a live rig found.")

    def b003(self):
        """Recalculate Silhouette: re-render the rig(s) the selection touches
        (or all) from their source's current position."""
        planes = self._selected_planes("recalculate", allow_all=True)
        if not planes:
            return
        with self._one_step("Shadow Rig: Recalculate Silhouette"):
            refreshed = self.tk.ShadowRig.refresh_silhouette(planes)
        if refreshed:
            self.sb.message_box(f"Recalculated {len(refreshed)} silhouette(s).")
        else:
            self.sb.message_box(
                "No shadow planes to recalculate (rigs built before the "
                "target/source stamps must be re-created)."
            )

    def apply_source(self):
        """Apply Source (Recalculate's option box): re-point the rig(s) the
        selection touches at the first Source Name and re-render their
        silhouettes."""
        planes = self._selected_planes("re-source")
        if not planes:
            return
        engine = self.tk.ShadowRig
        with self._one_step("Shadow Rig: Apply Source"):
            try:
                source = engine.ensure_source(self._source_names()[0])
            except ValueError as e:  # Maya: the name is taken by a non-transform
                self.sb.message_box(str(e))
                return
            done, failed = [], []
            for plane in planes:
                name = self._name(plane)
                rig = engine.from_plane(plane)
                if rig is None:
                    failed.append(f"{name}: built before the stamps")
                    continue
                try:
                    rig.set_source(source, size=self._resolution())
                    done.append(name)
                except Exception as e:  # noqa: BLE001 -- one plane never blocks the rest
                    failed.append(f"{name}: {e}")
                    self.logger.error(f"Apply Source ({name}): {e}", exc_info=True)
        self.sb.message_box(
            self._summary(f"Source now {self._name(source)}", done, failed)
        )

    def rebuild_rig(self):
        """Rebuild Rig (Recalculate's option box): re-create the rig(s) the
        selection touches from the target's current geometry with this
        panel's options."""
        planes = self._selected_planes("rebuild")
        if not planes:
            return
        done, failed = [], []
        with self._one_step("Shadow Rig: Rebuild"):
            for plane in planes:
                name = self._name(plane)
                try:
                    rig = self.tk.ShadowRig.rebuild(
                        plane,
                        texture_res=self._resolution(),
                        recursive=self.ui.chk_combine.isChecked(),
                    )
                except Exception as e:  # noqa: BLE001 -- one plane never blocks the rest
                    failed.append(f"{name}: {e}")
                    self.logger.error(f"Rebuild ({name}): {e}", exc_info=True)
                    continue
                if rig is None:
                    failed.append(f"{name}: built before the stamps, or its parts are gone")
                else:
                    done.append(name)
        self._sync_preview_box()
        self.sb.message_box(self._summary("Rebuilt", done, failed))

    def restore_expression(self):
        """Restore Expression (Bake's option box): un-bake the rig(s) the
        selection touches."""
        planes = self._selected_planes("restore")
        if not planes:
            return
        with self._one_step("Shadow Rig: Restore Expression"):
            restored = self.tk.ShadowRig.unbake_planes(planes)
        if restored:
            self.sb.message_box(f"Restored the live rig on {len(restored)} plane(s).")
        else:
            self.sb.message_box(
                "Nothing to restore: the selected rig(s) are live already, or "
                "predate the target/source stamps."
            )

    def b009(self):
        """Delete Rig: tear down the rig(s) the selection touches."""
        planes = self._selected_planes("delete")
        if not planes:
            return
        with self._one_step("Shadow Rig: Delete"):
            deleted = self.tk.ShadowRig.delete_rigs(planes)
        self._sync_preview_box()
        self.sb.message_box(f"Deleted {len(deleted)} shadow rig(s).")

    def detach_to_plane(self):
        """Detach to Plane (Delete Rig's option box): the rig(s) the selection
        touches become plain textured planes (``ShadowRig.detach_planes``,
        one undo step of its own)."""
        planes = self._selected_planes("detach")
        if not planes:
            return
        names = [self._name(p) for p in planes]
        done = [self._name(p) for p in self.tk.ShadowRig.detach_planes(planes)]
        self._sync_preview_box()
        self.sb.message_box(
            self._summary(
                "Detached to plane",
                done,
                [f"{n}: no silhouette on disk" for n in names if n not in done],
            )
        )

    def b010(self):
        """Pack Atlas: pack or repack every shadow rig's tiles into the
        scene's atlases (one per kind)."""
        planes = self.tk.ShadowRig.find_shadow_planes()
        if not planes:
            self.sb.message_box("No shadow planes in the scene.")
            return
        with self._one_step("Shadow Rig: Pack Atlas"):
            packed = self.tk.ShadowRig.pack_atlas(planes)
        if packed:
            names = ", ".join(os.path.basename(p) for p in packed.values())
            self.sb.message_box(f"Packed {len(planes)} plane(s) into {names}.")
        else:
            self.sb.message_box("No tiles to pack -- the planes' PNGs are missing.")
