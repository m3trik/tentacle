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

from _host import MAYA_AVAILABLE as _MAYA_AVAILABLE, maya_module
from uitk.widgets.mixins.tooltip_mixin import TooltipFormat

cmds = maya_module("maya.cmds")
mtk = maya_module("mayatk")
uv_module = maya_module("tentacle.slots.maya.uv")


class _FakeCmb:
    def __init__(self, text):
        self._t = text

    def currentText(self):
        return self._t


class _FakeUi:
    pass


class _RecordedProgress:
    """The slice of ``Switchboard.progress`` a slot actually uses.

    The long-running UV slots wrap their engine call in the footer's
    task-indicator context; a double without it turns every one of those
    slots into an AttributeError. Records the status texts so a test can
    assert a slot reported what it was doing.
    """

    def __init__(self, log, text):
        self._log = log
        self._text = text

    def __enter__(self):
        self._log.append(self._text)
        return self._tick

    def _tick(self, value=None, text=None):
        """``update(value, text)`` -- a text re-labels the running task."""
        if text:
            self._log.append(text)
        return True  # never cancelled

    def __exit__(self, *exc):
        return False


class _RecordedSb:
    def __init__(self):
        self.messages = []
        self.progress_texts = []

    def message_box(self, *args, **kwargs):
        self.messages.append((args, kwargs))

    def progress(self, ui=None, total=None, text=""):
        return _RecordedProgress(self.progress_texts, text)


class _FakeB000Widget:
    """b000's option-box surface -- the merged Transfer UV Set / Textures tool.

    b000 reads every row up front (both passes share one option box), so a
    double that carries only the two rows a given test cares about turns every
    call into an AttributeError from an unrelated row. Defaults describe the
    common case: source = first selected, scope = selection order, UV pass on,
    texture pass off.
    """

    class _Combo:
        def __init__(self, data):
            self._data = data

        def currentData(self):
            return self._data

    class _Spin:
        def __init__(self, value):
            self._value = value

        def value(self):
            return self._value

    class _Check:
        def __init__(self, checked):
            self._checked = checked

        def isChecked(self):
            return self._checked

    class _Text:
        def __init__(self, text):
            self._text = text

        def text(self):
            return self._text

    def __init__(
        self,
        scope="order",
        tolerance=0.9,
        mode="first",
        transfer="uvs",
        output_name="transfer_result",
    ):
        menu = _FakeUi()
        menu.cmb024 = self._Combo(mode)  # Source
        menu.cmb014 = self._Combo(scope)  # Scope
        menu.d000 = self._Spin(tolerance)  # Similarity
        menu.cmb028 = self._Combo(transfer)  # Transfer: uvs / textures / auto
        # Texture-pass rows -- read even when the pass is off.
        menu.t_tt_name = self._Text(output_name)
        menu.t_tt_src_uvset = self._Text("")
        menu.t_tt_dst_uvset = self._Text("")
        menu.t_tt_output = self._Text("")
        menu.cmb025 = self._Combo(0)  # Resolution
        menu.cmb026 = self._Combo(2)  # Quality
        menu.s025 = self._Spin(-1)  # Padding
        menu.cmb027 = self._Combo(None)  # Normal convention
        menu.chk050 = self._Check(True)  # Assign Result
        self.option_box = _FakeUi()
        self.option_box.menu = menu


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

        # Capture mtk.transfer_uvs calls. `self.space` is the sample space the
        # engine reports back per pair -- anything but "topology" means the pair
        # was approximated, which b000 must surface to the user.
        import mayatk as mtk

        self._original = mtk.transfer_uvs
        self.captured = []
        self.space = "topology"

        def fake_transfer(frm, to, **kwargs):
            self.captured.append((frm, to, kwargs))
            sources = frm if isinstance(frm, (list, tuple)) else [frm]
            targets = to if isinstance(to, (list, tuple)) else [to]
            return [(s, t, self.space) for s, t in zip(sources * len(targets), targets)]

        mtk.transfer_uvs = fake_transfer

    @staticmethod
    def _leaves(names):
        """Leaf names of a bulk argument -- b000 pairs on FULL DAG paths."""
        if not isinstance(names, (list, tuple)):
            names = [names]
        return [str(n).rsplit("|", 1)[-1] for n in names]

    def tearDown(self):
        import mayatk as mtk

        mtk.transfer_uvs = self._original
        cmds.file(new=True, force=True)

    def test_no_selection_warns_and_skips(self):
        cmds.select(clear=True)
        self.instance.b000(widget=_FakeB000Widget())
        self.assertEqual(self.captured, [])
        self.assertTrue(self.instance.sb.messages)

    def test_one_object_warns_and_skips(self):
        a = cmds.polyCube(name="uv_b000_one")[0]
        cmds.select(a)
        self.instance.b000(widget=_FakeB000Widget())
        self.assertEqual(self.captured, [])
        self.assertTrue(self.instance.sb.messages)

    def test_two_objects_transfer_as_one_pair(self):
        a = cmds.polyCube(name="uv_b000_a")[0]
        b = cmds.polyCube(name="uv_b000_b")[0]
        cmds.select([a, b])

        self.instance.b000(widget=_FakeB000Widget())

        # The engine takes the pairing in bulk: sources[] -> targets[].
        self.assertEqual(len(self.captured), 1)
        sources, targets, kwargs = self.captured[0]
        self.assertEqual(self._leaves(sources), [a])
        self.assertEqual(self._leaves(targets), [b])
        # The selection order IS the correspondence; re-vetting it by geometric
        # similarity would silently drop pairs the user named deliberately.
        self.assertIs(kwargs.get("match_by_similarity"), False)

    def test_the_footer_reports_the_running_task(self):
        """A transfer over many meshes freezes the UI for its duration; the
        footer is what says *why*, so the busy context is part of the slot's
        contract rather than a decoration."""
        a = cmds.polyCube(name="uv_b000_p1")[0]
        b = cmds.polyCube(name="uv_b000_p2")[0]
        cmds.select([a, b])
        self.instance.b000(widget=_FakeB000Widget())
        self.assertTrue(
            any("Transfer UV Set" in t for t in self.instance.sb.progress_texts),
            self.instance.sb.progress_texts,
        )

    def test_the_footer_relabels_itself_for_the_texture_pass(self):
        """One indicator spans both passes, so it has to say which is running
        -- the texture remap is the one that freezes the UI for minutes."""
        a = cmds.polyCube(name="uv_b000_p3")[0]
        b = cmds.polyCube(name="uv_b000_p4")[0]
        cmds.select([a, b])
        widget = _FakeB000Widget(transfer="textures")
        self.instance.b000(widget=widget)
        self.assertIn("Working: Transfer Textures", self.instance.sb.progress_texts)

    def test_the_texture_pass_is_refused_without_an_output_name(self):
        """It names the material AND every map; there is no safe default, and
        finding out after the remap has run costs the whole run."""
        a = cmds.polyCube(name="uv_b000_noname_a")[0]
        b = cmds.polyCube(name="uv_b000_noname_b")[0]
        cmds.select([a, b])
        self.instance.b000(
            widget=_FakeB000Widget(transfer="textures", output_name="  ")
        )
        self.assertEqual(self.captured, [])  # refused before any pass ran
        self.assertIn(
            "output name",
            "".join(str(m) for m in self.instance.sb.messages).lower(),
        )

    def test_three_objects_pair_the_source_against_every_target(self):
        a = cmds.polyCube(name="uv_b000_a3")[0]
        b = cmds.polyCube(name="uv_b000_b3")[0]
        c = cmds.polyCube(name="uv_b000_c3")[0]
        cmds.select([a, b, c])

        self.instance.b000(widget=_FakeB000Widget())

        # frm=a paired against each of [b, c], in one bulk call.
        self.assertEqual(len(self.captured), 1)
        sources, targets, _ = self.captured[0]
        self.assertEqual(set(self._leaves(sources)), {a})
        self.assertEqual(set(self._leaves(targets)), {b, c})

    def test_exact_transfer_stays_silent(self):
        """A topology-space transfer is exact; popping a dialog on every routine
        use would be noise."""
        a = cmds.polyCube(name="uv_b000_quiet_a")[0]
        b = cmds.polyCube(name="uv_b000_quiet_b")[0]
        cmds.select([a, b])

        self.instance.b000(widget=_FakeB000Widget())

        self.assertEqual(len(self.captured), 1)
        # One report is always posted; it must not carry an approximation warning.
        self.assertNotIn(
            "proximity", "".join(str(m) for m in self.instance.sb.messages)
        )

    def test_approximated_transfer_is_reported(self):
        """A target that didn't match the source's topology was sampled by
        proximity -- the user has to be told, or an approximate result looks
        identical to an exact one until they inspect the UVs."""
        self.space = "object"
        a = cmds.polyCube(name="uv_b000_approx_a")[0]
        b = cmds.polyCube(name="uv_b000_approx_b")[0]
        c = cmds.polyCube(name="uv_b000_approx_c")[0]
        cmds.select([a, b, c])

        self.instance.b000(widget=_FakeB000Widget())

        self.assertEqual(len(self.captured), 1)  # one bulk call, both pairs
        self.assertEqual(len(self.instance.sb.messages), 1)
        args, _kwargs = self.instance.sb.messages[0]
        message = args[0]
        self.assertIn("2", message)  # both pairs counted, not just the last
        self.assertIn("proximity", message.lower())


