# !/usr/bin/python
# coding=utf-8
import sys
import logging
from PySide2 import QtCore, QtGui, QtWidgets
import pythontk as ptk
from uitk.switchboard import Switchboard
from uitk.events import EventFactoryFilter, MouseTracking
from tentacle.overlay import Overlay


class Tcl(QtWidgets.QStackedWidget):
    """Tcl is a marking menu based on a QStackedWidget.
    The various UI's are set by calling 'set_ui' with the intended UI name string. ex. Tcl().set_ui('polygons')

    Parameters:
        parent (QWidget): The parent application's top level window instance. ie. the Maya main window.
        key_show (str): The name of the key which, when pressed, will trigger the display of the marking menu. This should be one of the key names defined in QtCore.Qt. Defaults to 'Key_F12'.
        ui_location (str): The directory path or the module where the UI files are located.
                If the given dir is not a full path, it will be treated as relative to the default path.
                If a module is given, the path to that module will be used.
        slots_location (str): The directory path where the slot classes are located or a class object.
                If the given dir is a string and not a full path, it will be treated as relative to the default path.
                If a module is given, the path to that module will be used.
        prevent_hide (bool): While True, the hide method is disabled.
        log_level (int): Determines the level of logging messages to print. Defaults to logging.WARNING. Accepts standard Python logging module levels: DEBUG, INFO, WARNING, ERROR, CRITICAL.
    """

    # return the existing QApplication object, or create a new one if none exists.
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)

    left_mouse_double_click = QtCore.Signal()
    left_mouse_double_click_ctrl = QtCore.Signal()
    left_mouse_double_click_ctrl_alt = QtCore.Signal()
    middle_mouse_double_click = QtCore.Signal()
    right_mouse_double_click = QtCore.Signal()
    key_show_release = QtCore.Signal()

    def __init__(
        self,
        parent=None,
        key_show="Key_F12",
        ui_location="ui",
        slots_location="slots",
        prevent_hide=False,
        log_level=logging.WARNING,
    ):
        """ """
        super().__init__(parent)

        self._init_logger(log_level)

        self.key_show = getattr(QtCore.Qt, key_show)
        self.key_close = QtCore.Qt.Key_Escape
        self.prevent_hide = prevent_hide
        self._mouse_press_pos = QtCore.QPoint()

        # self.app.setDoubleClickInterval(400)
        # self.app.setKeyboardInputInterval(400)
        self.setFocusPolicy(QtCore.Qt.StrongFocus)

        self.setWindowFlags(QtCore.Qt.Tool | QtCore.Qt.FramelessWindowHint)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setAttribute(QtCore.Qt.WA_NoMousePropagation, False)
        self.resize(1600, 800)

        self.sb = Switchboard(
            self,
            ui_location=ui_location,
            slots_location=slots_location,
            set_legal_name_no_tags_attr=True,
            log_level=logging.ERROR,
        )
        self.child_event_filter = EventFactoryFilter(
            self,
            event_name_prefix="child_",
            forward_events_to=self,
        )
        self.overlay = Overlay(self, antialiasing=True)
        self.mouse_tracking = MouseTracking(self)

        self.left_mouse_double_click_ctrl.connect(self.repeat_last_command)
        # self.left_mouse_double_click_ctrl_alt.connect()
        # self.middle_mouse_double_click.connect()
        self.right_mouse_double_click.connect(self.repeat_last_ui)

    def _init_logger(self, log_level):
        """Initializes logger."""
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(log_level)
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )
        self.logger.addHandler(handler)

    def _init_ui(self, ui):
        """Initialize the given UI.

        Parameters:
            ui (QWidget): The UI to initialize.
        """
        if not isinstance(ui, QtWidgets.QWidget):
            raise ValueError(f"Invalid datatype: {type(ui)}, expected QWidget.")

        if ui.has_tag("startmenu|submenu"):  # StackedWidget
            ui.set_style(theme="dark", style_class="translucentBgNoBorder")
            self.addWidget(ui)  # add the UI to the stackedLayout.

        else:  # MainWindow
            ui.setParent(self.parent())
            ui.setWindowFlags(QtCore.Qt.Tool | QtCore.Qt.FramelessWindowHint)
            ui.setAttribute(QtCore.Qt.WA_TranslucentBackground)
            ui.centralWidget().setProperty("class", "translucentBgWithBorder")
            ui.set_style(theme="dark")
            self.key_show_release.connect(ui.hide)

        # set style before child init (resize).
        self.add_child_event_filter(ui.widgets)
        ui.on_child_added.connect(lambda w: self.add_child_event_filter(w))

    def set_ui(self, ui):
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
        if not found_ui:
            raise ValueError(f"UI not found: {ui}")

        found_ui.set_as_current()  # only set stacked UI as current.
        if not found_ui.is_initialized:
            self._init_ui(found_ui)

        if found_ui.has_tag("startmenu|submenu"):
            if found_ui.has_tag("startmenu"):
                self.move(self.sb.get_cursor_offset_from_center(self))
            self.setCurrentWidget(found_ui)  # set the stacked widget to the found UI.

        else:
            self.hide()
            found_ui.show()
            found_ui.setFixedSize(found_ui.minimumSizeHint())
            found_ui.update()
            # move to cursor position.
            self.sb.center_widget(found_ui, "cursor", offset_y=25)

    def set_submenu(self, ui, w):
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

    def return_to_startmenu(self):
        """Return the stacked widget to it's starting index."""
        if not self.overlay.path.start_pos:
            raise ValueError("No start position found in the path.")

        startmenu = self.sb.ui_history(-1, inc="*#startmenu*")
        # logging.info(f"startmenu: {startmenu.name}")
        self.set_ui(startmenu)
        self.move(self.overlay.path.start_pos - self.rect().center())

    # ---------------------------------------------------------------------------------------------
    #   Stacked Widget Event handling:

    def send_key_press_event(self, key, modifier=QtCore.Qt.NoModifier):
        """ """
        self.grabKeyboard()
        event = QtGui.QKeyEvent(QtCore.QEvent.KeyPress, key, modifier)
        self.keyPressEvent(event)  # self.app.postEvent(self, event)

    def keyPressEvent(self, event):
        """A widget must call setFocusPolicy() to accept focus initially, and have focus, in order to receive a key press event."""
        if event.isAutoRepeat():
            return

        # modifiers = self.app.keyboardModifiers()
        elif event.key() == self.key_close:
            self.close()

        super().keyPressEvent(event)

    def keyReleaseEvent(self, event):
        """A widget must accept focus initially, and have focus, in order to receive a key release event."""
        if event.isAutoRepeat():
            return

        modifiers = self.app.keyboardModifiers()

        if event.key() == self.key_show and not modifiers == QtCore.Qt.ControlModifier:
            self.key_show_release.emit()
            self.releaseKeyboard()
            self.hide()

        super().keyReleaseEvent(event)

    def mousePressEvent(self, event):
        """ """
        modifiers = self.app.keyboardModifiers()

        if self.sb.ui.has_tag("startmenu|submenu"):
            if not modifiers:
                if event.button() == QtCore.Qt.LeftButton:
                    self.set_ui("cameras#startmenu")

                elif event.button() == QtCore.Qt.MiddleButton:
                    self.set_ui("editors#startmenu")

                elif event.button() == QtCore.Qt.RightButton:
                    self.set_ui("main#startmenu")

        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        """ """
        self.set_ui("init#startmenu")

        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        """ """
        modifiers = self.app.keyboardModifiers()

        if self.sb.ui.has_tag("startmenu|submenu"):
            if event.button() == QtCore.Qt.LeftButton:
                if modifiers == QtCore.Qt.ControlModifier:
                    self.left_mouse_double_click_ctrl.emit()
                elif modifiers == (QtCore.Qt.ControlModifier | QtCore.Qt.AltModifier):
                    self.left_mouse_double_click_ctrl_alt.emit()
                else:
                    self.left_mouse_double_click.emit()

            elif event.button() == QtCore.Qt.MiddleButton:
                self.middle_mouse_double_click.emit()

            elif event.button() == QtCore.Qt.RightButton:
                self.right_mouse_double_click.emit()

        super().mouseDoubleClickEvent(event)

    def show(self, ui="init#startmenu", profile=False):
        """Sets the widget as visible.

        Parameters:
            ui (str/QWidget): Show the given UI.
            profile (bool): Prints the total running time, times each function separately,
                    and tells you how many times each function was called.
        """
        self.send_key_press_event(self.key_show)

        if profile:
            import cProfile

            ui_name = self.sb.get_ui(ui).name
            cProfile.runctx("self.set_ui(ui_name)", globals(), locals())

        else:
            self.set_ui(ui)

        if self.sb.ui.name == "init#startmenu":
            self.move(self.sb.get_cursor_offset_from_center(self))

        super().show()
        self.activateWindow()  # the window cannot be activated for keyboard events until after it is shown.

    def hide(self, force=False):
        """Sets the widget as invisible.
        Prevents hide event under certain circumstances.

        Parameters:
            force (bool): override prevent_hide.
        """
        if force or not self.prevent_hide:
            # logging.info(f"mouseGrabber: {self.mouseGrabber()}") #Returns the widget that is currently grabbing the mouse input. else: None
            super().hide()

    def hideEvent(self, event):
        """Hide events are sent to widgets immediately after they have been hidden."""
        try:
            self.mouseGrabber().releaseMouse()
        except AttributeError:  # NoneType object has no attribute 'releaseMouse'
            pass

        super().hideEvent(event)

    # ---------------------------------------------------------------------------------------------

    def add_child_event_filter(self, widgets):
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
            if (w.derived_type not in filtered_types) or (  # not correct type.
                not w.ui.has_tag("startmenu|submenu")  # not stacked UI:
            ):
                continue

            # print('add_child_event_filter:', w.ui.name.ljust(26), w.base_name.ljust(25), (w.name or type(w).__name__).ljust(25), w.type.ljust(15), w.derived_type.ljust(15), id(w)) #debug
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

            if w.type == self.sb.Region:
                w.visible_on_mouse_over = True

    def child_enterEvent(self, w, event):
        """ """
        if w.derived_type == QtWidgets.QPushButton:
            if w.base_name == "i":  # set the stacked widget.
                submenu_name = f"{w.whatsThis()}#submenu"
                if submenu_name != w.ui.name:
                    submenu = self.sb.get_ui(submenu_name)
                    if submenu:
                        self.set_submenu(submenu, w)

        if w.base_name == "chk":
            if w.ui.has_tag("submenu"):
                if self.isVisible():  # Omit children of popup menus.
                    w.click()  # send click signal on enterEvent.

        w.enterEvent(event)

    def child_mousePressEvent(self, w, event):
        """ """
        self._mouse_press_pos = event.globalPos()  # mouse positon at press
        self.__mouseMovePos = event.globalPos()  # mouse move position from last press

        w.mousePressEvent(event)

    def child_mouseMoveEvent(self, w, event):
        """ """
        try:
            globalPos = event.globalPos()
            self.__mouseMovePos = globalPos
        except AttributeError:
            pass

        w.mouseMoveEvent(event)

    def child_mouseReleaseEvent(self, w, event):
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
                w.click()  # send click signal on mouseRelease.

        w.mouseReleaseEvent(event)

    def child_sendKeyPressEvent(self, w, key, modifier=QtCore.Qt.NoModifier):
        """ """
        w.grabKeyboard()
        event = QtGui.QKeyEvent(QtCore.QEvent.KeyPress, key, modifier)
        self.child_keyPressEvent(w, event)

    def child_keyReleaseEvent(self, w, event):
        """A widget must accept focus initially, and have focus, in order to receive a key release event."""
        if not event.isAutoRepeat():
            # logging.info(f'child_keyReleaseEvent: {e}: {event}')
            modifiers = self.app.keyboardModifiers()

            if (
                event.key() == self.key_show
                and not modifiers == QtCore.Qt.ControlModifier
            ):
                if w.derived_type == QtWidgets.QMainWindow:
                    if not w.ui.has_tag("startmenu|submenu"):
                        self.key_show_release.emit()
                        w.releaseKeyboard()

        w.keyReleaseEvent(event)

    # ---------------------------------------------------------------------------------------------

    @staticmethod
    def get_unknown_tags(tag_string, known_tags="submenu|startmenu"):
        """Extracts all tags from a given string that are not known tags.

        Parameters:
            tag_string (str): The string from which to extract unknown tags.

        Returns:
            list: A list of unknown tags extracted from the tag_string.

        Note:
            Known tags are defined as 'submenu' and 'startmenu'. Any other tag found in the string
            is considered unknown. Tags are expected to be prefixed by a '#' symbol.
        """
        import re

        unknown_tags = re.findall(f"#(?!{known_tags})[a-zA-Z0-9]*", tag_string)
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

    def hide_unmatched_groupboxes(self, ui, tag_string):
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

    def repeat_last_command(self):
        """Repeat the last stored command."""
        method = self.sb.prev_slot

        if callable(method):
            method()
        else:
            logging.info("No recent commands in history.")
        self.option_box = False

    def repeat_last_ui(self):
        """Open the last used top level menu."""
        prev_ui = self.sb.ui_history(-1, exc=("*#submenu*", "*#startmenu*"))
        if prev_ui:
            self.set_ui(prev_ui)
        else:
            logging.info("No recent menus in hibstory.")


# --------------------------------------------------------------------------------------------

if __name__ == "__main__":
    tcl = Tcl(slots_location="slots/maya")
    tcl.show(profile=0)

    # run app, show window, wait for input, then terminate program with a status code returned from app.
    exit_code = tcl.app.exec_()
    if exit_code != -1:
        sys.exit(exit_code)

# module name
# logging.info(__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
