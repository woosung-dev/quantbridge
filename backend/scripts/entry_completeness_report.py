# 진입 완결성 분해를 오프라인에서 찍어보는 얇은 CLI — 로직은 전부 순수 모듈에 있다
"""라이브 진입 유실 크기 측정 (BL-536).

원장 한 창을 두 층위로 분해해 출력한다. 계산은 전부
`src/trading/entry_completeness.py` 에 있고 이 스크립트는 **조립만** 한다.

## 사용

    cd backend && set -a; source .env.local; set +a

    # 세션 하나
    uv run python scripts/entry_completeness_report.py --session-id <uuid>

    # 창으로 (겹치는 세션 전부)
    uv run python scripts/entry_completeness_report.py \
        --since 2026-07-29T00:00:00+00:00 --until 2026-07-30T00:00:00+00:00

    # counter 화해까지 (soak 전후 /metrics 스냅샷)
    curl -s localhost:8000/metrics > /tmp/before.txt      # soak 시작 전
    ...
    curl -s localhost:8000/metrics > /tmp/after.txt       # soak 종료 후
    uv run python scripts/entry_completeness_report.py --session-id <uuid> \
        --metrics-before /tmp/before.txt --metrics-after /tmp/after.txt

    --json 을 주면 사람이 읽는 표 대신 기계용 JSON 을 낸다.

## 왜 counter 를 파일로 받나

`qb_live_conditional_cancelled_total` 은 **프로세스 전역 누적** counter 이고 세션 label 이
없다. DB 세션만으로는 특정 soak 창의 `replaced` 차분을 복원할 수 없고, multiprocess
registry 도 현재 합계를 렌더할 뿐 과거 창을 되살리지 못한다. 그래서 창 양 끝의 스냅샷을
**명시 입력**으로 받는다. 스냅샷이 없으면 화해 섹션은 "counter 미제공" 으로 비운다 -
없는 숫자를 지어내지 않는다.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import UUID

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from src.tasks._worker_engine import create_worker_engine_and_sm  # noqa: E402
from src.trading.entry_completeness import (  # noqa: E402
    COUNTER_INTRODUCED,
    AttemptFact,
    AttemptLayer,
    CounterBasis,
    CounterReading,
    EntryCompletenessReport,
    EpisodeLayer,
    build_report,
    cancel_inequality_check,
    placement_identity_check,
)
from src.trading.repositories.live_signal_session_repository import (  # noqa: E402
    SESSION_WINDOW_SCAN_LIMIT,
    LiveSignalSessionRepository,
)
from src.trading.repositories.order_repository import (  # noqa: E402
    ENTRY_ATTEMPT_SCAN_LIMIT,
    OrderRepository,
    SessionScope,
)

# --- counter 스냅샷 파싱 -------------------------------------------------------
#
# Prometheus text exposition 한 줄: `name{label="v",...} 12.0`.
# 필요한 series 만 읽는다 - 전체 파싱기를 만들 이유가 없다.
_SAMPLE_PATTERN = re.compile(
    r"^(?P<name>[a-zA-Z_:][a-zA-Z0-9_:]*)(?P<labels>\{[^}]*\})?\s+(?P<value>\S+)$"
)
_LABEL_PATTERN = re.compile(r'(?P<key>[a-zA-Z_][a-zA-Z0-9_]*)="(?P<value>(?:[^"\\]|\\.)*)"')

# 화해에 쓰는 series. 원장 발자국이 있는지(`ledger_backed`)를 함께 박는다 - 이 라벨이
# "counter 전용 채널을 원장 비율과 합산하지 마라" 를 표에서 강제하는 자리다.
_CHANNELS: tuple[tuple[str, str, bool, str], ...] = (
    (
        "qb_live_conditional_placed_total",
        "조건부 진입 등재 (long+short)",
        True,
        "주문 행을 만든다. 원장 분해의 시도 수와 대조 가능",
    ),
    (
        "qb_live_conditional_guard_total",
        "등재 가드 판정",
        True,
        "conditional_placed + market_converted 의 합이 placed_total 과 같아야 한다",
    ),
    (
        "qb_live_conditional_cancelled_total",
        "reconcile 취소 (계측된 것만)",
        True,
        "★취소 전이 9 곳 중 여기만 counter 를 올린다. 원장 cancelled 가 항상 크거나 같다",
    ),
    (
        "qb_live_conditional_reconcile_errors_total",
        "reconcile 단계별 중단",
        False,
        "★`deferred_market_inflight` 등은 **주문 행을 만들지 않는다**. counter 전용 - "
        "원장 기반 비율과 절대 합산하지 마라",
    ),
    (
        "qb_live_conditional_plan_drop_evaluations_total",
        "계획기 드롭 평가 발화 (BL-536 신규)",
        False,
        "★유실 건수가 아니라 발화 횟수(중복 포함). 한 의도가 N분 살아 있으면 N 이다",
    ),
    (
        "qb_live_pending_order_skip_evaluations_total",
        "엔진 pending skip 평가 발화 (BL-536 신규)",
        False,
        "★유실 건수가 아니라 발화 횟수(중복 포함). run_live 성공 평가에서만 오른다",
    ),
)


@dataclass(frozen=True, slots=True)
class CounterSnapshot:
    samples: dict[tuple[str, tuple[tuple[str, str], ...]], float]

    def value(self, name: str, **labels: str) -> float:
        """없는 series 는 0.0. **차분 계산에는 쓰지 마라** — `probe` 를 써라."""
        key = (name, tuple(sorted(labels.items())))
        return self.samples.get(key, 0.0)

    def probe(self, name: str, **labels: str) -> float | None:
        """없는 series 를 `None` 으로 구분해 돌려준다.

        ★`value()` 의 0.0 기본값은 "counter 가 아직 0" 과 "그 스냅샷에 series 자체가
        없다" 를 같은 값으로 뭉갠다. 후자는 **counter 도입 전 스냅샷**일 수 있고, 그때
        `after - 0` 은 차분이 아니라 절대값이다 (R2-④).
        """
        return self.samples.get((name, tuple(sorted(labels.items()))))

    def series(self, name: str) -> list[tuple[tuple[tuple[str, str], ...], float]]:
        return sorted(
            (sample_labels, value)
            for (sample_name, sample_labels), value in self.samples.items()
            if sample_name == name
        )


def parse_metrics_text(text: str) -> CounterSnapshot:
    samples: dict[tuple[str, tuple[tuple[str, str], ...]], float] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        match = _SAMPLE_PATTERN.match(line)
        if match is None:
            continue
        try:
            value = float(match.group("value"))
        except ValueError:
            continue
        labels = tuple(
            sorted(
                (item.group("key"), item.group("value"))
                for item in _LABEL_PATTERN.finditer(match.group("labels") or "")
            )
        )
        samples[(match.group("name"), labels)] = value
    return CounterSnapshot(samples=samples)


# ★예전에 있던 `_delta()` 는 **삭제했다** (R2-④). 그 함수는 `before` 가 없으면 0 을
#   기준으로 빼서 절대값을 차분처럼 돌려줬다 — 즉 이 도구가 막으려는 함정을 만드는
#   함수였다. 남겨두면 다음 사람이 그걸 부른다. 차분은 `_reading` / `_summed_reading`
#   하나로만 얻는다.


def _reading(
    before: CounterSnapshot | None, after: CounterSnapshot | None, name: str, **labels: str
) -> CounterReading | None:
    """스냅샷에서 counter 하나를 읽되 **어떻게 읽었는지**를 값에 묶어 돌려준다 (R1).

    ★`before` 가 없으면 그것은 차분이 아니라 **절대값**이다. 예전 이 스크립트는 그 값을
    "차분" 이라고 출력했고, 그것이 실측 126 vs 99 의 27 을 설명 불가로 만든 원인이다.
    `CounterBasis` 가 그 구분을 타입으로 들고 다니며, 교차 비교 함수가 절대값을 **거부**한다.
    """
    if after is None:
        return None
    if before is None:
        return CounterReading(
            name=name, value=after.value(name, **labels), basis=CounterBasis.absolute
        )
    return _delta_reading(name, before.probe(name, **labels), after.value(name, **labels))


def _delta_reading(name: str, base: float | None, current: float) -> CounterReading:
    """차분 하나를 basis 와 함께 만든다. **두 함정을 여기서 한꺼번에 막는다.**

    ★R2-④ — `base` 가 `None` 이면 before 스냅샷에 그 series 가 **없었다**는 뜻이다.
    없는 key 를 0 으로 읽어 `current - 0` 을 차분이라 부르면, 그것은 절대값이면서
    `delta` 라벨을 달고 비교를 통과한다. 그 상황이 정확히 이 가드가 겨냥한 것이다 —
    **counter 가 태어나기 전에 뜬 스냅샷.**

    ★R2-⑤ — 차분이 음수면 창 중간에 counter 가 리셋된 것이다(재배포·mmap 재생성).
    음수를 그대로 두면 `원장 >= 음수` 가 무조건 성립해 부등식의 검정력이 0 이 된다.
    절대값은 거부하면서 음수는 통과시키는 비대칭을 남기지 않는다.
    """
    if base is None:
        return CounterReading(name=name, value=current, basis=CounterBasis.unknown)
    value = current - base
    if value < 0:
        return CounterReading(name=name, value=value, basis=CounterBasis.counter_reset)
    return CounterReading(name=name, value=value, basis=CounterBasis.delta)


def _summed_reading(
    before: CounterSnapshot | None, after: CounterSnapshot | None, name: str
) -> CounterReading | None:
    """한 counter 의 전 label series 를 합친다 (`placed_total{long}+{short}`).

    ★basis 는 **가장 약한 것**을 취한다. series 하나라도 판독 불가면 합계 전체가 판독
    불가다 — 합산이 basis 를 씻어내는 구멍을 남기지 않는다.
    """
    if after is None:
        return None
    if before is None:
        total = sum(value for _labels, value in after.series(name))
        return CounterReading(name=name, value=total, basis=CounterBasis.absolute)

    # ★**before ∪ after 를 순회한다** (R3-③). `after.series()` 만 돌면 before 에 있던
    #   series 가 after 에서 **사라진** 경우를 방문조차 하지 못한다 — 리셋이나 부분 mmap
    #   소실이 그 모양이고, 남은 series 만 합산한 값이 조용히 `delta` 로 라벨된다.
    #   R2-④ 는 "before 에 없음" 을 막았고, 이것은 **대칭인 반대쪽 문**이다.
    #   사라진 series 는 `after.value()` 가 0.0 이라 차분이 음수가 되고, 기존 음수 규칙이
    #   `counter_reset` 으로 판정한다 — 새 규칙을 만들지 않고 전파를 재사용한다.
    label_sets = sorted(
        {labels for labels, _value in after.series(name)}
        | {labels for labels, _value in before.series(name)}
    )
    readings = [
        _delta_reading(name, before.probe(name, **dict(labels)), after.value(name, **dict(labels)))
        for labels in label_sets
    ]
    total = sum(reading.value for reading in readings)
    for weakest in (CounterBasis.unknown, CounterBasis.counter_reset):
        if any(reading.basis is weakest for reading in readings):
            return CounterReading(name=name, value=total, basis=weakest)
    return CounterReading(name=name, value=total, basis=CounterBasis.delta)


_BASIS_NOTES: dict[CounterBasis, str] = {
    CounterBasis.delta: "차분(두 스냅샷)",
    CounterBasis.absolute: "★절대값 — 유효 시작점 미상. 다른 counter 와 비교 금지",
    CounterBasis.unknown: "★판독 불가 — before 스냅샷에 그 series 가 없다(도입 전일 수 있다). 비교 금지",
    CounterBasis.counter_reset: "★counter 리셋 — 차분이 음수다(재배포·mmap 재생성). 비교 금지",
}


def _basis_note(basis: CounterBasis) -> str:
    return _BASIS_NOTES[basis]


# --- 출력 ---------------------------------------------------------------------


def _rate(value: Decimal | None) -> str:
    return "n/a (분모 0)" if value is None else f"{value * Decimal('100'):.2f}%"


def _print_attempt_layer(layer: AttemptLayer) -> None:
    print(f"\n  [{layer.label}]  총 {layer.total} 행")
    print(
        f"    has_fill {layer.has_fill} · rejected {layer.rejected} · "
        f"cancelled {layer.cancelled} · open {layer.open}"
        f"   (합 {layer.has_fill + layer.rejected + layer.cancelled + layer.open})"
    )
    print(
        f"    거절 출처 — 거래소 확정 {layer.rejected_exchange} · "
        f"로컬 실패(거래소 미도달) {layer.rejected_local} · 코드 미상 {layer.rejected_unknown}"
    )
    print(
        f"    확정 거절률 = 거래소 확정 거절 / (체결 + 거래소 확정 거절) "
        f"= {_rate(layer.confirmed_rejection_rate)}   (n={layer.exchange_verdicted})"
    )
    print(
        "      ★분모는 '거래소 도달' 이 아니라 '**판정으로 종결**' 이다 — "
        "submitted/cancelled 도 거래소가 수락했지만 판정은 아니다."
    )
    print(
        f"    겹치는 진단 — 판독 불가 종결 {layer.unreadable_terminal} · "
        f"판정 유예 {layer.verdict_deferred}"
    )
    if layer.rejected_local:
        print(
            f"    ★로컬 실패 {layer.rejected_local} 건은 거래소에 도달조차 못 했다 "
            "(자격증명 복호화 실패 등) — 유실이 아니라 우리 장애다."
        )
    if layer.rejected_ret_codes:
        codes = " · ".join(f"{code}x{count}" for code, count in layer.rejected_ret_codes)
        print(f"    거절 retCode — {codes}")
        print(
            "      ★`unparsed` 는 '거절 아님' 이 아니다 — **비동기 경로 거절은 코드 미상**이다"
            "(retCode 를 원문에 싣는 경로가 동기 1곳뿐인 선재 결함)."
        )


def _print_episode_layer(layer: EpisodeLayer) -> None:
    provisional = "  ★잠정(open 있음)" if layer.provisional else ""
    print(f"\n  [{layer.label}]  총 {layer.total} 에피소드{provisional}")
    print(
        f"    won {layer.won} · lost {layer.lost} · abandoned {layer.abandoned} · "
        f"open {layer.open}   (합 {layer.won + layer.lost + layer.abandoned + layer.open})"
    )
    rate = _rate(layer.loss_rate)
    if layer.provisional:
        print(f"    유실률 = lost / (won + lost + abandoned) = {rate}  ★잠정 — **하한**이다")
        print(
            f"      open {layer.open} 건이 아직 판정되지 않았다. "
            "확정값으로 인용하지 마라 — 나중에 lost 로 굳을 수 있다."
        )
    else:
        print(f"    유실률 = lost / (won + lost + abandoned) = {rate}")
    if layer.open_with_prior_rejection:
        # ★"확정 거절" 이라고 쓰면 안 된다 (R3-④) — 이 수는 `_counts_as_loss` 기준이라
        #   retCode 가 있는 확정 거절과 코드 미상 거절을 **함께** 센다(로컬 실패만 제외).
        print(
            f"    ★★open 에피소드 중 {layer.open_with_prior_rejection} 건은 그 구간에 "
            "**거절이 있었다(확정 + 코드 미상)** — 유실이 open 뒤에 숨어 있다."
        )
    if layer.lost_with_unknown_origin:
        print(
            f"    lost 중 {layer.lost_with_unknown_origin} 건은 retCode 가 없어 "
            "거래소 확정이 아니다(코드 미상 거절)."
        )
    print(
        f"    창 안 완전 종결분만 = {_rate(layer.settled_loss_rate)} (n={layer.settled_resolved})"
    )


def _print_report(report: EntryCompletenessReport) -> None:
    print("=" * 78)
    print(f"세션 {report.session_id}")
    print(
        f"창(created_at) [{report.since.isoformat()}, {report.until.isoformat() if report.until else '∞'})"
    )
    print(f"조회 시각 {report.queried_at.isoformat()}   ← 상태는 이 시각의 값이다")
    if report.truncated:
        print("★절단됨 — 창을 좁혀라. 아래 숫자는 부분 원장이다.")
    print(
        f"귀속 — 조건부 우리 것 {report.attribution.conditional_ours} · "
        f"비조건부 우리 것 {report.attribution.nonconditional_ours} · "
        f"귀속 불가 {report.attribution.unattributable}"
    )
    print("\n── 층위 1: 발주 시도 (행 하나 = 시도 하나) ──")
    _print_attempt_layer(report.scope_attempts)
    _print_attempt_layer(report.conditional_attempts)
    print("\n── 층위 2: 진입 에피소드 (조건부 우리 것만) ──")
    print("  ★두 규칙의 수치를 함께 낸다. 한쪽만 인용하면 그것이 거짓말이다.")
    _print_episode_layer(report.primary)
    _print_episode_layer(report.alternative)
    print("\n★층위 1 과 층위 2 를 합산하지 마라 — 분모가 다르다.")


def _print_reconciliation(
    report: EntryCompletenessReport,
    before: CounterSnapshot | None,
    after: CounterSnapshot | None,
) -> None:
    print("\n── 화해: 원장 vs counter ──")
    print("  채널마다 **원장 발자국이 있는지**를 먼저 박는다.")
    for name, title, ledger_backed, note in _CHANNELS:
        mark = "원장 O" if ledger_backed else "counter 전용"
        print(f"\n  [{mark}] {title}  ({name})")
        print(f"    {note}")
        if after is None:
            print("    차분: counter 스냅샷 미제공 (--metrics-after)")
            continue
        series = after.series(name)
        if not series:
            print("    차분: 스냅샷에 해당 series 없음")
            continue
        introduced = COUNTER_INTRODUCED.get(name)
        if introduced:
            print(f"    도입 {introduced}")
        # ★읽기 방식은 series 마다 다를 수 있다 — before 에 하나만 빠져도 그 하나는
        #   차분이 아니다. counter 단위로 한 줄 찍고 끝내면 그 구분이 사라진다.
        for labels, _value in series:
            label_text = ",".join(f"{k}={v}" for k, v in labels) or "(no labels)"
            reading = _reading(before, after, name, **dict(labels))
            if reading is None:
                continue
            print(f"    {label_text}: {reading.value}   [{_basis_note(reading.basis)}]")

    print("\n  ── 항등식 검산 (③-c a) ──")
    placed = _summed_reading(before, after, "qb_live_conditional_placed_total")
    guard_conditional = _reading(
        before, after, "qb_live_conditional_guard_total", outcome="conditional_placed"
    )
    guard_market = _reading(
        before, after, "qb_live_conditional_guard_total", outcome="market_converted"
    )
    if placed is None or guard_conditional is None or guard_market is None:
        print("    counter 스냅샷 미제공 (--metrics-after)")
    else:
        check = placement_identity_check(
            placed=placed,
            conditional_placed=guard_conditional,
            market_converted=guard_market,
        )
        print(f"    {check.label}")
        print(f"    {check.detail}")
    print("    (구조: live_signal 의 인접 두 줄에서 무조건 함께 오른다 — 라벨 축만 다르다)")
    print(
        "    ★그래도 절대값으로는 검산 못 한다 — 두 counter 의 도입 시점이 하루 다르다"
        " (30031efe / 274dc645). 실측 126 vs 99 의 27 이 그 차이다."
    )

    print("\n  ── 부등식 검산 (③-b) ──")
    ledger_cancelled = report.conditional_attempts.cancelled
    replaced = _reading(before, after, "qb_live_conditional_cancelled_total", reason="replaced")
    if replaced is None:
        print(f"    원장 cancelled {ledger_cancelled} · counter{{replaced}} 미제공")
        print("    ★`원장 cancelled == counter{replaced}` 는 **항등식이 아니다**.")
    else:
        check = cancel_inequality_check(ledger_cancelled=ledger_cancelled, replaced=replaced)
        print(f"    {check.label}")
        print(f"    {check.detail}")
    print(
        "    근거: `transition_to_cancelled` 호출부 9 곳 중 counter 를 올리는 곳은 1 곳뿐이고"
        " (`live_signal.py` reconcile 취소 루프), `Order` 에 취소 사유 컬럼이 없다."
    )


def _report_to_json(report: EntryCompletenessReport) -> dict[str, Any]:
    def attempts(layer: AttemptLayer) -> dict[str, Any]:
        return {
            "label": layer.label,
            "total": layer.total,
            "has_fill": layer.has_fill,
            "rejected": layer.rejected,
            "cancelled": layer.cancelled,
            "open": layer.open,
            "unreadable_terminal": layer.unreadable_terminal,
            "verdict_deferred": layer.verdict_deferred,
            "rejected_ret_codes": dict(layer.rejected_ret_codes),
            "rejected_exchange": layer.rejected_exchange,
            "rejected_local": layer.rejected_local,
            "rejected_unknown": layer.rejected_unknown,
            "exchange_verdicted": layer.exchange_verdicted,
            "confirmed_rejection_rate": None
            if layer.confirmed_rejection_rate is None
            else str(layer.confirmed_rejection_rate),
        }

    def episodes(layer: EpisodeLayer) -> dict[str, Any]:
        return {
            "rule": layer.rule.value,
            "label": layer.label,
            "total": layer.total,
            "won": layer.won,
            "lost": layer.lost,
            "abandoned": layer.abandoned,
            "open": layer.open,
            # ★기계 판독 소비자도 잠정 여부를 알아야 한다 - 숫자만 뽑아가면 확정값이 된다.
            "provisional": layer.provisional,
            "open_with_prior_rejection": layer.open_with_prior_rejection,
            "lost_with_unknown_origin": layer.lost_with_unknown_origin,
            "loss_rate": None if layer.loss_rate is None else str(layer.loss_rate),
            "settled_loss_rate": None
            if layer.settled_loss_rate is None
            else str(layer.settled_loss_rate),
            "settled_resolved": layer.settled_resolved,
        }

    return {
        "session_id": str(report.session_id),
        "since": report.since.isoformat(),
        "until": None if report.until is None else report.until.isoformat(),
        "queried_at": report.queried_at.isoformat(),
        "truncated": report.truncated,
        "attribution": {
            "conditional_ours": report.attribution.conditional_ours,
            "nonconditional_ours": report.attribution.nonconditional_ours,
            "unattributable": report.attribution.unattributable,
        },
        "scope_attempts": attempts(report.scope_attempts),
        "conditional_attempts": attempts(report.conditional_attempts),
        "primary": episodes(report.primary),
        "alternative": episodes(report.alternative),
    }


# --- 조립 ---------------------------------------------------------------------


async def _collect(
    *, session_ids: list[UUID], since: datetime | None, until: datetime | None
) -> list[EntryCompletenessReport]:
    engine, sm = create_worker_engine_and_sm()
    reports: list[EntryCompletenessReport] = []
    try:
        async with sm() as db:
            session_repo = LiveSignalSessionRepository(db)
            order_repo = OrderRepository(db)

            if session_ids:
                sessions = [await session_repo.get_by_id(sid) for sid in session_ids]
                live_sessions = [s for s in sessions if s is not None]
                missing = len(sessions) - len(live_sessions)
                if missing:
                    print(f"★세션 {missing} 개를 찾지 못했다", file=sys.stderr)
            else:
                if since is None:
                    raise SystemExit("--session-id 가 없으면 --since 가 필요하다")
                live_sessions = list(
                    await session_repo.list_overlapping_window(since=since, until=until)
                )
                # ★세션 집합의 절단도 주문 절단과 **같은 규율**로 다룬다 (R3-⑥).
                #   조용히 잘리면 리포트가 "이 창의 전부" 라고 말하면서 세션 몇 개를
                #   통째로 빠뜨린다 — 절단된 분모는 유실률을 낙관적으로 왜곡한다.
                if len(live_sessions) > SESSION_WINDOW_SCAN_LIMIT:
                    live_sessions = live_sessions[:SESSION_WINDOW_SCAN_LIMIT]
                    print(
                        f"★세션 집합 절단 — 창에 겹치는 세션이 {SESSION_WINDOW_SCAN_LIMIT} 개를 "
                        "넘는다. 아래는 **부분 집합**이다. 창을 좁혀서 다시 돌려라.",
                        file=sys.stderr,
                    )

            for live_session in live_sessions:
                scope = SessionScope.from_live_session(live_session)
                window_since = since if since is not None else scope.started_at
                rows = await order_repo.list_entry_attempts(scope, since=window_since, until=until)
                truncated = len(rows) > ENTRY_ATTEMPT_SCAN_LIMIT
                facts = [
                    AttemptFact(
                        order_id=row.order_id,
                        session_id=live_session.id,
                        idempotency_key=row.idempotency_key,
                        state=row.state,
                        quantity=row.quantity,
                        filled_quantity=row.filled_quantity,
                        created_at=row.created_at,
                        terminal_at=row.terminal_at,
                        error_message=row.error_message,
                    )
                    for row in rows[:ENTRY_ATTEMPT_SCAN_LIMIT]
                ]
                reports.append(
                    build_report(
                        facts,
                        session_id=live_session.id,
                        since=window_since,
                        until=until,
                        queried_at=datetime.now(UTC),
                        truncated=truncated,
                    )
                )
    finally:
        await engine.dispose()
    return reports


def _parse_time(raw: str | None) -> datetime | None:
    if raw is None:
        return None
    parsed = datetime.fromisoformat(raw)
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)


def _load_snapshot(path: str | None) -> CounterSnapshot | None:
    if path is None:
        return None
    return parse_metrics_text(Path(path).read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="라이브 진입 완결성 분해 (BL-536). 아무것도 고치지 않고 크기만 잰다."
    )
    parser.add_argument("--session-id", action="append", default=[], help="반복 지정 가능")
    parser.add_argument("--since", default=None, help="ISO 8601. 없으면 세션 시작 시각")
    parser.add_argument("--until", default=None, help="ISO 8601. 없으면 상한 없음")
    parser.add_argument("--metrics-before", default=None, help="창 시작 시점 /metrics 덤프")
    parser.add_argument("--metrics-after", default=None, help="창 종료 시점 /metrics 덤프")
    parser.add_argument("--json", action="store_true", help="사람용 표 대신 JSON")
    args = parser.parse_args()

    session_ids = [UUID(value) for value in args.session_id]
    since = _parse_time(args.since)
    until = _parse_time(args.until)
    before = _load_snapshot(args.metrics_before)
    after = _load_snapshot(args.metrics_after)

    reports = asyncio.run(_collect(session_ids=session_ids, since=since, until=until))
    if not reports:
        print("해당 창에 세션이 없다", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps([_report_to_json(report) for report in reports], indent=2))
        return 0

    for report in reports:
        _print_report(report)
        _print_reconciliation(report, before, after)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
