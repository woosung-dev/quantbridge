# 진입 완결성 분해의 전수성·상호배타성과, 판정이 숫자를 바꾸는 지점을 고정한다

"""BL-536 계측기 대조군.

★이 파일이 지키는 것은 "코드가 돈다" 가 아니라 **"틀린 판정과 맞는 판정이 서로 다른
숫자를 낸다"** 이다. 그래서 픽스처는 아래 행들을 반드시 포함한다 — 그 행이 없으면
표적 변이가 **동치**가 되어 통과하고, 우리는 "테스트가 있다" 고 잘못 믿는다.

| 필요 행                                    | 없으면 동치가 되는 변이            |
| ------------------------------------------ | ---------------------------------- |
| 같은 trade_id 에 체결이 **2 개 이상**      | M1 에피소드 구간 끊기 제거         |
| **부분체결 후 `cancelled`**                | M3 has_fill 을 state=='filled' 로  |
| `condmkt` 체결이 **유일한 체결**인 에피소드 | M4 키 파서가 condmkt 거부          |
| `idempotency_key` 가 남의 세션 / NULL      | M7 귀속 불가 행 조용히 버리기      |
| `filled` 인데 수량 판독 불가               | has_fill 에 state 를 OR 로 얹기    |
"""

from __future__ import annotations

import random
import re
from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from src.trading.entry_completeness import (
    CANONICAL_PREDICATES,
    ENTRY_RACE_REJECTION_BASELINE,
    ENTRY_RACE_REJECTION_THRESHOLD,
    AttemptBucket,
    AttemptFact,
    Attribution,
    EntryRaceRejectionAttempt,
    EpisodeOutcome,
    EpisodeRule,
    MeasurementQuestion,
    PopulationRow,
    RejectionOrigin,
    RestingInterval,
    assert_partitions,
    build_episode_layer,
    build_population_tally,
    build_report,
    classify_attempt,
    classify_attempts,
    classify_rejection_origin,
    count_entry_race_rejections_by_utc_day,
    max_concurrent_resting,
)
from src.trading.models import OrderState
from src.trading.services.conditional_entry_planner import (
    build_conditional_entry_key,
    build_market_converted_entry_key,
)

SESSION_ID = UUID("a0861954-1c7c-4a27-bfee-6f6af1a4d440")
OTHER_SESSION_ID = UUID("b0861954-1c7c-4a27-bfee-6f6af1a4d440")
SINCE = datetime(2026, 7, 29, 0, 0, tzinfo=UTC)
UNTIL = datetime(2026, 7, 30, 0, 0, tzinfo=UTC)
QUERIED_AT = datetime(2026, 7, 30, 0, 5, tzinfo=UTC)


def test_every_question_has_a_canonical_predicate() -> None:
    assert set(CANONICAL_PREDICATES) == set(MeasurementQuestion)


def test_each_question_names_the_other_question_predicate_as_its_trap() -> None:
    population = CANONICAL_PREDICATES[MeasurementQuestion.conditional_population]
    truncation = CANONICAL_PREDICATES[MeasurementQuestion.resting_truncation_risk]

    assert population.trap == truncation.predicate
    assert truncation.trap == population.predicate


def test_canonical_predicate_cards_cite_code_not_line_numbers() -> None:
    assert all(
        re.search(r":\d+", predicate.evidence) is None
        for predicate in CANONICAL_PREDICATES.values()
    )


def test_population_tally_uses_parser_for_kind_and_utc_created_at() -> None:
    cond_key = build_conditional_entry_key(
        SESSION_ID,
        "PopulationCond",
        SINCE,
        Decimal("64000"),
        Decimal("0.029"),
    )
    condmkt_key = build_market_converted_entry_key(
        SESSION_ID,
        "PopulationCondmkt",
        SINCE,
        Decimal("64000"),
        Decimal("0.029"),
    )
    assert cond_key is not None
    assert condmkt_key is not None

    tally = build_population_tally(
        (
            PopulationRow(idempotency_key=cond_key, created_at=SINCE),
            PopulationRow(
                idempotency_key=condmkt_key,
                created_at=datetime(2026, 7, 29, 9, tzinfo=UTC),
            ),
            PopulationRow(idempotency_key="live:malformed", created_at=SINCE),
        )
    )

    assert (tally.cond, tally.condmkt, tally.total, tally.unattributable) == (1, 1, 2, 1)
    assert tally.created_by_utc_day == ((date(2026, 7, 29), 2),)


