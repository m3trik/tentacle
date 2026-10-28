#!/usr/bin/python
# coding=utf-8
"""The Lightmap Baker panel's one Slots class, shared by both hosts.

It reaches its host only through ``self.tk`` (the toolkit the entry point set),
so a fake toolkit stands in for ``mtk`` / ``btk`` -- either host's engine
shape: mayatk's dial keys (``gi_depth`` / ``gi_samples``, Arnold units) or
blendertk's (``bounces``, Cycles paths) -- and records what the panel asks of
its engine. The widgets are stubs each wired by the panel's own ``*_init``,
read back through the panel's own readers. The ``.ui`` is read as XML for the
layout the panel relies on. Then the panel loads for real through Blender's
handler (Qt, no bpy) over ``btk``, and in Maya drives the real ``mtk`` on a
real scene. The engines' own side (``scope_meshes`` / ``scope_lights`` /
``select`` / ``preset_name``, the bake) is the libraries':
``test_lightmap_baker.py`` in each.
"""

import contextlib
import dataclasses
import os
import sys
import types
import unittest
import xml.etree.ElementTree as ET
from typing import Any, Optional
from unittest import mock

import pythontk as ptk

import tentacle
from _host import MAYA_AVAILABLE, maya_module
from tentacle.slots._slots import Slots
from tentacle.slots.tools.lightmap_baker import LightmapBakerSlots

UI_PATH = os.path.join(
    os.path.dirname(tentacle.__file__), "ui", "tools", "lightmap_baker.ui"
)
MONO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(tentacle.__file__))))

#: Each engine's declared preset keys and shipped tiers (the libraries'
#: ``presets/*.json``): what the panel binds its dials to.
MAYA_INT_KEYS = ("resolution", "samples", "gi_depth", "gi_samples")
BLENDER_INT_KEYS = ("resolution", "samples", "bounces")
BOOL_KEYS = (
    "adaptive",
    "include_scene_lights",
    "include_environment",
    "include_hidden_lights",
    "denoise",
    "beside_textures",
    "reflection_probe",
)
TIERS = {
    "maya": {
        "preview": {"resolution": 256, "samples": 2, "gi_depth": 2, "gi_samples": 2},
        "mobile": {"resolution": 1024, "samples": 4, "gi_depth": 4, "gi_samples": 2},
        "desktop": {"resolution": 2048, "samples": 4, "gi_depth": 6, "gi_samples": 4},
        "hero": {"resolution": 4096, "samples": 6, "gi_depth": 8, "gi_samples": 4},
    },
    "blender": {
        "preview": {"resolution": 256, "samples": 128, "bounces": 2},
        "mobile": {"resolution": 1024, "samples": 1024, "bounces": 4},
        "desktop": {"resolution": 2048, "samples": 2048, "bounces": 6},
        "hero": {"resolution": 4096, "samples": 4096, "bounces": 8},
    },
}
#: A filesystem root, so the output-directory paths are absolute on any platform.
ROOT = "C:\\" if os.name == "nt" else "/"


def _abs(*parts):
    return os.path.normpath(os.path.join(ROOT, *parts))


SRC = _abs("proj", "sourceimages")

# ---------------------------------------------------------------------------
# The fake toolkit
# ---------------------------------------------------------------------------


@dataclasses.dataclass
class _Result:
    """Enough of ``LightmapBakeResult`` for the report the panel writes."""

    maps: dict = dataclasses.field(default_factory=dict)
    excluded: list = dataclasses.field(default_factory=list)
    hidden: list = dataclasses.field(default_factory=list)
    unbaked: list = dataclasses.field(default_factory=list)
    retired: list = dataclasses.field(default_factory=list)
    refused: Optional[str] = None
    verdict: Optional[str] = None
    in_place: list = dataclasses.field(default_factory=list)
    repacked: dict = dataclasses.field(default_factory=dict)
    report: Any = None
    cancelled: bool = False

    def __bool__(self):
        return bool(self.maps)

    @property
    def files(self):
        return sorted(set(self.maps.values()))

    @property
    def folders(self):
        return sorted({os.path.dirname(path) for path in self.maps.values()})


class _Store:
    """A preset store holding a host's shipped tiers."""

    def __init__(self, tiers):
        self.tiers = tiers
        self.user_dir = "C:/presets/user"
        self.builtin_dir = "C:/presets/builtin"

    def load(self, name):
        return dict(self.tiers[name], description=f"the {name} tier")

    def exists(self, name):
        return name in self.tiers


class _Engine:
    """A stand-in for a host's ``LightmapBaker`` class: its declared keys,
    range and processors (set per host by :func:`_engine`), and instances
    that record what the panel asks of them."""

    PRESET_BOOL_KEYS = BOOL_KEYS
    OUTPUT_SUBDIR = "lightmaps"
    COMBINE_KEEP = 0.97

    instances: list = []
    #: Scope word -> the meshes / lights it gathers.
    scopes: dict = {}
    scope_light_map: dict = {}
    #: Every select() call, and what select() cannot select.
    selections: list = []
    unselectable: set = set()
    # What the next bake / dry run answers.
    refusal = None
    empty = False
    verdict = None
    excluded: tuple = ()
    hidden: tuple = ()
    retired: tuple = ()
    report = None
    rows = None
    baked = None
    folders: dict = {}
    sizes = [(1024, 0.8), (2048, 1.0)]
    combine_result = None

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.calls = []
        type(self).instances.append(self)

    @classmethod
    def preset_store(cls):
        return _Store(cls.TIERS)

    @classmethod
    def preset_name(cls, name):
        return {"quest": "mobile"}.get(name, name)

    @classmethod
    def scope_meshes(cls, scope):
        return list(cls.scopes.get(scope, ()))

    @classmethod
    def scope_lights(cls, scope):
        return list(cls.scope_light_map.get(scope, ()))

    @classmethod
    def select(cls, objects):
        objects = list(objects)
        cls.selections.append(objects)
        return [obj for obj in objects if obj not in cls.unselectable]

    def bake(self, objects, packing="atlas", output_dir=None, prefix="",
             suffix="", on_progress=None):
        self.calls.append(("bake", tuple(objects), packing))
        self.bake_args = {"output_dir": output_dir, "prefix": prefix, "suffix": suffix}
        targets = [
            obj for obj in objects
            if "light" not in str(obj).lower()
            and obj not in self.excluded
            and obj not in self.hidden
        ]
        result = _Result(
            excluded=list(self.excluded), hidden=list(self.hidden),
            retired=list(self.retired),
        )
        if self.refusal:
            result.refused = self.refusal
            return result
        if not targets:
            result.refused = "Nothing to bake: every object is in the Exclude set."
            return result
        for i, obj in enumerate(targets):
            if on_progress:
                on_progress(i, len(targets), str(obj).rsplit("|", 1)[-1])
        if self.empty:
            result.unbaked = targets
            return result
        folder = output_dir or "C:/out"
        for obj in targets:
            leaf = str(obj).rsplit("|", 1)[-1]
            name = f"Mat{suffix}.exr" if packing == "atlas" else f"{prefix}{leaf}{suffix}.exr"
            result.maps[obj] = os.path.join(folder, name)
        result.verdict = self.verdict
        return result

    def stale_report(self, output_dir=None, **_kwargs):
        self.calls.append(("stale_report",))
        self.stale_output_dir = output_dir
        return self.report or ptk.StaleReport()

    def bake_maps(self, report=None):
        if self.rows is not None:
            return list(self.rows)
        report = report or ptk.StaleReport()
        return report.map_rows(
            [{"map": "Fake_Lightmap.exr", "path": "C:/fake/Fake_Lightmap.exr",
              "folder": "lm", "objects": list(report.targets) or ["|fake"]}]
        )

    def baked_objects(self, objects=None):
        self.calls.append(("baked_objects", tuple(objects or ())))
        return list(objects or ()) if self.baked is None else list(self.baked)

    def revert(self, objects=None):
        self.calls.append(("revert", tuple(objects or ())))
        return list(objects or ())

    def track(self, objects=None):
        self.calls.append(("track", tuple(objects or ())))
        return list(objects or ())

    def map_folders(self, objects=None):
        return dict(self.folders)

    def rebake_report(self, objects=None, output_dir=None, **_kwargs):
        self.calls.append(("rebake_report", tuple(objects or ())))
        return self.report or ptk.StaleReport()

    def rebake(self, objects=None, on_progress=None, **kwargs):
        self.calls.append(("rebake", tuple(objects or ())))
        return self._rebaked(kwargs)

    def rebake_changed(self, on_progress=None, **kwargs):
        self.calls.append(("rebake_changed",))
        return self._rebaked(kwargs)

    def _rebaked(self, kwargs):
        self.rebake_kwargs = kwargs
        report = self.report or ptk.StaleReport()
        result = _Result(report=report)
        if not report.targets:
            result.refused = report.summary()
            return result
        for obj in report.targets:
            result.maps[obj] = os.path.join(
                kwargs.get("output_dir") or "C:/out",
                f"Mat{kwargs.get('suffix', '_Lightmap')}.exr",
            )
        result.in_place = list(report.in_place)
        result.repacked = dict(report.repack)
        return result

    def combine_sizes(self, maps=None):
        return list(self.sizes)

    def combine(self, maps=None, size=None, on_progress=None):
        self.calls.append(("combine", tuple(maps or ()), size))
        if self.combine_result is not None:  # a refused result is falsy, as the host's
            return self.combine_result
        return _Result(maps={"|s": "C:/out/S_Lightmap.exr"})

    def bake_breakdown(self, output_dir=None):
        self.calls.append(("bake_breakdown",))
        self.breakdown_output_dir = output_dir
        return types.SimpleNamespace(to_html=lambda: "<h1>Lightmap Bake State</h1>")


def _engine(host):
    """*host*'s ``LightmapBaker`` stand-in: :class:`_Engine` with that engine's
    keys, Samples range, adaptive processors and tiers, and record lists of its
    own (a fresh class per toolkit, so nothing leaks between tests)."""
    maya = host == "maya"
    return type(
        "LightmapBaker",
        (_Engine,),
        {
            "PRESET_INT_KEYS": MAYA_INT_KEYS if maya else BLENDER_INT_KEYS,
            "SAMPLES_RANGE": (1, 256) if maya else (1, 4096),
            "ADAPTIVE_DEVICES": ("AUTO", "GPU") if maya else ("AUTO", "GPU", "CPU"),
            "TIERS": TIERS[host],
            "instances": [],
            "scopes": {},
            "scope_light_map": {},
            "selections": [],
            "unselectable": set(),
            "folders": {},
        },
    )


class _SceneSet:
    """A scene set (Exclude / Isolate): its members, and the meshes they name."""

    def __init__(self, tk):
        self.tk, self._members = tk, None

    def define(self, objects=None):
        members = list(self.tk.selection if objects is None else objects)
        self._members = members or None
        return members

    def members(self):
        return list(self._members or ())

    def meshes(self):
        return self.tk.TextureBaker.resolve_meshes(self.members(), descendants=True)

    def exists(self):
        return self._members is not None

    def clear(self):
        self._members = None


def _toolkit(host="maya"):
    """A fake ``mtk`` / ``btk``: the names the panel calls, over test data --
    ``selection`` (what is selected), ``meshes_under`` (what an item names as
    meshes; any other ``|`` path not named for a light is a mesh) and
    ``sourceimages`` (the project's texture folder; an exception raises)."""
    tk = types.SimpleNamespace(
        host=host, selection=[], meshes_under={}, sourceimages=SRC, chunks=[]
    )
    tk.LightmapBaker = _engine(host)

    @contextlib.contextmanager
    def undo_chunk(name=""):
        tk.chunks.append(name)
        yield
        tk.chunks.append(f"/{name}")

    tk.CoreUtils = types.SimpleNamespace(
        selected_objects=lambda: list(tk.selection),
        undo_chunk=undo_chunk,
        leaf_name=lambda node: str(node).rsplit("|", 1)[-1],
    )

    def resolve_meshes(objects, descendants=False):
        found = []
        for obj in objects or ():
            default = [obj] if str(obj).startswith("|") and "light" not in str(obj).lower() else []
            for mesh in tk.meshes_under.get(obj, default):
                if mesh not in found:
                    found.append(mesh)
        return found

    def scene_source_images_dir():
        if isinstance(tk.sourceimages, Exception):
            raise tk.sourceimages
        return tk.sourceimages

    tk.TextureBaker = types.SimpleNamespace(resolve_meshes=resolve_meshes)
    tk.DataNodes = types.SimpleNamespace(scene_source_images_dir=scene_source_images_dir)
    tk.jobs = mock.MagicMock(name="ScriptJobManager")
    tk.ScriptJobManager = types.SimpleNamespace(instance=lambda: tk.jobs)
    tk.UiUtils = types.SimpleNamespace(dispatch_log_link=mock.MagicMock())
    tk.LightmapExcludeSet = _SceneSet(tk)
    tk.LightmapIsolateSet = _SceneSet(tk)
    return tk


# ---------------------------------------------------------------------------
# Stub widgets: enough of each for its ``*_init`` and the panel's readers
# ---------------------------------------------------------------------------


class _Toggle:
    """Enough of uitk's ToggleOption."""

    def __init__(self, on=False):
        self.is_on = bool(on)
        self.widget = mock.MagicMock(name="toggle button")
        self.toggled = mock.MagicMock(name="toggled")

    def set_on(self, value, *, emit=True):
        self.is_on = bool(value)


