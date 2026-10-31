#!/usr/bin/python
# coding=utf-8
"""
Tests for the standalone Map Converter panel (``slots/tools/converter.py``).

Its batch rules are extapps' ``MapConverter`` (``extapps/test/test_converter.py``).
The panel reports through its logger and the engine through ``print``, so a run's
report is read from both (:class:`_Reported`).

Tests cover:
- TextureMapFactory integration in tb001 (Spec/Gloss conversion)
- New b012 method for batch PBR workflow preparation
- All 7 workflow templates
- Error handling and fallback behavior
"""
import io
import logging
import os
import contextlib
import tempfile
import shutil
import unittest
from unittest.mock import Mock, MagicMock, patch
from PIL import Image

from pythontk import ImgUtils, FileUtils
from pythontk.core_utils.engines.textures.map_factory import MapFactory as TextureMapFactory
from pythontk.core_utils.engines.textures.map_registry import MapRegistry, WF

from tentacle.slots.tools.converter import ConverterSlots

# Check if Qt (PySide6/PyQt) is available via qtpy (for b012 tests)
try:
    from qtpy import QtWidgets  # noqa: F401

    QT_AVAILABLE = True
except Exception:
    QT_AVAILABLE = False

skip_if_no_qt = unittest.skipUnless(
    QT_AVAILABLE, "Qt not available - b012 tests require QInputDialog"
)


class _Reported:
    """What a panel run reports: the engine's prints and the panel's own log lines.

    ``getvalue()`` is both, prints first; the cases read it for substrings and
    for the line a marker starts.
    """

    def __init__(self, logger):
        self._logger, self._lines = logger, []
        self._stdout = contextlib.redirect_stdout(io.StringIO())

    def __enter__(self):
        self._buffer = self._stdout.__enter__()
        self._handler = logging.Handler()
        self._handler.emit = lambda record: self._lines.append(record.getMessage())
        self._logger.addHandler(self._handler)
        return self

    def __exit__(self, *exc):
        self._logger.removeHandler(self._handler)
        return self._stdout.__exit__(*exc)

    def getvalue(self):
        return "\n".join([self._buffer.getvalue()] + self._lines)