def test_max_concurrent_resting_counts_carry_in_and_open_intervals() -> None:
    strategy_id = uuid4()
    account_id = uuid4()
    peak = max_concurrent_resting(
        (
            RestingInterval(
                strategy_id=strategy_id,
                exchange_account_id=account_id,
                created_at=SINCE - timedelta(minutes=1),
                closed_at=SINCE + timedelta(minutes=1),
            ),
            RestingInterval(
                strategy_id=strategy_id,
                exchange_account_id=account_id,
                created_at=SINCE + timedelta(minutes=1),
                closed_at=SINCE + timedelta(minutes=2),
            ),
            RestingInterval(
                strategy_id=strategy_id,
                exchange_account_id=account_id,
                created_at=SINCE + timedelta(minutes=3),
                closed_at=None,
            ),
            RestingInterval(
                strategy_id=strategy_id,
                exchange_account_id=account_id,
                created_at=SINCE + timedelta(minutes=4),
                closed_at=SINCE + timedelta(minutes=5),
            ),
        )
    )

    assert peak == {(strategy_id, account_id): 2}


def test_recorded_baseline_floor_covers_every_excluded_day() -> None:
    baseline = ENTRY_RACE_REJECTION_BASELINE
    assert baseline.excluded_through.date() > max(day for day, _count in baseline.observed)


def test_recorded_baseline_excludes_only_threshold_exceeding_days() -> None:
    assert all(
        count >= ENTRY_RACE_REJECTION_THRESHOLD
        for _day, count in ENTRY_RACE_REJECTION_BASELINE.observed
    )


def test_recorded_baseline_observations_do_not_trigger_again() -> None:
    baseline = ENTRY_RACE_REJECTION_BASELINE
    attempts = tuple(
        EntryRaceRejectionAttempt(
            created_at=datetime(day.year, day.month, day.day, 12, tzinfo=UTC),
            state=OrderState.rejected,
            error_message='{"retCode":110092,"retMsg":"expect Rising"}',
        )
        for day, count in baseline.observed
        for _ in range(count)
    )

    tally = count_entry_race_rejections_by_utc_day(attempts, baseline)

    assert tally.triggered_days == ()


def test_entry_race_rejections_surface_unknown_origin_as_unmeasured() -> None:
    baseline = ENTRY_RACE_REJECTION_BASELINE
    attempts = (
        EntryRaceRejectionAttempt(
            created_at=baseline.excluded_through + timedelta(hours=1),
            state=OrderState.rejected,
            error_message='{"retCode":110092,"retMsg":"expect Rising"}',
        ),
        EntryRaceRejectionAttempt(
            created_at=baseline.excluded_through + timedelta(days=1),
            state=OrderState.rejected,
            error_message="rejection payload omitted retCode",
        ),
        EntryRaceRejectionAttempt(
            created_at=baseline.excluded_through + timedelta(days=1, hours=1),
            state=OrderState.rejected,
            error_message="credential_decrypt_failed: key unavailable",
        ),
    )

    tally = count_entry_race_rejections_by_utc_day(attempts, baseline)

    assert tally.matched_by_utc_day == ((date(2026, 7, 29), 1),)
    assert tally.unmeasured_by_utc_day == ((date(2026, 7, 30), 1),)
    assert (tally.not_matched, tally.candidates, tally.triggered_days) == (1, 3, ())


def _bar(minutes: int) -> datetime:
    return SINCE + timedelta(minutes=minutes)


def _fact(
    *,
    trade_id: str,
    minutes: int,
    state: OrderState,
    filled_quantity: str | None = None,
    kind: str = "cond",
    session_id: UUID = SESSION_ID,
    key_session_id: UUID | None = None,
    idempotency_key: str | None = "<build>",
    terminal_at: datetime | None = None,
    error_message: str | None = None,
) -> AttemptFact:
    bar_time = _bar(minutes)
    if idempotency_key == "<build>":
        builder = (
            build_market_converted_entry_key if kind == "condmkt" else build_conditional_entry_key
        )
        idempotency_key = builder(
            key_session_id or session_id, trade_id, bar_time, Decimal("64000"), Decimal("0.029")
        )
    terminal = terminal_at
    if terminal is None and state in (OrderState.filled, OrderState.rejected, OrderState.cancelled):
        terminal = bar_time + timedelta(seconds=30)
    return AttemptFact(
        order_id=uuid4(),
        session_id=session_id,
        idempotency_key=idempotency_key,
        state=state,
        quantity=Decimal("0.029"),
        filled_quantity=None if filled_quantity is None else Decimal(filled_quantity),
        created_at=bar_time,
        terminal_at=terminal,
        error_message=error_message,
    )


