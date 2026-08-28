"""`GET /strategies/{id}/brief` — 결정론 브리핑 계약 ([ADR-040]).

★이 응답에 **LLM 이 만든 값은 하나도 없다.** 해설 층은 별 엔드포인트이고, 그쪽이 죽어도
이 응답만으로 화면이 완결되어야 한다는 것이 ADR-040 결정 4 다. 그래서 여기서 고정하는 것은
「판정어를 결정론 층이 낸다」와 「구조 추출 실패가 판정을 뒤집지 않는다」 둘이다.
"""

from __future__ import annotations

import hashlib
import uuid

import pytest

from src.auth.models import User
from src.strategy.models import ParseStatus, PineVersion, Strategy

RSI_V5 = """//@version=5
strategy("RSI Mean Reversion", overlay=true, pyramiding=2)
length = input.int(14, title="RSI Length", minval=1)
oversold = input.float(30.0, title="Oversold")
r = ta.rsi(close, length)
longCond = ta.crossover(r, oversold)
if longCond
    strategy.entry("long", strategy.long)
if r > 70
    strategy.close("long")
"""

UNSUPPORTED = """//@version=5
strategy("Needs supertrend")
[st, dir] = ta.supertrend(3.0, 10)
if close > st
    strategy.entry("long", strategy.long)
"""


async def _create(client, source: str, name: str = "brief-fixture") -> str:
    res = await client.post(
        "/api/v1/strategies",
        json={"name": name, "pine_source": source, "symbol": "BTC/USDT", "timeframe": "1h"},
    )
    assert res.status_code == 201, res.text
    return res.json()["id"]


@pytest.mark.asyncio
async def test_brief_reports_verdict_params_orders_and_signals(client, mock_authed_user):
    sid = await _create(client, RSI_V5)

    res = await client.get(f"/api/v1/strategies/{sid}/brief")
    assert res.status_code == 200, res.text
    body = res.json()

    assert body["strategy_id"] == sid
    # 해설 캐시 키 — `repository.create_version` 과 같은 식이어야 한다.
    assert body["source_hash"] == hashlib.sha256(RSI_V5.encode()).hexdigest()
    assert body["track"] == "S"  # strategy() 선언 → 네이티브 경로

    # ── 판정은 parse 가 품는다 (필드를 복제하지 않는다) ──
    parse = body["parse"]
    assert parse["is_runnable"] is True
    assert parse["unsupported_builtins"] == []
    assert {p["var_name"] for p in parse["inputs"]} == {"length", "oversold"}
    assert parse["declaration"]["pyramiding"] == 2

    # ── 주문 호출 + 줄번호 ──
    names = [o["name"] for o in body["orders"]]
    assert names == ["strategy.entry", "strategy.close"]
    lines = [o["line"] for o in body["orders"]]
    assert lines == sorted(lines), "줄번호 오름차순이어야 화면이 위에서 아래로 읽힌다"
    assert all(line_no is not None for line_no in lines)
    # ★인자는 stringify 된 원문이다(홑따옴표 보존) — 브리핑이 「어느 방향인가」를 답한다.
    entry = body["orders"][0]
    values = [a["value"] for a in entry["args"]]
    assert "strategy.long" in values, values

    # ── 신호 변수 — ★Track S 의 `if cond` 형태에서는 **비어 있는 것이 정상이다** ──
    #   `SignalExtractor` 는 `strategy.entry(..., when=var)` · `plotshape` · `label.new(var ? ..)` ·
    #   `alertcondition(var, ..)` 네 형태만 본다(`_find_signal_vars_ast`). 즉 **indicator 계열
    #   선언에서만 값이 나온다.** 화면은 비었을 때 이 절을 **그리지 않아야** 한다 —
    #   「신호 없음」으로 읽히면 거짓이다(`_KIT.md` §4.9).
    assert body["signals"] == []


