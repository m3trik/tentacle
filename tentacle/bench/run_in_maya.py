"""Launch a fresh Maya, run an :class:`OptionBoxInitBench` subclass, capture JSON.

Per the monorepo session-safety rule (``mayatk/CLAUDE.md``), every run
launches a **new** Maya GUI instance; the bench must never attach to a
live session.

This driver deliberately does **not** use Maya's command port.  Sending
bench code over the port and calling ``processEvents`` from the
exec-on-port handler is reentrant and crashes Maya during ``Menu.add``
deferred-timer drain.  Instead we install a startup command (via
``maya.utils.executeDeferred``) that runs the bench inside Maya's own
event loop — the same loop the user's tentacle session uses — then
writes JSON to a file before calling ``cmds.quit``.

Usage::

    python -m tentacle.bench.run_in_maya \\
        tentacle.bench.option_box:TentacleOptionBoxBench \\
        --ui edit --label baseline --samples 3

The first positional arg is a ``module.path:ClassName`` spec for the
bench class.

Optional ``--diff`` compares against a previously-saved JSON and prints
per-phase deltas suitable for before/after reporting.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Path injection on the Maya side
# ---------------------------------------------------------------------------

# These dirs are inserted into sys.path inside the launched Maya so the
# bench class and its dependencies resolve consistently with the dev
# checkout.  Edit if your monorepo lives elsewhere.
DEFAULT_MAYA_SYSPATH = [
    # tentacle/tentacle/bench/run_in_maya.py -> parents[3] = monorepo root
    str(Path(__file__).resolve().parents[3] / p)
    for p in ("pythontk", "uitk", "mayatk", "tentacle")
]


# ---------------------------------------------------------------------------
# Bench-runner template (executed inside Maya's native event loop)
# ---------------------------------------------------------------------------

_RUNNER_TEMPLATE = r'''
"""Bench runner — written by tentacle.bench.run_in_maya into a temp file.

