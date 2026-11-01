# !/usr/bin/python
# coding=utf-8
"""Cameras: one Slots class for both hosts.

Every operation is the host toolkit's ``CamUtils`` / ``CameraVisibility``
(``self.tk``), named as mayatk names them: the standard views
(``switch_viewport_camera``), Align View, the interactive Dolly / Roll / Truck /
Orbit tools (``navigate_view``: Maya's camera tool contexts, a modal drag in
Blender) and the Camera Options list. A host's refusal (no 3D viewport, no
camera, nothing selected) reaches the user as the host words it.

Double-click inside the marking menu (or the keyable ``toggle_camera_view``
command) toggles between the perspective and the last orthographic view: the
shared base's :meth:`Slots.toggle_camera_view`, wired in ``__init__``.
"""

from tentacle import Slots


class CamerasSlots(Slots):
    #: Create Camera leaves -> focal length (mm), in list order.
    CAMERA_TYPES = {"Standard Camera": 35, "Wide Angle Camera": 18, "Telephoto Camera": 85}

    #: Visibility Settings leaves -> (``CameraVisibility`` operation, the report
    #: label for the operations that grow a set, else None), in list order.
    VISIBILITY = {
        "Exclusive to Camera": ("set_exclusive", "Exclusive set"),
        "Hidden from Camera": ("set_hidden", "Hidden set"),
        "Remove from Exclusive": ("remove_from_exclusive", None),
        "Remove from Hidden": ("remove_from_hidden", None),
        "Remove All for Camera": ("remove_all", None),
        "Remove All": ("remove_all_for_all", None),
    }

    #: Camera Options leaves -> the ``adjust_camera_clipping`` directive, in list order.
    CLIPPING = {"Auto Adjust Clipping": "auto", "Reset Clipping": "reset"}

    #: list000 categories -> the handler each leaf of it runs.
    _LIST000_HANDLERS = {
        "Create Camera": "_create_camera",
        "Select Camera": "_select_camera",
        "Visibility Settings": "_camera_visibility",
        "Camera Options": "_camera_clipping",
    }

    def __init__(self, switchboard):
        super().__init__(switchboard)
        self.ui = self.sb.loaded_ui.cameras
        # Double-click gesture + keyable 'toggle_camera_view' command: the shared
        # wiring on the base slot class (tentacle.slots._slots.Slots).
        self.register_camera_view_toggle()

    # ------------------------------------------------------------------ list000  Camera options
    def list000_init(self, widget):
        """Initialize the Camera Options list (rebuilt on every show)."""
        widget.clear()
        if not widget.is_initialized:
            widget.refresh_on_show = True  # this method runs on each show
            widget.fixed_item_height = 18

        widget.add("Create Camera").sublist.add(dict(self.CAMERA_TYPES))
        cameras = self.tk.CamUtils.get_cameras()
        if cameras:
            widget.add("Select Camera").sublist.add(cameras)
        widget.add("Visibility Settings").sublist.add(list(self.VISIBILITY))
        widget.add("Camera Options").sublist.add(list(self.CLIPPING))

    @Slots.Signals("on_item_interacted")
    def list000(self, item):
        """Camera Options list: run the leaf's operation."""
        handler = self._LIST000_HANDLERS.get(item.parent_item_text())
        if handler is None:  # a category row: navigation only
            return
        try:
            getattr(self, handler)(item.item_text(), item)
        except (RuntimeError, ValueError) as error:
            self.sb.message_box(str(error))

    def _create_camera(self, text, item):
        """Create Camera: a new camera with the leaf's focal length."""
        self.tk.CamUtils.create_camera(focal_length=float(item.item_data()))

    def _select_camera(self, text, item):
        """Select Camera: select it and look through it."""
        self.tk.CamUtils.look_through(text, select=True)

    def _camera_visibility(self, text, item):
        """Visibility Settings: edit the camera's exclusive / hidden sets."""
        operation, label = self.VISIBILITY[text]
        names = getattr(self.tk.CameraVisibility, operation)()
        if label:
            self.sb.message_box(f"{label}: <hl>{len(names or ())}</hl> object(s).")

    def _camera_clipping(self, text, item):
        """Camera Options: fit or reset the camera's clip planes."""
        directive = self.CLIPPING[text]
        self.tk.CamUtils.adjust_camera_clipping(near_clip=directive, far_clip=directive)

    # ------------------------------------------------------------------ b000-b006  views
    def _switch_view(self, view):
        """Switch the viewport to a standard view by mayatk's name for it."""
        try:
            switched = self.tk.CamUtils.switch_viewport_camera(view)
        except (RuntimeError, ValueError) as error:
            self.sb.message_box(str(error))
            return
        if switched is None:
            self.sb.message_box(f"Could not switch to the <hl>{view}</hl> view.")

    def b000(self):
        """Cameras: Back View"""
        self._switch_view("back")

    def b001(self):
        """Cameras: Top View"""
        self._switch_view("top")

    def b002(self):
        """Cameras: Right View (Maya's 'side' camera)."""
        self._switch_view("side")

    def b003(self):
        """Cameras: Left View"""
        self._switch_view("left")

    def b004(self):
        """Cameras: Perspective View"""
        self._switch_view("persp")

    def b005(self):
        """Cameras: Front View"""
        self._switch_view("front")

    def b006(self):
        """Cameras: Bottom View"""
        self._switch_view("bottom")

    # ------------------------------------------------------------------ b007  Align View
    def b007(self):
        """Cameras: Align View. Look along the selected faces' normal and frame the
        selection (Maya: the alignToPoly camera; Blender: Align View to Active)."""
        try:
            aligned = self.tk.CamUtils.align_view_to_selection()
        except RuntimeError as error:
            self.sb.message_box(str(error))
            return
        if aligned == []:
            self.sb.message_box(self.NOTHING_SELECTED)

    # ------------------------------------------------------------------ b010-b013  nav tools
    def _navigate(self, mode):
        """Arm the interactive viewport-navigation tool for *mode*: drag in the
        view to navigate (Maya: its camera tool; Blender: RMB / Enter finishes,
        Esc cancels)."""
        try:
            self.tk.CamUtils.navigate_view(mode)
        except (RuntimeError, ValueError) as error:
            self.sb.message_box(str(error))

    def b010(self):
        """Camera: Dolly. Drag to move the eye in and out."""
        self._navigate("DOLLY")

    def b011(self):
        """Camera: Roll. Drag to roll the view about its axis."""
        self._navigate("ROLL")

    def b012(self):
        """Camera: Truck. Drag to pan the view (Maya's Track tool)."""
        self._navigate("TRACK")

    def b013(self):
        """Camera: Orbit. Drag to orbit the view (Maya's Tumble tool)."""
        self._navigate("ORBIT")
