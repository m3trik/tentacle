# !/usr/bin/python
# coding=utf-8
"""Shared Win32 input/window helpers for the GUI Blender harnesses in this directory.

Not a check script (no ``_check`` suffix) — import it from a harness after putting this
directory on ``sys.path`` (Blender's ``--python`` does NOT add the script's dir)::

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import _input

Centralizes the fiddly bits every injection harness needs:

* ``ghost_windows()`` / ``main_ghost_hwnd()`` — enumerate THIS process's visible GHOST windows.
* ``force_foreground(hwnd)`` — Windows denies ``SetForegroundWindow`` to background processes;
  retry across the known workarounds (restoring a just-minimized window is granted foreground;
  an ALT key-tap unlocks the call; ``AttachThreadInput`` to the current foreground thread as
  belt-and-braces). Still inherently flaky on a busy desktop — callers should record the
  foreground state at injection time (see ``fg_at_key`` in the activation harness) so a lost
  grant isn't misread as a product failure.
* ``click(x, y)`` / ``click_and_pump(app, x, y)`` — inject a real click; the latter pumps a
  Qt ``app`` on the GUI thread while the click runs off-thread (delivery to a Qt-over-Blender UI).
"""
import os
import time
import ctypes
import threading
from ctypes import wintypes

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

KEYUP = 0x0002
MOUSE_MOVE = 0x0001
BTN = {  # mouse_event down/up flag pairs
    "L": (0x0002, 0x0004),
    "M": (0x0020, 0x0040),
    "R": (0x0008, 0x0010),
}
SW_MINIMIZE, SW_RESTORE = 6, 9


def ghost_windows():
    """[(hwnd, title)] of visible GHOST windows belonging to THIS process."""
    pid = os.getpid()
    found = []

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def _enum(hwnd, _lparam):
        wpid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(wpid))
        if wpid.value == pid and user32.IsWindowVisible(hwnd):
            cls = ctypes.create_unicode_buffer(64)
            user32.GetClassNameW(hwnd, cls, 64)
            if cls.value == "GHOST_WindowClass":
                title = ctypes.create_unicode_buffer(128)
                user32.GetWindowTextW(hwnd, title, 128)
                found.append((hwnd, title.value))
        return True

    user32.EnumWindows(_enum, 0)
    return found


def main_ghost_hwnd():
    """First visible GHOST window of this process (None when there is none yet)."""
    windows = ghost_windows()
    return windows[0][0] if windows else None


def force_foreground(hwnd, allow_minimize=True):
    """Acquire OS foreground for ``hwnd`` — retries across the known workarounds.

    ``allow_minimize=False`` skips the restore-a-minimized-window grant and relies only on the
    ALT-tap unlock. Use it when ``hwnd`` *owns* visible child windows (e.g. Blender's GHOST
    window owning live tentacle tool windows): minimizing the owner hides every owned window and
    scrambles their geometry, which breaks a harness that then wants to click one of them.
    """
    for attempt in range(5):
        if user32.GetForegroundWindow() == hwnd:
            return True
        if allow_minimize and attempt % 2 == 0:  # restore-a-minimized-window grant
            user32.ShowWindow(hwnd, SW_MINIMIZE)
            time.sleep(0.25)
            user32.ShowWindow(hwnd, SW_RESTORE)
        else:  # ALT-tap unlocks SetForegroundWindow; AttachThreadInput as belt+braces
            user32.keybd_event(0x12, 0, 0, 0)  # VK_MENU down
            user32.keybd_event(0x12, 0, KEYUP, 0)
            fg = user32.GetForegroundWindow()
            fg_thread = user32.GetWindowThreadProcessId(fg, None)
            our_thread = kernel32.GetCurrentThreadId()
            user32.AttachThreadInput(our_thread, fg_thread, True)
            user32.SetForegroundWindow(hwnd)
            user32.AttachThreadInput(our_thread, fg_thread, False)
        user32.SetForegroundWindow(hwnd)
        time.sleep(0.4)
    return user32.GetForegroundWindow() == hwnd


def click(x, y, button="L", jiggle=True):
    """Inject one real click (down+up) at screen pixel ``(x, y)``.

    OS-level input only (no ``bpy``) so it is safe to call from a background thread while
    Blender's event loop keeps turning. ``jiggle`` first nudges the cursor by ±1px so a host
    that tracks hover from real motion (GHOST) refreshes its region-under-cursor before the
    click — ``SetCursorPos`` alone leaves it stale. ``button`` indexes :data:`BTN` (L/M/R).
    """
    down, up = BTN[button]
    user32.SetCursorPos(x, y)
    time.sleep(0.05)
    if jiggle:
        user32.mouse_event(MOUSE_MOVE, 1, 1, 0, 0)
        time.sleep(0.03)
        user32.mouse_event(MOUSE_MOVE, -1, -1, 0, 0)
        time.sleep(0.05)
        user32.SetCursorPos(x, y)
        time.sleep(0.05)
    user32.mouse_event(down, 0, 0, 0, 0)
    time.sleep(0.06)
    user32.mouse_event(up, 0, 0, 0, 0)


def click_and_pump(app, x, y, button="L", settle=1.5):
    """Inject one :func:`click` on a daemon thread while pumping ``app`` on the CALLING (GUI)
    thread for ``settle`` seconds — the harness idiom for delivering a real click to a
    Qt-over-Blender window whose events are drained by ``app.processEvents()``. The injection
    runs off-thread (OS-level, no bpy) so the pump keeps turning during the click. ``app`` is
    duck-typed (anything with ``processEvents``) so this module stays Qt-import-free. Must be
    called on the GUI thread."""
    threading.Thread(target=click, args=(x, y, button), daemon=True).start()
    t0 = time.time()
    while time.time() - t0 < settle:
        app.processEvents()
        time.sleep(0.01)
