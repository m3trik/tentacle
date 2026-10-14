# !/usr/bin/python
# coding=utf-8
import os
from typing import List

import maya.cmds as cmds
import maya.mel as mel

from tentacle import RenderingMixin, SlotsMaya
import mayatk as mtk
import pythontk as ptk


class RenderingSlots(RenderingMixin, SlotsMaya):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.ui = self.sb.loaded_ui.rendering
        self.submenu = self.sb.loaded_ui.rendering_submenu
        # (camera, renderer) of the last render this session — drives Smart Redo.
        self._last_render_key = None

    # Curated multi-output bundles appended after the registry's individual
    # targets (single-capture planning makes multi-target exports cheap).
    _TARGET_BUNDLES = [
        ("MP4 + PNG Sequence", ["mp4", "png_sequence"]),
        ("MP4 + Arnold Sequence", ["mp4", "arnold"]),
    ]

    def tb000_init(self, widget):
        """Export Playblast: built once, then re-run on every panel show.

        ``refresh_on_show`` re-runs this init, so the output field's
        placeholder (the default path, ``_show_playblast_default``) follows the
        open scene instead of the one the panel was built in.
        """
        menu = widget.option_box.menu
        if not getattr(widget, "_playblast_menu_built", False):
            widget.refresh_on_show = True
            self._build_playblast_menu(menu)
            widget._playblast_menu_built = True
        self._show_playblast_default(menu.t000)

    def _build_playblast_menu(self, menu):
        """Add the Playblast option box's controls."""
        menu.setTitle("Playblast Export")

        playback_min = int(cmds.playbackOptions(q=True, minTime=True))
        playback_max = int(cmds.playbackOptions(q=True, maxTime=True))

        # Left empty: the placeholder shows the scene's default, and a blank
        # field resolves to it at playblast time (_split_output_base).
        menu.add(
            "QLineEdit",
            setObjectName="t000",
            setToolTip="Output directory, or directory plus base name. A bare directory "
            "uses the scene name; any typed extension is ignored (each output appends its own). "
            "Blank: the default shown, the scene workspace's movie folder.",
        )
        menu.add(
            "QComboBox",
            addItems=[
                "Playback Range",
                "Animation Range",
                "Current Frame",
                "Custom Range",
            ],
            setObjectName="cmb010",
            setCurrentIndex=0,
            block_signals_on_restore=False,
            setToolTip="Frame range preset controlling the start and end frames.",
        )
        menu.add(
            "QSpinBox",
            setPrefix="Custom Start Frame: ",
            setObjectName="s010",
            setMinimum=-1000000,
            setMaximum=1000000,
            setValue=playback_min,
            setToolTip="First frame included in the playblast range when using Custom Range.",
        )
        menu.add(
            "QSpinBox",
            setPrefix="Custom End Frame: ",
            setObjectName="s011",
            setMinimum=-1000000,
            setMaximum=1000000,
            setValue=playback_max,
            setToolTip="Last frame included in the playblast range when using Custom Range.",
        )
        menu.add(
            "QSpinBox",
            setPrefix="Frame Padding: ",
            setObjectName="s012",
            setMinimum=1,
            setMaximum=10,
            setValue=4,
            setToolTip="Number of digits to use when naming image sequence frames.",
        )
        menu.add(
            "QComboBox",
            addItems=[
                "3840 x 2160",
                "2560 x 1440",
                "1920 x 1080",
                "1280 x 720",
                "960 x 540",
                "640 x 360",
            ],
            setObjectName="cmb040",
            setCurrentIndex=2,
            block_signals_on_restore=False,
            setToolTip="Resolution preset applied to all playblast captures.",
        )
        menu.add(
            "QSpinBox",
            setPrefix="Scale %: ",
            setObjectName="s015",
            setMinimum=1,
            setMaximum=100,
            setValue=100,
            setToolTip="Viewport scaling percentage applied by Maya prior to capture.",
        )
        menu.add(
            "QComboBox",
            addItems=[
                "Draft (20)",
                "Preview (50)",
                "Low (70)",
                "Medium (80)",
                "High (90)",
                "Maximum (100)",
            ],
            setObjectName="cmb016",
            setCurrentIndex=5,
            block_signals_on_restore=False,
            setToolTip="Quality applied to movie outputs (native playblast quality; "
            "encoding rate factor for MP4/MOV).",
        )

        camera_items = ["Active Viewport"] + self._camera_transforms()
        menu.add(
            "QComboBox",
            addItems=camera_items,
            setObjectName="cmb041",
            setCurrentIndex=0,
            block_signals_on_restore=False,
            setToolTip="Camera override used during playblast capture.",
        )

        menu.add(
            "QComboBox",
            setObjectName="cmb050",
            setCurrentIndex=0,
            setMaxVisibleItems=12,
            block_signals_on_restore=False,
            setToolTip=(
                "Output(s) to generate. MP4/MOV are encoded from a single lossless "
                "capture via FFmpeg; sequences keep real scene frame numbers; bundles "
                "produce several outputs from one capture pass."
            ),
        )
        menu.add(
            "QCheckBox",
            setText="Offscreen Capture",
            setObjectName="chk056",
            setChecked=True,
            setToolTip="Enable Maya's offscreen playblast capture mode to avoid viewport redraw issues.",
        )
        menu.add(
            "QCheckBox",
            setText="Show Ornaments",
            setObjectName="chk057",
            setChecked=True,
            setToolTip="Include HUD and ornament elements in the capture.",
        )
        menu.add(
            "QCheckBox",
            setText="Open When Done",
            setObjectName="chk058",
            setChecked=False,
            setToolTip="Open the first finished movie output with its default application.",
        )
        menu.add(
            "QCheckBox",
            setText="Include Audio",
            setObjectName="chk060",
            setChecked=False,
            setToolTip="Attach the timeline's active sound to movie outputs "
            "(muxed into MP4/MOV; native playblast audio for AVI).",
        )

        range_combo = menu.cmb010
        range_combo.setItemData(0, {"mode": "playback"})
        range_combo.setItemData(1, {"mode": "animation"})
        range_combo.setItemData(2, {"mode": "current"})
        range_combo.setItemData(3, {"mode": "custom"})

        custom_start = menu.s010
        custom_end = menu.s011
        custom_start.setVisible(False)
        custom_end.setVisible(False)

        def update_range_widgets(index):
            mode_data = range_combo.itemData(index) or {}
            is_custom = mode_data.get("mode") == "custom"
            custom_start.setVisible(is_custom)
            custom_end.setVisible(is_custom)
            if not is_custom:
                custom_start.setValue(playback_min)
                custom_end.setValue(playback_max)

        range_combo.currentIndexChanged.connect(update_range_widgets)
        update_range_widgets(range_combo.currentIndex())

        resolution_combo = menu.cmb040
        preset_sizes = {
            0: (3840, 2160),
            1: (2560, 1440),
            2: (1920, 1080),
            3: (1280, 720),
            4: (960, 540),
            5: (640, 360),
        }
        for index, size in preset_sizes.items():
            resolution_combo.setItemData(index, size)

        quality_combo = menu.cmb016
        quality_map = {
            0: 20,
            1: 50,
            2: 70,
            3: 80,
            4: 90,
            5: 100,
        }
        for index, value in quality_map.items():
            quality_combo.setItemData(index, value)

        camera_combo = menu.cmb041
        camera_combo.restore_by = "text"  # scene-dependent items; index is unstable
        camera_combo.setItemData(0, None)
        for idx, camera_name in enumerate(camera_items[1:], start=1):
            camera_combo.setItemData(idx, camera_name)

        # Output picker is registry-driven: individual targets from the
        # exporter, then the curated bundles.
        output_combo = menu.cmb050
        output_combo.restore_by = "text"  # registry-driven items; index is unstable
        entries = [
            (label, [name]) for name, label in mtk.PlayblastExporter.available_targets()
        ]
        entries += self._TARGET_BUNDLES
        output_combo.addItems([label for label, _ in entries])
        for idx, (_, target_names) in enumerate(entries):
            output_combo.setItemData(idx, target_names)

    @SlotsMaya.Cancelable(600)
    def tb000(self, widget):
        """Export Playblast"""

        # A playblast over a static scene is just N identical frames — bail before
        # doing any capture work if nothing is keyed over time.
        if not mtk.AnimUtils.scene_has_animation():
            self.sb.message_box("No animation in the scene — nothing to playblast.")
            return

        menu = widget.option_box.menu

        range_data = menu.cmb010.itemData(menu.cmb010.currentIndex()) or {}
        range_mode = range_data.get("mode", "playback")
        start_frame = end_frame = None
        if range_mode == "custom":
            start_frame = int(menu.s010.value())
            end_frame = int(menu.s011.value())
            if start_frame > end_frame:
                self.sb.message_box(
                    "Start frame must be less than or equal to end frame."
                )
                return

        targets = menu.cmb050.itemData(menu.cmb050.currentIndex()) or []
        if not targets:
            self.sb.message_box("Select an output before running the playblast.")
            return
        # MP4/MOV need ffmpeg for a second at the END of a minutes-long capture:
        # offer the install now, never an error after the wait.
        # .get: a stale persisted picker entry is the exporter's ValueError to
        # raise ("Unknown export target"), not a KeyError here.
        registry = mtk.PlayblastExporter.TARGETS
        needs_encoder = any(
            getattr(registry.get(t), "kind", None) == "encode" for t in targets
        )
        if needs_encoder and not self._ffmpeg_ready():
            return

        output_dir, output_name = self._split_output_base(menu.t000.text())

        resolution = menu.cmb040.itemData(menu.cmb040.currentIndex()) or (1920, 1080)
        camera_selection = menu.cmb041.itemData(menu.cmb041.currentIndex())

        exporter = mtk.PlayblastExporter(
            camera=str(camera_selection) if camera_selection else None,
            width=resolution[0],
            height=resolution[1],
            percent=int(menu.s015.value()),
            quality=int(menu.cmb016.itemData(menu.cmb016.currentIndex()) or 100),
            off_screen=menu.chk056.isChecked(),
            show_ornaments=menu.chk057.isChecked(),
            frame_padding=int(menu.s012.value()),
            include_audio=menu.chk060.isChecked(),
        )

        with self.sb.progress(text="Working: Export Playblast") as update:
            results = exporter.export(
                output_dir=output_dir,
                name=output_name,
                targets=targets,
                range_mode=range_mode,
                start=start_frame,
                end=end_frame,
                progress_callback=self.sb.progress_adapter(update),
            )

        outputs: List[str] = []
        errors: List[str] = []
        movie_outputs: List[str] = []
        for result in results:
            label = mtk.PlayblastExporter.TARGETS[result.target].label
            if not result.ok:
                errors.append(f"{label}: {result.error}")
            elif isinstance(result.output, list):
                outputs.append(f"{label}: {len(result.output)} frame(s)")
            elif result.output:
                outputs.append(f"{label}: {result.output}")
                if result.kind in ("encode", "native"):
                    movie_outputs.append(result.output)

        if menu.chk058.isChecked() and movie_outputs:
            # The OS's default player (xdg-open on Linux); best-effort.
            ptk.FileUtils.open_explorer(os.path.normpath(movie_outputs[0]))

        if errors:
            self.sb.message_box(
                "One or more playblast exports failed:<br>" + "<br>".join(errors)
            )
        elif outputs:
            self.sb.message_box("Playblast export complete:<br>" + "<br>".join(outputs))
        else:
            self.sb.message_box("No playblast outputs were generated.")

    def _split_output_base(self, text: str) -> tuple:
        """Split the output field into (directory, base name).

        A bare/existing directory (or trailing separator) uses the scene
        name; a typed extension is dropped (each target appends its own); an
        empty field falls back to the default playblast path.
        """
        raw = (text or "").strip()
        base = raw or self._default_playblast_path()
        base = os.path.normpath(os.path.expanduser(os.path.expandvars(base)))
        if os.path.isdir(base) or raw.endswith(("/", "\\")):
            return base, self._scene_base_name()
        directory, name = os.path.split(base)
        name = os.path.splitext(name)[0] or self._scene_base_name()
        if not directory:
            directory = os.path.dirname(self._default_playblast_path())
        return directory, name

    #: Scene-backed render-setting fields in the Render option box, grouped
    #: under a separator each: ``(objectName, RenderUtils key, label, min,
    #: max)``. The maxima sit well above any sane value: a scene value past a
    #: spinbox's maximum would display clamped -- a lie about the scene.
    #: The keys are ``mtk.RenderUtils.RENDER_SETTINGS``'s, so a field, a preset
    #: and a script all name a setting the same way.
    _RESOLUTION_FIELDS = (
        ("s020", "width", "Width", 1, 32768),
        ("s021", "height", "Height", 1, 32768),
    )
    _ARNOLD_FIELDS = (
        # AA 0 traces no camera rays at all; 0 per-ray samples is a valid "off".
        ("s022", "camera_samples", "Camera (AA)", 1, 100),
        ("s023", "diffuse_samples", "Diffuse", 0, 100),
        ("s024", "specular_samples", "Specular", 0, 100),
        ("s025", "transmission_samples", "Transmission", 0, 100),
        ("s026", "diffuse_depth", "Diffuse Depth", 0, 100),
        ("s027", "specular_depth", "Specular Depth", 0, 100),
        ("s028", "transmission_depth", "Transmission Depth", 0, 100),
    )

    def tb001_init(self, widget):
        """Render: camera, renderer, IPR, smart redo, key settings and presets.

        Built once, then re-run on every panel show (``refresh_on_show``): the
        camera list and the setting fields re-read the scene, so a new or
        re-opened scene never shows the last one's values. The setting fields
        are the scene's own render settings -- written as they change, never
        session-restored -- and the menu's native preset selector applies
        ``mtk.RenderUtils``'s render presets (shipped Arnold tiers + saved ones)
        to the same settings.
        """
        menu = widget.option_box.menu
        if not getattr(widget, "_render_menu_built", False):
            widget.refresh_on_show = True
            self._build_render_menu(menu)
            widget._render_menu_built = True
        self._refresh_cameras(menu)
        self._sync_render_options(menu)

    def _build_render_menu(self, menu):
        """Add the Render option box's controls and wire its preset selector."""
        menu.setTitle("Render")

        # Camera transforms (not shapes): Render-View procs expect a transform.
        # Populated from the scene on every show (_refresh_cameras).
        menu.add(
            "QComboBox",
            setObjectName="cmb002",
            block_signals_on_restore=False,
            setToolTip="Camera to render into the Render View / IPR.",
        )

        # Renderer: built-ins + installed plugins; default to the active one.
        renderers = mtk.RenderUtils.get_available_renderers()
        menu.add(
            "QComboBox",
            addItems=[r["label"] for r in renderers],
            setObjectName="cmb003",
            block_signals_on_restore=False,
            setToolTip="Renderer to use. Installed-but-unloaded renderers "
            "(e.g. Arnold) load on demand when selected.",
        )
        for i, r in enumerate(renderers):
            menu.cmb003.setItemData(i, r["name"])
        names = [r["name"] for r in renderers]
        current = mtk.RenderUtils.current_renderer()
        if current in names:
            menu.cmb003.setCurrentIndex(names.index(current))

        menu.add(
            "QCheckBox",
            setText="IPR (realtime)",
            setObjectName="chk001",
            setChecked=False,
            setToolTip="Launch interactive realtime rendering instead of a single "
            "frame. Disabled automatically for renderers that don't provide IPR.",
        )
        menu.add(
            "QCheckBox",
            setText="Smart Redo",
            setObjectName="chk002",
            setChecked=True,
            setToolTip="Re-render the previous result when the camera and renderer "
            "are unchanged (faster); otherwise render fresh.",
        )

        for title, fields in (
            ("Resolution", self._RESOLUTION_FIELDS),
            ("Arnold Sampling", self._ARNOLD_FIELDS),
        ):
            menu.add("Separator", setTitle=title)
            for name, key, label, minimum, maximum in fields:
                field = menu.add(
                    "QSpinBox",
                    setObjectName=name,
                    setPrefix=f"{label}: ",
                    set_limits=[minimum, maximum],
                    # Typed digits commit once (Enter / focus out), not per
                    # keystroke: "1920" must not write 1, 19 and 192 first.
                    setKeyboardTracking=False,
                    setToolTip=f"The scene's {label} render setting, applied as "
                    "it changes. Presets below set several at once.",
                )
                # The scene owns these values: a restored session value would
                # overwrite the open scene's settings. (Also keeps them out of
                # Restore Defaults: no default is captured without it.)
                field.restore_state = False
                field.valueChanged.connect(
                    lambda value, k=key: self._write_render_setting(menu, k, value)
                )

        # The menu's native preset selector, in semantic mode: a preset is a
        # ``{setting: value}`` dict read from and applied to the SCENE, so the
        # files are the ones ``mtk.RenderUtils.render_preset_store`` serves to
        # any script, and the shipped Arnold tiers appear as read-only entries.
        store = mtk.RenderUtils.render_preset_store()
        presets = menu.presets
        presets.preset_dir = str(store.user_dir)
        presets.builtin_dir = str(store.builtin_dir)
        presets.value_provider = mtk.RenderUtils.render_settings
        presets.value_applier = lambda values: self._apply_render_preset(menu, values)
        menu.add_presets = True

        menu.cmb003.currentIndexChanged.connect(
            lambda _=None: self._sync_render_options(menu)
        )
        # ``activated`` is the USER's pick only (never a restore or a
        # programmatic set): the one place a renderer choice may create nodes.
        menu.cmb003.activated.connect(lambda _=None: self._on_renderer_picked(menu))

    def _refresh_cameras(self, menu):
        """Repopulate the camera combo from the scene, keeping the pick."""
        cameras = [c for c in self._camera_transforms() if "Target" not in c]
        previous = menu.cmb002.currentText()
        # Keep the pick; else the perspective camera (a namespaced `ns:persp`
        # too); else the first.
        default = next(
            (c for c in cameras if c == "persp" or c.endswith(":persp")), None
        )
        pick = previous if previous in cameras else default
        menu.cmb002.blockSignals(True)
        try:
            menu.cmb002.clear()
            menu.cmb002.addItems(cameras)
            menu.cmb002.setCurrentIndex(cameras.index(pick) if pick else 0)
        finally:
            menu.cmb002.blockSignals(False)

    def _sync_render_options(self, menu):
        """Gate the renderer-specific options and re-read the scene's settings.

        Each option is disabled (and an IPR request cleared) when it doesn't
        apply, so the user can't ask for something that would only fail after
        the click. This runs on every panel show and on a restored renderer
        pick, so it only READS the scene: it never loads mtoa or creates
        ``defaultArnoldRenderOptions`` (that would modify any scene the panel
        is shown over, and the scene would then save with ``requires mtoa``).
        Arnold's fields enable when Arnold is picked and show values once its
        options exist; they are created by the user's pick
        (:meth:`_on_renderer_picked`) or the first field edit or preset
        (``mtk.RenderUtils.set_render_settings``).
        """
        renderer = menu.cmb003.currentData()
        ipr = bool(renderer) and mtk.RenderUtils.supports_ipr(renderer)
        menu.chk001.setEnabled(ipr)
        if not ipr:
            menu.chk001.setChecked(False)
        self._enable_arnold_fields(menu, renderer == "arnold")
        self._show_render_settings(menu)

    def _enable_arnold_fields(self, menu, enabled: bool) -> None:
        """Enable or disable every Arnold Sampling field."""
        for name, *_ in self._ARNOLD_FIELDS:
            getattr(menu, name).setEnabled(enabled)

    def _on_renderer_picked(self, menu):
        """The user picked a renderer: Arnold gets its render options now.

        What Maya's Render Settings does when Arnold is picked, so the fields
        show and edit the scene's real values. Only this user-driven pick (and
        a write) creates them; see :meth:`_sync_render_options`.
        """
        if menu.cmb003.currentData() != "arnold":
            return
        try:
            mtk.RenderUtils.ensure_arnold_options()
        except (ValueError, RuntimeError) as error:
            # ValueError: Plugins.LoadError (mtoa is not installed);
            # RuntimeError: mtoa failed to load or to create its options.
            self._enable_arnold_fields(menu, False)
            self.sb.message_box(f"Arnold is unavailable: {error}")
            return
        self._show_render_settings(menu)

    def _show_render_settings(self, menu):
        """Set every setting field to the scene's value, without writing back."""
        settings = mtk.RenderUtils.render_settings()
        for name, key, *_ in self._RESOLUTION_FIELDS + self._ARNOLD_FIELDS:
            if key not in settings:
                continue
            field = getattr(menu, name)
            field.blockSignals(True)
            try:
                field.setValue(int(settings[key]))
            finally:
                field.blockSignals(False)
        menu.presets.refresh_modified_state()

    def _write_render_setting(self, menu, key, value):
        """A field edit: write it to the scene and update the preset marker.

        An Arnold field's first write creates Arnold's options; if mtoa can't
        load, the field is disabled and the reason shown, never raised out of
        the signal.
        """
        try:
            mtk.RenderUtils.set_render_settings({key: value})
        except (ValueError, RuntimeError) as error:
            if key not in {k for _, k, *_ in self._ARNOLD_FIELDS}:
                raise
            self._enable_arnold_fields(menu, False)
            self.sb.message_box(f"Arnold is unavailable: {error}")
            return
        menu.presets.refresh_modified_state()

    def _apply_render_preset(self, menu, values) -> int:
        """The preset selector's applier: write the preset, then show it."""
        applied = mtk.RenderUtils.set_render_settings(values)
        self._show_render_settings(menu)
        return applied

    def tb001(self, widget):
        """Render: render the current frame through the selected camera and renderer.

        An Arnold render first readies the scene to render what the viewport
        shows (``mtk.RenderUtils.prepare_arnold_preview``): the game shaders
        get their Arnold bridge and viewport backface culling reaches Arnold's
        camera rays.
        """
        menu = widget.option_box.menu

        camera = menu.cmb002.currentText()
        if not camera:
            self.sb.message_box("No render camera available.")
            return
        # Render-View procs expect a transform; resolve if the combo yields a shape.
        if cmds.objExists(camera) and cmds.objectType(camera) == "camera":
            camera = mtk.NodeUtils.get_parent(camera) or camera

        renderer = menu.cmb003.currentData() or mtk.RenderUtils.current_renderer()
        mtk.RenderUtils.set_renderer(renderer)

        # Arnold reads neither the game shaders (error magenta) nor viewport
        # backface culling (a cutaway room renders as a black box), so ready
        # the scene first. The setup stays: IPR and every other Arnold render
        # read the same scene, and none of it touches what exports.
        if renderer == "arnold":
            mtk.RenderUtils.prepare_arnold_preview()

        # IPR supersedes a single frame. The checkbox is disabled for renderers
        # that can't start one (see _sync), so this only fires when supported;
        # the False fall-through silently covers the rare launch race.
        if menu.chk001.isChecked() and mtk.RenderUtils.start_ipr(camera, renderer):
            self._last_render_key = None  # an IPR session invalidates redo
            return

        # Smart redo: reuse the previous render when nothing relevant changed.
        key = (camera, renderer)
        if menu.chk002.isChecked() and self._last_render_key == key:
            mtk.RenderUtils.redo_previous_render()
        else:
            mtk.RenderUtils.render_camera(camera)
            self._last_render_key = key

    # ------------------------------------------------------------------ b000  WebXR Preview
    # A LAUNCH, not a slot with an option box. The preview's settings, its push
    # and its live status (which version is up, whether anything is watching)
    # are one panel now -- ``extapps``'s ``webxr_preview`` -- because the option
    # box was duplicated per fork and drifted, and because a transient menu had
    # nowhere to put state that outlives a click. This fork supplies only what
    # is Maya's: the bridge class.
    #
    # ``show=False`` then ``marking_menu.show`` is the house pattern for a
    # host-fed external app (see the Map Packer / Map Converter slots): the
    # handler returns the widget after import and reparenting so context can be
    # injected, and the marking menu reveals it at the cursor -- so this costs
    # what opening any other menu page costs. The handler caches the widget, so
    # the second press raises the panel the user already configured.
    #
    # RENAMED tb002 -> b000 with that change. The ``tb`` prefix means a tool
    # BUTTON -- a control that carries an option box -- and this one no longer
    # does, so it takes the plain ``b`` prefix. The name is the only signal of
    # which kind a slot is, since both are ``PushButton`` in the .ui and the
    # option box is attached at run time by the ``_init`` hook.
    def b000(self, widget):
        """WebXR Preview — open the live preview panel, wired to this scene."""
        ui = self.sb.handlers.external_app.launch("webxr_preview", show=False)
        # The CLASS, not an instance: the panel builds it lazily and keeps it,
        # and its deliverer is a class attribute, so the port and any page
        # already open survive both the panel and this slot being rebuilt.
        ui.slots.engine = mtk.WebXrPreview
        self.sb.handlers.marking_menu.show(ui)

    def b001(self):
        """Open Render Settings Window"""
        mel.eval("unifiedRenderGlobalsWindow")

    def b003(self):
        """Editor: Render Setup"""
        mel.eval("RenderSetupWindow")

    def b004(self):
        """Editor: Rendering Flags"""
        mel.eval("renderFlagsWindow")

    def _scene_workspace(self):
        """The open scene's project (RenderingMixin hook): the scene's own, not
        merely the active one."""
        return mtk.EnvUtils.scene_workspace()

    @staticmethod
    def _scene_base_name() -> str:
        # Single source of truth — includes the batch phantom-"untitled" guard.
        return mtk.PlayblastExporter.scene_name()

    @staticmethod
    def _camera_transforms() -> List[str]:
        camera_names: List[str] = []
        for camera_shape in cmds.ls(type="camera") or []:
            parent = mtk.NodeUtils.get_parent(camera_shape)
            if parent:
                camera_names.append(parent)
        return sorted(set(camera_names))


# --------------------------------------------------------------------------------------------

# module name
# print(__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