class _OptionBox:
    """Enough of uitk's OptionBoxManager: switches (found by type, all of them
    in the order added), actions, the browse and affix options."""

    def __init__(self):
        self.toggles, self.wired_all, self.actions = [], [], []
        self.browsed = self.affix = None
        self.clear_option = False

    @property
    def wired(self):
        return self.wired_all[-1] if self.wired_all else None

    def find_option(self, _option_type):
        return self.toggles[0] if self.toggles else None

    def get_options(self):
        return list(self.toggles)

    def set_toggle(self, *, initial=True, replace=True, **kwargs):
        if replace:
            self.toggles, self.wired_all = [], []
        self.toggles.append(_Toggle(initial))
        self.wired_all.append(dict(kwargs, initial=initial, replace=replace))

    def add_action(self, **kwargs):
        self.actions.append(kwargs)

    def browse(self, **kwargs):
        self.browsed = kwargs

    def set_affix(self, **kwargs):
        self.affix = kwargs

    def resolve_affix(self, text=None, *, default="prefix"):
        return ptk.StrUtils.split_affix(text or "", mode="auto", default=default)


class _Spin:
    def __init__(self, value=1):
        self._value, self.range, self.visible = value, (0, 99999), True
        self.option_box = _OptionBox()
        self.valueChanged = mock.MagicMock(name="valueChanged")

    def default_signals(self):
        return "valueChanged"

    def value(self):
        return self._value

    def setValue(self, value):
        low, high = self.range
        self._value = max(low, min(high, int(value)))

    def setRange(self, low, high):
        self.range = (low, high)
        self.setValue(self._value)

    def setVisible(self, visible):
        self.visible = bool(visible)


class _Combo:
    def __init__(self):
        self.items, self._index = [], -1
        self.option_box = _OptionBox()
        self.is_initialized = False
        self.refresh_on_show = False
        self._blocked = False
        self.currentIndexChanged = mock.MagicMock(name="currentIndexChanged")

    def default_signals(self):
        return "currentIndexChanged"

    def clear(self):
        self.items, self._index = [], -1

    def addItems(self, texts):
        for text in texts:
            self.addItem(text)

    def addItem(self, text, data=None):
        self.items.append((text, data))
        if self._index < 0:
            self._index = 0

    def count(self):
        return len(self.items)

    def itemText(self, index):
        return self.items[index][0]

    def texts(self):
        return [text for text, _data in self.items]

    def setCurrentIndex(self, index):
        self._index = index

    def currentIndex(self):
        return self._index

    def currentText(self):
        return self.items[self._index][0] if 0 <= self._index < len(self.items) else ""

    def currentData(self):
        return self.items[self._index][1] if 0 <= self._index < len(self.items) else None

    def blockSignals(self, on):
        was, self._blocked = self._blocked, bool(on)
        return was


class _Line:
    def __init__(self, text="", placeholder=""):
        self._text, self._placeholder = text, placeholder
        self.option_box = _OptionBox()
        self.textChanged = mock.MagicMock(name="textChanged")

    def default_signals(self):
        return "textChanged"

    def text(self):
        return self._text

    def setText(self, text):
        self._text = text

    def placeholderText(self):
        return self._placeholder

    def setPlaceholderText(self, text):
        self._placeholder = text


class _Footer:
    def __init__(self):
        self._text, self.level, self.ticks, self.added = "", None, [], []

    def setText(self, text, level=None):
        self._text, self.level = text, level

    def text(self):
        return self._text

    def height(self):
        return 20

    def add_widget(self, widget, background=False):
        self.added.append(widget)

    def progress(self, text=""):
        footer = self

        class _Run:
            def __enter__(self):
                def update(value=None, label=None):
                    footer.ticks.append(label)
                    return True

                return update

            def __exit__(self, *exc):
                return False

        return _Run()


class _Label:
    def __init__(self, text):
        self._text = text

    def text(self):
        return self._text

    def setText(self, text):
        self._text = text

    def toolTip(self):
        return f"{self._text} help."


class _Stack:
    def __init__(self):
        self.index = 0

    def setCurrentIndex(self, index):
        self.index = index


class _Ui:
    """The panel's window: the widgets its readers reach (the table's Qt half
    is the real-Qt class's; here ``_fill_maps`` / ``_highlight_maps`` record)."""

    def __init__(self):
        self.footer = _Footer()
        self.cmb000 = mock.MagicMock(name="cmb000")
        self.cmb002, self.cmb_scope, self.cmb_device = _Combo(), _Combo(), _Combo()
        self.cmb_resolution, self.cmb_page = _Combo(), _Combo()
        self.spn_samples, self.spn_gi_samples, self.spn_bounces = _Spin(), _Spin(), _Spin()
        self.txt_output_dir = _Line(placeholder="(blank: sourceimages/lightmaps)")
        self.txt000 = _Line(placeholder="_Lightmap")
        self.lbl_exclude, self.lbl_isolate = _Label("Exclude:"), _Label("Isolate:")
        self.stk_pages = _Stack()
        self.tbl_maps = mock.MagicMock(name="tbl_maps")
        self.settings = None
        self.visible = True
        self.destroyed = mock.MagicMock()

    def isVisible(self):
        return self.visible


#: The widgets whose ``*_init`` builds them, in the order the switchboard meets them.
_INITS = (
    "cmb_page", "cmb_scope", "cmb002", "cmb_device", "cmb_resolution",
    "spn_samples", "spn_gi_samples", "spn_bounces", "txt_output_dir", "txt000",
)


def _panel(host="maya", tk=None, **values):
    """The panel over stub widgets, each wired by its own ``*_init``, over a
    fake *host* toolkit (or *tk*, handed over before the panel is built, as
    ``Slots.tk`` is); then *values* set (see :func:`_set`)."""
    tk = tk or _toolkit(host)
    sb = mock.MagicMock()
    sb.tk = tk
    sb.ResetGesture.SAVE = "save"
    ui = sb.loaded_ui.lightmap_baker = _Ui()
    slots = LightmapBakerSlots(sb)
    for name in _INITS:
        widget = getattr(ui, name)
        getattr(slots, f"{name}_init")(widget)
        widget.is_initialized = True
    # The Manage table's Qt half: rows land in _map_rows, highlights recorded.
    slots.highlighted = []
    slots._fill_maps = lambda rows, report: setattr(
        slots, "_map_rows", {row["map"]: row for row in rows}
    )
    slots._highlight_maps = slots.highlighted.append
    _set(slots, **values)
    return slots, sb, ui, tk


def _set(slots, res=None, samples=None, gi_samples=None, bounces=None, packing=None,
         scope=None, device=None, page=None, output_dir=None, affix=None, **switches):
    """Set the panel's fields the way the user does."""
    ui = slots.ui
    if res is not None:
        slots._set_resolution(res)
    for spin, value in ((ui.spn_samples, samples), (ui.spn_gi_samples, gi_samples),
                        (ui.spn_bounces, bounces)):
        if value is not None:
            spin.setValue(value)
    if packing is not None:
        slots._set_packing(packing)
    if scope is not None:
        ui.cmb_scope.setCurrentIndex(LightmapBakerSlots._SCOPE_LABELS.index(scope))
    if device is not None:
        ui.cmb_device.setCurrentIndex(
            [value for _label, value in LightmapBakerSlots._DEVICES].index(device)
        )
    if page is not None:
        ui.cmb_page.setCurrentIndex(LightmapBakerSlots._PAGES.index(page))
    if output_dir is not None:
        ui.txt_output_dir.setText(output_dir)
    if affix is not None:
        ui.txt000.setText(affix)
    for key, on in switches.items():
        slots._set_toggle_state(key, on)


def _asked(sb, answer):
    """Answer every question with *answer* (a button name) and record each."""
    asked = []

    def message_box(text, *buttons, **_kwargs):
        asked.append((text, buttons))
        return answer

    def confirm(text, yes="Yes", no="No"):
        asked.append((text, (yes, no)))
        return answer == yes

    sb.message_box.side_effect = message_box
    sb.confirm.side_effect = confirm
    return asked


class _PanelCase(unittest.TestCase):
    def setUp(self):
        migrated = Slots._legacy_repeat_last_migrated
        Slots._legacy_repeat_last_migrated = True  # no migration under test
        self.addCleanup(setattr, Slots, "_legacy_repeat_last_migrated", migrated)
        # The class logger is shared: a fake here keeps the run's records off it.
        self.logger = mock.MagicMock()
        patcher = mock.patch.object(LightmapBakerSlots, "logger", self.logger)
        patcher.start()
        self.addCleanup(patcher.stop)


# ---------------------------------------------------------------------------
# Setup, header, pages
# ---------------------------------------------------------------------------


class TestLightmapBakerPanelSetup(_PanelCase):
    def test_setup_waits_for_the_widgets(self):
        sb = mock.MagicMock()
        sb.tk = _toolkit()
        slots = LightmapBakerSlots(sb)
        self.assertIs(slots.ui, sb.loaded_ui.lightmap_baker)
        sb.QtCore.QTimer.singleShot.assert_called_once_with(0, slots._initialize_ui)
        self.logger.set_log_prefix.assert_called_once_with("[Lightmap Baker] ")

    def test_initialize_listens_to_the_scene_and_shows_the_bake_page(self):
        slots, sb, ui, tk = _panel()
        ui.cmb_scope.setCurrentIndex(-1)  # a session saved on the retired Changed row
        slots._initialize_ui()
        events = [call.args[0] for call in tk.jobs.subscribe.call_args_list]
        self.assertEqual(
            events, ["SceneOpened", "NewSceneOpened", "SceneSaved", "Undo", "Redo"]
        )
        handlers = {call.args[0]: call.args[1] for call in tk.jobs.subscribe.call_args_list}
        self.assertEqual(handlers["SceneOpened"], slots._scene_opened)
        self.assertEqual(handlers["Undo"], slots._scene_undone)
        tk.jobs.connect_cleanup.assert_called_once_with(ui, owner=slots)
        self.assertEqual(ui.cmb_scope.currentIndex(), 0)
        self.assertEqual(ui.stk_pages.index, 0)
        combo, fix = ui.footer._lightmap_manage
        fix.setVisible.assert_called_with(False)

    def test_an_event_the_host_lacks_never_blocks_the_open(self):
        slots, sb, ui, tk = _panel()
        tk.jobs.subscribe.side_effect = [None, ValueError("no such event"), None, None, None]
        slots._initialize_ui()  # must not raise
        self.assertEqual(tk.jobs.subscribe.call_count, 5)

    def test_header_offers_the_bake_report_and_help(self):
        slots, sb, ui, tk = _panel()
        header = mock.MagicMock()
        slots.header_init(header)
        header.config_buttons.assert_called_once_with("menu", "collapse", "hide")
        names = [call.kwargs.get("setObjectName") for call in header.menu.add.call_args_list]
        self.assertEqual(names, ["show_bake_state"])
        self.assertEqual(sb.tooltip.fmt.call_args.kwargs["title"], "Lightmap Baker")
        self.assertEqual(
            header.set_help_text.call_args.kwargs["url"], LightmapBakerSlots.HELP_URL
        )
        body = sb.tooltip.fmt.call_args.kwargs["body"]
        self.assertIn("Maya: Arnold", body)
        self.assertIn("Blender: Cycles", body)

    def test_the_help_links_mayatks_reference(self):
        self.assertTrue(
            LightmapBakerSlots.HELP_URL.endswith("/mayatk/blob/main/docs/lightmap_baker.md")
        )
        doc = os.path.join(MONO, "mayatk", "docs", "lightmap_baker.md")
        if os.path.isdir(os.path.join(MONO, "mayatk")):
            self.assertTrue(os.path.isfile(doc), doc)

    def test_the_page_picker_lists_bake_then_manage_and_rereads_on_show(self):
        slots, sb, ui, tk = _panel()
        self.assertEqual(ui.cmb_page.texts(), ["Bake", "Manage"])
        self.assertTrue(ui.cmb_page.refresh_on_show, "re-read on every later show")
        _set(slots, page="Manage")
        slots.cmb_page_init(ui.cmb_page)  # the show's refresh: no repopulate
        self.assertEqual(ui.cmb_page.currentText(), "Manage")
        self.assertEqual(ui.stk_pages.index, 1)
        self.assertEqual(tk.LightmapBaker.instances[-1].calls, [("stale_report",)])

    def test_scope_bakes_fresh_and_changed_is_the_manage_pages(self):
        self.assertEqual(LightmapBakerSlots._SCOPE_LABELS, ("Selected", "Visible", "Scene"))
        self.assertEqual(LightmapBakerSlots._PAGES, ("Bake", "Manage"))

    def test_only_the_manage_page_reads_the_scene(self):
        slots, sb, ui, tk = _panel(res=2048, output_dir=_abs("bakes", "lm"))
        slots.cmb_page(0)
        self.assertEqual(tk.LightmapBaker.instances, [], "the Bake page reads nothing")
        _set(slots, page="Manage")
        tk.LightmapBaker.report = ptk.StaleReport(
            targets=("|room|A",), stale={"|room|A": (ptk.BakeBaseline.Reason.MOVED,)}
        )
        slots.cmb_page(1)
        baker = tk.LightmapBaker.instances[-1]
        self.assertEqual(ui.stk_pages.index, 1)
        self.assertEqual(ui.footer.text(), "1 changed", "the table's states, counted")
        self.assertEqual(baker.kwargs["resolution"], 2048, "the panel's dials")
        self.assertEqual(
            baker.stale_output_dir, _abs("bakes", "lm"),
            "the dry run asks the folder Bake writes to",
        )

    def test_a_dry_run_that_fails_says_so(self):
        slots, sb, ui, tk = _panel(page="Manage")
        tk.LightmapBaker.stale_report = mock.Mock(side_effect=RuntimeError("no scene"))
        self.assertIsNone(slots._refresh_page())
        self.assertEqual(ui.footer.level, "error")
        self.assertIn("see the log", ui.footer.text())


