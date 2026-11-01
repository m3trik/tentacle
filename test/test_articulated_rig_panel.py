#!/usr/bin/python
# coding=utf-8
"""The Articulated Rig panel's one Slots class, shared by both hosts.

It reaches its host only through ``self.tk``, so a fake toolkit stands in for
``mtk`` / ``btk`` here: a small rig that keeps its plan with the real
``ptk.ArticulationPlan`` and records every engine call, a selection list for
the scene glue (``ArticulatedRig.selection`` / ``select``), and a widget-free
joints table. Plain pytest, no DCC, no widgets: Analyze filling the table
(Selection Order reading the picks as the chain); a row's type combo retyping
the plan and the built rig (the rebuild replaces the very combo whose signal
ran it, so the refresh waits); limits and give typed into a row, the give
scrolled; a row clicked selecting its control; the End Control checkbox on a
built rig; Switch IK / FK, Match End Control and Rest Pose; the Grab Tool;
Split Off Selected, Fold Into Parent, Set Limits From Pose, Clear Limits,
Adjust Pivots, Rebuild and Remove Rig.

In a fresh GUI Maya (``run_tests.py --in-maya``) the panel itself loads the
way the marking menu opens it and drives the real ``mtk`` on mayatk's
magnifier-arm fixture. The scene glue is the libraries' (tested in mayatk's
``test_articulated_rig.py`` and blendertk's harness).
"""

import contextlib
import copy
import logging
import math
import types
import unittest
from unittest import mock

import pythontk as ptk
from qtpy import QtCore

from _host import MAYA_AVAILABLE, maya_module, qt_widgets_available
from tentacle.slots._slots import Slots
from tentacle.slots.tools import articulated_rig as panel_module
from tentacle.slots.tools.articulated_rig import ArticulatedRigSlots

#: The fixture's parts (mayatk's magnifier arm), root first, and what the fake
#: analysis proposes for each joint.
ARM = ["BASE", "LEG_1", "LEG_2", "LEG_3", "LEG_4", "HEAD"]
TYPES = ["universal", "hinge", "hinge", "slide", "ball"]
IDENTITY = [float(r == c) for r in range(4) for c in range(4)]


# ----------------------------------------------------------------- the fakes
class _Signal:
    def __init__(self):
        self.slots = []

    def connect(self, fn):
        self.slots.append(fn)

    def emit(self, *args):
        for fn in list(self.slots):
            fn(*args)


class _Combo:
    """A type cell's combo, without a widget."""

    def __init__(self):
        self.items, self.text = [], ""
        self.currentTextChanged = _Signal()

    def addItems(self, items):
        self.items = list(items)

    def currentText(self):
        return self.text

    def setCurrentText(self, text):
        changed = text != self.text
        self.text = text
        if changed:
            self.currentTextChanged.emit(text)


class _Item:
    def __init__(self, row, column, text):
        self._row, self._column, self._text = row, column, str(text)
        self._flags = QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsEnabled

    def row(self):
        return self._row

    def column(self):
        return self._column

    def text(self):
        return self._text

    def flags(self):
        return self._flags

    def setFlags(self, flags):
        self._flags = flags

    def editable(self):
        return bool(self._flags & QtCore.Qt.ItemIsEditable)


class _Table:
    """uitk's TableWidget, as far as the panel drives it, without a widget."""

    def __init__(self):
        self.columns, self.items, self.widgets, self.selected = 0, [], {}, []
        self.cellWheelScrolled = _Signal()
        self.itemChanged = _Signal()
        self.itemSelectionChanged = _Signal()
        self.headers = []

    def setColumnCount(self, n):
        self.columns = n

    def columnCount(self):
        return self.columns

    def setHorizontalHeaderLabels(self, labels):
        self.headers = list(labels)

    def setToolTip(self, text):
        self.tooltip = text

    def verticalHeader(self):
        return mock.MagicMock()

    def set_cell_widget_click_columns(self, columns):
        self.click_columns = list(columns)

    def set_wheel_scrub_columns(self, columns):
        self.scrub_columns = list(columns)

    def add(self, rows, headers=None):
        self.items = [[_Item(r, c, v) for c, v in enumerate(row)] for r, row in enumerate(rows)]
        self.widgets = {}
        self.headers = list(headers or self.headers)

    def setRowCount(self, n):
        self.items = self.items[:n]
        self.widgets = {k: w for k, w in self.widgets.items() if k[0] < n}

    def rowCount(self):
        return len(self.items)

    def item(self, row, column):
        return self.items[row][column]

    def setCellWidget(self, row, column, widget):
        self.widgets[(row, column)] = widget

    def cellWidget(self, row, column):
        return self.widgets.get((row, column))

    def resizeColumnsToContents(self):
        pass

    def selectedIndexes(self):
        return [types.SimpleNamespace(row=lambda r=r: r) for r in self.selected]

    # -- what a user does
    def type_into(self, row, column, text):
        item = self.items[row][column]
        item._text = text
        self.itemChanged.emit(item)

    def select_row(self, row):
        self.selected = [row]
        self.itemSelectionChanged.emit()


class _Scene:
    """The scene side: the selection, what the panel selected, the rigs, and
    every engine call the panel made."""

    def __init__(self):
        self.reset()

    def reset(self):
        self.selection, self.selected, self.rigs, self.calls = [], [], [], []

    def verbs(self, verb):
        return [c[1:] for c in self.calls if c[0] == verb]


SCENE = _Scene()


