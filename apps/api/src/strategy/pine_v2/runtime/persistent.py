"""Pine `var`/`varip` 런타임 state container.

Pine 의미론 요약:
- `var x = expr`    : 첫 bar에서 expr 1회 평가 → 저장. 이후 bar는 마지막 값 유지.
                     실시간(realtime) bar 재실행 시 **시작-of-bar 값으로 롤백**.
- `varip x = expr`  : var과 동일하되 **인트라-bar 업데이트가 실시간 재실행에서도 유지**.
                     (historical 백테스트에서는 var/varip 동작이 동일; 차이는 live에서만)

PyneCore 참조 이식 (Apache 2.0):
- PyneCore는 Python AST transformer로 `var x: Persistent[int] = 0`을 모듈 globals로 재작성
- QB는 Pine AST 직접 해석이므로 transformer가 아닌 **런타임 저장소**로 구현
- 의미론만 차용 — 코드는 직접 복사 아님

핵심 API:
- `declare_if_new(key, factory, varip=False)` — 첫 호출만 factory() 평가하여 저장, 이후는 기존 값
- `get(key)` / `set(key, value)` — 통상 read/write
- `begin_bar()` / `commit_bar()` / `rollback_bar()` — bar 경계 lifecycle
  - begin_bar: 현재 모든 var 값 스냅샷 (varip 제외)
  - commit_bar: 스냅샷 폐기 (bar 확정)
  - rollback_bar: var 값만 스냅샷으로 복원 (varip는 그대로) — realtime 재실행
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

_Key = str  # 의미: "{scope_name}::{var_name}" 포맷 관례 (인터프리터 책임)


@dataclass
class _Slot:
    """단일 persistent 변수의 내부 슬롯."""

    value: Any
    is_varip: bool


class PersistentStore:
    """var/varip 변수의 bar-bound state container.

    스레드 안전성: 현재 단일 스레드 사용 가정. 바 이벤트 루프는 직렬.
    """

    def __init__(self) -> None:
        self._slots: dict[_Key, _Slot] = {}
        # non-varip 값의 바 시작 스냅샷. rollback 시 복원 대상. begin_bar~commit/rollback 사이에만 non-None.
        self._bar_snapshot: dict[_Key, Any] | None = None

    # ---- 선언 / 조회 -------------------------------------------------

    def is_declared(self, key: _Key) -> bool:
        return key in self._slots

    def declare_if_new(
        self,
        key: _Key,
        factory: Callable[[], Any],
        *,
        varip: bool = False,
    ) -> Any:
        """첫 호출 시 factory()로 초기화하여 저장, 이후는 기존 값 반환.

        Pine의 `var x = expr` / `varip x = expr` 의미를 그대로 구현.
        expr은 factory 람다로 감싸 **lazy evaluation** — 첫 bar가 아니면 재평가 안 함.

        Args:
            key: 변수 식별자 (인터프리터가 (scope, name)으로 구성).
            factory: 첫 호출에서만 실행되는 초기값 생성자.
            varip: True면 varip semantics (롤백에서 제외).
        """
        if key not in self._slots:
            self._slots[key] = _Slot(value=factory(), is_varip=varip)
        return self._slots[key].value

    def get(self, key: _Key) -> Any:
        """현재 값 조회. 미선언 시 KeyError."""
        return self._slots[key].value

    def set(self, key: _Key, value: Any) -> None:
        """기존 변수에 값 할당. 미선언 변수에 set 금지 (declare_if_new 선행 필요)."""
        if key not in self._slots:
            raise KeyError(
                f"Persistent variable {key!r} not declared; "
                "call declare_if_new() first"
            )
        self._slots[key].value = value

    def is_varip(self, key: _Key) -> bool:
        return self._slots[key].is_varip

    # ---- Bar lifecycle ----------------------------------------------

    def begin_bar(self) -> None:
        """바 시작: non-varip 값 스냅샷.

        이미 begin 상태에서 재호출하면 기존 스냅샷 폐기 후 새로 — 인터프리터 버그 감지용.
        """
        self._bar_snapshot = {
            k: slot.value for k, slot in self._slots.items() if not slot.is_varip
        }

    def commit_bar(self) -> None:
        """바 확정: 스냅샷 폐기. 이후 rollback_bar 불가."""
        self._bar_snapshot = None

    def rollback_bar(self) -> None:
        """Realtime 바 재실행: var 값을 시작-of-bar로 복원. varip는 그대로 유지.

        begin_bar 이후 rollback 전에 declare된 NEW var는 삭제됨 (시작-of-bar에 없었으므로).
        varip는 모두 유지 (선언 전이든 후든).
        """
        if self._bar_snapshot is None:
            raise RuntimeError(
                "rollback_bar() called without begin_bar(); "
                "lifecycle: begin_bar() → (execute bar) → commit_bar() or rollback_bar()"
            )

        snapshot = self._bar_snapshot
        # 스냅샷에 없는 non-varip 슬롯은 '이번 바에서 새로 선언된 var' → 제거
        to_remove = [
            k for k, slot in self._slots.items()
            if not slot.is_varip and k not in snapshot
        ]
        for k in to_remove:
            del self._slots[k]

        # 스냅샷 값으로 복원
        for k, value in snapshot.items():
            if k in self._slots:
                self._slots[k].value = value
        # 스냅샷은 한 번 쓰고 폐기
        self._bar_snapshot = None

    # ---- Introspection ----------------------------------------------

    def __len__(self) -> int:
        return len(self._slots)

    def __contains__(self, key: object) -> bool:
        return isinstance(key, str) and key in self._slots

    def snapshot_dict(self) -> dict[_Key, Any]:
        """현재 모든 변수 값의 plain dict 복사 — 디버깅·테스트용."""
        return {k: slot.value for k, slot in self._slots.items()}
