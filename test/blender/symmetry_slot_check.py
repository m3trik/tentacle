"""Manual harness for the Blender ``symmetry`` slot (``tentacle/slots/blender/symmetry.py``).

Requires a real Blender binary (it ``import bpy``), so it is **not** a CI/unittest target — the
``blender/`` subdir and the non-``test_`` name keep it out of auto-discovery. Run it against a
*fresh* Blender (never an existing session)::

    blender --background --factory-startup --python tentacle/test/blender/symmetry_slot_check.py

Drives the real ``Symmetry`` slot methods with stubbed sb/widget objects (the slot's Qt/UI layer
can't load headless): axis flags (``use_mirror_x/y/z``), Topo matching (``use_mirror_topology``),
and the chk004 position radio — selecting it must clear topology matching, deselecting it must be
a no-op (radio signal ordering: Topo handles its own activation).
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
    slot.messages = []
    slot.sb = NS(message_box=lambda *a, **k: slot.messages.append(a[0] if a else ""))
    return slot


def reset():
    import bpy

    if bpy.context.view_layer.objects.active and bpy.context.view_layer.objects.active.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    bpy.ops.object.select_all(action="DESELECT")
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)


def add_cube(name):
    import bpy

    bpy.ops.mesh.primitive_cube_add()
    o = bpy.context.active_object
    o.name = name
    return o


try:
    import bpy
    from tentacle import tcl_blender  # noqa: F401 — provisions Qt (qtpy/PySide6) for the slot imports
    from tentacle.slots.blender.symmetry import Symmetry

    slot = make_slot(Symmetry)

    # chk000/1/2 set the matching mirror flag on every selected mesh
    reset()
    a, b = add_cube("A"), add_cube("B")
    a.select_set(True)
    slot.chk000(state=True, widget=None)
    check("chk000 sets use_mirror_x on both selected meshes",
          a.data.use_mirror_x and b.data.use_mirror_x)
    check("chk000 posts 'Symmetry: <space> <hl>X</hl>' feedback",
          bool(slot.messages) and slot.messages[-1].startswith("Symmetry:")
          and "<hl>X</hl>" in slot.messages[-1],
          f"msg={(slot.messages or [None])[-1]!r}")
    slot.chk001(state=True, widget=None)
    slot.chk002(state=True, widget=None)
    check("chk001/chk002 set y/z", a.data.use_mirror_y and a.data.use_mirror_z)
    slot.chk000(state=False, widget=None)
    check("chk000 state=False clears x (y/z untouched)",
          not a.data.use_mirror_x and a.data.use_mirror_y and a.data.use_mirror_z)

    # chk005 Topo matching
    reset()
    a = add_cube("A")
    slot.chk005(state=True, widget=None)
    check("chk005 sets use_mirror_topology", a.data.use_mirror_topology)

    # chk004 selected -> position matching (clears topology)
    slot.chk004(state=True, widget=None)
    check("chk004 selected clears use_mirror_topology", not a.data.use_mirror_topology)

    # chk004 deselected (Topo taking over) must not touch the flag
    a.data.use_mirror_topology = True
    slot.chk004(state=False, widget=None)
    check("chk004 deselected is a no-op", a.data.use_mirror_topology)

    # non-mesh selections are filtered, not crashed on
    reset()
    bpy.ops.object.empty_add(type="PLAIN_AXES")
    slot.chk000(state=True, widget=None)
    slot.chk004(state=True, widget=None)
    check("non-mesh selection is filtered (no crash)", True)

    # chk000_init reflects the active mesh's current axis on the stub UI
    reset()
    a = add_cube("A")
    a.data.use_mirror_y = True
    states = {}

    def radio(name):
        return NS(setChecked=lambda v, n=name: states.__setitem__(n, v))

    ui = NS(chk000=radio("chk000"), chk001=radio("chk001"), chk002=radio("chk002"))
    slot.sb = NS(message_box=lambda *a, **k: None,
                 create_button_groups=lambda *a, **k: None)
    slot.chk000_init(NS(ui=ui))
    check("chk000_init reflects active mesh (y checked)", states == {"chk001": True},
          f"states={states}")

except Exception as e:
    lines.append(f"FAIL setup: {e!r}")
    lines.append(traceback.format_exc())

ok = all(line.startswith("OK") for line in lines)
print("\n===BLENDER-SYMMETRY-SLOT===")
print("\n".join(lines))
print(f"===RESULT: {'PASS' if ok else 'FAIL'}===")
