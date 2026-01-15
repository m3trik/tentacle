# !/usr/bin/python
# coding=utf-8
import sys
from typing import Callable, Any
from qtpy import QtWidgets, QtGui, QtCore


class OverlayFactoryFilter(QtCore.QObject):
    def __init__(self, overlay: QtWidgets.QWidget):
        super().__init__(overlay)
        self.overlay = overlay

    def eventFilter(self, widget, event):
        if not widget.isWidgetType():
            return False

        etype = event.type()

        if etype == QtCore.QEvent.MouseButtonPress:
            self.overlay.mousePressEvent(event)

        elif etype == QtCore.QEvent.MouseButtonRelease:
            self.overlay.mouseReleaseEvent(event)

        elif etype == QtCore.QEvent.MouseMove:
            self.overlay.mouseMoveEvent(event)

        elif etype == QtCore.QEvent.Resize:
            if widget == self.overlay.parentWidget():
                self.overlay.resize(widget.size())

        elif etype == QtCore.QEvent.Show:
            self.overlay.raise_()

        return False


class Path:
    """The Path class represents a sequence of widget positions and cursor positions
    that can be navigated. It is used in conjunction with the Overlay class to
    visually represent a path on a GUI.

    Attributes:
        _path: A list of tuples, where each tuple contains a widget reference,
               the global position of the widget's center, and the global cursor
               position at the time of adding.
    """

    def __init__(self):
        """Initializes a new instance of the Path class."""
        self._path = []

    def __iter__(self):
        """Special method to allow iteration."""
        return iter(self._path)

    def __getitem__(self, index):
        """Special method to allow indexed access."""
        return self._path[index]

    def __setitem__(self, index, value):
        """Special method to allow indexed assignment."""
        self._path[index] = value

    def __repr__(self):
        """Provides a string representation of the current path."""
        return f"Path({self._path})"

    def __len__(self):
        """Return number of entries in path."""
        return len(self._path)

    @property
    def is_empty(self) -> bool:
        """Check if path has no entries."""
        return len(self._path) == 0

    @property
    def intermediate_entries(self):
        """Entries between start and end (for cloning)."""
        return self._path[1:-1]

    @property
    def start_pos(self) -> QtCore.QPoint:
        """Gets the starting position of the path.

        Returns:
            The cursor position when the path was first created, or None if the
            path is empty.
        """
        try:
            return self._path[0][2]
        except IndexError:
            return None

    @property
    def widget_positions(self) -> dict:
        """Gets the global position of the center of a specific widget in the path.

        Parameters:
            target_widget: The widget to find the position of.

        Returns:
            The global position of the center of the target_widget,
            or None if the widget is not found in the path.
        """
        return {widget: widget_pos for widget, widget_pos, _ in self._path[1:]}

    def widget_position(self, target_widget):
        """Gets the global position of the center of a specific widget in the path.

        Parameters:
            target_widget: The widget to find the position of.

        Returns:
            The global position of the center of the target_widget,
            or None if the widget is not found in the path.
        """
        return next(
            (
                widget_pos
                for widget, widget_pos, _ in self._path
                if widget == target_widget
            ),
            None,
        )

    def reset(self):
        """Clears the path and appends the current cursor position as the new starting position."""
        self.clear()
        curPos = QtGui.QCursor.pos()
        self._path.append((None, None, curPos))

    def clear(self):
        """Clears the entire path."""
        self._path.clear()

    def clear_to_origin(self):
        """Clears the path but retains the original starting position."""
        self._path = self._path[:1]

    def add(self, ui, widget):
        """Adds a widget and its global position to the path."""
        if widget is None or not widget.isVisible():
            return
        w_pos = widget.mapToGlobal(widget.rect().center())

        self._path.append((widget, w_pos, QtGui.QCursor.pos()))
        self.remove(ui)

    def remove(self, target_ui):
        """Removes all references to the provided ui object from the path.
        Preserves the portion of the path up to and including the last occurrence
        of the target_ui.

        Parameters:
            target_ui: The ui object to remove from the path.
        """
        last_occurrence_index = next(
            (
                index + 1
                for index, (widget, _, _) in reversed(list(enumerate(self._path[1:])))
                if widget.ui == target_ui
            ),
            None,
        )
        if last_occurrence_index is not None:
            self._path = self._path[:last_occurrence_index]
        else:
            self._path = self._path[:]


