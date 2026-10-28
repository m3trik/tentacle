"""Shot Sequencer panel checks in a real Blender: the shared panel's controller
(``tentacle/slots/tools/_shot_sequencer``) over blendertk.

Requires a real Blender binary (it ``import bpy``), so it is **not** a CI/unittest target -- the
``blender/`` subdir and the non-``test_`` name keep it out of auto-discovery. Run it against a
*fresh* Blender (never an existing session)::

    blender --background --factory-startup --python tentacle/test/blender/shot_sequencer_panel_check.py

or ``python tentacle/test/run_tests.py shot_sequencer_panel --in-blender``.

The panel's handlers -- key and clip drags, the delete paths, the key menu's
edits and clipboard, the tangent drag, Ctrl edge drags, the widget sync, the
undo / redo and the scene-event reactions -- driven on the scenes blendertk's
engine harness (``blendertk/test/test_shot_sequencer.py``) builds, which they
left when the panel moved here.  Each host is the tentacle controller with
``tk = blendertk`` and its ``__init__`` bypassed (no Qt widgets): what it
reaches of the scene goes through ``btk.SequencerHost``, as the panel's does.
The engine and the host half (``SequencerHost``) stay checked in blendertk.
"""

import logging
import os
import sys
import tempfile
import traceback
from pathlib import Path

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


