"""Strategy CRUD E2E — POST/GET/PUT/DELETE."""

from __future__ import annotations

import pytest

_OK = """//@version=5
strategy("ok")
long = ta.crossover(close, ta.sma(close, 5))
if long
    strategy.entry("L", strategy.long)
"""

_BAD = "@@@ this is not pine script $$$"

# 파싱은 **성공**하는데 미지원 빌트인을 쓰는 소스. `_BAD` 는 이 경로를 안 지난다
# (그쪽은 `parse_to_ast` 가 던져서 `error` 로 끝난다) — 2026-09-06 실측:
# parse OK · `is_runnable=False` · `all_unsupported=('request.security_lower_tf',)` · line 3.
_PARSES_BUT_UNSUPPORTED = """//@version=5
strategy("lower tf")
htf = request.security_lower_tf(syminfo.tickerid, "1", close)
if ta.crossover(close, ta.sma(close, 5))
    strategy.entry("L", strategy.long)
"""

# 문법도 깨졌고 미지원 함수도 쓴 소스. 이 둘이 겹칠 때 **어느 판정이 이기는가**를 재는
# 유일한 입력이다 — 2026-09-06 실측: `parse_to_ast` SyntaxError ∧ `is_runnable=False` ∧
# `all_unsupported=('request.security_lower_tf',)`.
# ★이 픽스처가 없으면 「파싱 실패를 덮지 않는다」 가드는 **무증거**다: 변이로 그 가드를
#   제거해도 13건이 전부 초록이었다(기존 `_BAD` 에는 미지원 함수가 없어 그 경로를 안 지난다).
_BROKEN_AND_UNSUPPORTED = """//@version=5
strategy("x")
htf = request.security_lower_tf(syminfo.tickerid, "1", close)
if if if
"""


@pytest.mark.asyncio
async def test_create_strategy_ok_returns_201_with_parse_status(client, mock_authed_user):
    res = await client.post(
        "/api/v1/strategies",
        json={
            "name": "my ema",
            "pine_source": _OK,
            "timeframe": "1h",
            "symbol": "BTCUSDT",
            "tags": ["ema"],
        },
    )
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["name"] == "my ema"
    assert body["parse_status"] == "ok"
    assert body["pine_version"] == "v5"
    assert body["tags"] == ["ema"]


@pytest.mark.asyncio
async def test_create_strategy_stores_parse_failure_as_error(client, mock_authed_user):
    """문법이 깨진 소스는 저장되되 `error` 다 — 미지원 판정이 이것을 덮으면 안 된다.

    ★이름이 종전에 `..._stores_unsupported` 였는데 이 소스는 `unsupported` 를 **한 번도**
    내지 않는다(`parse_to_ast` 가 던진다). 단언도 `in ("unsupported", "error")` 라
    두 판정을 구별하지 못했다 — 결함이 계약처럼 보이던 자리다.
    """
    res = await client.post(
        "/api/v1/strategies",
        json={"name": "bad", "pine_source": _BAD},
    )
    assert res.status_code == 201
    body = res.json()
    assert body["parse_status"] == "error"
    assert body["parse_errors"] is not None


@pytest.mark.asyncio
async def test_create_strategy_marks_parsed_but_unsupported(client, mock_authed_user):
    """파싱은 됐지만 실행할 수 없는 소스는 저장된 행이 스스로 그렇게 말한다.

    저장을 막지 않는 이유는 [ADR-003] all-or-nothing 이 **실행** 게이트이고 백테스트
    제출이 이미 422 로 막기 때문이다(`backtest/service.py`). 판정자를 둘로 만들지 않는다.
    """
    res = await client.post(
        "/api/v1/strategies",
        json={"name": "lower tf", "pine_source": _PARSES_BUT_UNSUPPORTED},
    )
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["parse_status"] == "unsupported"
    # 근거가 없으면 화면이 「왜 미지원인지」를 말할 수 없다.
    errors = body["parse_errors"]
    assert errors, "미지원 판정에 근거가 실려야 한다"
    assert any("request.security_lower_tf" in (e.get("message") or "") for e in errors)


@pytest.mark.asyncio
async def test_parse_failure_wins_over_unsupported(client, mock_authed_user):
    """문법 실패와 미지원이 겹치면 **`error` 가 이긴다**.

    「문법을 못 읽었다」가 「읽었는데 못 돌린다」보다 강한 사실이다. 뒤엣것으로 덮으면
    사용자가 편집기에서 고쳐야 할 진짜 이유가 화면에서 사라진다.
    """
    res = await client.post(
        "/api/v1/strategies",
        json={"name": "broken and unsupported", "pine_source": _BROKEN_AND_UNSUPPORTED},
    )
    assert res.status_code == 201, res.text
    assert res.json()["parse_status"] == "error"


