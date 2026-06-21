# !/usr/bin/python
# coding=utf-8
"""Blender entry point for tentacle's Qt marking menu — host + keymap bridge + launcher in one.

Blender is not a Qt app (GHOST event loop, no bundled PySide6), so — unlike Maya, which provides
a live QApplication and whose viewport keystrokes already reach Qt — tentacle must:

  1. **Host** a QApplication itself and pump Qt events from Blender's timer loop
     (:class:`_QtHost`).
  2. **Bridge** the activation key: GHOST consumes viewport keystrokes before Qt, so
     ``MarkingMenu``'s ``QShortcut`` never fires. A 3D-View keymap operator calls ``tcl.show(...)``
     instead — wired automatically in :meth:`TclBlender.__init__` (via :class:`_KeymapBridge`), so
     instantiating ``TclBlender`` "just works" with the key, the same install model as Maya (no
     separate add-on to enable).

Everything here is encapsulated in classes — the only module-level surface is ``bl_info`` plus a
thin set of delegating functions (:func:`register` / :func:`unregister` / :func:`reload` /
:func:`launch` / :func:`diagnose` / the Qt-host helpers): Blender's add-on contract *requires*
module-scope ``register``/``unregister``/``bl_info``, and those functions are the documented console
API. They carry no logic or state — each forwards to a classmethod. The collaborators are:

  * :class:`_Config`       — env-overridable configuration (the only mutable knobs).
  * :class:`_QtBootstrap`  — path + Qt-binding provisioning (the import-time side effect).
  * :class:`_NativeWindow` — Windows native-window ownership / modal-loop / foreground helpers.
  * :class:`_QtHost`       — QApplication + ``blender_widget`` parent + event pump.
  * :class:`_KeymapBridge` — operator, 3D-View keymap, held-button poller, activation state machine.
  * :class:`TclBlender`    — the ``MarkingMenu`` subclass.
  * :class:`_ClickDebugger`— opt-in mouse-event tracer.
  * :class:`Diagnostics`   — the live-state report.
  * :class:`BlenderHost`   — the launch / add-on lifecycle coordinator.

Usage (inside a running Blender — console, startup script, or add-on)::

    from tentacle import tcl_blender
    tcl_blender.register()            # stand up the host + wire the activation key
    # ...or for a handle: tcl = tcl_blender.launch(); tcl.show("main#startmenu")

Install — exactly like the Maya version (≈ ``userSetup.py``): a module in Blender's user
``scripts/startup`` that puts the **sibling package dirs** (pythontk/uitk/tentacle/blendertk) on
``sys.path`` and then calls :func:`register` (deferred via a one-shot ``bpy.app.timers``). The path
step must cover all siblings *before* ``import tentacle`` — the package ``__init__`` imports
pythontk at the top, so this module's own :meth:`_QtBootstrap.bootstrap_paths` (and
``TENTACLE_MONOREPO``) runs too late to provide them; the bare two-line snippet above only works
once they resolve. Qt itself is handled automatically: Maya bundles PySide6 (used as-is, never
installed), and Blender's Qt-less Python gets PySide6 + qtpy **pip-installed on first launch**
(:meth:`_QtBootstrap.ensure_qt`) — point ``TENTACLE_QT_DEPS`` at a pre-staged folder to skip the
download. This file also carries ``bl_info`` + :func:`register`/:func:`unregister`, so it doubles as
an add-on / Text-Editor ▸ Run-Script target when loaded from its package location.
Env overrides: ``TENTACLE_MONOREPO``, ``TENTACLE_QT_DEPS``, ``TENTACLE_KEY`` (default ``F12`` —
see Preferences ▸ Keymap; the activation key is configurable).

See ``tentacle/docs/BLENDER_PORT_PLAN.md``.
"""
import os
import sys
import time

bl_info = {
    "name": "Tentacle Marking Menu",
    "author": "m3trik",
    "version": (0, 1, 0),
    "blender": (4, 1, 0),
    "location": "3D View ▸ activation key (default F12)",
    "description": "Qt marking menu (tentacle) for Blender — press the activation key in the 3D view.",
    "category": "Interface",
}


class _Config:
    """Env-overridable configuration (defaults target the dev box).

    Class attributes rather than module globals so every collaborator reads one source and tests /
    harnesses can flip a knob in place — e.g. ``_Config.DEBUG = True`` to log each activation fire.
    """

    MONOREPO = os.environ.get("TENTACLE_MONOREPO", r"o:\Cloud\Code\_scripts")
    QT_DEPS = os.environ.get("TENTACLE_QT_DEPS")  # optional pre-staged Qt folder (skips on-demand)
    ACTIVATION_KEY = os.environ.get("TENTACLE_KEY", "F12")
    DEBUG = False  # set True to log each activation (helps confirm the keymap is firing live)


# --------------------------------------------------------------------------------------------
# Import-time provisioning — the asymmetry between Maya and Blender.
# --------------------------------------------------------------------------------------------
# Maya (2025+) *bundles* PySide6, so qtpy resolves a binding with zero setup — and we must NEVER
# pip-install Qt into Maya (it would shadow/clash with the bundled copy). That's also why
# tentacle/uitk deliberately exclude qtpy/PySide from their pyproject ``dependencies``. Blender's
# bundled Python ships *no* Qt, so tentacle has to provide one.
class _QtBootstrap:
    """Make the monorepo packages + a Qt binding importable *before* the qtpy/uitk imports below.

    :meth:`run` is the import-time side effect that makes this file a self-contained drop-in,
    mirroring the Maya install's "monorepo on the path and you're done". It must run before the
    ``from uitk import MarkingMenu`` below — ``QT_API`` has to be set before qtpy is first imported,
    and the monorepo has to be importable for the import to resolve. A normal ``import tentacle`` has
    already satisfied these, so every guard no-ops.
    """

    @staticmethod
    def bootstrap_paths():
        """Put the monorepo packages on ``sys.path`` and pin ``QT_API`` (idempotent)."""
        os.environ.setdefault("QT_API", "pyside6")
        # ``extapps`` rides along so the in-process external-app launchers (Map Converter / Packer /
        # Compositor + the photogrammetry workflows) can ``import extapps`` in Blender's own
        # interpreter — Maya gets it from mayapy's site-packages; Blender's bundled Python has no such
        # install, and without it ``ExternalAppHandler.launch`` would try a (synchronous,
        # blender.exe-targeted) pip install and wedge the UI. A pip-installed deployment finds extapps
        # in site-packages and this path-add simply no-ops (the dir guard below).
        for pkg in ("pythontk", "uitk", "tentacle", "blendertk", "extapps"):
            path = os.path.join(_Config.MONOREPO, pkg)
            if os.path.isdir(path) and path not in sys.path:
                sys.path.insert(0, path)

    @staticmethod
    def qt_importable():
        """True if qtpy can resolve a real Qt binding (Maya's bundled PySide, or Blender's installed one)."""
        try:
            from qtpy import QtWidgets  # noqa: F401

            return True
        except Exception:
            return False

    @staticmethod
    def qt_install_dir():
        """Where Blender's on-demand Qt deps live. Prefer Blender's *own* per-version user-modules dir
        (``bpy.utils.user_resource('SCRIPTS', 'modules')``) — Blender creates it and already has it on
        ``sys.path`` in a normal launch, so once installed Qt imports with no further wiring, and it's a
        folder the user can see/clear in their Blender profile. Falls back to a non-roaming managed dir
        when bpy isn't importable (the install itself is bpy-gated, so that branch is just the reuse-scan)."""
        try:
            import bpy

            return bpy.utils.user_resource("SCRIPTS", path="modules", create=True)
        except Exception:
            base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
            return os.path.join(base, "tentacle", "qt_deps", f"py{sys.version_info[0]}{sys.version_info[1]}")

    @staticmethod
    def blender_python_exe():
        """Blender's bundled Python interpreter (``sys.executable`` is the Blender binary, not python)."""
        for name in ("python.exe", "python3.exe", "python", "python3"):
            exe = os.path.join(sys.prefix, "bin", name)
            if os.path.isfile(exe):
                return exe
        return sys.executable

    @classmethod
    def ensure_qt(cls):
        """Make a Qt binding importable; no-op under Maya, on-demand pip-install under Blender.

        ``ensure_qt`` adds a pre-staged folder if you point ``TENTACLE_QT_DEPS`` at one, otherwise
        pip-installs PySide6 + qtpy into Blender's *own* user-modules dir **on first launch** (the
        on-demand install) — gated on actually running inside Blender so a bare interpreter never gets
        an unsolicited download.
        """
        if cls.qt_importable():  # Maya (bundled) and any already-provisioned interpreter stop here.
            return
        install_dir = cls.qt_install_dir()
        for target in (_Config.QT_DEPS, install_dir):  # reuse a pre-staged / previously-installed dir
            if target and os.path.isdir(target) and target not in sys.path:
                sys.path.insert(0, target)
        if cls.qt_importable():
            return
        try:
            import bpy  # noqa: F401 — only auto-install inside Blender, never a bare interpreter
        except Exception:
            return
        if not install_dir:  # user_resource can return "" if the path can't be resolved/created
            return
        import subprocess

        py = cls.blender_python_exe()
        print(f"tentacle: Blender has no Qt — installing PySide6 + qtpy into {install_dir} (first launch only)…")
        try:
            os.makedirs(install_dir, exist_ok=True)
            subprocess.run([py, "-m", "ensurepip", "--upgrade"], check=False)
            subprocess.check_call(
                [py, "-m", "pip", "install", "--target", install_dir, "PySide6", "qtpy"]
            )
        except Exception as error:
            print(
                f"tentacle: on-demand Qt install failed ({error}). Set TENTACLE_QT_DEPS to a folder "
                "holding PySide6 + qtpy, or pip-install them into Blender's Python."
            )
            return
        if install_dir not in sys.path:
            sys.path.insert(0, install_dir)

    @classmethod
    def run(cls):
        """Provision paths + Qt — the import-time side effect that makes this file a drop-in."""
        cls.bootstrap_paths()
        cls.ensure_qt()