@pytest.mark.asyncio
async def test_signals_are_populated_for_alert_style_declarations(client, mock_authed_user):
    """★양성 대조 — 위 테스트의 빈 배열이 「추출기가 죽었다」가 아님을 증명한다.

    `alertcondition(var, ...)` 형태에서는 같은 추출기가 값을 낸다. 이 대조가 없으면
    `signals == []` 단언은 판별력이 0이다(추출기가 통째로 고장나도 초록).
    """
    indicator = """//@version=5
indicator("UT signal")
r = ta.rsi(close, 14)
buySignal = ta.crossover(r, 30)
alertcondition(buySignal, title="Buy")
"""
    sid = await _create(client, indicator, name="brief-alert-style")

    res = await client.get(f"/api/v1/strategies/{sid}/brief")
    assert res.status_code == 200, res.text
    body = res.json()

    assert body["signals"] == ["buySignal"]
    assert body["track"] == "A"  # indicator + alert → 가상 strategy 래퍼 경로


@pytest.mark.asyncio
async def test_brief_carries_a_read_only_python_view(client, mock_authed_user):
    """[ADR-042] 「파이썬으로 보기」의 데이터. ★**실행되는 코드가 아니다.**"""
    sid = await _create(client, RSI_V5, name="brief-python-view")

    res = await client.get(f"/api/v1/strategies/{sid}/brief")
    assert res.status_code == 200, res.text
    view = res.json()["python_view"]
    assert view is not None

    code = view["code"]
    # ★헤더가 두 사실을 말해야 한다 — 안 말하면 이 뷰는 거짓말이 된다.
    assert "실행되지 않습니다" in code
    assert "한 봉 전의 값" in code
    # 전략의 실체가 코드로 보여야 한다(주석이 아니라).
    assert "if " in code
    assert "strategy.entry" in code

    # 줄 대응은 **실재하는 Pine 줄**만 가리킨다 — 없는 대응을 지어내지 않는다.
    pine_lines = RSI_V5.count("\n")
    assert view["source_map"], "source_map 이 비면 원본으로 데려갈 수 없다"
    for py_line, pine_line in view["source_map"]:
        assert 1 <= pine_line <= pine_lines, (py_line, pine_line)


@pytest.mark.asyncio
async def test_python_view_is_absent_when_parsing_fails(client, mock_authed_user):
    """★렌더는 판정자가 아니다 — 못 그려도 브리핑은 살아야 한다."""
    sid = await _create(client, "//@version=5\nstrategy(  <<< broken", name="brief-broken")

    res = await client.get(f"/api/v1/strategies/{sid}/brief")
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["python_view"] is None
    assert body["parse"]["status"] == "error"  # 판정은 살아 있다


@pytest.mark.asyncio
async def test_brief_shows_what_blocks_the_backtest(client, mock_authed_user):
    """★미지원이 있을 때가 브리핑이 가장 필요한 순간이다 — 404/422 로 감추지 않는다."""
    sid = await _create(client, UNSUPPORTED, name="brief-unsupported")

    res = await client.get(f"/api/v1/strategies/{sid}/brief")
    assert res.status_code == 200, res.text
    parse = res.json()["parse"]

    assert parse["is_runnable"] is False
    assert "ta.supertrend" in parse["unsupported_builtins"]
    # 무엇이 막았는지 **줄번호와 함께** 나와야 화면이 소스로 데려갈 수 있다.
    blocked = [c for c in parse["unsupported_calls"] if c["name"] == "ta.supertrend"]
    assert blocked and blocked[0]["line"] is not None


@pytest.mark.asyncio
async def test_brief_is_owner_scoped(client, mock_authed_user, db_session):
    """★남의 전략 브리핑은 404 다.

    브리핑은 **소스 전문을 파싱해 되돌려 주는** 표면이라 소유권이 새면 남의 Pine 이
    통째로 노출된다. `get` 과 같은 `find_by_id_and_owner` 를 쓰는지 여기서 잠근다.
    """
    other = User(
        auth_subject=f"user_other_{uuid.uuid4().hex[:6]}",
        email="other-brief@b.com",
        username="other-brief",
    )
    db_session.add(other)
    await db_session.commit()
    await db_session.refresh(other)

    victim = Strategy(
        user_id=other.id,
        name="not-yours",
        pine_source=RSI_V5,
        pine_version=PineVersion.v5,
        parse_status=ParseStatus.ok,
    )
    db_session.add(victim)
    await db_session.commit()
    await db_session.refresh(victim)

    res = await client.get(f"/api/v1/strategies/{victim.id}/brief")
    assert res.status_code == 404
    assert "RSI Mean Reversion" not in res.text
