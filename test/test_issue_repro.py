import sys
import os
import unittest
from unittest.mock import MagicMock, patch

# Ensure paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# test -> tentacle (repo) -> ...
REPO_ROOT = os.path.dirname(SCRIPT_DIR)
if REPO_ROOT not in sys.path:
    sys.path.append(REPO_ROOT)

from qtpy import QtWidgets, QtCore, QtGui

# Mock modules that might not be present or need bypassing
ptk = MagicMock()


class MockSingleton:
    pass


class MockLogging:
    def __init__(self):
        self.logger = MagicMock()

    @property
    def logger(self):
        if not hasattr(self, "_logger"):
            self._logger = MagicMock()
        return self._logger


class MockHelp:
    pass


ptk.SingletonMixin = MockSingleton
ptk.LoggingMixin = MockLogging
ptk.HelpMixin = MockHelp

ptk.core_utils = MagicMock()
ptk.core_utils.module_resolver = MagicMock()
sys.modules["pythontk"] = ptk
sys.modules["pythontk.core_utils"] = ptk.core_utils
sys.modules["pythontk.core_utils.module_resolver"] = ptk.core_utils.module_resolver

sys.modules["uitk.switchboard"] = MagicMock()
sys.modules["uitk.events"] = MagicMock()
sys.modules["tentacle.overlay"] = MagicMock()

# Now import Tcl
from tentacle import tcl

# Re-import to ensure mocks are used if it was already imported
import importlib

try:
    importlib.reload(tcl)
except Exception:
    pass


