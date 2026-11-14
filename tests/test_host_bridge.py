#!/usr/bin/python
# coding=utf-8
"""The bridge panels' shared base, ``HostBridge`` (``slots/tools/_app_bridge/``).

uitk's ``ParamPanelSlots`` over the host toolkit: a bridge panel names its engine
(``self.tk.<X>Bridge``) and gets its registry, templates, modes and preset folder
off it, the Scope through the host's ``BridgeHost`` (``resolve_scope`` /
``scope_closure``), the optional-package install where the host imports, and the
Bake Source row over ``BakeSourceSet``. A fake toolkit stands in for ``mtk`` /
``btk`` and records what the base asks of it; the cases run the base's own methods
on a probe panel that was never built (``__new__``: the bridge base is a plain
class, not a ``QObject``), with only the attributes those methods read. In Maya
the same methods drive the real ``mtk`` on a real scene. Each bridge panel's own
additions are its ``test_<bridge>_panel.py``'s; ``BridgeHost``'s scope precedence
is mayatk's ``mock_tests/test_bridge_host_scope.py``.
"""

import types
import unittest
from pathlib import Path
from unittest import mock

from _host import MAYA_AVAILABLE, maya_module
from tentacle.slots._slots import Slots
from tentacle.slots.tools._app_bridge.host_bridge import HostBridge


# ---------------------------------------------------------------------------
# The fake toolkit
# ---------------------------------------------------------------------------


class _Log:
    """A bridge logger that keeps what it was told, by level."""

    def __init__(self):
        self.records = []

    def __getattr__(self, level):  # info / warning / error / the redirect hooks
        if level.startswith("__"):
            raise AttributeError(level)
        return lambda msg="", *a, **k: self.records.append((level, str(msg)))

    def said(self, level):
        return [msg for lvl, msg in self.records if lvl == level]


class _BakeRegistry:
    """A bake bridge's registry: it declares the Bake Source row."""

    PARAMS = {"SCOPE": None, "BAKE_SOURCE_SET": None}


class _PlainRegistry:
    """A bridge registry without the Bake Source row."""

    PARAMS = {"SCOPE": None}


class _ProbeBridge:
    """The engine surface the base reads."""

    TEMPLATE_DIR = "templates"

    def __init__(self):
        self.logger = _Log()

    @classmethod
    def params_registry(cls):
        return _BakeRegistry

    @staticmethod
    def list_template_modes():
        return [("bake", "send_to")]


class _PlainBridge(_ProbeBridge):
    @classmethod
    def params_registry(cls):
        return _PlainRegistry


def _toolkit(name="mayatk"):
    """``mtk`` / ``btk`` as the bridge panels reach them: by name, nothing else."""
    bake_set = mock.MagicMock(name="BakeSourceSet")
    bake_set.SET_NAME = "bakeBridge_source"
    return types.SimpleNamespace(
        __name__=name,
        ProbeBridge=_ProbeBridge,
        PlainBridge=_PlainBridge,
        BridgeHost=mock.MagicMock(name="BridgeHost"),
        BakeSourceSet=bake_set,
    )


class _ProbeBridgeSlots(HostBridge):
    """A bridge's panel as it plugs in: a name, an engine, a send."""

    UI_NAME = "probe_bridge"

    @property
    def bridge_class(self):
        return self.tk.ProbeBridge

    def b000(self):
        pass


class _PlainBridgeSlots(_ProbeBridgeSlots):
    @property
    def bridge_class(self):
        return self.tk.PlainBridge


def _stub(cls=_ProbeBridgeSlots, tk=None):
    """A *cls* panel never built, over the attributes its methods read."""
    slots = cls.__new__(cls)
    slots.sb = mock.MagicMock(name="switchboard")
    slots.sb.tk = tk or _toolkit()
    slots._bridge = _ProbeBridge()
    slots._output_dir_edit = None
    slots._refresh_param_enablement = mock.MagicMock(name="_refresh_param_enablement")
    return slots


def _scoped(slots, objects):
    """The host resolves the Scope to *objects*; a Maya closure ships them as-is."""
    host = slots.tk.BridgeHost
    host.resolve_scope.return_value = list(objects)
    host.scope_closure.side_effect = lambda found, params: list(found)
    return host


