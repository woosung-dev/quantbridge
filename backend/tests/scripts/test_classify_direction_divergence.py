"""`direction` 발산 판별식의 경계 동작을 못박는다 ([BL-591] 슬라이스 A 선행).

## 왜 지금 쓰나

판별식은 프로덕션 관측 **11건**에서 유도됐고 그 11건에 100% 맞는다. 그런데 **적합은 검증이
아니다** — 11건은 전부 `1m` 단일 심볼이고, 경계(`t_fill == horizon`)·`unattributed`·
세션 오귀속은 **한 번도 밟히지 않았다.** 슬라이스 A 가 이 술어를 `live_signal.py` 로 옮길 때
그 미검증 경계가 그대로 따라간다.

여기서 경계를 고정해 두면 포팅이 **설계가 아니라 전사(轉寫)** 가 된다.

★**이 테스트는 DB 픽스처를 쓰지 않는다** — `conftest._test_engine` 은 session-scoped 이고
autouse 가 아니므로 `drop_all` 이 돌지 않는다. 소크가 살아 있어도 안전하다.
"""

from __future__ import annotations

import importlib.util
import sys
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import UUID

import pytest

SESSION_A = UUID("aaaaaaaa-0000-4000-8000-000000000001")
SESSION_B = UUID("bbbbbbbb-0000-4000-8000-000000000002")


