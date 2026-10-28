"""Manual harness for the Rendering slot (``tentacle/slots/rendering.py``) over the real ``btk``.

Requires a real Blender binary (it ``import bpy``), so it is **not** a CI/unittest target -- the
``blender/`` subdir and the non-``test_`` name keep it out of auto-discovery. Run it against a
*fresh* Blender (never an existing session)::

    blender --background --factory-startup --python tentacle/test/blender/rendering_slot_check.py

Drives the composed ``RenderingSlots`` (one class for both hosts, its switchboard's ``tk`` the
real ``blendertk``) with a stubbed option-box menu (the fake widgets of
``tentacle/test/test_rendering_helpers.py``, the Maya counterpart of this file); everything
downstream is live ``bpy`` state:

* cmb003 (Renderer) -- ``tb001_init`` lists ``btk.RenderUtils``' engines and defaults to the
  scene's; ``tb001`` switches ``scene.render.engine`` to the pick before it renders.
* t000 (output) -- empty, showing the file's default playblast path, which follows a saved file.
* chk057 (Show Ornaments) -- ``tb000`` drives ``btk.PlayblastExporter``, which toggles the 3D
  viewport's ``space.overlay.show_overlays`` around the capture and restores it, both ways.
  ``bpy.ops.render.opengl`` always raises under ``--background`` (no OpenGL context), so the
  exporter's one call to it (``PlayblastExporter._opengl``) is substituted by a recorder that
  writes what Blender would; the viewport space, the scene and the overlay are live.
* the Maya-only controls (IPR, Smart Redo, Arnold, Offscreen Capture) are tagged ``requires``.
"""
import os
import sys
import traceback
from pathlib import Path
from types import SimpleNamespace as NS

MONO = Path(__file__).resolve().parents[3]
for pkg in ("pythontk", "uitk", "tentacle", "blendertk"):
    p = str(MONO / pkg)
    if os.path.isdir(p) and p not in sys.path:
        sys.path.insert(0, p)
os.environ.setdefault("QT_API", "pyside6")
# A throwaway Blender: keep its settings off the developer's live uitk stores.
from uitk.testing import TestSandbox  # noqa: E402

try:
    TestSandbox.activate()
except ImportError:  # a first launch: tentacle provisions Qt as it imports
    from tentacle import tcl_blender  # noqa: E402, F401

    TestSandbox.activate()
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

lines = []


def check(name, cond, detail=""):
    lines.append(f"{'OK  ' if cond else 'FAIL'} {name}{(' | ' + detail) if detail else ''}")


def reset_scene():
    import bpy

    if bpy.context.view_layer.objects.active and bpy.context.view_layer.objects.active.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    bpy.ops.object.select_all(action="DESELECT")
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)


# --- fake option-box widgets: one stand-in answers every kind the slot adds -------------
class _Signal:
    def __init__(self):
        self.fns = []

    def connect(self, fn):
        self.fns.append(fn)

    def emit(self, *args):
        for fn in list(self.fns):
            fn(*args)


