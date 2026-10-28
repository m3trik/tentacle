"""Manual harness for the deepened (stub → real) Blender slots across domains.

Covers the implementations that replaced deferred-message stubs once their Blender primitive
existed: selection list000 (select-by-type), transform cmb002 (object.align), normals b002 +
uv b000 (Data-Transfer), uv b003/b004 (texel density), uv b029 (pin toggle), uv tb022 (cut
hard edges), polygons b043 (interactive target weld), animation
tb002/tb004/tb007/tb008 (key spacing / transfer / align / visibility keys), transform
chk024/chk025 (constraints -> snap elements), selection b002-b007 (one-shot constraints),
rigging cmb002 (Rigify quick rig), nurbs b056 (image tracer), the manager-panel routing,
main list000 (workspace browser = the current .blend's sub-folders, as Maya's tree),
editors buttons + list (every entry opens a real editor; no-analogue buttons relabel).

Requires a real Blender binary (it ``import bpy``), so it is **not** a CI/unittest target — the
``blender/`` subdir and the non-``test_`` name keep it out of auto-discovery. Run it against a
*fresh* Blender (never an existing session)::

    blender --background --factory-startup --python tentacle/test/blender/deepened_slots_check.py
"""
import contextlib
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


def make_slot(cls, **attrs):
    """Instance without the UI-loading __init__ (headless: no loaded_ui)."""
    slot = cls.__new__(cls)
    slot.sb = NS(message_box=lambda *a, **k: None)
    for k, v in attrs.items():
        setattr(slot, k, v)
    return slot


def reset():
    import bpy

    if bpy.context.view_layer.objects.active and bpy.context.view_layer.objects.active.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    bpy.ops.object.select_all(action="DESELECT")
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)


def add_cube(name, location=(0, 0, 0)):
    import bpy

    bpy.ops.mesh.primitive_cube_add(location=location)
    o = bpy.context.active_object
    o.name = name
    return o


def option_box(**widgets):
    return NS(option_box=NS(menu=NS(**widgets)))


def chk(state):
    return NS(isChecked=lambda s=state: s)


def spin(v):
    return NS(value=lambda v=v: v)


def combo(data):
    return NS(currentData=lambda d=data: d)


