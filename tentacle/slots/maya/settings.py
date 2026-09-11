# !/usr/bin/python
# coding=utf-8
import html
import os

import maya.cmds as cmds
import mayatk as mtk
from maya.utils import executeDeferred

# From this package:
from tentacle import SettingsMixin, SlotsMaya


class Settings(SettingsMixin, SlotsMaya):
    """Maya fork of the shared ``settings`` menu.

    Everything DCC-agnostic (header Package menu, the ecosystem updater, editor
    launchers, marking-menu binding combos) lives on ``SettingsMixin``. This class
    supplies the pip interpreter (mayapy) and Reload Scripts.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.ui = self.sb.loaded_ui.settings
        self.submenu = self.sb.loaded_ui.settings_submenu

    def _update_python_path(self) -> str:
        """The interpreter whose environment the updater checks and upgrades."""
        return os.path.join(mtk.get_env_info("install_path"), "bin", "mayapy.exe")

    def tb001(self):
        """Reload Scripts (tear down, reload the ecosystem in place, rebuild deferred).

        The rebuild is DEFERRED onto Maya's idle queue rather than run here: this
        slot's own frame belongs to the module the reload is re-executing, and
        building a new marking menu while Qt is still dispatching the click that
        launched it destroys and constructs widget trees underneath the event
        being delivered. ``Tcl.launch`` defers on its own, so the new instance
        comes up on an idle tick with every stale frame unwound.
        """
        from tentacle import Tcl

        retired = Tcl.prepare_reload("maya")

        def rebuild():
            from tentacle import Tcl as ReloadedTcl

            try:
                ReloadedTcl.launch()
            finally:
                Tcl.dispose_retired(retired)
            return None

        try:
            reloaded = Tcl.reload_packages("maya")
        except Exception as error:
            # The teardown above already retired the menu, so returning here would
            # strand the session with no marking menu at all — a worse place than
            # the stale one it started from. Rebuild from whatever is loaded.
            print(f"# Error: tentacle: reload failed: {error} #")
            executeDeferred(rebuild)
            self._report(f"Tentacle reload FAILED: {html.escape(str(error))}")
            return

        executeDeferred(rebuild)

        # reload_packages already NAMED each failure on the console; the user-facing
        # line only has to say that the reload was partial. Tolerant access: an
        # older pythontk returns a plain list rather than a ReloadReport.
        failed = getattr(reloaded, "failed", ())
        if failed:
            self._report(
                f"Tentacle reloaded {len(reloaded)} modules, "
                f"{len(failed)} FAILED (see the script editor)."
            )
        else:
            self._report(f"Tentacle reloaded ({len(reloaded)} modules).")

    @staticmethod
    def _report(message):
        """Report through MAYA, not through the panel that is being torn down.

        A ``message_box`` here would render on the switchboard this reload has
        just retired, i.e. a widget tree built by the previous generation of the
        code — exactly the stale-Qt interaction the deferral above exists to
        avoid.
        """
        try:
            cmds.inViewMessage(amg=message, pos="topCenter", fade=True)
        except Exception:  # no viewport (batch) — the console still gets it
            pass
        print(f"# Result: {message} #")


# -------------------------------------------------------------------------------------------

# module name
# print(__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
