#!/usr/bin/python
# coding=utf-8
"""Regression tests for tentacle.slots.maya.uv.

uv.py is the largest tentacle slot (~1200 lines) and almost entirely UI
orchestration over mayatk and cmds. The testable units worth pinning
at this layer:

- get_map_size: the cmb003 value-carrier read (not a click handler).
- b000 (Transfer UVs): the ≥2-ordered-selection gate.
- b005 (Cut UVs): the "selected edges vs whole mesh" routing.
"""
import unittest
from unittest import mock

try:
    import maya.cmds as cmds
    import mayatk as mtk
    from tentacle.slots.maya import uv as uv_module

    _MAYA_AVAILABLE = True
except ImportError:
    cmds = None
    mtk = None
    uv_module = None
    _MAYA_AVAILABLE = False


class _FakeCmb:
    def __init__(self, text):
        self._t = text

    def currentText(self):
        return self._t


class _FakeUi:
    pass


class _RecordedSb:
    def __init__(self):
        self.messages = []

    def message_box(self, *args, **kwargs):
        self.messages.append((args, kwargs))


@unittest.skipUnless(_MAYA_AVAILABLE, "Requires maya.cmds")
class TestGetMapSize(unittest.TestCase):
    """get_map_size casts cmb003 text to int. Used throughout the file
    by texel-density operations.
    """

    def setUp(self):
        cmds.file(new=True, force=True)
        self.instance = uv_module.UvSlots.__new__(uv_module.UvSlots)
        self.instance.ui = _FakeUi()

    def tearDown(self):
        cmds.file(new=True, force=True)

    def test_returns_int_from_combo_text(self):
        self.instance.ui.cmb003 = _FakeCmb("2048")
        self.assertEqual(self.instance.get_map_size(), 2048)

    def test_returns_correct_int_for_common_sizes(self):
        for size in (256, 512, 1024, 2048, 4096):
            self.instance.ui.cmb003 = _FakeCmb(str(size))
            self.assertEqual(self.instance.get_map_size(), size)

    def test_non_numeric_text_raises(self):
        """Contract: garbage in cmb003 raises ValueError (no silent fallback)."""
        self.instance.ui.cmb003 = _FakeCmb("not_a_number")
        with self.assertRaises(ValueError):
            self.instance.get_map_size()


@unittest.skipUnless(_MAYA_AVAILABLE, "Requires maya.cmds")
class TestB000TransferUVsGate(unittest.TestCase):
    """b000 (Transfer UVs) requires ≥2 ordered-selected objects."""

    def setUp(self):
        cmds.file(new=True, force=True)
        self.instance = uv_module.UvSlots.__new__(uv_module.UvSlots)
        self.instance.sb = _RecordedSb()

        # Capture mtk.transfer_uvs calls.
        import mayatk as mtk
        self._original = mtk.transfer_uvs
        self.captured = []

        def fake_transfer(frm, to):
            self.captured.append((frm, to))

        mtk.transfer_uvs = fake_transfer

    def tearDown(self):
        import mayatk as mtk
        mtk.transfer_uvs = self._original
        cmds.file(new=True, force=True)

    def test_no_selection_warns_and_skips(self):
        cmds.select(clear=True)
        self.instance.b000(widget=None)
        self.assertEqual(self.captured, [])
        self.assertTrue(self.instance.sb.messages)

    def test_one_object_warns_and_skips(self):
        a = cmds.polyCube(name="uv_b000_one")[0]
        cmds.select(a)
        self.instance.b000(widget=None)
        self.assertEqual(self.captured, [])
        self.assertTrue(self.instance.sb.messages)

    def test_two_objects_dispatches_once(self):
        a = cmds.polyCube(name="uv_b000_a")[0]
        b = cmds.polyCube(name="uv_b000_b")[0]
        cmds.select([a, b])

        self.instance.b000(widget=None)

        # frm=a, to=[b] → one transfer call
        self.assertEqual(len(self.captured), 1)
        self.assertEqual(self.captured[0][0], a)
        self.assertEqual(self.captured[0][1], b)

    def test_three_objects_dispatches_twice(self):
        a = cmds.polyCube(name="uv_b000_a3")[0]
        b = cmds.polyCube(name="uv_b000_b3")[0]
        c = cmds.polyCube(name="uv_b000_c3")[0]
        cmds.select([a, b, c])

        self.instance.b000(widget=None)

        # frm=a, to=[b, c] → two transfer calls
        self.assertEqual(len(self.captured), 2)
        self.assertEqual(self.captured[0][0], a)
        self.assertEqual(self.captured[1][0], a)
        self.assertEqual({self.captured[0][1], self.captured[1][1]}, {b, c})


