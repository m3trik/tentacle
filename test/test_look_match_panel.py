# !/usr/bin/python
# coding=utf-8
"""Tests for the standalone Look Match panel, driven as a person drives it.

A small real session (two light layers and an emission layer, a reference
rendered from a known mix, two regions) opened in the real panel: edits are
typed, dragged and rolled into the mix table, regions are picked, proposals
accepted, and what each gesture did is read back from the mix and the view.
"""

import json
import os
import shutil
import sys
import time
import unittest
from unittest import mock

from uitk.testing import TestSandbox

TestSandbox.activate()  # before the first QSettings: never the developer's panel state

import numpy as np
import pythontk as ptk
from PIL import Image
from qtpy import QtCore, QtGui, QtWidgets

H, W = 24, 32


def _ensure_app():
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)


def _wait(predicate, seconds=20.0):
    """Process events until *predicate* holds (a background task's callback)."""
    end = time.time() + seconds
    while time.time() < end:
        QtWidgets.QApplication.processEvents()
        if predicate():
            return True
        time.sleep(0.02)
    return False


def _session(folder: str, worker: bool = False) -> str:
    """A session: key (lights the left), fill (flat), glow (emission); the
    reference is the mix key 1.0 + fill 0.5; the session opens at key 0.4."""
    xx = np.mgrid[0:H, 0:W][1] / W
    store = ptk.LightLayers(os.path.join(folder, "layers"))
    key = np.repeat(np.exp(-((xx - 0.25) ** 2) / 0.02)[..., None], 3, 2).astype(np.float32)
    store.add(
        "key",
        key,
        spec={"lights": [{"name": "L_KEY", "type": "spot", "pos": [0, 200, 100], "aim": [0, 90, 200], "cone": 40}]},
    )
    store.add(
        "fill",
        np.full((H, W, 3), 0.2, np.float32),
        spec={"lights": [{"name": "L_FILL", "type": "area", "pos": [0, 300, 0], "rot": [-90, 0, 0]}]},
    )
    store.add(
        "glow",
        np.full((H, W, 3), 0.05, np.float32),
        kind="emission",
        target={"node": "MAT_PANELS", "attr": "emissive_intensity", "scale": 3.14},
    )
    truth = ptk.LightMix({"key": {"weight": 1.0}, "fill": {"weight": 0.5}})
    ref = (ptk.LightPredictor(store).frame(truth) * 255 + 0.5).astype(np.uint8)
    Image.fromarray(ref).save(os.path.join(folder, "reference.png"))
    ptk.LookTarget(
        os.path.join(folder, "reference.png"),
        [
            ptk.LookRegion("left", "area", {"rect": [0.05, 0.2, 0.45, 0.8]}, measures=["mean"]),
            ptk.LookRegion("right", "area", {"rect": [0.6, 0.2, 0.95, 0.8]}, measures=["mean"]),
        ],
    ).save(os.path.join(folder, "target.json"))
    os.makedirs(os.path.join(folder, "mixes"))
    truth.with_weights({"key": 0.4}).save(os.path.join(folder, "mixes", "start.json"))
    data = {
        "version": 1,
        "layers": "layers",
        "target": "target.json",
        "mix": "mixes/start.json",
        "size": [W, H],
        "template": "room.glb",
    }
    if worker:  # a bake worker on a scene; key from its last save, fill from an older one
        scene = os.path.join(folder, "room.ma")
        with open(scene, "w", encoding="utf-8") as f:
            f.write("//Maya ASCII")
        now = ptk.LightLayerScene.of(scene)
        for name, record in (("key", now), ("fill", dict(now, mtime=now["mtime"] - 60))):
            info = store.info(name)
            store.add(name, store.load(name), spec=info["spec"], replace=True, scene=record, settings={"resolution": 256})
        data["loop"] = {"queue": "queue", "worker": {"module": "mayatk.light_utils.light_layer_baker", "scene": "room.ma"}}
    path = os.path.join(folder, "session.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f)
    return path


class _PanelCase(unittest.TestCase):
    #: The session names a bake worker (Update layers).
    WORKER = False

    @classmethod
    def setUpClass(cls):
        cls.app = _ensure_app()

    def setUp(self):
        from tentacle.tcl_standalone import LookMatchUI

        self.temp = ptk.TempArtifacts("test_look_match_panel", policy="scoped")
        self.addCleanup(self.temp.cleanup, force=True)
        self.folder = str(self.temp.dir_path())
        self.path = _session(self.folder, worker=self.WORKER)
        self.ui = LookMatchUI()
        self.ui.resize(1100, 600)
        self.ui.show()
        self.addCleanup(self.ui.close)
        self.slots = self.ui.slots
        QtWidgets.QApplication.processEvents()
        self.assertTrue(self.slots.open_session(self.path))
        self.assertTrue(_wait(lambda: self.slots.session == self.path), "the session never loaded")

    # ------------------------------------------------------------------ helpers
    def settle(self, seconds=20.0):
        """Wait as a person does: until the view has caught up with the mix
        (no refresh pending, no analysis running)."""
        slots = self.slots
        self.assertTrue(
            _wait(
                lambda: not slots._refresh_timer.isActive()
                and not slots._quick_timer.isActive()
                and "analyse" not in slots._tasks
                and not slots._stale,
                seconds,
            ),
            "the view never caught up",
        )

    def row(self, name):
        return self.slots._rows[name]

    def cell(self, name, column):
        return self.slots.ui.tbl_mix.item(self.row(name), column)

    def weight(self, name):
        return self.slots.match.mix.weight(name)

    def mouse(self, kind, pos, button, buttons):
        viewport = self.slots.ui.tbl_mix.viewport()
        local = QtCore.QPointF(pos)
        QtWidgets.QApplication.sendEvent(
            viewport,
            QtGui.QMouseEvent(
                kind, local, QtCore.QPointF(viewport.mapToGlobal(local.toPoint())), button, buttons, QtCore.Qt.NoModifier
            ),
        )

    def weight_cell_centre(self, name):
        table = self.slots.ui.tbl_mix
        table.scrollToItem(self.cell(name, self.slots.WEIGHT))
        return QtCore.QPointF(table.visualItemRect(self.cell(name, self.slots.WEIGHT)).center())

    def pick_region(self, name):
        table = self.slots.ui.tbl_regions
        for i in range(table.rowCount()):
            if table.item(i, 1).text() == name:
                table.selectRow(i)
                return
        self.fail(f"no region {name}")


class TestOpening(_PanelCase):
    def test_a_session_shows_its_mix_regions_and_comparison(self):
        rows = self.slots._rows
        self.assertEqual(set(rows), {"key", "fill"})  # the mix's layers (glow is off it)
        self.assertEqual(self.ui.tbl_regions.rowCount(), 2)
        self.assertIn("of 2 regions within tolerance", self.ui.lbl_headline.text())
        self.assertEqual(self.ui.cmp_view.view_a.image_size(), (W, H))
        self.ui.chk_all.setChecked(True)  # every layer in the store
        self.assertIn("glow", self.slots._rows)

    def test_a_later_open_wins_over_one_still_loading(self):
        other_folder = os.path.join(self.folder, "other")
        os.makedirs(other_folder)
        other = _session(other_folder)
        self.assertTrue(self.slots.open_session(other))
        self.assertTrue(self.slots.open_session(self.path))  # asked for while the other loads
        self.assertTrue(_wait(lambda: self.slots._opening is None))
        _wait(lambda: False, 0.5)  # any late callback has had its chance
        self.assertEqual(self.slots.session, self.path)

    def test_what_a_session_was_asked_stays_with_it(self):
        """A region's owners asked of one session never land in the next, even
        when the next has a region of that name."""
        import threading

        release = threading.Event()
        real = ptk.LookMatch.owners

        def slow(match, region, *args, **kwargs):
            release.wait(10)
            return real(match, region, *args, **kwargs)

        with mock.patch.object(ptk.LookMatch, "owners", slow):
            self.pick_region("left")
            other_folder = os.path.join(self.folder, "other")
            os.makedirs(other_folder)
            other = _session(other_folder)
            self.slots.open_session(other)
            self.assertTrue(_wait(lambda: self.slots.session == other))
            release.set()
            _wait(lambda: "owners" not in self.slots._tasks, 10)
        self.assertNotIn("left", self.slots._owners)

    def test_a_session_switch_never_waits_on_the_old_viewer(self):
        process = mock.Mock()
        process.wait.side_effect = lambda timeout=None: time.sleep(1.0)
        asked = []
        self.slots.service = (process, "http://127.0.0.1:5997/")
        with mock.patch.object(ptk.LookCapture, "client", return_value=mock.Mock(invoke=lambda op, **kw: asked.append(op))):
            started = time.time()
            self.slots.stop_service(wait=False)
            self.assertLess(time.time() - started, 0.5)
            self.assertIsNone(self.slots.service)
            self.assertTrue(_wait(lambda: asked == ["stop"], 5))

    def test_a_file_that_is_not_a_session_is_refused_with_why(self):
        bad = os.path.join(self.folder, "notes.json")
        with open(bad, "w", encoding="utf-8") as f:
            json.dump({"hello": 1}, f)
        self.assertFalse(self.slots.open_session(bad))
        self.assertEqual(self.slots.session, self.path)  # the open session stays


class TestEditingTheMix(_PanelCase):
    def test_a_typed_weight_changes_the_mix_and_undo_puts_it_back(self):
        left_before = self.slots.preview[12, 6].mean()
        self.cell("key", self.slots.WEIGHT).setData(QtCore.Qt.EditRole, 1.0)
        self.assertEqual(self.weight("key"), 1.0)
        self.settle()
        self.assertGreater(self.slots.preview[12, 6].mean(), left_before)
        self.ui.b_undo.click()
        self.assertAlmostEqual(self.weight("key"), 0.4)
        self.ui.b_redo.click()
        self.assertEqual(self.weight("key"), 1.0)

    def test_a_middle_drag_scrubs_a_weight_as_one_undo_step(self):
        start = self.weight("key")
        steps = self.slots.undo.count()
        point = self.weight_cell_centre("key")
        drag = QtCore.QPointF(self.slots.SCRUB_DOUBLING_PX, 0)
        self.mouse(QtCore.QEvent.MouseButtonPress, point, QtCore.Qt.MiddleButton, QtCore.Qt.MiddleButton)
        self.mouse(QtCore.QEvent.MouseMove, point + drag / 2, QtCore.Qt.NoButton, QtCore.Qt.MiddleButton)
        self.mouse(QtCore.QEvent.MouseMove, point + drag, QtCore.Qt.NoButton, QtCore.Qt.MiddleButton)
        self.mouse(QtCore.QEvent.MouseButtonRelease, point + drag, QtCore.Qt.MiddleButton, QtCore.Qt.NoButton)
        self.assertAlmostEqual(self.weight("key"), start * 2.0, places=6)
        self.assertEqual(self.slots.undo.count(), steps + 1)
        self.slots.undo.undo()
        self.assertAlmostEqual(self.weight("key"), start)

    def test_a_drag_moves_the_picture_now_and_the_scores_when_it_pauses(self):
        score = self.slots.score
        point = self.weight_cell_centre("key")
        self.mouse(QtCore.QEvent.MouseButtonPress, point, QtCore.Qt.MiddleButton, QtCore.Qt.MiddleButton)
        self.mouse(QtCore.QEvent.MouseMove, point + QtCore.QPointF(60, 0), QtCore.Qt.NoButton, QtCore.Qt.MiddleButton)
        _wait(lambda: False, 0.05)  # the quick tier runs on the next turn of the loop
        self.assertEqual(self.slots.preview.shape[:2], (H, W))  # half size, shown at full
        self.assertIs(self.slots.score, score)  # not scored mid-gesture
        self.mouse(QtCore.QEvent.MouseButtonRelease, point + QtCore.QPointF(60, 0), QtCore.Qt.MiddleButton, QtCore.Qt.NoButton)
        self.assertTrue(_wait(lambda: self.slots.score is not score, 3))

    def test_wheel_notches_roll_a_weight_and_undo_as_one(self):
        start = self.weight("key")
        point = self.weight_cell_centre("key")
        viewport = self.slots.ui.tbl_mix.viewport()
        for _ in range(3):
            QtWidgets.QApplication.sendEvent(
                viewport,
                QtGui.QWheelEvent(
                    point,
                    QtCore.QPointF(viewport.mapToGlobal(point.toPoint())),
                    QtCore.QPoint(),
                    QtCore.QPoint(0, 120),
                    QtCore.Qt.NoButton,
                    QtCore.Qt.NoModifier,
                    QtCore.Qt.NoScrollPhase,
                    False,
                ),
            )
        self.assertAlmostEqual(self.weight("key"), start * self.slots.WHEEL_STEP**3, places=6)
        self.slots.undo.undo()
        self.assertAlmostEqual(self.weight("key"), start)

    def test_a_colour_temperature_undone_to_none_shows_none(self):
        cell = self.cell("key", self.slots.KELVIN)
        self.assertEqual(cell.text(), "—")  # white: no temperature yet
        cell.setData(QtCore.Qt.EditRole, 3200.0)
        self.assertEqual(self.slots.match.mix.kelvin("key"), 3200.0)
        self.slots.undo.undo()
        self.assertIsNone(self.slots.match.mix.kelvin("key"))
        delegate = self.ui.tbl_mix.itemDelegateForColumn(self.slots.KELVIN)
        self.assertIsNone(delegate.value_of(self.ui.tbl_mix.indexFromItem(cell)))  # no number, no bar
        self.assertEqual(cell.text(), "—")

    def test_the_picture_follows_an_edit_made_while_the_scores_are_still_working(self):
        import threading

        release = threading.Event()
        real = type(self.slots)._analyse

        def slow(*args):
            release.wait(10)
            return real(*args)

        with mock.patch.object(type(self.slots), "_analyse", staticmethod(slow)):
            self.cell("key", self.slots.WEIGHT).setData(QtCore.Qt.EditRole, 0.8)
            self.assertTrue(_wait(lambda: "analyse" in self.slots._tasks, 3))
            before = self.slots.preview[12, 6].copy()
            self.cell("key", self.slots.WEIGHT).setData(QtCore.Qt.EditRole, 1.2)  # while scoring
            _wait(lambda: False, 0.2)
            self.assertGreater(self.slots.preview[12, 6].mean(), before.mean())
            release.set()
            self.settle()
        self.assertAlmostEqual(self.weight("key"), 1.2)
        expected = self.slots.match.predict(self.slots._effective_mix(), (W, H))
        np.testing.assert_allclose(self.slots.preview, expected, atol=1e-6)  # the mix as it is

    def test_solo_and_mute_change_the_view_not_the_mix(self):
        before = self.slots.preview[12, 6].mean()
        self.cell("key", self.slots.MUTE).setCheckState(QtCore.Qt.Checked)
        self.settle()
        self.assertLess(self.slots.preview[12, 6].mean(), before)
        self.assertAlmostEqual(self.weight("key"), 0.4)  # the mix is unchanged
        self.cell("key", self.slots.MUTE).setCheckState(QtCore.Qt.Unchecked)
        self.cell("fill", self.slots.SOLO).setCheckState(QtCore.Qt.Checked)
        self.settle()
        np.testing.assert_allclose(self.slots.preview[12, 6], self.slots.preview[12, 28], atol=0.02)


class TestRegionsAndProposals(_PanelCase):
    def test_a_picked_region_shows_who_lights_it_and_solve_proposes(self):
        self.pick_region("left")
        self.assertEqual(self.slots.region, "left")
        self.settle()
        self.assertIsNotNone(self.slots._detail)  # its close-up
        share = self.cell("key", self.slots.SHARE).data(QtCore.Qt.EditRole)
        self.assertGreater(share, 0.4)  # the key owns the left
        self.assertTrue(_wait(lambda: "left" in self.slots._owners))
        self.assertEqual(self.ui.cmb_solve.itemText(0), "key")  # the owner first
        self.ui.cmb_solve.setCurrentText("key")
        self.ui.b_solve.click()
        self.assertTrue(_wait(lambda: self.slots.proposal is not None))
        self.assertTrue(self.ui.frm_proposal.isVisible())
        proposed = self.slots.proposal.weight("key")
        self.assertAlmostEqual(proposed, 1.0, delta=0.15)  # the reference's own
        self.assertAlmostEqual(self.weight("key"), 0.4)  # nothing changes until accepted
        ghost = self.cell("key", self.slots.WEIGHT).data(self.slots.GHOST_ROLE)
        self.assertAlmostEqual(ghost, proposed)
        self.ui.b_accept.click()
        self.assertAlmostEqual(self.weight("key"), proposed)
        self.assertFalse(self.ui.frm_proposal.isVisible())
        self.slots.undo.undo()
        self.assertAlmostEqual(self.weight("key"), 0.4)

    def test_a_solve_that_fails_says_why(self):
        """Only a region the layer cannot reach (ValueError) was caught: any
        other failure left the footer on "Solving..." for good."""
        self.pick_region("left")
        self.ui.cmb_solve.setCurrentIndex(self.ui.cmb_solve.findText("key"))
        with mock.patch.object(ptk.LookMatch, "solve", side_effect=RuntimeError("the predictor broke")):
            self.ui.b_solve.click()
            self.assertTrue(_wait(lambda: "solve" not in self.slots._tasks, 10))
        self.assertIn("the predictor broke", self.ui.footer.statusText())
        self.assertIsNone(self.slots.proposal)

    def test_an_edit_discards_a_proposal(self):
        self.pick_region("left")
        self.ui.cmb_solve.setCurrentIndex(self.ui.cmb_solve.findText("key"))
        self.ui.b_solve.click()
        self.assertTrue(_wait(lambda: self.slots.proposal is not None))
        self.assertTrue(self.ui.frm_proposal.isVisible())
        self.cell("fill", self.slots.WEIGHT).setData(QtCore.Qt.EditRole, 0.6)
        self.assertIsNone(self.slots.proposal)
        self.assertFalse(self.ui.frm_proposal.isVisible())

    def test_fit_moves_only_the_ticked_layers(self):
        self.ui.b_fit.click()  # nothing ticked: it says so
        self.assertIsNone(self.slots.proposal)
        self.cell("key", self.slots.FREE).setCheckState(QtCore.Qt.Checked)
        menu = self.ui.b_fit.option_box.menu
        menu.chk_fit_selected.setChecked(False)
        menu.spn_fit_tolerance.setValue(0.0)  # no "good enough": all the way
        menu.spn_fit_regularize.setValue(0.0)  # and no pull back
        self.ui.b_fit.click()
        self.assertTrue(_wait(lambda: self.slots.proposal is not None, 60))
        self.assertAlmostEqual(self.slots.proposal.weight("fill"), 0.5)
        self.assertAlmostEqual(self.slots.proposal.weight("key"), 1.0, delta=0.1)

    def test_difference_mode_shows_one_picture(self):
        self.ui.cmb_mode.setCurrentIndex(self.ui.cmb_mode.findText("Difference"))
        self.assertEqual(self.ui.cmp_view.mode(), "a")
        self.assertIn("against", self.ui.cmp_view._caption_a.text())


class TestEditingRegions(_PanelCase):
    def target_names(self):
        return [r["name"] for r in json.load(open(os.path.join(self.folder, "target.json"), encoding="utf-8"))["regions"]]

    def draw_rect(self, start, end):
        view = self.ui.cmp_view.view_a
        viewport = view.viewport()

        def send(kind, x, y, button, buttons):
            local = QtCore.QPointF(view.mapFromScene(QtCore.QPointF(x, y)))
            QtWidgets.QApplication.sendEvent(
                viewport,
                QtGui.QMouseEvent(kind, local, QtCore.QPointF(viewport.mapToGlobal(local.toPoint())), button, buttons, QtCore.Qt.NoModifier),
            )

        send(QtCore.QEvent.MouseButtonPress, *start, QtCore.Qt.LeftButton, QtCore.Qt.LeftButton)
        send(QtCore.QEvent.MouseMove, *end, QtCore.Qt.NoButton, QtCore.Qt.LeftButton)
        send(QtCore.QEvent.MouseButtonRelease, *end, QtCore.Qt.LeftButton, QtCore.Qt.NoButton)

    def test_editing_shows_the_tools_and_a_drawn_box_becomes_a_scored_region(self):
        self.assertFalse(self.ui.frm_region_tools.isVisibleTo(self.ui))
        self.ui.b_edit_regions.click()
        self.assertTrue(self.ui.frm_region_tools.isVisibleTo(self.ui))
        self.assertFalse(self.ui.b_solve.isVisibleTo(self.ui))
        self.ui.b_draw_rect.click()
        with mock.patch.object(QtWidgets.QInputDialog, "getText", return_value=("bench", True)):
            self.draw_rect((4, 4), (16, 20))
        self.assertEqual(self.target_names(), ["left", "right", "bench"])
        self.settle()
        self.assertIn("bench", [r["region"] for r in self.slots.summary])
        self.assertEqual(self.ui.tbl_regions.rowCount(), 3)
        region = self.slots.match.target.region("bench")  # the box drawn, give or take a screen pixel
        np.testing.assert_allclose(region.shapes["ours"]["rect"], [4 / W, 4 / H, 16 / W, 20 / H], atol=0.02)

    def test_a_region_is_renamed_weighed_and_deleted_in_its_table(self):
        self.ui.b_edit_regions.click()
        self.pick_region("left")
        table = self.ui.tbl_regions
        row = next(i for i in range(table.rowCount()) if table.item(i, 1).text() == "left")
        table.item(row, self.slots.REGION_NAME).setText("left wall")
        self.assertEqual(self.target_names(), ["left wall", "right"])
        self.assertEqual(self.slots.region, "left wall")  # the selection follows
        table.item(row, self.slots.REGION_WEIGHT).setData(QtCore.Qt.EditRole, 3.0)
        self.assertEqual(self.slots.match.target.region("left wall").weight, 3.0)
        table.item(row, self.slots.REGION_NAME).setText("right")  # taken
        self.assertEqual(self.target_names(), ["left wall", "right"])
        with mock.patch.object(QtWidgets.QMessageBox, "question", return_value=QtWidgets.QMessageBox.Yes):
            self.ui.b_region_delete.click()
        self.assertEqual(self.target_names(), ["right"])
        self.assertIsNone(self.slots.region)

    def test_painted_regions_follow_their_layer_after_a_reload(self):
        self.ui.b_edit_regions.click()
        with mock.patch.object(QtWidgets.QMessageBox, "question", return_value=QtWidgets.QMessageBox.Yes), mock.patch.object(
            type(self.slots), "_reveal"
        ):
            self.ui.b_paint.click()
        markers = os.path.join(self.folder, "ref_markers.png")
        self.assertTrue(os.path.isfile(markers))
        spec = self.slots.match.target.region("left").shapes["ref"]
        self.assertEqual(spec["mask"], "ref_markers.png")
        before = int(self.slots.match.target.region("left").mask("ref", (W, H)).sum())
        # Repaint: "left" now covers the whole left half of the layer.
        layer = np.array(Image.open(markers).convert("RGBA"))
        layer[:, : W // 2] = list(spec["color"]) + [255]
        Image.fromarray(layer).save(markers)
        self.ui.b_reload.click()
        after = int(self.slots.match.target.region("left").mask("ref", (W, H)).sum())
        self.assertGreater(after, before)
        self.settle()
        self.assertEqual(self.ui.tbl_regions.rowCount(), 2)


class TestSaving(_PanelCase):
    def test_save_as_writes_a_mix_and_lists_it(self):
        self.cell("key", self.slots.WEIGHT).setData(QtCore.Qt.EditRole, 0.8)
        with mock.patch.object(QtWidgets.QInputDialog, "getText", return_value=("brighter key", True)):
            self.slots.save_mix_as()
        path = os.path.join(self.folder, "mixes", "brighter key.json")
        self.assertAlmostEqual(ptk.LightMix.load(path).weight("key"), 0.8)
        self.assertEqual(self.ui.cmb_mix.currentText(), "brighter key")
        self.assertGreaterEqual(self.ui.cmb_b.findText("Mix: brighter key"), 0)

    def test_save_as_names_the_file_it_wrote(self):
        """The store spells a name its own way ("warm.v2 (final)" saves as
        ``warm_v2 _final_.json``): the footer says the name saved, not the one
        typed."""
        with mock.patch.object(
            QtWidgets.QInputDialog, "getText", return_value=("warm.v2 (final)", True)
        ):
            self.slots.save_mix_as()
        path = os.path.join(self.folder, "mixes", "warm_v2 _final_.json")
        self.assertTrue(os.path.isfile(path))
        self.assertEqual(self.ui.cmb_mix.currentText(), "warm_v2 _final_")
        self.assertEqual(self.ui.footer.statusText(), "Saved warm_v2 _final_.")

    def test_delete_sends_the_picked_mix_to_the_trash(self):
        path = os.path.join(self.folder, "mixes", "start.json")
        self.assertEqual(self.ui.cmb_mix.currentText(), "start")
        bin_dir = os.path.join(self.folder, "bin")
        os.makedirs(bin_dir)

        def to_bin(file_path):  # the platform trash: the file moves, restorable
            return shutil.move(file_path, os.path.join(bin_dir, os.path.basename(file_path)))

        with mock.patch.object(ptk.FileUtils, "can_trash", return_value=True), mock.patch.object(
            ptk.FileUtils, "move_to_trash", side_effect=to_bin
        ) as trash, mock.patch.object(self.slots, "_confirm", return_value=True) as confirm:
            self.slots.delete_mix()
        self.assertIn("Recycle Bin" if sys.platform.startswith("win") else "Trash", confirm.call_args[0][0])
        trash.assert_called_once_with(path)
        self.assertTrue(os.path.isfile(os.path.join(bin_dir, "start.json")))  # restorable
        self.assertEqual(self.ui.cmb_mix.findText("start"), -1)
        self.assertEqual(self.ui.cmb_b.findText("Mix: start"), -1)

    def test_save_to_the_rig_library_writes_a_rig_maya_applies(self):
        with mock.patch.object(QtWidgets.QInputDialog, "getText", return_value=("panel_test_rig", True)):
            self.ui.b_save_rig.click()
        rig = ptk.LightRigPayload.library().load("panel_test_rig")
        self.assertEqual(ptk.LightRigPayload.validate(rig).errors, [])
        self.assertEqual({light["name"] for light in rig["lights"]}, {"L_KEY", "L_FILL"})


class TestUpdatingLayers(_PanelCase):
    WORKER = True

    def test_update_bakes_what_an_older_save_made_and_keeps_the_mix(self):
        import threading

        self.assertTrue(self.ui.b_update.isVisible())
        self.assertEqual(self.ui.b_update.text(), "Update layers (1)")
        self.cell("key", self.slots.WEIGHT).setData(QtCore.Qt.EditRole, 0.7)  # an edit to keep
        scene = os.path.join(self.folder, "room.ma")
        queue_root = os.path.join(self.folder, "queue")
        jobs = []

        def bake(job):  # the worker: a bake folder per layer, its layer.json
            jobs.append(job)
            for name, payload in job["layers"].items():
                folder = os.path.join(job["output"], name)
                os.makedirs(folder, exist_ok=True)
                with open(os.path.join(folder, "layer.json"), "w", encoding="utf-8") as f:
                    json.dump({"name": name, "kind": "light", "spec": payload, "files": [], "scene": ptk.LightLayerScene.of(scene)}, f)
            return {"layers": {n: {"folder": os.path.join(job["output"], n)} for n in job["layers"]}}

        worker = threading.Thread(target=lambda: ptk.JobQueue(queue_root).serve(bake, poll=0.05, beat=0.1), daemon=True)

        def launch(app, args=None, env=None, **kw):  # what `launch` does: a worker comes up
            worker.start()
            return mock.Mock(returncode=0, stdout="", stderr="")

        def stop_worker():
            ptk.JobQueue(queue_root).stop()
            worker.join(10)

        self.addCleanup(stop_worker)
        store = self.slots.match.layers

        class _Client:
            def invoke(self_, op, timeout=None, **request):
                if op == "capture":
                    for folder in ptk.LookCapture.bake_folders(request["source"]):
                        with open(os.path.join(folder, "layer.json"), encoding="utf-8") as f:
                            info = json.load(f)
                        ptk.LightLayers(store.root).add(
                            info["name"], np.full((H, W, 3), 0.2, np.float32), spec=info["spec"], replace=True, scene=info["scene"]
                        )
                return {}

        process = mock.Mock()
        process.poll.return_value = None
        target = self.slots.match.target
        with mock.patch.object(ptk.AppLauncher, "run", side_effect=launch) as run, mock.patch.object(
            ptk.LookCapture, "spawn", return_value=(process, "http://127.0.0.1:5998/")
        ), mock.patch.object(ptk.LookCapture, "client", return_value=_Client()), mock.patch.object(
            QtWidgets.QMessageBox, "question", return_value=QtWidgets.QMessageBox.Yes
        ):
            self.ui.b_update.click()
            self.assertTrue(_wait(lambda: "update" not in self.slots._tasks, 30))
        argv = json.loads(run.call_args.kwargs["env"]["PYTHONTK_ARGV"])
        self.assertEqual(argv[:4], ["-m", "mayatk.light_utils.light_layer_baker", "launch", "--queue"])
        self.assertEqual(sorted(jobs[0]["layers"]), ["fill"])  # only what the old save made
        self.assertTrue(ptk.LightLayerScene.matches(self.slots.match.layers.info("fill")["scene"], scene))
        self.assertEqual(self.ui.b_update.text(), "Update layers (0)")
        self.assertFalse(self.ui.b_update.isEnabled())
        self.assertAlmostEqual(self.weight("key"), 0.7)  # the mix is the panel's still
        self.assertIs(self.slots.match.target, target)  # regions untouched: masks kept
        self.assertTrue(self.slots.undo.canUndo())
        self.slots.stop_worker()  # the panel launched it: it ends it
        self.assertTrue(os.path.exists(os.path.join(queue_root, ptk.JobQueue.STOP)) or not worker.is_alive())

    def _update_then_open_another(self):
        """Update layers, and open another session (with a worker of its own)
        while the bake runs; returns the other session's folder."""
        import threading

        release = threading.Event()
        other_folder = os.path.join(self.folder, "other")
        os.makedirs(other_folder)
        other = _session(other_folder, worker=True)
        process = mock.Mock()
        process.poll.return_value = None
        with mock.patch.object(
            ptk.AppLauncher, "run", return_value=mock.Mock(returncode=0, stdout="", stderr="")
        ), mock.patch.object(ptk.LookCapture, "spawn", return_value=(process, "http://127.0.0.1:5995/")), mock.patch.object(
            ptk.LookCapture, "client", return_value=mock.Mock()
        ), mock.patch.object(
            QtWidgets.QMessageBox, "question", return_value=QtWidgets.QMessageBox.Yes
        ), mock.patch.object(
            ptk.LookLoop, "rebake", lambda loop, names, folder: release.wait(10) and {}
        ):
            self.ui.b_update.click()
            self.assertIn("update", self.slots._tasks)
            self.slots.open_session(other)
            self.assertTrue(_wait(lambda: self.slots.session == other))
            release.set()
            self.assertTrue(_wait(lambda: "update" not in self.slots._tasks, 10))
        return other_folder

    def test_an_update_that_outlives_its_session_frees_the_button(self):
        """The next session opened while the bake ran: the button stayed on
        "Updating layers..." and disabled, in a session with nothing updating."""
        self._update_then_open_another()
        self.assertEqual(self.ui.b_update.text(), "Update layers (1)")
        self.assertTrue(self.ui.b_update.isEnabled())

    def test_the_worker_stopped_is_the_one_this_panel_launched(self):
        """After a session switch, the stop went to the open session's queue --
        a worker this panel never launched -- and the launched one was left."""
        other_folder = self._update_then_open_another()
        self.slots.stop_worker()
        self.assertTrue(os.path.exists(os.path.join(self.folder, "queue", ptk.JobQueue.STOP)))
        self.assertFalse(os.path.exists(os.path.join(other_folder, "queue", ptk.JobQueue.STOP)))

    def test_a_panel_closed_for_good_stops_keeping_the_worker_up(self):
        """The lease renewal outlived a panel destroyed mid-Update (its end,
        which stops the renewal, died with the panel): the worker's lease never
        lapsed, so the Maya it bakes in stayed up for the host's whole life."""
        import threading

        release = threading.Event()
        self.addCleanup(release.set)
        renewals = []
        real_lease = ptk.JobQueue.lease
        process = mock.Mock()
        process.poll.return_value = None
        self.slots._lease_timer.setInterval(20)
        with mock.patch.object(
            ptk.AppLauncher, "run", return_value=mock.Mock(returncode=0, stdout="", stderr="")
        ), mock.patch.object(ptk.LookCapture, "spawn", return_value=(process, "http://127.0.0.1:5992/")), mock.patch.object(
            ptk.LookCapture, "client", return_value=mock.Mock()
        ), mock.patch.object(
            QtWidgets.QMessageBox, "question", return_value=QtWidgets.QMessageBox.Yes
        ), mock.patch.object(
            ptk.LookLoop, "rebake", lambda loop, names, folder: release.wait(10) and {}
        ), mock.patch.object(
            ptk.JobQueue, "lease", lambda queue, seconds: (renewals.append(seconds), real_lease(queue, seconds))
        ):
            self.ui.b_update.click()
            self.assertTrue(_wait(lambda: len(renewals) > 2, 5))  # renewing while it bakes
            self._cleanups = [c for c in self._cleanups if c[0] != self.ui.close]  # gone for good
            self.ui.deleteLater()
            QtWidgets.QApplication.sendPostedEvents(None, QtCore.QEvent.DeferredDelete)
            renewed = len(renewals)
            _wait(lambda: False, 0.3)
            self.assertEqual(len(renewals), renewed)
            release.set()

    def test_a_session_with_no_worker_hides_the_button(self):
        plain = os.path.join(self.folder, "plain")
        os.makedirs(plain)
        path = _session(plain)
        self.slots.open_session(path)
        self.assertTrue(_wait(lambda: self.slots.session == path))
        self.assertFalse(self.ui.b_update.isVisible())


class TestWebXr(_PanelCase):
    def test_a_render_starts_a_fresh_viewer_and_shows_its_frame(self):
        asked = []
        process = mock.Mock()
        process.poll.return_value = None

        class _Client:
            def invoke(self_, op, timeout=None, **request):
                asked.append(op)
                if op == "exact":  # the viewer's frame: the prediction stands in
                    frame = self.slots.match.predict(ptk.LightMix.from_dict(request["mix"]), (W, H))
                    Image.fromarray((frame * 255 + 0.5).astype(np.uint8)).save(request["out"])
                return {}

        with mock.patch.object(ptk.LookCapture, "spawn", return_value=(process, "http://127.0.0.1:5999/")) as spawn, mock.patch.object(
            ptk.LookCapture, "client", return_value=_Client()
        ):
            self.ui.b_render.click()
            self.assertTrue(_wait(lambda: "webxr" in self.slots.frames))
            spawn.assert_called_once_with(self.path)  # its own viewer, never a running one
            self.assertEqual(self.ui.cmb_a.itemData(self.ui.cmb_a.currentIndex()), "webxr")
            self.assertIn("this mix", self.ui.lbl_trust.text())
            self.cell("key", self.slots.WEIGHT).setData(QtCore.Qt.EditRole, 0.9)
            self.settle()
            self.assertIn("an earlier mix", self.ui.lbl_trust.text())
            self.ui.b_render.click()  # the viewer is up: no second start
            self.assertTrue(_wait(lambda: asked.count("exact") == 2))
            spawn.assert_called_once()
            self.slots.stop_service()
        self.assertEqual(asked[-1], "stop")
        process.wait.assert_called()


class TestTheViewerService(_PanelCase):
    """The capture service is started off the UI thread -- minutes, the first
    time -- by a render and by Update layers alike."""

    def test_a_render_and_an_update_asking_at_once_share_one_viewer(self):
        import threading

        started, release, calls, urls = threading.Event(), threading.Event(), [], []
        process = mock.Mock()
        process.poll.return_value = None

        def spawn(session, *args, **kwargs):
            calls.append(session)
            started.set()
            release.wait(10)
            return process, "http://127.0.0.1:5996/"

        with mock.patch.object(ptk.LookCapture, "spawn", side_effect=spawn):
            askers = [threading.Thread(target=lambda: urls.append(self.slots._ensure_service())) for _ in range(2)]
            for asker in askers:
                asker.start()
            self.assertTrue(started.wait(5))
            time.sleep(0.2)  # the second asks while the first is starting
            release.set()
            for asker in askers:
                asker.join(10)
        self.assertEqual(len(calls), 1)  # two viewers: one never stopped
        self.assertEqual(urls, ["http://127.0.0.1:5996/"] * 2)
        self.slots.service = None

    def test_a_viewer_started_for_the_last_session_never_renders_the_next(self):
        """A session opened while its predecessor's viewer was starting: the
        viewer came up after the switch had stopped none, and the next
        session's renders went to the old session's template."""
        import threading

        release, calls, asked = threading.Event(), [], []
        old, new = mock.Mock(), mock.Mock()
        old.poll.return_value = new.poll.return_value = None

        def spawn(session, *args, **kwargs):
            calls.append(session)
            if len(calls) == 1:
                release.wait(10)
                return old, "http://127.0.0.1:5993/"
            return new, "http://127.0.0.1:5994/"

        other_folder = os.path.join(self.folder, "other")
        os.makedirs(other_folder)
        other = _session(other_folder)
        client = mock.Mock(invoke=lambda op, **kw: asked.append(op))
        with mock.patch.object(ptk.LookCapture, "spawn", side_effect=spawn), mock.patch.object(
            ptk.LookCapture, "client", return_value=client
        ):
            starting = threading.Thread(target=self.slots._ensure_service)
            starting.start()
            self.assertTrue(_wait(lambda: len(calls) == 1, 5))
            self.slots.open_session(other)
            self.assertTrue(_wait(lambda: self.slots.session == other))
            release.set()
            starting.join(10)
            url = self.slots._ensure_service()
            self.assertTrue(_wait(lambda: "stop" in asked, 5))  # the old one ends
            self.slots.service = None
        self.assertEqual(url, "http://127.0.0.1:5994/")
        self.assertEqual(calls, [self.path, other])


if __name__ == "__main__":
    unittest.main()
