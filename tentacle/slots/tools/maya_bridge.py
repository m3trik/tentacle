# !/usr/bin/python
# coding=utf-8
"""Maya Bridge: send the selection to a fresh Maya through an import template.

A Blender tool (``tentacle.slots.tools.HOSTS``). Each library ships the cross-DCC
bridge named after its TARGET app: blendertk's ``MayaBridge`` sends to Maya, and
mayatk's ``BlenderBridge`` sends back (tentacle's Blender Bridge, a Maya tool).
On the bridge panels' shared base (:class:`HostBridge`: parameter rows, presets,
log pane, Scope); the engine is ``self.tk.MayaBridge``, and its parameter
registry, template folder and ``(template, mode)`` list are the engine's.

``REQUIRE_OUTPUT_DIR = False``: a send goes through a temp FBX the engine
manages, so there is no artifact to point the panel at.
"""

import traceback

from ._app_bridge.host_bridge import HostBridge


class MayaBridgeSlots(HostBridge):
    UI_NAME = "maya_bridge"
    LOG_TAG = "maya_bridge"
    REQUIRE_OUTPUT_DIR = False

    # The base's default header menu (Clear Log; the combo carries Refresh /
    # Open Templates Folder); only the help differs, so it is declared as data.
    HELP_SPEC = {
        "title": "Maya Bridge",
        "body": "Send the selected objects to a fresh Maya. Blender exports the selection as "
        "FBX; Maya runs the chosen import template with your parameter values substituted in.",
        "steps": [
            "Select one or more objects.",
            "Toggle the import options (clear scene, frame in view, materials, …).",
            "Click <b>Send to Maya</b>.",
        ],
        "sections": [
            (
                "Options",
                [
                    "<b>Clear Scene First</b> — open a new Maya scene before importing (clean slate). "
                    "Off imports additively.",
                    "<b>Frame in View</b> — after import, select &amp; frame the new objects (viewFit).",
                ],
            ),
        ],
        "notes": [
            "One <b>import</b> template ships, exposing every option above; the dropdown also "
            "picks up custom templates you drop into the templates folder (use "
            "<code>__KEY__</code> tokens from <i>parameters.py</i>), then click "
            "<b>Refresh Templates</b>.",
            "A fresh Maya is launched every time; your running Maya is never touched.",
        ],
    }

    # ------------------------------------------------------------------ engine
    @property
    def bridge_class(self):
        return self.tk.MayaBridge

    # ------------------------------------------------------------- b000: send
    def b000(self):
        """Send the selected objects to Maya with the chosen template."""
        # The base logs the scope-aware reason when the Scope is empty.
        params = self.collect_param_values()
        selection = self.scoped_objects(params)
        if not selection:
            return

        pair = self._selected_template_mode()
        if not pair:
            self.bridge.logger.warning(
                "No template chosen. Pick one from the dropdown above."
            )
            return
        template, mode = pair

        if not self.bridge.app_path:
            self.bridge.logger.error(self.bridge.app_spec.not_found_message)
            return

        self.bridge.logger.info(
            f"--- {template} ({mode}) on {len(selection)} object(s) ---"
        )
        try:
            self.bridge.send(
                objects=selection,
                template=template,
                mode=mode,
                params=params,
            )
        except Exception:
            self.bridge.logger.error("Bridge raised:\n" + traceback.format_exc())