# ---------------------------------------------------------------------------
# Dials: the engine's keys, units and defaults
# ---------------------------------------------------------------------------


class TestLightmapBakerPanelDials(_PanelCase):
    def test_maya_dials_take_arnolds_units_and_keys(self):
        slots, sb, ui, tk = _panel("maya")
        self.assertEqual(ui.spn_samples.range, (1, 256))
        self.assertEqual(
            (ui.spn_samples.value(), ui.spn_gi_samples.value(), ui.spn_bounces.value()),
            (4, 2, 4),
            "the default tier's dials are the factory defaults",
        )
        self.assertTrue(ui.spn_gi_samples.visible)
        self.assertEqual(slots._resolution(), 1024)

    def test_blender_dials_take_cycles_units_and_hide_gi_samples(self):
        slots, sb, ui, tk = _panel("blender")
        self.assertEqual(ui.spn_samples.range, (1, 4096))
        self.assertEqual((ui.spn_samples.value(), ui.spn_bounces.value()), (1024, 4))
        self.assertFalse(ui.spn_gi_samples.visible, "Cycles has no GI samples")
        self.assertNotIn("gi_samples", slots._preset_fields())

    def test_an_unreadable_default_tier_leaves_the_ui_values(self):
        tk = _toolkit()
        tk.LightmapBaker.preset_store = staticmethod(
            lambda: mock.Mock(load=mock.Mock(side_effect=OSError("gone")))
        )
        slots, sb, ui, tk = _panel(tk=tk)
        self.assertEqual(ui.spn_samples.value(), 1, "the stub's own value, untouched")
        self.assertEqual(slots._resolution(), 1024)

    def test_the_resolution_snaps_to_its_fixed_sizes(self):
        slots, sb, ui, tk = _panel()
        self.assertEqual(
            ui.cmb_resolution.texts(),
            [f"Resolution:\t{r}" for r in (256, 512, 1024, 2048, 4096)],
        )
        slots._set_resolution(1500)
        self.assertEqual(slots._resolution(), 1024)

    def test_the_processor_rows_are_auto_gpu_cpu(self):
        slots, sb, ui, tk = _panel()
        self.assertEqual([data for _text, data in ui.cmb_device.items], ["AUTO", "GPU", "CPU"])
        self.assertTrue(all(t.startswith("Processor:") for t in ui.cmb_device.texts()))
        self.assertEqual(slots._device(), "AUTO")

    def _gate(self, host):
        slots, sb, ui, tk = _panel(host)
        slots._initialize_ui()
        target, trigger, rule = sb.enable_when.call_args.args[1:4]
        self.assertIs(target, slots._toggle("adaptive").widget)
        self.assertEqual(trigger, "cmb_device")
        return rule

    def test_adaptive_greys_out_on_an_arnold_cpu_bake(self):
        rule = self._gate("maya")
        self.assertEqual([rule(d) for d in ("AUTO", "GPU", "CPU")], [True, True, False])

    def test_adaptive_stays_live_on_every_cycles_processor(self):
        rule = self._gate("blender")
        self.assertEqual([rule(d) for d in ("AUTO", "GPU", "CPU")], [True, True, True])


# ---------------------------------------------------------------------------
# Presets: the store's keys, the switches, seeding and reset
# ---------------------------------------------------------------------------


class TestLightmapBakerPanelPresets(_PanelCase):
    _TUNED = dict(
        res=2048, packing="atlas", adaptive=False, include_environment=False,
        denoise=False, beside_textures=True, reflection_probe=False,
        include_scene_lights=False, include_hidden_lights=True,
    )
    _TUNED_SWITCHES = {
        "adaptive": False, "include_scene_lights": False, "include_environment": False,
        "include_hidden_lights": True, "denoise": False, "beside_textures": True,
        "reflection_probe": False,
    }

    def test_maya_save_reads_every_setting_under_its_store_key(self):
        slots, *_ = _panel("maya", samples=6, gi_samples=5, bounces=3, **self._TUNED)
        self.assertEqual(
            slots._preset_values(),
            {"packing": "atlas", "resolution": 2048, "samples": 6, "gi_depth": 3,
             "gi_samples": 5, **self._TUNED_SWITCHES},
        )

    def test_blender_save_reads_every_setting_under_its_store_key(self):
        slots, *_ = _panel("blender", samples=64, bounces=2, **self._TUNED)
        self.assertEqual(
            slots._preset_values(),
            {"packing": "atlas", "resolution": 2048, "samples": 64, "bounces": 2,
             **self._TUNED_SWITCHES},
        )

    def test_every_key_the_panel_saves_is_one_the_headless_path_reads(self):
        """Drift guard: a key only the panel knew would save, load in the
        panel, and silently do nothing in ``from_preset``."""
        for host, ints in (("maya", MAYA_INT_KEYS), ("blender", BLENDER_INT_KEYS)):
            with self.subTest(host=host):
                slots, *_ = _panel(host)
                self.assertEqual(
                    set(slots._preset_fields()) - {"packing"}, set(ints) | set(BOOL_KEYS)
                )

    def test_a_saved_preset_loads_back_onto_every_widget(self):
        for host in ("maya", "blender"):
            with self.subTest(host=host):
                saved = _panel(host, samples=3, bounces=1, **self._TUNED)[0]._preset_values()
                target = _panel(host)[0]
                applied = target._apply_preset_values(dict(saved, description="ignored"))
                self.assertEqual(applied, len(saved))
                self.assertEqual(target._preset_values(), saved)

    def test_a_shipped_tier_moves_the_dials_and_leaves_the_switches(self):
        """Overlay semantics: a built-in stores only the quality dials."""
        for host, dials in (
            ("maya", {"resolution": 2048, "samples": 4, "gi_depth": 6, "gi_samples": 4}),
            ("blender", {"resolution": 2048, "samples": 2048, "bounces": 6}),
        ):
            with self.subTest(host=host):
                slots, sb, ui, tk = _panel(host, **self._TUNED)
                slots._apply_preset_values(tk.LightmapBaker.preset_store().load("desktop"))
                values = slots._preset_values()
                self.assertEqual({k: values[k] for k in dials}, dials)
                self.assertEqual(
                    {k: values[k] for k in self._TUNED_SWITCHES}, self._TUNED_SWITCHES
                )

    def test_a_bad_value_is_skipped_not_fatal(self):
        slots, sb, ui, tk = _panel("blender", samples=64)
        applied = slots._apply_preset_values({"samples": "lots", "bounces": 3})
        self.assertEqual(applied, 1)
        self.assertEqual((ui.spn_samples.value(), ui.spn_bounces.value()), (64, 3))
        self.assertTrue(self.logger.warning.called)

    def test_the_preset_combo_is_the_template_over_the_engines_store(self):
        slots, sb, ui, tk = _panel()
        presets = sb.PresetManager.return_value
        presets.active_preset = "mobile"
        presets.exists.return_value = True
        widget = mock.MagicMock()
        slots.cmb000_init(widget)
        kwargs = sb.PresetManager.call_args.kwargs
        self.assertEqual(kwargs["preset_dir"], "C:/presets/user")
        self.assertEqual(kwargs["builtin_dir"], "C:/presets/builtin")
        self.assertEqual(kwargs["value_provider"], slots._preset_values)
        self.assertEqual(kwargs["value_applier"], slots._apply_preset_values)
        presets.use_logger.assert_called_once_with(slots.logger)
        presets.wire_combo.assert_called_once_with(widget, placeholder="Preset…")
        self.assertIs(widget.restore_state, False, "the store's pointer owns the pick")

    def test_the_modified_marker_follows_every_preset_field(self):
        slots, sb, ui, tk = _panel()
        slots._presets = mock.MagicMock()
        slots._initialize_ui()
        ui.spn_samples.valueChanged.connect.assert_called_once()
        ui.cmb002.currentIndexChanged.connect.assert_called_once()
        ui.txt_output_dir.option_box.toggles[0].toggled.connect.assert_called_once()
        slots._presets.refresh_modified_state.assert_called()

    # Seeding: once per machine; a pointer on a retired tier follows the rename.

    def _open(self, settings, pointer):
        slots, sb, ui, tk = _panel()
        ui.settings = settings
        presets = types.SimpleNamespace(
            active_preset=pointer,
            exists=lambda name: name in TIERS["maya"],
            use_logger=lambda _logger: None,
            wire_combo=lambda widget, placeholder=None: None,
        )
        sb.PresetManager.return_value = presets
        slots.cmb000_init(mock.MagicMock())
        return presets.active_preset

    class _Settings:
        def __init__(self):
            self.values = {}

        def value(self, key, default=None):
            return self.values.get(key, default)

        def setValue(self, key, value):
            self.values[key] = value

    def test_the_first_open_names_the_default_tier(self):
        self.assertEqual(self._open(self._Settings(), None), "mobile")

    def test_an_open_after_a_reset_keeps_the_pointer_cleared(self):
        settings = self._Settings()
        self._open(settings, None)  # the first open seeds it
        self.assertIsNone(self._open(settings, None), "a reset cleared it")

    def test_a_pointer_left_on_a_renamed_tier_follows_the_rename(self):
        settings = self._Settings()
        settings.setValue(LightmapBakerSlots._PRESET_SEEDED_KEY, True)
        self.assertEqual(self._open(settings, "quest"), "mobile")

    # Reset to Defaults: uitk's grammar; what the panel owes is the pointer.

    def test_reset_to_defaults_is_uitks_grammar(self):
        slots, sb, ui, tk = _panel()
        button = mock.MagicMock()
        slots.btn_reset_defaults_init(button)
        sb.ResetGesture.assert_called_once_with(button, on_performed=slots._after_reset)

    def test_a_reset_lets_go_of_the_active_preset(self):
        for action in ("reset", "factory"):
            with self.subTest(action=action):
                slots, *_ = _panel()
                slots._presets = mock.MagicMock(active_preset="mobile")
                slots._after_reset(action)
                self.assertIsNone(slots._presets.active_preset)
                slots._presets.refresh_combo.assert_called_once_with()

    def test_saving_the_current_values_as_defaults_keeps_the_preset(self):
        slots, *_ = _panel()
        slots._presets = mock.MagicMock(active_preset="mobile")
        slots._after_reset("save")
        self.assertEqual(slots._presets.active_preset, "mobile")
        slots._presets.refresh_combo.assert_not_called()

    def test_a_reset_before_the_combo_is_wired_is_a_no_op(self):
        slots, *_ = _panel()
        slots._after_reset("reset")  # must not raise


# ---------------------------------------------------------------------------
# Switches: each rides the field it qualifies
# ---------------------------------------------------------------------------


