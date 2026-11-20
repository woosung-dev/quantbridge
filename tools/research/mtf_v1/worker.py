"""사용자 승인 동일 BTC 문맥을 검증한 뒤 기존 금융 엔진에 새 전송만 주입한다."""

from __future__ import annotations

import argparse
import os
import subprocess
from pathlib import Path

from tools.research.mtf_v1.feeds import CausalFeeds, FeedCursor, csv_rows
from tools.research.mtf_v1.transport import MtfTransport
from tools.research.period_study import controller
from tools.research.period_study.schema import TIMEFRAMES
from tools.research.period_study.state import checked, identity, immutable, lock, now, read, sha


def admit(run: Path, pid: str, timeframe: str) -> tuple[dict, dict, dict]:
    authorization = checked(run.parent, "authorization.json", read(run / "mtf-policy-v1.json")["authorization_sha256"])
    assert pid in read(authorization)["selected"]["G5A_same_symbol_security"]
    policy = read(run / "mtf-policy-v1.json")
    assert policy["run_state"] == "active" and policy["contract"] == "same_btc_causal_raw_v1"
    pause = run / "financial-pause-request.json"
    assert not pause.exists() or read(pause).get("pause_requested") is False
    assert not (run / "runtime-blocks" / f"{pid}.json").exists(), "원본 최종 실패 격리"
    item = next(r for r in read(run / "catalogue.json")["items"] if r["id"] == pid)
    _, _, review = controller.artifact(run, run, item, "python")
    assert review["fresh_mtf_review"] is True and review["runtime_contract"] == policy["contract"]
    link = review["market_context_proof"]
    proof_path = checked(run, link["file"], link["sha256"])
    proof = read(proof_path)
    assert proof["kind"] == "authorized_same_BTC_context_recovery"
    assert proof["publication_id"] == pid and proof["symbol"] == "BTCUSDT"
    assert proof["source_sha256"] == item["source_sha256"]
    assert proof["mapping_review_sha256"] == sha((run / "reviews" / f"{pid}.json").read_bytes())
    status_path = run / "generation" / pid / "status.json"
    assert proof["generation_status_sha256"] == sha(status_path.read_bytes())
    assert proof["generated_sha256"] == read(status_path)["generated_sha256"]
    assert proof["native_signal_verification"] is False
    assert proof["worker_sha256"] == sha(Path(__file__).read_bytes())
    assert proof["original_implementation"] == controller.implementation()
    for entry in proof["evidence"]:
        checked(run, entry["file"], entry["sha256"])
    profile_path = checked(run, proof["profile"]["file"], proof["profile"]["sha256"])
    profile = read(profile_path)
    for relative, expected in profile["files"].items():
        checked(controller.ROOT, relative, expected)
    protocol = read(checked(run, proof["protocol"]["file"], proof["protocol"]["sha256"]))
    assert protocol["status"] == "passed" and protocol["generated_sha256"] == proof["generated_sha256"]
    assert timeframe in proof["plans"] and proof["plans"][timeframe]["status"] == "verified"
    assert timeframe in protocol["real_data_counts"], "해당 chart TF의 격리 증인 필요"
    assert proof["authorization_sha256"] == sha(authorization.read_bytes())
    historical = read(run.parent / "historical-request-budget.json")[pid]["historical_requests_used"]
    requests = list((run.parent).glob(f"*/generation/{pid}/*/request.json"))
    assert historical + len(requests) <= 2
    assert not list((run.parent).glob(f"*/generation/{pid}/*/*/request.json")), "예산 원장 밖 중첩 생성 요청"
    return item, proof, profile


