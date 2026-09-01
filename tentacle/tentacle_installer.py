# !/usr/bin/python
# coding=utf-8
"""Install, update or uninstall tentacle in a DCC -- one file, dropped in, no administrator rights.

Maya (2025+)
    Drag this file into the viewport. Maya imports it and calls :func:`onMayaDroppedPythonFile`:
    the first time it registers a user-owned Maya module
    (``<MAYA_APP_DIR>/<version>/modules/tentacle.mod`` -> ``<MAYA_APP_DIR>/<version>/tentacle/``),
    provisions ``tentacletk[maya]`` into that module's ``site`` folder and launches the menu;
    from then on the module's own ``scripts/userSetup.py`` calls it back at every start.
    Dropped again, it offers **Update / Uninstall**.

Blender (4.x+)
    *Edit > Preferences > Add-ons > Install from Disk*, pick this file, enable it. Blender copies
    it into its add-ons folder and calls :func:`register` on every start; the first one provisions
    ``tentacletk[blender]`` plus a Qt binding into Blender's per-user ``scripts/addons/modules``.
    The add-on's preferences carry **Update** and **Uninstall**.

Command line (deployment scripts, no UI)::

    "<mayapy>" tentacle_installer.py [install|update|uninstall]
    blender --background --python tentacle_installer.py -- [install|update|uninstall]

    (Under mayapy the verb is immediate. Under Blender ``install`` installs and enables the
    add-on; ``update`` / ``uninstall`` run after the enabled add-on has already imported
    tentacle, so they are recorded and applied by the next start -- one more
    ``blender --background`` run completes them. Do not add ``--factory-startup``: saving
    preferences from a factory session overwrites the user's.)

Both hosts share one policy, :class:`TentacleInstaller`: everything lands in a per-user,
per-DCC-version directory the host already imports from at TAIL precedence -- Blender's
``addons/modules`` (``sys.path`` index 9, after the bundled site-packages at 7), the Maya module's
``site`` via the ``.mod``'s ``PYTHONPATH +:=`` (26-38, after site-packages at 7-19; measured) -- so
nothing installed can shadow what the host bundles and no elevation is ever needed. Provisioning
is resolver-aware (``pythontk.PackageManager.install_targeted``: pip plans against the host's own
site-packages and only the reported set is applied), bootstrapped by a single ``--no-deps``
install of pythontk, and runs on a worker thread with progress in the host UI.

**Update / uninstall apply now if nothing of ours is imported yet, otherwise at the next start.**
A running menu has compiled extensions mapped into the process (``PIL/_imaging.pyd``, PySide6's
DLLs) that Windows will not let pip replace or delete; both startup hooks run *before* anything
of ours is imported, so a request recorded in the manifest (``tentacle_installer.json`` beside the
packages: spec, pins applied, pending verb) completes there with nothing locked. Uninstall removes
exactly what the manifest records (Blender's ``addons/modules`` is shared with every other add-on's
dependencies) -- for Maya the whole module folder and its ``.mod``.

Nothing happens at import: the API-registry generator, Maya's drop executor and Blender's add-on
loader all *import* this module before calling anything.
"""

import importlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import threading
from importlib import metadata

# Blender's add-on contract -- module-scope ``bl_info`` + ``register`` / ``unregister``.
bl_info = {
    "name": "Tentacle Marking Menu",
    "author": "m3trik",
    "version": (1, 1, 0),
    "blender": (4, 1, 0),
    "location": "3D View > activation key (default Z); Preferences > Add-ons for update / uninstall",
    "description": "Installs tentacle on first start (no admin rights) and launches its marking menu.",
    "category": "Interface",
}


