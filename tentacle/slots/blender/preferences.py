# !/usr/bin/python
# coding=utf-8
import os
import sys

import bpy
import blendertk as btk
from tentacle.slots.blender._slots_blender import SlotsBlender


class Preferences(SlotsBlender):
    """Blender port of the shared ``preferences`` menu.

    Working units (length) and frame rate map onto ``scene.unit_settings`` / ``scene.render.fps``;
    autosave maps onto Blender's user filepaths prefs. The Maya preference windows (color, hotkeys,
    plug-ins) open Blender's Preferences editor instead.
    """

    # Blender metric length units (combo label -> length_unit enum).
    _LENGTH_UNITS = {
        "Millimeter": "MILLIMETERS",
        "Centimeter": "CENTIMETERS",
        "Meter": "METERS",
        "Kilometer": "KILOMETERS",
    }
    _FPS_OPTIONS = [24, 25, 30, 48, 60]

    def __init__(self, switchboard):
        super().__init__(switchboard)
        self.ui = self.sb.loaded_ui.preferences
        self.submenu = self.sb.loaded_ui.preferences_submenu

        # The preferences .ui pair is shared with every other DCC, so the app name
        # can't live in Designer — each host writes its own over the `<app>` token.
        self.ui.parent_app.setTitle("Blender Preferences")
        self.submenu.b010.setText("Blender Preferences")

    def _open_preferences(self, section=None):
        """Open Blender's Preferences editor, optionally on a specific section, and make sure
        the window actually surfaces.

        Three live-verified gotchas (see ``test/blender/userpref_visibility_check.py``):

        - ``userpref_show``'s poll reads ``context.window``, which is ``None`` when tentacle
          drives a slot from its Qt event-pump timer (``userpref_show.poll() failed, context is
          incorrect``) — so every prefs button dead-ended in the "Could not open" message below.
          Wrapping in ``btk.window_context_override`` supplies the first open window, exactly as
          ``btk.open_editor`` does for this same op; it's a harmless no-op when a window is
          already active.
        - ``bpy.ops.screen.userpref_show`` can succeed *invisibly*: with OS foreground held by
          another process (e.g. the user was last in Maya and clicked straight onto this Qt
          panel), Windows denies GHOST the foreground transfer — the window opens (or is
          reused) fully obscured and retries never raise it, which reads as a dead button.
          Same-process the op raises it fine, so the explicit lift below is a cheap no-op
          there and the visible fix otherwise.
        - Failures were previously swallowed (``except Exception: pass``), making every
          failure mode indistinguishable from a dead click — surface them like ``invoke_op``.
        """
        if section:
            try:
                bpy.context.preferences.active_section = section
            except (TypeError, AttributeError):
                pass
        try:
            with btk.window_context_override():
                bpy.ops.screen.userpref_show()
        except Exception as error:
            self.sb.message_box(f"Could not open Blender Preferences: {error}")
            return
        self._raise_ghost_window("Preferences")

    @staticmethod
    def _raise_ghost_window(title_fragment):
        """Best-effort: lift this process's GHOST (Blender-native) window whose title contains
        ``title_fragment`` above our own windows — and to OS foreground where Windows allows it
        (always granted same-process; denied cross-process, where the z-lift still applies).
        Windows-only and English-UI window titles; silently a no-op elsewhere or when no such
        window exists (the operator itself already succeeded)."""
        if sys.platform != "win32":
            return
        import ctypes
        from ctypes import wintypes

        user32 = ctypes.windll.user32
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
                    if title_fragment in title.value:
                        found.append(hwnd)
            return True

        user32.EnumWindows(_enum, 0)
        if found:
            HWND_TOP, SWP_NOMOVE, SWP_NOSIZE = 0, 0x2, 0x1
            user32.SetWindowPos(found[0], HWND_TOP, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE)
            user32.SetForegroundWindow(found[0])

    # ------------------------------------------------------------------ cmb001  Linear units
    def cmb001_init(self, widget):
        # The scene owns its units, so mirror them rather than persist a copy: a restored
        # index re-fired cmb001 on panel open, overwriting the scene's real units with the
        # last session's pick. Same for cmb002/fps below. (Neither combo passes `header=`,
        # which is what opts a combo out of restore for free -- see ComboBox.add.)
        #
        # Populating happens inside the seed because `add` itself emits currentIndexChanged
        # (ComboBox.add's own emit, and Qt's on the first item), which on uitk's DEFERRED
        # init path -- where *_init runs unblocked -- fired cmb001 and wrote index 0's unit
        # to the scene before the real one was seeded.
        current = bpy.context.scene.unit_settings.length_unit
        labels = list(self._LENGTH_UNITS)
        match = next((lbl for lbl, u in self._LENGTH_UNITS.items() if u == current), None)

        def seed():
            widget.add(self._LENGTH_UNITS)
            # No matching label (IMPERIAL/NONE unit system): show no selection (-1)
            # rather than misreporting item 0 (Millimeter) as the scene's current unit.
            widget.setCurrentIndex(labels.index(match) if match else -1)

        self.mirror_app_state(widget, seed)

    def cmb001(self, index, widget):
        """Set Working Units: Linear"""
        unit = widget.currentData()
        us = bpy.context.scene.unit_settings
        us.system = "METRIC"
        us.length_unit = unit

    # ------------------------------------------------------------------ cmb002  Frame rate
    def cmb002_init(self, widget):
        render = bpy.context.scene.render
        # Effective rate — a 23.98 scene stores fps=24 / fps_base=1.001; raw fps alone
        # would also misread a scene whose base was left fractional by an import.
        fps = round(render.fps / render.fps_base)

        def seed():  # populated inside the seed for the reason given in cmb001_init
            widget.add({f"{f} fps": f for f in self._FPS_OPTIONS})
            # Nonstandard rate: show no selection (-1) rather than misreporting
            # item 0 (24 fps) as the scene's current rate.
            widget.setCurrentIndex(
                self._FPS_OPTIONS.index(fps) if fps in self._FPS_OPTIONS else -1
            )

        self.mirror_app_state(widget, seed)

    def cmb002(self, index, widget):
        """Set Working Units: Time (frame rate)"""
        render = bpy.context.scene.render
        render.fps = int(widget.currentData())
        # Clear any fractional-rate divisor — a 23.98 scene (fps=24, fps_base=1.001)
        # would otherwise become 30/1.001 = 29.97 when the user picks 30.
        render.fps_base = 1.0

    # ------------------------------------------------------------------ s000/s001  Autosave
    def s000_init(self, widget):
        if not widget.is_initialized:
            widget.setValue(bpy.context.preferences.filepaths.save_version)
            widget.valueChanged.connect(
                lambda v: setattr(bpy.context.preferences.filepaths, "save_version", int(v))
            )

    def s001_init(self, widget):
        if not widget.is_initialized:
            fp = bpy.context.preferences.filepaths
            # 0 = disabled, like the Maya twin (maya/preferences.py s000_init) — showing
            # the live interval while autosave is off would misreport it as active.
            widget.setValue(fp.auto_save_time if fp.use_auto_save_temporary_files else 0)

            def _update(value):
                fp.use_auto_save_temporary_files = value > 0
                if value > 0:
                    fp.auto_save_time = int(value)

            widget.valueChanged.connect(_update)

    # ------------------------------------------------------------------ b-slots (open prefs)
    def b001(self):
        """Color Settings → Blender Preferences (Themes)."""
        self._open_preferences("THEMES")

    def cmb003_init(self, widget):
        """App-style / theme selector — mirrors Blender's Preferences > Themes dropdown. It
        injects our shipped ``Maya`` theme into Blender's preset dir (idempotent), then lists the
        whole native set (built-in + user + ours) exactly like the dropdown would. Reverting to the
        user's own look is just picking their built-in/own theme back from this same list — no
        bespoke backup entry needed. See ``blendertk.ui_utils.style_setter`` and the Maya-side
        counterpart (``slots/maya/preferences.py`` ``cmb003``)."""
        # Same self-fire/restore hazard as cmb001/cmb002 above: `add` emits
        # currentIndexChanged (silently applying the alphabetically-first theme on panel
        # open), and a restored index re-fires cmb003 with a stale pick. Blender records
        # no "current preset" (StyleSetter has no getter — applying a theme leaves no
        # pointer to read back), so the index is left unselected (-1) instead of seeded:
        # item 0 would misreport as active, and a first theme shown at index 0 could
        # never be applied by picking it (no index change, no signal).
        def seed():
            btk.StyleSetter.install()  # inject shipped 'Maya' theme into the native dropdown
            widget.add(btk.StyleSetter.list_templates())  # {display_name: token}
            widget.setCurrentIndex(-1)

        self.mirror_app_state(widget, seed)

    def cmb003(self, index, widget):
        """Apply the selected native theme preset (Blender's built-in, the user's own, or our
        injected ``Maya``) — exactly as Blender's own Themes dropdown would."""
        import blendertk as btk

        btk.StyleSetter.apply_template(widget.currentData())

    def b008(self):
        """Hotkeys → Blender Preferences (Keymap)."""
        self._open_preferences("KEYMAP")

    def b009(self):
        """Plug-In Manager → Blender Preferences (Add-ons)."""
        self._open_preferences("ADDONS")

    def b010(self):
        """Settings/Preferences → Blender Preferences (Interface)."""
        self._open_preferences("INTERFACE")

    def b011(self):
        """Macro Manager — the unified shortcut editor over the blendertk macros
        (``btk.Macros.show_editor``, 1:1 with mayatk; the bespoke panel was
        retired)."""
        btk.Macros.show_editor(parent=self.sb.handlers.marking_menu)


# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