@unittest.skipUnless(_MAYA_AVAILABLE, "Requires maya.cmds")
class TestB000TransferAuto(unittest.TestCase):
    """Transfer: Auto -- b000 picks the pass from the SOURCE's materials."""

    def setUp(self):
        cmds.file(new=True, force=True)
        self.instance = uv_module.UvSlots.__new__(uv_module.UvSlots)
        self.instance.sb = _RecordedSb()

        # Capture mtk.transfer_uvs so the UV pass is observable without
        # touching real UVs (mirrors TestB000TransferUVsGate's harness).
        import mayatk as mtk

        self._original = mtk.transfer_uvs
        self.captured = []

        def fake_transfer(frm, to, **kwargs):
            self.captured.append((frm, to, kwargs))
            sources = frm if isinstance(frm, (list, tuple)) else [frm]
            targets = to if isinstance(to, (list, tuple)) else [to]
            return [(s, t, "topology") for s, t in zip(sources * len(targets), targets)]

        mtk.transfer_uvs = fake_transfer

    def tearDown(self):
        import mayatk as mtk

        mtk.transfer_uvs = self._original
        cmds.file(new=True, force=True)

    def test_a_mapped_source_resolves_to_the_texture_pass(self):
        """A source whose material carries a map has textures to move, so Auto
        must pick the texture pass -- observed through that pass's own gate:
        it demands an Output Name before touching anything, and the refusal
        has to say Auto made the pick (the user never chose Textures)."""
        src = cmds.polyCube(name="uv_auto_mapped_src")[0]
        tgt = cmds.polyCube(name="uv_auto_mapped_tgt")[0]
        mat = cmds.shadingNode("lambert", asShader=True, name="uv_auto_mat")
        sg = cmds.sets(
            renderable=True, noSurfaceShader=True, empty=True, name="uv_auto_sg"
        )
        cmds.connectAttr(f"{mat}.outColor", f"{sg}.surfaceShader")
        file_node = cmds.shadingNode("file", asTexture=True)
        cmds.setAttr(
            f"{file_node}.fileTextureName",
            "sourceimages/uv_auto_map.png",
            type="string",
        )
        cmds.connectAttr(f"{file_node}.outColor", f"{mat}.color")
        cmds.sets(src, edit=True, forceElement=sg)
        cmds.select([src, tgt])

        self.instance.b000(widget=_FakeB000Widget(transfer="auto", output_name=""))

        self.assertEqual(self.captured, [])  # no UV pass ran
        message = "".join(str(m) for m in self.instance.sb.messages)
        self.assertIn("Output Name required", message)
        self.assertIn("Auto", message)

    def test_an_unmapped_source_resolves_to_the_uv_pass(self):
        """No maps on the source's materials: nothing for the texture pass to
        read, so Auto transfers the layout instead -- with no Output Name
        demanded, since no texture is written."""
        a = cmds.polyCube(name="uv_auto_plain_a")[0]
        b = cmds.polyCube(name="uv_auto_plain_b")[0]
        cmds.select([a, b])

        self.instance.b000(widget=_FakeB000Widget(transfer="auto", output_name=""))

        self.assertEqual(len(self.captured), 1)
        self.assertIn("Working: Transfer UV Set", self.instance.sb.progress_texts)


@unittest.skipUnless(_MAYA_AVAILABLE, "Requires maya.cmds")
class TestB005CutUVsRouting(unittest.TestCase):
    """b005 (Cut UVs) routes to polyMapCut differently for edges vs transforms."""

    def setUp(self):
        cmds.file(new=True, force=True)
        self.instance = uv_module.UvSlots.__new__(uv_module.UvSlots)
        self.instance.sb = _RecordedSb()

        # Capture polyMapCut calls. Accept **kwargs like the real command (and
        # like the polyMapSew fake below): the edge branch routes through
        # ``mtk.UvUtils.cut_uv_edges``, which passes ``constructionHistory=`` —
        # a positional-only fake turned an upstream signature change into a
        # TypeError *inside* the slot, which reads as a slot regression.
        self._original = cmds.polyMapCut
        self.captured = []
        self.captured_kwargs = []

        def _fake_cut(*args, **kwargs):
            self.captured.append(args[0] if args else None)
            self.captured_kwargs.append(kwargs)

        cmds.polyMapCut = _fake_cut

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
        # The edge branch goes through cut_uv_edges, which keeps construction
        # history — pin the kwarg so a silent upstream drop is caught here.
        self.assertTrue(
            all(k.get("constructionHistory") for k in self.captured_kwargs),
            f"expected constructionHistory=True on every cut; got {self.captured_kwargs}",
        )

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
        self.assertEqual(uv_module.UvSlots._classify_u3d_error(err), "overlapping UVs")

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

        # An operand: tb004 now guards on an empty selection (see
        # TestTb004EmptySelectionGuard), so the control-flow cases below need
        # something selected to get past it.
        cmds.select(cmds.polyCube()[0], replace=True)

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
class TestUvEmptySelectionGuard(unittest.TestCase):
    """A selection-driven UV command run with nothing selected must report it in
    a message box — never as a traceback.

    Regression: tb004 (Unfold) read the selection without guarding it. u3dUnfold
    merely logged "This command requires at least 1 argument(s)", but the orient
    pass is MEL (texOrientShells -> texCheckSelection), which raises
    RuntimeError — so an empty selection surfaced to the user as an unhandled
    traceback out of the slot dispatcher.
    """

    def setUp(self):
        cmds.file(new=True, force=True)  # nothing selected
        self.instance = uv_module.UvSlots.__new__(uv_module.UvSlots)
        self.instance.sb = _RecordedSb()
        self.instance.get_map_size = lambda: 2048

        self._missing = object()
        self._orig = {
            name: getattr(cmds, name, self._missing)
            for name in ("selectMode", "u3dUnfold", "u3dOptimize")
        }
        self.unfold_calls = []
        cmds.selectMode = lambda *a, **k: False
        cmds.u3dUnfold = lambda *a, **k: self.unfold_calls.append((a, k))
        cmds.u3dOptimize = lambda *a, **k: None

    def tearDown(self):
        for name, fn in self._orig.items():
            if fn is self._missing:
                if hasattr(cmds, name):
                    delattr(cmds, name)
            else:
                setattr(cmds, name, fn)
        cmds.file(new=True, force=True)

    def _assert_reported_empty(self):
        self.assertTrue(self.instance.sb.messages, "expected a message box")
        joined = " ".join(str(m) for m in self.instance.sb.messages).lower()
        self.assertIn("nothing selected", joined)

    def test_tb004_reports_instead_of_raising(self):
        # orient=True is the shipped default and the exact path that raised.
        self.instance.tb004(widget=_FakeUnfoldWidget(orient=True))

        self._assert_reported_empty()
        self.assertEqual(self.unfold_calls, [], "must not reach u3dUnfold")

    def test_b021_reports_once_and_skips_both_steps(self):
        """Unfold+Pack must not fire the guard twice (once per chained step)."""
        called = []

        class _Btn:
            def __init__(self, name):
                self.name = name

            def call_slot(self, *a, **k):
                called.append(self.name)

        self.instance.ui = _FakeUi()
        self.instance.ui.tb004 = _Btn("tb004")
        self.instance.ui.tb000 = _Btn("tb000")

        self.instance.b021(widget=None)

        self._assert_reported_empty()
        self.assertEqual(len(self.instance.sb.messages), 1)
        self.assertEqual(called, [], "neither chained step should run")

    def test_b011_sew_reports_instead_of_silently_doing_nothing(self):
        self.instance.b011()
        self._assert_reported_empty()

    def test_b005_cut_reports(self):
        self.instance.b005()
        self._assert_reported_empty()


