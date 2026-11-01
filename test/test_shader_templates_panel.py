#!/usr/bin/python
# coding=utf-8
"""The Shader Templates panel's one Slots class, shared by both hosts.

It reaches its host only through ``self.tk``: a fake toolkit's
``ShaderTemplates`` stands in for ``mtk`` / ``btk``'s and records what the panel
asks of it, over a real ``ptk.PresetStore`` in a temp folder -- plain pytest, no
DCC. In Maya, the same class drives the real ``mtk``. Saving, restoring, the
plug-ins a restore loads and the summaries it announces are the libraries':
mayatk's ``test_shader_templates.py``, blendertk's ``test_mat_anim_utils.py``.
"""

import logging
import os
import shutil
import tempfile
import unittest
from unittest import mock

import pythontk as ptk

from _host import MAYA_AVAILABLE, maya_module
from tentacle.slots._slots import Slots
from tentacle.slots.tools.shader_templates import ShaderTemplatesSlots


class _Capture(logging.Handler):
    def __init__(self):
        super().__init__(logging.DEBUG)
        self.records = []

    def emit(self, record):
        self.records.append((record.levelname, record.getMessage()))


class _Combo:
    """The template combo: a current row (name + file) and a re-init counter."""

    def __init__(self, name="", data=None):
        self.name, self.data = name, data
        self.items = []
        self.inits = 0

    def currentText(self):
        return self.name

    def currentData(self):
        return self.data

    def clear(self):
        self.items = []

    def addItem(self, name, data=None):
        self.items.append((name, data))

    def init_slot(self):
        self.inits += 1


def _store(tmp):
    """A store with a shipped (built-in) template and a user one."""
    builtin = os.path.join(tmp, "builtin")
    os.makedirs(builtin)
    with open(os.path.join(builtin, "glTF 2.0.json"), "w") as fh:
        fh.write("{}")
    store = ptk.PresetStore(
        "shader_templates", builtin_dir=builtin, user_dir=os.path.join(tmp, "user")
    )
    store.save("Mine", {"nodes": []})
    return store


def _panel(store=None, tk=None, selection=("lambert2",)):
    """A Slots instance over a mock ui and a fake toolkit (or *tk*, handed over
    before the panel is built, as ``Slots.tk`` is). Its log is captured."""
    sb = mock.MagicMock()
    if tk is not None:
        sb.tk = tk
    else:
        templates = sb.tk.ShaderTemplates
        templates.store.return_value = store or mock.MagicMock()
        templates.EXCLUDE_TYPES = ("shadingEngine", "transform")
        templates.suggested_name.return_value = "lambert2"
        templates.restore_template.return_value = {"<shader>": "lambert3", "<file>": "file1"}
        sb.tk.CoreUtils.selected_objects.return_value = list(selection)
        sb.tk.DataNodes.scene_source_images_dir.return_value = "C:/proj/sourceimages"
    slots = ShaderTemplatesSlots(sb)
    capture = _Capture()
    slots.logger.addHandler(capture)
    slots._capture = capture
    return slots, sb


class _PanelCase(unittest.TestCase):
    def setUp(self):
        migrated = Slots._legacy_repeat_last_migrated
        Slots._legacy_repeat_last_migrated = True  # no migration under test
        self.addCleanup(setattr, Slots, "_legacy_repeat_last_migrated", migrated)

    def tmpdir(self):
        path = tempfile.mkdtemp(prefix="tcl_shader_tpl_")
        self.addCleanup(shutil.rmtree, path, True)
        return path

    def panel(self, *args, **kwargs):
        slots, sb = _panel(*args, **kwargs)
        self.addCleanup(slots.logger.removeHandler, slots._capture)
        return slots, sb

    @staticmethod
    def logged(slots, level=None):
        return [m for lv, m in slots._capture.records if level is None or lv == level]


class TestShaderTemplatesPanelSetup(_PanelCase):
    def test_the_hosts_store_and_the_log_panel(self):
        slots, sb = self.panel()
        sb.tk.ShaderTemplates.store.assert_called_once_with()
        self.assertIs(slots._store, sb.tk.ShaderTemplates.store.return_value)
        ui = sb.loaded_ui.shader_templates
        ui.txt001.anchorClicked.connect.assert_called_once_with(slots._on_log_link_clicked)
        slots._on_log_link_clicked("action://select?node=lambert3")
        sb.tk.UiUtils.dispatch_log_link.assert_called_once_with(
            "action://select?node=lambert3", slots.logger
        )

    def test_the_header_menu_and_help(self):
        slots, sb = self.panel()
        header = mock.MagicMock()
        slots.header_init(header)
        names = [c.kwargs["setObjectName"] for c in header.menu.add.call_args_list]
        self.assertEqual(names, ["lbl_open_templates_dir", "lbl_graph_material"])
        header.set_help_text.assert_called_once()

    def test_the_combo_lists_each_template_with_its_file(self):
        tmp = self.tmpdir()
        store = _store(tmp)
        slots, sb = self.panel(store)
        combo = mock.MagicMock()
        combo.is_initialized = False
        added = []
        combo.addItem.side_effect = lambda name, data: added.append((name, data))
        slots.cmb002_init(combo)
        self.assertEqual(combo.restore_by, "text")  # rebuilt each show: never an index
        self.assertIs(combo.refresh_on_show, True)
        menu = [c.kwargs["setObjectName"] for c in combo.menu.add.call_args_list]
        self.assertEqual(menu, ["lbl000", "lbl001", "lbl002"])
        self.assertEqual(
            sorted(added),
            [
                ("Mine", str(store.path("Mine", "user"))),
                ("glTF 2.0", str(store.path("glTF 2.0", "builtin"))),
            ],
        )


