"""조사 전용 재현: Python 소스 실행 없이 선정85를 고정 config로 식별한다.

저장소 루트에서 --output <존재하지 않는 새 JSON 경로>로 실행한다.
입력 파일은 읽기만 하며 source 모듈 import/표현식 평가를 하지 않는다.
"""

import argparse
import ast
import hashlib
import json
from collections import Counter
from pathlib import Path


def sha(data):
    return hashlib.sha256(data).hexdigest()


def file_sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def literal(node):
    """검토한 지역 상수의 literal AST만 읽고 나머지는 거부한다."""
    if isinstance(node, ast.Constant) and type(node.value) in (
        str,
        int,
        float,
        bool,
        type(None),
    ):
        return node.value
    if isinstance(node, (ast.List, ast.Tuple)):
        items = [literal(item) for item in node.elts]
        return tuple(items) if isinstance(node, ast.Tuple) else items
    if isinstance(node, ast.Dict):
        return {
            literal(key): literal(value) for key, value in zip(node.keys, node.values)
        }
    raise ValueError("nonliteral AST: " + type(node).__name__)


def constant(path, name):
    for node in ast.parse(path.read_text()).body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            if isinstance(node.targets[0], ast.Name) and node.targets[0].id == name:
                return literal(node.value)
    raise ValueError("missing constant: " + name)