_QtBootstrap.run()

from qtpy import QtWidgets, QtCore  # noqa: E402  (deferred until paths/Qt are provisioned above)
from uitk import MarkingMenu  # noqa: E402
from uitk.handlers.external_app_handler import ExternalAppHandler  # noqa: E402
from blendertk.ui_utils.blender_ui_handler import BlenderUiHandler  # noqa: E402


class _NativeWindow:
    """Windows native-window helpers (ctypes) that keep tentacle's top-level Qt windows tied to
    Blender's foreign GHOST window.

    Blender isn't a Qt app, so a top-level Qt window is otherwise an unrelated OS window: it falls
    behind Blender on focus loss and doesn't move/minimize with it. These helpers enumerate Blender's
    GHOST window, set the OS *owner* relationship directly (Qt won't, for a foreign transient parent),
    detect native modal loops the Qt pump must stay out of, and hand focus back to Blender. All state
    caches on the QApplication (the per-process singleton), so there are no module globals; off-Windows
    every method degrades to a safe no-op.
    """

    # Windows owner index: setting it on a top-level window makes that window *owned* by another — the
    # OS then keeps it stacked above the owner and hides/closes it with the owner. GWLP_HWNDPARENT = -8.
    _GWLP_HWNDPARENT = -8
    # GetGUIThreadInfo flags for native modal loops on this thread: size/move (title-bar drag) and the
    # native menu modes. GUI_INMOVESIZE=0x2, GUI_INMENUMODE=0x4, GUI_SYSTEMMENUMODE=0x8, GUI_POPUPMENUMODE=0x10.
    _NATIVE_MODAL_FLAGS = 0x2 | 0x4 | 0x8 | 0x10
    _modal_probe = None  # lazily built GetGUIThreadInfo probe (Windows only)

    @classmethod
    def native_modal_loop_active(cls):
        """True while THIS thread is inside a native modal size/move or menu loop — e.g. the user
        is dragging a Blender window by its title bar. Blender's timers still fire inside that
        loop (WM_TIMER), but pumping Qt from there is destructive: Qt's dispatcher PeekMessages
        the *whole thread queue*, stealing the loop's WM_MOUSEMOVE/WM_LBUTTONUP — the window can't
        be repositioned and the loop never sees the mouse-up (Blender wedges; reproduced by
        ``test/blender/native_drag_check.py``). The pump and the key watcher skip their tick
        while this is true."""
        if sys.platform != "win32":
            return False
        if cls._modal_probe is None:
            import ctypes
            from ctypes import wintypes

            class _GUITHREADINFO(ctypes.Structure):
                _fields_ = [
                    ("cbSize", wintypes.DWORD),
                    ("flags", wintypes.DWORD),
                    ("hwndActive", wintypes.HWND),
                    ("hwndFocus", wintypes.HWND),
                    ("hwndCapture", wintypes.HWND),
                    ("hwndMenuOwner", wintypes.HWND),
                    ("hwndMoveSize", wintypes.HWND),
                    ("hwndCaret", wintypes.HWND),
                    ("rcCaret", wintypes.RECT),
                ]

            user32 = ctypes.windll.user32
            kernel32 = ctypes.windll.kernel32
            info = _GUITHREADINFO()
            info.cbSize = ctypes.sizeof(_GUITHREADINFO)

            def probe():
                if user32.GetGUIThreadInfo(kernel32.GetCurrentThreadId(), ctypes.byref(info)):
                    return bool(info.flags & cls._NATIVE_MODAL_FLAGS)
                return False

            cls._modal_probe = probe
        try:
            return cls._modal_probe()
        except Exception:
            return False

    @staticmethod
    def blender_window():
        """Blender's main GHOST window wrapped as a foreign ``QWindow`` (cached on the QApplication).

        Used as the marking menu's *transient parent* so the OS keeps the overlay stacked above
        Blender natively (an owned window on Windows) instead of relying solely on raise_().
        Light-touch on purpose — no bqt-style ``createWindowContainer`` reparenting, which would
        take ownership of the GHOST window. Returns ``None`` off-Windows or on any failure
        (top-level behavior then continues to work as before).
        """
        app = QtWidgets.QApplication.instance()
        cached = getattr(app, "_blender_native_window", None) if app else None
        if cached is not None:
            try:
                import ctypes

                # Re-enumerate if the cached handle went stale (GHOST window re-created).
                if ctypes.windll.user32.IsWindow(getattr(app, "_blender_native_hwnd", 0)):
                    return cached
            except Exception:
                return cached
        if sys.platform != "win32":
            return None
        try:
            import ctypes
            from ctypes import wintypes
            from qtpy import QtGui

            user32 = ctypes.windll.user32
            pid = os.getpid()
            found = []

            @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
            def _enum(hwnd, _lparam):
                wpid = wintypes.DWORD()
                user32.GetWindowThreadProcessId(hwnd, ctypes.byref(wpid))
                if wpid.value == pid and user32.IsWindowVisible(hwnd):
                    buf = ctypes.create_unicode_buffer(64)
                    user32.GetClassNameW(hwnd, buf, 64)
                    if buf.value == "GHOST_WindowClass":
                        found.append(hwnd)
                        return False  # stop enumeration
                return True

            user32.EnumWindows(_enum, 0)
            if not found:
                return None
            window = QtGui.QWindow.fromWinId(int(found[0]))
            if app is not None:
                app._blender_native_window = window
                app._blender_native_hwnd = int(found[0])
            return window
        except Exception:
            return None

    @classmethod
    def set_owner(cls, widget, owner_hwnd):
        """Set ``widget``'s Windows *owner* to ``owner_hwnd`` (``GWLP_HWNDPARENT``); return the
        resulting owner handle, or ``None`` off-Windows / on failure.

        This is the reliable way to keep a top-level Qt window above a *foreign* (non-Qt) window:
        Qt's ``setTransientParent`` does **not** set ``GWLP_HWNDPARENT`` when the transient parent is
        a foreign ``QWindow`` (verified on PySide6 6.10 — the OS owner stays unset whether set before
        or after ``show()``), so the window is unowned and falls behind Blender the moment it loses
        focus. Setting the owner directly fixes it: owned windows always stack above their owner and
        minimize/close with it (the Maya-parity behavior). Idempotent — re-setting the same owner is a
        cheap no-op, so it can be re-asserted on every show (Qt re-creating a native window on a flag
        change silently drops the owner)."""
        if sys.platform != "win32" or widget is None or not owner_hwnd:
            return None
        try:
            import ctypes

            user32 = ctypes.windll.user32
            if not user32.IsWindow(ctypes.c_void_p(int(owner_hwnd))):  # c_void_p: don't truncate the handle
                return None
            # Force native restypes so the 64-bit handle isn't truncated to a 32-bit c_int.
            user32.SetWindowLongPtrW.restype = ctypes.c_void_p
            user32.SetWindowLongPtrW.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p]
            user32.GetWindowLongPtrW.restype = ctypes.c_void_p
            user32.GetWindowLongPtrW.argtypes = [ctypes.c_void_p, ctypes.c_int]
            hwnd = ctypes.c_void_p(int(widget.winId()))  # forces native-window creation
            user32.SetWindowLongPtrW(hwnd, cls._GWLP_HWNDPARENT, ctypes.c_void_p(int(owner_hwnd)))
            return user32.GetWindowLongPtrW(hwnd, cls._GWLP_HWNDPARENT)
        except Exception:
            return None

    @staticmethod
    def restore_foreground(active_tcl):
        """Give Blender's GHOST window OS focus back unless a visible tentacle window holds it
        (a pinned tool window the user is typing in keeps focus — Maya parity). ``active_tcl`` is the
        live menu, excluded from the "some other tentacle window is active" check."""
        if sys.platform != "win32":
            return
        try:
            app = QtWidgets.QApplication.instance()
            active = app.activeWindow() if app else None
            if active is not None and active is not active_tcl and active.isVisible():
                return
            import ctypes

            hwnd = getattr(app, "_blender_native_hwnd", 0)
            if hwnd and ctypes.windll.user32.IsWindow(hwnd):
                ctypes.windll.user32.SetForegroundWindow(hwnd)
        except Exception:
            pass