class _FakeRig:
    """``ArticulatedRig``'s surface the panel drives, over a plan dict the real
    ``ptk.ArticulationPlan`` edits. Nodes are names: a part by its own, a
    control ``<rig>_<joint>_ctrl``."""

    JOINT_TYPES = ptk.ArticulationAnalysis.JOINT_TYPES
    END_KEY = ptk.ArticulationPlan.END_KEY
    logger = mock.MagicMock()
    #: What the next ``create`` raises (a refused build), or None.
    refuse = None

    def __init__(self, spec):
        self._spec = spec
        self.group_uuid = spec["group_uuid"]
        self.alive = True
        self.handles = {}
        self.moved = False
        self.ik = True
        self.pose = {}

    # ----------------------------------------------------------- the toolkit's
    @classmethod
    def selection(cls):
        return list(SCENE.selection)

    @classmethod
    def select(cls, nodes):
        SCENE.selected.append(list(nodes))

    @classmethod
    def analyze(cls, nodes, root=None, ordered=False):
        SCENE.calls.append(("analyze", list(nodes), ordered))
        return {
            "links": [[f"|ASSET|ARM|{p}"] for p in ARM],
            "joints": [
                {
                    "link": i + 1,
                    "parent": i,
                    "type": kind,
                    "position": [0.0, 0.0, float(i)],
                    "aim": [0.0, 0.0, 1.0],
                    "normal": [1.0, 0.0, 0.0],
                    "limits": {},
                    "size": 1.0,
                    "reason": f"{kind} from the contact",
                }
                for i, kind in enumerate(TYPES)
            ],
            "unreached": ["|ASSET|ARM|LOOSE"],
        }

    @classmethod
    def create(cls, links, joints=None, name=None, parent=None, end_control=True):
        SCENE.calls.append(("create", name, end_control, copy.deepcopy(joints)))
        if cls.refuse:
            raise ValueError(cls.refuse)
        names = [[str(m).split("|")[-1] for m in link] for link in links]
        spec = {
            "name": name or "arm",
            "group_uuid": f"g{len(SCENE.rigs)}",
            "links": [[{"uuid": f"u_{m}", "name": m} for m in link] for link in names],
            "joints": [dict(copy.deepcopy(j), id=names[j["link"]][0]) for j in joints],
        }
        if end_control:
            spec["end"] = {"part": f"u_{names[-1][0]}", "frame": IDENTITY}
        rig = cls(spec)
        SCENE.rigs.append(rig)
        return rig

    @classmethod
    def for_node(cls, node):
        for rig in SCENE.rigs:
            if rig.alive and (node == rig._group or rig.joint_id_of(node)):
                return rig
        return None

    @classmethod
    def repair_scene(cls):
        SCENE.calls.append(("repair_scene",))
        return 0

    # ----------------------------------------------------------------- a rig
    @property
    def _group(self):
        return f"|{self._spec['name']}_RIG"

    @property
    def group(self):
        if not self.alive:
            raise RuntimeError("The rig group no longer exists.")
        return self._group

    @property
    def spec(self):
        _ = self.group
        return copy.deepcopy(self._spec)

    @property
    def name(self):
        return self._spec["name"]

    @property
    def end_control(self):
        return f"{self.name}_end_ctrl" if self._spec.get("end") else None

    @property
    def adjusting(self):
        _ = self.group
        return bool(self.handles)

    def ensure_solver(self):
        SCENE.calls.append(("ensure_solver", self.name))
        return self.end_control is not None

    def joint_ids(self):
        return [j["id"] for j in self._spec["joints"]]

    def control(self, joint_id):
        return f"{self.name}_{joint_id}_ctrl"

    def _parts(self):
        return {m["name"] for link in self._spec["links"] for m in link}

    def joint_id_of(self, node):
        for joint in self._spec["joints"]:
            if node == self.control(joint["id"]):
                return joint["id"]
            if node in [m["name"] for m in self._spec["links"][joint["link"]]]:
                return joint["id"]
        return None

    def parts_of(self, nodes):
        return [n for n in nodes if n in self._parts()]

    def edit_joint(self, joint_id, **fields):
        SCENE.calls.append(("edit_joint", joint_id, fields))
        joint = ptk.ArticulationPlan.joint_entry(self._spec, joint_id)
        if "type" in fields:
            ptk.ArticulationPlan.retype(joint, fields["type"])
        return self

    def set_limits(self, joint_id, channel, minimum, maximum):
        SCENE.calls.append(("set_limits", joint_id, channel, minimum, maximum))
        ptk.ArticulationPlan.set_limits(self._spec, joint_id, channel, minimum, maximum)

    def channel_value(self, joint_id, channel):
        return self.pose.get((joint_id, channel), 0.0)

    def set_limit_from_pose(self, joint_id, channel, side):
        value = self.channel_value(joint_id, channel)
        SCENE.calls.append(("set_limit_from_pose", joint_id, channel, side))
        lo, hi = ptk.ArticulationPlan.side_limits(self._spec, joint_id, channel, side, value)
        ptk.ArticulationPlan.set_limits(self._spec, joint_id, channel, lo, hi)
        return value

    def set_weight(self, joint_id, weight, channel=None):
        SCENE.calls.append(("set_weight", joint_id, weight))
        ptk.ArticulationPlan.set_weight(self._spec, joint_id, weight, channel)

    def set_end_control(self, enabled=True, part=None):
        SCENE.calls.append(("set_end_control", enabled))
        if enabled:
            self._spec["end"] = {"part": "u_HEAD", "frame": IDENTITY}
        else:
            self._spec.pop("end", None)
        return self

    def insert_joint(self, members, joint_type=None, **fields):
        SCENE.calls.append(("insert_joint", list(members), joint_type))
        uuids = {f"u_{m}" for m in members}
        host, keep, split = ptk.ArticulationPlan.split_link(self._spec, uuids)
        self._spec["links"][host] = keep
        self._spec["links"].append(split)
        self._spec["joints"].append(
            {
                "id": split[0]["name"],
                "link": len(self._spec["links"]) - 1,
                "parent": host,
                "type": joint_type or "slide",
                "limits": {},
                "reason": "split off",
            }
        )
        return self

    def remove_joint(self, joint_id):
        SCENE.calls.append(("remove_joint", joint_id))
        self._spec["joints"] = [j for j in self._spec["joints"] if j["id"] != joint_id]
        return self

    def rebuild(self, spec=None):
        SCENE.calls.append(("rebuild", self.name))
        return self

    def teardown(self):
        SCENE.calls.append(("teardown", self.name))
        self.alive = False

    def switch_ik(self, on=None, key=None):
        if self.end_control is None:
            raise RuntimeError(f"Rig {self.name!r} has no end control.")
        self.ik = (not self.ik) if on is None else bool(on)
        SCENE.calls.append(("switch_ik", self.ik))
        return self.ik

    def match_end_control(self, key=None):
        SCENE.calls.append(("match_end_control", self.name))

    def reset_pose(self, key=None):
        SCENE.calls.append(("reset_pose", self.name))
        self.pose.clear()

    def begin_adjust(self):
        SCENE.calls.append(("begin_adjust", self.name))
        self.handles = {j: f"{self.name}_{j}_pivot" for j in self.joint_ids()}
        if self.end_control is not None:
            self.handles[self.END_KEY] = f"{self.name}_end_pivot"
        return dict(self.handles)

    def adjust_handles(self):
        return dict(self.handles)

    def end_adjust(self, apply=True):
        SCENE.calls.append(("end_adjust", self.name, apply))
        moved = bool(self.handles) and self.moved
        self.handles = {}
        return moved


