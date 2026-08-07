# !/usr/bin/python
# coding=utf-8
"""Shared, DCC-agnostic behavior for the ``rendering`` panel.

The per-panel home for logic the Maya and Blender ``Rendering`` forks share
(mixed in ahead of their ``SlotsMaya`` / ``SlotsBlender`` base). Grow this
class rather than adding a new module per feature — see the convention in
``tentacle/CLAUDE.md``.

Currently: the WebXR Preview slot (``tb002``). Its option box and push flow
are identical across DCCs by design — same objectNames per the cross-DCC
QSettings rule, same engine surface (``mtk.WebXrPreview`` /
``btk.WebXrPreview`` mirror each other via ``pythontk.PreviewBridge``) — and
duplicated per fork they drifted exactly as the convention predicts: a stale
tooltip had to be found and fixed twice. Only what genuinely differs per DCC
stays in the forks: the selection read, the engine class, where its log goes,
and the Scene Sidecar tooltip (each names what *that* DCC's FBX exporter
loses).
"""


class RenderingMixin:
    """DCC-agnostic ``rendering`` slot behavior (WebXR Preview option box + push)."""

    def webxr_init(self, widget, sidecar_tooltip):
        """Build the WebXR Preview option box (``rendering.tb002``).

        Parameters:
            widget: The ``tb002`` widget being initialized.
            sidecar_tooltip: Per-DCC Scene Sidecar tooltip — the one control
                whose explanation is deliberately not shared, because it names
                the specific channels that DCC's FBX exporter loses.

        objectNames are the contract here: the same names in both forks, per
        the cross-DCC QSettings rule, so a scope chosen in Maya is the scope
        restored in Blender.
        """
        menu = widget.option_box.menu
        menu.setTitle("WebXR Preview")

        menu.add(
            "QComboBox",
            addItems=["Selection", "Entire Scene"],
            setObjectName="cmb061",
            setCurrentIndex=0,
            setToolTip="What to publish: the current selection, or the whole scene.",
        )
        menu.add(
            "QCheckBox",
            setText="Include Textures",
            setObjectName="chk061",
            setChecked=True,
            setToolTip="Embed textures in the published GLB. Unchecked is much faster "
            "and much smaller over the wire, but the preview shows flat materials.",
        )
        menu.add(
            "QCheckBox",
            setText="Scene Sidecar",
            setObjectName="chk063",
            setChecked=True,
            setToolTip=sidecar_tooltip,
        )
        menu.add(
            "QCheckBox",
            setText="Open In Browser",
            setObjectName="chk062",
            setChecked=True,
            setToolTip="Open a tab whenever no preview page is already watching. A push "
            "that an open page can pick up — including one open in a headset — reuses it "
            "rather than stealing focus; a push after you closed it opens a new one.",
        )

    def webxr_push(self, widget, engine, has_selection, log_hint):
        """Read the option box and push to the live preview (``rendering.tb002``).

        Parameters:
            widget: The ``tb002`` widget (its option box carries the settings).
            engine: The DCC's bridge class (``mtk.WebXrPreview`` /
                ``btk.WebXrPreview``) — instantiated lazily on first push so
                the deliverer's server, port and tab survive across pushes for
                the DCC session.
            has_selection: Zero-arg callable — whether anything is selected.
            log_hint: Where that DCC surfaces bridge logging (e.g. "script
                editor"), for the failure message.
        """
        menu = widget.option_box.menu
        whole_scene = menu.cmb061.currentIndex() == 1

        if not whole_scene and not has_selection():
            self.sb.message_box("Nothing selected — select an object to preview.")
            return

        # The bridge is mixin-owned state (``getattr``: mixins here define no
        # ``__init__``), created lazily and kept for the slot instance's life.
        # The server outliving even THAT is the engine's job -- its deliverer
        # is a class attribute on the bridge, so the port and the open tab
        # survive panel reopens regardless of when this instance is rebuilt.
        if getattr(self, "_webxr", None) is None:
            self._webxr = engine()

        result = self._webxr.push(
            whole_scene=whole_scene,
            open_browser="auto" if menu.chk062.isChecked() else False,
            EMBED_TEXTURES=menu.chk061.isChecked(),
            SCENE_SIDECAR=menu.chk063.isChecked(),
        )
        if not result:
            self.sb.message_box(
                f"WebXR preview failed — see the {log_hint} for details."
            )
            return

        # The sidecar summary is reported, not left to the log: read nothing /
        # matched nothing / switched off all render the same unlit preview, so
        # without it the feature can't be debugged from the panel.
        self.sb.message_box(
            f"Preview v{result['version']} live at <hl>{result['url']}</hl>"
            f"<br>{self._webxr.sidecar_summary(result)}"
        )
