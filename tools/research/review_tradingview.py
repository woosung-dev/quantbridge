"""공개 원문의 명시적 신호만 정적으로 검토한다. 전략 코드 자체는 실행하지 않는다."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from collections import Counter
from contextlib import suppress
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "apps/api"))
SIGNALS = {"alertcondition", "plotshape", "plotchar"}
REVIEWER = "codex-static-source-review-v1"


def digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def read(path: Path) -> dict:
    return json.loads(path.read_text())


def write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    temporary.replace(path)


def code_mask(source: str) -> str:
    """문자열·주석의 위치를 공백으로 보존해 코드 참조와 설명 문구를 구분한다."""
    return re.sub(
        r"""//[^\n]*|"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*' """,
        lambda match: re.sub(r"[^\n]", " ", match.group()),
        source,
        flags=re.X,
    )


def feedback_references(source: str) -> tuple[list[str], list[str]]:
    """현재 포지션 세 필드로 재현할 수 없는 거래·계정 상태는 별도로 남긴다."""
    references = sorted(
        set(
            re.findall(
                r"\bstrategy\.(?:position\w*|opentrades|closedtrades|equity|netprofit|openprofit|"
                r"initial_capital|grossprofit|grossloss|wintrades|losstrades|eventrades|"
                r"max_drawdown|max_runup)(?:\.[A-Za-z_]\w*)*\b",
                code_mask(source),
            )
        )
    )
    unavailable = [
        name
        for name in references
        if name not in {"strategy.position_size", "strategy.position_avg_price"}
    ]
    return references, unavailable


def calls(source: str, names: set[str]) -> list[dict]:
    """실제 코드의 호출 범위를 괄호·문자열 상태로 찾고 AST 검사는 자식 프로세스가 한다."""
    mask = code_mask(source)
    pattern = re.compile(r"\b(" + "|".join(re.escape(name) for name in sorted(names)) + r")\s*\(")
    result = []
    for match in pattern.finditer(mask):
        depth, end = 1, match.end()
        while end < len(mask) and depth:
            depth += (mask[end] == "(") - (mask[end] == ")")
            end += 1
        if depth:
            continue
        line_start = source.rfind("\n", 0, match.start()) + 1
        prefix = source[line_start : match.start()]
        result.append(
            {
                "function": match.group(1),
                "line": source.count("\n", 0, match.start()) + 1,
                "column": match.start() - line_start,
                "source": source[match.start() : end],
                "standalone": not prefix.strip(),
                "multiline": "\n" in source[match.start() : end],
            }
        )
    return result


def explicit_direction(text: str) -> str | None:
    label = re.sub(r"[\s_]+", " ", text.strip().lower())
    if re.fullmatch(r"(?:close|exit) (?:long|short)|(?:long|short) (?:close|exit)", label):
        return "long_exit" if "long" in label else "short_exit"
    match = re.fullmatch(
        r"(?:(?:strong|confirmed|new) )?(buy|sell|long|short)(?: (?:entry|signal|alert))?", label
    ) or re.fullmatch(r"(?:enter|go) (long|short)", label)
    if match:
        return "long" if match.group(1) in {"buy", "long"} else "short"
    return None


def argument(call: Any, name: str, index: int) -> Any:
    positional = [arg.value for arg in call.args if arg.name is None]
    values = [arg.value for arg in call.args if arg.name == name]
    if len(values) == 1:
        return values[0]
    return positional[index] if not values and len(positional) > index else None