class _FakeGrab:
    """``ArticulatedRigGrab``: the tool's activation, refused when :attr:`refuse`."""

    refuse = None

    @classmethod
    def activate(cls):
        SCENE.calls.append(("grab",))
        if cls.refuse:
            raise RuntimeError(cls.refuse)
        return True


class _FakeCore:
    """``CoreUtils``: a node's name as shown, and the undo chunk (recorded)."""

    @staticmethod
    def leaf_name(node):
        return str(node).split("|")[-1]

    @staticmethod
    @contextlib.contextmanager
    def undo_chunk(name=""):
        SCENE.calls.append(("undo_chunk", name))
        yield


def _toolkit():
    return types.SimpleNamespace(
        ArticulatedRig=_FakeRig,
        ArticulatedRigGrab=_FakeGrab,
        CoreUtils=_FakeCore,
        UiUtils=mock.MagicMock(),
    )


def _panel():
    """A Slots instance over a mock ui (a widget-free joints table) and the
    fake toolkit, handed over before the panel is built (as ``Slots.tk`` is)."""
    sb = mock.MagicMock()
    sb.tk = _toolkit()
    ui = sb.loaded_ui.articulated_rig
    ui.tbl_joints = _Table()
    ui.cmb_source.currentIndex.return_value = 0
    ui.cmb_insert_type.currentIndex.return_value = 0
    ui.txt_name.text.return_value = ""
    ui.chk_end_control.isChecked.return_value = True
    ui.chk_adjust.isChecked.return_value = False
    return ArticulatedRigSlots(sb), sb


class _PanelCase(unittest.TestCase):
    def setUp(self):
        migrated = Slots._legacy_repeat_last_migrated
        Slots._legacy_repeat_last_migrated = True  # no migration under test
        self.addCleanup(setattr, Slots, "_legacy_repeat_last_migrated", migrated)
        SCENE.reset()
        _FakeRig.refuse = None
        _FakeGrab.refuse = None
        # The type combos are widget-free; the deferred refresh runs on settle().
        self.deferred = []
        qt = types.SimpleNamespace(
            Qt=QtCore.Qt,
            QTimer=types.SimpleNamespace(
                singleShot=lambda ms, fn: self.deferred.append(fn)
            ),
        )
        patches = [
            mock.patch.object(panel_module, "QtCore", qt),
            mock.patch.object(panel_module, "QtWidgets", types.SimpleNamespace(QComboBox=_Combo)),
        ]
        for patcher in patches:
            patcher.start()
            self.addCleanup(patcher.stop)
        self.slots, self.sb = _panel()
        self.ui = self.sb.loaded_ui.articulated_rig
        self.table = self.ui.tbl_joints

    def settle(self):
        while self.deferred:
            self.deferred.pop(0)()

    def rows(self):
        return [
            (self.table.item(r, 0).text(), self.table.cellWidget(r, 1).currentText())
            for r in range(self.table.rowCount())
        ]

    def select(self, *nodes):
        SCENE.selection = list(nodes)

    def build(self, end_control=True):
        self.ui.chk_end_control.isChecked.return_value = end_control
        self.select("ARM")
        self.slots.btn_build()  # analyzes first when nothing is planned
        self.assertIsNotNone(self.slots.rig)
        return self.slots.rig

    def logged(self, level="INFO"):
        return self.assertLogs(self.slots.logger, level=level)


