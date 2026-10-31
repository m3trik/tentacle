# !/usr/bin/python
# coding=utf-8
"""Tests for the standalone Unity Workflow panel (``slots/tools/unity_workflow.py``).

The panel is a file-driven :class:`uitk.bridge.BridgeSlotsBase` (the DCC-agnostic
sibling of the Unity Bridge panel): pick a model file -> copy it into a
Unity project's ``Assets/`` via :class:`unitytk.FileToUnityBridge`. Build-time wiring
(param widgets, Model File + Unity Project rows, the single delivery mode), the
``set_model_path`` host hand-off, and b000 dispatch are exercised against the real
panel under the offscreen QPA without launching Unity.
"""

from __future__ import annotations

import importlib.util
import os
import shutil
import sys
import tempfile
import types
import unittest
from unittest import mock

from qtpy.QtWidgets import QApplication

from uitk.testing import TestSandbox

# A direct `python test/test_unity_workflow_panel.py` loads no conftest, so the sandbox is
# activated here too -- before the first QSettings, or tearDown's
# store.clear() would wipe the developer's live panel state. Idempotent.
TestSandbox.activate()


#: The panel's optional engine (installed on demand by Manage Unity Scripts).
UNITYTK = importlib.util.find_spec("unitytk") is not None
NO_UNITYTK = "unitytk is not installed (the panel installs it on demand)"


def _ensure_app() -> QApplication:
    return QApplication.instance() or QApplication(sys.argv)


class TestUnityWorkflowParameters(unittest.TestCase):
    def _P(self):
        from tentacle.slots.tools._unity_workflow import parameters as P

        return P

    def test_defaults_are_unity_side_only(self) -> None:
        P = self._P()
        self.assertEqual(
            set(P.Parameters.defaults()),
            {
                "ASSETS_SUBDIR",
                "ASSET_NAME",
                "LAUNCH_MODE",
                "UNITY_VERSION",
                # Manage Unity Scripts mode's script checklist + action combo —
                # Unity-side too (they manage the embedded unitytk package in
                # the project).
                "SCRIPTS",
                "SCRIPTS_ACTION",
            },
        )
        # No DCC export knobs (this panel takes an already-exported file).
        for export_key in (
            "SCOPE",
            "TRIANGULATE",
            "EMBED_TEXTURES",
            "INCLUDE_MATERIALS",
        ):
            self.assertNotIn(export_key, P.PARAMS)

    def test_referenced_keys_is_token_based(self) -> None:
        # referenced_keys is the generic __KEY__ token scan; with no tokens in
        # the text it finds nothing (the panel drives visibility explicitly
        # from _relevant_param_keys() instead — see the panel-load test).
        P = self._P()
        self.assertEqual(P.Parameters.referenced_keys("plain text"), set())
        self.assertEqual(
            P.Parameters.referenced_keys("uses __ASSET_NAME__"), {"ASSET_NAME"}
        )


