#!/usr/bin/env python
# coding=utf-8
"""Tests for the standalone WebXR Preview panel (``slots/tools/webxr_preview.py``).

UI smoke tests cover the build-time wiring; the delivery tests run a real
loopback :class:`pythontk.PreviewServer` against a tiny GLB fixture, because
the behaviour worth pinning here is what actually reaches the page. No DCC is
needed: the host bridge is faked, which is the point of the panel.

Run::

    python tentacle/test/run_tests.py webxr_preview_panel
"""

from __future__ import annotations

import hashlib
import os
import sys
import unittest
import urllib.request
from pathlib import Path
from unittest import mock

# Offscreen, as test_compositor / test_packer do: on the native platform the
# clipboard these cases set and read is the desktop's -- a run overwrote the
# user's, and another process holding it read back as "" (two different
# clipboard asserts failed on two runs; both pass offscreen).
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pythontk as ptk
from qtpy import QtCore, QtWidgets
from qtpy.QtWidgets import QApplication

from uitk.bridge import KindFactory
from uitk.testing import TestSandbox

# A direct `python test/test_webxr_preview_panel.py` loads no conftest, so the sandbox is
# activated here too -- before the first QSettings, or tearDown's
# store.clear() would wipe the developer's live panel state. Idempotent.
TestSandbox.activate()

from pythontk.net_utils.preview import server as _preview_server


#: Browser CLASSES a launch can go through, mirroring ``TestSandbox``'s own
#: ``_LAUNCHER_TYPES``. A caller that wants a SPECIFIC browser cannot use the
#: module function -- it only ever opens the system default -- so it builds one
#: of these. Kept as the same SET the sandbox guards rather than just the one
#: the server happens to use today: that one changed under this suite once
#: already, and the failure looked like a bug in the panel.
_BROWSER_CLASSES = ("BackgroundBrowser", "GenericBrowser")


def _ensure_app() -> QApplication:
    return QApplication.instance() or QApplication(sys.argv)


class _FakeHostBridge(ptk.PreviewBridge):
    """A DCC bridge's shape without a DCC.

    Carries its own class-level deliverer exactly as ``mayatk.WebXrPreview``
    does, because that placement -- a class attribute, so the server outlives
    any one panel -- is what several of these tests are about.
    """

    payload_prefix = "test_fake_host"
    deliverer = ptk.PreviewDeliverer(title="Fake Host")
    scope_result: list = []

    def _resolve_objects(self, objects):
        return list(objects or [])

    def scope_objects(self, scope="selected"):
        return list(self.scope_result)


class _PanelTestCase(unittest.TestCase):
    """Shared fixture: a built panel, a GLB on disk, and no real browser."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.app = _ensure_app()

    @staticmethod
    def _reset_servers() -> None:
        """Release every class-level deliverer's server between tests.

        A deliverer is a CLASS attribute on its bridge on purpose -- that is
        what keeps the port and the open tab alive across panel reopens for a
        whole session. It therefore also survives between TESTS, so without
        this the version counter carries over and a case asserting 'nothing is
        served yet' sees the previous case's server.
        """
        for deliverer in (_FakeHostBridge.deliverer, ptk.FilePreviewBridge.deliverer):
            server = getattr(deliverer, "server", None)
            if server is not None:
                try:
                    server.stop()
                except Exception:  # noqa: BLE001
                    pass
            deliverer.server = None
            # The page's switch outlives a test the same way.
            deliverer.locomotion = True

    def setUp(self) -> None:
        from tentacle.tcl_standalone import WebXrPreviewUI

        self._reset_servers()

        # Ephemeral ports: the default is the production one, where a preview
        # tab the user has open would start polling a test's server.
        port = mock.patch.object(ptk.PreviewServer, "DEFAULT_PORT", 0)
        port.start()
        self.addCleanup(port.stop)

        # A push opens a browser tab on the machine running the tests. Patch
        # what LAUNCHES, not the server method, so the "was a tab opened"
        # decision is still exercised.
        #
        # BOTH routes, because there are two: the module function opens the
        # system default, and a caller that wants a SPECIFIC browser has to
        # build a browser class directly -- which `open_in_browser` now does
        # when it can find one that can enter VR. Patching only the module
        # function left that route live, and it reached `ptk.TestSandbox`'s
        # guard and raised. That is the same pair the sandbox itself patches
        # (`_LAUNCHERS` / `_LAUNCHER_TYPES`); if a third route ever appears,
        # that tuple is where it will be named.
        # A push with an empty Source File reaches the ROW's browse button,
        # which opens a MODAL file dialog: under a test run that blocks the
        # process with no output and no failure -- the same class of hazard as
        # the browser launch above, and it cost one 300s hang to learn. Guarded
        # at the DIALOG, the way the browser is guarded at what launches it: a
        # case exercising the prompt patches the option instance over the top.
        # (Not at `BrowseOption.browse`: a plain MagicMock on that class
        # crashes the process when the row is built -- see BACKLOG.md.)
        for name in ("getOpenFileName", "getOpenFileNames", "getExistingDirectory"):
            guard = mock.patch.object(
                QtWidgets.QFileDialog, name, return_value=("", "")
            )
            guard.start()
            self.addCleanup(guard.stop)

        self.opened = []
        recorder = self.opened

        class _RecordingBrowser:
            def __init__(self, *args, **kwargs):
                pass

            def open(self, url, *args, **kwargs):
                recorder.append(url)
                return True

        self._real_open = _preview_server.webbrowser.open
        self._real_classes = {
            name: getattr(_preview_server.webbrowser, name) for name in _BROWSER_CLASSES
        }
        _preview_server.webbrowser.open = lambda url, *a, **k: (
            recorder.append(url),
            True,
        )[1]
        for name in _BROWSER_CLASSES:
            setattr(_preview_server.webbrowser, name, _RecordingBrowser)

        # Nor may a share reach a real tunnel provider: it would publish this
        # machine through the user's own tailnet or account. One did, once --
        # "Auto" resolved on the real machine spawned Tailscale Funnel, which
        # refused only because the user's own share held its port. Guarded at
        # what LAUNCHES, like the browser, and at the download settle offers.
        from pythontk.core_utils.app_installer import AppInstaller
        from pythontk import AppLauncher

        tunnels = ("tailscale", "cloudflared")
        real_spawn, real_ensure = AppLauncher.spawn, AppInstaller.ensure

        def _guarded_spawn(executable, *args, **kwargs):
            stem = os.path.splitext(os.path.basename(str(executable)))[0].lower()
            if stem in tunnels:
                raise AssertionError(f"a test reached a real tunnel: {executable}")
            return real_spawn(executable, *args, **kwargs)

        def _guarded_ensure(name, *args, **kwargs):
            if name in tunnels:
                raise AssertionError(f"a test tried to download {name}")
            return real_ensure(name, *args, **kwargs)

        for guard in (
            mock.patch.object(AppLauncher, "spawn", side_effect=_guarded_spawn),
            mock.patch.object(AppInstaller, "ensure", side_effect=_guarded_ensure),
        ):
            guard.start()
            self.addCleanup(guard.stop)

        # Artifacts go through the shared store, which owns their teardown.
        self.temp = ptk.TempArtifacts("test_webxr_preview", policy="scoped")
        self.glb = self.temp.path(extension=".glb")
        # A GLB is published unchanged, so nothing here parses it; the bytes
        # only have to survive the trip intact.
        with open(self.glb, "wb") as handle:
            handle.write(b"glTF\x02\x00\x00\x00" + b"webxr-preview-fixture")
        self.digest = hashlib.md5(open(self.glb, "rb").read()).hexdigest()

        self.ui = WebXrPreviewUI()
        self.slots = self.ui.slots

        # A message box is modal too. A push that has to ASK -- a missing KTX2
        # encoder offers its managed install -- blocked the CI runner, which has
        # no toktx, until the 300s timeout killed pytest before it printed a
        # summary, and so kept the publish job red. Fail the case instead; a case
        # that expects a message replaces this, as TestTextureToolGate does.
        def _unexpected_message_box(*args, **kwargs):
            raise AssertionError(f"a test opened a modal message box: {args[:1]!r}")

        self.slots.sb.message_box = _unexpected_message_box

    def _record_log(self):
        """The panel's log lines from here on, as plain text."""
        logged = []
        real = self.slots.panel_log

        def record(text, *args, **kwargs):
            logged.append(str(text))
            return real(text, *args, **kwargs)

        self.slots.panel_log = record
        return logged

    def _pane_links(self):
        """Every link in the panel's log pane, by address."""
        links = set()
        block = self.slots.ui.txt000.document().begin()
        while block.isValid():
            fragments = block.begin()
            while not fragments.atEnd():
                fmt = fragments.fragment().charFormat()
                if fmt.isAnchor():
                    links.add(fmt.anchorHref())
                fragments += 1
            block = block.next()
        return links

    def _reopen(self, engine=None):
        """A second panel over the same QSettings store: the next DCC session."""
        from tentacle.tcl_standalone import WebXrPreviewUI

        ui = WebXrPreviewUI()
        self.addCleanup(ui.deleteLater)
        # The host injects its bridge AFTER the panel is built -- exactly what
        # tentacle's launch does (``launch(show=False)``, then ``engine =``).
        if engine is not None:
            ui.slots.engine = engine
        return ui.slots

    def tearDown(self) -> None:
        self._reset_servers()
        _preview_server.webbrowser.open = self._real_open
        for name, cls in self._real_classes.items():
            setattr(_preview_server.webbrowser, name, cls)
        self.temp.cleanup()
        store = self.ui.settings
        self.ui.deleteLater()
        self.app.processEvents()
        # Every row persists, and the sandboxed store lives for the whole run:
        # without this a box one case ticks opens ticked in the next case's
        # fresh panel. Cleared after the panel goes, so nothing re-saves.
        store.clear()
        store.sync()


