# !/usr/bin/python
# coding=utf-8
"""Exploded View: spread the selected objects apart to inspect interior parts.

One Slots class for both hosts over the host toolkit's ``ExplodedView``
(``self.tk``), which works on the selection.
"""

from tentacle import Slots


class ExplodedViewSlots(Slots):
    def __init__(self, switchboard):
        super().__init__(switchboard)
        self.ui = self.sb.loaded_ui.exploded_view
        self.engine = self.tk.ExplodedView()

    def header_init(self, widget):
        """Configure header help text."""
        # Gesture-scoped window: pin button + auto-hide on key_show release.
        widget.config_buttons("menu", "collapse", "pin")
        widget.set_help_text(
            self.sb.tooltip.fmt(
                title="Exploded View",
                body="Spread selected objects outward from their shared "
                "center to inspect interior parts. Each object's original "
                "position is stored on it, so the explode is fully reversible.",
                sections=[
                    (
                        "Actions",
                        [
                            "<b>Explode</b> — push the selected objects apart from "
                            "the group's center (a selected group explodes its "
                            "children).",
                            "<b>Un-Explode</b> — return selected objects to their "
                            "stored positions.",
                            "<b>Un-Explode All</b> — reset every exploded object "
                            "in the scene (regardless of selection).",
                            "<b>Toggle Explode</b> — alternate between exploded "
                            "and original views on the current selection.",
                        ],
                    ),
                ],
            )
        )

    def b000(self):
        """Explode."""
        self.engine.explode()

    def b001(self):
        """Un-Explode (selected)."""
        self.engine.un_explode()

    def b002(self):
        """Un-Explode All."""
        self.engine.un_explode_all()

    def b003(self):
        """Toggle Explode."""
        self.engine.toggle_explode()