def _soak_like_facts() -> list[AttemptFact]:
    """실측 24h 표본의 모양을 그대로 옮긴 픽스처 + 변이 판별용 행."""
    return [
        # --- LE: cancelled -> rejected -> filled -> (부분체결 cancelled) -> cancelled ---
        _fact(trade_id="PivRevLE", minutes=1, state=OrderState.cancelled),
        _fact(
            trade_id="PivRevLE",
            minutes=2,
            state=OrderState.rejected,
            error_message='{"retCode":110092,"retMsg":"expect Rising"}',
        ),
        _fact(trade_id="PivRevLE", minutes=3, state=OrderState.filled, filled_quantity="0.029"),
        # ★M3 판별 행 — 부분체결을 보존한 채 cancelled. state 로 판정하면 유실로 오분류된다.
        _fact(trade_id="PivRevLE", minutes=4, state=OrderState.cancelled, filled_quantity="0.011"),
        _fact(trade_id="PivRevLE", minutes=5, state=OrderState.cancelled),
        # --- SE: cancelled -> condmkt 체결 (★M4 판별 — 유일한 체결이 condmkt) ---
        _fact(trade_id="PivRevSE", minutes=6, state=OrderState.cancelled),
        _fact(
            trade_id="PivRevSE",
            minutes=7,
            kind="condmkt",
            state=OrderState.filled,
            filled_quantity="0.02",
        ),
        # --- OP: 아직 살아 있다 ---
        _fact(trade_id="PivRevOP", minutes=8, state=OrderState.submitted),
        # --- UR: filled 인데 수량 판독 불가 -> open (성공도 유실도 아니다) ---
        _fact(trade_id="PivRevUR", minutes=9, state=OrderState.filled, filled_quantity=None),
        # --- 귀속 불가 (★M7 판별) ---
        _fact(
            trade_id="Foreign",
            minutes=10,
            state=OrderState.filled,
            filled_quantity="0.5",
            key_session_id=OTHER_SESSION_ID,
        ),
        _fact(trade_id="Webhook", minutes=11, state=OrderState.cancelled, idempotency_key=None),
        # --- 비조건부 우리 것 (시장가 진입 key) ---
        _fact(
            trade_id="MarketLE",
            minutes=12,
            state=OrderState.filled,
            filled_quantity="0.03",
            idempotency_key=f"live:{SESSION_ID}:{_bar(12).isoformat()}:1:entry:MarketLE",
        ),
    ]


# --- ②-c 전수성 / 상호배타성 -------------------------------------------------


def test_layer_one_buckets_partition_every_row() -> None:
    report = build_report(
        _soak_like_facts(),
        session_id=SESSION_ID,
        since=SINCE,
        until=UNTIL,
        queried_at=QUERIED_AT,
        truncated=False,
    )
    layer = report.scope_attempts
    assert (
        layer.has_fill + layer.rejected + layer.cancelled + layer.open == layer.total
    ), "층위 1 네 버킷은 행 수를 정확히 분할해야 한다"
    assert layer.total == len(_soak_like_facts())


def test_layer_one_partition_holds_for_random_inputs() -> None:
    """★고정 픽스처 하나로는 전수성을 증명하지 못한다 - 상태 조합을 훑는다.

    seed 를 박아 실패가 재현 가능하게 한다(무작위 실패는 조사 불가능한 red 다).
    """
    rng = random.Random(536)
    states = list(OrderState)
    quantities = [None, "0", "0.001", "0.029"]
    for case in range(300):
        facts = [
            _fact(
                trade_id=rng.choice(["A", "B", "C"]),
                minutes=index,
                state=rng.choice(states),
                filled_quantity=rng.choice(quantities),
                kind=rng.choice(["cond", "condmkt"]),
                key_session_id=rng.choice([SESSION_ID, OTHER_SESSION_ID]),
            )
            for index in range(rng.randint(1, 12))
        ]
        report = build_report(
            facts,
            session_id=SESSION_ID,
            since=SINCE,
            until=UNTIL,
            queried_at=QUERIED_AT,
            truncated=False,
        )
        layer = report.scope_attempts
        assert (
            layer.has_fill + layer.rejected + layer.cancelled + layer.open == layer.total == len(facts)
        ), f"case {case}: 층위 1 분할이 깨졌다"
        assert report.attribution.total == len(facts), f"case {case}: 귀속 분할이 깨졌다"
        for episode_layer in (report.primary, report.alternative):
            assert (
                episode_layer.won
                + episode_layer.lost
                + episode_layer.abandoned
                + episode_layer.open
                == episode_layer.total
            ), f"case {case}: 층위 2 분할이 깨졌다"
            # 에피소드는 조건부 행을 정확히 덮는다 - 행을 잃지도 겹치지도 않는다.
            covered = [
                order_id
                for episode in episode_layer.episodes
                for order_id in episode.order_ids
            ]
            conditional = [
                attempt.fact.order_id
                for attempt in classify_attempts(facts, since=SINCE, until=UNTIL)
                if attempt.attribution is Attribution.conditional_ours
            ]
            assert sorted(map(str, covered)) == sorted(map(str, conditional)), (
                f"case {case}: 에피소드가 조건부 행을 덮지 못한다"
            )


