# !/usr/bin/python
# coding=utf-8
"""Each shared tool's one Slots class, paired by name with its ``ui/tools/<tool>.ui``
(``Tcl.register_shared``). A package, so a class imports by its module path.

:data:`HOSTS` declares the tools one host serves; every other tool serves both.
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
    # Sends to Blender (mayatk's BlenderBridge): a Blender session has no bridge
    # to itself; its counterpart is the Maya Bridge.
    "blender_bridge": ("maya",),
    # Sends to Maya (blendertk's MayaBridge); Maya's counterpart is the Blender Bridge.
    "maya_bridge": ("blender",),
    # blendertk has no LightRig yet (BACKLOG: "Light Rigs has no blendertk twin").
    "light_rig": ("maya",),
    # blendertk has no WorkspaceMap engine; Blender finds projects through the
    # Workspace tab and edits one in the Workspace Editor.
    "workspace_map": ("maya",),
    # Maya's own Project Window is Maya's editor (the Workspace tab's Edit
    # Workspace row opens it), so Maya users are never offered a second one.
    "workspace_editor": ("blender",),
}