class TestLightmapBakerPanelSwitches(_PanelCase):
    def test_the_switches_are_keyed_as_the_preset_store_keys_them(self):
        self.assertEqual(set(LightmapBakerSlots._TOGGLES), set(BOOL_KEYS))

    def test_each_switch_rides_its_field_under_a_panel_scoped_key(self):
        slots, sb, ui, tk = _panel()
        for key, (field, default) in LightmapBakerSlots._TOGGLES.items():
            with self.subTest(key):
                box = getattr(ui, field).option_box
                place = slots._field_switches(key).index(key)
                self.assertEqual(
                    box.wired_all[place]["settings_key"], f"lightmap_baker_{key}"
                )
                self.assertEqual(box.wired_all[place]["initial"], default)
                self.assertEqual(slots._toggle_state(key), default)

    def test_the_panel_opens_on_atlas_by_material_with_the_probe_on(self):
        slots, sb, ui, tk = _panel()
        self.assertEqual(ui.cmb002.texts(), list(LightmapBakerSlots._PACKING_LABELS))
        self.assertEqual(slots._packing(), "atlas")
        self.assertTrue(slots._reflection_probe())
        self.assertEqual(ui.cmb002.option_box.wired["icon"], "camera")

    def test_the_scope_opens_on_the_selection_with_its_three_lighting_switches(self):
        """Include Scene Lighting, Include Environment, Include Hidden Lights:
        each read from its own button, so flipping one never reads as another;
        every icon one uitk ships."""
        slots, sb, ui, tk = _panel()
        self.assertEqual(ui.cmb_scope.texts(), ["Selected", "Visible", "Scene"])
        self.assertEqual(slots._scope(), "selected")
        wired = ui.cmb_scope.option_box.wired_all
        self.assertEqual([w["initial"] for w in wired], [True, True, False])
        icons = os.path.join(os.path.dirname(__import__("uitk").__file__), "icons")
        for w in wired:
            self.assertNotIn("gated_widgets", w)
            for key in ("icon", "icon_off"):
                if w.get(key):
                    self.assertTrue(os.path.isfile(os.path.join(icons, f"{w[key]}.svg")), w[key])
        _set(slots, include_scene_lights=False, include_hidden_lights=True)
        self.assertEqual(
            (slots._include_scene_lights(), slots._include_environment(),
             slots._include_hidden_lights()),
            (False, True, True),
        )

    def test_a_switch_read_before_its_field_is_wired_gives_the_shipped_default(self):
        slots, sb, ui, tk = _panel()
        for field in ("cmb_scope", "spn_samples", "cmb_resolution", "txt_output_dir", "cmb002"):
            getattr(ui, field).option_box.toggles = []
        self.assertEqual(
            (slots._include_environment(), slots._adaptive(), slots._denoise(),
             slots._beside_textures(), slots._reflection_probe()),
            (True, True, True, False, True),
        )

    def test_a_preset_load_writes_a_switch_through_its_toggle(self):
        slots, *_ = _panel()
        applied = slots._apply_preset_values(
            {"include_environment": False, "denoise": False, "adaptive": False,
             "beside_textures": True, "reflection_probe": False}
        )
        self.assertEqual(applied, 5)
        self.assertEqual(
            (slots._include_environment(), slots._denoise(), slots._adaptive(),
             slots._beside_textures(), slots._reflection_probe()),
            (False, False, False, True, False),
        )

    def test_the_beside_switch_says_in_the_empty_field_where_the_maps_go(self):
        slots, sb, ui, tk = _panel()
        self.assertEqual(ui.txt_output_dir.placeholderText(), "(blank: sourceimages/lightmaps)")
        self.assertEqual(
            ui.txt_output_dir.option_box.wired["on_toggled"], slots._show_output_mode
        )
        slots._show_output_mode(True)
        self.assertEqual(
            ui.txt_output_dir.placeholderText(),
            "(blank: beside textures, else sourceimages/lightmaps)",
        )

    def test_the_output_field_browses_and_opens_its_folder(self):
        slots, sb, ui, tk = _panel()
        box = ui.txt_output_dir.option_box
        self.assertEqual(box.browsed["mode"], "directory")
        self.assertEqual(box.browsed["callback"], slots._relativize_output_dir)
        opens = [a for a in box.actions if a["callback"] == slots.open_output]
        self.assertEqual(len(opens), 1)

    def test_the_name_field_takes_the_lightmap_affix(self):
        slots, sb, ui, tk = _panel()
        self.assertEqual(
            ui.txt000.option_box.affix,
            {"default": "auto", "settings_key": "lightmap_baker_affix",
             "convention_key": "lightmap"},
        )


# ---------------------------------------------------------------------------
# Output directory
# ---------------------------------------------------------------------------


class TestLightmapBakerPanelOutput(_PanelCase):
    def test_an_empty_field_is_the_projects_lightmaps_folder(self):
        slots, *_ = _panel()
        self.assertEqual(slots._output_dir(), os.path.join(SRC, "lightmaps"))

    def test_a_relative_entry_resolves_under_the_texture_folder(self):
        slots, sb, ui, tk = _panel(output_dir="lightmaps")
        self.assertEqual(slots._output_dir(), os.path.join(SRC, "lightmaps"))
        ui.txt_output_dir.setText("bake/lm")
        self.assertEqual(slots._output_dir(), os.path.normpath(os.path.join(SRC, "bake/lm")))

    def test_a_full_path_is_used_as_is_with_or_without_a_project(self):
        full = _abs("bakes", "lm")
        slots, sb, ui, tk = _panel(output_dir=full)
        self.assertEqual(slots._output_dir(), full)
        tk.sourceimages = None
        self.assertEqual(slots._output_dir(), full)

    def test_an_entry_is_trimmed_and_expanded(self):
        slots, sb, ui, tk = _panel(output_dir='  " lightmaps "  ')
        self.assertEqual(slots._output_dir(), os.path.join(SRC, "lightmaps"))
        with mock.patch.dict(os.environ, {"LM_OUT": _abs("shared")}):
            ui.txt_output_dir.setText("%LM_OUT%" if os.name == "nt" else "$LM_OUT")
            self.assertEqual(slots._output_dir(), _abs("shared"))

    @unittest.skipUnless(os.name == "nt", "a driveless rooted entry is a full path on POSIX")
    def test_a_driveless_entry_stays_under_the_texture_folder(self):
        slots, *_ = _panel(output_dir="/lightmaps")
        self.assertEqual(slots._output_dir(), os.path.join(SRC, "lightmaps"))

    def test_no_project_never_returns_a_relative_path(self):
        for failure in (None, RuntimeError("no project")):
            with self.subTest(failure=failure):
                slots, sb, ui, tk = _panel(output_dir="lightmaps")
                tk.sourceimages = failure
                self.assertIsNone(slots._output_dir())
                ui.txt_output_dir.setText("")
                self.assertIsNone(slots._output_dir())

    def test_a_browsed_folder_is_stored_portably(self):
        slots, sb, ui, tk = _panel()
        slots._relativize_output_dir(os.path.join(SRC, "lightmaps", "hero"))
        self.assertEqual(ui.txt_output_dir.text(), "lightmaps/hero")
        slots._relativize_output_dir(SRC)
        self.assertEqual(ui.txt_output_dir.text(), "")
        for outside in (_abs("bakes"), _abs("proj", "sourceimages_old")):
            ui.txt_output_dir.setText(outside)
            slots._relativize_output_dir(outside)
            self.assertEqual(ui.txt_output_dir.text(), outside)

    def test_open_output_opens_where_the_last_bake_wrote(self):
        slots, *_ = _panel()
        wrote = os.path.dirname(os.path.abspath(__file__))
        slots._last_output_dir = wrote
        with mock.patch.object(ptk.FileUtils, "open_explorer", return_value=True) as opened:
            slots.open_output()
        self.assertEqual(opened.call_args.args[0], wrote)

    def test_open_output_falls_back_to_the_texture_folder_then_says_so(self):
        slots, sb, ui, tk = _panel()
        with mock.patch.object(ptk.FileUtils, "open_explorer", return_value=True) as opened:
            slots.open_output()  # lightmaps not made yet: its base
        self.assertEqual(opened.call_args.args[0], SRC)
        tk.sourceimages = None
        slots.open_output()
        self.assertEqual(ui.footer.level, "warning")
        self.assertIn("set a project", ui.footer.text())


# ---------------------------------------------------------------------------
# Bake
# ---------------------------------------------------------------------------


class TestLightmapBakerPanelBake(_PanelCase):
    def _bake(self, host="maya", meshes=("|cube",), **values):
        tk = _toolkit(host)
        tk.LightmapBaker.scopes = {"selected": list(meshes), "scene": list(meshes)}
        slots, sb, ui, tk = _panel(tk=tk, **values)
        slots.b000()
        return slots, ui, tk

    def test_bake_hands_the_scope_and_every_dial_to_the_engine(self):
        slots, ui, tk = self._bake("maya", res=2048, samples=8, gi_samples=7, bounces=3)
        (baker,) = tk.LightmapBaker.instances
        self.assertEqual(
            baker.kwargs,
            {"device": "AUTO", "resolution": 2048, "samples": 8, "gi_depth": 3,
             "gi_samples": 7, "adaptive": True, "include_scene_lights": True,
             "include_environment": True, "include_hidden_lights": False,
             "denoise": True, "beside_textures": False, "reflection_probe": True},
        )
        self.assertEqual(baker.calls, [("bake", ("|cube",), "atlas")])
        self.assertEqual(baker.bake_args["output_dir"], os.path.join(SRC, "lightmaps"))
        self.assertIn("Baked 1 object", ui.footer.text())

    def test_blender_bakes_take_its_own_keys(self):
        slots, ui, tk = self._bake("blender", bounces=6, device="CPU", adaptive=False)
        kwargs = tk.LightmapBaker.instances[0].kwargs
        self.assertEqual(
            (kwargs["bounces"], kwargs["device"], kwargs["adaptive"]), (6, "CPU", False)
        )
        self.assertNotIn("gi_samples", kwargs)
        self.assertNotIn("gi_depth", kwargs)

    def test_the_rows_are_bake_inputs_not_cosmetics(self):
        slots, ui, tk = self._bake(
            device="CPU", include_environment=False, denoise=False,
            reflection_probe=False, include_scene_lights=False,
            include_hidden_lights=True, beside_textures=True,
        )
        kwargs = tk.LightmapBaker.instances[0].kwargs
        self.assertEqual(
            {k: kwargs[k] for k in ("device", "include_environment", "denoise",
                                    "reflection_probe", "include_scene_lights",
                                    "include_hidden_lights", "beside_textures")},
            {"device": "CPU", "include_environment": False, "denoise": False,
             "reflection_probe": False, "include_scene_lights": False,
             "include_hidden_lights": True, "beside_textures": True},
        )

    def test_the_scopes_lights_ride_beside_its_meshes(self):
        """What lights the bake with Include Scene Lighting off; the bake's
        targets stay the meshes, and nothing is handed twice."""
        tk = _toolkit()
        tk.LightmapBaker.scopes = {"scene": ["|room|wall", "|room|floor"]}
        tk.LightmapBaker.scope_light_map = {"scene": ["|room|lampLight", "|room|wall"]}
        slots, sb, ui, tk = _panel(tk=tk, scope="Scene")
        slots.b000()
        self.assertEqual(
            tk.LightmapBaker.instances[0].calls[0][1],
            ("|room|wall", "|room|floor", "|room|lampLight"),
        )

    def test_packing_reaches_the_bake_and_its_report(self):
        slots, ui, tk = self._bake(packing="per_object")
        self.assertEqual(tk.LightmapBaker.instances[0].calls[0][2], "per_object")
        self.assertIn("1 map in", ui.footer.text())
        slots, ui, tk = self._bake(packing="atlas")
        self.assertIn("1 atlas in", ui.footer.text())

    def test_the_footer_names_each_object_as_it_bakes(self):
        slots, ui, tk = self._bake(meshes=("|pbA", "|pbB"))
        self.assertEqual(ui.footer.ticks[:2], ["Baking pbA…  (1/2)", "Baking pbB…  (2/2)"])

    def test_the_affix_resolves_to_a_prefix_or_a_suffix(self):
        for affix, expected in (("_Lightmap", ("", "_Lightmap")), ("LM_", ("LM_", "")),
                                ("", ("", "_Lightmap"))):
            with self.subTest(affix=affix):
                slots, ui, tk = self._bake(affix=affix)
                args = tk.LightmapBaker.instances[0].bake_args
                self.assertEqual((args["prefix"], args["suffix"]), expected)

    def test_bake_writes_into_the_resolved_output_dir(self):
        slots, ui, tk = self._bake(output_dir="lightmaps", packing="atlas")
        baker = tk.LightmapBaker.instances[0]
        self.assertEqual(baker.bake_args["output_dir"], os.path.join(SRC, "lightmaps"))

    def test_nothing_in_scope_builds_no_baker(self):
        slots, ui, tk = self._bake(meshes=())
        self.assertEqual(tk.LightmapBaker.instances, [])
        self.assertIn("Select one or more mesh objects", ui.footer.text())
        self.assertEqual(ui.footer.level, "warning")
        slots, ui, tk = self._bake(meshes=(), scope="Visible")
        self.assertEqual(ui.footer.text(), "No meshes found for scope 'visible'.")

    def test_no_project_bakes_nothing_and_says_so(self):
        tk = _toolkit()
        tk.LightmapBaker.scopes = {"selected": ["|cube"]}
        tk.sourceimages = None
        slots, sb, ui, tk = _panel(tk=tk)
        slots.b000()
        self.assertEqual(tk.LightmapBaker.instances[0].calls, [])
        self.assertIn("No project to bake into", ui.footer.text())
        self.assertEqual(ui.footer.level, "error")

    def test_a_refusal_is_shown_as_the_engine_words_it(self):
        tk = _toolkit()
        tk.LightmapBaker.scopes = {"selected": ["|cube"]}
        tk.LightmapBaker.refusal = "Bake skipped: all 4 scene light(s) are hidden."
        slots, sb, ui, tk = _panel(tk=tk)
        slots.b000()
        self.assertEqual(ui.footer.text(), tk.LightmapBaker.refusal)
        self.assertEqual(ui.footer.level, "error")
        self.assertIsNone(slots._last_output_dir)

    def test_an_empty_bake_says_where_to_look(self):
        tk = _toolkit()
        tk.LightmapBaker.scopes = {"selected": ["|cube"]}
        tk.LightmapBaker.empty = True
        slots, sb, ui, tk = _panel(tk=tk)
        slots.b000()
        self.assertEqual(ui.footer.text(), "Bake produced no output (see the log).")

    def test_the_report_counts_what_it_left_alone_and_the_verdict(self):
        tk = _toolkit()
        tk.LightmapBaker.scopes = {"selected": ["|kept", "|leftOut", "|hidden"]}
        tk.LightmapBaker.excluded = ("|leftOut",)
        tk.LightmapBaker.hidden = ("|hidden",)
        tk.LightmapBaker.retired = ("C:/out/old_LM.exr", "C:/out/old_LM_1.exr")
        tk.LightmapBaker.verdict = "bake is essentially UNLIT."
        slots, sb, ui, tk = _panel(tk=tk, packing="per_object")
        slots.b000()
        text = ui.footer.text()
        for words in ("1 excluded", "1 hidden", "2 old → Recycle Bin on save",
                      "WARNING: bake is essentially UNLIT."):
            self.assertIn(words, text)
        self.assertEqual(ui.footer.level, "warning")
        self.assertEqual(slots._last_output_dir, os.path.join(SRC, "lightmaps"))

    def test_the_report_counts_the_atlases_repacked(self):
        slots, *_ = _panel(packing="atlas")
        text = slots._bake_report(
            _Result(maps={"|c": "C:/out/Crate_LM.exr"},
                    repacked={"Crate_LM.exr": "rcA: its cell no longer fits"})
        )
        self.assertIn("1 atlas", text)
        self.assertIn("1 re-packed", text)