@unittest.skipUnless(_MAYA_AVAILABLE, "Requires maya.cmds")
class TestB005CutUVsRouting(unittest.TestCase):
    """b005 (Cut UVs) routes to polyMapCut differently for edges vs transforms."""

    def setUp(self):
        cmds.file(new=True, force=True)
        self.instance = uv_module.UvSlots.__new__(uv_module.UvSlots)
        self.instance.sb = _RecordedSb()

        # Capture polyMapCut calls.
        self._original = cmds.polyMapCut
        self.captured = []
        cmds.polyMapCut = lambda edges: self.captured.append(edges)

    def tearDown(self):
        cmds.polyMapCut = self._original
        cmds.file(new=True, force=True)

    def test_no_selection_warns(self):
        cmds.select(clear=True)
        self.instance.b005()
        self.assertEqual(self.captured, [])
        self.assertTrue(self.instance.sb.messages)

    def test_edge_selection_routes_polyMapCut(self):
        cube = cmds.polyCube(name="uv_cut_cube")[0]
        cmds.select(f"{cube}.e[0:3]")
        self.instance.b005()
        self.assertGreater(len(self.captured), 0)

    def test_transform_selection_cuts_all_mesh_edges(self):
        """When a transform is selected (no edge components), Cut UVs targets all edges."""
        cube = cmds.polyCube(name="uv_cut_all")[0]
        cmds.select(cube)
        self.instance.b005()
        # Should have made at least one polyMapCut call on the cube's edges.
        self.assertGreater(len(self.captured), 0)
        # The argument should be a glob-like edge spec.
        joined = " ".join(str(c) for c in self.captured)
        self.assertIn(".e[", joined)


@unittest.skipUnless(_MAYA_AVAILABLE, "Requires maya.cmds")
class TestB011SewUVsDuplicateNames(unittest.TestCase):
    """b011 (Sew UVs) must resolve mesh shapes by full path. Two transforms
    sharing a short leaf name make their shapes share a short name; the old
    per-shape ``cmds.objectType(shape)`` call then raised 'No object matches
    name: <shape>' because the ambiguous short name resolves to nothing.
    """

    def setUp(self):
        cmds.file(new=True, force=True)
        self.instance = uv_module.UvSlots.__new__(uv_module.UvSlots)
        self.instance.sb = _RecordedSb()
        self._orig = cmds.polyMapSew
        self.sewed = []
        cmds.polyMapSew = lambda *a, **k: self.sewed.append(a[0])

    def tearDown(self):
        cmds.polyMapSew = self._orig
        cmds.file(new=True, force=True)

    def test_sews_meshes_with_colliding_short_shape_names(self):
        g1 = cmds.group(empty=True, name="grpA")
        cmds.parent(cmds.polyCylinder(name="dupCyl")[0], g1)
        g2 = cmds.group(empty=True, name="grpB")
        cmds.parent(cmds.polyCylinder(name="dupCyl")[0], g2)
        cmds.select([f"{g1}|dupCyl", f"{g2}|dupCyl"])

        # Old code raised here on objectType("dupCylShape"); must not now.
        self.instance.b011()

        # Both meshes were sewn, addressed by unambiguous full paths.
        self.assertEqual(len(self.sewed), 2)
        self.assertTrue(all(s.startswith("|grp") and ".e[*]" in s for s in self.sewed))


class _FakeCheck:
    def __init__(self, checked):
        self._c = checked

    def isChecked(self):
        return self._c


class _FakeSpin:
    def __init__(self, value):
        self._v = value

    def value(self):
        return self._v