class TestPanelSurface(_PanelCase):
    def test_the_table_is_set_up_with_its_columns(self):
        self.assertEqual(self.table.headers, self.slots.COLUMNS)
        self.assertEqual(self.table.columnCount(), len(self.slots.COLUMNS))
        self.assertEqual(self.table.click_columns, [self.slots.TYPE_COLUMN])
        self.assertEqual(self.table.scrub_columns, [self.slots.GIVE_COLUMN])

    def test_the_panel_open_restores_the_end_controls(self):
        """Opening the panel arms every end control's solve."""
        self.assertIn(("repair_scene",), SCENE.calls)

    def test_the_engine_logs_into_the_panel(self):
        _FakeRig.logger.setup_logging_redirect.assert_called_with(self.ui.txt003)
        self.assertTrue(self.slots.logger.isEnabledFor(logging.INFO))

    def test_adjust_pivots_is_never_restored(self):
        """The box shows a live state -- whether the rig in the table is
        adjusting -- not a setting: restored, an adjust that ended any way but
        by clearing the box began again on the next panel open."""
        self.assertFalse(self.ui.chk_adjust.restore_state)

    def test_the_help_card_links_the_tools_reference(self):
        self.assertTrue(self.slots.HELP_URL.endswith("/docs/articulated_rig.md"))
        header = mock.MagicMock()
        self.slots.header_init(header)
        self.assertEqual(header.set_help_text.call_args.kwargs["url"], self.slots.HELP_URL)

    def test_log_links_dispatch_through_the_host(self):
        self.slots._on_log_link_clicked("action://select?node=arm_RIG")
        self.sb.tk.UiUtils.dispatch_log_link.assert_called_once_with(
            "action://select?node=arm_RIG", self.slots.logger
        )

    def test_limits_typed_as_text_parse(self):
        parse = self.slots.parse_limits
        self.assertEqual(parse("rz -30..95", ("rz",)), {"rz": (-30.0, 95.0)})
        self.assertEqual(parse("-..12.5", ("tx",)), {"tx": (None, 12.5)})
        self.assertEqual(
            parse("rx -10..10, rz ..45", ("rx", "rz")),
            {"rx": (-10.0, 10.0), "rz": (None, 45.0)},
        )
        self.assertEqual(
            parse("free", ("rx", "rz")), {"rx": (None, None), "rz": (None, None)}
        )
        for bad in ("rz 5", "ry -1..1", "-1..1", "rz 9..3"):
            with self.assertRaises(ValueError, msg=bad):
                parse(bad, ("rx", "rz"))


class TestAnalyzeAndBuild(_PanelCase):
    def test_analyze_fills_the_table_by_the_parts_names(self):
        self.select("ARM")
        with self.logged("WARNING") as log:
            self.slots.btn_analyze()
        self.assertEqual(
            self.rows(),
            [
                ("LEG_1", "universal"),
                ("LEG_2", "hinge"),
                ("LEG_3", "hinge"),
                ("LEG_4", "slide"),
                ("HEAD", "ball"),
            ],
        )
        self.assertEqual(self.table.item(0, 2).text(), "BASE")  # Hangs Off
        self.assertIn("LOOSE touches nothing", "\n".join(log.output))

    def test_only_limits_and_give_are_typed_into(self):
        self.select("ARM")
        self.slots.btn_analyze()
        editable = [c for c in range(6) if self.table.item(0, c).editable()]
        self.assertEqual(editable, [self.slots.LIMITS_COLUMN, self.slots.GIVE_COLUMN])

    def test_a_row_retypes_the_plan_after_its_signal_returns(self):
        self.select("ARM")
        self.slots.btn_analyze()
        combo = self.table.cellWidget(1, 1)
        combo.setCurrentText("ball")
        self.assertEqual(self.slots.plan["joints"][1]["type"], "ball")
        self.assertIs(self.table.cellWidget(1, 1), combo, "refreshed under its own signal")
        self.settle()
        self.assertEqual(self.rows()[1], ("LEG_2", "ball"))

    def test_selection_order_analyzes_the_picks_as_the_chain(self):
        self.select("BASE", "LEG_2", "LEG_1")
        self.ui.cmb_source.currentIndex.return_value = 1  # Parts: Selection Order
        self.slots.btn_analyze()
        self.assertEqual(SCENE.verbs("analyze"), [(["BASE", "LEG_2", "LEG_1"], True)])
        self.ui.cmb_source.currentIndex.return_value = 0
        self.slots.btn_analyze()
        self.assertFalse(SCENE.verbs("analyze")[-1][1])

    def test_nothing_selected_is_reported_and_analyzes_nothing(self):
        with self.logged("ERROR") as log:
            self.slots.btn_analyze()
        self.assertEqual(SCENE.verbs("analyze"), [])
        self.assertIn("Select the prop", "\n".join(log.output))

    def test_build_names_the_rig_then_a_row_retypes_the_built_joint(self):
        self.ui.txt_name.text.return_value = "desk"
        with self.logged() as log:
            rig = self.build()
        ((name, end_control, _joints),) = SCENE.verbs("create")
        self.assertEqual((name, end_control), ("desk", True))
        self.assertIsNone(self.slots.plan)
        self.assertIn("Built", "\n".join(log.output))
        self.assertIn("node=desk_RIG", "\n".join(log.output))  # the group's link
        self.table.cellWidget(1, 1).setCurrentText("ball")
        self.settle()
        self.assertEqual(SCENE.verbs("edit_joint"), [("LEG_2", {"type": "ball"})])
        self.assertEqual(self.rows()[1], ("LEG_2", "ball"))
        self.assertIs(self.slots.rig, rig)

    def test_a_build_without_the_end_control(self):
        rig = self.build(end_control=False)
        self.assertIsNone(rig.end_control)
        self.assertFalse(SCENE.verbs("create")[0][1])

    def test_a_refused_build_is_reported_and_keeps_the_plan(self):
        self.select("ARM")
        self.slots.btn_analyze()
        _FakeRig.refuse = "LEG_2 is driven"
        self.slots.btn_build()
        self.assertIsNone(self.slots.rig)
        self.assertIsNotNone(self.slots.plan)
        self.assertIn("LEG_2 is driven", self.sb.message_box.call_args.args[0])