def run_one(run: Path, pid: str, timeframe: str, period: str) -> dict:
    item, proof, profile = admit(run, pid, timeframe)
    policy_path = run / "mtf-policy-v1.json"
    frozen_policy = sha(policy_path.read_bytes())
    preflight = read(run.parent / "runtime-preflight.json")
    os.environ["DOCKER_HOST"] = preflight["docker_host"]
    original_images = controller.runtime()
    assert original_images == preflight["image_ids"], "구 이미지 태그 보존 확인"
    image = profile["image_id"]
    actual = subprocess.check_output(["docker", "image", "inspect", "--format", "{{.Id}}", image], text=True).strip()
    assert actual == image
    original_implementation = controller.implementation()
    extended = dict(original_implementation)
    for path in sorted((controller.ROOT / "tools/research/mtf_v1").glob("*.py")):
        extended[str(path.relative_to(controller.ROOT))] = sha(path.read_bytes())
    for relative in ("infra/python-mtf-runner/main.py", "infra/python-mtf-runner/Dockerfile"):
        extended[relative] = sha((controller.ROOT / relative).read_bytes())
    extended[str(policy_path.relative_to(controller.ROOT))] = frozen_policy
    from src.strategy.code_runtime import backtest

    original_backtest = backtest.run_code_backtest
    original_runtime, original_impl = controller.runtime, controller.implementation
    plan = proof["plans"][timeframe]

    def adapted_backtest(*args, **kwargs):
        assert "transport_factory" not in kwargs
        cursors = {}
        for key, entry in plan["feeds"].items():
            path = checked(run, entry["file"], entry["sha256"])
            cursors[key] = FeedCursor(csv_rows(path), entry["timeframe"], initial_closed_limit=entry["initial_closed_limit"])
        feeds = CausalFeeds(TIMEFRAMES[timeframe][0], cursors)
        return original_backtest(*args, **kwargs, transport_factory=lambda: MtfTransport(image, feeds))

    cells = []
    job = run / "mtf-jobs" / pid / timeframe / period
    with lock(run / "mtf-source-locks" / f"{pid}.lock"):
        controller.runtime = lambda: {**original_images, "python": image}
        controller.implementation = lambda: extended
        backtest.run_code_backtest = adapted_backtest
        try:
            rows = controller.run_group(run, run, item, "python", timeframe, period, policies=("A",))
            cells.extend(rows)
            if rows[0]["status"] == "completed":
                tape = None
                if rows[0]["signal_mode"] == "shared_events":
                    payload = read(checked(run, rows[0]["result_file"], rows[0]["result_sha256"]))
                    tape = payload["signals"]
                cells.extend(controller.run_group(run, run, item, "python", timeframe, period,
                                                 policies=("B",), signal_tape=tape))
        finally:
            backtest.run_code_backtest = original_backtest
            controller.runtime, controller.implementation = original_runtime, original_impl
    assert sha(policy_path.read_bytes()) == frozen_policy
    _, after, _ = admit(run, pid, timeframe)
    assert after == proof and controller.implementation() == original_implementation
    assert controller.runtime() == original_images
    failed = [row for row in cells if row["status"] == "failed" and row.get("execution_attempt") == 2]
    if failed:
        immutable(run / "runtime-blocks" / f"{pid}.json", {"status": "terminal_failure_quarantine", "at": now(),
                  "publication_id": pid, "triggers": failed, "worker_sha256": sha(Path(__file__).read_bytes())})
    receipt = {"status": "completed" if len(cells) == 2 and all(r["status"] == "completed" for r in cells) else "partial_or_failed",
               "at": now(), "publication_id": pid, "timeframe": timeframe, "period": period,
               "cells": cells, "context_proof_hash": identity(proof), "worker_sha256": sha(Path(__file__).read_bytes()),
               "original_implementation": original_implementation, "extended_implementation": extended,
               "policy_sha256": frozen_policy, "native_signal_verification": False, "host_source_executions": 0}
    receipt_path = job / (identity(cells) + ".json")
    if receipt_path.exists():
        previous = read(receipt_path)
        assert {k: v for k, v in previous.items() if k != "at"} == {k: v for k, v in receipt.items() if k != "at"}
        return previous
    immutable(receipt_path, receipt)
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--id", required=True)
    parser.add_argument("--timeframe", choices=tuple(TIMEFRAMES), required=True)
    parser.add_argument("--period", choices=("P1", "P2", "P3", "P4", "P5"), required=True)
    args = parser.parse_args()
    result = run_one(args.run.resolve(), args.id, args.timeframe, args.period)
    print(result["status"], flush=True)


if __name__ == "__main__":
    main()
