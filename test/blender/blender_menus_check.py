"""Headless no-dead-links guard for the both-button menu (``blender#startmenu`` / ``Blender``).

Run in a **fresh** headless Blender (never an existing session)::

    blender --background --factory-startup --python tentacle/test/blender/blender_menus_check.py

Asserts every native-menu idname the radial maps to is a real Blender menu (so no wedge can
dead-end), that ``btk.menu_exists`` rejects a bogus id, and that the per-mode relabel/disable logic
in ``Blender._init_button`` is correct (Object↔Mesh; edit-only wedges off in Object mode). The
actual ``wm.call_menu`` popup is modal + GUI-only, so it's proven live, not here.
"""
import sys
import os
import traceback
from pathlib import Path

MONO = Path(__file__).resolve().parents[3]
for _pkg in ("pythontk", "uitk", "tentacle", "blendertk"):
    _p = str(MONO / _pkg)
    if os.path.isdir(_p) and _p not in sys.path:
        sys.path.insert(0, _p)
os.environ.setdefault("QT_API", "pyside6")

import bpy
from tentacle import tcl_blender  # noqa: F401 — provisions qtpy so the slot import resolves
from tentacle.slots.blender.blender import Blender
import blendertk as btk

lines = []


def log(*a):
    print(*a)
    sys.stdout.flush()


def check(name, cond, detail=""):
    lines.append(f"{'OK  ' if cond else 'FAIL'} {name}{(' | ' + detail) if detail else ''}")


class _Btn:
    """Minimal stand-in for the Qt button the slot's ``_init`` touches."""

    def __init__(self, name):
        self._name = name
        self.text = None
        self.enabled = True
        self.tip = None

    def objectName(self):
        return self._name

    def setText(self, t):
        self.text = t

    def setEnabled(self, e):
        self.enabled = e

    def setToolTip(self, t):
        self.tip = t


def _menu_idnames():
    """Every menu idname the radial can resolve to (all per-mode + mode-agnostic entries)."""
    ids = []
    for spec in Blender._BUTTON_MENUS.values():
        ids += [v for k, v in spec.items() if k not in ("label", "edit_label")]
    return ids


def main():
    try:
        # 1. No dead links — every mapped idname is a registered Blender menu.
        bad = sorted({i for i in _menu_idnames() if not btk.menu_exists(i)})
        check("every wedge menu resolves to a real Blender menu", not bad, f"{bad}")
        check("menu_exists rejects a bogus id", not btk.menu_exists("VIEW3D_MT_does_not_exist"))

        # 2. Mode-sensitive set is exactly the relabel/disable buttons.
        derived = {
            b
            for b, spec in Blender._BUTTON_MENUS.items()
            if spec.get("edit_label") or not (spec.get("*") or spec.get("OBJECT"))
        }
        check(
            "_MODE_SENSITIVE matches the buttons that relabel/disable",
            set(Blender._MODE_SENSITIVE) == derived,
            f"declared={sorted(Blender._MODE_SENSITIVE)} derived={sorted(derived)}",
        )

        # 3. Object-mode relabel/disable (default headless mode is OBJECT).
        inst = Blender.__new__(Blender)  # bypass __init__ (no switchboard needed)
        check("headless mode is OBJECT", inst._mode() == "OBJECT", inst._mode())

        b001 = _Btn("b001")
        inst._init_button(b001)
        check("b001 labels 'Object' in Object mode", b001.text == "Object", f"{b001.text!r}")

        b006 = _Btn("b006")
        inst._init_button(b006)
        check("b006 (Vertex) disabled in Object mode", b006.enabled is False)
        check("b006 (Vertex) resolves to no menu in Object mode", inst._menu_for("b006") is None)

        check(
            "b003 (Transform) resolves mode-agnostically",
            inst._menu_for("b003") == "VIEW3D_MT_transform",
            f"{inst._menu_for('b003')!r}",
        )
        check(
            "b000 (Add) resolves to the Object-mode Add menu",
            inst._menu_for("b000") == "VIEW3D_MT_add",
            f"{inst._menu_for('b000')!r}",
        )

        # 4. _open routing (the deferred-popup glue): a valid wedge schedules
        # call_native_menu(idname); an N/A wedge messages instead. Patch the timer to run the
        # one-shot synchronously and call_native_menu to a recorder (no modal popup).
        recorded, messages = [], []
        inst.sb = type("SB", (), {"message_box": lambda self, m: messages.append(m)})()
        orig_call, orig_reg = btk.call_native_menu, bpy.app.timers.register
        btk.call_native_menu = lambda idname: recorded.append(idname)
        bpy.app.timers.register = lambda fn, **kw: fn()
        try:
            inst._open("b000")  # Add — valid in Object mode
            inst._open("b006")  # Vertex — N/A in Object mode → message
        finally:
            btk.call_native_menu, bpy.app.timers.register = orig_call, orig_reg
        check(
            "b000 routes to a deferred call_native_menu('VIEW3D_MT_add')",
            recorded == ["VIEW3D_MT_add"],
            f"{recorded}",
        )
        check(
            "b006 in Object mode messages instead of popping",
            len(messages) == 1 and "Edit Mode" in messages[0],
            f"{messages}",
        )

        # 5. Edit-mesh path (best-effort — needs the default mesh + a valid context).
        try:
            bpy.ops.object.mode_set(mode="EDIT")
            if inst._mode() == "EDIT_MESH":
                b001e = _Btn("b001")
                inst._init_button(b001e)
                check("b001 relabels to 'Mesh' in Edit mode", b001e.text == "Mesh", f"{b001e.text!r}")
                b006e = _Btn("b006")
                inst._init_button(b006e)
                check("b006 (Vertex) enabled in Edit mode", b006e.enabled is True)
                check(
                    "b002 (Select) resolves to the edit-mesh Select menu",
                    inst._menu_for("b002") == "VIEW3D_MT_select_edit_mesh",
                    f"{inst._menu_for('b002')!r}",
                )
            else:
                lines.append("note: could not enter EDIT_MESH headless — edit-mode checks skipped")
            bpy.ops.object.mode_set(mode="OBJECT")
        except Exception as error:
            lines.append(f"note: edit-mode checks skipped ({error!r})")
    except Exception as error:
        lines.append(f"FAIL setup: {error!r}")
        lines.append(traceback.format_exc())
    finally:
        for line in lines:
            log(line)
        ok = all(line.startswith(("OK", "note")) for line in lines) and lines
        log(f"===RESULT: {'PASS' if ok else 'FAIL'}===")


main()