class TestShaderTemplatesPanelManage(_PanelCase):
    def test_a_rename_takes_the_sidecar_and_the_active_pointer(self):
        """Through the store (``PresetStore.rename``): a raw ``os.rename`` moved
        the file alone, so its sidecar (the id a collection finds it by) and the
        active pointer kept the old name. Added: 2026-10-13 (moved from mayatk's
        test_shader_templates.py with the panel)."""
        store = _store(self.tmpdir())
        store.active = "Mine"
        identity = store.info("Mine").get("id")
        slots, sb = self.panel(store)
        combo = _Combo("Mine", str(store.path("Mine", "user")))
        slots.rename_template_safe(combo, "Ours")
        self.assertEqual(store.source("Ours"), "user")
        self.assertIsNone(store.source("Mine"))
        self.assertEqual(store.info("Ours").get("id"), identity)
        self.assertEqual(store.active, "Ours")
        self.assertEqual(combo.inits, 1)

    def test_a_rename_is_refused_where_it_would_lose_something(self):
        store = _store(self.tmpdir())
        slots, sb = self.panel(store)
        for current, new, said in (
            ("glTF 2.0", "Mine2", "read-only"),  # a shipped template
            ("Mine", "glTF 2.0", "already exists"),
            ("Mine", ' :*? ', "Invalid template name"),
        ):
            with self.subTest(current=current, new=new):
                combo = _Combo(current, "data")
                slots.rename_template_safe(combo, new)
                self.assertTrue(any(said in m for m in self.logged(slots, "ERROR")))
                self.assertEqual(combo.inits, 0)
        self.assertEqual(store.source("Mine"), "user")

    def test_names_are_made_file_safe(self):
        self.assertEqual(ShaderTemplatesSlots._sanitize_name('  a/b:c*  '), "abc")

    def test_delete_removes_a_user_template_only(self):
        store = _store(self.tmpdir())
        slots, sb = self.panel(store)
        sb.loaded_ui.shader_templates.cmb002 = combo = _Combo("glTF 2.0", "data")
        slots.lbl001()
        self.assertEqual(store.source("glTF 2.0"), "builtin")
        combo.name = "Mine"
        slots.lbl001()
        self.assertIsNone(store.source("Mine"))
        self.assertEqual(combo.inits, 1)

    def test_open_template_file_and_directory(self):
        store = _store(self.tmpdir())
        slots, sb = self.panel(store)
        sb.loaded_ui.shader_templates.cmb002 = _Combo("Mine", "C:/t/Mine.json")
        with mock.patch("pythontk.open_explorer") as open_explorer:
            slots.lbl002()
            slots.lbl_open_templates_dir()
        self.assertEqual(
            open_explorer.call_args_list,
            [
                mock.call("C:/t/Mine.json"),
                mock.call(str(store.user_dir), create_dir=True),
            ],
        )

    def test_graph_material_graphs_the_last_restore(self):
        slots, sb = self.panel()
        slots.lbl_graph_material()
        sb.tk.MatUtils.graph_materials.assert_not_called()
        self.assertTrue(any("No material" in m for m in self.logged(slots, "WARNING")))
        slots.last_restored_nodes = ["lambert3"]
        slots.lbl_graph_material()
        sb.tk.MatUtils.graph_materials.assert_called_once_with(["lambert3"])


