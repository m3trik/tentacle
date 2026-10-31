# !/usr/bin/python
# coding=utf-8
"""Regression tests for the standalone Substance Workflow panel
(``slots/tools/substance_workflow.py``) over extapps' Painter engine.

Covers the panel's log pane: its startup docs anchor and the width its boxes
are sized to. The panel is a plain ``ptk.LoggingMixin`` slots class, NOT a
``BridgeSlotsBase`` subclass, so it does not inherit the bridge base's log
wiring and sets uitk's ``TextEditLogHandler`` itself. Also the Painter
session the panel follows, and Run Workflow's stages running off the GUI
thread (with Cancel); a live run against a NEW Painter is gated behind
``SUBSTANCE_WORKFLOW_RUN_INTEGRATION=1``.
"""

import os
import sys
import threading
import time
import unittest
from unittest.mock import MagicMock, Mock, patch

from qtpy.QtWidgets import QApplication, QTextBrowser

from tentacle.slots.tools.substance_workflow import SubstanceWorkflowSlots

#: Where the panel's module reads PainterFinder from (patched: no Painter scan).
_FINDER = "tentacle.slots.tools.substance_workflow.PainterFinder.find_installs"


def _ensure_app():
    return QApplication.instance() or QApplication([])


def _switchboard(kind=Mock):
    """A stand-in switchboard that answers the uitk names the panel reads off it
    (``self.sb.BackgroundTask``, ...), as the real one's namespace does."""
    import uitk

    sb = kind()
    for name in ("BackgroundTask", "KindFactory", "TextEditLogHandler"):
        setattr(sb, name, getattr(uitk, name))
    return sb


class TestSubstanceDocsLink(unittest.TestCase):
    """The startup docs line must be a LIVE anchor, not just styled text.

    A bare ``setup_logging_redirect`` attaches pythontk's
    ``DefaultTextLogHandler``. pythontk is deliberately Qt-free, so that
    handler cannot wire Qt link handling (the pane is left with
    ``openExternalLinks`` False and clicking the anchor does nothing) nor
    measure the pane. ``BridgeSlotsBase`` sets ``TextEditLogHandler`` for its
    own panels; this panel is not one, so it sets it itself.
    """

    @classmethod
    def setUpClass(cls):
        cls.app = _ensure_app()

    def test_logging_redirect_alone_leaves_the_pane_unrouted(self):
        """Pins WHY the panel sets its handler itself.

        ``setup_logging_redirect`` builds the logger's own text handler, else
        the process default ``LoggerExt._text_handler``, else pythontk's
        Qt-free ``DefaultTextLogHandler`` -- the case on this panel's
        documented standalone launch (``SubstanceWorkflowUI().show(...)``),
        where nothing else has registered one, and the anchor is inert. This
        test forces that unregistered state so the dependency is pinned
        deterministically rather than by suite order.

        Unrouted is worse than inert: QTextBrowser.openLinks defaults True, so
        a click navigates the pane to the URL and REPLACES the log document.
        """
        import pythontk as ptk
        from uitk.widgets.textEditLogHandler import TextEditLogHandler

        class _Host(ptk.LoggingMixin):
            pass

        from pythontk.core_utils.logging_mixin import LoggerExt

        host = _Host()
        saved = LoggerExt._text_handler
        try:
            LoggerExt._text_handler = None  # the standalone-launch state
            pane = QTextBrowser()
            host.logger.setup_logging_redirect(pane)

            self.assertIsNone(pane.property(TextEditLogHandler._LINKS_ROUTED_PROP))
            self.assertTrue(
                pane.openLinks(), "unrouted pane would navigate away on click"
            )
        finally:
            LoggerExt._text_handler = saved

    def _open_panel(self, pane):
        """Run the panel's real ``__init__`` against *pane* (no Painter scan)."""
        from unittest.mock import patch

        sb = _switchboard()
        sb.loaded_ui.substance_workflow.txt003 = pane
        with patch(_FINDER, return_value={}):
            inst = SubstanceWorkflowSlots(sb)
        for handler in inst.logger.handlers:
            if getattr(handler, "widget", None) is pane:
                self.addCleanup(inst.logger.removeHandler, handler)
                return inst, handler
        self.fail("the panel never redirected its log into the pane")

    def test_panel_log_pane_reports_its_width(self):
        """The panel logs boxes (its run header, WORKFLOW COMPLETE), and a box
        is sized to the width its handler reports. pythontk's Qt-free
        ``DefaultTextLogHandler`` reports none, so every box came out
        ``DEFAULT_BOX_WIDTH`` (100) columns wide whatever the pane, and broke
        in any narrower one."""
        _inst, handler = self._open_panel(QTextBrowser())
        self.assertTrue(callable(getattr(handler, "available_columns", None)))

    def test_panel_startup_routes_the_log_pane(self):
        """After the panel wires its pane, a web anchor reaches the browser and
        the log document is never navigated away from."""
        from unittest.mock import patch
        from qtpy.QtCore import QUrl
        from uitk.widgets.textEditLogHandler import TextEditLogHandler

        pane = QTextBrowser()
        self._open_panel(pane)

        self.assertTrue(pane.property(TextEditLogHandler._LINKS_ROUTED_PROP))
        # setOpenLinks(False) is what stops a click wiping the log document.
        self.assertFalse(pane.openLinks())
        self.assertFalse(pane.openExternalLinks())

        # And the docs anchor actually reaches the browser.
        with patch(
            "uitk.widgets.textEditLogHandler.QtGui.QDesktopServices.openUrl"
        ) as opened:
            pane.anchorClicked.emit(QUrl(SubstanceWorkflowSlots.DOCS_URL))
        self.assertEqual(opened.call_count, 1)
        self.assertEqual(
            opened.call_args[0][0].toString(), SubstanceWorkflowSlots.DOCS_URL
        )



