"""Manual harness for the Blender ``hud`` slot (``tentacle/slots/blender/hud.py``).

Requires a real Blender binary (it ``import bpy``), so it is **not** a CI/unittest target — the
``blender/`` subdir and the non-``test_`` name keep it out of auto-discovery. Run it against a
*fresh* Blender (never an existing session)::

    blender --background --factory-startup --python tentacle/test/blender/hud_slot_check.py

Drives the status/selection/component/warning mixins with a recording hud stub (the Qt/UI
layer can't load headless): scene-status lines, dense-safe poly counts, edit-mode component
counts, and the warning checks + shared gating.
"""
import sys
import os
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


class _Hud:
    def __init__(self):
        self.texts = []

    def insertText(self, text):
        self.texts.append(text)

    def joined(self):
        return "\n".join(self.texts)


class _Checkbox:
    def __init__(self, checked):
        self._checked = checked

    def isChecked(self):
        return self._checked


def reset():
    import bpy

    if bpy.context.view_layer.objects.active and bpy.context.view_layer.objects.active.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    bpy.ops.object.select_all(action="DESELECT")
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)


try:
    import bpy
    import bmesh
    from tentacle import tcl_blender  # noqa: F401 — provisions Qt for the slot imports
    from tentacle.slots.blender.hud import HudSlots

    slot = HudSlots.__new__(HudSlots)
    slot.sb = NS(prev_slot=None, loaded_ui=NS())  # no preferences -> warnings gate closed

    # scene status: units + fps always present; symmetry line when a mirror flag is set
    reset()
    bpy.ops.mesh.primitive_cube_add()
    cube = bpy.context.active_object
    cube.data.use_mirror_x = True
    hud = _Hud()
    slot.insert_scene_status(hud)
    check("status has Units + Frame Rate",
          "Units:" in hud.joined() and "Frame Rate:" in hud.joined())
    check("status shows symmetry X", "Symmetry Axis" in hud.joined() and ">X<" in hud.joined(),
          detail=next((t for t in hud.texts if "Symmetry" in t), ""))

    # selection info: cube -> 1 selected, 6 faces, 12 tris, 24 uvs
    hud = _Hud()
    slot.insert_selection_info(hud, [cube])
    joined = hud.joined()
    check("selection count line", "Selected:" in joined and ">1<" in joined)
    check("faces=6 tris=12", "6" in next((t for t in hud.texts if "Faces" in t), "")
          and "12" in next((t for t in hud.texts if "Tris" in t), ""))
    check("uvs=24", "24" in next((t for t in hud.texts if "UVs" in t), ""))

    # component info: edit mode, 3 selected verts of 8 (vert select mode)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_mode(type="VERT")
    bpy.ops.mesh.select_all(action="DESELECT")
    bm = bmesh.from_edit_mesh(cube.data)
    bm.verts.ensure_lookup_table()
    for i in range(3):
        bm.verts[i].select = True
    bmesh.update_edit_mesh(cube.data)
    hud = _Hud()
    slot.insert_component_info(hud, cube)
    check("component counts 3/8", "Selected Verts" in hud.joined()
          and ">3 <" in hud.joined() and "/8" in hud.joined(),
          detail=hud.joined())
    bpy.ops.object.mode_set(mode="OBJECT")

    # warnings: scene unsaved (factory startup) + checks fire correctly
    check("_scene_is_unsaved True on untitled", slot._scene_is_unsaved())
    fps_spec, autosave_spec, open_spec = slot.WARNING_DEFS
    check("default-fps check fires at 24",
          bpy.context.scene.render.fps != 24 or fps_spec["check"](slot))
    autosave_on = bpy.context.preferences.filepaths.use_auto_save_temporary_files
    check("autosave-off check mirrors prefs", autosave_spec["check"](slot) == (not autosave_on))
    check("autosave-open False on untitled", not open_spec["check"](slot))

    # shared gating: enabled warning fires; skip-unsaved suppresses everything on untitled
    prefs = NS(
        chk_warn_framerate=_Checkbox(True),
        chk_warn_autosave_off=_Checkbox(False),
        chk_warn_autosave_open=_Checkbox(False),
        chk_warn_skip_unsaved=_Checkbox(False),
    )
    slot.sb = NS(prev_slot=None, loaded_ui=NS(preferences=prefs))
    bpy.context.scene.render.fps = 24
    active = slot.evaluate_warnings()
    check("gating: enabled fps warning fires", [w["key"] for w in active] == ["chk_warn_framerate"],
          detail=str([w["key"] for w in active]))
    prefs.chk_warn_skip_unsaved = _Checkbox(True)
    check("gating: skip-unsaved suppresses on untitled", slot.evaluate_warnings() == [])

except Exception as e:
    import traceback

    lines.append(f"FAIL setup: {e!r}")
    lines.append(traceback.format_exc())

ok = all(line.startswith("OK") for line in lines)
print("\n===BLENDER-HUD-SLOT===")
print("\n".join(lines))
print(f"===RESULT: {'PASS' if ok else 'FAIL'}===")
