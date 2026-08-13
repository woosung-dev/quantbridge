# 채널 표를 코드가 만들게 하고, 손으로 세던 표가 틀렸던 그 자리를 대조군으로 고정한다

"""BL-522 유실 채널 분류기 대조군.

★이 파일이 지키는 것은 "채널 표가 나온다" 가 아니라 **"손으로 셀 때 틀렸던 판정과 맞는
판정이 서로 다른 숫자를 낸다"** 이다. 지금까지 표가 두 번 틀렸고 원인은 같았다 —
술어가 코드에 없어서 아무도 반증할 수 없었다.

| 필요 행                                  | 없으면 동치가 되는 변이                       |
| ---------------------------------------- | --------------------------------------------- |
| `reduce_only=true` 부분체결              | C3 에서 reduce_only 가드 제거                 |
| 부분체결을 보존한 채 `cancelled`         | C3 후보를 `state==filled` 로 좁히기           |
| retCode 110007 거절                      | C1 에서 retCode 집합 검사 제거                |
| retCode 가 아예 없는 거절                | C1 에서 `unknown` 을 not_matched 로 떨구기    |
| `condmkt` cancelled                      | C4 후보에 condmkt 포함                        |
| 봉 없는 `cond` cancelled                 | C4 에서 probe 없음을 not_matched 로 떨구기    |
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from src.trading.entry_completeness import (
    AttemptFact,
    Attribution,
    Bar,
    ChannelTally,
    ChannelVerdict,
    LedgerChannel,
    NonLedgerStatus,
    assert_channel_partition,
    bars_breakout_probe,
    build_channel_table,
    channel_verdict,
    classify_attempts,
)
from src.trading.models import OrderState
from src.trading.services.conditional_entry_planner import (
    build_conditional_entry_key,
    build_market_converted_entry_key,
)

SESSION_ID = UUID("a0861954-1c7c-4a27-bfee-6f6af1a4d440")
SINCE = datetime(2026, 7, 29, 0, 0, tzinfo=UTC)
UNTIL = datetime(2026, 7, 30, 0, 0, tzinfo=UTC)
TRIGGER = Decimal("64000")


def _fact(
    *,
    trade_id: str = "PivRevLE",
    minutes: int = 1,
    state: OrderState,
    quantity: str = "0.029",
    filled_quantity: str | None = None,
    kind: str = "cond",
    reduce_only: bool = False,
    error_message: str | None = None,
    idempotency_key: str | None = "<build>",
    terminal_after_seconds: int | None = 30,
) -> AttemptFact:
    bar_time = SINCE + timedelta(minutes=minutes)
    if idempotency_key == "<build>":
        builder = (
            build_market_converted_entry_key if kind == "condmkt" else build_conditional_entry_key
        )
        idempotency_key = builder(
            SESSION_ID, trade_id, bar_time, TRIGGER, Decimal(quantity)
        )
    return AttemptFact(
        order_id=uuid4(),
        session_id=SESSION_ID,
        idempotency_key=idempotency_key,
        state=state,
        quantity=Decimal(quantity),
        filled_quantity=None if filled_quantity is None else Decimal(filled_quantity),
        created_at=bar_time,
        terminal_at=None
        if terminal_after_seconds is None
        else bar_time + timedelta(seconds=terminal_after_seconds),
        error_message=error_message,
        reduce_only=reduce_only,
    )


def _classify(*facts: AttemptFact):  # type: ignore[no-untyped-def]
    return classify_attempts(facts, since=SINCE, until=UNTIL)


def _verdict(fact: AttemptFact, channel: LedgerChannel, probe=None):  # type: ignore[no-untyped-def]
    (attempt,) = _classify(fact)
    return channel_verdict(attempt, channel, breakout_probe=probe)


def _tally(table, channel: LedgerChannel) -> ChannelTally:  # type: ignore[no-untyped-def]
    return next(item for item in table.ledger if item.channel is channel)


# --- C1 잔여 거절 ---------------------------------------------------------------


@pytest.mark.parametrize("code", ["110092", "110093"])
def test_c1_matches_only_the_trigger_breached_codes(code: str) -> None:
    fact = _fact(
        state=OrderState.rejected,
        error_message=f'{{"retCode":{code},"retMsg":"expect Rising"}}',
    )
    assert _verdict(fact, LedgerChannel.c1_residual_rejection) is ChannelVerdict.matched


def test_c1_rejects_a_different_retcode() -> None:
    """★경계 — retCode 집합 검사를 지우면 이 행이 C1 로 들어온다(잔고 부족은 다른 채널이다)."""
    fact = _fact(
        state=OrderState.rejected,
        error_message='{"retCode":110007,"retMsg":"insufficient balance"}',
    )
    assert _verdict(fact, LedgerChannel.c1_residual_rejection) is ChannelVerdict.not_matched


def test_c1_without_a_retcode_is_unmeasured_not_a_denial() -> None:
    """★모르는 것을 아는 것처럼 분류하지 마라 (BL-562/574).

    비동기 확정 거절 경로는 retCode 를 원문에 싣지 않는다. 그 행이 110092 였는지 우리는
    **모른다** — `not_matched` 로 떨구면 C1 이 구조적으로 작아 보인다.
    """
    fact = _fact(state=OrderState.rejected, error_message="order rejected by exchange")
    assert _verdict(fact, LedgerChannel.c1_residual_rejection) is ChannelVerdict.unmeasured


def test_c1_local_failure_is_a_definite_no() -> None:
    """거래소에 도달조차 못 했다 = 가격이 다시 움직여서 거절된 것일 수 **없다**."""
    fact = _fact(
        state=OrderState.rejected,
        error_message="provider_failure: credential_decrypt_failed: bad key",
    )
    assert _verdict(fact, LedgerChannel.c1_residual_rejection) is ChannelVerdict.not_matched


def test_c1_ignores_rows_that_are_not_rejected() -> None:
    fact = _fact(state=OrderState.cancelled)
    assert _verdict(fact, LedgerChannel.c1_residual_rejection) is None


def test_c1_sees_a_rejection_that_carried_a_partial_fill() -> None:
    """★`state=rejected` 로 후보를 잡는다 — 버킷으로 잡으면 이 행이 통째로 사라진다.

    부분체결을 보존한 채 거절된 행은 `AttemptBucket.has_fill` 이지만 `state` 는 여전히
    `rejected` 다. 그리고 그 행은 C3 에도 걸린다 — 채널은 상호배타가 아니다.
    """
    fact = _fact(
        state=OrderState.rejected,
        filled_quantity="0.011",
        error_message='{"retCode":110093,"retMsg":"expect Falling"}',
    )
    assert _verdict(fact, LedgerChannel.c1_residual_rejection) is ChannelVerdict.matched
    assert _verdict(fact, LedgerChannel.c3_partial_fill) is ChannelVerdict.matched


# --- C3 부분체결 ----------------------------------------------------------------


def test_c3_matches_a_partial_fill() -> None:
    fact = _fact(state=OrderState.filled, quantity="0.029", filled_quantity="0.011")
    assert _verdict(fact, LedgerChannel.c3_partial_fill) is ChannelVerdict.matched


def test_c3_does_not_match_a_full_fill() -> None:
    fact = _fact(state=OrderState.filled, quantity="0.029", filled_quantity="0.029")
    assert _verdict(fact, LedgerChannel.c3_partial_fill) is ChannelVerdict.not_matched


def test_c3_refuses_a_reduce_only_partial_fill() -> None:
    """★★이번 회차의 핵심 결함 — 손으로 센 표의 '부분체결 7 건' 은 전부 **청산측**이었다.

    reduce_only 가드를 지우면 이 행이 진입 유실 C3 로 계상된다. 그것이 dev-log 에 적힌
    그 숫자였고, 진입측 실측은 0 건이었다.
    """
    fact = _fact(
        state=OrderState.filled, quantity="0.029", filled_quantity="0.011", reduce_only=True
    )
    assert _verdict(fact, LedgerChannel.c3_partial_fill) is None


def test_c3_sees_a_partial_fill_preserved_on_a_cancelled_row() -> None:
    """★후보를 `state==filled` 로 좁히면 BL-544 형제 케이스가 통째로 안 보인다."""
    fact = _fact(state=OrderState.cancelled, quantity="0.029", filled_quantity="0.011")
    assert _verdict(fact, LedgerChannel.c3_partial_fill) is ChannelVerdict.matched


def test_c3_sees_a_partial_fill_preserved_on_a_rejected_row() -> None:
    fact = _fact(state=OrderState.rejected, quantity="0.029", filled_quantity="0.011")
    assert _verdict(fact, LedgerChannel.c3_partial_fill) is ChannelVerdict.matched


def test_c3_zero_fill_is_not_a_partial_fill() -> None:
    fact = _fact(state=OrderState.cancelled, quantity="0.029", filled_quantity="0")
    assert _verdict(fact, LedgerChannel.c3_partial_fill) is ChannelVerdict.not_matched


def test_c3_unreadable_quantity_on_a_filled_row_is_unmeasured() -> None:
    """`filled` 인데 수량 NULL — 부분체결이 아니라고 **밝혀진 게 아니다** (BL-544 unreadable)."""
    fact = _fact(state=OrderState.filled, filled_quantity=None)
    assert _verdict(fact, LedgerChannel.c3_partial_fill) is ChannelVerdict.unmeasured


@pytest.mark.parametrize("state", [OrderState.cancelled, OrderState.rejected])
def test_c3_null_quantity_on_a_cancel_or_reject_is_just_a_cancel(state: OrderState) -> None:
    """★NULL 을 상태와 무관하게 unmeasured 로 두면 실측 창의 판정불가가 194 로 부푼다.

    갈림의 근거는 내가 정한 게 아니라 `order_repository._STATES_THAT_CAN_CARRY_FILLS` 다 —
    두 전이는 체결분이 있을 때만 수량을 쓰므로 NULL 은 "체결 없음" 의 기록이다.
    """
    fact = _fact(state=state, filled_quantity=None)
    assert _verdict(fact, LedgerChannel.c3_partial_fill) is ChannelVerdict.not_matched


def test_c3_ignores_rows_that_are_still_alive() -> None:
    fact = _fact(state=OrderState.submitted, terminal_after_seconds=None)
    assert _verdict(fact, LedgerChannel.c3_partial_fill) is None


def test_c3_counts_market_entries_too_and_shows_the_conditional_subset() -> None:
    """★실측 재현 — 진입측 부분체결은 **전부 시장가 진입**이었고 조건부는 0 건이었다.

    조건부로만 좁힌 표는 "부분체결 0 건" 이라는 다른 거짓말을 한다. 두 수를 함께 낸다.
    """
    market_key = f"live:{SESSION_ID}:2026-07-26T00:00:00+00:00:1:entry:PivRevLE"
    attempts = _classify(
        _fact(
            state=OrderState.filled,
            filled_quantity="0.011",
            idempotency_key=market_key,
        ),
        _fact(state=OrderState.filled, minutes=2, filled_quantity="0.029"),
    )
    tally = _tally(build_channel_table(attempts), LedgerChannel.c3_partial_fill)
    assert tally.matched == 1
    assert tally.matched_conditional == 0, "조건부 진입 부분체결은 0 건이다 (실측)"
    assert attempts[0].attribution is Attribution.nonconditional_ours


# --- C4 취소가 트리거를 이김 ----------------------------------------------------


def _probe_bars(*, high: str, low: str) -> list[Bar]:
    """`_fact(minutes=1)` 의 [created, terminal) 창을 덮는 1 분봉 두 개."""
    return [
        Bar(start=SINCE + timedelta(minutes=1), high=Decimal(high), low=Decimal(low)),
        Bar(start=SINCE + timedelta(minutes=2), high=Decimal(high), low=Decimal(low)),
    ]


def test_c4_without_a_probe_is_unmeasured() -> None:
    """★경계 — 봉이 없으면 **모른다**. `not_matched` 로 떨구면 C4 는 항상 0 이다."""
    fact = _fact(state=OrderState.cancelled)
    assert _verdict(fact, LedgerChannel.c4_cancel_beats_trigger) is ChannelVerdict.unmeasured


def test_c4_matches_when_the_market_touched_the_trigger_before_the_cancel() -> None:
    probe = bars_breakout_probe(_probe_bars(high="64100", low="63900"))
    fact = _fact(state=OrderState.cancelled)
    assert _verdict(fact, LedgerChannel.c4_cancel_beats_trigger, probe) is ChannelVerdict.matched


def test_c4_does_not_match_when_the_market_never_reached_the_trigger() -> None:
    probe = bars_breakout_probe(_probe_bars(high="63500", low="63000"))
    fact = _fact(state=OrderState.cancelled)
    assert (
        _verdict(fact, LedgerChannel.c4_cancel_beats_trigger, probe) is ChannelVerdict.not_matched
    )


def test_c4_is_unmeasured_when_the_probe_itself_cannot_answer() -> None:
    """★변이 M-C4c 생존이 잡아낸 구멍 — 포트 계약과 채널 판정을 잇는 자리다.

    probe 를 **주긴 줬는데** 그 창을 덮는 봉이 없어 `None` 이 돌아온 경우. 포트 계약
    테스트(아래)와 "probe 미주입" 테스트가 각각 따로 있어도, 그 둘을 잇는 이 한 줄이
    없으면 `None -> not_matched` 변이가 통과한다.
    """
    far_bars = [
        Bar(start=SINCE + timedelta(days=1), high=Decimal("64100"), low=Decimal("63900")),
        Bar(start=SINCE + timedelta(days=1, minutes=1), high=Decimal("64100"), low=Decimal("63900")),
    ]
    probe = bars_breakout_probe(far_bars)
    fact = _fact(state=OrderState.cancelled)
    assert probe(TRIGGER, fact.created_at, fact.terminal_at) is None  # type: ignore[arg-type]
    assert _verdict(fact, LedgerChannel.c4_cancel_beats_trigger, probe) is ChannelVerdict.unmeasured


def test_c4_ignores_condmkt_rows() -> None:
    """★시장가 전환 주문은 호가창에 남지 않는다 — '트리거를 기다린다' 가 성립하지 않는다."""
    probe = bars_breakout_probe(_probe_bars(high="64100", low="63900"))
    fact = _fact(state=OrderState.cancelled, kind="condmkt")
    assert _verdict(fact, LedgerChannel.c4_cancel_beats_trigger, probe) is None


def test_c4_ignores_rows_that_were_not_cancelled() -> None:
    probe = bars_breakout_probe(_probe_bars(high="64100", low="63900"))
    fact = _fact(state=OrderState.filled, filled_quantity="0.029")
    assert _verdict(fact, LedgerChannel.c4_cancel_beats_trigger, probe) is None


def test_c4_without_a_readable_trigger_price_is_unmeasured() -> None:
    """key 가 우리 형식이 아니면 트리거 가격을 모른다 — 추정하지 않는다."""
    probe = bars_breakout_probe(_probe_bars(high="64100", low="63900"))
    fact = _fact(state=OrderState.cancelled, idempotency_key=None)
    # 우리 key 가 아니면 kind 자체가 None 이라 후보가 아니다.
    assert _verdict(fact, LedgerChannel.c4_cancel_beats_trigger, probe) is None

    broken = _fact(
        state=OrderState.cancelled,
        idempotency_key=f"live:{SESSION_ID}:cond:1785000000:not-a-price:0.029:PivRevLE",
    )
    assert (
        _verdict(broken, LedgerChannel.c4_cancel_beats_trigger, probe) is ChannelVerdict.unmeasured
    )


# --- C4 포트 계약 (bars_breakout_probe) -----------------------------------------


def test_probe_returns_none_when_bars_do_not_cover_the_window() -> None:
    """★계약 1 — 구멍이 있으면 `None`. 'False' 로 답하면 봉 부재가 크기 0 으로 위장한다."""
    probe = bars_breakout_probe(
        [
            Bar(start=SINCE, high=Decimal("64100"), low=Decimal("63900")),
            Bar(start=SINCE + timedelta(minutes=1), high=Decimal("64100"), low=Decimal("63900")),
            # 3 분봉이 없다 — 아래 창의 뒤쪽이 덮이지 않는다.
            Bar(start=SINCE + timedelta(minutes=4), high=Decimal("64100"), low=Decimal("63900")),
        ]
    )
    start = SINCE + timedelta(minutes=2)
    assert probe(TRIGGER, start, start + timedelta(minutes=2)) is None


def test_probe_returns_none_when_the_bars_run_out_before_the_window_ends() -> None:
    """★변이 M-P2 생존이 잡아낸 구멍 — 창 **뒤쪽**이 안 덮인 경우는 다른 분기다.

    중간 구멍(위 테스트)과 시작 전(아래 테스트)만 막으면, 봉이 창 끝보다 먼저 끊긴
    가장 흔한 모양(soak 종료 직후 취소)이 "안 건드렸다" 로 답한다.
    """
    probe = bars_breakout_probe(_probe_bars(high="63500", low="63000"))  # [1분, 3분) 만 덮는다
    start = SINCE + timedelta(minutes=1)
    assert probe(TRIGGER, start, start + timedelta(minutes=1)) is False, "덮인 창은 판정된다"
    assert probe(TRIGGER, start, start + timedelta(minutes=3)) is None, "창 끝이 안 덮였다"


def test_probe_returns_none_when_the_window_starts_before_the_first_bar() -> None:
    probe = bars_breakout_probe(_probe_bars(high="64100", low="63900"))
    assert probe(TRIGGER, SINCE, SINCE + timedelta(minutes=2)) is None


def test_probe_returns_none_for_a_backwards_or_empty_window() -> None:
    """★계약 3 — 취소 시각이 생성 시각보다 앞서면 시계 왜곡이다. 판정하지 않는다."""
    probe = bars_breakout_probe(_probe_bars(high="64100", low="63900"))
    start = SINCE + timedelta(minutes=1)
    assert probe(TRIGGER, start, start) is None
    assert probe(TRIGGER, start, start - timedelta(seconds=1)) is None


def test_probe_needs_at_least_two_bars_to_know_the_bar_length() -> None:
    """★계약 4 — 봉 하나로는 봉 길이를 모른다. 길이를 모르면 덮였는지도 모른다."""
    probe = bars_breakout_probe([Bar(start=SINCE, high=Decimal("64100"), low=Decimal("63900"))])
    assert probe(TRIGGER, SINCE, SINCE + timedelta(seconds=30)) is None

    explicit = bars_breakout_probe(
        [Bar(start=SINCE, high=Decimal("64100"), low=Decimal("63900"))],
        interval=timedelta(minutes=1),
    )
    assert explicit(TRIGGER, SINCE, SINCE + timedelta(seconds=30)) is True


def test_probe_is_direction_agnostic_because_touching_the_level_is_the_event() -> None:
    """resting stop 은 발주 시점에 아직 발화하지 않았다 — 수준을 건드리는 것 자체가 발화다."""
    probe = bars_breakout_probe(_probe_bars(high="64000", low="63000"))
    assert probe(TRIGGER, SINCE + timedelta(minutes=1), SINCE + timedelta(minutes=2)) is True
    below = bars_breakout_probe(_probe_bars(high="65000", low="64000"))
    assert below(TRIGGER, SINCE + timedelta(minutes=1), SINCE + timedelta(minutes=2)) is True


# --- 표 전체: 파티션 · 비배타 · 원장 밖 채널 -----------------------------------


def _mixed_attempts():  # type: ignore[no-untyped-def]
    return _classify(
        _fact(
            trade_id="A",
            minutes=1,
            state=OrderState.rejected,
            error_message='{"retCode":110092,"retMsg":"expect Rising"}',
        ),
        _fact(trade_id="B", minutes=2, state=OrderState.cancelled),
        _fact(trade_id="C", minutes=3, state=OrderState.filled, filled_quantity="0.011"),
        _fact(trade_id="D", minutes=4, state=OrderState.filled, filled_quantity="0.029"),
        _fact(trade_id="E", minutes=5, state=OrderState.submitted, terminal_after_seconds=None),
    )


def test_every_channel_partitions_its_own_candidates() -> None:
    table = build_channel_table(_mixed_attempts())
    for tally in table.ledger:
        assert tally.matched + tally.not_matched + tally.unmeasured == tally.candidates
        assert tally.candidates <= tally.rows
        assert_channel_partition(tally)


def test_build_channel_table_actually_calls_the_partition_guard(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """★가드 함수만 있고 배선이 없으면 그 가드는 아무것도 지키지 않는다."""
    calls: list[str] = []
    import src.trading.entry_completeness as module

    monkeypatch.setattr(
        module, "assert_channel_partition", lambda tally: calls.append(tally.channel.value)
    )
    build_channel_table(_mixed_attempts())
    assert calls == [channel.value for channel in LedgerChannel]


def test_channels_are_declared_non_exclusive_and_overlaps_are_named() -> None:
    """요구사항 2 — 상호배타가 아님을 **명시**하고, 실제로 겹친 주문을 이름으로 낸다."""
    probe = bars_breakout_probe(_probe_bars(high="64100", low="63900"))
    attempts = _classify(
        _fact(state=OrderState.cancelled, filled_quantity="0.011"),  # C3 + C4
    )
    table = build_channel_table(attempts, breakout_probe=probe)
    assert table.mutually_exclusive is False
    assert len(table.overlaps) == 1
    assert set(table.overlaps[0].channels) == {
        LedgerChannel.c3_partial_fill,
        LedgerChannel.c4_cancel_beats_trigger,
    }


def test_the_table_has_no_total_to_add_up() -> None:
    """★합산 금지를 타입으로 유지한다 — 더할 수 있는 총합 프로퍼티가 존재하지 않는다."""
    table = build_channel_table(_mixed_attempts())
    for forbidden in ("total", "sum", "matched_total"):
        assert not hasattr(table, forbidden), f"{forbidden} 이 생기면 채널이 한 분모로 합쳐진다"


def test_c5_and_c2_carry_no_number_at_all() -> None:
    """★요구사항 1 — 원장 발자국 없는 채널은 **숫자 칸이 없어야** 산식이 구조적으로 불가능하다."""
    table = build_channel_table(_mixed_attempts())
    keys = {channel.key for channel in table.non_ledger}
    assert keys == {"C5", "C2"}
    for channel in table.non_ledger:
        for field_name in channel.__slots__:
            assert not isinstance(getattr(channel, field_name), int | float), (
                "숫자를 들고 있으면 누군가 원장 채널과 더한다"
            )
    c5 = next(item for item in table.non_ledger if item.key == "C5")
    assert c5.status is NonLedgerStatus.counter_only
    c2 = next(item for item in table.non_ledger if item.key == "C2")
    assert c2.status is NonLedgerStatus.disproven, "C2 는 반증됐다 (PR #511) — 유실 채널이 아니다"


def test_c2_is_kept_visible_instead_of_deleted() -> None:
    """지워 버리면 다음 사람이 또 넣는다 — 표면에 '반증됨' 으로 남긴다."""
    table = build_channel_table(_mixed_attempts())
    c2 = next(item for item in table.non_ledger if item.key == "C2")
    assert "deferred_market_inflight" in c2.title
    assert "청산" in c2.why and "#511" in c2.why


def test_c2_is_not_a_ledger_channel() -> None:
    assert "C2" not in {channel.value for channel in LedgerChannel}


def test_unmeasured_never_enters_the_denominator() -> None:
    """봉이 없으면 C4 의 비율은 **없다**(n/a) — 0% 가 아니다."""
    table = build_channel_table(_mixed_attempts())
    c4 = _tally(table, LedgerChannel.c4_cancel_beats_trigger)
    assert c4.candidates == 1 and c4.unmeasured == 1
    assert c4.measured == 0
    assert c4.matched_rate is None, "0% 로 내면 '재봤더니 없더라' 로 읽힌다"
    assert c4.provisional is True


def test_partition_guard_rejects_a_hand_built_broken_tally() -> None:
    broken = ChannelTally(
        channel=LedgerChannel.c1_residual_rejection,
        title="t",
        predicate="p",
        rows=10,
        candidates=5,
        matched=2,
        not_matched=2,
        unmeasured=0,
        matched_conditional=0,
        matched_order_ids=(),
    )
    with pytest.raises(ValueError, match="채널 분할 위반"):
        assert_channel_partition(broken)


def test_partition_guard_is_not_an_assert_statement() -> None:
    """`python -O` 가 지우는 `assert` 로 두면 프로덕션에서만 가드가 사라진다."""
    import inspect

    from src.trading.entry_completeness import assert_channel_partition as guard

    source = inspect.getsource(guard)
    assert "raise ValueError" in source
    assert "\n    assert " not in source