# --- ②-a has_fill 판정 (M3 / 판독 불가) --------------------------------------


def test_partial_fill_preserved_on_cancelled_row_counts_as_fill() -> None:
    """★M3 — `state == 'filled'` 로 판정하면 이 행이 유실로 오분류된다."""
    fact = _fact(
        trade_id="PivRevLE", minutes=4, state=OrderState.cancelled, filled_quantity="0.011"
    )
    assert classify_attempt(fact) is AttemptBucket.has_fill


def test_filled_row_without_readable_quantity_is_not_a_win() -> None:
    """판독 불가를 성공으로 바꾸지 않는다. `open` 이라 분자에도 분모에도 안 들어간다."""
    fact = _fact(trade_id="PivRevUR", minutes=9, state=OrderState.filled, filled_quantity=None)
    assert classify_attempt(fact) is AttemptBucket.open
    zero_fill = _fact(trade_id="PivRevUR", minutes=9, state=OrderState.filled, filled_quantity="0")
    assert classify_attempt(zero_fill) is AttemptBucket.open


def test_unreadable_terminal_is_surfaced_not_hidden() -> None:
    report = build_report(
        _soak_like_facts(),
        session_id=SESSION_ID,
        since=SINCE,
        until=UNTIL,
        queried_at=QUERIED_AT,
        truncated=False,
    )
    assert report.conditional_attempts.unreadable_terminal == 1


# --- ②-b 에피소드 (M1) --------------------------------------------------------


def test_fill_closes_the_episode_so_one_trade_id_yields_many() -> None:
    """★M1 — 체결에서 끊지 않으면 `PivRevLE` 다섯 행이 에피소드 1 개가 된다.

    실측이 이 함정을 확정했다 — 24h 진입 42 주문에 trade_id 는 단 2 개였다. 끊지 않으면
    표본 전체가 에피소드 2 개가 되고 둘 다 체결을 포함해 **유실률이 0% 로 소멸**한다.
    """
    conditional = [
        attempt
        for attempt in classify_attempts(_soak_like_facts(), since=SINCE, until=UNTIL)
        if attempt.attribution is Attribution.conditional_ours
    ]
    layer = build_episode_layer(conditional, rule=EpisodeRule.fill_closes, label="t")
    le_episodes = [episode for episode in layer.episodes if episode.trade_id == "PivRevLE"]
    assert len(le_episodes) == 3, "체결 2 개가 구간을 두 번 끊어 3 구간이 나와야 한다"
    assert [episode.outcome for episode in le_episodes] == [
        EpisodeOutcome.won,
        EpisodeOutcome.won,
        EpisodeOutcome.abandoned,
    ]


def test_condmkt_fill_wins_the_episode() -> None:
    """★M4 — 키 파서가 `condmkt` 를 거부하면 이 에피소드의 유일한 체결이 사라진다."""
    conditional = [
        attempt
        for attempt in classify_attempts(_soak_like_facts(), since=SINCE, until=UNTIL)
        if attempt.attribution is Attribution.conditional_ours
    ]
    layer = build_episode_layer(conditional, rule=EpisodeRule.fill_closes, label="t")
    se_episodes = [episode for episode in layer.episodes if episode.trade_id == "PivRevSE"]
    assert len(se_episodes) == 1
    assert se_episodes[0].outcome is EpisodeOutcome.won
    assert "condmkt" in se_episodes[0].kinds


# --- ②-d 모호 케이스: 두 해석이 서로 다른 숫자를 낸다 -------------------------


def test_ambiguous_reject_then_later_fill_is_reported_under_both_rules() -> None:
    """실측 `PivRevSE` 07:53 rejected -> 07:56/57 cancelled -> 08:07 filled.

    채택 규칙은 `won` 1 개, 반대 해석은 `lost` 1 + `won` 1. **두 숫자를 함께 내지 않으면
    한쪽이 거짓말이 된다** — 그래서 이 테스트가 둘의 값이 실제로 다름을 고정한다.
    """
    facts = [
        _fact(
            trade_id="PivRevSE",
            minutes=53,
            state=OrderState.rejected,
            error_message='{"retCode":110093,"retMsg":"expect Falling"}',
        ),
        _fact(trade_id="PivRevSE", minutes=56, state=OrderState.cancelled),
        _fact(trade_id="PivRevSE", minutes=57, state=OrderState.cancelled),
        _fact(trade_id="PivRevSE", minutes=67, state=OrderState.filled, filled_quantity="0.029"),
    ]
    report = build_report(
        facts,
        session_id=SESSION_ID,
        since=SINCE,
        until=UNTIL,
        queried_at=QUERIED_AT,
        truncated=False,
    )

    assert (report.primary.total, report.primary.won, report.primary.lost) == (1, 1, 0)
    assert report.primary.loss_rate == Decimal("0")

    assert (report.alternative.total, report.alternative.won, report.alternative.lost) == (2, 1, 1)
    assert report.alternative.loss_rate == Decimal("1") / Decimal("2")

    assert report.primary.loss_rate != report.alternative.loss_rate, (
        "두 해석이 같은 숫자를 내면 함께 출력할 이유가 없다 - 판별력이 없다는 뜻이다"
    )


