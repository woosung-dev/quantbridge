# `direction` 발산을 원장으로 재판정하는 오프라인 오라클 — 구현과 독립이어야 뜻이 있다
"""`direction` 포지션 발산을 `replay_lag` / `phantom` 으로 가른다 ([BL-591]).

## 왜 필요한가

`qb_live_position_divergence_total{category="direction_transient"}` 은 **부호가 반대인 두
현상을 한 라벨에 묻는다**:

- **`replay_lag`** — 조건부 주문이 **봉 중간에 거래소에서 체결**됐고 엔진은 봉 마감까지
  그걸 못 본다. **거래소가 앞서고 엔진이 뒤진다.** 다음 tick 에 스스로 낫는다.
- **`phantom`** — 엔진 시뮬이 체결로 친 주문이 **거래소에 아예 없다.** **엔진이 앞선다.**
  낫지 않으며 연속 2회 판정으로 세션을 죽인다.

현행 코드는 이 둘을 **「연속 2회 판정」이라는 타이밍 대리 지표**로만 가른다
(`live_signal.py:2734`). 이 스크립트는 그 대리 지표 대신 **원장의 체결 시각**으로 직접
판정해, 프로덕션에 라벨을 넣기 전에 판별식을 검증한다.

## 판별식

엔진이 평가한 마지막 봉은 **닫힌 봉**이다 — `ccxt.py:145` 가
`last_closed_ts = (now // tf) * tf - tf` 로 진행 중 봉을 잘라내고, `live_signal.py:2299`
가 그 마지막 행의 **시가 시각**을 `last_bar_time` 으로 쓴다. 따라서 엔진의 가시 지평은

    horizon = last_bar_time + interval = floor(평가시각, interval)

이고, 세션 소유 최신 체결 `t_fill` 에 대해

| 조건                    | 라벨                       |
| ----------------------- | -------------------------- |
| `t_fill >= horizon`     | `replay_lag` (엔진이 아직 못 봄 — 무해) |
| `t_fill <  horizon`     | `phantom` (엔진이 봤는데도 어긋남)      |
| 세션 소유 체결이 없다   | `unattributed`             |

★**`unattributed` 는 실재한다** — 운영자 청산 주문은 `idempotency_key` 가 비어 있어 어느
세션에도 귀속되지 않는다. 유령으로도 정상으로도 접지 않는다(`engine_only` 세분화 선례).

★**세션 귀속은 `idempotency_key` 로만 한다.** `trading.orders` 에는 `session_id` 가 없고,
계정으로 귀속하면 [BL-592] 의 `exchange_accounts` 2행 중복에 걸려 **3.7배 부풀려진다.**

## ★판별식은 한쪽으로만 틀린다 — `phantom` 은 믿을 수 있고 `replay_lag` 은 아니다

`Order.filled_at` 은 **거래소 체결시각이 아니라 우리 관측시각**이다
(`order_repository.py:53,107,129,212` — 이름과 달리 terminal 시각). 우리 타임스탬프는 실제
체결보다 **항상 늦으므로** `t_fill >= horizon` 이 참으로 기울고, 그래서 이 판별식은

- **`phantom` 을 과소계상한다** (진짜 phantom 을 `replay_lag` 로 놓칠 수 있다)
- **`replay_lag` 을 과대계상하지 않는다** (무해를 유령으로 뒤집지 않는다)

⇒ **`phantom` 라벨은 신뢰할 수 있다.** 슬라이스 2 가 「`phantom` 즉시 킬」을 채택한 근거가
여기다 — 이 방향의 오차는 **거짓 사망을 만들지 않는다.** 반대로 「`replay_lag` 이니 무해」는
그만큼 믿을 수 없다. 실측 최소 여유는 **0.652초**(2026-08-03 23:17)로, 경계는 실제로 붙는다.

## ★이 오라클이 증명하는 것과 못 하는 것

판별식을 관측 11건에서 **유도**했으므로 같은 11건에 잘 맞는 것은 검증이 아니다. 독립적인
검사는 **사망 상관** 하나뿐이다 — 사망은 「연속 2회 판정」으로 정해지고 체결 경과시간과
무관하게 결정되므로, `phantom` 쌍이 사망과 일치하면 서로 다른 두 신호가 만난 것이다.
나머지는 **전향 예측**으로만 갚을 수 있다.

## 사용

    QB=/path/to/quant-bridge
    set -a; . $QB/backend/.env.local; set +a; cd $QB/backend

    docker logs quantbridge-worker 2>&1 \\
      | uv run python scripts/classify_direction_divergence.py

    uv run python scripts/classify_direction_divergence.py --log /tmp/worker.log --json

★**워커 로그는 컨테이너 수명에 묶여 있다.** 재기동하면 증거가 사라지므로 출력을
`.soak/` 에 남겨라.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from sqlalchemy import text  # noqa: E402

from src.tasks._worker_engine import create_worker_engine_and_sm  # noqa: E402

# --- 로그 파싱 -----------------------------------------------------------------
#
# 워커 한 줄: `... live_signal_position_divergence session_id=<uuid> symbol=BTC/USDT
#              category=direction engine_position=-0.03 exchange_position=0.03`
# 앞의 celery prefix 는 포맷이 여러 벌이라 파싱하지 않는다 — ISO 타임스탬프만 집어낸다.
_LINE_PATTERN = re.compile(
    r"live_signal_position_divergence\s+"
    r"session_id=(?P<session>[0-9a-fA-F-]{36})\s+"
    r"symbol=(?P<symbol>\S+)\s+"
    r"category=(?P<category>\w+)\s+"
    r"engine_position=(?P<engine>-?[\d.eE+-]+)\s+"
    r"exchange_position=(?P<exchange>-?[\d.eE+-]+)"
)
# `docker logs --timestamps` 접두 또는 celery 자체 `[YYYY-MM-DD HH:MM:SS,mmm:` 중 첫 매치.
_TS_PATTERN = re.compile(
    r"(?P<date>\d{4}-\d{2}-\d{2})[T ](?P<time>\d{2}:\d{2}:\d{2})[.,](?P<frac>\d+)"
)

# 원장 idempotency key: `live:<session_id>:...`. 프로덕션 파서를 쓰지 않는다 — 이 오라클은
# 검증 대상 코드와 독립이어야 한다.
_IDEM_SESSION_PATTERN = re.compile(r"^live:(?P<session>[0-9a-fA-F-]{36}):")

_INTERVAL_SECONDS: dict[str, int] = {
    "1m": 60,
    "3m": 180,
    "5m": 300,
    "15m": 900,
    "30m": 1800,
    "1h": 3600,
    "2h": 7200,
    "4h": 14400,
    "1d": 86400,
}


@dataclass(frozen=True)
class DivergenceEvent:
    """로그 한 줄에서 읽은 발산 관측."""

    at: datetime
    session_id: UUID
    symbol: str
    category: str
    engine: float
    exchange: float


@dataclass
class Verdict:
    """한 관측의 재판정 결과."""

    event: DivergenceEvent
    interval_seconds: int
    horizon: datetime
    last_fill_at: datetime | None
    last_fill_side: str | None
    last_fill_qty: str | None
    label: str
    threshold_label: str
    died_here: bool

    @property
    def gap_seconds(self) -> float | None:
        if self.last_fill_at is None:
            return None
        return (self.event.at - self.last_fill_at).total_seconds()

    def as_dict(self) -> dict[str, Any]:
        return {
            "at": self.event.at.isoformat(),
            "session_id": str(self.event.session_id),
            "engine": self.event.engine,
            "exchange": self.event.exchange,
            "last_fill_at": self.last_fill_at.isoformat() if self.last_fill_at else None,
            "last_fill_side": self.last_fill_side,
            "gap_seconds": self.gap_seconds,
            "horizon": self.horizon.isoformat(),
            "label": self.label,
            "threshold_label": self.threshold_label,
            "died_here": self.died_here,
        }


def parse_log(lines: list[str], *, category: str = "direction") -> list[DivergenceEvent]:
    """워커 로그에서 해당 category 의 발산 관측을 뽑는다.

    타임스탬프를 못 읽은 줄은 **버리지 않고 예외로 올린다** — 조용히 빠지면 분모가
    말없이 줄어든다.
    """
    events: list[DivergenceEvent] = []
    for lineno, line in enumerate(lines, start=1):
        match = _LINE_PATTERN.search(line)
        if match is None or match.group("category") != category:
            continue
        ts_match = _TS_PATTERN.search(line)
        if ts_match is None:
            raise ValueError(f"타임스탬프를 못 읽었다 (line {lineno}): {line[:120]!r}")
        micro = f"{ts_match.group('frac'):0<6}"[:6]
        at = datetime.fromisoformat(
            f"{ts_match.group('date')}T{ts_match.group('time')}.{micro}+00:00"
        )
        events.append(
            DivergenceEvent(
                at=at,
                session_id=UUID(match.group("session")),
                symbol=match.group("symbol"),
                category=match.group("category"),
                engine=float(match.group("engine")),
                exchange=float(match.group("exchange")),
            )
        )
    return events


def floor_to_interval(at: datetime, interval_seconds: int) -> datetime:
    """`at` 을 봉 경계로 내림 — 엔진의 가시 지평 `last_bar_time + interval` 과 같다."""
    epoch = int(at.timestamp())
    return datetime.fromtimestamp((epoch // interval_seconds) * interval_seconds, tz=UTC)


async def _load_sessions(sm: Any, session_ids: set[UUID]) -> dict[UUID, dict[str, Any]]:
    if not session_ids:
        return {}
    async with sm() as db:
        rows = await db.execute(
            text(
                "SELECT id, interval, symbol, deactivated_at, deactivated_reason "
                "FROM trading.live_signal_sessions WHERE id = ANY(:ids)"
            ),
            {"ids": list(session_ids)},
        )
        return {row.id: dict(row._mapping) for row in rows}


async def _load_fills(sm: Any, symbols: set[str]) -> list[dict[str, Any]]:
    """창 안의 체결을 통째로 읽어 파이썬에서 세션 귀속한다.

    SQL 로 `idempotency_key LIKE 'live:<uuid>:%'` 를 세션마다 돌리는 것보다 왕복이 적고,
    귀속 규칙이 한곳(`_IDEM_SESSION_PATTERN`)에만 있게 된다.
    """
    if not symbols:
        return []
    async with sm() as db:
        rows = await db.execute(
            text(
                "SELECT filled_at, symbol, side::text AS side, quantity, idempotency_key "
                "FROM trading.orders "
                "WHERE state = 'filled' AND filled_at IS NOT NULL AND symbol = ANY(:symbols) "
                "ORDER BY filled_at"
            ),
            {"symbols": list(symbols)},
        )
        return [dict(row._mapping) for row in rows]


def adjudicate(
    events: list[DivergenceEvent],
    sessions: dict[UUID, dict[str, Any]],
    fills: list[dict[str, Any]],
) -> list[Verdict]:
    """관측마다 세션 소유 최신 체결을 찾아 라벨을 매긴다."""
    owned: dict[UUID, list[dict[str, Any]]] = {}
    for fill in fills:
        key = fill["idempotency_key"] or ""
        match = _IDEM_SESSION_PATTERN.match(key)
        if match is None:
            continue  # 원장에 남았지만 세션 귀속 불가 — `unattributed` 의 원인이다
        owned.setdefault(UUID(match.group("session")), []).append(fill)

    verdicts: list[Verdict] = []
    for event in events:
        sess = sessions.get(event.session_id)
        if sess is None:
            raise ValueError(f"세션 행이 없다: {event.session_id}")
        interval_seconds = _INTERVAL_SECONDS[sess["interval"]]
        horizon = floor_to_interval(event.at, interval_seconds)

        candidates = [
            f
            for f in owned.get(event.session_id, [])
            if f["symbol"] == event.symbol and f["filled_at"] <= event.at
        ]
        last = candidates[-1] if candidates else None

        if last is None:
            label = "unattributed"
            threshold_label = "unattributed"
        else:
            label = "replay_lag" if last["filled_at"] >= horizon else "phantom"
            gap = (event.at - last["filled_at"]).total_seconds()
            threshold_label = "replay_lag" if gap < interval_seconds else "phantom"

        deactivated_at = sess["deactivated_at"]
        died_here = (
            sess["deactivated_reason"] == "position_divergence"
            and deactivated_at is not None
            and abs((deactivated_at - event.at).total_seconds()) <= 1.0
        )

        verdicts.append(
            Verdict(
                event=event,
                interval_seconds=interval_seconds,
                horizon=horizon,
                last_fill_at=last["filled_at"] if last else None,
                last_fill_side=last["side"] if last else None,
                last_fill_qty=str(last["quantity"]) if last else None,
                label=label,
                threshold_label=threshold_label,
                died_here=died_here,
            )
        )
    return verdicts


@dataclass
class Summary:
    """사망 상관 — 이 오라클의 유일한 독립 검사."""

    counts: dict[str, int] = field(default_factory=dict)
    deaths_total: int = 0
    deaths_labelled_phantom: int = 0
    replay_lag_total: int = 0
    replay_lag_survived: int = 0
    predicate_disagreements: int = 0

    @property
    def death_correlation_holds(self) -> bool:
        return (
            self.deaths_total == self.deaths_labelled_phantom
            and self.replay_lag_total == self.replay_lag_survived
        )


def summarize(verdicts: list[Verdict]) -> Summary:
    summary = Summary()
    for verdict in verdicts:
        summary.counts[verdict.label] = summary.counts.get(verdict.label, 0) + 1
        if verdict.label != verdict.threshold_label:
            summary.predicate_disagreements += 1
        if verdict.died_here:
            summary.deaths_total += 1
            if verdict.label == "phantom":
                summary.deaths_labelled_phantom += 1
        if verdict.label == "replay_lag":
            summary.replay_lag_total += 1
            if not verdict.died_here:
                summary.replay_lag_survived += 1
    return summary


def render(verdicts: list[Verdict], summary: Summary) -> str:
    out: list[str] = []
    header = (
        f"{'관측시각(UTC)':<26} {'세션':<9} {'엔진':>10} {'거래소':>8} "
        f"{'최근체결':<13} {'경과(s)':>10} {'라벨':<14} 사망"
    )
    out.append(header)
    out.append("-" * len(header))
    for verdict in verdicts:
        gap = verdict.gap_seconds
        out.append(
            f"{verdict.event.at.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]:<26} "
            f"{str(verdict.event.session_id)[:8]:<9} "
            f"{verdict.event.engine:>10.6f} {verdict.event.exchange:>8.3f} "
            f"{(verdict.last_fill_at.strftime('%m-%d %H:%M:%S') if verdict.last_fill_at else '-'):<13} "
            f"{(f'{gap:.2f}' if gap is not None else '-'):>10} "
            f"{verdict.label:<14} {'★' if verdict.died_here else ''}"
        )

    out.append("")
    out.append(
        f"관측 {len(verdicts)}건 — "
        + " · ".join(f"{label} {count}" for label, count in sorted(summary.counts.items()))
    )
    out.append(
        f"사망 상관 (독립 검사): 사망 {summary.deaths_total}건 중 "
        f"phantom 판정 {summary.deaths_labelled_phantom}건 · "
        f"replay_lag {summary.replay_lag_total}건 중 생존 {summary.replay_lag_survived}건"
    )
    out.append(
        f"봉경계식 vs 시간문턱식 불일치: {summary.predicate_disagreements}건"
        + ("" if summary.predicate_disagreements else " (이 창에서는 두 식이 같은 답을 낸다)")
    )
    out.append("")
    if summary.death_correlation_holds:
        out.append("✓ 사망 상관 성립 — 판별식이 독립 신호와 일치한다.")
    else:
        out.append("✗ 사망 상관 불성립 — 판별식을 기각하고 재설계해라.")
    out.append(
        "★적합은 검증이 아니다 — 판별식을 이 관측들에서 유도했다. 갚을 방법은 전향 예측뿐이다."
    )
    return "\n".join(out)


async def _run(args: argparse.Namespace, raw: str) -> int:
    events = parse_log(raw.splitlines(), category=args.category)
    if not events:
        print(f"category={args.category} 관측이 없다 — 로그 창을 확인해라.", file=sys.stderr)
        return 1

    if args.since is not None:
        cutoff = datetime.fromisoformat(args.since)
        events = [e for e in events if e.at >= cutoff]

    engine, sm = create_worker_engine_and_sm()
    try:
        sessions = await _load_sessions(sm, {e.session_id for e in events})
        fills = await _load_fills(sm, {e.symbol for e in events})
    finally:
        await engine.dispose()

    verdicts = adjudicate(events, sessions, fills)
    summary = summarize(verdicts)

    if args.json:
        print(
            json.dumps(
                {
                    "generated_at": datetime.now(UTC).isoformat(),
                    "verdicts": [v.as_dict() for v in verdicts],
                    "counts": summary.counts,
                    "deaths_total": summary.deaths_total,
                    "deaths_labelled_phantom": summary.deaths_labelled_phantom,
                    "replay_lag_total": summary.replay_lag_total,
                    "replay_lag_survived": summary.replay_lag_survived,
                    "predicate_disagreements": summary.predicate_disagreements,
                    "death_correlation_holds": summary.death_correlation_holds,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        print(render(verdicts, summary))

    return 0 if summary.death_correlation_holds else 2


def main() -> int:
    parser = argparse.ArgumentParser(
        description="`direction` 발산을 원장 체결 시각으로 replay_lag / phantom 재판정한다 ([BL-591])."
    )
    parser.add_argument("--log", help="워커 로그 파일 (기본: stdin)")
    parser.add_argument("--since", help="이 ISO 시각 이후 관측만 (예: 2026-08-03T09:53:00+00:00)")
    parser.add_argument(
        "--category", default="direction", help="재판정할 category (기본: direction)"
    )
    parser.add_argument("--json", action="store_true", help="기계용 JSON 출력")
    args = parser.parse_args()
    # 로그 읽기는 이벤트 루프 밖에서 한다 (ruff ASYNC240 — async 안의 blocking IO).
    raw = (
        Path(args.log).read_text(encoding="utf-8", errors="replace")
        if args.log
        else sys.stdin.read()
    )
    return asyncio.run(_run(args, raw))


if __name__ == "__main__":
    raise SystemExit(main())
