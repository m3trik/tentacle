"""Manual harness for the Blender materials rename-affix option box.

Requires a real Blender binary (it ``import bpy`` and builds real Qt widgets), so it is
**not** a CI/unittest target — the ``blender/`` subdir + non-``test_`` name keep it out of
auto-discovery. Run against a *fresh* Blender (never an existing session)::

    blender --background --factory-startup --python tentacle/test/blender/materials_rename_affix_check.py

Confirms end-to-end, against real ``bpy`` + real widgets, that the shared
``MaterialsRenameAffixMixin`` renames a material when the apply path is triggered — isolating
"the affix doesn't apply" as a *trigger* problem (headless Enter/click delivery), not a bug in
``_apply_rename_affix`` / ``_join_affix`` / the Blender ``_rename_current`` hook:

  * LOGIC (fake widgets, REAL ``_rename_current``): Auto/Prefix/Suffix each rename the real
    datablock; an ambiguous case leaves it untouched.
  * WIDGETS (REAL Switchboard + Menu + option box): ``_add_rename_control`` builds a real
    Label + LineEdit (on top) + ComboBox; emitting the field's ``returnPressed`` AND calling
    ``lbl005()`` with affix text both rename the real material (the two commit paths), while
    ``lbl005()`` with an empty field falls through to making the combo editable.
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


def clear_mats():
    import bpy

    for m in list(bpy.data.materials):
        bpy.data.materials.remove(m)


def fake_ui(current, editable_sink=None):
    """Minimal cmb002 stand-in: currentData returns the current material NAME."""
    cmb = NS(
        currentData=lambda: current,
        init_slot=lambda: None,
        setAsCurrent=lambda n: None,
        setEditable=(lambda v: editable_sink.__setitem__("v", v)) if editable_sink is not None else (lambda v: None),
    )
    return NS(cmb002=cmb)


def option_box_item_names(menu):
    """objectNames of lbl005's option-box menu widgets, in grid-ROW order."""
    from qtpy import QtWidgets

    lbl = next(
        (c for c in menu.findChildren(QtWidgets.QWidget) if c.objectName() == "lbl005"),
        None,
    )
    if lbl is None:
        return []
    ob = lbl.option_box.get_menu(create=False)
    if ob is None:
        return []
    grid = ob.gridLayout
    rows = []
    for i in range(grid.count()):
        item = grid.itemAt(i)
        w = item.widget() if item is not None else None
        if w is None:
            continue
        row = grid.getItemPosition(i)[0]
        # unwrap: an option-box-wrapped item nests the named widget; ours aren't wrapped
        n = w.objectName()
        if not n:
            named = [c for c in w.findChildren(QtWidgets.QWidget) if c.objectName() in ("txt000", "cmb_rename_mode")]
            n = named[0].objectName() if named else ""
        if n in ("txt000", "cmb_rename_mode"):
            rows.append((row, n))
    return [n for _r, n in sorted(rows)]


try:
    import bpy
    from tentacle import tcl_blender  # noqa: F401 — provisions Qt (qtpy/PySide6) for slot imports
    from tentacle.slots.blender.materials import MaterialsSlots

    def make_slot():
        return MaterialsSlots.__new__(MaterialsSlots)

    # ---- LOGIC: fake widgets, REAL _rename_current against real datablocks ----
    def logic_case(label, base, affix, mode, expect):
        clear_mats()
        bpy.data.materials.new(base)
        slot = make_slot()
        slot.ui = fake_ui(base)
        slot.sb = NS(message_box=lambda *a, **k: None)
        slot._rename_affix = NS(text=lambda: affix, clear=lambda: None)
        slot._rename_mode_combo = NS(currentText=lambda: mode)
        slot._apply_rename_affix()
        if expect:
            check(f"logic {label}", bpy.data.materials.get(expect) is not None, f"want {expect!r}")
        else:
            check(f"logic {label}", bpy.data.materials.get(base) is not None, "base untouched")

    logic_case("auto suffix", "mat", "_lod0", "Auto", "mat_lod0")
    logic_case("auto prefix", "mat", "metal_", "Auto", "metal_mat")
    logic_case("prefix mode", "mat", "metal", "Prefix", "metal_mat")
    logic_case("suffix mode", "mat", "lod0", "Suffix", "mat_lod0")
    logic_case("auto ambiguous rejected", "mat", "plain", "Auto", None)

    # ---- WIDGETS: REAL Switchboard + Menu + option box ----
    from qtpy import QtWidgets
    from uitk import Switchboard
    from uitk.widgets.menu import Menu

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)

    def widget_slot():
        clear_mats()
        slot = make_slot()
        slot.sb = Switchboard()
        menu = Menu()
        slot._add_rename_control(menu)
        return slot, menu

    slot, menu = widget_slot()
    check("field has returnPressed signal", hasattr(slot._rename_affix, "returnPressed"),
          type(slot._rename_affix).__name__)
    order = option_box_item_names(menu)
    check("field above combo", order == ["txt000", "cmb_rename_mode"], str(order))

    # returnPressed commit path
    bpy.data.materials.new("mat")
    slot.ui = fake_ui("mat")
    slot._rename_mode_combo.setCurrentText("Auto")
    slot._rename_affix.setText("_lod0")
    slot._rename_affix.returnPressed.emit()
    check("returnPressed renames", bpy.data.materials.get("mat_lod0") is not None,
          str([m.name for m in bpy.data.materials]))

    # lbl005() commit path (affix present)
    slot, menu = widget_slot()
    bpy.data.materials.new("mat")
    slot.ui = fake_ui("mat")
    slot._rename_mode_combo.setCurrentText("Suffix")
    slot._rename_affix.setText("lod1")
    slot.lbl005()
    check("lbl005 with affix renames", bpy.data.materials.get("mat_lod1") is not None,
          str([m.name for m in bpy.data.materials]))

    # lbl005() with empty field -> editable, no rename
    slot, menu = widget_slot()
    bpy.data.materials.new("solo")
    editable = {"v": False}
    slot.ui = fake_ui("solo", editable_sink=editable)
    slot._rename_affix.setText("")
    slot.lbl005()
    check("lbl005 empty -> setEditable(True)", editable["v"] is True)
    check("lbl005 empty did not rename", bpy.data.materials.get("solo") is not None)

    print("\n".join(lines))
    print("RESULT:", "PASS" if all(l.startswith("OK") for l in lines) else "FAIL")

except Exception:
    print("HARNESS ERROR:\n" + traceback.format_exc())
    print("RESULT: FAIL")
