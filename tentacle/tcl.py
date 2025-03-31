# !/usr/bin/python
# coding=utf-8
import sys
from qtpy import QtCore, QtWidgets
import pythontk as ptk
from uitk.switchboard import Switchboard
from uitk.events import EventFactoryFilter, MouseTracking
from tentacle.overlay import Overlay


class Tcl(
    QtWidgets.QStackedWidget, ptk.SingletonMixin, ptk.LoggingMixin, ptk.HelpMixin
):
    """Tcl is a marking menu based on a QStackedWidget.
    The various UI's are set by calling 'set_ui' with the intended UI name string. ex. Tcl().set_ui('polygons')

    Parameters:
        parent (QWidget): The parent application's top level window instance. ie. the Maya main window.
        key_show (str): The name of the key which, when pressed, will trigger the display of the marking menu. This should be one of the key names defined in QtCore.Qt. Defaults to 'Key_F12'.
        ui_source (str): The directory path or the module where the UI files are located.
                If the given dir is not a full path, it will be treated as relative to the default path.
                If a module is given, the path to that module will be used.
        slot_source (str): The directory path where the slot classes are located or a class object.
                If the given dir is a string and not a full path, it will be treated as relative to the default path.
                If a module is given, the path to that module will be used.
        prevent_hide (bool): While True, the hide method is disabled.
        log_level (int): Determines the level of logging messages. Defaults to logging.WARNING. Accepts standard Python logging module levels: DEBUG, INFO, WARNING, ERROR, CRITICAL.
    """

    # return the existing QApplication object, or create a new one if none exists.
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)

    left_mouse_double_click = QtCore.Signal()
    left_mouse_double_click_ctrl = QtCore.Signal()
    middle_mouse_double_click = QtCore.Signal()
    right_mouse_double_click = QtCore.Signal()
    right_mouse_double_click_ctrl = QtCore.Signal()
    key_show_press = QtCore.Signal()
    key_show_release = QtCore.Signal()

    _first_show = True
    _instances = {}

    def __init__(
        self,
        parent=None,
        key_show="F12",
        ui_source="ui",
        slot_source="slots",
        widget_source=None,
        prevent_hide=False,
        log_level: str = "WARNING",
    ):
        """ """
        super().__init__(parent=parent)
        self.logger.setLevel(log_level)

        self.sb = Switchboard(
            self,
            ui_source=ui_source,
            slot_source=slot_source,
            widget_source=widget_source,
        )
        self.child_event_filter = EventFactoryFilter(
            self,
            event_name_prefix="child_",
            forward_events_to=self,
        )
        self.overlay = Overlay(self, antialiasing=True)
        self.mouse_tracking = MouseTracking(self)

        self.key_show = self.sb.convert.to_qkey(key_show)
        self.key_close = QtCore.Qt.Key_Escape
        self.prevent_hide = prevent_hide
        self._mouse_press_pos = QtCore.QPoint()

        # self.app.setDoubleClickInterval(400)
        # self.app.setKeyboardInputInterval(400)

        self.setWindowFlags(
            QtCore.Qt.Tool
            | QtCore.Qt.FramelessWindowHint
            | QtCore.Qt.WindowStaysOnTopHint
        )
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setAttribute(QtCore.Qt.WA_NoMousePropagation, False)
        self.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.resize(800, 800)

        self.app.installEventFilter(self)

    def eventFilter(self, watched, event):
        if event.type() in (QtCore.QEvent.KeyPress, QtCore.QEvent.KeyRelease):
            if event.key() != self.key_show or event.isAutoRepeat():
                return False

            if event.type() == QtCore.QEvent.KeyPress:
                self.key_show_press.emit()
                self.show()
                return True

            if event.type() == QtCore.QEvent.KeyRelease:
                self.key_show_release.emit()
                self.hide()
                return True

        return super().eventFilter(watched, event)

    def _init_ui(self, ui) -> None:
        """Initialize the given UI.

        Parameters:
            ui (QWidget): The UI to initialize.
        """
        if not isinstance(ui, QtWidgets.QWidget):
            raise ValueError(f"Invalid datatype: {type(ui)}, expected QWidget.")

        if ui.has_tags(["startmenu", "submenu"]):  # StackedWidget
            if ui.has_tags("submenu"):
                ui.set_style(theme="dark", style_class="transparentBgNoBorder")
            else:
                ui.set_style(theme="dark", style_class="translucentBgNoBorder")
            self.addWidget(ui)  # add the UI to the stackedLayout.

        else:  # MainWindow
            ui.setParent(self.parent())
            ui.setWindowFlags(QtCore.Qt.Tool | QtCore.Qt.FramelessWindowHint)
            ui.setAttribute(QtCore.Qt.WA_TranslucentBackground)
            ui.set_style(theme="dark", style_class="translucentBgWithBorder")
            try:
                ui.header.config_buttons(menu_button=True, pin_button=True)
            except AttributeError:
                pass
            self.key_show_release.connect(ui.hide)

        # set style before child init (resize).
        self.add_child_event_filter(ui.widgets)
        ui.on_child_added.connect(lambda w: self.add_child_event_filter(w))

    def set_ui(self, ui) -> None:
        """Set the stacked Widget's index to the given UI.

        Parameters:
            ui (str/QWidget): The UI or name of the UI to set the stacked widget index to.
        """
        if not isinstance(ui, (str, QtWidgets.QWidget)):
            raise ValueError(
                f"Invalid datatype for ui: {type(ui)}, expected str or QWidget."
            )

        # Get the UI of the given name, and set it as the current UI in the switchboard module.
        found_ui = self.sb.get_ui(ui)
        if not found_ui.is_initialized:
            self._init_ui(found_ui)

        if found_ui.has_tags(["startmenu", "submenu"]):
            if found_ui.has_tags("startmenu"):
                self.move(self.sb.get_cursor_offset_from_center(self))
            self.setCurrentWidget(found_ui)  # set the stacked widget to the found UI.

        else:
            self.hide()
            found_ui.show()
            QtWidgets.QApplication.processEvents()  # <-- force visibility + signal sync

            widget_before_adjust = found_ui.width()
            found_ui.adjustSize()
            found_ui.resize(widget_before_adjust, found_ui.sizeHint().height())
            found_ui.updateGeometry()
            self.sb.center_widget(found_ui, "cursor", offset_y=25)

    def set_submenu(self, ui, w) -> None:
        """Set the stacked widget's index to the submenu associated with the given widget.
        Positions the new UI to line up with the previous UI's button that called the new UI.
        If the given UI is already set, then this method will simply return without performing any operation.

        Parameters:
            ui (QWidget): The UI submenu to set as current.
            w (QWidget): The widget under cursor at the time this method was called.
        """
        if not isinstance(ui, QtWidgets.QWidget):
            raise ValueError(f"Invalid datatype for ui: {type(ui)}, expected QWidget.")

        self.overlay.path.add(ui, w)
        self.set_ui(ui)  # switch the stacked widget to the given submenu.

        # get the old widget position.
        p1 = w.mapToGlobal(w.rect().center())
        # get the widget of the same name in the new UI.
        w2 = self.sb.get_widget(w.name, ui)
        # get the new widget position.
        p2 = w2.mapToGlobal(w2.rect().center())
        currentPos = self.mapToGlobal(self.pos())
        # move the UI to currentPos + difference
        self.move(self.mapFromGlobal(currentPos + (p1 - p2)))

        # if the submenu UI called for the first time:
        if ui not in self.sb.ui_history(slice(0, -1), allow_duplicates=True):
            # re-construct any widgets from the previous UI that fall along the plotted path.
            return_func = self.return_to_startmenu
            self.overlay.clone_widgets_along_path(ui, return_func)

    def return_to_startmenu(self) -> None:
        """Return the stacked widget to it's starting index."""
        if not self.overlay.path.start_pos:
            raise ValueError("No start position found in the path.")

        startmenu = self.sb.ui_history(-1, inc="*#startmenu*")
        self.set_ui(startmenu)
        self.move(self.overlay.path.start_pos - self.rect().center())

    # ---------------------------------------------------------------------------------------------
    #   Stacked Widget Event handling:

    def mousePressEvent(self, event) -> None:
        """ """
        if self.sb.current_ui.has_tags(["startmenu", "submenu"]):
            if not event.modifiers():
                if event.button() == QtCore.Qt.LeftButton:
                    self.set_ui("cameras#startmenu")

                elif event.button() == QtCore.Qt.MiddleButton:
                    self.set_ui("editors#startmenu")

                elif event.button() == QtCore.Qt.RightButton:
                    self.set_ui("main#startmenu")

        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        """ """
        self.set_ui("init#startmenu")

        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:
        """ """
        if self.sb.current_ui.has_tags(["startmenu", "submenu"]):
            if event.button() == QtCore.Qt.LeftButton:
                if event.modifiers() == QtCore.Qt.ControlModifier:
                    self.left_mouse_double_click_ctrl.emit()
                else:
                    self.left_mouse_double_click.emit()

            elif event.button() == QtCore.Qt.MiddleButton:
                self.middle_mouse_double_click.emit()

            elif event.button() == QtCore.Qt.RightButton:
                if event.modifiers() == QtCore.Qt.ControlModifier:
                    self.right_mouse_double_click_ctrl.emit()
                else:
                    self.right_mouse_double_click.emit()

        super().mouseDoubleClickEvent(event)

    def show(self, ui="init#startmenu") -> None:
        """Override show to simulate key press only on first run for eventFilter to catch release."""
        if not self.isVisible():
            if self._first_show:
                self.sb.simulate_key_press(self, self.key_show)
                self._first_show = False
                self.set_ui(ui)

            if self.sb.current_ui.name == "init#startmenu":
                self.move(self.sb.get_cursor_offset_from_center(self))
            super().show()
        self.raise_()
        self.activateWindow()

    def hide(self, force=False) -> None:
        """Sets the widget as invisible.
        Prevents hide event under certain circumstances.

        Parameters:
            force (bool): override prevent_hide.
        """
        if force or not self.prevent_hide:
            super().hide()

    def hideEvent(self, event):
        if QtWidgets.QWidget.keyboardGrabber() is self:
            self.releaseKeyboard()

        if self.mouseGrabber():
            self.mouseGrabber().releaseMouse()

        super().hideEvent(event)

    # ---------------------------------------------------------------------------------------------

    def add_child_event_filter(self, widgets) -> None:
        """Initialize child widgets with an event filter.

        Parameters:
            widgets (str/list): The widget(s) to initialize.
        """
        # Only Install the event filter for the following widget types.
        filtered_types = [
            QtWidgets.QMainWindow,
            QtWidgets.QWidget,
            QtWidgets.QAction,
            QtWidgets.QLabel,
            QtWidgets.QPushButton,
            QtWidgets.QCheckBox,
            QtWidgets.QRadioButton,
        ]

        for w in ptk.make_iterable(widgets):
            if (w.derived_type not in filtered_types) or (  # not correct derived type:
                not w.ui.has_tags(["startmenu", "submenu"])  # not stacked UI:
            ):
                continue

            w.installEventFilter(self.child_event_filter)

            if w.derived_type in (
                QtWidgets.QPushButton,
                QtWidgets.QLabel,
                QtWidgets.QCheckBox,
                QtWidgets.QRadioButton,
            ):
                self.sb.center_widget(w, padding_x=25)
                if w.base_name == "i":
                    w.ui.set_style(widget=w)

            if w.type == self.sb.registered_widgets.Region:
                w.visible_on_mouse_over = True

    def child_enterEvent(self, w, event) -> None:
        """ """
        if w.derived_type == QtWidgets.QPushButton:
            if w.base_name == "i":  # set the stacked widget.
                submenu_name = f"{w.whatsThis()}#submenu"
                if submenu_name != w.ui.name:
                    submenu = self.sb.get_ui(submenu_name)
                    if submenu:
                        self.set_submenu(submenu, w)

        if w.base_name == "chk":
            if w.ui.has_tags("submenu"):
                if self.isVisible():  # Omit children of popup menus.
                    w.click()  # send click signal on enterEvent.

        w.enterEvent(event)

    def child_mousePressEvent(self, w, event) -> None:
        """ """
        self._mouse_press_pos = event.globalPos()  # mouse positon at press
        self.__mouseMovePos = event.globalPos()  # mouse move position from last press

        w.mousePressEvent(event)

    def child_mouseMoveEvent(self, w, event) -> None:
        """ """
        try:
            globalPos = event.globalPos()
            self.__mouseMovePos = globalPos
        except AttributeError:
            pass

        w.mouseMoveEvent(event)

    def child_mouseReleaseEvent(self, w, event) -> None:
        """ """
        if w.underMouse():  # if mouse over widget
            if w.derived_type == QtWidgets.QPushButton:
                if w.base_name == "i":  # ie. 'i012'
                    menu_name = w.whatsThis()
                    new_menu_name = self.clean_tag_string(menu_name)
                    menu = self.sb.get_ui(new_menu_name)
                    if menu:
                        self.hide_unmatched_groupboxes(menu, menu_name)
                        self.set_ui(menu)
            if hasattr(w, "click"):
                self.hide()
                if w.ui.has_tags(["startmenu", "submenu"]):
                    if not w.base_name == "chk":
                        w.click()  # send click signal on mouseRelease.

        w.mouseReleaseEvent(event)

    # ---------------------------------------------------------------------------------------------

    @staticmethod
    def get_unknown_tags(tag_string, known_tags=["submenu", "startmenu"]):
        """Extracts all tags from a given string that are not known tags.

        Parameters:
            tag_string (str/list): The known tags in which to derive any unknown tags from.

        Returns:
            list: A list of unknown tags extracted from the tag_string.

        Note:
            Known tags are defined as 'submenu' and 'startmenu'. Any other tag found in the string
            is considered unknown. Tags are expected to be prefixed by a '#' symbol.
        """
        import re

        # Join known_tags into a pattern string
        known_tags_list = ptk.make_iterable(known_tags)
        known_tags_pattern = "|".join(known_tags_list)
        unknown_tags = re.findall(f"#(?!{known_tags_pattern})[a-zA-Z0-9]*", tag_string)
        # Remove leading '#' from all tags
        unknown_tags = [tag[1:] for tag in unknown_tags if tag != "#"]
        return unknown_tags

    def clean_tag_string(self, tag_string):
        """Cleans a given tag string by removing unknown tags.

        Parameters:
            tag_string (str): The string from which to remove unknown tags.

        Returns:
            str: The cleaned tag string with unknown tags removed.

        Note:
            This function utilizes the get_unknown_tags function to identify and subsequently
            remove unknown tags from the provided string.
        """
        import re

        unknown_tags = self.get_unknown_tags(tag_string)
        # Remove unknown tags from the string
        cleaned_tag_string = re.sub("#" + "|#".join(unknown_tags), "", tag_string)
        return cleaned_tag_string

    def hide_unmatched_groupboxes(self, ui, tag_string) -> None:
        """Hides all QGroupBox widgets in the provided UI that do not match the unknown tags extracted
        from the provided tag string.

        Parameters:
            ui (QObject): The UI object in which to hide unmatched QGroupBox widgets.
            tag_string (str): The string from which to extract unknown tags for comparison.

        Note:
            This function uses the get_unknown_tags function to determine which QGroupBox widgets
            to hide. If a QGroupBox widget's objectName does not match one of the unknown tags,
            the widget will be hidden.
        """
        unknown_tags = self.get_unknown_tags(tag_string)

        # Find all QGroupBox widgets in the UI
        groupboxes = ui.findChildren(QtWidgets.QGroupBox)

        # Hide all groupboxes that do not match the unknown tags
        for groupbox in groupboxes:
            if unknown_tags and groupbox.objectName() not in unknown_tags:
                groupbox.hide()
            else:
                groupbox.show()


# --------------------------------------------------------------------------------------------

if __name__ == "__main__":
    tcl = Tcl(slot_source="slots/maya")
    tcl.show("screen", app_exec=True)


# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