def raw_event_adaptation(adaptation: dict) -> dict:
    """어댑터가 삽입한 포지션 guard만 제거한다. 원본 조건과 내부 상태는 보존한다."""
    source = adaptation["strategy_source"]
    removed = []
    for binding in adaptation["bindings"]:
        if binding["direction"] not in {"long", "short"}:
            continue
        temp = re.escape(binding["condition_variable"])
        pattern = re.compile(
            rf"(?m)^if {temp} and (strategy\.position_size [<>]= 0|"
            rf"\(strategy\.position_size [<>]= 0 or \([^\r\n]*\)\))"
            rf" and not (qb_adapt_(?:long|short)_submitted_*)\r?$"
        )
        matches = list(pattern.finditer(source))
        if len(matches) != 1:
            raise ValueError("generated_position_guard_anchor_changed")
        match = matches[0]
        replacement = f"if {binding['condition_variable']} and not {match.group(2)}"
        if match.group().endswith("\r"):
            replacement += "\r"
        removed.append({"before": match.group(), "after": replacement})
        source = source[: match.start()] + replacement + source[match.end() :]
    return {
        **adaptation,
        "strategy_source": source,
        "converted_sha256": digest(source.encode()),
        "research_event_adaptation": {"version": 1, "removed_generated_guards": removed},
    }


def prior_review(prior: Path | None, item: dict, source: str, source_hash: str) -> dict | None:
    if prior is None:
        return None
    cohort = read(prior / "cohort.json")
    previous = next((value for value in cohort["items"] if value["id"] == item["id"]), None)
    if previous is None or previous.get("source_sha256") != source_hash:
        return None
    old_source = prior / previous["source_file"]
    if not old_source.is_file() or digest(old_source.read_bytes()) != source_hash:
        return None
    path = prior / "reviews" / f"{item['id']}.json"
    review = read(path) if path.is_file() else previous
    evidence = review.get("source_evidence") or review.get("source_review_evidence", {}).get(
        "lines", []
    )
    lines = source.splitlines()
    if not evidence or any(
        type(entry.get("line")) is not int
        or not 1 <= entry["line"] <= len(lines)
        or lines[entry["line"] - 1].rstrip() != entry.get("text", "").rstrip()
        for entry in evidence
    ):
        return {"status": "pending_review", "basis": "선행 리뷰의 원문 근거 줄이 일치하지 않습니다"}
    if review.get("expression_bindings"):
        return {
            "status": "pending_review",
            "basis": "선행 합성 expression은 원본의 명시적 진입 호출이 아닙니다",
            "prior_expression_bindings": review["expression_bindings"],
            "source_evidence": evidence,
            "prior_review_basis": review.get("basis"),
        }
    bindings = review.get("signal_bindings")
    if not bindings or not review.get("basis"):
        return None
    return {
        "status": "reviewed",
        "signal_bindings": bindings,
        "inputs": review.get("inputs", {}),
        "warmup_bars": review.get("warmup_bars", 1000),
        "basis": review["basis"],
        "source_evidence": evidence,
        "prior_review_sha256": digest(path.read_bytes()) if path.exists() else None,
        "prior_review_file": str(path),
        "prior_reviewer": review.get("reviewed_by"),
    }