class TestTableEdits(_PanelCase):
    def test_limits_typed_into_a_row_bound_the_built_joint_in_one_undo_step(self):
        self.build(end_control=False)
        self.table.type_into(1, self.slots.LIMITS_COLUMN, "rz -20..45")
        self.settle()
        self.assertEqual(SCENE.verbs("set_limits"), [("LEG_2", "rz", -20.0, 45.0)])
        self.assertIn(("Articulated Rig: Set Limits",), SCENE.verbs("undo_chunk"))
        self.assertEqual(self.table.item(1, self.slots.LIMITS_COLUMN).text(), "rz -20..45")

    def test_a_bad_limits_entry_is_reported_and_changes_nothing(self):
        rig = self.build(end_control=False)
        with self.logged("ERROR") as log:
            self.table.type_into(1, self.slots.LIMITS_COLUMN, "tight please")
        self.settle()
        joint = next(j for j in rig.spec["joints"] if j["id"] == "LEG_2")
        self.assertEqual(joint.get("limits") or {}, {})
        self.assertEqual(SCENE.verbs("set_limits"), [])
        self.assertIn("failed", "\n".join(log.output))
        self.assertEqual(self.table.item(1, self.slots.LIMITS_COLUMN).text(), "free")

    def test_limits_typed_into_a_plan_row_reach_the_build(self):
        self.select("ARM")
        self.slots.btn_analyze()
        self.table.type_into(1, self.slots.LIMITS_COLUMN, "rz -30..95")
        self.settle()
        self.slots.btn_build()
        joints = SCENE.verbs("create")[0][2]
        self.assertEqual(joints[1]["limits"], {"rz": [-30.0, 95.0]})

    def test_give_typed_and_scrolled_sets_the_weight(self):
        self.build()
        give = self.slots.GIVE_COLUMN
        self.table.type_into(0, give, "0.5")
        self.settle()
        self.assertEqual(SCENE.verbs("set_weight"), [("LEG_1", 0.5)])
        self.table.cellWheelScrolled.emit(0, give, 2, QtCore.Qt.NoModifier)
        self.settle()
        self.assertAlmostEqual(SCENE.verbs("set_weight")[-1][1], 0.7, places=6)
        self.assertEqual(self.table.item(0, give).text(), "0.7")
        self.table.cellWheelScrolled.emit(0, give, -1, QtCore.Qt.ShiftModifier)
        self.settle()
        self.assertEqual(SCENE.verbs("set_weight")[-1][1], 0.0)  # never below 0

    def test_a_give_in_the_plan_reaches_the_build(self):
        self.select("ARM")
        self.slots.btn_analyze()
        self.table.type_into(3, self.slots.GIVE_COLUMN, "0.25")
        self.settle()
        self.slots.btn_build()
        joints = SCENE.verbs("create")[0][2]
        self.assertEqual(joints[3]["weights"], {"tx": 0.25})

    def test_clicking_a_row_selects_its_control_or_before_the_build_its_part(self):
        self.select("ARM")
        self.slots.btn_analyze()
        self.table.select_row(1)
        self.assertEqual(SCENE.selected[-1], ["|ASSET|ARM|LEG_2"])
        rig = self.build()
        self.table.select_row(2)
        self.assertEqual(SCENE.selected[-1], [rig.control("LEG_3")])


class TestPose(_PanelCase):
    def test_the_end_control_checkbox_drops_and_restores_it(self):
        rig = self.build()
        self.slots._on_end_control_toggled(False)
        self.settle()
        self.assertIsNone(rig.end_control)
        self.slots._on_end_control_toggled(True)
        self.settle()
        self.assertIsNotNone(rig.end_control)
        self.assertEqual(SCENE.verbs("set_end_control"), [(False,), (True,)])

    def test_before_a_build_the_checkbox_is_only_the_builds_option(self):
        self.select("ARM")
        self.slots.btn_analyze()
        self.slots._on_end_control_toggled(False)
        self.assertEqual(SCENE.verbs("set_end_control"), [])

    def test_switch_ik_fk_and_rest_pose(self):
        rig = self.build()
        self.select(rig.end_control)
        with self.logged() as log:
            self.slots.btn_ik_fk()
        self.assertFalse(rig.ik)
        self.assertIn("FK", "\n".join(log.output))
        self.slots.btn_ik_fk()
        self.assertTrue(rig.ik)
        self.assertEqual(SCENE.verbs("switch_ik"), [(False,), (True,)])
        self.slots.btn_rest()
        self.assertEqual(SCENE.verbs("reset_pose"), [(rig.name,)])

    def test_switch_ik_fk_without_an_end_control_is_refused(self):
        rig = self.build(end_control=False)
        self.select(rig.control("LEG_2"))
        with self.logged("ERROR") as log:
            self.slots.btn_ik_fk()
        self.assertEqual(SCENE.verbs("switch_ik"), [])
        self.assertIn("has no end control", "\n".join(log.output))

    def test_match_end_control_from_the_option_box(self):
        rig = self.build()
        menu = mock.MagicMock()
        del menu.btn_match_end  # not built yet

        def add(*args, **kwargs):  # uitk's menu exposes an item by its objectName
            setattr(menu, kwargs["setObjectName"], mock.MagicMock())
            return getattr(menu, kwargs["setObjectName"])

        menu.add.side_effect = add
        widget = mock.MagicMock()
        widget.option_box.menu = menu
        self.slots.btn_ik_fk_init(widget)
        self.slots.btn_ik_fk_init(widget)  # built once
        menu.add.assert_called_once()
        menu.btn_match_end.clicked.connect.assert_called_once_with(
            self.slots.match_end_control
        )
        self.slots.match_end_control()
        self.assertEqual(SCENE.verbs("match_end_control"), [(rig.name,)])

    def test_nothing_selected_and_no_rig_shown_is_reported(self):
        with self.logged("ERROR") as log:
            self.slots.btn_rest()
        self.assertEqual(SCENE.verbs("reset_pose"), [])
        self.assertIn("Select a part or control", "\n".join(log.output))


