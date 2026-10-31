#!/usr/bin/python
# coding=utf-8
"""The standalone panels (``tentacle/tcl_standalone.py``) and their hub (``__main__.py``).

The panels are frameless uitk windows whose controls live on the uitk Header (no
native OS frame). They must behave like uitk's ``WindowPanel`` (the editor-window
reference): a clean ``Qt.Window | FramelessWindowHint`` so that, when a host's
external-app handler parents them under a DCC (e.g. Maya), they're *normal*
host-owned windows -- NOT always-on-top. A plain ``QMainWindow`` defaults to the
native title-bar decoration hints, and left set on a frameless owned window they
make it float on top of its host.

Three rosters name the family, and they are held to one another rather than to a
hand-kept list (CODE_STANDARD section 6): the entry points in ``pyproject.toml``
(how a host and the hub find a panel), ``slots.tools.STANDALONE`` (what no host
registers in its own switchboard) and the ``<Tool>UI`` classes. The runtime cases
build three panels and compare real ``windowFlags()`` with the reference -- the
only check that proves the chrome; the rest cover the whole roster cheaply.
"""

import importlib
import os
import re
import sys
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from qtpy import QtCore  # noqa: E402
from qtpy.QtWidgets import QApplication  # noqa: E402

from uitk.testing import TestSandbox  # noqa: E402

# A direct `python test/test_tcl_standalone.py` loads no conftest: the panels and
# the hub's switchboard read and write QSettings, so the sandbox is activated
# before the first one. Idempotent.
TestSandbox.activate()

from tentacle import tcl_standalone  # noqa: E402
from tentacle.slots.tools import STANDALONE  # noqa: E402
from tentacle.tcl import Tcl  # noqa: E402
from tentacle.tcl_standalone import PanelLauncher  # noqa: E402

PYPROJECT = Path(__file__).resolve().parents[1] / "pyproject.toml"
GROUP = "uitk.external_apps.in_process"

# Native title-bar decoration hints that must be cleared on a frameless window --
# the uitk Header supplies these controls instead.
_DECORATION_HINTS = (
    QtCore.Qt.WindowTitleHint
    | QtCore.Qt.WindowSystemMenuHint
    | QtCore.Qt.WindowMinimizeButtonHint
    | QtCore.Qt.WindowMaximizeButtonHint
    | QtCore.Qt.WindowCloseButtonHint
)


def _ensure_app() -> QApplication:
    return QApplication.instance() or QApplication(sys.argv)


def _table(name: str) -> dict:
    """``key = "value"`` pairs of one ``pyproject.toml`` table, by header text.

    The source file, never installed metadata: an editable install's metadata
    is only as new as its last ``pip install -e``.
    """
    text = PYPROJECT.read_text(encoding="utf-8")
    block = re.search(r"^\[%s\]\s*$(.*?)(?=^\[|\Z)" % re.escape(name), text, re.M | re.S)
    if not block:
        raise AssertionError(f"table [{name}] not found in pyproject.toml")
    return dict(re.findall(r'^\s*(\w+)\s*=\s*"([^"]+)"', block.group(1), re.M))


def _entry_points() -> dict:
    """``{panel: (module, class, extras)}`` from the entry-point table."""
    out = {}
    for name, target in _table(f'project.entry-points."{GROUP}"').items():
        module, _, rest = target.partition(":")
        cls, _, extras = rest.partition("[")
        out[name] = (module.strip(), cls.strip(), extras.rstrip("] ").strip())
    return out


def _launchers() -> dict:
    """``{class name: class}`` for every ``<Tool>UI`` the module declares."""
    return {
        name: value
        for name, value in vars(tcl_standalone).items()
        if isinstance(value, type)
        and issubclass(value, PanelLauncher)
        and value is not PanelLauncher
    }


