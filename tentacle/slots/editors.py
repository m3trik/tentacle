# !/usr/bin/python
# coding=utf-8
"""Editors: the editor buttons and the All Editors list, one Slots class for both hosts.

Each button names an editor and the host toolkit opens it (``self.tk.UiUtils``).
mayatk's editor names are the reference; blendertk opens its own counterpart
under the same name (the Attribute Editor is Blender's Properties editor, the
Node Editor its Shader Editor), in a new window. Time & Range and Cmd Line
toggle the host's docked strip: Maya's Time and Range Sliders and command line,
Blender's docked Timeline and Python Console. Maya's main-window chrome toggles
(Status Line, Shelf, Help Line, Tool Box) and the Dependency Graph have no
Blender counterpart, so the ``.ui`` tags them ``requires="maya"``; the row of
editors Blender shows in their place (``b014``-``b018``) is ``requires="blender"``.

The All Editors list is the host's own grouping
(``UiUtils.get_editor_categories``), so every row opens.
"""

from tentacle import Slots


class EditorsSlots(Slots):
    def __init__(self, switchboard):
        super().__init__(switchboard)
        self.ui = self.sb.loaded_ui.editors

    # ------------------------------------------------------------------ helpers
    def _open(self, editor):
        """Open *editor* (a mayatk editor name) in the host; say so when it could
        not open (an unloaded plug-in in Maya, no usable window in Blender)."""
        if self.tk.UiUtils.open_editor(editor) is None:
            self.sb.message_box(f"Could not open <strong>{editor}</strong>.")

    def _toggle(self, editor):
        """Show or hide the host's docked *editor*."""
        try:
            self.tk.UiUtils.toggle_editor(editor)
        except (RuntimeError, ValueError) as error:
            self.sb.message_box(str(error))

    # ------------------------------------------------------------------ All Editors list
    def list000_init(self, widget):
        """Fill the editors list: the host's categories, each a flyout of the
        editors it opens."""
        widget.fixed_item_height = 18
        for category, editors in self.tk.UiUtils.get_editor_categories().items():
            if editors:
                widget.add(category).sublist.add(sorted(editors))

    @Slots.Signals("on_item_interacted")
    def list000(self, item):
        """Open the picked editor; a category row only expands."""
        if getattr(item, "sublist", None) and item.sublist.get_items():
            return
        text = item.item_text()
        if text in self.tk.UiUtils.get_editor_types():
            self._open(text)

    # ------------------------------------------------------------------ editors
    def b000(self):
        """Attributes: the Attribute Editor (Blender: the Properties editor)."""
        self._open("Attribute Editor")

    def b001(self):
        """Outliner."""
        self._open("Outliner")

    def b002(self):
        """Tool: the tool settings (Blender: the Properties editor)."""
        self._open("Tool Settings")

    def b003(self):
        """Layers: the Layer Editor (Blender: the Outliner, where collections live)."""
        self._open("Layer Editor")

    def b004(self):
        """Channels: the Channel Box (Blender: the Properties editor)."""
        self._open("Channel Box")

    def b005(self):
        """Node Editor (Blender: the Shader Editor)."""
        self._open("Node Editor")

    def b006(self):
        """Dependency Graph: the Hypergraph hierarchy (Maya)."""
        self._open("Hypergraph: Hierarchy")

    def b014(self):
        """Geometry Nodes (Blender)."""
        self._open("Geometry Nodes")

    def b015(self):
        """UV Editor (Blender)."""
        self._open("UV Editor")

    def b016(self):
        """Image Editor (Blender)."""
        self._open("Image Editor")

    def b017(self):
        """Graph Editor (Blender)."""
        self._open("Graph Editor")

    def b018(self):
        """Text Editor (Blender)."""
        self._open("Text Editor")

    # ------------------------------------------------------------------ docked strips
    def b007(self):
        """Status Line (Maya)."""
        self._toggle("Status Line")

    def b008(self):
        """Shelf (Maya)."""
        self._toggle("Shelf")

    def b009(self):
        """Time & Range: the timeline (Maya: the Time and Range Sliders, hidden
        together when either shows; Blender: the docked Timeline)."""
        self._toggle("Timeline")

    def b010(self):
        """Script Output: the dockable console mirroring the session's output."""
        self.tk.ScriptConsole.toggle()

    def b011(self):
        """Cmd Line: the command line (Blender: a docked Python Console)."""
        self._toggle("Command Line")

    def b012(self):
        """Help Line (Maya)."""
        self._toggle("Help Line")

    def b013(self):
        """Tool Box (Maya)."""
        self._toggle("Tool Box")


# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
