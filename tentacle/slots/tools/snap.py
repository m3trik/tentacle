# !/usr/bin/python
# coding=utf-8
"""Snap: vertices to a target surface, to the closest target vertex, or to the grid.

One Slots class for both hosts over the host toolkit's ``Snap`` (``self.tk``),
which also splits the selection into sources and the target the way the host
orders it (Maya: the last selected; Blender: the active object).
"""

from tentacle import Slots


class SnapSlots(Slots):
    def __init__(self, switchboard):
        super().__init__(switchboard)
        self.ui = self.sb.loaded_ui.snap

    def header_init(self, widget):
        """Configure header help text."""
        widget.set_help_text(
            self.sb.tooltip.fmt(
                title="Snap",
                body="Snap vertices to other vertices, surfaces, or the world grid. "
                "Each button has an option box (▸) for its per-tool parameters.",
                sections=[
                    (
                        "Snap to Surface",
                        [
                            "Select the source mesh(es), then the target mesh last "
                            "(in Blender: the active object).",
                            "Source verts are projected onto the target surface.",
                            "Option box: <b>Offset</b>, <b>Threshold</b>, <b>Invert</b>.",
                        ],
                    ),
                    (
                        "Snap to Closest Vertex",
                        [
                            "Select exactly two meshes: source first, target last.",
                            "Source verts within <b>Tolerance</b> snap to the "
                            "closest target vert.",
                        ],
                    ),
                    (
                        "Snap to Grid",
                        [
                            "Select objects or vertices.",
                            "Option box: <b>Grid Size</b> + per-axis filter (X/Y/Z).",
                            "Vertices snap their positions; objects snap their pivots.",
                        ],
                    ),
                ],
            )
        )

    def b000_init(self, widget):
        """Initialize Snap to Surface button option box."""
        widget.option_box.menu.setTitle("Snap to Surface")
        widget.option_box.menu.add(
            "QDoubleSpinBox",
            setPrefix="Offset: ",
            setObjectName="s000",
            set_limits=[0, 100, 0.01, 1],
            setValue=0.0,
            setToolTip="Distance from surface to place affected vertices.",
        )
        widget.option_box.menu.add(
            "QDoubleSpinBox",
            setPrefix="Threshold: ",
            setObjectName="s001",
            set_limits=[0, 1000, 0.1, 1],
            setValue=0.0,
            setToolTip="Only process vertices within this distance. 0 = no limit.",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Invert",
            setObjectName="chk000",
            setChecked=False,
            setToolTip="Invert direction (use if target normals point inward).",
        )

    def b000(self):
        """Snap to Surface button."""
        sources, target = self.tk.Snap.source_and_target()
        if target is None:
            self.sb.message_box(
                "Select source mesh(es) first, then the target mesh last."
            )
            return
        count = self.tk.Snap.snap_to_surface(
            sources,
            target,
            offset=self.ui.b000.menu.s000.value(),
            threshold=self.ui.b000.menu.s001.value() or None,  # 0 means no limit
            invert=self.ui.b000.menu.chk000.isChecked(),
        )
        self.sb.message_box(f"<hl>Snapped {count} vertices to surface.</hl>")

    def b001_init(self, widget):
        """Initialize Snap to Closest Vertex button option box."""
        widget.option_box.menu.setTitle("Snap to Closest Vertex")
        widget.option_box.menu.add(
            "QDoubleSpinBox",
            setPrefix="Tolerance: ",
            setObjectName="s002",
            set_limits=[0, 1000, 0.1, 1],
            setValue=10.0,
            setToolTip="Maximum search distance for matching vertices.",
        )

    def b001(self):
        """Snap to Closest Vertex button."""
        sources, target = self.tk.Snap.source_and_target()
        if target is None or len(sources) != 1:
            self.sb.message_box("Select exactly two meshes: source first, then target.")
            return
        count = self.tk.Snap.snap_to_closest_vertex(
            sources[0], target, tolerance=self.ui.b001.menu.s002.value()
        )
        self.sb.message_box(f"<hl>Snapped {count} vertices.</hl>")

    def b002_init(self, widget):
        """Initialize Snap to Grid button option box."""
        widget.option_box.menu.setTitle("Snap to Grid")
        widget.option_box.menu.add(
            "QDoubleSpinBox",
            setPrefix="Grid Size: ",
            setObjectName="s003",
            set_limits=[0.001, 1000, 0.1, 3],
            setValue=1.0,
            setToolTip="Grid spacing to snap to.",
        )
        widget.option_box.menu.add(
            "QLineEdit",
            setPlaceholderText="Axes (xyz)...",
            setObjectName="txt000",
            setText="xyz",
            setToolTip="Which axes to snap: x, y, z, or combinations like xy.",
        )

    def b002(self):
        """Snap to Grid button."""
        count = self.tk.Snap.snap_to_grid(
            grid_size=self.ui.b002.menu.s003.value(),
            axes=self.ui.b002.menu.txt000.text() or "xyz",
        )
        self.sb.message_box(f"<hl>Snapped {count} items to grid.</hl>")