class TestSourceWiring(_PanelTestCase):
    """The Source combo and which rows each source answers."""

    def test_without_a_host_only_the_file_source_is_offered(self):
        self.assertEqual(
            [key for key, _label in self.slots._sources()],
            ["file"],
            "a panel with no host must not offer scopes it cannot resolve",
        )

    def test_injecting_a_host_grows_the_shared_scope_vocabulary(self):
        self.slots.engine = _FakeHostBridge
        keys = [key for key, _label in self.slots._sources()]
        # Read off Parameters.scope_spec, so this pins that the panel does not
        # keep a private copy of the vocabulary every other bridge shares.
        self.assertEqual(keys, ["selected", "all", "visible", "file"])
        self.assertEqual(keys[-1], "file", "File on Disk stays last")

    def test_a_file_source_hides_the_export_rows(self):
        from tentacle.slots.tools._webxr_preview import parameters as params

        self.slots._select_source("file")
        visible = self.slots._relevant_param_keys()
        # A file source exports nothing, so an export row would not merely be
        # unused -- it would be lying about what the push is going to do.
        self.assertFalse(visible & params.EXPORT_KEYS)
        self.assertTrue(params.FILE_KEYS <= visible)

    def test_a_scope_source_hides_the_file_rows(self):
        from tentacle.slots.tools._webxr_preview import parameters as params

        self.slots.engine = _FakeHostBridge
        self.slots._select_source("selected")
        visible = self.slots._relevant_param_keys()
        self.assertFalse(visible & params.FILE_KEYS)
        self.assertTrue(params.EXPORT_KEYS <= visible)

    def test_include_textures_is_a_host_row(self):
        """A file's textures are whatever its FBX embedded -- the push embeds
        nothing, so the row would claim a switch it does not have."""
        self.slots._select_source("file")
        self.assertNotIn("EMBED_TEXTURES", self.slots._relevant_param_keys())
        self.slots.engine = _FakeHostBridge
        self.slots._select_source("selected")
        self.assertIn("EMBED_TEXTURES", self.slots._relevant_param_keys())


class TestSourceComboShowsOnlyAChoice(_PanelTestCase):
    """Standalone there is one source, so there is no Source combo to read; a
    host's scopes bring it back, and taking the host away hides it again."""

    def test_standalone_shows_no_source_combo(self):
        self.assertTrue(self.slots.ui.cmb000.isHidden())
        self.assertEqual(self.slots._active_source(), "file")

    def test_a_host_brings_the_combo_back_and_its_removal_hides_it(self):
        self.slots.engine = _FakeHostBridge
        self.assertFalse(self.slots.ui.cmb000.isHidden())
        self.slots.engine = None
        self.assertTrue(self.slots.ui.cmb000.isHidden())
        self.assertEqual(self.slots._active_source(), "file")


class TestGlbRowsMirrorTheExporter(_PanelTestCase):
    """The Textures rows ARE the Scene Exporter's -- nothing to keep in sync.

    The preview used to offer WebP / KTX2 and nothing else, so every push was
    cut to the web ceiling (2048 px) whatever the export was set to.
    """

    def test_one_row_per_exporter_row_with_its_label_and_table(self):
        from tentacle.slots.tools._webxr_preview import parameters as params

        options = ptk.ExportProfile.glb_options()
        self.assertEqual(
            list(params.GLB_KEYS.values()), list(ptk.ExportProfile.GLB_ROWS)
        )
        for key, row in params.GLB_KEYS.items():
            with self.subTest(row=row):
                spec = params.PARAMS[key]
                self.assertEqual(spec.label, ptk.ExportProfile.GLB_ROWS[row])
                self.assertEqual(list(spec.choices), list(options[row].items()))
                widget = self.slots._param_widgets[key]
                self.assertEqual(
                    [widget.itemText(i) for i in range(widget.count())],
                    list(options[row]),
                )

    def test_the_rows_default_to_the_exporters_defaults(self):
        """Where the Scene Exporter starts each row (the off state), so a
        fresh preview and a fresh export build the same texture pass. Pinned on
        the registry, not a live panel -- a panel restores its last session."""
        from tentacle.slots.tools._webxr_preview import parameters as params

        exporter = ptk.ExportProfile.glb_defaults()
        defaults = params.Parameters.defaults()
        for key, row in params.GLB_KEYS.items():
            with self.subTest(row=row):
                self.assertEqual(defaults[key], exporter[row])

    def _texture_rows_shown(self) -> set:
        """The texture rows on screen now, KTX2 RDO aside (its own case)."""
        from tentacle.slots.tools._webxr_preview import parameters as params

        return {
            key
            for key in params.TEXTURE_KEYS - params.KTX2_KEYS
            if not self.slots._param_rows[key].isHidden()
        }

    def test_an_fbx_source_shows_the_texture_rows(self):
        """An FBX is converted, and the texture pass re-encodes what it
        embedded -- the rows answer it as they answer a scope."""
        from tentacle.slots.tools._webxr_preview import parameters as params

        self.slots.set_source_file("C:/assets/prop.fbx")
        self.assertEqual(
            self._texture_rows_shown(), params.TEXTURE_KEYS - params.KTX2_KEYS
        )

    def test_an_empty_field_shows_none_until_an_fbx_is_chosen(self):
        """The standalone panel opens empty, and most files it is handed are
        finished GLBs: the rows come with the FBX that reads them."""
        self.slots.set_source_file("C:/assets/prop.fbx")
        self.slots.set_source_files([])
        self.assertEqual(self._texture_rows_shown(), set())

    def test_a_glb_only_source_hides_them_as_it_is_typed(self):
        """A GLB is published as authored: no pass reads a texture row, so
        none is offered -- re-evaluated as the field changes, with no push."""
        self.slots.set_source_files(["C:/a/room.glb", "C:/a/props.GLB"])
        self.assertEqual(self._texture_rows_shown(), set())
        self.slots.set_source_files(["C:/a/room.glb", "C:/a/prop.fbx"])
        self.assertTrue(self._texture_rows_shown(), "one FBX part is built")

    def test_a_scene_pushed_without_textures_hides_them(self):
        """Include Textures off, the scene's export carries no image: the
        texture pass has nothing to re-encode, so its rows go with it."""
        from tentacle.slots.tools._webxr_preview import parameters as params

        self.slots.engine = _FakeHostBridge
        self.slots._select_source("selected")
        self.slots._write_param("EMBED_TEXTURES", False)
        self.assertEqual(self._texture_rows_shown(), set())
        self.slots._write_param("EMBED_TEXTURES", True)
        self.assertEqual(
            self._texture_rows_shown(), params.TEXTURE_KEYS - params.KTX2_KEYS
        )

    def test_ktx2_rdo_shows_only_with_a_ktx2_file_type(self):
        """As the Scene Exporter shows it: ETC1S / UASTC are KTX2's encodes."""
        rdo = self.slots._param_rows["UASTC_RDO"]
        self.slots.set_source_file("C:/assets/prop.fbx")
        for value, shown in (("", False), ("webp", False), ("ktx2", True)):
            with self.subTest(texture_file_type=value):
                self.slots._write_param("TEXTURE_FILE_TYPE", value)
                self.assertIs(rdo.isHidden(), not shown)
        self.slots._write_param("TEXTURE_FILE_TYPE", ptk.ExportRun.KTX2_WITH_FALLBACK)
        self.assertFalse(rdo.isHidden())

    def test_no_row_decides_the_lighting(self):
        """Baked Reflections retired 2026-10-19: its default, the lighting
        recipe's own level, was already right, so the preview publishes the
        recipe as the export does and no Lighting section is built."""
        from tentacle.slots.tools._webxr_preview import parameters as params

        self.assertNotIn("BAKED_REFLECTIONS", params.PARAMS)
        self.assertNotIn("Lighting", {spec.section for spec in params.PARAMS.values()})
        self.assertNotIn("BAKED_REFLECTIONS", self.slots._param_widgets)


class TestPersistence(_PanelTestCase):
    """What a panel reopened in a NEW session restores, and what it must not.

    A second ``WebXrPreviewUI`` is a fresh Switchboard over the same (sandboxed)
    QSettings store -- the shape of the next DCC session (``_reopen``).
    """

    def test_the_source_choice_survives_a_new_session_with_a_host(self):
        """Regression: the combo restored before the host injected its scopes,
        so the stored choice was out of range, skipped -- and the repopulate
        that followed reset it to the first entry, every session."""
        self.slots.engine = _FakeHostBridge
        self.slots._select_source("visible")

        reopened = self._reopen(engine=_FakeHostBridge)

        self.assertEqual(reopened._active_source(), "visible")

    def test_the_file_source_survives_a_new_session_with_a_host(self):
        self.slots.engine = _FakeHostBridge
        self.slots._select_source("file")

        reopened = self._reopen(engine=_FakeHostBridge)

        self.assertEqual(reopened._active_source(), "file")

    def test_a_file_handed_over_before_the_host_is_not_overridden(self):
        """A hand-off selects File on Disk; re-applying last session's scope
        when the host's engine arrives would push the scene instead of the file
        the caller just handed over."""
        self.slots.engine = _FakeHostBridge
        self.slots._select_source("visible")

        reopened = self._reopen()
        reopened.set_source_file(self.glb)
        reopened.engine = _FakeHostBridge

        self.assertEqual(reopened._active_source(), "file")

    def test_the_viewer_scripts_survive_a_new_session(self):
        """Regression: the check list persisted on ``itemClicked`` (it carries
        the clicked item, so nothing was stored) and came back empty."""
        self.slots._write_param("VIEWER_SCRIPTS", ["inspect", "snapshot"])
        self.app.processEvents()

        reopened = self._reopen()

        self.assertEqual(
            reopened._read_param("VIEWER_SCRIPTS"), ["inspect", "snapshot"]
        )

    def test_the_source_file_is_not_persisted(self):
        """The field names one hand-off, not a preference: a path restored from
        last session would be pushed by a press meant to ask for a file."""
        self.slots.set_source_file(self.glb)
        self.assertFalse(self.slots._source_edit().restore_state)

        reopened = self._reopen()

        self.assertEqual(reopened._source_paths(), [])


