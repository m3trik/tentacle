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


class File(SlotsMaya):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

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
        self.sb.file.cmb006.init_slot()

    def cmb002_init(self, widget):
        """ """
        widget.add(
            mtk.get_recent_autosave(format="timestamp|standard"),
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

    @SlotsMaya.hide_main
    def cmb003(self, index, widget):
        """Import"""
        self.sb.parent().hide(force=1)
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

    @SlotsMaya.hide_main
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
        widget.add(
            mtk.get_recent_files(slice(0, 20), format="timestamp|standard"),
            header="Recent Files",
            clear=True,
        )

    def cmb005(self, index, widget):
        """Recent Files"""
        # if sceneName prompt user to save; else force open
        force = True if str(pm.mel.file(q=True, sceneName=1, shortName=1)) else False
        pm.openFile(widget.items[index], open=1, force=force)

    def cmb006_init(self, widget):
        """ """
        widget.refresh = True
        if not widget.is_initialized:
            widget.menu.add(
                self.sb.Label,
                setObjectName="lbl000",
                setText="Set Project Directory",
                setToolTip="Set the project directory.",
            )
            widget.menu.add(
                self.sb.Label,
                setObjectName="lbl004",
                setText="Open Project Directory",
                setToolTip="Open the project root directory.",
            )

        workspace = mtk.get_maya_info("workspace_dir")
        project = ptk.format_path(workspace, "dir")
        # Add each dir in the workspace as well as its full path as data
        items = {d: f"{workspace}/{d}" for d in os.listdir(workspace)}
        widget.add(items, header=f"Project: {project}", clear=True)

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
        recentFiles = mtk.get_recent_files(slice(0, 11))
        w1 = widget.add("Recent Files")
        truncated = ptk.truncate(recentFiles, 65)
        w1.sublist.add(zip(truncated, recentFiles))
        widget.setVisible(bool(recentFiles))

    @Signals("on_item_interacted")
    def list000(self, item):
        """ """
        data = item.item_data()
        pm.openFile(data, open=True, force=True)

    def lbl000(self):
        """Set Workspace"""
        pm.mel.SetProject()
        # refresh project items to reflect new workspace.
        self.sb.file.cmb006.init_slot()

    def lbl004(self):
        """Open current project root"""
        dir_ = pm.workspace(q=True, rd=1)  # current project path.
        os.startfile(ptk.format_path(dir_))

    def b000(self):
        """Autosave: Open Directory"""
        # dir1 = str(pm.workspace(q=True, rd=1))+'autosave' #current project path.
        # get autosave dir path from env variable.
        dir2 = os.environ.get("MAYA_AUTOSAVE_FOLDER").split(";")[0]

        try:
            # os.startfile(self.format_path(dir1))
            os.startfile(ptk.format_path(dir2))

        except FileNotFoundError:
            self.sb.message_box("The system cannot find the file specified.")

    def b001(self):
        """Open Reference Manager"""
        module = mtk.core_utils.reference_manager
        slot_class = module.ReferenceManagerSlots

        self.sb.register("reference_manager.ui", slot_class, base_dir=module)
        self.sb.parent().set_ui("reference_manager")

    @SlotsMaya.hide_main
    def b007(self):
        """Import file"""
        self.sb.file.cmb003.call_slot(0)

    @SlotsMaya.hide_main
    def b008(self):
        """Export Selection"""
        self.sb.file.cmb004.call_slot(0)

    def b015(self):
        """Remove String From Object Names."""
        # asterisk denotes startswith*, *endswith, *contains*
        from_ = str(self.sb.file.t000.text())
        to = str(self.sb.file.t001.text())
        replace = self.sb.file.chk004.isChecked()
        selected = self.sb.file.chk005.isChecked()

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