class _FakeCutCylinderMenu:
    """tb009's option box: s021 / s022 / s023 / s016 / chk045 / chk040 /
    chk046 / chk041 / chk042."""

    def __init__(
        self,
        angle=45,
        taper=20,
        flat=60,
        fillet=12,
        hide=True,
        invert=False,
        keep_seams=False,
        unfold=True,
        orient=True,
    ):
        self.s021 = _FakeSpin(taper)  # Taper Angle
        self.s022 = _FakeSpin(flat)  # Flat Angle
        self.s023 = _FakeSpin(fillet)  # Fillet Size (%)
        self.s016 = _FakeSpin(angle)  # Crease Angle
        self.chk045 = _FakeCheck(hide)  # Hide Seam From View
        self.chk040 = _FakeCheck(invert)  # Invert Seam
        self.chk046 = _FakeCheck(keep_seams)  # Keep Existing Seams
        self.chk041 = _FakeCheck(unfold)  # Unfold
        self.chk042 = _FakeCheck(orient)  # Orient


class _FakeCutCylinderWidget:
    def __init__(self, **kwargs):
        self.option_box = _FakeOptionBox(_FakeCutCylinderMenu(**kwargs))


@unittest.skipUnless(_MAYA_AVAILABLE, "Requires maya.cmds")
class TestTb009CutCylinder(unittest.TestCase):
    """tb009 (Cut Cylinder) hands the option box straight to
    mtk.UvUtils.unwrap_cylinder -- in particular the seam-hiding camera: the
    active viewport camera when "Hide Seam From View" is on and a view
    exists, else None (mayatk then falls back to a fixed default side)."""

    def setUp(self):
        cmds.file(new=True, force=True)
        self.instance = uv_module.UvSlots.__new__(uv_module.UvSlots)
        self.instance.sb = _RecordedSb()
        self.instance.get_map_size = lambda: 2048
        self.mesh = cmds.polyCylinder(name="cutCyl")[0]
        cmds.select(self.mesh, replace=True)

    def tearDown(self):
        cmds.file(new=True, force=True)

    def _run(self, camera_lookup, **menu):
        with (
            mock.patch.object(
                mtk.UvUtils, "unwrap_cylinder", return_value=[self.mesh]
            ) as unwrap,
            mock.patch.object(
                mtk.CamUtils, "get_current_cam", side_effect=camera_lookup
            ),
        ):
            self.instance.tb009(widget=_FakeCutCylinderWidget(**menu))
        unwrap.assert_called_once()
        return unwrap.call_args.kwargs

    def test_hide_from_view_passes_the_viewport_camera(self):
        kwargs = self._run(
            lambda: "|persp|perspShape", hide=True, invert=True, angle=30
        )
        self.assertEqual(kwargs["camera"], "|persp|perspShape")
        self.assertTrue(kwargs["invert_seam"])
        self.assertEqual(kwargs["angle"], 30)
        self.assertEqual(kwargs["map_size"], 2048)

    def test_preference_knobs_pass_through(self):
        """Taper / Flat / Fillet Size and Keep Existing Seams reach
        unwrap_cylinder as taper_angle / flat_angle / trim_ratio / sew."""
        kwargs = self._run(lambda: None, taper=25, flat=45, fillet=8, keep_seams=True)
        self.assertEqual(kwargs["taper_angle"], 25)
        self.assertEqual(kwargs["flat_angle"], 45)
        self.assertAlmostEqual(kwargs["trim_ratio"], 0.08)
        self.assertFalse(kwargs["sew"])
        kwargs = self._run(lambda: None)
        self.assertEqual(
            (kwargs["taper_angle"], kwargs["flat_angle"], kwargs["sew"]), (20, 60, True)
        )
        self.assertAlmostEqual(kwargs["trim_ratio"], 0.12)

    def test_hide_off_passes_no_camera(self):
        kwargs = self._run(lambda: "|persp|perspShape", hide=False)
        self.assertIsNone(kwargs["camera"])

    def test_no_active_view_falls_back_to_no_camera(self):
        """Headless / no 3D view: M3dView raises -- the slot must not."""

        def boom():
            raise RuntimeError("no active 3d view")

        kwargs = self._run(boom, hide=True)
        self.assertIsNone(kwargs["camera"])

    def test_nothing_selected_reports_and_stops(self):
        cmds.select(clear=True)
        with mock.patch.object(mtk.UvUtils, "unwrap_cylinder") as unwrap:
            self.instance.tb009(widget=_FakeCutCylinderWidget())
        unwrap.assert_not_called()
        self.assertEqual(len(self.instance.sb.messages), 1)


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
        with (
            mock.patch.object(mtk.UvUtils, "unwrap_cylinder") as unwrap,
            mock.patch.object(cmds, "polyMapCut") as map_cut,
        ):
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


class _FakeTb001Widget:
    """tb001's option-box surface: mode combo (cmb011) + scale mode (cmb012)."""

    class _Combo:
        def __init__(self, data):
            self._data = data

        def currentData(self):
            return self._data

    def __init__(self, mode="standard", scale_mode=1):
        menu = _FakeUi()
        menu.cmb011 = self._Combo(mode)
        menu.cmb012 = self._Combo(scale_mode)
        self.option_box = _FakeUi()
        self.option_box.menu = menu


@unittest.skipUnless(_MAYA_AVAILABLE, "Requires maya.cmds")
class TestTb001AutoUnwrapDispatch(unittest.TestCase):
    """tb001 routes the engine modes to UvUtils.auto_unwrap and reports failures."""

    def setUp(self):
        cmds.file(new=True, force=True)
        self.instance = uv_module.UvSlots.__new__(uv_module.UvSlots)
        self.instance.sb = _RecordedSb()
        self.instance.ui = _FakeUi()
        self.instance.ui.cmb003 = _FakeCmb("2048")

        self.calls = []
        self._original = mtk.UvUtils.auto_unwrap

        def fake_auto_unwrap(objects, method=None, map_size=None, **kwargs):
            self.calls.append((objects, method, map_size))
            return mock.Mock(engine="mof", succeeded=list(objects), failed=[])

        mtk.UvUtils.auto_unwrap = staticmethod(fake_auto_unwrap)

    def tearDown(self):
        mtk.UvUtils.auto_unwrap = self._original
        cmds.file(new=True, force=True)

    def test_hard_mode_calls_the_engine_with_selection_and_map_size(self):
        cube = cmds.polyCube(name="tb001_hard")[0]
        cmds.select(cube)
        self.instance.tb001(widget=_FakeTb001Widget(mode="hard"))
        self.assertEqual(len(self.calls), 1)
        objects, method, map_size = self.calls[0]
        self.assertEqual(method, "hard")
        self.assertEqual(map_size, 2048)
        self.assertIn(cube, objects)

    def test_organic_mode_selects_the_organic_method(self):
        cmds.select(cmds.polyCube(name="tb001_organic")[0])
        self.instance.tb001(widget=_FakeTb001Widget(mode="organic"))
        self.assertEqual(self.calls[0][1], "organic")

    def test_standard_mode_does_not_call_the_engine(self):
        cmds.select(cmds.polyCube(name="tb001_standard")[0])
        self.instance.tb001(widget=_FakeTb001Widget(mode="standard"))
        self.assertEqual(self.calls, [])

    def test_missing_engine_is_reported_not_raised(self):
        def boom(*args, **kwargs):
            raise FileNotFoundError("not installed: https://example/download")

        mtk.UvUtils.auto_unwrap = staticmethod(boom)
        cmds.select(cmds.polyCube(name="tb001_missing")[0])
        self.instance.tb001(widget=_FakeTb001Widget(mode="hard"))
        self.assertTrue(self.instance.sb.messages)
        self.assertIn("https://", str(self.instance.sb.messages[0]))

    def test_no_selection_warns(self):
        cmds.select(clear=True)
        self.instance.tb001(widget=_FakeTb001Widget(mode="hard"))
        self.assertEqual(self.calls, [])
        self.assertTrue(self.instance.sb.messages)