try:
    import bpy
    import bmesh
    from tentacle import tcl_blender  # noqa: F401 — provisions Qt (qtpy/PySide6) for the slot imports
    from tentacle.slots.selection import SelectionSlots  # composed: both hosts, over sb.tk
    from tentacle.slots.transform import TransformSlots  # composed: over sb.tk
    from tentacle.slots.normals import NormalsSlots  # composed: both hosts, over sb.tk
    from tentacle.slots.polygons import PolygonsSlots  # composed: both hosts, over sb.tk
    from tentacle.slots.uv import UvSlots  # composed: both hosts, over sb.tk
    from tentacle.slots.animation import AnimationSlots  # composed: both hosts, over sb.tk
    import blendertk as btk

    # ---- selection list000: select by type --------------------------------------------------
    reset()
    add_cube("M")
    bpy.ops.object.empty_add(type="PLAIN_AXES")
    # Labels must be real _SELECTION_CONFIG leaves (what the list actually offers) — the old
    # flat-type labels ("Mesh"/"Empty") raise ValueError and no-op, passing only vacuously.
    # list000 reads its scope from the submenu's tb004 option box (all / selected / visible).
    slot = make_slot(SelectionSlots, sb=NS(message_box=lambda *a, **k: None, tk=btk),
                     submenu=NS(tb004=NS(menu=NS(
        cmb_bytype_scope=combo("all"), cmb_bytype_mode=combo("replace")))))
    slot.list000(NS(item_text=lambda: "Polygon Meshes", sublist=None, objectName=lambda: ""))
    sel = [o.name for o in bpy.context.selected_objects]
    check("selection list000 'Polygon Meshes' selects only meshes", sel == ["M"], f"sel={sel}")
    slot.list000(NS(item_text=lambda: "Locators", sublist=None, objectName=lambda: ""))
    sel = [o.type for o in bpy.context.selected_objects]
    check("selection list000 'Locators' selects the empty", sel == ["EMPTY"], f"sel={sel}")

    # ---- transform cmb002: align to active --------------------------------------------------
    reset()
    a = add_cube("A", (5, 1, 2))
    b = add_cube("B", (0, 0, 0))  # active
    a.select_set(True)
    slot = make_slot(TransformSlots, sb=NS(message_box=lambda *a, **k: None, tk=btk))
    items = list(btk.XformUtils.ALIGN_MODES)
    slot.cmb002(items.index("Align X to Active"), NS(items=items))
    bpy.context.view_layer.update()
    check("transform cmb002 aligns X to active",
          abs(a.location.x - b.location.x) < 1e-4 and abs(a.location.y - 1) < 1e-4,
          f"a={tuple(a.location)}")

    # ---- normals b002: data transfer ---------------------------------------------------------
    # (uv b000's UV pass moved with the Transfer tool to the shared Texture Combine panel's
    # Transfer mode; blendertk's test_texture_combine drives the engine on real geometry.)
    reset()
    src = add_cube("Src")
    tgt = add_cube("Tgt", (3, 0, 0))
    src.select_set(True)
    tgt.select_set(True)
    bpy.context.view_layer.objects.active = src

    slot = make_slot(NormalsSlots)
    slot.sb.tk = btk  # a composed Slots class reaches its host through Slots.tk
    slot.b002()
    check("normals b002 transfers custom split normals", tgt.data.has_custom_normals)

    # ---- uv b003/b004: texel density via the cmb003/s003 inputs ------------------------------
    reset()
    bpy.ops.mesh.primitive_plane_add(size=1.0)  # unit plane: density == map size
    readout = {}
    ui = NS(cmb003=NS(currentText=lambda: "1024"),
            s003=NS(value=lambda: 512.0, setValue=lambda v: readout.__setitem__("d", v)))
    slot = make_slot(UvSlots, ui=ui, sb=NS(message_box=lambda *a, **k: None, tk=btk))
    slot.b003()
    check("uv b003 reads density into s003", abs(readout.get("d", 0) - 1024.0) < 1e-3,
          f"d={readout.get('d')}")
    slot.b004()  # set to s003.value()=512 against map 1024
    o = bpy.context.active_object
    check("uv b004 sets density from s003", abs(btk.get_texel_density(o, 1024) - 512.0) < 1e-3,
          f"d={btk.get_texel_density(o, 1024):.3f}")

    # ---- uv b029: pin dual-state toggle ------------------------------------------------------
    def pin_count(obj):
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        uvl = bm.loops.layers.uv.active
        n = sum(1 for f in bm.faces for loop in f.loops if loop[uvl].pin_uv)
        bm.free()
        return n

    slot = make_slot(UvSlots, ui=ui, sb=NS(message_box=lambda *a, **k: None, tk=btk))
    slot.b029(None)
    pinned_after_first = pin_count(o)
    slot.b029(None)
    check("uv b029 toggle: pin then unpin",
          pinned_after_first == 4 and pin_count(o) == 0,
          f"first={pinned_after_first} second={pin_count(o)}")

    # ---- uv tb022: cut hard edges -------------------------------------------------------------
    reset()
    o = add_cube("Hard")  # every cube edge is 90 degrees
    slot = make_slot(UvSlots, ui=ui, sb=NS(message_box=lambda *a, **k: None, tk=btk))
    slot.tb022(option_box(
        s017=spin(70.0), s018=spin(180.0), chk025=chk(False), chk026=chk(False)
    ))
    seams = sum(1 for e in o.data.edges if e.use_seam)
    check("uv tb022 seams all 12 sharp cube edges", seams == 12, f"seams={seams}")

    # (uv cmb002 / tb005 / tb006 / tb008 moved to the shared shell_xform tool — the
    # tentacle Uv slot only launches it now; see slots/tools/shell_xform.py.)

    # ---- polygons b043: interactive target weld -----------------------------------------------
    # The tool needs a windowed viewport for its modal loop; headless the slot must register
    # the operator, refuse cleanly (RuntimeError -> message_box), and not raise.
    ts = bpy.context.scene.tool_settings
    slot = make_slot(PolygonsSlots, sb=NS(message_box=lambda *a, **k: None, tk=btk))
    slot.b043()  # headless has no 3D viewport — must not raise (slot catches + messages)
    check("polygons b043 target-weld activation is safe headless", True)
    check("polygons b043 registers the modal operator",
          hasattr(bpy.types, "BTK_OT_target_weld"))

    # ---- transform chk021-023: increment snap, live per toggle ---------------------------------
    # Each toggle re-inits the panel's tb004 option box (gates its increment spinbox).
    _spin = NS(setEnabled=lambda state: None)
    slot = make_slot(TransformSlots, sb=NS(message_box=lambda *a, **k: None, tk=btk),
                     ui=NS(tb004=NS(init_slot=lambda: None,
                                    option_box=NS(menu=NS(s021=_spin, s022=_spin, s023=_spin)))))
    slot.chk022(False, None)
    slot.chk021(True, None)
    move_on = ts.use_snap and ts.use_snap_translate and not ts.use_snap_scale
    slot.chk023(True, None)
    rot_on = ts.use_snap_rotate
    slot.chk021(False, None)
    slot.chk023(False, None)
    check("transform tb004/chk023 drive tool-settings snap",
          move_on and rot_on and not ts.use_snap,
          f"move={move_on} rot={rot_on} off={not ts.use_snap}")

    # ---- crease b002: transfer crease (Data-Transfer CREASE) ----------------------------------
    reset()
    src = add_cube("CSrc")
    tgt = add_cube("CTgt", (3, 0, 0))
    from tentacle.slots.crease import CreaseSlots

    cslot = make_slot(CreaseSlots, sb=NS(message_box=lambda *a, **k: None, tk=btk))
    btk.crease_edges(src, amount=10)  # full crease on every edge (object mode)
    src.select_set(True)
    tgt.select_set(True)
    bpy.context.view_layer.objects.active = src
    cslot.b002(None)
    crease_attr = tgt.data.attributes.get("crease_edge")
    creased = (
        sum(1 for d in crease_attr.data if d.value > 0.99) if crease_attr else 0
    )
    check("crease b002 transfers edge creases", creased == 12, f"creased={creased}")

    # ---- subdivision b028: quad draw = poly build tool ----------------------------------------
    from tentacle.slots.subdivision import SubdivisionSlots

    sslot = make_slot(SubdivisionSlots, sb=NS(message_box=lambda *a, **k: None, tk=btk))
    sslot.b028()  # headless has no tool context — must not raise (slot catches + messages)
    check("subdivision b028 poly-build activation is safe headless", True)

    # ---- animation tb002/tb004/tb007/tb008 ----------------------------------------------------
    reset()
    a = add_cube("A")
    b = add_cube("B", (3, 0, 0))

    def key_obj(o, frames):
        for f in frames:
            o.location.x = float(f)
            o.keyframe_insert(data_path="location", index=0, frame=f)

    def key_times(o):
        return sorted(k.co.x for fc in btk.get_fcurves(o) for k in fc.keyframe_points)

    key_obj(a, (10, 20))
    a.select_set(True)
    b.select_set(True)
    bpy.context.view_layer.objects.active = a

    # The composed class reaches Blender through sb.tk; tb019 reports progress.
    slot = make_slot(AnimationSlots, _copied=None, _copied_frame=None)
    slot.sb = NS(
        message_box=lambda *a, **k: None,
        tk=btk,
        progress=contextlib.contextmanager(lambda **_kw: (yield lambda *a, **k: True)),
        progress_adapter=lambda update: update,
    )
    # shift keys >= absolute frame 15 by +5 (chk004 Relative off; selected-objects scope)
    slot.tb002(option_box(s002=spin(15), s003=spin(5), chk004=chk(False), chk003=chk(True),
                          cmb036=combo("objects"), chk021=chk(False)))
    check("animation tb002 adjusts spacing", key_times(a) == [10.0, 25.0], f"{key_times(a)}")

    slot.tb004(option_box(chk006=chk(True), chk007=chk(True), chk035=chk(False)))  # a -> b
    check("animation tb004 transfers keys to targets",
          key_times(b) == key_times(a)
          and b.animation_data.action is not a.animation_data.action,
          f"b={key_times(b)}")

    # add intermediates: 11..24 sampled in (Percent=100 -> every interior frame)
    slot.tb005(option_box(s021=spin(-1), s006=spin(-1), s007=spin(100),
                          chk028=chk(False), chk027=chk(False)))
    check("animation tb005 adds intermediate keys", len(key_times(a)) == 16,
          f"n={len(key_times(a))}")
    slot.tb005(option_box(s021=spin(-1), s006=spin(-1), s007=spin(100),
                          chk028=chk(False), chk027=chk(True)))  # remove -> endpoints only
    check("animation tb005 remove keeps endpoints", key_times(a) == [10.0, 25.0],
          f"{key_times(a)}")

    slot.tb013(option_box(cmb041=combo("range"), chk039=chk(False), chk034=chk(False),
                          s012=spin(20), s013=spin(30)))
    sel = [k.co.x for fc in btk.get_fcurves(a) for k in fc.keyframe_points
           if k.select_control_point]
    check("animation tb013 selects keys in range", sel == [25.0], f"sel={sel}")

    # Each object's selected keys move as ONE block, spacing kept, so every object's
    # selection starts on one frame (btk.align_selected_keyframes, mirror of mtk's). A's
    # selection starts at 10, B's (its key at 25 alone) at 25; Use Earliest Frame off
    # elects the latest start.
    for k in [k for fc in btk.get_fcurves(a) for k in fc.keyframe_points]:
        k.select_control_point = True
    for k in [k for fc in btk.get_fcurves(b) for k in fc.keyframe_points]:
        k.select_control_point = k.co.x == 25.0
    b_before = key_times(b)
    slot.tb007(option_box(chk013=chk(False), spn000=spin(-1)))
    check("animation tb007 aligns each object's selected keys as one block",
          key_times(a) == [25.0, 40.0] and 25.0 in b_before and key_times(b) == b_before,
          f"a={key_times(a)} b={b_before}->{key_times(b)}")

    # The key edits carry the shot claims of the keys they touch (BACKLOG
    # 2026-10-04): a key one REPLACES takes its claims with it, a key one MOVES
    # carries them along -- left behind, a fade's claim passed to whatever key
    # arrived on its frame, and the next Build deleted that animator key. Twin
    # of tentacle/test/test_animation.py::TestAlignInvertReleaseShotClaims.
    claims = btk.BlenderShotStore()
    btk.BlenderShotStore.set_active(claims)
    try:
        def claimed(name, frames=(10, 20, 30), at=20.0, path="location"):
            o = add_cube(name, (6, 0, 0))
            key_obj(o, frames)
            key = btk.BlenderShotStore.curve_key(o.name, path, 0)
            if at is not None:
                claims.edit_ledger.record_authored(key, at, 0, "fade_in", o.name)
            bpy.ops.object.select_all(action="DESELECT")
            o.select_set(True)
            bpy.context.view_layer.objects.active = o
            return o, key

        def claimed_at(o):
            return [round(t, 3) for _k, t in claims.edit_ledger.authored(obj=o.name)]

        def select_keys(o, *frames):
            for k in [k for fc in btk.get_fcurves(o) for k in fc.keyframe_points]:
                k.select_control_point = any(abs(k.co.x - f) < 1e-3 for f in frames)

        c, c_key = claimed("ClaimAlign")
        select_keys(c, 10)
        slot.tb007(option_box(chk013=chk(True), spn000=spin(20)))
        check("animation tb007 releases the shot claims of the key it lands on",
              key_times(c) == [20.0, 30.0]
              and not claims.edit_ledger.owns_any(c_key, 20.0),
              f"{key_times(c)} {claims.edit_ledger.to_dict()}")

        def invert(time_value):
            slot.tb001(option_box(cmb035=combo("horizontal"), s001=spin(time_value),
                                  d000=spin(0.0), chk002=chk(False), chk005=chk(False)))

        # The reversed copy at 0 (absolute): t' = 30 - t, so 10's copy lands on 20.
        d, d_key = claimed("ClaimInvert")
        invert(0)
        check("animation tb001 releases the shot claims of the key its copy lands on",
              key_times(d) == [0.0, 10.0, 20.0, 30.0]
              and not claims.edit_ledger.owns_any(d_key, 20.0),
              f"{key_times(d)} {claims.edit_ledger.to_dict()}")

        # In place (Time = Auto): {10, 15, 25, 30} with a fade claimed at 15.
        e, _e_key = claimed("ClaimMoved", (10, 15, 25, 30), at=15.0)
        invert(-1)
        check("animation tb001 carries a moved key's shot claims to its new frame",
              claimed_at(e) == [25.0], f"{key_times(e)} {claims.edit_ledger.to_dict()}")

        f_obj, _f_key = claimed("ClaimSpacing", (1, 10), at=10.0)
        slot.tb002(option_box(s003=spin(5), s002=spin(6), chk004=chk(False),
                              chk003=chk(False), cmb036=combo("objects"),
                              chk021=chk(False)))
        check("animation tb002 carries the shot claims of the keys it moves",
              claimed_at(f_obj) == [15.0], f"{key_times(f_obj)}")

        src = add_cube("XferSource", (6, 0, 0))
        key_obj(src, (1, 10))
        src_fc = btk.get_fcurves(src)[0]
        src_fc.keyframe_points[0].co.y = 0.0  # the source holds 0 at frame 1
        src_fc.update()
        tgt, tgt_key = claimed("XferTarget", (1, 10), at=1.0)  # the target holds 1
        src.select_set(True)
        bpy.context.view_layer.objects.active = src
        slot.tb004(option_box(chk006=chk(False), chk007=chk(True), chk035=chk(False)))
        xo_src, xo_key = claimed("XferOptSource", (0, 10, 20, 30), at=10.0)
        for kp, v in zip(btk.get_fcurves(xo_src)[0].keyframe_points, (1.0, 1.0, 1.0, 5.0)):
            kp.co.y = v  # 0..20 a flat run: the optimize drops 10
        btk.get_fcurves(xo_src)[0].update()
        xo_tgt = add_cube("XferOptTarget", (6, 0, 0))
        key_obj(xo_tgt, (0, 5))
        bpy.ops.object.select_all(action="DESELECT")
        xo_tgt.select_set(True)
        xo_src.select_set(True)
        bpy.context.view_layer.objects.active = xo_src
        slot.tb004(option_box(chk006=chk(False), chk007=chk(True), chk035=chk(True)))
        check("animation tb004 (optimize) releases the claims of the source keys it drops",
              not claims.edit_ledger.owns_any(xo_key, 10.0),
              f"{key_times(xo_src)} {claims.edit_ledger.to_dict()}")
        check("animation tb004 releases the claims of a target key it replaces",
              not claims.edit_ledger.owns_any(tgt_key, 1.0), f"{key_times(tgt)}")

        g, g_key = claimed("ClaimMoveKeys", (1, 5, 10), at=5.0)
        select_keys(g, 1)
        bpy.context.scene.frame_set(5)
        slot.tb006(option_box(chk012=chk(False), chk031=chk(True), chk033=chk(False),
                              cmb_align=combo("start")))
        check("animation tb006 releases the shot claims of the key it lands on",
              key_times(g) == [5.0, 10.0] and not claims.edit_ledger.owns_any(g_key, 5.0),
              f"{key_times(g)}")

        h, _h_key = claimed("ClaimVis", (1, 10), at=None)
        for vis_path in ("hide_viewport", "hide_render"):
            setattr(h, vis_path, False)
            h.keyframe_insert(vis_path, frame=1)
        h_key = btk.BlenderShotStore.curve_key(h.name, "hide_viewport", 0)
        claims.edit_ledger.record_authored(h_key, 1.0, 0, "fade_in", h.name)
        bpy.context.scene.frame_set(1)
        slot.tb008(option_box(cmb_visibility=NS(currentText=lambda: "Hidden"),
                              cmb002=combo("current"), s008=spin(0), chk016=chk(False)))
        check("animation tb008 releases the claims of a visibility key it replaces",
              not claims.edit_ledger.owns_any(h_key, 1.0), f"{claims.edit_ledger.to_dict()}")

        i, i_key = claimed("ClaimSnap", (1, 10), at=None)
        btk.get_fcurves(i)[0].keyframe_points.insert(4.4, 4.0)
        claims.edit_ledger.record_authored(i_key, 4.4, 0, "fade_in", i.name)
        slot.tb009(option_box(chk017=chk(False), chk018=chk(False),
                              cmb003=combo("nearest")))
        check("animation tb009 carries the shot claims of the keys it snaps",
              claimed_at(i) == [4.0], f"{key_times(i)} {claims.edit_ledger.to_dict()}")

        j, j_key = claimed("ClaimPaste", (1, 10, 20), at=10.0)
        select_keys(j, 20)
        slot._copied = btk.copy_keys(j, mode="selected")
        slot._copied_frame = 10.0
        bpy.context.scene.frame_set(10)
        slot.tb018(option_box(cmb039=combo("playhead")))
        check("animation tb018 releases the shot claims of a key it pastes over",
              not claims.edit_ledger.owns_any(j_key, 10.0), f"{key_times(j)}")

        k_obj, _k_key = claimed("ClaimScale", (0, 10), at=10.0)
        slot.tb014(option_box(cmb014=combo("uniform"),
                              cmb_scale_pivot=combo("first_key"),
                              chk_channel_box=chk(False),
                              d001=spin(2.0),
                              cmb_scale_mode=NS(currentText=lambda: "Relative"),
                              cmb033=combo("single_group"), cmb034=combo("none"),
                              s014=spin(64), chk_split_static=chk(False),
                              chk_merge_touching=chk(False)))
        check("animation tb014 carries the shot claims of the keys it scales",
              claimed_at(k_obj) == [20.0], f"{key_times(k_obj)}")

        # Stagger's Start Frame override re-times one object: 5..15 -> 20..30.
        m_obj, _m_key = claimed("ClaimStagger", (5, 15), at=15.0)
        slot.tb003(option_box(s005=spin(20), s004=spin(0), chk025=chk(False),
                              chk008=chk(False), chk014=chk(False),
                              chk029=chk(False), chk009=chk(False), chk024=chk(False)))
        check("animation tb003 carries the shot claims of the keys it staggers",
              claimed_at(m_obj) == [30.0], f"{key_times(m_obj)}")

        # A deleted key takes its claims with it, as a replaced one does.
        n_obj, n_key = claimed("ClaimDelete", (1, 10, 20), at=10.0)
        bpy.context.scene.frame_set(10)
        slot.tb010(option_box(cmb004=combo("current"), chk020=chk(False)))
        check("animation tb010 releases the shot claims of the keys it deletes",
              key_times(n_obj) == [1.0, 20.0]
              and not claims.edit_ledger.owns_any(n_key, 10.0),
              f"{key_times(n_obj)} {claims.edit_ledger.to_dict()}")
        _o_obj, o_key = claimed("ClaimClear", (1, 10, 20), at=10.0)
        slot.tb010(option_box(cmb004=combo("all"), chk020=chk(False)))
        check("animation tb010 (all) releases the claims of the animation it clears",
              not claims.edit_ledger.owns_any(o_key, 10.0),
              f"{claims.edit_ledger.to_dict()}")
        p_obj, p_key = claimed("ClaimThin", (1, 10, 20), at=10.0)
        slot.tb005(option_box(s021=spin(-1), s006=spin(-1), s007=spin(100),
                              chk028=chk(False), chk027=chk(True)))
        check("animation tb005 remove releases the shot claims of the keys it deletes",
              key_times(p_obj) == [1.0, 20.0]
              and not claims.edit_ledger.owns_any(p_key, 10.0),
              f"{key_times(p_obj)} {claims.edit_ledger.to_dict()}")

        sc = bpy.context.scene
        frame_range = sc.frame_start, sc.frame_end
        sc.frame_start, sc.frame_end = 1, 30
        q_obj, q_key = claimed("ClaimUntie", (5, 10), at=None)
        btk.tie_keyframes([q_obj])  # bookends at 1 and 30
        claims.edit_ledger.record_authored(q_key, 30.0, 0, "fade_out", q_obj.name)
        slot.tb011(option_box(cmb_tie=NS(currentText=lambda: "Untie"),
                              chk023=chk(False)))
        check("animation tb011 untie releases the claims of the bookends it deletes",
              key_times(q_obj) == [5.0, 10.0]
              and not claims.edit_ledger.owns_any(q_key, 30.0),
              f"{key_times(q_obj)} {claims.edit_ledger.to_dict()}")
        sc.frame_start, sc.frame_end = frame_range

        r_obj, r_key = claimed("ClaimOptimize", (0, 10, 20, 30), at=10.0)
        r_fc = btk.get_fcurves(r_obj)[0]
        for kp, v in zip(r_fc.keyframe_points, (1.0, 1.0, 1.0, 5.0)):
            kp.co.y = v  # 0..20 a flat run: 10 is its redundant interior
        r_fc.update()
        r_obj.location.y = 3.0
        for f in (0, 10):
            r_obj.keyframe_insert(data_path="location", index=1, frame=f)  # static
        ry_key = btk.BlenderShotStore.curve_key(r_obj.name, "location", 1)
        claims.edit_ledger.record_authored(ry_key, 0.0, 0, "fade_in", r_obj.name)
        slot.tb019(option_box(chk000=chk(True), chk030=chk(True), chk032=chk(False),
                              chk040=chk(False), d017=spin(0.001)))
        check("animation tb019 releases the claims of the keys and curves it deletes",
              not claims.edit_ledger.owns_any(r_key, 10.0)
              and not claims.edit_ledger.owns_any(ry_key, 0.0),
              f"{key_times(r_obj)} {claims.edit_ledger.to_dict()}")

        s_obj, s_key = claimed("ClaimRepair", (1, 10, 20), at=1.0)
        btk.get_fcurves(s_obj)[0].keyframe_points[0].co.y = 1e9
        slot.tb015(option_box(chk036=chk(False), chk037=chk(True), chk038=chk(True),
                              d015=spin(1e6), d016=spin(1e6)))
        check("animation tb015 releases the claims of the keys it deletes",
              key_times(s_obj) == [10.0, 20.0]
              and not claims.edit_ledger.owns_any(s_key, 1.0),
              f"{key_times(s_obj)} {claims.edit_ledger.to_dict()}")

        # Undo pairing: with claims the edit is the store's scene_edit, one undo
        # step whose restore point (taken BEFORE it) brings the released claim
        # back -- the STORE applies it when Blender undoes that step, no Shot
        # Sequencer open (BACKLOG 2026-10-05: with none, the claim stayed
        # released).  With no claims, no restore point at all.
        u, u_key = claimed("ClaimUndo")
        select_keys(u, 10)
        bpy.ops.ed.undo_push(message="before the align")
        depth = len(claims._boundary_undo)
        slot.tb007(option_box(chk013=chk(True), spn000=spin(20)))
        tag = claims.peek_boundary_tag()
        released = not claims.edit_ledger.owns_any(u_key, 20.0)
        bpy.ops.ed.undo()
        u = bpy.data.objects["ClaimUndo"]  # memfile undo replaced the object
        serial_back = btk.BlenderShotStore.edit_serial() != (tag or (None, None))[1]
        check("animation tb007 with claims: Blender's undo alone brings the released "
              "claim back",
              released and len(claims._boundary_undo) == depth
              and isinstance(tag, tuple) and tag[0] is True and serial_back
              and key_times(u) == [10.0, 20.0, 30.0]
              and claims.edit_ledger.owns_any(u_key, 20.0),
              f"tag={tag} serial={btk.BlenderShotStore.edit_serial()} "
              f"{key_times(u)} {claims.edit_ledger.to_dict()}")

        # A no-op Snap between pushes a step of its own in Blender (it cannot
        # tell keys that did not move from keys that did), so the Align takes a
        # second undo -- and its claims still come back.
        n_obj, n_key = claimed("ClaimNoop")
        select_keys(n_obj, 10)
        bpy.ops.ed.undo_push(message="before the align")
        slot.tb007(option_box(chk013=chk(True), spn000=spin(20)))
        slot.tb021(option_box(cmb042=combo("nearest")))  # every key is whole
        bpy.ops.ed.undo()
        bpy.ops.ed.undo()
        n_obj = bpy.data.objects["ClaimNoop"]
        check("animation tb007 then a no-op tb021: the undos still bring the claim back",
              key_times(n_obj) == [10.0, 20.0, 30.0]
              and claims.edit_ledger.owns_any(n_key, 20.0),
              f"{key_times(n_obj)} {claims.edit_ledger.to_dict()}")

        # TC-5: the repair-scoped Snap and Copy + Paste carry claims too.
        w, w_key = claimed("ClaimSnapFrac", (1, 10), at=None)
        btk.get_fcurves(w)[0].keyframe_points.insert(4.4, 4.0)
        claims.edit_ledger.record_authored(w_key, 4.4, 0, "fade_in", w.name)
        slot.tb021(option_box(cmb042=combo("nearest")))
        check("animation tb021 carries the shot claims of the keys it snaps",
              claimed_at(w) == [4.0], f"{key_times(w)} {claims.edit_ledger.to_dict()}")

        tgt_cp, tgt_cp_key = claimed("ClaimCopyPaste", (1, 10, 20), at=10.0)
        src_cp = add_cube("CopyPasteSource", (8, 0, 0))
        for f, v in ((1, 0.0), (10, 99.0)):
            src_cp.location.x = v
            src_cp.keyframe_insert(data_path="location", index=0, frame=f)
        tgt_cp.select_set(True)
        src_cp.select_set(True)
        bpy.context.view_layer.objects.active = src_cp
        # Copy + Paste captures the active object (its picked keys, else its pose)
        # and pastes it at the playhead onto the selection: 10 is replaced.
        bpy.context.scene.frame_set(10)
        slot.tb012(option_box(cmb038=combo("copy_paste")))
        check("animation tb012 (Copy + Paste) releases the claims of a key it replaces",
              not claims.edit_ledger.owns_any(tgt_cp_key, 10.0),
              f"{key_times(tgt_cp)} {claims.edit_ledger.to_dict()}")

        bare = btk.BlenderShotStore()
        btk.BlenderShotStore.set_active(bare)
        v, _v_key = claimed("NoClaims", at=None)
        select_keys(v, 10)
        slot.tb007(option_box(chk013=chk(True), spn000=spin(20)))
        check("animation tb007 with no claims pushes no restore point",
              key_times(v) == [20.0, 30.0] and not bare.has_boundary_snapshot(),
              f"{key_times(v)}")
    finally:
        btk.BlenderShotStore.clear_active()
        bpy.ops.object.select_all(action="DESELECT")  # A and B, as tb008 expects
        a = bpy.data.objects["A"]  # an undo above may have replaced them
        b = bpy.data.objects["B"]
        a.select_set(True)
        b.select_set(True)
        bpy.context.view_layer.objects.active = a

    # key hidden at current frame
    slot.tb008(option_box(cmb_visibility=NS(currentText=lambda: "Hidden"),
                          cmb002=combo("current"), s008=spin(0), chk016=chk(False)))
    vis = [fc.data_path for fc in btk.get_fcurves(a) if fc.data_path.startswith("hide_")]
    check("animation tb008 keys visibility", sorted(vis) == ["hide_render", "hide_viewport"]
          and a.hide_render, f"vis={vis}")

    # ---- transform b002 Un-Freeze (restore_transforms round trip through the slot)
    reset()
    o = add_cube("Frozen", location=(4, 0, 0))
    o.select_set(True)
    bpy.context.view_layer.objects.active = o
    btk.freeze_transforms(o, location=True, rotation=False, scale=False)
    slot = make_slot(TransformSlots, sb=NS(message_box=lambda *a, **k: None, tk=btk))
    # b002 reads which channels to restore (and whether to walk children) from its option box.
    unfreeze = option_box(
        chk_unfreeze_t=chk(True),
        chk_unfreeze_r=chk(True),
        chk_unfreeze_s=chk(True),
        chk_unfreeze_children=chk(False),
    )
    slot.b002(unfreeze)
    check("transform b002 un-freezes (location restored)",
          abs(o.location.x - 4.0) < 1e-4, f"x={o.location.x:.3f}")
    msgs = []
    slot.sb = NS(message_box=msgs.append, tk=btk)
    slot.b002(unfreeze)  # bakes consumed -> nothing-to-restore message
    check("transform b002 reports when nothing stored",
          msgs and "Nothing to restore" in msgs[-1])

    # ---- transform tb001 Scale Connected Edges (slot reads option-box s001)
    reset()
    o = add_cube("Edges")
    o.select_set(True)
    bpy.context.view_layer.objects.active = o
    bpy.ops.object.mode_set(mode="EDIT")
    import bmesh as _bmesh

    bm = _bmesh.from_edit_mesh(o.data)
    for e in bm.edges:
        e.select = all(abs(v.co.z - 1.0) < 1e-4 for v in e.verts)  # top ring only
    _bmesh.update_edit_mesh(o.data)
    slot = make_slot(TransformSlots, sb=NS(message_box=lambda *a, **k: None, tk=btk))
    slot.tb001(option_box(s001=spin(2.0)))
    bm = _bmesh.from_edit_mesh(o.data)
    top_x = sorted(round(v.co.x, 2) for v in bm.verts if abs(v.co.z - 1.0) < 1e-4)
    check("transform tb001 scales the selected ring", top_x == [-2.0, -2.0, 2.0, 2.0],
          f"{top_x}")
    bpy.ops.object.mode_set(mode="OBJECT")
    msgs = []
    slot.sb = NS(message_box=msgs.append, tk=btk)
    slot.tb001(option_box(s001=spin(2.0)))  # object mode -> nothing scaled message
    check("transform tb001 reports when nothing scaled",
          msgs and "No connected edges" in msgs[-1])

    # ---- polygons b000/b053 extension wrap: factory startup has no LoopTools ->
    #      the wrap-if-present path must point at the extension, not crash
    from tentacle.slots.polygons import PolygonsSlots

    reset()
    msgs = []
    slot = make_slot(PolygonsSlots)
    slot.sb = NS(message_box=msgs.append, tk=btk)
    slot.b000()
    check("polygons b000 points at LoopTools when absent",
          msgs and "LoopTools" in msgs[-1], f"{msgs[-1:]}")
    slot.b053()
    check("polygons b053 points at the edge-flow add-on when absent",
          len(msgs) == 2 and "add-on" in msgs[-1], f"{msgs[-1:]}")

    # ---- polygons tb009 Snap Closest Verts (other mesh snaps onto the ACTIVE)
    reset()
    a = add_cube("A", location=(0.05, 0, 0))
    b = add_cube("B", location=(0, 0, 0))
    a.select_set(True)
    b.select_set(True)
    bpy.context.view_layer.objects.active = b
    slot = make_slot(PolygonsSlots, sb=NS(message_box=lambda *a, **k: None, tk=btk))
    slot.tb009(option_box(s005=spin(0.2), chk016=chk(True)))
    pos_a = sorted(tuple(round(c, 4) for c in (a.matrix_world @ v.co)) for v in a.data.vertices)
    pos_b = sorted(tuple(round(c, 4) for c in (b.matrix_world @ v.co)) for v in b.data.vertices)
    check("polygons tb009 snaps onto the active mesh", pos_a == pos_b)

    # ---- polygons b034 Wedge (edit mode, face + hinge edge)
    reset()
    import bmesh as _bm

    o = add_cube("W")
    o.select_set(True)
    bpy.context.view_layer.objects.active = o
    bpy.ops.object.mode_set(mode="EDIT")
    bm = _bm.from_edit_mesh(o.data)
    for f in bm.faces:
        f.select = False
    for e in bm.edges:
        e.select = False
    top = next(f for f in bm.faces if all(abs(v.co.z - 1.0) < 1e-4 for v in f.verts))
    top.select = True
    next(iter(top.edges)).select = True
    _bm.update_edit_mesh(o.data)
    f0 = len(bm.faces)
    slot = make_slot(PolygonsSlots, sb=NS(message_box=lambda *a, **k: None, tk=btk))
    slot.b034()
    bm = _bm.from_edit_mesh(o.data)
    check("polygons b034 wedges the selected face", len(bm.faces) > f0,
          f"{f0}->{len(bm.faces)}")
    bpy.ops.object.mode_set(mode="OBJECT")

    # ---- polygons b009 Collapse Component routes on the SELECTION, not the select mode
    #      (Maya parity: faces collapse each to a point, verts/edges merge at ONE center).
    #      Several modes on at once is Blender's multi-component: loose verts must merge.
    def collapse(select_mode, pick, grid=False):
        reset()
        if grid:  # 3x3 faces, 16 verts
            bpy.ops.mesh.primitive_plane_add()
            o = bpy.context.active_object
        else:
            o = add_cube("C")
        o.select_set(True)
        bpy.context.view_layer.objects.active = o
        bpy.ops.object.mode_set(mode="EDIT")
        if grid:
            bpy.ops.mesh.select_all(action="SELECT")
            bpy.ops.mesh.subdivide(number_cuts=2)
        bpy.context.tool_settings.mesh_select_mode = select_mode
        bpy.ops.mesh.select_all(action="DESELECT")
        bm = _bm.from_edit_mesh(o.data)
        bm.verts.ensure_lookup_table()
        pick(bm)
        bm.select_flush_mode()
        _bm.update_edit_mesh(o.data)
        make_slot(PolygonsSlots, sb=NS(message_box=lambda *a, **k: None, tk=btk)).b009()
        n = len(_bm.from_edit_mesh(o.data).verts)
        bpy.ops.object.mode_set(mode="OBJECT")
        return n

    def two_loose_verts(bm):
        a = bm.verts[0]
        far = max(bm.verts, key=lambda v: (v.co - a.co).length)  # opposite corner
        a.select = far.select = True

    def top_and_bottom(bm):
        for f in bm.faces:
            if abs(abs(f.normal.z) - 1.0) < 1e-4:
                f.select = True

    def two_corner_faces(bm):  # share no verts, so no mode can flush them together
        c = [(f.calc_center_median(), f) for f in bm.faces]
        min(c, key=lambda t: t[0].x + t[0].y)[1].select = True
        max(c, key=lambda t: t[0].x + t[0].y)[1].select = True

    def all_verts(bm):
        for v in bm.verts:
            v.select = True

    n = collapse((True, False, True), two_loose_verts)
    check("polygons b009 vert+face modes: loose verts merge at one center", n == 7, f"{n}")
    n = collapse((False, False, True), top_and_bottom)
    check("polygons b009 face mode: each face collapses to its own point", n == 2, f"{n}")
    n = collapse((True, False, True), two_corner_faces, grid=True)
    check("polygons b009 vert+face modes: each selected face collapses", n == 10, f"{n}")
    n = collapse((True, False, False), all_verts)
    check("polygons b009 vertex mode: every picked vert merges at one center", n == 1, f"{n}")

    # ---- display b013/b014: route to the co-located blendertk panels -------------------------
    # (b013 stopped being an inline toggle when the Exploded View panel shipped; the explode/
    # un-explode engine round-trip is covered by blendertk/test/test_wedge_snap_explode.py)
    from tentacle.slots.display import DisplaySlots

    reset()
    shown = []
    slot = make_slot(DisplaySlots, sb=NS(handlers=NS(marking_menu=NS(show=shown.append))))
    slot.b013()
    slot.b014()
    check("display b013/b014 open the exploded-view / color-id panels",
          shown == ["exploded_view", "color_id"], f"{shown}")

    # ---- materials b014: Remove Duplicate Materials merges, and says how many ----------------
    # (a baked pair needs no lightmap step: blendertk's LightmapBaker groups a duplicate's
    # atlas with the one it duplicates -- covered by blendertk/test/test_lightmap_baker.py)
    import blendertk as btk
    from tentacle.slots.materials import MaterialsSlots

    reset()
    told = []
    dup_img = bpy.data.images.new("DupCheck_BaseColor", 4, 4)
    dup_img.filepath_raw = "//DupCheck_BaseColor.png"
    for i, name in enumerate(("DupChkA", "DupChkB")):
        dup_mat = btk.create_mat("standard", name=f"{name}_mat")
        dup_mat.node_tree.nodes.new("ShaderNodeTexImage").image = dup_img
        btk.assign_mat(add_cube(name, (3 * i, 0, 0)), dup_mat)
    slot = make_slot(
        MaterialsSlots,
        sb=NS(message_box=told.append, tk=btk),
        _refresh_material_lists=lambda: None,
    )
    slot.b014()
    left = {bpy.data.objects[n].material_slots[0].material.name for n in ("DupChkA", "DupChkB")}
    check("materials b014 merges the duplicate and says how many, naming no lightmaps",
          len(left) == 1 and bool(told) and "<hl>1</hl>" in told[-1]
          and "lightmap" not in told[-1].lower(), f"{left} {told}")

    # ---- materials table hooks: rows, details (each issue), merge, delete, rename ------------
    # Mirror of tentacle/test/test_materials.py TestMaterialTableHooks (Maya).
    import pythontk as ptk

    reset()
    with ptk.TempArtifacts("tbl_mats", policy="scoped") as store:
        crate = bpy.data.images.new("TblCrate_BaseColor", 4, 4)
        crate.filepath_raw = os.path.join(store.dir_path(), "TblCrate_BaseColor.png")
        crate.file_format = "PNG"
        crate.save()
        wood = bpy.data.images.new("TblWood_BaseColor", 4, 4)
        wood.source = "FILE"
        wood.filepath = os.path.join(store.dir_path(), "gone", "TblWood_BaseColor.png")
        for i, (name, img) in enumerate((("TblCrateA", crate), ("TblCrateB", crate), ("TblWood", wood))):
            mat = btk.create_mat("standard", name=name)
            mat.node_tree.nodes.new("ShaderNodeTexImage").image = img
            btk.assign_mat(add_cube(f"{name}_geo", (3 * i, 0, 0)), mat)
        btk.create_mat("standard", name="TblOld")
        btk.create_mat("standard", name="TblKept").use_fake_user = True
        # Used only by a Geometry Nodes Set Material: no object slot carries it, yet
        # it is in use (deleting it from the Status column broke the node tree).
        gn_tree = bpy.data.node_groups.new("TblSetMaterial", "GeometryNodeTree")
        gn_tree.nodes.new("GeometryNodeSetMaterial").inputs["Material"].default_value = (
            btk.create_mat("standard", name="TblGeoNodes")
        )
        add_cube("TblGeoNodes_geo", (12, 0, 0)).modifiers.new("GN", "NODES").node_group = gn_tree
        slot = make_slot(
            MaterialsSlots,
            ui=NS(),
            sb=NS(message_box=lambda *a, **k: None, tk=btk),
            _refresh_material_lists=lambda *a, **k: None,
        )
        names = ["TblCrateA", "TblCrateB", "TblWood", "TblOld", "TblKept", "TblGeoNodes"]
        rows = {row["name"] for row in slot._material_rows()}
        details = slot._material_details(names)
        kinds = {n: (details[n]["issue"] or ("",))[0] for n in names}
        check("materials table: each material is a row, and the details flag what needs attention "
              "(a material only Geometry Nodes uses is in use)",
              set(names) <= rows
              and {k: v for k, v in kinds.items() if v}
              == {"TblCrateB": "duplicate", "TblWood": "missing", "TblOld": "unused"}
              and details["TblCrateB"]["issue"][2] == "TblCrateA"
              and (details["TblCrateA"]["users"], details["TblCrateA"]["textures"]) == (1, 1)
              and details["TblCrateA"]["type"] == "Principled BSDF",
              f"{kinds} {details.get('TblCrateA')}")
        for obj in bpy.data.objects:
            obj.select_set(obj.name == "TblCrateA_geo")
        selected = slot._selected_mat_names()
        merged = btk.MatUtils.merge_duplicate_materials({"TblCrateB": "TblCrateA"})
        btk.MatUtils.delete_mats(["TblOld"])
        slot._current = "TblWood"
        renamed = slot._rename_current("TblTimber")
        check("materials table: selection's materials, merge, delete and rename",
              selected == ["TblCrateA"] and merged == 1
              and "TblCrateB" not in bpy.data.materials
              and bpy.data.objects["TblCrateB_geo"].material_slots[0].material.name == "TblCrateA"
              and "TblOld" not in bpy.data.materials
              and renamed == "TblTimber" and slot._current_mat() == "TblTimber",
              f"{selected} {merged} {renamed}")

    # ---- display Template Selected (WIRE + non-render + non-select; re-click releases) --------
    reset()
    a = add_cube("TA")
    b = add_cube("TB", (3, 0, 0))
    a.select_set(True)
    b.select_set(True)
    slot = make_slot(DisplaySlots, sb=NS(message_box=lambda *a, **k: None, tk=btk))
    slot._template_selected()  # template both
    templated_ok = all(o.display_type == "WIRE" and o.hide_render and o.hide_select for o in (a, b))
    deselected = not any(o.select_get() for o in (a, b))  # hide_select deselects (verified live)
    slot._template_selected()  # nothing selected now -> release every templated object
    released_ok = all(
        not o.hide_select and not o.hide_render and o.display_type == "TEXTURED" for o in (a, b)
    )
    check("display Template Selected templates then releases",
          templated_ok and deselected and released_ok,
          f"templated={templated_ok} deselected={deselected} released={released_ok}")

    # ---- display Display Normals cycle Off->Face->Vertex->Off (Maya minus na Tangent) ---------
    # headless has no VIEW_3D area, so drive the state machine through a fake overlay
    ov = NS(show_face_normals=False, show_vertex_normals=False)
    fake_area = NS(spaces=NS(active=NS(overlay=ov)))
    # The library reads the viewports through CoreUtils (patched as the descriptors they are).
    _ga = vars(btk.CoreUtils)["get_areas"]
    _tr = vars(btk.CoreUtils)["tag_redraw"]
    btk.CoreUtils.get_areas = staticmethod(lambda *a, **k: [fake_area])
    btk.CoreUtils.tag_redraw = classmethod(lambda cls, *a, **k: 0)
    try:
        slot = make_slot(DisplaySlots, sb=NS(message_box=lambda *a, **k: None, tk=btk))
        m1 = slot._display_normals()
        s1 = (ov.show_face_normals, ov.show_vertex_normals)
        m2 = slot._display_normals()
        s2 = (ov.show_face_normals, ov.show_vertex_normals)
        m3 = slot._display_normals()
        s3 = (ov.show_face_normals, ov.show_vertex_normals)
        check("display normals cycles Off->Face->Vertex->Off",
              s1 == (True, False) and s2 == (False, True) and s3 == (False, False)
              and "Face" in m1 and "Vertex" in m2 and "Off" in m3,
              f"{s1}|{s2}|{s3}")
    finally:
        btk.CoreUtils.get_areas = _ga
        btk.CoreUtils.tag_redraw = _tr

    # ---- uv tb005/tb006/b030 (shell ops through the slot readers)
    from tentacle.slots.uv import UvSlots

    def uv_quads(rects, name="Q"):
        bm = _bm.new()
        uvl = bm.loops.layers.uv.new("UVMap")
        for n, (u0, v0, u1, v1) in enumerate(rects):
            x = n * 3.0
            verts = [bm.verts.new((x + dx, dy, 0.0)) for dx, dy in ((0, 0), (1, 0), (1, 1), (0, 1))]
            face = bm.faces.new(verts)
            for loop, (lu, lv) in zip(face.loops, ((u0, v0), (u1, v0), (u1, v1), (u0, v1))):
                loop[uvl].uv = (lu, lv)
        me = bpy.data.meshes.new(name)
        bm.to_mesh(me)
        bm.free()
        o = bpy.data.objects.new(name, me)
        bpy.context.collection.objects.link(o)
        o.select_set(True)
        bpy.context.view_layer.objects.active = o
        return o

    reset()
    o = uv_quads([(0.0, 0.0, 0.2, 0.2), (0.6, 0.6, 0.8, 0.8)])
    slot = make_slot(UvSlots, sb=NS(message_box=lambda *a, **k: None, tk=btk))
    stack_w = option_box(cmb020=combo("center"), s024=spin(1.0), chk047=chk(False))
    slot.b030(stack_w)  # stack
    snap_after_stack = btk.get_uv_coords([o])
    slot.b030(stack_w)  # unstack (same selection -> restore)
    check("uv b030 stack/unstack round-trips",
          btk.get_uv_coords([o])[o.name] != snap_after_stack[o.name]
          and round(btk.get_uv_coords([o])[o.name][0][0], 3) == 0.0)
    # Similar mode + Pin: a rotated twin is fitted onto the reference and pinned; the
    # second click restores positions AND pins (the snapshot carries them).
    reset()
    o = uv_quads([(0.0, 0.0, 0.2, 0.1), (0.5, 0.5, 0.7, 0.6)])
    bm = _bm.new()
    bm.from_mesh(o.data)
    bm.faces.ensure_lookup_table()
    uvl = bm.loops.layers.uv.active
    import math as _math
    for loop in bm.faces[1].loops:  # rotate the twin 37 deg about its center (0.6, 0.55)
        x, y = loop[uvl].uv.x - 0.6, loop[uvl].uv.y - 0.55
        a = _math.radians(37)
        loop[uvl].uv = (0.6 + x * _math.cos(a) - y * _math.sin(a), 0.55 + x * _math.sin(a) + y * _math.cos(a))
    bm.to_mesh(o.data)
    bm.free()
    slot = make_slot(UvSlots, sb=NS(message_box=lambda *a, **k: None, tk=btk))
    stack_w = option_box(cmb020=combo("similar"), s024=spin(1.0), chk047=chk(True))
    before = btk.get_uv_coords([o], pins=True)[o.name]
    slot.b030(stack_w)  # stack (similar + pin)
    after = btk.get_uv_coords([o], pins=True)[o.name]
    check("uv b030 similar mode fits the rotated twin onto the reference",
          all(round(after[i][0] - after[i + 4][0], 6) == 0 and round(after[i][1] - after[i + 4][1], 6) == 0
              for i in range(4)),
          f"{[(round(u, 3), round(v, 3)) for u, v, _ in after]}")
    check("uv b030 pin-after-stack pins the stacked shells", all(pin for _, _, pin in after))
    slot.b030(stack_w)  # unstack -> positions + pins restored
    check("uv b030 unstack restores positions and pins",
          btk.get_uv_coords([o], pins=True)[o.name] == before)

    # (uv tb005 Straighten / tb006 Distribute moved to the shared shell_xform tool with
    # the rest of the transform cluster — no longer tentacle Uv slot methods.)

    # ---- scene b005: routes to the blendertk Naming panel; cameras b007 fails soft headless --
    # (b005 stopped driving the native Batch Rename op when the Naming panel shipped.)
    from tentacle.slots.scene import SceneSlots
    from tentacle.slots.cameras import CamerasSlots

    reset()
    shown = []
    slot = make_slot(SceneSlots, sb=NS(handlers=NS(marking_menu=NS(show=shown.append))))
    slot.b005()
    check("scene b005 opens the naming panel", shown == ["naming"], f"{shown}")

    msgs = []
    slot = make_slot(CamerasSlots)
    slot.sb = NS(message_box=msgs.append, tk=btk)
    slot.b007()  # nothing selected after reset(): one message, no error
    check("cameras b007 fails soft headless (one message)", len(msgs) == 1, f"{msgs}")

    # ---- transform chk024/chk025: constraints -> snap-to-element ---------------------------
    reset()
    ts = bpy.context.scene.tool_settings
    ts.use_snap = False
    slot = make_slot(TransformSlots, sb=NS(message_box=lambda *a, **k: None, tk=btk),
                     ui=NS(tb003=NS(init_slot=lambda: None)))
    elements, individual = btk.XformUtils._snap_elements, btk.XformUtils._snap_individual
    slot.chk024(True, None)
    check("transform chk024 enables EDGE snap",
          ts.use_snap and ts.use_snap_translate and elements() == {"EDGE"},
          f"snap={ts.use_snap} elems={elements()}")
    slot.chk025(True, None)  # single-element like Maya: surface replaces edge
    check("transform chk025 replaces with FACE snap",
          ts.use_snap and elements() == {"FACE"},
          f"elems={elements()}")
    slot.chk025(False, None)
    check("transform constraint off disables snap", not ts.use_snap)

    # ---- transform chk026: Make Live -> FACE_NEAREST face-projection snap ------------------
    ts.use_snap = False
    slot.chk026(True, None)
    check("transform chk026 (Make Live) enables FACE_NEAREST projection snap",
          ts.use_snap and ts.use_snap_translate
          and individual() == {"FACE_NEAREST"},
          f"snap={ts.use_snap} indiv={individual()}")
    slot.chk024(True, None)  # base Edge constraint cross-clears the projection axis (radio)
    check("transform chk026<->chk024 mutually exclusive (radio cluster)",
          elements() == {"EDGE"} and individual() == set(),
          f"base={elements()} indiv={individual()}")
    slot.chk026(False, None)
    check("transform chk026 off disables snap", not ts.use_snap)

    # ---- selection b002-b007: one-shot constraint expansion (icon row, was cmb005) ----------
    reset()
    o = add_cube("C5")
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="DESELECT")
    bpy.ops.mesh.select_mode(type="VERT")
    bm = _bm.from_edit_mesh(o.data)
    bm.verts.ensure_lookup_table()
    bm.verts[0].select = True
    _bm.update_edit_mesh(o.data)
    slot = make_slot(SelectionSlots, sb=NS(message_box=lambda *a, **k: None, tk=btk))
    # a one-shot in Blender: the row's buttons are not checkable there
    slot.b006(NS(objectName=lambda: "b006", isCheckable=lambda: False, isChecked=lambda: False))
    bm = _bm.from_edit_mesh(o.data)
    check("selection b006 (Shell) expands to the whole shell",
          all(v.select for v in bm.verts),
          f"selected={sum(v.select for v in bm.verts)}/8")
    bpy.ops.object.mode_set(mode="OBJECT")

    # ---- rigging cmb002: Rigify quick rig ---------------------------------------------------
    from tentacle.slots.rigging import RiggingSlots  # composed: both hosts, over sb.tk

    reset()
    slot = make_slot(RiggingSlots, sb=NS(message_box=lambda *a, **k: None, tk=btk))
    rig_items = ["Human Meta-Rig", "Basic Human Meta-Rig", "Generate Rig"]
    slot.cmb002(0, NS(items=rig_items))
    meta = bpy.context.view_layer.objects.active
    check("rigging cmb002 adds the human meta-rig",
          meta is not None and meta.type == "ARMATURE",
          f"active={meta and meta.name}")
    slot.cmb002(2, NS(items=rig_items))  # generate on the active meta-rig
    rig = bpy.context.view_layer.objects.active
    check("rigging cmb002 generates the control rig",
          rig is not None and rig.name == "rig" and rig is not meta,
          f"active={rig and rig.name}")
    msgs = []
    reset()
    slot.sb = NS(message_box=msgs.append, tk=btk)
    slot.cmb002(2, NS(items=rig_items))  # nothing active -> message
    check("rigging cmb002 generate without a meta-rig messages", len(msgs) == 1, f"{msgs}")

    # The procedural rigs open their co-located blendertk panels -- the same names
    # tentacle/test/test_rigging.py pins for Maya's (mayatk parity).
    added, shown = [], []
    slot = make_slot(
        RiggingSlots, sb=NS(handlers=NS(marking_menu=NS(show=shown.append)), tk=btk)
    )
    slot.cmb002_init(NS(add=lambda items, **k: added.extend(items)))
    procedural = {"Telescope Rig": "telescope_rig", "Wheel Rig": "wheel_rig",
                  "Shadow Rig": "shadow_rig", "Tube Rig": "tube_rig",
                  "Articulated Rig": "articulated_rig"}
    for index, text in enumerate(added):
        if text in procedural:
            slot.cmb002(index, NS(items=added))
    check("rigging cmb002 offers every procedural rig and opens its panel",
          set(procedural) <= set(added)
          and shown == [procedural[t] for t in added if t in procedural],
          f"items={added} shown={shown}")

    # ---- rigging tb003: mayatk's locator rig; a bare locator typed a Maya locator ----------
    def affix(text=""):  # an affix field in the picker's Scene state
        return NS(text=lambda t=text: t, option_box=NS(affix_mode="convention"))

    tb003_box = option_box(
        t000=affix(), t001=affix(), t002=affix(), s001=spin(1.5), cmb011=combo("zyx"),
        cmb012=combo("ring"), **{f"chk00{i}": chk(False) for i in range(5, 10)},
    )
    reset()
    crate = add_cube("Crate", (2, 0, 1))
    slot = make_slot(RiggingSlots, sb=NS(message_box=lambda *a, **k: None, tk=btk))
    slot.tb003(tb003_box)
    loc = crate.parent
    check("rigging tb003 rigs the selection under a zeroed zyx locator, left selected",
          loc is not None and loc.rotation_mode == "ZYX"
          and tuple(loc.location) == (0.0, 0.0, 0.0)
          and loc.get("maya_node_type") == "locator"
          and list(bpy.context.view_layer.objects.selected) == [loc],
          f"parent={loc and loc.name} loc={loc and tuple(loc.location)}")
    grp = loc and loc.parent
    check("rigging tb003 cmb012 'ring' draws the group as a circle",
          grp is not None and grp.empty_display_type == "CIRCLE",
          f"{grp and grp.empty_display_type}")
    reset()
    slot.tb003(tb003_box)  # nothing selected -> a lone locator
    bare = bpy.context.view_layer.objects.active
    check("rigging tb003 with nothing selected adds a typed locator Empty",
          bare is not None and bare.type == "EMPTY"
          and bare.get("maya_node_type") == "locator"
          and abs(bare.empty_display_size - 1.5) < 1e-6 and bare.rotation_mode == "ZYX",
          f"{bare and bare.name} {bare and bare.get('maya_node_type')!r}")

    # ---- edit Create > Helper: a Locator and a Null Group, each typed its Maya node --------
    # (btk.Primitives.create, what the shared Edit panel's Create list calls)
    reset()
    btk.Primitives.create("Helper", "Locator")
    helper = bpy.context.view_layer.objects.active
    check("edit Create > Helper > Locator adds a typed locator Empty",
          helper is not None and helper.type == "EMPTY"
          and helper.get("maya_node_type") == "locator",
          f"{helper and helper.name}")
    reset()
    btk.Primitives.create("Helper", "Null Group")  # childless: untyped, it read as a locator
    null = bpy.context.view_layer.objects.active
    check("edit Create > Helper > Null Group adds a typed group Empty, its arrows kept",
          null is not None and null.get("maya_node_type") == "group"
          and btk.NodeUtils.is_group(null) and null.empty_display_type == "ARROWS"
          and abs(null.empty_display_size - 1.0) < 1e-6,
          f"{null and null.get('maya_node_type')!r} {null and null.empty_display_size}")

    # ---- nurbs b056 / b058: the shared Image Tracer and Curve to Tube panels -------------
    from tentacle.slots.nurbs import NurbsSlots

    shown = []
    slot = make_slot(NurbsSlots, sb=NS(handlers=NS(marking_menu=NS(show=shown.append)), tk=btk))
    slot.b056()
    slot.b058()
    check("nurbs b056: opens the shared Image Tracer panel (b058: Curve to Tube)",
          shown == ["image_tracer", "curve_to_tube"], f"{shown}")

    # ---- scene b001 / lighting b000: route to the new manager panels ------------------------
    from tentacle.slots.lighting import LightingSlots

    shown = []
    mm = NS(marking_menu=NS(show=shown.append))
    slot = make_slot(SceneSlots)
    slot.sb = NS(handlers=mm)
    slot.b001()
    slot = make_slot(LightingSlots)
    slot.sb = NS(handlers=mm)
    slot.b000()
    check("scene b001 / lighting b000 open the manager panels",
          shown == ["reference_manager", "hdr_manager"], f"{shown}")

    # ---- scene b004: routes to the Hierarchy Sync panel -----------------------------------
    # (b004 stopped opening a native Outliner window when the hierarchy_sync panel shipped.)
    shown = []
    slot = make_slot(SceneSlots, sb=NS(handlers=NS(marking_menu=NS(show=shown.append))))
    slot.b004()
    check("scene b004 opens the hierarchy-sync panel",
          shown == ["hierarchy_sync"], f"{shown}")

    # ---- scene tb001: Get Scene Info over btk -----------------------------------------------
    import blendertk as btk
    from tentacle.slots.scene import SceneSlots

    reset()
    base = add_cube("info_cube")
    bpy.context.collection.objects.link(base.copy())  # a linked duplicate (shares the mesh)
    views, msgs, warnings_logged, ticks = [], [], [], []
    slot = make_slot(
        SceneSlots,
        sb=NS(
            message_box=msgs.append,
            text_view_dialog=lambda text, *b, **k: views.append((text, k)),
            logger=NS(warning=warnings_logged.append, debug=lambda *a, **k: None),
            progress=lambda **k: contextlib.nullcontext(None),
            progress_adapter=lambda update: lambda *a: ticks.append(a),
            tk=btk,
        ),
    )
    sections = {f"chk_section_{key}": chk(True) for key in btk.SceneInfoSection.ALL}
    slot.tb001(option_box(cmb_scope1=combo("all"), cmb_profile=combo(True), **sections))
    html, kwargs = views[0] if views else ("", {})
    check("scene tb001 reports linked duplicates as instances",
          "2 instances of 1 unique mesh (1 instanced)" in html, f"{msgs}")
    check("scene tb001 drives the footer progress through the analyzer",
          bool(ticks) and ticks[-1] == (100, 100, "Done"), f"{ticks[-3:]}")
    handler = kwargs.get("link_handler")
    gone = NS(scheme=lambda: "action", host=lambda: "select", query=lambda: "node=gone")
    check("scene tb001's links go to the Blender dispatcher, which names a stale one",
          getattr(handler, "func", None) is btk.UiUtils.dispatch_log_link
          and handler(gone) is False and warnings_logged, f"{kwargs} | {warnings_logged}")
    bpy.ops.object.select_all(action="DESELECT")
    slot.tb001(option_box(cmb_scope1=combo("selection"), cmb_profile=combo(True), **sections))
    check("scene tb001 selection scope needs a selection",
          any("Nothing selected" in m for m in msgs), f"{msgs}")

    # tb001_init on a real uitk option-box menu, with btk's real section labels.
    from qtpy import QtGui, QtWidgets
    from uitk.widgets.label import Label
    from uitk.widgets.menu import Menu

    QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    info_menu = Menu()
    slot.sb.registered_widgets = NS(Label=Label)
    slot.tb001_init(NS(option_box=NS(menu=info_menu)))
    toggles = {key: getattr(info_menu, f"chk_section_{key}", None)
               for key in btk.SceneInfoSection.ALL}
    check("scene tb001_init builds one tooltipped toggle per section",
          all(t is not None and t.toolTip() for t in toggles.values()),
          f"{[k for k, t in toggles.items() if t is None or not t.toolTip()]}")
    notes = toggles["assumptions"]
    check("scene tb001's 'Notes & Assumptions' keeps its '&' and binds no mnemonic",
          notes is not None and notes.text() == "Notes && Assumptions"
          and QtGui.QKeySequence.mnemonic(notes.text()).isEmpty(),
          f"{notes.text() if notes else None!r}")
    check("scene tb001's Generic tooltip claims no budget the engine does not use",
          "100k" not in info_menu.cmb_profile.toolTip(), info_menu.cmb_profile.toolTip())

    # ---- scene tb002: Fix Non-Orthogonal Axes over btk (Entire Scene) -----------------------
    reset()
    skew_parent = add_cube("shear_parent")
    skew_parent.scale = (1.0, 3.0, 1.0)
    skew_child = add_cube("shear_child", location=(2, 0, 0))
    skew_child.parent = skew_parent
    skew_child.rotation_euler = (0.0, 0.0, 0.7)
    bpy.context.view_layer.update()
    msgs = []
    slot = make_slot(
        SceneSlots,
        sb=NS(
            message_box=lambda text, *buttons, **k: msgs.append(text)
            or ("Yes" if buttons else None),
            progress=lambda **k: contextlib.nullcontext(lambda *a, **kw: None),
            text_view_dialog=lambda *a, **k: None,
            tk=btk,
        ),
    )
    slot.tb002(option_box(
        cmb_scope2=combo("all"), chk_dry_run=chk(False), chk_break_connections=chk(False)
    ))
    check("scene tb002 fixes an inherited shear over btk (one confirm, one report)",
          not btk.Diagnostics.get_non_orthogonal(list(bpy.context.scene.objects))
          and any("Fixed <hl>1</hl> of <hl>1</hl>" in m for m in msgs), f"{msgs}")

    # ---- scene lists + Tools launchers: Blender's rows, the Maya bridge ---------------------
    imports = {label for label, _, _ in slot._list_rows(slot._IMPORT_ROWS, "import")}
    check("scene Import list: Blender's importers plus the Maya-scene pull",
          {"Import FBX", "Import OBJ", "Import Maya Scene", "Import glTF", "Import USD",
           "Append from .blend", "Link from .blend"} <= imports
          and "Import File" not in imports, f"{sorted(imports)}")
    exports = [(label, req) for label, _, req in slot._list_rows(slot._EXPORT_ROWS, "export")]
    check("scene Export list: Export .ma, Blender's exporters, Maya's glTF row tagged",
          {("Export Selection", None), ("Export .ma", None), ("Export USD", None),
           ("Export FBX", None), ("Export glTF", None), ("Export glTF", "maya")}
          <= set(exports) and ("Export All", None) not in exports, f"{exports}")
    shown = []
    slot = make_slot(SceneSlots, sb=NS(handlers=NS(marking_menu=NS(show=shown.append)), tk=btk))
    slot.b010()
    slot.b003()
    slot.b015()
    check("scene b010 / b003 / b015 open the Maya Bridge, Audio Clips, Blendshape Animator",
          shown == ["maya_bridge", "audio_clips", "blendshape_animator"], f"{shown}")

    # ---- deformation tb001: routes to the curtain panel -------------------------------------
    from tentacle.slots.deformation import DeformationSlots

    shown = []
    slot = make_slot(DeformationSlots)
    slot.sb = NS(handlers=NS(marking_menu=NS(show=shown.append)))
    slot.tb001(None)
    check("deformation tb001 opens the curtain panel", shown == ["curtain"], f"{shown}")

    # ---- main list000: workspace browser = the current .blend's dir CONTENTS ----------------
    # (files + sub-folders, not just sub-folders) — Blender's analogue of Maya's project tree.
    import os as _os
    import shutil as _shutil
    import tempfile as _tempfile
    from tentacle.slots.main import MainSlots

    class _SubStub:
        def __init__(self):
            self.added = []
        def add(self, text, data=None):
            child = _SubItem(text, data)
            self.added.append(child)
            return child

    class _SubItem:
        def __init__(self, text, data):
            self.text, self.data = text, data
            self.sublist = _SubStub()

    proj = _tempfile.mkdtemp(prefix="ws_proj_")
    _os.makedirs(_os.path.join(proj, "textures", "wood"))
    _os.makedirs(_os.path.join(proj, "exports"))
    for fn in ("scene.blend", "ref.png", "notes.txt"):
        open(_os.path.join(proj, fn), "w").close()
    bpy.ops.wm.save_as_mainfile(filepath=_os.path.join(proj, "scene.blend"))

    check("main workspace resolves to the saved .blend's dir",
          btk.get_env_info("workspace") == proj, f"ws={btk.get_env_info('workspace')}")

    # Folder rows take the "folder_filled" icon through the switchboard's IconManager.
    slot = make_slot(
        MainSlots,
        sb=NS(IconManager=NS(set_label_icon=lambda *a, **k: None), tk=btk),
    )
    root = _SubStub()
    slot._populate_dir_sublist(root, proj, max_depth=2)
    names = [i.text for i in root.added]
    # Folders only, like Maya's tree -- a click opens the folder in the system browser.
    check("workspace lists the sub-folders, not the files",
          names == ["exports", "textures"], f"names={names}")
    nested = next((i for i in root.added if i.text == "textures"), None)
    check("workspace recurses sub-folders",
          nested is not None and [c.text for c in nested.sublist.added] == ["wood"],
          f"textures->{nested and [c.text for c in nested.sublist.added]}")

    # restore an unsaved state so we don't leave the temp file as the 'open' doc
    bpy.ops.wm.read_homefile(use_empty=True)
    _shutil.rmtree(proj, ignore_errors=True)

    # ---- editors: every Blender button + list entry opens a REAL editor (no dead links) -----
    # The composed EditorsSlots names editors the mayatk way; blendertk resolves each to
    # its own editor (EDITOR_TYPES aliases). The buttons the .ui tags requires="maya" are
    # hidden here, so only the ones Blender shows are driven.
    from tentacle.slots.editors import EditorsSlots

    valid = set(btk.get_editor_types())
    bad_list = [
        e
        for items in btk.UiUtils.get_editor_categories().values()
        for e in items
        if e not in valid
    ]
    check("every editors-list entry opens a real editor", not bad_list, f"{bad_list}")

    asked = []
    eslot = make_slot(EditorsSlots)
    eslot.sb.tk = NS(
        UiUtils=NS(
            open_editor=lambda e: asked.append(e) or "ok",
            toggle_editor=lambda e: asked.append(e) or True,
            get_editor_types=btk.get_editor_types,
        ),
        ScriptConsole=NS(toggle=lambda: None),
    )
    blender_buttons = (
        "b000", "b001", "b002", "b003", "b004", "b005", "b009", "b011",
        "b014", "b015", "b016", "b017", "b018",
    )
    for bn in blender_buttons:
        getattr(eslot, bn)()
    bad_buttons = [e for e in asked if e not in valid]
    check(
        "every Blender editor button opens a real editor",
        len(asked) == len(blender_buttons) and not bad_buttons,
        f"asked={asked} bad={bad_buttons}",
    )
    blender_only = asked[-5:]
    check(
        "the five Blender-only buttons open five distinct editors",
        len(set(blender_only)) == 5,
        f"{blender_only}",
    )

except Exception as e:
    lines.append(f"FAIL setup: {e!r}")
    lines.append(traceback.format_exc())

ok = all(line.startswith("OK") for line in lines)
print("\n===BLENDER-DEEPENED-SLOTS===")
print("\n".join(lines))
print(f"===RESULT: {'PASS' if ok else 'FAIL'}===")
