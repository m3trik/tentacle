"""Ground truth for "I rebound the key in Preferences ▸ Keymap and nothing happened".

Launch a fresh GUI Blender (never an existing session)::

    blender --factory-startup --python tentacle/test/blender/gui_keymap_editor_check.py

The bridge installs its 3D-View items into the **addon** keyconfig, but Preferences ▸ Keymap
shows — and edits — the **user** keyconfig, which Blender builds by merging the addon one in.
Two undocumented facts decide what a keymap-editor rebind can do, and this measures both on real
injected keystrokes:

  1. Does dispatch follow the *edited user* item (does the new key reach our operator, and does
     the old one stop)?
  2. Does the edit propagate back to the addon item in ``_KeymapBridge.keymaps`` — i.e. can the
     bridge notice a rebind by reading its own item?

Then it measures the bridge's response, which is the part that decides what the *user* sees:
after the edit, ``sync_keymap_rebind`` must adopt the new key (moving the poller's virtual-key and
routing it through ``set_activation_key``), and a real press-and-HOLD on the new key must keep the
gesture armed for the whole hold. Without the adoption the poller still watches the old key, reads
it as up while the gesture is armed, and completes the release on the next 20 ms tick — the menu
opens and vanishes, which is exactly the "no effect" the rebind reads as.

Protocol: install the bridge on ``Z`` → tap ``Z`` (control) → rewrite the user items to ``F12`` the
way the editor would → let the scan adopt → hold ``F12`` and sample mid-hold → tap ``Z`` again.
Delivery mechanics (Raw Input, minimize→restore foreground hatch, viewport click, background input
thread) are ``gui_keypress_check.py``'s, documented there. Windows-only; **moves the real mouse +
steals foreground for ~10 s** — run only in a throwaway ``--factory-startup`` instance.

**Run it alone.** Injected keystrokes go to whatever holds the OS foreground, so any other
process that opens a window eats them and this reports a working bridge as broken — a background
test suite (uitk's runner owns a titled ``python`` window) turned it from green to 2-of-3 "the key
dispatches nothing". The pre-edit ``Z`` tap is the control for exactly that: if it records
nothing, the run measured delivery, not the bridge. ``op:`` events come from a wrapper on the
operator itself, so "never invoked" is distinguishable from "invoked and declined".
"""
import sys
import os
import time
import ctypes
import threading
from ctypes import wintypes
from pathlib import Path
from types import SimpleNamespace as NS

MONO = Path(__file__).resolve().parents[3]
for _pkg in ("pythontk", "uitk", "tentacle", "blendertk"):
    _p = str(MONO / _pkg)
    if os.path.isdir(_p) and _p not in sys.path:
        sys.path.insert(0, _p)
os.environ.setdefault("QT_API", "pyside6")

import bpy
from tentacle import tcl_blender as tb

_VK = {"F12": 0x7B, "Z": 0x5A, "ESC": 0x1B}
_KEYUP = 0x0002
_LDOWN, _LUP = 0x0002, 0x0004
_SW_MINIMIZE, _SW_RESTORE = 6, 9

_u = ctypes.windll.user32

_events = []
_result = {}


def _set_activation_key(new_key):
    """Stand in for ``TclBlender.set_activation_key`` — record, then move Blender's half."""
    _events.append(f"setkey:{new_key}")
    _stub._activation_key_str = new_key
    tb._KeymapBridge.rebind(_stub, new_key)


_stub = NS(
    _on_activation_press=lambda: _events.append("press"),
    _on_activation_release=lambda: _events.append("release"),
    _activation_key_held=False,
    _activation_key_str="Key_Z",
    isVisible=lambda: False,
    grabMouse=lambda: _events.append("grab"),
    raise_=lambda: None,
    activateWindow=lambda: None,
    set_activation_key=_set_activation_key,
)


def _ghost_hwnd():
    """Top-level GHOST window handle for THIS Blender process (None on failure)."""
    pid = os.getpid()
    found = []

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def _enum(hwnd, _lparam):
        wpid = wintypes.DWORD()
        _u.GetWindowThreadProcessId(hwnd, ctypes.byref(wpid))
        if wpid.value == pid and _u.IsWindowVisible(hwnd):
            buf = ctypes.create_unicode_buffer(64)
            _u.GetClassNameW(hwnd, buf, 64)
            if buf.value == "GHOST_WindowClass":
                found.append(hwnd)
                return False
        return True

    _u.EnumWindows(_enum, 0)
    return found[0] if found else None