class TestUvSlotSurface(unittest.TestCase):
    """Source-level pins — run in CI, where no DCC is importable.

    The Auto Unwrap option box was trimmed to three modes on 2026-07-28 and the
    Cut Cylinder algorithm picker was replaced by per-mesh detection; these keep
    the removed widgets from creeping back and keep both DCCs' labels identical
    (the parity sweep matches combo items by text).
    """

    ENGINE_LABELS = ("Hard Surface (Ministry of Flat)", "Organic (BFF)")
    REMOVED = ("cmb016", "cmb017", "chk000")

    def _source(self, dcc):
        import os

        path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "tentacle",
            "slots",
            dcc,
            "uv.py",
        )
        with open(path, encoding="utf-8") as f:
            return f.read()

    def test_engine_labels_match_across_dccs(self):
        for dcc in ("maya", "blender"):
            source = self._source(dcc)
            for label in self.ENGINE_LABELS:
                self.assertIn(label, source, f"{dcc} is missing {label!r}")

    def test_removed_widgets_are_gone(self):
        source = self._source("maya")
        for name in self.REMOVED:
            self.assertNotIn(name, source, f"{name} should have been removed")

    def test_both_slots_mix_in_the_shared_uv_behavior(self):
        for dcc in ("maya", "blender"):
            self.assertIn("UvMixin", self._source(dcc), f"{dcc} lost UvMixin")

    def test_engine_modes_route_through_the_shared_helper(self):
        for dcc in ("maya", "blender"):
            self.assertIn("_run_auto_unwrap", self._source(dcc))


class _FakeTb000Widget:
    """tb000's option-box surface with the same defaults as tb000_init."""

    class _Combo:
        def __init__(self, data):
            self._data = data

        def currentData(self):
            return self._data

    class _Spin:
        def __init__(self, value):
            self._value = value

        def value(self):
            return self._value

    class _Check:
        def __init__(self, checked):
            self._checked = checked

        def isChecked(self):
            return self._checked

    def __init__(self, **overrides):
        defaults = dict(
            cmb019=self._Combo("standard"),  # Method: Standard (u3dLayout)
            cmb009=self._Combo(1),  # Pre-Scale: Preserve 3D
            cmb010=self._Combo(0),  # Pre-Rotate: Off
            s004=self._Spin(1001),  # UDIM
            s011=self._Spin(90),  # Rotate Step
            s012=self._Spin(0),  # Rotate Min
            s013=self._Spin(0),  # Rotate Max (0 = search disabled)
            s014=self._Spin(1),  # Mutations
            cmb015=self._Combo((1.0, 1.0)),  # Tile Coverage: Full
            cmb018=self._Combo(2),  # Scale Mode: Fill (uniform)
            s019=self._Spin(1),  # Tiles U
            s020=self._Spin(1),  # Tiles V
            chk016=self._Check(True),  # Skip Instances
            chk043=self._Check(False),  # Brute Force (xatlas)
            chk044=self._Check(True),  # Rotate Shells (xatlas)
        )
        defaults.update(overrides)
        menu = _FakeUi()
        for name, control in defaults.items():
            setattr(menu, name, control)
        self.option_box = _FakeUi()
        self.option_box.menu = menu


