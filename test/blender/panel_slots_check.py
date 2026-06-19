"""Manual harness for the Blender tool-panel slots (mirror / duplicate_linear / duplicate_radial
/ duplicate_grid / cut_on_axis / hdr_manager / reference_manager).

Requires a real Blender binary (it ``import bpy``), so it is **not** a CI/unittest target — the
``blender/`` subdir and the non-``test_`` name keep it out of auto-discovery. Run it against a
*fresh* Blender (never an existing session)::

    blender --background --factory-startup --python tentacle/test/blender/panel_slots_check.py

Drives each slot's real ``perform_operation`` with stubbed sb/ui widgets (the Qt/UI layer can't
load headless) — catching widget-name drift between the slot readers and the ``.ui`` surface,
and verifying the slot -> blendertk round trip produces the expected geometry. The .ui side is
covered separately by ``menus_load_check.py`` (live GUI).
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


# ---- stub widgets (only the reader surface perform_operation touches)
def combo(index=0, data=None):
    return NS(currentIndex=lambda: index, currentData=lambda: data)


def chk(v=False):
    return NS(isChecked=lambda: v)


def spin(v=0):
    return NS(value=lambda: v)


messages = []  # sb.message_box capture (asserted by the manager-panel checks)


def make_slot(cls, ui, axis=""):
    """Instance without the UI-loading __init__; sb stubs message_box + the axis helper."""
    slot = cls.__new__(cls)
    slot.sb = NS(
        message_box=lambda *a, **k: messages.append(" ".join(map(str, a))),
        get_axis_from_checkboxes=lambda *a, **k: axis,
    )
    slot.ui = ui
    return slot


try:
    import bpy

    # The tool-panel Slots now live co-located in blendertk (next to their engine + .ui),
    # discovered by BlenderUiHandler — not in tentacle. Their Qt-only imports are deferred,
    # so importing the Slots classes is Qt-free (no tcl_blender Qt-provisioning needed here).
    from blendertk.edit_utils.mirror import MirrorSlots
    from blendertk.edit_utils.cut_on_axis import CutOnAxisSlots
    from blendertk.edit_utils.duplicate_linear import DuplicateLinearSlots
    from blendertk.edit_utils.duplicate_radial import DuplicateRadialSlots
    from blendertk.edit_utils.duplicate_grid import DuplicateGridSlots

    def reset():
        if (
            bpy.context.view_layer.objects.active
            and bpy.context.view_layer.objects.active.mode != "OBJECT"
        ):
            bpy.ops.object.mode_set(mode="OBJECT")
        bpy.ops.object.select_all(action="DESELECT")
        for o in list(bpy.data.objects):
            bpy.data.objects.remove(o, do_unlink=True)

    def cube(x=0.0, size=2.0):
        bpy.ops.mesh.primitive_cube_add(size=size, location=(x, 0, 0))
        return bpy.context.active_object

    # ---- mirror: world pivot, merge OFF -> separate _mirror object
    reset()
    o = cube(x=2.0)
    ui = NS(cmb002=combo(1), cmb003=combo(0), chk005=chk(False), chk006=chk(False))
    slot = make_slot(MirrorSlots, ui, axis="x")
    slot.perform_operation([o])
    check("mirror slot OFF makes a _mirror object",
          any(x.name.endswith("_mirror") for x in bpy.data.objects),
          f"{[x.name for x in bpy.data.objects]}")

    # ---- mirror: border merge welds in-mesh
    reset()
    o = cube(x=2.0)
    ui = NS(cmb002=combo(3), cmb003=combo(2), chk005=chk(False), chk006=chk(False))
    slot = make_slot(MirrorSlots, ui, axis="-x")  # border + '-' -> min face
    slot.perform_operation([o])
    xs = [(o.matrix_world @ v.co).x for v in o.data.vertices]
    check("mirror slot border(-x) spans -1..3 welded",
          abs(min(xs) + 1.0) < 1e-4 and abs(max(xs) - 3.0) < 1e-4 and len(o.data.vertices) == 12,
          f"x {min(xs):.2f}..{max(xs):.2f} v={len(o.data.vertices)}")

    # ---- mirror: bbox-center pivot symmetrizes (keeps the +x half by UI convention)
    reset()
    o = cube()
    ui = NS(cmb002=combo(2), cmb003=combo(0), chk005=chk(False), chk006=chk(False))
    slot = make_slot(MirrorSlots, ui, axis="x")
    slot.perform_operation([o])
    xs = [(o.matrix_world @ v.co).x for v in o.data.vertices]
    check("mirror slot center symmetrizes full span",
          abs(min(xs) + 1.0) < 1e-4 and abs(max(xs) - 1.0) < 1e-4,
          f"x {min(xs):.2f}..{max(xs):.2f}")

    # ---- mirror: missing axis raises the user-facing error
    try:
        make_slot(MirrorSlots, ui, axis="").perform_operation([o])
        check("mirror slot empty axis raises", False)
    except ValueError:
        check("mirror slot empty axis raises", True)

    # ---- cut_on_axis: 2 cuts via stub spinners
    reset()
    o = cube()
    ui = NS(cmb001=combo(2), s000=spin(2), s001=spin(0.0), chk005=chk(False), chk006=chk(False))
    slot = make_slot(CutOnAxisSlots, ui, axis="x")
    slot.perform_operation([o])
    check("cut slot 2 cuts -> 14 faces", len(o.data.polygons) == 14, f"f={len(o.data.polygons)}")

    # ---- cut_on_axis: delete clears the +x half
    reset()
    o = cube()
    ui = NS(cmb001=combo(2), s000=spin(1), s001=spin(0.0), chk005=chk(True), chk006=chk(False))
    slot = make_slot(CutOnAxisSlots, ui, axis="x")
    slot.perform_operation([o])
    xs = [(o.matrix_world @ v.co).x for v in o.data.vertices]
    check("cut slot delete removes +X half", max(xs) < 1e-4, f"max x {max(xs):.2f}")

    # ---- duplicate_linear: s009 copies includes the original; linear ramp
    reset()
    o = cube()
    ui = NS(
        s000=spin(6.0), s001=spin(0.0), s002=spin(0.0),  # translate
        s003=spin(0.0), s004=spin(0.0), s005=spin(0.0),  # rotate
        s006=spin(1.0), s007=spin(1.0), s008=spin(1.0),  # scale
        s009=spin(4),                                    # copies (incl. original) -> 3 dups
        s010=spin(0.5), s011=spin(4.0),
        cmb001=combo(0, "linear"), cmb003=combo(0, "object"), chk001=chk(True),
    )
    slot = make_slot(DuplicateLinearSlots, ui)
    slot.perform_operation([o])
    copies = [x for x in bpy.data.objects if x is not o]
    xs = sorted(c.matrix_world.translation.x for c in copies)
    check("linear slot makes count-1 copies", len(copies) == 3, f"n={len(copies)}")
    check("linear slot ramps to the full offset",
          all(abs(a - b) < 1e-4 for a, b in zip(xs, [2.0, 4.0, 6.0])),
          f"{[round(x, 2) for x in xs]}")
    check("linear slot instances share data", all(c.data is o.data for c in copies))

    # ---- duplicate_radial: 4 copies full revolution about world Z
    reset()
    o = cube(x=3.0)
    name = o.name
    ui = NS(
        s000=spin(0.0), s001=spin(0.0), s002=spin(0.0),
        s003=spin(0.0), s004=spin(0.0), s005=spin(0.0),
        s006=spin(1.0), s007=spin(1.0), s008=spin(1.0),
        s009=spin(4), s010=spin(0.0), s011=spin(0.0), s012=spin(0.0),
        s013=spin(0.0), s014=spin(360.0), s015=spin(0.5), s016=spin(0.5),
        cmb000=combo(1),                                  # world pivot
        chk002=chk(False), chk003=chk(False), chk004=chk(True),  # rotate axis -> z
        chk005=chk(False), chk006=chk(False), chk007=chk(False),
    )
    slot = make_slot(DuplicateRadialSlots, ui)
    slot.perform_operation([o])
    meshes = [x for x in bpy.data.objects if x.type == "MESH"]
    radii = [m.matrix_world.translation.length for m in meshes]
    check("radial slot 4 copies, original dropped",
          len(meshes) == 4 and name not in [m.name for m in meshes],
          f"n={len(meshes)}")
    check("radial slot orbit radius kept", all(abs(r - 3.0) < 1e-4 for r in radii))

    # ---- duplicate_grid: 2x2x1 instances under an Empty
    reset()
    o = cube(size=2.0)
    ui = NS(
        s000=spin(2), s001=spin(2), s002=spin(1), s003=spin(1.0),
        cmb000=combo(1, "instance"),
    )
    slot = make_slot(DuplicateGridSlots, ui)
    slot.perform_operation([o])
    copies = [x for x in bpy.data.objects if x.type == "MESH" and x is not o]
    check("grid slot 3 copies under an Empty",
          len(copies) == 3 and all(c.parent and c.parent.type == "EMPTY" for c in copies),
          f"n={len(copies)}")

    # ---- hdr_manager: folder scan + select-applies + live levels ---------------------------
    import tempfile
    import blendertk as btk
    from blendertk.light_utils.hdr_manager import HdrManagerSlots

    def lineedit(text=""):
        return NS(text=lambda: text)

    class ComboStub:
        def __init__(self):
            self.added, self.data = None, None
        def add(self, items, **kw):
            self.added = dict(items)
        def currentData(self):
            return self.data
        def blockSignals(self, state):  # _populate_maps guards its rebuild
            pass

    tmp_dir = tempfile.mkdtemp(prefix="tcl_hdr_")
    img = bpy.data.images.new("hdr_fixture", 8, 4, float_buffer=True)
    img.file_format = "HDR"
    hdr_path = os.path.join(tmp_dir, "studio.hdr")
    img.filepath_raw = hdr_path
    img.save()
    open(os.path.join(tmp_dir, "notes.txt"), "w").close()  # must be filtered out

    cmb = ComboStub()
    ui = NS(
        txt000=lineedit(tmp_dir), cmb000=cmb,
        spn_intensity=spin(2.0), spn_exposure=spin(1.0),
        slider000=spin(90), chk000=chk(True),
    )
    slot = make_slot(HdrManagerSlots, ui)
    slot._populate_maps()
    check("hdr slot scans only .hdr/.exr", cmb.added == {"studio.hdr": hdr_path},
          f"added={cmb.added}")

    messages.clear()
    slot.cmb000(0, cmb)  # nothing picked yet -> silent no-op, world untouched
    check("hdr slot select with no map is a no-op", len(messages) == 0
          and btk.get_world_hdri() is None)

    cmb.data = hdr_path
    slot.cmb000(0, cmb)  # selecting a map applies it (the sole apply action)
    state = btk.get_world_hdri()
    check("hdr slot select applies intensity*2^exposure", state is not None
          and abs(state["strength"] - 4.0) < 1e-6 and abs(state["rotation"] - 90) < 1e-4,
          f"state={state}")

    ui.slider000 = spin(180)  # live level update path
    slot.slider000(180, None)
    check("hdr slot live rotation update",
          abs(btk.get_world_hdri()["rotation"] - 180) < 1e-4)

    os.remove(hdr_path)
    os.remove(os.path.join(tmp_dir, "notes.txt"))
    os.rmdir(tmp_dir)

    # ---- reference_manager: link round trip (refresh / reload / remove) --------------------
    from blendertk.env_utils.reference_manager import ReferenceManagerSlots

    class ListStub:
        def __init__(self):
            self.items, self.row = [], -1
        def clear(self):
            self.items = []
        def addItem(self, text):
            self.items.append(text)
        def currentRow(self):
            return self.row

    reset()
    src = cube()
    src.name = "LibCube"
    lib_dir = tempfile.mkdtemp(prefix="tcl_lib_")
    lib_path = os.path.join(lib_dir, "lib.blend")
    bpy.data.libraries.write(lib_path, {src}, fake_user=True)
    reset()
    bpy.ops.wm.link(
        filepath=os.path.join(lib_path, "Object", "LibCube"),
        directory=os.path.join(lib_path, "Object"),
        filename="LibCube",
    )
    check("library linked for the fixture", len(bpy.data.libraries) == 1,
          f"libs={[lib.name for lib in bpy.data.libraries]}")

    lst = ListStub()
    slot = make_slot(ReferenceManagerSlots, NS(lst000=lst))
    slot._refresh()
    check("ref slot lists the library (no missing flag)",
          len(lst.items) == 1 and "lib.blend" in lst.items[0]
          and not lst.items[0].startswith("⚠"),
          f"items={lst.items}")

    messages.clear()
    slot.b002()  # no row selected -> message
    check("ref slot acts only on a selected row", len(messages) == 1)

    lst.row = 0
    messages.clear()
    slot.b002()  # reload the linked library in place
    check("ref slot reload succeeds and keeps the library",
          len(bpy.data.libraries) == 1 and messages == ["Reloaded <hl>lib.blend</hl>."],
          f"messages={messages}")

    lst.row = 0
    slot.b004()  # remove -> library and its objects gone
    check("ref slot remove unlinks the library",
          len(bpy.data.libraries) == 0 and not lst.items,
          f"libs={len(bpy.data.libraries)} items={lst.items}")

    os.remove(lib_path)
    os.rmdir(lib_dir)

    # ---- curtain: generated rail + rail-from-curve through the real slot reader ---------
    from blendertk.edit_utils.curtain import CurtainSlots

    def curtain_ui(**over):
        base = dict(
            s000=spin(2.0), s001=spin(6.0), s002=spin(0.0), s003=spin(5),
            s004=spin(0.4), s005=spin(1.5), s006=spin(2.5), s007=spin(0.5),
            s008=spin(0.0), s009=spin(8.0), s010=spin(0), s011=spin(0.0),
            s012=spin(0.0), s013=spin(0.0), s014=spin(0.0), s015=spin(0),
            s016=spin(0.0), s017=spin(0.0), s018=spin(0.25), s019=spin(0.0),
            s020=spin(0.0), s021=spin(0), s022=spin(0.0), s023=spin(0.0),
            s024=spin(0), s025=spin(0.0), s026=spin(0.0), s027=spin(0.0),
            chk001=chk(False), chk004=chk(False), chk005=chk(True),
        )
        base.update(over)
        return NS(**base)

    reset()
    slot = make_slot(CurtainSlots, curtain_ui())
    slot._created = None
    slot.perform_operation([])  # nothing selected -> rail generated from the fields
    curtain = bpy.data.objects.get(slot._created or "")
    check("curtain slot builds from the generated rail",
          curtain is not None and len(curtain.data.vertices) > 100,
          f"created={slot._created}")
    xs = [v.co.x for v in curtain.data.vertices]
    check("curtain spans the dialed width",
          abs(min(xs) + 3.0) < 0.5 and abs(max(xs) - 3.0) < 0.5,
          f"x {min(xs):.2f}..{max(xs):.2f}")

    bpy.ops.object.select_all(action="DESELECT")
    slot._finalize()  # Select Result
    check("curtain slot Select Result selects the curtain",
          bpy.context.view_layer.objects.active == curtain
          and curtain.select_get())

    reset()
    bpy.ops.curve.primitive_bezier_curve_add()
    curve = bpy.context.active_object
    slot = make_slot(CurtainSlots, curtain_ui())
    slot._created = None
    slot.perform_operation([curve])  # selected curve becomes the rail
    curtain = bpy.data.objects.get(slot._created or "")
    check("curtain slot drapes from a selected curve",
          curtain is not None and len(curtain.data.vertices) > 100)

except Exception:
    traceback.print_exc()
    lines.append("FAIL unhandled exception")

print("\n".join(lines))
ok = all(l.startswith("OK") for l in lines) and lines
print(f"===RESULT: {'PASS' if ok else 'FAIL'}=== ({sum(1 for l in lines if l.startswith('OK'))}/{len(lines)})")
