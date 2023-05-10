# !/usr/bin/python
# coding=utf-8
from tentacle.slots import Slots


class File(Slots):
    """ """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        """
        """
        # set the text for the open last file button to the last file's name.
        list000 = self.sb.file_submenu.list000
        list000.position = "top"
        list000.offset = 19
        list000.drag_interaction = True
        recentFiles = self.getRecentFiles()[:6]
        list000.setVisible(bool(recentFiles))
        w1 = list000.add("QPushButton", setText="Recent Files")
        from pythontk import truncate

        truncated = truncate(recentFiles, 65)
        w1.list.add(truncated, recentFiles)

        dh = self.sb.file.draggableHeader
        dh.ctxMenu.add(self.sb.ComboBox, setObjectName="cmb000", setToolTip="")
        dh.ctxMenu.add(
            self.sb.PushButton,
            setObjectName="tb000",
            setText="Save",
            setToolTip="Save the current file.",
        )
        dh.ctxMenu.add(
            self.sb.Label,
            setObjectName="lbl001",
            setText="Minimize App",
            setToolTip="Minimize the main application.",
        )
        dh.ctxMenu.add(
            self.sb.Label,
            setObjectName="lbl002",
            setText="Maximize App",
            setToolTip="Restore the main application.",
        )
        dh.ctxMenu.add(
            self.sb.Label,
            setObjectName="lbl003",
            setText="Close App",
            setToolTip="Close the main application.",
        )

        cmb005 = self.sb.file.cmb005
        cmb005.ctxMenu.add(
            "QPushButton",
            setObjectName="b001",
            setText="Last",
            setToolTip="Open the most recent file.",
        )
        cmb005.addItems_(
            dict(
                zip(
                    self.getRecentFiles(timestamp=True),
                    self.getRecentFiles(timestamp=False),
                )
            ),
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
            self.getRecentProjects(), "Recent Projects", clear=True
        )

        tb000 = self.sb.file.draggableHeader.ctxMenu.tb000
        tb000.ctxMenu.add(
            "QCheckBox",
            setText="Wireframe",
            setObjectName="chk000",
            setToolTip="Set view to wireframe before save.",
        )
        tb000.ctxMenu.add(
            "QCheckBox",
            setText="Increment",
            setObjectName="chk001",
            setChecked=True,
            setToolTip="Append and increment a unique integer value.",
        )
        tb000.ctxMenu.add(
            "QCheckBox",
            setText="Quit",
            setObjectName="chk002",
            setToolTip="Quit after save.",
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

                # if chk.sizeHint().width() > menu.sizeHint().width():
                #   chk.setMinimumSize(chk.sizeHint().width(), chk.sizeHint().height())

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
        # files = [file_ for file_ in (list(reversed(pm.optionVar(query='RecentFilesList')))) if "Autosave" not in file_]

        # force=True
        # if str(mel.eval("file -query -sceneName -shortName;")):
        #   force=False #if sceneName, prompt user to save; else force open
        # pm.openFile(files[0], open=1, force=force)

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
