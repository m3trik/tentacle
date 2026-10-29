# !/usr/bin/python
# coding=utf-8
"""Live check for the shared Shot Sequencer panel — real Qt stack + real bpy, one process.

blendertk's engine suite (``blendertk/test/test_shot_sequencer.py``) has no Qt;
the panel suite (``test/test_shot_sequencer_panel_blender.py``) has no bpy.  This
harness provisions Qt through ``tentacle.tcl_blender`` (offscreen, the same PySide
that tentacle runs inside Blender) in a *fresh* ``--background`` Blender, loads
``ui/tools/shot_sequencer.ui`` through Switchboard + BlenderUiHandler with
tentacle's shared roots registered, and drives the controller against a keyed scene
with a VSE strip: widget sync (tracks / clips / audio track / icons), per-attribute
sub-rows + Show Internal Holds, Move-to-Shot, clip + audio drags, Graph-Editor key
selection sync, per-key delete, native undo, playhead ↔ scene frame, the
keyframe-edit handler, transport controls, the combo context-menu helpers.

Non-``test_`` name keeps it out of unittest discovery (it needs bpy).  Run against
a fresh Blender (never an existing session)::

    blender --background --factory-startup --python tentacle/test/blender/shot_sequencer_live_check.py

or ``python tentacle/test/run_tests.py shot_sequencer_live --in-blender``.
"""

import os
import sys
import traceback
import wave
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
    ok = bool(cond)
    lines.append(
        f"{'OK  ' if ok else 'FAIL'} {name}{(' | ' + detail) if (detail and not ok) else ''}"
    )
    return ok


try:
    import bpy
    import pythontk as ptk
    from tentacle import tcl_blender  # noqa: F401 — provisions Qt for the panel imports
    from qtpy import QtWidgets, QtCore

    from blendertk import BlenderShotStore
    from blendertk.anim_utils._anim_utils import AnimUtils
    from blendertk.audio_utils._audio_utils import AudioUtils
    from blendertk.ui_utils.blender_ui_handler import BlenderUiHandler
    from tentacle.tcl import Tcl
    from uitk import Switchboard
except Exception:
    traceback.print_exc(file=sys.stdout)
    lines.append("FAIL imports (tentacle Qt deps / blendertk)")