class TestGrabTool(_PanelCase):
    def test_the_grab_button_starts_the_hosts_tool(self):
        with self.logged() as log:
            self.slots.btn_grab()
        self.assertEqual(SCENE.verbs("grab"), [()])
        self.assertIn("Grab Tool", "\n".join(log.output))

    def test_a_refused_grab_is_reported_not_raised(self):
        _FakeGrab.refuse = "No 3D viewport"
        with self.logged("ERROR") as log:
            self.slots.btn_grab()
        self.assertIn("No 3D viewport", "\n".join(log.output))


class TestPostRig(_PanelCase):
    def _telescope(self):
        """A rig with the inner rod riding the outer one -- the telescope left out."""
        links = [["BASE"], ["LEG_1"], ["LEG_2"], ["LEG_3", "LEG_4"], ["HEAD"]]
        joints = [
            {"link": i + 1, "parent": i, "type": kind, "limits": {}, "reason": ""}
            for i, kind in enumerate(["universal", "hinge", "hinge", "ball"])
        ]
        self.slots.rig = _FakeRig.create(links, joints)
        self.slots.refresh_table()
        return self.slots.rig

    def test_split_off_selected_splits_the_parts_never_a_control(self):
        rig = self._telescope()
        self.assertEqual(len(self.rows()), 4)
        self.select("LEG_4", rig.control("LEG_2"))
        self.ui.cmb_insert_type.currentIndex.return_value = 1  # Joint: Slide
        self.slots.btn_insert()
        self.assertEqual(SCENE.verbs("insert_joint"), [(["LEG_4"], "slide")])
        self.assertIn(("LEG_4", "slide"), self.rows())

    def test_split_off_with_no_part_selected_is_refused(self):
        rig = self._telescope()
        self.select(rig.control("LEG_2"))
        with self.logged("ERROR") as log:
            self.slots.btn_insert()
        self.assertEqual(SCENE.verbs("insert_joint"), [])
        self.assertIn("Select the parts to split off", "\n".join(log.output))

    def test_an_analysis_left_in_the_table_gives_way_to_the_rig_acted_on(self):
        rig = self.build()
        self.select("ARM")
        self.slots.btn_analyze()  # a plan for another prop fills the table
        self.select(rig.control("LEG_2"))
        self.slots.btn_rebuild()
        self.assertIsNone(self.slots.plan)
        self.assertIs(self.slots.rig, rig)
        self.assertEqual(SCENE.verbs("rebuild"), [(rig.name,)])
        self.assertEqual(len(self.rows()), 5)

    def test_another_instance_of_the_shown_rig_keeps_the_table(self):
        """The rig acted on is told from the one shown by its identity, not by
        the instance: one found again from a control refreshes nothing."""
        rig = self.build()
        again = _FakeRig(rig._spec)
        SCENE.rigs.insert(0, again)
        before = self.table.items
        self.select(rig.control("LEG_2"))
        self.slots.btn_rest()
        self.assertIs(self.table.items, before)
        self.assertIs(self.slots.rig, again)

    def test_adjust_pivots_puts_handles_out_and_rebuilds_when_cleared(self):
        rig = self.build()
        self.select(rig.control("LEG_2"))
        self.slots._on_adjust_toggled(True)
        self.settle()
        handles = rig.adjust_handles()
        self.assertEqual(set(handles), set(rig.joint_ids()) | {_FakeRig.END_KEY})
        self.assertEqual(SCENE.selected[-1], list(handles.values()))
        rig.moved = True  # a handle moved in the viewport
        with self.logged() as log:
            self.slots._on_adjust_toggled(False)
        self.settle()
        self.assertEqual(SCENE.verbs("end_adjust"), [(rig.name, True)])
        self.assertFalse(rig.adjusting)
        self.assertIn("rebuilt on the adjusted pivots", "\n".join(log.output))

    def test_limits_from_pose_then_clear_limits_in_one_undo_step_each(self):
        rig = self.build(end_control=False)
        rig.pose[("LEG_2", "rz")] = 55.0
        self.select(rig.control("LEG_2"), rig.control("LEG_1"))  # LEG_1 at rest
        self.slots.btn_limits_from_pose()
        self.assertEqual(SCENE.verbs("set_limit_from_pose"), [("LEG_2", "rz", "max")])
        self.assertEqual(self.table.item(1, self.slots.LIMITS_COLUMN).text(), "rz -..55")
        self.slots.btn_clear_limits()
        self.assertEqual(
            SCENE.verbs("set_limits"),
            [
                ("LEG_1", "rx", None, None),
                ("LEG_1", "rz", None, None),
                ("LEG_2", "rz", None, None),
            ],
        )
        chunks = [c[0] for c in SCENE.verbs("undo_chunk")]
        self.assertIn("Articulated Rig: Limits From Pose", chunks)
        self.assertIn("Articulated Rig: Clear Limits", chunks)

    def test_fold_into_parent(self):
        rig = self.build()
        self.select(rig.control("LEG_3"))
        self.slots.btn_fold()
        self.assertEqual(SCENE.verbs("remove_joint"), [("LEG_3",)])
        self.assertIn(("Articulated Rig: Fold",), SCENE.verbs("undo_chunk"))
        self.assertNotIn("LEG_3", [r[0] for r in self.rows()])

    def test_remove_rig(self):
        rig = self.build()
        self.select(rig.control("LEG_2"))
        self.slots.btn_remove()
        self.assertEqual(SCENE.verbs("teardown"), [(rig.name,)])
        self.assertIsNone(self.slots.rig)
        self.assertEqual(self.table.rowCount(), 0)

    def test_a_rig_gone_from_the_scene_is_dropped(self):
        rig = self.build()
        rig.alive = False  # deleted by hand
        with self.logged("ERROR"):
            self.slots.btn_rest()
        self.assertIsNone(self.slots.rig)
        self.assertEqual(SCENE.verbs("reset_pose"), [])