class TestMapConverterTextureFactory(unittest.TestCase):
    """Test MapConverter integration with TextureMapFactory."""

    @classmethod
    def setUpClass(cls):
        """Set up test fixtures once for all tests."""
        # Create temporary directory for test outputs
        cls.test_dir = tempfile.mkdtemp(prefix="converter_test_")
        cls.test_files_dir = os.path.join(cls.test_dir, "textures")
        os.makedirs(cls.test_files_dir, exist_ok=True)

        # Create sample texture files for testing
        cls._create_test_textures()

    @classmethod
    def tearDownClass(cls):
        """Clean up test directory after all tests."""
        if os.path.exists(cls.test_dir):
            shutil.rmtree(cls.test_dir)

    @classmethod
    def _create_test_textures(cls):
        """Create sample texture files for testing."""
        # Define test texture set
        cls.test_textures = {
            "Base_Color": "material_BaseColor.png",
            "Metallic": "material_Metallic.png",
            "Roughness": "material_Roughness.png",
            "Normal_OpenGL": "material_Normal_OpenGL.png",
            "Ambient_Occlusion": "material_AO.png",
            "Opacity": "material_Opacity.png",
            "Specular": "material_Specular.png",
            "Glossiness": "material_Glossiness.png",
            "Diffuse": "material_Diffuse.png",
        }

        # Create actual image files
        cls.texture_paths = []
        for map_type, filename in cls.test_textures.items():
            filepath = os.path.join(cls.test_files_dir, filename)

            # Create appropriate test images based on type
            if "Normal" in map_type:
                img = ImgUtils.create_image("RGB", (512, 512), (128, 128, 255))
            elif map_type in ["Metallic", "Roughness", "AO", "Opacity", "Glossiness"]:
                img = ImgUtils.create_image("L", (512, 512), 128)
            else:
                img = ImgUtils.create_image("RGB", (512, 512), (128, 128, 128))

            ImgUtils.save_image(img, filepath)
            cls.texture_paths.append(filepath)

    def setUp(self):
        """Set up test fixtures for each test."""
        # Create mock switchboard
        self.mock_sb = Mock()
        self.mock_sb.file_dialog = Mock(return_value=None)

        # Create ConverterSlots instance
        self.converter = ConverterSlots(self.mock_sb)

        # Mock UI components
        self.mock_widget = Mock()
        self.mock_widget.option_box.menu = Mock()
        self.mock_widget.option_box.menu.chk000 = Mock()
        self.mock_widget.option_box.menu.chk000.isChecked = Mock(return_value=False)

    # -------------------------------------------------------------------------
    # Test tb001 with TextureMapFactory Integration
    # -------------------------------------------------------------------------

    def test_tb001_spec_gloss_conversion_basic(self):
        """Test tb001 Spec/Gloss conversion using TextureMapFactory."""
        # Setup file dialog mock to return spec/gloss textures
        spec_gloss_textures = [
            os.path.join(self.test_files_dir, "material_Specular.png"),
            os.path.join(self.test_files_dir, "material_Glossiness.png"),
            os.path.join(self.test_files_dir, "material_Diffuse.png"),
        ]
        self.mock_sb.file_dialog.return_value = spec_gloss_textures

        # Run conversion
        self.converter.tb001(self.mock_widget)

        # Verify file dialog was called
        self.mock_sb.file_dialog.assert_called_once()

        # Check that processed files exist (TextureMapFactory should create outputs)
        # Note: Actual output verification depends on TextureMapFactory implementation

    def test_tb001_with_metallic_smoothness_packing(self):
        """Test tb001 with metallic smoothness packing enabled."""
        spec_gloss_textures = [
            os.path.join(self.test_files_dir, "material_Specular.png"),
            os.path.join(self.test_files_dir, "material_Glossiness.png"),
        ]
        self.mock_sb.file_dialog.return_value = spec_gloss_textures
        self.mock_widget.option_box.menu.chk000.isChecked.return_value = True

        # Run conversion with packing enabled
        self.converter.tb001(self.mock_widget)

        # Verify checkbox was checked
        self.mock_widget.option_box.menu.chk000.isChecked.assert_called()

    def test_tb001_empty_selection(self):
        """Test tb001 handles empty file selection."""
        self.mock_sb.file_dialog.return_value = None

        # Should return early without error
        result = self.converter.tb001(self.mock_widget)

        # Verify it returns None (early exit)
        self.assertIsNone(result)

    def test_tb001_multiple_texture_sets(self):
        """Test tb001 processes multiple texture sets."""
        # Create second texture set
        set2_textures = []
        for map_type, filename in [
            ("Specular", "model2_Specular.png"),
            ("Glossiness", "model2_Glossiness.png"),
        ]:
            filepath = os.path.join(self.test_files_dir, filename)
            img = ImgUtils.create_image("L", (512, 512), 128)
            ImgUtils.save_image(img, filepath)
            set2_textures.append(filepath)

        all_textures = [
            os.path.join(self.test_files_dir, "material_Specular.png"),
            os.path.join(self.test_files_dir, "material_Glossiness.png"),
        ] + set2_textures

        self.mock_sb.file_dialog.return_value = all_textures

        # Run conversion
        self.converter.tb001(self.mock_widget)

        # Should process both sets without error

    def test_tb001_fallback_on_factory_error(self):
        """Test tb001 falls back to legacy method if TextureMapFactory fails."""
        spec_textures = [
            os.path.join(self.test_files_dir, "material_Specular.png"),
        ]
        self.mock_sb.file_dialog.return_value = spec_textures

        # Mock MapFactory to raise exception
        with patch(
            "tentacle.slots.tools.converter.MapFactory.prepare_maps",
            side_effect=Exception("Factory error"),
        ):
            # Should fall back to legacy method without crashing
            self.converter.tb001(self.mock_widget)

    # -------------------------------------------------------------------------
    # Test b012 - Batch PBR Workflow Preparation
    # -------------------------------------------------------------------------

    @skip_if_no_qt
    @patch("qtpy.QtWidgets.QInputDialog.getItem")
    def test_b012_standard_pbr_workflow(self, mock_dialog):
        """Test b012 with standard PBR workflow."""
        self.mock_sb.file_dialog.return_value = self.texture_paths[
            :5
        ]  # Subset of textures
        mock_dialog.return_value = (WF.STD, True)

        # Run batch workflow
        self.converter.b012()

        # Verify dialog was shown
        mock_dialog.assert_called_once()
        self.mock_sb.file_dialog.assert_called_once()

    @skip_if_no_qt
    @patch("qtpy.QtWidgets.QInputDialog.getItem")
    def test_b012_unity_urp_workflow(self, mock_dialog):
        """Test b012 with Unity URP workflow."""
        self.mock_sb.file_dialog.return_value = self.texture_paths
        mock_dialog.return_value = (WF.URP, True)

        self.converter.b012()

        mock_dialog.assert_called_once()

    @skip_if_no_qt
    @patch("qtpy.QtWidgets.QInputDialog.getItem")
    def test_b012_unity_hdrp_workflow(self, mock_dialog):
        """Test b012 with Unity HDRP workflow (MSAO)."""
        self.mock_sb.file_dialog.return_value = self.texture_paths
        mock_dialog.return_value = (WF.HDRP, True)

        self.converter.b012()

        mock_dialog.assert_called_once()

    @skip_if_no_qt
    @patch("qtpy.QtWidgets.QInputDialog.getItem")
    def test_b012_unreal_workflow(self, mock_dialog):
        """Test b012 with Unreal Engine workflow."""
        self.mock_sb.file_dialog.return_value = self.texture_paths
        mock_dialog.return_value = (WF.UE, True)

        self.converter.b012()

        mock_dialog.assert_called_once()

    @skip_if_no_qt
    @patch("qtpy.QtWidgets.QInputDialog.getItem")
    def test_b012_gltf_workflow(self, mock_dialog):
        """Test b012 with glTF 2.0 workflow."""
        self.mock_sb.file_dialog.return_value = self.texture_paths
        mock_dialog.return_value = (WF.GLTF, True)

        self.converter.b012()

        mock_dialog.assert_called_once()

    @skip_if_no_qt
    @patch("qtpy.QtWidgets.QInputDialog.getItem")
    def test_b012_godot_workflow(self, mock_dialog):
        """Test b012 with Godot workflow."""
        self.mock_sb.file_dialog.return_value = self.texture_paths
        mock_dialog.return_value = (WF.GODOT, True)

        self.converter.b012()

        mock_dialog.assert_called_once()

    @skip_if_no_qt
    @patch("qtpy.QtWidgets.QInputDialog.getItem")
    def test_b012_specular_glossiness_workflow(self, mock_dialog):
        """Test b012 with Specular/Glossiness workflow."""
        spec_gloss_textures = [
            os.path.join(self.test_files_dir, "material_Specular.png"),
            os.path.join(self.test_files_dir, "material_Glossiness.png"),
            os.path.join(self.test_files_dir, "material_Diffuse.png"),
        ]
        self.mock_sb.file_dialog.return_value = spec_gloss_textures
        mock_dialog.return_value = (WF.SPEC, True)

        self.converter.b012()

        mock_dialog.assert_called_once()

    @skip_if_no_qt
    @patch("qtpy.QtWidgets.QInputDialog.getItem")
    def test_b012_user_cancels_workflow_selection(self, mock_dialog):
        """Test b012 handles user canceling workflow selection."""
        self.mock_sb.file_dialog.return_value = self.texture_paths
        mock_dialog.return_value = ("Unity URP", False)  # User canceled

        # Should return early
        result = self.converter.b012()

        self.assertIsNone(result)

    @skip_if_no_qt
    @patch("qtpy.QtWidgets.QInputDialog.getItem")
    def test_b012_empty_texture_selection(self, mock_dialog):
        """Test b012 handles empty texture selection."""
        self.mock_sb.file_dialog.return_value = None

        # Should return early without showing workflow dialog
        result = self.converter.b012()

        self.assertIsNone(result)
        mock_dialog.assert_not_called()

    @skip_if_no_qt
    @patch("qtpy.QtWidgets.QInputDialog.getItem")
    def test_b012_unknown_workflow(self, mock_dialog):
        """Test b012 handles unknown workflow gracefully."""
        self.mock_sb.file_dialog.return_value = self.texture_paths
        mock_dialog.return_value = ("Unknown Workflow", True)

        # Should handle gracefully
        self.converter.b012()

    @skip_if_no_qt
    @patch("qtpy.QtWidgets.QInputDialog.getItem")
    def test_b012_multiple_texture_sets(self, mock_dialog):
        """Test b012 processes multiple texture sets correctly."""
        # Create second texture set
        set2_textures = []
        for map_type, filename in [
            ("BaseColor", "model2_BaseColor.png"),
            ("Metallic", "model2_Metallic.png"),
            ("Roughness", "model2_Roughness.png"),
        ]:
            filepath = os.path.join(self.test_files_dir, filename)
            img = ImgUtils.create_image(
                "RGB" if map_type == "BaseColor" else "L",
                (512, 512),
                (128, 128, 128) if map_type == "BaseColor" else 128,
            )
            ImgUtils.save_image(img, filepath)
            set2_textures.append(filepath)

        all_textures = self.texture_paths[:3] + set2_textures

        self.mock_sb.file_dialog.return_value = all_textures
        mock_dialog.return_value = (WF.STD, True)

        # Should process both sets
        self.converter.b012()

    @skip_if_no_qt
    @patch("pythontk.core_utils.engines.textures.map_factory.MapFactory.prepare_maps")
    @patch("qtpy.QtWidgets.QInputDialog.getItem")
    def test_b012_handles_factory_errors(self, mock_dialog, mock_prepare):
        """Test b012 handles TextureMapFactory errors gracefully."""
        self.mock_sb.file_dialog.return_value = self.texture_paths
        mock_dialog.return_value = (WF.STD, True)
        mock_prepare.side_effect = Exception("Factory processing error")

        # Should catch and report error, not crash
        self.converter.b012()

    @skip_if_no_qt
    @patch("tentacle.slots.tools.converter.MapFactory.prepare_maps")
    @patch("qtpy.QtWidgets.QInputDialog.getItem")
    def test_b012_config_comes_from_registry(self, mock_dialog, mock_prepare):
        """b012 sources its workflow config from MapRegistry (SSoT), not a private copy.

        Guards against the two tools drifting: the config handed to
        ``prepare_maps`` must equal ``MapRegistry.resolve_config(name)`` (minus
        the description, plus the panel's default output format).
        """
        self.mock_sb.file_dialog.return_value = self.texture_paths
        mock_dialog.return_value = (WF.URP, True)
        mock_prepare.return_value = []

        self.converter.b012()

        mock_prepare.assert_called_once()
        passed = dict(mock_prepare.call_args.kwargs)

        expected = MapRegistry().resolve_config(WF.URP)
        expected.pop("description", None)
        expected.setdefault("output_extension", "png")

        self.assertEqual(passed, expected)

    @skip_if_no_qt
    @patch("qtpy.QtWidgets.QInputDialog.getItem")
    def test_b012_offers_registry_workflow_names(self, mock_dialog):
        """The workflow picker is populated from MapRegistry, so both tools list
        the same named workflows."""
        self.mock_sb.file_dialog.return_value = self.texture_paths
        mock_dialog.return_value = (WF.STD, True)

        self.converter.b012()

        offered = mock_dialog.call_args.args[3]
        self.assertEqual(
            sorted(offered), sorted(MapRegistry().get_workflow_presets())
        )

    # -------------------------------------------------------------------------
    # Integration Tests
    # -------------------------------------------------------------------------

    def test_texture_map_factory_import(self):
        """Test that MapFactory is properly imported."""
        from pythontk import MapFactory

        self.assertIsNotNone(MapFactory)
        self.assertTrue(hasattr(MapFactory, "prepare_maps"))

    def test_converter_has_all_methods(self):
        """Test that ConverterSlots has all expected methods."""
        self.assertTrue(hasattr(self.converter, "tb001"))
        self.assertTrue(hasattr(self.converter, "b012"))
        self.assertTrue(callable(self.converter.tb001))
        self.assertTrue(callable(self.converter.b012))

    def test_source_dir_property(self):
        """Test source_dir property getter/setter."""
        test_dir = "/test/directory"
        self.converter.source_dir = test_dir
        self.assertEqual(self.converter.source_dir, test_dir)

# =============================================================================
# Edge Cases
# =============================================================================

