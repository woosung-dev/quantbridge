# `direction` 발산을 원장으로 재판정하는 오프라인 오라클 — 구현과 독립이어야 뜻이 있다
"""`direction` 포지션 발산을 `replay_lag` / `phantom` 으로 가른다 ([BL-591]).

## 왜 필요한가

`qb_live_position_divergence_total{category="direction"}` 은 **낫는 발산과 안 낫는 발산을
한 라벨에 묻는다**:

- **`replay_lag`** — 다음 조정 주기 안에 스스로 낫는다. 무해.
- **`phantom`** — 낫지 않으며 연속 2회 판정으로 세션을 죽인다. 치명.

현행 코드는 이 둘을 **「연속 2회 판정」이라는 타이밍 대리 지표**로만 가른다
(`live_signal.py:3309-3318`). 이 스크립트는 그 대리 지표 대신 **원장**으로 직접 판정해,
프로덕션에 라벨을 넣기 전에 판별식을 검증한다.

★★**「엔진이 앞선다 vs 거래소가 앞선다」로 갈리지 않는다 — 2026-08-05 반증.** 종전 문서는
`phantom` 을 「엔진 시뮬이 체결로 친 주문이 거래소에 아예 없다(엔진이 앞선다)」로 정의했다.
그런데 관측 **19건 전량**이 「크기 같고 부호 반대」인 **반전(side flip)** 이고, 사망 4건을
엔진의 영속 보고서로 부검하니 **방향이 갈렸다**:

- **엔진이 앞선 사망 3건** — `open_trades[].entry_bar` 가 창의 **마지막 봉**이다. 그중 2건은
  엔진의 `entry_price` 가 거래소 resting 주문의 트리거와 **센트 단위로 같다**
  (`64285.81`/트리거 `64285.80` · `63723.69`/`63723.60`) — 엔진만 그 주문을 체결로 쳤다.
- **거래소가 앞선 사망 1건**(`39731d57`) — 엔진 포지션이 두 tick 에서 **비트 단위로 동일**
  (`-0.029722343673419874`)하고 open trade 는 **19봉 전**에 개시됐다. 거래소의 stale stop
  (트리거 `64071.9`)이 혼자 발화했고 엔진은 끝내 안 따라왔다.

⇒ **뿌리는 방향이 아니다. 엔진의 시뮬 stop 과 거래소의 resting stop 이 서로 다른 주문**
(수준도 수명도 다름)**이고, 그래서 양쪽 모두 혼자 발화할 수 있다**는 것이다. 실측: 재발주
때마다 트리거가 평균 **62~271 USDT** 움직이는데 1분봉 range 는 **30~90** 이다.

## 판별식 — 「재무장 도장」 (2026-08-05 교체)

★**경과 시간은 교란변수였다.** 종전 봉경계식은 「마지막 체결로부터 봉 경계를 넘었는가」로
갈랐다. 그건 **얼마나 지났는가**를 묻는 것이고, 「60초면 엔진이 따라왔어야 한다」를 가정한다.
실측은 그 가정을 부순다 — tick 이 봉 마감 뒤 **10~15초**에 돌고, 조건부 주문의 재발주 주기는
**4~14분**이며, 재발주 때마다 트리거가 평균 **62~271 USDT** 움직인다(1분봉 range 는 30~90).
그래서 봉 하나로는 「조정이 끝났는가」를 판정할 수 없다.

대신 **시스템 자신의 조정 주기**를 쓴다. `conditional_entry_planner.py:502-589` 가

    quantity = |target_position - current_position|

로 수량을 정하고 `current_position` 은 **거래소 REST 읽기**(`live_signal.py:1517-1546`)다.
따라서 원장의 주문 한 행에서

    L      = ledger_net(order.created_at)          # 체결 원장의 부호 있는 순포지션
    target = L + (+qty if side == buy else -qty)   # 그 주문이 겨냥한 포지션

를 계산해 `L != 0` 이고 `sign(target) == -sign(L)` 이고 `|target| ~= |L|` 이면 그 주문은
**반전 주문**이다 — 곧 **파이프라인이 체결을 인지하고 반대편을 다시 무장했다**는 시각 도장이다.
이것을 **재무장 도장**이라 부른다.

관측 시각 `T`, 마지막 세션 소유 체결 `F`, 마지막 재무장 도장 `H` 에 대해

| 조건                | 라벨           | 뜻                                                                |
| ------------------- | -------------- | ----------------------------------------------------------------- |
| `H > F`             | **`phantom`**  | 체결 뒤 재무장을 **끝냈는데도** 어긋나 있다 ⇒ 조정 주기를 넘겼다 |
| `F >= H`            | `replay_lag`   | 마지막 재무장 **뒤에** 거래소가 움직였다 ⇒ 아직 판정할 때가 아니다 |
| 도장이 없다         | (봉경계식으로) | 재무장을 한 번도 못 봤다 — 아래 fallback                          |
| 세션 소유 체결 없음 | `unattributed` | 운영자 청산 등                                                    |

★★★**이건 인과 판정이 아니라 성숙도 프록시다 — 「누가 움직였나」를 말하지 않는다.**
초안에서는 「2배 수량 주문 = 그 순간 엔진과 거래소가 **합의**했다」고 적었는데 **반증됐다**:
`39731d57` 의 `16:24:11` 도장 시점에 엔진은 short(개시 봉 ~16:04), 거래소는 long(16:24:00
체결)으로 **어긋나 있었다**(`live_signal_states.last_strategy_state_report` 실측).
2배 수량은 **거래소 쪽만** 증언한다 — 엔진은 이미 그 방향을 들고 있어도 같은 `trade_id` 로
pending stop 을 다시 무장할 수 있기 때문이다(`strategy_state.py:728-740`).

★**누가 움직였는지의 인과 판정은 엔진의 영속 보고서로만 된다** —
`last_strategy_state_report.open_trades[].entry_bar` 가 창의 마지막 봉이면 그 tick 에 엔진이
움직인 것이다. 단 그 보고서는 **세션당 마지막 tick 한 벌**만 남으므로(같은 행을 덮어쓴다)
과거 관측 전량에는 적용할 수 없다. 그래서 게이트는 프록시를 쓴다.

★**도장이 없으면 종전 봉경계식으로 내려간다**(`horizon_label`). 도장은 「재무장했다」의
양성 증거이지 「어긋났다」의 증거가 아니므로, 증거가 없는 구간을 유령으로 접지 않는다.

★**`unattributed` 는 실재한다** — 운영자 청산 주문은 `idempotency_key` 가 비어 있어 어느
세션에도 귀속되지 않는다. 유령으로도 정상으로도 접지 않는다(`engine_only` 세분화 선례).

★**세션 귀속은 `idempotency_key` 로만 한다.** `trading.orders` 에는 `session_id` 가 없고,
계정으로 귀속하면 [BL-592] 의 `exchange_accounts` 2행 중복에 걸려 **3.7배 부풀려진다.**

## ★두 판별식 모두 한쪽으로만 틀린다 — `phantom` 은 믿을 수 있다

- **재무장식** — 도장은 양성 증거다. 반전 주문이 안 나간 구간에는 도장이 안 찍히므로 `H` 가
  과거에 머물고 라벨은 `replay_lag` 쪽으로 기운다 ⇒ **phantom 과소계상**.
- **봉경계식** — `Order.filled_at` 은 거래소 체결시각이 아니라 **우리 관측시각**이다
  (`order_repository.py:53,107,129,212` — 이름과 달리 terminal 시각). 우리 타임스탬프는
  항상 더 늦으므로 `t_fill >= horizon` 이 참으로 기운다 ⇒ **phantom 과소계상**.

⇒ **`phantom` 라벨은 믿을 수 있다** — 이 방향의 오차는 **거짓 사망을 만들지 않는다.**
반대로 「`replay_lag` 이니 무해」는 그만큼 믿을 수 없다. 봉경계식의 실측 최소 여유는
**0.652초**(2026-08-03 23:17)로 경계는 실제로 붙는다.

★**재무장식이 거짓 `phantom` 을 내려면** 마지막 도장 뒤에 **우리 원장에 없는 반전**이
거래소에서 일어나야 한다. 운영자 청산은 포지션을 0 으로 만들 뿐이라 `direction` 이 아니라
`exchange_only`/`engine_only` 로 분류되므로 이 경로가 아니다. 남는 것은 **같은 계정을 쓰는
다른 전략의 반전**이고, 그건 [BL-592] 축의 별개 결함이다.

## ★이 오라클이 증명하는 것과 못 하는 것

판별식을 관측에서 **유도**했으므로 같은 관측에 잘 맞는 것은 검증이 아니다. 독립적인
검사는 **사망 상관** 하나뿐이다 — 사망은 「연속 2회 판정」으로 정해지고 체결 경과시간·주문
수량과 **무관하게** 결정되므로, `phantom` 이 사망과 일치하면 서로 다른 두 신호가 만난 것이다.
나머지는 **전향 예측**으로만 갚을 수 있다.

★검증이 하나 더 있다 — 이 규칙은 **2026-08-04 15:51 이후 관측 8건**에서 유도했는데, 그 앞
창의 **11건**(`.soak/direction-classification-20260804T0630Z.json`)에서는 봉경계식과
**11/11 일치**한다. 그 11건은 out-of-sample 이다.

★그리고 **아니라고 말할 수 있는 것도 재봤다**(2026-08-05) — 엔진이 재생하는 봉(`CCXTProvider`
perp) · 내가 잰 공개 perp · **데모** perp 가 사망 4건의 해당 봉에서 **소수점까지 동일**했다.
스팟만 27~36 USDT 떨어져 있고 체결 조건을 4/4 불만족(BL-530 수리가 유지되고 있다).
⇒ **가격 소스 불일치도, 1분 타이밍도 이 발산의 원인이 아니다.**

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
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
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

# ★판별식의 판(版). `--json` 출력과 `.soak/phantom-*.json` 아카이브에 함께 실린다.
#
# 왜 필요한가 — `scripts/soak-gate.sh` 는 **모든** 아카이브의 verdict 를 합집합으로 모으고
# `(시각, 종류, 상세)` 로 dedup 한다. 그래서 **판별식을 개선해 `phantom` 을 하나 취소해도
# 옛 아카이브의 그 라벨이 영원히 남는다** — 실측 2026-08-05: 교체 후 게이트가 여전히
# `phantom` 7건을 보고했고 그중 4건은 새 분류기가 이미 `replay_lag` 으로 판정한 것이었다.
# 방향은 fail-closed(과도하게 엄격) 지만, **개선이 게이트에 반영되지 않는다**는 뜻이다.
# ⇒ 판을 올리면 옛 아카이브를 `.soak/superseded-<판>/` 로 옮긴다([ADR-024] §아카이브 판).
PREDICATE_VERSION = "2026-08-05-rearm"

# 반전 주문 판정의 상대 허용오차. 반전 수량은 `|target - current|` 이고 current 는 거래소가
# 수량 스텝(BTC linear = 0.001)으로 양자화한 값이라 `|target|` 과 정확히 같지 않다 — 실측
# `L=+0.030` 에 `sell 0.059` → `target=-0.029` (3.3% 차). 프로덕션이 같은 이유로 쓰는
# `_POSITION_SIZE_REL_TOL`(`live_signal.py:238`)과 같은 5% 를 쓴다. 진짜 부분청산(실측
# 0.001 vs 0.029 = 96.5% 차)과는 여전히 멀리 떨어져 있다.
_REVERSAL_REL_TOL = Decimal("0.05")

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
    """한 관측의 재판정 결과.

    라벨이 넷이다 — **셋을 병기하고 하나를 채택한다.** 지우면 두 식이 언제 갈리는지 보이지
    않는다(2026-08-05 교체에서 실제로 4건이 갈렸다).

    - `label` — **채택**. 재무장식이 판정하면 그것, 아니면 `horizon_label`.
    - `rearm_label` — 재무장 도장식. 도장이 없으면 `None`(판정 안 함).
    - `horizon_label` — 종전 봉경계식(`t_fill >= floor(관측시각, interval)`).
    - `threshold_label` — 시간문턱식(`경과 < interval`). 참고용 — 채택된 적 없다.
    """

    event: DivergenceEvent
    interval_seconds: int
    horizon: datetime
    last_fill_at: datetime | None
    last_fill_side: str | None
    last_fill_qty: str | None
    last_rearm_at: datetime | None
    label: str
    rearm_label: str | None
    horizon_label: str
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
            "last_rearm_at": (self.last_rearm_at.isoformat() if self.last_rearm_at else None),
            "gap_seconds": self.gap_seconds,
            "horizon": self.horizon.isoformat(),
            "label": self.label,
            "rearm_label": self.rearm_label,
            "horizon_label": self.horizon_label,
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


async def _load_orders(sm: Any, symbols: set[str]) -> list[dict[str, Any]]:
    """창 안의 주문을 **상태 불문** 통째로 읽어 파이썬에서 세션 귀속한다.

    ★`state = 'filled'` 로 좁히지 않는다 — 합의 하트비트는 **취소·거절된 주문의 수량**도
    쓴다(수량은 발주 시점에 계산되므로 그 뒤의 운명과 무관하게 그 시점을 증언한다).
    실측 사망 4건 중 3건의 결정적 하트비트가 **끝내 체결되지 않은 주문**이었다.

    SQL 로 `idempotency_key LIKE 'live:<uuid>:%'` 를 세션마다 돌리는 것보다 왕복이 적고,
    귀속 규칙이 한곳(`_IDEM_SESSION_PATTERN`)에만 있게 된다.
    """
    if not symbols:
        return []
    async with sm() as db:
        rows = await db.execute(
            text(
                "SELECT created_at, filled_at, state::text AS state, symbol, "
                "       side::text AS side, quantity, filled_quantity, idempotency_key "
                "FROM trading.orders "
                "WHERE symbol = ANY(:symbols) "
                "ORDER BY created_at"
            ),
            {"symbols": list(symbols)},
        )
        return [dict(row._mapping) for row in rows]


# --- 합의 하트비트 (원장만 쓰는 순수 함수) --------------------------------------


def signed_quantity(order: dict[str, Any]) -> Decimal:
    """이 주문이 **겨냥한** 방향·크기. buy 는 +, sell 은 -.

    ★`quantity`(요청량)다 — 재무장 도장은 **무엇을 주문했나**를 묻지 무엇이 체결됐나를
    묻지 않는다. 원장 순포지션은 `signed_fill` 이 따로 계산한다.
    """
    qty = Decimal(str(order["quantity"]))
    return qty if str(order["side"]) == "buy" else -qty


def is_filled(order: dict[str, Any]) -> bool:
    """이 행이 **실제로 포지션을 만들었나.**

    ★★★**`state == 'filled'` 로 판정하면 안 된다 — 레포 정본이 이미 그렇게 적고 있다**
    (`entry_completeness.attempt_has_fill`): `transition_to_cancelled`/`_rejected` 는
    `filled_quantity` 가 0 이 아니면 체결분을 **보존한 채** 종결하므로 거래소에는 포지션이
    남았는데 상태가 `cancelled` 인 행이 실재한다. 반대로 `filled` 인데 `filled_quantity` 가
    NULL 이면 **판독 불가**이지 전량 체결이 아니다. ⇒ 판정은 **`filled_quantity > 0`** 이다.
    (codex challenge 2026-08-05 적발 — 나는 `state == 'filled'` 로 짰다.)

    ★★그리고 `filled_at IS NOT NULL` 로도 판정하면 안 된다 — 이 컬럼은 이름과 달리
    **terminal 시각**이라 취소·거절에도 채워진다(`order_repository.py:53,107,129,212`).
    실측: 상태 필터를 빼고 원장을 읽자 취소 주문 12건이 체결로 섞여 순포지션이 망가지고
    재무장 도장이 **전건 소실**됐다.

    ★`filled_quantity` 키가 없는 입력(`state` 도 없는 단위 테스트 픽스처)은 호출자가 이미
    체결만 걸러 넘긴 것으로 보고 `quantity` 를 쓴다.
    """
    if order.get("filled_at") is None:
        return False
    if "filled_quantity" in order:
        raw = order["filled_quantity"]
        return raw is not None and Decimal(str(raw)) > 0
    # `filled_quantity` 를 아예 싣지 않는 호출자(단위 테스트 픽스처)는 상태로 판정한다.
    # ★프로덕션 로더는 이제 그 컬럼을 **항상** 싣는다 — 이 갈래로 내려오지 않는다.
    return str(order.get("state", "filled")) == "filled"


def signed_fill(order: dict[str, Any]) -> Decimal:
    """이 주문이 **실제로 움직인** 포지션. 체결분이 없으면 0.

    ★`quantity` 가 아니라 `filled_quantity` 다 — 부분체결이면 요청량과 다르다.
    전체 원장 실측 2026-08-05: `filled` **202행 중 65행**이 `filled_quantity <> quantity` 다
    (단 이 회차 코퍼스 6세션 43행에서는 **0건**이라 19건 판정은 안 바뀐다).
    """
    if not is_filled(order):
        return Decimal("0")
    raw = order.get("filled_quantity")
    if raw is None:
        raw = order["quantity"]
    qty = Decimal(str(raw))
    return qty if str(order["side"]) == "buy" else -qty


def ledger_net_at(
    orders: Sequence[dict[str, Any]], at: datetime, *, exclude: dict[str, Any] | None = None
) -> Decimal:
    """`at` 시점까지 실제로 체결된 분의 부호 있는 순포지션.

    ★`exclude` 는 **자기 자신**을 빼기 위한 것이다 — 시장가 주문은 생성과 terminal 기록이
    같은 시각으로 찍힐 수 있고, 그러면 `filled_at <= created_at` 이 참이 되어 **자기 체결을
    자기 발주 전 원장에 포함**한다(codex challenge 2026-08-05 적발 · 프로덕션 미관측).
    """
    net = Decimal("0")
    for order in orders:
        if exclude is not None and order is exclude:
            continue
        if is_filled(order) and order["filled_at"] <= at:
            net += signed_fill(order)
    return net


def is_rearm_stamp(order: dict[str, Any], ledger_before: Decimal) -> bool:
    """이 주문이 **체결 인지 후 재무장을 끝냈다**는 증거인가.

    반전 주문이면 참이다 — `quantity = |target - current|` 에서 `current` 는 거래소 읽기이므로
    `target` 이 `ledger_before` 의 반대편에 같은 크기로 있다는 것은 **계획기가 그 체결을
    반영한 뒤 반대편을 다시 무장했다**는 뜻이다.

    ★★**엔진의 포지션은 증언하지 않는다.** 초안은 「그러므로 엔진도 같은 쪽에 있었다」고
    적었는데 반증됐다 — 엔진은 이미 그 방향을 들고 있어도 같은 `trade_id` 로 pending stop 을
    다시 무장할 수 있다(`strategy_state.py:728-740`). 실측 `39731d57` `16:24:11`: 엔진 short ·
    거래소 long 인데 이 함수는 참을 낸다. 모듈 docstring §판별식 참조.

    거짓이 되는 경우 — 최초 진입(`ledger_before == 0`) · 크기보정 주문(실측 `0.001`,
    부호가 안 바뀐다) · 부분청산.
    """
    if ledger_before == 0:
        return False
    target = ledger_before + signed_quantity(order)
    if target == 0:
        return False
    if (target > 0) == (ledger_before > 0):
        return False  # 부호가 안 바뀌었다 — 반전이 아니다
    magnitude, before = abs(target), abs(ledger_before)
    return abs(magnitude - before) <= _REVERSAL_REL_TOL * max(magnitude, before)


def find_rearm_stamps(orders: Sequence[dict[str, Any]]) -> list[datetime]:
    """한 (세션, 심볼) 의 주문 흐름에서 재무장 도장 시각을 뽑는다.

    ★`created_at` 이 없는 행은 도장이 될 수 없다 — 발주 시각을 모르면 「그 순간」을
    증언할 수 없다. 조용히 지금으로 치지 않는다.

    ★`exclude=order` — 자기 체결을 자기 발주 전 원장에 넣지 않는다(위 `ledger_net_at`).
    """
    stamps: list[datetime] = []
    for order in orders:
        created_at = order.get("created_at")
        if created_at is None:
            continue
        if is_rearm_stamp(order, ledger_net_at(orders, created_at, exclude=order)):
            stamps.append(created_at)
    return sorted(stamps)


def adjudicate(
    events: list[DivergenceEvent],
    sessions: dict[UUID, dict[str, Any]],
    orders: list[dict[str, Any]],
) -> list[Verdict]:
    """관측마다 세션 소유 최신 체결·최신 하트비트를 찾아 라벨을 매긴다."""
    owned: dict[UUID, list[dict[str, Any]]] = {}
    for order in orders:
        key = order["idempotency_key"] or ""
        match = _IDEM_SESSION_PATTERN.match(key)
        if match is None:
            continue  # 원장에 남았지만 세션 귀속 불가 — `unattributed` 의 원인이다
        owned.setdefault(UUID(match.group("session")), []).append(order)

    # (세션, 심볼) 별 하트비트는 관측과 무관하므로 한 번만 계산한다.
    rearm_index: dict[tuple[UUID, str], list[datetime]] = {}
    for session_id, session_orders in owned.items():
        for symbol in {str(o["symbol"]) for o in session_orders}:
            rearm_index[(session_id, symbol)] = find_rearm_stamps(
                [o for o in session_orders if str(o["symbol"]) == symbol]
            )

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
            if f["symbol"] == event.symbol and is_filled(f) and f["filled_at"] <= event.at
        ]
        # ★`[-1]` 이 아니라 `max` 다 — SQL 이 `ORDER BY` 로 주지만 그건 호출자의
        # 사정이고, 정렬을 암묵 계약으로 두면 순서가 흐트러졌을 때 **갈래가 조용히 뒤집힌다**
        # (오래된 체결을 집으면 무해가 유령이 된다). 단위 테스트가 이걸 잡았다.
        last = max(candidates, key=lambda f: f["filled_at"]) if candidates else None

        stamps = [h for h in rearm_index.get((event.session_id, event.symbol), []) if h <= event.at]
        last_rearm = max(stamps) if stamps else None

        if last is None:
            label = rearm_label = horizon_label = threshold_label = "unattributed"
        else:
            horizon_label = "replay_lag" if last["filled_at"] >= horizon else "phantom"
            gap = (event.at - last["filled_at"]).total_seconds()
            threshold_label = "replay_lag" if gap < interval_seconds else "phantom"
            if last_rearm is None:
                # 재무장을 한 번도 못 봤다 — 재무장식은 판정하지 않고,
                # 종전 봉경계식으로 내려간다(증거 부재를 유령으로 접지 않는다).
                rearm_label = None
                label = horizon_label
            else:
                rearm_label = "phantom" if last_rearm > last["filled_at"] else "replay_lag"
                label = rearm_label

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
                last_rearm_at=last_rearm,
                label=label,
                rearm_label=rearm_label,
                horizon_label=horizon_label,
                threshold_label=threshold_label,
                died_here=died_here,
            )
        )
    return verdicts


@dataclass
class Summary:
    """사망 상관 — 이 오라클의 유일한 독립 검사."""

    counts: dict[str, int] = field(default_factory=dict)
    horizon_counts: dict[str, int] = field(default_factory=dict)
    deaths_total: int = 0
    deaths_labelled_phantom: int = 0
    replay_lag_total: int = 0
    replay_lag_survived: int = 0
    predicate_disagreements: int = 0
    rearm_overrides: int = 0
    rearm_undecided: int = 0

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
        summary.horizon_counts[verdict.horizon_label] = (
            summary.horizon_counts.get(verdict.horizon_label, 0) + 1
        )
        # ★두 식의 불일치는 **봉경계식 vs 시간문턱식** 이다 — 채택 라벨과 비교하면
        #   재무장식 교체가 이 숫자에 섞여 들어와 옛 관측과 비교할 수 없게 된다.
        if verdict.horizon_label != verdict.threshold_label:
            summary.predicate_disagreements += 1
        if verdict.rearm_label is None:
            summary.rearm_undecided += 1
        elif verdict.rearm_label != verdict.horizon_label:
            summary.rearm_overrides += 1
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
        f"{'최근체결':<13} {'최근재무장':<13} {'경과(s)':>10} {'라벨':<12} {'봉경계식':<12} 사망"
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
            f"{(verdict.last_rearm_at.strftime('%m-%d %H:%M:%S') if verdict.last_rearm_at else '-'):<13} "
            f"{(f'{gap:.2f}' if gap is not None else '-'):>10} "
            f"{verdict.label:<12} {verdict.horizon_label:<12} {'★' if verdict.died_here else ''}"
        )

    out.append("")
    out.append(
        f"관측 {len(verdicts)}건 — "
        + " · ".join(f"{label} {count}" for label, count in sorted(summary.counts.items()))
    )
    out.append(
        "  (종전 봉경계식이라면 — "
        + " · ".join(f"{label} {count}" for label, count in sorted(summary.horizon_counts.items()))
        + f"; 재무장식이 뒤집은 관측 {summary.rearm_overrides}건 · "
        f"도장 없어 봉경계식으로 내려간 관측 {summary.rearm_undecided}건)"
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


def parse_events_json(blob: dict[str, Any], symbols: dict[UUID, str]) -> list[DivergenceEvent]:
    """이전 `--json` 출력(또는 `.soak/phantom-*.json` 아카이브)에서 관측을 되살린다.

    ★**워커 로그는 컨테이너 수명에 묶인다** — 재기동한 창의 관측은 로그로 다시 읽을 수 없고
    아카이브에만 남는다. 판별식을 바꿀 때 **과거 관측 전량에 재적용**하려면 그 아카이브를
    입력으로 받을 수 있어야 한다(그게 없으면 「바꾸기 전에 과거에 적용했다」를 못 한다).

    `symbol` 은 아카이브에 없으므로 **세션 행에서 가져온다** — 추측하지 않는다.
    """
    events: list[DivergenceEvent] = []
    for entry in blob.get("verdicts", []):
        session_id = UUID(str(entry["session_id"]))
        symbol = symbols.get(session_id)
        if symbol is None:
            raise ValueError(f"세션 행이 없다: {session_id}")
        events.append(
            DivergenceEvent(
                at=datetime.fromisoformat(str(entry["at"])),
                session_id=session_id,
                symbol=symbol,
                category="direction",
                # ★게이트 아카이브(`.soak/phantom-*.json`)는 `engine`/`exchange` 를
                #   **버린다** — `{at, label, session_id}` 만 싣는다. 필수로 읽으면
                #   그 아카이브를 재판정할 수 없다(codex challenge 2026-08-05: KeyError
                #   재현). 라벨은 이 두 값에 의존하지 않으므로(전용 테스트로 고정)
                #   없으면 0 으로 둔다 — 표시에만 쓰인다.
                engine=float(entry.get("engine", 0.0)),
                exchange=float(entry.get("exchange", 0.0)),
            )
        )
    return sorted(events, key=lambda e: e.at)


async def _run(args: argparse.Namespace, raw: str) -> int:
    # 아카이브 입력은 심볼을 안 담으므로 세션 행을 먼저 읽어야 관측을 만들 수 있다.
    # 로그 입력은 반대로 관측을 먼저 만들어야 세션 목록을 안다. 두 경로가 만나는 지점이
    # `events` 이고, 그 전까지는 세션 id 집합만 공유한다.
    archive: dict[str, Any] | None = None
    log_events: list[DivergenceEvent] = []
    if args.events_json is not None:
        archive = json.loads(raw)
        if not archive.get("verdicts"):
            print(f"{args.events_json} 에 관측이 없다.", file=sys.stderr)
            return 1
        session_ids = {UUID(str(v["session_id"])) for v in archive["verdicts"]}
    else:
        log_events = parse_log(raw.splitlines(), category=args.category)
        if not log_events:
            print(f"category={args.category} 관측이 없다 — 로그 창을 확인해라.", file=sys.stderr)
            return 1
        session_ids = {e.session_id for e in log_events}

    engine, sm = create_worker_engine_and_sm()
    try:
        sessions = await _load_sessions(sm, session_ids)
        events = (
            parse_events_json(archive, {sid: str(row["symbol"]) for sid, row in sessions.items()})
            if archive is not None
            else log_events
        )
        orders = await _load_orders(sm, {e.symbol for e in events})
    finally:
        await engine.dispose()

    if args.since is not None:
        cutoff = datetime.fromisoformat(args.since)
        events = [e for e in events if e.at >= cutoff]
        if not events:
            print(f"--since {args.since} 뒤에 관측이 없다.", file=sys.stderr)
            return 1

    verdicts = adjudicate(events, sessions, orders)
    summary = summarize(verdicts)

    if args.json:
        print(
            json.dumps(
                {
                    "generated_at": datetime.now(UTC).isoformat(),
                    "predicate_version": PREDICATE_VERSION,
                    "verdicts": [v.as_dict() for v in verdicts],
                    "counts": summary.counts,
                    "horizon_counts": summary.horizon_counts,
                    "rearm_overrides": summary.rearm_overrides,
                    "rearm_undecided": summary.rearm_undecided,
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
    parser.add_argument(
        "--events-json",
        help="이전 --json 출력 / .soak 아카이브에서 관측을 되살려 재판정 (로그 대신)",
    )
    parser.add_argument("--since", help="이 ISO 시각 이후 관측만 (예: 2026-08-03T09:53:00+00:00)")
    parser.add_argument(
        "--category", default="direction", help="재판정할 category (기본: direction)"
    )
    parser.add_argument("--json", action="store_true", help="기계용 JSON 출력")
    args = parser.parse_args()
    # 파일 읽기는 이벤트 루프 밖에서 한다 (ruff ASYNC240 — async 안의 blocking IO).
    if args.events_json:
        raw = Path(args.events_json).read_text(encoding="utf-8")
    elif args.log:
        raw = Path(args.log).read_text(encoding="utf-8", errors="replace")
    else:
        raw = sys.stdin.read()
    return asyncio.run(_run(args, raw))


if __name__ == "__main__":
    raise SystemExit(main())
