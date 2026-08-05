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
from datetime import UTC, datetime
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

    (verdict,) = oracle.adjudicate([_event(oracle, at)], {SESSION_A: _session()}, [_fill(fill_at)])

    assert verdict.label == "replay_lag"
    assert verdict.gap_seconds == pytest.approx(0.588, abs=0.001)


def test_fill_before_the_horizon_is_phantom(oracle: Any) -> None:
    """실측 `15:53:34` 재현 — 엔진이 봉을 여러 개 보고도 어긋나 있다."""
    at = datetime(2026, 8, 3, 15, 53, 34, 291000, tzinfo=UTC)
    fill_at = datetime(2026, 8, 3, 15, 38, 24, 625000, tzinfo=UTC)

    (verdict,) = oracle.adjudicate([_event(oracle, at)], {SESSION_A: _session()}, [_fill(fill_at)])

    assert verdict.label == "phantom"


# --- ★경계: 실측 최소 여유가 0.652초였다 --------------------------------------


def test_fill_exactly_at_the_horizon_is_replay_lag(oracle: Any) -> None:
    """`t_fill == horizon` 은 **무해** 쪽이다 (`>=` 이 포함).

    ★실측 최소 여유가 **0.652초**(2026-08-03 23:17)라 이 경계는 실제로 붙는다.
    부등호를 `>` 로 바꾸면 무해가 유령으로 뒤집혀 **거짓 사망**이 된다.
    """
    at = datetime(2026, 8, 3, 23, 17, 21, 979000, tzinfo=UTC)
    horizon = datetime(2026, 8, 3, 23, 17, tzinfo=UTC)

    (verdict,) = oracle.adjudicate([_event(oracle, at)], {SESSION_A: _session()}, [_fill(horizon)])

    assert verdict.horizon == horizon
    assert verdict.label == "replay_lag"


def test_one_microsecond_before_the_horizon_is_phantom(oracle: Any) -> None:
    """경계 바로 아래는 유령 — 엔진이 그 봉을 이미 재생했다."""
    at = datetime(2026, 8, 3, 23, 17, 21, 979000, tzinfo=UTC)
    fill_at = datetime(2026, 8, 3, 23, 16, 59, 999999, tzinfo=UTC)

    (verdict,) = oracle.adjudicate([_event(oracle, at)], {SESSION_A: _session()}, [_fill(fill_at)])

    assert verdict.label == "phantom"


def test_bar_boundary_and_time_threshold_disagree_below_the_horizon(oracle: Any) -> None:
    """★두 술어는 **동치가 아니다** — 실측 11건에서 우연히 일치했을 뿐이다.

    체결이 60초 안(경과 46초)이지만 봉 경계 **아래**면 엔진은 그 봉을 이미 봤다.
    ⇒ 봉경계식 `phantom` vs 시간문턱식 `replay_lag`. 시간문턱식이 유령을 놓친다.
    """
    at = datetime(2026, 8, 3, 10, 12, 36, tzinfo=UTC)
    fill_at = datetime(2026, 8, 3, 10, 11, 50, tzinfo=UTC)

    (verdict,) = oracle.adjudicate([_event(oracle, at)], {SESSION_A: _session()}, [_fill(fill_at)])

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

    (verdict,) = oracle.adjudicate(
        [_event(oracle, at)], {SESSION_A: _session()}, [_fill(fill_at, session_id=None)]
    )

    assert verdict.label == "unattributed"
    assert verdict.last_fill_at is None


def test_another_sessions_fill_is_not_attributed(oracle: Any) -> None:
    """세션 귀속은 `idempotency_key` 로만 한다 — 다른 세션의 체결을 빌려오지 않는다."""
    at = datetime(2026, 8, 4, 4, 17, 8, 667000, tzinfo=UTC)
    fill_at = datetime(2026, 8, 4, 4, 17, 8, 79000, tzinfo=UTC)

    (verdict,) = oracle.adjudicate(
        [_event(oracle, at)],
        {SESSION_A: _session()},
        [_fill(fill_at, session_id=SESSION_B)],
    )

    assert verdict.label == "unattributed"


def test_fill_on_another_symbol_is_not_attributed(oracle: Any) -> None:
    at = datetime(2026, 8, 4, 4, 17, 8, 667000, tzinfo=UTC)
    fill_at = datetime(2026, 8, 4, 4, 17, 8, 79000, tzinfo=UTC)

    (verdict,) = oracle.adjudicate(
        [_event(oracle, at)],
        {SESSION_A: _session()},
        [_fill(fill_at, symbol="ETH/USDT")],
    )

    assert verdict.label == "unattributed"


def test_fill_after_the_observation_is_ignored(oracle: Any) -> None:
    """관측 뒤에 난 체결로 과거를 판정하지 않는다."""
    at = datetime(2026, 8, 4, 4, 17, 8, tzinfo=UTC)

    (verdict,) = oracle.adjudicate(
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

    (verdict,) = oracle.adjudicate([_event(oracle, at)], {SESSION_A: _session()}, [late, early])

    assert verdict.last_fill_at == late["filled_at"]
    assert verdict.label == "replay_lag"


# --- interval 일반화 (실측은 전부 1m 이었다) -----------------------------------


def test_horizon_follows_the_session_interval(oracle: Any) -> None:
    """5m 세션에서는 5분 봉이 지평이다 — 1m 기준으로 판정하면 유령을 놓친다."""
    at = datetime(2026, 8, 4, 4, 17, 8, tzinfo=UTC)
    fill_at = datetime(2026, 8, 4, 4, 16, tzinfo=UTC)

    (one_minute,) = oracle.adjudicate(
        [_event(oracle, at)], {SESSION_A: _session(interval="1m")}, [_fill(fill_at)]
    )
    (five_minute,) = oracle.adjudicate(
        [_event(oracle, at)], {SESSION_A: _session(interval="5m")}, [_fill(fill_at)]
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

    verdicts = oracle.adjudicate(
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
    """★음성 대조 — 무해 판정이 사망과 겹치면 판별식을 기각해야 한다.

    이 단언이 없으면 `death_correlation_holds` 가 언제나 참인 동어반복일 수 있다.
    """
    at = datetime(2026, 8, 4, 4, 17, 8, 667000, tzinfo=UTC)
    sess = _session(deactivated_at=at, deactivated_reason="position_divergence")
    fill_at = datetime(2026, 8, 4, 4, 17, 8, 79000, tzinfo=UTC)

    verdicts = oracle.adjudicate([_event(oracle, at)], {SESSION_A: sess}, [_fill(fill_at)])

    assert verdicts[0].label == "replay_lag"
    assert verdicts[0].died_here is True
    assert oracle.summarize(verdicts).death_correlation_holds is False


def test_unknown_session_raises_instead_of_silently_dropping(oracle: Any) -> None:
    """분모가 말없이 줄어드는 것을 막는다."""
    at = datetime(2026, 8, 4, 4, 17, 8, tzinfo=UTC)
    with pytest.raises(ValueError):
        oracle.adjudicate([_event(oracle, at)], {}, [])


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
