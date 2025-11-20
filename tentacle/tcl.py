# !/usr/bin/python
# coding=utf-8
from typing import Optional

from qtpy import QtCore, QtWidgets, QtGui
import pythontk as ptk
from uitk.switchboard import Switchboard
from uitk.events import EventFactoryFilter, MouseTracking
from tentacle.overlay import Overlay


class ShortcutHandler(QtCore.QObject):
    """Application-wide shortcut that toggles the Tcl overlay."""

    _instance: Optional["ShortcutHandler"] = None

    def __init__(
        self, owner: "Tcl", shortcut_parent: Optional[QtWidgets.QWidget] = None
    ):
        super().__init__(owner)
        self._owner = owner
        self._target = self._resolve_target(shortcut_parent)
        sequence = self._build_sequence(owner.key_show)
        self._shortcut = QtWidgets.QShortcut(sequence, self._target)
        self._shortcut.setContext(QtCore.Qt.ApplicationShortcut)
        self._shortcut.setAutoRepeat(False)
        self._shortcut.activated.connect(self._on_key_press)
        self._key_is_down = False
        self._event_source = self._install_release_filter()

    @classmethod
    def create(
        cls, owner: "Tcl", shortcut_parent: Optional[QtWidgets.QWidget] = None
    ) -> "ShortcutHandler":
        """Install or update the global shortcut binding."""
        if cls._instance:
            cls._instance.deleteLater()
        cls._instance = cls(owner, shortcut_parent)
        return cls._instance

    def _install_release_filter(self):
        app = QtWidgets.QApplication.instance()
        source = app if app else self._target
        if source:
            source.installEventFilter(self)
        return source

    def _resolve_target(self, explicit_parent):
        if isinstance(explicit_parent, QtWidgets.QWidget):
            return explicit_parent

        app = getattr(self._owner.sb, "app", None) or QtWidgets.QApplication.instance()
        if app:
            active = app.activeWindow()
            if isinstance(active, QtWidgets.QWidget):
                return active

            for widget in app.topLevelWidgets():
                if (
                    isinstance(widget, QtWidgets.QWidget)
                    and widget.objectName() == "MayaWindow"
                ):
                    return widget

        parent_widget = self._owner.parentWidget()
        if isinstance(parent_widget, QtWidgets.QWidget):
            return parent_widget

        logical_parent = self._owner.parent()
        if isinstance(logical_parent, QtWidgets.QWidget):
            return logical_parent

        return self._owner

    def _build_sequence(self, key_value):
        if key_value is None:
            self._owner.logger.warning(
                "key_show is invalid; defaulting to F12 shortcut"
            )
            key_value = QtCore.Qt.Key_F12
            self._owner.key_show = key_value

        if isinstance(key_value, QtGui.QKeySequence):
            return key_value

        return QtGui.QKeySequence(key_value)

    def eventFilter(self, obj, event):
        if (
            self._key_is_down
            and event.type() == QtCore.QEvent.KeyRelease
            and event.key() == self._owner.key_show
            and not event.isAutoRepeat()
        ):
            self._on_key_release()
            return True
        return super().eventFilter(obj, event)

    def _on_key_press(self):
        if self._key_is_down:
            return
        self._key_is_down = True
        self._owner.key_show_press.emit()
        self._owner.show("hud#startmenu")
        QtCore.QTimer.singleShot(0, self._owner.hide_other_windows)

    def _on_key_release(self):
        if not self._key_is_down:
            return
        self._key_is_down = False
        self._owner.key_show_release.emit()
        self._owner.hide()
        QtCore.QTimer.singleShot(0, self._owner.show_other_windows)


