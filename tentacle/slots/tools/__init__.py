# !/usr/bin/python
# coding=utf-8
"""Each shared tool's one Slots class, paired by name with its ``ui/tools/<tool>.ui``
(``Tcl.register_shared``). A package, so a class imports by its module path.

:data:`HOSTS` declares the tools one host serves; every other tool serves both.
:data:`RENAMED_FROM` declares the panel names a tool took over, and
:data:`RENAMED_HOSTS` the host each served. The host-free standalone apps
(Map Converter, the photogrammetry workflows, WebXR Preview, ...) are extapps':
a category's slots open one BY NAME through the host's external-app handler
(``self.sb.handlers.external_app.launch("converter")``), never from here.
"""

#: ``{tool: hosts it serves}`` (``Tcl.HOSTS`` keys) for the tools that serve one
#: host, each with the reason. A tool not named here serves every host. The
#: launcher registers a tool only in a host it serves (``Tcl.register_shared``),
#: so the other host never offers it: no menu row, no UI Browser entry, nothing
#: for ``marking_menu.show`` to open (CODE_STANDARD section 15: a tool with no
#: equivalent in a host is hidden there, never a stub). A host that gains the
#: tool's API adds itself here; the panel already calls only ``self.tk``.
HOSTS = {
    # Arnold renders inside Maya alone: Blender has no Arnold, and Cycles and
    # EEVEE read one material graph, so there is no preview network to add.
    "arnold_bridge": ("maya",),
    # blendertk has no LightRig yet (BACKLOG: "Light Rigs has no blendertk twin").
    "light_rig": ("maya",),
}

#: ``{tool: {former panel: {former widget name: its name now}}}`` for the tools
#: that took over other panels' names (a merge or a rename), each with the
#: reason. A user's saved values live under the panel's name (its settings
#: branch: widget states, settings keys, shortcut overrides), so
#: ``Tcl.register_shared`` has uitk's ``PanelRenames.carry`` copy each former
#: panel's into the tool's store, once per host, before any panel loads
#: (CODE_STANDARD section 5: saved names keep their spelling, so a merge carries
#: them); ``check_saved_names.py`` reads this table to judge a former panel's
#: names in its tool's ``.ui``. A widget whose name the merge gave to another
#: keeps its values under its new name.
RENAMED_FROM = {
    # The cross-DCC bridges, one panel over the host's bridge to the other DCC:
    # the Blender Bridge in Maya, the Maya Bridge in Blender.
    "dcc_bridge": {"blender_bridge": {}, "maya_bridge": {}},
    # The Workspace Map (Maya) and the Workspace Editor (Blender), one panel. The
    # map keeps its Root Directory field's name, so the editor's Project Root
    # field moved.
    "workspaces": {"workspace_map": {}, "workspace_editor": {"txt000": "txt002"}},
}

#: ``{former panel: hosts it served}`` (:data:`HOSTS`' shape) for the panels in
#: :data:`RENAMED_FROM`. Two former panels of one tool that served separate
#: hosts stored their values in separate hosts' stores, so a widget name both
#: keep never merges two users' values; ``check_saved_names.py`` requires it of
#: every name two formers keep (else the table renames one).
RENAMED_HOSTS = {
    "blender_bridge": ("maya",),
    "maya_bridge": ("blender",),
    "workspace_map": ("maya",),
    "workspace_editor": ("blender",),
}