# --- ②-f 귀속 (M7) ------------------------------------------------------------


def test_rows_that_are_not_ours_are_counted_not_dropped() -> None:
    """★M7 — 조용히 버리면 분모가 거짓말한다. 남의 세션과 우리 시장가 진입을 구분한다."""
    report = build_report(
        _soak_like_facts(),
        session_id=SESSION_ID,
        since=SINCE,
        until=UNTIL,
        queried_at=QUERIED_AT,
        truncated=False,
    )
    assert report.attribution.unattributable == 2, "남의 세션 1 + key 없는 웹훅 1"
    assert report.attribution.nonconditional_ours == 1, "우리 시장가 진입은 외부 주문이 아니다"
    assert report.attribution.conditional_ours == 9
    assert report.attribution.total == report.scope_attempts.total
    # 조건부 분모에서 둘 다 빠졌는지 - 층위 1 은 전량, 조건부 층은 조건부만.
    assert report.conditional_attempts.total == 9
    assert report.scope_attempts.total == 12


def test_foreign_rows_never_join_our_episodes() -> None:
    """남의 세션 행이 같은 trade_id 를 써도 우리 에피소드에 섞이면 안 된다."""
    facts = [
        _fact(trade_id="Shared", minutes=1, state=OrderState.cancelled),
        _fact(
            trade_id="Shared",
            minutes=2,
            state=OrderState.filled,
            filled_quantity="0.029",
            key_session_id=OTHER_SESSION_ID,
        ),
    ]
    report = build_report(
        facts,
        session_id=SESSION_ID,
        since=SINCE,
        until=UNTIL,
        queried_at=QUERIED_AT,
        truncated=False,
    )
    assert report.primary.total == 1
    assert report.primary.episodes[0].outcome is EpisodeOutcome.abandoned, (
        "남의 체결이 우리 유실을 덮으면 안 된다"
    )


# --- ②-e 시간 왜곡 -------------------------------------------------------------


def test_terminal_outside_window_is_marked_deferred_and_split_out() -> None:
    """창 밖에서 종결된 행은 이 창의 표로 재현 불가능하다 - 별도로 센다."""
    facts = [
        _fact(
            trade_id="Late",
            minutes=10,
            state=OrderState.filled,
            filled_quantity="0.029",
            terminal_at=UNTIL + timedelta(minutes=5),
        ),
        _fact(trade_id="InWindow", minutes=11, state=OrderState.rejected),
    ]
    report = build_report(
        facts,
        session_id=SESSION_ID,
        since=SINCE,
        until=UNTIL,
        queried_at=QUERIED_AT,
        truncated=False,
    )
    assert report.conditional_attempts.verdict_deferred == 1
    # 전체 유실률과 "창 안 완전 종결분" 유실률이 서로 다른 값을 낸다.
    assert report.primary.loss_rate == Decimal("1") / Decimal("2")
    assert report.primary.settled_loss_rate == Decimal("1")
    assert report.primary.settled_resolved == 1


def test_open_episode_is_not_declared_lost() -> None:
    """아직 살아 있는 시도를 유실로 단정하지 않는다 (fail-closed)."""
    facts = [
        _fact(trade_id="Alive", minutes=1, state=OrderState.cancelled),
        _fact(trade_id="Alive", minutes=2, state=OrderState.submitted),
    ]
    report = build_report(
        facts,
        session_id=SESSION_ID,
        since=SINCE,
        until=UNTIL,
        queried_at=QUERIED_AT,
        truncated=False,
    )
    assert report.primary.total == 1
    assert report.primary.episodes[0].outcome is EpisodeOutcome.open
    assert report.primary.loss_rate is None, "분모가 0 이면 비율이 없다 - 0% 가 아니다"


# --- 시도 거절률 + retCode ------------------------------------------------------