class _QtHost:
    """Qt host — Blender has no QApplication of its own, so stand one up and pump it from the timer
    loop. :meth:`BlenderHost.launch` wires these together; idempotent so re-launching reuses the live
    host. State that must survive a reload caches on the QApplication; ``_pump_registered`` resets
    with the module so a reloaded module registers a fresh pump (the old one retires via its
    generation token)."""

    _pump_registered = False

    @staticmethod
    def ensure_qapp():
        """Return the process QApplication, creating one if Blender has none."""
        app = QtWidgets.QApplication.instance()
        if app is None:
            app = QtWidgets.QApplication(sys.argv or ["blender"])
        return app

    @staticmethod
    def ensure_widget(app):
        """Establish ``app.blender_widget`` — the parent for the marking menu.

        A hidden top-level ``QWidget`` (top-level Qt windows over Blender work — Phase 0).
        Native z-order against Blender's own window is handled separately by transient-parenting
        the menu to the GHOST window (:meth:`_NativeWindow.blender_window`), not by this widget.
        """
        if getattr(app, "blender_widget", None) is None:
            widget = QtWidgets.QWidget()
            widget.setObjectName("BlenderWindow")
            app.blender_widget = widget
        return app.blender_widget

    @classmethod
    def start_pump(cls, app, interval=0.01):
        """Pump Qt events from Blender's timer loop so the Qt UI stays responsive (idempotent).

        The pump carries a generation token on the QApplication: after :meth:`BlenderHost.reload` the
        module is re-executed (resetting ``_pump_registered``), so the reloaded module registers a
        fresh pump and stamps a new token — the superseded pump sees the mismatch on its next tick and
        unregisters itself (no double-pumping, no stale-closure leak).
        """
        import bpy

        if cls._pump_registered:
            return
        token = object()
        app._tentacle_pump_token = token

        def _pump():
            if getattr(app, "_tentacle_pump_token", None) is not token:
                return None  # superseded by a reloaded module's pump — unregister
            # Never pump Qt inside a native modal size/move loop (window drag) — see
            # _NativeWindow.native_modal_loop_active. Qt pauses for the drag's duration; nothing is lost.
            if not _NativeWindow.native_modal_loop_active():
                app.processEvents()
            return interval

        # persistent — non-persistent timers are dropped on File ▸ New/Open, which would
        # silently freeze the Qt UI for the rest of the session.
        bpy.app.timers.register(_pump, persistent=True)
        cls._pump_registered = True


