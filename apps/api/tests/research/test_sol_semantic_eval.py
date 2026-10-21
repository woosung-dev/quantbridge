"""hold 편향·실패 분모·미래 참조·독립 기준의 실제 거래 비교."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from tools.research import sol_semantic_eval as subject  # noqa: E402


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


def test_unsupported_rule_has_no_success_score():
    result = subject.evaluate("unexecuted", "python", "22")
    assert result["status"] == "not_evaluable"
    assert "contract_points" not in result
