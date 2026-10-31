# !/usr/bin/python
# coding=utf-8
"""Unity Bridge: export the selection and copy the FBX into a Unity project's Assets/.

One Slots class for both hosts, on the bridge panels' shared base
(:class:`HostBridge`: parameter rows, presets, log pane, Scope). The engine is the
host toolkit's ``UnityBridge`` (``self.tk.UnityBridge``: export through the host,
copy into ``Assets/`` through ``unitytk.CopyToAssetsDeliverer``), and its parameter
registry is the engine's. The Unity panel behavior shared with the standalone
Unity Workflow panel (``unity_workflow.py``) -- the 'Unity Project' row and its
project actions, the mode combo, the Editor combo, Manage Unity Scripts -- is
:class:`UnityPanelMixin`, in ``_unity_bridge/``. This module owns the engine pick,
the help text and the ``b000`` send.

The required 'Output Dir' row is the **Unity Project** path (the folder holding
``Assets/``), with no scene-folder fallback: a scene's folder is not a Unity
project. Unity imports what lands in ``Assets/`` on its next window focus, so an
open editor is never disturbed.

Note: *Unity Studio* is a separate paid, browser-based product (assets enter it via
Unity Cloud's Asset Manager), not this desktop FBX hand-off -- this bridge does not
target it.
"""

import traceback

from ._app_bridge.host_bridge import HostBridge
from ._unity_bridge._unity_panel import UnityPanelMixin


class UnityBridgeSlots(UnityPanelMixin, HostBridge):
    # The mixin is FIRST: its hooks (template_dir, list_template_modes, the
    # Unity Project row) override the bridge base's defaults.
    UI_NAME = "unity_bridge"
    LOG_TAG = "unity_bridge"

    OUTPUT_DIR_TOOLTIP = (
        "Path to the target Unity project -- the folder that contains the\n"
        "'Assets/' directory. The exported FBX is copied into\n"
        "Assets/<subfolder>; Unity imports it on its next window focus.\n"
        "No project yet? Create one via 'New Unity Project...' in the field's menu."
    )

    HELP_SPEC = {
        "title": "Unity Bridge",
        "body": "Export the selected objects and copy the FBX into a Unity project's "
        "<b>Assets/</b> folder. Unity imports the asset automatically on its next "
        "window focus -- no script, no fresh-instance launch, your open editor is "
        "never disturbed.",
        "steps": [
            "Set the <b>Unity Project</b> folder (or create one via the menu).",
            "Choose the <b>Scope</b> and tweak the export parameters.",
            "Click <b>Send to Unity</b>.",
        ],
        "sections": [
            (
                "Parameters",
                [
                    "<b>Scope</b> — Selected / Entire Scene / Visible Only.",
                    "<b>Assets Subfolder</b> — where under Assets/ the FBX lands.",
                    "<b>Asset Name</b> — optional; blank uses the object's name.",
                    "<b>Launch Unity</b> — after copying: <i>Don't launch</i> (Unity "
                    "imports on focus), <i>Open Editor</i> (windowed), or "
                    "<i>Headless</i> (batch import).",
                ],
            ),
        ],
        "notes": [
            "Embedded textures (default) ride inside the FBX; unitytk's import "
            "scripts extract the maps its materials and channels use (Unity's "
            "stock import binds no embedded map).",
            "Copying into Assets/ is non-destructive to a running Unity session.",
            "The <b>Manage Unity Scripts</b> template installs, updates, "
            "inspects or removes unitytk's C# import automation in the project "
            "(the embedded <i>com.m3trik.unitytk</i> package). Check the "
            "scripts to act on — one row per import channel, all on by "
            "default; the shared core files ride along with any install. "
            "Per-channel import toggles live in Unity under Edit ▸ Project "
            "Settings ▸ unitytk.",
        ],
    }

    def __init__(self, switchboard):
        super().__init__(switchboard)
        self._populate_unity_rows()  # UnityPanelMixin: Editor combo + SCRIPTS list

    # ------------------------------------------------------------------ engine
    @property
    def bridge_class(self):
        return self.tk.UnityBridge

    def make_bridge(self):
        """The engine, or ``None`` while the optional unitytk is absent.

        SILENT on purpose: this runs from ``__init__`` (the log wiring), and a
        modal raised from a constructor is parented to a window that does not
        exist yet, stranding an undismissable dialog if construction then fails.
        The panel opens either way; installing unitytk is an explicit action on
        the Manage Unity Scripts template.
        """
        if not self.optional_package_available("unitytk"):
            return None
        return super().make_bridge()

    # ------------------------------------------------------------- b000: send
    def b000(self):
        """Run the selected template: export-and-copy, or script management."""
        if self._run_manage_mode():
            return

        params = self.collect_param_values()
        # The default `scoped_objects` resolves with, so the header line always
        # names the scope the objects were actually collected under.
        scope = params.get("SCOPE", "selected")
        objects = self.scoped_objects(params)
        if not objects:
            return

        project = self.resolved_output_dir()
        if not project:
            self.bridge.logger.error(
                "Set the Unity Project folder in the field above (the one "
                "containing 'Assets/'), or create one via 'New Unity Project…'."
            )
            if self._output_dir_edit is not None:
                self._output_dir_edit.setFocus()
            return

        self.bridge.project_path = project
        self.bridge.logger.info(
            f"--- Send to Unity ({scope}) on {len(objects)} object(s) -> {project} ---"
        )
        try:
            with self.sb.progress(text="Working: Send to Unity"):
                self.bridge.send(
                    objects=objects,
                    template=self.MODE_COPY,
                    mode="",
                    params=params,
                )
        except Exception:
            self.bridge.logger.error("Bridge raised:\n" + traceback.format_exc())
