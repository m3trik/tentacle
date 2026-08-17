"""Manual harness for the Blender ``selection`` slot (``tentacle/slots/blender/selection.py``).

Requires a real Blender binary (it ``import bpy``), so it is **not** a CI/unittest target — the
``blender/`` subdir and the non-``test_`` name keep it out of auto-discovery. Run it against a
*fresh* Blender (never an existing session)::

    blender --background --factory-startup --python tentacle/test/blender/selection_slot_check.py

Pins two things end-to-end through the REAL slot class (not just the ``btk.Selection`` engine,
which ``blendertk/test/test_selection.py`` already covers directly):

1. **list001 "Convert To"** — the 18-entry list (mayatk parity: 7→18 of Maya's 20; the
   ``cmb003`` combo until 2026-08-16) dispatches every entry without raising against real
   geometry, and the touching-vs-contained fix ("Faces" vs "Contained Faces" from an identical
   seed) actually differs through the slot dispatch, not just the underlying engine call.
2. **The ``loop_multi_select`` phantom-operator bug** — ``tb000``'s Edge Ring/Edge Loop radios
   and the Selection-Constraint row's entries used to call a Blender operator that doesn't
   exist (``bpy.ops.mesh.loop_multi_select``; ``hasattr`` lies, ``get_rna_type()`` proves it
   fake) — fixed to ``select_edge_ring_multi``/``select_edge_loop_multi``. Pins real loop/ring
   growth (not just "doesn't crash") through both call sites.
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


def grid(cuts=6):
    import bpy

    bpy.ops.mesh.primitive_grid_add(x_subdivisions=cuts, y_subdivisions=cuts, size=2)
    obj = bpy.context.active_object
    bpy.ops.object.mode_set(mode="EDIT")
    return obj


try:
    import bpy
    import bmesh
    from tentacle import tcl_blender  # noqa: F401 — provisions Qt (qtpy/PySide6) for the slot imports
    from tentacle.slots.blender.selection import Selection

    slot = make_slot(Selection)

    class _Leaf:
        """A Convert To list leaf as ``_dispatch_convert_to`` sees it."""

        sublist = None

        def __init__(self, label):
            self._label = label

        def item_text(self):
            return self._label

    # -- _CONVERT_TO_OPS: exactly the 18 expected entries, in order (the table IS the list) --
    # This list also drives the dispatch loop, so a stale copy doesn't just fail the count --
    # it silently skips leaves. Keep it in sync with the fork's _CONVERT_TO_OPS.
    EXPECTED_CMB003 = [
        "Verts", "Vertex Perimeter",
        "Edges", "Edge Loop", "Edge Ring", "Contained Edges", "Edge Perimeter",
        "Border Edges",
        "Faces", "Face Path", "Contained Faces", "Face Perimeter",
        "UV Shell", "UV Shell Border", "UV Perimeter", "UV Edge Loop",
        "Shell", "Shell Border",
    ]
    check("_CONVERT_TO_OPS holds all 18 expected entries in order",
          list(Selection._CONVERT_TO_OPS) == EXPECTED_CMB003, f"{list(Selection._CONVERT_TO_OPS)}")

    # -- list001: drive every entry through the real dispatch against real geometry --
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

    for label in EXPECTED_CMB003:
        seed_for(label)
        try:
            slot.list001(_Leaf(label))
            ok, err = True, ""
        except Exception as e:  # noqa: BLE001 — pin "doesn't raise", report whatever it was
            ok, err = False, repr(e)
        check(f"list001 dispatches '{label}' without raising", ok, err)

    # -- regression: 'Faces' (touching) must differ from 'Contained Faces' from an identical
    #    1-vertex seed, through the REAL slot dispatch (not just the underlying engine call) --
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

    # -- loop_multi_select phantom-operator fix: tb000's Edge Ring / Edge Loop radios --
    class _Chk:
        def __init__(self, state):
            self._state = state

        def isChecked(self):
            return self._state

    class _Spin:
        def value(self):
            return 1

    class _Menu:
        def __init__(self, checked_name):
            for n in ("chk000", "chk001", "chk002", "chk010", "chk021"):
                setattr(self, n, _Chk(n == checked_name))
            self.s003 = _Spin()

    class _OptWidget:
        def __init__(self, checked_name):
            self.option_box = NS(menu=_Menu(checked_name))

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
    slot.tb000(_OptWidget("chk000"))  # Edge Ring
    bm = bmesh.from_edit_mesh(obj.data)
    n_ring = len([e for e in bm.edges if e.select])
    check("tb000 Edge Ring (select_edge_ring_multi) grows beyond the 1 seed edge", n_ring > 1, f"got {n_ring}")

    seed_one_interior_edge()
    slot.tb000(_OptWidget("chk001"))  # Edge Loop
    bm = bmesh.from_edit_mesh(obj.data)
    n_loop = len([e for e in bm.edges if e.select])
    check("tb000 Edge Loop (select_edge_loop_multi) grows beyond the 1 seed edge", n_loop > 1, f"got {n_loop}")

    # -- same fix, second call site: the Selection-Constraint row's Edge Ring (b005) --
    seed_one_interior_edge()
    slot.b005(NS(objectName=lambda: "b005"))
    bm = bmesh.from_edit_mesh(obj.data)
    n_b005_ring = len([e for e in bm.edges if e.select])
    check("b005 (Edge Ring constraint) grows beyond the 1 seed edge", n_b005_ring > 1, f"got {n_b005_ring}")

    bpy.ops.object.mode_set(mode="OBJECT")

    # -- b001 Toggle Selectability round-trip: setting hide_select=True auto-deselects in
    #    Blender, so a naive toggle could turn selectability OFF but never back ON. Pin that a
    #    second click (with nothing selected, because the objects were auto-deselected) restores
    #    selectability and re-selects. --
    reset()
    bpy.ops.mesh.primitive_cube_add()
    ca = bpy.context.active_object
    bpy.ops.mesh.primitive_cube_add(location=(3, 0, 0))
    cb = bpy.context.active_object
    ca.select_set(True); cb.select_set(True)

    slot.b001()  # selection present -> OFF
    off_ok = ca.hide_select and cb.hide_select and not slot.selected_objects()
    check("b001 turns selectability OFF and Blender auto-deselects", off_ok,
          f"hide_select=({ca.hide_select},{cb.hide_select}) selected={[o.name for o in slot.selected_objects()]}")

    slot.b001()  # nothing selected -> recover: ON + re-select
    on_ok = (not ca.hide_select and not cb.hide_select
             and {o.name for o in slot.selected_objects()} == {ca.name, cb.name})
    check("b001 re-enables selectability from an empty selection (the reported bug)", on_ok,
          f"hide_select=({ca.hide_select},{cb.hide_select}) selected={[o.name for o in slot.selected_objects()]}")

    # -- tb004 Select-by-Type settings: _by_type_scope_objects pools per the scope combo.
    #    Notably pins that the Selected scope reads via selected_objects() (view_layer),
    #    not bpy.context.selected_objects, which is [] in the Qt event-pump state. --
    class _ScopeMenu:
        def __init__(self, scope, mode="replace"):
            self.cmb_bytype_scope = NS(currentData=lambda: scope)
            self.cmb_bytype_mode = NS(currentData=lambda: mode)

    def set_scope(scope, mode="replace"):
        # tb004's settings menu is the button's own MenuMixin menu now (no
        # option box), so the scope/mode reads go through ``.menu``.
        slot.submenu = NS(tb004=NS(menu=_ScopeMenu(scope, mode)))

    reset()
    bpy.ops.mesh.primitive_cube_add()
    c_sel = bpy.context.active_object
    bpy.ops.mesh.primitive_cube_add(location=(3, 0, 0))
    c_hidden = bpy.context.active_object
    bpy.ops.mesh.primitive_cube_add(location=(6, 0, 0))
    c_plain = bpy.context.active_object
    c_hidden.hide_set(True)
    bpy.ops.object.select_all(action="DESELECT")
    c_sel.select_set(True)

    set_scope("selected")
    pool = slot._by_type_scope_objects()
    check("tb004 Selected scope pools exactly the selection", pool == [c_sel],
          f"{[o.name for o in pool]}")

    set_scope("visible")
    pool = set(slot._by_type_scope_objects())
    check("tb004 Visible scope excludes the hidden object",
          c_hidden not in pool and {c_sel, c_plain} <= pool, f"{[o.name for o in pool]}")

    set_scope(None)  # unset combo → "all"
    pool = set(slot._by_type_scope_objects())
    check("tb004 All scope pools every object", pool == {c_sel, c_hidden, c_plain},
          f"{[o.name for o in pool]}")

    # -- tb004 mode: Add / Remove flow end-to-end through list000's real dispatch --
    class _Leaf:
        sublist = None

        def objectName(self):  # a real leaf row is an unnamed list item
            return ""

        def item_text(self):
            return "Polygon Meshes"

    set_scope("all", mode="add")
    slot.list000(_Leaf())  # c_sel already selected; adds the other cubes.
    # Blender natively refuses selection on hidden objects (select_set doesn't
    # stick on c_hidden), so Add grows to the 2 selectable matches, not 3.
    n_after_add = len(slot.selected_objects())
    check("tb004 Mode: Add grows the selection to every selectable match", n_after_add == 2,
          f"got {n_after_add}")

    set_scope("all", mode="remove")
    slot.list000(_Leaf())
    n_after_remove = len(slot.selected_objects())
    check("tb004 Mode: Remove deselects the matches", n_after_remove == 0,
          f"got {n_after_remove}")

except Exception as e:
    lines.append(f"FAIL setup: {e!r}")
    lines.append(traceback.format_exc())

ok = all(line.startswith("OK") for line in lines)
print("\n===BLENDER-SELECTION-SLOT===")
print("\n".join(lines))
print(f"===RESULT: {'PASS' if ok else 'FAIL'}===")