def test_confirmed_rejection_rate_uses_the_verdict_denominator() -> None:
    """★분모는 "거래소 도달" 이 아니라 "**판정으로 종결**" 이다 (R2-⑦).

    Bybit 는 조건부·시장가 주문을 모두 `submitted` 로 수락하고 `cancelled` 행도
    거래소가 이미 보유하던 것이다. 그래서 `has_fill + rejected` 는 "도달" 이 아니다.
    """
    report = build_report(
        _soak_like_facts(),
        session_id=SESSION_ID,
        since=SINCE,
        until=UNTIL,
        queried_at=QUERIED_AT,
        truncated=False,
    )
    layer = report.conditional_attempts
    assert (layer.has_fill, layer.rejected) == (3, 1)
    assert layer.rejected_exchange == 1, "retCode 가 있으므로 거래소 확정 거절"
    assert layer.exchange_verdicted == 4
    assert layer.confirmed_rejection_rate == Decimal("1") / Decimal("4")
    assert layer.rejected_ret_codes == (("110092", 1),)


# --- R2-③ open 이 확정 거절을 삼키지 못하게 -----------------------------------


def test_open_episode_keeps_the_rejection_it_swallowed() -> None:
    """★활성 세션에서 유실률이 구조적으로 0 이 되는 경로를 막는다.

    조회 시각에 resting `submitted` 가 있으면 `fill_closes` 는 마지막 체결 이후 전부를
    한 구간으로 묶는다. 그 구간에 확정 거절이 있어도 판정은 `open` 이다(fail-closed).
    ★그 자체는 옳다. 문제는 **그 결과가 안 보인다**는 것이었다.
    """
    facts = [
        _fact(
            trade_id="PivRevSE",
            minutes=1,
            state=OrderState.rejected,
            error_message='{"retCode":110093,"retMsg":"expect Falling"}',
        ),
        _fact(trade_id="PivRevSE", minutes=2, state=OrderState.submitted),
    ]
    report = build_report(
        facts,
        session_id=SESSION_ID,
        since=SINCE,
        until=UNTIL,
        queried_at=QUERIED_AT,
        truncated=False,
    )
    layer = report.primary
    assert layer.total == 1
    assert layer.episodes[0].outcome is EpisodeOutcome.open, "유실을 단정하지 않는다"
    # ★그러나 거절이 있었다는 사실은 남는다.
    assert layer.episodes[0].had_rejection is True
    assert layer.open_with_prior_rejection == 1
    # ★그리고 비율은 잠정으로 표시된다.
    assert layer.provisional is True
    assert layer.loss_rate is None, "resolved 가 0 이면 비율이 없다"


def test_rate_is_provisional_whenever_any_episode_is_open() -> None:
    facts = [
        _fact(trade_id="Done", minutes=1, state=OrderState.filled, filled_quantity="0.029"),
        _fact(trade_id="Alive", minutes=2, state=OrderState.submitted),
    ]
    report = build_report(
        facts,
        session_id=SESSION_ID,
        since=SINCE,
        until=UNTIL,
        queried_at=QUERIED_AT,
        truncated=False,
    )
    assert report.primary.open == 1
    assert report.primary.provisional is True
    assert report.primary.loss_rate == Decimal("0"), "지금은 0 이지만 **하한**이다"


# --- R2-⑥ 거래소에 닿지 못한 실패는 유실이 아니다 -----------------------------


def _local_failure_fact(trade_id: str, minutes: int) -> AttemptFact:
    return _fact(
        trade_id=trade_id,
        minutes=minutes,
        state=OrderState.rejected,
        error_message="credential_decrypt_failed: InvalidToken",
    )


def test_local_failure_is_not_counted_as_an_entry_loss() -> None:
    """★(a) 유실률 분자에 안 들어간다 — 우리 인프라 장애가 진입 유실로 위장하면 안 된다."""
    report = build_report(
        [_local_failure_fact("PivRevLE", 1)],
        session_id=SESSION_ID,
        since=SINCE,
        until=UNTIL,
        queried_at=QUERIED_AT,
        truncated=False,
    )
    assert report.primary.lost == 0
    assert report.primary.abandoned == 1
    assert report.primary.loss_rate == Decimal("0")
    # 확정 거절률의 분자·분모 어디에도 안 들어간다.
    assert report.conditional_attempts.exchange_verdicted == 0
    assert report.conditional_attempts.confirmed_rejection_rate is None


def test_local_failure_is_still_visible() -> None:
    """★(b) 조용히 사라지지도 않는다."""
    report = build_report(
        [_local_failure_fact("PivRevLE", 1)],
        session_id=SESSION_ID,
        since=SINCE,
        until=UNTIL,
        queried_at=QUERIED_AT,
        truncated=False,
    )
    layer = report.conditional_attempts
    assert layer.rejected == 1, "여전히 rejected 버킷에 있다 (전수성 유지)"
    assert (layer.rejected_local, layer.rejected_exchange, layer.rejected_unknown) == (1, 0, 0)
    assert report.primary.episodes[0].had_local_failure is True