# ---------------------------------------------------------------------------
# Exclude / Isolate rows
# ---------------------------------------------------------------------------


class TestLightmapBakerPanelSetRows(_PanelCase):
    def _rows(self):
        slots, sb, ui, tk = _panel()
        tk.meshes_under = {"|grp": ["|grp|a", "|grp|b"], "|loc": []}
        return slots, sb, ui, tk

    def test_the_exclude_row_sets_selects_and_clears_the_scene_set(self):
        slots, sb, ui, tk = self._rows()
        tk.selection = ["|grp"]
        slots.set_exclusions()
        self.assertEqual(ui.lbl_exclude.text(), "Exclude (2):", "a group counts its meshes")
        self.assertIn("2 meshes excluded", ui.footer.text())

        tk.selection = []
        slots.select_exclusions()
        self.assertEqual(tk.LightmapBaker.selections[-1], ["|grp"])
        self.assertEqual(ui.footer.text(), "Selected 1 excluded object.")

        slots.clear_exclusions()
        self.assertFalse(tk.LightmapExcludeSet.exists())
        self.assertEqual(ui.lbl_exclude.text(), "Exclude:")
        self.assertIn("cleared", ui.footer.text())

        tk.LightmapExcludeSet.define(["|grp|a"])
        slots.set_exclusions()  # nothing selected: clears, and says so
        self.assertFalse(tk.LightmapExcludeSet.exists())
        self.assertIn("Nothing selected", ui.footer.text())

        tk.selection = ["|loc"]  # no mesh in it: excludes nothing, says so
        slots.set_exclusions()
        self.assertEqual(ui.lbl_exclude.text(), "Exclude:")
        self.assertIn("holds no meshes", ui.footer.text())
        self.assertEqual(ui.footer.level, "warning")

    def test_the_isolate_row_is_the_exclude_rows_twin(self):
        slots, sb, ui, tk = self._rows()
        tk.selection = ["|grp"]
        slots.set_isolation()
        self.assertEqual(ui.lbl_isolate.text(), "Isolate (2):")
        self.assertIn("2 meshes isolated", ui.footer.text())
        self.assertEqual(ui.lbl_exclude.text(), "Exclude:", "Exclude is untouched")
        slots.select_isolation()
        self.assertEqual(tk.LightmapBaker.selections[-1], ["|grp"])
        slots.clear_isolation()
        self.assertFalse(tk.LightmapIsolateSet.exists())
        self.assertIn("one pass", ui.footer.text())
        slots.clear_isolation()
        self.assertIn("Nothing is isolated", ui.footer.text())

    def test_a_member_the_host_cannot_select_is_counted_not_forced(self):
        """Blender: a hidden member, or one outside the view layer, takes no
        select; unhiding it would change the scene the set leaves alone."""
        slots, sb, ui, tk = self._rows()
        tk.LightmapExcludeSet.define(["|grp", "|hiddenBox"])
        tk.LightmapBaker.unselectable = {"|hiddenBox"}
        slots.select_exclusions()
        self.assertIn("Selected 1 excluded object.", ui.footer.text())
        self.assertIn("1 could not be selected", ui.footer.text())

    def test_selecting_an_empty_set_selects_nothing(self):
        slots, sb, ui, tk = self._rows()
        slots.select_exclusions()
        self.assertEqual(tk.LightmapBaker.selections, [])
        self.assertEqual(ui.footer.level, "warning")

    def test_a_row_hangs_select_and_clear_and_a_live_hover(self):
        slots, sb, ui, tk = self._rows()
        button = mock.MagicMock()
        button.toolTip.return_value = "Exclude help."
        slots.set_exclusions_init(button)
        actions = [call.kwargs for call in button.option_box.add_action.call_args_list]
        self.assertEqual([a["icon"] for a in actions], ["select", "clear"])
        self.assertTrue(all(a["settings_key"] is False for a in actions))
        self.assertEqual(sb.tooltip.bind.call_count, 2, "the button and its label")

    def test_the_hover_lists_the_meshes_the_label_counts(self):
        slots, sb, ui, tk = self._rows()
        tk.LightmapExcludeSet.define(["|grp"])
        slots._set_row_tooltip("set_exclusions", "Exclude help.")
        meshes = sb.tooltip.stored_items.call_args.args[0]
        kwargs = sb.tooltip.stored_items.call_args.kwargs
        self.assertEqual(meshes, ["|grp|a", "|grp|b"])
        self.assertEqual(kwargs["formatter"]("|grp|a"), "a")
        self.assertIn("in this scene", kwargs["noun"])
        tk.LightmapExcludeSet.meshes = mock.Mock(side_effect=RuntimeError("no scene"))
        self.assertEqual(
            slots._set_row_tooltip("set_exclusions", "Exclude help."), "Exclude help."
        )

    def test_a_label_refresh_never_raises(self):
        slots, sb, ui, tk = self._rows()
        del tk.LightmapExcludeSet  # a root that does not expose the set
        slots._refresh_set_row("set_exclusions")
        self.assertEqual(ui.lbl_exclude.text(), "Exclude:")


# ---------------------------------------------------------------------------
# Manage: the table menu's verbs, Select, Fix All, the Bake Report
# ---------------------------------------------------------------------------


def _moved(*targets, **fields):
    """A dry run whose *targets* moved."""
    return ptk.StaleReport(
        targets=tuple(targets),
        stale={t: (ptk.BakeBaseline.Reason.MOVED,) for t in targets},
        **fields,
    )


