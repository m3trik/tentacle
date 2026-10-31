# !/usr/bin/python
# coding=utf-8
"""Mesh Converter: batch-convert FBX files to binary glTF (GLB) with FBX2glTF.

A standalone panel (``tentacle/tcl_standalone.py``): the engine is pythontk's
:class:`MeshConvert`; a host that opens it (Scene > Tools) hands it a start
folder and the FBX files behind the selected references.
"""

import os
from typing import Callable, Dict, Iterable, List, Optional, Tuple

import pythontk as ptk

from tentacle import Slots


class MeshConvertSlots(Slots, ptk.LoggingMixin):
    """Switchboard slots for the Mesh Converter UI.

    HOLDS the conversion engine (:class:`pythontk.MeshConvert`) as
    ``self.engine`` rather than inheriting it: the panel is wiring, and the
    engine's surface (``fbx_to_glb``, ``resolve_binary``, the GLB passes) is
    not the panel's. Reports what it converts through its logger, at INFO.
    """

    def __init__(self, switchboard, **kwargs):
        super().__init__(switchboard)
        self.logger.setLevel("INFO")
        #: The conversion engine this panel drives (held, not inherited).
        self.engine = ptk.MeshConvert()
        self.ui = self.sb.loaded_ui.mesh_convert

        self._source_dir: str = kwargs.get("source_dir", "")
        self._fbx_provider: Optional[Callable[[], Iterable[str]]] = kwargs.get(
            "fbx_provider", None
        )

    @property
    def source_dir(self) -> str:
        """Starting directory for the FBX file dialog."""
        return self._source_dir

    @source_dir.setter
    def source_dir(self, value: str) -> None:
        self._source_dir = value

    @property
    def fbx_provider(self) -> Optional[Callable[[], Iterable[str]]]:
        """Callable returning FBX paths from the host DCC selection.

        Set by the host integration to power the header "From FBX
        references" toggle. Returns None when running standalone, in
        which case every tool falls back to the file dialog.
        """
        return self._fbx_provider

    @fbx_provider.setter
    def fbx_provider(self, fn: Optional[Callable[[], Iterable[str]]]) -> None:
        self._fbx_provider = fn

    def header_init(self, widget) -> None:
        """Add the From-FBX-references toggle to the header menu."""
        widget.menu.add(
            "QCheckBox",
            setText="From FBX references",
            setObjectName="chk_use_selection",
            setChecked=False,
            setToolTip=(
                "When enabled, tools that take FBX input read their paths from "
                "the host DCC's currently selected reference nodes (provided by "
                "the host integration) instead of opening a file browser. Tools "
                "with other input types are unaffected. Imported geometry is "
                "ignored — only nodes whose reference filename ends in .fbx "
                "contribute."
            ),
        )

    def _selection_enabled(self) -> bool:
        try:
            return self.ui.header.menu.chk_use_selection.isChecked()
        except (AttributeError, RuntimeError):
            return False

    def _get_fbx_paths(self, *, title: str, allow_multiple: bool = True) -> List[str]:
        """Resolve FBX paths via Use-Selection toggle, falling back to dialog."""
        use_selected = self._selection_enabled()

        if use_selected and self.fbx_provider:
            paths = list(self.fbx_provider() or [])
            if not paths:
                self.logger.warning("No FBX paths found on the selected objects.")
                return []
        else:
            if use_selected:
                self.logger.warning(
                    "'From FBX references' is enabled but no FBX provider "
                    "is wired up — falling back to file dialog."
                )
            paths = self.sb.file_dialog(
                file_types=["*.fbx"],
                title=title,
                start_dir=self.source_dir,
                allow_multiple=allow_multiple,
            )
            paths = list(paths or [])

        valid = [
            p
            for p in paths
            if p and os.path.isfile(p) and p.lower().endswith(".fbx")
        ]
        for missing in (p for p in paths if p not in valid):
            self.logger.warning(f"Skipping (not an existing .fbx file): {missing}")
        return valid

    def _ensure_binary_or_offer_download(self) -> Optional[str]:
        """Find FBX2glTF; if missing, prompt via Qt and install on confirm."""
        existing = self.engine.resolve_binary(required=False, auto_install=False)
        if existing:
            return existing

        from qtpy.QtWidgets import QMessageBox

        answer = QMessageBox.question(
            None,
            "FBX2glTF not installed",
            (
                f"FBX2glTF v{self.engine.FBX2GLTF_VERSION} is required to convert FBX to GLB.\n\n"
                "Download it now (a few MB) into ~/.pythontk/tools/?"
            ),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )
        if answer != QMessageBox.Yes:
            self.logger.info("Mesh Converter: user declined FBX2glTF installation.")
            return None

        try:
            return self.engine.resolve_binary(
                required=True, auto_install=True, prompt=False
            )
        except (RuntimeError, OSError, FileNotFoundError, LookupError) as exc:
            QMessageBox.critical(
                None,
                "FBX2glTF install failed",
                f"Could not install FBX2glTF:\n\n{exc}",
            )
            return None

    def tb000_init(self, widget) -> None:
        """Set up the FBX -> GLB tool button option box."""
        widget.option_box.menu.setTitle("FBX to GLB")
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Draco compression",
            setObjectName="chk_draco",
            setChecked=False,
            setToolTip="Apply Draco mesh compression — smaller file, slightly slower decode.",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Overwrite existing",
            setObjectName="chk_overwrite",
            setChecked=True,
            setToolTip="Replace any existing .glb at the destination.",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Check materials",
            setObjectName="chk_check_materials",
            setChecked=True,
            setToolTip=(
                "After conversion, scan the GLB for materials flagged "
                "transparent whose base-color alpha is fully opaque — the "
                "classic Stingray/OpenPBR/Standard-Surface artifact where "
                "an RGBA texture leaks through despite no opacity input.\n\n"
                "Findings are printed to the console and summarized in a "
                "warning dialog."
            ),
        )

    def tb000(self, widget) -> None:
        """Convert the selected FBX file(s) to GLB beside their source."""
        fbx_paths = self._get_fbx_paths(title="Select FBX file(s) to convert to GLB:")
        if not fbx_paths:
            return

        if not self._ensure_binary_or_offer_download():
            return

        draco = widget.option_box.menu.chk_draco.isChecked()
        overwrite = widget.option_box.menu.chk_overwrite.isChecked()
        check_materials = widget.option_box.menu.chk_check_materials.isChecked()
        extra_args = ["--draco"] if draco else None

        # Conversion of a half-GB FBX takes ~75 s. Block re-clicks while
        # the footer progress bar reports per-file progress.
        widget.setEnabled(False)
        all_findings: List[Tuple[str, List[Dict[str, str]]]] = []
        total = len(fbx_paths)
        try:
            ok_count = 0
            with self.sb.progress(
                total=total, text=f"Converting 0/{total}"
            ) as update:
                for i, fbx_path in enumerate(fbx_paths):
                    self.logger.info(f"Converting: {fbx_path} ..")
                    try:
                        out_path = self.engine.fbx_to_glb(
                            fbx_path,
                            overwrite=overwrite,
                            auto_install=False,
                            extra_args=extra_args,
                        )
                        self.logger.result(out_path)
                        ok_count += 1
                        if check_materials:
                            try:
                                findings = self.engine.check_glb_materials(out_path)
                            except (RuntimeError, ValueError, OSError) as exc:
                                self.logger.error(
                                    f"Material check failed for {out_path}: {exc}"
                                )
                                findings = []
                            if findings:
                                all_findings.append((out_path, findings))
                                for f in findings:
                                    self.logger.warning(
                                        f"  {f['material']} "
                                        f"(alphaMode={f['alpha_mode']}, "
                                        f"image={f['image']}): {f['reason']}"
                                    )
                            else:
                                self.logger.info(
                                    f"Material check OK: {os.path.basename(out_path)}"
                                )
                    except FileExistsError as exc:
                        self.logger.warning(f"Skipped (exists, overwrite=False): {exc}")
                    except (RuntimeError, OSError) as exc:
                        self.logger.error(f"Error converting {fbx_path}: {exc}")
                    update(
                        i + 1,
                        f"Converted {i + 1}/{total}: {os.path.basename(fbx_path)}",
                    )

            self.logger.info(f"Mesh Converter: {ok_count}/{total} succeeded.")
        finally:
            widget.setEnabled(True)

        if all_findings:
            self._show_material_findings_dialog(all_findings)

        try:
            self.source_dir = ptk.FileUtils.format_path(fbx_paths[0], "path")
        except Exception:
            pass

    @staticmethod
    def _show_material_findings_dialog(
        all_findings: List[Tuple[str, List[Dict[str, str]]]],
    ) -> None:
        """Render a warning dialog summarizing material issues across files.

        Summary lives in the always-visible rich-text body; the per-finding
        list goes into ``detailedText`` so large batches stay readable
        (Qt provides a scrollable, expandable area).
        """
        from qtpy.QtCore import Qt
        from qtpy.QtWidgets import QApplication, QMessageBox

        total = sum(len(f) for _, f in all_findings)
        summary = (
            f"<p><b>{total} material issue(s)</b> found across "
            f"{len(all_findings)} GLB file(s).</p>"
            "<p>These materials are flagged <b>transparent</b> in the GLB but "
            "their base-color textures are fully opaque — renderers may "
            "disable depth-write (BLEND) or alpha-test as a no-op (MASK).</p>"
            "<p><b>Fix at source:</b> in Maya, ensure the color texture has "
            "no alpha channel (or convert palette PNGs to RGB), and verify "
            "the shader's opacity/transparency input is unconnected.</p>"
            "<p><i>Click &ldquo;Show Details&hellip;&rdquo; for the full list.</i></p>"
        )

        detail_lines: List[str] = []
        for glb_path, findings in all_findings:
            detail_lines.append(os.path.basename(glb_path))
            for f in findings:
                detail_lines.append(
                    f"  - {f['material']}  "
                    f"[alphaMode={f['alpha_mode']}]  "
                    f"image={f['image']}"
                )
            detail_lines.append("")  # blank line between files

        box = QMessageBox(QApplication.activeWindow())
        box.setIcon(QMessageBox.Warning)
        box.setWindowTitle("Material check: opaque-with-alpha")
        box.setTextFormat(Qt.RichText)
        box.setText(summary)
        box.setDetailedText("\n".join(detail_lines).rstrip())
        box.setStandardButtons(QMessageBox.Ok)
        box.exec_()
