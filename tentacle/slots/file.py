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
        list000 = self.sb.file_submenu.list000
        list000.position = "top"
        list000.offset = 19
        list000.drag_interaction = True
        recentFiles = self.getRecentFiles(slice(0, 6))
        w1 = list000.add("QPushButton", setText="Recent Files")
        truncated = truncate(recentFiles, 65)
        w1.list.add(truncated, recentFiles)
        list000.setVisible(bool(recentFiles))

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
            self.getRecentFiles(slice(0, 20), format="timestamp|standard"),
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
            self.getRecentProjects(slice(0, 20), format="timestamp|standard"),
            "Recent Projects",
            clear=True,
        )

    def referenceSceneMenu(self, clear=False):
        """ """
        try:
            if clear:
                del self._referenceSceneMenu
            return self._referenceSceneMenu

        except AttributeError as error:
            menu = self.sb.Menu(self.sb.file.lbl005)
            for i in self.getWorkspaceScenes(
                fullPath=True
            ):  # zip(self.getWorkspaceScenes(fullPath=False), self.getWorkspaceScenes(fullPath=True)):
                chk = menu.add(self.sb.CheckBox, setText=i)
                chk.toggled.connect(
                    lambda state, scene=i: self.referenceScene(scene, not state)
                )

            self._referenceSceneMenu = menu
            return self._referenceSceneMenu

    def draggableHeader(self, state=None):
        """Context menu"""
        dh = self.sb.file.draggableHeader

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