class _FakeDataCombo:
    def __init__(self, data):
        self._d = data

    def currentData(self):
        return self._d


class _FakeUnfoldMenu:
    """Mimics tb004's widget.option_box.menu (chk017/chk007/chk022/cmb013/s000)."""

    def __init__(
        self,
        optimize=True,
        orient=True,
        stack=True,
        tolerance=1.0,
        nonmanifold_mode="select",
    ):
        self.chk017 = _FakeCheck(optimize)  # Optimize
        self.chk007 = _FakeCheck(orient)  # Orient
        self.chk022 = _FakeCheck(stack)  # Stack Similar
        self.cmb013 = _FakeDataCombo(nonmanifold_mode)  # Non-Manifold strategy
        self.s000 = _FakeSpin(tolerance)  # Tolerance


class _FakeOptionBox:
    def __init__(self, menu):
        self.menu = menu


class _FakeUnfoldWidget:
    def __init__(self, **kwargs):
        self.option_box = _FakeOptionBox(_FakeUnfoldMenu(**kwargs))


@unittest.skipUnless(_MAYA_AVAILABLE, "Requires maya.cmds")
class TestClassifyU3dError(unittest.TestCase):
    """_classify_u3d_error condenses Unfold3D RuntimeErrors into short reasons.

    Shared by tb000 (Pack) and tb004 (Unfold) for their message boxes.
    """

    def test_non_manifold(self):
        err = RuntimeError(
            "Mesh has non-manifold vertices. Clean up the mesh before using unfold."
        )
        self.assertEqual(
            uv_module.UvSlots._classify_u3d_error(err), "non-manifold vertices"
        )

    def test_overlapping(self):
        err = RuntimeError("u3dLayout: overlapping UVs detected in the shell")
        self.assertEqual(
            uv_module.UvSlots._classify_u3d_error(err), "overlapping UVs"
        )

    def test_other_truncates_first_line(self):
        err = RuntimeError("Some unexpected failure\nwith trailing detail lines")
        self.assertEqual(
            uv_module.UvSlots._classify_u3d_error(err), "Some unexpected failure"
        )


@unittest.skipUnless(_MAYA_AVAILABLE, "Requires maya.cmds")
class TestTb004UnfoldGuard(unittest.TestCase):
    """tb004 (Unfold) must surface u3dUnfold's non-manifold RuntimeError as a
    message and abort, instead of letting it escape as an unhandled traceback
    (and instead of running the downstream optimize/stack steps).
    """

    def setUp(self):
        cmds.file(new=True, force=True)
        self.instance = uv_module.UvSlots.__new__(uv_module.UvSlots)
        self.instance.sb = _RecordedSb()
        self.instance.get_map_size = lambda: 2048

        # Isolate tb004's control flow from Maya UI state and the Unfold3D
        # plugin by stubbing the cmds it drives. The u3d* commands only exist
        # once Unfold3D.mll is loaded, so capture a sentinel for any that are
        # absent and delete them again on teardown.
        self._missing = object()
        self._orig = {
            name: getattr(cmds, name, self._missing)
            for name in (
                "selectMode",
                "u3dUnfold",
                "u3dOptimize",
                "polyUVStackSimilarShells",
            )
        }
        self.optimize_calls = []
        self.stack_calls = []
        cmds.selectMode = lambda *a, **k: False  # query → already-object: skip switch
        cmds.u3dOptimize = lambda *a, **k: self.optimize_calls.append((a, k))
        cmds.polyUVStackSimilarShells = lambda *a, **k: self.stack_calls.append((a, k))

    def tearDown(self):
        for name, fn in self._orig.items():
            if fn is self._missing:
                if hasattr(cmds, name):
                    delattr(cmds, name)
            else:
                setattr(cmds, name, fn)
        cmds.file(new=True, force=True)

    def test_non_manifold_runtimeerror_is_caught_and_aborts(self):
        def _raise(*a, **k):
            raise RuntimeError(
                "Mesh has non-manifold vertices. Clean up the mesh before using unfold."
            )

        cmds.u3dUnfold = _raise

        # Must not raise.
        self.instance.tb004(widget=_FakeUnfoldWidget())

        # A message naming the cause was surfaced.
        self.assertTrue(self.instance.sb.messages)
        joined = " ".join(str(m) for m in self.instance.sb.messages).lower()
        self.assertIn("non-manifold", joined)

        # Early return: downstream steps were skipped.
        self.assertEqual(self.optimize_calls, [])
        self.assertEqual(self.stack_calls, [])

    def test_successful_unfold_runs_downstream_steps(self):
        cmds.u3dUnfold = lambda *a, **k: None  # succeeds

        # orient=False avoids the mel texOrientShells dependency; the optimize
        # and stack stubs record that the post-unfold steps ran.
        self.instance.tb004(widget=_FakeUnfoldWidget(orient=False))

        self.assertFalse(self.instance.sb.messages)
        self.assertEqual(len(self.optimize_calls), 1)
        self.assertEqual(len(self.stack_calls), 1)


@unittest.skipUnless(_MAYA_AVAILABLE, "Requires maya.cmds")
class TestTb004NeverSeamCuts(unittest.TestCase):
    """Regression: tb004 (Unfold) relaxes existing UVs only — it must never cut
    new seams. A closed, single-shell ("seamless") mesh was previously routed to
    mtk.UvUtils.unwrap_cylinder, which polyMapCuts fresh seams in. Seaming is the
    job of the dedicated Cut Cylinder tool (tb009); Unfold must leave the UV
    layout's shell structure untouched.
    """

    def setUp(self):
        cmds.file(new=True, force=True)
        self.instance = uv_module.UvSlots.__new__(uv_module.UvSlots)
        self.instance.sb = _RecordedSb()
        self.instance.get_map_size = lambda: 2048

        # A closed cylinder with a single, sewn UV shell — the exact mesh the old
        # auto-cut path triggered on.
        self.mesh = cmds.polyCylinder(name="seamlessCyl")[0]
        cmds.polyMapSew(f"{self.mesh}.e[*]", constructionHistory=True)
        cmds.select(self.mesh, replace=True)

        self._missing = object()
        self._orig = {
            name: getattr(cmds, name, self._missing)
            for name in (
                "selectMode",
                "u3dUnfold",
                "u3dOptimize",
                "polyUVStackSimilarShells",
            )
        }
        cmds.selectMode = lambda *a, **k: False  # already-object: skip switch
        cmds.u3dUnfold = lambda *a, **k: None  # succeed without the Unfold3D plugin
        cmds.u3dOptimize = lambda *a, **k: None
        cmds.polyUVStackSimilarShells = lambda *a, **k: None

    def tearDown(self):
        for name, fn in self._orig.items():
            if fn is self._missing:
                if hasattr(cmds, name):
                    delattr(cmds, name)
            else:
                setattr(cmds, name, fn)
        cmds.file(new=True, force=True)

    def test_seamless_mesh_is_not_routed_through_seam_cutting(self):
        shells_before = cmds.polyEvaluate(self.mesh, uvShell=True)
        with mock.patch.object(
            mtk.UvUtils, "unwrap_cylinder"
        ) as unwrap, mock.patch.object(cmds, "polyMapCut") as map_cut:
            self.instance.tb004(widget=_FakeUnfoldWidget(orient=False, stack=False))
        unwrap.assert_not_called()
        map_cut.assert_not_called()
        self.assertEqual(
            cmds.polyEvaluate(self.mesh, uvShell=True),
            shells_before,
            "Unfold must not add UV shells (no new seams) on a seamless mesh",
        )