tmp = None
try:
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def pump(n=5, ms=0):
        for _ in range(n):
            app.processEvents()
            if ms:
                QtCore.QThread.msleep(ms)

    def key_times(obj_name):
        obj = bpy.data.objects.get(obj_name)
        return sorted(
            {
                round(float(kp.co[0]), 3)
                for fc in AnimUtils.get_fcurves(obj)
                for kp in fc.keyframe_points
            }
        )

    def own_key_times(obj_name):
        """*obj_name*'s key times less the samples the shot system claims.

        Keys leaving a shot pin the pose they held on the next shot's facing
        bound -- the one rule: an op on one shot never changes what another
        plays inside its own span -- and that pin is the system's, not the
        object's animation (``ShotSequencer._animator_key_times``; blendertk's
        engine suite reads a moved object's keys the same way).
        """
        obj = bpy.data.objects.get(obj_name)
        return sorted(
            {
                round(float(t), 3)
                for fc in AnimUtils.get_fcurves(obj)
                for t in ctl.sequencer._animator_key_times(obj_name, fc)
            }
        )

    def keyed(name, frames_values, index=0):
        bpy.ops.mesh.primitive_cube_add()
        o = bpy.context.active_object
        o.name = name
        for f, v in frames_values:
            o.location[index] = v
            o.keyframe_insert(data_path="location", index=index, frame=f)
        return o

    # ---- scene: A/B/C ramps, a hold object, one sound strip ---------------------
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()
    keyed("A", [(f, f * 0.1) for f in range(0, 11)])
    keyed("B", [(f, f * 0.1) for f in range(20, 31)])
    keyed("C", [(f, f * 0.1) for f in range(40, 51)])
    holder = keyed("Holder", [(0, 0.0), (5, 1.0), (8, 1.0), (10, 2.0)])  # hold 5..8
    for f in (
        0,
        10,
    ):  # translateY: flat channel (a pure hold -> only visible with holds on)
        holder.location[1] = 2.0
        holder.keyframe_insert(data_path="location", index=1, frame=f)

    tmp = ptk.TempArtifacts(prefix="btk_seq_live_")
    wav_path = tmp.path(".wav")
    with wave.open(wav_path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(8000)
        wf.writeframes(b"\x00\x00" * 4000)  # 0.5 s -> 12 frames @ 24
    scene = bpy.context.scene
    AudioUtils.add_clip(wav_path, frame_start=22, name="Cue", scene=scene)
    # Background Blender creates the undo stack lazily at the first push — give it a
    # baseline step so the first ``ed.undo`` has something to return to (a GUI
    # session always has the file-load step).
    bpy.ops.ed.undo_push(message="baseline")

    BlenderShotStore.clear_active()
    store = BlenderShotStore.active()
    store.define_shot("A", 0, 10, objects=["A", "Holder"])
    store.define_shot("B", 20, 30, objects=["B"])
    store.define_shot("C", 40, 50, objects=["C"])
    a_id, b_id, c_id = (store.shot_by_name(n).shot_id for n in ("A", "B", "C"))
    store.set_active_shot(a_id)

    # ---- load the real panel ------------------------------------------------------
    sb = Switchboard()
    handler = BlenderUiHandler(switchboard=sb)
    sb = handler.sb  # a process singleton keeps the switchboard holding the UIs
    Tcl.register_shared(sb)
    ui = handler.get("shot_sequencer")
    pump()
    ctl = ui.slots.controller
    widget = ctl._get_sequencer_widget()
    check(
        "panel: sequencer widget promoted",
        widget is not None and hasattr(widget, "add_track"),
    )
    check("panel: controller bound to the ACTIVE store", ctl.sequencer.store is store)

    # ---- initial sync: tracks, clips, audio, icons -------------------------------------
    ctl._set_view_mode("all")
    ctl._sync_to_widget(shot_id=a_id)
    pump()
    names = sorted(td.name for td in widget.tracks())
    check(
        "sync: object + audio tracks present",
        names == ["A", "B", "C", "Cue", "Holder"],
        f"{names}",
    )
    clips = widget.clips()
    a_clip = next(
        (c for c in clips if c.data.get("obj") == "A" and not c.sub_row), None
    )
    check(
        "sync: A clip [0,10] on active shot, label blank + centre abbrev",
        a_clip is not None
        and (a_clip.start, a_clip.start + a_clip.duration) == (0, 10)
        and a_clip.label == ""
        and a_clip.data.get("label_center") == "tx"
        and a_clip.data.get("attributes") == ["translateX"],
        f"{a_clip and (a_clip.start, a_clip.duration, a_clip.label, a_clip.data)}",
    )
    holder_clips = [c for c in clips if c.data.get("obj") == "Holder" and not c.sub_row]
    spans = sorted((c.start, c.start + c.duration) for c in holder_clips)
    check(
        "sync: Holder's two motion runs merge on the main track (gap < detection_threshold, as mayatk)",
        spans == [(0, 10)]
        and "translateX" in holder_clips[0].data.get("attributes", []),
        f"{spans}",
    )
    b_clip = next(
        (c for c in clips if c.data.get("obj") == "B" and not c.sub_row), None
    )
    check(
        "sync: non-active shot clip is read-only/locked",
        b_clip is not None and b_clip.data.get("read_only") and b_clip.locked,
    )
    audio = [c for c in clips if c.data.get("is_audio")]
    check(
        "sync: one audio clip, strip name as track id, waveform attached",
        len(audio) == 1
        and audio[0].data.get("audio_track_id") == "Cue"
        and audio[0].data.get("orig_start") == 22
        and len(audio[0].data.get("waveform") or []) > 0,
        f"{[(c.data.get('audio_track_id'), c.data.get('orig_start'), len(c.data.get('waveform') or [])) for c in audio]}",
    )
    a_track = next(td for td in widget.tracks() if td.name == "A")
    check(
        "sync: mesh track carries a NodeIcons icon",
        a_track.icon is not None and not a_track.icon.isNull(),
    )
    check(
        "sync: footer summary shows the active shot",
        "[1/3]" in ui.footer.text(),
        ui.footer.text(),
    )

    # ---- sub-rows + Show Internal Holds ----------------------------------------------
    ctl._set_show_internal_holds(
        False
    )  # the option-box state persists across runs (QSettings)
    pump()
    h_track = next(td for td in widget.tracks() if td.name == "Holder")
    rows = ctl._provide_sub_rows(h_track.track_id, "Holder")
    row_map = {attr: segs for attr, segs in rows}
    check(
        "sub-rows: translateX row split at the hold; flat translateY hidden by default",
        "translateX" in row_map
        and [(s[0], s[0] + s[1]) for s in row_map["translateX"]] == [(0, 5), (8, 10)]
        and "translateY" not in row_map,
        f"{[(a, [(s[0], s[1]) for s in segs]) for a, segs in rows]}",
    )
    check(
        "sub-rows: each segment carries a curve preview",
        all(s[4].get("curve_preview") for s in row_map.get("translateX", [])),
    )
    ctl._set_show_internal_holds(True)
    pump()
    h_track = next(td for td in widget.tracks() if td.name == "Holder")
    rows = dict(ctl._provide_sub_rows(h_track.track_id, "Holder"))
    segs_y = rows.get("translateY", [])
    check(
        "holds on: the flat translateY channel appears as one is_hold span [0,10]",
        [(s[0], s[0] + s[1], bool(s[4].get("is_hold"))) for s in segs_y]
        == [(0, 10, True)],
        f"{[(s[0], s[1], s[4].get('is_hold')) for s in segs_y]}",
    )
    check(
        "holds on: motion rows keep normal styling",
        all(not s[4].get("is_hold") for s in rows.get("translateX", [])),
    )
    ctl._set_show_internal_holds(False)
    pump()

    # ---- expand a track through the widget's provider protocol --------------------------
    a_track = next(td for td in widget.tracks() if td.name == "A")
    widget.expand_track(a_track.track_id)
    pump()
    sub = [c for c in widget.clips() if c.sub_row and c.data.get("obj") == "A"]
    check(
        "expand_track: sub-row clip for A.translateX built by the provider",
        len(sub) == 1 and sub[0].data.get("attr_name") == "translateX",
        f"{[(c.sub_row, c.data.get('attr_name')) for c in sub]}",
    )

    # ---- Graph-Editor key selection sync --------------------------------------------------
    ctl.on_key_selection_changed([{"clip_id": sub[0].clip_id, "times": [3.0, 4.0]}])
    a_obj = bpy.data.objects["A"]
    sel = sorted(
        round(kp.co[0], 3)
        for fc in AnimUtils.get_fcurves(a_obj)
        for kp in fc.keyframe_points
        if kp.select_control_point
    )
    check(
        "key selection: exactly the named keys selected on A",
        sel == [3.0, 4.0],
        f"{sel}",
    )

    # ---- clip drag (main row): move_object_in_shot, shot grows + ripples --------------------
    a_clip = next(
        c for c in widget.clips() if c.data.get("obj") == "A" and not c.sub_row
    )
    ctl.on_clip_moved(a_clip.clip_id, 5.0)
    pump()
    check(
        "clip drag: A keys -> 5..15, shot A grew to 15, B rippled +5",
        key_times("A") == [float(5 + i) for i in range(11)]
        and store.shot_by_id(a_id).end == 15
        and store.shot_by_id(b_id).start == 25,
        f"A={key_times('A')[:2]}.. A.end={store.shot_by_id(a_id).end} B.start={store.shot_by_id(b_id).start}",
    )
    check(
        "clip drag: strip rippled with shot B (22 -> 27)",
        AudioUtils.get_clip("Cue")["frame_start"] == 27,
        str(AudioUtils.get_clip("Cue")["frame_start"]),
    )

    # ---- native undo through the widget ----------------------------------------------------
    ctl.on_undo()
    pump()
    check(
        "on_undo: keys + bounds + strip restored",
        key_times("A") == [float(i) for i in range(11)]
        and store.shot_by_id(a_id).end == 10
        and AudioUtils.get_clip("Cue")["frame_start"] == 22,
        f"A={key_times('A')[:2]}.. end={store.shot_by_id(a_id).end} strip={AudioUtils.get_clip('Cue')['frame_start']}",
    )
    check(
        "on_undo: controller still bound to a live store (undo swapped bpy.data)",
        ctl.sequencer.store is BlenderShotStore.active(),
    )

    # ---- audio clip drag ------------------------------------------------------------------
    ctl._sync_to_widget(shot_id=b_id)
    pump()
    audio = next(c for c in widget.clips() if c.data.get("is_audio"))
    ctl.on_clip_moved(audio.clip_id, 24.0)
    pump()
    check(
        "audio drag: strip moved to 24",
        AudioUtils.get_clip("Cue")["frame_start"] == 24,
        str(AudioUtils.get_clip("Cue")["frame_start"]),
    )

    # ---- Move to Shot: B's anim + strip into A ------------------------------------------------
    ids = [
        c.clip_id
        for c in widget.clips()
        if c.data.get("shot_id") == b_id and not c.sub_row
    ]
    seqs = ctl._clips_to_sequences(widget, ids)
    check(
        "move-to-shot: sequences collected (anim + audio)",
        sorted(s["kind"] for s in seqs) == ["anim", "audio"],
        f"{seqs}",
    )
    ctl._send_to_shot(seqs, a_id)
    pump()
    a, b = store.shot_by_id(a_id), store.shot_by_id(b_id)
    check(
        "move-to-shot: B keys + strip now inside A; A extended to fit; B emptied",
        all(a.start <= t <= a.end for t in own_key_times("B"))
        and a.start <= AudioUtils.get_clip("Cue")["frame_start"] <= a.end
        and "B" in a.objects
        and "B" not in b.objects,
        f"A={(a.start, a.end, a.objects)} B={(b.start, b.end, b.objects)} strip={AudioUtils.get_clip('Cue')['frame_start']} B keys={own_key_times('B')}",
    )
    names = sorted(td.name for td in widget.tracks())
    check(
        "move-to-shot: widget rebuilt (B track under A)",
        "B" in names and "Cue" in names,
        f"{names}",
    )

    # ---- per-key delete + delete clip ----------------------------------------------------------
    ctl._sync_to_widget(shot_id=a_id)
    pump()
    b_main = next(
        c for c in widget.clips() if c.data.get("obj") == "B" and not c.sub_row
    )
    ctl._delete_clip_keys([b_main.clip_id])
    pump()
    check(
        "delete clip: B's transform keys gone",
        own_key_times("B") == [],
        f"{own_key_times('B')}",
    )
    ctl.on_undo()
    pump()
    check(
        "undo restores B's keys",
        len(own_key_times("B")) == 11,
        f"{own_key_times('B')}",
    )

    # ---- playhead <-> scene frame, scrub arming, frame-change handler --------------------------
    scene = (
        bpy.context.scene
    )  # undo swapped bpy.data — never hold a Scene ref across it
    ctl.on_playhead_moved(7.0)
    check(
        "playhead -> scene.frame_current",
        scene.frame_current == 7,
        str(scene.frame_current),
    )
    check(
        "playhead: audio scrub armed once strips exist", scene.use_audio_scrub is True
    )
    scene.frame_set(3)
    pump()
    check(
        "frame_change_post -> widget playhead",
        abs(widget._timeline._scene.playhead.time - 3) < 1e-6,
        str(widget._timeline._scene.playhead.time),
    )

    # ---- keyframe-edit handler: new keyed selected object auto-joins the active shot ---------
    ctl._sync_to_widget(shot_id=a_id)
    pump()
    bpy.ops.mesh.primitive_cube_add()
    newb = bpy.context.active_object
    newb.name = "Newbie"
    for f, v in ((1, 0.0), (6, 3.0)):
        newb.location[0] = v
        newb.keyframe_insert(data_path="location", index=0, frame=f)
    bpy.context.view_layer.update()
    pump(n=20, ms=30)  # let the 200 ms debounce fire
    check(
        "keyframe edit: selected newly-keyed object merged into the active shot",
        "Newbie" in store.shot_by_id(a_id).objects,
        f"{store.shot_by_id(a_id).objects}",
    )

    # ---- transport + play controller --------------------------------------------------------
    transport = getattr(ui.footer, "_shot_transport_controls", None)
    pc = transport._play_controller if transport else None
    check(
        "transport: row attached, Blender play controller",
        pc is not None and type(pc).__name__ == "_BlenderPlayController",
    )
    if pc is not None:
        err = ""
        try:
            pc.play(True)
            pc.stop()
        except Exception as e:  # pragma: no cover
            err = repr(e)
        check(
            "transport: play/stop never raise (background: no screen -> logged, not thrown)",
            err == "",
            err,
        )
        scene = bpy.context.scene
        # The transport targets the ACTIVE SHOT, not the scene range: the
        # scene range spans every visible shot in adjacent/all view, so
        # go-to-start / go-to-end used to skip the current shot's own edges.
        active = store.shot_by_id(ctl.active_shot_id)
        expected = (
            (float(active.start), float(active.end))
            if active is not None and active.end > active.start
            else (float(scene.frame_start), float(scene.frame_end))
        )
        check(
            "transport: range_fn targets the active shot (scene range as fallback)",
            ctl._playback_range() == expected,
            f"{ctl._playback_range()} != {expected}",
        )

    # ---- track header menu: Reveal in Outliner -------------------------------------------------
    menu = QtWidgets.QMenu()
    ctl.on_track_menu(menu, ["C"])
    acts = [a.text() for a in menu.actions() if a.text()]
    check(
        "track menu: Reveal in Outliner offered",
        "Reveal in Outliner" in acts,
        f"{acts}",
    )
    next(a for a in menu.actions() if a.text() == "Reveal in Outliner").trigger()
    check(
        "track menu: reveal selected C",
        bpy.data.objects["C"].select_get()
        and bpy.context.view_layer.objects.active.name == "C",
    )

    # ---- track header menu: Copy to Clipboard --------------------------------------------------
    copy_act = next((a for a in menu.actions() if a.text().startswith("Copy ")), None)
    check(
        "track menu: Copy '<name>' to Clipboard offered",
        copy_act is not None and copy_act.text() == "Copy 'C' to Clipboard",
        f"{acts}",
    )
    if copy_act is not None:
        copy_act.trigger()
        pasted = QtWidgets.QApplication.clipboard().text()
        check(
            "track menu: clipboard holds the short name", pasted == "C", f"{pasted!r}"
        )
    menu_multi = QtWidgets.QMenu()
    ctl.on_track_menu(menu_multi, ["C", "B"])
    multi_act = next(
        (a for a in menu_multi.actions() if a.text().startswith("Copy ")), None
    )
    check(
        "track menu: multi-select copies every name, one per line",
        multi_act is not None and multi_act.text() == "Copy 2 Names to Clipboard",
        f"{multi_act and multi_act.text()}",
    )
    if multi_act is not None:
        multi_act.trigger()
        pasted = QtWidgets.QApplication.clipboard().text()
        check(
            "track menu: multi clipboard is newline-joined",
            pasted == "C" + chr(10) + "B",
            f"{pasted!r}",
        )

    # ---- clip context menu: Move to Shot submenu ---------------------------------------------
    ctl._sync_to_widget(shot_id=c_id)
    pump()
    c_main = next(
        c for c in widget.clips() if c.data.get("obj") == "C" and not c.sub_row
    )
    menu = QtWidgets.QMenu()
    ctl.on_clip_menu(menu, c_main.clip_id)
    titles = [a.text() for a in menu.actions() if a.text()]
    sub_menu = next((a.menu() for a in menu.actions() if a.menu() is not None), None)
    check(
        "clip menu: Store Keys / Lock Others / Unlock All / Move to Shot",
        {"Store Keys", "Lock Others", "Unlock All", "Move to Shot"} <= set(titles),
        f"{titles}",
    )
    check(
        "clip menu: no Delete row (the Delete key owns it)",
        not any("Delete" in t for t in titles),
        f"{titles}",
    )
    # One list of shots for Move and Copy: a Copy toggle (a widget row) heads
    # the submenu, then a separator, then the shots.
    rows = sub_menu.actions() if sub_menu is not None else []
    toggle = (
        rows[0].defaultWidget().findChild(QtWidgets.QCheckBox)
        if rows and isinstance(rows[0], QtWidgets.QWidgetAction)
        else None
    )
    labels = ["---" if a.isSeparator() else a.text() for a in rows[1:]]
    check(
        "clip menu: Move to Shot leads with the Copy toggle, the neighbours, then the named shots",
        toggle is not None and labels[:3] == ["---", "Previous Shot  (B)", "---"],
        f"toggle={toggle is not None} {labels}",
    )
    check(
        "clip menu: Move to Shot lists the OTHER shots only",
        len(labels) == 5 and all("C" not in lab.split("  ")[0] for lab in labels[3:]),
        f"{labels}",
    )

    # ---- shot-lane menu (mirror of mayatk's TestShotLaneMenu) -------------------------------
    # Unreachable before 2026-10-04: the slots never set ``zone_menu_enabled``,
    # so every right-click fell through to the widget's default menu.
    check(
        "shot lane: right-clicks are routed to the controller's zone menu",
        widget.zone_menu_enabled,
    )

    def menu_rows(lst):
        return [w.text() for w in lst._row_widgets() if hasattr(w, "text")]

    lane_shot = store.sorted_shots()[0]
    mid = (lane_shot.start + lane_shot.end) / 2.0
    lane = ctl._build_shot_lane_context_menu(mid)
    try:
        root = menu_rows(lane.list)
        by_text = {w.text(): w for w in lane.list._row_widgets() if hasattr(w, "text")}
        check(
            "shot lane: Edit / New Shot / Split / Merge / Move To / Add Frames / Trim"
            " / Delete",
            root
            and root[0] == f'Edit "{lane_shot.name}"…'
            and root[-1] == f'Delete "{lane_shot.name}"…'
            and all(
                lbl in root
                for lbl in (
                    "New Shot",
                    f"Split Here ({mid:.0f})",
                    "Merge",
                    "Move To",
                    "Add Frames",
                    "Trim Empty Space",
                )
            ),
            f"{root}",
        )
        check(
            "shot lane: the verbs fan out into their forms",
            menu_rows(by_text["New Shot"].sublist)
            == ["Insert Shot Before", "Insert Shot After"]
            and menu_rows(by_text["Trim Empty Space"].sublist)
            == ["Trim Leading Space", "Trim Trailing Space"],
            f"{menu_rows(by_text['New Shot'].sublist)} / "
            f"{menu_rows(by_text['Trim Empty Space'].sublist)}",
        )
    finally:
        lane.dispose()
    gap_t = lane_shot.end + 1.0
    if not any(s.start <= gap_t <= s.end for s in store.shots):
        outside = ctl._build_shot_lane_context_menu(gap_t)
        try:
            check(
                "shot lane: outside every shot only creation remains",
                menu_rows(outside.list) == ["New Shot"],
                f"{menu_rows(outside.list)}",
            )
        finally:
            outside.dispose()
    tl = ctl._build_timeline_context_menu(mid)
    try:
        check(
            "timeline: its own menu (markers + display toggles)",
            menu_rows(tl.list)[:1] == [f"Add Marker at {mid:.0f}…"],
            f"{menu_rows(tl.list)}",
        )
    finally:
        tl.dispose()

    # A lane action through to the panel's undo: Split, then Undo restores the one
    # shot, Redo brings the cut back -- the restore point paired with its own step.
    n_shots = len(store.shots)
    ctl.split_shot_at(lane_shot.shot_id, mid)
    pump()
    split_ok = len(store.shots) == n_shots + 1
    ctl.on_undo()
    pump()
    undo_ok = len(store.shots) == n_shots
    ctl.on_redo()
    pump()
    check(
        "shot lane: Split, panel Undo, panel Redo (restore point paired to its step)",
        split_ok and undo_ok and len(store.shots) == n_shots + 1,
        f"split={split_ok} undo={undo_ok} redo={len(store.shots)}",
    )
    ctl.on_undo()
    pump()

    # ---- shot combo helpers --------------------------------------------------------------------
    cand = ctl.sequencer.detect_next_shot(gap_threshold=5.0)
    check("detect_next_shot on a fully covered scene -> None", cand is None, f"{cand}")
    n_before = len(store.shots)
    ctl._create_shot_one_click()
    pump()
    check(
        "one-click New Shot appended after the last shot",
        len(store.shots) == n_before + 1
        and store.sorted_shots()[-1].start >= store.sorted_shots()[-2].end,
        f"{[(s.name, s.start, s.end) for s in store.sorted_shots()]}",
    )
    ctl._trim_shot(
        store.sorted_shots()[-1].shot_id
    )  # empty shot: trim is a no-op, must not raise
    pump()

    # ---- store invalidation (scene swap) rebinds cleanly -----------------------------------
    BlenderShotStore.clear_active()
    BlenderShotStore._notify_invalidated()
    pump()
    check(
        "invalidation: controller rebound to the new active store",
        ctl.sequencer.store is BlenderShotStore.active(),
    )
    # The host's scene watcher holds the handlers (``btk.SequencerHost.watch_scene``).
    watch = ctl._scene_watch
    check(
        "invalidation: handlers re-registered",
        watch is not None
        and any(
            fn == watch._on_frame_change for fn in bpy.app.handlers.frame_change_post
        ),
    )

    ctl.remove_callbacks()
    check(
        "teardown: handlers detached",
        ctl._scene_watch is None
        and not any(
            fn == watch._on_frame_change for fn in bpy.app.handlers.frame_change_post
        ),
    )

except Exception:
    traceback.print_exc(file=sys.stdout)
    lines.append("FAIL unhandled exception")
finally:
    if tmp is not None:
        tmp.cleanup()

print("\n".join(lines))
ok = bool(lines) and all(ln.startswith("OK") for ln in lines)
print(
    f"===RESULT: {'PASS' if ok else 'FAIL'}=== ({sum(1 for ln in lines if ln.startswith('OK'))}/{len(lines)})"
)