def _screen_viewport_point(hwnd):
    """Screen-pixel (x, y) inside the 3D viewport region (Blender area rect → client → screen)."""
    for area in bpy.context.window.screen.areas:
        if area.type == "VIEW_3D":
            for region in area.regions:
                if region.type == "WINDOW":
                    rect = wintypes.RECT()
                    _u.GetClientRect(hwnd, ctypes.byref(rect))
                    pt = wintypes.POINT(
                        region.x + region.width // 2,
                        rect.bottom - (region.y + region.height // 2),
                    )
                    _u.ClientToScreen(hwnd, ctypes.byref(pt))
                    return pt.x, pt.y
    rect = wintypes.RECT()
    _u.GetWindowRect(hwnd, ctypes.byref(rect))
    return (rect.left + rect.right) // 2, (rect.top + rect.bottom) // 2


def _down(key):
    vk = _VK[key]
    _u.keybd_event(vk, _u.MapVirtualKeyW(vk, 0), 0, 0)


def _up(key):
    vk = _VK[key]
    _u.keybd_event(vk, _u.MapVirtualKeyW(vk, 0), _KEYUP, 0)


def _tap(key):
    _down(key)
    time.sleep(0.05)
    _up(key)


def _inject(hwnd, x, y):
    # OS calls only — no bpy off the main thread. The edit itself is done by a main-thread
    # timer; the two sides hand off through _result flags so the control tap is provably
    # BEFORE the edit and the measured taps provably after (no timing race).
    time.sleep(0.5)
    if not hwnd:
        _result["error"] = "no GHOST hwnd — cannot inject"
        _result["edit_now"] = True  # never strand the main-thread timer
        return
    _u.ShowWindow(hwnd, _SW_MINIMIZE)
    time.sleep(0.3)
    _u.ShowWindow(hwnd, _SW_RESTORE)
    _u.SetForegroundWindow(hwnd)
    time.sleep(0.5)
    _result["fg_ok"] = _u.GetForegroundWindow() == hwnd
    _u.SetCursorPos(x, y)
    time.sleep(0.2)
    _u.mouse_event(_LDOWN, 0, 0, 0, 0)  # click → focus + active region = the 3D viewport
    _u.mouse_event(_LUP, 0, 0, 0, 0)
    time.sleep(0.3)

    _tap("Z")  # control: the installed key, BEFORE any edit — proves delivery works at all
    time.sleep(1.2)
    _result["control"] = list(_events)
    _events.clear()
    _tap("ESC")
    time.sleep(0.3)

    _result["edit_now"] = True  # → main thread rewrites the user keyconfig items
    for _ in range(100):
        if _result.get("edit_done"):
            break
        time.sleep(0.05)
    # Wait for the adoption to actually land rather than guessing a delay: the scan is throttled
    # to KEY_SCAN_INTERVAL and the re-installed add-on item then has to re-merge into the user
    # keyconfig before anything dispatches. A fixed sleep straddles that window and measures an
    # empty keymap (seen: a run where the adoption completed but the hold recorded nothing).
    for _ in range(200):
        if _result.get("adopted"):
            break
        time.sleep(0.05)
    time.sleep(1.0)  # settle the re-merge
    _result["adopt"] = list(_events)
    _events.clear()

    # Press and HOLD the new key. Mid-hold there must be a press and NO release — a poller still
    # watching the old key would have completed the gesture within ~20 ms of the press.
    _down("F12")
    time.sleep(1.0)
    _result["mid_hold"] = list(_events)
    _up("F12")
    time.sleep(0.6)
    _result["after_hold"] = list(_events)
    _events.clear()
    _tap("ESC")
    time.sleep(0.3)

    _tap("Z")  # the old key must now do nothing
    time.sleep(1.2)
    _result["old_key"] = list(_events)

    _tap("ESC")  # dismiss anything a fall-through opened
    time.sleep(0.3)


def _report_and_quit():
    control = _result.get("control", [])
    mid, after = _result.get("mid_hold", []), _result.get("after_hold", [])
    old = _result.get("old_key", [])
    # The control proves DELIVERY, so it too is judged on the operator invocation: a control that
    # reached the operator but failed inside it still tells us the injected keystrokes land.
    control_ok = "op:press" in control
    print("\n===KEYMAP-EDITOR-REBIND===")
    print(f"fg_ok             = {_result.get('fg_ok')}  error={_result.get('error')}")
    print(f"user items before = {_result.get('user_before')}")
    print(f"user items after  = {_result.get('user_after')}   (the 'editor' edit)")
    print(f"addon items @edit = {_result.get('addon_at_edit')}  (what the bridge holds)")
    print(f"tap Z pre-edit    = {control}")
    print(f"adopt window      = {_result.get('adopt')}")
    print(f"addon key @end    = {_result.get('addon_key')}  active_vk={_result.get('active_vk')}")
    print(f"user items @end   = {_result.get('user_end')}")
    print(f"hold F12 mid      = {mid}")
    print(f"hold F12 after    = {after}")
    print(f"tap Z post-edit   = {old}")

    # Dispatch is about whether the KEY reached our keymap item, so judge it on the ``op:``
    # markers — the operator's own invocation. Judging it on ``press`` (the state machine the
    # handler drives) would report "the key never reached the operator" for a key that reached it
    # and then failed inside, which is the exact confusion these markers were added to remove.
    if not control_ok:
        dispatch = "INCONCLUSIVE — the control tap never reached the operator (delivery broken)"
    elif "op:press" in mid and "op:press" not in old:
        dispatch = "FOLLOWS THE EDIT — F12 reaches the operator, Z no longer does"
    elif "op:press" in mid:
        dispatch = "BOTH KEYS FIRE — the old binding still dispatches alongside the edit"
    else:
        dispatch = "EDIT NOT DISPATCHING — the new key never reached the operator"
    print("dispatch  =", dispatch)
    print(
        "bridge-visible =",
        (
            "YES — the addon item shows the new key"
            if _result.get("addon_at_edit")
            and all(t == "F12" for t, _v in _result["addon_at_edit"])
            else "NO — the addon item keeps the old key, so the bridge must read the USER keyconfig"
        ),
    )
    adopted = f"setkey:Key_F12" in _result.get("adopt", [])
    print(
        "adoption  =",
        (
            "OK — the rebind was adopted (set_activation_key + poller moved)"
            if adopted and _result.get("active_vk") == 0x7B
            else f"PARTIAL — set_activation_key={adopted}, active_vk={_result.get('active_vk')}"
            if adopted
            else "FAILED — the bridge never noticed the rebind"
        ),
    )
    # One press, still armed mid-hold, released by key-up. The release can legitimately arrive
    # twice — the RELEASE keymap item and the poller's key-up level check both complete the
    # gesture, which is pre-existing and idempotent (``drive_release`` / ``_on_activation_release``
    # only clear already-clear state). What must NOT happen is a release DURING the hold: that is
    # the signature of a poller left watching the old key, i.e. the rebind reading as "no effect".
    # Verdict on the STATE-MACHINE events only — ``op:`` markers just record that the operator was
    # invoked, and counting them here would make the trace's own instrumentation change the result.
    mid_sm = [e for e in mid if not e.startswith("op:")]
    after_sm = [e for e in after if not e.startswith("op:")]
    print(
        "hold      =",
        (
            "OK — armed for the whole hold, released on key-up"
            if mid_sm == ["press"]
            and after_sm.count("press") == 1
            and "release" in after_sm
            else "BROKEN — the gesture did not survive the hold (poller still on the old key?)"
        ),
    )
    print("===END===")
    sys.stdout.flush()
    bpy.ops.wm.quit_blender()
    return None


def _edit_when_asked():
    """Rewrite the *user* keyconfig items the way Preferences ▸ Keymap would (main thread)."""
    if not _result.get("edit_now"):
        return 0.05  # keep polling for the input thread's handshake
    items = tb._KeymapBridge.user_keymap_items()
    _result["user_before"] = [(k.type, k.value) for k in items]
    for k in items:
        k.type = "F12"
    _result["user_after"] = [(k.type, k.value) for k in items]
    _result["addon_at_edit"] = [
        (kmi.type, kmi.value) for _km, kmi in tb._KeymapBridge.keymaps
    ]
    _result["edit_done"] = True
    bpy.app.timers.register(_watch_adoption, first_interval=0.1)
    return None


def _watch_adoption():
    """Signal the input thread once BOTH keyconfigs carry the new key (main thread).

    The add-on item moving proves the bridge adopted; the user item proves Blender re-merged, so
    something is actually bound again. Injecting between the two measures an empty keymap."""
    addon_ok = tb._KeymapBridge.addon_key_type() == "F12"
    user_ok = [k for k in tb._KeymapBridge.user_keymap_items() if k.type == "F12"]
    if addon_ok and user_ok:
        _result["adopted"] = True
        return None
    return 0.1


def _snapshot_and_quit():
    _result["addon_key"] = tb._KeymapBridge.addon_key_type()
    _result["active_vk"] = tb._KeymapBridge.active_vk
    _result["user_end"] = [(k.type, k.value) for k in tb._KeymapBridge.user_keymap_items()]
    return _report_and_quit()


def _inject_start():
    hwnd = _ghost_hwnd()
    x, y = _screen_viewport_point(hwnd) if hwnd else (0, 0)
    threading.Thread(target=_inject, args=(hwnd, x, y), daemon=True).start()
    bpy.app.timers.register(_edit_when_asked, first_interval=0.1)
    bpy.app.timers.register(_snapshot_and_quit, first_interval=22.0)
    return None


def _trace_operator():
    """Record every operator invocation, so "no press" can be told apart from "never invoked".

    Without this a silent result is ambiguous: the key may not have reached our keymap item at
    all, or the item may have fired and the handler declined."""
    op = getattr(bpy.types, "TENTACLE_OT_show_marking_menu", None)
    if op is None:
        return
    original = op.execute

    def traced(self, context):
        _events.append(f"op:{self.phase}")
        return original(self, context)

    op.execute = traced


def _go():
    tb._KeymapBridge.install_keymap(_stub, "Z")  # the real product path
    _trace_operator()
    tb._KeymapBridge.install_poller(_stub, "Key_Z")  # the half that has to follow a rebind
    # One pass for Blender to merge the addon keymap into the user keyconfig before we edit it.
    bpy.app.timers.register(_inject_start, first_interval=1.5)
    return None


bpy.app.timers.register(_go, first_interval=2.0)
