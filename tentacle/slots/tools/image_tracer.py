# !/usr/bin/python
# coding=utf-8
"""Image Tracer: trace a raster image's contours into curves, then fill them
into meshes.

One Slots class for both hosts over the host toolkit's ``ImageTracer``
(``self.tk``): Maya builds one NURBS curve per contour, Blender one curve
object with a spline per contour. Tracing Blue Pencil strokes is Maya's alone.
"""

from tentacle import Slots


class ImageTracerSlots(Slots):
    #: What a tracer raises for input the user can fix (no OpenCV, a missing or
    #: unreadable image, Blue Pencil on a host without it): said, not raised.
    INPUT_ERRORS = (ImportError, FileNotFoundError, ValueError, NotImplementedError)

    def __init__(self, switchboard):
        super().__init__(switchboard)
        self.ui = self.sb.loaded_ui.image_tracer
        # Blue Pencil is Maya's 2D annotation plugin. Blender has none, and
        # tracing Grease Pencil strokes instead would be new architecture, so
        # its ImageTracer has no open_blue_pencil and the header's two Blue
        # Pencil entries show disabled there.
        self._open_blue_pencil = getattr(self.tk.ImageTracer, "open_blue_pencil", None)

        # Re-apply chk000's restored state to the path field once the panel's
        # settings have loaded.
        from qtpy import QtCore

        QtCore.QTimer.singleShot(200, self._sync_ui)

    def _sync_ui(self):
        """Enable the path field per the (restored) Use Blue Pencil box."""
        chk000 = getattr(self.ui.header.menu, "chk000", None)
        if chk000 is not None:
            self.chk000(chk000.isChecked())

    def header_init(self, widget):
        """Initialize the header widget."""
        has_blue_pencil = self._open_blue_pencil is not None
        widget.menu.add(
            "QCheckBox",
            setText="Use Blue Pencil",
            setObjectName="chk000",
            setChecked=False,
            setEnabled=has_blue_pencil,
            setToolTip="Trace Blue Pencil strokes instead of an image (Maya only).",
        )
        widget.menu.add(
            "QPushButton",
            setText="Open Blue Pencil",
            setObjectName="blue_pencil_button",
            setEnabled=has_blue_pencil,
            setToolTip="Open Maya's Blue Pencil tool (Maya only).",
        )
        widget.set_help_text(
            self.sb.tooltip.fmt(
                title="Image Tracer",
                body="Trace the contours of a raster image into editable curves, "
                "then optionally fill them into a mesh.",
                steps=[
                    "Browse (▸) to an image file. In Maya you can instead check "
                    "<b>Use Blue Pencil</b> in the header menu to trace Blue Pencil "
                    "strokes (<b>Open Blue Pencil</b> opens the tool).",
                    "Set <b>Scale</b> (scene units per pixel) and <b>Simplify</b> "
                    "(contour tolerance in pixels; 0 turns it off).",
                    "Press <b>Trace Curves</b> for curves, <b>Create Mesh</b> to fill "
                    "the contours, <b>Create Negative Space</b> to fill around them, "
                    "or <b>Project on Plane</b> to drop them onto a backing plane.",
                ],
                notes=[
                    "Curves are laid flat on the ground plane from the world origin "
                    "and can be extruded, lofted or beveled like any other curve.",
                ],
            )
        )

    def txt000_init(self, widget):
        """Configure the path field's option box (▸) as an image file browser."""
        widget.option_box.browse(
            file_types="Images (*.png *.jpg *.jpeg *.bmp *.tif *.tiff);;All Files (*.*)",
            title="Select Image",
            mode="file",
        )

    def chk000(self, state):
        """Use Blue Pencil: no image path while it is on."""
        self.ui.txt000.setEnabled(not state)

    def blue_pencil_button(self):
        """Open Blue Pencil: the host's Blue Pencil tool (disabled where none)."""
        if self._open_blue_pencil is not None:
            self._open_blue_pencil()

    def _uses_blue_pencil(self) -> bool:
        """Use Blue Pencil is checked, on a host that has it."""
        return (
            self._open_blue_pencil is not None
            and self.ui.header.menu.chk000.isChecked()
        )

    def _tracer(self):
        """The host's tracer over the panel's values, or None (and why, said)."""
        use_blue_pencil = self._uses_blue_pencil()
        image_path = self.ui.txt000.text()
        if not use_blue_pencil and not image_path:
            self.sb.message_box(
                "Select an image first (browse via the ▸ on the path field)."
            )
            return None
        simplify = self.ui.s001.value()
        try:
            return self.tk.ImageTracer(
                image_path,
                scale=self.ui.s000.value(),
                simplify=simplify if simplify > 0 else None,
                use_blue_pencil=use_blue_pencil,
            )
        except self.INPUT_ERRORS as error:
            self.sb.message_box(str(error))
            return None

    def _build(self, build, done: str):
        """Run *build* on the panel's tracer; say what came of it."""
        tracer = self._tracer()
        if tracer is None:
            return
        try:
            result = build(tracer)
        except self.INPUT_ERRORS as error:
            self.sb.message_box(str(error))
            return
        self.sb.message_box(f"<hl>{done}</hl>" if result else "No contours found.")

    def b002(self):
        """Trace the source image into curves."""
        self._build(lambda t: t.trace_curves(), "Traced the image into curves.")

    def b003(self):
        """Build a mesh from the traced curves."""
        self._build(lambda t: t.create_mesh(), "Created a filled mesh.")

    def b004(self):
        """Build a mesh from the traced negative space."""
        self._build(
            lambda t: t.create_negative_space_mesh(), "Created a negative-space mesh."
        )

    def b005(self):
        """Project the traced result onto a plane."""
        self._build(
            lambda t: t.project_on_plane(), "Projected the curves onto a plane."
        )
