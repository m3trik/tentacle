"""Tentacle-side marking-menu init bench.

Subclass of :class:`bench.marking_menu_init.MarkingMenuInitBench`
that drives the **real** tentacle entry point — :class:`TclMaya` — so
the measurement reflects what a user actually feels when the menu first
appears on F12.

``TclMaya.__init__`` builds its own :class:`Switchboard` internally
(it does not accept a ``switchboard=`` kwarg), so :meth:`setup_switchboard`
returns ``None`` and the full Switchboard + MarkingMenu cost is bundled
into ``03_marking_menu_construct``.  The base class reads ``mm.sb`` after
construction and the rest of the lifecycle phases work unchanged.

The startmenu defaults to ``hud#startmenu`` — the activation-key default
in :file:`tentacle/tcl_maya.py`.  The submenu is autodetected from the
first ``i`` button in the loaded startmenu, which mirrors what the user
hits when they hover.

Runs inside a fresh Maya launched by ``run_in_maya`` (sibling file).

Run from the repo root::

    python tentacle/test/bench/run_in_maya.py \\
        marking_menu:TentacleMarkingMenuBench \\
        --ui hud#startmenu --label baseline --samples 3
"""

from __future__ import annotations

from typing import Optional

from bench.marking_menu_init import MarkingMenuInitBench


class TentacleMarkingMenuBench(MarkingMenuInitBench):
    #: Activation-key default in :file:`tentacle/tcl_maya.py`.
    STARTMENU_UI = "hud#startmenu"

    #: ``None`` → autodetect via :meth:`find_submenu_name` (first ``i``
    #: button in the loaded startmenu).  Set explicitly to pin the bench
    #: to a specific submenu when you need cross-run comparability.
    SUBMENU_UI: Optional[str] = None

    def setup_switchboard(self):
        # ``TclMaya`` builds its own Switchboard internally — it does
        # not accept a ``switchboard=`` kwarg and does not forward
        # ``**kwargs`` to ``MarkingMenu.__init__``.  Returning ``None``
        # tells the base bench to absorb the construction cost into
        # phase 03.  The trade-off (loss of Switchboard-vs-MM split) is
        # worth it: this is the only path that mirrors the real user
        # experience byte-for-byte.
        return None

    def setup_marking_menu(self, sb):
        # Imports happen inside the method so this module can be
        # imported outside Maya (e.g. for static analysis) without
        # exploding on ``import maya.cmds``.
        from tentacle.tcl_maya import TclMaya

        # ``parent=None`` → ``TclMaya`` auto-resolves to
        # ``mtk.get_main_window()``, which matches how a user invokes
        # tentacle.  The global F12 shortcut wires up against the Maya
        # main window; cmds.quit at end-of-bench tears it down.
        return TclMaya(log_level="WARNING")
