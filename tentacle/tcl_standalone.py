# !/usr/bin/python
# coding=utf-8
"""The standalone panels: each a window of its own, in a switchboard of its own.

A tool a DCC hosts opens in that host's switchboard (:meth:`Tcl.register_shared`).
The standalone panels -- the content-pipeline tools over ``extapps``' engines and
pythontk's (texture maps, mesh conversion, photogrammetry, Substance Painter,
Marmoset Toolbag, Unity, WebXR, Look Match) -- need no DCC, so each opens on its own
instead: built here from ``ui/tools/<tool>.ui`` and its one Slots class
``slots/tools/<tool>.py``, laid out like every other tool. ``pyproject.toml``'s
``uitk.external_apps.in_process`` entry points name the ``<Tool>UI`` classes below,
which is how ``python -m tentacle [panel]`` (the hub, ``__main__.py``) and a host's
external-app handler (Maya, Blender) find them; no host registers them in its own
switchboard (``slots.tools.STANDALONE``).

One recipe builds every panel -- the Switchboard, the frameless chrome, the style,
the header, the title -- because eleven hand-written copies of it once kept a
window-flag fix out of eight panels for a release (``CODE_STANDARD.md`` section 6).
A ``<Tool>UI`` declares only what differs, as data::

    class MetashapeWorkflowUI(PanelLauncher):
        TITLE = "Metashape Workflow"

and the rest is derived from its name: the ``.ui`` is the ``ui/tools`` file spelled
like the class less ``UI``, case and underscores aside (``WebXrPreviewUI`` ->
``webxr_preview.ui``), and the Slots class the ``<Base>Slots`` its
``slots/tools/<tool>.py`` defines, by the same rule. ``<Tool>UI()`` returns the
built window (``__new__`` returns it; no instance of the launcher class is made).
"""

from __future__ import annotations

import importlib
import os
from typing import Optional, Tuple


class _PanelLauncherInternal:
    """Derivation helpers for :class:`PanelLauncher`."""

    #: The ``tentacle`` package folder: ``ui/tools`` and ``slots/tools`` sit in it.
    _ROOT = os.path.dirname(os.path.abspath(__file__))

    @staticmethod
    def _folded(name: str) -> str:
        """*name* as the naming rule compares it: no case, no underscores."""
        return name.replace("_", "").lower()

    @classmethod
    def _tool(cls) -> str:
        """The panel's ``ui/tools`` stem: the one spelled like the class less ``UI``."""
        wanted = cls._folded(cls.__name__[: -len("UI")])
        for name in sorted(os.listdir(os.path.join(cls._ROOT, "ui", "tools"))):
            stem, ext = os.path.splitext(name)
            if ext == ".ui" and cls._folded(stem) == wanted:
                return stem
        raise LookupError(f"{cls.__name__}: no ui/tools/<tool>.ui reads {wanted!r}.")

    @classmethod
    def _slots_class(cls, tool: str) -> type:
        """The ``<Base>Slots`` class ``slots/tools/<tool>.py`` defines."""
        module = importlib.import_module(f"tentacle.slots.tools.{tool}")
        wanted = cls._folded(tool) + "slots"
        for name, value in vars(module).items():
            if (
                isinstance(value, type)
                and value.__module__ == module.__name__
                and cls._folded(name) == wanted
            ):
                return value
        raise LookupError(f"{module.__name__} defines no {wanted!r} Slots class.")


class PanelLauncher(_PanelLauncherInternal):
    """Base of every standalone panel's ``<Tool>UI``: calling it returns the built panel.

    Class attributes (data, per panel):
        TITLE: Window-title stem. A titled panel also shows the release on its
            header, is titled ``"<TITLE> v<version>"`` and opens at its size
            hint; ``None`` (the compact tools) leaves the ``.ui``'s own title
            and size.
        STYLE_CLASS: The uitk style class of the window.
        HEADER_BUTTONS: The header's window controls, in order. No
            ``fullscreen``: every panel is a parameter form over a log, which
            fullscreen only stretches.
    """

    TITLE: Optional[str] = None
    STYLE_CLASS: str = "bgWithBorder"
    HEADER_BUTTONS: Tuple[str, ...] = ("menu", "minimize", "hide")
    #: The folder the panels' presets keep under the presets root (their
    #: ``PRESETS_ROOT``s), and the Preset Editor's label for it. The folder is
    #: saved data: it keeps the name the panels were published under.
    PRESETS_FOLDER: Tuple[str, str] = ("extapps", "Standalone")

    def __new__(cls, *args, **kwargs):
        from qtpy import QtCore
        from uitk import Bootstrap, PresetEditor, Switchboard

        # Before the first QApplication (a no-op inside a host that owns one).
        Bootstrap.configure_high_dpi()
        # uitk names no app: the Preset Editor learns this folder's label here.
        PresetEditor.register_app_label(*cls.PRESETS_FOLDER)
        tool = cls._tool()
        sb = Switchboard(
            *args,
            ui_source=os.path.join(cls._ROOT, "ui", "tools", f"{tool}.ui"),
            slot_source=cls._slots_class(tool),
            **kwargs,
        )
        ui = getattr(sb.loaded_ui, tool)
        Bootstrap.set_translucent(ui)  # opaque where nothing composites (X11)
        # Frameless chromed window: the uitk Header supplies the window
        # controls in place of the native OS frame. Set the SAME clean flag set
        # as uitk's WindowPanel rather than OR-ing FramelessWindowHint onto a
        # QMainWindow's defaults -- those defaults carry native decoration hints
        # which, on a frameless host-owned window, make it float always-on-top
        # of its parent. With the clean set it behaves as a normal window that
        # parents to the host (e.g. Maya, via the external-app handler).
        ui.setWindowFlags(QtCore.Qt.Window | QtCore.Qt.FramelessWindowHint)
        ui.style.set(theme="dark", style_class=cls.STYLE_CLASS)
        ui.header.config_buttons(*cls.HEADER_BUTTONS)
        if cls.TITLE:
            from tentacle import __version__

            ui.header.setVersion(__version__)
            ui.setWindowTitle(f"{cls.TITLE} v{__version__}")
            ui.resize(ui.sizeHint())
        return ui


# ------------------------------------------------------------------ the panels
# One per ``uitk.external_apps.in_process`` entry point (``pyproject.toml``) and
# per ``slots.tools.STANDALONE`` name; ``test_tcl_standalone.py`` holds the three
# rosters to one another.


class CompositorUI(PanelLauncher):
    TITLE = "Map Compositor"


class ConverterUI(PanelLauncher):
    STYLE_CLASS = "translucentBgWithBorder"


class PackerUI(PanelLauncher):
    STYLE_CLASS = "translucentBgWithBorder"


class MeshConvertUI(PanelLauncher):
    STYLE_CLASS = "translucentBgWithBorder"


class MetashapeWorkflowUI(PanelLauncher):
    TITLE = "Metashape Workflow"


class RealityScanWorkflowUI(PanelLauncher):
    TITLE = "RealityCapture Workflow"


class GaussianSplatWorkflowUI(PanelLauncher):
    TITLE = "Brush Splat Workflow"


class SubstanceWorkflowUI(PanelLauncher):
    TITLE = "Substance Workflow"


class MarmosetWorkflowUI(PanelLauncher):
    TITLE = "Marmoset Workflow"


class UnityWorkflowUI(PanelLauncher):
    TITLE = "Unity Workflow"


class WebXrPreviewUI(PanelLauncher):
    TITLE = "WebXR Preview"


class LookMatchUI(PanelLauncher):
    TITLE = "Look Match"
