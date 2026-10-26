"""검토한 공개 원문만 Sol 구독 CLI에 전달하고 최대 두 시도를 보존한다."""

from __future__ import annotations

import ast
import json
from pathlib import Path

from tools.research.period_study.schema import publication_id
from tools.research.period_study.state import checked, identity, now, read, sha, write
from tools.research.sol_codegen import generate

CONTRACT = """공개 Pine 원문과 검토된 신호 매핑의 계산·기본 입력·이벤트 의미를 그대로 Python으로 재현하세요.
Python init(params)->dict(선택), on_bar(ctx,state)->dict 계약입니다.
ctx['history']는 현재 완료봉까지의 dict 목록이고 ctx['bar']는 현재 완료봉입니다.
ctx['position']은 direction(flat/long/short),size,average_price를 갖습니다.
OHLCV는 decimal 문자열입니다. numpy/pandas/표준 라이브러리만 사용하세요.
반환은 {'action':'hold'|'long'|'short'|'close'}입니다.
봉마다 같은 방향의 새로운 이벤트도 그대로 반환하세요. 상태 지속을 새 이벤트로 만들지 마세요.
원문의 버전별 NA·seed·var·이전 봉·교차·동률 조건과 검토한 명시 close를 보존하세요.
SL/TP/수량/체결/수익/펀딩은 구현하지 마세요. 외부 실행기가 A/B 정책을 적용합니다.
미래 데이터·네트워크·파일·도구·검색·셸을 사용하지 마세요.
개선·최적화·새 매매 조건을 추가하지 마세요.
JSON {"source_code":"...","assumptions":["..."]}만 반환하세요.
"""


def failure_class(folder: Path, error: str) -> str:
    evidence = error.lower()
    for name in ("stderr.txt", "events.jsonl"):
        path = folder / name
        if path.exists():
            evidence += path.read_text().lower()
    if any(word in evidence for word in ("unauthorized", "not logged in", "authentication", "token expired", "401")):
        return "authentication"
    if any(word in evidence for word in ("quota", "usage limit", "rate limit", "429", "usage_limit")):
        return "quota_or_rate_limit"
    if "timeout" in evidence or "시간 초과" in evidence:
        return "timeout"
    return "generation_or_protocol"


def reviewed_source(root: Path, item: dict) -> tuple[str, str, dict]:
    pid = publication_id(item)
    receipt_path = root / "source_receipts" / f"{pid}.json"
    receipt = read(receipt_path) if receipt_path.exists() else {}
    expected = item.get("source_sha256") or receipt.get("source_sha256")
    if not expected:
        raise ValueError("source_receipt_missing")
    source_path = checked(root, item.get("source_file") or f"sources/{pid}.pine", expected)
    review_path = root / (item.get("review_file") or f"reviews/{pid}.json")
    if not review_path.is_file():
        raise ValueError("signal_mapping_review_missing")
    review = read(review_path)
    if review.get("source_sha256") != expected:
        raise ValueError("signal_mapping_source_hash_mismatch")
    if not review.get("reviewer", review.get("reviewed_by")) or not review.get("basis"):
        raise ValueError("signal_mapping_reviewer_or_basis_missing")
    if review.get("status", "reviewed") not in {"reviewed", "ready", "supported", "ok"}:
        raise ValueError(f"signal_mapping_review_not_ready:{review.get('status')}")
    if not isinstance(review.get("signal_bindings"), list):
        raise ValueError("signal_bindings_missing")
    return source_path.read_text(), expected, review


def generate_one(root: Path, source_root: Path, item: dict) -> dict:
    pid = publication_id(item)
    source, source_hash, review = reviewed_source(source_root, item)
    context = {
        "source": source, "signal_bindings": review["signal_bindings"],
        "inputs": review.get("inputs", {}), "signal_mode": review.get("signal_mode"),
    }
    binding_hash = identity(context)
    folder = root / "generation" / pid
    status_path = folder / "status.json"
    if status_path.exists():
        previous = read(status_path)
        if previous["input_hash"] != binding_hash:
            raise ValueError("생성 원문·입력·매핑 변경: 새 namespace가 필요합니다")
        return previous
    failures, classes = [], []
    for attempt in (0, 1):
        attempt_dir = folder / str(attempt)
        prompt = CONTRACT + "\n" + json.dumps(context, ensure_ascii=False)
        if attempt:
            prompt += "\n공개 구문·프로토콜 오류만 수정하세요: " + failures[-1]
        try:
            result = generate(prompt, attempt_dir, timeout=180)
            if result["status"] != "completed":
                failures.append(result.get("error") or result["status"])
                classes.append(failure_class(attempt_dir, failures[-1]))
                continue
            payload = read(attempt_dir / "payload.json")
            code = payload["source_code"]
            if not isinstance(code, str) or not code.strip() or len(code.encode()) > 131072:
                raise ValueError("source_code는 1~131072 byte 문자열이어야 합니다")
            ast.parse(code)
            source_path = attempt_dir / "source.py"
            if source_path.exists() and source_path.read_text() != code:
                raise ValueError("완료 생성 코드 변경")
            source_path.write_text(code)
            value = {
                "publication_id": pid, "status": "completed", "attempt": attempt,
                "input_hash": binding_hash, "source_sha256": source_hash,
                "generated_file": str(source_path.relative_to(root)),
                "generated_sha256": sha(code.encode()),
                "requested_model": "gpt-6.1-sol", "requested_effort": "high",
                "provider_reported_model": result.get("actual_model") or "UNKNOWN",
                "model_attestation": result.get("model_attestation"),
                "generation_hash": result["job_hash"], "completed_at": now(),
                "previous_failures": failures,
            }
            write(status_path, value)
            return value
        except (ValueError, KeyError, SyntaxError, RuntimeError) as error:
            failures.append(f"{type(error).__name__}:{error}")
            classes.append(failure_class(attempt_dir, failures[-1]))
    value = {
        "publication_id": pid, "status": "failed", "input_hash": binding_hash,
        "source_sha256": source_hash, "attempts": 2, "failures": failures,
        "failure_classes": classes,
        "requested_model": "gpt-6.1-sol", "provider_reported_model": "UNKNOWN",
        "completed_at": now(),
    }
    write(status_path, value)
    return value
