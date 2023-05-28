# !/usr/bin/python
# coding=utf-8
from tentacle.slots import Slots
from pythontk import truncate


class File(Slots):
    """ """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        """
        """

        dh = self.sb.file.draggableHeader
        dh.ctxMenu.add(self.sb.ComboBox, setObjectName="cmb000", setToolTip="")

        cmb005 = self.sb.file.cmb005
        cmb005.ctxMenu.add(
            "QPushButton",
            setObjectName="b001",
            setText="Last",
            setToolTip="Open the most recent file.",
        )
        cmb005.addItems_(
            self.get_recent_files(slice(0, 20), format="timestamp|standard"),
            "Recent Files",
            clear=True,
        )

        cmb006 = self.sb.file.cmb006
        cmb006.ctxMenu.add(
            self.sb.ComboBox,
            setObjectName="cmb001",
            setToolTip="Current project directory root.",
        )
        cmb006.ctxMenu.add(
            self.sb.Label,
            setObjectName="lbl000",
            setText="Set",
            setToolTip="Set the project directory.",
        )
        cmb006.ctxMenu.add(
            self.sb.Label,
            setObjectName="lbl004",
            setText="Root",
            setToolTip="Open the project directory.",
        )
        cmb006.ctxMenu.cmb001.addItems_(
            self.get_recent_projects(slice(0, 20), format="timestamp|standard"),
            "Recent Projects",
            clear=True,
        )

    def list000_init(self, root):
        """ """
        print("list000_init:", root)
        root.position = "top"
        root.sublist_y_offset = 18
        recentFiles = self.get_recent_files(slice(0, 6))
        w1 = root.add("Recent Files")
        truncated = truncate(recentFiles, 65)
        w1.sublist.add(truncated, recentFiles)
        root.setVisible(bool(recentFiles))

    def referenceSceneMenu(self, clear=False):
        """ """
        try:
            if clear:
                del self._referenceSceneMenu
            return self._referenceSceneMenu

        except AttributeError:
            menu = self.sb.Menu(self.sb.file.lbl005)
            for i in self.get_workspace_scenes(
                fullPath=True
            ):  # zip(self.get_workspace_scenes(fullPath=False), self.get_workspace_scenes(fullPath=True)):
                chk = menu.add(self.sb.CheckBox, setText=i)
                chk.toggled.connect(
                    lambda state, scene=i: self.reference_scene(scene, not state)
                )

            self._referenceSceneMenu = menu
            return self._referenceSceneMenu

    def lbl005(self):
        """Reference"""
        self.referenceSceneMenu().show()

    @Slots.hideMain
    def b001(self):
        """Recent Files: Open Last"""
        self.cmb005(index=1)

    @Slots.hideMain
    def b007(self):
        """Import file"""
        self.cmb003(index=1)

    @Slots.hideMain
    def b008(self):
        """Export Selection"""
        self.cmb004(index=1)


# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------


# deprecated:
