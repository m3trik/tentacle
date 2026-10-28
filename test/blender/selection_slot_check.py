"""Manual harness for the ``selection`` slot (``tentacle/slots/selection.py``) over blendertk.

Requires a real Blender binary (it ``import bpy``), so it is **not** a CI/unittest target — the
``blender/`` subdir and the non-``test_`` name keep it out of auto-discovery. Run it against a
*fresh* Blender (never an existing session)::

    blender --background --factory-startup --python tentacle/test/blender/selection_slot_check.py

Pins, end-to-end through the REAL composed slot class with ``sb.tk = btk`` (the
``btk.Selection`` operations themselves are covered by ``blendertk/test/test_selection.py``):

1. **list001 "Convert To"** — the 18 rows Blender serves (Maya's 20 less Vertex Faces and UV's,
   which Blender has no component for) dispatch without raising against real geometry, and
   "Faces" (touching) differs from "Contained Faces" from an identical seed.
2. **The ``loop_multi_select`` phantom-operator bug** — ``tb000``'s Edge Ring / Edge Loop paths
   and the constraint row's Edge Ring once called an operator that does not exist; pins real
   loop/ring growth through both call sites.
3. **b001 Toggle Selectability** — a second click with nothing selected (Blender drops an
   unselectable object from the selection) makes the objects selectable again.
4. **Select by Type** — the scope pools (``btk.Selection.objects_in_scope``) and the Add /
   Remove modes through ``list000``'s real dispatch.
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


def make_slot(cls, tk):
    """Instance without the UI-loading __init__ (headless: no loaded_ui); the
    composed class reaches Blender through ``sb.tk``."""
    slot = cls.__new__(cls)
    slot.sb = NS(message_box=lambda *a, **k: None, tk=tk)
    return slot


def reset():
    import bpy

    if bpy.context.view_layer.objects.active and bpy.context.view_layer.objects.active.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    bpy.ops.object.select_all(action="DESELECT")
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)


def grid(cuts=6):
    import bpy

    bpy.ops.mesh.primitive_grid_add(x_subdivisions=cuts, y_subdivisions=cuts, size=2)
    obj = bpy.context.active_object
    bpy.ops.object.mode_set(mode="EDIT")
    return obj


class _Leaf:
    """A list leaf as the list handlers see it: no sublist, an unnamed row."""

    sublist = None

    def __init__(self, label):
        self._label = label

    def item_text(self):
        return self._label

    def objectName(self):
        return ""


try:
    import bpy
    import bmesh
    from tentacle import tcl_blender  # noqa: F401 — provisions Qt (qtpy/PySide6) for the slot imports
    from tentacle.slots.selection import SelectionSlots
    import blendertk as btk

    slot = make_slot(SelectionSlots, btk)

    # -- the Convert To rows Blender serves: Maya's 20 less the two it has no component for --
    # This list also drives the dispatch loop, so a stale copy doesn't just fail the count --
    # it silently skips rows.
    EXPECTED_ROWS = [
        "Verts", "Vertex Perimeter",
        "Edges", "Edge Loop", "Edge Ring", "Contained Edges", "Edge Perimeter",
        "Border Edges",
        "Faces", "Face Path", "Contained Faces", "Face Perimeter",
        "UV Shell", "UV Shell Border", "UV Perimeter", "UV Edge Loop",
        "Shell", "Shell Border",
    ]
    rows = slot._convert_to_rows()
    check("Convert To serves the 18 expected rows", rows == set(EXPECTED_ROWS),
          f"{sorted(rows ^ set(EXPECTED_ROWS))}")

    # -- list001: drive every row through the real dispatch against real geometry --
    reset()
    obj = grid(6)
    bpy.ops.uv.smart_project()

    def seed_for(label):
        bpy.ops.mesh.select_all(action="DESELECT")
        bm = bmesh.from_edit_mesh(obj.data)
        bm.verts.ensure_lookup_table()
        bm.edges.ensure_lookup_table()
        bm.faces.ensure_lookup_table()
        if label == "Face Path":
            bpy.ops.mesh.select_mode(type="FACE")
            bm = bmesh.from_edit_mesh(obj.data)
            bm.faces[0].select = True
            bm.faces[-1].select = True
        elif label in ("Vertex Perimeter", "Edge Perimeter", "Face Perimeter"):
            bpy.ops.mesh.select_mode(type="FACE")
            bm = bmesh.from_edit_mesh(obj.data)
            start = bm.faces[len(bm.faces) // 2]
            block = {start}
            frontier = [start]
            while len(block) < 9 and frontier:
                f = frontier.pop(0)
                for e in f.edges:
                    for nf in e.link_faces:
                        if nf not in block and len(block) < 9:
                            block.add(nf)
                            frontier.append(nf)
            for f in block:
                f.select = True
        elif label == "UV Edge Loop":  # a UV-space edge loop needs an edge seed, not a face
            bpy.ops.mesh.select_mode(type="EDGE")
            bm = bmesh.from_edit_mesh(obj.data)
            interior_e = [e for e in bm.edges if len(e.link_faces) == 2][0]
            interior_e.select = True
        elif label in (
            "Contained Faces", "Faces", "UV Shell", "UV Shell Border", "UV Perimeter",
            "Shell", "Shell Border",
        ):
            bpy.ops.mesh.select_mode(type="FACE")
            bm = bmesh.from_edit_mesh(obj.data)
            interior = [f for f in bm.faces if len(f.verts) == 4][0]
            interior.select = True
        elif label in ("Edge Loop", "Edge Ring"):
            bpy.ops.mesh.select_mode(type="EDGE")
            bm = bmesh.from_edit_mesh(obj.data)
            interior_e = [e for e in bm.edges if len(e.link_faces) == 2][0]
            interior_e.select = True
        else:
            bpy.ops.mesh.select_mode(type="VERT")
            bm = bmesh.from_edit_mesh(obj.data)
            interior_v = [v for v in bm.verts if len(v.link_faces) == 4][0]
            interior_v.select = True
        bm.select_flush_mode()
        bmesh.update_edit_mesh(obj.data)

    for label in EXPECTED_ROWS:
        seed_for(label)
        try:
            slot.list001(_Leaf(label))
            ok, err = True, ""
        except Exception as e:  # noqa: BLE001 — pin "doesn't raise", report whatever it was
            ok, err = False, repr(e)
        check(f"list001 dispatches '{label}' without raising", ok, err)

    # -- 'Faces' (touching) must differ from 'Contained Faces' from an identical 1-vertex seed,
    #    through the REAL slot dispatch (not just the underlying engine call) --
    seed_for("Verts")
    slot.list001(_Leaf("Faces"))
    bm = bmesh.from_edit_mesh(obj.data)
    n_touching = len([f for f in bm.faces if f.select])

    seed_for("Verts")
    slot.list001(_Leaf("Contained Faces"))
    bm = bmesh.from_edit_mesh(obj.data)
    n_contained = len([f for f in bm.faces if f.select])

    check(
        "slot-level regression: 'Faces' (touching) != 'Contained Faces' from the same seed",
        n_touching == 4 and n_contained == 0,
        f"touching={n_touching} contained={n_contained}",
    )

    # -- loop_multi_select phantom-operator fix: tb000's Edge Ring / Edge Loop paths --
    def path_widget(checked_name):
        menu = NS(s003=NS(value=lambda: 1))
        for n in ("chk000", "chk001", "chk002", "chk010", "chk021"):
            setattr(menu, n, NS(isChecked=lambda n=n: n == checked_name))
        return NS(option_box=NS(menu=menu))

    def seed_one_interior_edge():
        bpy.ops.mesh.select_all(action="DESELECT")
        bpy.ops.mesh.select_mode(type="EDGE")
        bm = bmesh.from_edit_mesh(obj.data)
        bm.edges.ensure_lookup_table()
        interior_e = [e for e in bm.edges if len(e.link_faces) == 2][0]
        interior_e.select = True
        bm.select_flush_mode()
        bmesh.update_edit_mesh(obj.data)

    seed_one_interior_edge()
    slot.tb000(path_widget("chk000"))  # Edge Ring
    bm = bmesh.from_edit_mesh(obj.data)
    n_ring = len([e for e in bm.edges if e.select])
    check("tb000 Edge Ring grows beyond the 1 seed edge", n_ring > 1, f"got {n_ring}")

    seed_one_interior_edge()
    slot.tb000(path_widget("chk001"))  # Edge Loop
    bm = bmesh.from_edit_mesh(obj.data)
    n_loop = len([e for e in bm.edges if e.select])
    check("tb000 Edge Loop grows beyond the 1 seed edge", n_loop > 1, f"got {n_loop}")

    # -- same fix, second call site: the constraint row's Edge Ring (b005), a one-shot here --
    seed_one_interior_edge()
    slot.b005(NS(objectName=lambda: "b005", isCheckable=lambda: False, isChecked=lambda: False))
    bm = bmesh.from_edit_mesh(obj.data)
    n_b005_ring = len([e for e in bm.edges if e.select])
    check("b005 (Edge Ring constraint) grows beyond the 1 seed edge", n_b005_ring > 1, f"got {n_b005_ring}")

    bpy.ops.object.mode_set(mode="OBJECT")

    # -- b001 Toggle Selectability round-trip: setting hide_select=True auto-deselects in
    #    Blender, so a naive toggle could turn selectability OFF but never back ON. Pin that a
    #    second click (nothing selected, the objects were auto-deselected) restores
    #    selectability and re-selects. --
    reset()
    bpy.ops.mesh.primitive_cube_add()
    ca = bpy.context.active_object
    bpy.ops.mesh.primitive_cube_add(location=(3, 0, 0))
    cb = bpy.context.active_object
    btk.CoreUtils.select([ca, cb])

    slot.b001()  # selection present -> OFF
    selected = btk.CoreUtils.selected_objects()
    check("b001 turns selectability OFF and Blender auto-deselects",
          ca.hide_select and cb.hide_select and not selected,
          f"hide_select=({ca.hide_select},{cb.hide_select}) selected={[o.name for o in selected]}")

    slot.b001()  # nothing selected -> recover: ON + re-select
    selected = btk.CoreUtils.selected_objects()
    check("b001 re-enables selectability from an empty selection (the reported bug)",
          not ca.hide_select and not cb.hide_select
          and {o.name for o in selected} == {ca.name, cb.name},
          f"hide_select=({ca.hide_select},{cb.hide_select}) selected={[o.name for o in selected]}")

    # -- Select by Type: the scope pools. Selected reads the window's view layer, not
    #    bpy.context.selected_objects, which is [] in the Qt event-pump state. --
    reset()
    bpy.ops.mesh.primitive_cube_add()
    c_sel = bpy.context.active_object
    bpy.ops.mesh.primitive_cube_add(location=(3, 0, 0))
    c_hidden = bpy.context.active_object
    bpy.ops.mesh.primitive_cube_add(location=(6, 0, 0))
    c_plain = bpy.context.active_object
    c_hidden.hide_set(True)
    btk.CoreUtils.select([c_sel])

    pool = btk.Selection.objects_in_scope("selected")
    check("Selected scope pools exactly the selection", pool == [c_sel], f"{[o.name for o in pool]}")
    pool = set(btk.Selection.objects_in_scope("visible"))
    check("Visible scope excludes the hidden object",
          c_hidden not in pool and {c_sel, c_plain} <= pool, f"{[o.name for o in pool]}")
    pool = set(btk.Selection.objects_in_scope("all"))
    check("All scope pools every object in the scene", pool == {c_sel, c_hidden, c_plain},
          f"{[o.name for o in pool]}")

    # -- the mode: Add / Remove end-to-end through list000's real dispatch --
    def set_scope(scope, mode="replace"):
        menu = NS(cmb_bytype_scope=NS(currentData=lambda: scope),
                  cmb_bytype_mode=NS(currentData=lambda: mode))
        slot.submenu = NS(tb004=NS(menu=menu))

    set_scope("all", mode="add")
    slot.list000(_Leaf("Polygon Meshes"))  # c_sel already selected; adds the other cubes.
    # Blender refuses selection on hidden objects (select_set doesn't stick on c_hidden), so
    # Add grows to the 2 selectable matches, not 3.
    n_after_add = len(btk.CoreUtils.selected_objects())
    check("Mode: Add grows the selection to every selectable match", n_after_add == 2,
          f"got {n_after_add}")

    set_scope("all", mode="remove")
    slot.list000(_Leaf("Polygon Meshes"))
    n_after_remove = len(btk.CoreUtils.selected_objects())
    check("Mode: Remove deselects the matches", n_after_remove == 0, f"got {n_after_remove}")

except Exception as e:
    lines.append(f"FAIL setup: {e!r}")
    lines.append(traceback.format_exc())

ok = all(line.startswith("OK") for line in lines)
print("\n===BLENDER-SELECTION-SLOT===")
print("\n".join(lines))
print(f"===RESULT: {'PASS' if ok else 'FAIL'}===")