class TestLightmapBakerPanelManage(_PanelCase):
    def test_select_changed_selects_the_targets_and_highlights_their_maps(self):
        tk = _toolkit()
        report = tk.LightmapBaker.report = _moved("|room|A")
        tk.LightmapBaker.rows = report.map_rows(
            [{"map": "Room_LM.exr", "path": "C:/p/Room_LM.exr", "folder": "lm",
              "objects": ["|room|A", "|room|B"]},
             {"map": "Desk_LM.exr", "path": "C:/p/Desk_LM.exr", "folder": "lm",
              "objects": ["|room|D"]}]
        )
        slots, sb, ui, tk = _panel(tk=tk)
        slots.select_by_state("changed")
        self.assertEqual(ui.cmb_page.currentText(), "Manage", "the page shows")
        self.assertEqual(
            tk.LightmapBaker.selections[-1], ["|room|A"], "exactly what re-bakes"
        )
        self.assertEqual(slots.highlighted[-1], {"Room_LM.exr"})
        self.assertEqual(ui.footer.text(), "Selected 1 object on 1 map.")

    def test_a_pick_that_finds_nothing_clears_the_last_one(self):
        slots, sb, ui, tk = _panel(page="Manage")
        slots.select_by_state("changed")
        self.assertEqual(tk.LightmapBaker.selections[-1], [])
        self.assertEqual(ui.footer.text(), "No changed maps.")

    def test_select_by_state_takes_the_readers_of_its_maps(self):
        tk = _toolkit()
        tk.LightmapBaker.rows = ptk.StaleReport(untracked=("|u",)).map_rows(
            [{"map": "U_LM.exr", "path": "C:/p/U_LM.exr", "folder": "lm",
              "objects": ["|u"]}]
        )
        slots, sb, ui, tk = _panel(tk=tk, page="Manage")
        slots.select_by_state("untracked")
        self.assertEqual(tk.LightmapBaker.selections[-1], ["|u"])
        self.assertEqual(ui.footer.text(), "Selected 1 object on 1 map.")

    def test_the_footer_select_runs_the_pick_and_shows_its_label(self):
        slots, sb, ui, tk = _panel()
        combo = mock.MagicMock()
        combo.itemText.return_value = "Split"
        ui.footer._lightmap_manage = (combo, mock.MagicMock())
        slots.select_by_state = mock.MagicMock()
        slots._on_select(2)
        combo.setCurrentIndex.assert_called_once_with(0)
        slots.select_by_state.assert_called_once_with("split")

    def test_highlighting_rows_selects_their_readers(self):
        slots, sb, ui, tk = _panel()
        slots._selected_maps = lambda: [{"objects": ["|b", "|a"]}, {"objects": ["|a"]}]
        slots._select_map_readers()
        self.assertEqual(tk.LightmapBaker.selections[-1], ["|a", "|b"])
        slots._selected_maps = lambda: []
        slots._select_map_readers()
        self.assertEqual(tk.LightmapBaker.selections[-1], [], "none: clear")

    def test_the_table_menu_fits_the_highlighted_rows(self):
        slots, sb, ui, tk = _panel()
        items = {name: mock.MagicMock() for name in
                 ("open_map_folder", "combine_selected", "track_selected")}
        ui.tbl_maps.menu.findChild.side_effect = lambda _type, name: items[name]
        slots._selected_maps = lambda: [{"path": None, "state": "split"}]
        slots._fit_map_menu()
        items["open_map_folder"].setEnabled.assert_called_with(False)
        items["combine_selected"].setEnabled.assert_called_with(True)
        items["track_selected"].setEnabled.assert_called_with(False)

    def test_open_map_folder_opens_its_home(self):
        slots, sb, ui, tk = _panel()
        slots._selected_maps = lambda: []
        slots.open_map_folder()
        self.assertEqual((ui.footer.text(), ui.footer.level), ("Highlight a map first.", "warning"))
        slots._selected_maps = lambda: [{"path": None}]
        slots.open_map_folder()
        self.assertEqual((ui.footer.text(), ui.footer.level), ("That map is missing.", "error"))
        slots._selected_maps = lambda: [
            {"path": "C:/session/lm/A_LM.exr", "saves_to": "C:/proj/lm/A_LM.exr"}
        ]
        with mock.patch.object(ptk.FileUtils, "open_explorer") as opened:
            slots.open_map_folder()
        self.assertEqual(opened.call_args.args[0], "C:/proj/lm", "where it lands at the save")

    def test_combine_asks_the_size_and_packs_the_split(self):
        tk = _toolkit()
        tk.LightmapBaker.report = ptk.StaleReport(
            split={"S_LM.exr": ("S_LM.exr", "S_LM_1.exr")},
            split_materials={"S_LM.exr": ("sMat", "sMatDup")},
        )
        slots, sb, ui, tk = _panel(tk=tk, page="Manage")
        slots._refresh_manage()
        slots._selected_maps = lambda: [{"map": "S_LM.exr", "state": "split"}]
        asked = _asked(sb, "Cancel")
        slots.combine_selected()
        text, buttons = asked[0]
        self.assertIn("S_LM_1.exr", text)
        self.assertIn("Merges the duplicate materials (sMat, sMatDup)", text)
        self.assertEqual(buttons, ("1024 px: 80% detail", "2048 px: all detail", "Cancel"))
        self.assertEqual(ui.footer.text(), "Combine cancelled.")
        _asked(sb, "2048 px: all detail")
        slots.combine_selected()
        combined = [c for b in tk.LightmapBaker.instances for c in b.calls if c[0] == "combine"]
        self.assertEqual(combined, [("combine", ("S_LM.exr",), 2048)])
        self.assertEqual(ui.footer.text(), "Combined into S_Lightmap.exr.")
        slots._selected_maps = lambda: [{"map": "T_LM.exr", "state": "ok"}]
        slots.combine_selected()
        self.assertEqual(ui.footer.text(), "Highlight a split map first.")

    def test_fix_all_leaves_no_row_needing_a_fix(self):
        """Fix All, once confirmed (``ptk.StaleReport.fix_plan``): the
        missing map off its hidden object, the split combined, the untracked
        tracked, then what changed re-baked -- the render last; the steps that
        render nothing one undo step; the footer one short line."""
        tk = _toolkit()
        report = tk.LightmapBaker.report = _moved(
            "|cube", in_place=("|cube",), untracked=("|u",), unbakeable=("|h",),
            split_materials={"S_LM.exr": ("sMat", "sMatDup")},
        )
        tk.LightmapBaker.rows = (
            report.map_rows([{"map": "Fake_LM.exr", "path": "C:/fake/Fake_LM.exr",
                              "folder": "lm", "objects": ["|cube"]}])
            + ptk.StaleReport(split={"S_LM.exr": ("S_LM.exr", "S_LM_1.exr")}).map_rows(
                [{"map": "S_LM.exr", "path": "C:/p/S_LM.exr", "folder": "lm",
                  "objects": ["|s"]}])
            + ptk.StaleReport(untracked=("|u",)).map_rows(
                [{"map": "U_LM.exr", "path": "C:/p/U_LM.exr", "folder": "lm",
                  "objects": ["|u"]}])
            + ptk.StaleReport(unbakeable=("|h",)).map_rows(
                [{"map": "H_LM.exr", "path": None, "folder": "lm", "objects": ["|h"]}])
        )
        slots, sb, ui, tk = _panel(tk=tk, page="Manage")
        asked = _asked(sb, "Fix All")

        def steps():
            return [c for b in tk.LightmapBaker.instances for c in b.calls
                    if c[0] in ("revert", "combine", "track", "rebake_changed")]

        slots.fix_all()
        question = asked[0][0]
        for words in ("Take the lightmap off 1 object", "Combine 1 split map",
                      "Start tracking 1 untracked object", "Re-bake 1 changed object",
                      "merges the duplicate materials (sMat, sMatDup)"):
            self.assertIn(words, question)
        self.assertEqual(
            steps(),
            [("revert", ("|h",)), ("combine", ("S_LM.exr",), None), ("track", ("|u",)),
             ("rebake_changed",)],
            "the render last",
        )
        self.assertEqual(tk.chunks, ["Fix All", "/Fix All"])
        self.assertEqual(
            ui.footer.text(), "Fix All: 1 reverted, 1 combined, 1 tracked, 1 re-baked."
        )
        # A step refused is counted as not done, never as done.
        tk.LightmapBaker.combine_result = _Result(refused="Nothing to combine.")
        slots.fix_all()
        self.assertEqual(
            ui.footer.text(),
            "Fix All: 1 reverted, 1 not combined, 1 tracked, 1 re-baked (see the log).",
        )
        self.assertEqual(ui.footer.level, "warning")
        # A cancel stops it: nothing after the artist said stop runs.
        tk.LightmapBaker.instances.clear()
        tk.LightmapBaker.combine_result = _Result(refused="Combine cancelled.", cancelled=True)
        slots.fix_all()
        self.assertEqual(steps(), [("revert", ("|h",)), ("combine", ("S_LM.exr",), None)])
        self.assertEqual(ui.footer.text(), "Fix All cancelled: 1 reverted, 1 not combined.")

    def test_fix_all_with_nothing_to_fix_asks_nothing(self):
        slots, sb, ui, tk = _panel(page="Manage")
        tk.LightmapBaker.rows = []
        slots.fix_all()
        sb.confirm.assert_not_called()
        self.assertEqual(ui.footer.text(), "Nothing to fix.")

    def test_select_changed_then_rebake_redoes_it_with_the_panels_dials(self):
        tk = _toolkit()
        tk.LightmapBaker.report = _moved("|csCube", in_place=("|csCube",))
        slots, sb, ui, tk = _panel(tk=tk, page="Manage", res=512)
        slots.select_by_state("changed")
        self.assertEqual(tk.LightmapBaker.selections[-1], ["|csCube"])
        tk.selection = ["|csCube"]  # what the select made
        slots.rebake_selected()
        baker = [b for b in tk.LightmapBaker.instances
                 if b.calls and b.calls[-1][0] == "rebake"][-1]
        self.assertEqual(baker.kwargs["resolution"], 512)
        self.assertEqual(baker.calls[-1], ("rebake", ("|csCube",)))
        self.assertIs(baker.rebake_kwargs["relocate"], False, "maps stay where they are")
        self.assertEqual(baker.rebake_kwargs["suffix"], "_Lightmap")
        self.assertIn("1 in place", ui.footer.text())

    def test_rebake_with_nothing_selected_says_how_to_pick(self):
        slots, sb, ui, tk = _panel()
        slots.rebake_selected()
        self.assertEqual(
            ui.footer.text(), "Highlight the maps to re-bake (or select their objects)."
        )
        tk.selection = ["|unbaked"]
        slots.rebake_selected()
        self.assertEqual(ui.footer.text(), "None of the selection is baked yet.")

    def test_rebake_asks_when_the_panels_dials_are_not_the_bakes(self):
        """A fresh panel holds its default dials, not the preset the maps were
        baked with: every map would re-bake at the wrong size, unasked."""
        tk = _toolkit()
        tk.LightmapBaker.report = ptk.StaleReport(
            targets=("|c",), stale={"|c": (ptk.BakeBaseline.Reason.LIGHTING,)},
            lighting=(ptk.BakeBaseline.SETTINGS,), in_place=("|c",),
        )
        slots, sb, ui, tk = _panel(tk=tk)
        tk.selection = ["|c"]
        asked = _asked(sb, "Cancel")
        slots.rebake_selected()
        self.assertIn("Bounces", asked[0][0])
        self.assertIn("preset", asked[0][0])
        self.assertNotIn("rebake", [c[0] for b in tk.LightmapBaker.instances for c in b.calls])
        self.assertEqual(ui.footer.text(), "Re-Bake cancelled.")

    def test_rebake_asks_before_an_atlas_repacks_whole(self):
        tk = _toolkit()
        tk.LightmapBaker.report = _moved(
            "|c", repack={"Crate_LM.exr": "c: its cell no longer fits"}, joining=("|j1", "|j2")
        )
        slots, sb, ui, tk = _panel(tk=tk)
        tk.selection = ["|c"]
        asked = _asked(sb, "Cancel")
        slots.rebake_selected()
        text, buttons = asked[0]
        self.assertIn("3 objects", text)
        self.assertIn("its cell no longer fits", text)
        self.assertEqual(buttons, ("Bake All", "Cancel"))
        _asked(sb, "Bake All")
        slots.rebake_selected()
        self.assertEqual(tk.LightmapBaker.instances[-1].calls[-1], ("rebake", ("|c",)))

    def test_rebake_asks_keep_or_move_when_its_maps_live_elsewhere(self):
        tk = _toolkit()
        tk.LightmapBaker.report = _moved("|c", in_place=("|c",))
        tk.LightmapBaker.folders = {"C:/proj/sourceimages": ["Crate_LM.exr"]}
        slots, sb, ui, tk = _panel(tk=tk, output_dir=_abs("bakes", "lm"))
        tk.selection = ["|c"]
        for answer, relocate in (("Keep", False), ("Move", True)):
            with self.subTest(answer=answer):
                asked = _asked(sb, answer)
                slots.rebake_selected()
                self.assertIn("C:/proj/sourceimages", asked[0][0])
                self.assertEqual(asked[0][1], ("Keep", "Move", "Cancel"))
                self.assertIs(tk.LightmapBaker.instances[-1].rebake_kwargs["relocate"], relocate)
        blank = _panel(tk=tk)[0]  # a blank Output Directory: each map stays
        asked = _asked(blank.sb, "Cancel")
        blank.rebake_selected()
        self.assertEqual(asked, [])

    def test_revert_asks_first_and_cancel_changes_nothing(self):
        slots, sb, ui, tk = _panel()
        tk.selection = ["|cube"]
        asked = _asked(sb, "Cancel")
        slots.revert_selected()
        text, buttons = asked[0]
        self.assertIn("1 selected object", text)
        self.assertEqual(buttons, ("Ok", "Cancel"))
        self.assertNotIn("revert", [c[0] for c in slots._baker.calls])
        self.assertEqual(ui.footer.text(), "Revert cancelled.")

    def test_revert_routes_the_selected_meshes_once_confirmed(self):
        """Faces name their mesh, as for a bake: read as objects only, a face
        selection was "nothing selected", and the dialog offered to revert
        EVERY baked object."""
        slots, sb, ui, tk = _panel()
        tk.selection = ["|cube.f[0]"]
        tk.meshes_under = {"|cube.f[0]": ["|cube"]}
        _asked(sb, "Ok")
        slots.revert_selected()
        self.assertEqual(
            slots._baker.calls, [("baked_objects", ("|cube",)), ("revert", ("|cube",))]
        )
        self.assertIn("Reverted 1 object", ui.footer.text())

    def test_revert_with_nothing_selected_or_nothing_baked_asks_nothing(self):
        slots, sb, ui, tk = _panel()
        asked = _asked(sb, "Ok")
        slots.revert_selected()
        self.assertIn("select their objects", ui.footer.text())
        tk.selection = ["|grp"]
        tk.meshes_under = {"|grp": []}  # a group with no mesh under it
        slots.revert_selected()
        self.assertIn("has a lightmap", ui.footer.text())
        tk.selection = ["|cube"]
        tk.LightmapBaker.baked = []
        slots.revert_selected()
        self.assertIn("has a lightmap", ui.footer.text())
        self.assertEqual(asked, [])

    def test_start_tracking_tracks_the_selected_meshes(self):
        slots, sb, ui, tk = _panel()
        slots.track_selected()
        self.assertEqual(ui.footer.text(), "Highlight the untracked maps first.")
        tk.selection = ["|grp"]
        tk.meshes_under = {"|grp": ["|grp|a", "|grp|b"]}
        slots.track_selected()
        self.assertEqual(tk.LightmapBaker.instances[-1].calls, [("track", ("|grp|a", "|grp|b"))])
        self.assertEqual(ui.footer.text(), "Tracking 2 objects.")
        tk.LightmapBaker.track = lambda self, objects=None: []
        slots.track_selected()
        self.assertEqual(ui.footer.text(), "None of the selected objects is untracked.")

    def test_the_bake_report_is_one_window_that_reads_itself_again(self):
        slots, sb, ui, tk = _panel(output_dir=_abs("bakes", "lm"))
        view = sb.text_view_dialog.return_value
        view.isVisible.return_value = True
        slots.show_bake_state()
        args, kwargs = sb.text_view_dialog.call_args
        self.assertIn("Lightmap Bake State", args[0])
        self.assertEqual(args[1:], ("Ok",), "no footer Refresh: the header has one")
        self.assertEqual(kwargs["title"], "Lightmap Bake State")
        self.assertTrue(callable(kwargs["link_handler"]), "its links act")
        self.assertEqual(tk.LightmapBaker.instances[-1].breakdown_output_dir, _abs("bakes", "lm"))
        kwargs["on_refresh"]()  # the header's refresh button
        view.setText.assert_called()
        slots.show_bake_state()  # asked again while open: the same window
        self.assertEqual(sb.text_view_dialog.call_count, 1)
        view.present.assert_called_once_with()
        events = [c.args[0] for c in tk.jobs.subscribe.call_args_list]
        self.assertEqual(events, ["SceneSaved", "SceneOpened", "NewSceneOpened"])
        view.isVisible.return_value = False  # closed: asked again, a new one
        slots.show_bake_state()
        self.assertEqual(sb.text_view_dialog.call_count, 2)
        tk.jobs.unsubscribe_all.assert_called_with(view)

    def test_a_bake_report_that_fails_says_so(self):
        slots, sb, ui, tk = _panel()
        tk.LightmapBaker.bake_breakdown = mock.Mock(side_effect=RuntimeError("no scene"))
        slots.show_bake_state()
        sb.text_view_dialog.assert_not_called()
        self.assertEqual(ui.footer.level, "error")


# ---------------------------------------------------------------------------
# Scene events: one read per burst
# ---------------------------------------------------------------------------


class TestLightmapBakerPanelSceneEvents(_PanelCase):
    def test_an_undo_reads_the_set_rows_now_and_the_table_once_it_settles(self):
        """Every Undo ran the Manage page's whole dry run (0.7-1.9 s on the
        production room), once per step of a held Ctrl+Z."""
        slots, sb, ui, tk = _panel(page="Manage")
        rows, reads = [], []
        slots._refresh_set_row = rows.append
        slots._refresh_manage = lambda footer=True: reads.append(footer)
        slots._scene_undone()
        slots._scene_undone()
        self.assertEqual(rows, list(LightmapBakerSlots._SET_ROWS) * 2)
        self.assertEqual(reads, [], "no dry run per step")
        timer = sb.QtCore.QTimer.return_value
        self.assertEqual(sb.QtCore.QTimer.call_count, 1, "one timer")
        self.assertEqual(timer.start.call_args_list, [mock.call(400)] * 2)
        timer.timeout.connect.call_args.args[0]()  # it settles
        self.assertEqual(reads, [True], "one dry run")

    def test_an_undo_off_the_manage_page_reads_no_table(self):
        slots, sb, ui, tk = _panel(page="Bake")
        slots._scene_undone()
        sb.QtCore.QTimer.assert_not_called()

    def test_a_load_reported_twice_is_read_once(self):
        """Blender's load_post backs both an open and a new scene."""
        slots, sb, ui, tk = _panel()
        reads = []
        slots._refresh_scene_sets = lambda manage=True: reads.append(manage)
        slots._scene_opened()
        slots._scene_opened()
        timer = sb.QtCore.QTimer.return_value
        self.assertEqual(sb.QtCore.QTimer.call_count, 1)
        self.assertEqual(timer.start.call_args_list, [mock.call(0)] * 2)
        self.assertEqual(reads, [], "not per event")
        timer.timeout.connect.call_args.args[0]()
        self.assertEqual(reads, [True])


# ---------------------------------------------------------------------------
# The .ui
# ---------------------------------------------------------------------------