Maya boots normally, fires our ``-command`` MEL on startup which calls
``executeDeferred`` so we run *after* the main window + autoload have
finished.  We then build the bench, run it, write JSON, and quit Maya.
"""
import json, os, sys, traceback


SYSPATH = __SYSPATH__
BENCH_SPEC = __BENCH_SPEC__
UI_NAME = __UI_NAME__
LABEL = __LABEL__
OUT_PATH = __OUT_PATH__
ERR_PATH = __ERR_PATH__


def _bench_main():
    try:
        for p in SYSPATH:
            if p not in sys.path:
                sys.path.insert(0, p)

        mod_name, cls_name = BENCH_SPEC.split(":", 1)
        mod = __import__(mod_name, fromlist=[cls_name])
        BenchCls = getattr(mod, cls_name)
        bench = BenchCls(ui_name=UI_NAME, label=LABEL)

        result = bench.run()

        with open(OUT_PATH, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)
    except Exception:
        with open(ERR_PATH, "w", encoding="utf-8") as f:
            traceback.print_exc(file=f)
    finally:
        try:
            import maya.cmds as cmds
            cmds.quit(force=True)
        except Exception:
            os._exit(0)


# Defer until Maya's main window + autoload are settled.  Without this
# the bench runs while Maya is still in early init, which breaks UI
# loading and slot registration in subtle ways.
import maya.utils
maya.utils.executeDeferred(_bench_main)
'''


def _build_runner_script(
    bench_spec: str,
    ui_name: str,
    label: str,
    syspath: list[str],
    out_path: Path,
    err_path: Path,
) -> Path:
    src = (
        _RUNNER_TEMPLATE
        .replace("__SYSPATH__", json.dumps(syspath))
        .replace("__BENCH_SPEC__", json.dumps(bench_spec))
        .replace("__UI_NAME__", json.dumps(ui_name))
        .replace("__LABEL__", json.dumps(label))
        .replace("__OUT_PATH__", json.dumps(str(out_path)))
        .replace("__ERR_PATH__", json.dumps(str(err_path)))
    )
    fd, runner_path = tempfile.mkstemp(prefix="tentacle_bench_", suffix=".py")
    os.close(fd)
    Path(runner_path).write_text(src, encoding="utf-8")
    return Path(runner_path)


# ---------------------------------------------------------------------------
# Maya launch
# ---------------------------------------------------------------------------


def _find_maya_exe() -> str:
    candidates = [
        os.environ.get("MAYA_EXE"),
        r"C:\Program Files\Autodesk\Maya2025\bin\maya.exe",
        r"C:\Program Files\Autodesk\Maya2024\bin\maya.exe",
    ]
    for c in candidates:
        if c and Path(c).is_file():
            return c
    raise FileNotFoundError(
        "maya.exe not found.  Set $MAYA_EXE or edit _find_maya_exe()."
    )


def _run_one_sample(
    bench_spec: str,
    ui_name: str,
    label: str,
    syspath: list[str],
    launch_args: list[str],
    timeout_s: int = 300,
) -> Optional[dict[str, Any]]:
    """Spawn a fresh Maya, run the bench-runner, return the JSON result."""
    sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "pythontk"))
    from pythontk import AppLauncher

    out_dir = Path(tempfile.gettempdir())
    out_path = out_dir / f"tentacle_bench_out_{os.getpid()}_{int(time.time() * 1000)}.json"
    err_path = out_path.with_suffix(".err.txt")
    out_path.unlink(missing_ok=True)
    err_path.unlink(missing_ok=True)

    runner_path = _build_runner_script(
        bench_spec=bench_spec,
        ui_name=ui_name,
        label=label,
        syspath=syspath,
        out_path=out_path,
        err_path=err_path,
    )

    # MEL ``python(...)`` to bridge Maya's startup MEL into Python.  We
    # use a doubly-escaped string for the inner Python so the literal
    # path survives MEL parsing.
    runner_str = str(runner_path).replace("\\", "/")
    mel_command = (
        f'python("exec(open(r\'{runner_str}\').read())")'
    )

    args = ["-command", mel_command]
    if launch_args:
        args.extend(launch_args)

    maya_exe = _find_maya_exe()
    print(f"[run_in_maya] launching fresh Maya ({maya_exe})")
    process = AppLauncher.launch(maya_exe, args=args, detached=True)
    if process is None:
        print("[run_in_maya] AppLauncher returned None — launch failed")
        return None

    # Poll for the result file or process exit.
    start = time.time()
    while True:
        if out_path.exists() and out_path.stat().st_size > 0:
            # Result file written; wait briefly for Maya to start exiting.
            break
        if err_path.exists() and err_path.stat().st_size > 0:
            break
        if process.poll() is not None:
            # Maya exited without writing the result file.
            break
        if time.time() - start > timeout_s:
            print(f"[run_in_maya] timeout ({timeout_s}s) — killing Maya")
            try:
                process.kill()
            except Exception:
                pass
            return None
        time.sleep(0.5)

    # Wait for process to actually exit (cmds.quit takes a moment).
    try:
        process.wait(timeout=30)
    except Exception:
        try:
            process.kill()
        except Exception:
            pass

    # Cleanup runner script
    try:
        runner_path.unlink(missing_ok=True)
    except Exception:
        pass

    if err_path.exists() and err_path.stat().st_size > 0:
        print("[run_in_maya] bench raised inside Maya:")
        print(err_path.read_text(encoding="utf-8"))
        err_path.unlink(missing_ok=True)
        return None

    if not out_path.exists() or out_path.stat().st_size == 0:
        print("[run_in_maya] no JSON produced — Maya exited without result")
        return None

    try:
        result = json.loads(out_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"[run_in_maya] result file unparseable: {exc}")
        return None
    finally:
        try:
            out_path.unlink(missing_ok=True)
        except Exception:
            pass

    return result


# ---------------------------------------------------------------------------
# Aggregation + diff
# ---------------------------------------------------------------------------


def _aggregate_samples(
    samples: list[dict[str, Any]], label: str, ui_name: str
) -> dict[str, Any]:
    """Merge N single-shot samples into best-of / median tables."""
    if not samples:
        return {}

    keys = list(samples[0].get("phases_ms_best", {}).keys())

    def _vals(k):
        return [s["phases_ms_best"][k] for s in samples if k in s["phases_ms_best"]]

    def _median(vals):
        s = sorted(vals)
        mid = len(s) // 2
        return s[mid] if len(s) % 2 else (s[mid - 1] + s[mid]) / 2

    best = {k: round(min(_vals(k)), 3) for k in keys if _vals(k)}
    median = {k: round(_median(_vals(k)), 3) for k in keys if _vals(k)}

    init_keys = ("04_register_children_sync", "05_drain_deferred_timers")
    init_total = round(sum(best.get(k, 0.0) for k in init_keys), 3)

    return {
        "label": label,
        "ui": ui_name,
        "samples": len(samples),
        "widget_count": samples[0].get("widget_count"),
        "wrapped_menus": samples[0].get("wrapped_menus"),
        "total_menu_items": samples[0].get("total_menu_items"),
        "sample_widget": samples[0].get("sample_widget"),
        "phases_ms_best": best,
        "phases_ms_median": median,
        "all_samples": [s.get("phases_ms_best", {}) for s in samples],
        "init_total_ms_best": init_total,
        "first_show_ms_best": best.get("06_first_show_option_box_menu"),
    }


def _print_diff(baseline: dict[str, Any], current: dict[str, Any]) -> None:
    print("\n# DIFF (baseline vs current, ms — negative = faster)")
    print(f"  baseline label : {baseline.get('label')}")
    print(f"  current  label : {current.get('label')}")
    print(f"{'phase':<48} {'before':>10} {'after':>10} {'delta':>10} {'pct':>7}")
    print("-" * 92)
    base = baseline.get("phases_ms_best", {})
    curr = current.get("phases_ms_best", {})
    for key in sorted(set(base) | set(curr)):
        b = base.get(key, float("nan"))
        c = curr.get(key, float("nan"))
        if b != b or c != c:
            continue
        delta = c - b
        pct = (delta / b * 100) if b else 0.0
        print(f"{key:<48} {b:>10.2f} {c:>10.2f} {delta:>10.2f} {pct:>6.1f}%")
    print("-" * 92)
    for key in ("init_total_ms_best", "first_show_ms_best"):
        b = baseline.get(key)
        c = current.get(key)
        if b is None or c is None:
            continue
        delta = c - b
        pct = (delta / b * 100) if b else 0.0
        print(f"{key:<48} {b:>10.2f} {c:>10.2f} {delta:>10.2f} {pct:>6.1f}%")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument(
        "bench_spec",
        help="Bench class to instantiate, formatted ``module.path:ClassName``",
    )
    p.add_argument("--ui", default=None, help="UI name to load (default: bench's DEFAULT_UI)")
    p.add_argument("--label", default="run")
    p.add_argument(
        "--samples",
        type=int,
        default=1,
        help="Number of fresh Maya launches to aggregate (best/median across samples).",
    )
    p.add_argument(
        "--out",
        default=None,
        help="Path to write the resulting JSON.  Defaults to bench_<label>_<ui>.json next to the driver.",
    )
    p.add_argument(
        "--diff",
        default=None,
        help="Path to a previously-saved JSON to diff against (prints deltas).",
    )
    p.add_argument(
        "--maya-syspath",
        nargs="*",
        default=None,
        help="Extra dirs to add to Maya's sys.path (defaults to monorepo packages).",
    )
    p.add_argument(
        "--launch-args",
        nargs="*",
        default=["-noAutoloadPlugins"],
        help="Extra args forwarded to maya.exe at launch.",
    )
    p.add_argument(
        "--timeout",
        type=int,
        default=300,
        help="Per-sample timeout in seconds (default 300).",
    )
    args = p.parse_args()

    if not re.match(r"[\w\.]+:[\w_]+$", args.bench_spec):
        p.error(f"bench_spec must be 'module.path:ClassName', got {args.bench_spec!r}")

    syspath = args.maya_syspath if args.maya_syspath is not None else DEFAULT_MAYA_SYSPATH

    ui_name = args.ui or "edit"

    samples: list[dict[str, Any]] = []
    for i in range(max(1, args.samples)):
        print(f"\n========== sample {i + 1}/{args.samples} ==========")
        sample = _run_one_sample(
            bench_spec=args.bench_spec,
            ui_name=ui_name,
            label=f"{args.label}#{i + 1}",
            syspath=syspath,
            launch_args=args.launch_args,
            timeout_s=args.timeout,
        )
        if sample is None:
            print(f"[run_in_maya] sample {i + 1} failed; aborting")
            return 3
        samples.append(sample)

    result = (
        samples[0] if len(samples) == 1 else _aggregate_samples(samples, args.label, ui_name)
    )
    if len(samples) > 1:
        result["label"] = args.label
        result["ui"] = ui_name

    out_path = (
        Path(args.out)
        if args.out
        else Path(__file__).parent / f"bench_{args.label}_{ui_name}.json"
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, indent=2))
    print(f"\n[run_in_maya] wrote {out_path}")

    # Pretty-print
    print()
    print(f"{'phase':<48} {'best ms':>10} {'median ms':>12}")
    print("-" * 72)
    best = result.get("phases_ms_best", {})
    median = result.get("phases_ms_median", best)
    for k in sorted(best):
        print(f"{k:<48} {best[k]:>10.2f} {median.get(k, 0):>12.2f}")
    print("-" * 72)
    print(f"{'init total (04+05)':<48} {result.get('init_total_ms_best', 0):>10.2f}")
    print(f"{'first show (06)':<48} {(result.get('first_show_ms_best') or 0):>10.2f}")

    if args.diff:
        try:
            baseline = json.loads(Path(args.diff).read_text())
        except Exception as exc:
            print(f"[run_in_maya] couldn't read --diff baseline: {exc}")
        else:
            _print_diff(baseline, result)

    return 0


if __name__ == "__main__":
    sys.exit(main())
