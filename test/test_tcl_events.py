import unittest
from qtpy import QtWidgets, QtCore, QtGui
from tentacle.tcl import Tcl, ShortcutHandler
from unittest.mock import MagicMock, patch


class TestTclEvents(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Create app if not exists
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def setUp(self):
        # Mock Switchboard to avoid loading config files
        self.sb_patcher = patch("tentacle.tcl.Switchboard")
        self.MockSB = self.sb_patcher.start()
        self.mock_sb_instance = self.MockSB.return_value
        self.mock_sb_instance.convert.to_qkey.side_effect = lambda x: x

        # Setup Tcl
        self.tcl = Tcl(parent=None)

        # Setup a mock UI widget that "has_tags"
        self.mock_ui = QtWidgets.QWidget()
        self.mock_ui.has_tags = lambda tags: "startmenu" in tags or "submenu" in tags
        self.mock_ui.objectName = lambda: "mock_ui"

        # Tcl setup
        self.tcl.sb.current_ui = self.mock_ui

    def tearDown(self):
        self.tcl.deleteLater()
        self.mock_ui.deleteLater()
        self.sb_patcher.stop()

    def test_button_release_emits_clicked(self):
        """Verify that releasing mouse on a button emits clicked and hides Tcl."""
        # Use MagicMock for button to control behaviors like underMouse and attributes
        btn = MagicMock()
        btn.underMouse.return_value = True
        # derived_type needed for logic branching
        btn.derived_type = QtWidgets.QPushButton
        btn.base_name.return_value = "b001"
        btn.ui = self.mock_ui

        # Ensure 'clicked' exists and is a mock
        btn.clicked = MagicMock()

        # Event can be mocked too
        event = MagicMock()

        # Ensure current_ui is set on the mock SB
        self.tcl.sb.current_ui = self.mock_ui

        # Call handler
        result = self.tcl.child_mouseButtonReleaseEvent(btn, event)

        # Expectation:
        self.assertTrue(result, "Event handler should return True")

        # Check if emit was called
        btn.clicked.emit.assert_called_once()

    def test_get_menu_name(self):
        """Test get_menu_name logic mapping buttons to menus."""
        self.assertEqual(
            self.tcl.get_menu_name(QtCore.Qt.LeftButton), "cameras#startmenu"
        )
        self.assertEqual(
            self.tcl.get_menu_name(QtCore.Qt.MiddleButton), "editors#startmenu"
        )
        self.assertEqual(
            self.tcl.get_menu_name(QtCore.Qt.RightButton), "main#startmenu"
        )
        # Global fallback (no button pressed)
        with patch(
            "qtpy.QtWidgets.QApplication.mouseButtons", return_value=QtCore.Qt.NoButton
        ):
            self.assertEqual(self.tcl.get_menu_name(), "hud#startmenu")

    @patch("qtpy.QtWidgets.QApplication.mouseButtons")
    def test_hotkey_force_show_with_context(self, mock_mouseButtons):
        """Test hotkey forces show with correct menu context."""
        mock_mouseButtons.return_value = QtCore.Qt.RightButton

        # Mock show to verify call
        self.tcl.show = MagicMock()

        handler = ShortcutHandler(self.tcl)

        with (
            patch("qtpy.QtWidgets.QApplication.widgetAt", return_value=self.tcl),
            patch("qtpy.QtWidgets.QApplication.postEvent") as mock_postInfo,
        ):

            handler._on_key_press()

            # Verify show call
            # With RightButton held, get_menu_name returns 'main#startmenu'
            self.tcl.show.assert_called_once_with("main#startmenu", force=True)

    def test_show_triggers_overlay_gesture(self):
        """Test that show() calls overlay.start_gesture() when a startmenu is loaded."""
        # Mock overlay
        self.tcl.overlay = MagicMock()

        # Mock internal methods to isolate show logic
        mock_ui = MagicMock()
        # Ensure has_tags returns True for "startmenu"
        mock_ui.has_tags.side_effect = lambda tag: tag == "startmenu"

        self.tcl._prepare_ui = MagicMock(return_value=mock_ui)
        self.tcl._show_ui = MagicMock()

        # force=True to bypass visibility checks
        self.tcl.show("some_ui", force=True)

        # Verify start_gesture called with a QPoint
        self.tcl.overlay.start_gesture.assert_called_once()
        args, _ = self.tcl.overlay.start_gesture.call_args
        self.assertIsInstance(args[0], QtCore.QPoint)

    def test_show_does_not_trigger_overlay_for_non_startmenu(self):
        """Test that show() does NOT call start_gesture for non-startmenu UIs."""
        # Mock overlay
        self.tcl.overlay = MagicMock()
        self.tcl._handle_overlay_cloning = MagicMock()

        # Mock internal methods
        mock_ui = MagicMock()
        # Ensure has_tags returns False
        mock_ui.has_tags.return_value = False

        self.tcl._prepare_ui = MagicMock(return_value=mock_ui)
        self.tcl._show_ui = MagicMock()

        # force=True
        self.tcl.show("other_ui", force=True)

        # Verify start_gesture NOT called
        self.tcl.overlay.start_gesture.assert_not_called()
        # Verify cloning called instead
        self.tcl._handle_overlay_cloning.assert_called_once_with(mock_ui)
