"""동결 결과의 메모리 제한 후처리. 전략·경제 계산을 다시 실행하지 않는다.

기존 report/export 인자를 그대로 전달하며 원격 종결은 앞에 remote를 붙인다.
install()은 watcher에서도 호출할 수 있다. 원시 파일·판정은 보존하고 두 대형
곡선의 메모리 누적을 막으며 계산 불가능한 Sharpe만 표시용 NULL로 바꾼다.
계획 해시는 receipts 호출 한 번 안에서만 재사용하고 종료 시 원본으로 재검사한다.
verification 전역 identity의 임시 교체는 스레드 없는 순차 후처리 호출자 전용이다.
"""

from __future__ import annotations

import argparse
import sys
from functools import wraps
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "apps/api")]

CURVES = ("drawdown_curve", "buy_and_hold_curve")
POSTPROCESSING = {
    "schema_version": 1,
    "calculation_rerun": False,
    "raw_files_modified": False,
    "omitted_in_memory_metrics": list(CURVES),
    "sharpe_display": "unavailable_convention_as_null_valid_zero_preserved",
    "plan_identity_scope": "one_receipts_call_sequential_only",
}


def install():
    """반환 메모리·표시 열만 보강한다. 기존 해시·경제·신호 판정은 그대로다."""
    from tools.research.editor_picks import report, verification

    from src.backtest.engine.metrics import sharpe_is_unavailable

    if "sharpe_convention" not in report.METRICS:
        report.METRICS = (*report.METRICS, "sharpe_convention")
    original_receipts = verification.receipts
    if not getattr(original_receipts, "editor_picks_receipts_postprocess", False):

        @wraps(original_receipts)
        def scoped_receipts(root, frozen):
            original_identity = verification.identity
            plan_hash = original_identity(frozen)

            def scoped_identity(value):
                return plan_hash if value is frozen else original_identity(value)

            verification.identity = scoped_identity
            try:
                return original_receipts(root, frozen)
            finally:
                verification.identity = original_identity
                if original_identity(frozen) != plan_hash:
                    raise ValueError("receipt 검증 중 동결 계획이 변경됐습니다")

        scoped_receipts.editor_picks_receipts_postprocess = True
        scoped_receipts.editor_picks_receipts_original = original_receipts
        verification.receipts = scoped_receipts
    report.receipts = verification.receipts
    original = verification.read
    if getattr(original, "editor_picks_postprocess", False):
        return original.editor_picks_postprocess_original

    @wraps(original)
    def projected_read(path):
        value = original(path)
        if Path(path).name == "receipt.json" and isinstance(value, dict):
            metrics = value.get("metrics")
            if isinstance(metrics, dict):
                for key in CURVES:
                    metrics.pop(key, None)
                if sharpe_is_unavailable(metrics.get("sharpe_convention")):
                    metrics["sharpe_ratio"] = None
        return value

    projected_read.editor_picks_postprocess = True
    projected_read.editor_picks_postprocess_original = original
    projected_read.postprocessing = POSTPROCESSING
    verification.read = projected_read
    return original


def main(argv=None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if arguments[:1] == ["remote"]:
        if arguments[1:2] != ["finalize"]:
            raise SystemExit("원격 후처리는 remote finalize만 허용합니다")
        from tools.research.editor_picks.remote import main as delegate

        delegated = arguments[1:]
    else:
        parser = argparse.ArgumentParser(add_help=False)
        parser.add_argument("--run-dir")
        _, remaining = parser.parse_known_args(arguments)
        if not remaining or remaining[0] not in {"report", "export"}:
            raise SystemExit("후처리는 기존 report/export 인자 또는 remote finalize를 사용합니다")
        from tools.research.editor_picks.__main__ import main as delegate

        delegated = arguments
    install()
    previous = sys.argv
    try:
        sys.argv = [previous[0], *delegated]
        return delegate()
    finally:
        sys.argv = previous


if __name__ == "__main__":
    raise SystemExit(main())