@unittest.skipUnless(_MAYA_AVAILABLE, "Requires maya.cmds")
class TestTb000Pack(unittest.TestCase):
    """tb000 (Pack UVs) — u3dLayout parameter plumbing, pinned against
    behavior verified live in Maya 2025 (probe session 2026-07-28):

    - packBox is [umin, umax, vmin, vmax]; the UDIM spinbox anchors it.
    - layoutScaleMode omitted == Uniform; 1 keeps shell scale exactly.
    - tileU/tileV distribute shells across a grid anchored at the pack box.
    - A single-mesh batch failure reports directly — no redundant probe pass.
    """

    @classmethod
    def setUpClass(cls):
        cmds.loadPlugin("Unfold3D", quiet=True)

    def setUp(self):
        cmds.file(new=True, force=True)
        self.instance = uv_module.UvSlots.__new__(uv_module.UvSlots)
        self.instance.sb = _RecordedSb()
        self.instance.ui = _FakeUi()
        self.instance.ui.cmb003 = _FakeCmb("1024")

    def tearDown(self):
        cmds.file(new=True, force=True)

    @staticmethod
    def _bbox2d(obj):
        return cmds.polyEvaluate(obj, boundingBox2d=True)

    def _message_text(self):
        return " ".join(str(args) for args, _ in self.instance.sb.messages)

    def test_default_pack_fills_target_tile(self):
        a = cmds.polyCube(name="packA", ch=False)[0]
        b = cmds.polyCube(name="packB", ch=False)[0]
        cmds.select(a, b)

        self.instance.tb000(widget=_FakeTb000Widget())

        for obj in (a, b):
            (u0, u1), (v0, v1) = self._bbox2d(obj)
            self.assertGreaterEqual(min(u0, v0), 0.0)
            self.assertLessEqual(max(u1, v1), 1.0)
        self.assertIn("UV Pack Complete", self._message_text())

    def test_udim_anchor_offsets_pack_box(self):
        a = cmds.polyCube(name="packA", ch=False)[0]
        cmds.select(a)

        self.instance.tb000(widget=_FakeTb000Widget(s004=_FakeTb000Widget._Spin(1002)))

        (u0, u1), _ = self._bbox2d(a)
        self.assertGreaterEqual(u0, 1.0)
        self.assertLessEqual(u1, 2.0)

    def test_scale_mode_off_preserves_shell_scale(self):
        a = cmds.polyPlane(name="packA", sx=1, sy=1, ch=False)[0]
        uvs = cmds.polyListComponentConversion(a, fromFace=True, toUV=True)
        cmds.polyEditUV(uvs, pivotU=0.0, pivotV=0.0, scaleU=0.3, scaleV=0.3)
        cmds.select(a)

        widget = _FakeTb000Widget(
            cmb009=_FakeTb000Widget._Combo(0),  # Preserve UV
            cmb018=_FakeTb000Widget._Combo(1),  # Scale Mode: Off
        )
        self.instance.tb000(widget=widget)

        (u0, u1), (v0, v1) = self._bbox2d(a)
        self.assertAlmostEqual(u1 - u0, 0.3, places=3)
        self.assertAlmostEqual(v1 - v0, 0.3, places=3)

    def test_tile_grid_spans_udims_and_reports_range(self):
        a = cmds.polyCube(name="packA", ch=False)[0]
        b = cmds.polyCube(name="packB", ch=False)[0]
        cmds.select(a, b)

        self.instance.tb000(widget=_FakeTb000Widget(s019=_FakeTb000Widget._Spin(2)))

        u_maxes = [self._bbox2d(obj)[0][1] for obj in (a, b)]
        u_mins = [self._bbox2d(obj)[0][0] for obj in (a, b)]
        self.assertGreater(max(u_maxes), 1.0, "grid should reach the second tile")
        self.assertLess(min(u_mins), 1.0, "grid should still use the first tile")
        self.assertIn("1001-1002", self._message_text())

    def test_tile_grid_clamps_to_udim_row_end(self):
        """UDIM 1010 sits at the row end (u=9): Tiles U 2 would pack past
        u=10, outside UDIM addressing, so it clamps to 1 and says so."""
        a = cmds.polyCube(name="packA", ch=False)[0]
        cmds.select(a)

        widget = _FakeTb000Widget(
            s004=_FakeTb000Widget._Spin(1010),
            s019=_FakeTb000Widget._Spin(2),
        )
        self.instance.tb000(widget=widget)

        (u0, u1), _ = self._bbox2d(a)
        self.assertGreaterEqual(u0, 9.0)
        self.assertLessEqual(u1, 10.0)
        text = self._message_text()
        self.assertIn("Target UDIM:</b> 1010", text)
        self.assertIn("clamped", text)

    def test_single_mesh_failure_reports_without_probe_pass(self):
        a = cmds.polyCube(name="packA", ch=False)[0]
        cmds.select(a)

        calls = []

        def boom(*args, **kwargs):
            calls.append((args, kwargs))
            raise RuntimeError("u3dLayout: non-manifold vertices")

        with mock.patch.object(uv_module.cmds, "u3dLayout", side_effect=boom):
            self.instance.tb000(widget=_FakeTb000Widget())

        self.assertEqual(len(calls), 1, "single mesh must not be re-probed")
        text = self._message_text()
        self.assertIn("Skipped: 1", text)
        self.assertIn("non-manifold", text)

    def test_xatlas_method_packs_into_target_tile(self):
        """Method: xatlas dispatches to mtk.UvUtils.pack_uvs and honors the
        UDIM anchor + coverage; u3dLayout is never called."""
        import pythontk as ptk

        if not ptk.UvPack.available():
            self.skipTest("xatlas not installed in this interpreter")
        a = cmds.polyCube(name="packA", ch=False)[0]
        b = cmds.polyCube(name="packB", ch=False)[0]
        cmds.select(a, b)

        widget = _FakeTb000Widget(
            cmb019=_FakeTb000Widget._Combo("xatlas"),
            s004=_FakeTb000Widget._Spin(1002),
        )
        with mock.patch.object(
            uv_module.cmds, "u3dLayout", side_effect=AssertionError("native packer ran")
        ):
            self.instance.tb000(widget=widget)

        for obj in (a, b):
            (u0, u1), (v0, v1) = self._bbox2d(obj)
            self.assertGreaterEqual(u0, 1.0)
            self.assertLessEqual(u1, 2.0)
            self.assertGreaterEqual(v0, 0.0)
            self.assertLessEqual(v1, 1.0)
        self.assertIn("UV Pack Complete", self._message_text())

    def test_xatlas_method_honors_a_face_selection(self):
        """User-reported: Method: xatlas only worked on a whole-object selection
        — a face / shell selection reported "No mesh objects to pack." and
        nothing moved. It must pack the selected faces into the target tile and
        leave the rest of the map alone."""
        import pythontk as ptk

        if not ptk.UvPack.available():
            self.skipTest("xatlas not installed in this interpreter")
        cube = cmds.polyCube(name="packA", ch=False)[0]
        cmds.polyMapCut(f"{cube}.e[*]", ch=False)  # six separate shells
        cmds.polyEditUV(f"{cube}.map[*]", u=5.0, v=5.0)  # park the map off-tile
        before = cmds.polyEditUV(f"{cube}.map[*]", query=True)
        scoped = {
            int(c.split("[")[1].rstrip("]"))
            for c in cmds.ls(
                cmds.polyListComponentConversion(f"{cube}.f[0:2]", toUV=True),
                flatten=True,
            )
        }
        cmds.select(f"{cube}.f[0:2]")

        widget = _FakeTb000Widget(cmb019=_FakeTb000Widget._Combo("xatlas"))
        self.instance.tb000(widget=widget)

        after = cmds.polyEditUV(f"{cube}.map[*]", query=True)
        moved = {
            i
            for i in range(len(before) // 2)
            if abs(before[2 * i] - after[2 * i]) > 1e-6
            or abs(before[2 * i + 1] - after[2 * i + 1]) > 1e-6
        }
        self.assertEqual(moved, scoped)
        for i in sorted(scoped):
            self.assertLessEqual(max(after[2 * i], after[2 * i + 1]), 1.0 + 1e-4)
        self.assertIn("UV Pack Complete", self._message_text())

    def test_standard_method_honors_a_face_selection(self):
        """The native packer's twin of the case above — both methods pack
        exactly the selected scope, so switching method can't change it."""
        cube = cmds.polyCube(name="packA", ch=False)[0]
        cmds.polyMapCut(f"{cube}.e[*]", ch=False)
        cmds.polyEditUV(f"{cube}.map[*]", u=5.0, v=5.0)
        before = cmds.polyEditUV(f"{cube}.map[*]", query=True)
        scoped = {
            int(c.split("[")[1].rstrip("]"))
            for c in cmds.ls(
                cmds.polyListComponentConversion(f"{cube}.f[0:2]", toUV=True),
                flatten=True,
            )
        }
        cmds.select(f"{cube}.f[0:2]")

        self.instance.tb000(widget=_FakeTb000Widget())

        after = cmds.polyEditUV(f"{cube}.map[*]", query=True)
        moved = {
            i
            for i in range(len(before) // 2)
            if abs(before[2 * i] - after[2 * i]) > 1e-6
            or abs(before[2 * i + 1] - after[2 * i + 1]) > 1e-6
        }
        self.assertTrue(moved)
        self.assertTrue(moved <= scoped, "the pack reached outside the selection")

    def test_xatlas_missing_engine_reports_install_note(self):
        """A missing engine must message (with the install command) and leave
        the scene untouched — not raise out of the slot."""
        a = cmds.polyCube(name="packA", ch=False)[0]
        cmds.select(a)
        before = self._bbox2d(a)

        widget = _FakeTb000Widget(cmb019=_FakeTb000Widget._Combo("xatlas"))
        with mock.patch.object(
            mtk.UvUtils,
            "pack_uvs",
            side_effect=RuntimeError("pip install --user xatlas"),
        ):
            self.instance.tb000(widget=widget)

        self.assertEqual(self._bbox2d(a), before)
        text = self._message_text()
        self.assertIn("pip install", text)


class _FakeStackWidget:
    """b030's option-box surface (UvMixin.b030_init): Mode (cmb020), Tolerance (s024),
    Pin after stack (chk047)."""

    def __init__(self, mode="similar", tolerance=1.0, pin=False):
        menu = _FakeUi()
        menu.cmb020 = _FakeDataCombo(mode)
        menu.s024 = _FakeSpin(tolerance)
        menu.chk047 = _FakeCheck(pin)
        self.option_box = _FakeOptionBox(menu)


@unittest.skipUnless(_MAYA_AVAILABLE, "Requires maya.cmds")
class TestB030Stack(unittest.TestCase):
    """b030 (Stack / Unstack) — Similar mode is Maya's polyUVStackSimilarShells (rotates
    identical shells into exact overlap), Center mode is texStackShells (translate only);
    the second click restores positions and prior pin weights."""

    def setUp(self):
        cmds.file(new=True, force=True)
        cmds.loadPlugin("Unfold3D.mll", quiet=True)
        self.instance = uv_module.UvSlots.__new__(uv_module.UvSlots)
        self.instance.sb = _RecordedSb()
        # __init__ is bypassed (it needs the loaded UI); seed the toggle state it owns.
        self.instance._b030_stacked = False
        self.instance._b030_last_selection = None
        self.instance._b030_uv_snapshot = None
        self.instance._b030_pin_weights = None
        # texStackShells is MEL over GUI-only selection-mask queries (fails headless);
        # capture the call instead — the command itself is Maya's, not ours.
        self._orig_eval = uv_module.mel.eval
        self.mel_calls = []
        uv_module.mel.eval = lambda cmd: self.mel_calls.append(cmd)

    def tearDown(self):
        uv_module.mel.eval = self._orig_eval
        cmds.file(new=True, force=True)

    # -- fixtures ------------------------------------------------------------
    @staticmethod
    def _twins(rotate=37.0, scale=1.0):
        """Two identical 2x2 planes; B's shell rotated / scaled / moved away from A's."""
        a = cmds.polyPlane(w=1, h=1, sx=2, sy=2, ch=False, name="stackA")[0]
        b = cmds.polyPlane(w=1, h=1, sx=2, sy=2, ch=False, name="stackB")[0]
        cmds.polyEditUV(f"{a}.map[*]", pu=0.5, pv=0.5, su=0.3, sv=0.3, r=True)
        cmds.polyEditUV(f"{a}.map[*]", u=-0.3, v=-0.3, r=True)
        cmds.polyEditUV(
            f"{b}.map[*]", pu=0.5, pv=0.5, su=0.3 * scale, sv=0.3 * scale, r=True
        )
        cmds.polyEditUV(f"{b}.map[*]", pu=0.5, pv=0.5, a=rotate, r=True)
        cmds.polyEditUV(f"{b}.map[*]", u=0.3, v=0.2, r=True)
        return a, b

    @staticmethod
    def _uvs(obj):
        n = cmds.polyEvaluate(obj, uv=True)
        return [tuple(cmds.polyEditUV(f"{obj}.map[{i}]", q=True)) for i in range(n)]

    @staticmethod
    def _max_dist(pa, pb):
        return max(
            ((x[0] - y[0]) ** 2 + (x[1] - y[1]) ** 2) ** 0.5 for x, y in zip(pa, pb)
        )

    def _pin(self, uv):
        return (cmds.polyPinUV(uv, q=True, value=True) or [0.0])[0]

    # -- tests ---------------------------------------------------------------
    def test_similar_mode_rotates_twins_into_exact_overlap_and_unstack_restores(self):
        a, b = self._twins()
        before_b = self._uvs(b)
        cmds.select(f"{a}.f[*]", f"{b}.f[*]")
        widget = _FakeStackWidget(mode="similar", tolerance=1.0)

        self.instance.b030(widget)
        self.assertLess(self._max_dist(self._uvs(a), self._uvs(b)), 1e-5)
        self.assertEqual(self.instance.sb.messages, [])
        self.assertEqual(self.mel_calls, [])  # not the translate-only path

        self.instance.b030(widget)  # same selection -> Unstack
        self.assertLess(self._max_dist(self._uvs(b), before_b), 1e-6)
        self.assertFalse(self.instance._b030_stacked)

    def test_similar_mode_matches_a_scaled_copy_too(self):
        a, b = self._twins(rotate=90.0, scale=0.5)
        cmds.select(f"{a}.f[*]", f"{b}.f[*]")
        self.instance.b030(_FakeStackWidget(mode="similar", tolerance=1.0))
        self.assertLess(self._max_dist(self._uvs(a), self._uvs(b)), 1e-5)

    def test_object_selection_is_widened_to_faces(self):
        """polyUVStackSimilarShells silently ignores whole objects (Maya's toolkit widens
        them to .f[*]); the slot must do the same or a transform selection is a no-op."""
        a, b = self._twins()
        cmds.select(a, b)
        self.instance.b030(_FakeStackWidget(mode="similar", tolerance=1.0))
        self.assertLess(self._max_dist(self._uvs(a), self._uvs(b)), 1e-5)

    def test_non_mesh_object_in_selection_is_skipped_not_raised(self):
        """A curve selected alongside the meshes must not blow up the .f[*] widening."""
        a, b = self._twins()
        curve = cmds.circle(ch=False, name="stackCurve")[0]
        cmds.select(a, b, curve)
        self.instance.b030(_FakeStackWidget(mode="similar", tolerance=1.0))
        self.assertLess(self._max_dist(self._uvs(a), self._uvs(b)), 1e-5)
        self.assertEqual(self.instance.sb.messages, [])

    def test_similar_mode_with_no_match_reports_and_stays_unstacked(self):
        a = cmds.polyPlane(w=1, h=1, sx=2, sy=2, ch=False, name="lone2x2")[0]
        c = cmds.polyPlane(w=1, h=1, sx=3, sy=1, ch=False, name="lone3x1")[0]
        cmds.polyEditUV(f"{c}.map[*]", u=0.5, v=0.5, r=True)
        before = self._uvs(a) + self._uvs(c)
        cmds.select(f"{a}.f[*]", f"{c}.f[*]")
        self.instance.b030(_FakeStackWidget(mode="similar", tolerance=0.1))
        self.assertEqual(before, self._uvs(a) + self._uvs(c))
        self.assertTrue(self.instance.sb.messages)
        self.assertIn("No similar shells", self.instance.sb.messages[0][0][0])
        self.assertFalse(self.instance._b030_stacked)  # next click stacks again
        self.assertIsNone(self.instance._b030_uv_snapshot)

    def test_center_mode_routes_to_texStackShells_with_uvs_selected(self):
        """All-shells mode runs texStackShells over the selection's UVs (the MEL
        needs a UV/face selection -- a plain object selection would be "No UVs
        selected") and puts the original selection back for the toggle."""
        a, b = self._twins()
        cmds.select(a, b)
        seen = []
        uv_module.mel.eval = lambda cmd: seen.append((cmd, cmds.ls(sl=True)))
        self.instance.b030(_FakeStackWidget(mode="center"))
        self.assertEqual(len(seen), 1)
        self.assertEqual(seen[0][0], "texStackShells {}")
        self.assertTrue(all(".map[" in item for item in seen[0][1]), seen[0][1])
        self.assertEqual(cmds.ls(sl=True), [a, b])  # selection restored
        self.assertTrue(self.instance._b030_stacked)
        self.assertTrue(self.instance._b030_uv_snapshot)

    def test_pin_after_stack_pins_stacked_shells_and_unstack_restores_prior_weights(
        self,
    ):
        a, b = self._twins()
        cmds.polyPinUV(f"{a}.map[0]", value=1.0)  # a pin the user set beforehand
        before_b = self._uvs(b)
        cmds.select(f"{a}.f[*]", f"{b}.f[*]")
        widget = _FakeStackWidget(mode="similar", tolerance=1.0, pin=True)

        self.instance.b030(widget)
        self.assertEqual(self._pin(f"{a}.map[4]"), 1.0)
        self.assertEqual(self._pin(f"{b}.map[4]"), 1.0)

        self.instance.b030(widget)  # Unstack
        # Positions come back even though the UVs were pinned meanwhile
        # (polyEditUV honours pins -- Unstack must lift them first).
        self.assertLess(self._max_dist(self._uvs(b), before_b), 1e-6)
        self.assertEqual(self._pin(f"{a}.map[0]"), 1.0)  # the user's pin survives
        self.assertEqual(self._pin(f"{a}.map[4]"), 0.0)
        self.assertEqual(self._pin(f"{b}.map[4]"), 0.0)

    def test_unstack_moves_back_uvs_the_user_had_pinned(self):
        """polyUVStackSimilarShells ignores pins but polyEditUV honours them:
        a user-pinned UV that the stack moved must still come back on Unstack."""
        a, b = self._twins()
        cmds.polyPinUV(f"{b}.map[2]", value=1.0)
        before_b = self._uvs(b)
        cmds.select(f"{a}.f[*]", f"{b}.f[*]")
        widget = _FakeStackWidget(mode="similar", tolerance=1.0, pin=False)
        self.instance.b030(widget)
        self.assertGreater(self._max_dist(self._uvs(b), before_b), 0.01)
        self.instance.b030(widget)  # Unstack
        self.assertLess(self._max_dist(self._uvs(b), before_b), 1e-6)
        self.assertEqual(self._pin(f"{b}.map[2]"), 1.0)  # weight restored

    def test_selection_change_resets_the_toggle(self):
        a, b = self._twins()
        cmds.select(f"{a}.f[*]", f"{b}.f[*]")
        widget = _FakeStackWidget(mode="similar", tolerance=1.0)
        self.instance.b030(widget)
        c, d = self._twins()
        cmds.select(f"{c}.f[*]", f"{d}.f[*]")
        self.instance.b030(widget)  # fresh selection -> stacks (not Unstack)
        self.assertTrue(self.instance._b030_stacked)
        self.assertLess(self._max_dist(self._uvs(c), self._uvs(d)), 1e-5)


# TestCmb002Dispatch (+ its _FakeItemsWidget/_FakeAddWidget helpers) removed 2026-07-12:
# the cmb002 "UV Transform" menu it drove was relocated wholesale to the mayatk
# shell_xform panel on 2026-07-09 (commit e80fcdc0, "UV transform cluster relocated to
# the DCC engines") — UvSlots has no cmb002/cmb002_init anymore, so all 8 tests raised
# AttributeError under mayapy. The capability's coverage now lives with the engine:
# mayatk/mayatk/uv_utils/shell_xform.py + mayatk/test/test_uv_utils.py (op-level), and
# the Blender twin via blendertk's shell_xform + tentacle/test/blender checks — the
# same relocation note as test/blender/uv_slot_check.py's tb005/tb008 removal.


class _FakeButton:
    """Stand-in for a QPushButton / option-box action button."""

    def __init__(self):
        self.enabled = True

    def setEnabled(self, state):
        self.enabled = bool(state)


class _FakeAction:
    """Stand-in for the ActionOption ``set_action`` returns."""

    def __init__(self):
        self.widget = _FakeButton()


class _FakeCheck(_FakeButton):
    """A checkbox row the enablement sync reads AND greys."""

    def __init__(self, checked):
        super().__init__()
        self._checked = checked

    def isChecked(self):
        return self._checked


class _FakeTransferCombo:
    """The Transfer combo (uvs / textures / auto), enough of it for the sync.

    ``setCurrentIndex`` re-enters the sync exactly as the real combo's
    ``currentIndexChanged`` does -- the pin path is only correct because the
    outer call re-reads the value afterwards, and a double that swallowed the
    signal could not catch that.
    """

    ITEMS = ("uvs", "textures", "auto")

    def __init__(self, data="uvs", on_change=None):
        self._index = self.ITEMS.index(data)
        self.enabled = True
        self.on_change = on_change

    def currentData(self):
        return self.ITEMS[self._index]

    def currentIndex(self):
        return self._index

    def findData(self, data):
        return self.ITEMS.index(data) if data in self.ITEMS else -1

    def setCurrentIndex(self, index):
        if index == self._index:
            return
        self._index = index
        if self.on_change:
            self.on_change()

    def setEnabled(self, state):
        self.enabled = bool(state)


class _FakeSourceCombo:
    def __init__(self, data="stored"):
        self._data = data

    def currentData(self):
        return self._data


@unittest.skipUnless(_MAYA_AVAILABLE, "Requires maya.cmds")
class TestTransferTexturesSourceControls(unittest.TestCase):
    """b034's Set Source row -- the stored set is invisible state, so the row
    itself has to report it: the capture button follows the Source mode, and
    Clear follows whether anything is stored."""

    def setUp(self):
        cmds.file(new=True, force=True)
        self.instance = uv_module.UvSlots.__new__(uv_module.UvSlots)
        self.instance.sb = _RecordedSb()
        self.instance._tt_src_button = _FakeButton()
        self.instance._tt_clear_action = _FakeAction()
        self.instance._tt_sources = []
        # The control map b034_init hands the sync (``_tt_ctl``): every row it
        # greys, keyed the way the slot reads them.
        self._mode = _FakeSourceCombo("stored")
        self.instance._tt_ctl = {
            "source": self._mode,
            "scope": _FakeButton(),
            "similarity": _FakeButton(),
            "transfer": _FakeTransferCombo(
                on_change=lambda: self.instance._tt_sync_controls()
            ),
            "texture_controls": (_FakeButton(),),
        }
        self.instance._tt_ctl["scope"].currentData = lambda: "order"

    def tearDown(self):
        cmds.file(new=True, force=True)

    def _set_mode(self, mode):
        self.instance._tt_ctl["source"] = _FakeSourceCombo(mode)

    def _sync(self):
        self.instance._tt_sync_controls()
        return (
            self.instance._tt_src_button.enabled,
            self.instance._tt_clear_action.widget.enabled,
        )

    def test_clear_is_greyed_until_something_is_stored(self):
        self.assertEqual(self._sync(), (True, False))
        self.instance._tt_sources = ["|pCube1"]
        self.assertEqual(self._sync(), (True, True))

    def test_other_source_modes_grey_the_whole_row(self):
        """'first' / 'uvset' never read the stored set, so capturing into it
        would silently do nothing -- which reads as a broken button."""
        self.instance._tt_sources = ["|pCube1"]
        for mode in ("first", "uvset"):
            self._set_mode(mode)
            self.assertEqual(self._sync(), (False, False), mode)

    def test_clear_empties_the_set_and_greys_itself(self):
        self.instance._tt_sources = ["|pCube1", "|pCube2"]
        self.instance._tt_clear_source()
        self.assertEqual(self.instance._tt_sources, [])
        self.assertFalse(self.instance._tt_clear_action.widget.enabled)

    def test_capture_stores_the_selection_and_enables_clear(self):
        cube = cmds.polyCube()[0]
        cmds.select(cube, replace=True)
        self.instance._tt_set_source_from_selection()
        self.assertEqual(len(self.instance._tt_sources), 1)
        self.assertTrue(self.instance._tt_clear_action.widget.enabled)


@unittest.skipUnless(_MAYA_AVAILABLE, "Requires maya.cmds")
class TestTransferTexturesSourceTooltip(unittest.TestCase):
    """The live hover is the ONLY place the stored set can be inspected."""

    def setUp(self):
        cmds.file(new=True, force=True)
        self.instance = uv_module.UvSlots.__new__(uv_module.UvSlots)
        self.instance.sb = _RecordedSb()
        self.instance.sb.tooltip = TooltipFormat

    def tearDown(self):
        cmds.file(new=True, force=True)

    def test_lists_short_names_not_full_dag_paths(self):
        self.instance._tt_sources = ["|grp|pCube1", "|grp|pCube2"]
        html = self.instance._tt_source_tooltip()
        self.assertIn("<li>pCube1</li>", html)
        self.assertNotIn("grp", html)

    def test_truncates_a_long_capture(self):
        n = TooltipFormat.STORED_ITEMS_MAX
        self.instance._tt_sources = [f"|pCube{i}" for i in range(n + 4)]
        html = self.instance._tt_source_tooltip()
        self.assertEqual(html.count("<li>"), n)
        self.assertIn("4 more", html)

    def test_empty_still_explains_what_the_button_does(self):
        self.instance._tt_sources = []
        html = self.instance._tt_source_tooltip()
        self.assertNotIn("<li>", html)
        self.assertIn("Set Source From Selection", html)

    def test_deleted_nodes_are_called_out(self):
        """b034 drops them; a count that no longer matches needs a reason."""
        cube = cmds.polyCube()[0]
        self.instance._tt_sources = cmds.ls(cube, long=True) + ["|goneForever"]
        html = self.instance._tt_source_tooltip()
        self.assertIn("1 no longer in the scene", html)


class TestTransferSyncControls(unittest.TestCase):
    """``UvMixin._tt_sync_controls`` -- which rows the current mode greys.

    DCC-free (the mixin only touches its own control map), so the enablement
    contract is pinned where it runs without Maya. The Maya-gated class below
    covers the parts that need real nodes.
    """

    def setUp(self):
        from tentacle.slots._uv import UvMixin

        class _Host(UvMixin):
            pass

        self.instance = _Host()
        self.instance._tt_sources = []
        self.instance._tt_src_button = _FakeButton()
        self.instance._tt_clear_action = _FakeAction()
        self.instance._tt_ctl = {
            "source": _FakeSourceCombo("stored"),
            "scope": _FakeButton(),
            "similarity": _FakeButton(),
            "transfer": _FakeTransferCombo(
                on_change=lambda: self.instance._tt_sync_controls()
            ),
            "texture_controls": (_FakeButton(),),
        }
        self.instance._tt_ctl["scope"].currentData = lambda: "order"

    def _set_mode(self, mode):
        self.instance._tt_ctl["source"] = _FakeSourceCombo(mode)

    def _sync(self):
        self.instance._tt_sync_controls()
        return (
            self.instance._tt_src_button.enabled,
            self.instance._tt_clear_action.widget.enabled,
        )

    def test_pinning_the_combo_leaves_the_texture_rows_live(self):
        """The pin re-enters the sync through the combo's signal; the outer
        call must re-read the mode, or it finishes with the pre-pin flags and
        greys every row the re-entrant call had just enabled."""
        row = self.instance._tt_ctl["texture_controls"][0]
        self.instance._tt_ctl["transfer"] = _FakeTransferCombo(
            "uvs", on_change=lambda: self.instance._tt_sync_controls()
        )
        self._set_mode("uvset")
        self._sync()
        self.assertEqual(self.instance._tt_ctl["transfer"].currentData(), "textures")
        self.assertTrue(row.enabled, "texture rows greyed under a Textures-only mode")

    def test_the_same_mesh_source_pins_the_transfer_combo_to_textures(self):
        """Two layouts of ONE mesh give the UV pass no second mesh to read, so
        the combo is moved (and locked) rather than left offering a mode that
        would run nothing."""
        combo = self.instance._tt_ctl["transfer"]
        self._set_mode("uvset")
        self._sync()
        self.assertEqual(combo.currentData(), "textures")
        self.assertFalse(combo.enabled)
        # ... and released again for a mesh source, keeping the value.
        self._set_mode("first")
        self._sync()
        self.assertTrue(combo.enabled)
        self.assertEqual(combo.currentData(), "textures")

    def test_a_partial_control_map_is_a_no_op(self):
        """The mixin's contract: a fork that has not built every row yet must
        not raise from inside a signal handler."""
        self.instance._tt_ctl = {"source": _FakeSourceCombo("stored")}
        self.instance._tt_sync_controls()  # must not raise
        del self.instance._tt_ctl
        self.instance._tt_sync_controls()

    def test_the_texture_rows_follow_the_transfer_combo(self):
        row = self.instance._tt_ctl["texture_controls"][0]
        self.instance._tt_ctl["transfer"] = _FakeTransferCombo("uvs")
        self._sync()
        self.assertFalse(row.enabled)
        self.instance._tt_ctl["transfer"] = _FakeTransferCombo("textures")
        self._sync()
        self.assertTrue(row.enabled)
        # Auto may resolve to the texture pass at run time, so its rows (the
        # Output Name above all) must stay editable while it is selected.
        self.instance._tt_ctl["transfer"] = _FakeTransferCombo("auto")
        self._sync()
        self.assertTrue(row.enabled)


class TestTransferPasses(unittest.TestCase):
    """``UvMixin._tt_passes`` -- the Transfer combo's one meaning.

    DCC-free: the mode pair is panel logic, and it decides which engine calls
    ``b000`` makes, so it is pinned where it can run without Maya.
    """

    def _passes(self, source_mode, transfer_mode):
        from tentacle.slots._uv import UvMixin

        return UvMixin._tt_passes(source_mode, transfer_mode)

    def test_each_mode_selects_exactly_one_pass(self):
        """The two are alternatives, not options that compose: the texture
        pass keeps the TARGET's own layout, so a source layout copied
        alongside it would land in a UV set nothing references."""
        self.assertEqual(self._passes("first", "uvs"), (True, False))
        self.assertEqual(self._passes("first", "textures"), (False, True))

    def test_the_same_mesh_source_drops_the_uv_pass(self):
        """Two layouts of ONE mesh: there is no second mesh to read a layout
        from, so only the texture pass can run there."""
        self.assertEqual(self._passes("uvset", "textures"), (False, True))
        self.assertEqual(self._passes("uvset", "uvs"), (False, False))

    def test_an_unset_combo_falls_back_to_the_uv_pass(self):
        """currentData() is None before the combo is populated; the default
        must be the non-destructive pass, not a texture write."""
        self.assertEqual(self._passes("first", None), (True, False))

    def test_auto_is_unresolved_here_so_both_passes_stay_possible(self):
        """Auto is resolved by b000 (``_tt_resolve_auto``) before the flags
        are acted on; for control enablement either pass could still run, so
        both halves of the option box must stay live."""
        self.assertEqual(self._passes("first", "auto"), (True, True))
        self.assertEqual(self._passes("stored", "auto"), (True, True))
        # The same-mesh source still has no second mesh for a UV pass to read.
        self.assertEqual(self._passes("uvset", "auto"), (False, True))


class _FakeTextureTransferEngine:
    """Engine double for ``_tt_resolve_auto``.

    A mesh is its material list; a material is its own ``{channel: path}``
    map dict -- the only two lookups the resolver makes.
    """

    @staticmethod
    def face_materials(mesh):
        if mesh == "raises":
            raise RuntimeError("no shape")
        return list(mesh), None

    @staticmethod
    def material_maps(material):
        if material == "raises":
            raise RuntimeError("unreadable shader")
        return material


class TestTransferResolveAuto(unittest.TestCase):
    """``UvMixin._tt_resolve_auto`` -- Auto's run-time decision.

    DCC-free: the decision is panel logic over the engine's material lookup
    (both engines expose the same two calls), so it is pinned against a
    double that runs without either DCC.
    """

    def _resolve(self, source_meshes):
        from tentacle.slots._uv import UvMixin

        return UvMixin._tt_resolve_auto(_FakeTextureTransferEngine, source_meshes)

    def test_a_mapped_source_material_picks_the_texture_pass(self):
        result = self._resolve([[{}, {"baseColor": "map.png"}]])
        self.assertEqual(result, "textures")

    def test_unmapped_source_materials_pick_the_uv_pass(self):
        """An untextured source has no maps to move -- its layout is the
        thing worth transferring."""
        self.assertEqual(self._resolve([[{}, {}]]), "uvs")

    def test_any_source_mesh_with_a_map_is_enough(self):
        result = self._resolve([[{}], [{"normal": "map.png"}]])
        self.assertEqual(result, "textures")

    def test_an_empty_probe_resolves_to_the_uv_pass(self):
        """b000 probes before its selection gates run; an empty probe must
        resolve (to the non-destructive pass) and let those gates report."""
        self.assertEqual(self._resolve([]), "uvs")

    def test_an_unreadable_mesh_or_shader_contributes_no_maps(self):
        """A shader the manifest cannot read must not crash the slot from
        inside the probe -- it simply has no maps to offer."""
        self.assertEqual(self._resolve(["raises", ["raises"]]), "uvs")
        self.assertEqual(
            self._resolve(["raises", [{"baseColor": "map.png"}]]), "textures"
        )


class TestTransferAutoNote(unittest.TestCase):
    """``UvMixin._tt_auto_note`` -- the gate suffix must name the real reason.

    DCC-free: pure message logic, identical in both forks.
    """

    @staticmethod
    def note(*args):
        from tentacle.slots._uv import UvMixin

        return UvMixin._tt_auto_note(*args)

    def test_no_note_unless_auto_actually_chose_textures(self):
        self.assertEqual(self.note(False, True, "first"), "")
        self.assertEqual(self.note(True, False, "first"), "")

    def test_a_probed_pick_cites_the_source_materials(self):
        self.assertIn("materials carry texture maps", self.note(True, True, "first"))
        self.assertIn("materials carry texture maps", self.note(True, True, "stored"))

    def test_a_uvset_source_must_not_claim_the_materials_decided(self):
        """With a ``uvset`` source nothing is probed at all -- the UV pass is
        structurally unavailable (there is no second mesh to read a layout
        from), so Textures is the only reading Auto has. Citing materials
        that were never consulted sends the user hunting for maps that may
        not exist.
        """
        message = self.note(True, True, "uvset")
        self.assertNotIn("materials", message)
        self.assertIn("no layout", message.replace("carries no layout", "no layout"))


if __name__ == "__main__":
    unittest.main()