class TestUnityWorkflowPanelLoads(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = _ensure_app()

    def setUp(self) -> None:
        from tentacle.tcl_standalone import UnityWorkflowUI

        self.ui = UnityWorkflowUI()
        self.slots = self.ui.sb.get_slots_instance(self.ui)
        self.assertIsNotNone(self.slots, "Switchboard returned no slots instance")

    def tearDown(self) -> None:
        store = self.ui.settings
        self.ui.deleteLater()
        self.app.processEvents()
        # Rows persist and the sandboxed store outlives the case: cleared once
        # the panel is gone, so the next case's fresh panel opens on defaults.
        store.clear()
        store.sync()

    def test_param_widgets_built_for_every_spec(self) -> None:
        from tentacle.slots.tools._unity_workflow import parameters as P

        for key in P.PARAMS:
            self.assertIn(key, self.slots._param_widgets, f"no widget for {key}")

    def test_model_and_project_rows_exist(self) -> None:
        self.assertIsNotNone(self.slots._model_edit, "Model File row not built")
        self.assertIsNotNone(self.slots._output_dir_edit, "Unity Project row not built")

    def test_delivery_combo_shows_friendly_label(self) -> None:
        self.assertGreaterEqual(self.ui.cmb000.findText("Copy to Project"), 0)

    def test_copy_mode_shows_every_delivery_param(self) -> None:
        # Copy-to-assets shows every delivery param and hides the script
        # checklist + action combo that only Manage Unity Scripts uses.
        from tentacle.slots.tools._unity_workflow import parameters as P

        self.assertEqual(
            self.slots._relevant_param_keys(),
            set(P.PARAMS) - {"SCRIPTS", "SCRIPTS_ACTION"},
        )

    def test_manage_mode_shows_only_the_script_params(self) -> None:
        # The other half of the same gate: delivery params hide in manage mode.
        with mock.patch.object(
            self.slots,
            "_selected_template_mode",
            return_value=(self.slots.MODE_MANAGE, None),
        ):
            self.assertEqual(
                self.slots._relevant_param_keys(), {"SCRIPTS", "SCRIPTS_ACTION"}
            )

    @unittest.skipUnless(UNITYTK, NO_UNITYTK)
    def test_script_checklist_populates_from_unitytk(self) -> None:
        """One checked row per optional unitytk component — discovered from
        the installed release, not hard-coded in the panel (core is implicit:
        it rides along with every install)."""
        from unitytk import TemplateDeployer

        expected = [c for c in TemplateDeployer.components() if not c.required]
        lw = self.slots._param_widgets["SCRIPTS"]
        self.assertEqual(
            [lw.item(i).text() for i in range(lw.count())],
            [c.label for c in expected],
        )
        self.assertNotIn("Core", [lw.item(i).text() for i in range(lw.count())])
        # All checked by default == the historical full-set deploy.
        self.assertEqual(self.slots._script_selection(), [c.key for c in expected])

    @unittest.skipUnless(UNITYTK, NO_UNITYTK)
    def test_action_runs_over_the_checked_scripts_only(self) -> None:
        """The action is applied to the checked components — the panel hands
        that selection straight to the engine."""
        keys = [c.key for c in self.slots._script_components]
        self.slots._write_param("SCRIPTS", keys[:1])
        self.slots._output_dir_edit.setText("C:/proj/MyUnityProject")
        with mock.patch("unitytk.TemplateDeployer.run_action", return_value=[]) as run:
            self.slots._manage_unity_scripts("install")
        run.assert_called_once_with("C:/proj/MyUnityProject", "install", keys[:1])

    def test_set_model_path_prefills_field(self) -> None:
        self.slots.set_model_path("C:/scan/robot.fbx")
        self.assertEqual(self.slots.resolved_model_path(), "C:/scan/robot.fbx")


@unittest.skipUnless(UNITYTK, NO_UNITYTK)
class TestUnityWorkflowVersionPopulate(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = _ensure_app()

    def test_unity_version_combo_appends_installed_newest_first(self) -> None:
        from tentacle.tcl_standalone import UnityWorkflowUI

        editors = {
            "2021.3.1f1": "C:/U/2021/Unity.exe",
            "6000.0.5f1": "C:/U/6000/Unity.exe",
        }
        with mock.patch("unitytk.UnityFinder.find_editors", return_value=editors):
            ui = UnityWorkflowUI()
        try:
            slots = ui.sb.get_slots_instance(ui)
            cmb = slots._param_widgets["UNITY_VERSION"]
            texts = [cmb.itemText(i) for i in range(cmb.count())]
            self.assertEqual(texts[0], "Auto (newest)")
            # Discovered versions appended newest-first after the auto default.
            self.assertEqual(texts[1:], ["6000.0.5f1", "2021.3.1f1"])
        finally:
            ui.deleteLater()
            self.app.processEvents()


class TestTheUnityPanelsShareOneMixin(unittest.TestCase):
    """Both Unity panels take ``UnityPanelMixin`` from one module, as their FIRST
    base: listed after ``BridgeSlotsBase``, the mixin's ``template_dir`` /
    ``TEMPLATE_MENU`` / ``default_output_dir`` would lose the MRO, silently."""

    def test_each_panel_lists_the_mixin_first(self) -> None:
        from tentacle.slots.tools._unity_bridge._unity_panel import UnityPanelMixin
        from tentacle.slots.tools.unity_bridge import UnityBridgeSlots
        from tentacle.slots.tools.unity_workflow import UnityWorkflowSlots

        for cls in (UnityBridgeSlots, UnityWorkflowSlots):
            with self.subTest(panel=cls.__name__):
                self.assertIs(cls.__bases__[0], UnityPanelMixin)


@unittest.skipUnless(UNITYTK, NO_UNITYTK)
class TestUnityWorkflowVersionOrder(unittest.TestCase):
    def test_unity_version_combo_orders_same_major_numerically(self) -> None:
        """`_populate_unity_versions` must list editors newest-first *numerically*.

        A lexicographic sort ranks 2020.3.9f1 above 2020.3.10f1 (because '9' > '1'
        at the differing char), inverting the documented 'newest first' order for
        same-major versions. The fix routes ordering through
        UnityFinder.version_sort_key. Exercised against a stub `self` so no live
        Unity / full Qt UI construction is needed.
        """
        from tentacle.slots.tools.unity_workflow import UnityWorkflowSlots

        class _FakeCombo:
            def __init__(self):
                self.items = []

            def addItem(self, text, data):
                self.items.append(text)

        combo = _FakeCombo()
        # Older patch (2020.3.9f1) must end up BELOW the newer 2020.3.10f1 despite
        # sorting higher lexicographically.
        editors = {
            "2020.3.9f1": "C:/U/2020.3.9f1/Unity.exe",
            "2020.3.10f1": "C:/U/2020.3.10f1/Unity.exe",
        }
        stub = types.SimpleNamespace(_param_widgets={"UNITY_VERSION": combo})
        with mock.patch("unitytk.UnityFinder.find_editors", lambda: editors):
            UnityWorkflowSlots._populate_unity_versions(stub)

        self.assertEqual(combo.items, ["2020.3.10f1", "2020.3.9f1"])


@unittest.skipUnless(UNITYTK, NO_UNITYTK)  # stubs the engine's send
class TestUnityWorkflowDispatch(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = _ensure_app()

    def setUp(self) -> None:
        from tentacle.tcl_standalone import UnityWorkflowUI

        self.tmp = tempfile.mkdtemp(prefix="unity_workflow_")
        self.project = os.path.join(self.tmp, "Proj")
        os.makedirs(os.path.join(self.project, "Assets"))
        self.model = os.path.join(self.tmp, "robot.fbx")
        with open(self.model, "wb") as fh:
            fh.write(b"FBX")
        self.ui = UnityWorkflowUI()
        self.slots = self.ui.sb.get_slots_instance(self.ui)
        # Stub the engine's send so nothing is copied/launched; capture the call.
        self.captured: dict = {}

        def fake_send(model_path=None, template=None, mode=None, params=None):
            self.captured["model_path"] = model_path
            self.captured["project"] = self.slots.bridge.project_path
            self.captured["params"] = params
            return {"asset": "ok"}

        self.slots.bridge.send = fake_send

    def tearDown(self) -> None:
        store = self.ui.settings
        self.ui.deleteLater()
        self.app.processEvents()
        # Rows persist and the sandboxed store outlives the case: cleared once
        # the panel is gone, so the next case's fresh panel opens on defaults.
        store.clear()
        store.sync()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_b000_dispatches_with_model_and_project(self) -> None:
        self.slots.set_model_path(self.model)
        self.slots._output_dir_edit.setText(self.project)
        self.ui.b000.click()
        self.assertEqual(self.captured.get("model_path"), self.model)
        self.assertEqual(self.captured.get("project"), self.project)
        self.assertIn("ASSETS_SUBDIR", self.captured.get("params", {}))

    def test_b000_aborts_without_model(self) -> None:
        self.slots._output_dir_edit.setText(self.project)
        self.ui.b000.click()
        self.assertNotIn("model_path", self.captured)

    def test_b000_aborts_without_project(self) -> None:
        self.slots.set_model_path(self.model)
        self.slots._output_dir_edit.setText("")
        self.ui.b000.click()
        self.assertNotIn("model_path", self.captured)

    def test_b000_aborts_on_missing_model_file(self) -> None:
        self.slots.set_model_path(os.path.join(self.tmp, "gone.fbx"))
        self.slots._output_dir_edit.setText(self.project)
        self.ui.b000.click()
        self.assertNotIn("model_path", self.captured)


if __name__ == "__main__":
    unittest.main()