@pytest.mark.asyncio
async def test_create_strategy_supported_source_stays_ok(client, mock_authed_user):
    """음성 대조 — 지원 범위 안의 소스를 미지원으로 끌어내리지 않는다."""
    res = await client.post(
        "/api/v1/strategies",
        json={"name": "supported", "pine_source": _OK},
    )
    assert res.status_code == 201
    assert res.json()["parse_status"] == "ok"


@pytest.mark.asyncio
async def test_update_strategy_repeats_the_same_verdict(client, mock_authed_user):
    """`update()` 도 같은 판정을 낸다 — 두 입구가 갈리면 목록이 거짓말을 시작한다."""
    created = await client.post(
        "/api/v1/strategies",
        json={"name": "will change", "pine_source": _OK},
    )
    sid = created.json()["id"]

    res = await client.put(
        f"/api/v1/strategies/{sid}",
        json={"pine_source": _PARSES_BUT_UNSUPPORTED},
    )
    assert res.status_code == 200, res.text
    assert res.json()["parse_status"] == "unsupported"

    # 되돌리면 판정도 돌아온다 — 한 방향으로만 굳지 않는다.
    back = await client.put(f"/api/v1/strategies/{sid}", json={"pine_source": _OK})
    assert back.status_code == 200
    assert back.json()["parse_status"] == "ok"


@pytest.mark.asyncio
async def test_list_strategies_paginates(client, mock_authed_user):
    # 3건 생성
    for i in range(3):
        await client.post(
            "/api/v1/strategies",
            json={"name": f"s{i}", "pine_source": _OK},
        )
    res = await client.get("/api/v1/strategies?page=1&limit=2")
    assert res.status_code == 200
    body = res.json()
    assert body["total"] == 3
    assert body["page"] == 1
    assert body["limit"] == 2
    assert len(body["items"]) == 2


@pytest.mark.asyncio
async def test_list_filter_parse_status(client, mock_authed_user):
    await client.post("/api/v1/strategies", json={"name": "ok", "pine_source": _OK})
    await client.post("/api/v1/strategies", json={"name": "bad", "pine_source": _BAD})

    res = await client.get("/api/v1/strategies?parse_status=unsupported")
    assert res.status_code == 200
    body = res.json()
    for item in body["items"]:
        assert item["parse_status"] == "unsupported"


@pytest.mark.asyncio
async def test_list_pine_source_not_in_items(client, mock_authed_user):
    await client.post("/api/v1/strategies", json={"name": "x", "pine_source": _OK})
    res = await client.get("/api/v1/strategies")
    assert res.status_code == 200
    body = res.json()
    for item in body["items"]:
        assert "pine_source" not in item


@pytest.mark.asyncio
async def test_get_strategy_returns_full_dto(client, mock_authed_user):
    res = await client.post("/api/v1/strategies", json={"name": "x", "pine_source": _OK})
    sid = res.json()["id"]
    detail = await client.get(f"/api/v1/strategies/{sid}")
    assert detail.status_code == 200
    body = detail.json()
    assert body["pine_source"] == _OK
    assert "description" in body


@pytest.mark.asyncio
async def test_get_strategy_not_found(client, mock_authed_user):
    import uuid

    bogus = str(uuid.uuid4())
    res = await client.get(f"/api/v1/strategies/{bogus}")
    assert res.status_code == 404
    assert res.json()["detail"]["code"] == "strategy_not_found"


@pytest.mark.asyncio
async def test_update_pine_source_reparses(client, mock_authed_user):
    res = await client.post("/api/v1/strategies", json={"name": "x", "pine_source": _OK})
    sid = res.json()["id"]
    updated = await client.put(
        f"/api/v1/strategies/{sid}",
        json={"pine_source": _BAD},
    )
    assert updated.status_code == 200
    assert updated.json()["parse_status"] in ("unsupported", "error")


@pytest.mark.asyncio
async def test_update_archive_toggle(client, mock_authed_user):
    res = await client.post("/api/v1/strategies", json={"name": "x", "pine_source": _OK})
    sid = res.json()["id"]
    await client.put(f"/api/v1/strategies/{sid}", json={"is_archived": True})
    # 기본 목록에서 제외
    listed = await client.get("/api/v1/strategies")
    assert sid not in [i["id"] for i in listed.json()["items"]]
    # archive 필터로만 나옴
    archived = await client.get("/api/v1/strategies?is_archived=true")
    assert sid in [i["id"] for i in archived.json()["items"]]


@pytest.mark.asyncio
async def test_delete_strategy(client, mock_authed_user):
    res = await client.post("/api/v1/strategies", json={"name": "x", "pine_source": _OK})
    sid = res.json()["id"]
    deleted = await client.delete(f"/api/v1/strategies/{sid}")
    assert deleted.status_code == 204
    # 후속 GET은 404
    res = await client.get(f"/api/v1/strategies/{sid}")
    assert res.status_code == 404