class _W:
    """A combo, spinbox, checkbox or line edit -- whichever the slot treats it as."""

    def __init__(self, **kw):
        self._items = []  # (label, data)
        self._idx = kw.get("setCurrentIndex", 0)
        self._value = kw.get("setValue", 0)
        self._checked = kw.get("setChecked", False)
        self._text = kw.get("setText", "")
        self._placeholder = ""
        self._props = {}
        self._visible = self._enabled = True
        self.currentIndexChanged = _Signal()
        self.activated = _Signal()
        self.valueChanged = _Signal()
        self.addItems(kw.get("addItems", []))

    # combo
    def addItems(self, labels):
        self._items.extend((str(label), None) for label in labels)

    def addItem(self, label, data=None):
        self._items.append((label, data))

    def clear(self):
        self._items, self._idx = [], 0

    def setItemData(self, i, data):
        self._items[i] = (self._items[i][0], data)

    def itemData(self, i):
        return self._items[i][1] if 0 <= i < len(self._items) else None

    def setCurrentIndex(self, i):
        self._idx = i
        self.currentIndexChanged.emit(i)

    def currentIndex(self):
        return self._idx

    def currentText(self):
        return self._items[self._idx][0] if self._items else ""

    def currentData(self):
        return self.itemData(self._idx)

    # spinbox
    def value(self):
        return self._value

    def setValue(self, v):
        self._value = v

    # checkbox
    def isChecked(self):
        return self._checked

    def setChecked(self, v):
        self._checked = bool(v)

    # line edit
    def text(self):
        return self._text

    def setText(self, t):
        self._text = t

    def setPlaceholderText(self, t):
        self._placeholder = t

    def placeholderText(self):
        return self._placeholder

    # every widget
    def blockSignals(self, block):
        return False

    def setVisible(self, v):
        self._visible = bool(v)

    def setEnabled(self, v):
        self._enabled = bool(v)

    def isEnabled(self):
        return self._enabled

    def setProperty(self, name, value):
        self._props[name] = value

    def property(self, name):
        return self._props.get(name)


class _Menu:
    def __init__(self):
        self.added = []
        self.add_presets = False
        self.presets = NS(
            preset_dir=None, builtin_dir=None, value_provider=None, value_applier=None,
            refresh_modified_state=lambda: False,
        )

    def setTitle(self, t):
        pass

    def add(self, kind, **kw):
        self.added.append(kw.get("setObjectName", kind))
        if kind == "Separator":
            return None
        w = _W(**kw)
        setattr(self, kw["setObjectName"], w)
        return w


class _Widget:
    def __init__(self):
        self.option_box = NS(menu=_Menu())


def make_slot(cls, tk, messages):
    """Instance without the UI-loading __init__ (headless: no loaded_ui)."""
    from contextlib import contextmanager

    @contextmanager
    def progress(text=""):
        yield lambda *a, **k: None

    slot = cls.__new__(cls)
    slot._last_render_key = None
    # Blender: a control tagged for Maya is hidden by the visibility policy.
    slot.sb = NS(
        tk=tk,
        message_box=lambda text, *a, **k: messages.append(text),
        tooltip=NS(fmt=lambda *a, **k: ""),
        apply_visibility_policy=lambda w: w.property("requires") == "maya",
        progress=progress,
        progress_adapter=lambda update: None,
    )
    return slot