# ---------------------------------------------------------------------------
# The base's shape and its engine
# ---------------------------------------------------------------------------


class TestHostBridgeShape(unittest.TestCase):
    def test_the_base_is_uitks_panel_with_slots_own_tk(self):
        """uitk's bridge base with ``Slots``' own ``tk`` -- the same property, and
        no ``QObject`` (``ParamPanelSlots.__init__`` never chains to one)."""
        self.assertTrue(issubclass(HostBridge, Slots.ParamPanelSlots))
        self.assertIs(vars(HostBridge)["tk"], vars(Slots)["tk"])
        qobject = Slots.__mro__[1]
        self.assertFalse(issubclass(HostBridge, qobject))


class TestHostBridgeDefaults(unittest.TestCase):
    def test_a_bridge_reads_its_registry_templates_and_modes_off_its_engine(self):
        probe = _stub()
        self.assertIs(probe.params_module, _BakeRegistry)
        self.assertEqual(probe.template_dir, "templates")
        self.assertEqual(probe.list_template_modes(), [("bake", "send_to")])
        self.assertIsInstance(probe.make_bridge(), _ProbeBridge)
        self.assertEqual(probe.PRESETS_ROOT, Path("mayatk") / "probe_bridge")

    def test_the_panel_resolves_templates_where_its_engine_does(self):
        """A user tier is the engine's: the panel reads the folders it runs from."""
        self.assertEqual(_stub().template_dirs, (Path("templates"),), "no tier: its one folder")
        tiered = (Path("mine"), Path("templates"))
        with mock.patch.object(_ProbeBridge, "template_dirs", staticmethod(lambda: tiered), create=True):
            self.assertEqual(_stub().template_dirs, tiered)
            self.assertEqual(_stub().user_scripts_dir, Path("mine"))

    def test_presets_stay_in_each_hosts_folder(self):
        """Where each host's panel kept them: saved user presets."""
        for name in ("mayatk", "blendertk"):
            with self.subTest(host=name):
                root = _stub(tk=_toolkit(name)).PRESETS_ROOT
                self.assertEqual(root, Path(name) / "probe_bridge")

    def test_a_panel_must_name_its_engine(self):
        bare = HostBridge.__new__(HostBridge)
        with self.assertRaises(NotImplementedError):
            bare.bridge_class  # noqa: B018 - the property is the assertion


# ---------------------------------------------------------------------------
# What the base asks of its host
# ---------------------------------------------------------------------------


class TestHostBridgeAsksItsHost(unittest.TestCase):
    def test_the_scope_resolves_through_the_host_with_the_engine(self):
        slots = _stub()
        _scoped(slots, ["|pCube1"])
        self.assertEqual(slots.resolve_scope_objects("visible"), ["|pCube1"])
        slots.tk.BridgeHost.resolve_scope.assert_called_once_with(
            "visible", slots._bridge
        )

    def test_without_an_engine_the_scope_resolves_without_one(self):
        """Entire Scene then falls back to the scene's meshes (the host's rule)."""
        slots = _stub()
        slots._bridge = None
        _scoped(slots, ["|mesh"])
        with mock.patch.object(_ProbeBridgeSlots, "make_bridge", return_value=None):
            slots.resolve_scope_objects("all")
        slots.tk.BridgeHost.resolve_scope.assert_called_once_with("all", None)

    def test_the_host_closes_a_scope_over_what_ships(self):
        slots = _stub()
        host = slots.tk.BridgeHost
        host.resolve_scope.return_value = ["|grp"]
        host.scope_closure.return_value = ["|grp", "|grp|child"]
        params = {"SCOPE": "all"}
        self.assertEqual(slots.scoped_objects(params), ["|grp", "|grp|child"])
        host.scope_closure.assert_called_once_with(["|grp"], params)

    def test_an_empty_scope_is_reported_not_closed(self):
        slots = _stub()
        _scoped(slots, [])
        self.assertEqual(slots.scoped_objects({"SCOPE": "visible"}), [])
        slots.tk.BridgeHost.scope_closure.assert_not_called()
        self.assertEqual(
            slots._bridge.logger.said("warning"),
            ["No visible mesh geometry to export."],
        )

    def test_an_optional_package_installs_where_the_host_imports(self):
        slots = _stub()
        slots._install_optional_package("some-package>=1.0")
        slots.tk.BridgeHost.install_package.assert_called_once_with(
            "some-package>=1.0"
        )