class Overlay(QtWidgets.QWidget):
    """Handles paint events as an overlay on top of an existing widget.
    Inherits from OverlayFactoryFilter to relay events from the parent widget to the overlay.
    Maintains a list of draw paths to track the user's interactions.

    Parameters:
        parent (QWidget, optional): The parent widget for the overlay. Defaults to None.
        antialiasing (bool, optional): Set antialiasing for the tangent paint events. Defaults to False.
    """

    # Attributes to copy when cloning widgets
    CLONE_ATTRS = (
        "objectName",
        "accessibleName",
        "toolTip",
        "statusTip",
        "whatsThis",
        "font",
        "styleSheet",
        "enabled",
        "visible",
        "size",
        "minimumSize",
        "maximumSize",
        "layoutDirection",
        "contextMenuPolicy",
        "cursor",
        "windowTitle",
        "windowIcon",
    )

    # return the existing QApplication object, or create a new one if none exist.
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)

    def __init__(self, parent=None, antialiasing=False):
        super().__init__(parent)

        self.antialiasing = antialiasing
        self.draw_enabled = False
        self.clear_painting = False

        self.setAttribute(QtCore.Qt.WA_NoSystemBackground)
        self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)
        self.setFocusPolicy(QtCore.Qt.NoFocus)

        self.fg_color = QtGui.QColor(115, 115, 115)
        self.bg_color = QtGui.QColor(127, 127, 127, 0)
        self.pen_color = QtGui.QPen(
            self.fg_color,
            3,
            QtCore.Qt.SolidLine,
            QtCore.Qt.RoundCap,
            QtCore.Qt.RoundJoin,
        )
        self.pen_stroke = QtGui.QPen(
            QtGui.QColor(0, 0, 0),
            2,
            QtCore.Qt.SolidLine,
            QtCore.Qt.RoundCap,
            QtCore.Qt.RoundJoin,
        )

        self.painter = QtGui.QPainter()
        self.path = Path()
        self._cursor_overridden = False

        self._event_filter = OverlayFactoryFilter(self)
        if parent:
            parent.installEventFilter(self._event_filter)

    def draw_tangent(self, start_point, end_point, ellipseSize=7):
        """Draws a tangent line between two points with an ellipse at the start point.

        Parameters:
            start_point (QtCore.QPointF): The starting point of the line.
            end_point (QtCore.QPointF): The ending point of the line.
            ellipseSize (int, optional): The size of the ellipse at the starting point. Defaults to 7.
        """
        if end_point.isNull():
            return

        linePath = QtGui.QPainterPath()
        ellipsePath = QtGui.QPainterPath()

        if ellipseSize:
            ellipsePath.addEllipse(start_point, ellipseSize, ellipseSize)

        self.painter.fillRect(self.rect(), self.bg_color)
        self.painter.setRenderHint(QtGui.QPainter.Antialiasing, self.antialiasing)

        # Draw the line
        linePath.moveTo(start_point)
        linePath.lineTo(end_point)

        # Combine the paths
        combinedPath = QtGui.QPainterPath()
        combinedPath.addPath(ellipsePath)
        combinedPath.addPath(linePath)

        # Create a stroker with the pen_stroke and stroke the combined path
        stroker = QtGui.QPainterPathStroker(self.pen_stroke)
        strokedPath = stroker.createStroke(combinedPath)

        # Draw the stroked path (outline)
        self.painter.setPen(self.pen_stroke)
        self.painter.setBrush(QtCore.Qt.NoBrush)
        self.painter.drawPath(strokedPath)

        # Draw the combined shape with the fill color
        self.painter.setPen(self.pen_color)
        self.painter.setBrush(self.fg_color)
        self.painter.drawPath(combinedPath)

    def init_region(self, ui, *args, **kwargs):
        """Initializes a Region widget with the specified properties and adds it to the given UI's central widget.

        Parameters:
            ui (QWidget): The parent QWidget in which the Region widget will be added.

        Returns:
            Region: The initialized Region widget.
        """
        from uitk.widgets.region import Region

        region_widget = Region(ui, *args, **kwargs)

        return region_widget

    def start_gesture(self, global_pos: QtCore.QPoint) -> None:
        """Begin a gesture at the given global position.

        This sets the cursor to CrossCursor, clears any existing painting,
        and resets the path to start from the given position.

        Parameters:
            global_pos: The global screen position to start the gesture.
        """
        if not self._cursor_overridden:
            QtWidgets.QApplication.setOverrideCursor(
                QtGui.QCursor(QtCore.Qt.CrossCursor)
            )
            self._cursor_overridden = True

        self.clear_paint_events()
        self.path.reset()
        self.mouseMovePos = self.mapFromGlobal(global_pos)

    def clone_widgets_along_path(self, ui, return_func):
        """Re-constructs the relevant widgets from the previous UI for the new UI, and positions them.
        Initializes the new widgets by adding them to the switchboard.
        The previous widget information is derived from the widget and draw paths.
        Sets up the on_enter signal of the Region widget to be connected to the return_to_start method.

        Parameters:
            ui (QMainWindow): The UI in which to copy the widgets to.
        """
        if not self.path.start_pos:
            # Fallback: initialize path at current cursor if missing
            self.start_gesture(QtGui.QCursor.pos())

        # Initialize the return area region for the UI
        region_widget = self.init_region(ui, self.path.start_pos)
        region_widget.on_enter.connect(return_func)
        region_widget.on_enter.connect(self.path.clear_to_origin)

        # Clone the widgets along the path (intermediate entries only)
        new_widgets = tuple(
            self._clone_widget(ui, w, pos)
            for w, pos, _ in self.path.intermediate_entries
        )

        return new_widgets

    def _clone_widget(
        self,
        ui: QtWidgets.QMainWindow,
        prev_widget: QtWidgets.QWidget,
        position: QtCore.QPoint,
    ) -> QtWidgets.QWidget:
        """Clone a widget and place it at the given position in the UI."""
        new_widget = type(prev_widget)(ui)

        # Build getter map from class constant
        attr_getters = {
            "objectName": lambda w: w.objectName(),
            "accessibleName": lambda w: w.accessibleName(),
            "toolTip": lambda w: w.toolTip(),
            "statusTip": lambda w: w.statusTip(),
            "whatsThis": lambda w: w.whatsThis(),
            "font": lambda w: w.font(),
            "styleSheet": lambda w: w.styleSheet(),
            "enabled": lambda w: w.isEnabled(),
            "visible": lambda w: w.isVisible(),
            "size": lambda w: w.size(),
            "minimumSize": lambda w: w.minimumSize(),
            "maximumSize": lambda w: w.maximumSize(),
            "layoutDirection": lambda w: w.layoutDirection(),
            "contextMenuPolicy": lambda w: w.contextMenuPolicy(),
            "cursor": lambda w: w.cursor(),
            "windowTitle": lambda w: w.windowTitle(),
            "windowIcon": lambda w: w.windowIcon(),
        }

        if hasattr(prev_widget, "text") and callable(prev_widget.text):
            attr_getters["text"] = lambda w: w.text()

        for attr in self.CLONE_ATTRS:
            getter = attr_getters.get(attr)
            if not getter:
                continue
            setter_name = f"set{attr[0].upper()}{attr[1:]}"
            if hasattr(new_widget, setter_name):
                try:
                    getattr(new_widget, setter_name)(getter(prev_widget))
                except Exception:
                    continue

        # Handle text separately if present
        if "text" in attr_getters and hasattr(new_widget, "setText"):
            try:
                new_widget.setText(attr_getters["text"](prev_widget))
            except Exception:
                pass

        new_pos = new_widget.mapFromGlobal(position - new_widget.rect().center())
        new_widget.move(new_pos)
        new_widget.setVisible(True)

        return new_widget

    def clear_paint_events(self):
        """Clear paint events by disabling drawing and updating the overlay."""
        self.clear_painting = True
        self.update()

    def paintEvent(self, event):
        """Handles the paint event for the overlay, drawing the tangent paths as needed."""
        self.painter.begin(self)

        if self.clear_painting:
            self.painter.fillRect(self.rect(), self.bg_color)
            self.clear_painting = False
        elif self.draw_enabled:
            # plot and draw the points in the path list.
            for i, (_, _, start_point) in enumerate(self.path._path):
                start_point = self.mapFromGlobal(start_point)
                try:
                    end_point = self.mapFromGlobal(self.path._path[i + 1][2])
                except IndexError:
                    end_point = self.mouseMovePos
                    # after the list points are drawn, plot the current end_point, controlled by the mouse move event.

                self.draw_tangent(start_point, end_point)

        self.painter.end()

    def mousePressEvent(self, event):
        """Handle mouse press by starting gesture at the event position."""
        self.start_gesture(event.globalPos())
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        """Handle mouse release by restoring cursor and clearing painting."""
        if self._cursor_overridden:
            QtWidgets.QApplication.restoreOverrideCursor()
            self._cursor_overridden = False

        self.clear_paint_events()
        super().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event):
        """ """
        self.draw_enabled = True
        self.mouseMovePos = event.pos()
        self.update()

        super().mouseMoveEvent(event)

    def hideEvent(self, event):
        """Clears the path and restores the cursor when the overlay is hidden."""
        self.path.clear()
        if self._cursor_overridden:
            QtWidgets.QApplication.restoreOverrideCursor()
            self._cursor_overridden = False
        super().hideEvent(event)


# --------------------------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    overlay = Overlay()

    sys.exit(overlay.app.exec_())

# module name
# print(__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
