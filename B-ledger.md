# BL-783 레인 β 원장 초안

**상태:** ✅ **Resolved (2026-08-17, 커밋 대기 — push/PR 은 사람 몫).** Stress Test 의 엔진 재실행 3경로가
부모 Backtest 에 핀된 `StrategyVersion` 스냅샷을 쓴다. `_RunContext.strategy: Strategy` →
`pine_source: str` 로 타입을 좁혀 호출부에서 현재 소스를 다시 읽을 문 자체를 닫았고, 핀 조회는
`_resolve_pinned_pine_source` 한 곳이다([BL-773] optimizer 처방과 동형). `strategy_version_id` NULL 인
legacy 행만 현재 Strategy 로 떨어지고 그 경로는 `stress_test_run_without_pinned_strategy_version`
경고를 남긴다. `grep -c strategy_version .../stress_test/service.py` **0 → 7**.
★**표적 변이 5/5 red 이고 3경로가 각각 독립으로 red** — `:427`(CA/PS) · `:360`(WFO) · `:380`(plain WF)
를 하나씩 되돌리면 그 경로의 테스트만 정확히 깨진다. AC-3 은 diff 로 확정(MC 관련 줄 **0건**,
`_execute_monte_carlo` 는 `strategy`·`_load_run_context` 를 **한 번도 참조하지 않는다**).
게이트 `--pre-pr` rc=0 · 전량 BE pytest rc=0 **4759 passed**(기준선 4753 + 신규 6).
★**낡은 mock 2곳이 이 회차에도 있었다**([LESSON-116] 재현) — `_bt()` 의 `SimpleNamespace` 에
`id`·`strategy_version_id` 가 없어 라우팅 테스트 3건이 `AttributeError` 로 깨졌고,
config-propagation 의 bare `AsyncMock` 은 `get_version_by_id` 가 MagicMock 을 돌려줘 **초록이면서도
무엇을 실행하는지 말할 수 없는** 상태였다. 둘 다 명시 스냅샷으로 고쳤다.
★**미채택 1건** — optimizer 에 있는 `engine_version` 가드는 옮기지 않았다(범위 밖 + AC 없음, 아래 참조).

## 레인이 확인하지 못한 것

- **거래소·celery 경유 라이브 검증 없음.** 계약이 워크트리 celery 검증을 금지하고 이 항목은
  worker 코드가 아니라 service 순수 경로라, 검증은 pytest(DB 포함)까지다. 브라우저 실사용
  대조(Pine A 백테스트 → B 로 수정 → WF 실행)는 하지 않았다.
- **`--deferred-only` 미실행.** 계약대로 `--pre-pr` 까지가 이 레인 몫이다. e2e 는 안 돌렸다.

## 분리 제안 — optimizer 의 `engine_version` 가드가 stress_test 에 없다

PR #650 의 optimizer 처방에는 `bt.engine_version not in (None, PINE_V2_ENGINE_VERSION)` 이면
거부하는 가드가 있는데, 레인 파일이 복제 대상으로 열거한 것은 **스냅샷 조회 + 폴백 경고**뿐이라
옮기지 않았다. 옮기면 동작이 바뀌고(비-pine_v2 부모에 대해 stress test 가 실패한다) 그것을 재는
AC 가 없다. Stress Test 도 같은 엔진을 재실행하므로 같은 부류의 결함으로 보이지만,
**측정하지 않았다** — 새 BL 로 등재할지는 오케스트레이터 판단이다.

## 부수 관측 (BL 미등재)

- `backtests.strategy_version_id` 의 FK 는 `ondelete="RESTRICT"` 라 **「핀은 있는데 스냅샷 행이
  없다」는 오늘의 DB 에서 도달 불가**다(실측: 존재하지 않는 UUID 를 넣으면 `ForeignKeyViolationError`).
  그 분기 테스트만 repo mock 으로 세웠고, 이유를 테스트 docstring 에 남겼다. 가드 자체는 optimizer
  와의 짝을 위해 유지했다.
- `ruff format` 을 `tests/stress_test/` 디렉터리 단위로 돌리면 **손대지 않은 15파일이 재포맷**된다.
  되돌리고 편집한 3파일만 남겼다 — pre-commit 은 staged 파일만 포맷하므로 나머지는 원래대로다.
