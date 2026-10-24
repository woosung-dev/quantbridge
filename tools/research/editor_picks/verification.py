"""원시 native 근거·prefix·반복 실행·경제 원장을 확인한 것만 수출한다."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from tools.research.editor_picks.common import (
    ARMS,
    TIMEFRAMES,
    checked_file,
    identity,
    now,
    read,
    sha,
    write,
)
from tools.research.editor_picks.execution import artifact, implementation, require_runtime


def receipts(root: Path, frozen: dict) -> dict:
    rows = {}
    assigned = {identity(job) for job in frozen["jobs"]}
    for path in sorted((root / "results").glob("*/receipt.json")):
        value = read(path)
        request = read(path.parent / "request.json")
        if request["plan"] != identity(frozen):
            continue
        if value["job_hash"] != identity(request):
            raise ValueError("작업 완료 기록이 다른 요청을 가리킵니다")
        if value.get("job") != request.get("job") or identity(value["job"]) not in assigned:
            raise ValueError("완료 기록이 배정한 셀과 다릅니다")
        required = {"request.json"}
        if value["status"] == "completed":
            required |= {"result.json.gz", "signals.json.gz"}
            selection = frozen["artifacts"][value["job"]["id"]][value["job"]["arm"]]
            if (
                "source_sha256" not in selection
                or request.get("source_sha256") != selection["source_sha256"]
            ):
                raise ValueError("완료 기록의 코드가 동결 생성물과 다릅니다")
        if not required <= value["files"].keys():
            raise ValueError("완료 기록의 필수 원시 근거가 없습니다")
        for name, digest in value["files"].items():
            checked_file(path.parent, name, digest)
        key = identity(value["job"])
        if key in rows:
            raise ValueError("한 계획의 동일 셀이 중복 완료됐습니다")
        rows[key] = {
            **value,
            "evidence_folder": str(path.parent),
            "execution_images": request.get("images"),
        }
    return rows


def frozen_inputs(root: Path, frozen: dict) -> dict:
    checked_file(root, frozen["cohort_file"], frozen["cohort_sha256"])
    checked_file(root, "data/dataset.json", frozen["dataset_sha256"])
    if frozen["implementation"] != implementation():
        raise ValueError("동결 검증 구현이 바뀌었습니다")
    return read(root / frozen["cohort_file"])


def exact_cells(completed: dict, jobs: list[dict], arm: str, images: dict) -> int:
    exact = 0
    for job in jobs:
        if job["arm"] != arm:
            continue
        row = completed.get(identity(job))
        pine = completed.get(identity({**job, "arm": "pine"}))
        if (
            row
            and pine
            and row["status"] == pine["status"] == "completed"
            and row["action_sha256"] == pine["action_sha256"]
            and row["ledger_sha256"] == pine["ledger_sha256"]
            and row["execution_images"] == pine["execution_images"] == images
        ):
            exact += 1
    return exact


def native_export_gate(
    root: Path, identifier: str, proof: dict, arm: str, digest: str, warmup: int
) -> None:
    windows = proof["native_windows"]
    if set(windows) != set(TIMEFRAMES):
        raise ValueError("native 검증의 세 시간봉 근거가 부족합니다")
    for tf, window in windows.items():
        check = window.get("checks", {}).get(arm, {})
        if (
            window.get("status") != "checked_partial_window"
            or check.get("passed") is not True
            or check.get("source_sha256") != digest
            or window.get("warmup_bars") != warmup
            or type(window.get("checked_bars")) is not int
            or window["checked_bars"] <= 0
            or window.get("bars") != warmup + window["checked_bars"]
            or type(check.get("prefix_bars")) is not int
            or not warmup < check["prefix_bars"] < window["bars"]
        ):
            raise ValueError("native 검증을 통과한 현재 생성물 근거가 없습니다")
        checked_file(root, f"native/{identifier}/{tf}.json", window["capture_sha256"])


def session_actions(source, language, frame, params, images):
    from src.strategy.code_runtime.session import (
        CodeExecutionSession,
        create_code_transport,
    )

    def transport():
        instance = create_code_transport(language, frame)
        if instance.image_id != images[language]:
            instance.close()
            raise ValueError("검증 실행 이미지가 다릅니다")
        return instance

    actions = []
    with CodeExecutionSession(
        source, language, params, frame, transport_factory=transport
    ) as session:
        for index, (timestamp, row) in enumerate(frame.iterrows()):
            bar = {
                "index": index,
                "timestamp": timestamp.isoformat(),
                **{key: str(row[key]) for key in ("open", "high", "low", "close", "volume")},
            }
            actions.append(
                session.action(bar, {"direction": "flat", "size": "0", "average_price": None})
            )
    return actions


def native_bindings(item: dict) -> list[dict]:
    """검토 방향·위치는 유지하고 원문 AST에서 확정한 열 좌표만 보강한다."""
    reviewed = item["signal_bindings"]
    adapted = item["adaptation"]["bindings"]
    if len(reviewed) != len(adapted):
        raise ValueError("native 바인딩과 변환 근거의 개수가 다릅니다")
    result = []
    seen = set()
    for binding in reviewed:
        key = tuple(binding[name] for name in ("function", "line", "direction"))
        matches = [
            candidate for candidate in adapted
            if tuple(candidate[name] for name in ("function", "line", "direction")) == key
        ]
        if key in seen or len(matches) != 1:
            raise ValueError("native 바인딩의 원문 위치·방향이 모호하거나 다릅니다")
        candidate = matches[0]
        column = candidate.get("column")
        if (
            type(column) is not int
            or column < 0
            or candidate.get("when", "truthy") != binding.get("when", "truthy")
            or ("column" in binding and (type(binding["column"]) is not int or binding["column"] != column))
        ):
            raise ValueError("native 바인딩의 열 좌표 또는 조건 의미가 다릅니다")
        seen.add(key)
        result.append({**binding, "column": column})
    return result


def native_action_match(expected, first, repeated, prefix, warmup: int) -> bool:
    """준비봉 이후 native를 대조하고 재실행·미래 제거는 전체 이력을 확인한다."""
    if (
        len(expected) <= warmup + 1
        or len(first) != len(expected)
        or len(repeated) != len(first)
        or not warmup < len(prefix) < len(first)
    ):
        raise ValueError("native 준비봉과 검증·prefix 구간이 충분하지 않습니다")
    return (
        first[warmup:] == expected[warmup:]
        and first == repeated
        and first[: len(prefix)] == prefix
    )


def verify(root: Path, identifier: str, plan_path: Path) -> dict:
    from scripts.pine_validation.native_capture import parse_native_capture

    frozen = read(plan_path)
    if frozen["phase"] != "full":
        raise ValueError("파일럿을 전체 기술 검증으로 승격할 수 없습니다")
    cohort = frozen_inputs(root, frozen)
    item = next(row for row in cohort["items"] if row["id"] == identifier)
    images = require_runtime()
    completed = receipts(root, frozen)
    result = {
        "id": identifier,
        "source_sha256": item["source_sha256"],
        "plan_sha256": identity(frozen),
        "images": images,
        "observed_at": now(),
        "arms": {},
        "native_windows": {},
    }
    native_success = dict.fromkeys(ARMS, True)
    for tf in TIMEFRAMES:
        native_path = root / "native" / identifier / f"{tf}.json"
        if not native_path.exists():
            result["native_windows"][tf] = {"status": "missing_native_capture"}
            native_success = dict.fromkeys(ARMS, False)
            continue
        try:
            raw = read(native_path)
            source = checked_file(root, item["source_file"], item["source_sha256"]).read_bytes()
            native = parse_native_capture(
                raw,
                source=source,
                signal_bindings=native_bindings(item),
                expected_indicator_id=identifier,
                expected_symbol="BYBIT:BTCUSDT.P",
                expected_timeframe=tf,
                expected_inputs=item.get("inputs", {}),
            )
            end = (
                native.ohlcv.index[-1]
                + {
                    "1h": pd.Timedelta(hours=1),
                    "4h": pd.Timedelta(hours=4),
                    "1d": pd.Timedelta(days=1),
                }[tf]
            )
            events = native.window_events(
                native.ohlcv.index[0].to_pydatetime(), end.to_pydatetime()
            )
            expected = dict.fromkeys(native.ohlcv.index, "hold")
            for event in events:
                action = event.direction
                if action not in {"long", "short"} or expected[event.bar_time] != "hold":
                    raise ValueError("native 사건의 방향 또는 동봉 충돌이 모호합니다")
                expected[event.bar_time] = action
            warmup = item["warmup_bars"]
            if len(native.ohlcv) <= warmup + 1:
                raise ValueError("native 이력이 동결 준비봉보다 짧습니다")
            if {"long", "short"} - set(list(expected.values())[warmup:]):
                raise ValueError("native 구간의 양방향 사건 근거가 부족합니다")
            checks = {}
            for arm in ARMS:
                try:
                    code, language, digest = artifact(root, item, arm)
                    first = session_actions(
                        code, language, native.ohlcv, item.get("inputs", {}), images
                    )
                    repeated = session_actions(
                        code, language, native.ohlcv, item.get("inputs", {}), images
                    )
                    length = warmup + max(1, (len(first) - warmup) * 2 // 3)
                    prefix = session_actions(
                        code,
                        language,
                        native.ohlcv.iloc[:length],
                        item.get("inputs", {}),
                        images,
                    )
                    passed = native_action_match(
                        list(expected.values()), first, repeated, prefix, warmup
                    )
                    checks[arm] = {
                        "passed": passed,
                        "source_sha256": digest,
                        "actions_sha256": identity(first),
                        "prefix_bars": length,
                    }
                    native_success[arm] &= passed
                except Exception as error:
                    native_success[arm] = False
                    checks[arm] = {"passed": False, "error": str(error)}
            result["native_windows"][tf] = {
                "status": "checked_partial_window",
                "checks": checks,
                "capture_sha256": sha(native_path.read_bytes()),
                "start": str(native.ohlcv.index[0]),
                "end": str(end),
                "bars": len(native.ohlcv),
                "warmup_bars": warmup,
                "checked_start": str(native.ohlcv.index[warmup]),
                "checked_bars": len(native.ohlcv) - warmup,
                "metadata": native.metadata,
            }
        except Exception as error:
            result["native_windows"][tf] = {
                "status": "invalid_native_capture",
                "error": str(error),
            }
            native_success = dict.fromkeys(ARMS, False)
    jobs = [job for job in frozen["jobs"] if job["id"] == identifier]
    for arm in ARMS:
        exact = exact_cells(completed, jobs, arm, images)
        result["arms"][arm] = {
            "status": "passed" if native_success[arm] and exact == 36 else "incomplete",
            "exact_economic_cells": exact,
            "expected_economic_cells": 36,
            "native_prefix_repeat_passed": native_success[arm],
        }
    write(root / "verification" / f"{identifier}.json", result)
    return result


def reconcile(root: Path, plan_path: Path) -> dict:
    """불변 ARM native 증거와 수거한 전체 경제 셀을 결합한다. 전략은 실행하지 않는다."""
    frozen = read(plan_path)
    if frozen["phase"] != "full":
        raise ValueError("전체 계획만 native·경제 증거를 결합합니다")
    cohort = frozen_inputs(root, frozen)
    completed = receipts(root, frozen)
    passed = 0
    for item in cohort["items"]:
        relative = f"native-checks/{item['id']}.json"
        path = root / relative
        if not path.is_file():
            raise ValueError(f"ARM native 판정 증거가 없습니다: {item['id']}")
        raw = read(path)
        if (
            raw.get("id") != item["id"]
            or raw.get("source_sha256") != item["source_sha256"]
            or raw.get("plan_sha256") != identity(frozen)
        ):
            raise ValueError("ARM native 증거의 원문·계획이 다릅니다")
        proof = {**raw, "arms": {}}
        jobs = [job for job in frozen["jobs"] if job["id"] == item["id"]]
        for arm in ARMS:
            selection = frozen["artifacts"][item["id"]][arm]
            native_passed = raw["arms"][arm]["native_prefix_repeat_passed"] is True
            reason = None
            if "source_sha256" not in selection:
                native_passed = False
                reason = selection["unavailable_reason"]
            else:
                _, language, digest = artifact(root, item, arm)
                if selection != {"language": language, "source_sha256": digest}:
                    raise ValueError("ARM 검증 후 동결 생성물이 바뀌었습니다")
                try:
                    native_export_gate(root, item["id"], raw, arm, digest, item["warmup_bars"])
                except ValueError as error:
                    native_passed, reason = False, str(error)
            exact = exact_cells(completed, jobs, arm, raw["images"])
            status = "passed" if native_passed and exact == 36 else "incomplete"
            passed += status == "passed"
            proof["arms"][arm] = {
                "status": status,
                "exact_economic_cells": exact,
                "expected_economic_cells": 36,
                "native_prefix_repeat_passed": native_passed,
                "native_gate_error": reason,
            }
        proof.update(
            native_check_file=relative,
            native_check_sha256=sha(path.read_bytes()),
            economic_reconciled_at=now(),
        )
        write(root / "verification" / f"{item['id']}.json", proof)
    return {"source_count": len(cohort["items"]), "passed_arms": passed}


def export(root: Path, plan_path: Path) -> dict:
    from tools.research.cli import RESEARCH_POLICY
    from tools.research.editor_picks.common import MODELS

    from src.strategy.code_schemas import SaveCodeStrategyRequest

    frozen = read(plan_path)
    if frozen["phase"] != "full":
        raise ValueError("전체 계획만 앱 저장 묶음을 만들 수 있습니다")
    cohort = frozen_inputs(root, frozen)
    completed = receipts(root, frozen)
    requests = []
    for item in cohort["items"]:
        path = root / "verification" / f"{item['id']}.json"
        if not path.exists():
            continue
        proof = read(path)
        if (
            proof["plan_sha256"] != identity(frozen)
            or proof["source_sha256"] != item["source_sha256"]
        ):
            raise ValueError("기술 검증이 현재 원문·계획과 다릅니다")
        for arm in ARMS:
            if proof["arms"][arm]["status"] != "passed":
                continue
            native_proof_path = checked_file(
                root, proof["native_check_file"], proof["native_check_sha256"]
            )
            native_proof = read(native_proof_path)
            if (
                proof["native_check_file"] != f"native-checks/{item['id']}.json"
                or native_proof["native_windows"] != proof["native_windows"]
                or native_proof["images"] != proof["images"]
                or native_proof["plan_sha256"] != identity(frozen)
                or native_proof["source_sha256"] != item["source_sha256"]
            ):
                raise ValueError("불변 ARM native 증거와 저장 판정이 다릅니다")
            source, language, digest = artifact(root, item, arm)
            selection = frozen["artifacts"][item["id"]][arm]
            if selection != {"language": language, "source_sha256": digest}:
                raise ValueError("검증 후 동결 생성물이 바뀌었습니다")
            native_export_gate(root, item["id"], proof, arm, digest, item["warmup_bars"])
            jobs = [job for job in frozen["jobs"] if job["id"] == item["id"]]
            if exact_cells(completed, jobs, arm, proof["images"]) != 36:
                raise ValueError("현재 원시 근거로 경제 36셀의 일치를 확인할 수 없습니다")
            provenance = {
                "origin": "editor_picks_reproduction",
                "experiment": root.name,
                "publication_id": item["id"],
                "url": item["url"],
                "author": item["author"],
                "source_sha256": item["source_sha256"],
                "arm": arm,
                "requested_model": MODELS.get(arm),
                "requested_effort": "high" if arm in MODELS else None,
                "actual_model": None,
                "validation_sha256": sha(path.read_bytes()),
                "plan_sha256": identity(frozen),
                "validated_timeframes": list(TIMEFRAMES),
                "native_scope": "observed_partial_windows",
                "economic_status": "retrospective_not_untouched",
                "promotable": False,
                "license_notices": item["license_notices"],
                "research_assumptions": {
                    **{key: RESEARCH_POLICY[key] for key in (
                        "init_cash", "fees", "maker_fee", "slippage", "fill_timing",
                        "position_size_pct", "leverage", "cost_basis", "funding_policy",
                    )},
                    "warmup_bars": item["warmup_bars"],
                    "risk_policy": frozen["policy"],
                    "execution_timeframe": "1min",
                },
            }
            request = SaveCodeStrategyRequest.model_validate(
                {
                    "name": f"{item['title'][:85]} · {arm} · {item['id']}",
                    "description": "에디터 픽 원문 재현 연구. 과거 성과·부분 native 구간 검증이며 자동매매 승인이 아닙니다.",
                    "symbol": "BTC/USDT:USDT",
                    "timeframe": "1h",
                    "settings": {
                        "leverage": int(RESEARCH_POLICY["leverage"]),
                        "margin_mode": "isolated",
                        "position_size_pct": float(RESEARCH_POLICY["position_size_pct"]),
                        "fill_timing": RESEARCH_POLICY["fill_timing"],
                    },
                    "code": {
                        "schema_version": 1,
                        "execution_policy": "code_v1",
                        "language": language,
                        "source_code": source,
                        "warmup_bars": item["warmup_bars"],
                        "params": item.get("inputs", {}),
                        "provenance": provenance,
                    },
                }
            )
            requests.append(request.model_dump(mode="json"))
    payload = {
        "plan_sha256": identity(frozen),
        "count": len(requests),
        "requests": requests,
    }
    write(root / "registration/requests.json", payload)
    return {"status": "exported", "count": len(requests)}