class TestOneServerPerPanel(_PanelTestCase):
    """Both sources must publish to ONE server.

    Regression: the file bridge used to adopt the host's deliverer inside the
    lazy host-bridge build, which a FILE push never reaches. Each source then
    started its own server, so a file push landed on a second port while the
    footer -- and the user's open tab -- were still on the first. The push
    reported success onto a page nobody was looking at.
    """

    def test_the_file_bridge_adopts_the_hosts_deliverer(self):
        self.slots.engine = _FakeHostBridge
        self.assertIs(self.slots.bridge.deliverer, _FakeHostBridge.deliverer)

    def test_adoption_does_not_construct_the_host_bridge(self):
        # Reading the deliverer off the CLASS is what lets the footer describe
        # a server a previous panel started without instantiating a DCC bridge.
        self.slots.engine = _FakeHostBridge
        self.assertIsNone(self.slots._host_bridge)

    def test_a_file_push_lands_on_the_hosts_server(self):
        self.slots.engine = _FakeHostBridge
        host_url = _FakeHostBridge.deliverer.ensure_server().url

        self.slots.set_source_file(self.glb)
        self.slots.b000()

        self.assertEqual(
            _FakeHostBridge.deliverer.server.url,
            host_url,
            "a file push started a second server; the open tab is on the first",
        )
        self.assertEqual(
            self.opened,
            [host_url],
            "the tab that opened points somewhere other than the live server",
        )

    def test_clearing_the_engine_releases_the_hosts_deliverer(self):
        # Symmetric with adoption. Keeping it would go on publishing through
        # the previous host's server -- the same footer/push disagreement,
        # reached from the other direction.
        self.slots.engine = _FakeHostBridge
        self.slots.engine = None
        self.assertIs(self.slots.bridge.deliverer, ptk.FilePreviewBridge.deliverer)

    def test_the_template_menu_is_off_for_a_source_combo(self):
        # `template_dir` is this package's own folder, so Refresh Templates
        # would re-scan nothing and Open Templates Folder would reveal source.
        self.assertFalse(self.slots.TEMPLATE_MENU)

    def test_adoption_leaves_other_users_of_the_class_alone(self):
        # An instance attribute shadows the class one, so a FilePreviewBridge
        # built anywhere else keeps its own deliverer.
        self.slots.engine = _FakeHostBridge
        self.assertIsNot(ptk.FilePreviewBridge().deliverer, _FakeHostBridge.deliverer)


class TestLocomotionSwitch(_PanelTestCase):
    """The Locomotion row is the page's switch, applied at once.

    The page reads it on every poll, so a headset mid-session -- a share's
    guests included -- follows the box within a second. Waiting for the next
    push would cost a re-export to stop someone walking about.
    """

    def _row(self):
        return self.slots._param_widgets["LOCOMOTION"]

    def test_the_row_is_on_by_default_and_reaches_the_deliverer(self):
        self.slots.engine = _FakeHostBridge
        self.assertIs(self._row().isChecked(), True)
        self.assertIs(_FakeHostBridge.deliverer.locomotion, True)

    def test_unticking_stops_a_running_page_without_a_push(self):
        self.slots.engine = _FakeHostBridge
        server = _FakeHostBridge.deliverer.ensure_server()
        self._row().setChecked(False)
        self.assertIs(_FakeHostBridge.deliverer.locomotion, False)
        self.assertIs(server.manifest()["locomotion"], False)
        self._row().setChecked(True)
        self.assertIs(server.manifest()["locomotion"], True)

    def test_the_row_follows_the_deliverer_a_host_brings(self):
        # Unticked before any host: the file bridge's own deliverer takes it,
        # and adopting the host's hands the answer over rather than losing it.
        self._row().setChecked(False)
        self.slots.engine = _FakeHostBridge
        self.assertIs(_FakeHostBridge.deliverer.locomotion, False)

    def test_a_push_publishes_the_row_whatever_set_the_deliverer_last(self):
        self.slots.engine = _FakeHostBridge
        self._row().setChecked(False)
        _FakeHostBridge.deliverer.locomotion = True  # behind the panel's back
        self.slots.set_source_file(self.glb)
        self.slots.b000()
        manifest = _FakeHostBridge.deliverer.server.manifest()
        self.assertIs(manifest["locomotion"], False)


class TestGlbIsPublishedAsAuthored(_PanelTestCase):
    """A GLB source short-circuits the build and is served byte-identical."""

    def _push_file(self):
        self.slots.set_source_file(self.glb)
        self.slots.b000()
        return self.slots._deliverer().server

    def test_the_served_bytes_are_the_source_bytes(self):
        server = self._push_file()
        served = urllib.request.urlopen(
            f"{server.url}/{server.manifest()['asset']}"
        ).read()
        self.assertEqual(hashlib.md5(served).hexdigest(), self.digest)

    def test_the_users_own_file_is_never_moved_or_rewritten(self):
        # The deliverer publishes with move=True because the GLB is normally
        # its own scratch artifact. On this path it is the user's file, so the
        # identity build MUST hand over a copy -- this is the assertion that
        # catches a regression there, and the failure would be unrecoverable.
        self._push_file()
        self.assertTrue(os.path.isfile(self.glb), "the source file was moved away")
        self.assertEqual(
            hashlib.md5(open(self.glb, "rb").read()).hexdigest(), self.digest
        )

    def test_the_sources_own_folder_is_searched_for_its_maps(self):
        """Why the panel no longer asks for a texture folder.

        A bake names its maps by basename plus the folder they were authored
        in, and that hint goes stale the moment the project moves -- so the
        field existed to repair it. The file being previewed is the one
        location that cannot be stale, and searching it unconditionally
        answers the case the field was added for without asking anything.
        """
        self._push_file()
        self.assertIn(
            os.path.normpath(os.path.dirname(self.glb)),
            [os.path.normpath(d) for d in self.slots.bridge.lightmap_search_dirs()],
        )

    def test_a_push_logs_where_its_time_went(self):
        """The question after every slow push, answered in the panel rather
        than by a profiler: the result's stage timings, one line."""
        logged = self._record_log()
        self._push_file()
        self.assertTrue(any(line.startswith("Push took ") for line in logged), logged)

    def test_the_first_push_opens_exactly_one_tab(self):
        self._push_file()
        self.assertEqual(len(self.opened), 1)

    def test_a_second_push_reuses_the_watching_page(self):
        self._push_file()
        self._push_file()
        # "auto" opens only when nothing is watching; a fresh tab per push
        # would pile up and steal focus from the host.
        self.assertEqual(len(self.opened), 1)


class TestGuardsReportRatherThanPushBlind(_PanelTestCase):
    """Each refusal names its own cause, because they look identical on screen."""

    def test_a_dismissed_prompt_starts_no_server(self):
        # Cancelling the row's browse is an answer, not a failure: the push
        # stops where it stands, with nothing served and nothing to report.
        # A dismissal there is a no-op, so the field simply stays empty.
        from uitk import BrowseOption

        self.slots.set_source_file("")
        option = self.slots._source_edit().option_box.find_option(BrowseOption)
        with mock.patch.object(option, "browse"):
            self.slots.b000()
        self.assertIsNone(self.slots._deliverer().server)

    def test_a_missing_file_is_refused(self):
        self.slots.set_source_file(self.glb + ".nope")
        self.slots.b000()
        self.assertIsNone(self.slots._deliverer().server)

    def test_an_empty_scope_is_reported_not_exported(self):
        _FakeHostBridge.scope_result = []
        self.slots.engine = _FakeHostBridge
        self.slots._select_source("selected")
        self.slots.b000()
        # Pushing blind would collapse "nothing selected", "the scene is empty"
        # and "the export failed" into one message -- and the first two are the
        # user's own next action.
        self.assertIsNone(_FakeHostBridge.deliverer.server)

    def test_a_scope_push_without_a_host_is_reported(self):
        # Reachable when a host injects an engine, the user picks a scope, and
        # the engine is then cleared; the panel must not raise.
        self.slots.engine = _FakeHostBridge
        self.slots._select_source("selected")
        self.slots.engine = None
        self.slots.b000()
        self.assertIsNone(self.slots._deliverer().server)


class TestFooterReportsLiveState(_PanelTestCase):
    """The standing facts an option box had nowhere to put."""

    def test_it_says_so_when_nothing_is_served(self):
        self.assertIn("No preview server", self.slots._status_text())

    def test_it_names_the_version_and_url_after_a_push(self):
        self.slots.set_source_file(self.glb)
        self.slots.b000()
        text = self.slots._status_text()
        self.assertIn("v1", text)
        self.assertIn(self.slots._deliverer().server.url, text)