# ---------------------------------------------------------------------------
# The Bake Source row
# ---------------------------------------------------------------------------


class TestHostBridgeBakeSource(unittest.TestCase):
    """The Bake Source row's three buttons and its live member list, once for
    every bake bridge, over the host's ``BakeSourceSet``."""

    def setUp(self):
        self.probe = _stub()
        self.bake_set = self.probe.tk.BakeSourceSet
        self.log = self.probe._bridge.logger

    def test_the_row_lists_the_sets_members_live(self):
        self.bake_set.member_names.return_value = ["source_mesh"]
        provider = self.probe.live_param_tooltip_blocks()["BAKE_SOURCE_SET"]
        self.assertIn("source_mesh", provider())
        self.bake_set.member_names.return_value = ["other_mesh"]
        self.assertIn("other_mesh", provider())  # read on each hover

    def test_only_a_bridge_with_the_row_lists_it(self):
        self.assertNotIn(
            "BAKE_SOURCE_SET", _stub(_PlainBridgeSlots).live_param_tooltip_blocks()
        )

    def test_the_member_list_never_raises_into_qt(self):
        self.bake_set.member_names.side_effect = RuntimeError("no scene")
        self.assertEqual(self.probe._bake_source_tooltip(), "")

    def test_set_from_selection_defines_the_set(self):
        self.bake_set.define.return_value = ["|a", "|b"]
        self.probe.set_bake_source_from_selection()
        self.bake_set.define.assert_called_once_with()
        self.probe._refresh_param_enablement.assert_called_once_with()
        self.assertEqual(
            self.log.said("info"),
            [
                "Bake Source set: 2 object(s) -> bakeBridge_source. "
                "Sends now ship it as the companion bake source."
            ],
        )

    def test_a_bridge_says_what_the_set_means_for_its_sends(self):
        self.probe.BAKE_SOURCE_DEFINED_NOTE = (
            "Bake sends now export it as the bake source."
        )
        self.bake_set.define.return_value = ["|a"]
        self.probe.set_bake_source_from_selection()
        self.assertTrue(
            self.log.said("info")[0].endswith("export it as the bake source.")
        )

    def test_set_from_nothing_clears_and_says_so(self):
        self.bake_set.define.return_value = []
        self.probe.set_bake_source_from_selection()
        self.assertEqual(
            self.log.said("warning"),
            ["Nothing selected; the bake-source set was cleared."],
        )

    def test_select_counts_what_the_host_could_not_select(self):
        self.bake_set.members.return_value = ["a", "b", "c"]
        self.bake_set.select.return_value = ["a", "b"]
        self.probe.select_bake_source()
        self.assertEqual(
            self.log.said("info"),
            [
                "Selected 2 bake-source object(s). 1 could not be selected (hidden, "
                "or not selectable here); they still export."
            ],
        )

    def test_select_of_every_member_says_only_that(self):
        self.bake_set.members.return_value = ["a"]
        self.bake_set.select.return_value = ["a"]
        self.probe.select_bake_source()
        self.assertEqual(self.log.said("info"), ["Selected 1 bake-source object(s)."])

    def test_select_without_a_set_selects_nothing(self):
        self.bake_set.members.return_value = []
        self.probe.select_bake_source()
        self.bake_set.select.assert_not_called()
        self.assertEqual(self.log.said("warning"), ["No bake-source set is defined."])

    def test_clear_removes_the_set_and_says_what_follows(self):
        self.bake_set.exists.return_value = True
        self.probe.BAKE_SOURCE_CLEARED_NOTE = "Pairing falls back to the suffixes."
        self.probe.clear_bake_source()
        self.bake_set.clear.assert_called_once_with()
        self.assertEqual(
            self.log.said("info"),
            ["Bake-source set cleared. Pairing falls back to the suffixes."],
        )

    def test_clear_without_a_set_touches_nothing(self):
        self.bake_set.exists.return_value = False
        self.probe.clear_bake_source()
        self.bake_set.clear.assert_not_called()
        self.assertEqual(self.log.said("warning"), ["No bake-source set is defined."])


