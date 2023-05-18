# !/usr/bin/python
# coding=utf-8
import functools
from tentacle.slots import Slots


class Cameras(Slots):
    """ """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        """
        """
        self.sb.parent().left_mouse_double_click.connect(self.toggle_camera_view)

        list000 = self.sb.cameras_lower_submenu.list000
        list000.position = "right"
        list000.offset = 19
        list000.drag_interaction = True
        recentFiles = [
            "uuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuu",
            "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
            "zzzzzzzzzzzzzzzzzzzz",
        ]
        w1 = list000.add(setText="Camera Settings")
        w1.list.add(recentFiles)

    def toggle_camera_view(self):
        """Toggle between the last two camera views in history."""
        # Get all slot methods from b000 to b007
        slots = self.sb.get_slots_from_string(self, "b000-7")

        # Get the last two methods from the slot history
        history = self.sb.slot_history(slice(-2, None), inc=slots)

        if not history:
            return

        # If the last method is b004, call the last non-perspective camera
        if history[-1].__name__ == self.b004.__name__:
            last_non_persp_cam = history[-2]
            last_non_persp_cam()
            self.sb._slot_history.append(last_non_persp_cam)
        else:  # Otherwise, call b004
            self.b004()
            self.sb._slot_history.append(self.b004)