@unittest.skipUnless(_MAYA_AVAILABLE, "Requires maya.cmds")
class TestTb004NonManifoldStrategy(unittest.TestCase):
    """tb004's non-manifold strategy combo: Warn + Select vs Repair + Retry.

    Drives the real polyInfo / clean_geometry / selection paths against a real
    bowtie mesh; only u3dUnfold is stubbed (its Unfold3D plugin need not load).
    """

    def setUp(self):
        cmds.file(new=True, force=True)
        self.instance = uv_module.UvSlots.__new__(uv_module.UvSlots)
        self.instance.sb = _RecordedSb()
        self.instance.get_map_size = lambda: 2048

        # Two planes sharing a single corner vertex → one non-manifold (bowtie) vert.
        p1 = cmds.polyPlane(w=1, h=1, sx=1, sy=1)[0]
        p2 = cmds.polyPlane(w=1, h=1, sx=1, sy=1)[0]
        cmds.move(1, 0, 1, p2)
        self.mesh = cmds.polyUnite(p1, p2, ch=False)[0]
        cmds.polyMergeVertex(self.mesh, d=0.001, ch=False)
        self.shape = cmds.listRelatives(self.mesh, shapes=True, ni=True)[0]
        cmds.select(self.mesh)

        self._orig_unfold = getattr(cmds, "u3dUnfold", None)

        def _raise(*a, **k):
            raise RuntimeError(
                "Mesh has non-manifold vertices. Clean up the mesh before using unfold."
            )

        cmds.u3dUnfold = _raise

    def tearDown(self):
        if self._orig_unfold is None:
            if hasattr(cmds, "u3dUnfold"):
                del cmds.u3dUnfold
        else:
            cmds.u3dUnfold = self._orig_unfold
        cmds.file(new=True, force=True)

    def test_select_mode_selects_and_warns(self):
        self.instance.tb004(widget=_FakeUnfoldWidget(nonmanifold_mode="select"))

        sel = cmds.ls(sl=True, flatten=True) or []
        self.assertTrue(sel, "expected the non-manifold vertices to be selected")
        self.assertTrue(
            all(".vtx[" in s for s in sel), f"expected vtx components, got {sel}"
        )
        joined = " ".join(str(m) for m in self.instance.sb.messages).lower()
        self.assertIn("non-manifold", joined)
        self.assertIn("vertex mode", joined)

    def test_does_not_preempt_unfold_on_polyinfo_flag(self):
        # Regression ("unfold fails on every mesh"): tb004 must NOT abort based on
        # a polyInfo non-manifold scan. u3dUnfold's rejection is narrower than
        # polyInfo's topological flag, so when u3dUnfold accepts this mesh (here:
        # stubbed to succeed) the unfold proceeds — no warn, no vertex re-select —
        # even though polyInfo reports the bowtie vert as non-manifold.
        self.assertTrue(  # precondition: polyInfo does flag this mesh
            self.instance._non_manifold_vertices([self.mesh]),
            "fixture should be polyInfo-non-manifold",
        )
        cmds.u3dUnfold = lambda *a, **k: None  # u3dUnfold tolerates it

        self.instance.tb004(
            widget=_FakeUnfoldWidget(
                nonmanifold_mode="select", optimize=False, orient=False, stack=False
            )
        )

        self.assertFalse(
            self.instance.sb.messages, "unfold should proceed, not warn + abort"
        )
        sel = cmds.ls(sl=True, flatten=True) or []
        self.assertFalse(
            any(".vtx[" in s for s in sel), f"should not select vertices, got {sel}"
        )

    def test_repair_mode_repairs_and_retries(self):
        # u3dUnfold itself gates unfoldability (its non-manifold rejection is
        # narrower than polyInfo's flag), so we must NOT pre-empt on a polyInfo
        # scan. The first real unfold fails, the repair runs, and the retry — on
        # the now-manifold mesh — succeeds, all in one click.
        calls = {"n": 0}

        def _unfold(*a, **k):
            calls["n"] += 1
            if cmds.polyInfo(self.shape, nonManifoldVertices=True):
                raise RuntimeError(
                    "Mesh has non-manifold vertices. Clean up the mesh before using unfold."
                )
            return None  # post-repair retry succeeds on the cleaned mesh

        cmds.u3dUnfold = _unfold

        self.instance.tb004(
            widget=_FakeUnfoldWidget(
                nonmanifold_mode="repair", optimize=False, orient=False, stack=False
            )
        )

        self.assertEqual(calls["n"], 2, "expected u3dUnfold to be retried after repair")
        # The real clean_geometry actually made the mesh manifold.
        self.assertIsNone(cmds.polyInfo(self.shape, nonManifoldVertices=True))
        joined = " ".join(str(m) for m in self.instance.sb.messages).lower()
        self.assertIn("repair", joined)

    def test_repair_mode_falls_back_when_unrepairable(self):
        # clean_geometry no-op → the mesh stays non-manifold, the retry fails, and
        # tb004 falls back to Warn + Select.
        with mock.patch.object(mtk.Diagnostics, "clean_geometry", lambda *a, **k: None):
            self.instance.tb004(
                widget=_FakeUnfoldWidget(
                    nonmanifold_mode="repair", optimize=False, orient=False, stack=False
                )
            )

        sel = cmds.ls(sl=True, flatten=True) or []
        self.assertTrue(
            any(".vtx[" in s for s in sel), f"expected vtx selection, got {sel}"
        )
        joined = " ".join(str(m) for m in self.instance.sb.messages).lower()
        self.assertIn("non-manifold", joined)

    def test_repair_mode_survives_cleanup_error(self):
        # A raising clean_geometry must not escape tb004 — it degrades to the
        # retry, which fails, falling back to Warn + Select.
        def _boom(*a, **k):
            raise RuntimeError("polyCleanup failed")

        with mock.patch.object(mtk.Diagnostics, "clean_geometry", _boom):
            self.instance.tb004(  # must not raise
                widget=_FakeUnfoldWidget(
                    nonmanifold_mode="repair", optimize=False, orient=False, stack=False
                )
            )

        joined = " ".join(str(m) for m in self.instance.sb.messages).lower()
        self.assertIn("non-manifold", joined)