class TestMapConverterEdgeCases(unittest.TestCase):
    """Test edge cases and error handling."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_sb = Mock()
        self.converter = ConverterSlots(self.mock_sb)
        self.mock_widget = Mock()

    def test_tb001_with_corrupted_texture(self):
        """Test tb001 handles corrupted texture files."""
        # Create a corrupted file
        temp_dir = tempfile.mkdtemp()
        try:
            corrupted_file = os.path.join(temp_dir, "corrupted_spec.png")
            with open(corrupted_file, "w") as f:
                f.write("This is not a valid PNG")

            self.mock_sb.file_dialog.return_value = [corrupted_file]

            # Should handle gracefully
            self.converter.tb001(self.mock_widget)

        finally:
            shutil.rmtree(temp_dir)

    @skip_if_no_qt
    @patch("qtpy.QtWidgets.QInputDialog.getItem")
    def test_b012_with_missing_texture_files(self, mock_dialog):
        """Test b012 handles missing texture files."""
        fake_paths = [
            "/nonexistent/texture1.png",
            "/nonexistent/texture2.png",
        ]

        self.mock_sb.file_dialog.return_value = fake_paths
        mock_dialog.return_value = (WF.STD, True)

        # Should handle gracefully
        self.converter.b012()

    def test_tb001_with_invalid_image_format(self):
        """Test tb001 handles unsupported image formats."""
        temp_dir = tempfile.mkdtemp()
        try:
            # Create a text file with .png extension
            fake_png = os.path.join(temp_dir, "fake_spec.png")
            with open(fake_png, "wb") as f:
                f.write(b"Not an image")

            self.mock_sb.file_dialog.return_value = [fake_png]

            # Should handle gracefully without crashing
            self.converter.tb001(self.mock_widget)

        finally:
            shutil.rmtree(temp_dir)

    def test_tb001_with_single_channel_specular(self):
        """Test tb001 handles grayscale specular maps correctly."""
        temp_dir = tempfile.mkdtemp()
        try:
            # Create grayscale specular map
            spec_file = os.path.join(temp_dir, "model_Specular.png")
            img = ImgUtils.create_image("L", (512, 512), 128)
            ImgUtils.save_image(img, spec_file)

            self.mock_sb.file_dialog.return_value = [spec_file]

            # Should process without error
            self.converter.tb001(self.mock_widget)

        finally:
            shutil.rmtree(temp_dir)

    def test_tb001_workflow_config_passthrough(self):
        """Test tb001 correctly passes workflow config to TextureMapFactory."""
        temp_dir = tempfile.mkdtemp()
        try:
            spec_file = os.path.join(temp_dir, "test_Specular.png")
            img = ImgUtils.create_image("RGB", (512, 512), (128, 128, 128))
            ImgUtils.save_image(img, spec_file)

            self.mock_sb.file_dialog.return_value = [spec_file]
            self.mock_widget.option_box.menu.chk000.isChecked.return_value = False

            with patch(
                "pythontk.core_utils.engines.textures.map_factory.MapFactory.prepare_maps"
            ) as mock_prepare:
                mock_prepare.return_value = [spec_file]

                self.converter.tb001(self.mock_widget)

                # Verify workflow_config was passed correctly
                self.assertTrue(mock_prepare.called)
                call_args = mock_prepare.call_args
                # workflow_config is now passed as kwargs
                kwargs = call_args[1]

                self.assertFalse(kwargs.get("albedo_transparency"))
                self.assertFalse(kwargs.get("metallic_smoothness"))
                self.assertEqual(kwargs.get("normal_type"), "OpenGL")

        finally:
            shutil.rmtree(temp_dir)

    def test_tb001_with_mixed_resolution_textures(self):
        """Test tb001 handles textures with different resolutions."""
        temp_dir = tempfile.mkdtemp()
        try:
            # Create textures with different sizes
            spec_512 = os.path.join(temp_dir, "model_Specular.png")
            gloss_1024 = os.path.join(temp_dir, "model_Glossiness.png")

            img_512 = ImgUtils.create_image("RGB", (512, 512), (128, 128, 128))
            img_1024 = ImgUtils.create_image("L", (1024, 1024), 128)

            ImgUtils.save_image(img_512, spec_512)
            ImgUtils.save_image(img_1024, gloss_1024)

            self.mock_sb.file_dialog.return_value = [spec_512, gloss_1024]

            # Should process (factory may handle resolution mismatch)
            self.converter.tb001(self.mock_widget)

        finally:
            shutil.rmtree(temp_dir)

    def test_tb001_empty_texture_set(self):
        """Test tb001 with empty file list."""
        self.mock_sb.file_dialog.return_value = []

        # Should return early without error
        result = self.converter.tb001(self.mock_widget)
        self.assertIsNone(result)

    def test_source_dir_persistence(self):
        """Test source_dir is updated after tb001 processing."""
        temp_dir = tempfile.mkdtemp()
        try:
            spec_file = os.path.join(temp_dir, "test_Specular.png")
            img = ImgUtils.create_image("RGB", (512, 512), (128, 128, 128))
            ImgUtils.save_image(img, spec_file)

            self.mock_sb.file_dialog.return_value = [spec_file]

            # Process and verify source_dir is set
            self.converter.tb001(self.mock_widget)

            # source_dir should be updated to the texture directory
            self.assertIsNotNone(self.converter.source_dir)

        finally:
            shutil.rmtree(temp_dir)

class TestMapConverterMethods(unittest.TestCase):
    """Tests for ConverterSlots individual button methods (b004-b010)."""

    @classmethod
    def setUpClass(cls):
        cls.test_dir = tempfile.mkdtemp(prefix="converter_methods_")
        cls.test_files_dir = os.path.join(cls.test_dir, "textures")
        os.makedirs(cls.test_files_dir, exist_ok=True)

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(cls.test_dir):
            shutil.rmtree(cls.test_dir)

    def setUp(self):
        self.mock_sb = Mock()
        self.mock_sb.file_dialog = Mock(return_value=None)
        self.converter = ConverterSlots(self.mock_sb)

        # Mock UI
        self.mock_widget = Mock()
        self.mock_widget.option_box.menu = Mock()
        self.converter.ui = self.mock_widget

    def create_dummy_image(self, name, mode="RGB"):
        path = os.path.join(self.test_files_dir, name)
        img = ImgUtils.create_image(mode, (64, 64), 128)
        ImgUtils.save_image(img, path)
        return path

    def test_b004_pack_transparency(self):
        """Test b004: Pack Transparency into Albedo."""
        albedo = self.create_dummy_image("mat_Albedo.png")
        opacity = self.create_dummy_image("mat_Opacity.png", "L")

        self.mock_sb.file_dialog.return_value = [albedo, opacity]

        with patch.object(
            TextureMapFactory,
            "pack_transparency_into_albedo",
            return_value="packed.png",
        ) as mock_method:
            self.converter.b004()
            mock_method.assert_called()

    def test_b007_unpack_specular_gloss(self):
        """Test b007: Unpack SpecularGloss."""
        sg = self.create_dummy_image("mat_SpecularGloss.png", "RGBA")
        self.mock_sb.file_dialog.return_value = [sg]

        with patch.object(
            TextureMapFactory, "unpack_specular_gloss", return_value=("s.png", "g.png")
        ) as mock_method:
            self.converter.b007()
            mock_method.assert_called()

    def test_b010_convert_smoothness_roughness(self):
        """Test b010: Convert Smoothness to Roughness."""
        smooth = self.create_dummy_image("mat_Smoothness.png", "L")
        self.mock_sb.file_dialog.return_value = [smooth]

        with patch.object(
            TextureMapFactory,
            "convert_smoothness_to_roughness",
            return_value="rough.png",
        ) as mock_method:
            self.converter.b010()
            mock_method.assert_called()

    def test_b011_convert_roughness_smoothness(self):
        """Test b011: Convert Roughness to Smoothness."""
        rough = self.create_dummy_image("mat_Roughness.png", "L")
        self.mock_sb.file_dialog.return_value = [rough]

        with patch.object(
            TextureMapFactory,
            "convert_roughness_to_smoothness",
            return_value="smooth.png",
        ) as mock_method:
            self.converter.b011()
            mock_method.assert_called()

    def test_tb003_convert_bump_normal(self):
        """Test tb003: Convert Bump to Normal."""
        bump = self.create_dummy_image("mat_Bump.png", "L")
        self.mock_sb.file_dialog.return_value = [bump]

        # Mock UI elements used in tb003
        self.mock_widget.option_box.menu.tb003_cmb_format.currentText.return_value = "OpenGL"
        self.mock_widget.option_box.menu.tb003_dsb_intensity.value.return_value = 1.0

        with patch.object(
            TextureMapFactory, "convert_bump_to_normal", return_value="normal.png"
        ) as mock_method:
            self.converter.tb003(self.mock_widget)
            mock_method.assert_called()

class TestMapConverterIntegration(unittest.TestCase):
    """
    Integration tests for ConverterSlots running against the real TextureMapFactory.
    No mocks on the factory methods to ensure true end-to-end validity.
    """

    @classmethod
    def setUpClass(cls):
        cls.test_dir = tempfile.mkdtemp(prefix="converter_integration_")
        cls.test_files_dir = os.path.join(cls.test_dir, "textures")
        os.makedirs(cls.test_files_dir, exist_ok=True)

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(cls.test_dir):
            shutil.rmtree(cls.test_dir)

    def setUp(self):
        self.mock_sb = Mock()
        self.mock_sb.file_dialog = Mock(return_value=None)
        self.converter = ConverterSlots(self.mock_sb)

        # Mock UI (needed for parameter retrieval)
        self.mock_widget = Mock()
        self.mock_widget.option_box.menu = Mock()
        self.converter.ui = self.mock_widget

    def create_test_image(self, name, mode="RGB", color=128):
        path = os.path.join(self.test_files_dir, name)
        img = ImgUtils.create_image(mode, (64, 64), color)
        ImgUtils.save_image(img, path)
        return path

    def test_b004_pack_transparency_real(self):
        """Integration: Pack Transparency into Albedo (Real File I/O)."""
        albedo_path = self.create_test_image("mat_Albedo.png", "RGB", (255, 0, 0))
        opacity_path = self.create_test_image("mat_Opacity.png", "L", 128)

        self.mock_sb.file_dialog.return_value = [albedo_path, opacity_path]

        # Run the actual method
        self.converter.b004()

        # Verify output
        expected_output = os.path.join(
            self.test_files_dir, "mat_AlbedoTransparency.png"
        )
        self.assertTrue(os.path.exists(expected_output), "Packed file was not created")

        # Verify content
        with Image.open(expected_output) as img:
            self.assertEqual(img.mode, "RGBA")
            # Check alpha value (should be 128 from opacity map)
            alpha = img.split()[3]
            self.assertEqual(alpha.getpixel((0, 0)), 128)

    def test_b010_convert_smoothness_roughness_real(self):
        """Integration: Convert Smoothness to Roughness (Real File I/O)."""
        smoothness_path = self.create_test_image("mat_Smoothness.png", "L", 100)
        self.mock_sb.file_dialog.return_value = [smoothness_path]

        self.converter.b010()

        expected_output = os.path.join(self.test_files_dir, "mat_Roughness.png")
        self.assertTrue(os.path.exists(expected_output))

        with Image.open(expected_output) as img:
            # Roughness = 255 - Smoothness = 255 - 100 = 155
            self.assertEqual(img.getpixel((0, 0)), 155)

    def test_tb003_convert_bump_normal_real(self):
        """Integration: Convert Bump to Normal (Real File I/O)."""
        bump_path = self.create_test_image("mat_Bump.png", "L", 128)
        self.mock_sb.file_dialog.return_value = [bump_path]

        # Mock UI options
        self.mock_widget.option_box.menu.tb003_cmb_format.currentData.return_value = "opengl"
        self.mock_widget.option_box.menu.tb003_cmb_format.currentText.return_value = "OpenGL"
        self.mock_widget.option_box.menu.tb003_dsb_intensity.value.return_value = 1.0

        self.converter.tb003(self.mock_widget)

        expected_output = os.path.join(self.test_files_dir, "mat_Normal_OpenGL.png")
        self.assertTrue(os.path.exists(expected_output))

        with Image.open(expected_output) as img:
            self.assertEqual(img.mode, "RGB")
            # Flat bump (128) should result in flat normal (128, 128, 255) roughly
            # Exact values depend on filter implementation, but should be close to blue
            r, g, b = img.getpixel((32, 32))
            self.assertTrue(b > r and b > g)

class _FakeScopeCombo:
    """Minimal uitk ComboBox stand-in for the header Scope picker."""

    def __init__(self):
        self._items = []  # (label, data)
        self._index = -1
        self.restore_state = True

    def add(self, entries, prefix=None, **kwargs):
        self._items = [(f"{prefix}\t{label}" if prefix else label, data) for label, data in entries]
        self._index = 0 if self._items else -1

    def setCurrentIndex(self, index):
        self._index = index

    def currentIndex(self):
        return self._index

    def currentData(self):
        if 0 <= self._index < len(self._items):
            return self._items[self._index][1]
        return None

    @property
    def labels(self):
        return [data for _, data in self._items]


class TestConverterScopes(unittest.TestCase):
    """The global Scope picker — the panel's only route to host selection."""

    def setUp(self):
        self.mock_sb = MagicMock()
        self.mock_sb.file_dialog = Mock(return_value=[])
        self.converter = ConverterSlots(self.mock_sb)

        self.combo = _FakeScopeCombo()
        self.header = MagicMock()
        self.header.menu.cmb_scope = self.combo
        self.converter.ui = MagicMock()
        self.converter.ui.header = self.header

    def _select(self, label):
        self.combo.setCurrentIndex(self.converter.scopes.index(label))

    def test_browse_is_the_only_scope_standalone(self):
        """With no host providers the picker offers just the file dialog."""
        self.assertEqual(self.converter.scopes, (ConverterSlots.BROWSE_SCOPE,))

    def test_register_scope_appends_and_repopulates_combo(self):
        self.converter.header_init(self.header)
        self.converter.register_scope("Selected Objects", lambda: [])
        self.converter.register_scope("Selected Materials", lambda: [])

        self.assertEqual(
            self.converter.scopes,
            (ConverterSlots.BROWSE_SCOPE, "Selected Objects", "Selected Materials"),
        )
        self.assertEqual(self.combo.labels, list(self.converter.scopes))

    def test_register_scope_keeps_the_active_scope(self):
        """Registering a second scope must not silently retarget the first."""
        self.converter.header_init(self.header)
        self.converter.register_scope("Selected Objects", lambda: [])
        self._select("Selected Objects")

        self.converter.register_scope("Selected File Nodes", lambda: [])

        self.assertEqual(self.converter._current_scope(), "Selected Objects")

    def test_scope_combo_state_is_not_persisted(self):
        """Combo state restores by index; a saved index means a different scope
        under a different host, so persistence stays off."""
        self.converter.header_init(self.header)
        self.converter.register_scope("Selected Objects", lambda: [])

        self.assertFalse(self.combo.restore_state)

    def test_browse_scope_uses_the_file_dialog(self):
        self.converter.register_scope("Selected Objects", lambda: ["/nope.png"])
        self.converter.header_init(self.header)  # defaults to Browse

        self.converter._get_texture_paths(title="t")

        self.mock_sb.file_dialog.assert_called_once()

    def test_host_scope_calls_its_provider_not_the_dialog(self):
        provider = Mock(return_value=[])
        self.converter.header_init(self.header)
        self.converter.register_scope("Selected Objects", provider, select=True)

        self.converter._get_texture_paths(title="t")

        provider.assert_called_once()
        self.mock_sb.file_dialog.assert_not_called()

    def test_provider_is_called_per_invocation(self):
        """Selection is read at tool time, not cached at registration."""
        provider = Mock(return_value=[])
        self.converter.header_init(self.header)
        self.converter.register_scope("Selected Objects", provider, select=True)

        self.converter._get_texture_paths(title="t")
        self.converter._get_texture_paths(title="t")

        self.assertEqual(provider.call_count, 2)

    def test_map_type_filter_applies_to_scope_results(self):
        temp_dir = tempfile.mkdtemp()
        try:
            normal = os.path.join(temp_dir, "mat_Normal_OpenGL.png")
            rough = os.path.join(temp_dir, "mat_Roughness.png")
            for path, mode in ((normal, "RGB"), (rough, "L")):
                ImgUtils.save_image(ImgUtils.create_image(mode, (8, 8), 128), path)

            self.converter.header_init(self.header)
            self.converter.register_scope(
                "Selected Objects", lambda: [normal, rough], select=True
            )

            kept = self.converter._get_texture_paths(
                title="t", map_type_filter=["Normal", "Normal_OpenGL"]
            )

            self.assertEqual(kept, [normal])
        finally:
            shutil.rmtree(temp_dir)

    def test_texture_provider_registers_a_selected_scope(self):
        """Back-compat: hosts that set the single-provider property still work."""
        provider = Mock(return_value=[])
        self.converter.header_init(self.header)
        self.converter.texture_provider = provider

        self.assertIn("Selected", self.converter.scopes)
        self.assertIs(self.converter.texture_provider, provider)

        self._select("Selected")
        self.converter._get_texture_paths(title="t")
        provider.assert_called_once()

    def test_texture_provider_none_removes_the_scope(self):
        self.converter.header_init(self.header)
        self.converter.texture_provider = Mock(return_value=[])
        self.converter.texture_provider = None

        self.assertNotIn("Selected", self.converter.scopes)
        self.assertIsNone(self.converter.texture_provider)

    def test_register_scope_rejects_non_callable(self):
        with self.assertRaises(TypeError):
            self.converter.register_scope("Bad", ["not", "callable"])

    def test_register_scope_rejects_the_reserved_browse_label(self):
        """Shadowing it would route the built-in entry to the host, so 'Browse'
        would silently stop opening the file dialog."""
        with self.assertRaises(ValueError):
            self.converter.register_scope(
                ConverterSlots.BROWSE_SCOPE, lambda: ["/nope.png"]
            )
        self.assertEqual(self.converter.scopes, (ConverterSlots.BROWSE_SCOPE,))

    def test_select_survives_registration_before_the_combo_exists(self):
        """Hosts register right after launch(show=False); the header menu may
        not be built until first show, so the request has to survive the gap."""
        provider = Mock(return_value=[])
        self.converter.register_scope("Selected Objects", provider, select=True)

        self.converter.header_init(self.header)  # combo appears only now

        self.assertEqual(self.converter._current_scope(), "Selected Objects")
        self.converter._get_texture_paths(title="t")
        provider.assert_called_once()
        self.mock_sb.file_dialog.assert_not_called()

    def test_current_scope_falls_back_to_browse_without_a_header(self):
        self.converter.ui = MagicMock()  # no real combo behind it
        self.assertEqual(self.converter._current_scope(), ConverterSlots.BROWSE_SCOPE)


