# !/usr/bin/python
# coding=utf-8
import blendertk as btk
from uitk import Signals
from tentacle.slots.blender._slots_blender import SlotsBlender


class Editors(SlotsBlender):
    """Blender port of the shared ``editors`` menu.

    Maya's editor windows map onto Blender editor *areas* — ``btk.open_editor`` opens a new
    window switched to the requested ``ui_type`` (GUI-only; Blender has no headless windows).
    Every button opens a **real** Blender editor: the five Maya buttons with no Blender
    analogue (Dependency Graph / Status Line / Shelf / Help Line / Tool Box) are relabeled
    in ``_init`` to a substitute editor instead of dead-ending in a message. Because the
    ``editors#startmenu.ui`` is shared with Maya, the relabel happens per-DCC in the slot
    (the ``.ui`` keeps the Maya text for the Maya slot). The lower-submenu list is filtered
    against the canonical editor map so it can never show a dead link.
    """

    # Button objectName -> the Blender editor it opens. Single source of truth: every value
    # is a key of ``btk.get_editor_types()`` (enforced by the headless no-dead-links check),
    # so no button can dead-end. The five buttons whose Maya editor has no Blender analogue
    # carry a substitute editor and are relabeled to it (see ``_RELABELED``).
    _BUTTON_EDITORS = {
        "b000": "Properties",       # Maya "Attributes" -> Properties editor
        "b001": "Outliner",
        "b002": "Properties",       # Maya "Tool" -> tool settings live in Properties
        "b003": "Outliner",         # Maya "Layers" -> collections live in the Outliner
        "b004": "Properties",       # Maya "Channels" -> object data lives in Properties
        "b005": "Shader Editor",    # Maya "Node Editor"
        "b006": "Geometry Nodes",   # was "Dependency Graph" (no Blender analogue)
        "b007": "UV Editor",        # was "Status Line" (no Blender analogue)
        "b008": "Image Editor",     # was "Shelf" (no Blender analogue)
        "b009": "Timeline",         # Maya "Time & Range"
        "b010": "Info Log",         # Maya "Script Output"
        "b011": "Python Console",   # Maya "Command Line"
        "b012": "Graph Editor",     # was "Help Line" (no Blender analogue)
        "b013": "Text Editor",      # was "Tool Box" (no Blender analogue)
    }
    # Buttons relabeled per-DCC (their Maya editor has no Blender analogue): show + open the
    # substitute editor instead of the Maya name. The shared .ui keeps the Maya text for Maya.
    _RELABELED = ("b006", "b007", "b008", "b012", "b013")

    # (category -> [editor friendly-names]) for the lower-submenu list — curated to Blender's
    # real editor set; filtered against btk.get_editor_types() at init so none can dead-end.
    _EDITORS = {
        "General Editors": [
            "Outliner", "Properties", "Preferences", "Spreadsheet", "Text Editor",
            "Python Console", "Info Log", "File Browser", "Asset Browser",
        ],
        "Modeling Editors": [
            "UV Editor", "Image Editor",
        ],
        "Animation Editors": [
            "Timeline", "Dope Sheet", "Graph Editor", "Drivers", "NLA Editor",
        ],
        "Rendering Editors": [
            "Shader Editor", "Compositor", "Geometry Nodes", "Video Sequencer",
            "Movie Clip Editor",
        ],
    }

    def __init__(self, switchboard):
        super().__init__(switchboard)
        self.ui = self.sb.loaded_ui.editors

    # ------------------------------------------------------------------ lower-submenu list
    def list000_init(self, widget):
        """Initialize the editors list (categories → Blender editors).

        Each item is filtered against ``btk.get_editor_types()`` so only editors that
        actually open are shown — an empty category is dropped (no dead links)."""
        widget.fixed_item_height = 18
        valid = btk.get_editor_types()
        for category, items in self._EDITORS.items():
            items = [e for e in items if e in valid]
            if not items:
                continue
            w = widget.add(category)
            w.sublist.add(sorted(items))

    @Signals("on_item_interacted")
    def list000(self, item):
        """Open the picked editor in a new window (category headers are nav-only)."""
        if getattr(item, "sublist", None) and item.sublist.get_items():
            return
        text = item.item_text()
        if text in btk.get_editor_types():
            btk.open_editor(text)

    # ------------------------------------------------------------------ buttons
    def _open_button(self, name):
        """Open the editor mapped to a button objectName."""
        btk.open_editor(self._BUTTON_EDITORS[name])

    def _relabel(self, widget):
        """Per-DCC label override for a substituted button (the shared .ui keeps the Maya
        text for the Maya slot). Shows + tooltips the substitute editor."""
        editor = self._BUTTON_EDITORS.get(widget.objectName())
        if editor:
            widget.setText(editor)
            widget.setToolTip(f"Open the {editor} in a new window.")

    def b000(self):
        """Attributes (Properties editor)"""
        self._open_button("b000")

    def b001(self):
        """Outliner"""
        self._open_button("b001")

    def b002(self):
        """Tool (active-tool settings live in the Properties editor's Tool tab)"""
        self._open_button("b002")

    def b003(self):
        """Layers (Blender's collections live in the Outliner)"""
        self._open_button("b003")

    def b004(self):
        """Channels (object data lives in the Properties editor)"""
        self._open_button("b004")

    def b005(self):
        """Node Editor (Shader Editor)"""
        self._open_button("b005")

    def b006_init(self, widget):
        """Relabel: Dependency Graph → Geometry Nodes."""
        self._relabel(widget)

    def b006(self):
        """Geometry Nodes (substitute for Maya's Dependency Graph)"""
        self._open_button("b006")

    def b007_init(self, widget):
        """Relabel: Status Line → UV Editor."""
        self._relabel(widget)

    def b007(self):
        """UV Editor (substitute for Maya's Status Line toggle)"""
        self._open_button("b007")

    def b008_init(self, widget):
        """Relabel: Shelf → Image Editor."""
        self._relabel(widget)

    def b008(self):
        """Image Editor (substitute for Maya's Shelf toggle)"""
        self._open_button("b008")

    def b009(self):
        """Time & Range (Timeline editor)"""
        self._open_button("b009")

    def b010(self):
        """Script Output (Info log)"""
        self._open_button("b010")

    def b011(self):
        """Command Line (Python Console)"""
        self._open_button("b011")

    def b012_init(self, widget):
        """Relabel: Help Line → Graph Editor."""
        self._relabel(widget)

    def b012(self):
        """Graph Editor (substitute for Maya's Help Line toggle)"""
        self._open_button("b012")

    def b013_init(self, widget):
        """Relabel: Tool Box → Text Editor."""
        self._relabel(widget)

    def b013(self):
        """Text Editor (substitute for Maya's Tool Box toggle)"""
        self._open_button("b013")


# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
