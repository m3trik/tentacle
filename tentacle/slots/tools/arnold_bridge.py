# !/usr/bin/python
# coding=utf-8
"""Arnold Preview Shader: add or remove the Arnold preview network beside each
game material, so the asset renders in Arnold inside Maya while the exported
Stingray / Standard Surface material stays the one thing FBX ships.

A thin driver over the host toolkit's ``ArnoldBridge`` (``self.tk``). A Maya
tool (``tentacle.slots.tools.HOSTS``): Blender has no Arnold, and Cycles and
EEVEE read one material graph, so Blender never offers it. Add and Remove act
on the Scope combo's pick; Force makes Add rebuild a network that exists. Each
is one undo step (the engine's).
"""

import pythontk as ptk

from tentacle import Slots


class ArnoldBridgeSlots(Slots, ptk.LoggingMixin):
    #: The Scope combo's items. The combo saves an index, so the order is the
    #: contract: 0 is the selected objects' materials, 1 every scene material.
    SCOPES = ("Selected Objects", "All Scene Materials")
    _VERB = {"add": "Added", "remove": "Removed"}

    def __init__(self, switchboard):
        super().__init__(switchboard)
        self.logger.setLevel("WARNING")
        self.ui = self.sb.loaded_ui.arnold_bridge
        self._bridge = self.tk.ArnoldBridge()

    # ------------------------------------------------------------------ header
    def header_init(self, widget) -> None:
        """The header menu's Select Bridged Materials, and the help text."""
        widget.config_buttons("menu", "collapse", "hide")
        widget.menu.add(
            "QPushButton",
            setText="Select Bridged Materials",
            setObjectName="select_bridged",
            setToolTip="Select every scene material that has an Arnold network.",
        )
        widget.set_help_text(
            self.sb.tooltip.fmt(
                title="Arnold Preview Shader",
                body="Attach (or remove) an Arnold <i>aiStandardSurface</i> "
                "shader beside a game material so the asset renders in Arnold, "
                "without touching the Stingray / Standard Surface material that "
                "exports to FBX.",
                steps=[
                    "Pick a <b>Scope</b>: the selected objects' materials, or "
                    "every scene material.",
                    "<b>Add Network</b> mirrors each material's textures onto a "
                    "new Arnold shader wired to the shading group's "
                    "<i>aiSurfaceShader</i> slot.",
                    "<b>Remove Network</b> deletes the Arnold network (the "
                    "exported material is untouched). Turn on <b>Force</b> to "
                    "rebuild a material that already has a network.",
                ],
                sections=[
                    (
                        "Scene-only by design",
                        [
                            "The network drives <i>aiSurfaceShader</i>, which FBX "
                            "does not represent: only the material on "
                            "<i>surfaceShader</i> exports, so the Arnold network "
                            "never leaves the scene.",
                            "It owns its own file nodes, so Remove deletes the whole "
                            "Arnold network and the material's textures stay put.",
                        ],
                    ),
                ],
            )
        )

    # -------------------------------------------------------------------- combo
    def cmb000_init(self, widget) -> None:
        """The Scope combo (Selected Objects by default)."""
        widget.clear()
        widget.addItems(self.SCOPES)
        widget.setCurrentIndex(0)

    # ------------------------------------------------------------------ actions
    def b000(self) -> None:
        """Add Network."""
        self._run("add", force=self.ui.chk000.isChecked())

    def b001(self) -> None:
        """Remove Network."""
        self._run("remove")

    def select_bridged(self) -> None:
        """Header menu: select every material that has a network (never the
        Arnold shaders themselves)."""
        bridged = self._bridge.select_bridged()
        if not bridged:
            self.ui.footer.setText("No materials have an Arnold network.")
            return
        self.ui.footer.setText(
            f"Selected {len(bridged)} material(s) with an Arnold network."
        )

    # ------------------------------------------------------------------ helpers
    def _scope(self):
        """``(kwargs, description)`` for the Scope combo's pick, or
        ``(None, message)`` when it holds nothing to act on."""
        if self.ui.cmb000.currentIndex() == 1:
            materials = self._bridge.base_materials()
            if not materials:
                return None, "No scene materials found."
            return {"materials": materials}, f"{len(materials)} scene material(s)"
        selection = self.tk.CoreUtils.selected_objects()
        if not selection:
            return None, "Select object(s), or switch Scope to All Scene Materials."
        return {"objects": selection}, "selection"

    def _run(self, op: str, force: bool = False) -> None:
        """Run *op* (``add`` / ``remove``) on the scope and report the count."""
        kwargs, desc = self._scope()
        if kwargs is None:
            self.ui.footer.setText(desc)
            return
        if op == "add":
            kwargs["force"] = force
        with self.ui.footer.progress(text=f"{op.capitalize()} Arnold network ({desc})…"):
            result = getattr(self._bridge, op)(**kwargs)
        n = len(result)
        self.ui.footer.setText(
            f"{self._VERB[op]} {n} Arnold network{'' if n == 1 else 's'} ({desc})."
        )