class TestPainterSessionState(unittest.TestCase):
    """The panel follows the Painter it launched. Painter quit from its own
    window left the button on Close Painter and Run failing; a rebuilt panel
    (``conn=None``) saw no session beside a running one and its launch
    orphaned that Painter."""

    @classmethod
    def setUpClass(cls):
        cls.app = _ensure_app()

    def setUp(self):
        from extapps import PainterConnection

        self.PainterConnection = PainterConnection
        PainterConnection._instance = None
        self.addCleanup(setattr, PainterConnection, "_instance", None)

    def _panel(self):
        from unittest.mock import patch

        sb = _switchboard()
        pane = QTextBrowser()
        sb.loaded_ui.substance_workflow.txt003 = pane
        with patch(_FINDER, return_value={}):
            inst = SubstanceWorkflowSlots(sb)
        for handler in list(inst.logger.handlers):
            if getattr(handler, "widget", None) is pane:
                self.addCleanup(inst.logger.removeHandler, handler)
        self.addCleanup(inst._session_timer.stop)
        return inst

    def _running(self):
        conn = self.PainterConnection.get_instance()
        conn.process = Mock(pid=4242, **{"poll.return_value": None})
        conn.is_connected = True
        return conn

    @staticmethod
    def _label(inst):
        return inst.ui.btn_launch.setText.call_args.args[0]

    def test_a_rebuilt_panel_picks_up_the_running_painter(self):
        self._running()
        inst = self._panel()
        self.assertIs(inst.conn, self.PainterConnection.get_instance())
        self.assertTrue(inst._connected)
        self.assertEqual(self._label(inst), "Close Painter")

    def test_the_button_follows_a_painter_that_quit_by_itself(self):
        from unittest.mock import patch

        conn = self._running()
        inst = self._panel()
        self.assertTrue(inst._session_timer.isActive())
        conn.process.poll.return_value = 0  # quit from its own window
        with patch.object(inst.logger, "warning") as warned:
            inst._check_session()  # what the watch runs
        self.assertEqual(self._label(inst), "Launch Painter")
        warned.assert_called_once()
        self.assertFalse(inst._session_timer.isActive())

    def test_a_click_on_the_stale_button_only_refreshes_it(self):
        from unittest.mock import patch

        conn = self._running()
        inst = self._panel()
        conn.process.poll.return_value = 0
        with patch.object(inst, "_launch_painter") as launch, patch.object(inst, "_close_painter") as close:
            inst.btn_launch(None)
        launch.assert_not_called()
        close.assert_not_called()
        self.assertEqual(self._label(inst), "Launch Painter")

    def test_the_watch_runs_only_while_a_session_is_up(self):
        inst = self._panel()
        self.assertFalse(inst._session_timer.isActive())
        self._running()
        inst._sync_launch_button()
        self.assertTrue(inst._session_timer.isActive())


