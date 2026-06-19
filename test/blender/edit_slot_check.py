"""Manual harness for the Blender ``edit`` slot (``tentacle/slots/blender/edit.py``).

Requires a real Blender binary (it ``import bpy``), so it is **not** a CI/unittest target — the
``blender/`` subdir and the non-``test_`` name keep it out of auto-discovery. Run it against a
*fresh* Blender (never an existing session)::

    blender --background --factory-startup --python tentacle/test/blender/edit_slot_check.py

Drives the real ``Edit`` slot methods with stubbed sb/widget objects (the slot's Qt/UI layer
can't load headless): Mesh-Cleanup option routing, mode-aware Delete-Selected (FACE vs VERT
dispatch — deleting by VERT in face mode would nuke neighboring faces), Create-Primitive and
Convert list handlers.
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


def reset():
    import bpy

    if bpy.context.view_layer.objects.active and bpy.context.view_layer.objects.active.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    bpy.ops.object.select_all(action="DESELECT")
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)


def list_item(text, parent=""):
    return NS(item_text=lambda: text, parent_item_text=lambda: parent)


try:
    import bpy
    from tentacle import tcl_blender  # noqa: F401 — provisions Qt (qtpy/PySide6) for the slot imports
    from tentacle.slots.blender.edit import Edit

    slot = make_slot(Edit)

    # list000 Create Primitive: every mapped operator exists on bpy.ops.mesh
    missing = [
        f"{cat}/{label}"
        for cat, items in Edit._PRIMITIVES.items()
        for label, op in items.items()
        if not hasattr(bpy.ops.mesh, op)
    ]
    check("list000 primitive ops all exist", missing == [], f"missing={missing}")

    # list000 creates a cube
    reset()
    slot.list000(list_item("Cube", "Polygon"))
    check("list000 'Cube' creates a mesh object",
          len(bpy.data.objects) == 1 and bpy.data.objects[0].type == "MESH",
          f"objects={[o.name for o in bpy.data.objects]}")

    # list001 Convert: bezier circle -> Mesh
    reset()
    bpy.ops.curve.primitive_bezier_circle_add()
    o = bpy.context.active_object
    slot.list001(list_item("Mesh"))
    check("list001 'Mesh' converts curve -> MESH", o.type == "MESH", f"type={o.type}")

    # tb000 Mesh Cleanup option routing (chk024/chk032/chk033/chk028/chk029 + s000)
    reset()
    import bmesh

    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=2.0)
    bm.verts.ensure_lookup_table()
    bm.verts.new(bm.verts[0].co.copy())  # loose double
    me = bpy.data.meshes.new("M"); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new("Clean", me)
    bpy.context.collection.objects.link(o)
    o.select_set(True); bpy.context.view_layer.objects.active = o
    v0 = len(o.data.vertices)

    def chk(state):
        return NS(isChecked=lambda s=state: s)

    menu = NS(chk024=chk(True), s000=NS(value=lambda: 0.001), chk032=chk(True),
              chk033=chk(True), chk028=chk(True), chk029=chk(False))
    slot.tb000(NS(option_box=NS(menu=menu)))
    # the loose double welds into the corner vert (9 -> 8); nothing loose remains after
    check("tb000 cleanup merges the loose double", len(o.data.vertices) == v0 - 1,
          f"{v0}->{len(o.data.vertices)}")

    # tb002 Delete Selected in FACE mode: middle face of a 3x3 grid -> 8 faces remain.
    # (The old VERT-typed delete removed the face's verts, nuking all 8 neighbors too.)
    reset()
    bpy.ops.mesh.primitive_grid_add(x_subdivisions=3, y_subdivisions=3)
    o = bpy.context.active_object
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_mode(type="FACE")
    bpy.ops.mesh.select_all(action="DESELECT")
    bm = bmesh.from_edit_mesh(o.data)
    bm.faces.ensure_lookup_table()
    center = min(bm.faces, key=lambda f: f.calc_center_median().length)
    center.select_set(True)
    bmesh.update_edit_mesh(o.data)
    slot.tb002(None)
    bpy.ops.object.mode_set(mode="OBJECT")
    check("tb002 FACE-mode delete keeps neighbors (9->8)", len(o.data.polygons) == 8,
          f"faces={len(o.data.polygons)}")

    # tb002 in OBJECT mode deletes the selected object
    reset()
    bpy.ops.mesh.primitive_cube_add()
    slot.tb002(None)
    check("tb002 object-mode delete removes object", len(bpy.data.objects) == 0,
          f"objects={len(bpy.data.objects)}")

except Exception as e:
    lines.append(f"FAIL setup: {e!r}")
    lines.append(traceback.format_exc())

ok = all(line.startswith("OK") for line in lines)
print("\n===BLENDER-EDIT-SLOT===")
print("\n".join(lines))
print(f"===RESULT: {'PASS' if ok else 'FAIL'}===")