def inspect_worker(request: dict) -> dict:
    from pynescript import ast as A

    from scripts.pine_validation.strategy_adapter import StrategyAdapterError, adapt_strategy
    from src.strategy.pine_v2.coverage import analyze_coverage
    from src.strategy.pine_v2.parser_adapter import parse_to_ast

    source = request["source"]
    reviewed, candidates, warnings = [], [], []
    for entry in request["calls"]:
        if not entry["standalone"]:
            continue
        if entry["multiline"] and not request.get("prior"):
            warnings.append({"line": entry["line"], "reason": "multiline_signal_requires_review"})
            continue
        try:
            tree = parse_to_ast(entry["source"] + "\n")
            call = tree.body[0].value
            if not isinstance(call, A.Call):
                continue
        except Exception as error:
            warnings.append(
                {"line": entry["line"], "reason": f"call_ast_failed:{type(error).__name__}"}
            )
            continue
        order_id = None
        if entry["function"].startswith("strategy."):
            identifier = argument(call, "id", 0)
            order_id = identifier.value if isinstance(identifier, A.Constant) else None
        if entry["function"] == "strategy.entry":
            direction_node = argument(call, "direction", 1)
            direction = getattr(direction_node, "attr", None)
            if (
                not isinstance(direction_node, A.Attribute)
                or not isinstance(direction_node.value, A.Name)
                or direction_node.value.id != "strategy"
                or direction not in {"long", "short"}
            ):
                warnings.append({"line": entry["line"], "reason": "dynamic_strategy_direction"})
                continue
            if not isinstance(order_id, str):
                warnings.append({"line": entry["line"], "reason": "dynamic_strategy_entry_id"})
                continue
            if any(
                arg.name not in {None, "id", "direction", "when", "comment"} for arg in call.args
            ):
                request["native_price_exits"] = True
            condition = "원본의 바깥 제어 흐름 및 when 인자를 그대로 보존"
        elif entry["function"] in {"strategy.close", "strategy.close_all"}:
            direction = "close"
            condition = "원본의 바깥 제어 흐름 및 when 인자를 그대로 보존"
            if entry["function"] == "strategy.close" and not isinstance(order_id, str):
                warnings.append({"line": entry["line"], "reason": "dynamic_strategy_close_id"})
                continue
        else:
            title = argument(call, "title", 1)
            direction = (
                explicit_direction(title.value)
                if isinstance(title, A.Constant) and isinstance(title.value, str)
                else None
            )
            condition_node = argument(
                call, "condition" if entry["function"] == "alertcondition" else "series", 0
            )
            condition = A.unparse(condition_node) if condition_node is not None else None
        record = {key: entry[key] for key in ("function", "line", "column")}
        record.update(direction=direction, condition=condition, original_call=entry["source"])
        if entry["function"].startswith("strategy."):
            record["order_id"] = order_id
        candidates.append(record)
        if request.get("prior"):
            selected = [
                binding
                for binding in request["prior"]["signal_bindings"]
                if binding["function"] == entry["function"]
                and binding["line"] == entry["line"]
                and binding.get("column", entry["column"]) == entry["column"]
            ]
            if len(selected) == 1:
                reviewed.append({**record, **selected[0]})
        elif direction is not None and condition is not None:
            reviewed.append(record)
    if request.get("strategy"):
        for entry in reviewed:
            if entry["function"] != "strategy.close":
                continue
            directions = {
                value["direction"]
                for value in reviewed
                if value["function"] == "strategy.entry" and value["order_id"] == entry["order_id"]
            }
            if not directions:
                warnings.append({"line": entry["line"], "reason": "unmatched_strategy_close_id"})
            elif len(directions) == 1:
                entry["direction"] = next(iter(directions)) + "_exit"
    if request.get("prior"):
        valid = len(reviewed) == len(request["prior"]["signal_bindings"])
    else:
        entries = [entry for entry in reviewed if entry["direction"] in {"long", "short"}]
        valid = len(entries) == 2 and {entry["direction"] for entry in entries} == {"long", "short"}
        # 여러 신호군 중 성과를 보고 한 쌍을 고르지 않는다.
        valid = valid and not warnings
        if not request.get("strategy"):
            alert = [entry for entry in reviewed if entry["function"] == "alertcondition"]
            plots = [entry for entry in reviewed if entry["function"] != "alertcondition"]
            if alert and plots:
                valid = False
    response: dict[str, Any] = {
        "status": "reviewed" if valid else "pending_review",
        "signal_bindings": reviewed if valid else [],
        "signal_candidates": candidates,
        "review_warnings": warnings,
    }
    # 전체 원문 파서가 시간 상한에 걸려도 이미 끝낸 신호 위치 검토는 잃지 않는다.
    print(json.dumps(response, ensure_ascii=False), flush=True)
    coverage = analyze_coverage(source)
    response["pine_coverage"] = {
        "status": "supported_static"
        if coverage.is_runnable and not coverage.has_degraded
        else "unsupported",
        "unsupported_functions": coverage.unsupported_functions,
        "unsupported_attributes": coverage.unsupported_attributes,
        "degraded_calls": coverage.degraded_calls,
    }
    print(json.dumps(response, ensure_ascii=False), flush=True)
    if valid and (not coverage.is_runnable or coverage.has_degraded):
        response["pine_execution_reason"] = "original_pine_coverage_unsupported_or_degraded"
    elif valid and not request.get("strategy"):
        try:
            adaptation = adapt_strategy(source, reviewed, fixed_quantity=None)
            response["adaptation"] = raw_event_adaptation(adaptation.to_dict())
        except StrategyAdapterError as error:
            response["pine_execution_reason"] = f"{error.code}:{error}"
    elif valid:
        if request.get("native_price_exits"):
            response["pine_execution_reason"] = (
                "native_order_configuration_requires_reviewed_signal_extraction"
            )
        else:
            response["executable_source"] = source
    return response


