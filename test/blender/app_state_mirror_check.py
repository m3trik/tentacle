"""Manual harness: ``*_init`` methods that mirror live DCC state must not fire their slots.

Requires a real Blender binary (the slot modules ``import bpy``), so it is **not** a CI target
— the ``blender/`` subdir and the non-``test_`` name keep it out of auto-discovery. Run against
a *fresh* Blender (never an existing session)::

    blender --background --factory-startup --python tentacle/test/blender/app_state_mirror_check.py

The bug: opening the Blender selection submenu popped "<hl>Box Select</hl> tool active." every
time. chk005 (Select Style: Marquee) persisted like any widget, and uitk *fires the slot* on
state restore (``StateManager.apply`` unblocks signals per ``block_signals_on_restore``, default
False) — so merely opening the panel re-set the viewport tool and toasted. The same shape sat in
four other submenus (symmetry re-mirrored the mesh, subdivision re-subdivided the selection,
preferences overwrote the scene's units), plus a second trigger: ``init_slot`` blocks only the
widget it is initializing, so a ``*_init`` seeding its *siblings* (a radio group) fired theirs.

``Slots.mirror_app_state`` fixes both. ``test/test_slots_base.py`` pins the primitive headlessly;
this pins what that test cannot reach — that each real Blender ``*_init`` actually calls it, and
seeds honestly from live bpy state.

Pins, per submenu, driving the REAL ``*_init`` against real bpy state:

1. **No message_box and no slot call during init** — the reported symptom, caught by recording
   every ``sb.message_box`` and every slot invocation across the init.
2. **restore_state is False** on every widget the init mirrors — the mechanism that stops uitk
   from restoring (and re-firing) a stale value on the next panel open.
3. **The seed reflects live bpy state**, not the .ui default — set the scene up two different
   ways and assert the widget follows.
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


try:
    import bpy
    from tentacle import tcl_blender  # noqa: F401 — provisions Qt (qtpy/PySide6); must precede it
    from qtpy import QtWidgets
    from uitk import ComboBox  # the REAL widget: its `add` re-arms restore_state (see below)

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    # ---------------------------------------------------------------- doubles
    class _Recorder:
        """Stands in for the switchboard, recording what an init tried to surface."""

        def __init__(self):
            self.messages = []

        def message_box(self, text, *a, **k):
            self.messages.append(text)

        def create_button_groups(self, ui, *args, **kwargs):
            return []

    def make_slot(cls, ui):
        """Instance without the UI-loading __init__ (headless: no loaded_ui)."""
        slot = cls.__new__(cls)
        slot.sb = _Recorder()
        slot.ui = ui
        return slot

    class _Ui:
        """A bag of real Qt widgets addressable as ``ui.chk005``, like a loaded uitk ui."""

        def __init__(self, **widgets):
            self._fired = []
            for name, w in widgets.items():
                w.setObjectName(name)
                w.restore_state = True  # uitk's default (MainWindow.register_widget)
                w.ui = self
                self._connect(name, w)
                setattr(self, name, w)

        def _connect(self, name, w):
            """Stand in for uitk's slot wiring: record any slot the init provokes.

            Deliberately left UNBLOCKED. ``init_slot`` blocks the widget it is initializing,
            but uitk's *deferred* init path runs ``*_init`` unblocked (slots.py: "the deferred
            batch ran *unblocked*, so a widget whose ``*_init`` mutates its value (``addItems``
            flips a combo to index 0 ...)"), which is the harsher of the two paths and the one
            worth pinning — it is what caught the combos firing on ``add`` alone.
            """
            if isinstance(w, QtWidgets.QAbstractButton):
                w.toggled.connect(lambda v, n=name: self._fired.append((n, v)))
            elif isinstance(w, QtWidgets.QComboBox):
                w.currentIndexChanged.connect(lambda v, n=name: self._fired.append((n, v)))
            else:
                w.valueChanged.connect(lambda v, n=name: self._fired.append((n, v)))

        @property
        def fired(self):
            return list(self._fired)

    def chk():
        w = QtWidgets.QCheckBox()
        w.setCheckable(True)
        return w

    def assert_quiet_init(label, slot, ui, widget_names):
        """The core contract: init surfaced nothing and ran no slot; widgets opt out of restore."""
        check(f"{label}: init pops no message box", not slot.sb.messages, f"{slot.sb.messages}")
        check(f"{label}: init fires no slot", not ui.fired, f"{ui.fired}")
        stateful = [n for n in widget_names if getattr(ui, n).restore_state]
        check(
            f"{label}: mirrored widgets opt out of QSettings restore",
            not stateful,
            f"still restore_state=True: {stateful}",
        )

    def reset_scene():
        if bpy.context.view_layer.objects.active and bpy.context.view_layer.objects.active.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")
        for o in list(bpy.data.objects):
            bpy.data.objects.remove(o, do_unlink=True)

    # ================================================================ selection
    from tentacle.slots.blender.selection import Selection

    # -- chk005-007 Select Style: the reported bug --
    ui = _Ui(chk005=chk(), chk006=chk(), chk007=chk())
    slot = make_slot(Selection, ui)
    for n in ("chk005", "chk006", "chk007"):  # uitk inits each registered widget
        getattr(slot, f"{n}_init")(getattr(ui, n))
    assert_quiet_init("selection chk005-7 (Select Style)", slot, ui, ("chk005", "chk006", "chk007"))

    # The reported symptom, stated exactly: the toast must be absent at init.
    check(
        "selection: no '<hl>Box Select</hl> tool active.' toast on submenu init (the report)",
        not any("tool active" in m for m in slot.sb.messages),
        f"{slot.sb.messages}",
    )

    # ...and the tool itself must be untouched — the toast was only the visible half.
    check(
        "selection: chk005_init sets no viewport tool",
        not ui.fired,
        f"slots fired: {ui.fired}",
    )

    # -- chk004 Ignore Backfacing: seed must follow live X-ray, both ways --
    import blendertk as btk

    areas = btk.get_areas("VIEW_3D")
    if areas:  # --background still yields a VIEW_3D area
        for xray, expect in ((True, False), (False, True)):
            areas[0].spaces.active.shading.show_xray = xray
            ui = _Ui(chk004=chk())
            slot = make_slot(Selection, ui)
            slot.chk004_init(ui.chk004)
            check(
                f"selection chk004: seeds Ignore-Backfacing={expect} from live show_xray={xray}",
                ui.chk004.isChecked() is expect,
                f"got {ui.chk004.isChecked()}",
            )
            assert_quiet_init(f"selection chk004 (xray={xray})", slot, ui, ("chk004",))
    else:
        check("selection chk004: VIEW_3D area available to seed from", False, "no VIEW_3D area")

    # -- cmb005 Selection Constraints: one-shot ops must never restore --
    # The REAL uitk ComboBox, not a QComboBox with a stubbed `add`: `ComboBox.add` ends with
    # `restore_state = not self.has_header`, so a headerless combo populated inside the seed
    # re-arms its own persistence. A stub `add` doesn't, and passed this vacuously.
    ui = _Ui(cmb005=ComboBox())
    slot = make_slot(Selection, ui)
    slot.cmb005_init(ui.cmb005)
    check(
        "selection cmb005: Selection Constraints opt out of restore (one-shot ops)",
        not ui.cmb005.restore_state,
        f"restore_state={ui.cmb005.restore_state}",
    )
    check(
        "selection cmb005: populated with the items it dispatches",
        ui.cmb005.count() == len(Selection._CONSTRAINT_OPS) + 1,
        f"count={ui.cmb005.count()}",
    )
    assert_quiet_init("selection cmb005", slot, ui, ("cmb005",))

    # ================================================================ symmetry
    from tentacle.slots.blender.symmetry import Symmetry

    reset_scene()
    bpy.ops.mesh.primitive_cube_add()
    cube = bpy.context.active_object

    # A mesh mirrored in Y is the case that used to toast: chk000_init seeded its SIBLING
    # chk001, whose signals init_slot never blocked.
    for axis, expect in (("y", "chk001"), ("z", "chk002"), (None, None)):
        for a in "xyz":
            cube.data.__setattr__(f"use_mirror_{a}", a == axis)
        ui = _Ui(chk000=chk(), chk001=chk(), chk002=chk())
        slot = make_slot(Symmetry, ui)
        for n in ("chk000", "chk001", "chk002"):
            getattr(slot, f"{n}_init")(getattr(ui, n))
        checked = [n for n in ("chk000", "chk001", "chk002") if getattr(ui, n).isChecked()]
        check(
            f"symmetry: mesh mirrored in {axis or 'nothing'} seeds {expect or 'no box'}",
            checked == ([expect] if expect else []),
            f"checked={checked}",
        )
        assert_quiet_init(f"symmetry chk000-2 (mirror {axis})", slot, ui, ("chk000", "chk001", "chk002"))

    # Multi-axis mesh: seeding bypasses the group's exclusivity handler, so only one may light.
    for a in "xyz":
        cube.data.__setattr__(f"use_mirror_{a}", True)
    ui = _Ui(chk000=chk(), chk001=chk(), chk002=chk())
    slot = make_slot(Symmetry, ui)
    slot.chk000_init(ui.chk000)
    n_checked = sum(getattr(ui, n).isChecked() for n in ("chk000", "chk001", "chk002"))
    check(
        "symmetry: an X+Y+Z mirrored mesh still lights exactly one radio box",
        n_checked == 1,
        f"{n_checked} boxes checked",
    )

    # -- chk004/5 match mode --
    for topo, expect in ((True, "chk005"), (False, "chk004")):
        cube.data.use_mirror_topology = topo
        ui = _Ui(chk004=chk(), chk005=chk())
        slot = make_slot(Symmetry, ui)
        for n in ("chk004", "chk005"):
            getattr(slot, f"{n}_init")(getattr(ui, n))
        checked = [n for n in ("chk004", "chk005") if getattr(ui, n).isChecked()]
        check(
            f"symmetry: use_mirror_topology={topo} seeds {expect}",
            checked == [expect],
            f"checked={checked}",
        )
        assert_quiet_init(f"symmetry chk004-5 (topo={topo})", slot, ui, ("chk004", "chk005"))

    # ================================================================ init order independence
    # Every radio member must opt out via its OWN init. uitk's immediate init path runs
    # slot-init -> state-init per widget, and chk006 precedes chk005 in selection#submenu.ui,
    # so a chk005_init that marked its siblings would land too late to stop chk006 restoring
    # (and toasting "Lasso Select tool active"). Same for symmetry's chk001/chk002/chk004.
    for cls, group in (
        (Selection, ("chk005", "chk006", "chk007")),
        (Symmetry, ("chk000", "chk001", "chk002")),
        (Symmetry, ("chk004", "chk005")),
    ):
        for name in group:
            ui = _Ui(**{n: chk() for n in group})
            slot = make_slot(cls, ui)
            getattr(slot, f"{name}_init")(getattr(ui, name))  # ONLY this widget's init runs
            check(
                f"{cls.__name__}.{name}_init alone opts {name} out of restore "
                "(init order must not matter)",
                not getattr(ui, name).restore_state,
                f"restore_state={getattr(ui, name).restore_state}",
            )

    # ================================================================ subdivision
    from tentacle.slots.blender.subdivision import Subdivision

    reset_scene()
    bpy.ops.mesh.primitive_cube_add()
    obj = bpy.context.active_object
    mod = obj.modifiers.new(name="Subdivision", type="SUBSURF")
    mod.levels, mod.render_levels = 2, 4

    ui = _Ui(s000=QtWidgets.QSpinBox(), s001=QtWidgets.QSpinBox())
    slot = make_slot(Subdivision, ui)
    slot.s000_init(ui.s000)
    slot.s001_init(ui.s001)
    check("subdivision s000: seeds viewport level 2 from the live SUBSURF modifier",
          ui.s000.value() == 2, f"got {ui.s000.value()}")
    check("subdivision s001: seeds render level 4 from the live SUBSURF modifier",
          ui.s001.value() == 4, f"got {ui.s001.value()}")
    assert_quiet_init("subdivision s000/s001", slot, ui, ("s000", "s001"))

    # No modifier -> nothing to mirror; must not invent a level or fire.
    obj.modifiers.remove(mod)
    ui = _Ui(s000=QtWidgets.QSpinBox(), s001=QtWidgets.QSpinBox())
    slot = make_slot(Subdivision, ui)
    slot.s000_init(ui.s000)
    slot.s001_init(ui.s001)
    assert_quiet_init("subdivision (no SUBSURF modifier)", slot, ui, ("s000", "s001"))

    # ================================================================ transform
    from tentacle.slots.blender.transform import TransformSlots as Transform

    for snap in (True, False):
        bpy.context.scene.tool_settings.use_snap_rotate = snap
        ui = _Ui(chk023=chk())
        slot = make_slot(Transform, ui)
        slot.chk023_init(ui.chk023)
        check(
            f"transform chk023: seeds Snap-Rotate={snap} from live tool_settings",
            ui.chk023.isChecked() is snap,
            f"got {ui.chk023.isChecked()}",
        )
        assert_quiet_init(f"transform chk023 (snap={snap})", slot, ui, ("chk023",))

    # ================================================================ preferences
    from tentacle.slots.blender.preferences import Preferences

    bpy.context.scene.unit_settings.system = "METRIC"
    bpy.context.scene.unit_settings.length_unit = "CENTIMETERS"
    bpy.context.scene.render.fps = 30

    ui = _Ui(cmb001=ComboBox(), cmb002=ComboBox())  # real widget — see the cmb005 note
    slot = make_slot(Preferences, ui)
    slot.cmb001_init(ui.cmb001)
    slot.cmb002_init(ui.cmb002)
    check(
        "preferences cmb001: seeds the scene's live length unit (CENTIMETERS)",
        ui.cmb001.currentData() == "CENTIMETERS",
        f"got {ui.cmb001.currentData()!r}",
    )
    check(
        "preferences cmb002: seeds the scene's live fps (30)",
        int(ui.cmb002.currentData() or 0) == 30,
        f"got {ui.cmb002.currentData()!r}",
    )
    # Both combos are POPULATED inside the init, and `add` emits currentIndexChanged on its
    # own — so this also pins that populating is done under the seed's blocked scope.
    assert_quiet_init("preferences cmb001/cmb002", slot, ui, ("cmb001", "cmb002"))

    # The scene must be exactly as we left it — an init is a READ of app state.
    check(
        "preferences: init does not write back to the scene",
        bpy.context.scene.unit_settings.length_unit == "CENTIMETERS"
        and bpy.context.scene.render.fps == 30,
        f"units={bpy.context.scene.unit_settings.length_unit} fps={bpy.context.scene.render.fps}",
    )

except Exception as e:
    lines.append(f"FAIL setup: {e!r}")
    lines.append(traceback.format_exc())

ok = all(line.startswith("OK") for line in lines)
print("\n===BLENDER-APP-STATE-MIRROR===")
print("\n".join(lines))
print(f"===RESULT: {'PASS' if ok else 'FAIL'}===")