class _KeymapBridge:
    """Bridge the activation key from Blender's keymap to the Qt marking menu — the half Maya needs none of.

    Maya is a Qt app, so MarkingMenu's ``QShortcut`` (ApplicationShortcut context) catches the
    activation key from anywhere — TclMaya adds nothing. Blender's GHOST owns the keyboard, so that
    shortcut never sees viewport keystrokes. This registers one Blender operator + a **3D-View**
    keymap item that calls ``tcl.show(...)``, restoring the "instantiate and the key works" behavior —
    automatically, on construction, with no separate add-on to enable. Scoped to the viewport on
    purpose: a 3D-View region keymap item is evaluated before the global ``Screen`` keymap, so it takes
    the key when the viewport has focus *without* us disabling anyone's global shortcut (F12 still
    renders everywhere else). ``import bpy`` is deferred so importing this module never needs Blender.

    One per Blender process: the live menu (:attr:`tcl`), the keymap items (:attr:`keymaps`), the
    held-button poller (:attr:`poller`) and the in-flight gesture flag (:attr:`gesture_active`) are
    class state, so the registered Blender operator and the poller timer reach them through the class.
    They reset when the module is re-executed on reload (matching the old module globals' semantics).
    """

    tcl = None  # the live TclBlender the operator drives (one Qt host per Blender process)
    keymaps = []  # (keymap, keymap_item) pairs we added, for clean removal
    poller = None  # live poll callback (held-button activation fallback), for clean removal
    gesture_active = False  # a bridge-initiated press is awaiting its key-up (≈ GlobalShortcut pairing)
    chord_active = False  # the live gesture is a button-held chord (the grab path) — drives hover pump

    # Qt key-name → Blender keymap ``type`` enum. Most keys line up after stripping ``Key_`` and
    # upper-casing (``F12``→``F12``, ``A``→``A``, ``SPACE``→``SPACE``); these are the ones that don't —
    # notably the Windows/Cmd/Super key, which Qt calls ``Meta``/``Super_L`` and Blender calls ``OSKEY``.
    _BLENDER_KEY_ALIASES = {
        "META": "OSKEY", "SUPER_L": "OSKEY", "SUPER_R": "OSKEY",
        "ESCAPE": "ESC", "RETURN": "RET", "ENTER": "RET",
        "CONTROL": "LEFT_CTRL", "ALT": "LEFT_ALT", "SHIFT": "LEFT_SHIFT",
        "PAGEUP": "PAGE_UP", "PAGEDOWN": "PAGE_DOWN", "DELETE": "DEL",
    }

    # Windows virtual-key → Qt button for the held-button poller (VK order: L=0x01, R=0x02, M=0x04).
    _POLL_VK_BUTTONS = (
        (0x01, "LeftButton"),
        (0x02, "RightButton"),
        (0x04, "MiddleButton"),
    )

    # --- key translation --------------------------------------------------------------------
    @classmethod
    def qt_key_to_blender_type(cls, key_show):
        """Translate a Qt key name (``'Key_F12'`` / ``'Key_Meta'``) to a Blender keymap ``type``
        (``'F12'`` / ``'OSKEY'``). Falls back to the stripped-upper name for keys that already match."""
        name = (key_show or "").replace("Key_", "").upper()
        return cls._BLENDER_KEY_ALIASES.get(name, name)

    @staticmethod
    def _is_bare_press(kmi):
        """True if ``kmi`` is an unmodified PRESS chord (no Ctrl/Alt/Shift/OS/any) — the kind that
        collides with a bare activation key. A modified combo like ``Ctrl+F12`` does not."""
        return kmi.value == "PRESS" and not (
            kmi.any or kmi.ctrl or kmi.alt or kmi.shift or kmi.oskey
        )

    @staticmethod
    def _vk_for_key(key_show):
        """Windows virtual-key code for a Qt key name (``'Key_F12'`` → ``0x7B``); None if unmapped
        (the poller is then simply skipped — the keymap bridge still covers the no-button path)."""
        name = (key_show or "").replace("Key_", "")
        if len(name) > 1 and name[0].upper() == "F" and name[1:].isdigit() and 1 <= int(name[1:]) <= 24:
            return 0x70 + int(name[1:]) - 1  # VK_F1..VK_F24
        if len(name) == 1:
            import ctypes

            # VkKeyScanW returns a SHORT — force the restype so the -1 failure check is
            # reliable (ctypes' default c_int leaves the upper bits undefined).
            ctypes.windll.user32.VkKeyScanW.restype = ctypes.c_short
            code = ctypes.windll.user32.VkKeyScanW(ord(name.upper()))
            return code & 0xFF if code != -1 else None
        return None

    @classmethod
    def physical_mouse_buttons(cls):
        """Qt mouse-button mask read from the OS (``GetAsyncKeyState``), or ``NoButton``.

        GHOST owns the mouse, so Qt's own ``QApplication.mouseButtons()`` can't see a
        button held over the viewport. This reads the physical state directly — the one
        signal that's always true (same source as the held-button poller). Windows-only;
        ``NoButton`` elsewhere (the caller then falls back to Qt). Shared by the poller's
        chord detection and the menu's ``MouseTracking`` buttons-provider so the marking
        menu's ``visible_on_mouse_over`` Regions reveal during a grabbed chord gesture.
        """
        if sys.platform != "win32":
            return QtCore.Qt.NoButton
        import ctypes

        user32 = ctypes.windll.user32
        held = QtCore.Qt.NoButton
        for button_vk, name in cls._POLL_VK_BUTTONS:
            if user32.GetAsyncKeyState(button_vk) & 0x8000:
                held |= getattr(QtCore.Qt, name)
        return held

    # --- operator ---------------------------------------------------------------------------
    @classmethod
    def ensure_operator(cls):
        """Register the bridge operator once per process (idempotent)."""
        import bpy

        if hasattr(bpy.types, "TENTACLE_OT_show_marking_menu"):
            return

        class TENTACLE_OT_show_marking_menu(bpy.types.Operator):
            """Bridge a Blender key event to the tentacle Qt marking menu.

            GHOST owns the keyboard, so the menu's own Qt shortcut never fires from the viewport — this
            operator stands in for it, driving the SAME interaction state machine Maya's Qt
            ``GlobalShortcut`` does: ``_KeymapBridge.drive_press`` on key-down (arms the gesture +
            ``_activation_key_held``, shows + syncs the menu) and ``_KeymapBridge.drive_release`` on
            key-up (completes/hides, releases the grab). Two keymap items (PRESS + RELEASE) set ``phase``.
            The old bridge called ``show()`` directly — it painted the overlay but never armed it, so the
            menu was "stuck at the launch screen" (no grab → child buttons swallowed the click → no nav)."""

            bl_idname = "tentacle.show_marking_menu"
            bl_label = "Tentacle Marking Menu"
            # "press" (key-down) or "release" (key-up). The F821 suppression is a
            # pyflakes false positive: it misreads the string default inside the
            # bpy.props annotation as a forward-reference type name.
            phase: bpy.props.StringProperty(default="press")  # noqa: F821

            def execute(self, context):
                # Key-up: complete/hide the gesture and release the mouse grab.
                if self.phase == "release":
                    if _KeymapBridge.tcl is None:
                        return {"CANCELLED"}  # inactive → consume nothing (symmetry with the press branch)
                    try:
                        _KeymapBridge.drive_release()
                    except Exception as error:
                        self.report({"ERROR"}, f"Tentacle: {error}")
                        if _Config.DEBUG:
                            print(f"tentacle: release failed → {error!r}")
                    return {"FINISHED"}

                # Key-down, no live menu → let the key do its normal thing (CANCELLED passes F12 through
                # to render). report() — not print() — is what's visible from a keymap-invoked operator
                # (print goes to the hidden system console, never the Python Console panel).
                if _KeymapBridge.tcl is None:
                    if _Config.DEBUG:
                        self.report({"WARNING"}, "Tentacle: key fired but no live menu → render")
                    return {"CANCELLED"}
                if _Config.DEBUG:
                    self.report({"INFO"}, "Tentacle: key fired → marking menu")
                try:
                    _KeymapBridge.drive_press()
                except Exception as error:  # surface in the status bar, never crash Blender
                    self.report({"ERROR"}, f"Tentacle: {error}")
                    if _Config.DEBUG:
                        print(f"tentacle: activation press failed → {error!r}")
                # ALWAYS consume the key-down once tentacle is active so it never falls through to render.
                return {"FINISHED"}

        bpy.utils.register_class(TENTACLE_OT_show_marking_menu)

    # --- activation state machine -----------------------------------------------------------
    @classmethod
    def drive_press(cls, buttons=None):
        """Drive the menu's real activation state machine (arms ``_activation_key_held``, shows +
        syncs the menu) — the entry point Maya's Qt shortcut calls — then nudge the overlay to the
        front (GHOST keeps OS focus). Released by :meth:`drive_release` (key-up) or by the menu
        itself after an action.

        Crucially this does **not** grab the mouse for the plain key-hold (no-button) path — it
        mirrors Maya, where the shared ``MarkingMenu`` grabs *only* when a button is already held
        (the chord gesture, via ``_transfer_mouse_control``, reached through
        ``_on_activation_press(buttons=...)``). An explicit ``grabMouse()`` on the always-visible
        overlay was the cause of "Blender menu buttons need several clicks": a Qt mouse grab
        suppresses the child enter/leave events hover-navigation relies on (``child_enterEvent`` never
        fires → submenus don't open on hover) **and** funnels every click into ``MarkingMenu``'s own
        ``mousePressEvent``, which re-resolves it as the ``F12|LeftButton`` chord (jumping the menu to
        ``cameras#startmenu``) instead of letting the click reach the button. Without the grab, hover
        opens submenus and a leaf click reaches the leaf — exactly Maya's behavior (proven by
        ``test/blender/hover_nav_check.py`` and the deterministic ``grab_policy_check.py``). The chord
        gesture keeps its grab because the button-held branch still routes through
        ``_transfer_mouse_control``.

        Shared by the keymap operator (no-button path — GHOST never dispatches the key while a
        button is held) and the held-button key poller, which passes the physically-held button
        mask so the ``F12|LeftButton``-style chord bindings resolve."""
        cls.gesture_active = True  # pair every press with a guaranteed release on physical key-up
        # A button held at activation is a chord (the grab path). Record it so the poller pumps
        # MouseTracking during the gesture — GHOST doesn't deliver MouseMove to the grabbed Qt
        # overlay, so the menu's own event-driven hover tracking never fires (see install_poller).
        cls.chord_active = buttons is not None and buttons != QtCore.Qt.NoButton
        if buttons is None:
            # bare call keeps the keymap path working against uitk builds (and harness stubs)
            # that predate the `buttons` kwarg — only the poller's chord path needs it.
            cls.tcl._on_activation_press()
        else:
            # Button held at activation → the shared state machine grabs the mouse itself
            # (_transfer_mouse_control) for the chord gesture, same as Maya. No grab here.
            cls.tcl._on_activation_press(buttons=buttons)
        for nudge in ("raise_", "activateWindow"):
            try:
                getattr(cls.tcl, nudge)()
            except Exception:
                pass

    @classmethod
    def drive_release(cls):
        """Complete the gesture — the single release path for every Blender-side trigger (keymap
        RELEASE item, Qt ``keyReleaseEvent``, key-watcher edge/stuck checks). Mirrors Maya's
        ``GlobalShortcut.released``, which fires application-wide on key-up no matter which window
        has focus: ``_on_activation_release`` must run even when ``_show_window`` already cleared
        ``_activation_key_held`` (opening a standalone window mid-gesture does that, see uitk
        ``_show_window``) — it's what clears ``_standalone_suppress`` (otherwise every subsequent
        press is silently ignored) and what runs ``request_hide`` on unpinned standalone windows
        at key-up. Afterwards hand OS focus back to Blender unless a tentacle window kept it —
        otherwise the foreground is left on a hidden window and the next key press reaches neither
        Blender's keymap nor Qt until the user clicks the viewport."""
        cls.gesture_active = False
        cls.chord_active = False
        if cls.tcl is None:
            return
        try:
            cls.tcl._on_activation_release()
        finally:
            _NativeWindow.restore_foreground(cls.tcl)

    # --- keymap install / uninstall ---------------------------------------------------------
    @classmethod
    def uninstall_keymap(cls):
        """Remove the keymap items added by :meth:`install_keymap`."""
        for km, kmi in cls.keymaps:
            try:
                km.keymap_items.remove(kmi)
            except Exception:
                pass
        cls.keymaps.clear()

    @classmethod
    def install_keymap(cls, tcl, key_type):
        """Bind ``key_type`` in Blender's **3D View** keymap to the bridge operator — a PRESS item and a
        RELEASE item — so holding the key over the viewport opens the marking menu and releasing it
        completes/hides, the same press/hold/release gesture as Maya (driven through the operator since
        GHOST consumes the key before Qt). Records ``tcl`` as the live menu the operator drives.

        Scoped to the viewport on purpose: a 3D-View region keymap item is evaluated before the global
        ``Screen`` keymap, so it takes the key over the viewport and naturally wins over ``render.render``
        — *without* us disabling anyone's global F12 (it still renders everywhere else). No muting needed.
        """
        import bpy

        cls.tcl = tcl
        cls.ensure_operator()
        cls.uninstall_keymap()  # re-launch safe
        kc = bpy.context.window_manager.keyconfigs.addon
        if not (kc and key_type):
            return
        km = kc.keymaps.new(name="3D View", space_type="VIEW_3D")
        for value, phase in (("PRESS", "press"), ("RELEASE", "release")):
            kmi = km.keymap_items.new("tentacle.show_marking_menu", type=key_type, value=value)
            kmi.properties.phase = phase
            cls.keymaps.append((km, kmi))

    # --- held-button poller -----------------------------------------------------------------
    @classmethod
    def install_poller(cls, tcl, key_show):
        """Global activation-key watcher (Windows-only, idempotent) — the focus-independent half
        of the bridge. Qt only receives the key when a Qt window has OS focus, and Blender's
        keymap only when GHOST has it *and* dispatch isn't eaten, so neither side alone can track
        the key through a real gesture; ``GetAsyncKeyState`` reads the physical key state and is
        the one signal that is always true. Two duties, polled on the pump cadence:

        **Press (edge, held-button case only).** Measured (held-button probe, 2026-06-12): with ANY
        mouse button physically held, GHOST dispatches the activation key to NOTHING — not our
        3D-View item, not Screen render; the pending click/drag, modal op, or popup consumes it. So
        the keymap bridge alone can never serve Maya's "hold a button, then the key" chords, and a
        mistaken button press before the key killed activation entirely. On the key's down-edge
        with a button held (the keymap operator owns the no-button path; ``_activation_key_held``
        dedups any overlap), drive the same press path with the OS-read button mask —
        ``QApplication.mouseButtons()`` is blind to GHOST's mouse state. Nothing competes for the
        key here (the measured eaten-by-Blender state means no render fires alongside).

        **Release (level — the watchdog).** The gesture must end when the key is physically up,
        but every event-driven release path is conditional: Qt's ``keyReleaseEvent`` needs the
        overlay to have won the focus tussle, and the RELEASE keymap item is region-scoped (cursor
        must still hover the viewport). Miss both and the menu stays open with the mouse grab
        eating every click. A *half-failed* press is worse: ``_on_activation_press``'s error
        handler resets ``_activation_key_held`` but doesn't un-show/un-grab, leaving a stuck
        overlay no flag-gated path will ever release. So: whenever the key is physically up and
        the gesture is still armed (``_activation_key_held``) **or** the overlay is visible while
        holding the mouse grab (the half-failed-press signature; the grab gate keeps programmatic
        ``show()`` — harnesses, tools — untouched), complete the release. ``drive_release``
        is idempotent and hiding auto-releases the Qt grab."""
        if sys.platform != "win32":
            return
        vk = cls._vk_for_key(key_show)
        if vk is None:
            return
        import bpy
        import ctypes
        from ctypes import wintypes

        cls.uninstall_poller()
        user32 = ctypes.windll.user32
        state = {"down": False}

        def _poll():
            try:
                if _NativeWindow.native_modal_loop_active():  # never act inside a native size/move loop
                    return 0.02
                # Pump the menu's hover tracking during a chord. GHOST owns the mouse and doesn't
                # deliver MouseMove to the grabbed Qt overlay, so MouseTracking's event-driven
                # track() never fires — without this the menu's `visible_on_mouse_over` Regions
                # (cameras/editors upper+lower) never reveal their nav buttons and hover-nav into a
                # submenu never happens. track() reads the live cursor + grab state directly, so
                # driving it on the timer reproduces what mouse-move would do under Maya's Qt host.
                if cls.chord_active and cls.tcl is tcl and tcl.isVisible():
                    try:
                        tcl.mouse_tracking.update_child_widgets()  # follow submenu transitions
                        tcl.mouse_tracking.track()
                    except Exception:
                        pass
                down = bool(user32.GetAsyncKeyState(vk) & 0x8000)
                if down and not state["down"]:
                    held = cls.physical_mouse_buttons()
                    pid = wintypes.DWORD()
                    user32.GetWindowThreadProcessId(
                        user32.GetForegroundWindow(), ctypes.byref(pid)
                    )
                    if (
                        held != QtCore.Qt.NoButton
                        and cls.tcl is tcl
                        and not tcl._activation_key_held
                        and pid.value == os.getpid()  # any of our windows foreground (Maya-parity)
                    ):
                        try:
                            cls.drive_press(buttons=held)
                        except Exception as error:
                            # Always audible (system console) — a silent failure here reads as
                            # "the menu just doesn't work"; then tear down any half-armed state.
                            print(f"tentacle: held-button activation failed → {error!r}")
                            try:
                                cls.drive_release()
                            except Exception:
                                pass
                elif not down:
                    # Key physically up → the gesture must end (GlobalShortcut pairing):
                    # gesture_active covers presses whose flags were since cleared (opening a
                    # standalone window does — see drive_release); the stuck checks
                    # cover armed/half-failed states reached without the bridge.
                    stuck = tcl._activation_key_held or (
                        tcl.isVisible() and QtWidgets.QWidget.mouseGrabber() is tcl
                    )
                    if (cls.gesture_active or stuck) and cls.tcl is tcl:
                        try:
                            cls.drive_release()
                        except Exception:
                            pass
                state["down"] = down
            except Exception as error:
                # Swallow: a raising bpy timer is auto-unregistered, and a dead watchdog means
                # permanently stuck menus. Still audible in debug so plumbing bugs surface.
                if _Config.DEBUG:
                    print(f"tentacle: key-watcher tick failed → {error!r}")
            return 0.02

        bpy.app.timers.register(_poll, persistent=True)  # persistent: survive File ▸ New/Open
        cls.poller = _poll

    @classmethod
    def uninstall_poller(cls):
        """Remove the held-button poll timer (idempotent)."""
        if cls.poller is None:
            return
        import bpy

        try:
            bpy.app.timers.unregister(cls.poller)
        except Exception:
            pass
        cls.poller = None

    @classmethod
    def teardown(cls):
        """Remove the keymap items and unregister the bridge operator (for add-on unregister)."""
        import bpy

        cls.tcl = None  # the next launch() builds a fresh instance (with a fresh keymap)
        cls.gesture_active = False
        cls.uninstall_poller()
        cls.uninstall_keymap()
        op = getattr(bpy.types, "TENTACLE_OT_show_marking_menu", None)
        if op is not None:
            try:
                bpy.utils.unregister_class(op)
            except Exception:
                pass