# ------------------------------------------------------------ in a GUI Maya
def _build_arm(cmds):
    """mayatk's magnifier-arm fixture (``test_articulated_rig.build_arm``):
    the production prop's shape from primitives under a scaled asset node --
    six part groups whose analysis is five joints (universal, hinge, hinge,
    slide, ball). Returns the ``ARM`` group's path."""

    def norm(v):
        n = math.sqrt(sum(c * c for c in v))
        return tuple(c / n for c in v)

    def add(p, d, s=1.0):
        return tuple(a + b * s for a, b in zip(p, d))

    def cyl(name, p0, p1, radius, sides=12):
        axis = tuple(b - a for a, b in zip(p0, p1))
        height = math.sqrt(sum(c * c for c in axis))
        node = cmds.polyCylinder(
            name=name, r=radius, h=height, ax=axis, sx=sides, sy=2, ch=False
        )[0]
        cmds.move(*[(a + b) / 2 for a, b in zip(p0, p1)], node)
        return node

    def cube(name, centre, size):
        node = cmds.polyCube(name=name, w=size[0], h=size[1], d=size[2], ch=False)[0]
        cmds.move(*centre, node)
        return node

    def sphere(name, centre, radius):
        node = cmds.polySphere(name=name, r=radius, sx=8, sy=6, ch=False)[0]
        cmds.move(*centre, node)
        return node

    r = norm((0.966, 0.259, 0.0))
    elbow = (0.0, 32.0, 0.0)
    collar = add(elbow, (0.8, 0.6, 0.0), 25)
    rod_end = add(collar, r, 32)
    inner_0, inner_1 = add(collar, r, 20), add(collar, r, 40)
    ball = add(inner_1, r, 0.7)
    parts = {
        "BASE": [
            cube("plate", (0, 0.45, 0), (14, 0.9, 14)),
            cyl("post", (0, 0.9, 0), (0, 7, 0), 2.0),
        ],
        "LEG_1": [
            cyl("housing", (0, 4, 0), (0, 10, 0), 2.5),
            cyl("pole", (0, 10, 0), (0, 31, 0), 2.47),
            cube("tilt_knob", (0, 8, 3.4), (6, 2, 1)),
        ],
        "LEG_2": [
            cyl("tube", elbow, collar, 2.47),
            cube("elbow_knob", (elbow[0], elbow[1], 3.4), (6, 2, 1)),
            cube("collar_knob", (collar[0], collar[1], -3.4), (6, 2, 1)),
        ],
        "LEG_3": [cyl("rod", collar, rod_end, 2.0)],
        "LEG_4": [cyl("inner", inner_0, inner_1, 1.1)],
        "HEAD": [
            sphere("ball", ball, 0.7),
            cyl("ring", add(ball, r, 12), add(ball, r, 12.3), 11.0, sides=24),
            cyl("stub", ball, add(ball, r, 1.5), 0.35),
        ],
    }
    groups = [cmds.group(shells, name=name) for name, shells in parts.items()]
    arm = cmds.group(groups, name="ARM")
    asset = cmds.group(arm, name="ASSET")
    cmds.setAttr(f"{asset}.scale", 2.0, 2.0, 2.0)
    return f"|{asset}|{arm}"