def _run_ui(mesh: str, save_path: str):
    """The widgets Run Workflow reads, real (stage boxes, Advanced fields from
    the panel's own specs); the footer a Mock -- it only shows progress."""
    from qtpy import QtWidgets
    from uitk import KindFactory

    from tentacle.slots.tools.substance_workflow import ADVANCED_PARAMS, PIPELINE_STAGES

    ui = QtWidgets.QWidget()
    ui.txt000 = QtWidgets.QLineEdit(mesh, ui)
    ui.txt001 = QtWidgets.QLineEdit("", ui)
    ui.txt002 = QtWidgets.QLineEdit(save_path, ui)
    ui.txt003 = QTextBrowser(ui)
    ui.b000 = QtWidgets.QPushButton("Run Workflow", ui)
    ui.btn_launch = QtWidgets.QPushButton("Launch Painter", ui)
    ui.cmb000 = Mock()
    ui.footer = Mock()
    for name, label, _tooltip, default_on in PIPELINE_STAGES:
        box = QtWidgets.QCheckBox(label, ui)
        box.setChecked(default_on)
        setattr(ui, name, box)
    for spec in ADVANCED_PARAMS:
        setattr(ui, spec.key, KindFactory.make_widget(spec, ui))
    return ui


def _pump_until(app, condition, seconds: float = 10.0, what: str = "") -> None:
    """Run the Qt loop until *condition* holds (the way the panel's own loop
    would), failing after *seconds*."""
    deadline = time.monotonic() + seconds
    while not condition():
        if time.monotonic() > deadline:
            raise AssertionError(f"timed out waiting for {what or condition}")
        app.processEvents()
        time.sleep(0.01)