class TestTextureToolGate(_PanelTestCase):
    """KTX2's encoder must be OFFERED, never dead-end in a log line.

    Ported with the behaviour when the preview moved out of tentacle. The
    bridge already refuses a KTX2 push without ``toktx`` -- eagerly, before it
    pays for the sidecar and lightmap passes -- but it refuses by RAISING with
    an install URL, and a panel control that dead-ends in a URL is what the
    Scene Exporter's own KTX2 row stopped doing.
    """

    def setUp(self) -> None:
        super().setUp()
        self.answers = []
        self.slots.sb.message_box = lambda *a, **k: (
            self.answers.append(a[0]),
            "Yes" if len(a) > 1 else None,
        )[1]

    KTX2 = {"texture_file_type": "ktx2"}

    def test_webp_asks_nothing(self):
        # Probing for a tool the push will not use would ask about a control
        # the user never touched -- Original is the web default, WebP too.
        with mock.patch("pythontk.ImgUtils.ensure_ktx2_encoder") as ensure:
            for rows in ({}, {"texture_file_type": ""}, {"texture_file_type": "webp"}):
                self.assertTrue(self.slots._texture_tool_ready(rows), rows)
        ensure.assert_not_called()

    def test_ktx2_with_its_twin_asks_too(self):
        """Both KTX2 entries encode with toktx; the twin only adds a copy."""
        with mock.patch(
            "pythontk.ImgUtils.ensure_ktx2_encoder", return_value=None
        ) as ensure:
            self.assertTrue(
                self.slots._texture_tool_ready(
                    {"texture_file_type": ptk.ExportRun.KTX2_WITH_FALLBACK}
                )
            )
        ensure.assert_called_once()

    def test_ktx2_hands_the_primitive_the_panels_own_consent(self):
        seen = {}

        def _capture(prompt=None):
            seen["prompt"] = prompt
            return None

        with mock.patch("pythontk.ImgUtils.ensure_ktx2_encoder", side_effect=_capture):
            self.assertTrue(self.slots._texture_tool_ready(self.KTX2))
        self.assertTrue(callable(seen["prompt"]))

    def test_an_accepted_install_reports_the_binary_it_landed(self):
        with mock.patch(
            "pythontk.ImgUtils.ensure_ktx2_encoder", return_value="C:/toktx.exe"
        ):
            self.assertTrue(self.slots._texture_tool_ready(self.KTX2))
        self.assertTrue(any("toktx.exe" in m for m in self.answers))

    def test_an_already_installed_toktx_says_nothing(self):
        with mock.patch("pythontk.ImgUtils.ensure_ktx2_encoder", return_value=None):
            self.assertTrue(self.slots._texture_tool_ready(self.KTX2))
        self.assertEqual(self.answers, [])

    def test_a_declined_install_stops_the_push_with_the_fix(self):
        error = FileNotFoundError(
            "toktx not found; install KTX-Software from https://…"
        )
        with mock.patch("pythontk.ImgUtils.ensure_ktx2_encoder", side_effect=error):
            self.assertFalse(self.slots._texture_tool_ready(self.KTX2))
        # The refusal names the manual install, so it IS the message.
        self.assertEqual(self.answers, [str(error)])

    def test_a_declined_install_leaves_its_install_page_in_the_log(self):
        """The dialog is a toast gone in seconds; the log keeps the install
        page, as a link."""
        page = "https://github.com/KhronosGroup/KTX-Software/releases"
        error = FileNotFoundError(f"toktx not found; install KTX-Software from {page}.")
        with mock.patch("pythontk.ImgUtils.ensure_ktx2_encoder", side_effect=error):
            self.assertFalse(self.slots._texture_tool_ready(self.KTX2))
        self.assertIn(page, self._pane_links())

    def _fbx(self) -> str:
        """An FBX on disk -- the source a texture pass runs for. The gate
        stops before the build, so its bytes are never read."""
        path = self.temp.path(extension=".fbx")
        Path(path).write_bytes(b"Kaydara FBX Binary  \x00")
        return path

    def test_a_declined_install_never_reaches_the_server(self):
        error = FileNotFoundError("toktx not found")
        self.slots.set_source_file(self._fbx())
        self.slots._write_param("TEXTURE_FILE_TYPE", "ktx2")
        with mock.patch("pythontk.ImgUtils.ensure_ktx2_encoder", side_effect=error):
            self.slots.b000()
        self.assertIsNone(self.slots._deliverer().server)

    def test_a_glb_push_asks_nothing_whatever_the_file_type(self):
        """A GLB is published as authored, so no texture pass runs and no
        encoder is needed -- KTX2 left picked from a scene push must not stop
        a GLB push to offer an install it would never use."""
        self.slots.set_source_file(self.glb)
        self.slots._write_param("TEXTURE_FILE_TYPE", "ktx2")
        with mock.patch(
            "pythontk.ImgUtils.ensure_ktx2_encoder",
            side_effect=FileNotFoundError("toktx not found"),
        ) as ensure:
            self.slots.b000()
        ensure.assert_not_called()
        self.assertEqual(self.answers, [])
        self.assertIsNotNone(self.slots._deliverer().server)

    def test_a_scene_pushed_without_textures_asks_nothing(self):
        """No image rides the export, so no pass needs the encoder: the push
        goes on to the scope (reported empty here) without asking."""
        _FakeHostBridge.scope_result = []
        self.slots.engine = _FakeHostBridge
        self.slots._select_source("selected")
        self.slots._write_param("TEXTURE_FILE_TYPE", "ktx2")
        self.slots._write_param("EMBED_TEXTURES", False)
        logged = self._record_log()
        with mock.patch(
            "pythontk.ImgUtils.ensure_ktx2_encoder",
            side_effect=FileNotFoundError("toktx not found"),
        ) as ensure:
            self.slots.b000()
        ensure.assert_not_called()
        self.assertIn(self.slots.empty_scope_message("selected"), logged)

    def test_an_empty_field_is_asked_for_before_the_gate(self):
        """The gate reads what the push will build, so the file is chosen
        first -- a GLB picked at the prompt asks nothing either."""
        from uitk import BrowseOption

        self.slots.set_source_file("")
        self.slots._write_param("TEXTURE_FILE_TYPE", "ktx2")
        option = self.slots._source_edit().option_box.find_option(BrowseOption)
        pick = mock.patch.object(
            option,
            "browse",
            side_effect=lambda: self.slots._source_edit().setText(self.glb),
        )
        with pick, mock.patch("pythontk.ImgUtils.ensure_ktx2_encoder") as ensure:
            self.slots.b000()
        ensure.assert_not_called()
        self.assertIsNotNone(self.slots._deliverer().server)


class TestPushWiring(_PanelTestCase):
    """What the panel actually sends, ported from the retired tentacle tests."""

    def setUp(self) -> None:
        super().setUp()
        self.sent = []
        self.slots.bridge.push = lambda **kwargs: (
            self.sent.append(kwargs),
            {"version": 1, "url": "http://x/", "asset": "a.glb"},
        )[1]
        # The KTX2 tool gate is TestTextureToolGate's subject. Here every push
        # would otherwise ask the MACHINE: with KTX2 restored from an earlier
        # case and no toktx installed (the CI runner), each push opened the
        # install prompt -- green on a workstation, a timeout on CI.
        encoder = mock.patch("pythontk.ImgUtils.ensure_ktx2_encoder", return_value=None)
        encoder.start()
        self.addCleanup(encoder.stop)

    def test_scripts_are_an_explicit_list_even_when_none_are_ticked(self):
        self.slots.set_source_file(self.glb)
        self.slots.b000()
        # None would mean "leave the server's set alone", which would make an
        # unticked box unable to turn a script back off.
        self.assertEqual(self.sent[0]["scripts"], [])

    def test_several_source_files_are_pushed_as_the_parts_of_one_scene(self):
        """File on Disk takes several files -- the parts of one scene: ONE
        push names them all, in order, and the log names them."""
        second = Path(self.temp.path(extension=".glb"))
        second.write_bytes(Path(self.glb).read_bytes())
        self.slots.set_source_files([self.glb, str(second)])
        logged = self._record_log()
        self.slots.b000()
        self.assertEqual(len(self.sent), 1)
        self.assertEqual(self.sent[0]["objects"], [self.glb, str(second)])
        self.assertTrue(
            any(line.startswith("Sources (2 parts): ") for line in logged), logged
        )

    def test_a_missing_part_is_refused_by_name_and_nothing_pushed(self):
        """Every file is checked before the push: a typo in one must not cost
        the others their build, and the log says which."""
        gone = self.glb + ".gone"
        self.slots.set_source_files([self.glb, gone])
        logged = self._record_log()
        self.slots.b000()
        self.assertEqual(self.sent, [])
        self.assertTrue(any(gone in line for line in logged), logged)

    def test_ticked_scripts_are_sent_by_their_registered_name(self):
        from tentacle.slots.tools._webxr_preview import parameters as params

        widget = self.slots._param_widgets["VIEWER_SCRIPTS"]
        for i in range(widget.count()):
            widget.item(i).setCheckState(QtCore.Qt.Checked)
        self.slots.set_source_file(self.glb)
        self.slots.b000()
        registered = [choice[1] for choice in params.PARAMS["VIEWER_SCRIPTS"].choices]
        self.assertEqual(sorted(self.sent[0]["scripts"]), sorted(registered))

    def test_every_viewer_script_row_names_a_packaged_script(self):
        """A row whose value the server does not ship raises at push time, AFTER
        the export has been paid for -- so the registry is checked here."""
        from tentacle.slots.tools._webxr_preview import parameters as params

        values = [choice[1] for choice in params.PARAMS["VIEWER_SCRIPTS"].choices]
        self.assertIn("snapshot", values, "the Export Image row is missing")
        self.assertEqual(sorted(set(values) - set(ptk.PreviewServer.SCRIPTS)), [])

    def test_the_glb_rows_reach_the_deliverer_as_the_export_names_them(self):
        """Every row, every push, keyed as the Scene Exporter keys it -- so the
        deliverer resolves them with the exporters' own methods."""
        self.slots._write_param("TEXTURE_FILE_TYPE", "ktx2")
        self.slots._write_param("OPTIMIZE_TEXTURES", 4096)
        self.slots.set_source_file(self.glb)
        self.slots.b000()
        self.assertEqual(
            self.sent[0]["glb_options"],
            {
                "texture_file_type": "ktx2",
                "optimize_textures": 4096,
                "secondary_max_size": 0,
                "uastc_rdo": 0,
            },
        )

    def test_a_file_push_carries_no_export_switch(self):
        """Include Textures is the host's FBX export switch: left off from a
        scene push, it must not reach a file push, whose FBX already chose."""
        self.slots._write_param("EMBED_TEXTURES", False)
        self.slots.set_source_file(self.glb)
        self.slots.b000()
        self.assertNotIn("EMBED_TEXTURES", self.sent[0])

    def test_open_browser_is_always_auto(self):
        # "auto" reuses a page that can pick the version up -- including one
        # open in a headset -- rather than stealing focus with a fresh tab.
        self.slots.set_source_file(self.glb)
        self.slots.b000()
        self.assertEqual(self.sent[0]["open_browser"], "auto")

    def test_a_progress_callback_travels_with_the_push(self):
        # Named on push() rather than swept into **params, which is the
        # EXPORT bag -- there it would reach the FBX write, never the build.
        self.slots.set_source_file(self.glb)
        self.slots.b000()
        self.assertTrue(callable(self.sent[0]["progress"]))

    def _browse_option(self):
        from uitk import BrowseOption

        return self.slots._source_edit().option_box.find_option(BrowseOption)

    def _answer_the_prompt(self, path):
        """Stand in for the user picking *path* in the row's browse dialog."""
        option = self._browse_option()
        return mock.patch.object(
            option,
            "browse",
            side_effect=lambda: self.slots._source_edit().setText(path),
        )

    def test_an_empty_source_field_prompts_instead_of_refusing(self):
        """The first push has nothing chosen, and that is not an error.

        Refusing it sends the user to do by hand exactly what the dialog
        does, on the one press where what they want is unambiguous.
        """
        self.slots.set_source_file("")
        with self._answer_the_prompt(self.glb):
            self.slots.b000()
        self.assertEqual(len(self.sent), 1)
        self.assertEqual(self.sent[0]["objects"], [self.glb])

    def test_the_prompted_file_is_written_back_into_the_field(self):
        # Otherwise the next push prompts again -- the panel asking about the
        # file it is already previewing.
        self.slots.set_source_file("")
        with self._answer_the_prompt(self.glb):
            self.slots.b000()
        self.assertEqual(self.slots._source_paths(), [self.glb])

    def test_the_prompt_is_the_rows_own_browse(self):
        """One dialog, declared once, reached two ways.

        A second dialog opened from the push would carry its own copy of the
        filter, the title and the folder to start in -- three things that
        then have to be kept saying the same thing as the field's own browse
        button, and nothing would fail when they stopped.
        """
        self.slots.set_source_file("")
        with mock.patch.object(self._browse_option(), "browse") as browse:
            self.slots.b000()
        browse.assert_called_once()
        self.assertEqual(self.sent, [])  # nothing was chosen, so nothing pushed

    def test_the_row_offers_the_types_the_bridge_accepts(self):
        # A dialog that lets you pick a .obj only moves the refusal later.
        from tentacle.slots.tools._webxr_preview import parameters as params

        file_types = self._browse_option()._file_types
        for pattern in params.SOURCE_FILE_TYPES:
            with self.subTest(pattern=pattern):
                self.assertIn(pattern, file_types)

    def test_a_chosen_file_does_not_prompt_again(self):
        self.slots.set_source_file(self.glb)
        with mock.patch.object(self._browse_option(), "browse") as browse:
            self.slots.b000()
        browse.assert_not_called()