class TestTclGhosting(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not QtWidgets.QApplication.instance():
            cls.app = QtWidgets.QApplication(sys.argv)
        else:
            cls.app = QtWidgets.QApplication.instance()

    def setUp(self):
        # Mock Switchboard behavior
        self.mock_sb = MagicMock()

        # Patch Switchboard in Tcl class
        self.patcher = patch("tentacle.tcl.Switchboard", return_value=self.mock_sb)
        self.patcher.start()

        # Initialize Tcl
        self.tcl = tcl.Tcl()

        # Create a mock Stacked UI
        self.mock_ui = QtWidgets.QWidget()
        self.mock_ui.objectName = MagicMock(return_value="hud#startmenu")
        self.mock_ui.has_tags = MagicMock(return_value=True)  # Tagged as startmenu
        self.mock_ui.isAncestorOf = MagicMock(return_value=True)  # acts as container

        # Create a Button inside the UI (Interactive widget)
        self.btn = QtWidgets.QPushButton(self.mock_ui)
        self.btn.setGeometry(10, 10, 100, 30)
        self.btn.clicked = MagicMock()
        self.btn.base_name = MagicMock(return_value="btn")
        # Mock underMouse to bypass check
        self.btn.underMouse = MagicMock(return_value=True)
        # Mock ui attribute
        self.btn.ui = MagicMock()
        self.btn.ui.has_tags = MagicMock(return_value=True)

        # Setup Tcl state
        self.tcl.sb.current_ui = self.mock_ui
        self.tcl.sb.get_ui.return_value = self.mock_ui
        self.tcl.isVisible = MagicMock(return_value=True)
        self.tcl.mouseGrabber = MagicMock(
            return_value=None
        )  # Simulate NOT grabbing (Click mode)
        self.tcl.mapFromGlobal = MagicMock(return_value=QtCore.QPoint(50, 50))
        self.tcl.releaseMouse = MagicMock()
        self.tcl.hide = MagicMock()
        self.tcl.show = MagicMock()

    def tearDown(self):
        self.patcher.stop()
        self.tcl.deleteLater()

    def test_mouse_release_on_button_prevents_ghosting(self):
        """
        Test that releasing the mouse over a button:
        1. Actuates the button (emit clicked)
        2. Hides the Tcl window
        3. DOES NOT trigger the fallback show() (ghosting)
        """

        # Setup specific button behavior for this test
        # We need isAncestorOf to return True for the button
        self.mock_ui.isAncestorOf = lambda w: w == self.btn or w == self.mock_ui

        # Mock QApplication.widgetAt to return our button
        # We simulate the cursor being over the button
        with patch.object(QtWidgets.QApplication, "widgetAt", return_value=self.btn):
            with patch.object(QtGui.QCursor, "pos", return_value=QtCore.QPoint(20, 20)):

                # Create the event
                event = QtGui.QMouseEvent(
                    QtCore.QEvent.MouseButtonRelease,
                    QtCore.QPointF(20, 20),
                    QtCore.Qt.LeftButton,
                    QtCore.Qt.LeftButton,
                    QtCore.Qt.NoModifier,
                )

                # Mock rect contains to True (simulating fallback condition is met IF logic fails)
                self.tcl.rect = MagicMock(return_value=QtCore.QRect(0, 0, 1000, 1000))
                self.tcl.isActiveWindow = MagicMock(return_value=True)

                # --- EXECUTE ---
                self.tcl.mouseReleaseEvent(event)

                # --- ASSERTIONS ---

                # 1. Check direct actuation
                self.btn.clicked.emit.assert_called_once()
                print("SUCCESS: Button was clicked.")

                # 2. Check Hide was called
                self.tcl.hide.assert_called_once()
                print("SUCCESS: Tcl.hide() was called.")

                # 3. Check Show was NOT called (The Core Issue)
                self.tcl.show.assert_not_called()
                print("SUCCESS: Tcl.show() was NOT called (No Ghosting).")

    def test_mouse_release_on_info_button_shows_submenu(self):
        """
        Test that releasing on an 'i' button:
        1. Shows submenu
        2. Does NOT Hide
        3. Does NOT manual emit clicked
        """
        # Create Info Button
        btn_i = QtWidgets.QPushButton(self.mock_ui)
        btn_i.underMouse = MagicMock(return_value=True)
        btn_i.base_name = MagicMock(return_value="i")
        btn_i.clicked = MagicMock()
        btn_i.accessibleName = MagicMock(return_value="submenu_A")

        # Mock finding this button
        self.mock_ui.isAncestorOf = lambda w: w == btn_i or w == self.mock_ui

        # Reset mocks
        self.tcl.show.reset_mock()
        self.tcl.hide.reset_mock()

        # Use child_mouseButtonReleaseEvent directly as that's where the logic lives for eventFilter
        with patch.object(QtWidgets.QApplication, "widgetAt", return_value=btn_i):
            event = QtGui.QMouseEvent(
                QtCore.QEvent.MouseButtonRelease,
                QtCore.QPointF(0, 0),
                QtCore.Qt.LeftButton,
                QtCore.Qt.LeftButton,
                QtCore.Qt.NoModifier,
            )

            # We need submenu to resolve
            self.mock_sb.get_unknown_tags.return_value = []
            self.mock_sb.edit_tags.return_value = "submenu_A"
            self.mock_sb.get_ui.return_value = MagicMock()  # Return a menu widget

            self.tcl.child_mouseButtonReleaseEvent(btn_i, event)

            # Assertions
            self.tcl.show.assert_called()
            print("SUCCESS: Tcl.show() was called for 'i' button.")

            self.tcl.hide.assert_not_called()
            print("SUCCESS: Tcl.hide() was NOT called for 'i' button.")

            btn_i.clicked.emit.assert_not_called()
            print("SUCCESS: Clicked not manually emitted.")

    def test_child_release_on_action_button(self):
        """Test child_mouseButtonReleaseEvent for Action button to ensure separate logic works there too."""
        # Reset mocks
        self.tcl.show.reset_mock()
        self.tcl.hide.reset_mock()
        self.btn.clicked.emit.reset_mock()

        event = QtGui.QMouseEvent(
            QtCore.QEvent.MouseButtonRelease,
            QtCore.QPointF(0, 0),
            QtCore.Qt.LeftButton,
            QtCore.Qt.LeftButton,
            QtCore.Qt.NoModifier,
        )

        self.tcl.child_mouseButtonReleaseEvent(self.btn, event)

        self.tcl.hide.assert_called_once()
        print("SUCCESS: Child Action: Tcl.hide() called.")

        self.btn.clicked.emit.assert_called_once()
        print("SUCCESS: Child Action: clicked emitted.")

        self.tcl.show.assert_not_called()
        print("SUCCESS: Child Action: Tcl.show() not called.")


if __name__ == "__main__":
    unittest.main()