class TestWorkflowRunOffTheGuiThread(unittest.TestCase):
    """Run Workflow runs its stages on a ``uitk.BackgroundTask``, one after
    another, and reports them on the GUI thread.

    The stages ran synchronously inside ``sb.progress``: a multi-set AO bake
    -- which waits on Painter's own "baking ended" event, up to the bridge's
    hour -- held the GUI thread for minutes. The progress bar could neither
    repaint nor cancel, and a hosting Maya/Blender stalled with it.
    """

    #: How long a gated op waits when nothing releases it -- the synchronous
    #: run this pins against blocked the slot for exactly this long.
    GATE_S = 2.0

    @classmethod
    def setUpClass(cls):
        cls.app = _ensure_app()

    def setUp(self):
        from extapps import PainterConnection

        PainterConnection._instance = None
        self.addCleanup(setattr, PainterConnection, "_instance", None)
        self.calls = []  # op names, in the order the bridge was asked
        self.threads = []  # the thread each op was called on
        self.gates = {}  # op -> Event the op waits on before answering
        self.raises = {}  # op -> what the op raises
        self.addCleanup(lambda: [gate.set() for gate in self.gates.values()])

    def _invoke(self, op, timeout=60.0, **kwargs):
        """The bridge, faked: records the call, waits on its gate, answers."""
        self.calls.append(op)
        self.threads.append(threading.current_thread())
        gate = self.gates.get(op)
        if gate is not None:
            gate.wait(self.GATE_S)
        if op in self.raises:
            raise self.raises[op]
        return {"op": op}

    def _gate(self, op):
        self.gates[op] = threading.Event()
        return self.gates[op]

    def _panel(self):
        """The panel on a connected (fake) Painter: a new project from a mesh,
        bake, save-as -- the default stages."""
        here = os.path.dirname(os.path.abspath(__file__))
        never = os.path.join(here, "temp_tests", "never_written")  # nothing is written
        ui = _run_ui(os.path.join(never, "cube.fbx"), os.path.join(never, "cube.spp"))
        self.addCleanup(ui.deleteLater)
        sb = _switchboard(MagicMock)  # its progress() is a context manager, as the switchboard's
        sb.loaded_ui.substance_workflow = ui
        with patch(_FINDER, return_value={}):
            inst = SubstanceWorkflowSlots(sb)
        for handler in list(inst.logger.handlers):
            if getattr(handler, "widget", None) is ui.txt003:
                self.addCleanup(inst.logger.removeHandler, handler)
        self.addCleanup(inst._session_timer.stop)
        conn = inst.conn
        conn.process = Mock(pid=4242, **{"poll.return_value": None})
        conn.is_connected = True
        conn.invoke = self._invoke
        inst._sync_launch_button()
        return inst

    def _log(self, inst) -> str:
        return inst.ui.txt003.toPlainText()

    def _settle(self, seconds: float = 0.6) -> None:
        """Pump past a BackgroundTask's poll, so a late callback would land."""
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            self.app.processEvents()
            time.sleep(0.01)

    def test_a_run_hands_the_loop_back_while_its_stages_run(self):
        inst = self._panel()
        bake = self._gate("bake.lighting_to_diffuse")
        inst.b000()
        # The slot returned with the run under way: Run reads Cancel.
        self.assertTrue(inst._busy)
        self.assertEqual(inst.ui.b000.text(), "Cancel")
        self.assertTrue(inst.ui.b000.isEnabled())
        _pump_until(self.app, lambda: "bake.lighting_to_diffuse" in self.calls, what="the bake")
        self.assertTrue(inst._busy)  # the bake waits off the GUI thread; the loop runs
        bake.set()
        _pump_until(self.app, lambda: not inst._busy, what="the run's end")

        self.assertEqual(
            self.calls, ["project.create", "bake.lighting_to_diffuse", "project.save_as"]
        )
        self.assertNotIn(threading.main_thread(), self.threads)
        self.assertEqual(inst.ui.b000.text(), "Run Workflow")
        self.assertTrue(inst.ui.b000.isEnabled())
        log = self._log(inst)
        for line in ("SUBSTANCE WORKFLOW", "Created:", "Baked  :", "Saved  :", "WORKFLOW COMPLETE"):
            self.assertIn(line, log)
        # The footer named each stage as it started, on a 3-step bar.
        footer = inst.ui.footer
        self.assertEqual(footer.start_progress.call_args.kwargs.get("total"), 3)
        shown = [call.args for call in footer.update_progress.call_args_list]
        self.assertEqual([value for value, _text in shown], [0, 1, 2])
        self.assertIn("Bake Lighting", shown[1][1])
        footer.finish_progress.assert_called_once()

    def test_cancel_stops_the_run_between_stages(self):
        inst = self._panel()
        create = self._gate("project.create")
        inst.b000()
        _pump_until(self.app, lambda: self.calls, what="the first stage")
        inst.b000()  # the button reads Cancel now
        # The running stage finishes first (the bridge cannot stop an op
        # mid-call); the button says so and takes no second click.
        self.assertTrue(inst._busy)
        self.assertFalse(inst.ui.b000.isEnabled())
        create.set()
        _pump_until(self.app, lambda: not inst._busy, what="the run's end")

        self.assertEqual(self.calls, ["project.create"])
        self.assertEqual(inst.ui.b000.text(), "Run Workflow")
        self.assertTrue(inst.ui.b000.isEnabled())
        log = self._log(inst)
        self.assertIn("Workflow cancelled", log)
        self.assertIn("Created:", log)  # what did run is still reported
        self.assertNotIn("WORKFLOW COMPLETE", log)

    def test_escape_hold_on_the_footer_cancels_the_same_run(self):
        """The footer's bar arms Esc-hold for its task: it must stop this run,
        not just hide the bar while the stages go on."""
        import pythontk as ptk

        inst = self._panel()
        scopes = []
        inst.ui.footer.start_progress.side_effect = lambda *a, **k: scopes.append(
            ptk.CancelScope.current()
        )
        create = self._gate("project.create")
        inst.b000()
        self.assertTrue(
            scopes and scopes[0] is not None, "the bar was not started inside the run's scope"
        )
        scopes[0].cancel("escape-hold")  # what the bar's Esc-hold does
        create.set()
        _pump_until(self.app, lambda: not inst._busy, what="the run's end")
        self.assertEqual(self.calls, ["project.create"])
        self.assertIn("Workflow cancelled", self._log(inst))

    def test_a_stage_that_raises_ends_the_run_and_gives_the_panel_back(self):
        inst = self._panel()
        bake = self._gate("bake.lighting_to_diffuse")
        self.raises["bake.lighting_to_diffuse"] = RuntimeError(
            "Op 'bake.lighting_to_diffuse' failed: iray ran out of memory"
        )
        inst.b000()
        self.assertTrue(inst._busy)  # it fails on the task, after the slot returned
        bake.set()
        _pump_until(self.app, lambda: not inst._busy, what="the run's end")

        self.assertEqual(self.calls, ["project.create", "bake.lighting_to_diffuse"])
        self.assertEqual(inst.ui.b000.text(), "Run Workflow")
        self.assertTrue(inst.ui.b000.isEnabled())
        log = self._log(inst)
        self.assertIn("Stages completed before the failure", log)
        self.assertIn("Workflow failed", log)
        self.assertIn("iray ran out of memory", log)
        self.assertNotIn("WORKFLOW COMPLETE", log)

    def test_painter_quitting_mid_run_ends_the_run(self):
        """The 2 s watch sees Painter gone: the run ends there, and the call
        still out on the dead bridge is never reported when it returns."""
        inst = self._panel()
        bake = self._gate("bake.lighting_to_diffuse")
        inst.b000()
        _pump_until(self.app, lambda: "bake.lighting_to_diffuse" in self.calls, what="the bake")
        inst.conn.process.poll.return_value = 0  # quit from its own window
        inst._check_session()  # what the watch runs

        self.assertFalse(inst._busy)
        self.assertEqual(inst.ui.b000.text(), "Run Workflow")
        self.assertTrue(inst.ui.b000.isEnabled())
        self.assertIn("Workflow stopped: Painter closed", self._log(inst))
        bake.set()  # the orphaned call answers late
        self._settle()
        self.assertEqual(self.calls, ["project.create", "bake.lighting_to_diffuse"])
        self.assertNotIn("WORKFLOW COMPLETE", self._log(inst))


