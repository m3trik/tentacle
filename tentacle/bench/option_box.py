"""Tentacle-side option_box init bench.

Subclass of :class:`uitk.bench.option_box_init.OptionBoxInitBench` that
points the Switchboard at tentacle's UI / slot sources.  The Switchboard
is constructed without a Maya parent — earlier attempts to parent it to
``mayatk.get_main_window()`` tripled ``register_children`` time without
changing the lifecycle being measured, so the bench mirrors the simpler
construction path.

Runs inside a fresh Maya launched by ``tentacle.bench.run_in_maya``.

Run from the repo root::

    python -m tentacle.bench.run_in_maya \\
        tentacle.bench.option_box:TentacleOptionBoxBench \\
        --ui edit --label baseline --samples 3
"""

from __future__ import annotations

from uitk.bench.option_box_init import OptionBoxInitBench


class TentacleOptionBoxBench(OptionBoxInitBench):
    DEFAULT_UI = "edit"

    #: UIs that have at least one ``tbXXX_init`` populating ``option_box.menu``.
    REPRESENTATIVE_UIS = (
        "edit",
        "polygons",
        "rendering",
        "selection",
        "transform",
        "uv",
    )

    def setup_switchboard(self):
        # Imports happen inside the method so this module can be imported
        # outside Maya (e.g. for static analysis) without exploding.
        import os
        import tentacle
        from uitk import Switchboard

        tentacle_root = os.path.dirname(os.path.abspath(tentacle.__file__))

        return Switchboard(
            ui_source=os.path.join(tentacle_root, "ui"),
            slot_source=os.path.join(tentacle_root, "slots", "maya"),
            base_dir=tentacle_root,
            log_level="warning",
        )

    def post_switchboard(self, sb) -> None:
        # tentacle's slot ``__init__`` chain references
        # ``self.sb.handlers.marking_menu``; the bench doesn't construct
        # the marking menu, so populate the attribute defensively.
        if not hasattr(sb.handlers, "marking_menu"):
            sb.handlers.marking_menu = None
