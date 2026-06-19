# !/usr/bin/python
# coding=utf-8
import bpy
import blendertk as btk
from tentacle.slots.blender._slots_blender import SlotsBlender


class Rendering(SlotsBlender):
    """Blender port of the shared ``rendering`` menu.

    Render-frame / show-last-render map onto ``render.render`` / ``render.view_show``;
    playblast maps onto Blender's OpenGL viewport render; render settings live in the
    Properties editor. Maya's Render-Setup / Rendering-Flags editors have no analogue.
    """

    def __init__(self, switchboard):
        super().__init__(switchboard)
        self.ui = self.sb.loaded_ui.rendering

    # ------------------------------------------------------------------ cmb001  Render camera
    def cmb001_init(self, widget):
        """Initialize the render-camera combo (label -> camera object)."""
        widget.refresh_on_show = True
        cameras = {o.name: o for o in bpy.data.objects if o.type == "CAMERA"}
        widget.add(cameras, header="Camera:", clear=True)
        current = bpy.context.scene.camera
        if current and current.name in cameras:
            widget.setCurrentIndex(list(cameras).index(current.name))

    def cmb001(self, index, widget):
        """Set the scene's active (render) camera."""
        cam = widget.currentData()
        if cam is not None:
            bpy.context.scene.camera = cam

    # ------------------------------------------------------------------ tb000  Playblast
    # Reuses the Maya rendering objectNames/labels for the same options (cross-DCC QSettings rule):
    # t000 path · cmb010/s010/s011 range · s012 padding · cmb040 resolution · s015 scale ·
    # cmb016 quality · cmb041 camera · cmb050 format · chk058 viewer. Format/quality drive the
    # tested btk.configure_render_output engine; the rest is capture-time scene override (restored).
    _RESOLUTIONS = [
        ("3840 x 2160", (3840, 2160)), ("2560 x 1440", (2560, 1440)),
        ("1920 x 1080", (1920, 1080)), ("1280 x 720", (1280, 720)),
        ("960 x 540", (960, 540)), ("640 x 360", (640, 360)),
    ]
    _QUALITIES = [
        ("Draft (20)", 20), ("Preview (50)", 50), ("Low (70)", 70),
        ("Medium (80)", 80), ("High (90)", 90), ("Maximum (100)", 100),
    ]
    # label -> (configure_render_output kwargs, is_movie, is_still). Blender-appropriate formats
    # (the Maya Arnold/IFF/"All" presets have no Blender analogue).
    _FORMATS = [
        ("MP4 (H.264)", {"file_format": "FFMPEG", "container": "MPEG4", "codec": "H264"}, True, False),
        ("MOV (H.264)", {"file_format": "FFMPEG", "container": "QUICKTIME", "codec": "H264"}, True, False),
        ("AVI (FFV1)", {"file_format": "FFMPEG", "container": "AVI", "codec": "FFV1"}, True, False),
        ("PNG Sequence", {"file_format": "PNG"}, False, False),
        ("PNG Still", {"file_format": "PNG"}, False, True),
        ("JPEG Sequence", {"file_format": "JPEG"}, False, False),
        ("TIFF Sequence", {"file_format": "TIFF"}, False, False),
        ("TGA Sequence", {"file_format": "TARGA"}, False, False),
        ("OpenEXR Sequence", {"file_format": "OPEN_EXR"}, False, False),
    ]

    @staticmethod
    def _frame_range(mode_index, menu):
        """(start, end) for the cmb010 mode against the scene (Playback = preview range when
        active, else the scene range; Animation = scene range; Current = single frame; Custom =
        the s010/s011 spinboxes)."""
        scene = bpy.context.scene
        if mode_index == 2:  # Current Frame
            return scene.frame_current, scene.frame_current
        if mode_index == 3:  # Custom Range
            return int(menu.s010.value()), int(menu.s011.value())
        if mode_index == 0 and scene.use_preview_range:  # Playback Range (preview range)
            return scene.frame_preview_start, scene.frame_preview_end
        return scene.frame_start, scene.frame_end  # Playback (no preview) / Animation Range

    def tb000_init(self, widget):
        scene = bpy.context.scene
        menu = widget.option_box.menu
        menu.setTitle("Playblast")
        menu.add(
            "QLineEdit", setPlaceholderText="Output base path (without extension)",
            setText=scene.render.filepath, setObjectName="t000",
            setToolTip="Output base filepath. The format's extension (and frame numbers for "
            "sequences) are appended automatically; '//' is a .blend-relative path.",
        )
        menu.add(
            "QComboBox",
            addItems=["Playback Range", "Animation Range", "Current Frame", "Custom Range"],
            setObjectName="cmb010", setToolTip="Frame range to capture.",
        )
        menu.add(
            "QSpinBox", setPrefix="Custom Start Frame: ", setObjectName="s010",
            set_limits=[-1000000, 1000000], setValue=scene.frame_start,
            setToolTip="First frame captured when using Custom Range.",
        )
        menu.add(
            "QSpinBox", setPrefix="Custom End Frame: ", setObjectName="s011",
            set_limits=[-1000000, 1000000], setValue=scene.frame_end,
            setToolTip="Last frame captured when using Custom Range.",
        )
        menu.add(
            "QSpinBox", setPrefix="Frame Padding: ", setObjectName="s012",
            set_limits=[1, 10], setValue=4,
            setToolTip="Digits used for image-sequence frame numbers (encoded as '#' in the path).",
        )
        cmb040 = menu.add(
            "QComboBox", setObjectName="cmb040",
            setToolTip="Resolution preset applied during capture (restored afterward).",
        )
        for label, data in self._RESOLUTIONS:
            cmb040.addItem(label, data)
        cmb040.setCurrentIndex(2)  # 1920 x 1080
        menu.add(
            "QSpinBox", setPrefix="Scale %: ", setObjectName="s015",
            set_limits=[1, 100], setValue=scene.render.resolution_percentage,
            setToolTip="Resolution percentage applied during capture.",
        )
        cmb016 = menu.add(
            "QComboBox", setObjectName="cmb016",
            setToolTip="Quality for movie/JPEG outputs (FFMPEG constant-rate-factor / JPEG quality).",
        )
        for label, data in self._QUALITIES:
            cmb016.addItem(label, data)
        cmb016.setCurrentIndex(5)  # Maximum
        cmb041 = menu.add(
            "QComboBox", setObjectName="cmb041",
            setToolTip="Camera used for the capture. 'Active Viewport' captures the viewport view; "
            "otherwise the chosen camera is made the scene camera for the capture (restored after).",
        )
        cmb041.addItem("Active Viewport", None)
        for cam in (o for o in bpy.data.objects if o.type == "CAMERA"):
            cmb041.addItem(cam.name, cam)
        cmb050 = menu.add(
            "QComboBox", setObjectName="cmb050", setMaxVisibleItems=12,
            setToolTip="Output format. Movie formats write one file; sequences write one image "
            "per frame; 'PNG Still' captures a single frame.",
        )
        for label, kwargs, is_movie, is_still in self._FORMATS:
            cmb050.addItem(label, (kwargs, is_movie, is_still))
        menu.add(
            "QCheckBox", setText="Launch Viewer", setObjectName="chk058", setChecked=True,
            setToolTip="Play the rendered output when the playblast finishes.",
        )

        # Show the custom start/end only for Custom Range (mirror of the Maya panel).
        def update_range_widgets(index):
            is_custom = index == 3
            menu.s010.setVisible(is_custom)
            menu.s011.setVisible(is_custom)

        menu.cmb010.currentIndexChanged.connect(update_range_widgets)
        update_range_widgets(menu.cmb010.currentIndex())

    def tb000(self, widget):
        """Export Playblast (OpenGL viewport render of the chosen frame range / format)."""
        m = widget.option_box.menu
        scene = bpy.context.scene
        mode = m.cmb010.currentIndex()
        start, end = self._frame_range(mode, m)
        if start > end:
            self.sb.message_box("Start frame must be ≤ end frame.")
            return

        fmt_kwargs, is_movie, is_still = m.cmb050.currentData()
        single_frame = is_still or mode == 2  # PNG Still or Current Frame -> one frame
        animation = not single_frame

        render = scene.render
        ff, imgs = render.ffmpeg, render.image_settings
        has_media_type = hasattr(imgs, "media_type")  # Blender 5.x movie/image gate
        snap = {
            "fs": scene.frame_start, "fe": scene.frame_end, "cam": scene.camera,
            "rx": render.resolution_x, "ry": render.resolution_y,
            "pct": render.resolution_percentage, "path": render.filepath,
            "media": imgs.media_type if has_media_type else None,
            "fmt": imgs.file_format, "q": imgs.quality,
            "ffmt": ff.format, "fcodec": ff.codec, "fcrf": ff.constant_rate_factor,
        }
        try:
            render.resolution_x, render.resolution_y = m.cmb040.currentData()
            render.resolution_percentage = int(m.s015.value())
            render.filepath = self._playblast_path(
                m.t000.text(), int(m.s012.value()), is_movie or is_still
            )
            btk.configure_render_output(scene, quality=m.cmb016.currentData(), **fmt_kwargs)
            cam = m.cmb041.currentData()
            view_context = cam is None
            if cam is not None:
                scene.camera = cam
            if animation:
                scene.frame_start, scene.frame_end = start, end
            else:
                scene.frame_set(start)
            bpy.ops.render.opengl(
                animation=animation, write_still=single_frame, view_context=view_context,
            )
        # ReferenceError: the cmb041 combo (built at init, not refreshed) can hold a camera that
        # was since deleted; TypeError: a missing/empty combo datum.
        except (RuntimeError, TypeError, ReferenceError) as e:
            self.sb.message_box(str(e))
            return
        finally:  # restore every scene setting the capture borrowed
            scene.frame_start, scene.frame_end, scene.camera = snap["fs"], snap["fe"], snap["cam"]
            render.resolution_x, render.resolution_y = snap["rx"], snap["ry"]
            render.resolution_percentage, render.filepath = snap["pct"], snap["path"]
            if has_media_type:  # restore before file_format (media_type gates its valid values)
                imgs.media_type = snap["media"]
            imgs.file_format, imgs.quality = snap["fmt"], snap["q"]
            ff.format, ff.codec, ff.constant_rate_factor = snap["ffmt"], snap["fcodec"], snap["fcrf"]
        if m.chk058.isChecked():
            try:
                bpy.ops.render.play_rendered_anim()
            except RuntimeError:
                pass  # no external player / headless — the file is still written
        self.sb.message_box(f"Playblast written to <hl>{render.filepath}</hl>.")

    @staticmethod
    def _playblast_path(base, padding, single):
        """Build the output filepath: a single file/still uses ``base`` as-is; an image sequence
        gets ``padding`` frame-number ``#`` placeholders appended (Blender's sequence-padding
        mechanism)."""
        base = base.strip()
        if single or not base:
            return base
        return base if "#" in base else base + "#" * max(1, padding)

    # ------------------------------------------------------------------ b-slots
    def b000(self):
        """Render Current Frame"""
        try:
            bpy.ops.render.render("INVOKE_DEFAULT")
        except RuntimeError as e:
            self.sb.message_box(str(e))

    def b001(self):
        """Render Settings (Properties editor, Render tab)"""
        btk.open_editor("Properties")

    def b002(self):
        """Show Last Render"""
        try:
            bpy.ops.render.view_show("INVOKE_DEFAULT")
        except RuntimeError as e:
            self.sb.message_box(str(e))

    # ------------------------------------------------------------------ Maya-editor analogues
    def b003(self):
        """Render Setup — Maya's render-layer manager maps onto Blender's **View Layers**
        (Properties ▸ View Layer)."""
        try:
            btk.open_editor("Properties", properties_context="VIEW_LAYER")
        except Exception as e:
            self.sb.message_box(str(e))

    def b004(self):
        """Rendering Flags — Maya's per-object render flags map onto Blender's per-object ray
        **Visibility** settings (Properties ▸ Object ▸ Visibility)."""
        try:
            btk.open_editor("Properties", properties_context="OBJECT")
        except Exception as e:
            self.sb.message_box(str(e))


# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
