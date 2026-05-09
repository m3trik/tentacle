"""Tentacle benchmarks.

Real-world Maya benches that subclass uitk's reusable bench harnesses
(``uitk/test/bench/``).  Each file here is loaded by ``run_in_maya``
via :func:`importlib.util.spec_from_file_location` under a private
module name (``_tentacle_bench_runner_module``) — so the bare key
``bench`` in :data:`sys.modules` stays reserved for uitk's bench
package, which is what each bench file's ``from bench.<name> import
<Class>`` resolves against.

That import works because ``run_in_maya`` puts ``uitk/test`` on
``sys.path`` before exec'ing the bench module.  This package's
``__init__`` is intentionally inert — putting path-setup logic here
would not run under the importlib path (the runner bypasses package
init) and would conflict with uitk's ``bench`` package on the bare
``sys.path`` lookup.
"""