def _load_module() -> Any:
    """오라클 스크립트 동적 import (`sys.path` 오염 회피 — tests/scripts 선례)."""
    script_path = Path(__file__).parents[2] / "scripts" / "classify_direction_divergence.py"
    spec = importlib.util.spec_from_file_location("classify_direction_divergence", script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    # ★`sys.modules` 등록이 필수다 — 스크립트가 `from __future__ import annotations` +
    # `@dataclass` 라, dataclasses 가 `sys.modules[cls.__module__].__dict__` 로 타입을
    # 되짚는다. 등록 없이 `exec_module` 하면 `AttributeError: 'NoneType'` 으로 죽는다.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def oracle() -> Any:
    return _load_module()


def _session(
    *,
    interval: str = "1m",
    deactivated_at: datetime | None = None,
    deactivated_reason: str | None = None,
) -> dict[str, Any]:
    return {
        "interval": interval,
        "symbol": "BTC/USDT",
        "deactivated_at": deactivated_at,
        "deactivated_reason": deactivated_reason,
    }


def _fill(
    at: datetime, *, session_id: UUID | None = SESSION_A, symbol: str = "BTC/USDT"
) -> dict[str, Any]:
    key = f"live:{session_id}:cond:x" if session_id is not None else None
    return {
        "filled_at": at,
        "symbol": symbol,
        "side": "buy",
        "quantity": "0.058",
        "idempotency_key": key,
    }


def _event(oracle: Any, at: datetime, *, session_id: UUID = SESSION_A) -> Any:
    return oracle.DivergenceEvent(
        at=at,
        session_id=session_id,
        symbol="BTC/USDT",
        category="direction",
        engine=-0.0298,
        exchange=0.029,
    )


def _adjudicate(
    oracle: Any,
    events: list[Any],
    sessions: dict[UUID, dict[str, Any]],
    orders: list[dict[str, Any]],
    *,
    corpus_end: datetime | None = None,
) -> list[Any]:
    """`corpus_end` 기본값 = **마지막 관측 시각** = 로그가 거기서 끝났다.

    ★기본값이 「끝났다」인 것은 의도다. 그러면 회복식이 판정 불가가 되어 종전 식으로
    내려가므로, 아래 legacy 경계 테스트들이 **재무장식·봉경계식을 그대로** 검사한다.
    회복식 자체를 검사하는 테스트는 `corpus_end` 를 **명시**한다 — 그게 그 테스트가
    무엇을 보는지 드러내는 유일한 방법이다.
    """
    return list(
        oracle.adjudicate(
            events,
            sessions,
            orders,
            corpus_end=corpus_end if corpus_end is not None else max(e.at for e in events),
        )
    )


# --- floor_to_interval ---------------------------------------------------------


def test_floor_to_interval_is_the_engine_visibility_horizon(oracle: Any) -> None:
    """`horizon = floor(평가시각, interval)` — `ccxt.py:145` 의 `last_closed_ts + tf` 와 같다."""
    at = datetime(2026, 8, 4, 4, 17, 8, 667000, tzinfo=UTC)
    assert oracle.floor_to_interval(at, 60) == datetime(2026, 8, 4, 4, 17, tzinfo=UTC)
    assert oracle.floor_to_interval(at, 300) == datetime(2026, 8, 4, 4, 15, tzinfo=UTC)
    assert oracle.floor_to_interval(at, 3600) == datetime(2026, 8, 4, 4, 0, tzinfo=UTC)


def test_floor_to_interval_is_idempotent_on_a_boundary(oracle: Any) -> None:
    exact = datetime(2026, 8, 4, 4, 17, tzinfo=UTC)
    assert oracle.floor_to_interval(exact, 60) == exact


# --- 두 갈래 기본 동작 ---------------------------------------------------------


def test_fill_inside_the_forming_bar_is_replay_lag(oracle: Any) -> None:
    """실측 `04:17:08` 재현 — 체결이 봉 마감 뒤면 엔진은 아직 못 봤다."""
    at = datetime(2026, 8, 4, 4, 17, 8, 667000, tzinfo=UTC)
    fill_at = datetime(2026, 8, 4, 4, 17, 8, 79000, tzinfo=UTC)

    (verdict,) = _adjudicate(
        oracle, [_event(oracle, at)], {SESSION_A: _session()}, [_fill(fill_at)]
    )

    assert verdict.label == "replay_lag"
    assert verdict.gap_seconds == pytest.approx(0.588, abs=0.001)


def test_fill_before_the_horizon_is_phantom(oracle: Any) -> None:
    """실측 `15:53:34` 재현 — 엔진이 봉을 여러 개 보고도 어긋나 있다."""
    at = datetime(2026, 8, 3, 15, 53, 34, 291000, tzinfo=UTC)
    fill_at = datetime(2026, 8, 3, 15, 38, 24, 625000, tzinfo=UTC)

    (verdict,) = _adjudicate(
        oracle, [_event(oracle, at)], {SESSION_A: _session()}, [_fill(fill_at)]
    )

    assert verdict.label == "phantom"


# --- ★경계: 실측 최소 여유가 0.652초였다 --------------------------------------


def test_fill_exactly_at_the_horizon_is_replay_lag(oracle: Any) -> None:
    """`t_fill == horizon` 은 **무해** 쪽이다 (`>=` 이 포함).

    ★실측 최소 여유가 **0.652초**(2026-08-03 23:17)라 이 경계는 실제로 붙는다.
    부등호를 `>` 로 바꾸면 무해가 유령으로 뒤집혀 **거짓 사망**이 된다.
    """
    at = datetime(2026, 8, 3, 23, 17, 21, 979000, tzinfo=UTC)
    horizon = datetime(2026, 8, 3, 23, 17, tzinfo=UTC)

    (verdict,) = _adjudicate(
        oracle, [_event(oracle, at)], {SESSION_A: _session()}, [_fill(horizon)]
    )

    assert verdict.horizon == horizon
    assert verdict.label == "replay_lag"


def test_one_microsecond_before_the_horizon_is_phantom(oracle: Any) -> None:
    """경계 바로 아래는 유령 — 엔진이 그 봉을 이미 재생했다."""
    at = datetime(2026, 8, 3, 23, 17, 21, 979000, tzinfo=UTC)
    fill_at = datetime(2026, 8, 3, 23, 16, 59, 999999, tzinfo=UTC)

    (verdict,) = _adjudicate(
        oracle, [_event(oracle, at)], {SESSION_A: _session()}, [_fill(fill_at)]
    )

    assert verdict.label == "phantom"


def test_bar_boundary_and_time_threshold_disagree_below_the_horizon(oracle: Any) -> None:
    """★두 술어는 **동치가 아니다** — 실측 11건에서 우연히 일치했을 뿐이다.

    체결이 60초 안(경과 46초)이지만 봉 경계 **아래**면 엔진은 그 봉을 이미 봤다.
    ⇒ 봉경계식 `phantom` vs 시간문턱식 `replay_lag`. 시간문턱식이 유령을 놓친다.
    """
    at = datetime(2026, 8, 3, 10, 12, 36, tzinfo=UTC)
    fill_at = datetime(2026, 8, 3, 10, 11, 50, tzinfo=UTC)

    (verdict,) = _adjudicate(
        oracle, [_event(oracle, at)], {SESSION_A: _session()}, [_fill(fill_at)]
    )

    assert verdict.gap_seconds == pytest.approx(46.0)
    assert verdict.label == "phantom"
    assert verdict.threshold_label == "replay_lag"
    assert oracle.summarize([verdict]).predicate_disagreements == 1


# --- 귀속 (★[BL-592] 계정 중복에 걸리지 않는 유일한 이유) ----------------------


def test_operator_flatten_without_idempotency_key_is_unattributed(oracle: Any) -> None:
    """운영자 청산 주문은 `idempotency_key` 가 없다 — 유령으로도 정상으로도 접지 않는다.

    실측 `2026-08-04 01:39:14` 의 `reduce_only` 주문이 이 경우다.
    """
    at = datetime(2026, 8, 4, 1, 40, tzinfo=UTC)
    fill_at = datetime(2026, 8, 4, 1, 39, 14, tzinfo=UTC)

    (verdict,) = _adjudicate(
        oracle, [_event(oracle, at)], {SESSION_A: _session()}, [_fill(fill_at, session_id=None)]
    )

    assert verdict.label == "unattributed"
    assert verdict.last_fill_at is None


def test_another_sessions_fill_is_not_attributed(oracle: Any) -> None:
    """세션 귀속은 `idempotency_key` 로만 한다 — 다른 세션의 체결을 빌려오지 않는다."""
    at = datetime(2026, 8, 4, 4, 17, 8, 667000, tzinfo=UTC)
    fill_at = datetime(2026, 8, 4, 4, 17, 8, 79000, tzinfo=UTC)

    (verdict,) = _adjudicate(
        oracle,
        [_event(oracle, at)],
        {SESSION_A: _session()},
        [_fill(fill_at, session_id=SESSION_B)],
    )

    assert verdict.label == "unattributed"


def test_fill_on_another_symbol_is_not_attributed(oracle: Any) -> None:
    at = datetime(2026, 8, 4, 4, 17, 8, 667000, tzinfo=UTC)
    fill_at = datetime(2026, 8, 4, 4, 17, 8, 79000, tzinfo=UTC)

    (verdict,) = _adjudicate(
        oracle,
        [_event(oracle, at)],
        {SESSION_A: _session()},
        [_fill(fill_at, symbol="ETH/USDT")],
    )

    assert verdict.label == "unattributed"


def test_fill_after_the_observation_is_ignored(oracle: Any) -> None:
    """관측 뒤에 난 체결로 과거를 판정하지 않는다."""
    at = datetime(2026, 8, 4, 4, 17, 8, tzinfo=UTC)

    (verdict,) = _adjudicate(
        oracle,
        [_event(oracle, at)],
        {SESSION_A: _session()},
        [_fill(datetime(2026, 8, 4, 4, 17, 30, tzinfo=UTC))],
    )

    assert verdict.label == "unattributed"


def test_latest_fill_wins_regardless_of_input_order(oracle: Any) -> None:
    """★입력 정렬에 의존하지 않는다 — SQL 이 정렬해 주지만 계약으로 못박는다."""
    at = datetime(2026, 8, 4, 4, 17, 8, 667000, tzinfo=UTC)
    early = _fill(datetime(2026, 8, 4, 3, 54, 44, tzinfo=UTC))  # horizon 아래 → phantom
    late = _fill(datetime(2026, 8, 4, 4, 17, 8, 79000, tzinfo=UTC))  # 봉 안 → replay_lag

    (verdict,) = _adjudicate(oracle, [_event(oracle, at)], {SESSION_A: _session()}, [late, early])

    assert verdict.last_fill_at == late["filled_at"]
    assert verdict.label == "replay_lag"


# --- interval 일반화 (실측은 전부 1m 이었다) -----------------------------------


def test_horizon_follows_the_session_interval(oracle: Any) -> None:
    """5m 세션에서는 5분 봉이 지평이다 — 1m 기준으로 판정하면 유령을 놓친다."""
    at = datetime(2026, 8, 4, 4, 17, 8, tzinfo=UTC)
    fill_at = datetime(2026, 8, 4, 4, 16, tzinfo=UTC)

    (one_minute,) = _adjudicate(
        oracle, [_event(oracle, at)], {SESSION_A: _session(interval="1m")}, [_fill(fill_at)]
    )
    (five_minute,) = _adjudicate(
        oracle, [_event(oracle, at)], {SESSION_A: _session(interval="5m")}, [_fill(fill_at)]
    )

    assert one_minute.label == "phantom"  # horizon 04:17 > 04:16
    assert five_minute.label == "replay_lag"  # horizon 04:15 <= 04:16


# --- 사망 상관 (오라클의 유일한 독립 검사) ------------------------------------


def test_death_is_attributed_only_to_the_observation_at_the_deactivation(oracle: Any) -> None:
    """사망 표시는 `deactivated_at` 과 1초 안에서만 붙는다 — 쌍의 첫 관측은 생존이다."""
    first = datetime(2026, 8, 3, 15, 53, 34, 291000, tzinfo=UTC)
    second = datetime(2026, 8, 3, 15, 54, 34, 409000, tzinfo=UTC)
    sess = _session(deactivated_at=second, deactivated_reason="position_divergence")
    fill_at = datetime(2026, 8, 3, 15, 38, 24, 625000, tzinfo=UTC)

    verdicts = _adjudicate(
        oracle,
        [_event(oracle, first), _event(oracle, second)],
        {SESSION_A: sess},
        [_fill(fill_at)],
    )

    assert [v.died_here for v in verdicts] == [False, True]
    summary = oracle.summarize(verdicts)
    assert summary.deaths_total == 1
    assert summary.deaths_labelled_phantom == 1
    assert summary.death_correlation_holds


def test_a_replay_lag_that_died_breaks_the_correlation(oracle: Any) -> None:
    """★음성 대조 — **독립 라벨**이 무해인데 사망과 겹치면 판별식을 기각해야 한다.

    이 단언이 없으면 `death_correlation_holds` 가 언제나 참인 동어반복일 수 있다.

    ★단언 대상이 `label` 이 아니라 `independent_label` 인 이유 — 회복식은 이 상황
    (후속 관측 없음 + 90초 안에 자동 사망)을 **`phantom` 으로 잡는다.** 그게 교체의 요점이다.
    독립 검사는 원장 기반 라벨로 재야 하므로 여기도 그 라벨을 본다.
    """
    at = datetime(2026, 8, 4, 4, 17, 8, 667000, tzinfo=UTC)
    sess = _session(deactivated_at=at, deactivated_reason="position_divergence")
    fill_at = datetime(2026, 8, 4, 4, 17, 8, 79000, tzinfo=UTC)

    verdicts = _adjudicate(oracle, [_event(oracle, at)], {SESSION_A: sess}, [_fill(fill_at)])

    assert verdicts[0].independent_label == "replay_lag"
    assert verdicts[0].recovery_label == "phantom"  # ★회복식은 이걸 잡는다
    assert verdicts[0].died_here is True
    assert oracle.summarize(verdicts).death_correlation_holds is False


def test_unknown_session_raises_instead_of_silently_dropping(oracle: Any) -> None:
    """분모가 말없이 줄어드는 것을 막는다."""
    at = datetime(2026, 8, 4, 4, 17, 8, tzinfo=UTC)
    with pytest.raises(ValueError):
        _adjudicate(oracle, [_event(oracle, at)], {}, [])


# --- 로그 파싱 -----------------------------------------------------------------


_REAL_LINE = (
    "2026-08-04T04:17:08.668483510Z [2026-08-04 04:17:08,667: WARNING/ForkPoolWorker-3] "
    "src.tasks.live_signal live_signal_position_divergence "
    "session_id=bbea6da4-e412-46a7-b395-e9042257cb91 symbol=BTC/USDT category=direction "
    "engine_position=-0.029847816854298426 exchange_position=0.029"
)


def test_parse_log_reads_a_real_worker_line(oracle: Any) -> None:
    (event,) = oracle.parse_log([_REAL_LINE])

    assert event.at == datetime(2026, 8, 4, 4, 17, 8, 668483, tzinfo=UTC)
    assert event.session_id == UUID("bbea6da4-e412-46a7-b395-e9042257cb91")
    assert event.category == "direction"
    assert event.exchange == pytest.approx(0.029)


def test_parse_log_keeps_sub_second_precision(oracle: Any) -> None:
    """★밀리초를 버리면 갈래가 뒤집힌다 — 실측에서 0.59초 건이 1344초로 보였다."""
    (event,) = oracle.parse_log([_REAL_LINE])
    assert event.at.microsecond != 0


def test_parse_log_filters_by_category(oracle: Any) -> None:
    other = _REAL_LINE.replace("category=direction", "category=exchange_only")
    assert oracle.parse_log([other]) == []
    assert len(oracle.parse_log([other], category="exchange_only")) == 1


def test_parse_log_raises_when_the_timestamp_is_missing(oracle: Any) -> None:
    """조용히 빠지면 분모가 말없이 줄어든다."""
    stripped = _REAL_LINE.split("Z ", 1)[1].split("] ", 1)[1]
    with pytest.raises(ValueError, match="타임스탬프"):
        oracle.parse_log([stripped])


# ==============================================================================
# 재무장 도장 (2026-08-05 판별식 교체)
# ==============================================================================
#
# 위 20 테스트는 **그대로 통과해야 한다** — 그 픽스처들에는 `created_at` 이 없어 도장이
# 하나도 없고, 그러면 판정은 종전 봉경계식으로 내려간다(`horizon_label`). 즉 위 20개는
# 이제 **fallback 경로**를 지킨다. 아래는 재무장 경로를 지킨다.


def _order(
    *,
    created_at: datetime,
    filled_at: datetime | None,
    state: str,
    side: str,
    quantity: str,
    session_id: UUID | None = SESSION_A,
    symbol: str = "BTC/USDT",
) -> dict[str, Any]:
    return {
        "created_at": created_at,
        "filled_at": filled_at,
        "state": state,
        "symbol": symbol,
        "side": side,
        "quantity": quantity,
        "idempotency_key": f"live:{session_id}:cond:x" if session_id is not None else None,
    }


def _at(spec: str) -> datetime:
    return datetime.fromisoformat(spec).replace(tzinfo=UTC)


# --- ★내가 실제로 밟은 함정: `filled_at` 은 체결의 증거가 아니다 -----------------


def test_cancelled_order_with_a_filled_at_is_not_a_fill(oracle: Any) -> None:
    """★`filled_at` 은 이름과 달리 **terminal 시각**이라 취소 주문에도 채워진다.

    실측 2026-08-05: 상태 필터를 빼고 원장을 읽자 취소 주문이 체결로 섞여 순포지션이
    망가지고 **재무장 도장이 전건 소실**됐다. 이 테스트가 그 재발을 막는다.
    """
    cancelled = _order(
        created_at=_at("2026-08-04 18:39:12"),
        filled_at=_at("2026-08-04 18:49:09"),  # ← 취소된 시각이다. 체결이 아니다.
        state="cancelled",
        side="buy",
        quantity="0.058",
    )
    assert oracle.is_filled(cancelled) is False
    assert oracle.ledger_net_at([cancelled], _at("2026-08-04 18:50:00")) == Decimal("0")


def test_a_row_without_state_is_treated_as_a_fill(oracle: Any) -> None:
    """호출자가 이미 체결만 걸러 넘긴 입력(위 20 테스트의 픽스처)은 그대로 체결이다."""
    assert oracle.is_filled({"filled_at": _at("2026-08-04 18:38:19")}) is True


# --- 재무장 도장 판정 ---------------------------------------------------------


def test_a_reversal_order_stamps_agreement(oracle: Any) -> None:
    """반전 주문 하나가 두 값을 동시에 증언한다 — 거래소는 원장 쪽, 엔진도 그 쪽.

    실측 `cc19abd2` `18:49:14` — 원장 순포지션 `-0.029` 위에 `buy 0.058`(= 2배).
    """
    ledger_before = Decimal("-0.029")
    order = _order(
        created_at=_at("2026-08-04 18:49:14"),
        filled_at=None,
        state="cancelled",
        side="buy",
        quantity="0.058",
    )
    assert oracle.is_rearm_stamp(order, ledger_before) is True


def test_the_first_entry_is_not_a_heartbeat(oracle: Any) -> None:
    """원장이 flat 이면 거래소 쪽을 증언하지 못한다 — 최초 1배 진입."""
    order = _order(
        created_at=_at("2026-08-04 16:33:11"),
        filled_at=None,
        state="cancelled",
        side="buy",
        quantity="0.029",
    )
    assert oracle.is_rearm_stamp(order, Decimal("0")) is False


def test_a_size_repair_order_is_not_a_heartbeat(oracle: Any) -> None:
    """실측 `4bf679af` `23:43:33` `sell 0.001` — 부호가 안 바뀐다 = 반전이 아니다."""
    order = _order(
        created_at=_at("2026-08-03 23:43:33"),
        filled_at=None,
        state="cancelled",
        side="sell",
        quantity="0.001",
    )
    assert oracle.is_rearm_stamp(order, Decimal("-0.029")) is False


def test_quantity_step_drift_still_counts_as_a_reversal(oracle: Any) -> None:
    """★거래소 수량 스텝 때문에 `|target|` 과 `|L|` 은 정확히 같지 않다.

    실측 `a201a47b` `14:46:47` — `L=+0.030` 에 `sell 0.059` → `target=-0.029` (3.3% 차).
    엄격 동등으로 두면 이 도장이 통째로 사라진다.
    """
    order = _order(
        created_at=_at("2026-08-03 14:46:47"),
        filled_at=None,
        state="cancelled",
        side="sell",
        quantity="0.059",
    )
    assert oracle.is_rearm_stamp(order, Decimal("0.030")) is True


def test_a_rearm_stamp_does_not_prove_the_engine_agrees(oracle: Any) -> None:
    """★★★**이 도장은 엔진의 포지션을 증언하지 않는다** — 초안의 근거가 반증된 자리다.

    실측 `39731d57` `16:24:11`: 원장 순포지션 `+0.029`(16:24:00 buy 체결) 위에 `sell 0.058`
    이 발주됐다 ⇒ 이 함수는 참을 낸다. 그런데 같은 시각 **엔진은 short** 였다
    (`live_signal_states` 의 open trade 가 19봉 전에 개시됐고, 두 tick 의 `engine_position`
    이 `-0.029722343673419874` 로 **비트 단위 동일**). 엔진은 이미 그 방향을 들고 있어도
    같은 `trade_id` 로 pending stop 을 다시 무장할 수 있다(`strategy_state.py:728-740`).

    ⇒ 도장이 증언하는 것은 **거래소 쪽과 「재무장을 끝냈다」는 사실**뿐이다.
    이 테스트가 red 가 되면 그 반증을 잊고 다시 「합의」로 읽고 있다는 뜻이다.
    """
    order = _order(
        created_at=_at("2026-08-04 16:24:11"),
        filled_at=_at("2026-08-04 16:25:03"),
        state="cancelled",
        side="sell",
        quantity="0.058",
    )
    ledger_after_the_buy = Decimal("0.029")

    assert oracle.is_rearm_stamp(order, ledger_after_the_buy) is True
    # ★엔진은 이때 short 였다. 도장은 그것과 **무관하게** 찍힌다.


def test_a_cancelled_order_that_carried_a_partial_fill_still_counts(oracle: Any) -> None:
    """★★레포 정본(`entry_completeness.attempt_has_fill`)이 이미 말한다 — `state` 로 판정하면
    안 된다. `transition_to_cancelled` 는 `filled_quantity` 가 0 이 아니면 **체결분을 보존한
    채** 종결한다. 상태로 걸러내면 거래소에 남은 포지션을 원장에서 잃는다.
    (codex challenge 2026-08-05 적발 — 나는 `state == 'filled'` 로 짰다.)
    """
    partial = {
        **_order(
            created_at=_at("2026-08-04 18:20:00"),
            filled_at=_at("2026-08-04 18:20:02"),
            state="cancelled",  # ← 상태는 취소인데
            side="buy",
            quantity="0.058",
        ),
        "filled_quantity": "0.029",  # ← 체결분이 남아 있다
    }
    assert oracle.is_filled(partial) is True
    assert oracle.signed_fill(partial) == Decimal("0.029")
    assert oracle.ledger_net_at([partial], _at("2026-08-04 18:30:00")) == Decimal("0.029")


def test_a_filled_row_without_a_filled_quantity_is_unreadable_not_a_full_fill(
    oracle: Any,
) -> None:
    """`filled` 인데 `filled_quantity` 가 NULL 이면 **판독 불가**다 — 전량 체결로 발명하지 않는다."""
    unreadable = {
        **_order(
            created_at=_at("2026-08-04 18:20:00"),
            filled_at=_at("2026-08-04 18:20:02"),
            state="filled",
            side="buy",
            quantity="0.058",
        ),
        "filled_quantity": None,
    }
    assert oracle.is_filled(unreadable) is False
    assert oracle.ledger_net_at([unreadable], _at("2026-08-04 18:30:00")) == Decimal("0")


def test_partial_fill_moves_the_ledger_by_the_filled_amount_not_the_request(
    oracle: Any,
) -> None:
    """전체 원장 실측: `filled` 202행 중 **65행**이 `filled_quantity <> quantity` 다."""
    partial = {
        **_order(
            created_at=_at("2026-08-04 18:20:00"),
            filled_at=_at("2026-08-04 18:20:02"),
            state="filled",
            side="sell",
            quantity="0.058",
        ),
        "filled_quantity": "0.030",
    }
    assert oracle.signed_fill(partial) == Decimal("-0.030")


def test_a_market_order_filled_at_its_own_creation_time_is_not_in_its_own_ledger(
    oracle: Any,
) -> None:
    """★시장가 주문은 생성과 terminal 기록이 같은 시각으로 찍힐 수 있다.

    그러면 `filled_at <= created_at` 이 참이 되어 **자기 체결이 자기 발주 전 원장에** 들어가고,
    반전 판정이 뒤집혀 도장을 놓친다(codex challenge 2026-08-05 적발 · 프로덕션 미관측).
    """
    same = _at("2026-08-04 18:38:17")
    seed = _order(
        created_at=_at("2026-08-04 18:20:00"),
        filled_at=_at("2026-08-04 18:20:02"),
        state="filled",
        side="buy",
        quantity="0.029",
    )
    market_reversal = _order(
        created_at=same,
        filled_at=same,  # ← 같은 시각
        state="filled",
        side="sell",
        quantity="0.058",
    )
    orders = [seed, market_reversal]

    # 자기 자신을 빼지 않으면 L = +0.029 - 0.058 = -0.029 가 되어 반전이 아니게 된다.
    assert oracle.ledger_net_at(orders, same, exclude=market_reversal) == Decimal("0.029")
    assert oracle.find_rearm_stamps(orders) == [same]


def test_a_gate_archive_without_engine_and_exchange_is_re_adjudicable(oracle: Any) -> None:
    """★게이트 아카이브(`.soak/phantom-*.json`)는 `engine`/`exchange` 를 **버린다.**

    필수로 읽으면 그걸 재판정할 수 없다(codex challenge 2026-08-05: `KeyError: 'engine'`
    재현). ADR-024 가 「언제든 재판정할 수 있다」고 적었으므로 실제로 읽혀야 한다.
    """
    archive = {
        "predicate_version": oracle.PREDICATE_VERSION,
        "verdicts": [
            {
                "at": "2026-08-04T18:50:01.926000+00:00",
                "label": "phantom",
                "session_id": str(SESSION_A),
            }
        ],
    }

    (event,) = oracle.parse_events_json(archive, {SESSION_A: "BTC/USDT"})

    assert event.at == _at("2026-08-04 18:50:01.926")
    assert event.session_id == SESSION_A
    assert event.symbol == "BTC/USDT"


def test_a_partial_close_is_not_a_reversal(oracle: Any) -> None:
    """부분청산(0.001 vs 0.029 = 96.5% 차)은 허용오차 밖이다."""
    order = _order(
        created_at=_at("2026-08-03 23:43:33"),
        filled_at=None,
        state="cancelled",
        side="sell",
        quantity="0.030",
    )
    assert oracle.is_rearm_stamp(order, Decimal("0.029")) is False


# --- 라벨 규칙 -----------------------------------------------------------------


_OBSERVED_AT = _at("2026-08-04 18:50:01.926")


def _stream_replay_lag() -> list[dict[str, Any]]:
    """실측 `cc19abd2` `18:07` 형태 — 마지막 도장 **뒤에** 거래소가 체결했다.

    두 번째 주문이 도장이자 체결이다: 발주 시점(`18:38:17`)에 원장이 `+0.029` 였으므로
    `sell 0.058` 은 반전이고 = 그 순간 재무장. 그 주문이 `18:38:19` 에 체결되며 거래소만
    반대편으로 넘어간다. ⇒ `F > H`.
    """
    return [
        _order(
            created_at=_at("2026-08-04 18:20:00"),
            filled_at=_at("2026-08-04 18:20:02"),
            state="filled",
            side="buy",
            quantity="0.029",
        ),
        _order(
            created_at=_at("2026-08-04 18:38:17"),
            filled_at=_at("2026-08-04 18:38:19"),
            state="filled",
            side="sell",
            quantity="0.058",
        ),
    ]


def _stream_phantom() -> list[dict[str, Any]]:
    """실측 `cc19abd2` `18:50` 형태 — 마지막 체결 **뒤에** 도장이 찍혔고 그 주문은 안 나갔다.

    `18:49:14` 의 `buy 0.058` 은 원장 `-0.029` 위의 반전이므로 도장이고, 끝내 체결되지
    않은 채(`cancelled`) 관측 시점에 어긋나 있다. ⇒ `H > F`, 움직인 건 엔진뿐이다.
    """
    return [
        *_stream_replay_lag(),
        _order(
            created_at=_at("2026-08-04 18:49:14"),
            filled_at=_at("2026-08-04 18:50:09"),  # ← 취소 시각. 체결이 아니다.
            state="cancelled",
            side="buy",
            quantity="0.058",
        ),
    ]


def test_agreement_after_the_last_fill_is_phantom(oracle: Any) -> None:
    """`H > F` — 체결 뒤 재무장을 끝냈는데도 어긋나 있다 ⇒ 조정 주기를 넘겼다."""
    (verdict,) = _adjudicate(
        oracle, [_event(oracle, _OBSERVED_AT)], {SESSION_A: _session()}, _stream_phantom()
    )

    assert verdict.last_rearm_at == _at("2026-08-04 18:49:14")
    assert verdict.last_fill_at == _at("2026-08-04 18:38:19")
    assert verdict.rearm_label == "phantom"
    assert verdict.label == "phantom"


def test_a_fill_after_the_last_agreement_is_replay_lag(oracle: Any) -> None:
    """`F >= H` — 마지막 재무장 뒤에 거래소가 움직였다 ⇒ 아직 판정할 때가 아니다."""
    (verdict,) = _adjudicate(
        oracle, [_event(oracle, _OBSERVED_AT)], {SESSION_A: _session()}, _stream_replay_lag()
    )

    assert verdict.last_rearm_at == _at("2026-08-04 18:38:17")
    assert verdict.last_fill_at == _at("2026-08-04 18:38:19")
    assert verdict.rearm_label == "replay_lag"
    assert verdict.label == "replay_lag"


def test_without_any_heartbeat_it_falls_back_to_the_horizon_predicate(oracle: Any) -> None:
    """★증거 부재를 유령으로 접지 않는다 — 도장이 없으면 종전 봉경계식이 판정한다."""
    at = _at("2026-08-03 15:53:34.291")
    fill_at = _at("2026-08-03 15:38:24.625")

    (verdict,) = _adjudicate(
        oracle, [_event(oracle, at)], {SESSION_A: _session()}, [_fill(fill_at)]
    )

    assert verdict.last_rearm_at is None
    assert verdict.rearm_label is None
    assert verdict.horizon_label == "phantom"
    assert verdict.label == "phantom"
    assert oracle.summarize([verdict]).rearm_undecided == 1


def test_another_sessions_reversal_is_not_a_heartbeat(oracle: Any) -> None:
    """도장도 `idempotency_key` 로만 귀속한다 — 남의 재무장을 빌려오지 않는다.

    ★남의 도장을 빼면 판정이 `phantom` → `replay_lag` 로 뒤집힌다. 「무시했다」가
    라벨에까지 닿는지 확인하는 게 요점이다.
    """
    orders = _stream_phantom()
    orders[-1] = {**orders[-1], "idempotency_key": f"live:{SESSION_B}:cond:x"}

    (verdict,) = _adjudicate(
        oracle, [_event(oracle, _OBSERVED_AT)], {SESSION_A: _session()}, orders
    )

    assert verdict.last_rearm_at == _at("2026-08-04 18:38:17")
    assert verdict.label == "replay_lag"


def test_another_symbols_reversal_is_not_a_heartbeat(oracle: Any) -> None:
    orders = _stream_phantom()
    orders[-1] = {**orders[-1], "symbol": "ETH/USDT"}

    (verdict,) = _adjudicate(
        oracle, [_event(oracle, _OBSERVED_AT)], {SESSION_A: _session()}, orders
    )

    assert verdict.last_rearm_at == _at("2026-08-04 18:38:17")
    assert verdict.label == "replay_lag"


def test_a_reversal_created_after_the_observation_is_ignored(oracle: Any) -> None:
    """관측 뒤에 찍힌 도장으로 과거를 판정하지 않는다."""
    at = _at("2026-08-04 18:45:00")  # `18:49:14` 도장보다 앞선다

    (verdict,) = _adjudicate(
        oracle, [_event(oracle, at)], {SESSION_A: _session()}, _stream_phantom()
    )

    assert verdict.last_rearm_at == _at("2026-08-04 18:38:17")
    assert verdict.label == "replay_lag"


def test_heartbeats_do_not_depend_on_input_order(oracle: Any) -> None:
    """★정렬을 암묵 계약으로 두지 않는다 (`candidates[-1]` 결함의 재무장판 회귀)."""
    forward = _stream_phantom()

    (a,) = _adjudicate(oracle, [_event(oracle, _OBSERVED_AT)], {SESSION_A: _session()}, forward)
    (b,) = _adjudicate(
        oracle, [_event(oracle, _OBSERVED_AT)], {SESSION_A: _session()}, list(reversed(forward))
    )

    assert a.last_rearm_at == b.last_rearm_at == _at("2026-08-04 18:49:14")
    assert a.label == b.label == "phantom"


def test_a_row_without_created_at_can_never_stamp_agreement(oracle: Any) -> None:
    """발주 시각을 모르면 「그 순간」을 증언할 수 없다 — 조용히 지금으로 치지 않는다."""
    stripped = [{k: v for k, v in o.items() if k != "created_at"} for o in _stream_phantom()]
    assert oracle.find_rearm_stamps(stripped) == []


def test_the_label_does_not_depend_on_the_position_magnitudes(oracle: Any) -> None:
    """★판별식은 원장 시각만 쓴다 — 로그의 엔진/거래소 수치는 판정에 안 들어간다.

    골든 회귀(아래)가 수치를 고정하지 않는 이유가 이것이다.
    """
    orders = _stream_phantom()
    flipped = oracle.DivergenceEvent(
        at=_OBSERVED_AT,
        session_id=SESSION_A,
        symbol="BTC/USDT",
        category="direction",
        engine=+0.0296,  # 부호도 크기도 바꿔 본다
        exchange=-0.029,
    )

    (base,) = _adjudicate(oracle, [_event(oracle, _OBSERVED_AT)], {SESSION_A: _session()}, orders)
    (other,) = _adjudicate(oracle, [flipped], {SESSION_A: _session()}, orders)

    assert base.label == other.label == "phantom"


# ==============================================================================
# ★현행 판별식 — 직접 회복 검사 (2026-08-05 2차 교체)
# ==============================================================================
#
# 이 식은 원장을 아예 안 본다. 「같은 스트림의 다음 관측이 바로 다음 평가인가」 하나다.
# 그래서 여기서 고정할 것도 셋뿐이다 — **경계**(1.5·I) · **꼬리 처리**(사망/절단) ·
# **스트림 격리**(남의 관측을 빌리지 않는다).

_RECOVERY_AT = _at("2026-08-04 16:24:01.674")


def _recovery(
    oracle: Any,
    offsets_seconds: list[float],
    *,
    corpus_end_offset: float | None = None,
    interval: str = "1m",
    deactivated_at: datetime | None = None,
    deactivated_reason: str | None = None,
) -> list[Any]:
    """`_RECOVERY_AT` 기준 상대 초로 관측을 만들고 재판정한다.

    체결은 하나만 두고 `created_at` 을 주지 않는다 ⇒ 도장이 없어 재무장식은 판정하지
    않는다. 그래야 **회복식이 채택됐는지**가 라벨에 그대로 드러난다.

    `corpus_end_offset` 기본값 = **마지막 관측** — 로그가 거기서 끝났다는 뜻이고,
    그러면 각 스트림의 마지막 관측은 판정 불가가 된다(그게 실제 창의 모습이다).
    """
    if corpus_end_offset is None:
        corpus_end_offset = max(offsets_seconds)
    events = [_event(oracle, _RECOVERY_AT + timedelta(seconds=off)) for off in offsets_seconds]
    return _adjudicate(
        oracle,
        events,
        {
            SESSION_A: _session(
                interval=interval,
                deactivated_at=deactivated_at,
                deactivated_reason=deactivated_reason,
            )
        },
        [_fill(_RECOVERY_AT - timedelta(seconds=1))],
        corpus_end=_RECOVERY_AT + timedelta(seconds=corpus_end_offset),
    )


def test_the_next_tick_still_diverging_is_phantom(oracle: Any) -> None:
    """실측 `39731d57` `16:24 → 16:25` (간격 60.02초) — 안 나았다.

    ★이 관측이 교체의 이유다. 재무장식은 여기에 `replay_lag` 을 붙였고, 60초 뒤 세션이
    죽었다. 회복식은 원장을 안 보고 **다음 평가에도 어긋나 있었다**만으로 잡는다.
    """
    first, second = _recovery(oracle, [0.0, 60.02])

    assert first.recovery_label == "phantom"
    assert first.rearm_label is None  # 도장이 없다 — 재무장식은 판정 못 한다
    assert first.label == "phantom"  # ⇒ 채택된 것은 회복식이다
    assert first.next_gap_seconds == pytest.approx(60.02)
    # 두 번째는 로그의 마지막 줄이라 후속자를 아직 못 봤다 ⇒ 판정 불가(§절단 약점).
    assert second.recovery_label is None


def test_a_later_observation_is_a_new_episode_not_a_continuation(oracle: Any) -> None:
    """실측 `cc19abd2` `17:26 → 17:29` (180.2초) — 그 사이 두 평가가 나았다."""
    (first, _) = _recovery(oracle, [0.0, 180.2], corpus_end_offset=600.0)

    assert first.recovery_label == "replay_lag"


def test_the_next_tick_boundary_is_inclusive_at_one_and_a_half_bars(oracle: Any) -> None:
    """`gap == 1.5·I` 는 **유령** 쪽이다(`<=` 이 포함) — 경계를 못박는다.

    실측 분리는 60초 vs 180초로 넓지만, 부등호가 뒤집히면 tick 지연이 큰 창에서
    유령이 조용히 무해로 바뀐다. 방향이 fail-open 이라 여기서 고정한다.
    """
    (exactly,) = _recovery(oracle, [0.0, 90.0])[:1]
    (just_past,) = _recovery(oracle, [0.0, 90.000001], corpus_end_offset=600.0)[:1]

    assert exactly.recovery_label == "phantom"
    assert just_past.recovery_label == "replay_lag"


def test_the_next_tick_horizon_follows_the_session_interval(oracle: Any) -> None:
    """문턱은 고정 초가 아니라 **그 세션의 봉 간격**을 따른다."""
    (one_minute,) = _recovery(oracle, [0.0, 120.0], corpus_end_offset=900.0)[:1]
    (five_minute,) = _recovery(oracle, [0.0, 120.0], corpus_end_offset=900.0, interval="5m")[:1]

    assert one_minute.recovery_label == "replay_lag"  # 120 > 1.5 × 60
    assert five_minute.recovery_label == "phantom"  # 120 <= 1.5 × 300


def test_a_skipped_tick_gap_lands_in_the_ambiguous_band(oracle: Any) -> None:
    """★경고 눈금의 **판별력 증명** — 「애매대 0건」이 뜻을 가지려면 채워질 수 있어야 한다.

    tick 이 한 번 빠지면(`probe_failed`) 다음 발산은 `2·I` 뒤에 온다. 회복식은 그것을
    `replay_lag` 이라 부르고(**fail-open 잔여**), `ambiguous_gap_band` 가 그 사실을 센다.
    이 테스트가 없으면 실측의 `0건` 은 「그런 일이 없다」가 아니라 「못 센다」일 수 있다.
    """
    verdicts = _recovery(oracle, [0.0, 120.0], corpus_end_offset=900.0)
    summary = oracle.summarize(verdicts)

    assert verdicts[0].recovery_label == "replay_lag"
    assert summary.ambiguous_gap_band == 1
    assert summary.min_replay_lag_gap == pytest.approx(120.0)


def test_an_automatic_death_right_after_the_observation_is_phantom(oracle: Any) -> None:
    """후속 관측이 없는 이유가 **자동 사망**이면 나은 게 아니다 — 죽어서 끊긴 것이다."""
    (verdict,) = _recovery(
        oracle,
        [0.0],
        deactivated_at=_RECOVERY_AT + timedelta(seconds=0.001),
        deactivated_reason="position_divergence",
    )

    assert verdict.recovery_label == "phantom"
    assert verdict.died_here is True


def test_a_user_stopped_tail_is_not_called_phantom(oracle: Any) -> None:
    """★우리가 껐으면 회복할 기회를 우리가 뺏은 것이다 — 유령으로 접지 않는다.

    실측 `4bf679af` / `bbea6da4` 가 `user_stopped` 다. 이걸 유령으로 세면 **운영자가
    소크를 멈출 때마다 게이트가 실격**되고, 그건 판별식이 아니라 운영 행위를 재는 것이다.
    """
    (verdict,) = _recovery(
        oracle,
        [0.0],
        deactivated_at=_RECOVERY_AT + timedelta(seconds=1),
        deactivated_reason="user_stopped",
    )

    assert verdict.recovery_label is None


def test_an_unknown_deactivation_reason_is_not_called_phantom(oracle: Any) -> None:
    """★사유 NULL 은 실재한다 — 25세션 중 12세션([ADR-024] 창 정의 ①). 추측하지 않는다."""
    (verdict,) = _recovery(
        oracle, [0.0], deactivated_at=_RECOVERY_AT + timedelta(seconds=1), deactivated_reason=None
    )

    assert verdict.recovery_label is None


def test_watching_long_enough_without_a_recurrence_is_replay_lag(oracle: Any) -> None:
    """후속 관측이 없고 창이 충분히 길면 **나은 것**이다 — 그게 대다수 관측의 경로다."""
    (verdict,) = _recovery(oracle, [0.0], corpus_end_offset=600.0)

    assert verdict.recovery_label == "replay_lag"


def test_a_truncated_log_is_undecidable_and_falls_back_to_the_rearm_predicate(
    oracle: Any,
) -> None:
    """★이 식의 약점 — 창의 마지막 관측은 후속자가 아직 없다.

    「없다」를 「나았다」로 접으면 fail-open 이므로 **판정하지 않고** 종전 식으로 내려간다.
    여기서는 도장이 있으므로 재무장식이 받는다.
    """
    (verdict,) = _adjudicate(
        oracle,
        [_event(oracle, _OBSERVED_AT)],
        {SESSION_A: _session()},
        _stream_phantom(),
        corpus_end=_OBSERVED_AT,  # 로그가 딱 여기서 끝났다
    )

    assert verdict.recovery_label is None
    assert verdict.rearm_label == "phantom"
    assert verdict.label == "phantom"
    assert oracle.summarize([verdict]).recovery_undecided == 1


def test_the_fallback_chain_reaches_the_horizon_predicate_when_no_stamp_exists(
    oracle: Any,
) -> None:
    """강하는 두 단이다 — 회복식 → 재무장식 → 봉경계식. 마지막 단까지 내려가는 경로."""
    (verdict,) = _recovery(oracle, [0.0])

    assert verdict.recovery_label is None
    assert verdict.rearm_label is None
    assert verdict.label == verdict.horizon_label


def test_the_recovery_label_does_not_borrow_another_sessions_observation(oracle: Any) -> None:
    """다른 세션이 60초 뒤에 어긋났다고 이 세션이 안 나은 것은 아니다."""
    events = [
        _event(oracle, _RECOVERY_AT),
        _event(oracle, _RECOVERY_AT + timedelta(seconds=60), session_id=SESSION_B),
    ]
    verdicts = _adjudicate(
        oracle,
        events,
        {SESSION_A: _session(), SESSION_B: _session()},
        [_fill(_RECOVERY_AT - timedelta(seconds=1))],
        corpus_end=_RECOVERY_AT + timedelta(seconds=600),
    )

    assert verdicts[0].recovery_label == "replay_lag"
    assert verdicts[0].next_observation_at is None


def test_the_recovery_label_does_not_borrow_another_symbols_observation(oracle: Any) -> None:
    """스트림은 (세션, 심볼) 이다 — 한 세션이 두 심볼을 들면 서로의 후속자가 아니다."""
    other = oracle.DivergenceEvent(
        at=_RECOVERY_AT + timedelta(seconds=60),
        session_id=SESSION_A,
        symbol="ETH/USDT",
        category="direction",
        engine=-0.0298,
        exchange=0.029,
    )
    verdicts = _adjudicate(
        oracle,
        [_event(oracle, _RECOVERY_AT), other],
        {SESSION_A: _session()},
        [_fill(_RECOVERY_AT - timedelta(seconds=1))],
        corpus_end=_RECOVERY_AT + timedelta(seconds=600),
    )

    assert verdicts[0].recovery_label == "replay_lag"


def test_the_recovery_label_is_independent_of_input_order(oracle: Any) -> None:
    """★정렬은 호출자의 사정이다 — 뒤섞여 오면 후속자가 조용히 바뀐다.

    같은 함정을 최신 체결(`max` vs `[-1]`)에서 이미 한 번 밟았다.
    """
    forward = _recovery(oracle, [0.0, 60.0, 600.0], corpus_end_offset=1200.0)
    shuffled = _recovery(oracle, [600.0, 0.0, 60.0], corpus_end_offset=1200.0)

    assert [v.recovery_label for v in forward] == ["phantom", "replay_lag", "replay_lag"]
    assert {v.event.at: v.recovery_label for v in shuffled} == {
        v.event.at: v.recovery_label for v in forward
    }


def test_adjudicate_refuses_to_guess_the_corpus_end(oracle: Any) -> None:
    """★`corpus_end` 에 기본값을 주지 않는다.

    기본값을 「지금」으로 두면 **로그 절단이 회복으로 오독**되고, 그 방향은 게이트에서
    fail-open 이다. 호출자가 무엇을 봤는지 말하게 강제한다.
    """
    with pytest.raises(TypeError):
        oracle.adjudicate([_event(oracle, _RECOVERY_AT)], {SESSION_A: _session()}, [])


# --- 코퍼스 지평 파싱 -----------------------------------------------------------


def test_log_horizon_reads_every_line_not_just_divergences(oracle: Any) -> None:
    """★발산 줄만 보면 창의 끝을 모른다 — 그게 「나았다」와 「아직 못 봄」을 가른다."""
    lines = [
        "[2026-08-05 05:01:50,825: WARNING/ForkPoolWorker-1] live_signal_position_divergence "
        "session_id=aaaaaaaa-0000-4000-8000-000000000001 symbol=BTC/USDT category=direction "
        "engine_position=-0.0298 exchange_position=0.029",
        "[2026-08-05 05:59:12,001: INFO/MainProcess] Task live_signal.evaluate_all succeeded",
    ]

    assert oracle.parse_log_horizon(lines) == _at("2026-08-05 05:59:12.001")


def test_log_horizon_is_none_when_nothing_carries_a_timestamp(oracle: Any) -> None:
    """지평을 못 읽으면 `None` 이다 — 호출자가 마지막 관측으로 떨어뜨린다(판정 불가 증가)."""
    assert oracle.parse_log_horizon(['  File "x.py", line 1, in <module>', "    raise"]) is None


# ==============================================================================
# ★골든 회귀 — 실측 19건 전량 (2026-08-02T13:19 ~ 2026-08-05T01:21)
# ==============================================================================
#
# 이 표가 판별식 교체의 **유일한 진짜 검증**이다. 손으로 낸 답과 코드가 갈리면 red 다.
#
# 모집단 = 로그로 재판정 가능한 `direction` 관측 **전량**이다:
#   · 창 A `2026-08-02T13:19 ~ 08-04T06:38` — 11건 (`.soak/direction-classification-*.json`)
#   · 창 B `2026-08-04T15:51 ~ 08-05T01:21` — 8건 (현 워커 로그)
# ★그 밖은 없다 — 워커 로그는 컨테이너 수명에 묶여 있고, 그 앞 관측은 아카이브가 없다.
#
# 주문 스트림은 각 세션의 **마지막 관측 시각까지**만 담았다(그 뒤 주문은 뒤를 볼 수 없는
# 판별식에 구조적으로 영향이 없다). 원장에서 기계로 뽑았고 손으로 옮겨 적지 않았다.

_GOLDEN_SESSIONS: dict[str, tuple[str, str | None, str | None]] = {
    # 접두사: (전체 UUID, deactivated_at, deactivated_reason)
    "04097fdc": (
        "04097fdc-0322-4a23-bfcc-d9f7c7a7e2b3",
        "2026-08-03 10:58:34.218897",
        "position_divergence",
    ),
    "a201a47b": (
        "a201a47b-2ff5-408d-821f-52f655054db1",
        "2026-08-03 15:54:34.409982",
        "position_divergence",
    ),
    "4bf679af": (
        "4bf679af-e535-402e-ba8e-8b91cebe3b51",
        "2026-08-04 01:39:04.921852",
        "user_stopped",
    ),
    "bbea6da4": (
        "bbea6da4-e412-46a7-b395-e9042257cb91",
        "2026-08-04 07:26:14.495420",
        "user_stopped",
    ),
    "39731d57": (
        "39731d57-f3ec-45c4-b4e1-db304c72692e",
        "2026-08-04 16:25:01.695025",
        "position_divergence",
    ),
    "cc19abd2": (
        "cc19abd2-a1ba-45a0-92f0-807385259b32",
        "2026-08-04 18:51:01.769866",
        "position_divergence",
    ),
}

# (세션 접두사, created_at, filled_at | "", state, side, quantity)
_GOLDEN_ORDERS: list[tuple[str, str, str, str, str, str]] = [
    # 04097fdc
    (
        "04097fdc",
        "2026-08-03 09:54:56.574796",
        "2026-08-03 10:04:43.269679",
        "cancelled",
        "sell",
        "0.03",
    ),
    (
        "04097fdc",
        "2026-08-03 10:00:46.461942",
        "2026-08-03 10:05:43.677480",
        "cancelled",
        "buy",
        "0.03",
    ),
    (
        "04097fdc",
        "2026-08-03 10:04:48.440134",
        "2026-08-03 10:05:04.755599",
        "filled",
        "sell",
        "0.03",
    ),
    (
        "04097fdc",
        "2026-08-03 10:05:48.778714",
        "2026-08-03 10:10:43.063643",
        "cancelled",
        "buy",
        "0.06",
    ),
    (
        "04097fdc",
        "2026-08-03 10:10:48.158154",
        "2026-08-03 10:12:34.278802",
        "filled",
        "buy",
        "0.06",
    ),
    (
        "04097fdc",
        "2026-08-03 10:13:46.027226",
        "2026-08-03 10:19:37.587011",
        "filled",
        "sell",
        "0.06",
    ),
    (
        "04097fdc",
        "2026-08-03 10:38:46.774880",
        "2026-08-03 10:56:41.752675",
        "cancelled",
        "buy",
        "0.06",
    ),
    # 39731d57
    (
        "39731d57",
        "2026-08-04 15:49:25.185468",
        "2026-08-04 15:54:17.116491",
        "cancelled",
        "sell",
        "0.029",
    ),
    (
        "39731d57",
        "2026-08-04 15:54:22.371782",
        "2026-08-04 16:01:09.234674",
        "cancelled",
        "buy",
        "0.029",
    ),
    (
        "39731d57",
        "2026-08-04 15:54:28.403303",
        "2026-08-04 16:01:22.124973",
        "filled",
        "sell",
        "0.029",
    ),
    (
        "39731d57",
        "2026-08-04 16:01:14.119587",
        "2026-08-04 16:02:09.357393",
        "cancelled",
        "buy",
        "0.029",
    ),
    (
        "39731d57",
        "2026-08-04 16:02:14.371616",
        "2026-08-04 16:15:09.243043",
        "cancelled",
        "buy",
        "0.058",
    ),
    (
        "39731d57",
        "2026-08-04 16:15:14.271888",
        "2026-08-04 16:21:09.205094",
        "cancelled",
        "buy",
        "0.058",
    ),
    (
        "39731d57",
        "2026-08-04 16:21:13.991182",
        "2026-08-04 16:24:00.145029",
        "filled",
        "buy",
        "0.058",
    ),
    (
        "39731d57",
        "2026-08-04 16:24:11.787997",
        "2026-08-04 16:25:03.480478",
        "cancelled",
        "sell",
        "0.058",
    ),
    # 4bf679af
    (
        "4bf679af",
        "2026-08-03 22:56:42.432980",
        "2026-08-03 23:05:29.729790",
        "cancelled",
        "sell",
        "0.029",
    ),
    (
        "4bf679af",
        "2026-08-03 22:57:32.654462",
        "2026-08-03 23:07:29.409250",
        "cancelled",
        "buy",
        "0.029",
    ),
    (
        "4bf679af",
        "2026-08-03 23:05:34.570419",
        "2026-08-03 23:06:38.088401",
        "filled",
        "sell",
        "0.029",
    ),
    (
        "4bf679af",
        "2026-08-03 23:07:34.432864",
        "2026-08-03 23:12:29.733681",
        "cancelled",
        "buy",
        "0.058",
    ),
    (
        "4bf679af",
        "2026-08-03 23:12:34.520072",
        "2026-08-03 23:17:00.652144",
        "filled",
        "buy",
        "0.058",
    ),
    # a201a47b
    (
        "a201a47b",
        "2026-08-03 14:10:55.816130",
        "2026-08-03 14:10:57.846890",
        "filled",
        "buy",
        "0.03",
    ),
    (
        "a201a47b",
        "2026-08-03 14:11:44.267631",
        "2026-08-03 14:17:41.549340",
        "cancelled",
        "sell",
        "0.06",
    ),
    (
        "a201a47b",
        "2026-08-03 14:17:46.342511",
        "2026-08-03 14:20:20.708815",
        "filled",
        "sell",
        "0.06",
    ),
    (
        "a201a47b",
        "2026-08-03 14:20:44.159445",
        "2026-08-03 14:26:56.795291",
        "filled",
        "buy",
        "0.06",
    ),
    (
        "a201a47b",
        "2026-08-03 14:27:45.718668",
        "2026-08-03 14:39:41.646195",
        "cancelled",
        "sell",
        "0.059",
    ),
    (
        "a201a47b",
        "2026-08-03 14:39:46.666316",
        "2026-08-03 14:46:42.276056",
        "cancelled",
        "sell",
        "0.059",
    ),
    (
        "a201a47b",
        "2026-08-03 14:46:47.297209",
        "2026-08-03 14:47:43.504698",
        "filled",
        "sell",
        "0.059",
    ),
    (
        "a201a47b",
        "2026-08-03 14:48:44.321359",
        "2026-08-03 14:55:09.578732",
        "filled",
        "buy",
        "0.058",
    ),
    (
        "a201a47b",
        "2026-08-03 14:55:44.499525",
        "2026-08-03 15:11:41.824129",
        "cancelled",
        "sell",
        "0.058",
    ),
    (
        "a201a47b",
        "2026-08-03 15:11:46.727086",
        "2026-08-03 15:12:24.338712",
        "filled",
        "sell",
        "0.058",
    ),
    (
        "a201a47b",
        "2026-08-03 15:12:45.142643",
        "2026-08-03 15:14:41.577170",
        "cancelled",
        "buy",
        "0.058",
    ),
    (
        "a201a47b",
        "2026-08-03 15:14:46.489884",
        "2026-08-03 15:37:41.559346",
        "cancelled",
        "buy",
        "0.058",
    ),
    (
        "a201a47b",
        "2026-08-03 15:37:46.381417",
        "2026-08-03 15:38:24.625012",
        "filled",
        "buy",
        "0.058",
    ),
    (
        "a201a47b",
        "2026-08-03 15:38:44.669702",
        "2026-08-03 15:45:41.476224",
        "cancelled",
        "sell",
        "0.058",
    ),
    (
        "a201a47b",
        "2026-08-03 15:45:46.325503",
        "2026-08-03 15:52:41.770506",
        "cancelled",
        "sell",
        "0.058",
    ),
    (
        "a201a47b",
        "2026-08-03 15:52:46.675499",
        "2026-08-03 15:52:49.055098",
        "rejected",
        "sell",
        "0.058",
    ),
    # bbea6da4
    (
        "bbea6da4",
        "2026-08-04 02:55:29.619014",
        "2026-08-04 03:03:16.094504",
        "cancelled",
        "buy",
        "0.029",
    ),
    (
        "bbea6da4",
        "2026-08-04 02:55:34.612083",
        "2026-08-04 02:57:16.234793",
        "cancelled",
        "sell",
        "0.029",
    ),
    (
        "bbea6da4",
        "2026-08-04 02:57:21.307437",
        "2026-08-04 03:04:11.992402",
        "filled",
        "sell",
        "0.029",
    ),
    (
        "bbea6da4",
        "2026-08-04 03:05:18.760926",
        "2026-08-04 03:20:16.200633",
        "cancelled",
        "buy",
        "0.058",
    ),
    (
        "bbea6da4",
        "2026-08-04 03:20:21.325642",
        "2026-08-04 03:27:12.173947",
        "filled",
        "buy",
        "0.058",
    ),
    (
        "bbea6da4",
        "2026-08-04 03:28:19.414535",
        "2026-08-04 03:45:16.409411",
        "cancelled",
        "sell",
        "0.058",
    ),
    (
        "bbea6da4",
        "2026-08-04 03:45:21.391641",
        "2026-08-04 03:48:16.854339",
        "filled",
        "sell",
        "0.058",
    ),
    (
        "bbea6da4",
        "2026-08-04 03:49:19.494170",
        "2026-08-04 03:49:24.351770",
        "filled",
        "buy",
        "0.058",
    ),
    (
        "bbea6da4",
        "2026-08-04 03:51:19.020547",
        "2026-08-04 03:54:44.184338",
        "filled",
        "sell",
        "0.058",
    ),
    (
        "bbea6da4",
        "2026-08-04 03:55:18.930281",
        "2026-08-04 04:14:17.458220",
        "cancelled",
        "buy",
        "0.058",
    ),
    (
        "bbea6da4",
        "2026-08-04 04:14:22.443177",
        "2026-08-04 04:17:08.079781",
        "filled",
        "buy",
        "0.058",
    ),
    # cc19abd2
    (
        "cc19abd2",
        "2026-08-04 16:33:11.724055",
        "2026-08-04 16:43:10.598773",
        "cancelled",
        "buy",
        "0.029",
    ),
    (
        "cc19abd2",
        "2026-08-04 16:42:12.104057",
        "2026-08-04 16:43:02.103906",
        "filled",
        "sell",
        "0.029",
    ),
    (
        "cc19abd2",
        "2026-08-04 16:44:12.855321",
        "2026-08-04 16:54:08.997536",
        "cancelled",
        "buy",
        "0.058",
    ),
    (
        "cc19abd2",
        "2026-08-04 16:54:13.861038",
        "2026-08-04 17:01:09.408596",
        "cancelled",
        "buy",
        "0.058",
    ),
    (
        "cc19abd2",
        "2026-08-04 17:01:18.400651",
        "2026-08-04 17:01:20.361683",
        "filled",
        "buy",
        "0.058",
    ),
    (
        "cc19abd2",
        "2026-08-04 17:02:12.050393",
        "2026-08-04 17:23:09.307066",
        "cancelled",
        "sell",
        "0.058",
    ),
    (
        "cc19abd2",
        "2026-08-04 17:23:14.144944",
        "2026-08-04 17:25:09.570671",
        "filled",
        "sell",
        "0.058",
    ),
    (
        "cc19abd2",
        "2026-08-04 17:27:12.286330",
        "2026-08-04 17:28:55.089474",
        "filled",
        "buy",
        "0.058",
    ),
    (
        "cc19abd2",
        "2026-08-04 17:29:12.163453",
        "2026-08-04 17:49:24.943898",
        "filled",
        "sell",
        "0.058",
    ),
    (
        "cc19abd2",
        "2026-08-04 17:50:11.845683",
        "2026-08-04 18:06:52.528628",
        "filled",
        "buy",
        "0.058",
    ),
    (
        "cc19abd2",
        "2026-08-04 18:07:11.942475",
        "2026-08-04 18:38:09.278276",
        "cancelled",
        "sell",
        "0.058",
    ),
    (
        "cc19abd2",
        "2026-08-04 18:38:17.391907",
        "2026-08-04 18:38:19.421635",
        "filled",
        "sell",
        "0.058",
    ),
    (
        "cc19abd2",
        "2026-08-04 18:39:12.399017",
        "2026-08-04 18:49:09.681182",
        "cancelled",
        "buy",
        "0.058",
    ),
    (
        "cc19abd2",
        "2026-08-04 18:49:14.610822",
        "2026-08-04 18:50:09.240365",
        "cancelled",
        "buy",
        "0.058",
    ),
]

# ★코퍼스 지평 = 창 B 워커 로그의 끝(`2026-08-05T01:21`, 교체 시점).
#
# 회복식은 「다음 관측이 없다」를 **회복**과 **아직 못 봄**으로 갈라야 하고, 그 경계가
# 이 값이다. 빼면 각 세션의 마지막 관측이 전부 판정 불가가 되어 이 표가 회복식을 아예
# 검사하지 못한다. ★코퍼스가 자라도 **이 값을 미래로 밀지 마라** — 그러면 교체 시점의
# n=19 를 동결한다는 이 표의 계약이 깨진다([ADR-024] §아카이브 판).
_GOLDEN_CORPUS_END = "2026-08-05 01:21:00.000"

# (관측시각, 세션 접두사, 회복식 라벨, 재무장식 라벨, 봉경계식 라벨, 사망)
_GOLDEN_VERDICTS: list[tuple[str, str, str, str, str, bool]] = [
    ("2026-08-03 10:12:36.166", "04097fdc", "replay_lag", "replay_lag", "replay_lag", False),
    ("2026-08-03 10:57:34.121", "04097fdc", "phantom", "phantom", "phantom", False),
    ("2026-08-03 10:58:34.218", "04097fdc", "phantom", "phantom", "phantom", True),
    ("2026-08-03 14:20:34.160", "a201a47b", "replay_lag", "replay_lag", "replay_lag", False),
    ("2026-08-03 14:55:34.300", "a201a47b", "replay_lag", "replay_lag", "replay_lag", False),
    ("2026-08-03 15:12:34.326", "a201a47b", "replay_lag", "replay_lag", "replay_lag", False),
    ("2026-08-03 15:38:34.166", "a201a47b", "replay_lag", "replay_lag", "replay_lag", False),
    ("2026-08-03 15:53:34.291", "a201a47b", "phantom", "phantom", "phantom", False),
    ("2026-08-03 15:54:34.409", "a201a47b", "phantom", "phantom", "phantom", True),
    ("2026-08-03 23:17:21.979", "4bf679af", "replay_lag", "replay_lag", "replay_lag", False),
    ("2026-08-04 04:17:08.667", "bbea6da4", "replay_lag", "replay_lag", "replay_lag", False),
    # ★★회복식이 뒤집은 **유일한 1건** — 재무장식은 「무해」라 했지만 **60.02초 뒤 사망의
    #   첫 짝**이다. 직전 회차가 「`replay_lag` 12/12 생존은 과장이었다」고 스스로 정정한
    #   바로 그 관측이고, 회복식은 그것을 처음부터 `phantom` 으로 판정한다.
    ("2026-08-04 16:24:01.674", "39731d57", "phantom", "replay_lag", "replay_lag", False),
    ("2026-08-04 16:25:01.694", "39731d57", "phantom", "phantom", "phantom", True),
    # ★재무장식이 뒤집은 4건 — 전부 `cc19abd2`, 전부 자가치유했고 전부 사망과 무관하다.
    #   회복식도 같은 답을 낸다(간격 180~2580초 = 그 사이 나았다).
    ("2026-08-04 17:26:01.788", "cc19abd2", "replay_lag", "replay_lag", "phantom", False),
    ("2026-08-04 17:29:01.989", "cc19abd2", "replay_lag", "replay_lag", "phantom", False),
    ("2026-08-04 17:50:01.750", "cc19abd2", "replay_lag", "replay_lag", "phantom", False),
    ("2026-08-04 18:07:01.829", "cc19abd2", "replay_lag", "replay_lag", "phantom", False),
    ("2026-08-04 18:50:01.926", "cc19abd2", "phantom", "phantom", "phantom", False),
    ("2026-08-04 18:51:01.769", "cc19abd2", "phantom", "phantom", "phantom", True),
]


@pytest.fixture(scope="module")
def golden(oracle: Any) -> list[Any]:
    sessions = {
        UUID(full): {
            "interval": "1m",
            "symbol": "BTC/USDT",
            "deactivated_at": _at(dead) if dead else None,
            "deactivated_reason": reason,
        }
        for full, dead, reason in _GOLDEN_SESSIONS.values()
    }
    orders = [
        {
            "created_at": _at(created),
            "filled_at": _at(filled) if filled else None,
            "state": state,
            "symbol": "BTC/USDT",
            "side": side,
            "quantity": quantity,
            "idempotency_key": f"live:{_GOLDEN_SESSIONS[prefix][0]}:cond:x",
        }
        for prefix, created, filled, state, side, quantity in _GOLDEN_ORDERS
    ]
    events = [
        oracle.DivergenceEvent(
            at=_at(at),
            session_id=UUID(_GOLDEN_SESSIONS[prefix][0]),
            symbol="BTC/USDT",
            category="direction",
            engine=-0.0298,
            exchange=0.029,
        )
        for at, prefix, _, _, _, _ in _GOLDEN_VERDICTS
    ]
    return _adjudicate(oracle, events, sessions, orders, corpus_end=_at(_GOLDEN_CORPUS_END))


def test_golden_every_observation_keeps_its_label(golden: list[Any]) -> None:
    """실측 19건 전량 — 식 **세 벌 전부**를 행 단위로 동결한다.

    ★채택 라벨만 얼리면 「어느 식이 언제 갈리는지」가 사라진다. 2026-08-05 의 두 교체가
    각각 4건·1건을 뒤집었고, 그 차이가 교체를 정당화하는 유일한 증거였다.
    """
    actual = [
        (v.event.at, v.label, v.recovery_label, v.rearm_label, v.horizon_label, v.died_here)
        for v in golden
    ]
    expected = [
        (_at(at), recovery, recovery, rearm, horizon, died)
        for at, _, recovery, rearm, horizon, died in _GOLDEN_VERDICTS
    ]
    assert actual == expected


def test_golden_totals(oracle: Any, golden: list[Any]) -> None:
    """총계 — 회복식이 `phantom` 을 **7 → 8 로 늘린다**. 줄이지 않는다.

    ★방향이 중요하다. 게이트의 위험 축은 fail-**open** 이므로(phantom 이 줄면 `window_start`
    가 앞당겨져 누적이 는다) **줄이는 교체가 위험한 교체**다. 이 단언이 반대로 뒤집히면
    「게이트를 통과시키기 쉽게」 바꾼 것이다.
    """
    summary = oracle.summarize(golden)

    assert len(golden) == 19
    assert summary.counts == {"phantom": 8, "replay_lag": 11}
    assert summary.rearm_counts == {"phantom": 7, "replay_lag": 12}
    assert summary.horizon_counts == {"phantom": 11, "replay_lag": 8}
    assert summary.recovery_overrides == 1
    assert summary.recovery_undecided == 0
    assert summary.rearm_overrides == 4
    assert summary.rearm_undecided == 0


def test_golden_recovery_phantoms_strictly_contain_the_rearm_phantoms(golden: list[Any]) -> None:
    """★★교체가 「엄격해지는 방향」임을 **집합 연산으로** 못박는다.

    총계가 7→8 이라는 것만으로는 부족하다 — 어떤 관측을 빼고 둘을 새로 넣어도 8이 된다.
    회복식의 `phantom` 집합이 재무장식의 것을 **완전히 포함**해야 「아무것도 사면(赦免)하지
    않았다」가 참이다. 이게 red 면 교체가 어딘가를 관대하게 만든 것이다.
    """
    recovery = {v.event.at for v in golden if v.recovery_label == "phantom"}
    rearm = {v.event.at for v in golden if v.rearm_label == "phantom"}

    assert rearm < recovery, f"재무장식만 phantom 인 관측이 남았다: {sorted(rearm - recovery)}"
    assert len(recovery - rearm) == 1


def test_golden_death_correlation_is_preserved(oracle: Any, golden: list[Any]) -> None:
    """★독립 검사 — 사망 4/4 가 phantom, 무해 12/12 가 생존.

    ★★**이 검사는 채택 라벨이 아니라 `rearm_label` 로 잰다.** 회복식의 phantom 은
    「다음 tick 도 어긋났다」이고 프로덕션 킬은 「연속 2회 판정된 tick」이라 거의 같은
    신호다 — 그걸로 사망 상관을 재면 동어반복이 된다. 재무장식은 **원장**에서, 사망은
    **tick 연속성**에서 오므로 그 둘만이 서로 독립이다.
    """
    summary = oracle.summarize(golden)

    assert summary.deaths_total == 4
    assert summary.deaths_labelled_phantom == 4
    assert summary.replay_lag_total == 12
    assert summary.replay_lag_survived == 12
    assert summary.death_correlation_holds


def test_golden_adopted_label_no_longer_calls_a_dying_tick_harmless(
    oracle: Any, golden: list[Any]
) -> None:
    """★채택 라벨 기준으로는 `replay_lag 11/11` 이 **정정 없이** 참이다.

    재무장식에서는 `16:24:01` 이 `replay_lag` 인데 60초 뒤 세션이 죽어, 직전 회차가
    「12/12 생존은 과장이었다」를 문서로 정정해야 했다. 회복식은 그 관측을 처음부터
    `phantom` 으로 잡으므로 **정정할 문장이 생기지 않는다.**
    """
    summary = oracle.summarize(golden)

    assert summary.adopted_replay_lag_total == 11
    assert summary.adopted_replay_lag_survived == 11
    assert summary.adopted_deaths_labelled_phantom == 4
    assert summary.adopted_death_correlation_holds


def test_golden_threshold_separation_stays_wide(oracle: Any, golden: list[Any]) -> None:
    """★`1.5 · I` 문턱의 감사 눈금 — 실측 분리가 좁아지면 여기서 먼저 red 가 난다.

    phantom 최대 간격 60.12초 vs replay_lag 최소 간격 180.20초 = **3배**. 문턱 90초는
    양쪽 어디에도 붙어 있지 않다. `ambiguous_gap_band`(tick 한 번 건너뜀 구간)가 0 인 것이
    「이 문턱이 아직 아무것도 자르지 않는다」의 증거다.
    """
    summary = oracle.summarize(golden)

    assert summary.max_phantom_gap == pytest.approx(60.12, abs=0.01)
    assert summary.min_replay_lag_gap == pytest.approx(180.20, abs=0.01)
    assert summary.ambiguous_gap_band == 0


def test_golden_window_a_is_out_of_sample_and_unchanged(oracle: Any, golden: list[Any]) -> None:
    """★두 새 규칙 모두 창 B(08-04 15:51~) 8건에서 유도했다.

    그 앞 창 A 의 **11건에서는 세 식이 11/11 일치**한다 — out-of-sample 이다.
    이 단언이 red 가 되면 「유도한 창에만 맞는 규칙」이라는 뜻이다.
    """
    window_a = [v for v in golden if v.event.at < _at("2026-08-04 15:51:00")]

    assert len(window_a) == 11
    assert all(v.label == v.horizon_label for v in window_a)
    assert all(v.recovery_label == v.horizon_label for v in window_a)
    summary = oracle.summarize(window_a)
    assert summary.rearm_overrides == 0
    assert summary.recovery_overrides == 0