def reproduce(baseline):
    base = Path("runs/strategy-registration-review")
    manifest = json.loads((base / "manifest.json").read_text())
    verification = json.loads((base / "verification.json").read_text())
    manifest_hash = file_sha(base / "manifest.json")
    assert manifest_hash == (base / "manifest.sha256").read_text().split()[0]
    assert manifest_hash == verification["manifest_sha256"]
    assert manifest_hash == baseline["manifest_integrity"]["actual_sha256"]
    inputs = []
    for relative, expected in manifest["input_artifacts"].items():
        path = Path(manifest["source_experiment"]) / relative
        assert file_sha(path) == expected, str(path)
        inputs.append({"path": str(path), "sha256": expected})
    catalogue = Path("tools/research/catalogue.py")
    swing = Path("tools/research/swing_signals.py")
    template_path = Path("tools/research/strategy_template.py.txt")
    filters, signals = constant(catalogue, "FILTERS"), constant(catalogue, "SIGNALS")
    block, template = constant(swing, "POSITION_BLOCK"), template_path.read_text()
    markers = [
        "__LONG_FILTER__",
        "__SHORT_FILTER__",
        "__LONG_SIGNAL__",
        "__SHORT_SIGNAL__",
    ]
    assert template.count(block) == 1 and all(
        template.count(key) == 1 for key in markers
    )
    lookup, generated_hashes = {}, set()
    for filter_id, (_, long_filter, short_filter) in filters.items():
        for signal_id, (_, long_signal, short_signal) in signals.items():
            candidate_id = f"hyp-v2-{filter_id}-{signal_id}"
            original = template
            for key, value in zip(
                markers, [long_filter, short_filter, long_signal, short_signal]
            ):
                original = original.replace(key, value)
            for policy, source in [
                ("source", original),
                ("swing", original.replace(block, "", 1)),
            ]:
                tree = ast.parse(source)
                assert not any(
                    isinstance(node, (ast.Import, ast.ImportFrom))
                    for node in ast.walk(tree)
                )
                on_bar = next(
                    node
                    for node in tree.body
                    if isinstance(node, ast.FunctionDef) and node.name == "on_bar"
                )
                if policy == "swing":
                    assert not any(
                        isinstance(node, ast.Name)
                        and node.id in {"position", "side", "risk_exit"}
                        for node in ast.walk(on_bar)
                    )
                config = {
                    "filter_id": filter_id,
                    "signal_id": signal_id,
                    "exit_policy": policy,
                }
                lookup[(candidate_id, policy)] = (source, sha(source.encode()), config)
                generated_hashes.add(sha(source.encode()))

    def identify(candidate_id, policy, source, params, warmup):
        found = lookup.get((candidate_id, policy))
        if found is None or source != found[0] or params != {} or warmup != 200:
            return None
        return found

    rows = []
    for record in manifest["records"]:
        source = (base / record["source_path"]).read_text()
        found = identify(
            record["candidate_id"],
            record["execution_policy"],
            source,
            record["params"],
            record["warmup_bars"],
        )
        assert found is not None, record["candidate_id"]
        assert found[1] == record["source_sha256"] == sha(source.encode())
        rows.append(
            {
                "candidate_id": record["candidate_id"],
                "execution_policy": record["execution_policy"],
                "source_sha256": found[1],
                "config": found[2],
            }
        )
    first = rows[0]
    candidate_id, policy = first["candidate_id"], first["execution_policy"]
    source = lookup[(candidate_id, policy)][0]
    negatives = [
        (
            "unknown_candidate_id",
            identify("hyp-v2-unknown-roc_zero", policy, source, {}, 200),
        ),
        ("unknown_exit_policy", identify(candidate_id, "unknown", source, {}, 200)),
        (
            "source_changed_by_comment",
            identify(candidate_id, policy, source + "\n# changed\n", {}, 200),
        ),
        (
            "unsupported_params",
            identify(candidate_id, policy, source, {"extra": 1}, 200),
        ),
        ("changed_warmup", identify(candidate_id, policy, source, {}, 201)),
    ]
    negative_checks = [
        {"case": case, "rejected": found is None} for case, found in negatives
    ]
    assert all(item["rejected"] for item in negative_checks)
    counts = {
        "total": len(rows),
        "identified_exact_config": len(rows),
        "unknown_or_rejected": 0,
        "policy_counts": dict(Counter(row["execution_policy"] for row in rows)),
        "distinct_hypotheses": len({row["candidate_id"] for row in rows}),
    }
    catalogue_counts = {
        "filters": len(filters),
        "signals": len(signals),
        "hypotheses": len(filters) * len(signals),
        "generated_source_policy_variants": len(lookup),
        "unique_generated_hashes": len(generated_hashes),
        "all_generated_variants_ast_parse": True,
        "single_exact_position_anchor": True,
        "all_four_placeholders_single_occurrence": True,
    }
    source_inputs = {
        str(path): file_sha(path) for path in [catalogue, template_path, swing]
    }
    assert counts == baseline["selected_records"]
    assert catalogue_counts == baseline["catalogue"]
    assert source_inputs == baseline["source_inputs"]
    assert negative_checks == baseline["negative_identification_probes"]
    assert [
        (row["candidate_id"], row["execution_policy"], row["source_sha256"])
        for row in rows
    ] == [
        (row["candidate_id"], row["execution_policy"], row["source_sha256"])
        for row in baseline["records"]
    ]
    return {
        "passed": True,
        "baseline_core_equal": True,
        "manifest_sha256": manifest_hash,
        "selected_records": counts,
        "catalogue": catalogue_counts,
        "source_inputs": source_inputs,
        "frozen_input_artifacts": inputs,
        "negative_identification_probes": negative_checks,
        "executed_strategy_source": False,
        "executed_catalogue_module": False,
        "evaluated_filter_signal_expressions": False,
        "numerical_parity_verified": False,
        "scope": "source/config identity only; not computation replay or production validator",
        "records": rows,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--baseline",
        type=Path,
        default=Path(
            "runs/python-strategy-methodology/agents/conversion/coverage-census.json"
        ),
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() or args.output.resolve() == args.baseline.resolve():
        parser.error("output은 기존 입력/결과를 덮어쓰지 않는 새 경로여야 합니다")
    result = reproduce(json.loads(args.baseline.read_text()))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x") as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
    print(
        json.dumps(
            {
                "passed": result["passed"],
                "baseline_core_equal": result["baseline_core_equal"],
                "selected_records": result["selected_records"],
                "manifest_sha256": result["manifest_sha256"],
                "negative_probes_rejected": sum(
                    item["rejected"]
                    for item in result["negative_identification_probes"]
                ),
                "output": str(args.output),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