try:
    import bpy
    from tentacle import tcl_blender  # noqa: F401 -- provisions Qt (qtpy/PySide6) for the slot imports
    import blendertk as btk
    from blendertk.anim_utils.playblast_exporter import PlayblastExporter
    from tentacle.slots.rendering import RenderingSlots  # composed: both hosts, over sb.tk

    messages = []
    slot = make_slot(RenderingSlots, btk, messages)

    # ============================================================== cmb003 Renderer picker
    reset_scene()
    scene = bpy.context.scene
    eevee = btk.RenderUtils._eevee_id()
    scene.render.engine = eevee

    init_widget = _Widget()
    slot.tb001_init(init_widget)
    init_menu = init_widget.option_box.menu
    idents = [d for _, d in init_menu.cmb003._items]
    check("cmb003 lists the engines (built-ins + Cycles)",
          {eevee, "BLENDER_WORKBENCH", "CYCLES"} <= set(idents), f"idents={idents}")
    check("cmb003 defaults to the scene's current engine",
          init_menu.cmb003.currentData() == eevee, f"got={init_menu.cmb003.currentData()}")
    check("IPR, Smart Redo and Arnold's fields are Maya's",
          all(getattr(init_menu, n).property("requires") == "maya"
              for n in ("chk001", "chk002", "s022", "s028")))
    check("the resolution fields show the scene's",
          init_menu.s020.value() == scene.render.resolution_x
          and init_menu.s020.property("requires") is None)

    # tb001 switches scene.render.engine to the picked renderer before rendering.
    reset_scene()
    bpy.ops.object.camera_add(location=(0, -5, 0), rotation=(1.5708, 0, 0))
    scene.camera = bpy.context.active_object
    scene.render.resolution_x = scene.render.resolution_y = 8
    scene.cycles.samples = 1
    scene.render.engine = eevee
    render_widget = _Widget()
    slot.tb001_init(render_widget)
    render_menu = render_widget.option_box.menu
    check("cmb002 lists the scene camera first",
          render_menu.cmb002.currentText() == scene.camera.name,
          f"{render_menu.cmb002.currentText()!r}")
    render_menu.cmb003.setCurrentIndex([d for _, d in render_menu.cmb003._items].index("CYCLES"))
    slot.tb001(render_widget)  # the INVOKE render refuses headless: a message, no raise
    check("tb001 switches scene.render.engine to the picked renderer",
          scene.render.engine == "CYCLES", f"engine={scene.render.engine}")

    # ============================================================== t000 output default
    # The field stays EMPTY and shows the default as its placeholder: a value written into
    # it would persist and pin the panel to the file it was built in.
    reset_scene()
    path_widget = _Widget()
    slot.tb000_init(path_widget)
    path_menu = path_widget.option_box.menu
    check("t000 starts empty", path_menu.t000.text() == "", f"text={path_menu.t000.text()!r}")
    check("t000's placeholder is the file's default playblast path",
          path_menu.t000.placeholderText() == slot._default_playblast_path(),
          f"placeholder={path_menu.t000.placeholderText()!r}")
    check("Offscreen Capture is Maya's", path_menu.chk056.property("requires") == "maya")
    check("the output picker is btk's registry (no Arnold bundle)",
          ["mp4"] in [d for _, d in path_menu.cmb050._items]
          and ["mp4", "arnold"] not in [d for _, d in path_menu.cmb050._items])
    import pythontk as ptk

    blend_tmp = ptk.TempArtifacts.scoped("tentacle_rendering_check")
    try:
        blend_path = os.path.join(blend_tmp.dir_path(), "ShotB.blend")
        bpy.ops.wm.save_as_mainfile(filepath=blend_path)
        built = list(path_menu.added)
        slot.tb000_init(path_widget)  # refresh_on_show re-runs the init on a panel show
        check("a re-shown playblast menu builds nothing twice", path_menu.added == built)
        placeholder = path_menu.t000.placeholderText()
        check("the placeholder follows a newly saved file",
              os.path.basename(placeholder) == "ShotB"
              and os.path.normcase(placeholder).startswith(
                  os.path.normcase(os.path.dirname(blend_path))),
              f"placeholder={placeholder!r}")
    finally:
        bpy.ops.wm.read_homefile(use_factory_startup=True)
        blend_tmp.cleanup()

    # ============================================================== chk057 Show Ornaments
    reset_scene()
    scene = bpy.context.scene
    cube = bpy.data.objects.new("AnimCube", bpy.data.meshes.new("M"))
    scene.collection.objects.link(cube)
    cube.location.x = 0.0
    cube.keyframe_insert(data_path="location", index=0, frame=1)
    cube.location.x = 5.0
    cube.keyframe_insert(data_path="location", index=0, frame=10)

    view3d_ctx = btk.get_view3d_context()
    check("a VIEW_3D area is available headless (factory-startup default screen)",
          view3d_ctx is not None and view3d_ctx.get("area") is not None)

    if view3d_ctx is not None:
        space = view3d_ctx["area"].spaces.active
        out_tmp = ptk.TempArtifacts.scoped("tentacle_rendering_capture")
        scratch = ptk.format_path(out_tmp.dir_path())
        real_opengl = PlayblastExporter.__dict__["_opengl"]

        def _run_capture(chk057_checked, baseline, path_text=None):
            """Run tb000 (MP4, frames 1-2) with chk057 set to ``chk057_checked`` and the
            viewport overlay pre-set to ``baseline``; returns (observed, after_value)."""
            space.overlay.show_overlays = baseline
            widget = _Widget()
            slot.tb000_init(widget)
            m = widget.option_box.menu
            m.t000.setText(
                os.path.join(out_tmp.dir_path(), "capture") if path_text is None else path_text
            )
            m.cmb010.setCurrentIndex(3)  # Custom Range
            m.s010.setValue(1)
            m.s011.setValue(2)
            m.cmb050.setCurrentIndex([d for _, d in m.cmb050._items].index(["mp4"]))
            m.chk057.setChecked(chk057_checked)
            observed = {}

            def _record(**kw):
                observed["kwargs"] = kw
                observed["show_overlays"] = space.overlay.show_overlays
                observed["filepath"] = path = bpy.context.scene.render.filepath
                # Written only inside the scratch folder: the default path is the
                # user's (a project movie folder, or the Desktop).
                if os.path.normcase(path).startswith(os.path.normcase(scratch)):
                    with open(path, "wb") as f:
                        f.write(b"movie")
                return {"FINISHED"}

            PlayblastExporter._opengl = staticmethod(_record)
            try:
                slot.tb000(widget)
            finally:
                PlayblastExporter._opengl = real_opengl
            return observed, space.overlay.show_overlays

        try:
            observed, after = _run_capture(chk057_checked=False, baseline=True)
            check("tb000 reached the (stubbed) capture call", "kwargs" in observed, f"{observed}")
            check("chk057 unchecked drives show_overlays False during the capture",
                  observed.get("show_overlays") is False, f"{observed}")
            check("show_overlays is restored to its pre-capture baseline (True) afterward",
                  after is True, f"after={after}")
            check("the movie is written as named", os.path.basename(observed.get("filepath", ""))
                  == "capture.mp4", f"{observed.get('filepath')!r}")

            observed2, after2 = _run_capture(chk057_checked=True, baseline=False)
            check("chk057 checked drives show_overlays True during the capture",
                  observed2.get("show_overlays") is True, f"{observed2}")
            check("show_overlays is restored to its pre-capture baseline (False) afterward",
                  after2 is False, f"after={after2}")
            check("the report names the output", any("capture.mp4" in m for m in messages),
                  f"{messages[-1:]}")

            # A blank field (the default state) playblasts to the shown default -- the
            # saved file's own movie folder, here inside the scratch folder (never the
            # user's Desktop: the movie target replaces a file of its name).
            bpy.ops.wm.save_as_mainfile(filepath=os.path.join(scratch, "Blank.blend"))
            check("the default playblast path follows the saved file into its folder",
                  os.path.normcase(ptk.format_path(slot._default_playblast_path())).startswith(
                      os.path.normcase(scratch)),
                  f"default={slot._default_playblast_path()!r}")
            observed3, _ = _run_capture(chk057_checked=True, baseline=True, path_text="")
            check("a blank t000 writes to the default playblast path (MP4: <default>.mp4)",
                  os.path.normcase(observed3.get("filepath", ""))
                  == os.path.normcase(ptk.format_path(slot._default_playblast_path() + ".mp4")),
                  f"filepath={observed3.get('filepath')!r} "
                  f"default={slot._default_playblast_path()!r}")
        finally:
            bpy.ops.wm.read_homefile(use_factory_startup=True)
            out_tmp.cleanup()

except Exception as e:
    lines.append(f"FAIL setup: {e!r}")
    lines.append(traceback.format_exc())

ok = all(line.startswith("OK") for line in lines)
print("\n===BLENDER-RENDERING-SLOT===")
print("\n".join(lines))
print(f"===RESULT: {'PASS' if ok else 'FAIL'}===")
