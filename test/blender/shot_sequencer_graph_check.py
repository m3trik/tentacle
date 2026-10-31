"""The Shot Sequencer's graph view in a real Blender: blendertk's ``GraphSync``
over the shared panel's controller (``tentacle/slots/tools/_shot_sequencer``).

Every edit the graph editor raises is checked in BLENDER -- the keys, the
handles, the interpolation, the infinity, the shot bounds -- with a real
(offscreen) ``SequencerWidget``, the tentacle controller with ``tk = blendertk``
and the host's ``GraphSync`` (``btk.SequencerHost.graph_sync_cls()``).  Maya's
twin is the tentacle Maya tests' graph cases.

Requires a real Blender binary (it ``import bpy``), so it is **not** a CI/unittest
target. Run it against a *fresh* Blender (never an existing session)::

    blender --background --factory-startup --python tentacle/test/blender/shot_sequencer_graph_check.py

or ``python tentacle/test/run_tests.py shot_sequencer_graph --in-blender``.
"""

import os
import sys
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

lines = []


def check(name, cond, detail=""):
    lines.append(
        f"{'OK' if cond else 'FAIL'}: {name}"
        + (f" | {detail}" if detail and not cond else "")
    )


def run():
    import bpy
    import pythontk as ptk
    from unittest.mock import MagicMock
    from qtpy import QtWidgets

    import blendertk as btk
    from blendertk import ShotStore
    from blendertk.anim_utils._anim_utils import AnimUtils
    from tentacle.slots.tools._shot_sequencer.controller import (
        ShotSequencerController,
    )
    from uitk import ComboBox, SequencerWidget

    ShotSequencer = btk.ShotSequencer
    GraphSync = btk.SequencerHost.graph_sync_cls()

    class _Sb:
        """The switchboard as the controller reads it: uitk's public names
        (``sb.RowMetrics``, ``sb.AttributeColorDialog``...) and its handlers."""

        handlers = MagicMock()

        def __getattr__(self, name):
            import uitk

            return getattr(uitk, name)

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    tmp = ptk.TempArtifacts("btk_graph_sync", policy="scoped")
    ShotStore._prefs_dir_override = tmp.dir_path()
    ShotStore.clear_active()

    def pump():
        for _ in range(3):
            app.processEvents()

    def keyed(name, keys):
        bpy.ops.mesh.primitive_cube_add()
        o = bpy.context.active_object
        o.name = name
        for f, v in keys:
            o.location.x = v
            o.keyframe_insert(data_path="location", index=0, frame=f)
        return o

    def loc_x(obj):
        return next(
            fc
            for fc in AnimUtils.get_fcurves(obj)
            if fc.data_path == "location" and fc.array_index == 0
        )

    def points(obj):
        return [
            (round(kp.co[0], 4), round(kp.co[1], 4))
            for kp in loc_x(obj).keyframe_points
        ]

    class Case:
        """One fresh scene, store, widget, controller and GraphSync."""

        def __init__(self):
            bpy.ops.object.select_all(action="SELECT")
            bpy.ops.object.delete()
            self.a = keyed("ctlA", ((0, 0.0), (40, 5.0)))
            self.b = keyed("ctlB", ((60, 0.0), (100, 5.0)))
            ShotStore.clear_active()
            self.store = ShotStore()
            self.store.define_shot("S0", 0, 50, objects=["ctlA"])
            self.store.define_shot("S1", 60, 120, objects=["ctlB"])
            self.widget = SequencerWidget()
            self.widget.resize(900, 400)
            self.widget.show()
            slots = MagicMock()
            slots.tk = btk
            slots.sb = _Sb()
            slots.ui.sequencer_widget = self.widget
            slots.ui.cmb_shot = ComboBox()
            self.ctrl = ShotSequencerController(slots)
            self.ctrl.sequencer = ShotSequencer(self.store)
            bpy.context.scene.frame_set(0)  # S0 under the playhead
            self.ctrl._sync_combobox()
            self.ctrl._sync_to_widget()
            self.sync = GraphSync(self.ctrl, self.widget)
            self.widget.set_editor("graph")
            pump()
            self.g = self.widget.editor("graph")
            self.crv = "ctlA|location|0"

        def close(self):
            self.sync.detach()
            try:
                self.ctrl.remove_callbacks()
            except Exception:
                pass
            self.widget.close()
            self.widget.deleteLater()
            pump()

        def shot(self, name):
            return self.store.shot_by_name(name)

    # -- the outline and the read ----------------------------------------------
    c = Case()
    entry = next((e for e in c.g._outline if e["label"] == "ctlA"), None)
    check(
        "outline: the shot's object and its curves",
        entry is not None and c.crv in [ch["curve_id"] for ch in entry["children"]],
        c.g._outline,
    )
    check(
        "read: the graph draws ctlA's keys",
        c.g.curve(c.crv).times() == [0.0, 40.0],
        c.g.curve(c.crv),
    )
    check(
        "the editor offers no weighting rows (a Blender handle has its length)",
        c.g.offers_weighting is False,
    )
    c.close()

    # -- a move lands time and value -------------------------------------------
    c = Case()
    c.g.keys_edited.emit([(c.crv, [(40.0, -5.0, 2.5)])])
    check(
        "move: time and value land in Blender",
        points(c.a) == [(0.0, 0.0), (35.0, 7.5)],
        points(c.a),
    )
    check(
        "move: the graph re-read",
        c.g.curve(c.crv).times() == [0.0, 35.0],
        c.g.curve(c.crv).times(),
    )
    c.close()

    c = Case()
    c.g.keys_edited.emit([(c.crv, [(0.0, 0.0, -1.0), (40.0, 0.0, -1.0)])])
    check(
        "value-only move keeps the times",
        points(c.a) == [(0.0, -1.0), (40.0, 4.0)],
        points(c.a),
    )
    c.close()

    # -- a move past the shot end grows it -------------------------------------
    c = Case()
    c.g.keys_edited.emit([(c.crv, [(40.0, 15.0, 0.0)])])
    check(
        "move past the end: the key lands and the shot grows",
        points(c.a)[-1][0] == 55.0 and c.shot("S0").end >= 55.0,
        (points(c.a), c.shot("S0").end),
    )
    c.close()

    # The graph records no press modifiers: a Shift a tracks gesture left in
    # the widget's flags (Shift: free across bounds) left the moved key
    # outside its shot (mayatk's twin, 2026-10-12).
    c = Case()
    c.widget.shift_held_at_press = True  # a tracks gesture's leftover
    c.g.keys_edited.emit([(c.crv, [(40.0, 15.0, 0.0)])])
    check(
        "move past the end after a Shift gesture: the shot still grows",
        points(c.a)[-1][0] == 55.0 and c.shot("S0").end >= 55.0,
        (points(c.a), c.shot("S0").end),
    )
    c.close()

    # A key on a seam two flush shots share moved right is the LATER shot's:
    # edited as the earlier one's, it grew that shot over it and rippled the
    # later one away (mayatk's twin, 2026-10-12).
    c = Case()
    c.store.update_shot(c.shot("S1").shot_id, start=50.0)  # flush with S0
    c.b.location.x = -1.0
    c.b.keyframe_insert(data_path="location", index=0, frame=50)
    c.ctrl._shot_display_mode = "all"
    c.sync.sync()
    c.g.keys_edited.emit([("ctlB|location|0", [(50.0, 5.0, 0.0)])])
    b_times = [round(kp.co[0], 4) for kp in loc_x(c.b).keyframe_points]
    check(
        "a seam key moved into the later shot grows neither shot",
        55.0 in b_times and (c.shot("S0").end, c.shot("S1").start) == (50.0, 50.0),
        (b_times, c.shot("S0").end, c.shot("S1").start),
    )
    c.close()

    # Every shot's cached segments go with a graph edit: the graph edits any
    # shot's keys (Adjacent / All), and a neighbour keyed from the graph drew
    # its old clips on the way back to the tracks (mayatk's twin, 2026-10-12).
    c = Case()
    s1 = c.shot("S1").shot_id
    c.ctrl._segment_cache[s1] = ["stale"]
    c.ctrl._shot_display_mode = "all"
    c.sync.sync()
    c.g.keys_inserted.emit([("ctlB|location|0", 80.0)])
    check(
        "a graph edit drops every shot's cached segments",
        c.ctrl._segment_cache.get(s1) != ["stale"],
        c.ctrl._segment_cache.get(s1),
    )
    c.close()

    # -- handles, handle types, interpolation, break ---------------------------
    c = Case()
    c.g.tangents_edited.emit([(c.crv, [(0.0, "out", 4.0, 4.0, False)])])
    kp = loc_x(c.a).keyframe_points[0]
    check(
        "tangent drag: the out handle lands at the vector",
        (round(kp.handle_right[0], 4), round(kp.handle_right[1], 4)) == (4.0, 4.0),
        tuple(kp.handle_right),
    )
    c.g.tangents_edited.emit([(c.crv, [(40.0, "in", -3.0, 1.0, True)])])
    kp = loc_x(c.a).keyframe_points[1]
    check(
        "Alt tangent drag breaks the key (both sides FREE)",
        (kp.handle_left_type, kp.handle_right_type) == ("FREE", "FREE"),
        (kp.handle_left_type, kp.handle_right_type),
    )
    c.g.tangent_type_requested.emit("VECTOR", [(c.crv, [0.0])])
    kp = loc_x(c.a).keyframe_points[0]
    check("handle type: VECTOR", kp.handle_right_type == "VECTOR", kp.handle_right_type)
    c.g.tangent_type_requested.emit("CONSTANT", [(c.crv, [0.0])])
    kp = loc_x(c.a).keyframe_points[0]
    check("interpolation: CONSTANT", kp.interpolation == "CONSTANT", kp.interpolation)
    check(
        "the graph re-read the stepped span",
        c.g.curve(c.crv).keys[0].interpolation == "step",
        c.g.curve(c.crv).keys[0].interpolation,
    )
    c.g.tangents_broken.emit(False, [(c.crv, [40.0])])
    kp = loc_x(c.a).keyframe_points[1]
    check(
        "unify aligns the FREE sides",
        (kp.handle_left_type, kp.handle_right_type) == ("ALIGNED", "ALIGNED"),
        (kp.handle_left_type, kp.handle_right_type),
    )
    c.close()

    # -- insert, delete --------------------------------------------------------
    c = Case()
    before = loc_x(c.a).evaluate(20.0)
    c.g.keys_inserted.emit([(c.crv, 20.0)])
    fc = loc_x(c.a)
    check(
        "insert: a key at 20 on the curve as it ran there",
        [p[0] for p in points(c.a)] == [0.0, 20.0, 40.0]
        and abs(fc.evaluate(20.0) - before) < 1e-4,
        (points(c.a), before),
    )
    c.g.keys_deleted.emit([(c.crv, [20.0])])
    check(
        "delete: the key goes", [p[0] for p in points(c.a)] == [0.0, 40.0], points(c.a)
    )
    check(
        "delete: the graph re-read",
        c.g.curve(c.crv).times() == [0.0, 40.0],
        c.g.curve(c.crv).times(),
    )
    c.close()

    # -- infinity --------------------------------------------------------------
    c = Case()
    c.g.infinity_requested.emit("post", "cycle_offset", [c.crv])
    mods = [(m.type, m.mode_before, m.mode_after) for m in loc_x(c.a).modifiers]
    check(
        "post cycle_offset: a Cycles modifier repeating after",
        mods == [("CYCLES", "NONE", "REPEAT_OFFSET")],
        mods,
    )
    check(
        "the graph reads the infinity back",
        (c.g.curve(c.crv).pre_infinity, c.g.curve(c.crv).post_infinity)
        == ("constant", "cycle_offset"),
        (c.g.curve(c.crv).pre_infinity, c.g.curve(c.crv).post_infinity),
    )
    c.g.infinity_requested.emit("post", "linear", [c.crv])
    fc = loc_x(c.a)
    check(
        "post linear: extrapolation LINEAR, the modifier gone",
        fc.extrapolation == "LINEAR" and not list(fc.modifiers),
        (fc.extrapolation, [m.type for m in fc.modifiers]),
    )
    c.close()

    # -- selection, the key menu, copy / paste, follow -------------------------
    c = Case()
    c.g.select_keys([(c.crv, 40.0)])
    sel = [kp.select_control_point for kp in loc_x(c.a).keyframe_points]
    check("the graph's key selection is Blender's", sel == [False, True], sel)
    menu = c.g.build_context_menu()
    titles = [a.text() for a in menu.actions()]
    check(
        "the key menu carries the key edits",
        "Store Keys" in titles and "Edit" in titles,
        titles,
    )
    bpy.context.scene.frame_set(20)
    c.ctrl._copy_keys_shortcut()
    c.g.select_keys([])
    c.ctrl._paste_keys_shortcut()
    check(
        "Ctrl+C / Ctrl+V act on the graph's selection",
        [p[0] for p in points(c.a)] == [0.0, 20.0, 40.0],
        points(c.a),
    )
    check(
        "the paste reaches the graph",
        c.g.curve(c.crv).times() == [0.0, 20.0, 40.0],
        c.g.curve(c.crv).times(),
    )

    c.ctrl._shot_display_mode = "all"
    c.sync.sync()
    check(
        "both shots' objects show under 'all'",
        [e["label"] for e in c.g._outline] == ["ctlA", "ctlB"],
        c.g._outline,
    )
    bpy.ops.object.select_all(action="DESELECT")
    c.b.select_set(True)
    c.sync._follow_selection()
    check(
        "the display follows Blender's selection",
        c.g.displayed_curve_ids() == ["ctlB|location|0"],
        c.g.displayed_curve_ids(),
    )
    c.g.auto_load = False
    bpy.ops.object.select_all(action="DESELECT")
    c.a.select_set(True)
    c.sync._follow_selection()
    check(
        "pinned (Auto Load off), it stays",
        c.g.displayed_curve_ids() == ["ctlB|location|0"],
        c.g.displayed_curve_ids(),
    )
    c.close()

    # -- Live Update, and the scope's window as the focus range ----------------
    c = Case()
    bpy.context.scene.frame_set(0)
    preview = c.g.curve(c.crv).copy()
    preview.keys[0].value = 3.0
    c.g.curves_previewed.emit([(c.crv, preview)])
    check(
        "live: the previewed value shows on the object",
        abs(c.a.location.x - 3.0) < 1e-4,
        c.a.location.x,
    )
    check("live: no key changed", points(c.a) == [(0.0, 0.0), (40.0, 5.0)], points(c.a))
    c.g.preview_cancelled.emit()
    check(
        "live: a cancel puts the animation back",
        abs(c.a.location.x) < 1e-4,
        c.a.location.x,
    )
    c.sync.sync()
    check(
        "the active shot is the graph's focus range",
        c.g.focus_range == (0.0, 50.0),
        c.g.focus_range,
    )
    c.close()

    # -- an edit made in Blender reaches the graph ----------------------------
    c = Case()
    c.a.location.x = 9.0
    c.a.keyframe_insert(data_path="location", index=0, frame=20)
    c.ctrl._sync_to_widget()  # what the depsgraph debounce runs
    check(
        "an edit made in Blender shows after the rebuild",
        c.g.curve(c.crv).times() == [0.0, 20.0, 40.0],
        c.g.curve(c.crv).times(),
    )
    c.close()

    # -- linked duplicates: one curve, moved once ------------------------------
    # Alt+D shares the action slot: the outline lists each sharer's channel
    # under its own id, so a selection over both named the one curve twice and
    # the commit moved it once per id (a clip drag's twin, 2026-10-12).
    c = Case()
    for f, v in ((10, 1.0), (20, 2.0)):
        c.a.location.x = v
        c.a.keyframe_insert(data_path="location", index=0, frame=f)
    link = c.a.copy()  # Alt+D: a new object, the action shared
    link.name = "ctlLink"
    bpy.context.scene.collection.objects.link(link)
    c.store.update_shot(c.shot("S0").shot_id, objects=["ctlA", "ctlLink"])
    c.sync.sync()
    rows = [(10.0, 10.0, 0.0), (20.0, 10.0, 0.0)]
    c.g.keys_edited.emit([(c.crv, rows), ("ctlLink|location|0", rows)])
    check(
        "linked duplicates: a move over both sharers' curves moves the curve once",
        points(c.a) == [(0.0, 0.0), (20.0, 1.0), (30.0, 2.0), (40.0, 5.0)],
        points(c.a),
    )
    c.close()

    # -- a scene swap subscribes the selection follow again --------------------
    # Blender drops every msgbus subscription on a file load: the graph's
    # follow of the active object died with the first File > Open, where the
    # controller subscribes its own again on the store's invalidation.
    c = Case()
    resubscribed = []
    subscribe = c.sync._subscribe
    c.sync._subscribe = lambda: (resubscribed.append(1), subscribe())
    ShotStore.invalidate()  # what a scene open runs
    check(
        "a scene swap subscribes the selection follow again",
        resubscribed == [1],
        resubscribed,
    )
    # The widget going lets go of the store, as the controller does
    # (``ui.destroyed``): the listener would keep a closed panel subscribing.
    c.widget.destroyed.emit()
    check(
        "a destroyed widget lets go of the store's invalidation",
        c.sync._on_scene_swap not in ShotStore._invalidation_listeners,
    )
    c.close()

    ShotStore.clear_active()
    ShotStore._prefs_dir_override = None
    tmp.cleanup()


if __name__ == "__main__":
    try:
        run()
    except Exception as e:  # pragma: no cover
        traceback.print_exc()
        lines.append(f"FAIL: harness raised -- {e!r}")
    print("\n".join(lines))
    passed = sum(1 for ln in lines if ln.startswith("OK"))
    ok = bool(lines) and all(ln.startswith("OK") for ln in lines)
    print(f"===RESULT: {'PASS' if ok else 'FAIL'}=== ({passed}/{len(lines)})")
