# !/usr/bin/python
# coding=utf-8
import os

try:
    import pymel.core as pm
except ImportError as error:
    print(__file__, error)
import pythontk as ptk
import mayatk as mtk
from uitk import Signals
from tentacle.slots.maya import SlotsMaya


class FileSlots(SlotsMaya):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.ui = self.sb.loaded_ui.file
        self.submenu = self.sb.loaded_ui.file_submenu

    def header_init(self, widget):
        """ """
        if not widget.is_initialized:
            widget.menu.add(
                self.sb.registered_widgets.PushButton,
                setToolTip="Export scene assets with environment checks and presets.",
                setText="Scene Exporter",
                setObjectName="b002",
            )
            widget.menu.add(
                self.sb.registered_widgets.PushButton,
                setText="Quick Export Scene Geo",
                setObjectName="b003",
                setToolTip="Export the scene geometry as FBX to the current maya file's directory.\nThe file name will be the same as the current scene and overwrite the current file if it exists.",
            )
            widget.menu.add(
                "QPushButton",
                setText="Reference Manager",
                setObjectName="b001",
                setToolTip="Open the reference manager.",
            )

    @Signals("textChanged", "returnPressed")
    def txt000(self, widget):
        """Workspace Scenes: Filter"""
        self.ui.cmb000.init_slot()

    def cmb000_init(self, widget):
        """ """
        if not widget.is_initialized:
            widget.refresh_on_show = True  # Call this method on show
            pm.scriptJob(event=["workspaceChanged", self.ui.cmb000.init_slot])

        include = self.ui.txt000.text() or None

        scenes = {
            ptk.format_path(f, "file"): f
            for f in mtk.get_workspace_scenes(
                recursive=True, inc=include, basename_only=True
            )
        }
        widget.add(
            scenes,
            header="Scenes:",
            clear=True,
        )

    def cmb000(self, index, widget):
        """Workspace Scenes"""
        scene = widget.items[index]
        pm.openFile(scene, force=True)

    def cmb001_init(self, widget):
        """ """
        widget.refresh = True

        widget.add(
            mtk.get_recent_projects(slice(0, 20), format="timestamp|standard"),
            header="Recent Projects:",
            clear=True,
        )

    def cmb001(self, index, widget):
        """Recent Projects"""
        project = widget.items[index]
        pm.workspace.open(project)
        self.ui.cmb006.init_slot()

    def cmb002_init(self, widget):
        """ """
        # Fetch recent autosave files
        recent_autosaves = mtk.get_recent_autosave(
            filter_time=24, timestamp_format="%H:%M:%S"
        )

        # Prepare dictionary for ComboBox: key is 'path + timestamp', value is 'path'
        autosave_dict = {
            f"{i[1]}  {ptk.format_path(i[0], 'file')}": i[0] for i in recent_autosaves
        }

        # Add items to the ComboBox
        widget.add(
            autosave_dict,
            header="Recent Autosave",
            clear=True,
        )

    def cmb002(self, index, widget):
        """Recent Autosave"""
        file = widget.items[index]
        pm.openFile(file, open=1, force=True)

    def cmb003_init(self, widget):
        """ """
        widget.add(
            [
                "Import File",
                "Import Options",
                "FBX Import Presets",
                "OBJ Import Presets",
            ],
            header="Import",
        )

    def cmb003(self, index, widget):
        """Import"""
        text = widget.items[index]
        if text == "Import File":  # Import
            pm.mel.Import()
        elif text == "Import Options":  # Import options
            pm.mel.ImportOptions()
        elif text == "FBX Import Presets":  # FBX Import Presets
            pm.mel.FBXUICallBack(-1, "editImportPresetInNewWindow", "fbx")
        elif text == "OBJ Import Presets":  # Obj Import Presets
            pm.mel.FBXUICallBack(-1, "editImportPresetInNewWindow", "obj")

    def cmb004_init(self, widget):
        """ """
        items = [
            "Export Selection",
            "Send to Unreal",
            "Send to Unity",
            "GoZ",
            "Send to 3dsMax: As New Scene",
            "Send to 3dsMax: Update Current",
            "Send to 3dsMax: Add to Current",
            "Export to Offline File",
            "Export Options",
            "FBX Export Presets",
            "OBJ Export Presets",
        ]
        widget.add(items, header="Export")

    def cmb004(self, index, widget):
        """Export"""
        text = widget.items[index]
        if text == "Export Selection":
            pm.mel.ExportSelection()
        elif text == "Send to Unreal":
            pm.mel.SendToUnrealSelection()
        elif text == "Send to Unity":
            pm.mel.SendToUnitySelection()
        elif text == "GoZ":
            pm.mel.eval(
                'print("GoZ"); source"C:/Users/Public/Pixologic/GoZApps/Maya/GoZBrushFromMaya.mel"; source "C:/Users/Public/Pixologic/GoZApps/Maya/GoZScript.mel";'
            )
        elif text == "Send to 3dsMax: As New Scene":  # Send to 3dsMax: As New Scene
            pm.mel.SendAsNewScene3dsMax()  # OneClickMenuExecute ("3ds Max", "SendAsNewScene"); doMaxFlow { "sendNew","perspShape","1" };
        elif text == "Send to 3dsMax: Update Current":  # Send to 3dsMax: Update Current
            pm.mel.UpdateCurrentScene3dsMax()  # OneClickMenuExecute ("3ds Max", "UpdateCurrentScene"); doMaxFlow { "update","perspShape","1" };
        elif text == "Send to 3dsMax: Add to Current":  # Send to 3dsMax: Add to Current
            pm.mel.AddToCurrentScene3dsMax()  # OneClickMenuExecute ("3ds Max", "AddToScene"); doMaxFlow { "add","perspShape","1" };
        elif text == "Export to Offline File":  # Export to Offline File
            pm.mel.ExportOfflineFileOptions()  # ExportOfflineFile
        elif text == "Export Options":  # Export options
            pm.mel.ExportSelectionOptions()
        elif text == "FBX Export Presets":  # FBX Export Presets
            pm.mel.FBXUICallBack(-1, "editExportPresetInNewWindow", "fbx")
        elif text == "OBJ Export Presets":  # Obj Export Presets
            pm.mel.FBXUICallBack(-1, "editExportPresetInNewWindow", "obj")

    def cmb005_init(self, widget):
        """ """
        recent_files = mtk.get_recent_files(slice(0, 20))
        truncated = ptk.truncate(recent_files, 165)
        widget.add(zip(truncated, recent_files), header="Recent Files", clear=True)

    def cmb005(self, index: int, widget):
        """Recent Files"""
        force = not mtk.get_env_info("scene_modified")
        pm.openFile(widget.items[index], open=True, force=force, ignoreVersion=True)

    def cmb006_init(self, widget):
        """ """
        if not widget.is_initialized:
            widget.refresh_on_show = True  # Call this method on show
            widget.menu.add(
                self.sb.registered_widgets.Label,
                setObjectName="lbl000",
                setText="Set Project",
                setToolTip="Set the project directory.",
            )
            widget.menu.add(
                self.sb.registered_widgets.Label,
                setObjectName="lbl005",
                setText="Auto Set Project",
                setToolTip="Determine the workspace directory by moving up directory levels until a workspace is found.",
            )
            widget.menu.add(
                self.sb.registered_widgets.Label,
                setObjectName="lbl004",
                setText="Open Project Root",
                setToolTip="Open the project root directory.",
            )

        workspace = mtk.get_env_info("workspace")
        workspace_dir = mtk.get_env_info("workspace_dir")
        # Add each dir in the workspace as well as its full path as data
        items = {d: f"{workspace}/{d}" for d in os.listdir(workspace)}
        widget.add(items, header=workspace_dir, clear=True)

    def cmb006(self, index, widget):
        """Workspace"""
        try:
            item = widget.items[index]
            os.startfile(item)
        except Exception as e:
            print(e)

    def list000_init(self, widget):
        """ """
        widget.position = "top"
        widget.sublist_y_offset = 18
        widget.fixed_item_height = 18
        recent_files = mtk.get_recent_files(slice(0, 11))
        w1 = widget.add("Recent Files")
        truncated = ptk.truncate(recent_files, 65)
        w1.sublist.add(zip(truncated, recent_files))
        widget.setVisible(bool(recent_files))

    @Signals("on_item_interacted")
    def list000(self, item):
        """ """
        data = item.item_data()
        pm.openFile(data, open=True, force=True)

    def lbl000(self):
        """Set Workspace"""
        pm.mel.SetProject()
        # refresh project items to reflect new workspace.
        self.ui.cmb006.init_slot()

    def lbl004(self):
        """Open current project root"""
        dir_ = pm.workspace(q=True, rd=1)  # current project path.
        os.startfile(ptk.format_path(dir_))

    def lbl005(self):
        """Auto Set Workspace"""
        workspace = mtk.find_workspace_using_path()
        if workspace:
            pm.workspace(workspace, openWorkspace=True)
            workspace_name = os.path.basename(workspace)
            self.sb.message_box(f"Workspace set to {workspace_name}.")
            self.ui.cmb006.init_slot()
        else:
            self.sb.message_box("No workspace found.")

    def b000(self):
        """Autosave: Open Directory"""
        autosave_dir = os.environ.get("MAYA_AUTOSAVE_FOLDER", "")
        if not autosave_dir:
            return
        dirs = autosave_dir.split(";")[0]

        try:
            os.startfile(ptk.format_path(dirs))

        except FileNotFoundError:
            self.sb.message_box("The system cannot find the file specified.")

    def b001(self):
        """Open Reference Manager"""
        ui = mtk.UiManager.instance(self.sb).get("reference_manager")
        self.sb.parent().show(ui)

    def b002(self):
        """Scene Exporter"""
        ui = mtk.UiManager.instance(self.sb).get("scene_exporter")
        self.sb.parent().show(ui)

    def b003(self):
        """Quick Export Scene Geo"""
        mtk.export_scene_as_fbx()

    def b007(self):
        """Import file"""
        self.ui.cmb003.call_slot(0)

    def b008(self):
        """Export Selection"""
        self.ui.cmb004.call_slot(0)

    def b015(self):
        """Remove String From Object Names."""
        # asterisk denotes startswith*, *endswith, *contains*
        from_ = str(self.ui.t000.text())
        to = str(self.ui.t001.text())
        replace = self.ui.chk004.isChecked()
        selected = self.ui.chk005.isChecked()

        objects = pm.ls(from_)  # Stores a list of all objects starting with 'from_'
        if selected:  # get user selected objects instead
            objects = pm.ls(sl=True)
        from_ = from_.strip("*")  # strip modifier asterisk from user input

        for obj in objects:  # Get a list of it's direct parent
            relatives = pm.listRelatives(obj, parent=1)
            # If that parent starts with group, it came in root level and is pasted in a group, so ungroup it
            if "group*" in relatives:
                relatives[0].ungroup()

            newName = to
            if replace:
                newName = obj.replace(from_, to)
            pm.rename(obj, newName)  # Rename the object with the new name


# --------------------------------------------------------------------------------------------

# module name
# print(__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
