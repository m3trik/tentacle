# Python

How the principles are spelled in Python; the rationale is CODE_STANDARD (`§N`).

- **Versions**: Python 3.9+; Qt is PySide6 through `qtpy` only. Style (ruff / PEP 8, Google docstrings with `Parameters:`, typed public signatures) is applied at review, not while prototyping (§1, §2).
- **Layout** (§3): `class MyClass` lives in `my_class.py`; `<x>_utils/_<x>_utils.py` holds `<X>Utils`, features are `snake_case.py`, never a nested `*_utils`; a feature earns `<feature>/` at a second cohesive module, internals or an asset dir; a `_`-prefixed module is internal.
- **Encapsulate** (§4): logic on classes, called through the class namespace; helpers on a `_<Class>Internal` base; never a flat `pkg.fn` wrapper.
- **Imports** (§4): no side effects; another package only through its root (`ptk.X`), never its `_` modules. Lazy by default: an `__init__` declares, never imports (the root's `DEFAULT_INCLUDE`, a subpackage's `lazy_exports`); an eager import says why.
- **Before writing a helper**, search for it: `api.search` (MCP `api_search`; `python -m pythontk ops run api.search "query=<words>"`).
- **Adapters** are `runtime_checkable` Protocols beside the model with a `Pure*` default; a library class keeping a shared class's name configures and adds, never overrides.
- **Operations**: a function agents and front ends call has typed arguments and an optional `ctx` (`ptk.OpContext`) it asks before each change (`should_change`, `should_create`, `should_delete`, `should_write`); it is declared in the package's `operations.py`, whose committed `operations.json` the `operations.catalog` operation rewrites and `operations.check` holds.
- **Line endings**: LF for scripts that run on Linux; `.bat` CRLF.
