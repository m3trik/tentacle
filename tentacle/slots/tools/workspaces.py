# !/usr/bin/python
# coding=utf-8
"""Workspaces: a host's project workspaces in one panel -- the Workspace Map
(browse a folder tree of workspaces and switch the current one) and the
Workspace Editor (one project's root and file rules, written to
``workspace.mel``).

One Slots class for both hosts, a facade over the two parts
(``_workspaces/``), each a collaborator with its own state; this class only
routes the ``.ui``'s widgets to them, by the widget's name as uitk dispatches
every slot (so repeat-last, shortcuts and the slot history see them). A part
serves the hosts its group in the ``.ui`` names (``requires``, CODE_STANDARD
section 15): uitk hides the group elsewhere and this class never builds the part
there:

* the map (``grp_map``), over the host toolkit's ``WorkspaceMap``: every host;
* the editor (``grp_editor``, ``requires="blender"``): Maya's own Project Window
  is Maya's editor (the Workspace tab's Edit Workspace row opens each host's).

Saved under the panel's former names too: ``slots.tools.RENAMED_FROM`` carries
the Workspace Map's and the Workspace Editor's values into this one.
"""

from tentacle import Slots
from ._workspaces.editor import WorkspaceEditorPart
from ._workspaces.map import WorkspaceMapPart


class WorkspacesSlots(Slots):
    """Switchboard slots for the ``workspaces.ui`` panel."""

    def __init__(self, switchboard):
        super().__init__(switchboard)
        self.ui = self.sb.loaded_ui.workspaces
        #: The map part, or None where the host does not serve it.
        self.map = self._part(self.ui.grp_map, WorkspaceMapPart)
        #: The editor part, or None where the host does not serve it.
        self.editor = self._part(self.ui.grp_editor, WorkspaceEditorPart)

    def _part(self, group, part_class):
        """*part_class* over this panel, or None where the host does not serve
        *group*: its ``requires`` tag excludes the host (uitk hides it), or the
        host toolkit lacks what the part reads (``part_class.TOOLKIT_NEEDS``). The
        second covers a switchboard that names no host (a dev or test one), where
        uitk shows every group; an unbuilt part's group is hidden there too."""
        if self.sb.apply_visibility_policy(group) or not all(
            hasattr(self.tk, name) for name in part_class.TOOLKIT_NEEDS
        ):
            group.setVisible(False)
            return None
        return part_class(self)

    @property
    def parts(self) -> list:
        """The parts this host serves, in the panel's order."""
        return [part for part in (self.map, self.editor) if part is not None]

    # ------------------------------------------------------------------ header
    def header_init(self, widget):
        """Each served part's header rows and chrome, and one help card: a part's
        own where it serves alone, every part's as sections where several do."""
        for part in self.parts:
            part.header_init(widget)
        specs = [part.help_spec() for part in self.parts]
        if len(specs) > 1:
            specs = [
                {
                    "title": "Workspaces",
                    "body": " ".join(spec["body"] for spec in specs),
                    "sections": [(spec["title"], spec["steps"]) for spec in specs]
                    + [
                        section
                        for spec in specs
                        for section in spec.get("sections", [])
                    ],
                }
            ]
        if specs:
            widget.set_help_text(self.sb.tooltip.fmt(**specs[0]))

    # ------------------------------------------------------------------ the map
    def txt000_init(self, widget):
        """The map's Root Directory field."""
        if self.map is not None:
            self.map.txt000_init(widget)

    def txt001_init(self, widget):
        """The map's workspace-name filter."""
        if self.map is not None:
            self.map.txt001_init(widget)

    def tree000_init(self, widget):
        """The map's workspace tree."""
        if self.map is not None:
            self.map.tree000_init(widget)

    def b000(self):
        """The map's Browse."""
        if self.map is not None:
            self.map.b000()

    def b001(self):
        """The map's Set to Workspace."""
        if self.map is not None:
            self.map.b001()

    def b002(self):
        """The map's Refresh."""
        if self.map is not None:
            self.map.b002()

    def chk000(self, checked):
        """The map's Recursive Search (its root field's option box)."""
        if self.map is not None:
            self.map.chk000(checked)

    def set_to_workspace(self):
        """The map's Set To Workspace (its root field's option box)."""
        if self.map is not None:
            self.map.set_to_workspace()

    def btn_open_workspace(self):
        """The map's Open Workspace (its tree's menu)."""
        if self.map is not None:
            self.map.btn_open_workspace()

    def btn_explore_folder(self):
        """The map's Explore Folder (its tree's menu)."""
        if self.map is not None:
            self.map.btn_explore_folder()

    def new_project(self):
        """The map's New Project (the header menu)."""
        if self.map is not None:
            self.map.new_project()

    def mark_root(self):
        """The map's Mark Root As Shared Project (the header menu)."""
        if self.map is not None:
            self.map.mark_root()

    def save_template(self):
        """The map's Save Rules As Template (the header menu)."""
        if self.map is not None:
            self.map.save_template()

    # ------------------------------------------------------------------ the editor
    def btn_create(self):
        """The editor's Create Project (the header menu)."""
        if self.editor is not None:
            self.editor.create_project()

    def btn_add_rule(self):
        """The editor's Add New File Rule (the header menu)."""
        if self.editor is not None:
            self.editor.add_rule()

    def chk_raw_names(self, checked):
        """The editor's View File Rules (the header menu)."""
        if self.editor is not None:
            self.editor._on_view_toggled(checked)

    def btn_reset(self):
        """The editor's Reset Settings (the header menu)."""
        if self.editor is not None:
            self.editor.reset_rules()

    def btn_clear(self):
        """The editor's Clear Settings (the header menu)."""
        if self.editor is not None:
            self.editor.clear_rules()

    def txt002_init(self, widget):
        """The editor's Project Root field."""
        if self.editor is not None:
            self.editor.txt002_init(widget)

    def tbl000_init(self, widget):
        """The editor's file-rules table."""
        if self.editor is not None:
            self.editor.tbl000_init(widget)
