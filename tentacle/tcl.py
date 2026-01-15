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

        # Use consolidated button detection
        active_button = self._owner._detect_active_button()

        # Dismiss external popups (e.g., Maya's native marking menus)
        # Pass the active button so a synthetic release can be sent
        self._owner._dismiss_external_popups(active_button)

        menu_name = self._owner.get_menu_name(active_button)
        self._owner.show(menu_name, force=True)
        QtCore.QTimer.singleShot(0, self._owner.dim_other_windows)

    def _on_key_release(self):
        if not self._key_is_down:
            return
        self._key_is_down = False
        self._owner.key_show_release.emit()
        self._owner.hide()
        QtCore.QTimer.singleShot(0, self._owner.restore_other_windows)


class Tcl(QtWidgets.QWidget, ptk.SingletonMixin, ptk.LoggingMixin, ptk.HelpMixin):
    """Tcl is a marking menu based on a QWidget.
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

    # Single source of truth for button→menu mapping
    # Combo (Left+Right) is checked first, then individual buttons (priority: R > M > L)
    # Set combo value to None to disable, or a menu name like "tools#startmenu" to enable
    BUTTON_MENU_MAP = {
        QtCore.Qt.LeftButton
        | QtCore.Qt.RightButton: None,  # Left+Right combo (disabled)
        QtCore.Qt.RightButton: "main#startmenu",
        QtCore.Qt.MiddleButton: "editors#startmenu",
        QtCore.Qt.LeftButton: "cameras#startmenu",
        None: "hud#startmenu",
    }

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
    _current_widget: Optional[QtWidgets.QWidget] = None

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
        self.mouse_tracking = MouseTracking(self, auto_update=False)

        self.key_show = self.sb.convert.to_qkey(key_show)
        self.key_close = QtCore.Qt.Key_Escape
        self._windows_to_restore = set()

        self.setWindowFlags(QtCore.Qt.Window | QtCore.Qt.FramelessWindowHint)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setAttribute(QtCore.Qt.WA_NoMousePropagation, False)
        self.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.showFullScreen()

        # Initialize smooth transition timer
        self._pending_show_timer = QtCore.QTimer()
        self._pending_show_timer.setSingleShot(True)
        self._pending_show_timer.timeout.connect(self._perform_transition)
        self._setup_complete = True

        # Auto-install shortcut if parent is provided
        if parent:
            ShortcutHandler.create(self, parent)

    def addWidget(self, widget: QtWidgets.QWidget) -> None:
        """Add a widget to the Tcl window.

        Parameters:
            widget (QWidget): The widget to add.
        """
        widget.setParent(self)

    def currentWidget(self) -> Optional[QtWidgets.QWidget]:
        """Get the currently active widget.

        Returns:
            QWidget: The currently active widget, or None if no widget is active.
        """
        return self._current_widget

    def setCurrentWidget(self, widget: QtWidgets.QWidget) -> None:
        """Set the current widget and position it at the cursor.

        Parameters:
            widget (QWidget): The widget to set as current.
        """
        if self._current_widget:
            self._current_widget.hide()

        self._current_widget = widget
        widget.show()
        widget.raise_()

        # Position the widget at the cursor
        cursor_pos = QtGui.QCursor.pos()
        local_pos = self.mapFromGlobal(cursor_pos)
        widget.move(local_pos - widget.rect().center())

        # Update mouse tracking cache for the new widget
        if hasattr(self, "mouse_tracking"):
            self.mouse_tracking.update_child_widgets()

    def setCurrentIndex(self, index: int) -> None:
        """Set the current widget index (compatibility method).

        Parameters:
            index (int): The index to set. If -1, hides the current widget.
        """
        if index == -1 and self._current_widget:
            self._current_widget.hide()
            self._current_widget = None

    def _init_ui(self, ui) -> None:
        """Initialize the given UI.

        Parameters:
            ui (QWidget): The UI to initialize.
        """
        if not isinstance(ui, QtWidgets.QWidget):
            raise ValueError(f"Invalid datatype: {type(ui)}, expected QWidget.")

        if ui.has_tags(["startmenu", "submenu"]):  # StackedWidget
            ui.style.set(theme="dark", style_class="translucentBgNoBorder")
            ui.resize(600, 600)
            ui.ensure_on_screen = False
            self.addWidget(ui)  # add the UI to the stackedLayout.
            self.add_child_event_filter(ui.widgets)
            ui.on_child_registered.connect(lambda w: self.add_child_event_filter(w))

        else:  # MainWindow
            ui.setParent(self)
            ui.set_flags(Window=True, FramelessWindowHint=True)
            ui.set_attributes(WA_TranslucentBackground=True)
            ui.style.set(theme="dark")
            if hasattr(ui, "header") and not ui.header.has_buttons():
                ui.header.config_buttons("menu", "collapse", "pin")
                self.key_show_release.connect(ui.hide)

            ui.default_slot_timeout = 360.0

    def _prepare_ui(self, ui) -> QtWidgets.QWidget:
        """Initialize and set the UI without showing it."""
        if not isinstance(ui, (str, QtWidgets.QWidget)):
            raise ValueError(f"Invalid datatype for ui: {type(ui)}")

        found_ui = self.sb.get_ui(ui)

        if not found_ui.is_initialized:
            self._init_ui(found_ui)

        if found_ui.has_tags(["startmenu", "submenu"]):
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

            self.raise_()
            self.activateWindow()
        else:
            self.restore_other_windows()
            current.show()

            # Position the widget at the cursor (handling parent coordinates)
            cursor_pos = QtGui.QCursor.pos()
            local_pos = self.mapFromGlobal(cursor_pos)
            offset = QtCore.QPoint(0, int(current.height() * 0.25))
            current.move(local_pos - current.rect().center() + offset)

            current.raise_()
            # current.activateWindow()

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

            # Update mouse tracking to include newly cloned widgets
            if hasattr(self, "mouse_tracking"):
                self.mouse_tracking.update_child_widgets()

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
                diff = p1 - p2

                # Move to position smoothly - let Qt handle the timing naturally
                ui.move(ui.pos() + diff)

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

        local_pos = self.mapFromGlobal(start_pos)
        startmenu.move(local_pos - startmenu.rect().center())

        self._show_ui()

    # ---------------------------------------------------------------------------------------------
    #   Menu Navigation Helpers:

    @property
    def is_stacked_ui(self) -> bool:
        """Check if current UI is a stacked menu (startmenu/submenu)."""
        ui = self.sb.current_ui
        return ui is not None and ui.has_tags(["startmenu", "submenu"])

    def get_menu_name(self, button: QtCore.Qt.MouseButton = None) -> str:
        """Return the menu name corresponding to the given mouse button.

        Parameters:
            button: The mouse button (LeftButton, MiddleButton, RightButton, or None).

        Returns:
            The menu name string (e.g., 'main#startmenu', 'hud#startmenu'),
            or None if the combo is disabled.
        """
        menu = self.BUTTON_MENU_MAP.get(button)
        if menu is None and button is not None:
            # Combo is disabled or not mapped, fall back to HUD
            menu = self.BUTTON_MENU_MAP[None]
        return menu

    def _detect_active_button(self) -> QtCore.Qt.MouseButton:
        """Detect which mouse button(s) are currently held.

        Returns combined flags for Left+Right combo, otherwise single button (priority: R > M > L).
        """
        held = QtWidgets.QApplication.mouseButtons()
        # Check Left+Right combo first
        if (held & QtCore.Qt.LeftButton) and (held & QtCore.Qt.RightButton):
            return QtCore.Qt.LeftButton | QtCore.Qt.RightButton
        if held & QtCore.Qt.RightButton:
            return QtCore.Qt.RightButton
        elif held & QtCore.Qt.MiddleButton:
            return QtCore.Qt.MiddleButton
        elif held & QtCore.Qt.LeftButton:
            return QtCore.Qt.LeftButton
        return None

    def _acquire_mouse_grab(self) -> None:
        """Grab mouse if not already grabbed by self."""
        if self.mouseGrabber() != self:
            self.grabMouse()

    def _release_mouse_grab(self) -> None:
        """Release mouse grab if held by self."""
        if self.mouseGrabber() == self:
            self.releaseMouse()

    def _begin_gesture(self, active_button=None) -> None:
        """Single entry point for starting a navigation gesture.

        Handles: dismissing external popups, starting overlay gesture,
        and acquiring mouse grab if buttons are held.
        """
        self._dismiss_external_popups(active_button)
        if hasattr(self, "overlay"):
            self.overlay.start_gesture(QtGui.QCursor.pos())
        if QtWidgets.QApplication.mouseButtons() != QtCore.Qt.NoButton:
            self._acquire_mouse_grab()

    def _dismiss_external_popups(self, active_button=None) -> None:
        """Dismiss any active popup widgets that are not children of Tcl.

        This is called before showing Tcl to close external menus that would
        otherwise conflict with the overlay's event handling.

        Parameters:
            active_button: The mouse button currently held (if any). If provided,
                          a synthetic release is sent to dismiss non-Qt popups.
        """
        # First, try closing Qt popup widgets
        popup = QtWidgets.QApplication.activePopupWidget()
        while popup is not None:
            # Don't close our own popups
            if self.isAncestorOf(popup):
                break
            popup.close()
            # Check for nested popups
            popup = QtWidgets.QApplication.activePopupWidget()

        # For non-Qt popups (native context menus, etc.), send a synthetic
        # mouse release to the widget under cursor to dismiss them
        if active_button is not None:
            cursor_pos = QtGui.QCursor.pos()
            target_widget = QtWidgets.QApplication.widgetAt(cursor_pos)
            if target_widget and target_widget is not self:
                local_pos = target_widget.mapFromGlobal(cursor_pos)
                release_event = QtGui.QMouseEvent(
                    QtCore.QEvent.MouseButtonRelease,
                    QtCore.QPointF(local_pos),
                    QtCore.QPointF(cursor_pos),
                    active_button,
                    QtCore.Qt.NoButton,  # No buttons held after release
                    QtWidgets.QApplication.keyboardModifiers(),
                )
                QtWidgets.QApplication.postEvent(target_widget, release_event)

    # ---------------------------------------------------------------------------------------------
    #   Stacked Widget Event handling:

    def mousePressEvent(self, event) -> None:
        """Handle mouse press to switch menus based on button(s)."""
        if self.is_stacked_ui:
            if not event.modifiers():
                # Detect all held buttons (including the one just pressed)
                active = self._detect_active_button()
                if active in self.BUTTON_MENU_MAP:
                    # Force=True to allow fast menu switching while visible
                    self.show(self.get_menu_name(active), force=True)

        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:
        """Handle double-click events to emit custom signals."""
        if self.is_stacked_ui:
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
        """Handle mouse release, releasing any mouse grab and processing the event."""
        self._release_mouse_grab()

        if self.is_stacked_ui:
            current_ui = self.sb.current_ui
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
                # Check what buttons remain held after this release
                remaining = self._detect_active_button()
                menu_name = self.get_menu_name(remaining)  # Returns HUD if None
                self.show(menu_name, force=True)

        super().mouseReleaseEvent(event)

    def show(self, ui=None, force=False) -> None:
        """Show the Tcl UI with the specified name.

        Parameters:
            ui (str/QWidget): The name of the UI to show or a QWidget instance.
            force (bool): If True, forces the UI to show even if it is already visible.
        """
        if ui is None:
            ui = self.BUTTON_MENU_MAP[None]

        ui = self._prepare_ui(ui)
        if not force and (QtWidgets.QApplication.mouseButtons() or self.isVisible()):
            return

        # Begin gesture for startmenu UIs (handles popups, cursor, grab)
        if ui.has_tags("startmenu"):
            self._begin_gesture()
        else:
            self._handle_overlay_cloning(ui)

        self._show_ui()

    def hide(self):
        """Override hide to properly reset stacked widget state."""
        self._release_mouse_grab()

        if self.currentWidget():
            self.setCurrentIndex(-1)

        # Reset pinned state for stacked UIs
        if self.is_stacked_ui:
            current_ui = self.sb.current_ui
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

    def dim_other_windows(self) -> None:
        """Dim all visible windows except the current one."""
        if not self.isVisible():
            return

        for win in self.sb.visible_windows:
            if win is not self and not win.has_tags(["startmenu", "submenu"]):
                self._windows_to_restore.add(win)
                win.setWindowOpacity(0.15)
                win.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents, True)

        if self._windows_to_restore:
            self.logger.debug(f"Dimming other windows: {self._windows_to_restore}")

    def restore_other_windows(self) -> None:
        """Restore all previously dimmed windows."""
        if not self._windows_to_restore:
            return

        for win in self._windows_to_restore:
            win.setWindowOpacity(1.0)
            win.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents, False)
        self._windows_to_restore.clear()
        self.logger.debug("Restored previously dimmed windows.")

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
            if hasattr(w, "toggle"):
                w.toggle()

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