def _write_cube_obj(path: str) -> None:
    """A unit cube, each face on its own tile of a 3x2 UV atlas (a bake needs UVs)."""
    corners = [(-1, -1, 1), (1, -1, 1), (1, 1, 1), (-1, 1, 1), (-1, -1, -1), (1, -1, -1), (1, 1, -1), (-1, 1, -1)]
    faces = [  # (corner indices counter-clockwise from outside, normal)
        ((1, 2, 3, 4), (0, 0, 1)),
        ((6, 5, 8, 7), (0, 0, -1)),
        ((2, 6, 7, 3), (1, 0, 0)),
        ((5, 1, 4, 8), (-1, 0, 0)),
        ((4, 3, 7, 8), (0, 1, 0)),
        ((5, 6, 2, 1), (0, -1, 0)),
    ]
    rows = [f"v {x} {y} {z}" for x, y, z in corners]
    margin = 0.02
    for i in range(len(faces)):
        u0, v0 = (i % 3) / 3 + margin, (i // 3) / 2 + margin
        u1, v1 = (i % 3 + 1) / 3 - margin, (i // 3 + 1) / 2 - margin
        rows += [f"vt {u:.4f} {v:.4f}" for u, v in ((u0, v0), (u1, v0), (u1, v1), (u0, v1))]
    rows += [f"vn {x} {y} {z}" for _, (x, y, z) in faces]
    for i, (quad, _normal) in enumerate(faces):
        rows.append("f " + " ".join(f"{c}/{4 * i + k + 1}/{i + 1}" for k, c in enumerate(quad)))
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(rows) + "\n")


@unittest.skipUnless(
    os.environ.get("SUBSTANCE_WORKFLOW_RUN_INTEGRATION") == "1",
    "Set SUBSTANCE_WORKFLOW_RUN_INTEGRATION=1 to run live Painter integration tests",
)
class TestWorkflowRunLive(unittest.TestCase):
    """The panel's run against a NEW Painter launched here (never an open
    one): the GUI loop keeps turning through a real bake, Cancel lands
    between stages, and a second run bakes and saves."""

    #: Longest the GUI loop may go unserved during a run. On the GUI thread a
    #: run held it for the whole bake.
    MAX_STALL_S = 1.0

    @classmethod
    def setUpClass(cls):
        cls.app = _ensure_app()

    def _stall(self, ticks, since: float) -> float:
        """The longest gap between GUI-loop ticks from *since* on."""
        stamps = [since] + [t for t in ticks if t >= since]
        return max(b - a for a, b in zip(stamps, stamps[1:])) if len(stamps) > 1 else float("inf")

    def test_a_live_run_keeps_the_loop_turning_and_cancels_between_stages(self):
        import pythontk as ptk
        from qtpy import QtCore

        from extapps import PainterConnection

        tmp = ptk.TempArtifacts.scoped("substance_workflow_live")
        self.addCleanup(tmp.cleanup, True)
        work = tmp.dir_path()
        mesh, spp = os.path.join(work, "cube.obj"), os.path.join(work, "cube.spp")
        _write_cube_obj(mesh)

        PainterConnection._instance = None
        self.addCleanup(setattr, PainterConnection, "_instance", None)
        conn = PainterConnection.get_instance()  # the panel's own session
        self.assertTrue(conn.connect(gui=False, timeout=240), "Painter bridge did not come up")
        # Painter holds the saved .spp open until it has exited: wait for that
        # before the temp folder goes (cleanups run last-added first).
        self.addCleanup(conn.process.wait, 60)
        self.addCleanup(conn.shutdown, force=True)  # only the Painter launched here
        calls, invoke = [], conn.invoke

        def recording(op, timeout=60.0, **kwargs):
            calls.append(op)
            return invoke(op, timeout=timeout, **kwargs)

        conn.invoke = recording

        ui = _run_ui(mesh, spp)
        self.addCleanup(ui.deleteLater)
        ui.cmb_bake_res.setCurrentText("256")
        ui.spn_ao_rays.setValue(16)
        sb = _switchboard(MagicMock)
        sb.loaded_ui.substance_workflow = ui
        with patch(_FINDER, return_value={}):
            inst = SubstanceWorkflowSlots(sb)
        for handler in list(inst.logger.handlers):
            if getattr(handler, "widget", None) is ui.txt003:
                self.addCleanup(inst.logger.removeHandler, handler)
        self.addCleanup(inst._session_timer.stop)
        ticks = []
        beat = QtCore.QTimer()
        beat.setInterval(20)
        beat.timeout.connect(lambda: ticks.append(time.monotonic()))
        beat.start()
        self.addCleanup(beat.stop)

        # Run 1: Cancel while the bake runs -- it finishes, the save never starts.
        started = time.monotonic()
        inst.b000()
        returned = time.monotonic() - started
        _pump_until(self.app, lambda: "bake.lighting_to_diffuse" in calls, 300, "the bake")
        inst.b000()  # the button reads Cancel
        _pump_until(self.app, lambda: not inst._busy, 1800, "the cancelled run's end")
        first = time.monotonic() - started
        log = ui.txt003.toPlainText()
        self.assertEqual(calls, ["project.create", "bake.lighting_to_diffuse"], log)
        self.assertIn("Baked  :", log)
        self.assertIn("Workflow cancelled before Save Project", log)
        self.assertFalse(os.path.exists(spp))
        self.assertLess(returned, self.MAX_STALL_S)
        stall = self._stall(ticks, started)
        self.assertLess(stall, self.MAX_STALL_S, f"the loop stalled {stall:.2f} s")
        print(f"run 1 (create + bake, cancelled): {first:.1f} s; slot returned in "
              f"{returned * 1000:.0f} ms; longest loop stall {stall * 1000:.0f} ms")

        # Run 2: the project is open -- bake and save.
        ui.stage_open.setChecked(False)
        del calls[:]
        started = time.monotonic()
        inst.b000()
        _pump_until(self.app, lambda: not inst._busy, 1800, "the second run's end")
        second = time.monotonic() - started
        log = ui.txt003.toPlainText()
        self.assertEqual(calls, ["bake.lighting_to_diffuse", "project.save_as"], log)
        self.assertIn("WORKFLOW COMPLETE", log)
        self.assertTrue(os.path.isfile(spp))
        stall = self._stall(ticks, started)
        self.assertLess(stall, self.MAX_STALL_S, f"the loop stalled {stall:.2f} s")
        self.assertEqual(ui.b000.text(), "Run Workflow")
        print(f"run 2 (bake + save): {second:.1f} s; longest loop stall {stall * 1000:.0f} ms")


# Default panel config: open + bake + save on, export off.
_DEFAULT_STAGES = {
    "stage_open": True,
    "stage_bake": True,
    "stage_save": True,
    "stage_export": False,
}


def _validate_stub(mesh: str, save_path: str):
    """Minimal stand-in exposing only what `_validate` reads."""
    import types

    errors = []
    ui = types.SimpleNamespace(
        txt000=types.SimpleNamespace(text=lambda: mesh),
        txt002=types.SimpleNamespace(text=lambda: save_path),
    )
    logger = types.SimpleNamespace(error=lambda msg: errors.append(msg))
    return types.SimpleNamespace(ui=ui, logger=logger), errors


class TestValidate(unittest.TestCase):
    """`_validate` guards a run before the expensive stages start, against a
    minimal stand-in `self` -- no live Painter, no Qt UI."""

    def setUp(self):
        import tempfile

        self.tmp = tempfile.mkdtemp()
        self.addCleanup(__import__("shutil").rmtree, self.tmp, True)

    def test_rejects_a_save_of_a_new_project_without_a_save_path(self):
        """Create-from-mesh + Save with an empty Save Path must be rejected
        up front (before the expensive bake runs), not fail at save time."""
        stub, errors = _validate_stub(mesh="C:/meshes/hero.fbx", save_path="")
        ok = SubstanceWorkflowSlots._validate(stub, dict(_DEFAULT_STAGES))
        self.assertIs(ok, False)
        self.assertTrue(errors, "an explanatory error should have been logged")
        self.assertIn("Save Path", errors[-1])

    def test_allows_a_new_project_with_a_save_target(self):
        """A not-yet-on-disk .spp save target is a valid save destination."""
        save_path = os.path.join(self.tmp, "hero.spp")  # does not exist yet
        stub, errors = _validate_stub(mesh="C:/meshes/hero.fbx", save_path=save_path)
        ok = SubstanceWorkflowSlots._validate(stub, dict(_DEFAULT_STAGES))
        self.assertIs(ok, True)
        self.assertFalse(errors)

    def test_allows_a_resave_of_an_existing_project(self):
        """Re-saving a project already on disk stays allowed even with no
        save-as target typed (project.save() has a path)."""
        spp = os.path.join(self.tmp, "existing.spp")
        with open(spp, "w") as handle:
            handle.write("stub")
        stub, errors = _validate_stub(mesh="", save_path=spp)
        ok = SubstanceWorkflowSlots._validate(stub, dict(_DEFAULT_STAGES))
        self.assertIs(ok, True)
        self.assertFalse(errors)


    def test_ignores_the_save_gap_when_the_save_stage_is_off(self):
        """When Save is unchecked, an empty Save Path is fine even for a new
        project (nothing tries to save)."""
        stages = dict(_DEFAULT_STAGES, stage_save=False)
        stub, errors = _validate_stub(mesh="C:/meshes/hero.fbx", save_path="")
        ok = SubstanceWorkflowSlots._validate(stub, stages)
        self.assertIs(ok, True)
        self.assertFalse(errors)

class TestRuntimeWidgets(unittest.TestCase):
    def test_they_are_the_advanced_fields(self):
        """``RUNTIME_WIDGETS`` (what the slot-coverage guard reads) is exactly
        the fields :data:`ADVANCED_PARAMS` builds, in order."""
        from tentacle.slots.tools.substance_workflow import ADVANCED_PARAMS

        self.assertEqual(
            SubstanceWorkflowSlots.RUNTIME_WIDGETS,
            tuple(spec.key for spec in ADVANCED_PARAMS),
        )

if __name__ == "__main__":
    sys.exit(unittest.main())