def test_rejection_origin_reads_retcode_through_our_wrapper_prefix() -> None:
    """`provider_failure: {...retCode...}` 처럼 우리 문구가 앞에 붙어도 거래소 확정이다."""
    assert (
        classify_rejection_origin('provider_failure: {"retCode":110093,"retMsg":"x"}')
        is RejectionOrigin.exchange
    )
    assert (
        classify_rejection_origin("credential_decrypt_failed: InvalidToken")
        is RejectionOrigin.local
    )
    assert (
        classify_rejection_origin("unexpected non-CCXT error: RuntimeError")
        is RejectionOrigin.local
    )
    # ★모르는 것은 거래소 거절이라고 **주장하지 않는다**.
    assert classify_rejection_origin("exchange_rejected_after_submission") is (
        RejectionOrigin.unknown
    )
    assert classify_rejection_origin(None) is RejectionOrigin.unknown


def test_unknown_origin_still_counts_as_loss_but_is_flagged() -> None:
    """★비동기 확정 거절이 retCode 를 안 싣는 선재 결함 때문에 유실 쪽에 남긴다.

    빼면 진짜 유실을 감춘다. 대신 `lost_with_unknown_origin` 으로 항상 표면화한다.
    """
    report = build_report(
        [
            _fact(
                trade_id="PivRevLE",
                minutes=1,
                state=OrderState.rejected,
                error_message="exchange_rejected_after_submission",
            )
        ],
        session_id=SESSION_ID,
        since=SINCE,
        until=UNTIL,
        queried_at=QUERIED_AT,
        truncated=False,
    )
    assert report.primary.lost == 1
    assert report.primary.lost_with_unknown_origin == 1
    assert report.conditional_attempts.rejected_unknown == 1


# --- R2-⑨ 문서화된 불변식을 실제로 집행한다 -----------------------------------


def test_assert_partitions_rejects_a_broken_attempt_layer() -> None:
    """★주석이 "잠근다" 고 적었으면 실제로 잠가야 한다."""
    good = build_report(
        _soak_like_facts(),
        session_id=SESSION_ID,
        since=SINCE,
        until=UNTIL,
        queried_at=QUERIED_AT,
        truncated=False,
    ).scope_attempts
    assert_partitions(good)  # 통과

    broken = replace(good, has_fill=good.has_fill + 1)
    with pytest.raises(ValueError, match="층위 1 분할 위반"):
        assert_partitions(broken)

    origin_broken = replace(good, rejected_exchange=good.rejected_exchange + 1)
    with pytest.raises(ValueError, match="거절 출처 분할 위반"):
        assert_partitions(origin_broken)


def test_assert_partitions_rejects_a_broken_episode_layer() -> None:
    good = build_report(
        _soak_like_facts(),
        session_id=SESSION_ID,
        since=SINCE,
        until=UNTIL,
        queried_at=QUERIED_AT,
        truncated=False,
    ).primary
    assert_partitions(good)

    with pytest.raises(ValueError, match="층위 2 분할 위반"):
        assert_partitions(replace(good, won=good.won + 1))


def test_assert_partitions_is_not_an_assert_statement() -> None:
    """★`python -O` 가 지우는 `assert` 면 프로덕션에서만 가드가 사라진다."""
    import inspect

    source = inspect.getsource(assert_partitions)
    assert "raise ValueError" in source
    assert "\n    assert " not in source


def test_builders_actually_call_the_partition_guard(monkeypatch: pytest.MonkeyPatch) -> None:
    """★R2-⑨ 의 배선 테스트 — 함수가 존재하는 것과 **불려지는 것**은 다르다.

    가드를 구현해 놓고 빌더에서 호출하지 않으면 파티션은 여전히 우연이다. 직접 호출
    테스트만 있으면 그 배선 제거가 조용히 통과한다(실측: 변이 R2-M9 탈출).
    """
    import src.trading.entry_completeness as module

    calls: list[str] = []
    original = module.assert_partitions

    def _spy(layer: object) -> None:
        calls.append(type(layer).__name__)
        original(layer)  # type: ignore[arg-type]

    monkeypatch.setattr(module, "assert_partitions", _spy)
    module.build_report(
        _soak_like_facts(),
        session_id=SESSION_ID,
        since=SINCE,
        until=UNTIL,
        queried_at=QUERIED_AT,
        truncated=False,
    )

    assert calls.count("AttemptLayer") >= 2, "층위 1 은 전량·조건부 두 번 만든다"
    assert calls.count("EpisodeLayer") >= 2, "층위 2 는 규칙 두 개를 만든다"


# --- R3-① 저장 형식(래핑 접두사)으로 분류한다 ---------------------------------