def inspect(request: dict) -> dict:
    attempts = []
    partial = None
    for attempt in (1, 2):
        try:
            result = subprocess.run(  # noqa: S603 — 고정 Python·현재 파일만 실행, 원문은 정적 stdin 데이터다.
                [sys.executable, str(Path(__file__).resolve()), "--worker"],
                input=json.dumps(request),
                text=True,
                capture_output=True,
                timeout=15,
                check=True,
            )
            return {
                **json.loads(result.stdout.splitlines()[-1]),
                "static_attempts": [*attempts, {"attempt": attempt, "status": "completed"}],
            }
        except (subprocess.SubprocessError, ValueError) as error:
            attempts.append(
                {"attempt": attempt, "status": type(error).__name__, "detail": str(error)[:600]}
            )
            output = getattr(error, "stdout", None)
            if output:
                with suppress(ValueError, IndexError):
                    partial = json.loads(output.splitlines()[-1])
    if partial is not None:
        return {
            **partial,
            "static_attempts": attempts,
            "pine_execution_reason": "static_parser_timeout_or_failure",
            "pine_coverage": partial.get("pine_coverage", {"status": "not_completed"}),
        }
    return {
        "status": "pending_review",
        "basis": "정적 검사 15초 상한·1회 재시도를 소진했습니다",
        "static_attempts": attempts,
        "pine_coverage": {"status": "not_completed"},
    }


def review_one(run: Path, item: dict, prior: Path | None) -> dict | None:
    receipt_path = run / "source_receipts" / f"{item['id']}.json"
    if not receipt_path.exists():
        return None
    receipt = read(receipt_path)
    if receipt.get("status") != "captured" or not receipt.get("source_sha256"):
        return None
    path = (run / receipt["source_file"]).resolve()
    if (
        not path.is_relative_to(run.resolve())
        or digest(path.read_bytes()) != receipt["source_sha256"]
    ):
        raise ValueError(f"source_receipt_hash_mismatch:{item['id']}")
    raw = path.read_bytes()
    source, source_hash = raw.decode("utf-8"), digest(raw)
    previous = prior_review(prior, item, source, source_hash)
    mask = code_mask(source)
    strategy = bool(re.search(r"(?m)^strategy\s*\(", mask))
    position_refs, unavailable = feedback_references(source)
    native_exits = bool(re.search(r"\bstrategy\.(?:exit|order|cancel|cancel_all)\s*\(", mask))
    request = {
        "source": source,
        "strategy": strategy,
        "native_price_exits": native_exits,
        "calls": calls(
            source,
            {"strategy.entry", "strategy.close", "strategy.close_all"} if strategy else SIGNALS,
        ),
        "prior": previous if previous and previous["status"] == "reviewed" else None,
    }
    if request["prior"]:
        bindings = request["prior"]["signal_bindings"]
        request["calls"] = [
            entry
            for entry in request["calls"]
            if any(
                entry["function"] == binding["function"] and entry["line"] == binding["line"]
                for binding in bindings
            )
        ]
    if unavailable:
        result = {"status": "not_comparable", "reason": "unsupported_broker_feedback"}
    else:
        result = previous if previous and previous["status"] != "reviewed" else inspect(request)
    basis = (
        previous.get("basis")
        if previous
        else (
            "원문 AST의 정적 제목과 조건에서 명시된 매수/매도 한 쌍만 연결했습니다. "
            "컴파일·실행·원본 신호 일치는 별도 검증입니다"
        )
    )
    review = {
        "id": item["id"],
        "source_sha256": source_hash,
        "source_file": str(path.relative_to(run.resolve())),
        "reviewer": REVIEWER,
        "basis": basis,
        "inputs": previous.get("inputs", {}) if previous else {},
        "warmup_bars": previous.get("warmup_bars", 1000) if previous else 1000,
        "warmup_status": "requires_prefix_validation",
        "signal_mode": None
        if unavailable
        else "position_feedback"
        if position_refs
        else "shared_events",
        "policy_position_references": position_refs,
        "native_verified": False,
        "execution_verified": False,
        "performance_observed_for_selection": False,
        "reviewed_at": datetime.now(UTC).isoformat(),
        "original_strategy_exit_difference": (
            "A/B는 원본 진입·명시 close만 매핑하고 원본 SL/TP·수량·피라미딩 성과를 재현하지 않습니다"
            if strategy
            else None
        ),
        **({key: value for key, value in previous.items() if key != "status"} if previous else {}),
        **result,
    }
    if unavailable:
        review.update(
            status="not_comparable",
            reason="unsupported_broker_feedback",
            unavailable_position_references=unavailable,
            basis="현재 ctx.position의 방향·수량·평균가만으로 원본 거래·계정 상태를 재현할 수 없습니다. 상수나 가짜 계정으로 대체하지 않습니다",
        )
    elif review["status"] != "reviewed" and previous is None:
        review["basis"] = "원문의 단일한 명시적 매수/매도 신호 쌍을 자동으로 확정하지 않았습니다"
    adaptation = review.pop("adaptation", None)
    executable = review.pop("executable_source", None)
    if adaptation:
        adapted = run / "adapted" / f"{item['id']}.pine"
        adapted.parent.mkdir(parents=True, exist_ok=True)
        adapted.write_bytes(adaptation.pop("strategy_source").encode())
        review.update(
            adapted_file=str(adapted.relative_to(run)),
            adapted_sha256=digest(adapted.read_bytes()),
            adaptation=adaptation,
        )
    elif executable:
        review.update(executable_file=receipt["source_file"], executable_sha256=source_hash)
    if strategy:
        review["native_price_exits_present"] = native_exits
    write(run / "reviews" / f"{item['id']}.json", review)
    return review