@unittest.skipUnless(_MAYA_AVAILABLE, "Requires maya.cmds")
class TestTb004ObjectModeGuard(unittest.TestCase):
    """tb004 must normalize a component selection to object mode before unfolding.

    The whole-object u3dUnfold behaves non-deterministically when a leftover
    component selection scopes it to a sub-shell, which is what made the repair
    flow appear to need a second click. (Regression: the guard's condition was
    inverted, so it never switched out of component mode.)

    selectMode is spied rather than queried for real: mayapy.standalone doesn't
    track interactive selection mode, so a real query is unreliable here. The
    spy reports "not in object mode" and records any switch — under the old
    inverted guard no switch is issued, so this fails before the fix.
    """

    def setUp(self):
        cmds.file(new=True, force=True)
        self.instance = uv_module.UvSlots.__new__(uv_module.UvSlots)
        self.instance.sb = _RecordedSb()
        self.instance.get_map_size = lambda: 2048

        self.mesh = cmds.polyPlane(w=1, h=1, sx=2, sy=2)[0]  # clean, manifold
        cmds.polyAutoProjection(self.mesh, ch=False)
        cmds.select(self.mesh, r=True)

        self._orig_selectMode = cmds.selectMode
        self._orig_unfold = getattr(cmds, "u3dUnfold", None)
        self.switched_to_object = []

        def _selectMode(*a, **k):
            if k.get("query") or k.get("q"):
                return False  # report: not currently in object mode
            if k.get("object"):
                self.switched_to_object.append(True)
            return self._orig_selectMode(*a, **k)

        cmds.selectMode = _selectMode
        self.unfold_calls = []
        cmds.u3dUnfold = lambda *a, **k: self.unfold_calls.append((a, k))

    def tearDown(self):
        cmds.selectMode = self._orig_selectMode
        if self._orig_unfold is None:
            if hasattr(cmds, "u3dUnfold"):
                del cmds.u3dUnfold
        else:
            cmds.u3dUnfold = self._orig_unfold
        cmds.file(new=True, force=True)

    def test_non_object_mode_is_switched_before_unfold(self):
        self.instance.tb004(
            widget=_FakeUnfoldWidget(orient=False, stack=False, optimize=False)
        )

        # The guard issued a switch to object mode, then unfolded once cleanly.
        self.assertTrue(
            self.switched_to_object,
            "tb004 should switch to object mode when not already in it",
        )
        self.assertEqual(len(self.unfold_calls), 1)
        self.assertFalse(self.instance.sb.messages)


if __name__ == "__main__":
    unittest.main()
