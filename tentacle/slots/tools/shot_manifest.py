# !/usr/bin/python
# coding=utf-8
"""Shot Manifest: a shot sheet checked against the scene, and the shots built from it.

One Slots class for both hosts: the ``.ui``'s widgets routed to the controller
(:class:`~tentacle.slots.tools._shot_manifest.controller.ShotManifestController`),
which reaches the host through the host library's ``ManifestHost``
(``self.tk``). The manifest engine is pythontk's.
"""

from tentacle import Slots
from tentacle.slots.tools._shot_manifest.controller import ShotManifestController


class ShotManifestSlots(Slots):
    """Switchboard slots for the ``shot_manifest.ui`` panel."""

    def __init__(self, switchboard):
        super().__init__(switchboard)
        self.ui = self.sb.loaded_ui.shot_manifest
        self.controller = ShotManifestController(self)

    # ---- header ----------------------------------------------------------

    def header_init(self, widget):
        """Header menu is configured once in the controller's ``__init__``."""

    def btn_settings(self):
        """Open the shared shots settings panel."""
        self.sb.handlers.marking_menu.show("shots")

    # ---- buttons ---------------------------------------------------------

    def b002(self):
        """Assess the steps against the scene."""
        self.controller.assess()

    def b003(self):
        """Build shots from loaded steps (or auto-detect from scene)."""
        self.controller.build()

    def b004(self):
        """Export the manifest's rows (the option menu says how)."""
        self.controller.export()
