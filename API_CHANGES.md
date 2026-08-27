# tentacle — API Changes

_Diff vs the last release (origin/main @ c5d46351)._

## Added (29)

- `tentacle_installer.py::TentacleInstaller(class)`
- `tentacle_installer.py::TentacleInstaller.dropped(cls, source)`
- `tentacle_installer.py::TentacleInstaller.ensure_and_launch(cls, host=None)`
- `tentacle_installer.py::TentacleInstaller.headless(host)`
- `tentacle_installer.py::TentacleInstaller.host()`
- `tentacle_installer.py::TentacleInstaller.install(cls, host, target=None, python=None, upgrade=False)`
- `tentacle_installer.py::TentacleInstaller.installed_version(cls, target, name=None)`
- `tentacle_installer.py::TentacleInstaller.is_installed(cls, host)`
- `tentacle_installer.py::TentacleInstaller.launch(cls, host)`
- `tentacle_installer.py::TentacleInstaller.loaded()`
- `tentacle_installer.py::TentacleInstaller.main(cls, argv=None)`
- `tentacle_installer.py::TentacleInstaller.manifest_path(cls, target)`
- `tentacle_installer.py::TentacleInstaller.maya_paths(cls, app_dir=None, version=None)`
- `tentacle_installer.py::TentacleInstaller.provision(cls, host, upgrade=False, target=None, python=None, specs=None)`
- `tentacle_installer.py::TentacleInstaller.python_exe(host)`
- `tentacle_installer.py::TentacleInstaller.read_manifest(cls, target)`
- `tentacle_installer.py::TentacleInstaller.register_blender_ui(cls, addon_name)`
- `tentacle_installer.py::TentacleInstaller.request(cls, host, verb)`
- `tentacle_installer.py::TentacleInstaller.shutdown(cls)`
- `tentacle_installer.py::TentacleInstaller.specs(cls, host, fresh=True)`
- `tentacle_installer.py::TentacleInstaller.target_dir(cls, host)`
- `tentacle_installer.py::TentacleInstaller.uninstall(cls, host, target=None, python=None)`
- `tentacle_installer.py::TentacleInstaller.unregister_blender_ui(cls)`
- `tentacle_installer.py::TentacleInstaller.update(cls, host, target=None, python=None)`
- `tentacle_installer.py::TentacleInstaller.write_manifest(cls, target, **updates)`
- `tentacle_installer.py::TentacleInstaller.write_maya_module(cls, source, app_dir=None, version=None)`
- `tentacle_installer.py::onMayaDroppedPythonFile(*_args)`
- `tentacle_installer.py::register()`
- `tentacle_installer.py::unregister()`
