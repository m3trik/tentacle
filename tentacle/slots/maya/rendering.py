# !/usr/bin/python
# coding=utf-8
import os
import re
from typing import Any, Dict, List, Optional

try:
    import pymel.core as pm
except ImportError as error:
    print(__file__, error)

from tentacle.slots.maya._slots_maya import SlotsMaya
import mayatk as mtk
from mayatk.anim_utils.playblast_exporter import PlayblastExporter


class Rendering(SlotsMaya):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.ui = self.sb.loaded_ui.rendering
        self.submenu = self.sb.loaded_ui.rendering_submenu

    def cmb001_init(self, widget):
        """Render: camera"""
        lst = {c.name(): c for c in pm.ls(type="camera") if "Target" not in c.name()}
        widget.add(lst)

    def tb000_init(self, widget):
        """Export Playblast Init"""

        menu = widget.option_box.menu
        menu.setTitle("Playblast Export")

        playback_min = int(pm.playbackOptions(q=True, minTime=True))
        playback_max = int(pm.playbackOptions(q=True, maxTime=True))
        default_path = self._default_playblast_path()

        menu.add(
            "QLineEdit",
            setPlaceholderText="Output base path",
            setText=default_path,
            setObjectName="t000",
            setToolTip="Base filepath (without extension). Variations will append labels and extensions automatically.",
        )
        menu.add(
            "QLineEdit",
            setPlaceholderText="Scene regex pattern -> replacement (optional)",
            setObjectName="t001",
            setToolTip="Optional regex applied to the scene name before building output filenames. Use 'pattern->replacement'.",
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
            setToolTip="Image quality preset applied to movie outputs.",
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
            addItems=[
                "AVI (Uncompressed)",
                "MP4 (Compressed)",
                "MOV (Animation)",
                "MOV (JPEG)",
                "MOV (No Compression)",
                "PNG Sequence",
                "PNG Still (Single Frame)",
                "JPEG Sequence",
                "TIFF Sequence",
                "TGA Sequence",
                "IFF Sequence",
                "Arnold Sequence",
                "AVI + PNG",
                "AVI + Arnold",
                "All Maya Movie/Sequences",
            ],
            setObjectName="cmb050",
            setCurrentIndex=0,
            setMaxVisibleItems=12,
            block_signals_on_restore=False,
            setToolTip=(
                "Choose the preset(s) to generate: AVI/MOV movie captures, FFmpeg-compressed MP4, "
                "individual image sequences (PNG/JPEG/TIFF/TGA/IFF), single-frame PNG stills, and the Arnold renderer. "
                "Combined presets bundle common outputs so you can trigger multiple formats at once."
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
            setText="Launch Viewer",
            setObjectName="chk058",
            setChecked=False,
            setToolTip="Open the captured clip in Maya's media viewer when finished.",
        )
        menu.add(
            "QCheckBox",
            setText="Clear Cache",
            setObjectName="chk059",
            setChecked=True,
            setToolTip="Clear temporary playblast files before exporting.",
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
        camera_combo.setItemData(0, None)
        for idx, camera_name in enumerate(camera_items[1:], start=1):
            camera_combo.setItemData(idx, camera_name)

        output_combo = menu.cmb050
        output_map = {
            0: ["avi"],
            1: ["mp4"],
            2: ["mov_animation"],
            3: ["mov_jpeg"],
            4: ["mov_uncompressed"],
            5: ["png_sequence"],
            6: ["png_still"],
            7: ["jpg_sequence"],
            8: ["tiff_sequence"],
            9: ["tga_sequence"],
            10: ["iff_sequence"],
            11: ["arnold_sequence"],
            12: ["avi", "png_sequence"],
            13: ["avi", "arnold_sequence"],
            14: [
                "avi",
                "avi_viewport",
                "mp4",
                "mov_animation",
                "mov_jpeg",
                "mov_uncompressed",
                "png_sequence",
                "png_still",
                "jpg_sequence",
                "tiff_sequence",
                "tga_sequence",
                "iff_sequence",
            ],
        }
        for idx, codes in output_map.items():
            output_combo.setItemData(idx, codes)

    def tb000(self, widget):
        """Export Playblast"""

        menu = widget.option_box.menu

        range_data = menu.cmb010.itemData(menu.cmb010.currentIndex()) or {}
        range_mode = range_data.get("mode", "playback")

        if range_mode == "animation":
            start_frame = int(pm.playbackOptions(q=True, animationStartTime=True))
            end_frame = int(pm.playbackOptions(q=True, animationEndTime=True))
        elif range_mode == "current":
            current = int(pm.currentTime(query=True))
            start_frame = current
            end_frame = current
        elif range_mode == "custom":
            start_frame = int(menu.s010.value())
            end_frame = int(menu.s011.value())
            if start_frame > end_frame:
                self.sb.message_box(
                    "Start frame must be less than or equal to end frame."
                )
                return
        else:
            start_frame = int(pm.playbackOptions(q=True, minTime=True))
            end_frame = int(pm.playbackOptions(q=True, maxTime=True))

        frame_padding = int(menu.s012.value())
        percent = int(menu.s015.value())
        quality = int(menu.cmb016.itemData(menu.cmb016.currentIndex()) or 100)

        output_base = menu.t000.text().strip()
        scene_name = self._scene_base_name()
        regex_spec = menu.t001.text().strip()
        if regex_spec:
            pattern = None
            replacement = ""
            if "->" in regex_spec:
                parts = regex_spec.split("->", 1)
                pattern = parts[0].strip()
                replacement = parts[1]
            elif "|" in regex_spec:
                parts = regex_spec.split("|", 1)
                pattern = parts[0].strip()
                replacement = parts[1]
            if pattern:
                try:
                    scene_name = re.sub(pattern, replacement, scene_name)
                except re.error as exc:
                    pm.warning(f"Invalid regex pattern '{pattern}': {exc}")
        if not scene_name:
            scene_name = self._scene_base_name()

        if not output_base:
            output_base = self._default_playblast_path()
        output_base = os.path.normpath(
            os.path.expanduser(os.path.expandvars(output_base))
        )

        if os.path.isdir(output_base):
            output_base = os.path.join(output_base, scene_name)
        elif output_base.endswith(("/", "\\")) or output_base == "":
            output_base = os.path.join(output_base, scene_name)
        elif os.path.splitext(output_base)[1]:
            output_base = os.path.splitext(output_base)[0]

        base_dir = os.path.dirname(output_base)
        if base_dir and not os.path.exists(base_dir):
            os.makedirs(base_dir, exist_ok=True)

        camera_combo = menu.cmb041
        camera_selection = camera_combo.itemData(camera_combo.currentIndex())
        camera_name = str(camera_selection) if camera_selection else None

        resolution = menu.cmb040.itemData(menu.cmb040.currentIndex())
        if not resolution:
            resolution = (1920, 1080)

        base_kwargs = {
            "clearCache": menu.chk059.isChecked(),
            "forceOverwrite": True,
            "viewer": menu.chk058.isChecked(),
            "offScreen": menu.chk056.isChecked(),
            "showOrnaments": menu.chk057.isChecked(),
            "percent": percent,
            "quality": quality,
            "widthHeight": resolution,
        }

        preset_codes = menu.cmb050.itemData(menu.cmb050.currentIndex()) or []
        if not preset_codes:
            self.sb.message_box("Select an output preset before running the playblast.")
            return

        def build_variation(code: str) -> Optional[Dict[str, Any]]:
            if code == "avi":
                return {
                    "label": "avi_uncompressed",
                    "playblast": {"format": "avi", "compression": "none"},
                }
            if code == "mp4":
                return {
                    "label": "mp4",
                    "playblast": {"format": "avi", "compression": "none"},
                    "post": "mp4",
                }
            if code == "mov_animation":
                return {
                    "label": "mov_animation",
                    "playblast": {"format": "qt", "compression": "animation"},
                }
            if code == "mov_jpeg":
                return {
                    "label": "mov_jpeg",
                    "playblast": {"format": "qt", "compression": "jpeg"},
                }
            if code == "mov_uncompressed":
                return {
                    "label": "mov_uncompressed",
                    "playblast": {"format": "qt", "compression": "none"},
                }
            if code == "png_sequence":
                return {
                    "label": "png_sequence",
                    "playblast": {
                        "format": "image",
                        "compression": "png",
                        "framePadding": frame_padding,
                    },
                    "make_directory": True,
                }
            if code == "png_still":
                return {
                    "label": "png_still",
                    "playblast": {
                        "format": "image",
                        "compression": "png",
                        "framePadding": frame_padding,
                    },
                    "make_directory": True,
                }
            if code == "jpg_sequence":
                return {
                    "label": "jpg_sequence",
                    "playblast": {
                        "format": "image",
                        "compression": "jpg",
                        "framePadding": frame_padding,
                    },
                    "make_directory": True,
                }
            if code == "tiff_sequence":
                return {
                    "label": "tiff_sequence",
                    "playblast": {
                        "format": "image",
                        "compression": "tif",
                        "framePadding": frame_padding,
                    },
                    "make_directory": True,
                }
            if code == "iff_sequence":
                return {
                    "label": "iff_sequence",
                    "playblast": {
                        "format": "image",
                        "compression": "iff",
                        "framePadding": frame_padding,
                    },
                    "make_directory": True,
                }
            if code == "tga_sequence":
                return {
                    "label": "tga_sequence",
                    "playblast": {
                        "format": "image",
                        "compression": "tga",
                        "framePadding": frame_padding,
                    },
                    "make_directory": True,
                }
            if code == "arnold_sequence":
                return {
                    "label": "arnold_sequence",
                    "renderer": "arnold",
                    "framePadding": frame_padding,
                }
            if code == "avi_viewport":
                return {
                    "label": "avi_viewport",
                    "playblast": {
                        "format": "avi",
                        "compression": "none",
                        "offScreen": False,
                    },
                }
            return None

        variations: List[Dict[str, Any]] = []
        seen_labels = set()
        for code in preset_codes:
            variation = build_variation(code)
            if not variation:
                continue
            label = variation.get("label")
            if label in seen_labels:
                continue
            seen_labels.add(label)
            variations.append(variation)

        if not variations:
            self.sb.message_box(
                "No output variations resolved from the selected preset."
            )
            return

        pm.optionVar["tentacleEnableArnoldPlayblast"] = int(
            any(variation.get("renderer") == "arnold" for variation in variations)
        )

        pm.currentTime(start_frame, update=True)

        exporter = PlayblastExporter(
            start_frame=start_frame,
            end_frame=end_frame,
            camera_name=camera_name,
        )

        results = exporter.export_variations(
            output_path=output_base,
            base_kwargs=base_kwargs,
            scene_name=scene_name,
            variations=variations,
        )

        outputs = []
        errors = []
        for result in results:
            if result.get("error"):
                errors.append(result)
                continue

            output_value = result.get("output")
            if isinstance(output_value, list):
                outputs.append(f"{result['label']}: {len(output_value)} frame(s)")
            elif output_value:
                outputs.append(f"{result['label']}: {output_value}")

            compressed = result.get("compressed")
            if compressed:
                outputs.append(f"{result['label']} mp4: {compressed}")

        if outputs:
            pm.displayInfo("Playblast export complete:\n" + "\n".join(outputs))

        if errors:
            for entry in errors:
                pm.warning(
                    f"Playblast variant '{entry['label']}' failed: {entry.get('error')}"
                )
            self.sb.message_box(
                "One or more playblast exports failed. Check the Script Editor for details."
            )
        elif outputs:
            self.sb.message_box("Playblast exports completed successfully.")
        else:
            self.sb.message_box("No playblast outputs were generated.")

    def b000(self):
        """Render Current Frame"""
        self.ui.cmb001.init_slot()
        camera = self.ui.cmb001.currentText()
        pm.render(camera)  # render with selected camera

    def b001(self):
        """Open Render Settings Window"""
        pm.mel.unifiedRenderGlobalsWindow()

    def b002(self):
        """Redo Previous Render"""
        pm.mel.redoPreviousRender("render")

    def b003(self):
        """Editor: Render Setup"""
        pm.mel.RenderSetupWindow()

    def b004(self):
        """Editor: Rendering Flags"""
        pm.mel.renderFlagsWindow()

    def b005(self):
        """Apply Vray Attributes To Selected Objects"""
        if not self.load_vray_plugin(query=True):
            print("VRay plugin is not loaded. Loading it now.")
            self.load_vray_plugin()

        selection = pm.ls(selection=True)
        currentID = 1
        for obj in selection:
            # get renderable shape nodes relative to transform, iterate through and apply subdivision
            shapes = pm.listRelatives(obj, s=1, ni=1)
            if shapes:
                for shape in shapes:
                    pm.mel.eval(
                        "vray addAttributesFromGroup " + shape + " vray_subdivision 1;"
                    )
                    pm.mel.eval(
                        "vray addAttributesFromGroup " + shape + " vray_subquality 1;"
                    )
            # apply object ID to xform. i don't like giving individual shapes IDs.
            pm.mel.eval("vray addAttributesFromGroup " + obj + " vray_objectID 1;")
            pm.setAttr(obj + ".vrayObjectID", currentID)
            currentID += 1

    def b006(self):
        """Load Vray Plugin"""
        mtk.vray_plugin()

    def _default_playblast_path(self) -> str:
        desktop = os.path.expanduser(os.path.join("~", "Desktop"))
        return os.path.normpath(os.path.join(desktop, self._scene_base_name()))

    @staticmethod
    def _scene_base_name() -> str:
        scene = pm.sceneName()
        if scene:
            return os.path.basename(scene).rsplit(".", 1)[0]
        return "playblast"

    @staticmethod
    def _camera_transforms() -> List[str]:
        camera_names: List[str] = []
        for camera_shape in pm.ls(type="camera"):
            parent = camera_shape.getParent()
            if parent:
                camera_names.append(parent.name())
        return sorted(set(camera_names))


# --------------------------------------------------------------------------------------------

# module name
# print(__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