class TentacleInstaller:
    """Provision tentacle into the host's per-user import dir, launch it, update or remove it.

    Every public method is a classmethod: the class is the namespace for one process-wide
    install flow, and the only state it keeps is the worker thread of an in-progress
    provisioning (so a second trigger while one runs is a no-op) and the Blender UI classes it
    registered.
    """

    #: Distribution name; the host's engine rides in as the extra (``tentacletk[maya]``).
    DIST = "tentacletk"
    #: Engine package each extra brings -- checked, with ``tentacle``, to decide "installed".
    ENGINES = {"maya": "mayatk", "blender": "blendertk"}
    #: Blender ships no Qt; installed with the package on a FRESH install so tentacle's own
    #: on-demand Qt bootstrap finds a binding and no-ops. Never named on an update: with
    #: ``--upgrade`` that would pull a newer Qt nobody asked for. Must equal
    #: ``tentacle.tcl_blender._QtBootstrap.QT_SPECS`` (drift-guarded by the test suite).
    QT_SPECS = ("PySide6", "qtpy")
    #: pip settings for a provisioning run: bounded waits -- pip's defaults stack to over a
    #: minute against a firewall that drops rather than refuses -- and no upgrade notice.
    PIP_ENV = {
        "PIP_DISABLE_PIP_VERSION_CHECK": "1",
        "PIP_RETRIES": "1",
        "PIP_TIMEOUT": "15",
    }
    #: Maya module name (the ``.mod`` line and the folder under the version prefs dir).
    MAYA_MODULE = "tentacle"
    #: The record of what this installer put in the target dir (and any pending verb).
    MANIFEST = "tentacle_installer.json"
    VERBS = ("install", "update", "uninstall")
    #: Seconds between worker polls while a GUI provisioning runs.
    POLL_INTERVAL = 0.5

    _worker = None
    _timer = None  # Maya: the QTimer polling the worker (kept alive here)
    _blender_ui = ()  # bpy classes registered by :meth:`register_blender_ui`
    _blender_addon = None  # the add-on module name Blender knows this file by

    # ------------------------------------------------------------------ host facts
    @staticmethod
    def host():
        """``"blender"`` / ``"maya"`` for the DCC this interpreter is embedded in, else None."""
        try:
            import bpy  # noqa: F401

            return "blender"
        except ImportError:
            pass
        try:
            import maya.cmds  # noqa: F401

            return "maya"
        except ImportError:
            return None

    @staticmethod
    def headless(host):
        """True with no UI to report into (``blender --background``, ``mayapy`` / ``maya -batch``)."""
        if host == "blender":
            import bpy

            return bool(bpy.app.background)
        if host == "maya":
            try:
                from maya import cmds

                return bool(cmds.about(batch=True))
            except Exception:
                return True
        return True

    @staticmethod
    def loaded():
        """True once our code is imported in this process -- its extension modules are then
        mapped and cannot be replaced or deleted on Windows, so verbs defer to the next start."""
        return "tentacle" in sys.modules

    @classmethod
    def specs(cls, host, fresh=True):
        """pip requirements for *host*: the package with its engine extra (+ Qt on a fresh Blender install)."""
        specs = [f"{cls.DIST}[{host}]"]
        if host == "blender" and fresh:
            specs.extend(cls.QT_SPECS)
        return specs

    @staticmethod
    def python_exe(host):
        """The host's own interpreter (``sys.executable`` is the DCC binary in a GUI session)."""
        if host == "blender":
            bindir = os.path.join(sys.prefix, "bin")
            for name in ("python.exe", "python3.exe", "python", "python3"):
                exe = os.path.join(bindir, name)
                if os.path.isfile(exe):
                    return exe
            if os.path.isdir(bindir):  # mac / linux: python3.13 and friends
                for name in sorted(os.listdir(bindir)):
                    if name.startswith("python") and not name.endswith(
                        (".dll", ".zip")
                    ):
                        return os.path.join(bindir, name)
        if host == "maya":
            exe = os.path.join(
                os.path.dirname(sys.executable),
                "mayapy.exe" if os.name == "nt" else "mayapy",
            )
            if os.path.isfile(exe):
                return exe
        return sys.executable

    @classmethod
    def maya_paths(cls, app_dir=None, version=None):
        """``(module_root, mod_file)`` for this Maya -- both under the per-version prefs dir.

        ``<app_dir>/<version>/modules`` is on Maya's default module path, so the ``.mod`` needs
        no environment setup; the module root beside it holds ``scripts/`` (this file + the
        ``userSetup.py`` that calls it) and ``site/`` (the packages). Deleting both uninstalls.
        """
        if app_dir is None or version is None:
            from maya import cmds

            app_dir = app_dir or cmds.internalVar(userAppDir=True)
            version = version or cmds.about(version=True)
        base = os.path.join(os.path.normpath(app_dir), str(version))
        return (
            os.path.join(base, cls.MAYA_MODULE),
            os.path.join(base, "modules", f"{cls.MAYA_MODULE}.mod"),
        )

    @classmethod
    def target_dir(cls, host):
        """Where the packages go: a per-user dir the host imports from at tail precedence."""
        if host == "blender":
            import bpy

            return os.path.normpath(
                bpy.utils.user_resource("SCRIPTS", path="addons/modules", create=True)
            )
        if host == "maya":
            return os.path.join(cls.maya_paths()[0], "site")
        raise RuntimeError("tentacle_installer: run this inside Maya or Blender.")

    # ------------------------------------------------------------------ state
    @staticmethod
    def _origin(name):
        """The file *name* would import from, or ``None`` when it backs no real file.

        The one probe both :meth:`_has` and the shadow reports go through. A bare folder
        of that name anywhere on the path (a repo checkout root, a stray ``tentacle/``
        next to a script) resolves as an empty namespace package -- a spec with no file
        behind it -- which would read as "installed" and skip the install.
        """
        importlib.invalidate_caches()
        try:
            spec = importlib.util.find_spec(name)
        except (ImportError, ValueError):
            return None
        if spec is None or not (spec.has_location and spec.origin):
            return None
        return spec.origin

    @classmethod
    def _has(cls, name):
        """True when *name* resolves to a REAL package on the current ``sys.path``."""
        return cls._origin(name) is not None

    @classmethod
    def _outside_origins(cls, host, target):
        """``{name: origin}`` for our packages that import from OUTSIDE *target*.

        Nothing this installer removes can reach them, which is exactly what makes a
        removal look like it did nothing: the next start imports that copy and the menu
        is back. A dev checkout on ``PYTHONPATH`` and a plain ``pip install tentacletk``
        in the user site are both this.

        This never raises. It runs on the pending path, straight out of ``userSetup.py``
        / ``register()``, and now runs AFTER a removal that already succeeded -- a
        diagnostic that can propagate there would have the host report the add-on as
        broken over a message about the add-on. One guard here covers every caller.
        """
        # The separator matters: a bare prefix test also swallows a SIBLING of the
        # target (``<target>_old``), which is a copy the removal cannot reach.
        root = os.path.normcase(os.path.normpath(target)) + os.sep
        found = {}
        try:
            for name in ("tentacle", cls.ENGINES.get(host)):
                origin = cls._origin(name) if name else None
                if origin and not os.path.normcase(os.path.normpath(origin)).startswith(
                    root
                ):
                    found[name] = origin
        except Exception:  # noqa: BLE001 -- see above
            return {}
        return found

    @classmethod
    def is_installed(cls, host):
        """True when ``tentacle`` and the host's engine both resolve on ``sys.path``."""
        return all(cls._has(name) for name in ("tentacle", cls.ENGINES[host]))

    @staticmethod
    def _rmtree(path):
        """Remove a tree, or raise naming the first path that would not go.

        On Windows the tree is addressed with the ``\\\\?\\`` extended-length prefix: a
        package tree under a per-version prefs dir reaches ``MAX_PATH`` (a 260-character
        ``__pycache__`` entry survived an ``ignore_errors`` rmtree, measured), and a
        silently half-removed module is worse than a message.
        """
        if not os.path.isdir(path):
            return
        target = TentacleInstaller._long_path(os.path.abspath(path))
        failed = []

        def on_error(_func, failed_path, _exc):
            failed.append(TentacleInstaller._short_path(str(failed_path)))

        if sys.version_info >= (
            3,
            12,
        ):  # onerror is deprecated there; onexc absent before
            shutil.rmtree(target, onexc=on_error)
        else:
            shutil.rmtree(target, onerror=on_error)
        if failed or os.path.isdir(path):
            first = failed[0] if failed else path
            raise RuntimeError(
                f"could not remove {first} - close the application and delete {path} by hand"
            )

    @staticmethod
    def _long_path(path):
        """Address *path* past ``MAX_PATH`` on Windows; unchanged elsewhere.

        A package tree under a per-version prefs dir reaches ``MAX_PATH`` (a
        260-character ``__pycache__`` entry survived an ``ignore_errors`` rmtree,
        measured), and a silently half-removed module is worse than a message.

        A UNC path takes ``\\\\?\\UNC\\<server>\\<share>``, NOT ``\\\\?\\<path>``:
        prefixing the plain form yields ``\\\\?\\\\\\<server>\\...``, which Windows
        rejects with WinError 123. A prefs dir on a network home (``MAYA_APP_DIR``,
        or a redirected Documents) is exactly that shape, so without this the
        uninstall could never succeed there -- and it failed claiming a file was
        locked, which was never true.
        """
        if os.name != "nt" or path.startswith("\\\\?\\"):
            return path
        if path.startswith("\\\\"):
            return "\\\\?\\UNC" + path[1:]
        return "\\\\?\\" + path

    @staticmethod
    def _short_path(path):
        """Inverse of :meth:`_long_path`, so a reported path stays readable.

        Longest prefix first: ``\\\\?\\`` is a prefix of ``\\\\?\\UNC``, and stripping
        it alone would report a UNC failure as ``UNC\\server\\share\\...``.
        """
        for prefix, restore in (("\\\\?\\UNC", "\\"), ("\\\\?\\", "")):
            if path.startswith(prefix):
                return restore + path[len(prefix) :]
        return path

    @staticmethod
    def _ensure_on_path(directory):
        """Append *directory* to ``sys.path`` (never insert: the host keeps precedence)."""
        wanted = os.path.normcase(os.path.normpath(directory))
        if wanted not in {os.path.normcase(os.path.normpath(p)) for p in sys.path if p}:
            sys.path.append(directory)

    # ------------------------------------------------------------------ manifest
    @classmethod
    def manifest_path(cls, target):
        return os.path.join(target, cls.MANIFEST)

    @classmethod
    def read_manifest(cls, target):
        """The manifest dict (``{}`` when absent or unreadable)."""
        return cls._read_manifest(target) or {}

    @classmethod
    def _read_manifest(cls, target):
        """``{}`` when ABSENT, ``None`` when present-but-unreadable, else the dict.

        The distinction is what stops :meth:`write_manifest` from silently replacing
        a truncated manifest's ``pins`` with a shorter list: a manifest that cannot be
        read still describes an install that is on disk, and treating it as empty is
        how a later uninstall came to remove nothing while reporting success.
        """
        path = cls.manifest_path(target)
        if not os.path.isfile(path):
            return {}
        try:
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
        except (OSError, ValueError):
            return None
        return data if isinstance(data, dict) else None

    @classmethod
    def write_manifest(cls, target, **updates):
        """Merge *updates* into the manifest. ``pins`` accumulates (union) across runs.

        Written atomically (sibling temp + ``os.replace``): the previous non-atomic
        ``open(...,'w') + json.dump`` could be interrupted by a DCC crash or a full
        disk and leave a truncated file, which then read as an EMPTY manifest and made
        the install look like it had nothing to uninstall.

        An unreadable existing manifest is kept, not destroyed: its pins cannot be
        merged (that is what unreadable means), but the install it describes is still
        on disk, so it is moved aside to ``<manifest>.corrupt`` before the fresh record
        is written. Overwriting it outright would drop the only list of what to remove.
        """
        data = cls._read_manifest(target)
        if data is None:
            # Unreadable. Its pins are unrecoverable, but they name packages that ARE
            # on disk, so preserve the file for hand-recovery instead of overwriting
            # the only record of what this installer put there.
            cls._preserve_corrupt_manifest(target)
            data = {}
        pins = set(data.get("pins") or [])
        if "pins" in updates:
            pins |= set(updates.pop("pins") or [])
        data.update(updates)
        data["pins"] = sorted(pins)
        os.makedirs(target, exist_ok=True)
        path = cls.manifest_path(target)
        tmp = path + ".tmp"
        try:
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump(data, fh, indent=1)
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(tmp, path)
        finally:
            if os.path.isfile(tmp):
                try:
                    os.remove(tmp)
                except OSError:
                    pass
        return data

    @classmethod
    def _preserve_corrupt_manifest(cls, target):
        """Move an unparseable manifest to ``<manifest>.corrupt``; never raise.

        Called before a fresh record replaces it. The pins inside name packages that
        are really on disk, so the file is evidence for a hand-cleanup even though it
        cannot be merged. Best effort by design: failing to preserve it must not stop
        the install that is trying to repair the situation.
        """
        path = cls.manifest_path(target)
        keep = path + ".corrupt"
        try:
            os.replace(path, keep)
            print(f"[tentacle] unreadable manifest preserved as {keep}")
        except OSError:
            pass

    @classmethod
    def installed_version(cls, target, name=None):
        """A dist's version as recorded in *target*'s dist-info (default: tentacletk), else None -- no import.

        The cache drop is load-bearing, not hygiene. ``importlib.metadata``
        memoizes each directory listing under ``(path, st_mtime)``, and
        Windows' mtime resolution is coarse enough that a dist-info written in
        the same tick as an earlier scan of that directory leaves the key
        unchanged -- so the stale EMPTY listing is served and this reports
        ``None`` for a package that is right there. Measured on mayapy 2025:
        14 of 60 scan/create/scan cycles came back stale; with the drop, 0 of
        60. That is exactly the shape of "install, then ask what is installed",
        which is what every caller here does.

        ``importlib.invalidate_caches()`` does NOT cover it (measured: 22/60
        still stale) -- ``MetadataPathFinder`` is not reached that way. It has
        to be this finder, and on an INSTANCE: Python 3.11 declares
        ``invalidate_caches(cls)`` without the ``@classmethod``, so the class
        form raises ``TypeError``.
        """
        wanted = (name or cls.DIST).lower()
        try:
            metadata.MetadataPathFinder().invalidate_caches()
        except Exception:  # noqa: BLE001 -- a stale read still beats no read
            pass
        try:
            for dist in metadata.distributions(path=[target]):
                if (dist.metadata["Name"] or "").lower() == wanted:
                    return dist.version
        except Exception:
            pass
        return None

    # ------------------------------------------------------------------ verbs
    @classmethod
    def install(cls, host, target=None, python=None, upgrade=False):
        """Provision (or upgrade) the host's spec set and record it; returns the pins applied."""
        target = target or cls.target_dir(host)
        python = python or cls.python_exe(host)
        specs = cls.specs(host, fresh=not upgrade)
        try:
            pins = cls.provision(
                host,
                upgrade=upgrade,
                target=target,
                python=python,
                specs=specs,
            )
        except BaseException:
            # A part-provisioned target still has dists in it -- on Blender that is a
            # SHARED addons/modules, so leaving them unrecorded orphans them for good
            # (a later uninstall reads no pins and removes nothing). Record the dist
            # names we were installing so uninstall can still name them; pip skips
            # the ones that never landed.
            cls.write_manifest(target, pins=cls._spec_names(specs))
            raise
        cls.write_manifest(target, spec=cls.specs(host)[0], pins=pins, pending=None)
        return pins

    @staticmethod
    def _spec_names(specs):
        """Bare dist names from requirement specs (``tentacletk[blender]==1.2`` -> ``tentacletk``)."""
        names = []
        for spec in specs or []:
            name = str(spec).strip()
            # Everything from the first extras bracket, comparison operator,
            # marker or space onward is not part of the dist name.
            for sep in ("[", "<", ">", "=", "!", "~", ";", " "):
                name = name.split(sep, 1)[0]
            if name:
                names.append(name)
        return sorted(set(names))

    @classmethod
    def update(cls, host, target=None, python=None):
        """Upgrade the package (and whatever its floors now require); never re-plans Qt."""
        return cls.install(host, target, python, upgrade=True)

    @classmethod
    def uninstall(cls, host, target=None, python=None):
        """Remove what this installer put there; returns the dist names removed.

        Maya: the module folder (scripts + site) and its ``.mod`` -- exclusively ours. Blender:
        ``addons/modules`` is shared, so only the dists the manifest records are removed
        (``pip uninstall`` finds them through ``PYTHONPATH``), then the add-on removes itself.

        *target* is honoured on BOTH hosts. It used to be read for the manifest and then
        discarded on the Maya branch, which recomputed the tree from :meth:`maya_paths` --
        so a caller honouring the published signature deleted the real prefs-dir module
        instead of the directory it named. Since ``target_dir('maya')`` is
        ``<root>/site``, deriving root and ``.mod`` back from *target* reproduces
        :meth:`maya_paths` exactly in the default case.
        """
        target = target or cls.target_dir(host)
        python = python or cls.python_exe(host)
        names = sorted(
            {pin.split("==")[0] for pin in cls.read_manifest(target).get("pins", [])}
        )
        if host == "maya":
            root, mod = cls._maya_uninstall_paths(target)
            # The one destructive rmtree in this file. Refuse a tree that does not
            # look like ours rather than trusting a computed path: the .mod still
            # goes, so a half-written module can always be uninstalled, it just
            # does not take an unrelated directory with it.
            if cls._is_our_module_root(root):
                cls._rmtree(root)
            elif os.path.isdir(root):
                print(
                    f"[tentacle] {root} does not look like a tentacle module "
                    "(no scripts/ or site/) - leaving it alone; remove it by hand"
                )
            if os.path.isfile(mod):
                os.remove(mod)
            return names
        if names:
            cls._run_checked(
                [python, "-s", "-m", "pip", "uninstall", "-y"] + names,
                env={**os.environ, "PYTHONPATH": target},
            )
        # The manifest and the .corrupt breadcrumb a failed read may have left
        # beside it: addons/modules is SHARED, so an uninstall that leaves its own
        # files there is the very thing this branch exists to avoid.
        for leftover in (
            cls.manifest_path(target),
            cls.manifest_path(target) + ".corrupt",
        ):
            try:
                os.remove(leftover)
            except OSError:
                pass
        cls._remove_blender_addon()
        return names

    @classmethod
    def _maya_uninstall_paths(cls, target):
        """``(module_root, mod_file)`` derived from *target*.

        ``target_dir('maya')`` is ``<root>/site`` and :meth:`maya_paths` puts the
        ``.mod`` at ``<root>/../modules/<name>.mod``, so both come back from the one
        argument -- identical to ``maya_paths()`` when *target* is the default, and
        actually pointing at what the caller named when it is not.
        """
        root = os.path.dirname(os.path.normpath(target))
        base = os.path.dirname(root)
        return root, os.path.join(base, "modules", f"{cls.MAYA_MODULE}.mod")

    @classmethod
    def _is_our_module_root(cls, root):
        """True when *root* carries the shape :meth:`write_maya_module` builds."""
        if not os.path.isdir(root):
            return False
        return any(
            os.path.isdir(os.path.join(root, part)) for part in ("scripts", "site")
        )

    @classmethod
    def request(cls, host, verb):
        """The one entry every surface calls with a verb; returns the message to show.

        ``install`` is :meth:`ensure_and_launch`. ``update`` / ``uninstall`` apply now when
        nothing of ours is imported yet, otherwise they are recorded as *pending* for the next
        start (see the module docstring for why).
        """
        if verb not in cls.VERBS:
            raise ValueError(f"unknown verb {verb!r}; expected one of {cls.VERBS}")
        if verb == "install":
            cls.ensure_and_launch(host)
            running = cls._worker is not None and cls._worker.is_alive()
            return "Tentacle install started" if running else "Tentacle is installed"
        target = cls.target_dir(host)
        if cls.loaded():
            cls.write_manifest(target, pending=verb)
            done = {"update": "updated", "uninstall": "uninstalled"}[verb]
            message = f"Tentacle will be {done} when {host.capitalize()} next starts - restart to apply"
            cls._say(host, message)
            return message
        if verb == "uninstall":
            return cls._report_uninstall(host, target, cls.uninstall(host, target))
        # update, nothing loaded: like a first install, and launch when done.
        cls._ensure_on_path(target)
        if cls.headless(host):
            cls._report(host, cls.update(host, target))
            cls.launch(host)
            return "Tentacle updated"
        cls._provision_async(host, True, target)
        return "Tentacle update started"

    @classmethod
    def _report_uninstall(cls, host, target, names):
        """Show what a removal actually achieved; returns the message.

        A copy of ours the removal could not reach is a problem report, not a routine
        success, and Maya's success channel is a four-second fading ``inViewMessage`` --
        the wrong carrier for the one message that explains why the menu is still
        there. It goes out on the error channel instead, which is a dialog that waits.
        """
        outside = cls._outside_origins(host, target)
        message = cls._uninstall_message(host, target, names, outside)
        cls._say(host, message, error=bool(outside))
        return message

    @classmethod
    def _uninstall_message(cls, host, target, names, outside):
        """What a removal reports -- including any copy of ours it could not reach.

        Maya's removal is exclusive (the whole module folder is ours), so it is complete
        whatever the manifest said. Blender's is driven ENTIRELY by the recorded pins
        into a SHARED ``addons/modules``, so no pins means nothing was removed -- and
        saying 'uninstalled' there, after deleting the add-on that is the only UI to
        retry from, is the report that hid the leftovers.

        Neither reaches a ``tentacle`` that resolves from OUTSIDE *target*, and that copy
        relaunches the menu at the next start -- so a complete removal still reads as
        having done nothing. Measured on a machine carrying the repo on ``PYTHONPATH``:
        a drop then Uninstall removed only the empty module shell the drop had just
        written, reported "Tentacle uninstalled", and the menu was back one restart
        later. It leads the message rather than trailing it, because Blender's popup
        shows the first line only.
        """
        if host == "maya" or names:
            removed = f" ({len(names)} package(s) removed)" if names else ""
            message = f"Tentacle uninstalled{removed}"
        else:
            message = (
                "Nothing was recorded to remove - the add-on is gone, but any "
                f"packages this installer added are still in {target}"
            )
        if outside:
            where = "; ".join(
                f"{name} in {os.path.dirname(origin)}"
                for name, origin in sorted(outside.items())
            )
            message += (
                " - tentacle still loads from outside the install dir, so the menu "
                "comes back at the next start."
                f"\nFound: {where}"
                "\nThat copy is not this installer's; remove it separately (a checkout "
                "on PYTHONPATH, or 'pip uninstall tentacletk' in that interpreter)."
            )
        return message

    # ------------------------------------------------------------------ provisioning
    @classmethod
    def provision(cls, host, upgrade=False, target=None, python=None, specs=None):
        """Install *specs* into *target*; returns the pins applied.

        Bootstrap order: make sure the interpreter has pip; put pythontk in the target with
        one ``--no-deps`` install when nothing provides it yet (a pure-Python wheel -- no
        resolver involved, so ``--target`` is safe here); then hand the real work to
        ``pythontk.PackageManager.install_targeted``, which is the one implementation of the
        resolver-aware policy. Raises ``RuntimeError`` with pip's own message on failure.

        *target* / *python* default to :meth:`target_dir` / :meth:`python_exe`, but the worker
        path MUST pass them: those resolve through ``cmds`` / ``bpy``, which are main-thread
        only -- ``cmds.internalVar`` called from the worker answered with a relative path and
        the packages landed beside the working directory (measured in a GUI Maya).
        """
        target = target or cls.target_dir(host)
        python = python or cls.python_exe(host)
        specs = list(specs or cls.specs(host, fresh=not upgrade))
        os.makedirs(target, exist_ok=True)
        cls._ensure_on_path(target)
        saved = {key: os.environ.get(key) for key in cls.PIP_ENV}
        os.environ.update(cls.PIP_ENV)
        try:
            if cls._run([python, "-s", "-m", "pip", "--version"]).returncode != 0:
                cls._run([python, "-m", "ensurepip", "--upgrade"])
            bootstrapped = []
            if not cls._has("pythontk"):
                cls._run_checked(
                    [
                        python,
                        "-s",
                        "-m",
                        "pip",
                        "install",
                        "--no-deps",
                        "--upgrade",
                        "--target",
                        target,
                        "pythontk",
                    ]
                )
                # Not part of install_targeted's report (already satisfied by then), so record
                # it here or uninstall leaves it behind (measured: a pythontk dist-info survived).
                version = cls.installed_version(target, "pythontk")
                if version:
                    bootstrapped.append(f"pythontk=={version}")
                    # Recorded NOW, not with the rest at the end: everything after
                    # this point can raise (a resolver failure, a full disk, the DCC
                    # being closed), and a pythontk that is on disk but absent from
                    # the manifest is one a later uninstall silently leaves behind.
                    cls.write_manifest(target, pins=bootstrapped)
            importlib.invalidate_caches()
            import pythontk as ptk

            manager = getattr(ptk, "PackageManager", None)
            if manager is None or not hasattr(manager, "install_targeted"):
                raise RuntimeError(
                    f"the pythontk at {os.path.dirname(getattr(ptk, '__file__', '?'))} is too old "
                    "(no PackageManager.install_targeted) - remove it so a current one is installed."
                )
            pins = bootstrapped + manager(python_path=python).install_targeted(
                specs, target, upgrade=upgrade
            )
        finally:
            for key, value in saved.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value
        importlib.invalidate_caches()
        if not cls.is_installed(host):
            raise RuntimeError(
                f"pip reported success but tentacle / {cls.ENGINES[host]} do not import from "
                f"{target}. Applied: {pins or 'nothing'}"
            )
        return pins

    @staticmethod
    def _startupinfo():
        """Keep pip's console window off the screen on Windows (output is captured anyway)."""
        if os.name != "nt":
            return None
        info = subprocess.STARTUPINFO()
        info.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        info.wShowWindow = subprocess.SW_HIDE
        return info

    @classmethod
    def _run(cls, command, env=None):
        return subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            errors="replace",
            env=env,
            startupinfo=cls._startupinfo(),
        )

    @classmethod
    def _run_checked(cls, command, env=None):
        result = cls._run(command, env=env)
        if result.returncode != 0:
            tail = (result.stderr or result.stdout or "").strip().splitlines()[-8:]
            raise RuntimeError(
                f"Command '{' '.join(command)}' failed:\n" + "\n".join(tail)
            )
        return result

    # ------------------------------------------------------------------ launch / teardown
    @classmethod
    def launch(cls, host):
        """Start the menu through tentacle's own host-aware entry (deferred as the host needs)."""
        importlib.invalidate_caches()
        from tentacle import Tcl

        cls._advise_shadow(host)
        key = os.environ.get("TENTACLE_KEY")
        return Tcl.launch(key_show=key) if key else Tcl.launch()

    @classmethod
    def _advise_shadow(cls, host):
        """Say so when anything of ours resolved from somewhere ahead of the install dir.

        Maya reads the user site ahead of everything (index 14 vs the module's 26-38); a stale
        ``tentacletk`` left there by a bare ``pip install`` wins every import and looks like
        an update that never took. pip cannot see that; this can.
        """
        try:
            target = cls.target_dir(host)
        except Exception:  # noqa: BLE001 -- cmds / bpy unavailable; nothing to compare to
            return
        for name, origin in sorted(cls._outside_origins(host, target).items()):
            print(
                f"[tentacle] {name} loads from {os.path.dirname(origin)}, not from the "
                "install dir: a copy earlier on sys.path outranks it "
                "(uninstall that one to use this install)."
            )

    @classmethod
    def shutdown(cls):
        """Blender add-on teardown: tear down the keymap bridge if tentacle ever came up."""
        module = sys.modules.get("tentacle.tcl_blender")
        if module is not None:
            module.unregister()

    # ------------------------------------------------------------------ orchestration
    @classmethod
    def ensure_and_launch(cls, host=None):
        """The startup entry both hosts call: finish a pending verb, install if needed, launch.

        A pending *uninstall* removes everything and does not launch. A pending *update*, or a
        missing install, provisions -- synchronously when there is no UI (batch / background,
        where a launch is a no-op anyway), on a worker thread with host-UI progress when there
        is one -- and launches when done. Otherwise it is ``import`` -> launch, no subprocess.
        """
        host = host or cls.host()
        if host is None:
            raise RuntimeError("tentacle_installer: run this inside Maya or Blender.")
        target = cls.target_dir(host)
        cls._ensure_on_path(target)
        pending = cls.read_manifest(target).get("pending")
        if pending == "uninstall":
            cls._report_uninstall(host, target, cls.uninstall(host, target))
            return None
        upgrade = pending == "update"
        if cls.is_installed(host) and not upgrade:
            return cls.launch(host)
        if cls.headless(host):
            # Unguarded, a failed pending verb propagates out of register() /
            # userSetup and the host reports the add-on itself as broken -- so a
            # transient network failure costs the artist the whole menu.
            try:
                cls._report(host, cls.install(host, target, upgrade=upgrade))
            except Exception as error:
                print(f"[tentacle] install failed: {error}")
                if upgrade:
                    cls.write_manifest(target, pending=None)
                if not cls.is_installed(host):
                    return None
            return cls.launch(host)
        cls._provision_async(host, upgrade, target)
        return None

    @classmethod
    def _report(cls, host, pins):
        target = cls.target_dir(host)
        print(
            f"[tentacle] installed {', '.join(pins) if pins else 'nothing new'} into {target}"
        )
        how = (
            "drop tentacle_installer.py into the viewport again"
            if host == "maya"
            else "use the add-on's preferences"
        )
        print(f"[tentacle] to update or uninstall: {how}")

    @classmethod
    def _provision_async(cls, host, upgrade, target):
        """Worker thread + host timer: the UI stays live and shows progress; finish on the main thread.

        Everything the worker needs from the host (*target*, the interpreter) is resolved HERE,
        on the main thread, and handed over -- the worker never touches ``cmds`` / ``bpy``.
        """
        if cls._worker is not None and cls._worker.is_alive():
            return
        outcome = {}
        python = cls.python_exe(host)

        def work():
            try:
                outcome["pins"] = cls.install(host, target, python, upgrade=upgrade)
            except Exception as error:  # reported on the main thread below
                outcome["error"] = error

        cls._worker = threading.Thread(
            target=work, name="tentacle-installer", daemon=True
        )

        def finish():
            if "error" not in outcome:
                cls._report(host, outcome.get("pins"))
            cls._feedback_end(host, upgrade, outcome)
            if "error" not in outcome:
                cls.launch(host)
                return

            # The provision failed and the user has just been shown why. Two
            # things must not survive into the next start. `pending` is cleared
            # HERE and only here -- the one branch that reported the failure --
            # because otherwise an unreachable index turns one Update click into
            # a modal error and a missing menu at EVERY start, forever, with a
            # working install sitting in the target dir and no way back but
            # hand-editing JSON. They can re-request from the same surface.
            if upgrade:
                try:
                    cls.write_manifest(target, pending=None)
                except Exception as error:
                    print(f"[tentacle] could not clear the pending verb: {error}")
            # ...and an install that is already importable still gets to run.
            if cls.is_installed(host):
                try:
                    cls.launch(host)
                except Exception as error:
                    print(f"[tentacle] could not launch the existing install: {error}")

        def start():
            cls._feedback_begin(host, upgrade)
            cls._worker.start()
            cls._poll(host, finish)

        if host == "maya":
            # userSetup.py runs before Maya's UI exists: the progress window and the QTimer
            # that finishes the job need the idle loop, so start on it (immediate from a drop).
            from maya.utils import executeDeferred

            executeDeferred(start)
        else:
            start()

    @classmethod
    def _poll(cls, host, finish):
        """Call *finish* on the main thread once the worker is done."""
        ticks = {"n": 0}

        def tick():
            ticks["n"] += 1
            if cls._worker.is_alive():
                cls._feedback_tick(host, ticks["n"])
                return True
            finish()
            return False

        if host == "blender":
            import bpy

            def blender_tick():
                return cls.POLL_INTERVAL if tick() else None

            bpy.app.timers.register(blender_tick, first_interval=cls.POLL_INTERVAL)
            return
        try:
            from PySide6 import QtCore
        except ImportError:  # Maya < 2025 is below our floor, but never crash on it
            from PySide2 import QtCore  # type: ignore

        timer = QtCore.QTimer()
        timer.setInterval(int(cls.POLL_INTERVAL * 1000))

        def qt_tick():
            if not tick():
                timer.stop()
                cls._timer = None

        timer.timeout.connect(qt_tick)
        cls._timer = timer
        timer.start()

    # ------------------------------------------------------------------ host feedback
    @staticmethod
    def _ui(action):
        """Run a host-UI call as best effort: feedback must never break the install itself."""
        try:
            return action()
        except Exception:
            return None

    @classmethod
    def _say(cls, host, message, error=False):
        """Print *message* and echo it in the host UI (in-view / dialog / popup).

        Headless, the print is all there is: a ``popup_menu`` with no window is a NATIVE
        access violation in ``blender --background`` (measured), which no ``try`` catches.
        """
        print(f"[tentacle] {message}")
        if cls.headless(host):
            return
        if host == "blender":

            def popup():
                import bpy

                bpy.context.window_manager.popup_menu(
                    lambda menu, _ctx: menu.layout.label(
                        text=message.splitlines()[0][:200]
                    ),
                    title="Tentacle",
                    icon="ERROR" if error else "INFO",
                )

            cls._ui(popup)
        elif host == "maya":
            from maya import cmds
            from maya.utils import executeDeferred

            def show():
                if error:
                    return cmds.confirmDialog(
                        title="Tentacle",
                        message=message[:1500],
                        button=["OK"],
                        icon="critical",
                    )
                return cmds.inViewMessage(
                    amg=f"<hl>{message}</hl>",
                    pos="topCenter",
                    fade=True,
                    fadeStayTime=4000,
                )

            # Deferred: userSetup.py runs before the UI exists, and a message from there
            # would be lost; on idle it lands in the viewport that is up by then.
            executeDeferred(lambda: cls._ui(show))

    @classmethod
    def _feedback_begin(cls, host, upgrade):
        verb = "Updating" if upgrade else "Installing"
        message = f"{verb} tentacle - a minute or so, first start only..."
        print(f"[tentacle] {message}")
        if host == "blender":
            cls._reveal_console()
        elif host == "maya":
            from maya import cmds

            cls._ui(
                lambda: cmds.progressWindow(
                    title="Tentacle",
                    status=message,
                    maxValue=100,
                    isInterruptable=False,
                )
            )

    @classmethod
    def _feedback_tick(cls, host, n):
        if host == "maya":
            from maya import cmds

            cls._ui(lambda: cmds.progressWindow(edit=True, progress=n % 100))

    @classmethod
    def _feedback_end(cls, host, upgrade, outcome):
        if host == "maya":
            from maya import cmds

            cls._ui(lambda: cmds.progressWindow(endProgress=True))
        error = outcome.get("error")
        if error is None:
            done = "updated" if upgrade else "installed"
            if upgrade and not outcome.get("pins"):
                done = "already up to date"
            # A key the user persisted earlier outranks the default, so name the default as such.
            cls._say(
                host,
                f"Tentacle {done} - hover the viewport and hold the activation key (Z by default)",
            )
        else:
            cls._say(
                host,
                f"Tentacle could not be {'updated' if upgrade else 'installed'}:\n{error}\n\n"
                f"Check that {cls.python_exe(host)} can reach PyPI (firewall / proxy), then try again.",
                error=True,
            )

    @staticmethod
    def _reveal_console():
        """Windows hides Blender's system console; show it so pip's progress is visible."""
        if os.name != "nt":
            return
        try:
            import ctypes

            handle = ctypes.windll.kernel32.GetConsoleWindow()
            if handle:
                ctypes.windll.user32.ShowWindow(handle, 5)  # SW_SHOW
        except Exception:
            pass

    # ------------------------------------------------------------------ Maya surface
    @classmethod
    def write_maya_module(cls, source, app_dir=None, version=None):
        """Register the user-owned Maya module that re-runs this file at every start.

        Writes ``<root>/scripts/tentacle_installer.py`` (a copy of *source*),
        ``<root>/scripts/userSetup.py`` (two lines that call :meth:`ensure_and_launch`) and
        ``<mod>`` with ``PYTHONPATH +:= site``. Idempotent: rerunning rewrites the same bytes.
        Returns the module root.
        """
        root, mod = cls.maya_paths(app_dir, version)
        scripts = os.path.join(root, "scripts")
        os.makedirs(scripts, exist_ok=True)
        os.makedirs(os.path.join(root, "site"), exist_ok=True)
        os.makedirs(os.path.dirname(mod), exist_ok=True)
        copy = os.path.join(scripts, "tentacle_installer.py")
        if os.path.normcase(os.path.abspath(source)) != os.path.normcase(
            os.path.abspath(copy)
        ):
            shutil.copyfile(
                source, copy
            )  # the module copy itself may be what was dropped
        with open(os.path.join(scripts, "userSetup.py"), "w", encoding="utf-8") as fh:
            fh.write(
                "# Written by tentacle_installer.py - starts tentacle in this Maya.\n"
                "# To remove it, drop tentacle_installer.py into the viewport and choose Uninstall.\n"
                "import tentacle_installer\n"
                "tentacle_installer.TentacleInstaller.ensure_and_launch('maya')\n"
            )
        with open(mod, "w", encoding="utf-8") as fh:
            fh.write(f"+ {cls.MAYA_MODULE} {bl_info['version'][0]}.0 {root}\n")
            fh.write("PYTHONPATH +:= site\n")
        return root

    @classmethod
    def dropped(cls, source):
        """Maya drop hook body: first drop installs; a later drop asks Update / Uninstall."""
        # Captured BEFORE the module is written, because writing it is what makes
        # a re-drop look like a first drop forever: the .mod and scripts/userSetup.py
        # land here unconditionally, but the Update/Uninstall dialog used to be gated
        # on the install having SUCCEEDED. So exactly when provisioning can never
        # succeed -- no route to PyPI, or a Maya whose Python the wheel refuses --
        # every start re-ran the failing pip behind a modal error, and dropping the
        # file in again only retried it. Uninstall was unreachable, while the
        # userSetup.py just written tells the user verbatim to drop the file in and
        # choose Uninstall.
        root, mod = cls.maya_paths()
        existed = os.path.isfile(mod) or os.path.isdir(root)
        cls.write_maya_module(source)
        version = cls.installed_version(os.path.join(root, "site"))
        if version is None and not cls.is_installed("maya") and not existed:
            cls.ensure_and_launch("maya")
            return "install"
        from maya import cmds

        message = cls._drop_message(root, version)
        choice = cls._ui(
            lambda: cmds.confirmDialog(
                title="Tentacle",
                message=message,
                button=["Update", "Uninstall", "Cancel"],
                defaultButton="Cancel",
                cancelButton="Cancel",
                dismissString="Cancel",
            )
        )
        verb = (choice or "Cancel").lower()
        if verb in cls.VERBS:
            cls.request("maya", verb)
        return verb

    @classmethod
    def _drop_message(cls, root, version):
        """What the re-drop dialog states about this machine before offering the verbs.

        *version* is what the module's own ``site`` records, so ``None`` means this
        module has nothing in it -- the drop just created it. Saying "Tentacle ? is
        installed in <root>" there invited an Uninstall that could only remove that
        empty shell, while the ``tentacle`` actually being imported (a checkout on
        ``PYTHONPATH``, a plain ``pip install tentacletk`` in the user site) is beyond
        this installer's reach and comes back at the next start.
        """
        if version:
            message = f"Tentacle {version} is installed in\n{root}"
        else:
            message = f"No packages of ours are installed in\n{root}"
        outside = cls._outside_origins("maya", os.path.join(root, "site"))
        if outside:
            found = "\n".join(
                f"    {name}: {os.path.dirname(origin)}"
                for name, origin in sorted(outside.items())
            )
            message += (
                "\n\nBut Maya imports ours from outside this module:\n"
                f"{found}\n\nUninstall cannot remove that copy - it has to go separately."
            )
        return message

    # ------------------------------------------------------------------ Blender surface
    @classmethod
    def register_blender_ui(cls, addon_name):
        """Build and register the add-on preferences (version, Update, Uninstall) lazily --
        ``bpy`` classes cannot exist at module level in a file Maya also imports."""
        import bpy

        cls._blender_addon = addon_name
        installer = cls

        class TENTACLE_OT_installer_update(bpy.types.Operator):
            bl_idname = "tentacle_installer.update"
            bl_label = "Update Tentacle"
            bl_description = "Upgrade tentacle to the latest release (applies at the next start if the menu is running)"

            def execute(self, _context):
                self.report({"INFO"}, installer.request("blender", "update"))
                return {"FINISHED"}

        class TENTACLE_OT_installer_uninstall(bpy.types.Operator):
            bl_idname = "tentacle_installer.uninstall"
            bl_label = "Uninstall Tentacle"
            bl_description = "Remove the packages this add-on installed, then the add-on (applies at the next start if the menu is running)"

            def execute(self, _context):
                self.report({"INFO"}, installer.request("blender", "uninstall"))
                return {"FINISHED"}

        class TentacleInstallerPreferences(bpy.types.AddonPreferences):
            bl_idname = addon_name

            def draw(self, _context):
                target = installer.target_dir("blender")
                manifest = installer.read_manifest(target)
                version = installer.installed_version(target)
                layout = self.layout
                if manifest.get("pending"):
                    layout.label(
                        text=f"Pending: {manifest['pending']} - restart Blender to apply",
                        icon="INFO",
                    )
                layout.label(
                    text=f"tentacletk {version} in {target}"
                    if version
                    else "Not installed yet"
                )
                row = layout.row()
                row.operator("tentacle_installer.update", icon="FILE_REFRESH")
                row.operator("tentacle_installer.uninstall", icon="TRASH")

        classes = (
            TENTACLE_OT_installer_update,
            TENTACLE_OT_installer_uninstall,
            TentacleInstallerPreferences,
        )
        for klass in classes:
            bpy.utils.register_class(klass)
        cls._blender_ui = classes

    @classmethod
    def unregister_blender_ui(cls):
        import bpy

        for klass in reversed(cls._blender_ui):
            try:
                bpy.utils.unregister_class(klass)
            except Exception:
                pass
        cls._blender_ui = ()

    @classmethod
    def _remove_blender_addon(cls):
        """Have Blender forget this add-on: disable it (drops the preferences entry), delete
        its file, save preferences -- what ``preferences.addon_remove`` does, minus the operator,
        which needs an area to redraw and raises from a timer / at startup after doing the work.
        Directly when headless; on a timer from a running session (removing the add-on from
        inside its own operator would pull the rug out)."""
        name = cls._blender_addon
        if not name:
            return

        def remove():
            try:
                import bpy
                import addon_utils

                path = getattr(sys.modules.get(name), "__file__", None)
                addon_utils.disable(name, default_set=True)
                if path and os.path.isfile(path):
                    os.remove(path)
                if not getattr(bpy.app, "factory_startup", False):
                    cls._ui(bpy.ops.wm.save_userpref)
            except Exception as error:
                print(
                    f"[tentacle] could not remove the add-on entry ({error}); remove it in Preferences"
                )
            return None

        if cls.headless("blender"):
            remove()
        else:
            import bpy

            bpy.app.timers.register(remove, first_interval=0.5)

    # ------------------------------------------------------------------ command line
    @classmethod
    def main(cls, argv=None):
        """``[install|update|uninstall]`` from a plain ``mayapy`` / ``blender --background`` run.

        Under mayapy this initialises Maya standalone itself, skipping ``userSetup.py`` so
        nothing of ours is imported first and the verb applies immediately.
        """
        args = [
            a for a in (argv if argv is not None else sys.argv[1:]) if a in cls.VERBS
        ]
        verb = args[-1] if args else "install"
        host = cls.host()
        if host is None:
            print(__doc__.split("\n\n")[0])
            print(
                "Run it with mayapy or blender --background, or drop it into the DCC."
            )
            return 2
        if host == "maya":
            from maya import cmds

            try:
                cmds.about(batch=True)
            except Exception:  # bare mayapy: not initialised yet
                os.environ["MAYA_SKIP_USERSETUP_PY"] = "1"
                import maya.standalone

                maya.standalone.initialize()
        if host == "maya" and verb == "install":
            cls.write_maya_module(os.path.abspath(__file__))
        if host == "blender" and verb == "install":
            # The add-on IS the launch hook: install and enable it; enabling runs register()
            # -> ensure_and_launch, which provisions (synchronously, headless).
            import bpy

            stem = os.path.splitext(os.path.basename(__file__))[0]
            bpy.ops.preferences.addon_install(
                filepath=os.path.abspath(__file__), overwrite=True
            )
            bpy.ops.preferences.addon_enable(module=stem)
            if getattr(bpy.app, "factory_startup", False):
                print(
                    "[tentacle] add-on enabled for this session only: --factory-startup "
                    "preferences are never saved (that would overwrite yours)"
                )
            else:
                bpy.ops.wm.save_userpref()
            print(f"[tentacle] add-on {stem} installed and enabled")
            return 0
        try:
            print(f"[tentacle] {cls.request(host, verb)}")
        except Exception as error:
            print(f"[tentacle] {verb} failed: {error}")
            return 1
        return 0


# ------------------------------------------------------------------------------------------
# Host entry points -- each a thin delegator (Blender's add-on contract and Maya's drop hook
# both require module-level functions).
# ------------------------------------------------------------------------------------------
def register():
    """Blender add-on entry: preferences UI, then finish any pending verb / install / launch."""
    TentacleInstaller.register_blender_ui(__name__)
    TentacleInstaller.ensure_and_launch("blender")


def unregister():
    """Blender add-on teardown."""
    TentacleInstaller.unregister_blender_ui()
    TentacleInstaller.shutdown()


def onMayaDroppedPythonFile(*_args):  # noqa: N802 -- Maya's hook name
    """Maya drop hook: first drop installs and launches; later drops offer Update / Uninstall."""
    TentacleInstaller.dropped(os.path.abspath(__file__))


if __name__ == "__main__":
    sys.exit(TentacleInstaller.main())
