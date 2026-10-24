"""hold 편향·실패 분모·미래 참조·독립 기준의 실제 거래 비교."""

import hashlib
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from tools.research import sol_semantic_eval as subject  # noqa: E402

from src.strategy.code_runtime.models import CodeRuntimeError  # noqa: E402


@pytest.mark.parametrize(
    ("reply", "expected_type"),
    [
        ({"wrong": True}, ValueError),
        ({"intent": {"action": "hold"}, "extra": True}, ValueError),
        ({"intent": {"action": "buy"}}, CodeRuntimeError),
    ],
)
def test_probe_keeps_existing_error_types_and_closes(monkeypatch, reply, expected_type):
    from unittest.mock import Mock

    adapter = Mock()
    adapter.exchange.side_effect = [{"ready": 1}, reply]
    monkeypatch.setattr(subject, "probe_transport", lambda *_: adapter)
    with pytest.raises(expected_type) as raised:
        subject.decision_probe("source", "python", "D01", subject.hidden_frame().head(1))
    assert type(raised.value) is expected_type
    adapter.close.assert_called_once_with()


def test_probe_keeps_init_error_type_and_closes(monkeypatch):
    from unittest.mock import Mock

    adapter = Mock()
    adapter.exchange.return_value = {"ready": 2}
    monkeypatch.setattr(subject, "probe_transport", lambda *_: adapter)
    with pytest.raises(ValueError, match="초기화 실패") as raised:
        subject.decision_probe("source", "python", "D01", subject.hidden_frame().head(1))
    assert type(raised.value) is ValueError
    adapter.close.assert_called_once_with()


def test_same_direction_intent_is_economically_hold():
    assert subject.normalized_action("long", {"direction": "long"}) == "hold"
    assert subject.normalized_action("close", {"direction": "flat"}) == "hold"
    assert subject.normalized_action("close", {"direction": "long"}) == "close"


def test_failed_repetitions_stay_in_strategy_mean():
    trials = [
        {
            "arm": "A",
            "language": "pine",
            "case_id": "01",
            "semantic": {"contract_points": 40, "ledger_points": 25, "reproducibility_points": 15},
        },
        {"arm": "A", "language": "pine", "case_id": "01"},
        {
            "arm": "A",
            "language": "pine",
            "case_id": "02",
            "semantic": {"contract_points": 40, "ledger_points": 25, "reproducibility_points": 15},
        },
    ]
    summary = subject.paired_summary(trials)
    assert summary["strategy_means"]["A/pine"] == {"01": 40, "02": 80}
    assert summary["cell_means"]["A/pine"] == 60


def test_independent_signals_pass_and_always_hold_fails(monkeypatch):
    real_run = subject.run_code_backtest

    def oracle_run(source, language, data, config, **kwargs):
        kwargs["transport_factory"] = kwargs.get("transport_factory") or (
            lambda: subject.OracleTransport("D01")
        )
        return real_run(source, language, data, config, **kwargs)

    monkeypatch.setattr(subject, "run_code_backtest", oracle_run)
    monkeypatch.setattr(
        subject, "probe_transport", lambda language, frame: subject.OracleTransport("D01")
    )
    correct = subject.evaluate("test source", "python", "D01")
    assert correct["status"] == "passed", correct
    assert correct["reference_entries"] > 0
    assert correct["contract_points"] == 40

    class Hold(subject.OracleTransport):
        def exchange(self, message):
            return {"ready": 1} if message["type"] == "init" else {"intent": {"action": "hold"}}

    def wrong_run(source, language, data, config, **kwargs):
        kwargs["transport_factory"] = kwargs.get("transport_factory") or (lambda: Hold("D01"))
        return real_run(source, language, data, config, **kwargs)

    monkeypatch.setattr(subject, "run_code_backtest", wrong_run)
    monkeypatch.setattr(subject, "probe_transport", lambda language, frame: Hold("D01"))
    wrong = subject.evaluate("test source", "python", "D01")
    assert wrong["status"] == "failed"
    assert not wrong["reference_ledger_match"]
    assert wrong["contract_points"] < 20


def test_missing_long_behavior_cannot_pass_sparse_htf_fixture(monkeypatch):
    real_run = subject.run_code_backtest

    class NoLong(subject.OracleTransport):
        def exchange(self, message):
            reply = super().exchange(message)
            if reply.get("intent", {}).get("action") == "long":
                return {"intent": {"action": "hold"}}
            return reply

    def native_run(source, language, data, config, **kwargs):
        kwargs["transport_factory"] = kwargs.get("transport_factory") or (lambda: NoLong("30"))
        return real_run(source, language, data, config, **kwargs)

    monkeypatch.setattr(subject, "run_code_backtest", native_run)
    monkeypatch.setattr(subject, "probe_transport", lambda language, frame: NoLong("30"))
    result = subject.evaluate("test source", "python", "30")
    assert result["status"] == "failed", result
    quality = result["action_quality"]
    assert quality["expected_counts"]["long"] > 0
    assert quality["correct_counts"]["long"] == 0


def test_unsupported_rule_has_no_success_score(monkeypatch):
    def forbidden(*_args, **_kwargs):
        pytest.fail("미지원 기준은 native 실행을 시도하지 않아야 합니다")

    monkeypatch.setattr(subject, "run_code_backtest", forbidden)
    result = subject.evaluate("unexecuted", "python", "unknown")
    assert result["status"] == "not_evaluable"
    assert "contract_points" not in result
    assert result["source_hash"] == hashlib.sha256(b"unexecuted").hexdigest()


def test_unreported_usage_gets_no_token_efficiency_but_preserves_observed_latency():
    known = {
        "arm": "B",
        "language": "python",
        "case_id": "01",
        "status": "public_pass",
        "generation_output_tokens": 0,
        "generation_seconds": 0,
        "semantic": {"contract_points": 40, "ledger_points": 25, "reproducibility_points": 15},
        "attempts": [{"generation": {"usage": {"output_tokens": 0}, "duration_seconds": 0}}],
    }
    unknown = {**known, "attempts": [{"generation": {"usage": {}, "duration_seconds": 0}}]}
    assert subject.paired_summary([known])["cell_means"]["B/python"] == 100
    assert subject.paired_summary([unknown])["cell_means"]["B/python"] == 95