class TestRosters(unittest.TestCase):
    """The entry points, ``STANDALONE`` and the ``<Tool>UI`` classes agree."""

    def test_the_entry_points_are_the_standalone_panels(self):
        self.assertEqual(set(_entry_points()), set(STANDALONE))

    def test_every_entry_point_names_a_launcher_here(self):
        launchers = _launchers()
        for name, (module, cls, _extras) in _entry_points().items():
            with self.subTest(panel=name):
                self.assertEqual(module, "tentacle.tcl_standalone")
                self.assertIn(cls, launchers)
        named = {cls for _module, cls, _extras in _entry_points().values()}
        self.assertEqual(named, set(launchers), "a launcher no entry point names")

    def test_each_launcher_derives_its_panel_and_slots(self):
        """``<Tool>UI`` -> the ``ui/tools`` stem its entry point is named for, and
        that tool's ``<Base>Slots`` class (the same case-blind rule)."""
        by_class = {cls: name for name, (_m, cls, _e) in _entry_points().items()}
        for cls_name, cls in sorted(_launchers().items()):
            with self.subTest(launcher=cls_name):
                tool = cls._tool()
                self.assertEqual(tool, by_class[cls_name])
                slots = cls._slots_class(tool)
                self.assertEqual(slots.__module__, f"tentacle.slots.tools.{tool}")
                self.assertTrue(slots.__name__.endswith("Slots"), slots.__name__)

    def test_maya_hides_the_panels_it_serves_with_its_own_bridges(self):
        """Substance / Marmoset stay gated out of Maya: it ships native bridges."""
        extras = {name: e for name, (_m, _c, e) in _entry_points().items()}
        for gated in ("substance_workflow", "marmoset_workflow"):
            self.assertIn("hide_maya", extras[gated])

    def test_no_host_registers_them_in_its_own_switchboard(self):
        for host in ("maya", "blender"):
            with self.subTest(host=host):
                self.assertLessEqual(set(STANDALONE), set(Tcl.unserved_tools({host})))
        self.assertEqual(Tcl.unserved_tools(None), [])  # a bare switchboard has all


class TestOneRecipe(unittest.TestCase):
    """Every panel is built by the ONE launcher recipe, which never ORs onto the
    ``QMainWindow`` defaults (``set_flags(FramelessWindowHint, ...)`` did: the
    fix once landed in three hand-written launchers and eight kept the bug)."""

    def test_no_launcher_rebuilds_the_recipe(self):
        stray = [
            name for name, cls in _launchers().items() if "__new__" in vars(cls)
        ]
        self.assertEqual(stray, [], "panels not built by PanelLauncher")

    def test_no_panel_offers_fullscreen(self):
        """Every panel is a parameter form over a log: fullscreen has nothing to
        show, and the DCC panels never offer it either."""
        offering = [
            name for name, cls in _launchers().items() if "fullscreen" in cls.HEADER_BUTTONS
        ]
        self.assertEqual(offering, [])

    def test_the_recipe_sets_the_clean_flag_set(self):
        source = Path(tcl_standalone.__file__).read_text(encoding="utf-8")
        self.assertIn("setWindowFlags(", source)
        self.assertNotIn("set_flags(FramelessWindowHint", source)


class TestWindowChrome(unittest.TestCase):
    """Built panels match the ``WindowPanel`` reference chrome."""

    PANELS = ("MetashapeWorkflowUI", "RealityScanWorkflowUI", "GaussianSplatWorkflowUI")

    @classmethod
    def setUpClass(cls) -> None:
        cls.app = _ensure_app()

    def _reference_flags(self) -> int:
        """The flag set uitk's editor windows use (WindowPanel default)."""
        from uitk.widgets.windowPanel import WindowPanel

        ref = WindowPanel(title="ref")
        flags = int(ref.windowFlags())
        ref.deleteLater()
        self.app.processEvents()
        return flags

    def _build(self, name):
        ui = getattr(tcl_standalone, name)()
        self.addCleanup(self.app.processEvents)
        self.addCleanup(ui.deleteLater)
        return ui

    def test_panels_match_windowpanel_reference(self) -> None:
        reference = self._reference_flags()
        for name in self.PANELS:
            with self.subTest(panel=name):
                flags = int(self._build(name).windowFlags())
                self.assertEqual(
                    flags,
                    reference,
                    f"{name} window flags {hex(flags)} != WindowPanel reference "
                    f"{hex(reference)} -- frameless chrome drifted.",
                )

    def test_panels_are_normal_frameless_windows(self) -> None:
        Qt = QtCore.Qt
        for name in self.PANELS:
            with self.subTest(panel=name):
                flags = self._build(name).windowFlags()
                self.assertEqual(int(flags & Qt.WindowType_Mask), int(Qt.Window))
                self.assertTrue(bool(flags & Qt.FramelessWindowHint))
                self.assertFalse(bool(flags & Qt.WindowStaysOnTopHint))
                self.assertEqual(int(flags & _DECORATION_HINTS), 0)

    def test_a_titled_panel_shows_tentacles_release(self) -> None:
        import tentacle

        ui = self._build("MetashapeWorkflowUI")
        self.assertEqual(
            ui.windowTitle(), f"Metashape Workflow v{tentacle.__version__}"
        )

    def test_the_panels_keep_their_saved_names(self) -> None:
        """A user's settings live under the window's name -- the ``.ui`` stem --
        and its presets under the folder the panels were published with."""
        ui = self._build("MetashapeWorkflowUI")
        self.assertEqual(ui.objectName(), "metashape_workflow")
        self.assertEqual(PanelLauncher.PRESETS_FOLDER[0], "extapps")


