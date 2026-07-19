# !/usr/bin/python
# coding=utf-8
import os
from typing import List

import maya.cmds as cmds
import maya.mel as mel

from uitk.switchboard import Cancelable
from tentacle.slots.maya._slots_maya import SlotsMaya
import mayatk as mtk
from mayatk.anim_utils.playblast_exporter import PlayblastExporter


class Rendering(SlotsMaya):
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
        """Export Playblast Init"""

        menu = widget.option_box.menu
        menu.setTitle("Playblast Export")

        playback_min = int(cmds.playbackOptions(q=True, minTime=True))
        playback_max = int(cmds.playbackOptions(q=True, maxTime=True))

        menu.add(
            "QLineEdit",
            setPlaceholderText="Output directory or base path",
            setText=self._default_playblast_path(),
            setObjectName="t000",
            setToolTip="Output directory, or directory plus base name. A bare directory "
            "uses the scene name; any typed extension is ignored (each output appends its own).",
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
            (label, [name]) for name, label in PlayblastExporter.available_targets()
        ]
        entries += self._TARGET_BUNDLES
        output_combo.addItems([label for label, _ in entries])
        for idx, (_, target_names) in enumerate(entries):
            output_combo.setItemData(idx, target_names)

    @Cancelable(600)
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

        output_dir, output_name = self._split_output_base(menu.t000.text())

        resolution = menu.cmb040.itemData(menu.cmb040.currentIndex()) or (1920, 1080)
        camera_selection = menu.cmb041.itemData(menu.cmb041.currentIndex())

        exporter = PlayblastExporter(
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
            label = PlayblastExporter.TARGETS[result.target].label
            if not result.ok:
                errors.append(f"{label}: {result.error}")
            elif isinstance(result.output, list):
                outputs.append(f"{label}: {len(result.output)} frame(s)")
            elif result.output:
                outputs.append(f"{label}: {result.output}")
                if result.kind in ("encode", "native"):
                    movie_outputs.append(result.output)

        if menu.chk058.isChecked() and movie_outputs:
            try:
                os.startfile(os.path.normpath(movie_outputs[0]))
            except (OSError, AttributeError):  # AttributeError: non-Windows
                pass

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

    def tb001_init(self, widget):
        """Render: camera, renderer, Arnold network, IPR, and smart redo."""
        menu = widget.option_box.menu
        menu.setTitle("Render")

        # Camera transforms (not shapes): Render-View procs expect a transform.
        cameras = [c for c in self._camera_transforms() if "Target" not in c]
        menu.add(
            "QComboBox",
            addItems=cameras,
            setObjectName="cmb002",
            block_signals_on_restore=False,
            setToolTip="Camera to render into the Render View / IPR.",
        )
        # Default to the perspective camera (handles a namespaced `ns:persp`).
        default_cam = next(
            (c for c in cameras if c == "persp" or c.endswith(":persp")), None
        )
        menu.cmb002.setCurrentIndex(cameras.index(default_cam) if default_cam else 0)

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
            setText="Add Arnold Network",
            setObjectName="chk000",
            setChecked=False,
            setToolTip="Before rendering, attach the Arnold aiStandardSurface "
            "preview network to the scene's materials (Arnold only).",
        )
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

        # Gate the renderer-specific options on the picked renderer: each is
        # disabled (and cleared) when it doesn't apply, so the user can't ask
        # for something that would only fail after the click.
        def _gate(checkbox, allowed):
            checkbox.setEnabled(allowed)
            if not allowed:
                checkbox.setChecked(False)

        def _sync(_=None):
            renderer = menu.cmb003.currentData()
            _gate(menu.chk000, renderer == "arnold")  # Arnold-only preview network
            _gate(menu.chk001, bool(renderer) and mtk.RenderUtils.supports_ipr(renderer))

        menu.cmb003.currentIndexChanged.connect(_sync)
        _sync()

    def tb001(self, widget):
        """Render: render the current frame through the selected camera and renderer."""
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

        # Optionally attach the Arnold preview network to the scene first.
        # ArnoldBridge.add() already excludes its own aiStandardSurface shaders,
        # so the raw scene-material list is safe to pass.
        if renderer == "arnold" and menu.chk000.isChecked():
            materials = mtk.MatUtils.get_scene_mats()
            if materials:
                mtk.ArnoldBridge().add(materials=materials)

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

    def b001(self):
        """Open Render Settings Window"""
        mel.eval("unifiedRenderGlobalsWindow")

    def b003(self):
        """Editor: Render Setup"""
        mel.eval("RenderSetupWindow")

    def b004(self):
        """Editor: Rendering Flags"""
        mel.eval("renderFlagsWindow")

    def _default_playblast_path(self) -> str:
        desktop = os.path.expanduser(os.path.join("~", "Desktop"))
        return os.path.normpath(os.path.join(desktop, self._scene_base_name()))

    @staticmethod
    def _scene_base_name() -> str:
        # Single source of truth — includes the batch phantom-"untitled" guard.
        return PlayblastExporter.scene_name()

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
