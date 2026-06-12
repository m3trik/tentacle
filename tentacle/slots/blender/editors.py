# !/usr/bin/python
# coding=utf-8
import blendertk as btk
from uitk import Signals
from tentacle.slots.blender._slots_blender import SlotsBlender


class Editors(SlotsBlender):
    """Blender port of the shared ``editors`` menu.

    Maya's editor windows map onto Blender editor *areas* — ``btk.open_editor`` opens a new
    window switched to the requested ``ui_type`` (GUI-only; Blender has no headless windows).
    The list is curated to Blender's real editor set rather than mirroring Maya's (most Maya
    relationship/XGen/Trax-style editors have no analogue and are simply absent). UI-chrome
    toggles with no Blender equivalent (status line, shelf, help line) are deferred.
    """

    # (category -> [editor friendly-names]) — names resolve via btk.get_editor_types().
    _EDITORS = {
        "General Editors": [
            "Outliner",
            "Properties",
            "Preferences",
            "Spreadsheet",
            "Text Editor",
            "Python Console",
            "Info Log",
            "File Browser",
            "Asset Browser",
        ],
        "Modeling Editors": [
            "UV Editor",
            "Image Editor",
        ],
        "Animation Editors": [
            "Timeline",
            "Dope Sheet",
            "Graph Editor",
            "Drivers",
            "NLA Editor",
        ],
        "Rendering Editors": [
            "Shader Editor",
            "Compositor",
            "Geometry Nodes",
            "Video Sequencer",
            "Movie Clip Editor",
        ],
    }

    def __init__(self, switchboard):
        super().__init__(switchboard)
        self.ui = self.sb.loaded_ui.editors

    def list000_init(self, widget):
        """Initialize the editors list (categories → Blender editors)."""
        widget.fixed_item_height = 18
        for category, items in self._EDITORS.items():
            w = widget.add(category)
            w.sublist.add(sorted(items))

    @Signals("on_item_interacted")
    def list000(self, item):
        """Open the picked editor in a new window."""
        if getattr(item, "sublist", None) and item.sublist.get_items():
            return
        text = item.item_text()
        if text in btk.get_editor_types():
            btk.open_editor(text)

    # ------------------------------------------------------------------ b-slots (panel buttons)
    def b000(self):
        """Attributes (Properties editor)"""
        btk.open_editor("Properties")

    def b001(self):
        """Outliner"""
        btk.open_editor("Outliner")

    def b002(self):
        """Tool (active-tool settings live in the Properties editor's Tool tab)"""
        btk.open_editor("Properties")

    def b003(self):
        """Layers (Blender's collections live in the Outliner)"""
        btk.open_editor("Outliner")

    def b004(self):
        """Channels (object data lives in the Properties editor)"""
        btk.open_editor("Properties")

    def b005(self):
        """Node Editor (Shader Editor)"""
        btk.open_editor("Shader Editor")

    def b009(self):
        """Time & Range (Timeline editor)"""
        btk.open_editor("Timeline")

    def b010(self):
        """Script Output (Info log)"""
        btk.open_editor("Info Log")

    def b011(self):
        """Command Line (Python Console)"""
        btk.open_editor("Python Console")

    # ------------------------------------------------------------------ deferred (no analogue)
    def b006(self):
        """Dependency Graph — Blender has no user-facing dependency-graph editor."""
        self.sb.message_box("Dependency Graph editor is not applicable in Blender.")

    def b007(self):
        """Status Line — Maya UI chrome; no Blender analogue."""
        self.sb.message_box("Status Line toggle is not applicable in Blender.")

    def b008(self):
        """Shelf — Maya UI chrome; no Blender analogue."""
        self.sb.message_box("Shelf toggle is not applicable in Blender.")

    def b012(self):
        """Help Line — Maya UI chrome; Blender shows hints in the status bar."""
        self.sb.message_box("Help Line toggle is not applicable in Blender.")

    def b013(self):
        """Tool Box — Blender's toolbar is the T-panel inside each editor."""
        self.sb.message_box("Tool Box toggle is not applicable in Blender (use T in an editor).")


# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
