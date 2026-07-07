"""Tentacle-side standalone-UI bench (mayatk hierarchy_manager etc.).

Subclass of :class:`bench.standalone_ui_init.StandaloneUiInitBench`
that drives the **real** path users hit when they open a mayatk tool
window from a tentacle slot:

1.  ``TclMaya`` is constructed (registers tentacle UIs + slots and,
    via the bundled ``MayaUiHandler``, mayatk's UIs + slots onto the
    same :class:`Switchboard`).
2.  The user's slot calls ``sb.handlers.ui.show("hierarchy_manager")``
    (or similar), which under the hood is just ``sb.get_ui(name)``
    + ``ui.show()``.

Phase ``02_construct`` therefore measures the bundled
``TclMaya + MayaUiHandler + register-everything`` cost (~2 s on a
fresh Maya).  Phases 03-08 isolate the per-UI cost the user actually
feels when they first open *this* tool.

Runs inside a fresh Maya launched by ``run_in_maya`` (sibling file).

Run from the repo root, one fresh Maya per UI::

    python tentacle/test/bench/run_in_maya.py \\
        standalone_ui:TentacleStandaloneUiBench \\
        --ui hierarchy_manager --label hier --samples 1

    python tentacle/test/bench/run_in_maya.py \\
        standalone_ui:TentacleStandaloneUiBench \\
        --ui color_id --label color --samples 1

    python tentacle/test/bench/run_in_maya.py \\
        standalone_ui:TentacleStandaloneUiBench \\
        --ui naming --label naming --samples 1
"""

from __future__ import annotations

from bench.standalone_ui_init import StandaloneUiInitBench


class TentacleStandaloneUiBench(StandaloneUiInitBench):
    #: Default mayatk UI to load.  Override per run via ``--ui``.
    UI_NAME = "hierarchy_manager"

    def setup_switchboard(self):
        # Imports happen inside the method so this module can be
        # imported outside Maya (e.g. for static analysis) without
        # exploding on ``import maya.cmds``.
        from tentacle.tcl_maya import TclMaya

        # ``TclMaya.__init__`` builds its own ``Switchboard`` and
        # registers tentacle UIs + slots; the bundled ``MayaUiHandler``
        # then registers mayatk UIs (hierarchy_manager, color_id,
        # naming, etc.) onto the *same* switchboard.  We retain a
        # reference so the marking menu doesn't get garbage-collected
        # mid-bench.
        self._mm = TclMaya(log_level="WARNING")
        return self._mm.sb
