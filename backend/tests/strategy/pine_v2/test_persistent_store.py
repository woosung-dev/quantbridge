"""PersistentStore 단위 테스트 — Pine var/varip 의미론 검증.

검증 시나리오:
- var 첫 bar 초기화 + factory 1회 호출
- var bar 지속 (bar N에서 값 유지)
- var bar 내 재할당
- var rollback → 시작-of-bar 값으로 복원
- varip rollback 제외 (인트라-bar 업데이트 유지)
- var/varip 혼합
- rollback 중 이번 바 새로 선언된 var 제거
- commit 후 rollback 금지
- 미선언 변수 set 금지
"""
from __future__ import annotations

import pytest

from src.strategy.pine_v2.runtime import PersistentStore


def test_declare_if_new_initializes_on_first_call_only() -> None:
    store = PersistentStore()
    call_count = {"n": 0}

    def factory() -> int:
        call_count["n"] += 1
        return 42

    v1 = store.declare_if_new("scope::x", factory)
    v2 = store.declare_if_new("scope::x", factory)
    v3 = store.declare_if_new("scope::x", factory)

    assert v1 == v2 == v3 == 42
    assert call_count["n"] == 1, "factory는 첫 호출에서만 평가되어야 함"


def test_set_without_declare_raises() -> None:
    store = PersistentStore()
    with pytest.raises(KeyError, match="not declared"):
        store.set("scope::missing", 10)


def test_get_without_declare_raises() -> None:
    store = PersistentStore()
    with pytest.raises(KeyError):
        store.get("scope::missing")


def test_var_persists_across_bars_without_rollback() -> None:
    """Pine: bar 0에서 var x = 1, bar 1에서 x := 5 하면 bar 2 시작 시 x == 5."""
    store = PersistentStore()

    # Bar 0
    store.begin_bar()
    store.declare_if_new("scope::x", lambda: 1)
    assert store.get("scope::x") == 1
    store.commit_bar()

    # Bar 1: 재할당
    store.begin_bar()
    store.set("scope::x", 5)
    store.commit_bar()

    # Bar 2: 시작 시 값 유지
    store.begin_bar()
    assert store.get("scope::x") == 5
    store.commit_bar()


def test_var_rollback_restores_start_of_bar_value() -> None:
    """Realtime 시나리오: bar 재실행 시 var는 롤백, 바 내 변경은 폐기."""
    store = PersistentStore()

    # Bar 0 확정
    store.begin_bar()
    store.declare_if_new("scope::x", lambda: 10)
    store.commit_bar()

    # Bar 1 begin — 현재 x=10 스냅샷
    store.begin_bar()
    store.set("scope::x", 99)  # 바 내 업데이트
    assert store.get("scope::x") == 99
    store.rollback_bar()  # realtime 재실행 신호

    # 롤백 후 x는 begin_bar 시점 값인 10으로 돌아감
    assert store.get("scope::x") == 10


def test_varip_rollback_preserves_intra_bar_update() -> None:
    """varip는 바 재실행 시에도 바 내 업데이트가 유지됨."""
    store = PersistentStore()

    # Bar 0: varip vx = 100 선언 + 확정
    store.begin_bar()
    store.declare_if_new("scope::vx", lambda: 100, varip=True)
    store.commit_bar()

    # Bar 1 begin — varip이므로 스냅샷에서 제외
    store.begin_bar()
    store.set("scope::vx", 500)  # 바 내 업데이트
    store.rollback_bar()

    # varip은 rollback에도 500 유지
    assert store.get("scope::vx") == 500


def test_mixed_var_and_varip_rollback_behavior() -> None:
    """var는 롤백, varip는 유지 — 혼합 시나리오."""
    store = PersistentStore()

    store.begin_bar()
    store.declare_if_new("scope::x", lambda: 1)
    store.declare_if_new("scope::vx", lambda: 1, varip=True)
    store.commit_bar()

    store.begin_bar()
    store.set("scope::x", 7)
    store.set("scope::vx", 7)
    store.rollback_bar()

    assert store.get("scope::x") == 1  # var 롤백
    assert store.get("scope::vx") == 7  # varip 유지


def test_rollback_removes_new_vars_declared_this_bar() -> None:
    """이번 바에서 새로 선언된 var는 rollback 시 제거돼야 한다 (시작-of-bar에 없었으므로)."""
    store = PersistentStore()

    store.begin_bar()
    store.declare_if_new("scope::y", lambda: 123)
    assert "scope::y" in store
    store.rollback_bar()

    assert "scope::y" not in store, "rollback 후 이번 바 신규 var는 제거되어야 함"


def test_rollback_keeps_new_varip_declared_this_bar() -> None:
    """이번 바에서 새로 선언된 varip은 rollback 후에도 유지 (varip 특성)."""
    store = PersistentStore()

    store.begin_bar()
    store.declare_if_new("scope::vy", lambda: 999, varip=True)
    store.rollback_bar()

    assert "scope::vy" in store
    assert store.get("scope::vy") == 999


def test_rollback_without_begin_bar_raises() -> None:
    store = PersistentStore()
    with pytest.raises(RuntimeError, match="without begin_bar"):
        store.rollback_bar()


def test_commit_then_rollback_raises() -> None:
    store = PersistentStore()
    store.begin_bar()
    store.declare_if_new("scope::x", lambda: 1)
    store.commit_bar()
    with pytest.raises(RuntimeError, match="without begin_bar"):
        store.rollback_bar()


def test_repeated_begin_bar_discards_previous_snapshot() -> None:
    """begin_bar 재호출(인터프리터 버그)은 이전 스냅샷을 새 것으로 덮어써야 — 디버깅 시 의도한 동작."""
    store = PersistentStore()

    store.begin_bar()
    store.declare_if_new("scope::x", lambda: 1)
    store.commit_bar()

    # Bar 1 begin → snapshot {x: 1}
    store.begin_bar()
    store.set("scope::x", 5)
    # Bar 1 mid begin (오용) → snapshot 덮어씀 {x: 5}
    store.begin_bar()
    store.set("scope::x", 9)
    store.rollback_bar()

    assert store.get("scope::x") == 5, "재호출된 begin_bar 시점 값으로 롤백"


def test_snapshot_dict_exposes_current_state() -> None:
    store = PersistentStore()
    store.declare_if_new("a", lambda: 1)
    store.declare_if_new("b", lambda: 2, varip=True)
    assert store.snapshot_dict() == {"a": 1, "b": 2}


def test_is_varip_reports_correctly() -> None:
    store = PersistentStore()
    store.declare_if_new("a", lambda: 1)
    store.declare_if_new("b", lambda: 2, varip=True)
    assert not store.is_varip("a")
    assert store.is_varip("b")


def test_historical_backtest_scenario() -> None:
    """Historical 백테스트 (rollback 없음) 시나리오 — 5 bar 시뮬레이션."""
    store = PersistentStore()
    highest_close: list[float] = []

    # Pine 의사코드: var highest = 0.0 ... highest := math.max(highest, close)
    closes = [10.0, 15.0, 12.0, 20.0, 18.0]
    for close in closes:
        store.begin_bar()
        store.declare_if_new("main::highest", lambda: 0.0)
        cur = store.get("main::highest")
        store.set("main::highest", max(cur, close))
        highest_close.append(store.get("main::highest"))
        store.commit_bar()

    assert highest_close == [10.0, 15.0, 15.0, 20.0, 20.0]