class Tcl(
    QtWidgets.QStackedWidget, ptk.SingletonMixin, ptk.LoggingMixin, ptk.HelpMixin
):
    """Tcl is a marking menu based on a QStackedWidget.
    The various UI's are set by calling 'show' with the intended UI name string. ex. Tcl().show('polygons')

    Parameters:
        parent (QWidget): The parent application's top level window instance. ie. the Maya main window.
        key_show (str): The name of the key which, when pressed, will trigger the display of the marking menu. This should be one of the key names defined in QtCore.Qt. Defaults to 'Key_F12'.
        ui_source (str): The directory path or the module where the UI files are located.
                If the given dir is not a full path, it will be treated as relative to the default path.
                If a module is given, the path to that module will be used.
        slot_source (str): The directory path where the slot classes are located or a class object.
                If the given dir is a string and not a full path, it will be treated as relative to the default path.
                If a module is given, the path to that module will be used.
        log_level (int): Determines the level of logging messages. Defaults to logging.WARNING. Accepts standard Python logging module levels: DEBUG, INFO, WARNING, ERROR, CRITICAL.
    """

    left_mouse_double_click = QtCore.Signal()
    left_mouse_double_click_ctrl = QtCore.Signal()
    middle_mouse_double_click = QtCore.Signal()
    right_mouse_double_click = QtCore.Signal()
    right_mouse_double_click_ctrl = QtCore.Signal()
    key_show_press = QtCore.Signal()
    key_show_release = QtCore.Signal()

    _in_transition: bool = False
    _instances: dict = {}
    _submenu_cache: dict = {}
    _last_ui_history_check: QtWidgets.QWidget = None
    _pending_show_timer: QtCore.QTimer = None
    _shortcut_instance: Optional["ShortcutHandler"] = None

    def __init__(
        self,
        parent=None,
        key_show="F12",
        ui_source="ui",
        slot_source="slots",
        widget_source=None,
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
            parent=self,
            forward_events_to=self,
            event_name_prefix="child_",
            event_types={
                "Enter",
                "Leave",
                "MouseMove",
                "MouseButtonPress",
                "MouseButtonRelease",
            },
        )

        self.overlay = Overlay(self, antialiasing=True)
        self.mouse_tracking = MouseTracking(self)

        self.key_show = self.sb.convert.to_qkey(key_show)
        self.key_close = QtCore.Qt.Key_Escape
        self._windows_to_restore = set()

        self.setWindowFlags(QtCore.Qt.Window | QtCore.Qt.FramelessWindowHint)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setAttribute(QtCore.Qt.WA_NoMousePropagation, False)
        self.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.resize(600, 600)

        # Initialize smooth transition timer
        self._pending_show_timer = QtCore.QTimer()
        self._pending_show_timer.setSingleShot(True)
        self._pending_show_timer.timeout.connect(self._perform_transition)
        self._setup_complete = True

        # Auto-install shortcut if parent is provided
        if parent:
            ShortcutHandler.create(self, parent)

    def _init_ui(self, ui) -> None:
        """Initialize the given UI.

        Parameters:
            ui (QWidget): The UI to initialize.
        """
        if not isinstance(ui, QtWidgets.QWidget):
            raise ValueError(f"Invalid datatype: {type(ui)}, expected QWidget.")

        if ui.has_tags(["startmenu", "submenu"]):  # StackedWidget
            ui.style.set(theme="dark", style_class="translucentBgNoBorder")
            self.addWidget(ui)  # add the UI to the stackedLayout.

        else:  # MainWindow
            ui.setParent(self)
            ui.set_flags(Window=True, FramelessWindowHint=True)
            ui.set_attributes(WA_TranslucentBackground=True)
            ui.style.set(theme="dark")
            if hasattr(ui, "header") and not ui.header.has_buttons():
                ui.header.config_buttons("menu_button", "pin_button")
                self.key_show_release.connect(ui.hide)

        # set style before child init (resize).
        self.add_child_event_filter(ui.widgets)
        ui.on_child_registered.connect(lambda w: self.add_child_event_filter(w))

    def _prepare_ui(self, ui) -> QtWidgets.QWidget:
        """Initialize and set the UI without showing it."""
        if not isinstance(ui, (str, QtWidgets.QWidget)):
            raise ValueError(f"Invalid datatype for ui: {type(ui)}")

        found_ui = self.sb.get_ui(ui)

        if not found_ui.is_initialized:
            self._init_ui(found_ui)

        if found_ui.has_tags(["startmenu", "submenu"]):
            if found_ui.has_tags("startmenu"):
                self.move(self.sb.get_cursor_offset_from_center(self))
            self.setCurrentWidget(found_ui)
        else:
            self.hide()

        self.sb.current_ui = found_ui
        return found_ui

    def _show_ui(self) -> None:
        """Show the current UI appropriately, hiding Tcl if needed."""
        current = self.sb.current_ui

        is_stacked_ui = current.has_tags(["startmenu", "submenu"])

        if is_stacked_ui:
            # For stacked UIs (submenus), show with smooth timing
            super().show()
            self.activateWindow()
            self.raise_()
        else:
            self.show_other_windows()
            current.show()

            current.adjustSize()
            current.updateGeometry()
            self.sb.center_widget(current, "cursor", offset_y=25)

            current.raise_()
            current.activateWindow()

    def _set_submenu(self, ui, w) -> None:
        """Set the submenu for the given UI and widget."""
        if self._in_transition:
            self.logger.debug(
                f"_set_submenu: Transition in progress, skipping for {ui}"
            )
            return
        self._in_transition = True

        # Store transition data and schedule execution
        self._pending_transition_ui = ui
        self._pending_transition_widget = w
        self._pending_show_timer.start(8)  # ~120fps timing for very smooth transitions

    def _perform_transition(self) -> None:
        """Execute the scheduled submenu transition."""
        ui = getattr(self, "_pending_transition_ui", None)
        w = getattr(self, "_pending_transition_widget", None)

        # Clear pending references
        self._pending_transition_ui = None
        self._pending_transition_widget = None

        if not ui or not w:
            self._clear_transition_flag()
            return

        try:
            # Preserve overlay path order by adding to path first
            self.overlay.path.add(ui, w)

            # Batch UI initialization and preparation
            if not ui.is_initialized:
                self._init_ui(ui)
            self._prepare_ui(ui)

            # Position submenu smoothly without forcing immediate updates
            self._position_submenu_smooth(ui, w)

            self._show_ui()

            # Optimize history check and overlay cloning
            self._handle_overlay_cloning(ui)

        finally:
            # Clear transition flag after a brief delay to allow smooth completion
            QtCore.QTimer.singleShot(16, self._clear_transition_flag)  # ~60fps timing

    def _position_submenu_smooth(self, ui, w) -> None:
        """Handle submenu positioning with smooth visual transitions."""
        try:
            # Cache widget centers to avoid repeated calculations
            w_center = w.rect().center()
            p1 = w.mapToGlobal(w_center)

            w2 = self.sb.get_widget(w.objectName(), ui)
            if w2:
                w2.resize(w.size())
                w2_center = w2.rect().center()
                p2 = w2.mapToGlobal(w2_center)

                # Calculate new position
                new_pos = self.pos() + (p1 - p2)

                # Move to position smoothly - let Qt handle the timing naturally
                self.move(new_pos)

        except Exception as e:
            self.logger.warning(f"Submenu positioning failed: {e}")

    def _handle_overlay_cloning(self, ui) -> None:
        """Handle overlay cloning with optimized history checking."""
        # Optimize history check by avoiding expensive slice operations
        # Only check if this is a different UI than last time
        if ui != self._last_ui_history_check:
            ui_history_slice = self.sb.ui_history(slice(0, -1), allow_duplicates=True)
            if ui not in ui_history_slice:
                self.overlay.clone_widgets_along_path(ui, self._return_to_startmenu)
            self._last_ui_history_check = ui

    def _delayed_show_ui(self) -> None:
        """Show the UI after smooth positioning delay."""
        if hasattr(self, "_pending_ui"):
            current_ui = self.sb.current_ui
            if current_ui == self._pending_ui:
                self._show_ui()
            delattr(self, "_pending_ui")

    def _clear_transition_flag(self):
        """Clear the transition flag to allow new transitions."""
        self._in_transition = False

    def _return_to_startmenu(self) -> None:
        """Return to the start menu by moving the overlay path back to the start position."""
        start_pos = self.overlay.path.start_pos
        if not isinstance(start_pos, QtCore.QPoint):
            self.logger.warning("_return_to_startmenu called with no valid start_pos.")
            return

        startmenu = self.sb.ui_history(-1, inc="*#startmenu*")
        self._prepare_ui(startmenu)
        self.move(start_pos - self.rect().center())
        self._show_ui()

    # ---------------------------------------------------------------------------------------------
    #   Stacked Widget Event handling:

    def mousePressEvent(self, event) -> None:
        """ """
        if self.sb.current_ui.has_tags(["startmenu", "submenu"]):
            if not event.modifiers():
                if event.button() == QtCore.Qt.LeftButton:
                    self.show("cameras#startmenu")

                elif event.button() == QtCore.Qt.MiddleButton:
                    self.show("editors#startmenu")

                elif event.button() == QtCore.Qt.RightButton:
                    self.show("main#startmenu")

        super().mousePressEvent(event)

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

    def mouseReleaseEvent(self, event) -> None:
        """ """
        current_ui = self.sb.current_ui
        if current_ui and current_ui.has_tags(["startmenu", "submenu"]):
            widget = QtWidgets.QApplication.widgetAt(QtGui.QCursor.pos())
            if (
                widget
                and widget is not self
                and widget is not current_ui
                and widget is not getattr(self, "overlay", None)
            ):
                if not current_ui.isAncestorOf(widget):
                    super().mouseReleaseEvent(event)
                    return

            if self.isActiveWindow() and self.rect().contains(event.pos()):
                self.show("hud#startmenu", force=True)

        super().mouseReleaseEvent(event)

    def show(self, ui=None, force=False) -> None:
        """Show the Tcl UI with the specified name.

        Parameters:
            ui (str/QWidget): The name of the UI to show or a QWidget instance.
            force (bool): If True, forces the UI to show even if it is already visible.
        """
        if ui is None:
            ui = "hud#startmenu"

        ui = self._prepare_ui(ui)
        if not force and (QtWidgets.QApplication.mouseButtons() or self.isVisible()):
            return

        self._show_ui()

    def hide(self):
        """Override hide to properly reset stacked widget state."""
        # Reset the current widget index to -1 to ensure proper hide behavior
        if self.currentWidget():
            self.setCurrentIndex(-1)

        # Reset pinned state for all stacked UIs to ensure they can be hidden next time
        current_ui = self.sb.current_ui
        if current_ui and current_ui.has_tags(["startmenu", "submenu"]):
            header = getattr(current_ui, "header", None)
            if header:
                if hasattr(header, "reset_pin_state"):
                    header.reset_pin_state()
                elif getattr(header, "pinned", False):
                    header.pinned = False
                    if hasattr(current_ui, "prevent_hide"):
                        current_ui.prevent_hide = False

        super().hide()

    def hideEvent(self, event):
        """ """
        # Clear optimization caches on hide to prevent memory leaks
        self._clear_optimization_caches()

        super().hideEvent(event)

    def _clear_optimization_caches(self):
        """Clear optimization caches to prevent memory accumulation."""
        # Cancel any pending show operations
        if self._pending_show_timer and self._pending_show_timer.isActive():
            self._pending_show_timer.stop()
        if hasattr(self, "_pending_ui"):
            delattr(self, "_pending_ui")

        # Periodically clear the submenu cache to prevent excessive memory usage
        if len(self._submenu_cache) > 50:  # Reasonable threshold
            self._submenu_cache.clear()
        self._last_ui_history_check = None

    def hide_other_windows(self) -> None:
        """Hide all visible windows except the current one."""
        if not self.isVisible():
            return

        for win in self.sb.visible_windows:
            if win is not self and not win.has_tags(["startmenu", "submenu"]):
                self._windows_to_restore.add(win)
                win.header.hide_window()

        if self._windows_to_restore:
            self.logger.debug(f"Hiding other windows: {self._windows_to_restore}")

    def show_other_windows(self) -> None:
        """Show all previously hidden windows."""
        if not self._windows_to_restore:
            return

        for win in self._windows_to_restore:
            if win.isVisible():
                continue
            win.header.unhide_window()
        self._windows_to_restore.clear()
        self.logger.debug("Restored previously hidden windows.")

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
            try:  # If not correct type, skip it.
                if (w.derived_type not in filtered_types) or (
                    not w.ui.has_tags(["startmenu", "submenu"])
                ):
                    continue
            except AttributeError:  # Or not initialized yet.
                continue

            if w.derived_type in (
                QtWidgets.QPushButton,
                QtWidgets.QLabel,
                QtWidgets.QCheckBox,
                QtWidgets.QRadioButton,
            ):
                self.sb.center_widget(w, padding_x=25)
                if w.base_name() == "i":
                    w.ui.style.set(widget=w)

            if w.type == self.sb.registered_widgets.Region:
                w.visible_on_mouse_over = True

            self.child_event_filter.install(w)

    def child_enterEvent(self, w, event) -> None:
        """Handle the enter event for child widgets."""
        if w.derived_type == QtWidgets.QPushButton:
            if w.base_name() == "i":
                acc_name = w.accessibleName()
                if not acc_name:
                    self.logger.debug(
                        f"child_enterEvent: Button '{w.objectName()}' with base_name 'i' has no accessibleName; skipping submenu lookup."
                    )
                    return

                submenu_name = f"{acc_name}#submenu"
                if submenu_name != w.ui.objectName():
                    # Cache submenu lookups to avoid repeated sb.get_ui() calls
                    submenu = self._submenu_cache.get(submenu_name)
                    if submenu is None:
                        submenu = self.sb.get_ui(submenu_name)
                        if submenu:
                            self._submenu_cache[submenu_name] = submenu

                    if submenu:
                        self._set_submenu(submenu, w)

        if w.base_name() == "chk" and w.ui.has_tags("submenu") and self.isVisible():
            # Emit signal directly to ensure it triggers even when widget state changes
            if hasattr(w, "clicked"):
                w.clicked.emit()

        # Safe default: call original enterEvent
        if hasattr(w, "enterEvent"):
            super_event = getattr(super(type(w), w), "enterEvent", None)
            if callable(super_event):
                super_event(event)

    def child_leaveEvent(self, w, event) -> None:
        """Handle the leave event for child widgets."""
        if w.derived_type == QtWidgets.QPushButton:
            if self._pending_show_timer.isActive():
                self._pending_show_timer.stop()
                self._clear_transition_flag()
                self._pending_transition_ui = None
                self._pending_transition_widget = None

        # Safe default: call original leaveEvent
        if hasattr(w, "leaveEvent"):
            super_event = getattr(super(type(w), w), "leaveEvent", None)
            if callable(super_event):
                super_event(event)

    def child_mouseButtonReleaseEvent(self, w, event) -> bool:
        """Handle mouse button release events on child widgets.

        Note: Uses clicked.emit() instead of click() because Qt's click() method
        doesn't emit signals when widgets are hidden, and this menu hides itself
        before triggering widget callbacks.
        """
        if not w.underMouse():
            w.mouseReleaseEvent(event)
            return False

        # Resolve container clicks to actual child widget (fixes OptionBox button clicks)
        if w.derived_type == QtWidgets.QWidget:
            child = w.childAt(event.pos())
            if child:
                w = child

        # Handle pushbutton clicks
        if isinstance(w, QtWidgets.QPushButton):
            if hasattr(w, "base_name") and w.base_name() == "i":
                menu_name = w.accessibleName()
                if menu_name:
                    unknown_tags = self.sb.get_unknown_tags(
                        menu_name, known_tags=["submenu", "startmenu"]
                    )
                    new_menu_name = self.sb.edit_tags(menu_name, remove=unknown_tags)

                    menu = self._submenu_cache.get(new_menu_name)
                    if menu is None:
                        menu = self.sb.get_ui(new_menu_name)
                        if menu:
                            self._submenu_cache[new_menu_name] = menu

                    if menu:
                        self.sb.hide_unmatched_groupboxes(menu, unknown_tags)
                        self.show(menu)

        # Emit clicked signal directly (bypasses Qt visibility checks)
        if hasattr(w, "clicked"):
            self.hide()
            if w.ui.has_tags(["startmenu", "submenu"]) and w.base_name() != "chk":
                w.clicked.emit()

        w.mouseReleaseEvent(event)
        return True


# --------------------------------------------------------------------------------------------

if __name__ == "__main__":
    tcl = Tcl(slot_source="slots/maya")
    tcl.show("screen", app_exec=True)


# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
