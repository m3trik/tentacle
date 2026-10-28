# !/usr/bin/python
# coding=utf-8
"""Rendering: one Slots class for both hosts.

The playblast is the host toolkit's ``PlayblastExporter`` (``self.tk``): its
target registry builds the output picker and one ``export`` call produces every
output picked (Maya: a viewport playblast, ffmpeg-encoded movies, Arnold;
Blender: an OpenGL viewport render, movies from Blender's own FFmpeg). The
Render button is the host's ``RenderUtils``: its renderers, the scene's render
settings and named presets over them, one rendered frame. IPR, Smart Redo,
Offscreen Capture and Arnold's sampling are Maya's (``requires``). The WebXR
Preview is the shared ``webxr_preview`` panel, handed the host's bridge class;
the settings buttons open the host's render editors (``UiUtils.open_editor``).
"""

import os
import posixpath
from typing import List

import pythontk as ptk

from tentacle import Slots


class RenderingSlots(Slots):
    #: Curated multi-output bundles appended after the registry's individual
    #: targets (one capture serves several outputs). A bundle naming a target
    #: the host's exporter lacks (Arnold, in Blender) is left out.
    _TARGET_BUNDLES = [
        ("MP4 + PNG Sequence", ["mp4", "png_sequence"]),
        ("MP4 + Arnold Sequence", ["mp4", "arnold"]),
    ]

    #: Resolution presets: ``(label, (width, height))``, in the saved order.
    _RESOLUTIONS = (
        ("3840 x 2160", (3840, 2160)),
        ("2560 x 1440", (2560, 1440)),
        ("1920 x 1080", (1920, 1080)),
        ("1280 x 720", (1280, 720)),
        ("960 x 540", (960, 540)),
        ("640 x 360", (640, 360)),
    )

    #: Quality presets: ``(label, 0-100)``, in the saved order.
    _QUALITIES = (
        ("Draft (20)", 20),
        ("Preview (50)", 50),
        ("Low (70)", 70),
        ("Medium (80)", 80),
        ("High (90)", 90),
        ("Maximum (100)", 100),
    )

    #: Playblast frame-range modes, in the saved order: ``(label, mode)``, the
    #: mode ``PlayblastExporter.export`` takes.
    _RANGE_MODES = (
        ("Playback Range", "playback"),
        ("Animation Range", "animation"),
        ("Current Frame", "current"),
        ("Custom Range", "custom"),
    )

    #: Scene-backed render-setting fields in the Render option box, grouped
    #: under a separator each: ``(objectName, RenderUtils key, label, min,
    #: max)``. The maxima sit well above any sane value: a scene value past a
    #: spinbox's maximum would display clamped -- a lie about the scene.
    #: The keys are ``RenderUtils.RENDER_SETTINGS``'s, so a field, a preset
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

    def __init__(self, switchboard):
        super().__init__(switchboard)
        self.ui = self.sb.loaded_ui.rendering
        # (camera, renderer) of the last render this session: drives Smart Redo.
        self._last_render_key = None

    # ------------------------------------------------------------------ helpers
    def _host_only(self, widget, host):
        """Tag a code-built *widget* only *host* serves (uitk hides it on the
        other host, CODE_STANDARD section 15). Returns True when this host
        serves it."""
        widget.setProperty("requires", host)
        return not self.sb.apply_visibility_policy(widget)

    def _open(self, editor):
        """Open the host's *editor* (a mayatk editor name); say so when it could
        not open."""
        if self.tk.UiUtils.open_editor(editor) is None:
            self.sb.message_box(f"Could not open <hl>{editor}</hl>.")

    # ------------------------------------------------------- playblast defaults
    def _scene_base_name(self) -> str:
        """The name a playblast of the open scene is written under ("playblast"
        while unsaved): the exporter's own rule."""
        return self.tk.PlayblastExporter.scene_name()

    def _default_playblast_path(self) -> str:
        """The playblast's default output base: ``<movie folder>/<scene name>``.

        The scene project's movie folder (``ptk.Workspace.movie_dir``: the
        ``movie`` rule, else ``movies/``) -- the same folder in both hosts, and
        the scene's own project rather than merely the active one. The Desktop
        only when no project resolves (an unsaved file with no session
        project). Asking creates nothing: the writer makes the folder.
        """
        ws = self.tk.DataNodes.scene_workspace()
        if ws is not None:
            folder = ws.movie_dir()
        else:
            folder = os.path.expanduser(os.path.join("~", "Desktop"))
        return os.path.normpath(os.path.join(folder, self._scene_base_name()))

    def _show_playblast_default(self, field) -> None:
        """Show the default output base as *field*'s placeholder (``t000``).

        The field itself stays empty unless the user types a path: a value
        written into it would persist and pin the panel to the scene it was
        built in. :meth:`tb000_init` re-runs this on every panel show, and a
        blank field resolves to the same default when it playblasts.
        """
        field.setPlaceholderText(self._default_playblast_path())

    def _split_output_base(self, text: str) -> tuple:
        """Split the output field into (directory, base name).

        A bare/existing directory (or trailing separator) uses the scene name;
        a typed extension is dropped (each output appends its own); an empty
        field falls back to the default playblast path. A leading ``//`` (a
        path relative to the open .blend) is left for the exporter to resolve.
        """
        raw = (text or "").strip()
        base = os.path.expanduser(os.path.expandvars(raw or self._default_playblast_path()))
        if base.startswith("//"):
            # Split as the forward-slash path it is: Windows reads '//x/y' as a
            # network share (and would probe it for an isdir).
            directory, name = posixpath.split(base.replace("\\", "/"))
            return directory, os.path.splitext(name)[0] or self._scene_base_name()
        base = os.path.normpath(base)
        if os.path.isdir(base) or raw.endswith(("/", "\\")):
            return base, self._scene_base_name()
        directory, name = os.path.split(base)
        name = os.path.splitext(name)[0] or self._scene_base_name()
        if not directory:
            directory = os.path.dirname(self._default_playblast_path())
        return directory, name

    def _ffmpeg_ready(self) -> bool:
        """Guarantee ffmpeg for an encoded playblast output, offering the
        managed install when it is missing.

        An encoded movie is made by ffmpeg from a viewport capture that takes
        minutes, and the exporter's own pre-flight can only *refuse*: a panel
        must *offer*. One primitive (``ptk.VidUtils.ensure_ffmpeg``) answers the
        environment the same way for every host; only the modal is the panel's.

        Returns:
            True when an encode can proceed; False after the user declined or
            the install failed (the reason has been shown).
        """
        try:
            installed = ptk.VidUtils.ensure_ffmpeg(
                prompt=lambda question: (
                    self.sb.message_box(question, "Yes", "No") == "Yes"
                )
            )
        except FileNotFoundError as e:
            self.sb.message_box(str(e))
            return False
        if installed:
            self.sb.message_box(f"Installed FFmpeg: <hl>{installed}</hl>")
        return True

    # ------------------------------------------------------------------ tb000  Playblast
    def tb000_init(self, widget):
        """Export Playblast: built once, then re-run on every panel show.

        ``refresh_on_show`` re-runs this init, so the output field's
        placeholder (the default path) follows the open scene instead of the
        one the panel was built in.
        """
        menu = widget.option_box.menu
        if not getattr(widget, "_playblast_menu_built", False):
            widget.refresh_on_show = True
            self._build_playblast_menu(menu)
            widget._playblast_menu_built = True
        self._refresh_playblast_cameras(menu)
        self._show_playblast_default(menu.t000)

    def _build_playblast_menu(self, menu):
        """Add the Playblast option box's controls."""
        menu.setTitle("Playblast Export")
        exporter = self.tk.PlayblastExporter
        playback_min, playback_max = exporter.resolve_frame_range("playback")

        # Left empty: the placeholder shows the scene's default, and a blank
        # field resolves to it at playblast time (_split_output_base).
        menu.add(
            "QLineEdit",
            setObjectName="t000",
            setToolTip="Output directory, or directory plus base name. A bare directory "
            "uses the scene name; any typed extension is ignored (each output appends its "
            "own). Blank: the default shown, the scene workspace's movie folder. "
            "(Blender: '//' is relative to the .blend.)",
        )
        range_combo = menu.add(
            "QComboBox",
            addItems=[label for label, _ in self._RANGE_MODES],
            setObjectName="cmb010",
            setCurrentIndex=0,
            block_signals_on_restore=False,
            setToolTip="Frame range preset controlling the start and end frames.",
        )
        for index, (_, mode) in enumerate(self._RANGE_MODES):
            range_combo.setItemData(index, {"mode": mode})
        custom_start = menu.add(
            "QSpinBox",
            setPrefix="Custom Start Frame: ",
            setObjectName="s010",
            setMinimum=-1000000,
            setMaximum=1000000,
            setValue=playback_min,
            setToolTip="First frame included in the playblast range when using Custom Range.",
        )
        custom_end = menu.add(
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
        resolution_combo = menu.add(
            "QComboBox",
            addItems=[label for label, _ in self._RESOLUTIONS],
            setObjectName="cmb040",
            setCurrentIndex=2,
            block_signals_on_restore=False,
            setToolTip="Resolution preset applied to all playblast captures.",
        )
        for index, (_, size) in enumerate(self._RESOLUTIONS):
            resolution_combo.setItemData(index, size)
        menu.add(
            "QSpinBox",
            setPrefix="Scale %: ",
            setObjectName="s015",
            setMinimum=1,
            setMaximum=100,
            setValue=100,
            setToolTip="Scaling percentage applied to the capture resolution.",
        )
        quality_combo = menu.add(
            "QComboBox",
            addItems=[label for label, _ in self._QUALITIES],
            setObjectName="cmb016",
            setCurrentIndex=5,
            block_signals_on_restore=False,
            setToolTip="Quality applied to movie outputs (Maya: native playblast "
            "quality; the encoding rate factor for MP4/MOV) and JPEG frames.",
        )
        for index, (_, value) in enumerate(self._QUALITIES):
            quality_combo.setItemData(index, value)

        # Populated from the scene on every show (_refresh_playblast_cameras).
        camera_combo = menu.add(
            "QComboBox",
            setObjectName="cmb041",
            block_signals_on_restore=False,
            setToolTip="Camera override used during the capture. 'Active Viewport' "
            "captures the viewport's own view.",
        )
        camera_combo.restore_by = "text"  # scene-dependent items; index is unstable

        # Registry-driven: the exporter's own targets, then the bundles it serves.
        output_combo = menu.add(
            "QComboBox",
            setObjectName="cmb050",
            setCurrentIndex=0,
            setMaxVisibleItems=12,
            block_signals_on_restore=False,
            setToolTip=(
                "Output(s) to generate. Sequences keep real scene frame numbers; "
                "bundles produce several outputs from one capture pass."
            ),
        )
        output_combo.restore_by = "text"  # registry-driven items; index is unstable
        entries = [(label, [name]) for name, label in exporter.available_targets()]
        entries += [
            (label, names)
            for label, names in self._TARGET_BUNDLES
            if all(name in exporter.TARGETS for name in names)
        ]
        output_combo.addItems([label for label, _ in entries])
        for index, (_, names) in enumerate(entries):
            output_combo.setItemData(index, names)

        offscreen = menu.add(
            "QCheckBox",
            setText="Offscreen Capture",
            setObjectName="chk056",
            setChecked=True,
            setToolTip="Capture offscreen, avoiding viewport redraw issues.",
        )
        # Maya's playblast flag; Blender's OpenGL render always draws offscreen.
        self._host_only(offscreen, "maya")
        menu.add(
            "QCheckBox",
            setText="Show Ornaments",
            setObjectName="chk057",
            setChecked=True,
            setToolTip="Include the HUD and viewport ornaments (Blender: the "
            "overlays) in the capture.",
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
            setToolTip="Attach the scene's sound to movie outputs (Maya: the "
            "timeline's active sound; Blender: the scene's sound strips and "
            "speakers).",
        )

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

    def _refresh_playblast_cameras(self, menu):
        """Repopulate the capture-camera combo from the scene, keeping the pick:
        "Active Viewport" (the view itself), then the host's cameras. A camera
        deleted since the last show would only fail its capture."""
        cameras = self.tk.RenderUtils.render_cameras()
        combo = menu.cmb041
        previous = combo.currentData()
        combo.blockSignals(True)
        try:
            combo.clear()
            combo.addItems(["Active Viewport"] + cameras)
            combo.setItemData(0, None)
            for index, camera in enumerate(cameras, start=1):
                combo.setItemData(index, camera)
            combo.setCurrentIndex(cameras.index(previous) + 1 if previous in cameras else 0)
        finally:
            combo.blockSignals(False)

    @Slots.Cancelable(600)
    def tb000(self, widget):
        """Export Playblast"""
        # A playblast over a static scene is just N identical frames: bail before
        # any capture work if nothing is keyed over time.
        if not self.tk.AnimUtils.scene_has_animation():
            self.sb.message_box("No animation in the scene: nothing to playblast.")
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
        # An encoded movie needs ffmpeg for a second at the END of a minutes-long
        # capture: offer the install now, never an error after the wait. .get: a
        # stale persisted picker entry is the exporter's ValueError to raise.
        exporter_class = self.tk.PlayblastExporter
        registry = exporter_class.TARGETS
        needs_encoder = any(
            getattr(registry.get(t), "kind", None) == "encode" for t in targets
        )
        if needs_encoder and not self._ffmpeg_ready():
            return

        output_dir, output_name = self._split_output_base(menu.t000.text())
        resolution = menu.cmb040.itemData(menu.cmb040.currentIndex()) or (1920, 1080)
        camera_selection = menu.cmb041.itemData(menu.cmb041.currentIndex())

        exporter = exporter_class(
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
        try:
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
        except ValueError as error:  # an unknown target, an unresolvable range
            self.sb.message_box(str(error))
            return

        outputs: List[str] = []
        errors: List[str] = []
        movie_outputs: List[str] = []
        for result in results:
            spec = registry.get(result.target)
            label = spec.label if spec else result.target
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

    # ------------------------------------------------------------------ tb001  Render
    def tb001_init(self, widget):
        """Render: camera, renderer, IPR, smart redo, key settings and presets.

        Built once, then re-run on every panel show (``refresh_on_show``): the
        camera list and the setting fields re-read the scene, so a new or
        re-opened scene never shows the last one's values. The setting fields
        are the scene's own render settings -- written as they change, never
        session-restored -- and the menu's native preset selector applies the
        host's render presets (``RenderUtils.render_preset_store``) to the
        same settings.
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
        render_utils = self.tk.RenderUtils

        # Populated from the scene on every show (_refresh_cameras).
        menu.add(
            "QComboBox",
            setObjectName="cmb002",
            block_signals_on_restore=False,
            setToolTip="Camera to render (Blender: made the scene camera).",
        )

        # Renderer: the host's renderers; default to the active one.
        renderers = render_utils.get_available_renderers()
        menu.add(
            "QComboBox",
            addItems=[r["label"] for r in renderers],
            setObjectName="cmb003",
            block_signals_on_restore=False,
            setToolTip="Renderer to use. Maya: an installed-but-unloaded renderer "
            "(e.g. Arnold) loads on demand when selected.",
        )
        for i, r in enumerate(renderers):
            menu.cmb003.setItemData(i, r["name"])
        names = [r["name"] for r in renderers]
        current = render_utils.current_renderer()
        if current in names:
            menu.cmb003.setCurrentIndex(names.index(current))

        ipr = menu.add(
            "QCheckBox",
            setText="IPR (realtime)",
            setObjectName="chk001",
            setChecked=False,
            setToolTip="Launch interactive realtime rendering instead of a single "
            "frame. Disabled automatically for renderers that don't provide IPR.",
        )
        smart_redo = menu.add(
            "QCheckBox",
            setText="Smart Redo",
            setObjectName="chk002",
            setChecked=True,
            setToolTip="Re-render the previous result when the camera and renderer "
            "are unchanged (faster); otherwise render fresh.",
        )
        # Maya's Render View: Blender's interactive render is the viewport's
        # Rendered shading, and its Render Result slots make a redo moot.
        self._host_only(ipr, "maya")
        self._host_only(smart_redo, "maya")

        for title, fields, host in (
            ("Resolution", self._RESOLUTION_FIELDS, None),
            ("Arnold Sampling", self._ARNOLD_FIELDS, "maya"),
        ):
            separator = menu.add("Separator", setTitle=title)
            if host and separator is not None:
                self._host_only(separator, host)
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
                if host:
                    self._host_only(field, host)
                field.valueChanged.connect(
                    lambda value, k=key: self._write_render_setting(menu, k, value)
                )

        # The menu's native preset selector, in semantic mode: a preset is a
        # ``{setting: value}`` dict read from and applied to the SCENE, so the
        # files are the ones ``RenderUtils.render_preset_store`` serves to any
        # script (Maya ships Arnold tiers as read-only entries).
        store = render_utils.render_preset_store()
        presets = menu.presets
        presets.preset_dir = str(store.user_dir)
        presets.builtin_dir = str(store.builtin_dir) if store.builtin_dir else None
        presets.value_provider = render_utils.render_settings
        presets.value_applier = lambda values: self._apply_render_preset(menu, values)
        menu.add_presets = True

        menu.cmb003.currentIndexChanged.connect(
            lambda _=None: self._sync_render_options(menu)
        )
        # ``activated`` is the USER's pick only (never a restore or a
        # programmatic set): the one place a renderer choice may create nodes.
        menu.cmb003.activated.connect(lambda _=None: self._on_renderer_picked(menu))

    def _refresh_cameras(self, menu):
        """Repopulate the camera combo from the scene, keeping the pick; else the
        host's default render camera (``RenderUtils.render_cameras`` lists it
        first: Maya's persp, Blender's scene camera)."""
        cameras = self.tk.RenderUtils.render_cameras()
        previous = menu.cmb002.currentText()
        menu.cmb002.blockSignals(True)
        try:
            menu.cmb002.clear()
            menu.cmb002.addItems(cameras)
            menu.cmb002.setCurrentIndex(
                cameras.index(previous) if previous in cameras else 0
            )
        finally:
            menu.cmb002.blockSignals(False)

    def _sync_render_options(self, menu):
        """Gate the renderer-specific options and re-read the scene's settings.

        Each option is disabled (and an IPR request cleared) when it doesn't
        apply, so the user can't ask for something that would only fail after
        the click. This runs on every panel show and on a restored renderer
        pick, so it only READS the scene: it never loads mtoa or creates
        Arnold's options (that would modify any scene the panel is shown over,
        and the scene would then save with ``requires mtoa``). Arnold's fields
        enable when Arnold is picked and show values once its options exist;
        they are created by the user's pick (:meth:`_on_renderer_picked`) or
        the first field edit or preset (``RenderUtils.set_render_settings``).
        """
        renderer = menu.cmb003.currentData()
        ipr = bool(renderer) and self.tk.RenderUtils.supports_ipr(renderer)
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
            self.tk.RenderUtils.ensure_arnold_options()
        except (ValueError, RuntimeError) as error:
            # ValueError: mtoa is not installed; RuntimeError: mtoa failed to
            # load or to create its options.
            self._enable_arnold_fields(menu, False)
            self.sb.message_box(f"Arnold is unavailable: {error}")
            return
        self._show_render_settings(menu)

    def _show_render_settings(self, menu):
        """Set every setting field to the scene's value, without writing back."""
        settings = self.tk.RenderUtils.render_settings()
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
            self.tk.RenderUtils.set_render_settings({key: value})
        except (ValueError, RuntimeError) as error:
            if key not in {k for _, k, *_ in self._ARNOLD_FIELDS}:
                raise
            self._enable_arnold_fields(menu, False)
            self.sb.message_box(f"Arnold is unavailable: {error}")
            return
        menu.presets.refresh_modified_state()

    def _apply_render_preset(self, menu, values) -> int:
        """The preset selector's applier: write the preset, then show it."""
        applied = self.tk.RenderUtils.set_render_settings(values)
        self._show_render_settings(menu)
        return applied

    def tb001(self, widget):
        """Render: render the current frame through the selected camera and renderer.

        An Arnold render first readies the scene to render what the viewport
        shows (``RenderUtils.prepare_arnold_preview``): the game shaders get
        their Arnold bridge and viewport backface culling reaches Arnold's
        camera rays.
        """
        menu = widget.option_box.menu
        camera = menu.cmb002.currentText()
        if not camera:
            self.sb.message_box("No render camera available.")
            return
        render_utils = self.tk.RenderUtils
        renderer = menu.cmb003.currentData() or render_utils.current_renderer()
        try:
            render_utils.set_renderer(renderer)
            # Arnold reads neither the game shaders (error magenta) nor viewport
            # backface culling (a cutaway room renders as a black box), so ready
            # the scene first. The setup stays: IPR and every other Arnold render
            # read the same scene, and none of it touches what exports.
            if renderer == "arnold":
                render_utils.prepare_arnold_preview()

            # IPR supersedes a single frame. The checkbox is disabled for
            # renderers that can't start one (_sync_render_options), so this only
            # fires when supported; False falls through to a single render.
            if menu.chk001.isChecked() and render_utils.start_ipr(camera, renderer):
                self._last_render_key = None  # an IPR session invalidates redo
                return

            # Smart redo: reuse the previous render when nothing relevant changed.
            key = (camera, renderer)
            if menu.chk002.isChecked() and self._last_render_key == key:
                render_utils.redo_previous_render()
            else:
                render_utils.render_camera(camera)
                self._last_render_key = key
        except (RuntimeError, ValueError) as error:
            self.sb.message_box(f"Could not render.<br><hl>{error}</hl>")

    # ------------------------------------------------------------------ b000  WebXR Preview
    # A LAUNCH, not a slot with an option box: the preview's settings, its push
    # and its live status are one panel (``extapps``'s ``webxr_preview``). This
    # supplies only what is the host's: its bridge class. ``show=False`` then
    # ``marking_menu.show`` is the house pattern for a host-fed external app: the
    # handler returns the widget after import and reparenting so context can be
    # injected, and the marking menu reveals it at the cursor. The handler caches
    # the widget, so the second press raises the panel the user configured.
    # (Renamed tb002 -> b000: ``tb`` means a button carrying an option box.)
    def b000(self, widget):
        """WebXR Preview: open the live preview panel, wired to this scene."""
        ui = self.sb.handlers.external_app.launch("webxr_preview", show=False)
        # The CLASS, not an instance: the panel builds it lazily and keeps it,
        # and its deliverer is a class attribute, so the port and any page
        # already open survive both the panel and this slot being rebuilt.
        ui.slots.engine = self.tk.WebXrPreview
        self.sb.handlers.marking_menu.show(ui)

    # ------------------------------------------------------------------ settings editors
    def b001(self):
        """Global Settings: the render settings (Blender: Properties > Render)."""
        self._open("Render Settings")

    def b003(self):
        """Render Setup: the render-layer manager (Blender: Properties > View Layer)."""
        self._open("Render Setup")

    def b004(self):
        """Rendering Flags: per-object render flags (Blender: Properties > Object,
        its ray Visibility)."""
        self._open("Rendering Flags")


# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
