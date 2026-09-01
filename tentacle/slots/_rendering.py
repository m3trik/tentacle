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
stays in the forks: the engine class, where its log goes, and the Scene
Sidecar tooltip (each names what *that* DCC's FBX exporter loses). The
selection read used to be a fork hook too; scope resolution now belongs to the
engine (``PreviewBridge.scope_objects``), so both forks lost it.
"""

import os


class RenderingMixin:
    """DCC-agnostic ``rendering`` slot behavior (WebXR Preview option box + push)."""

    #: Scope value for "publish a GLB already on disk" -- the one entry this
    #: panel adds to the shared scope vocabulary rather than reading from it.
    #: It is not a scope in the shared sense (it resolves no host objects and
    #: no other bridge could offer it), which is exactly why it is NOT pushed
    #: into ``Parameters.scope_spec``: every hand-off would inherit a choice
    #: only a viewer can honour.
    WEBXR_EXTERNAL_SCOPE = "external"

    #: ``(label, data)`` for the texture-container combo, WebP first because it
    #: is the deliverer's own default and the one that needs no external tool.
    WEBXR_TEXTURE_FORMATS = (
        ("WebP", "WEBP"),
        ("KTX2 (GPU compressed)", "KTX2"),
    )
    #: Packaged ``PreviewServer.SCRIPTS`` this panel offers, as
    #: ``(objectName, script, label, tooltip)``. A registry rather than a branch:
    #: a script added to pythontk becomes a row here by ONE entry, which is the
    #: whole point of the scripts seam — so the tooltip rides in the tuple too
    #: rather than in a second table an addition could forget.
    WEBXR_SCRIPTS = (
        (
            "chk065",
            "turntable",
            "Turntable",
            "Rotate the model hands-free in the page. Lives on the pivot, so it "
            "survives a push — the model swaps underneath it and keeps turning.",
        ),
        (
            "chk066",
            "inspect",
            "Inspect",
            "Overlay draw calls, material count and DECODED texture memory, read "
            "off the renderer. The last of those is the number a GLB's file size "
            "does not tell you, and the one that decides whether this scene needs "
            "the KTX2 texture format above.",
        ),
    )

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

        # Scope comes off the SHARED spec rather than a list written here: it is
        # the same control every other hand-off bridge offers, and the preview
        # had drifted from it already (two entries, and "Selection" where every
        # other panel says "Selected"). Reading the spec means the vocabulary
        # cannot fork again. Order is the spec's, which matters twice over --
        # these combos persist by INDEX, and "Visible Only" arriving last is
        # what makes the addition append-only for anyone who already has a
        # choice stored.
        # ``self.sb``, not an import: a slot module reaches uitk through the
        # Switchboard namespace (``test_dcc_invariants``.TestSlotImportDiscipline),
        # which resolves each bridge symbol from its OWN module -- so this costs
        # ``bridge.parameters`` and not ``bridge.slots``' widget tree.
        #
        # The one entry the spec does not carry is External GLB, appended
        # last (see the index note above): it publishes a file already on
        # disk, which is a source rather than a scope and which no other
        # hand-off could honour -- so it belongs to this panel, not to the
        # shared vocabulary.
        scope_spec = self.sb.Parameters.scope_spec()
        cmb_scope = menu.add(
            "QComboBox",
            setObjectName="cmb061",
            setToolTip=scope_spec.tooltip + "\n"
            "• External GLB — skip the export entirely and publish a "
            ".glb already on disk, exactly as authored. The same page, port and "
            "tab a push uses, so an authored asset and your own export can be "
            "compared by switching this one control. Pressing the button asks "
            "which file.",
        )
        for label, data in scope_spec.choices:
            cmb_scope.addItem(label, data)
        cmb_scope.addItem("External GLB", self.WEBXR_EXTERNAL_SCOPE)
        cmb_scope.setCurrentIndex(0)
        # Nothing is wired to the combo. The browse dialog belongs to the PUSH,
        # not to the choice: an option box is where a run is configured, and a
        # modal that interrupts configuring it -- on a click, or worse on the
        # QSettings restore that replays the stored index as the panel draws --
        # is a dialog nobody asked for yet. Asking when the button is pressed
        # also means the answer is never stale, so there is no remembered file
        # to go missing or to become unchangeable.

        menu.add(
            "QCheckBox",
            setText="Include Textures",
            setObjectName="chk061",
            setChecked=True,
            setToolTip="Embed textures in the published GLB. Unchecked is much faster "
            "and much smaller over the wire, but the preview shows flat materials.",
        )
        cmb_format = menu.add(
            "QComboBox",
            setObjectName="cmb062",
            setToolTip="Container the textures are re-encoded to for delivery.\n\n"
            "WebP is small on the wire but decodes to plain RGBA on the GPU: a "
            "measured 9.5 MB delivery became ~740 MB of video memory with mipmaps, "
            "and on a headset that — not the download — is what caps how large a "
            "scene can be previewed.\n\n"
            "KTX2 stays block-compressed on the GPU (transcoded to ASTC on a "
            "standalone headset, BC7 on desktop). It costs encode time on the push "
            "and needs KTX-Software's toktx, which this panel offers to install "
            "when it is missing — a push never quietly ships WebP instead.",
        )
        for label, data in self.WEBXR_TEXTURE_FORMATS:
            cmb_format.addItem(label, data)
        cmb_format.setCurrentIndex(0)
        menu.add(
            "QCheckBox",
            setText="Include Animation",
            setObjectName="chk064",
            setChecked=False,
            setToolTip="Bake the scene's animation into the pushed GLB so the "
            "preview can play it (the page grows a clip picker and transport). "
            "Off by default because baking samples every frame of the scene "
            "range, which costs push time and file size on a scene you are "
            "previewing for its look. A scene with shots declared ships its "
            "takes either way — arming them turns baking on regardless.",
        )
        menu.add(
            "QCheckBox",
            setText="Scene Sidecar",
            setObjectName="chk063",
            setChecked=True,
            setToolTip=sidecar_tooltip,
        )
        # Viewer scripts — ES modules the page imports on demand
        # (``PreviewServer.SCRIPTS``). Deliberately last: everything above
        # changes the DELIVERABLE, these change the page looking at it.
        #
        # There is no "Open In Browser" row. It was one, and the only case it
        # covered was "I closed the tab on purpose, don't reopen it" — the push
        # is hardcoded to ``open_browser="auto"``, which already reuses a page
        # that can pick the version up (including one open in a headset) rather
        # than stealing focus.
        for object_name, _script, label, tooltip in self.WEBXR_SCRIPTS:
            menu.add(
                "QCheckBox",
                setText=label,
                setObjectName=object_name,
                setChecked=False,
                setToolTip=tooltip,
            )

    def _webxr_browse_external(self) -> str:
        """Ask which GLB to publish. ``""`` if the dialog was cancelled.

        Asked per push rather than answered once and remembered. Remembering
        would save a click on a repeat push and cost the ability to ever choose
        a DIFFERENT file -- the combo is already sitting on External, so
        re-picking it says nothing new, and the only way out would be moving
        the file on disk. A remembered path also goes stale on its own (renamed,
        moved, deleted), and a stored answer that can quietly stop being true is
        worse than a question. What IS carried over is the folder, so the second
        ask opens where the first one landed.

        ``.glb`` only, and the filter says so: the preview serves ONE file out
        of its root, so a ``.gltf``'s sibling ``.bin`` and textures would 404
        and the page would show an empty scene with nothing to explain it.
        The bridge refuses one too -- this just keeps the refusal out of the
        file dialog.
        """
        chosen = self.sb.file_dialog(
            file_types=["*.glb"],
            title="WebXR Preview — select a GLB to publish",
            start_dir=getattr(self, "_webxr_external_dir", ""),
            filter_description="glTF Binary",
            allow_multiple=False,
        )
        if not chosen:
            return ""
        self._webxr_external_dir = os.path.dirname(chosen)
        return chosen

    def _webxr_texture_tool_ready(self, texture_format) -> bool:
        """Settle a missing encoder BEFORE the push, offering the managed install.

        Only KTX2 needs an external tool. The bridge already refuses a KTX2
        push without ``toktx`` — eagerly, before it pays for the sidecar and
        lightmap passes — but it refuses by RAISING with the install URL, and a
        panel control that dead-ends in a URL is exactly what the Scene
        Exporter's own KTX2 row stopped doing: missing tool means *offer the
        managed install*, never *abort and go read a log*. Both panels call the
        one primitive (``ptk.ImgUtils.ensure_ktx2_encoder``), so they answer
        the same environment the same way; only the modal differs.

        Gated on the choice, not run unconditionally: WebP needs nothing, and
        probing for a tool the push will not use would ask a question about a
        control the user did not touch.
        """
        if str(texture_format).upper() != "KTX2":
            return True

        import pythontk as ptk

        try:
            installed = ptk.ImgUtils.ensure_ktx2_encoder(
                prompt=lambda question: (
                    self.sb.message_box(question, "Yes", "No") == "Yes"
                )
            )
        except FileNotFoundError as e:
            # Declined, or the install failed. The error is the fix-shaped one
            # naming the manual install, so it IS the message.
            self.sb.message_box(str(e))
            return False
        if installed:
            self.sb.message_box(f"Installed KTX-Software (toktx): <hl>{installed}</hl>")
        return True

    def webxr_push(self, widget, engine, log_hint):
        """Read the option box and push to the live preview (``rendering.tb002``).

        Parameters:
            widget: The ``tb002`` widget (its option box carries the settings).
            engine: The DCC's bridge class (``mtk.WebXrPreview`` /
                ``btk.WebXrPreview``) — instantiated lazily on first push so
                the deliverer's server, port and tab survive across pushes for
                the DCC session.
            log_hint: Where that DCC surfaces bridge logging (e.g. "script
                editor"), for the failure message.

        Two sources reach the same page: the host's own scope, exported and
        converted, or an External GLB published as authored. Everything after
        the branch -- the failure message, the version and URL line -- is
        common, because from the page's side they are one thing.
        """
        menu = widget.option_box.menu
        scope = menu.cmb061.currentData() or "selected"

        # The bridge is mixin-owned state (``getattr``: mixins here define no
        # ``__init__``), created lazily and kept for the slot instance's life.
        # The server outliving even THAT is the engine's job -- its deliverer
        # is a class attribute on the bridge, so the port and the open tab
        # survive panel reopens regardless of when this instance is rebuilt.
        #
        # Built before EITHER source's step, including the one that opens a
        # file dialog: constructing the bridge is cheap -- the server is not
        # started until a delivery actually needs one -- so there is nothing to
        # gain by threading the construction through both branches.
        if getattr(self, "_webxr", None) is None:
            self._webxr = engine()

        # An explicit list every push, never ``None``: the panel's checkboxes
        # are the answer, and ``None`` means "leave the server's set alone" --
        # which would make an unticked box unable to turn a script back off.
        # The cost is that this panel is authoritative, so a script registered
        # on the server by other code is cleared by the next push from here.
        # Read before the branch because the viewer scripts are a property of
        # the PAGE, and the page is the same one either source publishes to.
        scripts = [
            script
            for object_name, script, _label, _tip in self.WEBXR_SCRIPTS
            if getattr(menu, object_name).isChecked()
        ]

        if scope == self.WEBXR_EXTERNAL_SCOPE:
            outcome = self._webxr_publish_external(scripts)
        else:
            outcome = self._webxr_push_scene(menu, scope, scripts)
        if outcome is None:
            # The step settled the run itself and has already said why (an
            # empty scope, a declined encoder install, a cancelled browse).
            # One sentinel rather than a tuple of Nones: ``result`` is None on
            # a genuine FAILURE too, and the two want different messages.
            return
        result, extra = outcome

        if not result:
            self.sb.message_box(
                f"WebXR preview failed — see the {log_hint} for details."
            )
            return

        lines = [
            f"Preview v{result['version']} live at <hl>{result['url']}</hl>",
            *extra,
        ]
        self.sb.message_box("<br>".join(line for line in lines if line))

    def _webxr_push_scene(self, menu, scope, scripts):
        """Export *scope* from the host and push it.

        Returns ``(result, extra_lines)``, or ``None`` when the flow settled
        the run itself and has already reported why.
        """
        # Resolved here rather than left to ``push``, so an empty result can be
        # REPORTED. Pushing blind collapses "nothing selected", "the scene is
        # empty" and "the export failed" into one message, and the first two are
        # the user's own next action.
        objects = self._webxr.scope_objects(scope)
        if not objects:
            # Resolved here rather than at module scope: this is the heavy half
            # of the bridge surface, and only an EMPTY scope needs its wording.
            self.sb.message_box(self.sb.BridgeSlotsBase.empty_scope_message(scope))
            return None

        texture_format = menu.cmb062.currentData()
        if not self._webxr_texture_tool_ready(texture_format):
            return None

        result = self._webxr.push(
            objects=objects,
            scope=scope,
            open_browser="auto",
            texture_format=texture_format,
            scripts=scripts,
            EMBED_TEXTURES=menu.chk061.isChecked(),
            INCLUDE_ANIMATION=menu.chk064.isChecked(),
            SCENE_SIDECAR=menu.chk063.isChecked(),
        )
        # The sidecar and lightmap summaries are reported, not left to the
        # log: read nothing / matched nothing / switched off all render the
        # same unlit preview, and a bake whose maps were not found renders
        # exactly like no bake -- so without them the feature can't be
        # debugged from the panel. The lightmap line is empty for a scene
        # with no committed bake.
        return result, [
            self._webxr.sidecar_summary(result),
            self._webxr.lightmap_summary(result),
        ]

    def _webxr_publish_external(self, scripts):
        """Publish the chosen GLB unchanged, through the same page and port.

        Returns ``(result, extra_lines)``, or ``None`` when the browse was
        cancelled or the file could not be served -- nothing left to report.

        None of the export rows apply here: textures, animation and the
        sidecar are questions about an export this path does not do, and the
        texture container is a re-encode a finished GLB has already answered.
        So the message names the file that went out rather than summaries that
        would all read "off" and imply something had been skipped.
        """
        path = self._webxr_browse_external()
        if not path:
            return None
        try:
            result = self._webxr.publish_file(
                path, open_browser="auto", scripts=scripts
            )
        except (OSError, ValueError, RuntimeError) as error:
            # The bridge's refusals are fix-shaped -- the file moved, or it is
            # not a .glb -- so the error IS the message.
            self.sb.message_box(str(error))
            return None
        return result, [
            f"Published <hl>{os.path.basename(path)}</hl> as authored "
            "(no export, no conversion)."
        ]
