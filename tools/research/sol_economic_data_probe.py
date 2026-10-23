"""선정·native 없이 동결 원 loader의12cell DataFrame 해시만 관찰한다."""

import argparse
import ast
import hashlib
import importlib.abc
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import sys

ECONOMICS_SHA = "6f47ecf5a6168b91383ff1d0338f3afbd3c0f3cb3e3431b8b07465c6b54917ed"
DATA_SHA = "edb6db7731871f485d16f21e8abe76bbe835ccc65d6d21eac4cd60b246f786f6"
SNAPSHOT_SHA = "37c603f7bd3c0dbcc384ca3678eaf27e44d4750dc57562024e37cca31f3fd6f1"


def sha(path):
    value = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024**2), b""):
            value.update(block)
    return value.hexdigest()


def guard(source, snapshot, pending):
    if (sha(snapshot) != SNAPSHOT_SHA or sha(source / "tools/research/sol_economics.py") != ECONOMICS_SHA
            or sha(source / "tools/research/sol_economic_data.py") != DATA_SHA
            or len(pending.get("source_hashes", {})) != 63 or len(pending.get("postprocess_hashes", {})) != 7):
        raise ValueError("original_economic_data_sources_required")
    for group in ("source_hashes", "postprocess_hashes"):
        for name, checksum in pending[group].items():
            path = (source / name).resolve()
            if not path.is_relative_to(source.resolve()) or path.is_symlink() or sha(path) != checksum:
                raise ValueError("frozen_source_or_postprocess_changed")
    for directory in (Path.cwd(), source, source / "apps/api"):
        if any(directory.glob(".env*")):
            raise ValueError("environment_file_present")


class DataOnlyImports(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if (fullname == "src" or fullname.startswith("src.") or fullname.split(".")[0] in {"celery", "ccxt", "openai", "anthropic", "google"}
                or fullname in {"tools.research.sol_economics", "tools.research.sol_score_report", "tools.research.sol_codegen", "tools.research.sol_strategy_lab"}):
            raise RuntimeError("model_native_selection_import_forbidden")
        return None


def audit(event, args):
    if event in {"socket.connect", "socket.connect_ex", "socket.bind", "subprocess.Popen", "os.system", "os.posix_spawn", "os.fork", "os.forkpty"}:
        raise RuntimeError("network_or_process_forbidden_in_data_probe")


def original_functions(source, pd, assets, timeframes):
    tree = ast.parse((source / "tools/research/sol_economics.py").read_text())
    functions = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in {"cells", "frame_hash"}]
    if [node.name for node in functions] != ["cells", "frame_hash"]:
        raise ValueError("original_data_function_shape")
    namespace = {"pd": pd, "hashlib": hashlib, "json": json, "ASSETS": assets, "TIMEFRAMES": timeframes}
    exec(compile(ast.Module(body=functions, type_ignores=[]), str(source / "tools/research/sol_economics.py"), "exec"), namespace)
    return namespace["cells"], namespace["frame_hash"]


def observe(loader, cell_builder, frame_hash, snapshot_path):
    snapshot = loader.load_snapshot(snapshot_path)
    rows = []
    for cell in cell_builder(snapshot):
        frames = loader.load_economic_cell(snapshot_path, cell["symbol"], cell["timeframe"],
            cell["start"], cell["end"], execution=cell["execution"], warmup_bars=snapshot["warmup_bars"])
        rows.append({"cell": cell, "hashes": dict(zip(("parent", "funding_observed", "execution"),
            map(frame_hash, frames), strict=True)), "rows": [None if frame is None else len(frame) for frame in frames]})
    if len(rows) != 12 or len({row["cell"]["id"] for row in rows}) != 12:
        raise ValueError("exact_twelve_data_cells_required")
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("source-root", "snapshot", "pending", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    source, snapshot = args.source_root.resolve(), args.snapshot.resolve()
    pending = json.loads(args.pending.read_text())
    guard(source, snapshot, pending)
    versions = {name: importlib.metadata.version(name) for name in ("numpy", "pandas")}
    if versions != pending["package_versions"] or platform.python_version() != pending["python_version"]:
        raise ValueError("original_python_package_versions_required")
    import pandas as pd
    sys.meta_path.insert(0, DataOnlyImports())
    sys.addaudithook(audit)
    sys.path.insert(0, str(source))
    from tools.research import sol_economic_data as loader
    cells, frame_hash = original_functions(source, pd, loader.ASSETS, loader.TIMEFRAMES)
    rows = observe(loader, cells, frame_hash, snapshot)
    result = {"schema_version": 1, "status": "DATA_HASHES_ONLY_NO_ECONOMICS", "cells": rows,
        "snapshot_sha256": sha(snapshot), "data_source_sha256": DATA_SHA, "economics_source_sha256": ECONOMICS_SHA,
        "probe_sha256": sha(__file__), "python": platform.python_version(), "packages": versions,
        "machine": platform.machine(), "system": platform.system(), "native_calls": 0,
        "selection_read": False, "historical_daily_loaded_for_parser_check_only": True}
    args.output.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd = os.open(args.output, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(fd, "w") as stream:
        json.dump(result, stream, sort_keys=True, allow_nan=False)


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print("economic data probe failed: " + type(error).__name__, file=sys.stderr)
        raise SystemExit(1) from None
