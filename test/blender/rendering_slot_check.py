"""Manual harness for the Blender ``rendering`` slot (``tentacle/slots/blender/rendering.py``).

Requires a real Blender binary (it ``import bpy``), so it is **not** a CI/unittest target — the
``blender/`` subdir and the non-``test_`` name keep it out of auto-discovery. Run it against a
*fresh* Blender (never an existing session)::

    blender --background --factory-startup --python tentacle/test/blender/rendering_slot_check.py

Drives the real ``Rendering`` slot methods with a stubbed option-box menu (mirrors the fake
``_Menu``/``_Combo``/``_Check`` widgets in ``tentacle/test/test_rendering_helpers.py``, the Maya
counterpart of this file) but everything downstream is live ``bpy`` state:

* cmb003 (Renderer picker) — ``tb001_init`` lists the live-registered engines and defaults to the
  scene's current one; ``tb001`` actually renders (Cycles, 1 sample, 8x8) after switching
  ``scene.render.engine`` to the picked entry.
* chk057 (Show Ornaments) — ``tb000`` toggles the active 3D viewport's
  ``space.overlay.show_overlays`` around the capture and restores it to whatever it was before,
  in both directions. ``bpy.ops.render.opengl`` always raises ``RuntimeError`` under
  ``--background`` (no OpenGL context — a Blender limitation, not a bug in this slot), so the
  capture call itself is substituted with a recording stub (only ``bpy.ops.render.opengl``;
  everything else — the viewport space, the scene, the overlay property — is the real live
  object) by swapping the ``bpy`` name inside the slot module's own namespace, the same
  dependency-substitution idiom the Maya test file uses for ``mtk.RenderUtils``.
"""
import sys
import os
import traceback
from pathlib import Path
from types import SimpleNamespace as NS

MONO = Path(__file__).resolve().parents[3]
for pkg in ("pythontk", "uitk", "tentacle", "blendertk"):
    p = str(MONO / pkg)
    if os.path.isdir(p) and p not in sys.path:
        sys.path.insert(0, p)
os.environ.setdefault("QT_API", "pyside6")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

lines = []


def check(name, cond, detail=""):
    lines.append(f"{'OK  ' if cond else 'FAIL'} {name}{(' | ' + detail) if detail else ''}")


def make_slot(cls):
    """Instance without the UI-loading __init__ (headless: no loaded_ui)."""
    slot = cls.__new__(cls)
    slot.sb = NS(message_box=lambda *a, **k: None)
    return slot


def reset_scene():
    import bpy

    if bpy.context.view_layer.objects.active and bpy.context.view_layer.objects.active.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    bpy.ops.object.select_all(action="DESELECT")
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)


# --- fake option-box widgets (mirrors test_rendering_helpers.py's _Menu/_Combo/_Check) ----------
class _Signal:
    def __init__(self):
        self.fns = []

    def connect(self, fn):
        self.fns.append(fn)


class _Combo:
    def __init__(self):
        self._items = []  # (label, data)
        self._idx = 0
        self.currentIndexChanged = _Signal()

    def addItem(self, label, data=None):
        self._items.append((label, data))

    def addItems(self, labels):
        self._items.extend((str(label), None) for label in labels)

    def setCurrentIndex(self, i):
        self._idx = i

    def currentIndex(self):
        return self._idx

    def currentText(self):
        return self._items[self._idx][0] if self._items else ""

    def currentData(self):
        return self._items[self._idx][1] if self._items else None


class _Check:
    def __init__(self, checked=False):
        self._checked = checked

    def isChecked(self):
        return self._checked

    def setChecked(self, v):
        self._checked = bool(v)


class _Spin:
    def __init__(self, value=0):
        self._value = value
        self._visible = True

    def value(self):
        return self._value

    def setValue(self, v):
        self._value = v

    def setVisible(self, v):
        self._visible = v


class _Text:
    def __init__(self, text=""):
        self._text = text

    def text(self):
        return self._text

    def setText(self, t):
        self._text = t


class _Menu:
    def setTitle(self, t):
        pass

    def add(self, kind, **kw):
        if kind == "QComboBox":
            w = _Combo()
            if "addItems" in kw:
                w.addItems(kw["addItems"])
            if "setCurrentIndex" in kw:
                w._idx = kw["setCurrentIndex"]
        elif kind == "QCheckBox":
            w = _Check(kw.get("setChecked", False))
        elif kind == "QSpinBox":
            w = _Spin(kw.get("setValue", 0))
        elif kind == "QLineEdit":
            w = _Text(kw.get("setText", ""))
        else:
            w = NS()
        setattr(self, kw["setObjectName"], w)
        return w


class _OptionBox:
    def __init__(self):
        self.menu = _Menu()


class _Widget:
    def __init__(self):
        self.option_box = _OptionBox()


# --- bpy proxy: substitutes only bpy.ops.render.opengl, delegates everything else live ---------
class _RenderOpsProxy:
    def __init__(self, real_render_ops, on_opengl):
        self._real = real_render_ops
        self._on_opengl = on_opengl

    def opengl(self, **kw):
        return self._on_opengl(kw)

    def __getattr__(self, name):
        return getattr(self._real, name)


