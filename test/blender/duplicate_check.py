"""Manual harness for tentacle.slots.blender.duplicate — the linked-duplicate ("instance") tools.

Requires a real Blender binary (``duplicate.py`` imports ``bpy`` at module scope), so it is
**not** a CI/unittest target — the ``blender/`` subdir + non-``test_`` name keep it out of
auto-discovery (same convention as ``materials_rename_affix_check.py``). Run against a *fresh*
Blender (never an existing session)::

    blender --background --factory-startup --python tentacle/test/blender/duplicate_check.py

Mirrors ``test/test_duplicate.py`` (the Maya-side regression suite, real ``maya.cmds``) with
real ``bpy.data`` objects and fake option-box widgets — no Qt needed, since ``Duplicate.__new__``
bypasses ``__init__`` (the same trick the Maya tests use).

The tb001 cases exist to prove, against real ``bpy``, the exact bug class fixed on the Maya
side (``tentacle/slots/maya/duplicate.py``): "Select Instanced Objects" must keep the
originally selected object(s) in the final selection alongside their instances, not just the
instances. ``blendertk.get_instances`` already includes the query objects by construction
(unlike ``mayatk.get_instances``, which excludes them by default) — this confirms the tentacle
slot layer doesn't accidentally filter them back out on the Blender side either.
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

lines = []


def check(name, cond, detail=""):
    lines.append(f"{'OK  ' if cond else 'FAIL'} {name}{(' | ' + detail) if detail else ''}")


def fake_menu(**widgets):
    """chk* -> isChecked() stand-in, s* -> value() stand-in (mirrors test_duplicate.py's
    Maya-side _FakeMenu/_FakeChk/_FakeSpin)."""
    ns = NS()
    for name, value in widgets.items():
        attr = "value" if name.startswith("s") else "isChecked"
        setattr(ns, name, NS(**{attr: (lambda v: lambda: v)(value)}))
    return ns


def fake_widget(**widgets):
    return NS(option_box=NS(menu=fake_menu(**widgets)))


try:
    import bpy
    import blendertk as btk
    from tentacle import tcl_blender  # noqa: F401 — provisions Qt (qtpy/PySide6) for slot imports
    from tentacle.slots.blender.duplicate import Duplicate

    def make_slot():
        slot = Duplicate.__new__(Duplicate)
        captured = []
        slot.sb = NS(message_box=lambda *a, **k: captured.append((a, k)), messages=captured)
        return slot

    def reset():
        bpy.ops.object.select_all(action="DESELECT")
        for o in list(bpy.data.objects):
            bpy.data.objects.remove(o, do_unlink=True)

    def cube(name, loc):
        bpy.ops.mesh.primitive_cube_add(location=loc)
        o = bpy.context.active_object
        o.name = name
        return o

    def select_only(*objs):
        bpy.ops.object.select_all(action="DESELECT")
        for o in objs:
            o.select_set(True)
        if objs:
            bpy.context.view_layer.objects.active = objs[0]

    # ---- tb000: Convert to Instances — gating + real linked-duplicate result ----
    reset()
    slot = make_slot()
    widget = fake_widget(chk000=False, chk002=True, chk012=False, chk013=False)

    a = cube("tb000_a", (0, 0, 0))
    select_only(a)
    slot.tb000(widget)
    check("tb000: single selection warns", bool(slot.sb.messages))
    check("tb000: single selection creates no instance", a.data.users == 1)

    slot = make_slot()  # fresh sb.messages — the prior warn must not leak into this case
    b = cube("tb000_b", (3, 0, 0))
    select_only(a, b)
    bpy.context.view_layer.objects.active = a  # a = source
    slot.tb000(widget)
    check("tb000: 2 objects, no warning", not slot.sb.messages)
    check("tb000: target now shares source data", b.data is a.data)

    # chk012 (Retain Relative Scale) / chk013 (Non-Uniform) reach the engine.
    reset()
    slot = make_slot()
    src = cube("tb000_scale_src", (0, 0, 0))          # 2 x 2 x 2
    tgt = cube("tb000_scale_tgt", (5, 0, 0))
    for v in tgt.data.vertices:                       # 2 x 4 x 4, baked into the mesh
        v.co.y *= 2.0
        v.co.z *= 2.0
    bpy.context.view_layer.update()
    select_only(src, tgt)
    bpy.context.view_layer.objects.active = src
    slot.tb000(fake_widget(chk000=False, chk002=False, chk012=True, chk013=True))
    check("tb000: chk012+chk013 -> non-uniform retained scale",
          abs(tgt.scale.y / tgt.scale.x - 2.0) < 1e-3
          and abs(tgt.scale.z / tgt.scale.x - 2.0) < 1e-3,
          f"scale={tuple(round(v, 4) for v in tgt.scale)}")

    # ---- tb001: Select Instanced Objects — the bug class fixed on the Maya side ----
    reset()
    slot = make_slot()
    src = cube("tb001_src", (0, 0, 0))
    other = cube("tb001_other", (3, 0, 0))
    other.data = src.data  # linked duplicate == Maya-style "instance"
    select_only(src)

    slot.tb001(fake_widget(chk003=False))
    selected = set(bpy.context.view_layer.objects.selected)
    check(
        "tb001: original selection kept alongside its instance",
        {src, other} <= selected,
        f"selected={sorted(o.name for o in selected)}",
    )

    # Non-instanced selection -> warn, not a silent no-op re-select of itself.
    reset()
    slot = make_slot()
    lonely = cube("tb001_lonely", (0, 0, 0))
    select_only(lonely)
    slot.tb001(fake_widget(chk003=False))
    check("tb001: non-instanced selection warns", bool(slot.sb.messages))

    # All Instanced Objects -> scene-wide, ignores current selection.
    reset()
    slot = make_slot()
    x = cube("tb001_scene_x", (0, 0, 0))
    y = cube("tb001_scene_y", (3, 0, 0))
    y.data = x.data
    other_lonely = cube("tb001_scene_lonely", (6, 0, 0))
    select_only(other_lonely)
    slot.tb001(fake_widget(chk003=True))
    selected = set(bpy.context.view_layer.objects.selected)
    check(
        "tb001: All Instanced selects the scene-wide instanced pair",
        {x, y} <= selected and other_lonely not in selected,
        f"selected={sorted(o.name for o in selected)}",
    )

    # ---- tb002: Auto Instance — forwards option-box values; selects survivors ----
    # AutoInstancer's own matching algorithm is covered by blendertk's
    # test_auto_instancer.py; this only pins the slot-layer forwarding/result
    # handling, so btk.AutoInstancer.run_once is monkeypatched (mirrors the
    # Maya-side TestTb002AutoInstanceRouting fix — that class was found broken
    # while writing this test, patching the removed mtk.auto_instance instead
    # of mtk.AutoInstancer.run_once; same shape here, done right from the start).
    reset()
    slot = make_slot()
    captured = []
    fake_result = {"value": []}

    def fake_run_once(nodes, **kwargs):
        captured.append((nodes, kwargs))
        if kwargs.get("return_summary"):
            return fake_result["value"], btk.AutoInstancer.default_summary()
        return fake_result["value"]

    original_run_once = btk.AutoInstancer.run_once
    btk.AutoInstancer.run_once = fake_run_once
    try:
        tb002_widget = fake_widget(
            s000=0.001, chk004=True, chk005=False, chk006=False, chk007=False,
            chk008=False, chk009=True, chk010=True, chk011=True, s001=10000.0,
        )
        slot.tb002(tb002_widget)
        check(
            "tb002: forwards nodes=None + option-box values",
            len(captured) == 1 and captured[0][0] is None and captured[0][1]["tolerance"] == 0.001,
            str(captured),
        )
        check(
            "tb002: no matches warns instead of silent no-op",
            bool(slot.sb.messages) and "No matching geometry found" in str(slot.sb.messages[-1]),
            str(slot.sb.messages),
        )

        survivor = cube("tb002_survivor", (0, 0, 0))
        fake_result["value"] = [survivor]
        slot2 = make_slot()
        select_only()
        slot2.tb002(tb002_widget)
        check(
            "tb002: selects surviving result",
            set(bpy.context.view_layer.objects.selected) == {survivor},
        )
    finally:
        btk.AutoInstancer.run_once = original_run_once

    # ---- b005: Uninstance ----
    reset()
    slot = make_slot()
    src2 = cube("b005_src", (0, 0, 0))
    other2 = cube("b005_other", (3, 0, 0))
    other2.data = src2.data
    select_only(other2)
    slot.b005()
    check("b005: uninstance makes data single-user", other2.data is not src2.data)

    print("\n".join(lines))
    print("RESULT:", "PASS" if all(l.startswith("OK") for l in lines) else "FAIL")

except Exception:
    print("HARNESS ERROR:\n" + traceback.format_exc())
    print("RESULT: FAIL")