# --------------------------------------------------------------------------------------------
class TclBlender(MarkingMenu):
    """Marking Menu class overridden for use with Blender.

    Blender is not a Qt app (GHOST loop, no bundled PySide6), so — unlike Maya — the
    QApplication, the Qt event pump, and the ``blender_widget`` parent are stood up by
    :meth:`BlenderHost.launch` (the Phase-0-proven recipe) *before* this is constructed.
    See ``tentacle/docs/BLENDER_PORT_PLAN.md``.
    """

    def __init__(
        self, parent=None, slot_source="slots/blender", log_level="WARNING", **kwargs
    ):
        if not parent:
            try:
                parent = self.get_main_window()
            except Exception as error:
                print(f"{__file__}: {error}")

        key_show = kwargs.pop("key_show", "F12")
        key_show = f"Key_{key_show}" if not key_show.startswith("Key_") else key_show

        # Activation key + default UI per chord (mirrors tcl_maya). Global activation
        # ultimately comes from the Blender keymap operator below (GHOST consumes keys
        # before Qt); these also define what show() displays by default.
        bindings = kwargs.pop("bindings", None) or {
            key_show: "hud#startmenu",  # Maya-parity default (hud ported 2026-06-12)
            f"{key_show}|LeftButton": "cameras#startmenu",
            f"{key_show}|MiddleButton": "editors#startmenu",
            f"{key_show}|RightButton": "main#startmenu",
            # Both-button chord → Blender's native menu sets (Maya parity: there it's
            # `maya#startmenu`). Resolved by the held-button poller, which ORs L+R into the
            # chord mask. Where Maya wraps its Qt menus, Blender pops its OWN native menus.
            f"{key_show}|LeftButton|RightButton": "blender#startmenu",
        }

        super().__init__(
            parent,
            ui_source=("ui", "ui/blender_menus"),
            slot_source=slot_source,
            bindings=bindings,
            # BlenderUiHandler scans the blendertk package recursively, so tools that ship
            # their own co-located ``.ui`` + ``<Tool>Slots`` (curtain, mirror, cut_on_axis,
            # duplicate_*, hdr_manager, reference_manager) are discovered and served by
            # ``marking_menu.show("<tool>")`` — exactly the mayatk/MayaUiHandler split, so the
            # Blender tool panels live in blendertk (next to their engine) rather than here.
            handlers={"ui": BlenderUiHandler, "external_app": ExternalAppHandler},
            log_level=log_level,
            suppress_default_on_reentry=True,
            context_tags={"blender"},  # `requires` widget filtering (Phase-5 visibility)
            **kwargs,
        )

        # External apps — the same standalone ``extapps`` panels Maya registers (tcl_maya).
        # They are DCC-agnostic Switchboard tools (image map utils + photogrammetry workflows),
        # so the Blender materials slot can launch them verbatim via ``external_app.launch``.
        # Auto-discovery (entry_points) + manual fallback with ``install_spec`` mirror tcl_maya;
        # ``module`` is spelled out per app (some live in the ``extapps.photogrammetry`` subpackage).
        for _name, _module, _entry in (
            ("compositor", "extapps.texture_maps.compositor", "CompositorUI"),
            ("metashape_workflow", "extapps.photogrammetry.metashape_workflow", "MetashapeWorkflowUI"),
            ("realityscan_workflow", "extapps.photogrammetry.realityscan_workflow", "RealityScanWorkflowUI"),
            ("gaussian_splat_workflow", "extapps.photogrammetry.gaussian_splat_workflow", "GaussianSplatWorkflowUI"),
            ("converter", "extapps.texture_maps.converter", "ConverterUI"),
            ("packer", "extapps.texture_maps.packer", "PackerUI"),
            ("mesh_convert", "extapps.mesh_convert", "MeshConvertUI"),
            # The Substance / Marmoset *bridges* reuse these DCC-agnostic extapps workflows: the
            # materials slot exports the Blender selection to FBX and launches the workflow with the
            # mesh pre-filled (the "Reuse extapps" bridge approach).
            ("substance_workflow", "extapps.substance_workflow", "SubstanceWorkflowUI"),
            ("marmoset_workflow", "extapps.marmoset_workflow", "MarmosetWorkflowUI"),
        ):
            self.sb.handlers.external_app.register(
                _name,
                module=_module,
                entry=_entry,
                # No ``install_spec`` here (Maya carries one): an in-process install resolves the
                # interpreter as ``sys.executable`` — the *Blender binary*, not a python — so a pip
                # call would hang/fail rather than help. extapps is put on ``sys.path`` by
                # ``_QtBootstrap.bootstrap_paths`` instead; if it's genuinely absent the launch raises
                # a clear RuntimeError (surfaced by the materials slot) rather than wedging the UI.
                mode="in_process",
            )

        # Bridge the activation key from Blender's keymap to this Qt menu (GHOST owns the
        # keyboard, so MarkingMenu's QShortcut can't fire from the viewport). Automatic on
        # construction — the same install model as Maya; no separate add-on to enable.
        # The poller covers what the keymap can't: GHOST eats the key while a mouse button
        # is held (see _KeymapBridge.install_poller).
        try:
            _KeymapBridge.install_keymap(self, _KeymapBridge.qt_key_to_blender_type(key_show))
            _KeymapBridge.install_poller(self, key_show)
        except Exception as error:
            print(f"{__file__}: Blender keymap bridge skipped: {error}")

        # Own the overlay to Blender's GHOST window so the OS keeps it stacked above Blender.
        self._parent_to_blender(self)

    @classmethod
    def get_main_window(cls):
        """Blender parent widget for the marking menu (set by :meth:`_QtHost.ensure_widget`).

        Returns ``None`` when unset — the menu then shows as a top-level window, which
        works over Blender (Phase 0). Never raises.
        """
        app = QtWidgets.QApplication.instance()
        return getattr(app, "blender_widget", None) if app is not None else None

    def _parent_to_blender(self, widget):
        """Make ``widget`` an *owned* window of Blender's native GHOST window so the OS keeps it
        stacked above Blender (and minimizes/closes it with Blender) — applied to the overlay AND
        to every standalone tool window the menu opens (see :meth:`_show_window`).

        Blender isn't a Qt app, so a top-level Qt window is otherwise an unrelated OS window: it
        falls behind Blender the moment it loses focus and doesn't move/minimize with it. The Qt
        idiom — ``setTransientParent`` to Blender's GHOST window wrapped as a foreign ``QWindow`` —
        is kept for Qt's own stacking bookkeeping and the non-Windows path, but it does **not** set
        the Windows owner (``GWLP_HWNDPARENT``) for a *foreign* transient parent (verified on PySide6
        6.10), which is the bug that left every Blender tool window unowned. So on Windows the owner
        is set explicitly via :meth:`_NativeWindow.set_owner`. Best-effort: a no-op off-Windows or
        before the GHOST handle is enumerable."""
        try:
            native = _NativeWindow.blender_window()  # also caches app._blender_native_hwnd
            if native is None or widget is None:
                return
            widget.winId()  # force native-window creation so windowHandle() exists
            handle = widget.windowHandle()
            if handle is not None:
                handle.setTransientParent(native)
            # Foreign transient parents don't set the OS owner — do it directly (Windows).
            app = QtWidgets.QApplication.instance()
            _NativeWindow.set_owner(widget, getattr(app, "_blender_native_hwnd", 0) if app else 0)
        except Exception as error:
            # Best-effort z-order nicety; DEBUG-gated so a persistent failure can't spam the console
            # (this runs per tool-window open via _show_window, not just once at construction).
            if _Config.DEBUG:
                print(f"{__file__}: parent-to-Blender skipped: {error}")

    def _show_window(self, widget, *args, **kwargs):
        """Parent standalone tool windows to Blender too (the overlay is done in ``__init__``)."""
        result = super()._show_window(widget, *args, **kwargs)
        self._parent_to_blender(result if result is not None else widget)
        return result

    def _host_mouse_buttons(self):
        # GHOST owns the mouse, so the base Qt query (QApplication.mouseButtons()) is blind to a
        # button held over the viewport. Read the physical state instead so the shared MouseTracking
        # runs its drag-gated track() during a chord gesture — that's what synthesizes the enter
        # events the marking menu's `visible_on_mouse_over` Regions (cameras/editors upper+lower)
        # need to reveal their nav buttons. Without this the regions never appear and the chord
        # submenus "don't launch". Falls back to Qt off-Windows / when nothing is physically held.
        physical = _KeymapBridge.physical_mouse_buttons()
        return physical if physical != QtCore.Qt.NoButton else super()._host_mouse_buttons()

    def showEvent(self, event):
        # Re-assert the GHOST ownership on every show: construction can run before the native
        # Blender window is enumerable, and Qt re-creates the overlay's native window on some
        # flag changes — either silently drops the OS owner (GWLP_HWNDPARENT) that keeps the menu
        # stacked above Blender. Can't gate on ``transientParent()``: Qt keeps recording the
        # transient parent across a native-window recreate even though the OS owner was dropped,
        # so the old gate skipped the re-set and the overlay fell behind Blender. Re-asserting is
        # a cheap idempotent SetWindowLongPtr.
        self._parent_to_blender(self)
        super().showEvent(event)

    def keyPressEvent(self, event):
        # Ctrl+Z while the menu holds focus -> Blender undo. (The previous stub referenced a
        # non-existent ``self.key_undo``; it never fired because TclBlender was never launched.)
        if not event.isAutoRepeat():
            modifiers = QtWidgets.QApplication.instance().keyboardModifiers()
            if event.key() == QtCore.Qt.Key_Z and modifiers == QtCore.Qt.ControlModifier:
                try:
                    import bpy

                    bpy.ops.ed.undo()
                except Exception:
                    pass

        super().keyPressEvent(event)

    def keyReleaseEvent(self, event):
        # Release detection lives HERE on the Qt side: once shown, the overlay takes OS keyboard
        # focus, so the activation key's RELEASE arrives as a Qt event (not at Blender's keymap, which
        # no longer has focus) — and the menu's own GlobalShortcut release filter is disarmed because
        # its press never fired (GHOST consumed the key-down). Completing the gesture here is what hides
        # the menu + releases the mouse grab. Idempotent with the Blender RELEASE keymap fallback.
        if not event.isAutoRepeat() and event.key() == self._activation_key:
            try:
                _KeymapBridge.drive_release()
            except Exception:
                pass
        super().keyReleaseEvent(event)


