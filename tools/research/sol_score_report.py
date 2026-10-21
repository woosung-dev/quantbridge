"""동결 실험 전체 분모의 품질 보고서. 모델·컨테이너·거래소를 실행하지 않는다.

python -m tools.research.sol_score_report --run-dir runs/... --output runs/.../quality.json
최종 full-eval 완료 후 정책의 후보를 --quality-selection B/typescript로 확인해야만
같은 디렉터리에 quality.selection.json·quality.artifacts.json을 생성한다.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
import random
import statistics
import sys
from collections import Counter
from functools import cache
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "apps/api"))

from tools.research.sol_codegen import CODE_SCHEMA, digest, strict_schema  # noqa: E402
from tools.research.sol_semantic_eval import paired_summary  # noqa: E402

SEED = 20261022
ACTIONS = ("hold", "long", "short", "close")
POINTS = ("contract_points", "ledger_points", "reproducibility_points")
SELECTION_POLICY = "quality90_then_known_tokens_then_known_p95_then_lexicographic_v1"


def selection_decision(cells: list[dict]) -> dict:
    """점수 공식과 분리한 사전 선정 순서다. 미관측 기준은 동률 집합 전체에서 건너뛴다."""
    if not cells or len({cell["combination"] for cell in cells}) != len(cells):
        raise ValueError("중복 없는 선정 조합이 필요합니다")
    quality = max(_number(cell["quality90"]) for cell in cells)
    tied = [cell for cell in cells if cell["quality90"] == quality]
    reasons = ["unique_quality90_maximum" if len(tied) == 1 else "exact_quality90_tie"]
    criteria = (
        (
            "all_attempt_output_tokens",
            "generation_output_tokens",
            "unknown_output_usage_calls",
            "generation_metric_observations",
        ),
        (
            "total_generation_p95",
            "generation_seconds_p95",
            "unknown_duration_calls",
            "generation_duration_observations",
        ),
    )
    for name, metric, unknown, observations in criteria:
        if len(tied) == 1:
            break
        if any(
            cell.get(unknown) != 0
            or cell.get(observations) != cell.get("expected_artifacts")
            or cell.get(metric) is None
            for cell in tied
        ):
            reasons.append(f"{name}_skipped_incomplete_observation")
            continue
        minimum = min(_number(cell[metric]) for cell in tied)
        tied = [cell for cell in tied if cell[metric] == minimum]
        reasons.append(f"{name}_minimum" if len(tied) == 1 else f"{name}_exact_tie")
    if len(tied) > 1:
        reasons.append("lexicographic_order_no_superiority_claim")
    return {
        "policy": SELECTION_POLICY,
        "selected_candidate": min(cell["combination"] for cell in tied),
        "tie_reason": reasons,
    }


C_SUFFIX = (
    "\n실행코드를내지말고주어진닫힌StrategySpec schema의명세를내세요. "
    "지표id/parameters/entry/invalidation을정확히표현하세요. warmup_bars=200. "
    "가격은open/high/low/close/volume/hlc3를참조합니다. "
    "지원못하는패턴을다른전략으로바꾸지마세요."
)


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def quantile(values: list[float], probability: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = (len(ordered) - 1) * probability
    low = math.floor(index)
    return ordered[low] + (ordered[math.ceil(index)] - ordered[low]) * (index - low)


def _number(value: Any) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or value < 0
    ):
        raise ValueError("유한한 음수 아닌 관측치가 필요합니다")
    return float(value)


def _load(path: Path, root: Path, evidence: dict[str, str]) -> dict:
    evidence[str(path.relative_to(root))] = file_hash(path)
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise ValueError(f"JSON 객체가 필요합니다: {path}")
    return value


@cache
def _schema(arm: str) -> dict:
    if arm != "C":
        return CODE_SCHEMA
    from src.strategy.code_runtime.spec import StrategySpec

    return StrategySpec.model_json_schema()


def _trial(
    root: Path,
    manifest: dict,
    manifest_hash: str,
    case: dict,
    arm: str,
    language: str,
    repetition: int,
    evidence: dict[str, str],
) -> dict:
    folder = root / "trials" / arm / language / case["id"] / str(repetition)
    row = {
        "case_id": case["id"],
        "arm": arm,
        "language": language,
        "repetition": repetition,
        "status": "missing",
        "semantic": {},
    }
    trial_path = folder / "trial.json"
    if not trial_path.exists():
        row["observation"] = "interrupted" if folder.exists() else "missing"
        return row
    trial = _load(trial_path, root, evidence)
    if trial.get("status") not in ("public_pass", "failed"):
        row["observation"] = "interrupted"
        return row
    for key in ("case_id", "arm", "language", "repetition"):
        if trial.get(key) != row[key]:
            raise ValueError(f"trial 경로·정체성이 다릅니다: {trial_path}")
    prompt = (
        manifest["contract"]
        + "\n"
        + manifest["language_contracts"][language]
        + "\n전략의 정확한 요구:\n"
        + case["prompt"]
    )
    if arm == "C":
        prompt += C_SUFFIX
    schema = _schema(arm)
    identity = digest(
        {
            "prompt": prompt,
            "schema": schema,
            "model": manifest["model"],
            "effort": manifest["effort"],
            "arm": arm,
            "language": language,
            "repetition": repetition,
            "manifest_hash": manifest_hash,
        }
    )
    if trial.get("input_identity") != identity:
        raise ValueError(f"trial 입력 hash가 다릅니다: {trial_path}")
    attempts = trial.get("attempts", [])
    if not isinstance(attempts, list) or not 1 <= len(attempts) <= (1 if arm == "A" else 3):
        raise ValueError("방식별 생성·수정 호출 수가 다릅니다")
    tokens, seconds = 0.0, 0.0
    initial_tokens = 0.0
    final_payload = None
    durations: list[float | None] = []
    for index, attempt in enumerate(attempts):
        directory = folder / f"attempt-{index}"
        generation = _load(directory / "generation.json", root, evidence)
        request = _load(directory / "request.json", root, evidence)
        if generation != attempt.get("generation") or generation.get("job_hash") != digest(request):
            raise ValueError("generation/request hash가 다릅니다")
        if (
            request.get("model") != manifest["model"]
            or request.get("effort") != manifest["effort"]
            or request.get("schema") != strict_schema(schema)
        ):
            raise ValueError("생성 model/effort/schema가 manifest와 다릅니다")
        if index == 0 and request.get("prompt") != prompt:
            raise ValueError("최초 prompt가 manifest와 다릅니다")
        if generation.get("status") == "completed":
            payload = _load(directory / "payload.json", root, evidence)
            if generation.get("payload_hash") != digest(payload):
                raise ValueError("생성 payload hash가 다릅니다")
        if index == len(attempts) - 1 and generation.get("status") == "completed":
            final_payload = payload
        used_tokens = _number(generation.get("usage", {}).get("output_tokens", 0))
        used_seconds = _number(generation.get("duration_seconds", 0))
        # interrupted의 timeout 값은 중단 후 복구된 선언 한도이며 실제 경과 관측이 아니다.
        durations.append(
            used_seconds
            if "duration_seconds" in generation
            and generation.get("status") != "interrupted"
            else None
        )
        if index == 0:
            initial_tokens = used_tokens
        tokens += used_tokens
        seconds += used_seconds
    if tokens != _number(trial.get("generation_output_tokens")) or not math.isclose(
        seconds, _number(trial.get("generation_seconds")), abs_tol=1e-6
    ):
        raise ValueError("생성 합계와 attempt 증거가 다릅니다")
    if (trial["status"] == "public_pass") != (
        attempts[-1].get("validation", {}).get("passed") is True
    ):
        raise ValueError("trial/public validation 종결 상태가 다릅니다")
    if trial["status"] == "public_pass":
        if final_payload is None:
            raise ValueError("성공한 생성 payload가 없습니다")
        if arm == "C":
            from src.strategy.code_runtime.compiler import compile_strategy
            from src.strategy.code_runtime.spec import StrategySpec

            expected_source = compile_strategy(StrategySpec.model_validate(final_payload), language)
        else:
            expected_source = final_payload.get("source_code")
        if not isinstance(expected_source, str) or hashlib.sha256(
            expected_source.encode()
        ).hexdigest() != trial.get("source_hash"):
            raise ValueError("source와 생성 payload hash가 다릅니다")
        source_path = folder / "source.txt"
        if not source_path.is_file() or file_hash(source_path) != trial.get("source_hash"):
            raise ValueError("실행 source hash가 다릅니다")
        evidence[str(source_path.relative_to(root))] = file_hash(source_path)
    row.update(trial)
    row["public_status"] = trial["status"]
    row["initial_public_pass"] = attempts[0].get("validation", {}).get("passed") is True
    row["repair_calls"] = len(attempts) - 1
    row["unknown_output_usage_calls"] = sum(
        "output_tokens" not in attempt["generation"].get("usage", {}) for attempt in attempts
    )
    row.update(
        initial_output_tokens=initial_tokens,
        repair_output_tokens=tokens - initial_tokens,
        initial_seconds=durations[0],
        repair_seconds=sum(durations[1:])
        if all(x is not None for x in durations[1:])
        else None,
        unknown_duration_calls=sum(x is None for x in durations),
        observed_generation_seconds=seconds
        if all(x is not None for x in durations)
        else None,
    )
    semantic_path = folder / "semantic.json"
    if not semantic_path.exists():
        row.update(status="missing", observation="semantic_missing", semantic={})
        return row
    semantic = _load(semantic_path, root, evidence)
    if semantic.get("input_identity") != identity:
        raise ValueError("semantic/trial 입력 hash가 다릅니다")
    if "source_hash" not in semantic or semantic["source_hash"] != trial.get("source_hash"):
        raise ValueError("semantic/trial 실행 source hash가 다릅니다")
    if semantic.get("status") not in (
        "passed",
        "failed",
        "generation_or_public_failure",
    ):
        raise ValueError("종결되지 않은 semantic 증거입니다")
    if (
        trial["status"] == "public_pass"
        and semantic["status"] == "generation_or_public_failure"
    ):
        raise ValueError("성공한 public 검사의 semantic 상태가 다릅니다")
    if trial["status"] == "failed" and (
        semantic["status"] != "generation_or_public_failure"
        or any(semantic.get(key, 0) != 0 for key in POINTS)
    ):
        raise ValueError("실패한 생성의 semantic 점수는 0이어야 합니다")
    for key, maximum in zip(POINTS, (40, 25, 15), strict=True):
        if _number(semantic.get(key, 0)) > maximum:
            raise ValueError("semantic 점수 범위를 벗어났습니다")
    counts = semantic.get("action_quality", {}).get("expected_counts", {})
    if not set(counts) <= set(ACTIONS):
        raise ValueError("알 수 없는 action 관찰입니다")
    for value in counts.values():
        if _number(value) != int(value):
            raise ValueError("action 관찰 수는 정수여야 합니다")
    row.update(semantic=semantic, observation="complete")
    return row


def paired_bootstrap(groups: dict[str, list[float]], *, draws: int = 20000) -> dict:
    """같은 전략 index를 모든 조합에 함께 재표집한다. 반복 생성물은 재표집하지 않는다."""
    if draws < 100:
        raise ValueError("bootstrap은 최소 100회입니다")
    size = len(next(iter(groups.values())))
    if not size or any(len(v) != size for v in groups.values()):
        raise ValueError("동일 전략 분모가 필요합니다")
    leader = sorted(groups, key=lambda key: (-statistics.mean(groups[key]), key))[0]
    # 비밀 생성이 아니라 재현 가능한 통계 재표집이다.
    rng = random.Random(SEED)  # noqa: S311
    samples = {key: [] for key in groups}
    for _ in range(draws):
        indices = [rng.randrange(size) for _ in range(size)]
        for key, values in groups.items():
            samples[key].append(sum(values[i] for i in indices) / size)
    comparisons = max(1, len(groups) - 1)
    tail = 0.05 / (2 * comparisons)
    return {
        "unit": "strategy",
        "strategies": size,
        "draws": draws,
        "seed": SEED,
        "descriptive_only": True,
        "selection_caveat": "선택 후 탐색 대조이며 Bonferroni도 승자 선택 편향을 제거하지 않는다. 확정 우월성 검정이 아니다.",
        "strategy_mean_ci95": {
            key: [quantile(values, 0.025), quantile(values, 0.975)]
            for key, values in samples.items()
        },
        "rank_leader_reference": leader,
        "paired_differences": [
            {
                "reference": leader,
                "other": key,
                "mean_difference": statistics.mean(groups[leader]) - statistics.mean(groups[key]),
                "ci95": [quantile(diff, 0.025), quantile(diff, 0.975)],
                "bonferroni_family95_ci": [
                    quantile(diff, tail),
                    quantile(diff, 1 - tail),
                ],
            }
            for key in sorted(groups)
            if key != leader
            for diff in [[a - b for a, b in zip(samples[leader], samples[key], strict=True)]]
        ],
        "family_comparisons": len(groups) - 1,
    }


def build_report(root: Path, *, draws: int = 20000) -> dict:
    root = root.resolve()
    manifest_path = root / "manifest.json"
    manifest_hash = file_hash(manifest_path)
    manifest = json.loads(manifest_path.read_text())
    cases, arms, languages, repetitions = (
        manifest[key] for key in ("cases", "arms", "languages", "repetitions")
    )
    case_ids = [case["id"] for case in cases]
    if (
        not cases
        or len(set(case_ids)) != len(cases)
        or len(set(arms)) != len(arms)
        or len(set(languages)) != len(languages)
        or type(repetitions) is not int
        or repetitions < 1
    ):
        raise ValueError("manifest 분모가 유효하지 않습니다")
    if not set(arms) <= {"A", "B", "C"} or not set(languages) <= {
        "pine",
        "python",
        "typescript",
    }:
        raise ValueError("알 수 없는 방식/언어입니다")
    expected = len(cases) * len(arms) * len(languages) * repetitions
    if manifest["total_jobs"] != expected:
        raise ValueError("manifest 전체 분모가 일치하지 않습니다")
    implementation_paths = [
        Path(__file__),
        ROOT / "tools/research/sol_semantic_eval.py",
    ]
    if "C" in arms:
        implementation_paths += [
            ROOT / "apps/api/src/strategy/code_runtime" / name
            for name in ("spec.py", "compiler.py")
        ]
    implementation_hashes = {
        str(path.relative_to(ROOT)): file_hash(path) for path in implementation_paths
    }
    frozen_hashes = manifest.get("environment", {}).get("source_hashes", {})
    for name, checksum in implementation_hashes.items():
        if (
            name != "tools/research/sol_score_report.py"
            and frozen_hashes
            and frozen_hashes.get(name) != checksum
        ):
            raise ValueError(f"동결 채점/컴파일 구현 hash가 다릅니다: {name}")
    evidence: dict[str, str] = {}
    rows = [
        _trial(root, manifest, manifest_hash, case, arm, language, repetition, evidence)
        for case, arm, language, repetition in itertools.product(
            cases, arms, languages, range(repetitions)
        )
    ]
    # 기존 점수 함수를 재사용하며 누락 행도 반드시 넣는다.
    base = paired_summary(rows)
    quality_rows = [
        {
            **row,
            "semantic": row["semantic"],
            "generation_output_tokens": 16384,
            "generation_seconds": 180,
        }
        for row in rows
    ]
    quality = paired_summary(quality_rows)
    cells = []
    for arm, language in itertools.product(arms, languages):
        combo = f"{arm}/{language}"
        group = [row for row in rows if row["arm"] == arm and row["language"] == language]
        observed = [row for row in group if "generation_seconds" in row]
        counts = Counter(dict.fromkeys(ACTIONS, 0))
        for row in group:
            counts.update(
                row["semantic"].get("action_quality", {}).get("expected_counts", {})
            )
        times = [
            _number(row["observed_generation_seconds"])
            for row in observed
            if row["observed_generation_seconds"] is not None
        ]
        cells.append(
            {
                "combination": combo,
                "expected_artifacts": len(group),
                "observations": dict(Counter(row["observation"] for row in group)),
                "score100": base["cell_means"][combo],
                "quality90": quality["cell_means"][combo],
                "semantic_passes": sum(row["semantic"].get("status") == "passed" for row in group),
                "semantic_pass_rate": sum(
                    row["semantic"].get("status") == "passed" for row in group
                )
                / len(group),
                "action_observations": dict(counts),
                "initial_public_passes": sum(
                    row.get("initial_public_pass", False) for row in group
                ),
                "repair_calls": sum(row.get("repair_calls", 0) for row in group),
                "initial_output_tokens": sum(
                    row.get("initial_output_tokens", 0) for row in group
                ),
                "repair_output_tokens": sum(
                    row.get("repair_output_tokens", 0) for row in group
                ),
                "initial_seconds_p50": quantile(
                    [
                        row["initial_seconds"]
                        for row in observed
                        if row["initial_seconds"] is not None
                    ],
                    0.5,
                ),
                "initial_seconds_p95": quantile(
                    [
                        row["initial_seconds"]
                        for row in observed
                        if row["initial_seconds"] is not None
                    ],
                    0.95,
                ),
                "repair_seconds_p50": quantile(
                    [
                        row["repair_seconds"]
                        for row in observed
                        if row["repair_calls"] and row["repair_seconds"] is not None
                    ],
                    0.5,
                ),
                "repair_seconds_p95": quantile(
                    [
                        row["repair_seconds"]
                        for row in observed
                        if row["repair_calls"] and row["repair_seconds"] is not None
                    ],
                    0.95,
                ),
                "generation_output_tokens": sum(
                    row.get("generation_output_tokens", 0) for row in observed
                ),
                "unknown_output_usage_calls": sum(
                    row.get("unknown_output_usage_calls", 0) for row in observed
                ),
                "generation_seconds_p50": quantile(times, 0.5),
                "generation_seconds_p95": quantile(times, 0.95),
                "generation_metric_observations": len(observed),
                "unknown_duration_calls": sum(
                    row["unknown_duration_calls"] for row in observed
                ),
                "generation_duration_observations": len(times),
                "usd": None,
            }
        )
    complete = all(row["observation"] == "complete" for row in rows)
    full = (
        manifest["stage"] == "evaluation"
        and set(case_ids) == {f"{i:02}" for i in range(1, 31)}
        and set(arms) == {"A", "B", "C"}
        and set(languages) == {"pine", "python", "typescript"}
        and repetitions == 5
    )
    if file_hash(manifest_path) != manifest_hash or any(
        file_hash(root / name) != checksum for name, checksum in evidence.items()
    ):
        raise ValueError("보고서 작성 중 입력 증거가 변경됐습니다")
    return {
        "schema_version": 1,
        **selection_decision(cells),
        "stage": manifest["stage"],
        "manifest_sha256": manifest_hash,
        "input_proof_sha256": digest(
            {
                "manifest_sha256": manifest_hash,
                "files": evidence,
                "implementations": implementation_hashes,
            }
        ),
        "implementation_hashes": implementation_hashes,
        "input_files": evidence,
        "expected_artifacts": expected,
        "observations": dict(Counter(row["observation"] for row in rows)),
        "complete": complete,
        "final_selection_allowed": complete and full,
        "ranking_is_provisional": not (complete and full),
        "usd": "unknown",
        "token_usage_note": "토큰 합계는 CLI가 보고한 관측값이다. usage 미보고 호출은 unknown_output_usage_calls로 구분하며 해당 artifact의 토큰 효율 성분은 0점이다. 관측 latency 성분은 별도 유지한다.",
        "observation_note": "4class 관찰수는 평가 실행들의 합이며 독립 전략 표본 수가 아니다. 누락 시간과 interrupted의 선언 timeout은 latency 분위수에서 제외하고 unknown_duration_calls·관측 수를 병기한다. 운영 적합성은 N/A이며 별도 검증이다.",
        "scoring": "sol_semantic_eval.paired_summary: 40+25+15+10+10; quality90 excludes generation efficiency",
        "score100_ranking": sorted(
            cells, key=lambda cell: (-cell["score100"], cell["combination"])
        ),
        "quality90_ranking": sorted(
            cells, key=lambda cell: (-cell["quality90"], cell["combination"])
        ),
        "artifact_scores": [
            {
                **{
                    key: row[key]
                    for key in (
                        "case_id",
                        "arm",
                        "language",
                        "repetition",
                        "observation",
                    )
                },
                "public_status": row.get("public_status", row["status"]),
                "semantic_status": row["semantic"].get("status", "not_evaluated"),
                "source_hash": row.get("source_hash"),
                "score100": paired_summary([row])["cell_means"][f"{row['arm']}/{row['language']}"],
                "quality90": paired_summary([quality_row])["cell_means"][
                    f"{row['arm']}/{row['language']}"
                ],
            }
            for row, quality_row in zip(rows, quality_rows, strict=True)
        ],
        "strategy_means100": base["strategy_means"],
        "strategy_means90": quality["strategy_means"],
        "bootstrap100": paired_bootstrap(
            {
                key: [values[case] for case in case_ids]
                for key, values in base["strategy_means"].items()
            },
            draws=draws,
        ),
        "bootstrap90": paired_bootstrap(
            {
                key: [values[case] for case in case_ids]
                for key, values in quality["strategy_means"].items()
            },
            draws=draws,
        ),
    }


def export_selection(root: Path, report_path: Path, combination: str) -> tuple[dict, list[dict]]:
    report = json.loads(report_path.read_text())
    if not report.get("final_selection_allowed"):
        raise ValueError("pilot/불완료 보고서는 winner·경제 선정을 생성할 수 없습니다")
    fresh = build_report(root, draws=report["bootstrap100"]["draws"])
    if fresh != report:
        raise ValueError("품질 보고서와 입력 증거 hash가 다릅니다")
    if combination != fresh["selected_candidate"]:
        raise ValueError("사전 선정 정책의 후보와 선택 조합이 다릅니다")
    arm, language = combination.split("/")
    passes, selected_hashes, artifacts = {}, {}, []
    for case_id in sorted(fresh["strategy_means90"][combination]):
        folder = root / "trials" / arm / language / case_id
        passed = [
            rep
            for rep in range(5)
            if json.loads((folder / str(rep) / "semantic.json").read_text())["status"] == "passed"
        ]
        repetition = min(passed) if passed else None
        source = (
            folder / str(repetition) / "source.txt" if repetition is not None else None
        )
        source_hash = file_hash(source) if source else None
        passes[case_id], selected_hashes[case_id] = passed, source_hash
        artifacts.append(
            {
                "case_id": case_id,
                "language": language,
                "arm": arm,
                "source_path": str(source.resolve()) if source else None,
                "source_hash": source_hash,
                "repetition": repetition,
            }
        )
    selection = {
        "policy": "quality_winner_then_first_semantic_pass",
        "quality_stage": "full_eval",
        "decided_before_economics": True,
        "arm": arm,
        "language": language,
        "decision_authority": SELECTION_POLICY,
        "candidate_selection": {
            key: fresh[key] for key in ("policy", "selected_candidate", "tie_reason")
        },
        "quality_evidence": {
            "path": report_path.name,
            "sha256": file_hash(report_path),
        },
        "manifest_sha256": fresh["manifest_sha256"],
        "input_proof_sha256": fresh["input_proof_sha256"],
        "semantic_pass_repetitions": passes,
        "selected_source_hashes": selected_hashes,
    }
    return selection, artifacts


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--quality-selection", help="사전 선정 정책의 후보 arm/language 확인"
    )
    parser.add_argument("--bootstrap-draws", type=int, default=20000)
    args = parser.parse_args()
    destination = args.output.resolve()
    if not destination.is_relative_to(ROOT / "runs"):
        parser.error("보고서 출력은 현재 checkout의 runs/ 아래에만 허용합니다")
    try:
        report = build_report(args.run_dir, draws=args.bootstrap_draws)
        if args.quality_selection and not report["final_selection_allowed"]:
            raise ValueError("pilot/불완료 보고서는 winner·경제 선정을 생성할 수 없습니다")
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(
            json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
        )
        if args.quality_selection:
            selection, artifacts = export_selection(
                args.run_dir.resolve(), destination, args.quality_selection
            )
            for suffix, value in (("selection", selection), ("artifacts", artifacts)):
                destination.with_suffix(f".{suffix}.json").write_text(
                    json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
                )
    except (ValueError, OSError, KeyError) as exc:
        parser.error(str(exc))
    print(
        json.dumps(
            {
                "report": str(destination),
                "complete": report["complete"],
                "usd": "unknown",
            }
        )
    )


if __name__ == "__main__":
    main()