def review_pass(run: Path, args: argparse.Namespace) -> dict:
    cohort = read(run / "catalogue.json")
    processed, counts = 0, Counter()
    for item in cohort["items"]:
        if args.ids is not None and item["id"] not in args.ids:
            continue
        if (run / "reviews" / f"{item['id']}.json").exists():
            continue
        result = review_one(run, item, args.prior)
        if result is None:
            continue
        counts[result["status"]] += 1
        processed += 1
        print(
            json.dumps(
                {
                    "id": item["id"],
                    "status": result["status"],
                    "pine": result.get("pine_coverage", {}).get("status"),
                }
            ),
            flush=True,
        )
        if args.limit is not None and processed >= args.limit:
            break
    summary = {
        "processed": processed,
        "counts": dict(counts),
        "observed_at": datetime.now(UTC).isoformat(),
    }
    print(json.dumps(summary, ensure_ascii=False), flush=True)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path)
    parser.add_argument("--prior", type=Path)
    parser.add_argument("--ids", nargs="*")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--watch", action="store_true")
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.worker:
        print(json.dumps(inspect_worker(json.load(sys.stdin)), ensure_ascii=False))
        return
    if args.run is None:
        parser.error("--run이 필요합니다")
    run = args.run.resolve()
    process = {
        "pid": os.getpid(),
        "started_at": datetime.now(UTC).isoformat(),
        "command": [sys.executable, *sys.argv],
        "watch": args.watch,
        "script_sha256": digest(Path(__file__).read_bytes()),
        "log_file": str(run / "source-review.log"),
    }
    while True:
        write(run / "source-review-process.json", {**process, "status": "reviewing"})
        summary = review_pass(run, args)
        write(
            run / "source-review-process.json",
            {
                **process,
                "status": "watching" if args.watch else "completed",
                "last_pass": summary,
            },
        )
        if not args.watch:
            break
        time.sleep(10)


if __name__ == "__main__":
    main()
