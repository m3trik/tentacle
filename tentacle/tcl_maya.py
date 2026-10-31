# !/usr/bin/python
# coding=utf-8
import mayatk as mtk
from uitk import MarkingMenu, ExternalAppHandler, ShortcutManager

from tentacle.tcl import Tcl


class TclMaya(MarkingMenu):
    """Marking Menu class overridden for use with Autodesk Maya."""

    #: Maya's event loop is native, so the preload advances only from it and
    #: waits out any script pumping events: a tick fired inside mayatk's
    #: test_shot_manifest (``processEvents`` after a menu) built the HUD start
    #: menu there and faulted Maya.
    PRELOAD_ONLY_FROM_HOST_LOOP = True

    #: The native-menu pages: pure navigation (no Slots class). A release opens
    #: one of Maya's own menus, which ``mtk.MayaUiHandler`` builds
    #: (``MayaNativeMenus``) the first time the switchboard resolves its name.
    NATIVE_MENU_UI = "ui/maya_menus"

    def __init__(self, parent=None, slot_source=None, log_level="WARNING", **kwargs):
        if not parent:
            try:
                parent = mtk.get_main_window()
            except Exception as error:
                print(f"Error getting main window: {error}")
        # Maya's main window owns application-scoped shortcuts (it is always up);
        # uitk names no host, so the host declares it.
        ShortcutManager.register_host_window("MayaWindow")

        # The key the user last CHOSE (persisted) > key_show (this install's default) >
        # Tcl.DEFAULT_KEY — see Tcl.resolve_key. context_tags must match the set passed
        # to super() below.
        key_show = Tcl.resolve_key(kwargs.pop("key_show", None), {"maya"})
        # Default bindings for Maya — the shared chord table, with Maya's native menus on the
        # both-button chord (see Tcl.chord_bindings; Blender's fork differs only in that target).
        bindings = kwargs.pop("bindings", None) or Tcl.chord_bindings(
            key_show, "maya#startmenu"
        )

        super().__init__(
            parent,
            ui_source=("ui", self.NATIVE_MENU_UI),
            slot_source=slot_source,
            bindings=bindings,
            handlers={"ui": mtk.MayaUiHandler, "external_app": ExternalAppHandler},
            log_level=log_level,
            suppress_default_on_reentry=True,
            precompile=True,
            # Scoped preloading: once Maya's event loop is idle, warm the
            # binding-target startmenus, then the submenus they open, so the
            # FIRST key_show press and the first hover into each submenu behave
            # like every later one. A native-menu page warms like any other:
            # Maya's own menu builds on its first release, never on a page load.
            preload=True,
            context_tags={"maya"},  # `requires` widget filtering (Phase-5 visibility)
            **kwargs,
        )
        # The toolkit a Slots class shared by both hosts calls (Slots.tk).
        self.sb.tk = mtk
        # The shot store's host half, injected here; a script that skips this
        # entry point gets it from the store, resolved on first call.
        mtk.ShotStore.set_host(mtk.MayaShotsHost.resolve())
        # The composed Slots classes and the tool panels both hosts share.
        Tcl.register_shared(self.sb)

        # tentacle provides the standalone panels (tcl_standalone.py) as external
        # apps. Named as their provider, a tentacle that reaches Maya as a source
        # checkout on PYTHONPATH (no installed metadata) has its entry-point
        # table read from its pyproject.toml instead.
        try:
            self.sb.handlers.external_app.add_provider(Tcl.DIST, probe_module="tentacle")
            self.sb.handlers.external_app.discover()  # now: the checkout's table wins
        except Exception:  # never let provisioning wiring block startup
            pass

        # Register the Maya hotkey-collision checker on the bundled
        # ShortcutEditor whenever it's built. Lazily wired so the editor
        # module stays unimported until the user opens it.
        for _editor_name in ("shortcut_editor", "global_shortcuts"):
            self.sb.editors.add_post_build_hook(
                _editor_name,
                lambda editor: editor.add_collision_checker(
                    mtk.HotkeyCollisions.maya_collision_checker
                ),
            )

        # Apply the user's active macro preset on launch so its hotkeys are live
        # immediately — without opening the Macro Manager. Maya persists
        # non-default hotkeys on its own (mayatk's docstring calls this out as
        # NOT a startup requirement), but re-applying makes the preset the
        # deterministic source of truth: the saved bindings win over anything
        # re-bound through Maya's native hotkey editor since the preset was
        # saved. Also matches TclBlender, where this call IS required (the
        # addon keyconfig doesn't outlive the process).
        # No active preset -> a no-op (the shipped 'default' set is empty).
        try:
            mtk.Macros.apply_saved_macros()
        except Exception as error:  # never let a preset issue block launch
            print(f"# Warning: tentacle: apply_saved_macros failed: {error} #")

        # The standalone panels (compositor, photogrammetry, texture/mesh tools)
        # self-describe via tentacle's ``uitk.external_apps.in_process`` entry
        # points and are auto-registered by ExternalAppHandler on construction
        # -- no per-app list here; each opens in a switchboard of its own
        # (``slots.tools.STANDALONE``). ``context_tags={"maya"}`` (above) hides
        # apps gated ``hide_maya`` (Substance/Marmoset, which Maya serves through
        # its own bridges). Their engines are extapps', a tentacle dependency.


# --------------------------------------------------------------------------------------------

if __name__ == "__main__":
    main = TclMaya()
    main.show()


# module name
# print(__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