# --------------------------------------------------------------------------------------------
# Click debugging — opt-in mouse-event tracer for "buttons need several clicks" reports.
# --------------------------------------------------------------------------------------------
class _ClickDebugger:
    """Opt-in two-layer tracer for "buttons need several clicks" reports.

    (1) An app-wide mouse-event observer logs every press/release/dblclick (target widget,
    ``widgetAt``, grab owner, active window, foreground, ``_activation_key_held``).
    (2) A slot-dispatch trace (:meth:`_install_slot_trace`) logs whether each click's slot
    actually ran.

    Captured data ruled out the original window-activation theory for the *open panel* case:
    presses and releases deliver cleanly to the button (``fg_is_ghost=False``, ``grab=None``)
    yet the action can still not happen — so the loss is at the slot layer, not the OS window.
    The slot trace localizes which: ``clicked`` never reaching the wrapper (dblclick-eaten or a
    lost connection), a debounce/coalesce swallow, or the slot running but raising into Blender's
    hidden system console.
    """

    path = os.path.join(os.path.expanduser("~"), "tentacle_click_debug.log")
    _fh = None
    _filter = None
    _slot_patch = None  # (orig __call__, orig _invoke) saved for restore on disable

    @staticmethod
    def _widget_id(w):
        """Short '<objectName-or-class>:<class>' id for a widget, never raises."""
        if w is None:
            return "None"
        try:
            return f"{w.objectName() or '-'}:{type(w).__name__}"
        except Exception:
            return repr(w)

    @classmethod
    def _write(cls, line):
        if cls._fh is None:
            return
        try:
            cls._fh.write(line + "\n")
        except Exception:
            pass

    @classmethod
    def _install_slot_trace(cls):
        """Trace the slot dispatch chokepoint so the log shows whether a click's
        slot actually *ran* — the event filter only proves the click was
        delivered, not that the slot fired. ``SLOT_CALL`` = the clicked signal
        reached the wrapper; ``SLOT_RUN``/``SLOT_RAISED`` = the slot body
        executed (and whether it threw — a Blender context error in
        ``@btk.undoable`` would surface here, invisible otherwise as it prints to
        Blender's hidden system console). A click with a clean delivery but no
        ``SLOT_CALL`` is dispatch loss; ``SLOT_CALL`` with no ``SLOT_RUN`` is a
        debounce/coalesce swallow; ``SLOT_RUN`` with no visible effect is an
        idempotent/no-op action, not a dead click. Patches the class (covers
        already-connected wrappers), restored verbatim by :meth:`_remove_slot_trace`."""
        if cls._slot_patch is not None:
            return
        try:
            from uitk.switchboard.slots import SlotWrapper
        except Exception as e:
            cls._write(f"{time.time():.3f} SLOT_TRACE_UNAVAILABLE err={e!r}")
            return

        # Anchor to the TRUE original, peeling any stale trace left installed by a
        # prior enable that was never disabled before a module reload — otherwise we
        # wrap an already-traced function (double logging) and disable() would restore
        # to the stale trace, leaving logging on after "off".
        orig_call = getattr(SlotWrapper.__call__, "_slot_trace_orig", SlotWrapper.__call__)
        orig_invoke = getattr(SlotWrapper._invoke, "_slot_trace_orig", SlotWrapper._invoke)

        def _name(self):
            try:
                w = self.widget.objectName() if self.widget is not None else "?"
            except Exception:
                w = "?"
            return f"{w}:{getattr(self.slot, '__name__', '?')}"

        def traced_call(self, *args, **kwargs):
            try:
                ui = getattr(self.widget, "ui", None)
                uin = ui.objectName() if ui is not None else "?"
                deb = getattr(self.widget, "debounce", 0) or 0
                cls._write(f"{time.time():.3f} SLOT_CALL widget={_name(self)} ui={uin} debounce={deb}")
            except Exception:
                pass
            return orig_call(self, *args, **kwargs)

        def traced_invoke(self, *args, **kwargs):
            cls._write(f"{time.time():.3f} SLOT_RUN  widget={_name(self)}")
            try:
                return orig_invoke(self, *args, **kwargs)
            except BaseException as e:
                cls._write(f"{time.time():.3f} SLOT_RAISED widget={_name(self)} err={e!r}")
                raise

        traced_call._slot_trace_orig = orig_call
        traced_invoke._slot_trace_orig = orig_invoke
        SlotWrapper.__call__ = traced_call
        SlotWrapper._invoke = traced_invoke
        cls._slot_patch = (orig_call, orig_invoke)

    @classmethod
    def _remove_slot_trace(cls):
        """Restore the un-traced slot dispatch installed by :meth:`_install_slot_trace`."""
        if cls._slot_patch is None:
            return
        try:
            from uitk.switchboard.slots import SlotWrapper

            SlotWrapper.__call__, SlotWrapper._invoke = cls._slot_patch
        except Exception:
            pass
        cls._slot_patch = None

    class Filter(QtCore.QObject):
        """Application event filter that logs each mouse-button event with the context needed to see
        why a first click doesn't execute. Installed by :meth:`_ClickDebugger.enable`, off by default."""

        _NAMES = {
            QtCore.QEvent.MouseButtonPress: "PRESS",
            QtCore.QEvent.MouseButtonRelease: "RELEASE",
            QtCore.QEvent.MouseButtonDblClick: "DBLCLICK",
        }

        def eventFilter(self, obj, event):
            name = self._NAMES.get(event.type())
            if name:
                try:
                    app = QtWidgets.QApplication.instance()
                    gpos = event.globalPosition().toPoint() if hasattr(event, "globalPosition") else event.globalPos()
                    at = QtWidgets.QApplication.widgetAt(gpos)
                    grab = QtWidgets.QWidget.mouseGrabber()
                    active = app.activeWindow() if app else None
                    held = getattr(_KeymapBridge.tcl, "_activation_key_held", None)
                    fg = ""
                    if sys.platform == "win32" and app is not None:
                        try:
                            import ctypes

                            hwnd = ctypes.windll.user32.GetForegroundWindow()
                            fg = f" fg_is_ghost={hwnd == getattr(app, '_blender_native_hwnd', 0)}"
                        except Exception:
                            pass
                    _ClickDebugger._write(
                        f"{time.time():.3f} {name:8} target={_ClickDebugger._widget_id(obj)} "
                        f"widgetAt={_ClickDebugger._widget_id(at)} grab={_ClickDebugger._widget_id(grab)} "
                        f"active={_ClickDebugger._widget_id(active)} held={held}{fg}"
                    )
                except Exception:
                    pass
            return False  # never consume — pure observer

    @classmethod
    def enable(cls):
        """Turn on click tracing — run in Blender's Python Console, reproduce the multi-click, then
        share ``~/tentacle_click_debug.log``.

        Installs an application-wide mouse-event observer (logs every press/release with the target
        widget, ``widgetAt``, grab owner, active window, foreground, and ``_activation_key_held``).
        :meth:`disable` removes it."""
        if cls._fh is None:
            cls._fh = open(cls.path, "a", buffering=1, encoding="utf-8")
        cls._write(f"\n===== click-debug enabled pid={os.getpid()} t={time.time():.3f} =====")
        app = _QtHost.ensure_qapp()
        if cls._filter is None:
            cls._filter = cls.Filter()
            app.installEventFilter(cls._filter)
        cls._install_slot_trace()  # also trace whether each click's slot actually runs
        print(f"tentacle: click debugging ON\n  {cls.path}\n"
              "Reproduce the multi-click, then disable_click_debug().")
        return cls.path

    @classmethod
    def disable(cls):
        """Remove the click tracer installed by :meth:`enable`."""
        app = QtWidgets.QApplication.instance()
        if cls._filter is not None and app is not None:
            app.removeEventFilter(cls._filter)
        cls._filter = None
        cls._remove_slot_trace()
        if cls._fh is not None:
            try:
                cls._fh.close()
            except Exception:
                pass
            cls._fh = None
        print("tentacle: click debugging OFF")