class _OpsProxy:
    def __init__(self, real_ops, on_opengl):
        self._real = real_ops
        self._render_proxy = _RenderOpsProxy(real_ops.render, on_opengl)

    @property
    def render(self):
        return self._render_proxy

    def __getattr__(self, name):
        return getattr(self._real, name)


class _BpyProxy:
    def __init__(self, real_bpy, on_opengl):
        self._real = real_bpy
        self._ops_proxy = _OpsProxy(real_bpy.ops, on_opengl)

    @property
    def ops(self):
        return self._ops_proxy

    def __getattr__(self, name):
        return getattr(self._real, name)


try:
    import bpy
    from tentacle import tcl_blender  # noqa: F401 — provisions Qt (qtpy/PySide6) for the slot imports
    from tentacle.slots.blender import rendering as rendering_module
    from tentacle.slots.blender.rendering import Rendering

    slot = make_slot(Rendering)

    # ============================================================== cmb003 Renderer picker
    reset_scene()
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"

    init_widget = _Widget()
    slot.tb001_init(init_widget)
    init_menu = init_widget.option_box.menu
    idents = [d for _, d in init_menu.cmb003._items]
    check("cmb003 lists the live-registered engines (built-ins + Cycles)",
          {"BLENDER_EEVEE", "BLENDER_WORKBENCH", "CYCLES"} <= set(idents), f"idents={idents}")
    check("cmb003 defaults to the scene's current engine",
          init_menu.cmb003.currentData() == "BLENDER_EEVEE",
          f"got={init_menu.cmb003.currentData()}")

    # tb001 actually switches scene.render.engine to the picked renderer before rendering.
    reset_scene()
    bpy.ops.mesh.primitive_cube_add()
    bpy.ops.object.camera_add(location=(0, -5, 0), rotation=(1.5708, 0, 0))
    scene.camera = bpy.context.active_object
    scene.render.resolution_x = scene.render.resolution_y = 8
    scene.cycles.samples = 1
    scene.render.engine = "BLENDER_EEVEE"

    render_widget = _Widget()
    slot.tb001_init(render_widget)
    render_menu = render_widget.option_box.menu
    render_idents = [d for _, d in render_menu.cmb003._items]
    render_menu.cmb003.setCurrentIndex(render_idents.index("CYCLES"))
    slot.tb001(render_widget)
    check("tb001 switches scene.render.engine to the picked renderer",
          scene.render.engine == "CYCLES", f"engine={scene.render.engine}")

    # ============================================================== chk057 Show Ornaments
    reset_scene()
    cube = bpy.data.objects.new("AnimCube", bpy.data.meshes.new("M"))
    bpy.context.collection.objects.link(cube)
    cube.location.x = 0.0
    cube.keyframe_insert(data_path="location", index=0, frame=1)
    cube.location.x = 5.0
    cube.keyframe_insert(data_path="location", index=0, frame=10)

    import blendertk as btk  # noqa: F401 — module already imported by rendering_module; alias for clarity

    view3d_ctx = btk.get_view3d_context()
    check("a VIEW_3D area is available headless (factory-startup default screen)",
          view3d_ctx is not None and view3d_ctx.get("area") is not None)

    if view3d_ctx is not None:
        space = view3d_ctx["area"].spaces.active

        def _run_capture(chk057_checked, baseline):
            """Run tb000 with chk057 set to ``chk057_checked`` and the viewport overlay
            pre-set to ``baseline``; returns (observed_during_capture, after_value)."""
            space.overlay.show_overlays = baseline
            widget = _Widget()
            slot.tb000_init(widget)
            m = widget.option_box.menu
            m.t000.setText("//_rendering_slot_check_")
            m.cmb010.setCurrentIndex(3)  # Custom Range
            m.s010.setValue(1)
            m.s011.setValue(2)
            m.chk057.setChecked(chk057_checked)

            observed = {}

            def _on_opengl(kw):
                observed["kwargs"] = kw
                observed["show_overlays"] = space.overlay.show_overlays
                return {"FINISHED"}

            orig_bpy = rendering_module.bpy
            rendering_module.bpy = _BpyProxy(orig_bpy, _on_opengl)
            try:
                slot.tb000(widget)
            finally:
                rendering_module.bpy = orig_bpy
            return observed, space.overlay.show_overlays

        observed, after = _run_capture(chk057_checked=False, baseline=True)
        check("tb000 reached the (stubbed) capture call", "kwargs" in observed, f"{observed}")
        check("chk057 unchecked drives show_overlays False during the capture",
              observed.get("show_overlays") is False, f"{observed}")
        check("show_overlays is restored to its pre-capture baseline (True) afterward",
              after is True, f"after={after}")

        observed2, after2 = _run_capture(chk057_checked=True, baseline=False)
        check("chk057 checked drives show_overlays True during the capture",
              observed2.get("show_overlays") is True, f"{observed2}")
        check("show_overlays is restored to its pre-capture baseline (False) afterward",
              after2 is False, f"after={after2}")

except Exception as e:
    lines.append(f"FAIL setup: {e!r}")
    lines.append(traceback.format_exc())

ok = all(line.startswith("OK") for line in lines)
print("\n===BLENDER-RENDERING-SLOT===")
print("\n".join(lines))
print(f"===RESULT: {'PASS' if ok else 'FAIL'}===")