class TestLightmapBakerPanelUi(unittest.TestCase):
    """The panel's shape, read off the ``.ui``: what the bake gathers, the
    machine it runs on, the quality dials, where the files go -- each switch
    riding the field it qualifies -- then the action group ending the Bake
    page (the WebXR preview panel's ``grp_process`` shape)."""

    @classmethod
    def setUpClass(cls):
        cls.root = ET.parse(UI_PATH).getroot()

    def _items(self, layout_name):
        layout = next(i for i in self.root.iter("layout") if i.get("name") == layout_name)
        return [child.get("name") for item in layout.findall("item") for child in item]

    def _widget(self, name):
        return next(w for w in self.root.iter("widget") if w.get("name") == name)

    def _property(self, widget, prop):
        return next(p for p in self._widget(widget).findall("property") if p.get("name") == prop)

    def test_every_widget_the_panel_uses_exists(self):
        names = {w.get("name") for w in self.root.iter("widget")}
        for name in ("header", "footer", "cmb000", "cmb002", "cmb_scope", "cmb_device",
                     "cmb_resolution", "cmb_page", "stk_pages", "page_bake", "page_manage",
                     "spn_samples", "spn_gi_samples", "spn_bounces", "txt_output_dir",
                     "txt000", "lbl_exclude", "lbl_isolate", "set_exclusions",
                     "set_isolation", "tbl_maps", "b000", "btn_reset_defaults"):
            self.assertIn(name, names)
        for retired in ("lbl_bake_set", "select_bake_set"):
            self.assertNotIn(retired, names)

    def test_the_sections_read_top_to_bottom(self):
        self.assertEqual(
            self._items("main_layout"),
            ["header", "cmb_page", "stk_pages", "verticalSpacer", "footer"],
        )
        self.assertEqual(
            self._items("bake_layout"),
            ["cmb_scope", "exclude_layout", "isolate_layout", "cmb002", "cmb_device",
             "quality_group", "output_group", "grp_process"],
        )
        self.assertEqual(self._items("manage_layout"), ["tbl_maps"])
        self.assertEqual(self._items("isolate_layout"), ["lbl_isolate", "set_isolation"])
        self.assertEqual(self._items("output_layout"), ["txt_output_dir", "txt000"])

    def test_the_processor_is_not_a_quality_dial(self):
        """It names one machine's hardware, so no preset stores it."""
        self.assertEqual(
            self._items("quality_layout"),
            ["cmb_resolution", "spn_samples", "spn_gi_samples", "spn_bounces"],
        )

    def test_the_action_group_reads_preset_then_reset_then_bake(self):
        self.assertEqual(self._items("process_layout"), ["cmb000", "btn_reset_defaults", "b000"])
        self.assertEqual(self._widget("btn_reset_defaults").get("class"), "QPushButton")
        self.assertEqual(
            self._property("btn_reset_defaults", "text").findtext("string"), "Reset to Defaults"
        )

    def test_no_switch_is_left_as_a_checkbox_row(self):
        boxes = [w.get("name") for w in self.root.iter("widget")
                 if w.get("class") in ("QCheckBox", "CheckBox")]
        self.assertEqual(boxes, [], "every switch rides its field's option box")

    def test_the_empty_output_field_names_the_lightmaps_folder(self):
        self.assertEqual(
            self._property("txt_output_dir", "placeholderText").findtext("string"),
            "(blank: sourceimages/lightmaps)",
        )

    def test_the_wording_serves_both_hosts(self):
        """Host words only in a parenthetical naming both, or Arnold's own dial."""
        text = ET.tostring(self.root, encoding="unicode")
        self.assertNotIn("Script Editor", text)
        self.assertNotIn("Maya project", text)
        self.assertIn("Blender:", text)
        self.assertIn("Maya:", text)


# ---------------------------------------------------------------------------
# The panel for real: Blender's handler over btk (Qt, no bpy)
# ---------------------------------------------------------------------------


def _qt_widgets():
    try:
        from qtpy import QtWidgets

        return QtWidgets
    except Exception:  # noqa: BLE001 -- Qt absent
        return None


@unittest.skipIf(MAYA_AVAILABLE, "real Qt widgets and real Maya crash in one process")
@unittest.skipIf(_qt_widgets() is None, "Qt not available")
class TestLightmapBakerPanelLoads(unittest.TestCase):
    """The shared panel loaded through a real (offscreen) Qt / Switchboard /
    ``BlenderUiHandler`` stack over ``btk``, the way ``tcl_blender`` stands it
    up: what only real widgets answer -- the option-box wraps, the window's
    state, the Manage table and the footer controls. The dry run and the map
    rows are stood in for (``LightmapBaker.stale_report`` / ``bake_maps``)."""

    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        blendertk_repo = os.path.join(MONO, "blendertk")
        if os.path.isdir(blendertk_repo) and blendertk_repo not in sys.path:
            sys.path.insert(0, blendertk_repo)
        try:
            import blendertk
            from blendertk.ui_utils.blender_ui_handler import BlenderUiHandler
        except Exception as error:  # noqa: BLE001 -- the Blender side absent
            raise unittest.SkipTest(f"blendertk unavailable: {error}") from error
        from uitk import Switchboard
        from uitk.testing import TestSandbox

        from tentacle.tcl import Tcl

        TestSandbox.activate()  # the panel's settings stay off the live stores
        QtWidgets = _qt_widgets()
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        cls.btk = blendertk
        handler = BlenderUiHandler(switchboard=Switchboard())
        cls.sb = handler.sb
        Tcl.register_shared(cls.sb)
        cls.ui = handler.get("lightmap_baker")
        for _ in range(5):
            cls.app.processEvents()
        cls.slots = cls.sb.get_slots_instance(cls.ui)

    def _show_page(self, index):
        self.ui.cmb_page.setCurrentIndex(index)
        self.slots.cmb_page(index)
        self.app.processEvents()

    def _manage(self, rows, report):
        baker = self.btk.LightmapBaker
        with mock.patch.object(baker, "stale_report", return_value=report), \
                mock.patch.object(baker, "bake_maps", return_value=rows), \
                mock.patch.object(self.slots, "_output_dir", return_value=None):
            self._show_page(1)

    def _quietly(self, run):
        """Highlight rows with no scene to select their readers in."""
        table = self.ui.tbl_maps
        blocked = table.blockSignals(True)
        try:
            run(table)
        finally:
            table.blockSignals(blocked)

    def _menu_item(self, menu, name):
        return menu.findChild(self.sb.QtWidgets.QPushButton, name)

    def tearDown(self):
        self._quietly(lambda table: table.clearSelection())
        self._show_page(0)

    def test_the_tool_binds_tentacles_slots_over_btk(self):
        self.assertIsInstance(self.slots, LightmapBakerSlots)
        self.assertEqual(type(self.slots).__module__, "tentacle.slots.tools.lightmap_baker")
        self.assertIs(self.slots.tk, self.btk)

    def test_the_help_card_links_the_reference(self):
        self.assertEqual(self.ui.header.help_url(), LightmapBakerSlots.HELP_URL)

    def test_the_dials_take_cycles_units(self):
        """Seeded in their ``_init``, the tier's values are the factory
        defaults the window's state resets to; GI Samples hides."""
        from uitk import StateManager

        state = StateManager.for_widget(self.ui)
        self.assertEqual(self.ui.spn_samples.maximum(), 4096)
        self.assertEqual(state.default_for(self.ui.spn_samples), 1024)
        self.assertEqual(state.default_for(self.ui.spn_bounces), 4)
        self.assertTrue(self.ui.spn_gi_samples.isHidden())

    def test_every_switch_is_wired_to_its_field(self):
        from uitk import ToggleOption

        for key, (field, _default) in LightmapBakerSlots._TOGGLES.items():
            with self.subTest(key):
                toggles = [
                    option for option in getattr(self.ui, field).option_box.get_options()
                    if isinstance(option, ToggleOption)
                ]
                place = self.slots._field_switches(key).index(key)
                self.assertIs(self.slots._toggle(key), toggles[place])
                self.assertIsInstance(self.slots._toggle_state(key), bool)

    def test_a_wrapped_field_is_still_readable_state_managed_and_in_place(self):
        """The wrap reparents each field into its option box's container: a
        dead wrapper raises here rather than at bake time, the state still
        restores and resets it, and its section survives."""
        from uitk import StateManager

        slots, ui = self.slots, self.ui
        self.assertIn(slots._scope(), [s.lower() for s in slots._SCOPE_LABELS])
        self.assertIn(slots._resolution(), slots._RESOLUTIONS)
        self.assertGreaterEqual(ui.spn_samples.value(), 1)
        self.assertIsInstance(ui.txt_output_dir.text(), str)
        self.assertIn(slots._packing(), ("atlas", "per_object"))
        self.assertIn(slots._device(), ("AUTO", "GPU", "CPU"))
        state = StateManager.for_widget(ui)
        for field, group in (("cmb_scope", "page_bake"), ("spn_samples", "quality_group"),
                             ("cmb_resolution", "quality_group"),
                             ("txt_output_dir", "output_group")):
            with self.subTest(field):
                widget = getattr(ui, field)
                self.assertIsNotNone(state.default_for(widget))
                self.assertIs(widget.option_box.container.parent(), getattr(ui, group))

    def test_a_panel_reset_reaches_the_switches(self):
        toggle = self.slots._toggle("denoise")
        was, default = toggle.is_on, toggle._default_on()
        try:
            toggle.set_on(not default)
            self.ui.cmb_resolution.option_box.restore_option_defaults()
            self.assertEqual(toggle.is_on, default)
        finally:
            toggle.set_on(was)

    def test_adaptive_stays_live_on_a_cycles_cpu_bake(self):
        button = self.slots._toggle("adaptive").widget
        try:
            self.ui.cmb_device.setCurrentIndex(2)  # CPU
            self.app.processEvents()
            self.assertEqual(self.slots._device(), "CPU")
            self.assertTrue(button.isEnabled())
        finally:
            self.ui.cmb_device.setCurrentIndex(0)

    def test_the_combos_list_their_fixed_rows(self):
        ui = self.ui
        self.assertEqual(
            [ui.cmb_resolution.itemText(i) for i in range(ui.cmb_resolution.count())],
            [f"Resolution:\t{r}" for r in (256, 512, 1024, 2048, 4096)],
        )
        self.assertEqual(
            [ui.cmb_scope.itemText(i) for i in range(ui.cmb_scope.count())],
            ["Selected", "Visible", "Scene"],
        )
        self.assertEqual(
            [ui.cmb_page.itemText(i) for i in range(ui.cmb_page.count())], ["Bake", "Manage"]
        )

    def test_a_preset_snaps_the_dials_and_writes_the_real_toggles(self):
        """(From blendertk's handler suite, 2026-10.)"""
        slots, ui = self.slots, self.ui
        store = self.btk.LightmapBaker.preset_store()
        preview, desktop = store.load("preview"), store.load("desktop")
        before = slots._preset_values()
        try:
            slots._apply_preset_values(preview)
            self.assertEqual(slots._resolution(), preview["resolution"])
            slots._apply_preset_values(desktop)
            self.assertEqual(
                (slots._resolution(), ui.spn_samples.value(), ui.spn_bounces.value()),
                (desktop["resolution"], desktop["samples"], desktop["bounces"]),
            )
            slots._apply_preset_values({"adaptive": False, "beside_textures": True})
            self.assertIs(slots._adaptive(), False)
            self.assertIs(slots._beside_textures(), True)
            self.assertTrue(ui.txt_output_dir.placeholderText().startswith("(blank: beside"))
        finally:
            slots._apply_preset_values(before)

    def test_the_preset_combo_lists_the_shipped_tiers(self):
        items = [self.ui.cmb000.itemText(i) for i in range(self.ui.cmb000.count())]
        self.assertIsNotNone(self.slots._presets)
        self.assertLessEqual({"preview", "mobile", "desktop", "hero"}, set(items))

    def test_the_bake_page_bakes_fresh_and_the_header_holds_the_report(self):
        QPushButton = self.sb.QtWidgets.QPushButton
        self.assertEqual(
            [b.objectName() for b in self.ui.header.menu.findChildren(QPushButton)
             if b.objectName() and not b.objectName().startswith("hdr_")],
            ["show_bake_state"],
        )
        self.assertIsNone(self._menu_item(self.ui.tbl_maps.menu, "show_bake_state"))
        self._show_page(0)
        self.assertEqual(self.ui.stk_pages.currentWidget(), self.ui.page_bake)
        self.assertEqual(self.ui.b000.text(), "Bake Lightmaps")
        self.assertTrue(self.ui.b000.isEnabled())

    def test_the_output_field_opens_its_folder(self):
        opens = [
            option for option in self.ui.txt_output_dir.option_box.get_options()
            if getattr(option, "_action_handler", None) == self.slots.open_output
        ]
        self.assertEqual(len(opens), 1)

    def test_preset_and_reset_are_the_bake_pages(self):
        ui = self.ui
        self._manage([], ptk.StaleReport())
        for widget in (ui.cmb000, ui.btn_reset_defaults, ui.b000):
            self.assertFalse(widget.isVisibleTo(ui), widget.objectName())
        self._show_page(0)
        for widget in (ui.cmb000, ui.btn_reset_defaults, ui.b000):
            self.assertTrue(widget.isVisibleTo(ui), widget.objectName())

    def test_the_table_menu_holds_the_selections_verbs(self):
        menu = self.ui.tbl_maps.menu
        labels = {name: self._menu_item(menu, name).text() for name in (
            "rebake_selected", "combine_selected", "track_selected", "revert_selected",
            "open_map_folder")}
        self.assertEqual(labels, {
            "rebake_selected": "Re-Bake", "combine_selected": "Combine…",
            "track_selected": "Start Tracking", "revert_selected": "Revert…",
            "open_map_folder": "Open Folder"})
        QPushButton = self.sb.QtWidgets.QPushButton
        buttons = [b.objectName() for b in self.ui.page_manage.findChildren(QPushButton)
                   if not menu.isAncestorOf(b)]
        self.assertEqual(buttons, [], "the Manage page carries no buttons of its own")
        self.assertIsNone(self._menu_item(menu, "merge_duplicate_materials"))
        self.assertFalse(hasattr(self.slots, "merge_duplicate_materials"))

    def test_the_manage_page_lists_each_map_with_its_state(self):
        report = _moved("RoomA")
        rows = report.map_rows([
            {"map": "Room_LM.exr", "path": "C:/p/Room_LM.exr", "folder": "lm",
             "objects": ["RoomA", "RoomB"], "writer": None, "size": (512, 512)},
            {"map": "Lost_LM.exr", "path": None, "folder": "lm",
             "objects": ["RoomC"], "writer": None, "size": None}])
        self._manage(rows, report)
        table = self.ui.tbl_maps
        self.assertEqual(self.ui.stk_pages.currentWidget(), self.ui.page_manage)
        cells = {table.item(r, 0).text(): (table.item(r, 1).text(), table.item(r, 2).text())
                 for r in range(table.rowCount())}
        self.assertEqual(cells, {"Room_LM.exr": ("2", "1 changed"), "Lost_LM.exr": ("1", "missing")})
        room = next(r for r in range(2) if table.item(r, 0).text() == "Room_LM.exr")
        tip = table.item(room, 2).toolTip()
        self.assertIn("RoomA: moved", tip)
        self.assertIn("Re-Bake", tip, "the tooltip names the fix")

    def test_highlighting_a_row_selects_its_maps_readers(self):
        report = ptk.StaleReport()
        rows = report.map_rows([{"map": "Room_LM.exr", "path": "C:/p/Room_LM.exr",
                                 "folder": "lm", "objects": ["A", "B"], "writer": None,
                                 "size": (512, 512)}])
        self._manage(rows, report)
        with mock.patch.object(self.btk.LightmapBaker, "select", return_value=[]) as select:
            self.ui.tbl_maps.selectRow(0)
            self.app.processEvents()
        select.assert_called_with(["A", "B"])

    def test_select_changed_highlights_the_targets_maps_quietly(self):
        report = _moved("A")
        rows = report.map_rows([
            {"map": "Room_LM.exr", "path": "C:/p/Room_LM.exr", "folder": "lm",
             "objects": ["A", "B"], "writer": None, "size": (512, 512)},
            {"map": "Desk_LM.exr", "path": "C:/p/Desk_LM.exr", "folder": "lm",
             "objects": ["D"], "writer": None, "size": (512, 512)}])
        self._manage(rows, report)
        baker = self.btk.LightmapBaker
        with mock.patch.object(baker, "stale_report", return_value=report), \
                mock.patch.object(baker, "bake_maps", return_value=rows), \
                mock.patch.object(self.slots, "_output_dir", return_value=None), \
                mock.patch.object(baker, "select", return_value=["A"]) as select:
            combo = self.ui.footer._lightmap_manage[0]
            combo.activated.emit(combo.findText("Changed"))
        self.assertEqual(select.call_args_list, [mock.call(["A"])], "the highlight selects nothing")
        self.assertEqual([r["map"] for r in self.slots._selected_maps()], ["Room_LM.exr"])
        self.assertEqual(self.ui.footer.text(), "Selected 1 object on 1 map.")
        self.assertEqual(combo.currentIndex(), 0, "the combo shows Select again")

    def test_a_refresh_keeps_the_highlighted_rows_and_selects_nothing(self):
        report = ptk.StaleReport()
        rows = report.map_rows([{"map": name, "path": f"C:/p/{name}", "folder": "lm",
                                 "objects": [name[0]], "writer": None, "size": (512, 512)}
                                for name in ("A_LM.exr", "B_LM.exr", "C_LM.exr")])
        self._manage(rows, report)
        table = self.ui.tbl_maps
        names = [table.item(r, 0).text() for r in range(table.rowCount())]
        flags = self.sb.QtCore.QItemSelectionModel

        def highlight(table):
            for name in ("A_LM.exr", "C_LM.exr"):
                table.selectionModel().select(
                    table.model().index(names.index(name), 0), flags.Select | flags.Rows
                )

        self._quietly(highlight)
        with mock.patch.object(self.btk.LightmapBaker, "select") as select:
            self._manage(rows, report)
        self.assertEqual(sorted(r["map"] for r in self.slots._selected_maps()),
                         ["A_LM.exr", "C_LM.exr"])
        select.assert_not_called()

    def _offered(self, name, rows, report, cases):
        item = self._menu_item(self.ui.tbl_maps.menu, name)
        self._manage(rows, report)
        table = self.ui.tbl_maps
        names = [table.item(r, 0).text() for r in range(table.rowCount())]
        for row_name, enabled in cases:
            self._quietly(lambda table, row=row_name: table.selectRow(names.index(row)))
            self.slots._fit_map_menu()
            self.assertEqual(item.isEnabled(), enabled, row_name)

    def test_start_tracking_is_offered_on_an_untracked_row(self):
        report = ptk.StaleReport(untracked=("U",))
        rows = report.map_rows([{"map": name, "path": f"C:/p/{name}", "folder": "lm",
                                 "objects": [obj], "writer": None, "size": (512, 512)}
                                for name, obj in (("T_LM.exr", "T"), ("U_LM.exr", "U"))])
        self._offered("track_selected", rows, report, (("T_LM.exr", False), ("U_LM.exr", True)))

    def test_combine_is_offered_on_a_split_row(self):
        report = ptk.StaleReport(split={"S_LM.exr": ("S_LM.exr", "S_LM_1.exr")},
                                 split_materials={"S_LM.exr": ("Crate",)})
        rows = report.map_rows([{"map": name, "path": f"C:/p/{name}", "folder": "lm",
                                 "objects": [name[0]], "writer": None, "size": (512, 512)}
                                for name in ("S_LM.exr", "T_LM.exr")])
        self._offered("combine_selected", rows, report, (("T_LM.exr", False), ("S_LM.exr", True)))

    def test_select_and_fix_all_are_the_manage_pages_footer(self):
        combo, fix = self.ui.footer._lightmap_manage
        self.assertEqual([combo.itemText(i) for i in range(combo.count())],
                         ["Select…", "Changed", "Split", "Untracked", "Missing", "All"])
        self.assertEqual(fix.text(), "Fix All")
        # A button with a background, and a list as wide as its items.
        self.assertFalse(fix.property("footerWidget"))
        self.assertGreaterEqual(combo.width(), combo.sizeHint().width())
        combo.showPopup()
        try:
            view = combo.view()
            self.assertGreaterEqual(view.viewport().width(), view.sizeHintForColumn(0))
        finally:
            combo.hidePopup()
            self.app.processEvents()
        self.slots._manage_footer()  # a reloaded panel re-wires its handler, once
        self.assertEqual(fix.receivers("2clicked(bool)"), 1)
        self._manage([], ptk.StaleReport())
        self.assertTrue(combo.isVisibleTo(self.ui) and fix.isVisibleTo(self.ui))
        self._show_page(0)
        self.assertFalse(combo.isVisibleTo(self.ui) or fix.isVisibleTo(self.ui))

    def test_a_footer_message_is_colored_by_its_level(self):
        moved = _moved("RoomA")
        rows = moved.map_rows([{"map": "Room_LM.exr", "path": "C:/p/Room_LM.exr",
                                "folder": "lm", "objects": ["RoomA"], "writer": None,
                                "size": (512, 512)}])
        missing = ptk.StaleReport().map_rows([{"map": "Gone_LM.exr", "path": None,
                                               "folder": "lm", "objects": ["RoomA"],
                                               "writer": None, "size": None}])
        footer = self.ui.footer
        self._manage(rows, moved)
        self.assertEqual(footer._status_level, "warning", "one to re-bake")
        self._manage(missing, ptk.StaleReport())
        self.assertEqual(footer._status_level, "error", "a map is missing")
        self._quietly(lambda table: table.clearSelection())
        self.slots.open_map_folder()
        self.assertEqual(footer._status_level, "warning", "nothing highlighted")
        self._manage([], ptk.StaleReport())
        self.assertIsNone(footer._status_level, "nothing baked is no fault")