class TestShaderTemplatesPanelRun(_PanelCase):
    def test_create_network_restores_through_the_host(self):
        slots, sb = self.panel()
        ui = sb.loaded_ui.shader_templates
        ui.cmb002.currentData.return_value = "C:/t/Mine.yaml"
        ui.cmb002.currentText.return_value = "Mine"
        slots.image_files = ["C:/tex/brick_BaseColor.png"]
        slots.b000()
        sb.tk.ShaderTemplates.restore_template.assert_called_once_with(
            "C:/t/Mine.yaml", ["C:/tex/brick_BaseColor.png"], logger=slots.logger
        )
        self.assertEqual(slots.last_restored_nodes, ["lambert3", "file1"])
        ui.txt001.clear.assert_called()

    def test_create_network_without_a_template_says_so(self):
        slots, sb = self.panel()
        sb.loaded_ui.shader_templates.cmb002.currentData.return_value = None
        slots.b000()
        sb.tk.ShaderTemplates.restore_template.assert_not_called()
        self.assertTrue(any("No template" in m for m in self.logged(slots, "ERROR")))

    def test_load_texture_maps_opens_in_the_projects_texture_folder(self):
        """Not a CWD-relative ``<project>/sourceimages``. Added: 2026-10-13
        (moved from mayatk's test_shader_templates.py with the panel)."""
        slots, sb = self.panel()
        sb.file_dialog.return_value = ["C:/tex/a.png", "C:/tex/b.png"]
        slots.b001()
        kwargs = sb.file_dialog.call_args.kwargs
        self.assertEqual(kwargs["start_dir"], "C:/proj/sourceimages")
        self.assertIn("*.png", kwargs["file_types"])
        self.assertEqual(slots.image_files, ["C:/tex/a.png", "C:/tex/b.png"])

    def test_save_template_names_and_saves_the_selection(self):
        store = _store(self.tmpdir())
        slots, sb = self.panel(store)
        sb.QtWidgets.QInputDialog.getText.return_value = ("Brick: v2", True)
        slots.b002()
        self.assertEqual(sb.QtWidgets.QInputDialog.getText.call_args.kwargs["text"], "lambert2")
        sb.tk.ShaderTemplates.suggested_name.assert_called_once_with(["lambert2"])
        sb.tk.ShaderTemplates.save_template.assert_called_once_with(
            ["lambert2"],
            str(store.path("Brick v2", "user")),
            exclude_types=["shadingEngine", "transform"],
            logger=slots.logger,
        )
        sb.loaded_ui.shader_templates.cmb002.init_slot.assert_called_once()

    def test_save_template_refusals(self):
        store = _store(self.tmpdir())
        slots, sb = self.panel(store, selection=())
        slots.b002()
        self.assertTrue(any("Select a material" in m for m in self.logged(slots, "ERROR")))

        slots, sb = self.panel(store)
        sb.QtWidgets.QInputDialog.getText.return_value = ("", False)
        slots.b002()
        self.assertTrue(any("cancelled" in m for m in self.logged(slots, "INFO")))

        slots, sb = self.panel(store)
        sb.QtWidgets.QInputDialog.getText.return_value = ("Mine", True)
        slots.b002()
        self.assertTrue(any("already exists" in m for m in self.logged(slots, "ERROR")))
        sb.tk.ShaderTemplates.save_template.assert_not_called()


@unittest.skipUnless(MAYA_AVAILABLE, "drives the real mtk; runs in a fresh Maya")
class TestShaderTemplatesPanelInMaya(_PanelCase):
    def setUp(self):
        super().setUp()
        sandbox = ptk.TestSandbox.user_config()  # keep the user's templates out
        sandbox.__enter__()
        self.addCleanup(sandbox.__exit__, None, None, None)
        self.cmds = maya_module("maya.cmds")
        self.cmds.file(new=True, force=True)
        self.mtk = maya_module("mayatk")

    def test_the_shipped_templates_are_listed_read_only(self):
        slots, sb = self.panel(tk=self.mtk)
        combo = _Combo()
        slots.refresh_templates(combo)
        names = [name for name, _ in combo.items]
        self.assertIn("glTF 2.0", names)
        combo.name, combo.data = "glTF 2.0", dict(combo.items)["glTF 2.0"]
        slots.rename_template_safe(combo, "Mine")
        self.assertTrue(any("read-only" in m for m in self.logged(slots, "ERROR")))

    def test_load_texture_maps_starts_in_an_absolute_folder(self):
        slots, sb = self.panel(tk=self.mtk)
        folder = slots.source_images_dir
        self.assertTrue(os.path.isabs(folder), folder)

    def test_a_saved_template_restores_into_a_network(self):
        cmds = self.cmds
        shader = cmds.shadingNode("lambert", asShader=True, name="tplPanelLambert")
        cmds.select(shader)
        slots, sb = self.panel(tk=self.mtk)
        sb.QtWidgets.QInputDialog.getText.return_value = ("Panel Lambert", True)
        slots.b002()
        path = str(slots._store.path("Panel Lambert", "user"))
        self.assertTrue(os.path.isfile(path))

        ui = sb.loaded_ui.shader_templates
        ui.cmb002.currentData.return_value = path
        ui.cmb002.currentText.return_value = "Panel Lambert"
        slots.b000()
        created = [n for n in slots.last_restored_nodes if cmds.objExists(n)]
        self.assertTrue(
            any(cmds.nodeType(n) == "lambert" for n in created), slots.last_restored_nodes
        )
        self.assertTrue(
            any(m.startswith("Network created") or "NETWORK CREATED" in m
                for m in self.logged(slots))
        )


if __name__ == "__main__":
    unittest.main()