# ---------------------------------------------------------------------------
# In Maya: the real mtk
# ---------------------------------------------------------------------------


@unittest.skipUnless(MAYA_AVAILABLE, "drives the real mtk; runs in a fresh Maya")
class TestHostBridgeInMaya(unittest.TestCase):
    """The base's host calls against the real ``mtk`` on a real scene. Built with
    ``__new__`` like the unit cases: a panel's ``__init__`` builds Qt rows, which a
    batch mayapy cannot host (``_host.qt_widgets_available``). The engine is the
    real ``mtk.UnityBridge``: a whole-scene hook (``_scene_objects``) needing no
    optional package."""

    def setUp(self):
        self.cmds = maya_module("maya.cmds")
        self.mtk = maya_module("mayatk")
        self.cmds.file(new=True, force=True)
        self.addCleanup(self.cmds.file, new=True, force=True)

    def _panel(self, engine=False):
        slots = _stub(tk=self.mtk)
        slots._bridge = self.mtk.UnityBridge() if engine else None
        if not engine:
            slots.make_bridge = lambda: None
        return slots

    def _long(self, node):
        return self.cmds.ls(node, long=True)[0]

    def test_scope_selected_ships_the_selection_as_is(self):
        """Maya's export-selection writes a group's subtree: no closure needed."""
        cmds = self.cmds
        group = cmds.group(cmds.polyCube(name="hostSelCube")[0], name="hostSelGroup")
        cmds.polySphere(name="hostOtherSphere")
        cmds.select(group, replace=True)
        resolved = self._panel().scoped_objects({"SCOPE": "selected"})
        self.assertEqual(resolved, [self._long(group)])

    def test_an_unknown_scope_never_widens(self):
        self.cmds.polyCube()
        self.cmds.select(clear=True)
        self.assertEqual(self._panel().resolve_scope_objects("bogus"), [])

    def test_entire_scene_returns_roots_so_the_hierarchy_travels(self):
        cmds = self.cmds
        group = cmds.group(cmds.polyCube(name="hostRootCube")[0], name="hostRootGroup")
        cmds.select(clear=True)
        resolved = self._panel(engine=True).resolve_scope_objects("all")
        self.assertIn(self._long(group), resolved)

    def test_entire_scene_without_an_engine_falls_back_to_the_meshes(self):
        self.cmds.polyCube(name="hostFallbackCube")
        self.cmds.select(clear=True)
        resolved = self._panel().resolve_scope_objects("all")
        self.assertTrue(resolved)
        self.assertTrue(
            all(self.cmds.objectType(o) == "mesh" for o in resolved), resolved
        )

    def test_visible_only_leaves_the_hidden_out(self):
        cmds = self.cmds
        cmds.polyCube(name="hostVisibleCube")
        hidden = cmds.polyCube(name="hostHiddenCube")[0]
        cmds.setAttr(f"{hidden}.visibility", 0)
        cmds.select(clear=True)
        resolved = [str(o) for o in self._panel().resolve_scope_objects("visible")]
        self.assertTrue(any("hostVisibleCube" in o for o in resolved), resolved)
        self.assertFalse(any("hostHiddenCube" in o for o in resolved), resolved)

    def test_the_bake_source_row_drives_the_scene_set(self):
        cmds, bake_set = self.cmds, self.mtk.BakeSourceSet
        cube = self._long(cmds.polyCube(name="hostBakeSource")[0])
        cmds.setAttr(f"{cube}.visibility", 0)  # a hidden member still selects in Maya
        slots = self._panel()
        slots._bridge = _ProbeBridge()  # the log the row's buttons report to
        cmds.select(cube, replace=True)
        slots.set_bake_source_from_selection()
        self.assertTrue(bake_set.exists())
        self.assertIn("hostBakeSource", slots._bake_source_tooltip())
        cmds.select(clear=True)
        slots.select_bake_source()
        self.assertEqual(cmds.ls(selection=True, long=True), [cube])
        self.assertIn(
            "Selected 1 bake-source object(s).", slots._bridge.logger.said("info")
        )
        slots.clear_bake_source()
        self.assertFalse(bake_set.exists())
        self.assertTrue(cmds.objExists(cube))


if __name__ == "__main__":
    unittest.main()