class TestDocsLinks(unittest.TestCase):
    """A panel over an engine documented in extapps links that page (logged at
    open, a clickable anchor in the log pane). Each is a GitHub blob URL into
    extapps' repo, so a doc rename fails here rather than 404-ing for users.
    RealityCapture / Brush inherit the photogrammetry base's TUNING.md link;
    Metashape and Substance point at their own pages."""

    SLOTS = (
        "metashape_workflow",
        "realityscan_workflow",
        "gaussian_splat_workflow",
        "substance_workflow",
    )

    def test_each_link_names_a_file_in_extapps(self):
        import extapps

        prefix = extapps.DOCS_BASE_URL
        repo = Path(extapps.__file__).resolve().parents[1]
        for tool in self.SLOTS:
            with self.subTest(panel=tool):
                cls = PanelLauncher._slots_class(tool)
                self.assertTrue(cls.DOCS_URL.startswith(prefix), cls.DOCS_URL)
                self.assertTrue(cls.DOCS_LABEL.strip())
                target = repo / cls.DOCS_URL[len(prefix) :]
                self.assertTrue(target.is_file(), f"{cls.DOCS_URL} -> missing {target}")


class TestHub(unittest.TestCase):
    """``python -m tentacle`` / the ``tentacle`` command: uitk's ExternalAppHub,
    declared here, serving every standalone panel."""

    @classmethod
    def setUpClass(cls):
        cls.app = _ensure_app()
        from tentacle.__main__ import HUB

        cls.hub = HUB
        cls.sb = HUB._switchboard()

    def test_the_hub_is_tentacles(self):
        self.assertEqual(self.hub.package, "tentacle")
        self.assertEqual(self.hub.dist, Tcl.DIST)
        self.assertEqual(self.hub.app_id, "m3trik.tentacle")

    def test_a_host_finds_it_as_the_providers_hub(self):
        from uitk import ExternalAppHub

        self.assertIs(ExternalAppHub.of("tentacle"), self.hub)

    def test_its_icon_ships_with_the_package(self):
        self.assertTrue(os.path.isfile(self.hub.icon), self.hub.icon)
        self.assertEqual(Path(self.hub.icon).parent, Path(tcl_standalone.__file__).parent)
        globs = re.search(r'^"\*" = \[([^\]]*)\]', PYPROJECT.read_text(encoding="utf-8"), re.M)
        self.assertIn('"*.svg"', globs.group(1), "*.svg is declared package data")

    def test_the_command_runs_the_hub(self):
        target = _table("project.gui-scripts")["tentacle"]
        module, _, attrs = target.partition(":")
        resolved = importlib.import_module(module)
        for attr in attrs.split("."):
            resolved = getattr(resolved, attr)
        self.assertEqual(resolved, self.hub.run)

    def test_tentacle_provides_the_apps(self):
        """A handler reading installed metadata also reads a source checkout's
        table (newer than an editable install's metadata)."""
        self.assertEqual(_table('project.entry-points."uitk.external_app_providers"'), {"tentacle": Tcl.DIST})

    def test_the_browser_lists_every_panel(self):
        handler = self.sb.handlers.external_app
        for name in STANDALONE:
            with self.subTest(panel=name):
                self.assertTrue(handler.is_registered(name))
                self.assertEqual(handler._apps[name]["module"], "tentacle.tcl_standalone")

    def test_every_panel_can_get_a_desktop_launcher_from_it(self):
        handler = self.sb.handlers.external_app
        for name in sorted(STANDALONE):
            with self.subTest(panel=name):
                self.assertIs(handler.hub_for(name), self.hub)


if __name__ == "__main__":
    unittest.main()