def test_wrapped_local_failure_is_classified_local() -> None:
    """★R2-⑥ 이 절반만 고쳤던 자리 (R3-①).

    `tasks/trading.py` 는 provider 예외를 `f"provider_failure: {e}"` 로 **감싸서** 저장한다.
    그래서 원장의 실제 값은 아래 형태이고, prefix 를 원문에 그냥 대면 통과하지 못해
    `unknown` -> `lost` 로 계상된다 = 우리 장애가 다시 진입 유실로 위장한다.

    ★내 R2 테스트는 **래핑되지 않은** 형태만 단언해서 이걸 못 잡았다 — 원장에 실제로
    저장되는 형태로 테스트하지 않으면 그 단언은 프로덕션 라인을 실행하지 않는다.
    """
    assert (
        classify_rejection_origin("provider_failure: unexpected non-CCXT error: RuntimeError")
        is RejectionOrigin.local
    )
    # 래핑 없는 경로(자격증명)는 예전에도 작동했다 — 회귀 방지로 함께 잠근다.
    assert (
        classify_rejection_origin("credential_decrypt_failed: InvalidToken")
        is RejectionOrigin.local
    )


def test_wrapped_exchange_rejection_still_wins_over_the_prefix() -> None:
    """retCode 가 있으면 래핑을 벗기기 **전에** 거래소 확정이다 — 순서가 뒤집히면 안 된다."""
    assert (
        classify_rejection_origin('provider_failure: {"retCode":110093,"retMsg":"expect Falling"}')
        is RejectionOrigin.exchange
    )


def test_unknown_is_not_promoted_to_exchange_rejection() -> None:
    """★fail-closed 유지 — 모르는 것을 거래소 거절로 승격시키지 않는다."""
    assert (
        classify_rejection_origin("provider_failure: something we have never seen")
        is RejectionOrigin.unknown
    )
    assert classify_rejection_origin("exchange_rejected_after_submission") is (
        RejectionOrigin.unknown
    )


def test_wrapped_local_failure_is_not_counted_as_loss_end_to_end() -> None:
    """분류만이 아니라 **유실률까지** 실제로 바뀌는지 — 라벨만 고치고 끝나면 의미가 없다."""
    report = build_report(
        [
            _fact(
                trade_id="PivRevLE",
                minutes=1,
                state=OrderState.rejected,
                error_message="provider_failure: unexpected non-CCXT error: RuntimeError",
            )
        ],
        session_id=SESSION_ID,
        since=SINCE,
        until=UNTIL,
        queried_at=QUERIED_AT,
        truncated=False,
    )
    assert report.conditional_attempts.rejected_local == 1
    assert report.conditional_attempts.rejected_unknown == 0
    assert report.primary.lost == 0
    assert report.primary.abandoned == 1


# --- R3-② local 거절은 대안 규칙에서 구간을 끊지 않는다 -----------------------


def test_local_failure_does_not_split_the_alternative_episode() -> None:
    """★R3-② — 끊게 두면 거절 1건인데 분모가 2가 되어 유실률이 낮아진다.

    같은 trade 에 로컬 실패 뒤 실제 거래소 거절이 오는 순서는 흔하다(자격증명 복구 후 재시도).
    """
    facts = [
        _fact(
            trade_id="PivRevSE",
            minutes=1,
            state=OrderState.rejected,
            error_message="provider_failure: unexpected non-CCXT error: RuntimeError",
        ),
        _fact(
            trade_id="PivRevSE",
            minutes=2,
            state=OrderState.rejected,
            error_message='{"retCode":110093,"retMsg":"expect Falling"}',
        ),
    ]
    report = build_report(
        facts,
        session_id=SESSION_ID,
        since=SINCE,
        until=UNTIL,
        queried_at=QUERIED_AT,
        truncated=False,
    )
    alternative = report.alternative
    assert alternative.total == 1, "로컬 실패가 구간을 끊으면 2개가 된다"
    assert (alternative.lost, alternative.abandoned) == (1, 0)
    assert alternative.loss_rate == Decimal("1"), "거절 1건 = 유실률 100%"


def test_exchange_rejection_still_splits_the_alternative_episode() -> None:
    """★가드가 대안 규칙의 검정력을 죽이지 않았는지 — 거래소 거절은 여전히 끊는다."""
    facts = [
        _fact(
            trade_id="PivRevSE",
            minutes=1,
            state=OrderState.rejected,
            error_message='{"retCode":110093,"retMsg":"expect Falling"}',
        ),
        _fact(trade_id="PivRevSE", minutes=2, state=OrderState.filled, filled_quantity="0.029"),
    ]
    report = build_report(
        facts,
        session_id=SESSION_ID,
        since=SINCE,
        until=UNTIL,
        queried_at=QUERIED_AT,
        truncated=False,
    )
    assert report.primary.total == 1, "채택 규칙은 체결에서만 끊는다"
    assert report.alternative.total == 2, "대안 규칙은 거래소 거절에서 끊는다"
    assert (report.alternative.lost, report.alternative.won) == (1, 1)
