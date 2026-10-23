"""생성기에 공개하지 않은 수식·경로로 의미와 재현성을 채점한다. 수익성 점수는 없다."""

from __future__ import annotations

import hashlib
from collections import Counter, defaultdict
from dataclasses import replace
from decimal import Decimal
from typing import Any

import numpy as np
import pandas as pd

from src.backtest.engine.types import BacktestConfig
from src.strategy.code_runtime.backtest import run_code_backtest
from src.strategy.code_runtime.models import validate_code_intent
from src.strategy.python_runtime.serialization import (
    bars_payload,
    digest,
    result_payload,
)
from tools.research.strategy_oracle import (
    expected_action,
    expected_risk_plan,
    unsupported_reason,
)


def hidden_frame() -> pd.DataFrame:
    """상승·하락·횡보·변동성 전환을 섞은 결정론적 완료봉. 공개 smoke와 다르다."""
    t = np.arange(1200)
    trend = np.piecewise(
        t.astype(float),
        [t < 300, (t >= 300) & (t < 650), t >= 650],
        [
            lambda x: x * 0.035,
            lambda x: 10.5 - (x - 300) * 0.055,
            lambda x: -8.75 + (x - 650) * 0.02,
        ],
    )
    close = 180 + trend + 6 * np.sin(t / 17.3) + 2 * np.sin(t / 4.7)
    close += np.where((t // 97) % 2, 1.3, -1.3)
    open_ = np.concatenate(([close[0]], close[:-1]))
    spread = 0.2 + (t % 31) / 35
    frame = pd.DataFrame(
        {
            "open": open_,
            "high": np.maximum(open_, close) + spread,
            "low": np.minimum(open_, close) - spread,
            "close": close,
            "volume": np.where(t % 79 == 0, 0, 40 + (t * 13) % 113),
        },
        index=pd.date_range("2025-12-20", periods=len(t), freq="1h", tz="UTC"),
    )
    # 지표 NA/0 분모 경계를 실제 평가 구간에도 넣는다.
    frame.loc[frame.index[:230], ["open", "high", "low", "close"]] = 180.0
    frame.loc[frame.index[900:941], ["open", "high", "low", "close"]] = close[899]
    frame.loc[frame.index[900:941], "volume"] = 0
    return frame


class OracleTransport:
    """생성 코드·컴파일러를 호출하지 않고 독립 신호만 공통 broker에 전달한다."""

    def __init__(self, case_id: str):
        self.case_id = case_id
        self.history: list[dict[str, Any]] = []
        self.state: dict[str, Any] = {}

    def exchange(self, message: dict[str, Any]) -> dict[str, Any]:
        if message["type"] == "init":
            return {"ready": 1}
        self.history.append(message["bar"])
        return {
            "intent": {
                "action": expected_action(
                    self.case_id,
                    self.history,
                    message["position"],
                    self.state,
                )
            }
        }

    def close(self) -> None:
        pass


def normalized_action(action: str, position: dict[str, Any]) -> str:
    direction = position["direction"]
    if action == direction or (action == "close" and direction == "flat"):
        return "hold"
    return action


def action_quality(case_id: str, trace: list[dict[str, Any]]) -> dict[str, Any]:
    history, state = [], {}
    counts: Counter[str] = Counter()
    correct: Counter[str] = Counter()
    mismatches = []
    for event in trace:
        if event["type"] != "intent":
            continue
        # 호출자가 저장한 평가 봉을 해당 시점의 실제 포지션과 결합한다.
        history.append(event["input_bar"])
        wanted = expected_action(case_id, history, event["position"], state)
        wanted = normalized_action(wanted, event["position"])
        actual = normalized_action(event["action"], event["position"])
        if event["disposition"] == "warmup":
            continue
        counts[wanted] += 1
        correct[wanted] += actual == wanted
        if actual != wanted and len(mismatches) < 20:
            mismatches.append(
                {
                    "bar_index": event["bar_index"],
                    "expected": wanted,
                    "actual": actual,
                    "position": event["position"],
                }
            )
    return quality_counts(counts, correct, mismatches)


def quality_counts(counts, correct, mismatches) -> dict[str, Any]:
    recall = {
        action: correct[action] / counts[action] if counts[action] else 0
        for action in ("hold", "long", "short", "close")
    }
    return {
        "macro_accuracy": sum(recall.values()) / 4,
        "expected_counts": dict(counts),
        "correct_counts": dict(correct),
        "all_actions_match": counts == correct,
        "missing_opportunities": [action for action in recall if not counts[action]],
        "mismatches": mismatches,
    }


def probe_transport(language: str, frame: pd.DataFrame):
    if language == "pine":
        from src.strategy.code_runtime.pine import PineSignalTransport

        return PineSignalTransport(frame)
    from src.strategy.code_runtime.sandbox import create_transport

    return create_transport(language)


def decision_probe(
    source: str, language: str, case_id: str, frame: pd.DataFrame
) -> dict[str, Any]:
    """확정 외부 포지션을 통제해 진입과 무효화의 관찰 기회를 만든다. 가상 체결은 없다."""
    transport = probe_transport(language, frame)
    history, state, trace = [], {}, []
    try:
        if transport.exchange(
            {"type": "init", "protocol": 1, "source": source, "params": {}}
        ) != {"ready": 1}:
            raise ValueError("의사결정 probe 초기화 실패")
        for index, bar in enumerate(bars_payload(frame)):
            bar["index"] = index
            history.append(bar)
            flat = {"direction": "flat", "size": "0", "average_price": None}
            wanted_flat = expected_action(case_id, history, flat, state)
            position = (
                flat
                if wanted_flat in ("long", "short")
                else {
                    "direction": "long" if index % 2 else "short",
                    "size": "10",
                    "average_price": bar["close"],
                }
            )
            response = transport.exchange(
                {"type": "bar", "bar": bar, "position": position}
            )
            if set(response) != {"intent"}:
                raise ValueError("의사결정 probe 응답은 intent만 허용")
            action = validate_code_intent(response["intent"])["action"]
            trace.append(
                {
                    "type": "intent",
                    "input_bar": bar,
                    "position": position,
                    "action": action,
                    "bar_index": index,
                    "disposition": "warmup" if index < 200 else "probe",
                }
            )
    finally:
        transport.close()
    return action_quality(case_id, trace)


def audit_risk(trace: list[dict[str, Any]], frame: pd.DataFrame) -> dict[str, Any]:
    """초기 R 손계산·수량 보존·반익절 1회·R 고정을 공통 구현 밖에서 재검산한다."""
    failures, plans = [], {}
    remaining: dict[int, Decimal] = {}
    partials: Counter[int] = Counter()
    for event in trace:
        if event["type"] == "fill":
            generation = event["generation"]
            quantity = Decimal(event["quantity"])
            if event["kind"] == "entry":
                index = frame.index.get_loc(pd.Timestamp(event["timestamp"]))
                previous = frame.iloc[index - 2 : index].to_dict("records")
                expected = expected_risk_plan(
                    Decimal(event["price"]), previous, event["direction"]
                )
                plan = event["plan"]
                pairs = {
                    "risk": "risk",
                    "stop_loss": "stop",
                    "tp_price": "partial",
                    "trailing_activation": "activation",
                    "trailing_distance": "distance",
                }
                if any(
                    Decimal(plan[key]) != expected[value]
                    for key, value in pairs.items()
                ):
                    failures.append(f"generation {generation}: 초기 R 수식 불일치")
                plans[generation] = plan
                remaining[generation] = quantity
            else:
                if quantity <= 0 or quantity > remaining.get(generation, Decimal(0)):
                    failures.append(f"generation {generation}: 초과/비양수 청산")
                remaining[generation] = remaining.get(generation, Decimal(0)) - quantity
                if event["kind"] == "partial_tp":
                    partials[generation] += 1
                    if (
                        partials[generation] > 1
                        or quantity != Decimal(plans[generation]["initial_qty"]) / 2
                    ):
                        failures.append(f"generation {generation}: 반익절 수량/횟수")
                elif remaining[generation] != 0:
                    failures.append(f"generation {generation}: 최종 잔량 미청산")
        state = event.get("risk_state")
        if state:
            plan = state["plan"]
            if plan != plans.get(plan["generation"]):
                failures.append(f"generation {plan['generation']}: 초기 계획 재설정")
    return {"passed": not failures, "entries": len(plans), "failures": failures[:20]}


def evaluate(source: str, language: str, case_id: str) -> dict[str, Any]:
    source_hash = hashlib.sha256(source.encode()).hexdigest()
    reason = unsupported_reason(case_id)
    if reason is not None:
        return {
            "source_hash": source_hash,
            "status": "not_evaluable",
            "reason": reason,
            "reference_scope": "independent_signals_shared_broker",
        }
    frame = hidden_frame()
    cfg = replace(BacktestConfig(), freq="1h", include_funding=False)
    input_bars = bars_payload(frame)

    def run(data=frame, factory=None):
        trace: list[dict[str, Any]] = []
        result = run_code_backtest(
            source,
            language,
            data,
            cfg,
            warmup_bars=200,
            transport_factory=factory,
            trace=trace,
        )
        return result_payload(result), trace

    try:
        result, trace = run()
        replay, replay_trace = run()
        prefix_result, prefix_trace = run(frame.iloc[:-37])
        del prefix_result
        reference, reference_trace = run(factory=lambda: OracleTransport(case_id))
        actual_intents = [event for event in trace if event["type"] == "intent"]
        for event in actual_intents:
            event["input_bar"] = input_bars[event["bar_index"]]
        broker_quality = action_quality(case_id, trace)
        for event in actual_intents:
            del event["input_bar"]
        mirrored = frame.copy()
        for column, original in (
            ("open", "open"),
            ("high", "low"),
            ("low", "high"),
            ("close", "close"),
        ):
            mirrored[column] = 360 - frame[original]
        probes = [
            decision_probe(source, language, case_id, data)
            for data in (frame, mirrored)
        ]
        counts, correct, mismatches = Counter(), Counter(), []
        for part in [broker_quality, *probes]:
            counts.update(part["expected_counts"])
            correct.update(part["correct_counts"])
            mismatches.extend(part["mismatches"])
        quality = quality_counts(counts, correct, mismatches[:20])
        covered = not quality["missing_opportunities"]
        reproducible = result == replay and trace == replay_trace
        prefix_stable = [
            event
            for event in trace
            if pd.Timestamp(event["timestamp"]) <= frame.index[-38]
        ] == prefix_trace
        fills = [event for event in trace if event["type"] == "fill"]
        reference_fills = [
            event for event in reference_trace if event["type"] == "fill"
        ]
        risk = audit_risk(trace, frame)
        ledger_match = result == reference and fills == reference_fills
        safety_passed = reproducible and prefix_stable and risk["passed"]
        return {
            "source_hash": source_hash,
            "status": "passed"
            if safety_passed
            and ledger_match
            and quality["all_actions_match"]
            and covered
            else "failed",
            "action_quality": quality,
            "opportunity_coverage": "complete" if covered else "incomplete_not_passed",
            "reference_ledger_match": ledger_match,
            "reference_entries": sum(
                event["kind"] == "entry" for event in reference_fills
            ),
            "reproducible": reproducible,
            "prefix_stable": prefix_stable,
            "risk_audit": risk,
            "contract_points": 40 * quality["macro_accuracy"] if safety_passed else 0,
            "ledger_points": 25 if safety_passed and ledger_match else 0,
            "reproducibility_points": 15 if reproducible and prefix_stable else 0,
            "data_hash": digest(input_bars),
            "result_hash": digest(result),
            "reference_result_hash": digest(reference),
            "trace_hash": digest(trace),
            "reference_scope": "independent_signals_shared_broker",
        }
    except Exception as exc:
        return {
            "source_hash": source_hash,
            "status": "failed",
            "error_type": type(exc).__name__,
            "error": str(exc)[:1500],
            "contract_points": 0,
            "ledger_points": 0,
            "reproducibility_points": 0,
            "reference_scope": "independent_signals_shared_broker",
        }


def paired_summary(trials: list[dict[str, Any]]) -> dict[str, Any]:
    """전략별 평균을 먼저 계산한다. 반복 생성물을 독립 전략처럼 세지 않는다."""
    groups: dict[tuple[str, str, str], list[float]] = defaultdict(list)
    for trial in trials:
        semantic = trial.get("semantic", {})
        semantic_score = sum(
            float(semantic.get(key, 0))
            for key in ("contract_points", "ledger_points", "reproducibility_points")
        )
        # 통합은 실제 native·protocol·공통broker·관찰 trace·외부 resource 경계 각2점.
        passed_public = trial.get("status") == "public_pass"
        integration = 10 if passed_public else 0
        # 구독 CLI의 USD 청구액은 알 수 없다. 생성 예산 효율만 동일 식으로 채점한다.
        unknown_usage = trial.get(
            "unknown_output_usage_calls",
            sum(
                "output_tokens" not in row["generation"].get("usage", {})
                for row in trial.get("attempts", [])
            ),
        )
        # 미보고 소비량을 측정 0으로 보상하지 않는다. 관측된 latency 성분은 별도 유지한다.
        efficiency = (
            0
            if unknown_usage
            else 5 * max(0, 1 - trial.get("generation_output_tokens", 16384) / 16384)
        )
        unknown_duration = trial.get(
            "unknown_duration_calls",
            sum(
                "duration_seconds" not in row["generation"]
                or row["generation"].get("status") == "interrupted"
                for row in trial.get("attempts", [])
            ),
        )
        if not unknown_duration:
            efficiency += 5 * max(0, 1 - trial.get("generation_seconds", 180) / 180)
        if not passed_public:
            efficiency = 0
        score = semantic_score + integration + efficiency
        groups[trial["arm"], trial["language"], trial["case_id"]].append(score)
    cells: dict[str, dict[str, float]] = defaultdict(dict)
    for (arm, language, case), scores in groups.items():
        cells[f"{arm}/{language}"][case] = sum(scores) / len(scores)
    return {
        "score_max": 100,
        "strategy_means": dict(cells),
        "cell_means": {
            key: sum(values.values()) / len(values) for key, values in cells.items()
        },
        "unit": "strategy",
        "missing_or_failed_artifact_points": 0,
    }
