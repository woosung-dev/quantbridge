# 하네스 자기검증 — 청산이 **남의 계정**을 건드리지 않는다는 계약.
"""`tests/real_broker/_harness.flatten_one` 의 계정 배타성 가드 회귀 (2026-08-15 soak-survival).

## ★왜 `tests/real_broker/` 안이 아니라 여기 있나 (실측)

처음엔 그 디렉터리에 `real_broker` **마커 없이** 뒀다. `pytest_collection_modifyitems` 가
`"real_broker" in item.keywords` 로 skip 을 주입하는데, `item.keywords` 는 마커뿐 아니라
**디렉터리·파일 이름**도 포함한다 ⇒ 마커를 안 달아도 `3 skipped` 였다(2026-08-15 실측).
**가드를 지키는 테스트가 가드와 함께 꺼진다.** 그래서 그 keyword 밖에 둔다.

## 무엇을 고정하나

`close_position` 은 계정 포지션을 **소유권을 보지 않고** 닫는다. 2026-08-14 에 그것이 서버
소크 세션 `de3db35a` 를 죽였다 — 거래소 원장 실측:

    04:44:07  소크 sell 0.058                       → 서버 숏 −0.029
    04:49:56  Buy 0.029 CreateByUser link=(empty)   ← real_broker 하네스의 청산
    04:50:27  exchange_position=+0.001              ← 남은 잔량, 관측치와 정확히 일치
    04:51:27  같은 값 2연속 → strike kill → position_divergence 사망

그때 verify-flat 은 `positions` 가 비었으므로 **성공으로 보고**했다 — 남의 포지션을 닫았다는
것을 구조적으로 알 수 없었다. [BL-633] 의 재발이고 경로만 다르다.
⇒ **남의 resting 조건부 주문이 보이면 청산 경로에 진입조차 하지 않는다.**

★반환값이 아니라 **부작용**을 잰다(`apps/api/AGENTS.md` §10). 안 부른 것이 이 가드의
전부이므로 `close_position` 호출 여부가 유일하게 유효한 관측면이다.
"""

from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest

from tests.real_broker import _harness
from tests.real_broker._harness import CleanupTarget


class _Recorder:
    """`_build_close_service` 가 불렸는지만 기록한다."""

    def __init__(self) -> None:
        self.close_service_built = 0

    def build_close_service(self, _db: object) -> object:
        self.close_service_built += 1
        raise AssertionError("가드가 열렸다 — 남의 계정이 있는데 close_position 경로로 갔다")


@pytest.fixture
def stubbed(monkeypatch: pytest.MonkeyPatch) -> _Recorder:
    """`flatten_one` 이 가드 앞까지 도달하도록 세션 조회·stop 만 통과시킨다."""
    # ① 세션 행은 존재하고 ② stop 뒤에는 is_active=False 여야 가드 자리까지 온다.
    live_row = SimpleNamespace(user_id=uuid4(), is_active=False)

    class _Repo:
        async def get_by_id(self, _sid: object) -> object:
            return live_row

    class _SessionService:
        async def deactivate(self, _user: object, _sid: object) -> None:
            return None

    monkeypatch.setattr(_harness, "_session_repo", lambda _db: _Repo())
    monkeypatch.setattr(_harness, "_build_session_service", lambda _db: _SessionService())

    recorder = _Recorder()
    monkeypatch.setattr(_harness, "_build_close_service", recorder.build_close_service)
    return recorder


def _target() -> CleanupTarget:
    return CleanupTarget(
        account_id=uuid4(),
        symbol="BTC/USDT",
        live_session_id=uuid4(),
        account_label="test",
    )


@pytest.mark.asyncio
async def test_foreign_resting_blocks_close(
    monkeypatch: pytest.MonkeyPatch, stubbed: _Recorder
) -> None:
    """남의 resting 이 보이면 청산하지 않고 undecidable 로 보고한다."""
    import scripts.live_session_admin as admin

    async def _foreign(_db: object, _symbol: str) -> list[str]:
        return ["soak:abc123:(link 없음)"]

    monkeypatch.setattr(admin, "find_foreign_resting", _foreign)

    result = await _harness.flatten_one(object(), _target())

    assert result.status == "undecidable"
    assert "soak:abc123" in result.detail
    # ★부작용 단언 — 이것이 가드의 전부다.
    assert stubbed.close_service_built == 0


@pytest.mark.asyncio
async def test_probe_failure_blocks_close(
    monkeypatch: pytest.MonkeyPatch, stubbed: _Recorder
) -> None:
    """배타성 조회 자체가 실패해도 청산하지 않는다 (fail-closed).

    ★「남이 있는지 모른다」에서 닫는 것이 2026-08-14 사고의 형태다. 조회 실패를 「깨끗하다」로
    접으면 가드가 정확히 필요한 순간에 스스로 열린다.
    """
    import scripts.live_session_admin as admin

    async def _boom(_db: object, _symbol: str) -> list[str]:
        raise RuntimeError("bybit unreachable")

    monkeypatch.setattr(admin, "find_foreign_resting", _boom)

    result = await _harness.flatten_one(object(), _target())

    assert result.status == "undecidable"
    assert "bybit unreachable" in result.detail
    assert stubbed.close_service_built == 0


@pytest.mark.asyncio
async def test_clean_account_reaches_close_path(
    monkeypatch: pytest.MonkeyPatch, stubbed: _Recorder
) -> None:
    """★양성 대조 — 계정이 깨끗하면 가드는 통과하고 청산 경로로 **간다**.

    이것이 없으면 「항상 거부」하는 가드도 위 두 테스트를 통과한다. 판별력의 근거는
    `close_service_built == 1` 이다(`_Recorder` 가 거기서 던지므로 그 뒤는 재지 않는다).
    """
    import scripts.live_session_admin as admin

    async def _clean(_db: object, _symbol: str) -> list[str]:
        return []

    monkeypatch.setattr(admin, "find_foreign_resting", _clean)

    result = await _harness.flatten_one(object(), _target())

    # 청산 경로에 진입했다 → `_Recorder` 가 던졌고 `flatten_one` 이 그것을 접었다.
    assert stubbed.close_service_built == 1
    assert result.status in {"residual", "undecidable"}