class Diagnostics:
    """The live-activation-state report — run in Blender's Python console to see why the key isn't
    showing the menu."""

    @staticmethod
    def report():
        """Return (and print) the live activation state — run in Blender's Python console to see why
        the key isn't showing the menu::

            print(tcl_blender.diagnose())

        The returned string is shown right in the Python Console panel (``print()`` alone would land in
        the hidden *system* console). Reports the live module file (a stale/duplicate ``tentacle`` on
        ``sys.path`` is the #1 cause of "nothing happens"), whether the bridge operator is registered,
        whether a live ``TclBlender`` is wired, the keymap item(s) we installed, any *other* active item
        bound to the same bare key in the ``3D View`` keymap (the only thing that could beat us over the
        viewport), and a plain-language VERDICT. Blender's bare-F12 ``render.render`` lives in the global
        ``Screen`` keymap and is evaluated *after* our region item, so it is intentionally not a rival."""
        import bpy

        wm = bpy.context.window_manager
        operator_ok = hasattr(bpy.types, "TENTACLE_OT_show_marking_menu")
        our_active = [kmi for _km, kmi in _KeymapBridge.keymaps if kmi.active]
        our_keys = {kmi.type for _km, kmi in _KeymapBridge.keymaps}
        rivals = []
        seen = set()
        # Scan every evaluated config — including ``addon`` (another add-on binding bare F12 in the
        # viewport is a real conflict the clean factory session can't show, so it must be checked too).
        # Dedup by name, not id(): ``active`` often aliases ``user``/``default`` but Blender hands back a
        # fresh Python wrapper each access (distinct id), so id()-dedup would double-list its rivals.
        for kc in (wm.keyconfigs.addon, wm.keyconfigs.user, wm.keyconfigs.active, wm.keyconfigs.default):
            if kc is None or kc.name in seen:
                continue
            seen.add(kc.name)
            # Only a *bare* same-key PRESS in the 3D View keymap could beat us when the viewport has
            # focus — modified combos coexist and the global Screen render shortcut is evaluated after us.
            rivals += [
                f"{kc.name}:{kmi.idname}"
                for km in kc.keymaps if km.name == "3D View"
                for kmi in km.keymap_items
                if kmi.active and kmi.type in our_keys and _KeymapBridge._is_bare_press(kmi)
                and kmi.idname != "tentacle.show_marking_menu"
            ]

        if not (operator_ok and our_active):
            verdict = ("PROBLEM: activation key not installed — call tcl_blender.register(). If you "
                       "just did, a stale/duplicate tentacle is on sys.path — check 'module file' above.")
        elif _KeymapBridge.tcl is None:
            verdict = "PROBLEM: no live menu wired — call tcl_blender.register() (it runs launch())."
        elif rivals:
            verdict = (f"CONFLICT: another 3D View binding {rivals} shares the key and may win — "
                       "disable it, or set TENTACLE_KEY to a different key.")
        else:
            key = next(iter(our_keys), _Config.ACTIVATION_KEY)
            verdict = (f"LIKELY WORKING: '{key}' is bound in the 3D View keymap. Hover the 3D viewport "
                       "and press it. If render still opens, set tcl_blender._Config.DEBUG=True — each "
                       "fire then shows 'Tentacle: key fired' in the status bar (print() output is in the "
                       "hidden system console: Window > Toggle System Console).")

        lines = [
            "=== tentacle Blender activation ===",
            f"module file        : {__file__}",
            f"operator registered: {operator_ok}",
            f"live TclBlender     : {_KeymapBridge.tcl!r}",
            f"DEBUG (logs fires)  : {_Config.DEBUG}",
            f"key watcher (poll)  : {'installed' if _KeymapBridge.poller is not None else 'NOT installed'} (held-button press + release watchdog)",
            f"our keymap items    : {[(km.name, kmi.type, kmi.value, kmi.active) for km, kmi in _KeymapBridge.keymaps]}",
            f"3D View rivals      : {rivals or 'none'}",
            f"VERDICT             : {verdict}",
        ]
        report = "\n".join(lines)
        print(report)
        return report


