#!/usr/bin/env python
"""조건부 진입 체결 귀속 counter 두 스냅샷의 판정을 파일로 만든다."""

from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from prometheus_client.parser import text_string_to_metric_families

COUNTER_NAME = "qb_live_conditional_fill_ownership_total"
KNOWN_LABELS = (
    "agree",
    "engine_only_suppressed",
    "ledger_only_adopted",
    "ledger_only_orphan",
    "ledger_fill_out_of_window",
    "ledger_unreadable_fallback",
    "other",
)
NUMERATOR_LABELS = ("agree",)
DENOMINATOR_LABELS = (
    "agree",
    "engine_only_suppressed",
    "ledger_only_adopted",
)
EXCLUDED_REASONS = {
    "ledger_only_orphan": "pending 이 없어 엔진이 판단할 대상 자체가 없다(무동작)",
    "ledger_fill_out_of_window": "300봉 창 밖이라 엔진의 답이 존재하지 않는다",
    "ledger_unreadable_fallback": "원장을 못 읽어 엔진이 단독 판정했다 — 대조가 없었다",
}
MIN_DENOMINATOR = 30


def _parse_timestamp(value: str) -> datetime:
    """ISO8601 시각을 검증한다. 출력에는 입력 문자열을 그대로 보존한다."""
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError(f"timezone 없는 ISO8601 시각: {value!r}")
    return parsed


def _read_counter(path: Path) -> dict[str, float]:
    """Prometheus 원문에서 대상 counter의 outcome별 값을 추출한다."""
    try:
        text = path.read_text()
    except OSError as exc:
        raise ValueError(f"입력 파일을 읽을 수 없다: {path}: {exc}") from exc

    try:
        families = text_string_to_metric_families(text)
        values: dict[str, float] = {}
        found_counter = False
        for family in families:
            for sample in family.samples:
                if sample.name != COUNTER_NAME:
                    continue
                found_counter = True
                label = sample.labels.get("outcome", "<missing>")
                if label in values:
                    raise ValueError(f"중복 outcome series: {label!r}")
                numeric = float(sample.value)
                if not math.isfinite(numeric):
                    raise ValueError(f"유한하지 않은 counter 값: {label!r}={sample.value!r}")
                values[label] = numeric
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Prometheus 원문 파싱 실패: {exc}") from exc

    if not found_counter:
        raise ValueError(f"counter 계열이 없다: {COUNTER_NAME}")
    return values


def _with_known_zeroes(values: dict[str, float]) -> dict[str, float]:
    """priming 전 누락된 series는 0으로 채운다."""
    return {label: values.get(label, 0.0) for label in (*KNOWN_LABELS, *values)}


def _table(raw_t0: dict[str, float], raw_t1: dict[str, float], delta: dict[str, float]) -> str:
    """stdout용 표. 표시 정밀도는 판단 데이터와 독립적이다."""
    rows = ["outcome                         t0          t1       delta"]
    for label in sorted(delta):
        rows.append(
            f"{label:<30} {raw_t0[label]:>10.4f} {raw_t1[label]:>10.4f} {delta[label]:>10.4f}"
        )
    return "\n".join(rows)


def _verdict(delta: dict[str, float]) -> tuple[str, str, float | None, dict[str, float | None]]:
    """동결된 게이트 순서대로 판정한다."""
    denominator = sum(delta[label] for label in DENOMINATOR_LABELS)
    rates: dict[str, float | None] = {
        "agreement_rate": None,
        "type_a_engine_ahead": None,
        "type_b_ledger_ahead": None,
    }

    if any(value < 0 for value in delta.values()):
        return "held", "counter_reset_detected", denominator, rates

    unknown_labels = set(delta) - set(KNOWN_LABELS)
    if unknown_labels or delta["other"] > 0:
        return "held", "unknown_label_present", denominator, rates

    if denominator < MIN_DENOMINATOR:
        return "undecidable", "sample_below_threshold", denominator, rates

    rates = {
        "agreement_rate": delta["agree"] / denominator,
        "type_a_engine_ahead": delta["engine_only_suppressed"] / denominator,
        "type_b_ledger_ahead": delta["ledger_only_adopted"] / denominator,
    }
    return "measured", "ok", denominator, rates


def build_report(t0_path: Path, t0_at: str, t1_path: Path, t1_at: str) -> dict[str, Any]:
    """두 counter 원문을 계약 JSON으로 변환한다."""
    parsed_t0_at = _parse_timestamp(t0_at)
    parsed_t1_at = _parse_timestamp(t1_at)
    raw_t0 = _with_known_zeroes(_read_counter(t0_path))
    raw_t1 = _with_known_zeroes(_read_counter(t1_path))
    labels = sorted(set(raw_t0) | set(raw_t1))
    raw_t0 = {label: raw_t0.get(label, 0.0) for label in labels}
    raw_t1 = {label: raw_t1.get(label, 0.0) for label in labels}
    delta = {label: raw_t1[label] - raw_t0[label] for label in labels}

    verdict, reason, denominator, rates = _verdict(delta)
    return {
        "window": {
            "t0_at": t0_at,
            "t1_at": t1_at,
            "elapsed_hours": (parsed_t1_at - parsed_t0_at).total_seconds() / 3600,
        },
        "raw": {"t0": raw_t0, "t1": raw_t1},
        "delta": delta,
        "numerator": {"value": delta["agree"], "labels": list(NUMERATOR_LABELS)},
        "denominator": {"value": denominator, "labels": list(DENOMINATOR_LABELS)},
        "excluded": {
            label: {"delta": delta[label], "reason": reason}
            for label, reason in EXCLUDED_REASONS.items()
        },
        "verdict": verdict,
        "verdict_reason": reason,
        "agreement_rate": rates["agreement_rate"],
        "breakdown": {
            "type_a_engine_ahead": rates["type_a_engine_ahead"],
            "type_b_ledger_ahead": rates["type_b_ledger_ahead"],
        },
        "thresholds": {
            "min_denominator": MIN_DENOMINATOR,
            "rationale": "rule of three: 3/30 = 10%",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Conditional-fill ownership counter verdict")
    parser.add_argument("--t0", type=Path, required=True)
    parser.add_argument("--t0-at", required=True)
    parser.add_argument("--t1", type=Path, required=True)
    parser.add_argument("--t1-at", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    try:
        report = build_report(args.t0, args.t0_at, args.t1, args.t1_at)
    except ValueError as exc:
        sys.stderr.write(f"ERROR: {exc}\n")
        return 2

    print(_table(report["raw"]["t0"], report["raw"]["t1"], report["delta"]))
    print(f"verdict: {report['verdict']} ({report['verdict_reason']})")
    args.out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
