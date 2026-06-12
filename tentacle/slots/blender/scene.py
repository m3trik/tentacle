# !/usr/bin/python
# coding=utf-8
import bpy
import pythontk as ptk
import blendertk as btk
from uitk import Signals
from tentacle.slots.blender._slots_blender import SlotsBlender


class SceneSlots(SlotsBlender):
    """Blender port of the shared ``scene`` menu.

    Recent files / autosave recovery map onto Blender's own recent-files.txt and temp-dir
    autosaves (``btk.get_recent_files`` / ``btk.get_recent_autosave``); import/export route
    through Blender's native format operators (file dialogs via ``INVOKE_DEFAULT``). Maya's
    workspace model, the mayatk manager windows (reference/hierarchy/naming/exporter) and
    command ports have no Blender analogue and are deferred.
    """

    # (label -> bpy.ops path) for the import/export combos; resolved at call time so a
    # missing importer add-on degrades to a message instead of an AttributeError.
    _IMPORTERS = {
        "Import FBX": "import_scene.fbx",
        "Import OBJ": "wm.obj_import",
        "Import Collada": "wm.collada_import",
        "Append from .blend": "wm.append",
        "Link from .blend": "wm.link",
    }
    _EXPORTERS = {
        "Export FBX": "export_scene.fbx",
        "Export OBJ": "wm.obj_export",
        "Export glTF": "export_scene.gltf",
        "Export Collada": "wm.collada_export",
    }

    def __init__(self, switchboard):
        super().__init__(switchboard)
        self.ui = self.sb.loaded_ui.scene
        self.submenu = self.sb.loaded_ui.scene_submenu

    def _invoke_op(self, op_path):
        """Invoke a (possibly add-on-provided) operator's file dialog by dotted path."""
        group, _, name = op_path.partition(".")
        op = getattr(getattr(bpy.ops, group, None), name, None)
        if op is None:
            self.sb.message_box(f"Operator <hl>{op_path}</hl> is not available.")
            return
        try:
            op("INVOKE_DEFAULT")
        except RuntimeError as e:
            self.sb.message_box(str(e))

    def _open_file(self, filepath):
        try:
            bpy.ops.wm.open_mainfile(filepath=filepath)
        except RuntimeError as e:
            self.sb.message_box(
                f"Could not open:\n<hl>{ptk.format_path(filepath, 'file')}</hl>\n\n{e}"
            )

    # ------------------------------------------------------------------ list000  Recent Files
    def list000_init(self, widget):
        """Initialize Recent Files"""
        widget.fixed_item_height = 18
        widget.apply_preset("expand_up")
        recent_files = btk.get_recent_files(slice(0, 11))
        w1 = widget.add("Recent Files")
        truncated = ptk.truncate(recent_files, 65)
        w1.sublist.add(zip(truncated, recent_files))
        widget.setVisible(bool(recent_files))

    @Signals("on_item_interacted")
    def list000(self, item):
        """Recent Files"""
        data = item.item_data()
        if data:
            self._open_file(str(data))

    # ------------------------------------------------------------------ cmb002  Autosave
    def cmb002_init(self, widget):
        """Initialize Autosave (recent temp-dir .blend autosaves, newest first)."""
        recent_autosaves = btk.get_recent_autosave(filter_time=24)
        autosave_dict = {
            f"{stamp}  {ptk.format_path(path, 'file')}": path
            for path, stamp in recent_autosaves
        }
        widget.add(autosave_dict, header="Autosave:", clear=True)

    def cmb002(self, index, widget):
        """Autosave"""
        self._open_file(widget.items[index])

    # ------------------------------------------------------------------ cmb003/cmb004  Import/Export
    def cmb003_init(self, widget):
        widget.add(list(self._IMPORTERS), header="Import")

    def cmb003(self, index, widget):
        """Import"""
        op_path = self._IMPORTERS.get(widget.items[index])
        if op_path:
            self._invoke_op(op_path)

    def cmb004_init(self, widget):
        widget.add(list(self._EXPORTERS), header="Export")

    def cmb004(self, index, widget):
        """Export"""
        op_path = self._EXPORTERS.get(widget.items[index])
        if op_path:
            self._invoke_op(op_path)

    # ------------------------------------------------------------------ tb/b slots
    def tb003(self, widget):
        """Export Scene (FBX file dialog)"""
        self._invoke_op("export_scene.fbx")

    def b007(self):
        """Import file"""
        self.ui.cmb003.call_slot(0)

    # ------------------------------------------------------------------ deferred (Maya-specific)
    def tb000(self, widget):
        """Set Workspace — Blender derives the workspace from the saved .blend's directory."""
        self.sb.message_box(
            "Blender has no project workspace — the saved .blend's directory is used."
        )

    def b001(self):
        """Reference Manager — Blender uses library linking (File ▸ Link); manager not ported."""
        self.sb.message_box("Reference Manager is not yet implemented for Blender.")

    def b002(self):
        """Scene Exporter — mayatk window; not ported."""
        self.sb.message_box("Scene Exporter is not yet implemented for Blender.")

    def b004(self):
        """Hierarchy Manager — mayatk window; not ported."""
        self.sb.message_box("Hierarchy Manager is not yet implemented for Blender.")

    def b005(self):
        """Naming — mayatk window; not ported."""
        self.sb.message_box("Naming tool is not yet implemented for Blender.")


# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