class BlenderHost:
    """Launcher + Blender add-on lifecycle coordinator — ties the Qt host, keymap bridge and menu
    together. The thin module-level functions below delegate here (Blender's add-on contract requires
    module-scope ``register``/``unregister``; the rest are the documented console API)."""

    @staticmethod
    def launch(**kwargs):
        """Stand up the Qt host (QApplication + ``blender_widget`` + event pump) and return a
        :class:`TclBlender` marking-menu instance.

        Idempotent: a repeat call (e.g. re-running :meth:`register` from a startup snippet) returns
        the live instance instead of stacking a second marking menu; :meth:`unregister` clears it,
        so unregister→register builds fresh. ``**kwargs`` are forwarded to ``TclBlender`` (e.g.
        ``key_show``, ``log_level``) and only take effect when a new instance is built.
        """
        app = _QtHost.ensure_qapp()
        _QtHost.ensure_widget(app)
        _QtHost.start_pump(app)
        if _KeymapBridge.tcl is not None:  # set by install_keymap during TclBlender.__init__
            return _KeymapBridge.tcl
        return TclBlender(**kwargs)

    @staticmethod
    def register():
        """Blender add-on / startup entry: stand up the host. ``TclBlender`` wires the keymap itself.

        Returns the :meth:`Diagnostics.report` report (so ``tcl_blender.register()`` typed in the
        Python Console shows the live state right there) and, if anything's wrong, raises a Blender
        popup — because a user running this from the console can't see ``print()`` output (it goes to
        the hidden *system* console, not the Python Console panel)."""
        import bpy

        BlenderHost.launch(key_show=_Config.ACTIVATION_KEY)
        report = Diagnostics.report()
        if "PROBLEM" in report or "CONFLICT" in report:
            message = report.splitlines()[-1].split(": ", 1)[-1]  # verdict text, minus the "VERDICT :" label
            try:
                bpy.context.window_manager.popup_menu(
                    lambda menu, _ctx: menu.layout.label(text=message[:200]),
                    title="Tentacle activation", icon="ERROR",
                )
            except Exception:
                pass
        return report

    @staticmethod
    def unregister():
        """Blender add-on teardown: remove the keymap items + bridge operator."""
        _KeymapBridge.teardown()

    @staticmethod
    def reload():
        """Reload the tentacle ecosystem in place and re-register — the Blender "Reload Scripts".

        ``bpy.ops.script.reload()`` would tear down the Qt host with it; this instead tears down
        tentacle's own surface (keymap / operator / poller; the event pump retires itself via its
        generation token), reloads the monorepo packages in dependency order via
        ``ptk.reload_package`` (Qt bindings are never touched), and re-registers from the freshly
        loaded module on the next timer tick — after the stale frames (including the slot that
        called this) have unwound. Returns the number of modules reloaded.
        """
        import importlib

        import bpy
        import pythontk as ptk

        if _KeymapBridge.tcl is not None:
            try:
                _KeymapBridge.tcl.hide()
            except Exception:
                pass
        _KeymapBridge.teardown()
        # import_missing=False: refresh only the modules actually loaded in this session —
        # discovery-importing the rest would pull in the OTHER DCCs' slot packages
        # (tentacle.slots.maya imports maya and would raise here).
        reloaded = ptk.reload_package(
            "tentacle",
            dependencies_first=("pythontk", "blendertk", "uitk"),
            import_missing=False,
        )

        def _re_register():
            importlib.import_module("tentacle.tcl_blender").register()
            return None

        bpy.app.timers.register(_re_register, first_interval=0.2)
        return len(reloaded)


# --------------------------------------------------------------------------------------------
# Module-level surface — Blender's add-on contract requires module-scope ``bl_info`` +
# ``register``/``unregister``; the rest are the documented console API + the Qt-host helpers the
# blender test harnesses call. Each is a thin delegator — all logic and state live in the classes.
# --------------------------------------------------------------------------------------------
def ensure_qapp():
    """Return the process QApplication, creating one if Blender has none."""
    return _QtHost.ensure_qapp()


def ensure_blender_widget(app):
    """Establish ``app.blender_widget`` — the parent for the marking menu."""
    return _QtHost.ensure_widget(app)


def start_event_pump(app, interval=0.01):
    """Pump Qt events from Blender's timer loop so the Qt UI stays responsive (idempotent)."""
    return _QtHost.start_pump(app, interval)


def blender_native_window():
    """Blender's main GHOST window wrapped as a foreign ``QWindow`` (cached on the QApplication)."""
    return _NativeWindow.blender_window()


def launch(**kwargs):
    """Stand up the Qt host and return a :class:`TclBlender` (idempotent). See :meth:`BlenderHost.launch`."""
    return BlenderHost.launch(**kwargs)


def register():
    """Blender add-on / startup entry. See :meth:`BlenderHost.register`."""
    return BlenderHost.register()


def unregister():
    """Blender add-on teardown. See :meth:`BlenderHost.unregister`."""
    return BlenderHost.unregister()


def reload():
    """Reload the tentacle ecosystem in place and re-register. See :meth:`BlenderHost.reload`."""
    return BlenderHost.reload()


def diagnose():
    """Return (and print) the live activation state. See :meth:`Diagnostics.report`."""
    return Diagnostics.report()


def enable_click_debug():
    """Turn on the opt-in click tracer. See :meth:`_ClickDebugger.enable`."""
    return _ClickDebugger.enable()


def disable_click_debug():
    """Remove the click tracer. See :meth:`_ClickDebugger.disable`."""
    return _ClickDebugger.disable()


# --------------------------------------------------------------------------------------------

if __name__ == "__main__":
    # Text-Editor ▸ Run-Script (or `blender --python tcl_blender.py`) lands here. Make it
    # idempotent: re-running otherwise errors on the already-registered operator.
    try:
        unregister()
    except Exception:
        pass
    register()


# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
