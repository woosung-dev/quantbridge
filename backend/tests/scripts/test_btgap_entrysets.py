"""`btgap_compare.py entrysets` — 세 진입 집합(B · R · L)의 쌍별 매칭.

★**새 매칭 규칙을 만들지 않는다.** 이 서브커맨드는 정규화 + 어댑터일 뿐이고 판정은
기존 `match_entries` 가 한다 (strict `(bar_epoch, direction, trade_id, qty)` → loose
±3봉, 후보 둘이면 ambiguous 로 버림). 그래서 여기서 지키는 것은 두 가지다:

1. **정규화가 봉 축을 안 흔든다.** B 는 엔진 진입봉, L·R`cond` 는 장전봉이다 —
   ±3봉 허용창이 그 차이를 흡수하지만, 흡수한다는 사실이 **strict/loose 등급**으로
   보여야 한다. 등급이 뭉개지면 「같은 봉에서 났다」와 「2봉 늦게 났다」가 한 숫자가 된다.
2. **분모를 숨기지 않는다.** 매칭률은 어느 집합으로 나눴느냐로 뜻이 완전히 바뀐다.

★DB 도 네트워크도 celery 도 타지 않는다. 합성 JSON 뿐이다.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from tests.scripts.btgap_fixtures import (
    conditional_entry_key,
    load_script,
    order_row,
    session_row,
    trade_row,
)

BASE = datetime(2026, 8, 5, 0, 0, tzinfo=UTC)


@pytest.fixture(scope="module")
def btgap() -> Any:
    return load_script("btgap_compare")


def at(minutes: int) -> datetime:
    return BASE + timedelta(minutes=minutes)


def epoch(minutes: int) -> int:
    return int(at(minutes).timestamp())


def iso(minutes: int) -> str:
    return at(minutes).isoformat()


def replay_row(
    *,
    minutes: int,
    kind: str = "cond",
    direction: str = "long",
    trade_id: str = "PbR",
    qty: str = "0.01",
    trigger: str | None = "60000",
) -> dict[str, Any]:
    return {
        "kind": kind,
        "bar_epoch": epoch(minutes),
        "bar_time": iso(minutes),
        "direction": direction,
        "trade_id": trade_id,
        "trigger": trigger,
        "qty": qty,
        "entry_qty": qty,
        "target_position": None,
        "engine_position": "0",
    }


def replay_payload(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {"params": {}, "bars_evaluated": len(rows), "entries": rows, "digest": "x"}


def live_order(
    *,
    minutes: int,
    order_id: str,
    side: str = "buy",
    qty: str = "0.01",
    trigger: str = "60000",
    trade_id: str = "PbR",
) -> dict[str, Any]:
    return order_row(
        order_id=order_id,
        side=side,
        idempotency_key=conditional_entry_key(
            bar_epoch=epoch(minutes), trigger=trigger, quantity=qty, trade_id=trade_id
        ),
        quantity=qty,
        filled_quantity=qty,
        filled_price=trigger,
        filled_at=iso(minutes + 1),
    )


def _write(path: Path, payload: Any) -> Path:
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return path


def _run(
    btgap: Any,
    tmp_path: Path,
    *,
    left: Any,
    left_kind: str,
    right: Any,
    right_kind: str,
    sessions: Any = None,
    extra: list[str] | None = None,
    out_name: str = "entrysets.json",
) -> dict[str, Any]:
    argv = [
        "entrysets",
        "--left",
        str(_write(tmp_path / "left.json", left)),
        "--left-kind",
        left_kind,
        "--right",
        str(_write(tmp_path / "right.json", right)),
        "--right-kind",
        right_kind,
        "--out",
        str(tmp_path / out_name),
    ]
    if sessions is not None:
        argv += ["--session-windows", str(_write(tmp_path / "sessions.json", sessions))]
    argv += extra or []
    assert btgap.main(argv) == 0
    payload: dict[str, Any] = json.loads((tmp_path / out_name).read_text(encoding="utf-8"))
    return payload


# --------------------------------------------------------------------------
# strict / loose / ambiguous
# --------------------------------------------------------------------------


def test_strict_pair_needs_same_bar_and_quantity(btgap: Any, tmp_path: Path) -> None:
    report = _run(
        btgap,
        tmp_path,
        left=replay_payload([replay_row(minutes=10)]),
        left_kind="replay",
        right=[live_order(minutes=10, order_id="o1")],
        right_kind="orders",
        sessions=[session_row(created_at=iso(0))],
    )

    assert report["strict_pairs"] == 1
    assert report["loose_pairs"] == 0
    assert report["ambiguous"] == 0
    assert report["matched_rows"][0]["grade"] == "strict"
    assert report["matched_rows"][0]["delta_bars_left_minus_right"] == 0


def test_bar_offset_within_tolerance_degrades_to_loose(btgap: Any, tmp_path: Path) -> None:
    """★2봉 늦은 진입은 **붙되 loose 다.**

    라이브 key 의 봉은 장전봉이고 엔진 진입봉은 그보다 늦다(실측 +1~2봉). 그 차이를
    strict 로 세면 「같은 봉에서 났다」가 거짓으로 늘어난다.
    """
    report = _run(
        btgap,
        tmp_path,
        left=replay_payload([replay_row(minutes=12, kind="fill")]),
        left_kind="replay",
        right=[live_order(minutes=10, order_id="o1")],
        right_kind="orders",
        sessions=[session_row(created_at=iso(0))],
        extra=["--replay-kinds", "fill"],
    )

    assert report["strict_pairs"] == 0
    assert report["loose_pairs"] == 1
    assert report["matched_rows"][0]["delta_bars_left_minus_right"] == 2


def test_beyond_tolerance_is_not_paired(btgap: Any, tmp_path: Path) -> None:
    """★음성 대조 — ±3봉을 넘으면 안 붙는다. 안 그러면 loose 는 술어가 아니다."""
    report = _run(
        btgap,
        tmp_path,
        left=replay_payload([replay_row(minutes=14, kind="fill")]),
        left_kind="replay",
        right=[live_order(minutes=10, order_id="o1")],
        right_kind="orders",
        sessions=[session_row(created_at=iso(0))],
        extra=["--replay-kinds", "fill"],
    )

    assert report["pairs"] == 0
    assert report["left_only"] == 1
    assert report["right_only"] == 1


def test_same_bar_collision_on_the_right_is_ambiguous(btgap: Any, tmp_path: Path) -> None:
    """오른쪽에 같은 `(봉, 방향)` 이 둘이면 **붙이지 않는다** — 과잉 매칭은 fail-open."""
    report = _run(
        btgap,
        tmp_path,
        left=replay_payload([replay_row(minutes=10)]),
        left_kind="replay",
        right=[
            live_order(minutes=10, order_id="o1"),
            live_order(minutes=10, order_id="o2", qty="0.02"),
        ],
        right_kind="orders",
        sessions=[session_row(created_at=iso(0))],
    )

    assert report["pairs"] == 0
    assert report["ambiguous"] == 2
    assert {row["reason"] for row in report["ambiguous_rows"]} == {"live_key_collision"}


# --------------------------------------------------------------------------
# 분모 · 채널 선택
# --------------------------------------------------------------------------


def test_match_rate_names_both_denominators(btgap: Any, tmp_path: Path) -> None:
    """매칭률은 분모 이름과 함께 나온다 — 「37%」 한 숫자는 뜻이 없다."""
    report = _run(
        btgap,
        tmp_path,
        left=replay_payload([replay_row(minutes=10), replay_row(minutes=30, trade_id="PbS")]),
        left_kind="replay",
        right=[live_order(minutes=10, order_id="o1")],
        right_kind="orders",
        sessions=[session_row(created_at=iso(0))],
    )

    assert report["left_count"] == 2
    assert report["right_count"] == 1
    assert report["match_rate"]["vs_left"] == {"denominator": "left_count", "n": 2, "value": "0.5"}
    assert report["match_rate"]["vs_right"] == {"denominator": "right_count", "n": 1, "value": "1"}


def test_replay_kinds_selects_the_channel(btgap: Any, tmp_path: Path) -> None:
    """★`cond`/`entry` 와 `fill` 은 **다른 단계**다 — 섞어 세면 R 이 2배가 된다."""
    payload = replay_payload(
        [replay_row(minutes=10, kind="cond"), replay_row(minutes=10, kind="fill")]
    )
    both = _run(
        btgap,
        tmp_path,
        left=payload,
        left_kind="replay",
        right=replay_payload([]),
        right_kind="replay",
        out_name="both.json",
        extra=["--replay-kinds", "cond,fill"],
    )
    only_fill = _run(
        btgap,
        tmp_path,
        left=payload,
        left_kind="replay",
        right=replay_payload([]),
        right_kind="replay",
        out_name="fill.json",
        extra=["--replay-kinds", "fill"],
    )

    assert both["left_count"] == 2
    assert only_fill["left_count"] == 1
    assert only_fill["left"]["replay_kinds"] == ["fill"]


def test_backtest_trades_normalize_onto_the_entry_bar(btgap: Any, tmp_path: Path) -> None:
    """B 는 `entry_time` 의 봉으로 선다 — 기존 `match` 와 같은 `trade_bar_epoch` 산식."""
    report = _run(
        btgap,
        tmp_path,
        left=[trade_row(trade_index=0, entry_time=iso(10), size="0.01")],
        left_kind="trades",
        right=[live_order(minutes=10, order_id="o1")],
        right_kind="orders",
        sessions=[session_row(created_at=iso(0))],
    )

    assert report["strict_pairs"] == 1


def test_unparsable_orders_are_counted_not_dropped(btgap: Any, tmp_path: Path) -> None:
    """수동 flatten 은 진입이 아니지만 **세어서** 남긴다."""
    report = _run(
        btgap,
        tmp_path,
        left=replay_payload([replay_row(minutes=10)]),
        left_kind="replay",
        right=[
            live_order(minutes=10, order_id="o1"),
            order_row(order_id="manual", side="sell", idempotency_key=None, reduce_only=True),
        ],
        right_kind="orders",
        sessions=[session_row(created_at=iso(0))],
    )

    assert report["right_count"] == 1
    assert report["right"]["unparsable_rows"] == 1


# --------------------------------------------------------------------------
# 세션 창 필터 (실험 B — 사전등록 ③)
# --------------------------------------------------------------------------


def test_session_filter_removes_left_entries_outside_windows(btgap: Any, tmp_path: Path) -> None:
    """세션 공백 구간의 R 진입을 제거하고 **제거 건수를 보고**한다."""
    report = _run(
        btgap,
        tmp_path,
        left=replay_payload(
            [replay_row(minutes=10), replay_row(minutes=40, trade_id="PbS", direction="short")]
        ),
        left_kind="replay",
        right=[live_order(minutes=10, order_id="o1")],
        right_kind="orders",
        sessions=[session_row(created_at=iso(0), deactivated_at=iso(20))],
        extra=["--filter-left"],
    )

    assert report["left_count"] == 1
    assert report["session_filter"]["applied"] is True
    assert report["session_filter"]["removed_by_session_filter"] == 1
    assert report["session_filter"]["removed_rows"][0]["trade_id"] == "PbS"


def test_session_file_alone_does_not_filter(btgap: Any, tmp_path: Path) -> None:
    """★`--session-windows` 만으로는 안 거른다.

    사전등록 ③ 은 `R′↔L − R↔L` 이라 **필터 없는 R↔L 도** 재야 하는데, L 파싱에도
    같은 파일이 필요하다. 파일 제공과 필터 적용을 한 플래그로 묶으면 ③ 의 한쪽 항이
    아예 측정 불가가 된다.
    """
    report = _run(
        btgap,
        tmp_path,
        left=replay_payload(
            [replay_row(minutes=10), replay_row(minutes=40, trade_id="PbS", direction="short")]
        ),
        left_kind="replay",
        right=[live_order(minutes=10, order_id="o1")],
        right_kind="orders",
        sessions=[session_row(created_at=iso(0), deactivated_at=iso(20))],
    )

    assert report["left_count"] == 2
    assert report["session_filter"]["applied"] is False
    assert report["session_filter"]["removed_by_session_filter"] == 0


def test_session_boundary_is_judged_on_bar_close(btgap: Any, tmp_path: Path) -> None:
    """★세션 포함 판정은 **봉 종료** 기준이다 (사전등록 정정 2차, 측정 전 동결).

    세션은 봉 **중간**에 생성된다 — 실측 첫 세션이 `00:34:22`(봉 시작 +22s)다. 봉
    시작으로 재면 그 봉은 세션 밖으로 떨어지는데, 라이브는 그 봉을 평가해 실제로
    주문을 냈다(L 에 2건 실재). 봉이 **닫히는 시점**엔 세션이 이미 살아 있으므로
    봉 종료가 정본이다.

    ★음성 대조가 같은 픽스처 안에 있다 — 세션 **종료** 직전 봉은 여전히 남고(포함),
    종료 뒤 봉은 빠진다. 「전부 남긴다」로 고쳐도 통과하는 테스트가 아니다.
    """
    session_start = at(10).replace(second=22).isoformat()
    report = _run(
        btgap,
        tmp_path,
        left=replay_payload(
            [
                # 봉 시작 10:00 < 세션 생성 10:22 ≤ 봉 종료 11:00 → **남는다**
                replay_row(minutes=10, trade_id="OnBoundary"),
                replay_row(minutes=15, trade_id="Inside"),
                # 세션 종료(20:00) 뒤 봉 → 빠진다
                replay_row(minutes=25, trade_id="AfterEnd"),
            ]
        ),
        left_kind="replay",
        right=[live_order(minutes=15, order_id="o1", trade_id="Inside")],
        right_kind="orders",
        sessions=[session_row(created_at=session_start, deactivated_at=iso(20))],
        extra=["--filter-left"],
    )

    removed = {row["trade_id"] for row in report["session_filter"]["removed_rows"]}
    assert removed == {"AfterEnd"}, "봉 종료 기준이면 경계 봉은 남고 종료 뒤 봉만 빠진다"
    assert report["left_count"] == 2
    assert report["session_filter"]["removed_by_session_filter"] == 1
    assert report["session_filter"]["boundary"] == "bar_close"


def test_delta_is_reported_in_bars_not_seconds(btgap: Any, tmp_path: Path) -> None:
    """★`delta_bars_…` 는 **봉** 수여야 한다.

    초를 그 이름으로 내면 1분봉 2봉 차가 `120` 으로 나와 120봉처럼 읽힌다. 같은 2봉
    차가 봉 길이에 따라 값이 변하면 그건 봉 단위가 아니다.
    """
    report = _run(
        btgap,
        tmp_path,
        left=replay_payload([replay_row(minutes=12, kind="fill")]),
        left_kind="replay",
        right=[live_order(minutes=10, order_id="o1")],
        right_kind="orders",
        sessions=[session_row(created_at=iso(0))],
        extra=["--replay-kinds", "fill"],
    )

    assert report["matched_rows"][0]["delta_bars_left_minus_right"] == 2


def test_key_multiset_difference_is_reported(btgap: Any, tmp_path: Path) -> None:
    """★「두 집합이 같다」를 **산출물이 직접** 증명해야 한다.

    pairs/ambiguous 카운트만으로는 서로 다른 multiset 을 배제하지 못한다 — 오른쪽
    collision 은 `ambiguous` 로 빠져 `right_only_rows` 에도 안 들어간다. 그래서
    `(bar_epoch, direction, trade_id)` multiset 차집합을 매칭과 **무관하게** 낸다.
    """
    same = [replay_row(minutes=10), replay_row(minutes=20, trade_id="PbS")]
    equal = _run(
        btgap,
        tmp_path,
        left=replay_payload(same),
        left_kind="replay",
        right=replay_payload(same),
        right_kind="replay",
        out_name="equal.json",
    )
    assert equal["key_multiset"]["equal"] is True
    assert equal["key_multiset"]["left_only_keys"] == []
    assert equal["key_multiset"]["right_only_keys"] == []

    differing = _run(
        btgap,
        tmp_path,
        left=replay_payload(same),
        left_kind="replay",
        right=replay_payload([replay_row(minutes=10), replay_row(minutes=20, trade_id="OTHER")]),
        right_kind="replay",
        out_name="differ.json",
    )
    assert differing["key_multiset"]["equal"] is False
    assert differing["key_multiset"]["left_only_keys"] == [
        {"bar_epoch": epoch(20), "direction": "long", "trade_id": "PbS", "count": 1}
    ]
    assert differing["key_multiset"]["right_only_keys"] == [
        {"bar_epoch": epoch(20), "direction": "long", "trade_id": "OTHER", "count": 1}
    ]


def test_matched_row_provenance_points_at_the_paired_left(btgap: Any, tmp_path: Path) -> None:
    """★행별 출처는 **매칭이 실제로 고른** 왼쪽이어야 한다.

    같은 `(봉, 방향, trade_id)` 에 수량만 다른 왼쪽이 둘이면, key 맵은 나중 것이
    앞의 것을 덮어써서 리포트가 **매칭되지 않은 행**을 가리킨다.
    """
    report = _run(
        btgap,
        tmp_path,
        left=replay_payload(
            [
                replay_row(minutes=10, qty="0.01"),
                replay_row(minutes=10, qty="0.02"),
            ]
        ),
        left_kind="replay",
        right=[live_order(minutes=10, order_id="o1", qty="0.01")],
        right_kind="orders",
        sessions=[session_row(created_at=iso(0))],
    )

    assert report["strict_pairs"] == 1
    # 수량 0.01 인 쪽이 strict 로 붙는다 — 출처도 그 행(index 0)이어야 한다.
    assert report["matched_rows"][0]["left_id"] == "replay:cond:0"


def test_orders_without_sessions_is_refused(btgap: Any, tmp_path: Path) -> None:
    """세션 id 없이 orders 를 읽으면 L 이 **조용히 0** 이 된다 — 거부한다."""
    with pytest.raises(ValueError, match="세션 id"):
        _run(
            btgap,
            tmp_path,
            left=replay_payload([replay_row(minutes=10)]),
            left_kind="replay",
            right=[live_order(minutes=10, order_id="o1")],
            right_kind="orders",
        )


def test_bar_seconds_must_agree_with_session_interval(btgap: Any, tmp_path: Path) -> None:
    """봉 길이가 세션과 다르면 ±3봉 허용창이 통째로 틀린다 — 조용히 넘기지 않는다."""
    with pytest.raises(ValueError, match="세션 interval"):
        _run(
            btgap,
            tmp_path,
            left=replay_payload([replay_row(minutes=10)]),
            left_kind="replay",
            right=[live_order(minutes=10, order_id="o1")],
            right_kind="orders",
            sessions=[session_row(created_at=iso(0), interval="5m")],
            extra=["--bar-seconds", "60"],
        )