class TestConverterOptimize(unittest.TestCase):
    """Optimize (tb000) — affix resolution, dry run, and size reporting."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="converter_optimize_")
        self.mock_sb = MagicMock()
        self.converter = ConverterSlots(self.mock_sb)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def _texture(self, name="rock_BaseColor.png", size=(128, 128)):
        path = os.path.join(self.test_dir, name)
        ImgUtils.save_image(ImgUtils.create_image("RGB", size, (200, 120, 60)), path)
        return path

    def _widget(
        self,
        *,
        modifier="",
        affix="auto",
        clamp=0,
        dry_run=False,
        new="",
        old="old",
        target="",
        lossy=0,
        file_type="",
        secondary=1.0,
        rdo=0,
        rdo_dictionary=ConverterSlots.DEFAULT_RDO_DICTIONARY,
    ):
        widget = MagicMock()
        menu = widget.option_box.menu
        menu.cmb001.currentData.return_value = file_type
        menu.cmb000.currentData.return_value = clamp
        # Explicit, not left to MagicMock: an auto-mocked currentData() returns a
        # truthy Mock, which reads as "a target is selected" and silently routes
        # every optimize test through the target-filter path.
        menu.cmb_target.currentData.return_value = target
        menu.cmb_lossy.currentData.return_value = lossy
        # Same reason: a Mock converts to 1.0 / 1, an "RDO on, dictionary 1" run
        # the dials refuse before any map is touched.
        menu.cmb_rdo.currentData.return_value = rdo
        menu.cmb_rdo_dictionary.currentData.return_value = rdo_dictionary
        menu.cmb_secondary_scale.currentData.return_value = secondary
        # Affix mode lives on the modifier field's option box (an icon button
        # beside it), not a sibling combobox.
        menu.txt_modifier.option_box.affix_mode = affix
        menu.txt_modifier.text.return_value = modifier
        menu.txt_new_folder.text.return_value = new
        menu.txt_old_folder.text.return_value = old
        menu.chk_dry_run.isChecked.return_value = dry_run
        return widget

    # ---- affix ----------------------------------------------------------


    def test_auto_prefix_names_the_output_file(self):
        path = self._texture()
        self.converter._get_texture_paths = Mock(return_value=[path])

        self.converter.tb000(self._widget(modifier="LD_"))

        self.assertTrue(
            os.path.isfile(os.path.join(self.test_dir, "LD_rock_BaseColor.png"))
        )

    def test_auto_suffix_names_the_output_file(self):
        path = self._texture()
        self.converter._get_texture_paths = Mock(return_value=[path])

        self.converter.tb000(self._widget(modifier="_LD"))

        self.assertTrue(
            os.path.isfile(os.path.join(self.test_dir, "rock_LD_BaseColor.png"))
        )

    # ---- dry run --------------------------------------------------------

    # ---- KTX2 RDO ---------------------------------------------------------

    def test_ktx2_is_offered_after_every_existing_format(self):
        """Optimize could not write KTX2 at all -- its Format list was
        ``ImgUtils.writable``, which keeps delivery containers out -- so the
        RDO rows had nothing to act on. KTX2 is offered now, LAST: the combo
        persists by index, and an entry anywhere else would re-point every
        saved choice. Added: 2026-09-19"""
        formats = self.converter.optimize_formats
        self.assertEqual(formats[: len(ImgUtils.writable)], tuple(ImgUtils.writable))
        self.assertEqual(formats[-1], "ktx2")

    def test_a_ktx2_run_offers_the_encoder_and_stops_when_declined(self):
        """No toktx: the run offers the managed install (the panels' rule) and,
        declined, writes nothing -- the message is the fix. Added: 2026-09-19"""
        path = self._texture(name="rock_Normal_OpenGL.png")
        self.converter._get_texture_paths = Mock(return_value=[path])
        declined = FileNotFoundError("KTX2 encoding requires 'toktx' ...")
        with patch(
            "pythontk.img_utils._img_utils.ImgUtils.ensure_ktx2_encoder",
            side_effect=declined,
        ), patch(
            "extapps.texture_maps.converter._converter.MapOptimizer.optimize_map"
        ) as optimize:
            self.converter.tb000(self._widget(file_type="ktx2", old=""))
        optimize.assert_not_called()
        self.mock_sb.message_box.assert_called_with(str(declined))

    def test_the_rdo_rows_reach_the_ktx2_encode(self):
        """Optimize's RDO and RDO Dictionary rows reach the encoder of a KTX2
        run -- the normal map capped at toktx's 0.75 -- and the dry run sizes
        the same encode. Off, nothing rides. Added: 2026-09-19"""
        import struct

        calls = []

        class _Encoder:
            def encode(
                self,
                source,
                output,
                codec="UASTC",
                srgb=True,
                mipmaps=True,
                quality=None,
                uastc_rdo=None,
                uastc_rdo_dictionary=None,
            ):
                calls.append((codec, uastc_rdo, uastc_rdo_dictionary))
                with open(output, "wb") as fh:
                    fh.write(b"\xabKTX 20\xbb\r\n\x1a\n")
                    fh.write(struct.pack("<5I", 0, 1, *source.size, 0))
                return output

        ImgUtils.register_ktx2_encoder(_Encoder())
        self.addCleanup(ImgUtils.register_ktx2_encoder, None)
        path = self._texture(name="rock_Normal_OpenGL.png")
        self.converter._get_texture_paths = Mock(return_value=[path])

        for dry_run, dictionary in ((False, 1024), (True, 256)):
            with self.subTest(dry_run=dry_run):
                calls.clear()
                self.converter.tb000(
                    self._widget(
                        file_type="ktx2",
                        rdo=2.0,
                        rdo_dictionary=dictionary,
                        old="",
                        dry_run=dry_run,
                    )
                )
                self.assertEqual(calls, [("UASTC", 0.75, dictionary)])
        calls.clear()
        self.converter.tb000(self._widget(file_type="ktx2", old=""))
        self.assertEqual(calls, [("UASTC", None, None)])

    # ---- target template / lossy ---------------------------------------

    def test_clamp_target_uses_the_profiles_budget(self):
        """'Clamp: Target' must resolve to a real number in the slot.

        Deferring the whole ceiling to enforce_budget would leave max_size None,
        and the secondary scale only engages when it has a max_size to scale —
        so the control would silently do nothing.
        """
        path = self._texture(name="rock_BaseColor.png", size=(4096, 4096))
        self.converter._get_texture_paths = Mock(return_value=[path])

        self.converter.tb000(
            self._widget(clamp=ConverterSlots.CLAMP_TARGET, target=WF.GLTF, old="")
        )
        written = os.path.join(self.test_dir, "rock_BaseColor.png")
        self.assertEqual(ImgUtils.ensure_image(written).size, (2048, 2048))

    def test_clamp_target_still_scales_secondary_maps(self):
        """The regression: with Clamp:Target the secondary scale was ignored."""
        path = self._texture(name="rock_Roughness.png", size=(4096, 4096))
        self.converter._get_texture_paths = Mock(return_value=[path])

        self.converter.tb000(
            self._widget(
                clamp=ConverterSlots.CLAMP_TARGET,
                target=WF.GLTF,
                secondary=0.5,
                old="",
            )
        )
        written = os.path.join(self.test_dir, "rock_Roughness.png")
        self.assertEqual(ImgUtils.ensure_image(written).size, (1024, 1024))

    def test_a_set_named_for_a_lobe_keeps_its_base_colour_full_size(self):
        """``Hero_Coat_Color`` read alone is a coat tint (secondary, shrunk);
        read with its set ``Hero_Coat`` it is the base colour (kept)."""
        colour = self._texture(name="Hero_Coat_Color.png", size=(256, 256))
        rough = self._texture(name="Hero_Coat_Roughness.png", size=(256, 256))
        self.converter._get_texture_paths = Mock(return_value=[colour, rough])

        with _Reported(self.converter.logger):
            self.converter.tb000(self._widget(clamp=128, secondary=0.5, old=""))

        self.assertEqual(ImgUtils.ensure_image(colour).size, (128, 128))
        self.assertEqual(ImgUtils.ensure_image(rough).size, (64, 64))


    def test_clamp_target_keeps_a_non_square_maps_aspect(self):
        """'Clamp: Target' also inherits the profile budget's POT rule, and
        that rule used to snap each axis on its own: a 1024x768 source came out
        1024x512 - a destroyed aspect ratio, well under the 2048 ceiling the
        tooltip advertises, and reported by nothing. The snap now takes the
        LONG edge and derives the other from the source ratio, so the clamp
        resizes maps instead of reshaping them.
        """
        path = self._texture(name="rock_BaseColor.png", size=(1024, 768))
        self.converter._get_texture_paths = Mock(return_value=[path])

        self.converter.tb000(
            self._widget(clamp=ConverterSlots.CLAMP_TARGET, target=WF.GLTF, old="")
        )

        written = os.path.join(self.test_dir, "rock_BaseColor.png")
        self.assertEqual(ImgUtils.ensure_image(written).size, (1024, 768))

    def test_unbudgeted_target_says_so_rather_than_silently_not_clamping(self):
        path = self._texture(size=(256, 256))
        self.converter._get_texture_paths = Mock(return_value=[path])
        with _Reported(self.converter.logger) as out:
            self.converter.tb000(
                self._widget(clamp=ConverterSlots.CLAMP_TARGET, target=WF.STD)
            )
        self.assertIn("unbudgeted", out.getvalue())

    def test_target_never_skips_a_loose_map(self):
        """foreign_packings is restricted to PACKED maps on purpose: a loose
        map's `workflows` lists the presets that EMIT it, so a general form
        would flag an ordinary AO map as an engine mismatch."""
        loose = [
            self._texture(name="rock_Ambient_Occlusion.png"),
            self._texture(name="rock_Roughness.png"),
            self._texture(name="rock_Emissive.png"),
        ]
        self.converter._get_texture_paths = Mock(return_value=loose)
        with _Reported(self.converter.logger) as out:
            self.converter.tb000(self._widget(target=WF.GLTF, dry_run=True))
        self.assertNotIn("Skipping (", out.getvalue())

    def test_target_keeps_an_undeclared_packing(self):
        """MRAO declares no workflows; an absent declaration is not an
        incompatible one, so it must never be accused."""
        path = self._texture(name="rock_MRAO.png")
        self.converter._get_texture_paths = Mock(return_value=[path])
        with _Reported(self.converter.logger) as out:
            self.converter.tb000(self._widget(target=WF.GLTF, dry_run=True))
        self.assertNotIn("Skipping (", out.getvalue())

    def test_target_skips_maps_it_cannot_consume(self):
        keep = self._texture(name="rock_BaseColor.png")
        drop = self._texture(name="rock_MSAO.png")
        self.converter._get_texture_paths = Mock(return_value=[keep, drop])

        with _Reported(self.converter.logger) as out:
            self.converter.tb000(self._widget(target=WF.GLTF, dry_run=True))
        printed = out.getvalue()

        self.assertIn("rock_MSAO.png", printed)
        self.assertIn("another engine's packing", printed)

    def test_no_target_processes_everything(self):
        keep = self._texture(name="rock_BaseColor.png")
        also = self._texture(name="rock_MSAO.png")
        self.converter._get_texture_paths = Mock(return_value=[keep, also])

        with _Reported(self.converter.logger) as out:
            self.converter.tb000(self._widget(dry_run=True))
        self.assertNotIn("Skipping (", out.getvalue())

    def test_target_filter_runs_before_the_collision_guard(self):
        """A map the target drops is never written, so it must not count
        toward the same-stem clash that refuses the whole batch."""
        shared = os.path.join(self.test_dir, "out")
        a = os.path.join(self.test_dir, "setA")
        b = os.path.join(self.test_dir, "setB")
        for d in (a, b):
            os.makedirs(d, exist_ok=True)
            ImgUtils.save_image(
                ImgUtils.create_image("RGB", (64, 64), (1, 2, 3)),
                os.path.join(d, "rock_MSAO.png"),
            )
        paths = [os.path.join(a, "rock_MSAO.png"), os.path.join(b, "rock_MSAO.png")]
        self.converter._get_texture_paths = Mock(return_value=paths)

        with _Reported(self.converter.logger) as out:
            self.converter.tb000(
                self._widget(target=WF.GLTF, new=shared, old="", dry_run=True)
            )
        printed = out.getvalue()
        self.assertNotIn("would collect", printed)
        self.assertIn("another engine's packing", printed)

    def test_lossy_is_refused_for_a_normal_map(self):
        path = self._texture(name="rock_Normal.png")
        self.converter._get_texture_paths = Mock(return_value=[path])

        with _Reported(self.converter.logger) as out:
            self.converter.tb000(
                self._widget(file_type="webp", lossy=90, dry_run=True)
            )
        self.assertIn("refused", out.getvalue())

    def test_lossy_is_allowed_for_base_color(self):
        path = self._texture(name="rock_BaseColor.png")
        self.converter._get_texture_paths = Mock(return_value=[path])

        with _Reported(self.converter.logger) as out:
            self.converter.tb000(
                self._widget(file_type="webp", lossy=90, dry_run=True)
            )
        self.assertNotIn("refused", out.getvalue())

    def test_dry_run_writes_nothing(self):
        path = self._texture(size=(256, 256))
        self.converter._get_texture_paths = Mock(return_value=[path])
        before = sorted(os.listdir(self.test_dir))

        self.converter.tb000(
            self._widget(modifier="LD_", clamp=128, dry_run=True)
        )

        self.assertEqual(sorted(os.listdir(self.test_dir)), before)

    def test_dry_run_predicts_the_real_result(self):
        """The projected byte count must match what the real run then produces —
        an estimate that drifts is worse than no number at all."""
        path = self._texture(size=(256, 256))
        self.converter._get_texture_paths = Mock(return_value=[path])

        predicted = self.converter.engine.optimize_one(
            path,
            file_type=None,
            max_size=128,
            secondary_scale=1.0,
            mode="suffix",
            modifier="",
            new_folder="",
            old_folder="",
            registry=MapRegistry(),
            dry_run=True,
        )
        actual = self.converter.engine.optimize_one(
            path,
            file_type=None,
            max_size=128,
            secondary_scale=1.0,
            mode="suffix",
            modifier="",
            new_folder="",
            old_folder="",
            registry=MapRegistry(),
        )

        self.assertEqual(predicted, actual)

    def test_dry_run_reports_the_path_the_real_run_writes(self):
        path = self._texture(size=(256, 256))
        self.converter._get_texture_paths = Mock(return_value=[path])

        predicted = self._captured_path(
            "// Would write: ", self._widget(modifier="LD_", clamp=128, dry_run=True)
        )
        written = self._captured_path(
            "// Result: ", self._widget(modifier="LD_", clamp=128)
        )

        self.assertEqual(predicted, written)
        self.assertTrue(os.path.isfile(predicted))
        self.assertEqual(os.path.basename(predicted), "LD_rock_BaseColor.png")

    def _captured_path(self, marker, widget):
        """Run tb000 and return the path reported on the line after *marker*."""
        with _Reported(self.converter.logger) as out:
            self.converter.tb000(widget)
        for line in out.getvalue().splitlines():
            if line.startswith(marker):
                return line[len(marker):].split("  [")[0].strip()
        self.fail(f"No {marker!r} line was printed.")

    def test_one_failing_map_does_not_abandon_the_batch(self):
        """A map that can't be written is reported; the rest still optimize.

        Regression (2026-08-05): optimizing a Maya selection that included a
        read-only source (StingrayPBS' preset cube maps live under Program
        Files) raised PermissionError straight out of the loop — the run
        stopped mid-batch with no summary and no indication of how far it got.
        """
        first = self._texture("a_BaseColor.png", size=(256, 256))
        doomed = self._texture("b_Roughness.png", size=(256, 256))
        last = self._texture("c_Metallic.png", size=(256, 256))
        self.converter._get_texture_paths = Mock(
            return_value=[first, doomed, last]
        )

        real_optimize_one = self.converter.engine.optimize_one

        def _fail_on_doomed(texture_path, **kwargs):
            if texture_path == doomed:
                raise PermissionError(f"[Errno 13] Permission denied: {doomed!r}")
            return real_optimize_one(texture_path, **kwargs)

        self.converter.engine.optimize_one = _fail_on_doomed

        with _Reported(self.converter.logger) as out:
            self.converter.tb000(self._widget(clamp=128))
        reported = out.getvalue()

        self.assertIn("PermissionError", reported)
        self.assertIn("b_Roughness.png", reported)
        # The two healthy maps still ran, and the summary counts only those.
        self.assertIn("Total (2 map(s)) (1 unmeasured):", reported)
        for survivor in (first, last):
            with Image.open(survivor) as im:
                self.assertEqual(max(im.size), 128, survivor)

    def test_dry_run_reports_a_size_transition(self):
        path = self._texture(size=(256, 256))
        self.converter._get_texture_paths = Mock(return_value=[path])

        with _Reported(self.converter.logger) as out:
            self.converter.tb000(self._widget(clamp=128, dry_run=True))
        reported = out.getvalue()

        self.assertRegex(reported, r"\d[\d,.]* (bytes|KB|MB|GB) -> \d[\d,.]* (bytes|KB|MB|GB)")

    # ---- size reporting -------------------------------------------------

    def test_real_run_reports_size_before_and_after(self):
        path = self._texture(size=(256, 256))
        self.converter._get_texture_paths = Mock(return_value=[path])
        size_before = os.path.getsize(path)

        with _Reported(self.converter.logger) as out:
            self.converter.tb000(self._widget(clamp=128))
        reported = out.getvalue()

        self.assertIn(FileUtils.format_bytes(size_before), reported)
        self.assertIn("Total (1 map(s)):", reported)

    def test_total_counts_only_the_maps_it_measured(self):
        """A total labelled '2 map(s)' that summed one of them is a wrong
        number, and size is the number being trusted here."""
        good = self._texture(size=(256, 256))
        missing = os.path.join(self.test_dir, "gone_Roughness.png")
        self.converter._get_texture_paths = Mock(return_value=[good, missing])

        with _Reported(self.converter.logger) as out:
            self.converter.tb000(self._widget(clamp=128, dry_run=True))
        reported = out.getvalue()

        self.assertIn("Total (1 map(s)) (1 unmeasured):", reported)

    def test_dry_run_calls_out_an_in_place_overwrite(self):
        """No modifier and no archive folder means the source is clobbered —
        the single most important thing a dry run can surface."""
        path = self._texture(size=(256, 256))
        self.converter._get_texture_paths = Mock(return_value=[path])

        with _Reported(self.converter.logger) as out:
            self.converter.tb000(
                self._widget(clamp=128, dry_run=True, old="")
            )
        reported = out.getvalue()

        self.assertIn("overwrites the original in place", reported)

    def test_archived_run_is_not_called_an_overwrite(self):
        path = self._texture(size=(256, 256))
        self.converter._get_texture_paths = Mock(return_value=[path])

        with _Reported(self.converter.logger) as out:
            self.converter.tb000(
                self._widget(clamp=128, dry_run=True, old="old")
            )
        reported = out.getvalue()

        self.assertNotIn("overwrites the original in place", reported)
        self.assertIn("Would move the original into: old/", reported)

    # ---- destination folder ---------------------------------------------

    def test_new_folder_receives_the_optimized_map(self):
        path = self._texture(size=(256, 256))
        self.converter._get_texture_paths = Mock(return_value=[path])

        self.converter.tb000(self._widget(clamp=128, new="new", old=""))

        self.assertTrue(
            os.path.isfile(os.path.join(self.test_dir, "new", "rock_BaseColor.png"))
        )
        self.assertTrue(os.path.isfile(path))  # source left where it was

    def test_new_folder_composes_with_the_modifier(self):
        path = self._texture(size=(256, 256))
        self.converter._get_texture_paths = Mock(return_value=[path])

        self.converter.tb000(
            self._widget(clamp=128, modifier="LD_", new="new", old="")
        )

        self.assertTrue(
            os.path.isfile(os.path.join(self.test_dir, "new", "LD_rock_BaseColor.png"))
        )

    def test_new_folder_archives_the_original_beside_the_source(self):
        """The archive is relative to the *source* folder, not the new one —
        otherwise the original is buried inside the output it produced."""
        path = self._texture(size=(256, 256))
        self.converter._get_texture_paths = Mock(return_value=[path])

        self.converter.tb000(self._widget(clamp=128, new="new", old="old"))

        self.assertTrue(
            os.path.isfile(os.path.join(self.test_dir, "old", "rock_BaseColor.png"))
        )
        self.assertTrue(
            os.path.isfile(os.path.join(self.test_dir, "new", "rock_BaseColor.png"))
        )
        self.assertFalse(os.path.isfile(path))

    def test_matching_destination_folders_are_refused(self):
        """Archiving into the folder just written to drops the original on top
        of the optimized map — refuse before the first texture is touched."""
        path = self._texture(size=(256, 256))
        self.converter._get_texture_paths = Mock(return_value=[path])

        with _Reported(self.converter.logger) as out:
            # "out/" not "/out/": a trailing separator is a typed spelling of
            # the same subdirectory everywhere, while a LEADING one roots the
            # path on POSIX by design (see _is_abs_dest), so the two fields
            # would name different folders and the guard under test could
            # never fire on that platform.
            self.converter.tb000(self._widget(clamp=128, new="out", old="out/"))
        reported = out.getvalue()

        self.assertIn("Use different names", reported)
        self.assertEqual(os.listdir(self.test_dir), [os.path.basename(path)])

    def test_matching_destinations_are_compared_the_way_the_filesystem_would(self):
        """'out' and 'OUT' are one directory on Windows and two on POSIX, so
        the guard has to defer to normcase rather than folding case outright."""
        same_dir = os.path.normcase("out") == os.path.normcase("OUT")
        path = self._texture(size=(256, 256))
        self.converter._get_texture_paths = Mock(return_value=[path])

        with _Reported(self.converter.logger) as out:
            self.converter.tb000(self._widget(clamp=128, new="out", old="OUT"))
        reported = out.getvalue()

        if same_dir:
            self.assertIn("Use different names", reported)
        else:  # two distinct directories — the run proceeds, filling both
            for folder in ("out", "OUT"):
                self.assertTrue(
                    os.path.isfile(
                        os.path.join(self.test_dir, folder, "rock_BaseColor.png")
                    )
                )

    def test_dry_run_reports_the_new_folder_path(self):
        path = self._texture(size=(256, 256))
        self.converter._get_texture_paths = Mock(return_value=[path])

        predicted = self._captured_path(
            "// Would write: ", self._widget(clamp=128, new="new", dry_run=True)
        )
        written = self._captured_path(
            "// Result: ", self._widget(clamp=128, new="new")
        )

        self.assertEqual(predicted, written)
        self.assertEqual(
            os.path.normcase(os.path.dirname(predicted)),
            os.path.normcase(os.path.join(self.test_dir, "new")),
        )

    def test_new_folder_is_not_created_on_a_dry_run(self):
        path = self._texture(size=(256, 256))
        self.converter._get_texture_paths = Mock(return_value=[path])

        self.converter.tb000(self._widget(clamp=128, new="new", dry_run=True))

        self.assertFalse(os.path.exists(os.path.join(self.test_dir, "new")))


    # ---- absolute destinations ------------------------------------------


    def test_absolute_new_folder_collects_maps_from_several_source_folders(self):
        """The capability the Material Updater's Output Folder used to carry:
        one destination for a batch whose sources live in different folders."""
        out = os.path.join(self.test_dir, "collected")
        sources = []
        for sub in ("a", "b"):
            os.makedirs(os.path.join(self.test_dir, sub), exist_ok=True)
            sources.append(
                self._texture(name=os.path.join(sub, f"{sub}_BaseColor.png"), size=(256, 256))
            )
        self.converter._get_texture_paths = Mock(return_value=sources)

        self.converter.tb000(self._widget(clamp=128, new=out, old=""))

        for sub in ("a", "b"):
            self.assertTrue(os.path.isfile(os.path.join(out, f"{sub}_BaseColor.png")))

    def test_absolute_old_folder_collects_the_originals(self):
        archive = os.path.join(self.test_dir, "archive")
        path = self._texture(size=(256, 256))
        self.converter._get_texture_paths = Mock(return_value=[path])

        self.converter.tb000(
            self._widget(clamp=128, new=os.path.join(self.test_dir, "out"), old=archive)
        )

        self.assertTrue(os.path.isfile(os.path.join(archive, "rock_BaseColor.png")))
        self.assertFalse(os.path.isfile(path))  # original moved out of the source dir

    def test_absolute_old_folder_works_in_overwrite_mode(self):
        """Overwrite mode archives via ``optimize_map``'s own old_files_folder,
        which resolves against the output dir — a full path must still win."""
        archive = os.path.join(self.test_dir, "archive")
        path = self._texture(size=(256, 256))
        self.converter._get_texture_paths = Mock(return_value=[path])

        self.converter.tb000(self._widget(clamp=128, new="", old=archive))

        self.assertTrue(os.path.isfile(os.path.join(archive, "rock_BaseColor.png")))
        self.assertTrue(os.path.isfile(path))  # optimized map written in place

    def test_absolute_new_folder_naming_the_source_dir_is_overwrite_mode(self):
        """A full path can name the texture's OWN folder. Treated as a new
        folder it would write over the source and then archive the *optimized*
        map, leaving nothing behind — so it has to take the in-place branch."""
        archive = os.path.join(self.test_dir, "archive")
        path = self._texture(size=(256, 256))
        self.converter._get_texture_paths = Mock(return_value=[path])

        self.converter.tb000(self._widget(clamp=128, new=self.test_dir, old=archive))

        self.assertTrue(os.path.isfile(path), "optimized map must remain in place")
        self.assertTrue(os.path.isfile(os.path.join(archive, "rock_BaseColor.png")))
        self.assertEqual(ImgUtils.get_image_size(path), (128, 128))

    def test_shared_destination_refuses_same_named_maps(self):
        """Collapsing several source folders into one destination makes two
        same-stem maps resolve to the same output path, and both writers
        default to overwrite - refuse before the first one is destroyed."""
        out = os.path.join(self.test_dir, "collected")
        sources = []
        for sub in ("a", "b"):
            os.makedirs(os.path.join(self.test_dir, sub), exist_ok=True)
            sources.append(
                self._texture(name=os.path.join(sub, "rock_BaseColor.png"), size=(256, 256))
            )
        self.converter._get_texture_paths = Mock(return_value=sources)

        with _Reported(self.converter.logger) as report:
            self.converter.tb000(self._widget(clamp=128, new=out, old=""))
        reported = report.getvalue()

        self.assertIn("claimed by more than one map", reported)
        self.assertFalse(os.path.exists(out), "nothing may be written after a refusal")
        for src in sources:  # every source left exactly as it was
            self.assertEqual(ImgUtils.get_image_size(src), (256, 256))

    def test_a_conversion_that_would_merge_two_maps_in_one_folder_is_refused(self):
        """`rock_BaseColor.tga` and `rock_BaseColor.png` in the SAME folder both
        resolve to `rock_BaseColor.png` under `Format: PNG`, and the writer
        defaults to overwriting -- so one optimized result was silently lost
        while the summary still counted two maps.

        Narrower than the shared-destination case: the SOURCES survive here
        whenever an archive folder is set, so only the result is destroyed.
        """
        png = self._texture("rock_BaseColor.png")
        tga = self._texture("rock_BaseColor.tga")
        self.converter._get_texture_paths = Mock(return_value=[png, tga])

        with _Reported(self.converter.logger) as out:
            self.converter.tb000(self._widget(file_type="png"))
        reported = out.getvalue()

        self.assertIn("rock_BaseColor.png", reported)
        self.assertIn("overwrite", reported.lower())

    def test_the_same_pair_with_NO_conversion_is_left_alone(self):
        """Each keeps its own extension, so nothing can be lost -- refusing here
        would start rejecting folders that process correctly today."""
        png = self._texture("rock_BaseColor.png")
        tga = self._texture("rock_BaseColor.tga")
        self.converter._get_texture_paths = Mock(return_value=[png, tga])

        with _Reported(self.converter.logger) as out:
            self.converter.tb000(self._widget(file_type=""))
        reported = out.getvalue()

        self.assertNotIn("overwrite the last", reported.lower())


    def test_a_shared_folder_does_NOT_refuse_maps_that_keep_two_names(self):
        """The over-fire the bare-stem guard used to produce.

        Collapsing two source folders into one output is only destructive when
        the inputs resolve to ONE name. `.tga` and `.png` with no conversion
        keep two, land side by side, and lose nothing -- so refusing them
        rejects a run that works.
        """
        out = os.path.join(self.test_dir, "collected")
        sources = []
        for sub, name in (("a", "rock_BaseColor.png"), ("b", "rock_BaseColor.tga")):
            os.makedirs(os.path.join(self.test_dir, sub), exist_ok=True)
            sources.append(self._texture(name=os.path.join(sub, name)))
        self.converter._get_texture_paths = Mock(return_value=sources)

        with _Reported(self.converter.logger) as report:
            self.converter.tb000(self._widget(new=out, old=""))
        reported = report.getvalue()

        self.assertNotIn("claimed by more than one map", reported)
        for name in ("rock_BaseColor.png", "rock_BaseColor.tga"):
            self.assertTrue(
                os.path.isfile(os.path.join(out, name)), f"{name} was not written"
            )

    def test_a_shared_ARCHIVE_folder_still_refuses_a_real_collision(self):
        """The archive keeps each source's own name, so two identically named
        files from different folders overwrite one another there -- the half of
        the old shared-destination guard that was never about the output."""
        archive = os.path.join(self.test_dir, "archived")
        sources = []
        for sub in ("a", "b"):
            os.makedirs(os.path.join(self.test_dir, sub), exist_ok=True)
            sources.append(
                self._texture(name=os.path.join(sub, "rock_BaseColor.png"))
            )
        self.converter._get_texture_paths = Mock(return_value=sources)

        with _Reported(self.converter.logger) as out:
            self.converter.tb000(self._widget(new="", old=archive))
        reported = out.getvalue()

        self.assertIn("archive path(s) would be claimed", reported)

    def test_subdirectory_destination_allows_same_named_maps(self):
        """Per-texture subdirectories keep each source in its own folder, so
        the guard must not block what has always worked."""
        sources = []
        for sub in ("a", "b"):
            os.makedirs(os.path.join(self.test_dir, sub), exist_ok=True)
            sources.append(
                self._texture(name=os.path.join(sub, "rock_BaseColor.png"), size=(256, 256))
            )
        self.converter._get_texture_paths = Mock(return_value=sources)

        self.converter.tb000(self._widget(clamp=128, new="new", old=""))

        for sub in ("a", "b"):
            self.assertTrue(
                os.path.isfile(
                    os.path.join(self.test_dir, sub, "new", "rock_BaseColor.png")
                )
            )

    def test_dry_run_reports_a_full_archive_path_as_typed(self):
        """A subdirectory reads as 'old/'; a full path is echoed verbatim."""
        archive = os.path.join(self.test_dir, "archive")
        path = self._texture(size=(256, 256))
        self.converter._get_texture_paths = Mock(return_value=[path])

        with _Reported(self.converter.logger) as out:
            self.converter.tb000(self._widget(clamp=128, dry_run=True, old=archive))
        reported = out.getvalue()

        self.assertIn(f"Would move the original into: {archive}", reported)
        self.assertNotIn(f"{archive}/", reported)

    def test_optimize_one_returns_measured_sizes(self):
        path = self._texture(size=(256, 256))
        size_before = os.path.getsize(path)

        before, after = self.converter.engine.optimize_one(
            path,
            file_type=None,
            max_size=128,
            secondary_scale=1.0,
            mode="suffix",
            modifier="",
            new_folder="",
            old_folder="",
            registry=MapRegistry(),
        )

        self.assertEqual(before, size_before)
        self.assertEqual(after, os.path.getsize(path))


class TestMapConverterFlipChannels(unittest.TestCase):
    """Tests for the Flip Channels tool (tb002) — invert / swizzle / constant-fill."""

    @classmethod
    def setUpClass(cls):
        cls.test_dir = tempfile.mkdtemp(prefix="converter_flip_")
        cls.test_files_dir = os.path.join(cls.test_dir, "textures")
        os.makedirs(cls.test_files_dir, exist_ok=True)

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(cls.test_dir):
            shutil.rmtree(cls.test_dir)

    def setUp(self):
        # MagicMock so ``with sb.progress(...) as update:`` works out of the box.
        self.mock_sb = MagicMock()
        self.mock_sb.file_dialog = Mock(return_value=None)
        self.converter = ConverterSlots(self.mock_sb)

    def create_test_image(self, name, mode="RGB", color=128):
        path = os.path.join(self.test_files_dir, name)
        ImgUtils.save_image(ImgUtils.create_image(mode, (64, 64), color), path)
        return path

    def _widget(self, r="R", g="G", b="B", a="A", suffix=""):
        """Build a mock toolbutton whose option menu returns the given tokens."""
        widget = MagicMock()
        menu = widget.option_box.menu
        menu.cmb_r.currentData.return_value = r
        menu.cmb_g.currentData.return_value = g
        menu.cmb_b.currentData.return_value = b
        menu.cmb_a.currentData.return_value = a
        menu.txt_suffix.text.return_value = suffix
        return widget

    def test_tb002_init_identity_defaults(self):
        """The option menu builds 4 source combos + a suffix field, defaulting to identity."""
        widget = MagicMock()
        self.converter.tb002_init(widget)

        added = [c.args[0] for c in widget.option_box.menu.add.call_args_list]
        self.assertEqual(added.count("QComboBox"), 4)
        self.assertEqual(added.count("QLineEdit"), 1)

        for idx, ch in enumerate("rgba"):
            combo = getattr(widget.option_box.menu, f"cmb_{ch}")
            combo.setCurrentIndex.assert_called_once_with(idx)

    def test_tb002_invert_channel_with_suffix(self):
        """An inverted source ('-G') inverts that output channel; suffix saves a copy."""
        path = self.create_test_image("flip_N.png", "RGB", (10, 200, 30))
        self.mock_sb.file_dialog.return_value = [path]

        self.converter.tb002(self._widget(g="-G", suffix="_flip"))

        out = os.path.join(self.test_files_dir, "flip_N_flip.png")
        self.assertTrue(os.path.exists(out))
        with Image.open(out) as img:
            self.assertEqual(img.getpixel((0, 0))[:3], (10, 55, 30))  # 255-200

    def test_tb002_swap_channels_overwrite(self):
        """Swizzling R↔B swaps those channels; empty suffix overwrites in place."""
        path = self.create_test_image("flip_Swap.png", "RGB", (10, 20, 30))
        self.mock_sb.file_dialog.return_value = [path]

        self.converter.tb002(self._widget(r="B", b="R"))

        with Image.open(path) as img:
            self.assertEqual(img.getpixel((0, 0))[:3], (30, 20, 10))

    def test_tb002_constant_alpha_fill(self):
        """A '1' source writes a constant-white channel (e.g. force opaque alpha)."""
        path = self.create_test_image("flip_RGBA.png", "RGBA", (10, 20, 30, 40))
        self.mock_sb.file_dialog.return_value = [path]

        self.converter.tb002(self._widget(a="1", suffix="_op"))

        out = os.path.join(self.test_files_dir, "flip_RGBA_op.png")
        with Image.open(out) as img:
            self.assertEqual(img.mode, "RGBA")
            self.assertEqual(img.getpixel((0, 0)), (10, 20, 30, 255))

    def test_tb002_identity_no_suffix_is_noop(self):
        """All-identity sources with no suffix short-circuits — no file is touched."""
        path = self.create_test_image("flip_Identity.png", "RGB", (10, 20, 30))
        self.mock_sb.file_dialog.return_value = [path]

        with patch.object(self.converter.engine, "flip_one") as mock_flip:
            self.converter.tb002(self._widget())
            mock_flip.assert_not_called()

    def test_tb002_add_alpha_to_rgb(self):
        """Pointing the A slot at a real source promotes an RGB map to RGBA."""
        path = self.create_test_image("flip_AddA.png", "RGB", (10, 20, 30))
        self.mock_sb.file_dialog.return_value = [path]

        self.converter.tb002(self._widget(a="R", suffix="_rgba"))

        out = os.path.join(self.test_files_dir, "flip_AddA_rgba.png")
        with Image.open(out) as img:
            self.assertEqual(img.mode, "RGBA")
            self.assertEqual(img.getpixel((0, 0)), (10, 20, 30, 10))  # A ← R

    def test_tb002_invert_grayscale_stays_grayscale(self):
        """A pure invert preserves a grayscale map's mode (no RGB promotion)."""
        path = self.create_test_image("flip_Gray.png", "L", 100)
        self.mock_sb.file_dialog.return_value = [path]

        self.converter.tb002(self._widget(r="-R", suffix="_inv"))

        out = os.path.join(self.test_files_dir, "flip_Gray_inv.png")
        with Image.open(out) as img:
            self.assertEqual(img.mode, "L")
            self.assertEqual(img.getpixel((0, 0)), 155)  # 255-100


if __name__ == "__main__":
    # Run tests with verbose output
    unittest.main(verbosity=2)