# ---------------------------------------------------------------------------
# In Maya: the real mtk on a real scene (the widgets stay stubs)
# ---------------------------------------------------------------------------


@unittest.skipUnless(MAYA_AVAILABLE, "drives the real mtk; runs in a fresh Maya")
class TestLightmapBakerPanelInMaya(_PanelCase):
    def setUp(self):
        super().setUp()
        self.cmds = maya_module("maya.cmds")
        self.mtk = maya_module("mayatk")
        self.cmds.file(new=True, force=True)
        self.addCleanup(self.cmds.file, new=True, force=True)

    def _real(self, **values):
        slots, sb, ui, _tk = _panel(tk=self.mtk, **values)
        # The panel subscribes real scriptJobs only in _initialize_ui (not run).
        return slots, sb, ui

    def _long(self, node):
        return self.cmds.ls(node, long=True)[0]

    def test_the_dials_take_arnolds_units_from_the_default_tier(self):
        slots, sb, ui = self._real()
        self.assertEqual(ui.spn_samples.range, tuple(self.mtk.LightmapBaker.SAMPLES_RANGE))
        tier = self.mtk.LightmapBaker.preset_store().load("mobile")
        self.assertEqual(
            (ui.spn_samples.value(), ui.spn_gi_samples.value(), ui.spn_bounces.value()),
            (tier["samples"], tier["gi_samples"], tier["gi_depth"]),
        )
        self.assertEqual(set(slots._preset_fields()) - {"packing"},
                         set(self.mtk.LightmapBaker.PRESET_INT_KEYS)
                         | set(self.mtk.LightmapBaker.PRESET_BOOL_KEYS))

    def test_bake_hands_the_scopes_meshes_and_its_lights(self):
        """With Include Scene Lighting off, the selected group's light rides
        beside its mesh; a light outside it does not."""
        cmds = self.cmds
        group = cmds.group(empty=True, name="lmPanelModule")
        cube = self._long(cmds.parent(cmds.polyCube(name="lmPanelCube")[0], group)[0])
        inside = self._long(cmds.parent(cmds.shadingNode("areaLight", asLight=True), group)[0])
        outside = self._long(cmds.shadingNode("areaLight", asLight=True))
        cmds.select(group, replace=True)
        slots, sb, ui = self._real(include_scene_lights=False)
        slots._output_dir = lambda: os.path.join(cmds.internalVar(userTmpDir=True), "lm_panel")
        engine = maya_module("mayatk.light_utils.lightmap_baker.lightmap_baker")
        refused = engine.LightmapBakeResult(refused="not rendered under test")
        with mock.patch.object(self.mtk.LightmapBaker, "bake", autospec=True,
                               return_value=refused) as bake:
            slots.b000()
        handed = set(cmds.ls(bake.call_args.args[1], long=True))
        inside_shape = cmds.listRelatives(inside, shapes=True, fullPath=True)[0]
        outside_shape = cmds.listRelatives(outside, shapes=True, fullPath=True)[0]
        self.assertIn(cube, handed)
        self.assertTrue({inside, inside_shape} & handed, handed)
        self.assertFalse({outside, outside_shape} & handed, handed)
        self.assertEqual(ui.footer.text(), "not rendered under test")

    def test_the_exclude_row_drives_the_scene_set(self):
        cmds = self.cmds
        group = cmds.group(empty=True, name="lmExcludeGroup")
        for name in ("lmExA", "lmExB"):
            cmds.parent(cmds.polyCube(name=name)[0], group)
        slots, sb, ui = self._real()
        cmds.select(group, replace=True)
        slots.set_exclusions()
        self.assertEqual(ui.lbl_exclude.text(), "Exclude (2):")
        cmds.select(clear=True)
        slots.select_exclusions()
        self.assertEqual(cmds.ls(selection=True, long=True), [self._long(group)])
        slots.clear_exclusions()
        self.assertFalse(self.mtk.LightmapExcludeSet.exists())
        self.assertEqual(ui.lbl_exclude.text(), "Exclude:")

    def test_revert_reads_a_face_selection_as_its_mesh(self):
        cmds = self.cmds
        cube = self._long(cmds.polyCube(name="lmRevertCube")[0])
        self.mtk.LightmapBaker().commit_lightmap({cube: "C:/lm/lmRevertCube_Lightmap.exr"})
        cmds.select(f"{cube}.f[0]", replace=True)
        slots, sb, ui = self._real()
        sb.confirm.return_value = True
        slots.revert_selected()
        self.assertIn("Reverted 1 object", ui.footer.text())
        self.assertEqual(self.mtk.LightmapBaker().baked_objects(), [])

    def test_select_changed_on_an_unbaked_scene_finds_nothing(self):
        cmds = self.cmds
        cmds.select(cmds.polyCube(name="lmUnbaked")[0], replace=True)
        slots, sb, ui = self._real(page="Manage")
        slots.select_by_state("changed")
        self.assertEqual(ui.footer.text(), "No changed maps.")
        self.assertEqual(cmds.ls(selection=True), [], "the earlier pick is cleared")


if __name__ == "__main__":
    unittest.main()