#: The link the fake tunnel prints.
_FAKE_LINK = "https://panel-share.example.test"
#: The page a fake provider's one-time step names (``fake-step``).
_STEP_PAGE = "https://step.example.test/enable"


class TestShareLink(_PanelTestCase):
    """Sharing through the panel: one server, one link, view-only.

    The Sharing row is the switch -- a provider shares, Off stops -- and its
    option box carries Share Now, Copy Link, Copy Scene Link and Stop Sharing.

    The tunnel is a fake provider -- a real child printing a link -- driven
    through pythontk's real ShareTunnel, so the path under test is the panel's
    wiring onto the server a push uses, not a mock of it.
    """

    def setUp(self):
        super().setUp()
        #: Created to take the ``fake-step-then-link`` provider's step.
        self.step_taken = self.temp.path(extension=".step")
        # The fake tunnel is a real child Python; under --in-maya ``sys.executable``
        # is maya.exe, whose ``-u -c`` would start GUI Mayas instead.
        from _host import standalone_interpreter

        python, why = standalone_interpreter()
        if python is None:
            self.skipTest(why)
        fake = {
            "label": "Fake tunnel",
            "executable": str(python),
            "args": [
                "-u",
                "-c",
                f"import time; print('{_FAKE_LINK}', flush=True); time.sleep(600)",
            ],
            "url": r"(https://panel-share\.example\.test)",
            "ready": None,
            "public": True,
            "install": "https://example.test/install",
        }
        providers = mock.patch.dict(
            ptk.ShareTunnel.PROVIDERS,
            {
                "fake": fake,
                "fake-exits": {**fake, "args": ["-c", "raise SystemExit(4)"]},
                # Prints the page a one-time step takes, then waits -- the way
                # Tailscale does with Funnel not yet enabled for the tailnet.
                "fake-step": {
                    **fake,
                    "args": [
                        "-u",
                        "-c",
                        f"import time; print('To enable, visit: {_STEP_PAGE}', "
                        "flush=True); time.sleep(600)",
                    ],
                    "action": r"https://step\.example\.test/\S+",
                },
                # The same step, then the link once it is taken -- here, once
                # the file ``self.step_taken`` names exists.
                "fake-step-then-link": {
                    **fake,
                    "args": [
                        "-u",
                        "-c",
                        "import os, time\n"
                        f"print('To enable, visit: {_STEP_PAGE}', flush=True)\n"
                        f"while not os.path.exists({self.step_taken!r}):\n"
                        "    time.sleep(0.05)\n"
                        f"print('{_FAKE_LINK}', flush=True)\n"
                        "time.sleep(600)",
                    ],
                    "action": r"https://step\.example\.test/\S+",
                },
            },
        )
        providers.start()
        self.addCleanup(providers.stop)
        # This machine's alias config must not leak into the case.
        env = mock.patch.dict(
            os.environ,
            {ptk.PreviewServer.ALIAS_ENV: "", ptk.PreviewServer.ALIAS_URL_ENV: ""},
        )
        env.start()
        self.addCleanup(env.stop)
        self.messages = []
        self.slots.sb.message_box = lambda text, *a, **k: self.messages.append(text)
        # Every new link is checked (`_verify_share`), and the fake link names
        # no real host: the check answers here, never over DNS, and a case
        # about the check sets what it answers (`_ping`).
        ping = mock.patch.object(
            self.slots.bridge, "ping_share", return_value={"ok": True, "ms": 1.0}
        )
        ping.start()
        self.addCleanup(ping.stop)
        # These cases push for real: the share rides the server a push starts.
        # The panel restores its rows between cases, so a KTX2 row an earlier
        # case left (TestPushWiring writes one) sent the push through the KTX2
        # tool gate, which on a runner without toktx -- CI -- stopped it before
        # any server started. Textures are not this class's subject: the row
        # goes back to its default, which needs no tool.
        self.slots._write_param("TEXTURE_FILE_TYPE", "")

    def _share(self, provider="fake"):
        """Share Now, pressed on the row's option box -- the wiring included."""
        with mock.patch.object(ptk.ShareTunnel, "settle", return_value=provider):
            self._action("btn_share_now").click()

    def _row(self):
        return self.slots._param_widgets["SHARE_VIA"]

    def _action(self, name):
        return getattr(self._row().option_box.menu, name)

    def _pump_until(self, condition, timeout=20.0):
        """Run the UI loop until *condition* holds; fail when it never does."""
        import time

        deadline = time.monotonic() + timeout
        while not condition():
            self.assertLess(time.monotonic(), deadline, "the panel never got there")
            self.app.processEvents()
            time.sleep(0.02)

    def _wait_on_the_step(self):
        """Share through a provider that stops on its step; the panel is free
        again while the share waits for it. The dialog is answered Not Now."""
        self.slots.sb.confirm = lambda *args, **kwargs: False
        self._share(provider="fake-step-then-link")
        self.assertTrue(self.slots._scenes[0].pending, "the share did not wait")
        self.assertIsNone(self.slots._server().share_info())

    def test_the_row_offers_every_provider_pythontk_drives(self):
        """A registry, not a list kept here: a provider added upstream
        arrives as an entry by itself."""
        from tentacle.slots.tools._webxr_preview import parameters as params

        values = [entry[1] for entry in params.PARAMS["SHARE_VIA"].choices]
        self.assertEqual(values[:2], ["off", "auto"])
        self.assertEqual(
            set(values[2:]),
            {name for name in ptk.ShareTunnel.PROVIDERS if not name.startswith("fake")},
        )

    def test_the_row_answers_every_source(self):
        self.slots.set_source_file(self.glb)
        self.assertIn("SHARE_VIA", self.slots._relevant_param_keys())
        self.slots.engine = _FakeHostBridge
        self.slots._select_source("selected")
        self.assertIn("SHARE_VIA", self.slots._relevant_param_keys())

    def test_the_sharing_actions_live_on_the_rows_option_box(self):
        """Beside the switch they act on, not in the header menu."""
        handlers = {item[3] for item in self.slots.HEADER_MENU_ITEMS}
        self.assertFalse(handlers & {"share_link", "stop_sharing"})
        for name in (
            "btn_share_now",
            "btn_copy_share_link",
            "btn_test_share_link",
            "btn_copy_scene_link",
            "btn_stop_sharing",
        ):
            self.assertIsNotNone(self._action(name), name)

    def test_the_row_starts_off_each_session(self):
        """A link is a door to this machine: a session opens it only when
        asked, so a row left on yesterday does not share today's first push."""
        with mock.patch.object(ptk.ShareTunnel, "settle", return_value="fake"):
            self.slots._write_param("SHARE_VIA", "auto")
        self.assertIsNotNone(self.slots._server().share_info())
        # Down with the row left on: what is left to restore is the setting.
        self.slots._server().unshare()

        reopened = self._reopen()

        self.assertEqual(reopened._sharing_choice(), "off")

    def _remember(self, slots, on=True):
        """Tick (or untick) Remember Sharing on *slots*' Sharing option box."""
        box = slots._param_widgets["SHARE_VIA"].option_box.menu.chk_remember_sharing
        box.setChecked(on)
        return box

    def test_remember_sharing_brings_the_row_back_without_opening_a_link(self):
        """Remembered, the row is a preference: the next session opens on it,
        and nothing is shared until a push (or Share Now) asks."""
        self._remember(self.slots)
        with mock.patch.object(ptk.ShareTunnel, "settle", return_value="fake"):
            self.slots._write_param("SHARE_VIA", "auto")
        # A new session: no server, as in a fresh host.
        self.slots._server().stop()

        reopened = self._reopen()

        self.assertEqual(reopened._sharing_choice(), "auto")
        self.assertTrue(reopened._param_widgets["SHARE_VIA"].isEnabled())
        self.assertIsNone(reopened._server().share_info(), "shared on open")
        self.assertFalse(reopened._scenes[0].pending)
        self.assertIn("shares with the first push", reopened._status_text())

    def test_a_remembered_row_shares_with_the_first_push(self):
        self._remember(self.slots)
        with mock.patch.object(ptk.ShareTunnel, "settle", return_value="fake"):
            self.slots._write_param("SHARE_VIA", "auto")
        self.slots._server().unshare()
        reopened = self._reopen()
        reopened.sb.message_box = self.slots.sb.message_box
        reopened.set_source_file(self.glb)
        ping = mock.patch.object(
            reopened.bridge, "ping_share", return_value={"ok": True, "ms": 1.0}
        )
        with ping, mock.patch.object(ptk.ShareTunnel, "settle", return_value="fake"):
            reopened.b000()
        self.assertEqual(reopened._server().share_url, _FAKE_LINK)

    def test_the_remember_option_is_itself_remembered_and_off_forgets(self):
        self._remember(self.slots)
        reopened = self._reopen()
        box = reopened._param_widgets["SHARE_VIA"].option_box.menu
        self.assertTrue(box.chk_remember_sharing.isChecked())
        with mock.patch.object(ptk.ShareTunnel, "settle", return_value="fake"):
            reopened._write_param("SHARE_VIA", "auto")
        reopened._server().unshare()
        self._remember(reopened, on=False)
        self.assertEqual(self._reopen()._sharing_choice(), "off")

    def test_a_panel_opened_on_a_live_share_shows_it_on_the_row(self):
        """The server outlives the panel: reopened while a share is up, the
        row shows its provider rather than Off beside a live link."""
        fake = ptk.ShareTunnel.PROVIDERS["fake"]
        with mock.patch.dict(ptk.ShareTunnel.PROVIDERS, {"cloudflared": fake}):
            with mock.patch.object(
                ptk.ShareTunnel, "settle", return_value="cloudflared"
            ):
                self.slots._write_param("SHARE_VIA", "cloudflared")
            self.assertEqual(self.slots._server().share_url, _FAKE_LINK)
            reopened = self._reopen()
            self.assertEqual(reopened._sharing_choice(), "cloudflared")
            self.assertEqual(self.slots._server().share_url, _FAKE_LINK)

    def test_picking_another_provider_while_one_waits_on_its_step_switches(self):
        """The wait was for one provider: asked for another, the panel ends
        it and shares there -- not the first one's page offered again."""
        self._wait_on_the_step()
        asked = []
        self.slots.sb.confirm = lambda question, *a, **k: asked.append(question)
        self.slots._share("fake", interactive=True)
        self.assertEqual(asked, [], "the first provider's step was offered again")
        self.assertEqual(self.slots._server().share_url, _FAKE_LINK)
        self.assertFalse(self.slots._scenes[0].pending)
        Path(self.step_taken).touch()  # the old wait's step, taken late
        self._pump_until(lambda: True)
        self.assertEqual(self.slots._server().share_url, _FAKE_LINK)

    def test_picking_a_provider_shares_at_once_and_off_takes_it_down(self):
        with mock.patch.object(ptk.ShareTunnel, "settle", return_value="fake"):
            self.slots._write_param("SHARE_VIA", "auto")
        server = self.slots._server()
        self.assertEqual(server.share_url, _FAKE_LINK)
        self.assertEqual(QApplication.clipboard().text(), _FAKE_LINK)

        self.slots._write_param("SHARE_VIA", "off")

        self.assertIsNone(server.share_info())
        self.assertTrue(server.is_running, "the owner's page lost its server")

    def test_with_sharing_on_every_push_keeps_the_link_up_and_logs_it(self):
        """The same link each push -- a guest's page picks the push up -- and a
        share whose client dropped is brought back by the next one."""
        self.slots.set_source_file(self.glb)
        with mock.patch.object(ptk.ShareTunnel, "settle", return_value="fake"):
            self.slots._write_param("SHARE_VIA", "auto")
            logged = self._record_log()
            self.slots.b000()
            server = self.slots._server()
            self.assertTrue(any(_FAKE_LINK in line for line in logged), logged)
            first = server._tunnel._process

            first.kill()
            first.wait(timeout=10)
            self.assertIsNone(server.share_info())
            logged.clear()
            self.slots.b000()

        self.assertEqual(server.share_url, _FAKE_LINK)
        self.assertIsNot(
            server._tunnel._process, first, "the dropped share stayed down"
        )
        self.assertTrue(any("Shared at" in line for line in logged), logged)
        self.assertEqual(self.messages, [], "a push put a share in a dialog")

    def test_with_sharing_off_a_push_shares_nothing(self):
        self.slots.set_source_file(self.glb)
        self.slots.b000()
        self.assertIsNone(self.slots._server().share_info())

    def test_a_push_share_that_fails_is_logged_not_put_in_a_dialog(self):
        """The row changed interactively; a push is not the moment to
        interrupt, and the next push tries again."""
        self.slots.set_source_file(self.glb)
        with mock.patch.object(ptk.ShareTunnel, "settle", return_value="fake-exits"):
            self.slots._write_param("SHARE_VIA", "auto")
            self.messages.clear()
            logged = self._record_log()
            self.slots.b000()
        self.assertEqual(self.messages, [])
        self.assertTrue(any("Sharing failed" in line for line in logged), logged)

    def test_stop_sharing_on_the_option_box_turns_the_row_off(self):
        self._share()
        server = self.slots._server()
        self._action("btn_stop_sharing").click()
        self.assertEqual(self.slots._sharing_choice(), "off")
        self.assertIsNone(server.share_info())

    def test_a_providers_one_time_step_is_offered_not_dead_ended(self):
        """Funnel not yet enabled for the tailnet: the page that enables it is
        offered and opened on a yes -- not an error dialog to copy a link from."""
        asked = []
        self.slots.sb.confirm = lambda question, *a, **k: asked.append(question) or True
        self._share(provider="fake-step")
        self.assertEqual(len(asked), 1)
        self.assertIn(_STEP_PAGE, self.opened)
        self.assertEqual(self.messages, [], "an offer, not an error")
        self.assertIsNone(self.slots._server().share_info())

    def test_a_push_logs_a_providers_step_and_asks_nothing(self):
        """The row asked once; a push is not the moment to ask again."""
        asked = []
        self.slots.sb.confirm = lambda question, *a, **k: (
            asked.append(question) or False
        )
        self.slots.set_source_file(self.glb)
        with mock.patch.object(ptk.ShareTunnel, "settle", return_value="fake-step"):
            self.slots._write_param("SHARE_VIA", "auto")
            logged = self._record_log()
            self.slots.b000()
        self.assertEqual(len(asked), 1, "the push asked again")
        self.assertTrue(any(_STEP_PAGE in line for line in logged), logged)
        self.assertNotIn(_STEP_PAGE, self.opened)

    def test_once_the_step_is_taken_the_link_comes_up_by_itself(self):
        """Reported: Funnel enabled in the browser, and still no link -- the
        share had given up on the step, and the retry it asked for was easy to
        miss. It waits on the step in the background now, the panel free
        meanwhile, and the link arrives with nothing pressed."""
        self._wait_on_the_step()
        self.assertIn(_STEP_PAGE, self._pane_links(), "the step page is not a link")
        Path(self.step_taken).touch()  # enabled, in the browser
        server = self.slots._server()
        self._pump_until(lambda: not self.slots._scenes[0].pending)
        self.assertEqual(server.share_url, _FAKE_LINK)
        self.assertEqual(QApplication.clipboard().text(), _FAKE_LINK)
        self.assertIn(_FAKE_LINK, self._pane_links())
        self.assertEqual(self.messages, [])

    def test_a_step_never_taken_ends_the_wait_and_names_the_page(self):
        """The wait is bounded; when it runs out the log says the share
        stopped waiting and where the step is -- no dialog, since whoever
        started it may be long gone."""
        with mock.patch.object(ptk.ShareTunnel, "_STEP_WAIT", 1.0):
            self._wait_on_the_step()
            logged = self._record_log()
            self._pump_until(lambda: not self.slots._scenes[0].pending, timeout=15)
        self.assertTrue(
            any("stopped waiting" in line and _STEP_PAGE in line for line in logged),
            logged,
        )
        self.assertIsNone(self.slots._server().share_info())
        self.assertEqual(self.messages, [])

    def test_turning_sharing_off_while_it_waits_on_the_step_ends_the_wait(self):
        self._wait_on_the_step()
        logged = self._record_log()
        self.slots._write_param("SHARE_VIA", "off")
        self._pump_until(lambda: not self.slots._scenes[0].pending, timeout=10)
        Path(self.step_taken).touch()  # taken after all: nothing comes up
        self.app.processEvents()
        self.assertIsNone(self.slots._server().share_info())
        self.assertFalse(any("failed" in line for line in logged), logged)
        self.assertEqual(self.messages, [])

    def test_a_push_while_the_share_waits_names_the_step_again(self):
        self.slots.set_source_file(self.glb)
        self._wait_on_the_step()
        logged = self._record_log()
        self.slots.b000()
        self.assertTrue(any(_STEP_PAGE in line for line in logged), logged)
        self.assertTrue(self.slots._scenes[0].pending, "the push dropped the wait")

    def test_copy_link_with_the_row_on_brings_the_link_up(self):
        """Reported: with the row on and its link down, Copy Link said to
        pick a provider -- the one already picked. It shares now, and the link
        is copied as it arrives."""
        with mock.patch.object(ptk.ShareTunnel, "settle", return_value="fake-exits"):
            self.slots._write_param("SHARE_VIA", "auto")  # on, but its share failed
        logged = self._record_log()
        QApplication.clipboard().setText("")
        with mock.patch.object(ptk.ShareTunnel, "settle", return_value="fake"):
            self._action("btn_copy_share_link").click()
        self.assertEqual(QApplication.clipboard().text(), _FAKE_LINK)
        self.assertFalse(any("pick a provider" in line for line in logged), logged)

    def _open_as_guest(self, tab="guest-tab-1"):
        """A guest's page polling the share, the way the tunnel forwards it."""
        server = self.slots._server()
        request = urllib.request.Request(
            f"http://127.0.0.1:{server.guest_port}/manifest.json?id={tab}",
            headers={"Host": _FAKE_LINK.split("://", 1)[1]},
        )
        with urllib.request.urlopen(request, timeout=10) as response:
            self.assertEqual(response.status, 200)

    def test_every_launch_link_is_followed_by_a_copy_link(self):
        """Asked for: each page address the log gives -- the owner's page and
        the share link -- carries a [copy] link that puts it on the clipboard.
        Said once: pythontk's own "Sharing the preview at" stays out of the
        pane, and a new link's check is not announced before its answer."""
        from urllib.parse import parse_qs, urlsplit

        self._ping(ms=42.0, route="public")
        self.slots.set_source_file(self.glb)
        pane = self.slots.ui.txt000
        pane.clear()
        with mock.patch.object(ptk.ShareTunnel, "settle", return_value="fake"):
            self.slots._write_param("SHARE_VIA", "auto")
            # THIS share's answer (its route): every case shares the same fake
            # link, so an earlier case's check still in flight passes the
            # still-shared guard and can log its "Link checked" first (CI,
            # 2026-10-24: "(1 ms)", then the push, then no "public DNS").
            self._pump_until(lambda: "public DNS" in pane.toPlainText())
            self.slots.b000()
        copies = {
            parse_qs(urlsplit(href).query)["text"][0]: href
            for href in self._pane_links()
            if href.startswith("action://copy")
        }
        local = self.slots._server().url
        self.assertEqual(set(copies), {_FAKE_LINK, local})

        text = pane.toPlainText()
        self.assertEqual(text.count(f"{_FAKE_LINK} [copy]"), 2, text)  # share + push
        self.assertIn(f"{local} [copy]", text)
        self.assertNotIn("Sharing the preview at", text)
        self.assertNotIn("Checking the link", text)
        self.assertNotIn("stranger", text)
        self.assertIn("public DNS", text)

        QApplication.clipboard().setText("")
        pane.anchorClicked.emit(QtCore.QUrl(copies[_FAKE_LINK]))
        self.assertEqual(QApplication.clipboard().text(), _FAKE_LINK)

    def test_a_push_says_who_has_the_link_open_never_a_bare_zero(self):
        """Reported: "(0 watching)" read like a counter stuck at zero. It
        counts the guest tabs open right now -- a push resets nothing -- so
        with the link unopened the line says so, and a guest shows by count."""
        self.slots.set_source_file(self.glb)
        with mock.patch.object(ptk.ShareTunnel, "settle", return_value="fake"):
            self.slots._write_param("SHARE_VIA", "auto")
            logged = self._record_log()
            self.slots.b000()
            live = [line for line in logged if line.startswith("Share link:")]
            self.assertEqual(len(live), 1, logged)
            self.assertIn("no guest has it open", live[0])
            self.assertNotIn("0 watching", live[0])

            self._open_as_guest()
            logged.clear()
            self.slots.b000()
        live = [line for line in logged if line.startswith("Share link:")]
        self.assertEqual(len(live), 1, logged)
        self.assertIn("1 guest watching", live[0])

    def test_the_footer_counts_a_guest_without_the_panel_doing_anything(self):
        """The footer's count moved only when the panel acted -- a guest who
        opened the link after the push stayed "0 guests" until the next one.
        It re-reads while the panel is open."""
        self._share()
        footer = self.slots.ui.footer
        self.assertIn("(0 guests)", footer.statusText())
        self.slots.ui.show()
        self.addCleanup(self.slots.ui.hide)
        self.slots._status_timer.setInterval(50)
        self._open_as_guest()
        self._pump_until(lambda: "(1 guest)" in footer.statusText(), timeout=5)

    def test_the_addresses_a_push_gives_are_links(self):
        self.slots.set_source_file(self.glb)
        self.slots.b000()
        self.assertIn(self.slots._server().url, self._pane_links())

    def test_a_refused_share_leaves_its_install_page_in_the_log(self):
        """The dialog is a toast gone in seconds; the log keeps the page."""
        absent = {
            **ptk.ShareTunnel.PROVIDERS["fake"],
            "executable": "no-such-tunnel-cli-xyz",
            "paths": (),
        }
        with mock.patch.dict(ptk.ShareTunnel.PROVIDERS, {"fake-absent": absent}):
            self.slots._share("fake-absent", interactive=True)
        self.assertEqual(len(self.messages), 1)
        self.assertIn("https://example.test/install", self._pane_links())

    def test_copy_link_copies_the_live_link(self):
        self._share()
        QApplication.clipboard().setText("")
        self._action("btn_copy_share_link").click()
        self.assertEqual(QApplication.clipboard().text(), _FAKE_LINK)

    def test_copy_scene_link_copies_the_shares_scene_as_data(self):
        """What to send a developer whose agent compares this scene with
        their own: the share's scene.json, which answers through the tunnel."""
        self.slots.set_source_file(self.glb)
        self.slots.b000()
        self._share()
        QApplication.clipboard().setText("")
        self._action("btn_copy_scene_link").click()
        self.assertEqual(QApplication.clipboard().text(), f"{_FAKE_LINK}/scene.json")
        self.assertIn(f"{_FAKE_LINK}/scene.json", self._pane_links())

    def test_copy_scene_link_unshared_is_this_machines_and_never_shares(self):
        """Nothing shared: the link on this machine, said to be local -- and
        no share brought up behind the user's back."""
        logged = self._record_log()
        QApplication.clipboard().setText("")
        self._action("btn_copy_scene_link").click()
        self.assertEqual(QApplication.clipboard().text(), "")
        self.assertTrue(any("push once" in line for line in logged), logged)

        self.slots.set_source_file(self.glb)
        self.slots.b000()
        logged.clear()
        self._action("btn_copy_scene_link").click()
        server = self.slots._server()
        self.assertEqual(QApplication.clipboard().text(), server.scene_url)
        self.assertTrue(any("this machine only" in line for line in logged), logged)
        self.assertIsNone(server.share_info())

    def test_share_link_shares_the_one_server_and_copies_the_link(self):
        self.slots.set_source_file(self.glb)
        self.slots.b000()  # the server a push made
        pushed_to = self.slots._server()

        self._share()

        self.assertIs(
            self.slots._server(), pushed_to, "sharing started a second server"
        )
        self.assertEqual(pushed_to.share_url, _FAKE_LINK)
        self.assertEqual(QApplication.clipboard().text(), _FAKE_LINK)
        self.assertIn(f"shared at {_FAKE_LINK} (0 guests)", self.slots._status_text())
        self.assertEqual(self.messages, [])

    def _ping(self, **result):
        """The bridge's ping answering *result* from here on (see setUp)."""
        self.slots.bridge.ping_share.return_value = {"ok": True, **result}

    def test_a_new_link_is_checked_and_the_log_says_it_answers(self):
        """The share is up when the provider says so -- and checked from here
        as a guest's page asks for it, the answer in the log."""
        self._ping(ms=42.0)
        logged = self._record_log()
        self._share()
        # THIS share's answer: an earlier case's check on the same fake link
        # can log its own "Link checked" first.
        self._pump_until(lambda: any("(42 ms)" in line for line in logged))
        self.assertTrue(any("(42 ms)" in line for line in logged), logged)

    def test_test_link_says_whether_a_guest_can_reach_the_share(self):
        """Test Link asks again -- and says when there is nothing to ask."""
        logged = self._record_log()
        self._action("btn_test_share_link").click()
        self.assertTrue(any("Nothing is being shared" in line for line in logged))
        self._share()
        self._pump_until(lambda: any("Link checked" in line for line in logged))
        self._ping(ok=False, error="HTTP 502 Bad Gateway")
        logged.clear()
        self._action("btn_test_share_link").click()
        self._pump_until(lambda: any("did not answer" in line for line in logged))
        self.assertTrue(any("HTTP 502 Bad Gateway" in line for line in logged))
        self.assertEqual(self.messages, [], "a failed check put up a dialog")

    def test_private_link_reaches_the_share_and_reshares_when_flipped(self):
        """Private Link shares under a fresh random path; flipped while
        shared, the link comes up again the new way -- a new link, copied."""

        def restore():
            # The row persists, and a later case must not share privately.
            # Sharing off FIRST, so turning privacy back off shares nothing.
            self.slots._write_param("SHARE_VIA", "off")
            self.slots._write_param("SHARE_PRIVATE", False)

        self.addCleanup(restore)
        self._share()
        self.assertIs(self.slots._server().share_info()["private"], False)
        with mock.patch.object(ptk.ShareTunnel, "settle", return_value="fake"):
            self.slots._write_param("SHARE_PRIVATE", True)
        info = self.slots._server().share_info()
        self.assertIs(info["private"], True)
        self.assertTrue(info["url"].startswith(_FAKE_LINK + "/"), info["url"])
        self.assertEqual(QApplication.clipboard().text(), info["url"])

    def test_private_link_flipped_while_a_share_waits_on_its_step_restarts_it(self):
        """The wait was opened for the other kind of link. Flipped, it must
        not come up as that kind once the step is taken -- a stable link where
        a disposable one was asked for -- so it starts again, private, rather
        than the old wait's step being offered again."""

        def restore():
            self.slots._write_param("SHARE_VIA", "off")  # first: see above
            self.slots._write_param("SHARE_PRIVATE", False)

        self.addCleanup(restore)
        self._wait_on_the_step()
        with mock.patch.object(
            ptk.ShareTunnel, "settle", return_value="fake-step-then-link"
        ):
            self.slots._write_param("SHARE_PRIVATE", True)
        self.assertTrue(self.slots._scenes[0].pending, "the share stopped waiting")
        Path(self.step_taken).touch()  # enabled, in the browser
        self._pump_until(lambda: not self.slots._scenes[0].pending)
        info = self.slots._server().share_info()
        self.assertIsNotNone(info, "the restarted share never came up")
        self.assertIs(info["private"], True)

    def test_a_panel_reopened_on_a_private_share_keeps_its_link(self):
        """The server outlives the panel: reopened while a private share is
        up, the row shows it and the link stays -- a guest holding it keeps
        it, rather than the reopen sharing again under a new one."""

        def restore():
            self.slots._write_param("SHARE_VIA", "off")
            self.slots._write_param("SHARE_PRIVATE", False)

        self.addCleanup(restore)
        self.slots._write_param("SHARE_PRIVATE", True)  # Off: shares nothing yet
        # A provider the row lists, so the reopened row can show it.
        fake = ptk.ShareTunnel.PROVIDERS["fake"]
        with mock.patch.dict(ptk.ShareTunnel.PROVIDERS, {"cloudflared": fake}):
            with mock.patch.object(
                ptk.ShareTunnel, "settle", return_value="cloudflared"
            ):
                self.slots._write_param("SHARE_VIA", "cloudflared")
                url = self.slots._server().share_info()["url"]
                self.assertTrue(url.startswith(_FAKE_LINK + "/"), url)
                reopened = self._reopen()
                self.app.processEvents()
            self.assertEqual(reopened._sharing_choice(), "cloudflared")
            self.assertEqual(self.slots._server().share_info()["url"], url)

    def test_share_link_before_any_push_starts_serving(self):
        """A link can go out before the first model does."""
        self._share()
        self.assertEqual(self.slots._server().share_url, _FAKE_LINK)
        self.assertEqual(self.opened, [], "sharing must not open a tab")

    def test_a_refused_provider_stops_before_anything_starts(self):
        """Declined install, or none possible: settle has already said why."""
        self._share(provider=None)
        self.assertIsNone(self.slots._server())

    def test_a_failed_share_leads_with_the_next_step(self):
        self._share(provider="fake-exits")
        self.assertEqual(len(self.messages), 1)
        self.assertIn("exited (code 4)", self.messages[0])
        self.assertNotIn("\n", self.messages[0], "the dialog carries the one line")
        self.assertIsNone(self.slots._server().share_info())

    def test_stop_sharing_takes_the_link_down_and_leaves_the_page(self):
        self._share()
        server = self.slots._server()
        self.slots.stop_sharing()
        self.assertIsNone(server.share_info())
        self.assertTrue(server.is_running, "the owner's page lost its server")
        self.assertNotIn("shared at", self.slots._status_text())

    def test_the_share_waits_off_the_ui_thread(self):
        """A share waits on its provider and then on public DNS -- 6-18 s for
        a quick tunnel's new name -- and on the UI thread that froze the panel,
        and the DCC hosting it, for the whole wait. It runs on a worker while
        the progress tick keeps the host's loop turning; a second press landing
        in that time (a tick is where one would) opens no second share."""
        import threading
        import time
        from contextlib import contextmanager

        calls, ticks = [], []

        def slow_share(**kwargs):
            calls.append(threading.current_thread())
            time.sleep(0.5)
            return {"url": _FAKE_LINK, "public": True, "alias_error": None}

        def tick(*args, **kwargs):
            ticks.append(threading.current_thread())
            if len(ticks) == 1:
                self.slots.share_link()  # a second press, mid-share
            return True

        @contextmanager
        def progress(*args, **kwargs):
            yield tick

        with (
            mock.patch.object(self.slots.bridge, "share", side_effect=slow_share),
            mock.patch.object(self.slots.sb, "progress", progress),
        ):
            self._share()

        self.assertEqual(len(calls), 1, "a second press opened a second share")
        self.assertIsNot(calls[0], threading.main_thread(), "shared on the UI thread")
        self.assertGreater(len(ticks), 3, "the panel was not kept turning")
        self.assertTrue(all(t is threading.main_thread() for t in ticks))
        self.assertEqual(QApplication.clipboard().text(), _FAKE_LINK)

    # ------------------------------------------------------------ scenes
    def _ping_every_scene(self, **result):
        """Every added scene's bridge answers its link check with *result*
        (the first scene's is set up in setUp)."""
        ping = mock.patch.object(
            ptk.FilePreviewBridge,
            "ping_share",
            return_value={"ok": True, "ms": 1.0, **result},
        )
        ping.start()
        self.addCleanup(ping.stop)

    def _two_scenes(self):
        """The fixture as scene 1 and scene 2 -- the + pressed -- pushed."""
        self._ping_every_scene()
        self.slots.set_source_file(self.glb)
        self.slots._add_scene_button.click()
        scene = self.slots._scenes[1]
        KindFactory.set_value(scene.row[1], [self.glb])
        self.slots.b000()
        return scene

    def test_the_plus_adds_a_scene_with_a_page_and_server_of_its_own(self):
        """Asked for: several scenes live at once, each its own page and
        link. The + adds a row; a push publishes both, apart."""
        scene = self._two_scenes()
        labels = [self.slots._param_labels["SOURCE_FILE"].text(), scene.row[2].text()]
        self.assertEqual(labels, ["Scene 1:", "Scene 2:"])
        first, second = self.slots._server(), scene.server
        self.assertIsNotNone(second, "the added scene was not pushed")
        self.assertIsNot(first, second)
        self.assertNotEqual(first.url, second.url)
        self.assertIn(second.url, self.opened, "the scene's page did not open")

        scene.row[0].findChild(QtWidgets.QPushButton).click()  # its -

        self.assertEqual(len(self.slots._scenes), 1)
        self.assertFalse(second.is_running, "a removed scene kept serving")
        self.assertEqual(
            self.slots._param_labels["SOURCE_FILE"].text(), "Source Files:"
        )

    def test_an_empty_added_scene_is_left_out_of_the_push(self):
        self.slots.set_source_file(self.glb)
        scene = self.slots.add_scene()
        self.slots.b000()
        self.assertIsNotNone(self.slots._server())
        self.assertIsNone(scene.server)

    def test_each_scene_shares_at_a_link_of_its_own(self):
        """One switch, a link per scene; Copy Link copies them all."""
        scene = self._two_scenes()
        with mock.patch.object(ptk.ShareTunnel, "settle", return_value="fake"):
            self.slots._write_param("SHARE_VIA", "auto")
        first, second = self.slots._server().share_info(), scene.share_info()
        self.assertIsNotNone(first)
        self.assertIsNotNone(second)
        self.assertNotEqual(first["guest_url"], second["guest_url"])
        QApplication.clipboard().setText("")
        self._action("btn_copy_share_link").click()
        self.assertEqual(QApplication.clipboard().text().splitlines(), [_FAKE_LINK] * 2)
        self._action("btn_stop_sharing").click()
        self.assertIsNone(scene.share_info())

    def test_only_the_first_scene_keeps_the_stable_alias(self):
        """A second share writing the alias would take it from the first --
        whose stop would then say the share ended while the other is live."""
        scene = self._two_scenes()
        asked = {}
        for index, each in enumerate(self.slots._scenes):
            real = each.bridge.share

            def record(*args, _index=index, _real=real, **kwargs):
                asked[_index] = kwargs.get("alias")
                return _real(*args, **kwargs)

            each.bridge.share = record
        with mock.patch.object(ptk.ShareTunnel, "settle", return_value="fake"):
            self.slots._write_param("SHARE_VIA", "auto")
        self.assertEqual(asked, {0: None, 1: False})
        self.assertIsNotNone(scene.share_info())

    def test_a_scene_added_while_sharing_shares_with_its_first_push(self):
        """Sharing turned on first, the scene after: it is shared as soon as
        it serves -- whichever came first."""
        self._ping_every_scene()
        self.slots.set_source_file(self.glb)
        with mock.patch.object(ptk.ShareTunnel, "settle", return_value="fake"):
            self.slots._write_param("SHARE_VIA", "auto")
            scene = self.slots.add_scene([self.glb])
            self.assertIsNone(scene.share_info(), "shared before it served")
            self.slots.b000()
        self.assertIsNotNone(scene.share_info())
        self.assertIn("Scene 2", self.slots._status_text())

    # ------------------------------------------------------------ reachability
    def _record_levels(self):
        """``[(text, level), ...]`` the panel logs from here on."""
        logged = []
        real = self.slots.panel_log

        def record(text, level="info"):
            logged.append((str(text), level))
            return real(text, level)

        self.slots.panel_log = record
        return logged

    def test_a_link_no_one_else_can_open_is_said_in_red_and_rechecked(self):
        """Reported: a share looked up while no guest could open it -- a new
        Tailscale Funnel name reaches public DNS minutes later. Said in red,
        in the log and the footer, and checked again until it opens."""
        unreachable = "public DNS does not have the link's name"
        self._ping(ok=False, error=unreachable)
        logged = self._record_levels()
        with mock.patch.object(type(self.slots), "RECHECK_MS", 50):
            self._share()
            self._pump_until(lambda: any(lv == "critical" for _t, lv in logged))
        red = [text for text, level in logged if level == "critical"]
        self.assertIn("NOT REACHABLE FROM OUTSIDE", red[0])
        self.assertIn("Cloudflare quick tunnel in the Sharing row", red[0])
        self.assertEqual(self.slots.ui.footer._status_level, "error")
        self.assertIn("NOT reachable", self.slots._status_text())
        self.assertIsNotNone(self.slots._scenes[0].recheck, "nothing re-checks")

        self._ping(ms=9.0)  # the name arrived
        self._pump_until(lambda: any("can now reach" in t for t, _lv in logged))
        self.assertIsNone(self.slots._scenes[0].recheck)
        self.assertIsNone(self.slots.ui.footer._status_level, "the footer stayed red")
        green = [lv for t, lv in logged if "can now reach" in t]
        self.assertEqual(green, ["success"])

    def test_a_link_that_never_opens_says_so_when_the_checks_run_out(self):
        self._ping(ok=False, error="HTTP 502 Bad Gateway")
        logged = self._record_levels()
        cls = type(self.slots)
        with (
            mock.patch.object(cls, "RECHECK_MS", 50),
            mock.patch.object(cls, "RECHECK_FOR_S", 0.2),
        ):
            self._share()
            self._pump_until(lambda: any("STILL NOT" in t for t, _lv in logged))
        self.assertIsNone(self.slots._scenes[0].recheck)

    def test_stopping_the_share_ends_its_rechecks(self):
        self._ping(ok=False, error="HTTP 502 Bad Gateway")
        logged = self._record_levels()
        self._share()
        self._pump_until(lambda: any(lv == "critical" for _t, lv in logged))
        self.assertIsNotNone(self.slots._scenes[0].recheck)
        self._action("btn_stop_sharing").click()
        self.assertIsNone(self.slots._scenes[0].recheck)
        self.assertIsNone(self.slots.ui.footer._status_level)

    def test_a_certificate_only_this_machine_doubts_is_still_a_pass(self):
        self._ping(ms=5.0, route="public", verified=False)
        logged = self._record_levels()
        self._share()
        # THIS share's answer (an earlier case's check can log first).
        self._pump_until(lambda: any("could not verify" in t for t, _lv in logged))
        line = next(t for t, _lv in logged if "could not verify" in t)
        self.assertIn("could not verify the link's certificate", line)
        self.assertIn("public DNS", line)

    def test_stop_sharing_retires_a_share_whose_client_died(self):
        """A share whose tunnel client exited on its own reads as not shared,
        so Stop Sharing answered "Nothing is being shared" and left it be: the
        guest listener open, and the alias still sending guests to the dead
        link until the next share."""
        from pathlib import Path

        folder = Path(self.temp.dir_path())
        with mock.patch.dict(os.environ, {ptk.PreviewServer.ALIAS_ENV: str(folder)}):
            self._share()
        server = self.slots._server()
        process = server._tunnel._process
        process.kill()
        process.wait(timeout=10)
        self.assertIsNone(server.share_info())

        self.slots.stop_sharing()

        self.assertIsNone(server.guest_port, "the guest listener was left open")
        page = (folder / "index.html").read_text(encoding="utf-8")
        self.assertNotIn(_FAKE_LINK, page)
        self.assertIn("Nothing is being shared right now", page)


if __name__ == "__main__":
    unittest.main()