def _run_panel_checks():
    lines = []

    def check(label, cond, detail=""):
        ok = bool(cond)
        lines.append(
            f"{'OK' if ok else 'FAIL'}: {label}"
            + (f" — {detail}" if detail and not ok else "")
        )
        return ok

    import bpy
    from qtpy import QtWidgets

    import blendertk as btk
    from blendertk import BlenderShotStore
    from blendertk.anim_utils._anim_utils import AnimUtils
    from blendertk.anim_utils.shots.shot_sequencer._shot_sequencer import (
        _ShotSequencerInternal as _SSI,
    )
    from tentacle.slots.tools._shot_sequencer.controller import (
        ShotSequencerController as _PanelController,
    )

    QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    ShotSequencer = btk.ShotSequencer
    BlenderShotStore._prefs_dir_override = tempfile.mkdtemp(prefix="tcl_seq_panel_")
    BlenderShotStore.clear_active()

    def _init_state(ctl):
        """What the panel's ``__init__`` sets, minus its widgets and hooks."""
        ctl.ui = None
        ctl._sequencer = None
        ctl._scene_watch = None
        ctl._keyframe_debounce = None
        ctl._rebuild_debounce = None
        ctl._edited_items = set()
        ctl._syncing = False
        ctl._syncing_playhead = False
        ctl._store_listener_bound = False
        ctl._shot_display_mode = "current"
        ctl._segment_cache = {}
        ctl._sub_row_cache = {}
        ctl._color_map_cache = None
        ctl._audio_segments_cache = None
        ctl._reconcile_needed = True
        ctl._shifted_out_keys = {}
        ctl._context_space_frames = ctl.CONTEXT_SPACE_FRAMES
        ctl._extend_to_keys = False
        ctl._playhead_to_shot_start = True
        ctl._copy_to_shot = False
        ctl._extend_reach = ctl.EXTEND_REACH_FRAMES
        ctl._prev_action = ctl._next_action = ctl._view_mode_action = None
        ctl._cmb_mode_widget = None
        ctl._playback_range_mode = "follows_view"
        ctl._track_order_scope = "visible"
        ctl._show_internal_holds = False
        ctl._cmb_mode = "shots"
        ctl._transport_controls = None

    class _Ctrl(_PanelController):
        """The panel's controller over blendertk, its state set before any
        ``__init__`` a test host bypasses the panel's with."""

        tk = btk

        def __new__(cls, *args, **kwargs):
            self = super().__new__(cls)
            _init_state(self)
            return self

    ShotSequencerController = _Ctrl  # the name the moved checks call it by

    # ---- the engine harness's scene helpers (``test_shot_sequencer.py``) ----
    def fresh(name_keys):
        """A store + sequencer over freshly keyed cubes.  ``{obj: {frame: x}}``."""
        bpy.ops.wm.read_factory_settings(use_empty=True)
        BlenderShotStore.clear_active()
        st = BlenderShotStore()
        BlenderShotStore.set_active(st)
        made = {}
        for obj_name, keys in name_keys.items():
            bpy.ops.mesh.primitive_cube_add()
            ob = bpy.context.active_object
            ob.name = obj_name
            for f, v in sorted(keys.items()):
                ob.location.x = v
                ob.keyframe_insert(data_path="location", index=0, frame=f)
            made[obj_name] = ob
        return st, ShotSequencer(store=st), made

    def fc_of(ob):
        return next(
            fc
            for fc in AnimUtils.get_fcurves(ob)
            if fc.data_path == "location" and fc.array_index == 0
        )

    def interp_at(ob, t):
        fc = fc_of(ob)
        for kp in fc.keyframe_points:
            if abs(kp.co[0] - t) < 1e-3:
                return kp.interpolation
        return None

    def times_of(ob):
        return sorted(round(kp.co[0], 3) for kp in fc_of(ob).keyframe_points)

    # ---- on_keys_moved: chained batch moves are two-pass ------------------
    # (pre-fix: single in-place pass let [(10,12),(12,14)] stack both keys on 14)

    class _FakeClip:
        def __init__(self, data):
            self.data = data

    class _FakeWidget:
        def __init__(self, clip):
            self._clip = clip

        def get_clip(self, cid):
            return self._clip

    class _KeysHost(_Ctrl):
        """The panel's per-key handlers over a fake widget (no Qt needed).

        ``sequencer`` is a plain attribute here, not the panel's lazy property:
        a key move needs no shots, and ``None`` must stay ``None``.
        """

        sequencer = None

        def __init__(self, widget, sequencer=None):
            self._widget = widget
            self.sequencer = sequencer
            self.logger = logging.getLogger("test.clip_motion_host")

        def _get_sequencer_widget(self):
            return self._widget

        def _save_shot_state(self):
            pass

        def _sync_to_widget(self, **kw):
            pass

        def _sync_combobox(self):
            pass

        def _set_footer(self, *a, **k):
            pass

    bpy.ops.mesh.primitive_cube_add()
    cm_obj = bpy.context.active_object
    cm_obj.name = "ChainMv"
    for f, x in ((10, 1.0), (12, 2.0)):
        cm_obj.location = (x, 0.0, 0.0)
        cm_obj.keyframe_insert(data_path="location", index=0, frame=f)

    host = _KeysHost(
        _FakeWidget(
            _FakeClip({"obj": "ChainMv", "attr_name": "translateX", "shot_id": None})
        )
    )
    host.on_keys_moved(1, [(10.0, 12.0), (12.0, 14.0)])
    fc_x = next(
        fc
        for fc in AnimUtils.get_fcurves(cm_obj)
        if fc.data_path == "location" and fc.array_index == 0
    )
    moved = sorted(
        (round(kp.co[0], 3), round(kp.co[1], 3)) for kp in fc_x.keyframe_points
    )
    check(
        "on_keys_moved: chained moves land distinctly (no key stacking)",
        moved == [(12.0, 1.0), (14.0, 2.0)],
        f"{moved}",
    )

    # ---- on_keys_batch_moved: one drag over TWO clips is one commit ---------
    # uitk emits keys_batch_moved for a multi-clip key drag; nothing else in
    # this suite exercises that entry point, and an unhandled signal would
    # make the drag silently do nothing.
    class _MultiWidget:
        def __init__(self, clips):
            self._clips = clips

        def get_clip(self, cid):
            return self._clips.get(cid)

    batch_objs = []
    for name, frames in (("BatchA", (10, 20)), ("BatchB", (10, 20))):
        bpy.ops.mesh.primitive_cube_add()
        o = bpy.context.active_object
        o.name = name
        for i, f in enumerate(frames):
            o.location = (float(i), 0.0, 0.0)
            o.keyframe_insert(data_path="location", index=0, frame=f)
        batch_objs.append(o)

    batch_host = _KeysHost(
        _MultiWidget(
            {
                1: _FakeClip(
                    {"obj": "BatchA", "attr_name": "translateX", "shot_id": None}
                ),
                2: _FakeClip(
                    {"obj": "BatchB", "attr_name": "translateX", "shot_id": None}
                ),
            }
        )
    )
    batch_host.on_keys_batch_moved([(1, [(20.0, 25.0)]), (2, [(20.0, 25.0)])])

    def _times(obj):
        fc = next(
            fc
            for fc in AnimUtils.get_fcurves(obj)
            if fc.data_path == "location" and fc.array_index == 0
        )
        return sorted(round(kp.co[0], 3) for kp in fc.keyframe_points)

    check(
        "on_keys_batch_moved: every clip in the gesture is committed",
        _times(batch_objs[0]) == [10.0, 25.0] and _times(batch_objs[1]) == [10.0, 25.0],
        f"{_times(batch_objs[0])} / {_times(batch_objs[1])}",
    )

    # ---- a drag onto a KEYED neighbour boundary moves the neighbour whole ----
    # Mirror of mayatk's TestADragOntoAKeyedNeighbourLeavesItWhole (2026-09-22):
    # the key handlers ripple BEFORE the keys land, but the carried window
    # treated the sample on the new bound as the dragged shot's, stranding the
    # neighbour's own pose in the gap; the clip paths landed first instead and
    # stacked the landed key on that pose.
    _seam_objects: list = []

    def _seam_scene(name, shots, keys):
        """A cube keyed on location.x, in every one of *shots*: (obj, store, seq).

        The previous seam scene's cube goes first: the sequencer moves (and
        checks for collisions on) the scene's whole keyed content, so a cube
        left keyed from the case before is part of the next one."""
        BlenderShotStore.clear_active()
        while _seam_objects:
            _old = bpy.data.objects.get(_seam_objects.pop())
            if _old is not None:
                bpy.data.objects.remove(_old, do_unlink=True)
        bpy.ops.mesh.primitive_cube_add()
        o = bpy.context.active_object
        o.name = name
        _seam_objects.append(o.name)
        for f, v in keys:
            o.location = (float(v), 0.0, 0.0)
            o.keyframe_insert(data_path="location", index=0, frame=f)
        st = BlenderShotStore()
        for sname, s, e in shots:
            st.define_shot(sname, s, e, objects=[o.name])
        return o, st, ShotSequencer(st)

    def _loc_x(o):
        return next(
            fc
            for fc in AnimUtils.get_fcurves(o)
            if fc.data_path == "location" and fc.array_index == 0
        )

    def _move_clip(data, sq, new_start):
        host = _KeysHost(_FakeWidget(_FakeClip(data)), sq)
        host._shifted_out_keys = {}
        host._audio_segments_cache = None
        host.on_clip_moved(1, new_start)

    def _seam_case(name, shots, keys, gesture):
        o, st, sq = _seam_scene(name, shots, keys)
        ids = [st.shot_by_name(sname).shot_id for sname, _s, _e in shots]
        kind, idx, payload = gesture
        data = {"obj": o.name, "shot_id": ids[idx]}
        if kind == "keys":
            data["attr_name"] = "translateX"
            _KeysHost(_FakeWidget(_FakeClip(data)), sq).on_keys_batch_moved(
                [(1, payload)]
            )
        else:
            clip_data, new_start = payload
            _move_clip(dict(data, **clip_data), sq, new_start)
        got = [
            (round(kp.co[0], 3), round(kp.co[1], 3)) for kp in _loc_x(o).keyframe_points
        ]
        return [(s.start, s.end) for s in st.sorted_shots()], got

    ab = [("A", 0, 50), ("B", 65, 100)]
    bounds, got = _seam_case(
        "SeamEq", ab, ((10, 0), (40, 1), (65, 1), (80, 2)), ("keys", 0, [(40.0, 65.0)])
    )
    check(
        "keyed neighbour: a key onto its start moves it whole",
        bounds == [(0, 65), (80, 115)]
        and got == [(10.0, 0.0), (65.0, 1.0), (80.0, 1.0), (95.0, 2.0)],
        f"{bounds} {got}",
    )
    _b, got = _seam_case(
        "SeamNe", ab, ((10, 0), (40, 1), (65, 7), (80, 2)), ("keys", 0, [(40.0, 65.0)])
    )
    check(
        "keyed neighbour: an unequal opening pose stays on its new start",
        got == [(10.0, 0.0), (65.0, 1.0), (80.0, 7.0), (95.0, 2.0)],
        f"{got}",
    )
    bounds, got = _seam_case(
        "SeamUp",
        [("P", 0, 35), ("A", 50, 100)],
        ((5, 0), (35, 4), (60, 2), (90, 3)),
        ("keys", 1, [(60.0, 35.0)]),
    )
    check(
        "keyed neighbour: a key onto the previous shot's end moves it whole",
        bounds == [(-15, 20), (35, 100)]
        and got == [(-10.0, 0.0), (20.0, 4.0), (35.0, 2.0), (90.0, 3.0)],
        f"{bounds} {got}",
    )
    _b, got = _seam_case(
        "SeamIn",
        ab,
        ((10, 0), (40, 1), (65, 1), (70, 2), (80, 3)),
        ("keys", 0, [(40.0, 70.0)]),
    )
    check(
        "keyed neighbour: a key dragged inside it moves it whole",
        got == [(10.0, 0.0), (70.0, 1.0), (85.0, 1.0), (90.0, 2.0), (100.0, 3.0)],
        f"{got}",
    )
    _b, got = _seam_case(
        "SeamClip",
        ab,
        ((10, 0), (30, 5), (40, 1), (65, 7), (80, 2)),
        (
            "clip",
            0,
            ({"attr_name": "translateX", "orig_start": 30.0, "orig_end": 40.0}, 55.0),
        ),
    )
    check(
        "keyed neighbour: a sub-row clip lands after the neighbour moved",
        got == [(10.0, 0.0), (55.0, 5.0), (65.0, 1.0), (80.0, 7.0), (95.0, 2.0)],
        f"{got}",
    )
    _b, got = _seam_case(
        "SeamStep",
        ab,
        ((10, 0), (40, 1), (65, 7), (80, 2)),
        ("clip", 0, ({"orig_start": 40.0, "orig_end": 40.0, "is_stepped": True}, 65.0)),
    )
    check(
        "keyed neighbour: a stepped clip lands after the neighbour moved",
        got == [(10.0, 0.0), (65.0, 1.0), (80.0, 7.0), (95.0, 2.0)],
        f"{got}",
    )
    # A run that outlasts its shot: made room for before it moved, its part in
    # the neighbour's envelope rode the ripple (+22) instead of the drag (+2).
    bounds, got = _seam_case(
        "SeamSpan",
        ab,
        ((10, 0), (45, 1), (70, 2), (85, 3)),
        (
            "clip",
            0,
            ({"attr_name": "translateX", "orig_start": 45.0, "orig_end": 70.0}, 47.0),
        ),
    )
    check(
        "keyed neighbour: a sub-row clip reaching into the next shot moves as one",
        bounds == [(0, 72), (87, 122)]
        and got == [(10.0, 0.0), (47.0, 1.0), (72.0, 2.0), (107.0, 3.0)],
        f"{bounds} {got}",
    )
    # A claim is a (curve, time) pair, so it moves with its key -- as the key
    # drag's always did; the sub-row move shifted the keys alone.
    from blendertk.anim_utils.shots.shot_sequencer._shot_sequencer import (
        _ShotSequencerInternal,
    )

    co, cst, csq = _seam_scene("SeamClaim", ab, ((10, 0), (30, 5), (40, 1), (80, 2)))
    ckey = _ShotSequencerInternal._fc_key(co.name, _loc_x(co))
    csq.ledger.record_key(ckey, 40.0)
    _move_clip(
        {
            "obj": co.name,
            "shot_id": cst.shot_by_name("A").shot_id,
            "attr_name": "translateX",
            "orig_start": 30.0,
            "orig_end": 40.0,
        },
        csq,
        32.0,
    )
    ctimes = [round(kp.co[0], 3) for kp in _loc_x(co).keyframe_points]
    check(
        "keyed neighbour: a sub-row clip carries its keys' claims",
        ctimes == [10.0, 32.0, 42.0, 80.0] and csq.ledger.key_times(ckey) == [42.0],
        f"{ctimes} claims={csq.ledger.key_times(ckey)}",
    )
    # Dragged back past its shot's start, a clip grows the head, which ripples
    # the shots before it back as far -- onto the lifted clip, on a long drag.
    bounds, got = _seam_case(
        "SeamBack",
        [("A", 0, 50), ("B", 60, 100)],
        ((10, 0), (40, 1), (70, 5), (90, 6)),
        (
            "clip",
            1,
            ({"attr_name": "translateX", "orig_start": 70.0, "orig_end": 90.0}, -980.0),
        ),
    )
    check(
        "keyed neighbour: a clip dragged far back is not met by the ripple",
        bounds == [(-1040, -990), (-980, 100)]
        and got == [(-1030.0, 0.0), (-1000.0, 1.0), (-980.0, 5.0), (-960.0, 6.0)],
        f"{bounds} {got}",
    )

    # ---- a landing on a CONTIGUOUS seam grows its shot a frame past it -------
    # Mirror of mayatk's TestALandingOnAContiguousSeamGrowsItsShotAFrame
    # (BACKLOG 2026-09-22, decided 2026-09-23): touching shots share ONE
    # sample, so a key landing on that frame took the neighbour's opening pose.
    touching = [("A", 0, 50), ("B", 50, 100)]
    seam_keys = ((10, 0), (40, 5), (50, 3), (70, 9), (90, 2))
    bounds, got = _seam_case(
        "SeamPast", touching, seam_keys, ("keys", 0, [(40.0, 60.0)])
    )
    check(
        "contiguous seam: a key past the end leaves B its opening pose",
        bounds == [(0, 61), (61, 111)]
        and got
        == [
            (10.0, 0.0),
            (50.0, 3.0),
            (60.0, 5.0),
            (61.0, 3.0),
            (81.0, 9.0),
            (101.0, 2.0),
        ],
        f"{bounds} {got}",
    )
    bounds, got = _seam_case(
        "SeamEqual",
        touching,
        ((10, 0), (40, 5), (50, 5), (70, 9), (90, 2)),
        ("keys", 0, [(40.0, 60.0)]),
    )
    check(
        "contiguous seam: equal poses keep their frames",
        bounds == [(0, 61), (61, 111)]
        and got
        == [
            (10.0, 0.0),
            (50.0, 5.0),
            (60.0, 5.0),
            (61.0, 5.0),
            (81.0, 9.0),
            (101.0, 2.0),
        ],
        f"{bounds} {got}",
    )
    bounds, got = _seam_case("SeamOn", touching, seam_keys, ("keys", 0, [(40.0, 50.0)]))
    check(
        "contiguous seam: a key onto the existing seam leaves B whole",
        bounds == [(0, 51), (51, 101)]
        and got == [(10.0, 0.0), (50.0, 5.0), (51.0, 3.0), (71.0, 9.0), (91.0, 2.0)],
        f"{bounds} {got}",
    )
    bounds, got = _seam_case(
        "SeamBack", touching, seam_keys, ("keys", 1, [(70.0, 45.0)])
    )
    check(
        "contiguous seam: a key dragged back over it mirrors the step",
        bounds == [(-6, 44), (44, 100)]
        and got
        == [
            (4.0, 0.0),
            (34.0, 5.0),
            (44.0, 3.0),
            (45.0, 9.0),
            (50.0, 3.0),
            (90.0, 2.0),
        ],
        f"{bounds} {got}",
    )
    unkeyed = ((10, 0), (20, 1), (40, 2), (55, 3))
    bounds, got = _seam_case(
        "SeamBare", [("A", 0, 30), ("B", 30, 60)], unkeyed, ("keys", 0, [(20.0, 30.0)])
    )
    check(
        "contiguous seam: with no key on it nothing steps",
        bounds == [(0, 30), (30, 60)]
        and [t for t, _v in got] == [10.0, 30.0, 40.0, 55.0],
        f"{bounds} {got}",
    )
    # A main-track OBJECT clip grows through move_object_in_shot, which sized
    # the bound itself (rounded, no step): past the seam the dragged 5 landed
    # on B's opening pose and one of the two was dropped, and onto the
    # existing seam the same.
    object_clip = {"orig_start": 10.0, "orig_end": 40.0}
    bounds, got = _seam_case(
        "SeamObjPast", touching, seam_keys, ("clip", 0, (object_clip, 30.0))
    )
    check(
        "contiguous seam: an object clip past the end leaves B its opening pose",
        bounds == [(0, 61), (61, 111)]
        and got == [(30.0, 0.0), (60.0, 5.0), (61.0, 3.0), (81.0, 9.0), (101.0, 2.0)],
        f"{bounds} {got}",
    )
    bounds, got = _seam_case(
        "SeamObjOn", touching, seam_keys, ("clip", 0, (object_clip, 20.0))
    )
    check(
        "contiguous seam: an object clip onto the existing seam leaves B whole",
        bounds == [(0, 51), (51, 101)]
        and got == [(20.0, 0.0), (50.0, 5.0), (51.0, 3.0), (71.0, 9.0), (91.0, 2.0)],
        f"{bounds} {got}",
    )
    bounds, got = _seam_case(
        "SeamObjBare",
        [("A", 0, 30), ("B", 30, 60)],
        unkeyed,
        ("clip", 0, ({"orig_start": 10.0, "orig_end": 20.0}, 20.0)),
    )
    check(
        "contiguous seam: an object clip onto an unkeyed seam steps nothing",
        bounds == [(0, 30), (30, 60)]
        and [t for t, _v in got] == [20.0, 30.0, 40.0, 55.0],
        f"{bounds} {got}",
    )
    # Back over the seam, A's closing pose stays behind in B's landing zone:
    # the object move shifted keys raw (mayatk's clears the landing zone), so
    # it stayed there as a stray 3 inside B and A closed on nothing.
    bounds, got = _seam_case(
        "SeamObjBack",
        touching,
        seam_keys,
        ("clip", 1, ({"orig_start": 70.0, "orig_end": 90.0}, 45.0)),
    )
    check(
        "contiguous seam: an object clip dragged back over it mirrors the step",
        bounds == [(-6, 44), (44, 100)]
        and got == [(4.0, 0.0), (34.0, 5.0), (44.0, 3.0), (45.0, 9.0), (65.0, 2.0)],
        f"{bounds} {got}",
    )

    # ---- a split seam: both shots play on as they did -----------------------
    # BACKLOG 2026-09-07 (mirror of mayatk's TestASplitSeamPlaysOnAsItDid):
    # opening a contiguous seam copies the shared sample to the following
    # shot's new start -- or CARRIES it there when only that shot animates the
    # curve. Inserted plain, the key took the default AUTO_CLAMPED handles (a
    # VECTOR seam: the following shot 1.152 off), the insert's subdivision cut
    # the next key's ALIGNED handle (0.431 off), and CONT_ACCEL re-solved each
    # auto run through the seam (a seam on a slope: AUTO_CLAMPED 0.437 off
    # before it, 0.718 after).
    def _split_case(name, keys, handle, op):
        o, st, sq = _seam_scene(name, [("A", 0, 50), ("B", 50, 100)], keys)
        fc = _loc_x(o)
        for kp in fc.keyframe_points:
            kp.handle_left_type = kp.handle_right_type = handle
        fc.update()
        a0 = [fc.evaluate(f) for f in range(0, 51)]
        b0 = [fc.evaluate(f) for f in range(50, 101)]
        if op == "grow":
            sq.resize_shot_bounds(st.shot_by_name("A").shot_id, 0, 60)
        else:
            sq.move_shot(st.shot_by_name("B").shot_id, 60)
        a1 = [fc.evaluate(f) for f in range(0, 51)]
        b1 = [fc.evaluate(f + 10) for f in range(50, 101)]
        da = max(abs(x - y) for x, y in zip(a0, a1))
        db = max(abs(x - y) for x, y in zip(b0, b1))
        return fc, da, db

    _split_keys = {
        "extremum": seam_keys,
        "slope": ((10, 0), (40, 3), (50, 5), (70, 9), (90, 2)),
    }
    for _where, _keys in _split_keys.items():
        for _handle in ("AUTO", "AUTO_CLAMPED", "VECTOR", "ALIGNED"):
            for _op in ("grow", "move"):
                _fc, _da, _db = _split_case(
                    f"Split{_where}{_handle}{_op}", _keys, _handle, _op
                )
                check(
                    f"a split {_handle} seam ({_where}, {_op}): both shots play on",
                    _da < 1e-3 and _db < 1e-3,
                    f"A {_da:.5f} B {_db:.5f}",
                )
    # Keyed from the seam on, nothing before it: the seam sample is B's.
    _carried = ((50, 3), (70, 9), (90, 2))
    # Keyed before A and through B: A plays the ramp into the seam sample, so
    # it is shared, copied, never carried (mirror of mayatk's, the one rule).
    _played_into = ((-30, 1), (50, 3), (70, 9), (90, 2))
    for _handle in ("AUTO", "AUTO_CLAMPED", "VECTOR", "ALIGNED"):
        _fc, _da, _db = _split_case(f"Carried{_handle}", _carried, _handle, "move")
        check(
            f"a carried {_handle} opening pose: the following shot plays on",
            _da < 1e-4 and _db < 1e-3,
            f"A {_da:.5f} B {_db:.5f}",
        )
        _fc, _da, _db = _split_case(
            f"PlayedInto{_handle}", _played_into, _handle, "move"
        )
        check(
            f"a {_handle} seam sample the preceding shot plays into is shared",
            _da < 1e-4 and _db < 1e-3,
            f"A {_da:.5f} B {_db:.5f}",
        )
    # A claimed carried sample (B's start-bound sample) leaves no claim behind
    # on the frame it was cut from (mirror of mayatk's).
    _o, _st, _sq = _seam_scene("CarriedClaim", [("A", 0, 50), ("B", 50, 100)], _carried)
    _key = _ShotSequencerInternal._fc_key(_o.name, _loc_x(_o))
    _sq.ledger.record_key(_key, 50.0, _st.shot_by_name("B").shot_id, "start")
    _sq.move_shot(_st.shot_by_name("B").shot_id, 60)
    _times = [round(kp.co[0], 3) for kp in _loc_x(_o).keyframe_points]
    check(
        "a carried sample leaves no claim behind at its old frame",
        _times == [60.0, 80.0, 100.0] and _sq.ledger.key_times(_key) == [60.0],
        f"{_times} claims={_sq.ledger.key_times(_key)}",
    )
    # ...and an UNCLAIMED one -- the animator's own opening pose -- lands
    # unclaimed: carried, it is still their key, not a sample the system made
    # (claimed, content scans skip it and a bound edit may move or cut it).
    _o, _st, _sq = _seam_scene("CarriedOwn", [("A", 0, 50), ("B", 50, 100)], _carried)
    _key = _ShotSequencerInternal._fc_key(_o.name, _loc_x(_o))
    _sq.move_shot(_st.shot_by_name("B").shot_id, 60)
    _times = [round(kp.co[0], 3) for kp in _loc_x(_o).keyframe_points]
    check(
        "a carried animator pose stays the animator's",
        _times == [60.0, 80.0, 100.0] and _sq.ledger.key_times(_key) == [],
        f"{_times} claims={_sq.ledger.key_times(_key)}",
    )
    # So do a lossless merge's cut keys (mirror of mayatk's): closing gaps
    # onto agreeing poses, B's 110 and C's 120 both land on 100 and one is
    # cut at its old frame, where C's animator key from 140 then lands.
    _o, _st, _sq = _seam_scene(
        "MergeClaim",
        [("A", 0, 50), ("B", 60, 110), ("C", 120, 170)],
        ((0, 0), (50, 2), (60, 2), (110, 4), (120, 4), (130, 5), (140, 7), (170, 9)),
    )
    _key = _ShotSequencerInternal._fc_key(_o.name, _loc_x(_o))
    for _t, _shot, _edge in (
        (50, "A", "end"),
        (60, "B", "start"),
        (110, "B", "end"),
        (120, "C", "start"),
    ):
        _sq.ledger.record_key(_key, float(_t), _st.shot_by_name(_shot).shot_id, _edge)
    _sq.respace(gap=0, start_frame=0)
    _times = [round(kp.co[0], 3) for kp in _loc_x(_o).keyframe_points]
    check(
        "a lossless merge's cut keys leave no claim behind",
        _times == [0.0, 50.0, 100.0, 110.0, 120.0, 150.0]
        and _sq.ledger.key_times(_key) == [50.0, 100.0],
        f"{_times} claims={_sq.ledger.key_times(_key)}",
    )

    def _halves(fc, t):
        kp = next(k for k in fc.keyframe_points if abs(k.co[0] - t) < 1e-3)
        return kp.handle_left_type, kp.handle_right_type, kp

    # A seam the split did not move keeps its types; one it did is frozen,
    # the shot-facing half exactly where it was while shared.
    # The original is the gap hold's now, its handles frozen flat where they
    # sat (ledger format 2).
    _fc, _da, _db = _split_case("SplitGate", seam_keys, "AUTO_CLAMPED", "move")
    _orig = _halves(_fc, 50)[2]
    check(
        "a split AUTO_CLAMPED extremum keeps its handle types",
        _halves(_fc, 60)[:2] == ("AUTO_CLAMPED",) * 2
        and abs(_orig.handle_left[1] - _orig.co[1]) < 1e-6
        and abs(_orig.handle_right[1] - _orig.co[1]) < 1e-6,
        f"50 {_halves(_fc, 50)[:2]} 60 {_halves(_fc, 60)[:2]}",
    )
    _o, _st, _sq = _seam_scene(
        "SplitFreeze", [("A", 0, 50), ("B", 50, 100)], _split_keys["slope"]
    )
    _fc = _loc_x(_o)
    for _kp in _fc.keyframe_points:
        _kp.handle_left_type = _kp.handle_right_type = "AUTO"
    _fc.update()
    _shared = _halves(_fc, 50)[2]
    _roff = _shared.handle_right[1] - _shared.co[1]
    _sq.move_shot(_st.shot_by_name("B").shot_id, 60)
    _lt, _rt, _copy = _halves(_fc, 60)
    check(
        "a split AUTO seam on a slope: the copy is frozen at the shared handle",
        (_lt, _rt) == ("FREE", "FREE")
        and abs(_copy.handle_right[1] - _copy.co[1] - _roff) < 1e-4,
        f"{_lt}/{_rt} right {_copy.handle_right[1] - _copy.co[1]:.4f} vs {_roff:.4f}",
    )

    # ---- a keyless flush seam: every op that opens it keeps both shots -------
    # BACKLOG 2026-10-07 (decided 2026-10-10; mirror of mayatk's
    # TestAMidMotionSeamKeepsBothSides): with NO key on a flush seam the
    # segment crossing it was both shots', so pulling B away re-timed it --
    # A 1.47 off and B 1.20 for a 10-frame move (headless 5.1, AUTO_CLAMPED).
    # The one rule: an op on one shot never changes what another plays inside
    # its own span.  _reconcile_boundaries pins A's own pose on the seam
    # (ShotPlanner.keyless_seam; _insert_shape_keys) before anything moves.
    _kl_keys = ((0, 0), (40, 3), (100, 10))

    def _keyless_case(label, handle, setup, op, b_shift=None):
        o, st, sq = _seam_scene(
            f"Keyless{label}{handle}", [("A", 0, 50), ("B", 50, 100)], _kl_keys
        )
        fc = _loc_x(o)
        for kp in fc.keyframe_points:
            kp.handle_left_type = kp.handle_right_type = handle
        fc.update()
        setup(sq, o, fc)
        a, b = sq.sorted_shots()[0], sq.sorted_shots()[-1]
        a_span, b_span = (a.start, a.end), (b.start, b.end)
        a0 = [fc.evaluate(f) for f in range(int(a_span[0]), int(a_span[1]) + 1)]
        b0 = [fc.evaluate(f) for f in range(int(b_span[0]), int(b_span[1]) + 1)]
        op(sq, a.shot_id, b.shot_id)
        shift = sq.shot_by_id(b.shot_id).start - b_span[0]
        shift = shift if b_shift is None else b_shift
        a1 = [fc.evaluate(f) for f in range(int(a_span[0]), int(a_span[1]) + 1)]
        b1 = [fc.evaluate(f + shift) for f in range(int(b_span[0]), int(b_span[1]) + 1)]
        da = max(abs(x - y) for x, y in zip(a0, a1))
        db = max(abs(x - y) for x, y in zip(b0, b1))
        return da, db, len(a0) + len(b0), (o, fc, st, sq)

    def _kl_none(sq, o, fc):
        pass

    def _kl_split(sq, o, fc):
        sq.store.remove_shot(sq.sorted_shots()[1].shot_id)
        sq.store.update_shot(sq.sorted_shots()[0].shot_id, end=100)
        sq.split_shot(sq.sorted_shots()[0].shot_id, 50)

    def _kl_ctrl(sq, o, fc):
        sq.set_shot_edge(sq.sorted_shots()[0].shot_id, new_end=45, push=True)
        sq.reconcile_system_edits(follow=False)

    def _kl_animator(sq, o, fc):
        for t in (45, 55):
            o.location = (fc.evaluate(t), 0.0, 0.0)
            o.keyframe_insert(data_path="location", index=0, frame=t)

    _kl_cases = (
        (
            "split then move the tail",
            _kl_split,
            lambda s, a, b: s.move_shot(b, 60),
            None,
        ),
        ("move the second shot", _kl_none, lambda s, a, b: s.move_shot(b, 60), None),
        ("Ctrl push then a move", _kl_ctrl, lambda s, a, b: s.move_shot(b, 55), None),
        (
            "insert a shot between",
            _kl_none,
            lambda s, a, b: s.insert_shot("N", 10, after_shot_id=a, gap=0),
            None,
        ),
        (
            "room at B's head",
            _kl_none,
            lambda s, a, b: s.add_shot_space(b, 10, edge="leading"),
            10.0,
        ),
        (
            "room at A's tail",
            _kl_none,
            lambda s, a, b: s.add_shot_space(a, 10, edge="trailing"),
            None,
        ),
        (
            "a plain grow of A",
            _kl_none,
            lambda s, a, b: s.resize_shot_bounds(a, 0, 60),
            None,
        ),
        (
            "an animator's keys across the seam, then a move",
            _kl_animator,
            lambda s, a, b: s.move_shot(b, 60),
            None,
        ),
    )
    for _handle in ("AUTO_CLAMPED", "AUTO", "VECTOR"):
        for _label, _setup, _op, _shift in _kl_cases:
            _da, _db, _n, _ = _keyless_case(_label, _handle, _setup, _op, _shift)
            check(
                f"flush keyless seam ({_handle}), {_label}: both shots play on",
                _n > 0 and _da < 1e-4 and _db < 1e-4,
                f"A {_da:.5f} B {_db:.5f} samples {_n}",
            )
        # split_shot(gap=10): A over [0, 50], B over [50, 100] shifted 10.
        _o, _st, _sq = _seam_scene(f"KeylessGap{_handle}", [("S", 0, 100)], _kl_keys)
        _fc = _loc_x(_o)
        for _kp in _fc.keyframe_points:
            _kp.handle_left_type = _kp.handle_right_type = _handle
        _fc.update()
        _before = [_fc.evaluate(f) for f in range(0, 101)]
        _tail = _sq.split_shot(_sq.sorted_shots()[0].shot_id, 50, gap=10)
        _da = max(abs(_before[f] - _fc.evaluate(f)) for f in range(0, 51))
        _db = max(abs(_before[f] - _fc.evaluate(f + 10)) for f in range(50, 101))
        check(
            f"flush keyless seam ({_handle}), split_shot(gap=10): both shots play on",
            _tail.start == 60.0 and _da < 1e-4 and _db < 1e-4,
            f"tail {_tail.start} A {_da:.5f} B {_db:.5f}",
        )
        # Closing the gap again gives both shots back exactly.
        _da, _db, _n, (_o, _fc, _st, _sq) = _keyless_case(
            "close", _handle, _kl_none, lambda s, a, b: s.move_shot(b, 60)
        )
        _before = [round(_fc.evaluate(f), 6) for f in range(0, 51)]
        _sq.move_shot(_sq.sorted_shots()[1].shot_id, 50)
        _d = max(abs(_before[f] - _fc.evaluate(f)) for f in range(0, 51))
        check(
            f"flush keyless seam ({_handle}): closing the gap again gives A back",
            _d < 1e-4,
            f"{_d:.5f}",
        )

    # The pin is A's end, claimed ``stays``: a later plain grow of A's end
    # disowns it where it is (followed, it re-timed A's last ramp).
    _da, _db, _n, (_o, _fc, _st, _sq) = _keyless_case(
        "stays", "AUTO_CLAMPED", _kl_none, lambda s, a, b: s.move_shot(b, 60)
    )
    _key = _ShotSequencerInternal._fc_key(_o.name, _fc)
    _a_id = _sq.sorted_shots()[0].shot_id
    _claimed = (50.0, _a_id, "end") in _sq.ledger.key_records(_key) and (
        _sq.ledger.key_stays(_key, 50.0)
    )
    _a0 = [_fc.evaluate(f) for f in range(0, 51)]
    _sq.resize_shot_bounds(_a_id, 0, 55)
    _times = [round(kp.co[0], 3) for kp in _fc.keyframe_points]
    _d = max(abs(x - _fc.evaluate(f)) for f, x in zip(range(0, 51), _a0))
    check(
        "a seam pin is A's end, stays: a plain grow disowns it in place",
        _claimed
        and 50.0 in _times
        and 50.0 not in _sq.ledger.key_times(_key)
        and _d < 1e-4,
        f"claimed={_claimed} {_times} claims={_sq.ledger.key_times(_key)} A {_d:.5f}",
    )
    # A landing that fills the room (Move to Shot's expansion, pending_bounds)
    # pins nothing in its way.
    _o, _st, _sq = _seam_scene(
        "KeylessPending", [("A", 0, 50), ("B", 50, 100)], _kl_keys
    )
    _a_id = _st.shot_by_name("A").shot_id
    with _sq.pending_bounds({_a_id: (0.0, 60.0)}):
        _sq.ripple_downstream(_a_id, 60.0, 10.0)
    _times = [round(kp.co[0], 3) for kp in _loc_x(_o).keyframe_points]
    _key = _ShotSequencerInternal._fc_key(_o.name, _loc_x(_o))
    check(
        "a landing that fills the room pins no keyless seam",
        _times == [0.0, 40.0, 110.0] and _sq.ledger.key_times(_key) == [],
        f"{_times} claims={_sq.ledger.key_times(_key)}",
    )

    # ---- every op closing a seam to gap 0: flush where the poses agree, one
    # frame apart where they differ (maintainer 2026-10-11; mirror of mayatk's
    # TestAClosingSeamStaysOneFrameApartWhereItsPosesDiffer).
    def _closing_case(
        name, shots, keys, op, spans, authored=(), handles=None, stepped=()
    ):
        # Alone in the scene: a respace moves -- and checks -- every keyed
        # object, so a cube an earlier case left keyed is part of this one.
        for _left in list(bpy.data.objects):
            bpy.data.objects.remove(_left, do_unlink=True)
        o, st, sq = _seam_scene(name, shots, keys)
        # Every key's handles of one type (*handles*: "AUTO" smooths through
        # an extreme, where the default clamps it flat); the keys at
        # *stepped* hold (CONSTANT).
        if handles or stepped:
            fc = _loc_x(o)
            for kp in fc.keyframe_points:
                if handles:
                    kp.handle_left_type = kp.handle_right_type = handles
                if round(kp.co[0]) in stepped:
                    kp.interpolation = "CONSTANT"
            fc.update()
        sq.reconcile_system_edits()
        # Left handles to author (FREE where they sit) before anything is
        # read: under CONT_ACCEL an edit re-solves the auto run beside it.
        fc = _loc_x(o)
        for kp in fc.keyframe_points:
            if round(kp.co[0]) in authored:
                kp.handle_left_type = "FREE"
        fc.update()
        before = {
            n: [_loc_x(o).evaluate(f) for f in range(int(a), int(b) + 1)]
            for n, (a, b) in spans.items()
        }
        op(sq, st)
        offs = {}
        for n, (a, b) in spans.items():
            sh = st.shot_by_name(n)
            fc = _loc_x(o)
            offs[n] = max(
                abs(x - fc.evaluate(f))
                for f, x in zip(
                    range(int(sh.start), int(sh.start) + 1 + int(b - a)), before[n]
                )
            )
        return st, offs

    _abc = [("A", 0, 50), ("B", 50, 100), ("C", 100, 150)]
    _st, _offs = _closing_case(
        "CloseDelete",
        _abc,
        ((0, 0), (40, 2), (50, 3), (70, 8), (100, 5), (130, 1)),
        lambda sq, st: sq.delete_shot(st.shot_by_name("B").shot_id),
        {"A": (0, 50), "C": (100, 150)},
    )
    _c = _st.shot_by_name("C")
    check(
        "a flush delete keeps the next shot's opening a frame apart",
        (_c.start, _c.end) == (51.0, 101.0) and max(_offs.values()) < 1e-4,
        f"C=({_c.start}, {_c.end}) {_offs}",
    )
    _st, _offs = _closing_case(
        "CloseDeleteAgree",
        _abc,
        ((0, 0), (40, 2), (50, 3), (70, 8), (100, 3), (130, 1)),
        lambda sq, st: sq.delete_shot(st.shot_by_name("B").shot_id),
        {"C": (100, 150)},
    )
    check(
        "a flush delete closes flush where the poses agree",
        _st.shot_by_name("C").start == 50.0 and _offs["C"] < 1e-4,
        f"C={_st.shot_by_name('C').start} {_offs}",
    )

    # The held key's handles are derived: the hold froze them (ledger format
    # 2), so the next shot's move no longer re-derives them (the held tail).
    _st, _offs = _closing_case(
        "CloseHeld",
        [("A", 0, 50), ("B", 60, 100)],
        ((0, 0), (20, 5), (60, 9), (90, 2)),
        lambda sq, st: sq.apply_gap(
            0, scope="end", shot_id=st.shot_by_name("A").shot_id
        ),
        {"A": (0, 50), "B": (60, 100)},
    )
    _b = _st.shot_by_name("B")
    check(
        "a collapse onto a held tail keeps one frame",
        (_b.start, _b.end) == (51.0, 91.0) and max(_offs.values()) < 1e-4,
        f"B=({_b.start}, {_b.end}) {_offs}",
    )

    def _respace_twice(sq, st):
        sq.respace(gap=0, start_frame=0)
        sq.respace(gap=0, start_frame=0)

    _st, _offs = _closing_case(
        "CloseRespace",
        [("A", 0, 40), ("B", 50, 90)],
        ((10, 0.0), (40, 1.0), (50, 2.0), (70, 3.0)),
        _respace_twice,
        {"A": (0, 40), "B": (50, 90)},
    )
    _layout = [(s.start, s.end) for s in _st.sorted_shots()]
    check(
        "a respace to 0 keeps a disagreeing seam a frame apart, twice over",
        _layout == [(0.0, 40.0), (41.0, 81.0)] and max(_offs.values()) < 1e-4,
        f"{_layout} {_offs}",
    )
    # A gap holding the animator's key keeps a frame too, its poses agreeing:
    # the retime refuses a zero-width gap (it would cut or stack the key), so
    # closed flush the key stayed where it was and B played it.  Found on
    # SOL_REPLACE_ASSEMBLY pulled with its stepped keys: A04 0.0012 off.
    _st, _offs = _closing_case(
        "CloseRespaceGapKey",
        [("A", 0, 40), ("B", 50, 90)],
        ((10, 0.0), (40, 1.0), (45, 5.0), (50, 1.0), (70, 3.0)),
        lambda sq, st: sq.respace(gap=0, start_frame=0),
        {"A": (0, 40), "B": (50, 90)},
    )
    _layout = [(s.start, s.end) for s in _st.sorted_shots()]
    _gap_keys = [
        round(kp.co[0], 3)
        for kp in _loc_x(bpy.data.objects["CloseRespaceGapKey"]).keyframe_points
        if 40.0 < kp.co[0] < 41.0
    ]
    check(
        "a respace to 0 keeps a frame where the gap holds a key, the key in it",
        _layout == [(0.0, 40.0), (41.0, 81.0)]
        and max(_offs.values()) < 1e-4
        and len(_gap_keys) == 1,
        f"{_layout} {_offs} gap keys {_gap_keys}",
    )
    # A placement closing that gap onto the shot before it, the same
    # (maintainer 2026-10-12, "same as respace"): the key is the STILL shot's,
    # so the slid shot landed over it and played it -- B 0.5 where it played
    # 1.0.  The seam keeps a frame and the key is retimed into it.
    for _label, _op in (
        ("band move", lambda sq, st: sq.move_shot(st.shot_by_name("B").shot_id, 60)),
        (
            "slide",
            lambda sq, st: sq.slide_shot(
                st.shot_by_name("B").shot_id, 60, direction=None
            ),
        ),
        (
            "start",
            lambda sq, st: sq.set_shot_start(
                st.shot_by_name("B").shot_id, 60, ripple=False
            ),
        ),
    ):
        _st, _offs = _closing_case(
            "ClosePlaceGapKey",
            [("A", 0, 60), ("B", 100, 160)],
            ((90, 0.5), (100, 0.0), (110, 1.0)),
            _op,
            {"A": (0, 60), "B": (100, 160)},
        )
        _layout = [(s.start, s.end) for s in _st.sorted_shots()]
        _times = [
            round(kp.co[0], 3)
            for kp in _loc_x(bpy.data.objects["ClosePlaceGapKey"]).keyframe_points
        ]
        check(
            f"a {_label} closing a keyed gap keeps a frame, the key retimed into it",
            _layout == [(0.0, 60.0), (61.0, 121.0)]
            and max(_offs.values()) < 1e-4
            and len([t for t in _times if 60.001 < t < 60.999]) == 1,
            f"{_layout} {_offs} keys {_times}",
        )
    # A Shift edge (a retime) closing a keyed gap, the same (maintainer
    # 2026-10-12, "same rule"): B retimed onto A's end was written across the
    # gap's key and played it, and A played 0.0 for 0.5.  Each edge: B's start
    # onto A, and A's end onto B (the gap's key then A's own tail).
    for _label, _shots, _keys, _op, _spans, _want in (
        (
            "start",
            [("A", 0, 60), ("B", 100, 160)],
            ((90, 0.5), (100, 0.0), (110, 1.0)),
            lambda sq, st: sq.set_shot_edge(
                st.shot_by_name("B").shot_id, new_start=60, scale=True
            ),
            {"A": (0, 60)},
            ([(0.0, 60.0), (61.0, 160.0)], (60.0, 61.0), [61.0, 77.5]),
        ),
        (
            "end",
            [("A", 0, 40), ("B", 50, 90)],
            ((10, 0.0), (40, 1.0), (45, 5.0), (50, 1.0), (70, 3.0)),
            lambda sq, st: sq.set_shot_edge(
                st.shot_by_name("A").shot_id, new_end=50, scale=True
            ),
            {"B": (50, 90)},
            ([(0.0, 49.0), (50.0, 90.0)], (49.0, 50.0), [12.25, 49.0]),
        ),
    ):
        _st, _offs = _closing_case("CloseShiftGapKey", _shots, _keys, _op, _spans)
        _layout = [(s.start, s.end) for s in _st.sorted_shots()]
        _times = [
            round(kp.co[0], 3)
            for kp in _loc_x(bpy.data.objects["CloseShiftGapKey"]).keyframe_points
        ]
        _lo, _hi = _want[1]
        _retimed = _st.sorted_shots()[1 if _label == "start" else 0]
        _inside = [
            t
            for t in _times
            if _retimed.start - 1e-3 <= t <= _retimed.end + 1e-3 and not _lo < t < _hi
        ]
        check(
            f"a Shift {_label} edge closing a keyed gap keeps a frame, the key in it",
            _layout == _want[0]
            and max(_offs.values()) < 1e-4
            and len([t for t in _times if _lo + 1e-3 < t < _hi - 1e-3]) == 1
            and _inside == _want[2],
            f"{_layout} {_offs} keys {_times} retimed {_inside}",
        )

    # ---- explicit placements follow the closing rule (maintainer 2026-10-11,
    # "ALL of them"; mirror of mayatk's TestExplicitPlacementsFollowTheClosingRule)
    # A's last key is the gap hold's, its handles derived and frozen by the
    # hold (ledger format 2).
    _ab = [("A", 0, 40), ("B", 50, 90)]
    _keysets = {
        "differ": (((0, 0), (40, 2), (50, 5), (90, 9)), ()),
        "agree": (((0, 0), (40, 2), (50, 2), (90, 9)), ()),
        "held": (((0, 0), (30, 5), (50, 9), (90, 2)), ()),
    }
    _ops = {
        "band move": lambda sq, st: sq.move_shot(st.shot_by_name("B").shot_id, 40),
        "slide": lambda sq, st: sq.slide_shot(
            st.shot_by_name("B").shot_id, 40, direction=None
        ),
    }
    for _op_name, _op in _ops.items():
        for _kind, (_keys, _auth) in _keysets.items():
            _st, _offs = _closing_case(
                f"Place{_op_name.title().replace(' ', '')}{_kind.title()}",
                _ab,
                _keys,
                _op,
                {"A": (0, 40), "B": (50, 90)},
                authored=_auth,
            )
            _want = 40.0 if _kind == "agree" else 41.0
            _b = _st.shot_by_name("B")
            check(
                f"a {_op_name} lands B {'flush' if _kind == 'agree' else 'a frame short'}"
                f" ({_kind} poses), both shots playing on",
                _b.start == _want and max(_offs.values()) < 1e-4,
                f"B={_b.start} {_offs}",
            )
    for _kind, (_keys, _auth) in _keysets.items():
        _st, _offs = _closing_case(
            f"PlaceCtrlEdge{_kind.title()}",
            _ab,
            _keys,
            lambda sq, st: sq.set_shot_edge(
                st.shot_by_name("A").shot_id, new_end=50, push=True
            ),
            {"A": (0, 49), "B": (50, 90)},
            authored=_auth,
        )
        _want = 50.0 if _kind == "agree" else 49.0
        _a = _st.shot_by_name("A")
        check(
            f"a ctrl edge ends A {'flush' if _kind == 'agree' else 'a frame short'}"
            f" ({_kind} poses), both shots playing on",
            _a.end == _want and max(_offs.values()) < 1e-4,
            f"A end={_a.end} {_offs}",
        )

    # A merge keeps what each side played: Q +7 between flush P and R, R's
    # copy of the shared sample merged with Q's original (mirror of mayatk's).
    _st, _offs = _closing_case(
        "MergeStep",
        [("P", 0, 50), ("Q", 50, 100), ("R", 100, 150)],
        ((60, 3), (100, 0), (120, 9)),
        lambda sq, st: sq.move_shot(st.shot_by_name("Q").shot_id, 57),
        {"R": (100, 150)},
    )
    check(
        "a merge keeps what the later side played (R ripples, Q lands on its copy)",
        _st.shot_by_name("R").start == 107.0 and _offs["R"] < 1e-4,
        f"R={_st.shot_by_name('R').start} {_offs}",
    )

    _st, _offs = _closing_case(
        "PlaceLanding",
        [("A", 0, 40), ("B", 40, 80), ("C", 80, 120)],
        ((10, 0), (25, 4), (40, -1), (55, 3), (80, 0), (95, 6), (120, 2)),
        lambda sq, st: sq.move_sequences_to_shot(
            [{"kind": "anim", "obj": "PlaceLanding", "start": 10.0, "end": 40.0}],
            st.shot_by_name("B").shot_id,
        ),
        {"C": (80, 120)},
    )
    _b, _c = _st.shot_by_name("B"), _st.shot_by_name("C")
    check(
        "a Move to Shot landing on a flush seam keeps the next shot's opening",
        _c.start - _b.end == 1.0 and _offs["C"] < 1e-4,
        f"B end {_b.end} C start {_c.start} {_offs}",
    )

    # ---- Move to Shot's head landing (mirror of mayatk's) -----------------------
    # P's run lands in front of Q's content; the block owns Q's start, a frame
    # after P's end where P closes on a different pose; P's close is kept.
    for _first, _want in ((0, 51.0), (5, 50.0)):
        for _left in list(bpy.data.objects):
            bpy.data.objects.remove(_left, do_unlink=True)
        _o, _st, _sq = _seam_scene(
            "HeadLand",
            [("P", 0, 50), ("Q", 50, 100)],
            ((10, _first), (20, 4), (30, 2), (50, 5), (70, 8), (100, 3)),
        )
        _sq.reconcile_system_edits()
        _close = _loc_x(_o).evaluate(50)
        _sq.move_sequences_to_shot(
            [{"kind": "anim", "obj": _o.name, "start": 10.0, "end": 30.0}],
            _st.shot_by_name("Q").shot_id,
        )
        _q = _st.shot_by_name("Q")
        _fc = _loc_x(_o)
        _landed = [round(_fc.evaluate(_q.start + d), 4) for d in (0, 10, 20)]
        check(
            f"a head landing {'keeps a frame' if _want > 50 else 'lands flush'}"
            " and the shot before keeps its closing pose",
            _q.start == _want
            and abs(_fc.evaluate(50) - _close) < 1e-4
            and _landed == [float(_first), 4.0, 2.0],
            f"Q start {_q.start} close {_close:.4f}->{_fc.evaluate(50):.4f} {_landed}",
        )

    # The block lands clear of Q's end, nothing keys the curve after it until
    # past R's start: R's opening is pinned (mirror of mayatk's).
    _st, _offs = _closing_case(
        "HeadNext",
        [("P", 0, 50), ("Q", 50, 100), ("R", 100, 150)],
        ((10, 9), (30, 8), (50, 0)),
        lambda sq, st: sq.move_sequences_to_shot(
            [{"kind": "anim", "obj": "HeadNext", "start": 10.0, "end": 30.0}],
            st.shot_by_name("Q").shot_id,
        ),
        {"R": (100, 150)},
    )
    check(
        "a head landing leaves the next shot its pose",
        _offs["R"] < 1e-4,
        f"{_offs}",
    )

    # A run from AFTER the destination, of an object it keys nothing of, is
    # anchored to its start -- on a flush seam the shot before's last frame
    # (mirror of mayatk's test_a_landing_from_after_*; SOL gap 0: B10_1's
    # last frame 98.35 off).  The destination opens a frame later where the
    # poses differ.
    for _first, _want in ((9, 51.0), (0, 50.0)):
        _st, _offs = _closing_case(
            f"Anchored{_first}",
            [("P", 0, 50), ("Q", 50, 100), ("R", 100, 150)],
            ((10, 0), (105, _first), (125, 4)),
            lambda sq, st, _n=f"Anchored{_first}": sq.move_sequences_to_shot(
                [{"kind": "anim", "obj": _n, "start": 105.0, "end": 125.0}],
                st.shot_by_name("Q").shot_id,
            ),
            {"P": (0, 50)},
            stepped=(10,),
        )
        check(
            f"a landing from after {'keeps a frame' if _want > 50 else 'lands flush'}"
            " and the shot before keeps its close",
            _st.shot_by_name("Q").start == _want and _offs["P"] < 1e-4,
            f"Q start {_st.shot_by_name('Q').start} {_offs}",
        )

    # A leading pad slides Q's content on and puts its start back: the gap
    # hold's stop pin on that start is the content's opening pose and stays
    # with it (mirror of mayatk's TestALeadingPadKeepsTheShotsOpening; SOL
    # harness: "A01_2" 1.65 off over 16 frames).
    for _left in list(bpy.data.objects):
        bpy.data.objects.remove(_left, do_unlink=True)
    _o, _st, _sq = _seam_scene(
        "LeadPad",
        [("P", 0, 50), ("Q", 60, 110), ("R", 120, 170)],
        ((10, 2), (90, 8), (150, 1)),
    )
    _st.gap = 10.0
    _sq.reconcile_system_edits()
    _p0 = [_loc_x(_o).evaluate(f) for f in range(0, 51)]
    _q0 = [_loc_x(_o).evaluate(f) for f in range(60, 111)]
    _sq.add_shot_space(_st.shot_by_name("Q").shot_id, 10.0, edge="leading")
    _fc = _loc_x(_o)
    _q = _st.shot_by_name("Q")
    _p_off = max(abs(v - _fc.evaluate(f)) for f, v in enumerate(_p0))
    _q_off = max(abs(v - _fc.evaluate(_q.start + 10 + i)) for i, v in enumerate(_q0))
    check(
        "a leading pad keeps the shot's opening pose with its content",
        _q.start == 60.0 and _p_off < 1e-4 and _q_off < 1e-4,
        f"Q start {_q.start} P off {_p_off:.5f} Q off {_q_off:.5f}",
    )

    # ---- a Shift retime keeps its flush neighbour (mirror of mayatk's) --------
    # BACKLOG 2026-10-11: the ripple's copy and the retimed sample stacked on
    # the seam; keyless, the next shot opened off; shrinking, its slope scaled.
    _abc3 = [("A", 0, 50), ("B", 50, 100), ("C", 100, 150)]
    for _label, _keys, _shot, _span, _watch, _wspan in (
        (
            "keyed grow",
            ((0, 0), (40, 2), (50, 3), (100, 5)),
            "A",
            (0, 60),
            "B",
            (50, 100),
        ),
        ("keyless grow", ((0, 0), (40, 2), (100, 5)), "A", (0, 60), "B", (50, 100)),
        (
            "keyed shrink",
            ((0, 0), (40, 2), (50, 3), (100, 5)),
            "A",
            (0, 45),
            "B",
            (50, 100),
        ),
        (
            "start grow",
            ((10, 0), (40, 2), (50, 3), (60, 4), (100, 5)),
            "B",
            (40, 100),
            "A",
            (0, 50),
        ),
    ):
        _name = "Retime" + _label.title().replace(" ", "")
        _st, _offs = _closing_case(
            _name,
            _abc3,
            _keys,
            lambda sq, st, _shot=_shot, _span=_span: sq.resize_shot(
                st.shot_by_name(_shot).shot_id, *_span
            ),
            {_watch: _wspan},
        )
        _t = sorted(kp.co[0] for kp in _loc_x(bpy.data.objects[_name]).keyframe_points)
        _stacked = [b for a, b in zip(_t, _t[1:]) if b - a < 0.01]
        check(
            f"a Shift retime ({_label}) stacks nothing and {_watch} plays on",
            not _stacked and _offs[_watch] < 1e-4,
            f"keys {[round(x, 3) for x in _t]} {_offs}",
        )

    # ---- a plain edge shrink closes its flush seam under the closing rule ------
    # (mirror of mayatk's TestAPlainEdgeShrinkKeepsItsFlushNeighbour; BACKLOG
    # 2026-10-11: a ramp crossing the seam keyless was compressed between the
    # two shots' keys, SOL "C02_2" 0.096 off).  Each shot plays on from
    # wherever it starts; the neighbour lands a frame short where it differs.
    _ramp = ((10, 0), (30, 2), (80, 6), (120, 1))
    _tail = {"A": (0, 46), "B": (50, 100), "C": (100, 150)}
    for _label, _keys, _shot, _span, _layout_want, _spans, _handles in (
        (
            "keyless ramp, poses differ",
            _ramp,
            "A",
            (0, 46),
            [(0.0, 46.0), (47.0, 97.0), (97.0, 147.0)],
            _tail,
            None,
        ),
        (
            # Symmetric about 48 as a whole: CONT_ACCEL solves the handles
            # over the curve's whole run.
            "keyless dip, poses agree",
            ((6, 5), (26, 0), (70, 0), (90, 5)),
            "A",
            (0, 46),
            [(0.0, 46.0), (46.0, 96.0), (96.0, 146.0)],
            _tail,
            "AUTO",
        ),
        (
            "a keyed opening rides",
            ((10, 2), (50, 2), (80, 6), (120, 1)),
            "A",
            (0, 46),
            [(0.0, 46.0), (46.0, 96.0), (96.0, 146.0)],
            _tail,
            None,
        ),
        (
            "head shrink",
            _ramp,
            "B",
            (54, 100),
            [(3.0, 53.0), (54.0, 100.0), (100.0, 150.0)],
            {"A": (0, 50), "B": (54, 100), "C": (100, 150)},
            None,
        ),
    ):
        _name = "Shrink" + "".join(w.title() for w in _label.split(",")[0].split())
        _st, _offs = _closing_case(
            _name,
            _abc3,
            _keys,
            lambda sq, st, _shot=_shot, _span=_span: sq.resize_shot_bounds(
                st.shot_by_name(_shot).shot_id, *_span
            ),
            _spans,
            handles=_handles,
        )
        _t = sorted(kp.co[0] for kp in _loc_x(bpy.data.objects[_name]).keyframe_points)
        _stacked = [b for a, b in zip(_t, _t[1:]) if b - a < 0.01]
        _layout = [(s.start, s.end) for s in _st.sorted_shots()]
        check(
            f"a plain edge shrink ({_label}) closes its seam and every shot plays on",
            _layout == _layout_want and not _stacked and max(_offs.values()) < 1e-4,
            f"{_layout} keys {[round(x, 3) for x in _t]} {_offs}",
        )

    # Across a gap (mirror of mayatk's test_a_trim / test_a_grow_across_a_gap):
    # a ramp keyed at 5 and 200 crosses every shot, and Q's members leave it
    # out -- the gap hold never steps Q's start pin, so Q|R stays a keyless
    # crossing the ripple re-timed (SOL pull: trimming "A01_2" played "A02"
    # 1.5 off).
    for _label, _op, _q_to, _r_start in (
        (
            "a trim",
            lambda sq, st: sq.trim_shot_to_content(
                st.shot_by_name("Q").shot_id, edge="trailing"
            ),
            30,
            100.0,
        ),
        (
            "a grow",
            lambda sq, st: sq.resize_shot_bounds(st.shot_by_name("Q").shot_id, 60, 116),
            50,
            126.0,
        ),
        (
            # The gap hold ends the crossing on Q's own end and pins R's
            # start (pythontk ``_through_pins``), so a ripple of R keeps Q.
            "a slide of R",
            lambda sq, st: sq.slide_shot(
                st.shot_by_name("R").shot_id, 130, direction="downstream"
            ),
            50,
            130.0,
        ),
    ):
        for _left in list(bpy.data.objects):
            bpy.data.objects.remove(_left, do_unlink=True)
        BlenderShotStore.clear_active()
        _mover = bpy.data.objects.new("GapMover", None)
        bpy.context.scene.collection.objects.link(_mover)
        for _f, _v in ((62, 0), (90, 5)):
            _mover.location = (0.0, float(_v), 0.0)
            _mover.keyframe_insert(data_path="location", index=1, frame=_f)
        _ramp = bpy.data.objects.new("GapRamp", None)
        bpy.context.scene.collection.objects.link(_ramp)
        for _f, _v in ((5, 0), (200, 10)):
            _ramp.location = (float(_v), 0.0, 0.0)
            _ramp.keyframe_insert(data_path="location", index=0, frame=_f)
        _st = BlenderShotStore()
        _st.gap = 10.0
        for _n, _s, _e, _objs in (
            ("P", 0, 50, ["GapRamp"]),
            ("Q", 60, 110, ["GapMover"]),
            ("R", 120, 170, ["GapRamp"]),
            ("S", 180, 230, ["GapRamp"]),
        ):
            _st.define_shot(_n, _s, _e, objects=_objs)
        _sq = ShotSequencer(_st)
        _sq.reconcile_system_edits()
        _b = {
            n: [_loc_x(_ramp).evaluate(f) for f in range(int(s), int(e) + 1)]
            for n, s, e in (("Q", 60, 60 + _q_to), ("R", 120, 170), ("S", 180, 230))
        }
        _op(_sq, _st)
        _fc = _loc_x(_ramp)
        _off = {
            n: max(
                abs(v - _fc.evaluate(_st.shot_by_name(n).start + i))
                for i, v in enumerate(vals)
            )
            for n, vals in _b.items()
        }
        check(
            f"{_label} across a gap leaves the shot and the shots after playing on",
            _st.shot_by_name("R").start == _r_start and max(_off.values()) < 1e-4,
            f"R start {_st.shot_by_name('R').start} {_off}",
        )

    # A head shrink behind a held gap: the stop pin on Q's start is superseded
    # by Q's pose pinned on its new start, and goes (mirror of mayatk's
    # test_a_head_shrink_behind_a_held_gap_keeps_the_held_tail; SOL "A01_1").
    for _left in list(bpy.data.objects):
        bpy.data.objects.remove(_left, do_unlink=True)
    _o, _st, _sq = _seam_scene(
        "HeldGapHead",
        [("P", 0, 50), ("Q", 60, 110), ("R", 120, 170)],
        ((0, 0), (40, 5), (90, 9), (130, 1)),
    )
    _st.gap = 10.0
    _sq.reconcile_system_edits()
    _p0 = [_loc_x(_o).evaluate(f) for f in range(0, 51)]
    _q0 = [_loc_x(_o).evaluate(f) for f in range(64, 111)]
    _sq.resize_shot_bounds(_st.shot_by_name("Q").shot_id, 64, 110)
    _fc = _loc_x(_o)
    _p_off = max(abs(v - _fc.evaluate(4 + i)) for i, v in enumerate(_p0))
    _q_off = max(abs(v - _fc.evaluate(64 + i)) for i, v in enumerate(_q0))
    check(
        "a head shrink behind a held gap keeps the shot before's held tail",
        _st.shot_by_name("P").start == 4.0 and _p_off < 1e-4 and _q_off < 1e-4,
        f"P start {_st.shot_by_name('P').start} P off {_p_off:.5f} Q off {_q_off:.5f}",
    )

    # ---- Move to Shot copies a shared seam sample (mirror of mayatk's) ----------
    _pqr = [("P", 0, 50), ("Q", 50, 100), ("R", 100, 150)]
    _st, _offs = _closing_case(
        "SharedFirst",
        _pqr,
        ((50, 3), (70, 8), (90, 5)),
        lambda sq, st: sq.move_sequences_to_shot(
            [{"kind": "anim", "obj": "SharedFirst", "start": 50.0, "end": 70.0}],
            st.shot_by_name("R").shot_id,
        ),
        {"P": (0, 50)},
    )
    check(
        "a run opening on the curve's first key leaves it: the shot before plays on",
        _offs["P"] < 1e-4,
        f"{_offs}",
    )
    _st, _offs = _closing_case(
        "SharedLast",
        _pqr,
        ((60, 1), (80, 4), (100, 7), (130, 2)),
        lambda sq, st: sq.move_sequences_to_shot(
            [{"kind": "anim", "obj": "SharedLast", "start": 60.0, "end": 100.0}],
            st.shot_by_name("P").shot_id,
        ),
        {"R": (100, 150)},
    )
    check(
        "a run closing on the next shot's opening leaves it: that shot plays on",
        _offs["R"] < 1e-4,
        f"{_offs}",
    )

    # ---- an audio clip moves by what its VISIBLE part moved ---------------
    # The widget draws only the part of a strip inside its shot and a drag
    # reports where THAT landed; measured from the strip's own start the move
    # was off by the part before the shot.
    import wave

    import pythontk as ptk
    from blendertk.audio_utils._audio_utils import AudioUtils as _Audio

    with ptk.TempArtifacts(prefix="btk_seq_visaudio_") as vtmp:
        vwav = vtmp.path(".wav")
        with wave.open(vwav, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(8000)
            wf.writeframes(b"\x00\x00" * 4000)  # 0.5 s of silence
        BlenderShotStore.clear_active()
        vst = BlenderShotStore()
        vst.define_shot("A", 0, 50, objects=[])
        b_shot = vst.define_shot("B", 60, 100, objects=[])
        strip = _Audio.add_clip(vwav, frame_start=55, scene=bpy.context.scene)
        info = _Audio.get_clip(strip)
        strip_data = {
            "is_audio": True,
            "audio_track_id": strip,
            "shot_id": b_shot.shot_id,
            "orig_start": float(info["frame_start"]),
            "orig_end": float(info["frame_end"]),
            "vis_start": 60.0,
        }
        _move_clip(strip_data, ShotSequencer(vst), 62.0)  # the visible part moved +2
        moved = _Audio.get_clip(strip)["frame_start"]
        vshots = [(s.start, s.end) for s in vst.sorted_shots()]
        check(
            "audio clip: moved by its visible part's +2, not +7, and no shot moved",
            moved == 57 and vshots == [(0, 50), (60, 100)],
            f"{moved} {vshots}",
        )
        _Audio.remove_clip(strip)

    # ---- a refused drag reports instead of raising (mirror of mayatk) -------
    # The planner REFUSES a ripple that would force two shots' disagreeing
    # poses onto one frame; measured in Maya, that refusal came out of the
    # clip handlers as a traceback at the end of a mouse drag.
    from pythontk import ShotBoundaryConflict

    class _RefusingHost(_KeysHost):
        def __init__(self, widget, sequencer):
            super().__init__(widget, sequencer)
            self.footers, self.warned = [], []
            self._shifted_out_keys = {}
            self._audio_segments_cache = None
            warned = self.warned

            class _Log:
                def warning(self, msg, *a, **k):
                    warned.append(msg)

                def __getattr__(self, _name):
                    return lambda *a, **k: None

            self.logger = _Log()

        def _set_footer(self, text, *a, **k):
            self.footers.append(text)

        def _expand_shot_range(self, *_a, **_kw):
            raise ShotBoundaryConflict([("crv", 1.0, [0.0, 1.0])])

    for label, drag in (
        ("a single clip drag", lambda h: h.on_clip_moved(1, 40.0)),
        ("a batch clip drag", lambda h: h.on_clips_batch_moved([(1, 40.0)])),
    ):
        ro, rst, rsq = _seam_scene("RefuseMv", [("A", 10, 20)], ((10, 0), (20, 1)))
        clip = _FakeClip(
            {
                "obj": ro.name,
                "attr_name": "translateX",
                "shot_id": rst.shot_by_name("A").shot_id,
                "orig_start": 10.0,
                "orig_end": 20.0,
            }
        )
        rhost = _RefusingHost(_FakeWidget(clip), rsq)
        # A refusal keeps every restore point (the store's ``scene_edit``:
        # the head may have rippled before the tail refused).
        rdepth = len(rst._boundary_undo)
        try:
            drag(rhost)
            raised = None
        except ShotBoundaryConflict as exc:  # the defect: a drag-end traceback
            raised = exc
        rdropped = len(rst._boundary_undo) < rdepth
        want = str(ShotBoundaryConflict([("crv", 1.0, [0.0, 1.0])]))
        check(
            f"refused drag: {label} reports the refusal instead of raising",
            raised is None
            and rhost.warned == [want]
            and rhost.footers[-1:] == [want]
            and not rdropped,
            f"raised={raised!r} warned={rhost.warned} footers={rhost.footers} "
            f"dropped={rdropped}",
        )

    # ---- _delete_clip_keys: whole-object clips scope to TRANSFORM curves ----
    # (pre-fix: every action fcurve in span was wiped — custom props included)
    bpy.ops.mesh.primitive_cube_add()
    del_obj = bpy.context.active_object
    del_obj.name = "DelScope"
    del_obj.location = (1.0, 0.0, 0.0)
    del_obj.keyframe_insert(data_path="location", frame=5)
    del_obj["myprop"] = 1.0
    del_obj.keyframe_insert(data_path='["myprop"]', frame=5)

    del_host = _KeysHost(
        _FakeWidget(
            _FakeClip({"obj": "DelScope", "orig_start": 0.0, "orig_end": 10.0})
        ),
        sequencer=ShotSequencer(BlenderShotStore()),
    )
    ShotSequencerController._delete_clip_keys(del_host, [1])
    remaining = {
        fc.data_path for fc in AnimUtils.get_fcurves(del_obj) if len(fc.keyframe_points)
    }
    check(
        "Delete Key: transform keys deleted, custom-prop key survives",
        "location" not in remaining and '["myprop"]' in remaining,
        f"{remaining}",
    )
    # A key delete is a key edit like any other, so it runs the bracket's
    # reconcile: a deleted key's claims -- a sample's and a gap hold's -- go
    # with it instead of waiting for the next key that lands on the frame.
    bpy.ops.mesh.primitive_cube_add()
    dc_obj = bpy.context.active_object
    dc_obj.name = "DelClaims"
    for f, v in ((5, 1.0), (10, 2.0), (60, 3.0)):
        dc_obj.location = (v, 0.0, 0.0)
        dc_obj.keyframe_insert(data_path="location", index=0, frame=f)
    dc_store = BlenderShotStore()
    dc_store.define_shot("A", 0, 50, objects=["DelClaims"])
    dc_seq = ShotSequencer(dc_store)
    dc_fc = next(
        fc
        for fc in AnimUtils.get_fcurves(dc_obj)
        if fc.data_path == "location" and fc.array_index == 0
    )
    dc_key = _ShotSequencerInternal._fc_key("DelClaims", dc_fc)
    dc_seq.ledger.record_key(dc_key, 10.0, 0, "end")
    dc_seq.ledger.record_step(dc_key, 10.0, "CONSTANT", "CONSTANT")
    dc_host = _KeysHost(
        _FakeWidget(
            _FakeClip({"obj": "DelClaims", "orig_start": 0.0, "orig_end": 50.0})
        ),
        sequencer=dc_seq,
    )
    ShotSequencerController._delete_clip_keys(dc_host, [1])
    dc_times = [round(kp.co[0], 3) for kp in dc_fc.keyframe_points]
    check(
        "Delete Key: a deleted key's claims go with it",
        dc_times == [60.0]
        and dc_seq.ledger.key_times(dc_key) == dc_seq.ledger.step_times(dc_key) == [],
        f"{dc_times} claims={dc_seq.ledger.key_times(dc_key)} "
        f"steps={dc_seq.ledger.step_times(dc_key)}",
    )
    # ...a sample still ON its bound too -- where the system makes them.  The
    # reconcile passed a claim on its bound before asking whether its key was
    # still there, so the claim waited on the frame for the next key to land.
    bpy.ops.mesh.primitive_cube_add()
    db_obj = bpy.context.active_object
    db_obj.name = "DelOnBound"
    for f, v in ((10, 0.0), (30, 5.0), (50, 3.0)):
        db_obj.location = (v, 0.0, 0.0)
        db_obj.keyframe_insert(data_path="location", index=0, frame=f)
    db_store = BlenderShotStore()
    db_shot = db_store.define_shot("A", 0, 50, objects=["DelOnBound"])
    db_seq = ShotSequencer(db_store)
    db_fc = next(
        fc
        for fc in AnimUtils.get_fcurves(db_obj)
        if fc.data_path == "location" and fc.array_index == 0
    )
    db_key = _ShotSequencerInternal._fc_key("DelOnBound", db_fc)
    db_seq.ledger.record_key(db_key, 50.0, db_shot.shot_id, "end")
    _KeysHost(
        _FakeWidget(
            _FakeClip(
                {
                    "obj": "DelOnBound",
                    "attr_name": "translateX",
                    "shot_id": db_shot.shot_id,
                }
            )
        ),
        sequencer=db_seq,
    ).on_keys_deleted(1, [50.0])
    db_times = [round(kp.co[0], 3) for kp in db_fc.keyframe_points]
    check(
        "Delete Key: a deleted sample on its bound gives up its claim",
        db_times == [10.0, 30.0] and db_seq.ledger.key_times(db_key) == [],
        f"{db_times} claims={db_seq.ledger.key_times(db_key)}",
    )
    # ...and every OTHER claim on a deleted key, through all three delete paths:
    # a behavior's authored claim is no sample, so the reconcile left it on the
    # frame for the next key that lands there to inherit.
    bpy.ops.mesh.primitive_cube_add()
    da_obj = bpy.context.active_object
    da_obj.name = "DelAuthored"
    for f, v in ((10, 0.0), (30, 5.0), (40, 6.0), (60, 3.0)):
        da_obj.location = (v, 0.0, 0.0)
        da_obj.keyframe_insert(data_path="location", index=0, frame=f)
    da_store = BlenderShotStore()
    da_store.define_shot("A", 0, 50, objects=["DelAuthored"])
    da_seq = ShotSequencer(da_store)
    da_key = _ShotSequencerInternal._fc_key("DelAuthored", _loc_x(da_obj))
    for t in (10.0, 30.0, 40.0):
        da_seq.ledger.record_authored(da_key, t, 0, "fade_in", "DelAuthored")
    da_sub = {"obj": "DelAuthored", "attr_name": "translateX", "shot_id": 0}
    _KeysHost(_FakeWidget(_FakeClip(da_sub)), sequencer=da_seq).on_keys_deleted(
        1, [30.0]
    )
    ShotSequencerController._delete_clip_keys(
        _KeysHost(
            _FakeWidget(
                _FakeClip({"obj": "DelAuthored", "orig_start": 0.0, "orig_end": 20.0})
            ),
            sequencer=da_seq,
        ),
        [1],
    )

    dk_widget = _FakeWidget(_FakeClip(da_sub))
    # The widget's key selection, as ``SequencerWidget.selected_keys`` reports it.
    dk_widget.selected_keys = lambda: [{"clip_id": 1, "times": [40.0]}]

    class _NoShotHost(_KeysHost):
        active_shot_id = None  # no shot selected: a plain attribute

    dk_host = _NoShotHost(dk_widget, sequencer=da_seq)
    ShotSequencerController._delete_selected_clip_keys(dk_host)
    da_times = [round(kp.co[0], 3) for kp in _loc_x(da_obj).keyframe_points]
    check(
        "Delete Key: every claim on a deleted key goes, a behavior's too (3 paths)",
        da_times == [60.0]
        and not any(da_seq.ledger.owns_any(da_key, t) for t in (10.0, 30.0, 40.0)),
        f"{da_times} {da_seq.ledger.to_dict()}",
    )
    # The restore point PREDATES the edit (mirror of mayatk's scene_edit): a
    # delete now reconciles, releasing the deleted keys' claims, so a point
    # pushed after it handed undo a ledger without them -- the keys came back
    # unclaimed.  A delete that removed nothing leaves no point behind.
    from pythontk.core_utils.engines.shots.shot_ledger import ShotEditLedger

    # The store's own ``scene_edit`` pushes the point before the edit (and a
    # cancelled edit drops it): no host stand-in for it any more.
    _SnapHost = _KeysHost

    bpy.ops.mesh.primitive_cube_add()
    du_obj = bpy.context.active_object
    du_obj.name = "DelUndo"
    for f, v in ((10, 0.0), (30, 5.0), (50, 3.0)):
        du_obj.location = (v, 0.0, 0.0)
        du_obj.keyframe_insert(data_path="location", index=0, frame=f)
    du_store = BlenderShotStore()
    du_shot = du_store.define_shot("A", 0, 50, objects=["DelUndo"])
    du_seq = ShotSequencer(du_store)
    du_key = _ShotSequencerInternal._fc_key("DelUndo", _loc_x(du_obj))
    du_seq.ledger.record_key(du_key, 50.0, du_shot.shot_id, "end")
    du_data = {"obj": "DelUndo", "attr_name": "translateX", "shot_id": du_shot.shot_id}
    du_host = _SnapHost(_FakeWidget(_FakeClip(du_data)), sequencer=du_seq)
    du_host.on_keys_deleted(1, [50.0])
    du_points = [state for state, _tag in du_store._boundary_undo]
    du_saved = (
        ShotEditLedger.from_dict(du_points[-1].get("ledger")).key_times(du_key)
        if du_points
        else None
    )
    check(
        "Delete Key: the restore point predates the edit (undo gets the claims)",
        len(du_points) == 1
        and du_saved == [50.0]
        and du_seq.ledger.key_times(du_key) == [],
        f"points={len(du_points)} saved={du_saved} "
        f"now={du_seq.ledger.key_times(du_key)}",
    )
    du_host.on_keys_deleted(1, [30.5])  # no key there
    ShotSequencerController._delete_clip_keys(
        _SnapHost(
            _FakeWidget(
                _FakeClip({"obj": "DelUndo", "orig_start": 31.0, "orig_end": 40.0})
            ),
            sequencer=du_seq,
        ),
        [1],
    )
    check(
        "Delete Key: a delete that removed nothing leaves no restore point",
        len(du_store._boundary_undo) == 1,
        f"points={len(du_store._boundary_undo)}",
    )

    # ---- the channel pick: every caller hands NAMES, and the pick replaces ----
    # (pre-fix: the clear read ``animation_data`` off the name strings, found no
    # fcurves, and left every earlier channel selected beside the new pick)
    bpy.ops.mesh.primitive_cube_add()
    chan_obj = bpy.context.active_object
    chan_obj.name = "ChanSel"
    chan_obj.keyframe_insert(data_path="location", frame=1)
    chan_obj.keyframe_insert(data_path="rotation_euler", frame=1)

    def _picked_channels():
        return sorted(
            (fc.data_path, fc.array_index)
            for fc in AnimUtils.get_fcurves(chan_obj)
            if fc.select
        )

    def _pick_every_channel():
        for fc in AnimUtils.get_fcurves(chan_obj):
            fc.select = True

    chan_ctl = ShotSequencerController.__new__(ShotSequencerController)
    chan_ctl.ui = None  # no footer to write to
    chan_ctl._syncing = False
    chan_ctl._get_sequencer_widget = lambda: _FakeWidget(
        _FakeClip({"obj": "ChanSel", "attr_name": "rotateZ"})
    )
    for label, act, expected in (
        (
            "a header label clears the object's channel selection",
            lambda: chan_ctl.on_track_selected(["ChanSel"]),
            [],
        ),
        (
            "a sub-row label selects only its channel",
            lambda: chan_ctl.on_sub_track_selected([("ChanSel", "translateX")]),
            [("location", 0)],
        ),
        (
            "a sub-row clip selects only its channel",
            lambda: chan_ctl.on_selection_changed([1]),
            [("rotation_euler", 2)],
        ),
    ):
        _pick_every_channel()
        try:
            act()
            picked = _picked_channels()
        except Exception as e:  # report, don't abort the suite
            picked = repr(e)
        check(f"channel pick: {label}", picked == expected, f"{picked}")
    bpy.data.objects.remove(chan_obj, do_unlink=True)

    # -- a Ctrl edge drag moves no sample (mirror of mayatk's
    # TestACtrlEdgeDragMovesNoSample, 2026-09-19).  The Ctrl path reconciled
    # with the default rule, so a claimed pin FOLLOWED the bound, re-timing its
    # ramp (and sliding past a gap key); nothing moves in a Ctrl drag.
    class _CtrlHost(_Ctrl):
        _syncing = False
        active_shot_id = None  # set per host: a plain attribute here

        def __init__(self, seq_, sid):
            self.sequencer, self.active_shot_id = seq_, sid

        def _drag_modifiers(self):
            return True, False  # Ctrl held at the press

        def _save_shot_state(self):
            pass

        def _gap_edit_epilogue(self):
            pass

    for label, new_end in (("grow", 53), ("grow over a gap key", 57), ("shrink", 45)):
        st, sq, obs = fresh({"cpA": {10: 0, 40: 5, 55: 1, 70: 2, 90: 8}})
        ca = sq.define_shot("A", 0, 50, objects=["cpA"])
        sq.define_shot("B", 60, 100, objects=["cpA"])
        cfc = fc_of(obs["cpA"])
        obs["cpA"].location.x = cfc.evaluate(50.0)
        obs["cpA"].keyframe_insert(data_path="location", index=0, frame=50)
        sq.ledger.record_key(_SSI._fc_key("cpA", cfc), 50.0, ca.shot_id, "end")
        sq._enforce_gap_holds()  # so only the gesture is measured
        before = [round(fc_of(obs["cpA"]).evaluate(f), 4) for f in range(0, 101)]
        _CtrlHost(sq, ca.shot_id).on_range_highlight_changed(0, new_end)
        after = [round(fc_of(obs["cpA"]).evaluate(f), 4) for f in range(0, 101)]
        check(
            f"ctrl {label}: the bound moves and no sample does",
            sq.shot_by_id(ca.shot_id).end == new_end
            and before == after
            and 50.0 in times_of(obs["cpA"]),
            f"end={sq.shot_by_id(ca.shot_id).end} times={times_of(obs['cpA'])} "
            f"changed={sum(a != b for a, b in zip(before, after))}",
        )

    # -- Ctrl past the neighbour (mirror of mayatk's
    # test_a_ctrl_edge_drag_pushes_into_the_next_shot, 2026-10-06): the
    # neighbour's start gives way, no key moves, and the object moving in the
    # frames taken joins this shot while still moving in the neighbour.
    st, sq, obs = fresh({"cpA": {10: 0, 40: 5}, "cpB": {70: 0, 90: 5}})
    ca = sq.define_shot("A", 0, 50, objects=["cpA"])
    cb = sq.define_shot("B", 60, 100, objects=["cpB"])
    keys_before = (times_of(obs["cpA"]), times_of(obs["cpB"]))
    _CtrlHost(sq, ca.shot_id).on_range_highlight_changed(0, 75)
    sa, sb = sq.shot_by_id(ca.shot_id), sq.shot_by_id(cb.shot_id)
    check(
        "ctrl past the neighbour: its start gives way and the mover joins",
        (sa.start, sa.end, sb.start, sb.end) == (0, 75, 75, 100)
        and "cpB" in sa.objects
        and "cpB" in sb.objects
        and (times_of(obs["cpA"]), times_of(obs["cpB"])) == keys_before,
        f"A={sa.start}-{sa.end} {sa.objects} B={sb.start}-{sb.end} {sb.objects}",
    )

    def bounds(*shots_):
        return tuple(float(v) for sh in shots_ for v in (sh.start, sh.end))

    # A key dragged past the end (to 50.4): the shot grows AROUND it.
    class _ExpandHost(_Ctrl):
        _syncing = False

        def __init__(self, seq_):
            self.sequencer, self._segment_cache = seq_, {}

        def _get_sequencer_widget(self):
            return None

    st, sq, obs = fresh({"exA": {10.6: 0, 50.4: 2}, "exB": {70: 0, 90: 5}})
    ea = sq.define_shot("A", 0, 50, objects=["exA"])
    eb = sq.define_shot("B", 60, 100, objects=["exB"])
    _ExpandHost(sq)._expand_shot_range(ea.shot_id, 10.6, 50.4)
    check(
        "fractional content: a key dragged past the end is enclosed",
        bounds(ea, eb) == (0, 51, 61, 101) and times_of(obs["exB"]) == [71.0, 91.0],
        f"bounds={bounds(ea, eb)} B={times_of(obs['exB'])}",
    )

    # -- a dragged tangent handle lands on the keyframe point ---------------
    st, sq, obs = fresh({"tanA": {0: 0, 10: 5, 20: 0}})
    sq.define_shot("A", 0, 20, objects=["tanA"])
    tan_footers = []

    class _TanClip:
        data = {"obj": "tanA", "attr_name": "translateX", "shot_id": 0}

    class _TanWidget:
        @staticmethod
        def get_clip(_cid):
            return _TanClip()

        @staticmethod
        def select_keys(_wanted):
            return 0

    class _TanCtl(_Ctrl):
        def __init__(self):  # bypass the panel's __init__
            self._segment_cache = {}
            self._sub_row_cache = {}
            self._audio_segments_cache = None
            self._syncing = False

        sequencer = sq

        def _get_sequencer_widget(self):
            return _TanWidget()

        def _set_footer(self, text, **kw):
            tan_footers.append(text)

        def _sync_to_widget(self, **kw):
            pass

    tan_ctl = _TanCtl()
    check(
        "the retired single-key tangent handler stays removed (2026-09-21)",
        not hasattr(_TanCtl, "on_key_tangent_dragged"),
    )
    fc_tan = fc_of(obs["tanA"])
    kp_mid = next(kp for kp in fc_tan.keyframe_points if abs(kp.co[0] - 10) < 1e-3)
    kp_mid.handle_left_type = kp_mid.handle_right_type = "AUTO_CLAMPED"
    fc_tan.update()
    tan_ctl.on_keys_tangent_dragged([(1, [(10.0, 3.0, 4.0)])], "out", False)
    kp_mid = next(kp for kp in fc_tan.keyframe_points if abs(kp.co[0] - 10) < 1e-3)
    hr = (round(kp_mid.handle_right[0], 3), round(kp_mid.handle_right[1], 3))
    hl = (kp_mid.handle_left[0] - 10.0, kp_mid.handle_left[1] - 5.0)
    check(
        "handle drag: the OUT handle lands on co + (dt, dv) and both sides go ALIGNED",
        hr == (13.0, 9.0)
        and kp_mid.handle_right_type == "ALIGNED"
        and kp_mid.handle_left_type == "ALIGNED",
        f"right={hr} types={kp_mid.handle_left_type}/{kp_mid.handle_right_type}",
    )
    check(
        "handle drag: the aligned IN handle is re-aimed opposite, length kept",
        abs(hl[0] * 4.0 - hl[1] * 3.0) < 1e-3 and hl[0] < 0,
        f"left vector={hl}",
    )
    kp_mid.handle_left_type = "FREE"
    fc_tan.update()
    _SC = btk.SequencerHost.segment_collector()

    check(
        "preview: a FREE handle marks the key broken",
        _SC.build_curve_preview(fc_tan, 0, 20)["broken"] == [False, True, False],
        f"{_SC.build_curve_preview(fc_tan, 0, 20).get('broken')}",
    )
    # The shot system's claimed samples get no dot (mirror of mayatk's
    # TestSystemSamplesDrawNoDot, 2026-10-06): flagged hidden, curve intact.
    hidden = _SC.build_curve_preview(fc_tan, 0, 20, hidden_times=[10.0])
    check(
        "preview: a key on hidden_times is flagged hidden, the others not",
        hidden["hidden"] == [False, True, False] and len(hidden["keys"]) == 3,
        f"{hidden.get('hidden')}",
    )
    tan_ctl.on_keys_tangent_dragged([(1, [(10.0, -2.0, 1.0)])], "in", False)
    kp_mid = next(kp for kp in fc_tan.keyframe_points if abs(kp.co[0] - 10) < 1e-3)
    check(
        "handle drag: a FREE side takes the vector as-is and stays FREE",
        (round(kp_mid.handle_left[0], 3), round(kp_mid.handle_left[1], 3)) == (8.0, 6.0)
        and kp_mid.handle_left_type == "FREE"
        and any("handle dragged" in f for f in tan_footers),
        f"left={tuple(kp_mid.handle_left)} type={kp_mid.handle_left_type}",
    )

    # -- a drag that carried the selection, and the Alt break ---------------
    tan_ctl.on_keys_tangent_dragged(
        [(1, [(0.0, 2.0, 1.0), (20.0, 3.0, -1.0)])], "out", False
    )
    kps = {round(kp.co[0]): kp for kp in fc_tan.keyframe_points}
    first = (round(kps[0].handle_right[0], 3), round(kps[0].handle_right[1], 3))
    last = (round(kps[20].handle_right[0], 3), round(kps[20].handle_right[1], 3))
    check(
        "handle drag: every key the gesture carried took its OWN vector",
        first == (2.0, 1.0) and last == (23.0, -1.0),
        f"first={first} last={last}",
    )
    kp_mid = next(kp for kp in fc_tan.keyframe_points if abs(kp.co[0] - 10) < 1e-3)
    kp_mid.handle_left_type = kp_mid.handle_right_type = "ALIGNED"
    fc_tan.update()
    left_before = (round(kp_mid.handle_left[0], 3), round(kp_mid.handle_left[1], 3))
    tan_ctl.on_keys_tangent_dragged([(1, [(10.0, 4.0, 2.0)])], "out", True)
    kp_mid = next(kp for kp in fc_tan.keyframe_points if abs(kp.co[0] - 10) < 1e-3)
    left_after = (round(kp_mid.handle_left[0], 3), round(kp_mid.handle_left[1], 3))
    right = (round(kp_mid.handle_right[0], 3), round(kp_mid.handle_right[1], 3))
    check(
        "handle drag: a broken drag frees BOTH sides and leaves the partner put",
        kp_mid.handle_left_type == "FREE"
        and kp_mid.handle_right_type == "FREE"
        and left_after == left_before
        and right == (14.0, 7.0)
        and any("handle broken" in f for f in tan_footers),
        f"left {left_before}->{left_after} right={right} "
        f"types={kp_mid.handle_left_type}/{kp_mid.handle_right_type}",
    )

    # -- widget sync parity with mayatk (2026-10-04) ----------------------------
    # Expected values are mayatk's own output on the identical scene, measured
    # side by side (fresh mayapy + fresh headless Blender, same keys).
    _SC = btk.SequencerHost.segment_collector()

    class _SyncWidget:
        """Records what the controller's widget sync hands the widget."""

        def __init__(self):
            self.clips = []
            self.attribute_colors = {}
            self.bg_rows = []

        def add_clip(self, track_id=None, start=None, duration=None, **kw):
            self.clips.append(dict(track_id=track_id, start=start, dur=duration, **kw))
            return len(self.clips) - 1

        def set_bg_curve_preview(self, track_id, sub_row, preview, **kw):
            self.bg_rows.append(sub_row)

    def sync_ctl(seq, widget):
        import logging

        ctl = _Ctrl.__new__(_Ctrl)
        ctl.sequencer = seq
        ctl.ui = None
        ctl._get_sequencer_widget = lambda: widget
        ctl.logger = logging.getLogger("test.widget_sync")
        ctl._sub_row_cache = {}
        ctl._segment_cache = {}
        ctl._shifted_out_keys = {}
        ctl._shot_display_mode = "current"
        ctl._track_order_scope = "shot"
        ctl._cmb_mode = "shots"
        ctl._show_internal_holds = False
        return ctl

    def build_main_row(seq, widget, ctl, shot):
        segs, objs = _SC.collect_segments(
            seq, shot, [shot], ctl._segment_cache, ctl._shifted_out_keys, ctl.logger
        )
        track_ids = {o: i for i, o in enumerate(sorted(objs))}
        ctl._build_clips(widget, shot, [shot], segs, track_ids)
        return track_ids, objs

    st, sq, obs = fresh({"wsFlat": {0: 1, 10: 1}, "wsMove": {0: 0, 10: 3}})
    vis = obs["wsVis"] = bpy.data.objects.new("wsVis", None)
    bpy.context.scene.collection.objects.link(vis)
    for f, hidden in ((0, False), (6, True), (12, False)):
        vis.hide_render = hidden
        vis.keyframe_insert("hide_render", frame=f)
    flag = bpy.data.objects.new("wsFlag", None)
    bpy.context.scene.collection.objects.link(flag)
    for f, v in ((0, 0.0), (10, 1.0)):
        flag["flag"] = v
        flag.keyframe_insert('["flag"]', frame=f)
    for f, x in ((12, 0.0), (20, 1.0)):
        flag.location.x = x
        flag.keyframe_insert("location", index=0, frame=f)
    ws_shot = sq.define_shot("WS", 0, 24, objects=["wsFlat", "wsMove", "wsFlag"])
    st.set_active_shot(ws_shot.shot_id)

    st.update_shot(ws_shot.shot_id, objects=["wsFlat", "wsMove", "wsFlag", "wsVis"])
    ws_widget = _SyncWidget()
    ws_ctl = sync_ctl(sq, ws_widget)
    tids, _objs = build_main_row(sq, ws_widget, ws_ctl, sq.shot_by_id(ws_shot.shot_id))
    by_obj = {}
    for c in ws_widget.clips:
        by_obj.setdefault(c.get("obj"), []).append(c)
    flat_clips = sorted(
        (c["start"], c["dur"], bool(c.get("is_stepped")), c.get("stepped_key_time"))
        for c in by_obj.get("wsFlat", [])
    )
    check(
        "main row: a hold-only object shows its keys as stepped point clips",
        flat_clips == [(0.0, 0.0, True, 0.0), (10.0, 0.0, True, 10.0)],
        f"{flat_clips}",
    )
    flag_clips = [
        (c["start"], c["dur"], sorted(c.get("attributes") or []))
        for c in by_obj.get("wsFlag", [])
    ]
    check(
        "main row: a custom-property channel joins the object's clip",
        flag_clips == [(0.0, 20.0, ["flag", "translateX"])],
        f"{flag_clips}",
    )
    vis_clips = [
        (c["start"], c["dur"], c.get("attributes")) for c in by_obj.get("wsVis", [])
    ]
    check(
        "main row: a visibility-only object gets a visibility clip",
        vis_clips == [(0.0, 12.0, ["visibility"])],
        f"{vis_clips}",
    )

    def rows_of(name):
        ws_ctl._sub_row_cache = {}
        return {
            attr: [(s[0], s[1], bool(s[4].get("is_hold"))) for s in segs]
            for attr, segs in ws_ctl._provide_sub_rows(tids.get(name, 0), name)
        }

    check(
        "sub-rows: a keyed custom property gets its own row",
        rows_of("wsFlag")
        == {"flag": [(0.0, 10.0, False)], "translateX": [(12.0, 8.0, False)]},
        f"{rows_of('wsFlag')}",
    )
    check(
        "sub-rows: hide_render expands as a 'visibility' row",
        rows_of("wsVis") == {"visibility": [(0.0, 12.0, False)]},
        f"{rows_of('wsVis')}",
    )

    # -- key menu edits (mayatk parity, 2026-10-04) ------------------------------
    def keyed_x(name, pairs):
        ob = bpy.data.objects.new(name, None)
        bpy.context.scene.collection.objects.link(ob)
        for f, v in pairs:
            ob.location.x = v
            ob.keyframe_insert("location", index=0, frame=f)
        return ob

    def pts(ob):
        return sorted(
            (round(kp.co[0], 3), round(kp.co[1], 3)) for kp in fc_of(ob).keyframe_points
        )

    km_footers = []
    km_selected = []  # what each paste asked the widget to select

    class _KmWidget:
        @staticmethod
        def select_keys(wanted):
            km_selected.append(list(wanted))
            return 0

    class _KeyHost(_Ctrl):
        def __init__(self, seq):  # bypass the panel's __init__
            self._segment_cache = {}
            self._sub_row_cache = {}
            self._audio_segments_cache = None
            self._syncing = False
            self.sequencer = seq

        def _get_sequencer_widget(self):
            return _KmWidget()

        def _save_shot_state(self):
            pass

        def _set_footer(self, text, **kw):
            km_footers.append(text)

        def _sync_to_widget(self, **kw):
            pass

        def _current_time(self):
            return float(bpy.context.scene.frame_current)

    st, sq, obs = fresh({})
    kh = _KeyHost(sq)

    snap = keyed_x("kmSnap", [(10.4, 0.0), (20.6, 1.0)])
    kh._snap_selected_keys([("kmSnap", "translateX", [10.4, 20.6], None)])
    check(
        "key menu: Snap Fractional Keys moves the selected keys to whole frames",
        [t for t, _v in pts(snap)] == [10.0, 21.0],
        f"{pts(snap)} footer={km_footers[-1:]}",
    )

    inv = keyed_x("kmInv", [(0, 0.0), (10, 1.0), (20, 4.0), (30, 9.0)])
    fc_of(inv).keyframe_points[1].interpolation = "CONSTANT"  # 10 -> 20 held
    kh._invert_selected_keys([("kmInv", "translateX", [10.0, 20.0], None)])
    check(
        "key menu: Invert Keys mirrors only the selected keys, in place",
        pts(inv) == [(0.0, 0.0), (10.0, 4.0), (20.0, 1.0), (30.0, 9.0)],
        f"{pts(inv)}",
    )
    check(
        "key menu: Invert Keys re-homes a hold to the key now opening its segment",
        interp_at(inv, 10) == "CONSTANT",
        f"@10={interp_at(inv, 10)} @20={interp_at(inv, 20)}",
    )

    al_a = keyed_x("kmAlA", [(10, 0.0), (15, 1.0), (40, 2.0)])
    al_b = keyed_x("kmAlB", [(20, 0.0), (30, 1.0), (50, 2.0)])
    kh._align_selected_keys(
        [
            ("kmAlA", "translateX", [10.0, 15.0], None),
            ("kmAlB", "translateX", [20.0, 30.0], None),
        ]
    )
    check(
        "key menu: Align Keys shifts each object's block to one start, spacing kept",
        [t for t, _v in pts(al_a)] == [10.0, 15.0, 40.0]
        and [t for t, _v in pts(al_b)] == [10.0, 20.0, 50.0],
        f"A={pts(al_a)} B={pts(al_b)}",
    )

    # A key Align / Invert lands on takes its claims with it (BTK-SHOTS-3):
    # left on the frame, a behavior's authored claim passed to the key that
    # landed there, which the next Build then deleted as its own.
    al_c = keyed_x("kmAlC", [(10, 0.0), (30, 1.0)])
    al_d = keyed_x("kmAlD", [(10, 7.0), (20, 0.0), (40, 1.0)])
    d_key = _SSI._fc_key("kmAlD", fc_of(al_d))
    kh.sequencer.ledger.record_authored(d_key, 10.0, 0, "fade_in", "kmAlD")
    kh._align_selected_keys(
        [
            ("kmAlC", "translateX", [10.0], None),
            ("kmAlD", "translateX", [20.0, 40.0], None),
        ]
    )
    check(
        "key menu: Align Keys releases the claims of a key it lands on",
        pts(al_d) == [(10.0, 0.0), (30.0, 1.0)]
        and pts(al_c) == [(10.0, 0.0), (30.0, 1.0)]
        and not kh.sequencer.ledger.owns_authored(d_key, 10.0),
        f"{pts(al_d)} {kh.sequencer.ledger.to_dict()}",
    )
    inv_o = keyed_x("kmInvO", [(0, 0.0), (3, 1.0), (7, 4.0), (10, 9.0)])
    o_key = _SSI._fc_key("kmInvO", fc_of(inv_o))
    kh.sequencer.ledger.record_authored(o_key, 7.0, 0, "fade_in", "kmInvO")
    kh._invert_selected_keys([("kmInvO", "translateX", [0.0, 3.0, 10.0], None)])
    check(
        "key menu: Invert Keys releases the claims of a key it lands on",
        pts(inv_o) == [(0.0, 9.0), (7.0, 1.0), (10.0, 0.0)]
        and not kh.sequencer.ledger.owns_authored(o_key, 7.0),
        f"{pts(inv_o)} {kh.sequencer.ledger.to_dict()}",
    )
    # A key Align / Invert MOVES carries its claims along (ShotStore.remap_moved):
    # left on its old frame, a fade's claim passed to the key that arrived there
    # and the moved fade key read as the animator's.
    inv_m = keyed_x("kmInvM", [(10, 1.0), (15, 2.0), (25, 3.0), (30, 4.0)])
    m_key = _SSI._fc_key("kmInvM", fc_of(inv_m))
    kh.sequencer.ledger.record_authored(m_key, 15.0, 0, "fade_in", "kmInvM")
    kh._invert_selected_keys([("kmInvM", "translateX", [10.0, 15.0, 25.0, 30.0], None)])
    check(
        "key menu: Invert Keys carries a moved key's claims to its new frame",
        kh.sequencer.ledger.authored(obj="kmInvM") == [(m_key, 25.0)]
        and (25.0, 2.0) in pts(inv_m),
        f"{pts(inv_m)} {kh.sequencer.ledger.to_dict()}",
    )
    al_m = keyed_x("kmAlM", [(10, 1.0), (20, 2.0)])
    keyed_x("kmAlN", [(5, 0.0), (30, 1.0)])  # its selection starts the block at 5
    am_key = _SSI._fc_key("kmAlM", fc_of(al_m))
    kh.sequencer.ledger.record_authored(am_key, 20.0, 0, "fade_out", "kmAlM")
    kh._align_selected_keys(
        [
            ("kmAlM", "translateX", [10.0, 20.0], None),
            ("kmAlN", "translateX", [5.0], None),
        ]
    )
    check(
        "key menu: Align Keys carries a moved key's claims to its new frame",
        [t for t, _v in pts(al_m)] == [5.0, 15.0]
        and kh.sequencer.ledger.authored(obj="kmAlM") == [(am_key, 15.0)],
        f"{pts(al_m)} {kh.sequencer.ledger.to_dict()}",
    )

    thin = keyed_x("kmThin", [(0, 0.0), (10, 1.0), (20, 3.0), (30, 2.0), (40, 0.0)])
    kh._thin_selected_keys([("kmThin", "translateX", [10.0, 20.0, 30.0], None)])
    check(
        "key menu: Remove Intermediate Keys keeps the selection's own end keys",
        [t for t, _v in pts(thin)] == [0.0, 10.0, 30.0, 40.0],
        f"{pts(thin)}",
    )
    # A key a delete edit removes takes its claims with it, as a replaced one
    # does: left on the frame, a behavior's claim passed to the next key there.
    km_tc = keyed_x("kmThinC", [(0, 0.0), (10, 1.0), (20, 3.0)])
    tc_key = _SSI._fc_key("kmThinC", fc_of(km_tc))
    kh.sequencer.ledger.record_authored(tc_key, 10.0, 0, "fade_in", "kmThinC")
    kh._thin_selected_keys([("kmThinC", "translateX", [0.0, 10.0, 20.0], None)])
    check(
        "key menu: Remove Intermediate Keys releases the claims of the keys it removes",
        [t for t, _v in pts(km_tc)] == [0.0, 20.0]
        and not kh.sequencer.ledger.owns_any(tc_key, 10.0),
        f"{pts(km_tc)} {kh.sequencer.ledger.to_dict()}",
    )
    km_sc = keyed_x("kmSimpC", [(0, 0.0), (10, 1.0), (20, 2.0)])  # 10: no shape
    sc_key = _SSI._fc_key("kmSimpC", fc_of(km_sc))
    kh.sequencer.ledger.record_authored(sc_key, 10.0, 0, "fade_in", "kmSimpC")
    kh._simplify_selected_keys([("kmSimpC", "translateX", [0.0, 10.0, 20.0], None)])
    check(
        "key menu: Simplify releases the claims of a key the shape pass removes",
        [t for t, _v in pts(km_sc)] == [0.0, 20.0]
        and not kh.sequencer.ledger.owns_any(sc_key, 10.0),
        f"{pts(km_sc)} {kh.sequencer.ledger.to_dict()}",
    )
    km_hc = keyed_x("kmHoldC", [(0, 1.0), (10, 1.0), (20, 1.0), (30, 0.0)])
    hc_key = _SSI._fc_key("kmHoldC", fc_of(km_hc))
    kh.sequencer.ledger.record_authored(hc_key, 10.0, 0, "fade_in", "kmHoldC")
    kh._simplify_selected_keys(
        [("kmHoldC", "translateX", [0.0, 10.0, 20.0, 30.0], None)]
    )
    check(
        "key menu: Simplify releases the claims of a hold key the flat pass removes",
        10.0 not in [t for t, _v in pts(km_hc)]
        and not kh.sequencer.ledger.owns_any(hc_key, 10.0),
        f"{pts(km_hc)} {kh.sequencer.ledger.to_dict()}",
    )

    flat = keyed_x("kmFlat", [(0, 0.0), (10, 5.0), (20, 0.0)])
    kp_mid = fc_of(flat).keyframe_points[0]
    for kp in fc_of(flat).keyframe_points:
        kp.handle_left_type = kp.handle_right_type = "AUTO"
    fc_of(flat).keyframe_points[2].co = (20.0, 9.0)
    fc_of(flat).update()
    kh._set_key_tangents([("kmFlat", "translateX", [10.0], None)], "FLAT")
    kp_mid = next(k for k in fc_of(flat).keyframe_points if abs(k.co[0] - 10) < 1e-3)
    check(
        "key menu: Flat tangent levels both handles on the key's value",
        abs(kp_mid.handle_left[1] - 5.0) < 1e-4
        and abs(kp_mid.handle_right[1] - 5.0) < 1e-4
        and kp_mid.handle_left[0] < 10.0 < kp_mid.handle_right[0],
        f"hl={tuple(kp_mid.handle_left)} hr={tuple(kp_mid.handle_right)}",
    )

    # One side: that handle goes level and FREE, and an ALIGNED partner is
    # freed where it sits -- left aligned, it would swing level with it.
    one = keyed_x("kmFlatOut", [(0, 0.0), (10, 5.0), (20, 9.0)])
    for kp in fc_of(one).keyframe_points:
        kp.handle_left_type = kp.handle_right_type = "ALIGNED"
        kp.interpolation = "LINEAR"
    fc_of(one).update()
    kp_one = next(k for k in fc_of(one).keyframe_points if abs(k.co[0] - 10) < 1e-3)
    one_left = tuple(round(v, 4) for v in kp_one.handle_left)
    kh._set_key_tangents([("kmFlatOut", "translateX", [10.0], None)], "FLAT", ("out",))
    kp_one = next(k for k in fc_of(one).keyframe_points if abs(k.co[0] - 10) < 1e-3)
    check(
        "key menu: a one-sided Flat levels that handle alone, the partner freed in place",
        abs(kp_one.handle_right[1] - 5.0) < 1e-4
        and kp_one.handle_right[0] > 10.0
        and (kp_one.handle_left_type, kp_one.handle_right_type) == ("FREE", "FREE")
        and tuple(round(v, 4) for v in kp_one.handle_left) == one_left
        and kp_one.interpolation == "BEZIER",
        f"hl={tuple(kp_one.handle_left)} (was {one_left}) hr={tuple(kp_one.handle_right)} "
        f"types={kp_one.handle_left_type}/{kp_one.handle_right_type} {kp_one.interpolation}",
    )

    uni = keyed_x("kmUni", [(0, 0.0), (10, 5.0), (20, 0.0)])
    pts_u = fc_of(uni).keyframe_points
    pts_u[0].handle_left_type = pts_u[0].handle_right_type = "FREE"
    pts_u[1].handle_left_type = pts_u[1].handle_right_type = "AUTO_CLAMPED"
    kh._lock_key_tangents([("kmUni", "translateX", [0.0, 10.0], None)], True)
    pts_u = fc_of(uni).keyframe_points
    check(
        "key menu: Unify aligns free handles and leaves auto handles auto",
        (pts_u[0].handle_left_type, pts_u[0].handle_right_type)
        == ("ALIGNED", "ALIGNED")
        and (pts_u[1].handle_left_type, pts_u[1].handle_right_type)
        == ("AUTO_CLAMPED", "AUTO_CLAMPED"),
        f"{[(k.handle_left_type, k.handle_right_type) for k in pts_u]}",
    )

    cp = keyed_x("kmCopy", [(0, 0.0), (10, 5.0), (20, 0.0)])
    src_kp = fc_of(cp).keyframe_points[1]
    src_kp.interpolation = "CONSTANT"
    src_kp.handle_left_type = src_kp.handle_right_type = "FREE"
    src_kp.handle_right = (13.0, 7.0)
    fc_of(cp).update()
    kh._copy_selected_keys([("kmCopy", "translateX", [10.0], None)])
    bpy.context.scene.frame_set(30)
    kh._paste_selected_keys([("kmCopy", "translateX", [10.0], None)])
    pasted = next(
        (k for k in fc_of(cp).keyframe_points if abs(k.co[0] - 30) < 1e-3), None
    )
    check(
        "key menu: pasted keys keep their interpolation and handles (tangent detail)",
        pasted is not None
        and pasted.interpolation == "CONSTANT"
        and pasted.handle_right_type == "FREE"
        and (round(pasted.handle_right[0], 3), round(pasted.handle_right[1], 3))
        == (33.0, 7.0),
        f"{pasted and (pasted.interpolation, pasted.handle_right_type, tuple(pasted.handle_right))}",
    )
    # Paste over a claimed key replaces it, and its claims go with it (mirror
    # of mayatk's TestKeySelectionEdits): left on the frame, a behavior's claim
    # passed to the pasted key, which the next Build then deleted as its own.
    km_ps = keyed_x("kmPaste", [(0, 0.0), (20, 2.0), (40, 5.0)])
    ps_key = _SSI._fc_key("kmPaste", fc_of(km_ps))
    kh.sequencer.ledger.record_authored(ps_key, 20.0, 0, "fade_in", "kmPaste")
    kh._copy_selected_keys([("kmPaste", "translateX", [40.0], None)])
    bpy.context.scene.frame_set(20)
    kh._paste_selected_keys([("kmPaste", "translateX", [40.0], None)])
    check(
        "key menu: Paste Keys releases the claims of a key it replaces",
        pts(km_ps) == [(0.0, 0.0), (20.0, 5.0), (40.0, 5.0)]
        and not kh.sequencer.ledger.owns_any(ps_key, 20.0),
        f"{pts(km_ps)} {kh.sequencer.ledger.to_dict()}",
    )
    # Copy a gap-held seam: the hold's CONSTANT is the system's, so the key the
    # hold stepped is copied with its pre-hold interpolation.  A key written
    # over the held one since (a Graph Editor paste) is the animator's, its
    # CONSTANT with it -- mirror of mayatk's ``is_same_key`` copy guard.  The
    # pasted key keeps the easing (a paste copies it): the hold's claim (ledger
    # format 2) knows its key by value + left handle, so the new value tells
    # (BACKLOG 2026-10-10: on the easing alone it read as the hold's).
    km_gh = keyed_x("kmGapHold", [(0, 0.0), (20, 9.0), (40, 1.0)])
    gh_key = _SSI._fc_key("kmGapHold", fc_of(km_gh))

    def gh_point():
        return next(k for k in fc_of(km_gh).keyframe_points if abs(k.co[0] - 20) < 1e-3)

    def gh_copied():
        kh._copy_selected_keys([("kmGapHold", "translateX", [20.0], None)])
        rows = type(kh)._key_clipboard.get("rows") or []
        return [kd["interpolation"] for _o, _a, keys in rows for kd in keys]

    kh.sequencer._apply_gap_holds({gh_key: [20.0]})  # the hold, as a pass writes it
    held_copy = gh_copied()
    check(
        "key menu: Copy gives a held seam back its pre-hold interpolation",
        held_copy == ["BEZIER"] and gh_point().interpolation == "CONSTANT",
        f"{held_copy}",
    )
    gh_kp = gh_point()
    gh_easing = gh_kp.easing
    gh_kp.co = (20.0, 3.0)
    fc_of(km_gh).update()
    check(
        "key menu: the key written over the hold keeps the hold's easing",
        gh_point().easing == gh_easing,
        f"{gh_point().easing} vs {gh_easing}",
    )
    over_copy = gh_copied()
    check(
        "key menu: Copy keeps the CONSTANT of a key written over a held seam since",
        over_copy == ["CONSTANT"] and kh.sequencer.ledger.owns_step(gh_key, 20.0),
        f"{over_copy} {kh.sequencer.ledger.to_dict()}",
    )
    # The held VALUE pasted back with another slope is the animator's too: the
    # claim knows its key by value and its frozen left handle (ledger format
    # 2), and the copy asked by value alone (2026-10-12).
    gh_kp = gh_point()
    gh_kp.handle_left_type = "FREE"
    gh_kp.co = (20.0, 9.0)
    gh_kp.handle_left = (16.0, 11.0)
    fc_of(km_gh).update()
    slope_copy = gh_copied()
    check(
        "key menu: Copy keeps the CONSTANT of the held value pasted with another slope",
        slope_copy == ["CONSTANT"],
        f"{slope_copy} left={tuple(gh_point().handle_left)} "
        f"{kh.sequencer.ledger.to_dict()}",
    )
    # A hold claimed in Maya: ShotTransfer carries the claim's Maya tangent
    # types verbatim, so the copy read "auto" back as the pre-hold
    # interpolation and the paste wrote it onto kp.interpolation (TypeError),
    # as the release did before it mapped them (2026-10-11).
    km_mh = keyed_x("kmMayaHold", [(0, 0.0), (20, 9.0), (40, 1.0)])
    mh_key = _SSI._fc_key("kmMayaHold", fc_of(km_mh))
    fc_of(km_mh).keyframe_points[1].interpolation = "CONSTANT"
    fc_of(km_mh).update()
    kh.sequencer.ledger.record_step(mh_key, 20.0, "auto", "auto", 9.0)
    kh._copy_selected_keys([("kmMayaHold", "translateX", [20.0], None)])
    mh_copied = [
        kd["interpolation"]
        for _o, _a, keys in type(kh)._key_clipboard.get("rows") or []
        for kd in keys
    ]
    bpy.context.scene.frame_set(50)
    try:
        kh._paste_selected_keys([("kmMayaHold", "translateX", [20.0], None)])
        mh_err = None
    except Exception as exc:  # noqa: BLE001 -- the defect raised TypeError
        mh_err = repr(exc)
    mh_pasted = next(
        (k for k in fc_of(km_mh).keyframe_points if abs(k.co[0] - 50) < 1e-3), None
    )
    check(
        "key menu: Copy gives a hold claimed in Maya a Blender interpolation",
        mh_copied == ["BEZIER"]
        and mh_err is None
        and mh_pasted is not None
        and mh_pasted.interpolation == "BEZIER",
        f"copied={mh_copied} err={mh_err} "
        f"pasted={mh_pasted and mh_pasted.interpolation}",
    )

    # -- the panel's clipboard: per attribute row, as mayatk's (2026-10-11) -----
    # Bug: Blender's Ctrl+C rewrote the Blender key selection to copy it and
    # kept one buffer per OBJECT on the controller; Ctrl+V landed each
    # object's earliest key on the playhead (the spacing between objects
    # lost), selected nothing, and a fresh controller had no clipboard.
    # mayatk's rows (``ShotSequencer.paste_pairs``) now drive both.
    type(kh)._key_clipboard = {}
    cb_a = keyed_x("cbA", [(0, 0.0), (40, 5.0)])
    cb_b = keyed_x("cbB", [(60, 0.0), (100, 5.0)])
    for k in fc_of(cb_a).keyframe_points:
        k.select_control_point = False  # no Blender key selection at all
    km_footers.clear()
    kh._copy_selected_keys([("cbA", "translateX", [40.0], None)])
    copied_footer = km_footers[-1:]
    kh_fresh = _KeyHost(sq)  # a slots re-init keeps the clipboard
    bpy.context.scene.frame_set(80)
    kh_fresh._paste_selected_keys([("cbB", "translateX", [60.0], None)])
    check(
        "clipboard: Ctrl+C reads the rows (no Blender selection), a fresh "
        "controller pastes onto another object",
        copied_footer == ["Copied 1 key"]
        and pts(cb_b) == [(60.0, 0.0), (80.0, 5.0), (100.0, 5.0)]
        and not any(k.select_control_point for k in fc_of(cb_a).keyframe_points),
        f"{copied_footer} {pts(cb_b)}",
    )
    km_footers.clear()
    km_selected.clear()
    kh._copy_selected_keys(
        [("cbA", "translateX", [40.0], None), ("cbB", "translateX", [100.0], None)]
    )
    bpy.context.scene.frame_set(10)
    kh._paste_selected_keys([])  # nothing selected: back onto the copied rows
    check(
        "clipboard: rows keep their spacing, nothing selected pastes back, and "
        "the pasted keys are selected",
        [t for t, _v in pts(cb_a)] == [0.0, 10.0, 40.0]
        and (70.0, 5.0) in pts(cb_b)
        and km_footers[-1:] == ["Pasted 2 keys onto 2 rows"]
        and sorted(
            (w["data"]["obj"], tuple(w["times"])) for w in (km_selected or [[]])[-1]
        )
        == [("cbA", (10.0,)), ("cbB", (70.0,))],
        f"{pts(cb_a)} {pts(cb_b)} {km_footers[-1:]} {km_selected[-1:]}",
    )
    kh._copy_selected_keys([("cbA", "translateX", [40.0], None)])
    bpy.data.objects.remove(cb_a, do_unlink=True)
    km_footers.clear()
    kh._paste_selected_keys([])
    check(
        "clipboard: a paste onto rows gone since the copy says nothing pasted",
        km_footers[-1:] and km_footers[-1].startswith("Nothing pasted"),
        f"{km_footers[-1:]}",
    )
    type(kh)._key_clipboard = {}
    km_footers.clear()
    kh._paste_selected_keys([("cbB", "translateX", [60.0], None)])
    check(
        "clipboard: nothing copied pastes nothing",
        km_footers[-1:] and km_footers[-1].startswith("Nothing copied here"),
        f"{km_footers[-1:]}",
    )

    # -- key selection mirror: scene-wide clear + channel scope -----------------
    other = keyed_x("ksOther", [(0, 0.0), (10, 1.0)])
    for kp in fc_of(other).keyframe_points:
        kp.select_control_point = True
    mine = keyed_x("ksMine", [(0, 0.0), (10, 1.0), (20, 2.0)])
    for f in (0, 20):
        mine.location.y = f * 0.1
        mine.keyframe_insert("location", index=1, frame=f)
    mine_y = next(
        fc
        for fc in AnimUtils.get_fcurves(mine)
        if fc.data_path == "location" and fc.array_index == 1
    )
    # New fcurves start SELECTED in Blender: clear the flags so the check
    # below measures the mirror, not the default.
    fc_of(mine).select = False
    mine_y.select = True

    class _KsClip:
        data = {"obj": "ksMine", "attr_name": "translateX", "shot_id": None}

    class _KsWidget:
        @staticmethod
        def get_clip(_cid):
            return _KsClip()

    ks = _KeyHost(sq)
    ks._get_sequencer_widget = lambda: _KsWidget()
    from blendertk.core_utils._core_utils import CoreUtils as _CU

    with _CU.window_context_override():
        for o in list(bpy.context.selected_objects):
            o.select_set(False)
        other.select_set(True)
    ks.on_key_selection_changed([{"clip_id": 1, "times": [10.0]}])
    with _CU.window_context_override():
        picked = {o.name for o in bpy.context.selected_objects}
    check(
        "key selection: the keys' object joins the object selection -- the "
        "Graph Editor lists only selected objects' curves (2026-10-07)",
        picked == {"ksOther", "ksMine"},
        f"{picked}",
    )
    check(
        "key selection: keys selected on OTHER objects are cleared (selectKey clear)",
        not any(kp.select_control_point for kp in fc_of(other).keyframe_points),
    )
    check(
        "key selection: the picked keys' channel becomes the channel selection",
        fc_of(mine).select
        and not mine_y.select
        and [kp.select_control_point for kp in fc_of(mine).keyframe_points]
        == [False, True, False],
        f"x={fc_of(mine).select} y={mine_y.select}",
    )

    with _CU.window_context_override():
        for o in list(bpy.context.selected_objects):
            o.select_set(False)
        mine.select_set(True)
    ks._select_and_show(["no such object"])
    with _CU.window_context_override():
        still = [o.name for o in bpy.context.selected_objects]
    check(
        "selection: a click with nothing to select keeps the scene selection",
        still == ["ksMine"],
        f"{still}",
    )

    # -- a point clip drag moves what its mark was drawn from (BACKLOG 2026-10-04)
    # A point (stepped) clip is a MARK: an animator's key on a member that holds
    # still in its shot, drawn from its content channels, CONSTANT or not.  The
    # drag moved every fcurve keyed on that frame -- a custom property the mark
    # never drew included -- where mayatk moved only stepped keys; both now move
    # the mark's own keys (pythontk ``ShotSequencer.move_stepped_keys``).  Each
    # curve has an equal key far outside the shots: a single-key curve is a
    # zero-length SPAN, not a mark.
    st, sq, obs = fresh({"ptMover": {0: 0.0, 50: 10.0, 60: 0.0, 100: 5.0}})
    bpy.ops.mesh.primitive_cube_add()
    pt = bpy.context.active_object
    pt.name = "ptHold"
    pt["note"] = 1.0
    for f in (25, 300):
        pt.location.y = 3.0
        pt.keyframe_insert(data_path="location", index=1, frame=f)
        pt.keyframe_insert(data_path="hide_viewport", frame=f)
        pt.keyframe_insert(data_path='["note"]', frame=f)
    pt_s0 = sq.define_shot("PT0", 0, 50, objects=["ptMover", "ptHold"])
    sq.define_shot("PT1", 60, 100, objects=["ptMover"])
    pt_drawn = [
        (s["start"], bool(s.get("is_stepped")))
        for s in sq.collect_object_segments(pt_s0.shot_id)
        if s["obj"] == "ptHold"
    ]
    pt_host = _KeysHost(
        _FakeWidget(
            _FakeClip(
                {
                    "obj": "ptHold",
                    "shot_id": pt_s0.shot_id,
                    "orig_start": 25.0,
                    "orig_end": 25.0,
                    "is_stepped": True,
                    "stepped_key_time": 25.0,
                }
            )
        ),
        sq,
    )
    pt_host._shifted_out_keys = {}
    pt_host.on_clip_moved(1, 30.0)

    def pt_times(path, index=0):
        fc = next(
            c
            for c in AnimUtils.get_fcurves(pt)
            if c.data_path == path and c.array_index == index
        )
        return sorted(round(kp.co[0], 3) for kp in fc.keyframe_points)

    pt_y, pt_hide = pt_times("location", 1), pt_times("hide_viewport")
    pt_note = pt_times('["note"]')
    check(
        "point clip: the drag moves the mark's own keys, no channel it never drew",
        pt_drawn == [(25.0, True)]
        and pt_y == [30.0, 300.0]
        and pt_hide == [30.0, 300.0]
        and pt_note == [25.0, 300.0],
        f"drawn={pt_drawn} y={pt_y} hide={pt_hide} note={pt_note}",
    )

    # -- undo pairing: only OUR step consumes a restore point (2026-10-04) --------
    st, sq, obs = fresh({"unA": {0: 0, 10: 5}})
    un_shot = sq.define_shot("U", 0, 10, objects=["unA"])

    class _UndoHost(_Ctrl):
        def __init__(self, seq):  # bypass the panel's __init__
            import logging

            self._segment_cache = {}
            self._sub_row_cache = {}
            self._audio_segments_cache = None
            self._syncing = False
            self._syncing_playhead = False  # read by the frame-change handler
            self._playback_range_mode = "off"  # the post-undo refresh reads it
            self._playhead_to_shot_start = True  # the header option's default
            self.sequencer = seq
            self.logger = logging.getLogger("test.undo_host")

        def _on_keys_edited(self, items=()):  # no Qt debounce here
            pass

        def _on_scene_changed(self):
            pass

        def _sync_to_widget(self, **kw):
            pass

        def _sync_combobox(self):
            pass

        def _get_sequencer_widget(self):
            return None

    uh = _UndoHost(sq)
    uh._register_scene_callbacks()
    try:
        bpy.ops.ed.undo_push(message="baseline")
        serial0 = BlenderShotStore.edit_serial()
        with st.scene_edit("Probe Edit"):
            st.update_shot(un_shot.shot_id, end=20.0)
        tag = st.peek_boundary_tag()
        check(
            "scene_edit: stamps a fresh serial inside its step and tags the point with it",
            isinstance(tag, tuple)
            and tag[0] is True
            and tag[1] == BlenderShotStore.edit_serial()
            and tag[1] != serial0,
            f"tag={tag} serial={BlenderShotStore.edit_serial()} before={serial0}",
        )
        depth = len(st._boundary_undo)
        with st.scene_edit("No-op") as edit:
            edit.cancel()
        check(
            "scene_edit: a cancelled edit leaves no restore point and no serial stamp",
            len(st._boundary_undo) == depth
            and BlenderShotStore.edit_serial() == tag[1],
            f"depth {depth}->{len(st._boundary_undo)}",
        )

        # An unrelated step on top: a native undo must take only that step.
        obs["unA"].location.z = 3.0
        bpy.ops.ed.undo_push(message="unrelated")
        bpy.ops.ed.undo()
        st_u = sq.shot_by_id(un_shot.shot_id)
        check(
            "native undo of an UNRELATED step leaves the shot bounds alone",
            st_u.end == 20.0 and st.has_boundary_snapshot(),
            f"end={st_u.end}",
        )
        bpy.ops.ed.undo()
        check(
            "native undo of OUR step restores the bounds",
            sq.shot_by_id(un_shot.shot_id).end == 10.0,
            f"end={sq.shot_by_id(un_shot.shot_id).end}",
        )
        bpy.ops.ed.redo()
        check(
            "native redo of OUR step re-applies the bounds",
            sq.shot_by_id(un_shot.shot_id).end == 20.0,
            f"end={sq.shot_by_id(un_shot.shot_id).end}",
        )

        # The panel's undo with an unrelated step on top: same contract.
        # (Memfile undo replaced the object: fetch it again, never reuse it.)
        bpy.data.objects["unA"].location.z = 7.0
        bpy.ops.ed.undo_push(message="unrelated 2")
        uh.on_undo()
        check(
            "panel undo: an unrelated step on top is undone alone, bounds kept",
            sq.shot_by_id(un_shot.shot_id).end == 20.0,
            f"end={sq.shot_by_id(un_shot.shot_id).end}",
        )
        uh.on_undo()
        check(
            "panel undo: then our step, bounds restored",
            sq.shot_by_id(un_shot.shot_id).end == 10.0,
            f"end={sq.shot_by_id(un_shot.shot_id).end}",
        )

        # One-click New Shot is its own undo step, paired with its point.
        n_before = len(sq.sorted_shots())
        uh._create_shot_one_click = _Ctrl._create_shot_one_click.__get__(uh)
        uh.ui = None
        uh.select_shot = lambda *_a, **_k: None
        uh._set_footer = lambda *_a, **_k: None
        bpy.context.scene.frame_set(1)
        uh._create_shot_one_click()
        made = len(sq.sorted_shots())
        newest = max(sq.sorted_shots(), key=lambda s: s.shot_id)
        check(
            "one-click New Shot: the playhead lands on its start (2026-10-06)",
            bpy.context.scene.frame_current == int(newest.start),
            f"frame={bpy.context.scene.frame_current} start={newest.start}",
        )
        bpy.ops.ed.undo()
        check(
            "one-click New Shot: a native undo removes exactly the new shot",
            made == n_before + 1 and len(sq.sorted_shots()) == n_before,
            f"{n_before} -> {made} -> {len(sq.sorted_shots())}",
        )

        # A shot change lands the playhead too, behind the header's Playhead
        # to Shot Start (mayatk 2026-10-07); the shot already active does not.
        later = sq.define_shot("U2", 40, 60, objects=[])
        uh._shifted_out_keys = {}
        uh._update_shot_nav_state = lambda: None
        uh.select_shot = st.set_active_shot
        st.set_active_shot(un_shot.shot_id)
        bpy.context.scene.frame_set(1)
        uh._go_to_shot(un_shot.shot_id)
        stayed = bpy.context.scene.frame_current
        uh._go_to_shot(later.shot_id)
        check(
            "shot change: the playhead lands on the shot's start, not on a re-pick",
            stayed == 1 and bpy.context.scene.frame_current == 40,
            f"re-pick={stayed} change={bpy.context.scene.frame_current}",
        )
        uh._set_playhead_to_shot_start(False)
        bpy.context.scene.frame_set(1)
        uh._go_to_shot(un_shot.shot_id)
        check(
            "shot change with Playhead to Shot Start off: the playhead stays",
            bpy.context.scene.frame_current == 1
            and st.active_shot_id == un_shot.shot_id,
            f"frame={bpy.context.scene.frame_current}",
        )
    finally:
        uh.remove_callbacks()

    # -- a key edit that raises keeps its restore point (BTK-SHOTS-8) ----------
    # ``scene_edit`` has pushed and tagged its step by then: dropped, the point
    # left an undo of that step reverting the keys but not the bounds.
    st, sq, obs = fresh({"kseA": {0: 0, 10: 5}})
    kse_shot = sq.define_shot("KS", 0, 10, objects=["kseA"])
    kse_host = _UndoHost(sq)
    kse_depth = len(st._boundary_undo)

    def _kse_boom():
        st.update_shot(kse_shot.shot_id, end=20.0)  # wrote, then failed
        raise RuntimeError("boom")

    try:
        kse_host._key_scene_edit("Boom", _kse_boom)
        kse_raised = None
    except RuntimeError as exc:
        kse_raised = exc
    kse_kept = len(st._boundary_undo) == kse_depth + 1 and isinstance(
        st.peek_boundary_tag(), tuple
    )
    st.restore_boundary_snapshot()
    check(
        "key edit: a raise keeps the restore point its pushed step pairs with",
        kse_raised is not None
        and kse_kept
        and sq.shot_by_id(kse_shot.shot_id).end == 10.0,
        f"raised={kse_raised!r} kept={kse_kept} end={sq.shot_by_id(kse_shot.shot_id).end}",
    )

    # -- a scene change rebuilds, never runs the keying epilogue (BTK-SHOTS-4) ---
    # The keyframe debounce's epilogue adds keyed objects to the active shot
    # and falls back to the SELECTION when nothing was keyed -- which a rename
    # and a Sequencer strip edit never are.  The host's watcher reports both as
    # a scene change (blendertk's harness checks that half); the panel answers
    # one with a plain rebuild.
    def _selected_nonmember_scene():
        """A shot holding reMem, active, with reSel -- keyed, not a member --
        selected: what the keying epilogue's selection fallback would add."""
        st, sq, obs = fresh({"reMem": {0: 0, 10: 5}, "reSel": {0: 1, 10: 3}})
        shot = sq.define_shot("RE", 0, 10, objects=["reMem"])
        st.set_active_shot(shot.shot_id)
        for ob in bpy.context.scene.objects:
            ob.select_set(ob.name == "reSel")
        return sq, obs, shot

    class _RebuildHost(_UndoHost):
        def __init__(self, seq):
            super().__init__(seq)
            self.armed = []
            self._reconcile_needed = False

        def _on_scene_changed(self):  # the panel's own (``_UndoHost`` stubs it)
            _Ctrl._on_scene_changed(self)

        def _arm_keyframe_debounce(self):
            self.armed.append("_on_keyframe_debounce_fire")

        def _arm_rebuild_debounce(self):
            self.armed.append("_on_rebuild_debounce_fire")

        def fire(self):
            """Run what the armed timers would, once each."""
            fired, self.armed = list(self.armed), []
            for name in fired:
                getattr(self, name)()
            return fired

    sq, obs, re_shot = _selected_nonmember_scene()
    re_host = _RebuildHost(sq)
    obs["reMem"].name = "reMemRenamed"
    re_host._on_scene_changed()  # what the watcher reports for a rename
    re_fired = re_host.fire()
    check(
        "scene change: a plain rebuild, and the selection joins no shot",
        re_fired == ["_on_rebuild_debounce_fire"]
        and re_host._reconcile_needed
        and "reSel" not in sq.shot_by_id(re_shot.shot_id).objects,
        f"fired={re_fired} members={sq.shot_by_id(re_shot.shot_id).objects}",
    )

    # Past the banked cap the burst is a bake / import: the keying epilogue
    # scans the selection instead (mirror of mayatk's curve cap).
    sq, obs, re_shot = _selected_nonmember_scene()
    cap_host = _RebuildHost(sq)
    cap_host._edited_items = {f"ghost{i}" for i in range(cap_host._EDITED_CAP + 1)}
    cap_added = cap_host._auto_add_keyed_objects(re_shot.shot_id)
    check(
        "keying epilogue: past the banked cap it falls back to the selection",
        cap_added
        and "reSel" in sq.shot_by_id(re_shot.shot_id).objects
        and not cap_host._edited_items,
        f"added={cap_added} members={sq.shot_by_id(re_shot.shot_id).objects}",
    )

    # -- the sequencer's own members are no hand edit (BACKLOG 2026-10-10) -----
    # The keying epilogue's additions read as a hand edit to the Shot Manifest,
    # so every later Build kept that shot, doc changes and all.  It tags what it
    # adds (ShotStore.SYSTEM_MEMBERS); a hand's add still counts.  (Filling an
    # empty shot is the engine's: blendertk's harness.)
    from blendertk.anim_utils.shots.shot_manifest._shot_manifest import (
        BlenderShotManifest,
    )
    from pythontk import BuilderObject, BuilderStep

    sm_st, sm_sq, _sm_obs = fresh({"smMember": {5: 0, 20: 5}, "smKeyed": {5: 1, 20: 3}})
    sm_step = BuilderStep("A01", "A", "SEC A", "", [BuilderObject("smMember")])
    BlenderShotManifest(sm_st).update([sm_step], initial_shot_length=30)
    sm_shot = sm_st.shot_by_name("A01")

    def sm_edited():
        return BlenderShotManifest(sm_st).edited_by_hand(sm_shot)

    sm_host = _RebuildHost(sm_sq)
    sm_host._edited_items = {"smKeyed"}
    sm_added = sm_host._auto_add_keyed_objects(sm_shot.shot_id)
    sm_keyed = sm_edited()
    sm_st.update_shot(sm_shot.shot_id, objects=["smMember"])  # a hand removes it
    sm_st.update_shot(sm_shot.shot_id, objects=["smMember", "smKeyed"])  # and back
    check(
        "keying epilogue: its addition is no hand edit; a hand's add still is",
        sm_added and not sm_keyed and sm_edited(),
        f"added={sm_added} keyed_edited={sm_keyed} members={sm_shot.objects}",
    )

    # -- the view's playback range is the PREVIEW range, never the render range --
    # Which range the view asks for is the panel's (locked: the shot; follows
    # the view: the visible shots); the host sets it on the preview range.
    pr_st, pr_sq, _pr_obs = fresh({})
    pr_a = pr_sq.define_shot("PA", 10, 40)
    pr_sq.define_shot("PB", 50, 90)
    pr_scene = bpy.context.scene
    pr_render = (pr_scene.frame_start, pr_scene.frame_end)
    pr_host = _RebuildHost(pr_sq)
    pr_host._shot_display_mode = "adjacent"
    ranges = {}
    for mode in ("locked", "follows_view"):
        pr_host._playback_range_mode = mode
        pr_host._apply_view_playback_range(pr_a)
        ranges[mode] = (
            pr_scene.use_preview_range,
            pr_scene.frame_preview_start,
            pr_scene.frame_preview_end,
        )
    check(
        "playback range: locked spans the shot, follows-view the visible shots, "
        "both on the preview range",
        ranges == {"locked": (True, 10, 40), "follows_view": (True, 10, 90)}
        and (pr_scene.frame_start, pr_scene.frame_end) == pr_render,
        f"{ranges} render={(pr_scene.frame_start, pr_scene.frame_end)} was {pr_render}",
    )

    # ---- linked duplicates share ONE curve (BACKLOG 2026-10-05) ---------------
    # The engine's own ops over a linked pair are blendertk's harness; these two
    # are the panel's: a drag and a key edit over both sharers' rows.
    def ld_scene(share, member):
        st, sq, obs = fresh({"ldA": {10: 0.0, 20: 5.0}, "ldOther": {30: 1.0, 40: 7.0}})
        if share:
            ld_b = obs["ldA"].copy()  # Alt+D: a new object, the action shared
            ld_b.name = "ldB"
            bpy.context.scene.collection.objects.link(ld_b)
        ld_a = sq.define_shot(
            "LA", 10, 20, objects=["ldA", "ldB"] if member else ["ldA"]
        )
        ld_o = sq.define_shot("LB", 30, 40, objects=["ldOther"])
        return st, sq, ld_a, ld_o

    def ld_played(sq):
        fc = fc_of(bpy.data.objects["ldA"])
        claims = sq.ledger.key_records(_SSI._fc_key("ldA", fc))
        return (
            [(round(kp.co[0], 3), round(kp.co[1], 3)) for kp in fc.keyframe_points],
            sorted((round(t, 3), edge) for t, _owner, edge in claims),
        )

    # A key drag over both sharers' clips: one curve, moved once.  The gesture
    # plan told curves apart by ``id()`` of a wrapper bpy hands out fresh per
    # access, so the shared curve took the drag once per clip.
    st, sq, ld_a, ld_o = ld_scene(True, True)
    ld_host = _KeysHost(
        _MultiWidget(
            {
                1: _FakeClip(
                    {"obj": "ldA", "attr_name": "translateX", "shot_id": None}
                ),
                2: _FakeClip(
                    {"obj": "ldB", "attr_name": "translateX", "shot_id": None}
                ),
            }
        )
    )
    ld_drag = [(10.0, 20.0), (20.0, 30.0)]
    ld_host.on_keys_batch_moved([(1, ld_drag), (2, ld_drag)])
    check(
        "linked duplicates: a key drag over both sharers' clips moves the curve once",
        ld_played(sq)[0] == [(20.0, 0.0), (30.0, 5.0)],
        f"{ld_played(sq)[0]}",
    )
    # A key edit over both sharers' rows: one curve, edited once.  The key
    # menu's curves were read per object, so the shared curve came twice and
    # an Invert ran twice -- mirrored back where it was.
    st, sq, ld_a, ld_o = ld_scene(True, True)
    _KeyHost(sq)._invert_selected_keys(
        [
            ("ldA", "translateX", [10.0, 20.0], None),
            ("ldB", "translateX", [10.0, 20.0], None),
        ]
    )
    check(
        "linked duplicates: a key edit over both sharers' rows edits the curve once",
        ld_played(sq)[0] == [(10.0, 5.0), (20.0, 0.0)],
        f"{ld_played(sq)[0]}",
    )

    BlenderShotStore.clear_active()
    BlenderShotStore._prefs_dir_override = None
    return lines


if __name__ == "__main__":
    try:
        result_lines = _run_panel_checks()
    except Exception as e:  # pragma: no cover
        traceback.print_exc()
        result_lines = [f"FAIL: harness raised — {e!r}"]

    print("\n".join(result_lines))
    passed = sum(1 for ln in result_lines if ln.startswith("OK"))
    ok = bool(result_lines) and all(ln.startswith("OK") for ln in result_lines)
    print(f"===RESULT: {'PASS' if ok else 'FAIL'}=== ({passed}/{len(result_lines)})")