@unittest.skipUnless(
    MAYA_AVAILABLE and qt_widgets_available(), "needs a GUI Maya (--in-maya)"
)
class TestArticulatedRigPanelInMaya(unittest.TestCase):
    """The panel loaded the way the marking menu opens it (``MayaUiHandler``
    with tentacle's shared roots), acted on as a user does, over the real
    ``mtk``. GUI only: its joint table is a uitk ``TableWidget``, which
    hard-crashes mayapy in batch."""

    @classmethod
    def setUpClass(cls):
        from tentacle.tcl import Tcl

        cls.cmds = maya_module("maya.cmds")
        cls.mtk = maya_module("mayatk")
        handler = cls.mtk.MayaUiHandler.instance()
        Tcl.register_shared(handler.sb)
        cls.ui = handler.get("articulated_rig")
        cls.slots = cls.ui.slots
        from qtpy import QtWidgets

        cls.app = QtWidgets.QApplication.instance()

    def setUp(self):
        self.cmds.file(new=True, force=True)
        self.slots.plan = None
        self.slots.rig = None
        self.slots._sync_adjust()  # clear a box a failed test left checked
        self.ui.cmb_source.setCurrentIndex(0)
        self.ui.txt_name.setText("")
        self.ui.chk_end_control.setChecked(True)
        self.messages = []
        patcher = mock.patch.object(
            self.slots.sb,
            "message_box",
            side_effect=lambda message, *a, **k: self.messages.append(str(message)),
        )
        patcher.start()
        self.addCleanup(patcher.stop)
        self.arm = _build_arm(self.cmds)

    def settle(self):
        self.app.processEvents()

    def rows(self):
        table = self.ui.tbl_joints
        return [
            (table.item(r, 0).text(), table.cellWidget(r, 1).currentText())
            for r in range(table.rowCount())
        ]

    def build(self, end_control=True):
        self.ui.chk_end_control.setChecked(end_control)
        self.cmds.select(self.arm, replace=True)
        self.ui.btn_build.click()  # analyzes first when nothing is planned
        self.settle()
        self.assertIsNotNone(self.slots.rig)
        return self.slots.rig

    def test_the_panel_is_the_shared_one_over_mayatk(self):
        self.assertEqual(
            type(self.slots).__module__, "tentacle.slots.tools.articulated_rig"
        )
        self.assertIs(self.slots.tk, self.mtk)
        headers = [
            self.ui.tbl_joints.horizontalHeaderItem(c).text()
            for c in range(self.ui.tbl_joints.columnCount())
        ]
        self.assertEqual(headers, self.slots.COLUMNS)

    def test_analyze_then_build_then_retype_a_built_joint(self):
        cmds = self.cmds
        cmds.select(self.arm, replace=True)
        self.ui.btn_analyze.click()
        self.assertEqual(
            self.rows(),
            [
                ("LEG_1", "universal"),
                ("LEG_2", "hinge"),
                ("LEG_3", "hinge"),
                ("LEG_4", "slide"),
                ("HEAD", "ball"),
            ],
        )
        self.ui.txt_name.setText("desk")
        rig = self.build()
        self.assertEqual(rig.name, "desk")
        ctrl = rig.control("LEG_2")
        cmds.setKeyframe(ctrl, attribute="rz", time=1, value=10)
        cmds.setKeyframe(ctrl, attribute="rz", time=24, value=40)
        # The combo's own signal rebuilds the rig: its refresh must wait.
        self.ui.tbl_joints.cellWidget(1, 1).setCurrentText("ball")
        self.settle()
        self.assertEqual(self.rows()[1], ("LEG_2", "ball"))
        ctrl = self.slots.rig.control("LEG_2")
        self.assertEqual(cmds.keyframe(ctrl, attribute="rz", query=True), [1.0, 24.0])

    def test_limits_typed_into_a_row_and_a_row_clicked(self):
        cmds = self.cmds
        rig = self.build(end_control=False)
        self.ui.tbl_joints.item(1, self.slots.LIMITS_COLUMN).setText("rz -20..45")
        self.settle()
        ctrl = rig.control("LEG_2")
        self.assertEqual(
            cmds.transformLimits(ctrl, query=True, rotationZ=True), [-20.0, 45.0]
        )
        cmds.select(clear=True)
        self.ui.tbl_joints.selectRow(1)
        self.settle()
        self.assertEqual(
            cmds.ls(selection=True, long=True), cmds.ls(rig.control("LEG_2"), long=True)
        )

    def test_switch_ik_fk_and_rest_pose(self):
        cmds = self.cmds
        rig = self.build()
        end = rig.end_control
        cmds.move(-6.0, 7.0, 5.0, end, relative=True, worldSpace=True)
        cmds.select(end, replace=True)
        self.ui.btn_ik_fk.click()
        self.assertEqual(cmds.getAttr(f"{end}.ikBlend"), 0.0)
        self.ui.btn_ik_fk.click()
        self.assertEqual(cmds.getAttr(f"{end}.ikBlend"), 1.0)
        self.ui.btn_rest.click()
        self.assertEqual(rig.fk_state(), [0.0] * len(rig.fk_state()))

    def test_split_off_selected_adds_the_telescope(self):
        arm = self.arm
        links = [[f"{arm}|{p}"] for p in ("BASE", "LEG_1", "LEG_2")]
        links += [[f"{arm}|LEG_3", f"{arm}|LEG_4"], [f"{arm}|HEAD"]]
        self.slots.rig = self.mtk.ArticulatedRig.create(links)
        self.slots.refresh_table()
        self.assertEqual(len(self.rows()), 4)
        self.cmds.select("LEG_4", replace=True)
        self.ui.cmb_insert_type.setCurrentIndex(1)  # Joint: Slide
        self.ui.btn_insert.click()
        self.assertIn(("LEG_4", "slide"), self.rows())

    def test_adjust_pivots_puts_handles_out_and_rebuilds_when_cleared(self):
        cmds = self.cmds
        rig = self.build()
        cmds.select(rig.control("LEG_2"), replace=True)
        self.ui.chk_adjust.setChecked(True)
        self.settle()
        handles = rig.adjust_handles()
        self.assertEqual(
            sorted(cmds.ls(selection=True, long=True)),
            sorted(cmds.ls(list(handles.values()), long=True)),
        )
        before = cmds.xform(rig.joint("LEG_2"), query=True, worldSpace=True, t=True)
        cmds.move(2.0, 0.0, 0.0, handles["LEG_2"], relative=True, objectSpace=True)
        self.ui.chk_adjust.setChecked(False)
        self.settle()
        self.assertFalse(self.slots.rig.adjusting)
        after = cmds.xform(
            self.slots.rig.joint("LEG_2"), query=True, worldSpace=True, t=True
        )
        self.assertGreater(math.dist(before, after), 1.0)

    def test_limits_from_pose_and_remove(self):
        cmds = self.cmds
        rig = self.build(end_control=False)
        ctrl = rig.control("LEG_2")
        cmds.setAttr(f"{ctrl}.rz", 55.0)
        cmds.select(ctrl, replace=True)
        self.ui.btn_limits_from_pose.click()
        self.assertEqual(cmds.transformLimits(ctrl, query=True, rotationZ=True)[1], 55.0)
        self.ui.btn_remove.click()
        self.assertFalse(self.mtk.ArticulatedRig.scene_rigs())
        self.assertEqual(self.ui.tbl_joints.rowCount(), 0)

    def test_the_grab_button_makes_the_dragger_the_current_tool(self):
        cmds = self.cmds
        self.ui.btn_grab.click()
        try:
            self.assertEqual(cmds.currentCtx(), self.mtk.ArticulatedRigGrab.CONTEXT)
        finally:
            cmds.setToolTo("selectSuperContext")


if __name__ == "__main__":
    unittest.main()
