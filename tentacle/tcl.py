# !/usr/bin/python
# coding=utf-8
import sys, os
import logging, traceback
from PySide2 import QtCore, QtGui, QtWidgets
from pythontk import makeList
from uitk.switchboard import Switchboard
from uitk.events import EventFactoryFilter, MouseTracking
from tentacle.overlay import Overlay


class Tcl(QtWidgets.QStackedWidget):
    """Tcl is a marking menu based on a QStackedWidget.
    The various UI's are set by calling 'set_ui' with the intended UI name string. ex. Tcl().set_ui('polygons')
    """

    # return the existing QApplication object, or create a new one if none exists.
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)

    _key_show_release = QtCore.Signal()

    def __init__(
        self,
        parent=None,
        key_show="Key_F12",
        ui_location="ui",
        slots_location="slots",
        prevent_hide=False,
    ):
        """
        Parameters:
            parent (obj): The parent application's top level window instance. ie. the Maya main window.
        """
        super().__init__(parent)

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
            suppress_warnings=True,
        )
        self.child_event_filter = EventFactoryFilter(
            self,
            event_name_prefix="child_",
            forward_events_to=self,
        )
        self.overlay = Overlay(self, antialiasing=True)
        self.mouse_tracking = MouseTracking(self)

    def init_ui(self, ui):
        """Initialize the given UI.

        Parameters:
            ui (obj): The UI to initialize.
        """
        if not isinstance(ui, QtWidgets.QWidget):
            raise ValueError(
                f"Incorrect datatype for ui: {type(ui)}, expected QWidget."
            )

        self.init_child_event_filter(ui.widgets)
        ui.set_style("dark", append_to_existing=True)

        if ui.has_tag("startmenu|submenu"):  # stacked UI.
            self.addWidget(ui)  # add the UI to the stackedLayout.

        else:  # popup UI.
            ui.setParent(self.parent() or self)
            ui.setWindowFlags(QtCore.Qt.Tool | QtCore.Qt.FramelessWindowHint)
            ui.setAttribute(QtCore.Qt.WA_TranslucentBackground)
            self._key_show_release.connect(ui.hide)

    def set_ui(self, ui):
        """Set the stacked Widget's index to the given UI.

        Parameters:
            ui (str/obj): The UI or name of the UI to set the stacked widget index to.
        """
        if not isinstance(ui, (str, QtWidgets.QWidget)):
            raise ValueError(
                f"Incorrect datatype for ui: {type(ui)}, expected str or QWidget."
            )

        # Get the UI of the given name, and set it as the current UI in the switchboard module.
        found_ui = self.sb.get_ui(ui)
        if not found_ui:
            raise ValueError(f"UI not found: {ui}")

        if not found_ui.is_initialized:
            self.init_ui(found_ui)

        if found_ui.has_tag("startmenu|submenu"):
            found_ui.set_as_current()  # only set stacked UI as current.
            self.setCurrentWidget(found_ui)  # set the stacked widget to the found UI.
        else:
            found_ui.resize(found_ui.minimumSizeHint())
            # move to cursor position.
            self.sb.move_and_center_widget(found_ui, QtGui.QCursor.pos(), offset_y=4)
            self.hide()
            found_ui.show()

    def set_sub_ui(self, ui, w=None):
        """Set the stacked widget's index to the submenu associated with the given widget.
        Positions the new UI to line up with the previous UI's button that called the new UI.
        If the given UI is already set, then this method will simply return without performing any operation.

        Parameters:
            ui (obj): The UI submenu to set as current.
            w (obj): The widget under cursor at the time this method was called.
        """
        if not isinstance(ui, QtWidgets.QWidget):
            raise ValueError(
                f"Incorrect datatype for ui: {type(ui)}, expected QWidget."
            )

        if ui == self.sb.ui:  # if the given ui is the current ui, no need to set.
            return

        if not w:  # if no widget is given, attempt to use the widget under cursor.
            widget_pos = widget.mapFromGlobal(QtGui.QCursor.pos())
            w = widget.childAt(widget_pos)
            if not w:
                return

        # get the widget position before submenu change.
        p1 = w.mapToGlobal(w.rect().center())
        self.overlay.add_to_path(ui, w)

        self.set_ui(ui)  # switch the stacked widget to the given submenu.
        # get the widget of the same name in the new UI.
        w2 = getattr(self.currentWidget(), w.name)
        # get the widget position after submenu change.
        p2 = w2.mapToGlobal(w2.rect().center())
        currentPos = self.mapToGlobal(self.pos())
        # move to currentPos + difference
        self.move(self.mapFromGlobal(currentPos + (p1 - p2)))

        # if the submenu UI called for the first time:
        if ui not in self.sb.get_prev_ui(as_list=True):
            # re-construct any widgets from the previous UI that fall along the plotted path.
            cloned_widgets = self.overlay.clone_widgets_along_path(
                ui, self.return_to_starting_ui
            )
            # Initialize the widgets to set things like the event filter.
            self.init_child_event_filter(cloned_widgets)

    def return_to_starting_ui(self):
        """Return the stacked widget to it's starting index."""
        # Check for start position and raise error if not found
        self.overlay.validate_path_start_pos()

        starting_ui = self.sb.get_prev_ui(exc="*#submenu")
        # logging.info(f"starting_ui: {starting_ui or starting_ui.name}")
        self.set_ui(starting_ui)

        self.move(self.overlay.path_start_pos - self.rect().center())

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
            self._key_show_release.emit()
            self.releaseKeyboard()
            self.hide()

        super().keyReleaseEvent(event)

    def mousePressEvent(self, event):
        """ """
        modifiers = self.app.keyboardModifiers()

        if self.sb.ui.has_tag("startmenu|submenu"):
            self.move(self.sb.get_center(self))

            if not modifiers:
                if event.button() == QtCore.Qt.LeftButton:
                    self.set_ui("cameras#startmenu")

                elif event.button() == QtCore.Qt.MiddleButton:
                    self.set_ui("editors#startmenu")

                elif event.button() == QtCore.Qt.RightButton:
                    self.set_ui("main#startmenu")

        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        """The widget will also receive mouse press and mouse release events
        in addition to the double click event. If another widget that overlaps
        this widget disappears in response to press or release events,
        then this widget will only receive the double click event.
        """
        modifiers = self.app.keyboardModifiers()

        if self.sb.ui.has_tag("startmenu|submenu"):
            if event.button() == QtCore.Qt.LeftButton:
                if modifiers in (
                    QtCore.Qt.ControlModifier,
                    QtCore.Qt.ControlModifier | QtCore.Qt.AltModifier,
                ):
                    self.repeat_last_command()
                else:
                    self.repeat_last_camera_view()

            elif event.button() == QtCore.Qt.MiddleButton:
                pass

            elif event.button() == QtCore.Qt.RightButton:
                self.repeat_last_ui()

        super().mouseDoubleClickEvent(event)

    def show(self, ui="init#startmenu", profile=False):
        """Sets the widget as visible.

        Parameters:
            ui (str/obj): Show the given UI.
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
            self.move(self.sb.get_center(self))

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
        except (
            AttributeError
        ) as error:  #'NoneType' object has no attribute 'releaseMouse'
            pass

        super().hideEvent(event)

    # ---------------------------------------------------------------------------------------------
    # child widget event handling:
    # ---------------------------------------------------------------------------------------------
    def init_child_event_filter(self, widgets):
        """Initialize child widgets with an event filter.

        Parameters:
            widgets (str/list): The widget(s) to initialize.
        """
        # Only Install the event filter for the following widget types.
        filtered_types = [
            "QMainWindow",
            "QWidget",
            "QAction",
            "QLabel",
            "QPushButton",
            "QCheckBox",
            "QRadioButton",
        ]
        for w in makeList(widgets):
            if (not w.derived_type in filtered_types) or (  # not correct type.
                not w.ui.has_tag("startmenu|submenu")  # not stacked UI:
            ):
                continue
            # print('init_child_event_filter:', w.ui.name.ljust(26), w.base_name.ljust(25), (w.name or type(w).__name__).ljust(25), w.type.ljust(15), w.derived_type.ljust(15), id(w)) #debug
            w.installEventFilter(self.child_event_filter)

            if w.derived_type in ("QPushButton", "QLabel"):
                if w.base_name == "i":
                    w.ui.set_style(widget=w)
                self.sb.resize_and_center_widget(w)

            if w.type == "Region":
                w.visible_on_mouse_over = True

    def child_showEvent(self, w, event):
        """ """
        if w.name == "info":
            self.sb.resize_and_center_widget(w)

        if w.type in ("ComboBox", "ListWidget"):
            try:  # call the class method associated with the current widget.
                w.get_slot()()
            except (AttributeError, TypeError):
                logging.info(traceback.format_exc())

        w.showEvent(event)

    def child_enterEvent(self, w, event):
        """ """
        if w.derived_type == "QPushButton":
            if w.base_name == "i":  # set the stacked widget.
                submenu_name = f"{w.whatsThis()}#submenu"
                submenu = self.sb.get_ui(submenu_name)
                if submenu:
                    self.set_sub_ui(submenu, w)

        if w.base_name == "chk":
            if w.ui.isSubmenu:
                w.click()

        w.enterEvent(event)

    def child_mousePressEvent(self, w, event):
        """ """
        self._mouse_press_pos = event.globalPos()  # mouse positon at press
        self.__mouseMovePos = event.globalPos()  # mouse move position from last press

        w.mousePressEvent(event)

    def child_mouseMoveEvent(self, w, event):
        """ """
        try:  # if hasattr(self, '__mouseMovePos'):
            globalPos = event.globalPos()
            diff = globalPos - self.__mouseMovePos
            self.__mouseMovePos = globalPos
        except AttributeError as error:
            pass

        w.mouseMoveEvent(event)

    def child_mouseReleaseEvent(self, w, event):
        """ """
        if w.underMouse():  # if mouse over widget
            if w.derived_type == "QPushButton":
                if w.base_name == "i":  # ie. 'i012'
                    self.set_ui(w.whatsThis())

                elif w.base_name in ("b", "tb"):
                    w.click()  # send click signal on mouseRelease.

                    if w.ui.name == "cameras#startmenu":
                        self.prev_camera(add=w.get_slot())

                    elif w.ui.isSubmenu:
                        self.hide()

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
                if w.type == "QMainWindow":
                    if not w.ui.has_tag("startmenu|submenu"):
                        self._key_show_release.emit()
                        w.releaseKeyboard()

        w.keyReleaseEvent(event)

    # ---------------------------------------------------------------------------------------------
    #
    # ---------------------------------------------------------------------------------------------
    def repeat_last_command(self):
        """Repeat the last stored command."""
        method = self.sb.prev_command

        if callable(method):
            method()
        else:
            logging.info("No recent commands in history.")

    def repeat_last_camera_view(self):
        """Show the previous camera view."""
        method = self.prev_camera()
        if method:
            method()
            method_ = self.prev_camera(allow_current=True, as_list=1)[-2][0]
        else:
            method_ = self.sb.cameras_startmenu.slots.b004  # get the persp camera.
            method_()
        self.prev_camera(add=method_)  # store the camera view

    def repeat_last_ui(self):
        """Open the last used top level menu."""
        prev_ui = self.sb.get_prev_ui(exc=("*#submenu", "*#startmenu"))
        if prev_ui:
            self.set_ui(prev_ui)
        else:
            logging.info("No recent menus in history.")

    camera_history = []

    def prev_camera(
        self,
        docstring=False,
        method=False,
        allow_current=False,
        as_list=False,
        add=None,
    ):
        """
        Parameters:
            docstring (bool): return the docstring of last camera command. Default is off.
            method (bool): return the method of last camera command. Default is off.
            allow_current (bool): allow the current camera. Default is off.
            add (str/obj): Add a method, or name of method to be used as the command to the current camera.
                    (if this flag is given, all other flags are invalidated)
        Returns:
            if docstring: 'string' description (derived from the last used camera command's docstring) (as_list: [string list] all docStrings, in order of use)
            if method: method of last used camera command. (as_list: [<method object> list} all methods, in order of use)
            if as_list: list of lists with <method object> as first element and <docstring> as second. ie. [[<v001>, 'camera: persp']]
            else : <method object> of the last used command
        """
        if add:  # set the given method as the current camera.
            if not callable(add):
                add = self.sb.get_slot("cameras#startmenu", add)
            docstring = add.__doc__
            prev_cameras = self.prev_camera(allow_current=True, as_list=1)
            if (
                not prev_cameras or not [add, docstring] == prev_cameras[-1]
            ):  # ie. do not append perp cam if the prev cam was perp.
                prev_cameras.append([add, docstring])  # store the camera view
            return

        # keep original list length restricted to last 20 elements
        self.camera_history = self.camera_history[-20:]

        # remove any previous duplicates if they exist; keeping the last added element.
        hist = self.camera_history
        [hist.remove(l) for l in hist[:] if hist.count(l) > 1]

        if not allow_current:
            hist = hist[:-1]  # remove the last index. (currentName)

        if as_list:
            if docstring and not method:
                try:
                    return [i[1] for i in hist]
                except:
                    return None
            elif method and not docstring:
                try:
                    return [i[0] for i in hist]
                except:
                    return ["No command history."]
            else:
                return hist

        elif docstring:
            try:
                return hist[-1][1]
            except:
                return ""

        else:
            try:
                return hist[-1][0]
            except:
                return None


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


# --------------------------------------------------------------------------------------------
# deprecated:
# --------------------------------------------------------------------------------------------

# self.app.focusChanged.connect(self.focusChanged)

# def focusChanged(self, old, new):
#   '''Called on focus events.

#   Parameters:
#       old (obj): The widget with previous focus.
#       new (obj): The widget with current focus.
#   '''
#   try:
#       new.grabKeyboard()
#   except AttributeError as error:
#       self.setFocus()

#   if not self.isActiveWindow():
#       self.hide()

# class Instance():
#   '''Manage multiple instances of the Tcl UI.
#   '''
#   instances={}

#   def __init__(self, parent=None, prevent_hide=False, key_show='Key_F12'):
#       '''
#       '''
#       self.Class = Tcl

#       self.parent = parent
#       self.prevent_hide = prevent_hide
#       self.key_show = key_show

#       self.activeWindow_ = None


#   @property
#   def instances_(self):
#       '''Get all instances as a dictionary with the names as keys, and the window objects as values.
#       '''
#       return {k:v for k,v in self.instances.items() if not any([v.isVisible(), v==self.activeWindow_])}


#   def _getInstance(self):
#       '''Internal use. Returns a new instance if one is running and currently visible.
#       Removes any old non-visible instances outside of the current 'activeWindow_'.
#       '''
#       if self.activeWindow_ is None or self.activeWindow_.isVisible():
#           name = 'tentacle'+str(len(self.instances_))
#           setattr(self, name, self.Class(self.parent, self.prevent_hide, self.key_show)) #set the instance as a property using it's name.
#           self.activeWindow_ = getattr(self, name)
#           self.instances_[name] = self.activeWindow_

#       return self.activeWindow_


#   def show(self, uiName=None, active=True):
#       '''Sets the widget as visible.

#       Parameters:
#           uiName (str): Show the UI of the given name.
#           active (bool): Set as the active window.
#       '''
#       inst = self._getInstance()
#       inst.show(uiName=uiName, active=active)


# class Worker(QtCore.QObject):
#   '''Send and receive signals from the GUI allowing for events to be
#   triggered from a separate thread.

#   ex. self.worker = Worker()
#       self.thread = QtCore.QThread()
#       self.worker.moveToThread(self.thread)
#       self.worker.finished.connect(self.thread.quit)
#       self.thread.started.connect(self.worker.start)
#       self.thread.start()
#       self.worker.stop()
#   '''
#   started = QtCore.Signal()
#   updateProgress = QtCore.Signal(int)
#   finished = QtCore.Signal()

#   def __init__(self, parent=None):
#       super().__init__(parent)

#   def start(self):
#       self.started.emit()

#   def stop(self):
#       self.finished.emit()


# self.worker = Worker()
# self.thread = QtCore.QThread()
# self.worker.moveToThread(self.thread)

# self.worker.finished.connect(self.thread.quit)
# self.thread.started.connect(self.worker.start)

# # self.loadingIndicator = self.sb.LoadingIndicator(color='white', start=True, setPosition_='cursor')
# self.loadingIndicator = self.sb.GifPlayer(setPosition_='cursor')
# self.worker.started.connect(self.loadingIndicator.start)
# self.worker.finished.connect(self.loadingIndicator.stop)
# self.thread.start()

# import time #threading test
# for _ in range(11):
#   time.sleep(.25)

# code
# self.worker.stop()


# if self.addUi(ui, query=True): #if the UI has not yet been added to the widget stack.
#   self.addUi(ui) #initialize the parent UI if not done so already.

# def addUi(self, ui, query=False):
#   '''Initializes the UI of the given name and it's dependancies.

#   Parameters:
#       ui (obj): The UI widget to be added to the layout stack.
#       query (bool): Check whether the UI widget has been added.

#   Returns:
#       (bool) When queried.
#   '''
#   if query:
#       return self.indexOf(ui)<0

#   for i in reversed(range(4)): #in order of uiLevel heirarchy (top-level parent down).
#       ui_ = self.sb.get_ui(ui, level=i)
#       if ui_:
#           name = self.sb.getUiName(ui_)

#           if self.addUi(ui_, query=True): #if the UI has not yet been added to the widget stack.
#               self.addWidget(ui_) #add the UI to the stackedLayout.
#               self.init_child_event_filter(name)
