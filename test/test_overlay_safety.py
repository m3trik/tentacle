import unittest
from qtpy import QtWidgets, QtCore
from unittest.mock import MagicMock, patch
from tentacle.overlay import Overlay, Path


class TestOverlayPathSafety(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def setUp(self):
        self.overlay = Overlay(parent=None)
        # Mock Tcl parent-like structure if needed, or overlay standalone
        # clone_widgets relies on self.path.start_pos

    def tearDown(self):
        self.overlay.deleteLater()

    def test_clone_widgets_recovers_from_empty_path(self):
        """Test that clone_widgets_along_path triggers start_gesture if path is empty."""
        # Ensure path is empty
        self.overlay.path.clear()
        self.assertIsNone(self.overlay.path.start_pos)

        # Mock start_gesture to verify call
        self.overlay.start_gesture = MagicMock(wraps=self.overlay.start_gesture)

        # Mock init_region to avoid UI complexities
        self.overlay.init_region = MagicMock()
        mock_region = MagicMock()
        self.overlay.init_region.return_value = mock_region

        # Mock UI
        ui = QtWidgets.QWidget()

        # Call function
        self.overlay.clone_widgets_along_path(ui, MagicMock())

        # Verify recovery
        self.overlay.start_gesture.assert_called_once()
        self.assertIsNotNone(self.overlay.path.start_pos)
