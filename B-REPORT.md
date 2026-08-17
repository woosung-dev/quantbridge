# 레인 β 보고 — [BL-783] Stress Test 가 실행 시점 mutable Pine 을 읽던 결함

브랜치 `stage/bl783-stress` · 메인 체크아웃(슬롯 0) · 커밋까지 완료, push/PR 미수행(계약대로).

## 무엇이 됐나

`apps/api/src/stress_test/service.py` 의 엔진 재실행 3경로가 전부 부모 Backtest 에 핀된
`StrategyVersion.pine_source` 스냅샷을 쓴다. 변경은 셋이다.

1. **`_RunContext.strategy: Strategy` → `pine_source: str`.** 호출부가 `ctx.strategy.pine_source` 로
   현재 소스를 다시 읽을 수 있는 문을 타입으로 닫았다. 필드가 사라졌으므로 되돌리는 변이는
   컴파일이 아니라 테스트에서 잡힌다.
2. **`_resolve_pinned_pine_source(bt, kind_label=...)` 신설.** 핀 조회는 이 한 곳이다.
   `strategy_repo.get_version_by_id(bt.strategy_version_id, strategy_id=bt.strategy_id)` →
   핀이 있는데 스냅샷이 없으면 `ValueError` → 핀이 없으면(legacy) `logger.warning` 후 현재 Strategy.
3. **호출 3곳 치환** — `run_walk_forward_optimization` · `run_walk_forward` · `engine_fn`(CA/PS 공통).

`grep -c strategy_version apps/api/src/stress_test/service.py` = **0 → 7**.

## 수용 기준별 판정

| AC                                                  | 판정 | 증거                                                                                                                                                                                      |
| --------------------------------------------------- | ---- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **AC-1** 핀 고정 테스트 신설, 구현 전 red           | ✅   | 신설 `tests/stress_test/test_strategy_version_pinning.py` 6건. 구현 전 `rc=1` **6 failed**, 실패 사유가 정확히 `'...version B...' != '...version A...'` (설정 오류가 아니라 결함 재현)    |
| **AC-2** 엔진 재실행 3경로 전부 스냅샷              | ✅   | 3경로를 하나씩 되돌리는 변이 M2a/M2b/M2c 가 **각각 독립으로** 해당 테스트만 red (아래 표)                                                                                                 |
| **AC-3** Monte Carlo 미변경                         | ✅   | `git diff -U0 -- .../service.py \| grep -i "monte_carlo\|equity_curve\|mc_result"` = **0건**. `_execute_monte_carlo` 본문에 `strategy`·`_load_run_context` **0회**                        |
| **AC-4** legacy 폴백 경고 + 그 로그가 나오는 테스트 | ✅   | `test_legacy_backtest_without_pinned_version_falls_back_and_warns` 가 `caplog` 로 `stress_test_run_without_pinned_strategy_version` WARNING **정확히 1건** 확인. 변이 M3(경고 삭제) → red |
| **AC-5** 전량 BE pytest rc=0, ≥4753                 | ✅   | **rc=0 · 4759 passed, 32 skipped** (431.26s). 기준선은 브랜치 작업 **전에** 실측 = rc=0 · **4753 passed**                                                                                 |

## 변이 결과표

심기·되돌리기는 문자열 치환 쌍(`git checkout` 금지)이고, 되돌린 뒤 **심을 때 쓰지 않은 방법**으로
확인했다 — 파일 sha256 이 변이 전 스냅샷 `44f0cf54d377…` 과 일치하는지 + 변이 페이로드 문자열
부재를 직접 셈. 5회 전부 일치했다. 앵커는 심기 전 **정확히 1건**임을 확인했다.

| 변이    | 무엇을 되돌렸나                                                           | rc  | red 가 난 테스트                                 | 기대와 일치  |
| ------- | ------------------------------------------------------------------------- | --- | ------------------------------------------------ | ------------ |
| **M1**  | `_resolve_pinned_pine_source` 의 핀 조회 자체 (= 실행 시점 Strategy 읽기) | 1   | 핀 4건 + missing-version 1건 = **5 failed**      | ✅ AC-1 red  |
| **M2a** | `:427` grid sweep(`engine_fn`)만                                          | 1   | cost_assumption · param_stability = **2 failed** | ✅ 그 경로만 |
| **M2b** | `:360` walk-forward optimization 만                                       | 1   | walk_forward_optimization = **1 failed**         | ✅ 그 경로만 |
| **M2c** | `:380` plain/fixed-param WF 만                                            | 1   | walk_forward = **1 failed**                      | ✅ 그 경로만 |
| **M3**  | legacy 폴백 `logger.warning` 삭제                                         | 1   | legacy_falls_back_and_warns = **1 failed**       | ✅ AC-4 red  |

M1 에서 AC-4 테스트가 green 인 것은 정상이다 — M1 은 폴백을 전 경로에 적용하는 변이이고
AC-4 테스트는 애초에 폴백 경로를 재기 때문이다.

## 이 회차에 드러난 것

**낡은 mock 2곳이 또 있었다** — 계약이 경고한 그 자리다.

- `test_service_walk_forward_routing.py` 의 `_bt()` 는 `SimpleNamespace` 인데 `id`·`strategy_version_id`
  가 없어 구현 직후 3건이 `AttributeError` 로 깨졌다. 표적 테스트만 봤으면 놓쳤다.
- `test_service_backtest_config_propagation.py` 의 bare `AsyncMock` 은 `get_version_by_id` 가
  MagicMock 을 돌려주고 `.pine_source` 도 MagicMock 이라 **초록이면서 무엇을 실행하는지 말할 수
  없는** 상태였다. 두 double 모두 명시 스냅샷을 주도록 고쳤다.

**여섯 번째 테스트의 전제가 DB 제약과 충돌했다.** 「핀은 있는데 스냅샷 행이 없다」를 DB 로
만들려다 `ForeignKeyViolationError` — `backtests.strategy_version_id` FK 가 `ondelete="RESTRICT"` 라
그 상태는 **오늘 도달 불가**다. 그 케이스만 repo mock 으로 옮기고 이유를 docstring 에 남겼다.
가드는 optimizer 와의 짝을 위해 유지했다(없으면 「핀이 있는데 못 찾음」이 「현재 소스로 실행」과
구분되지 않는다).

**`ruff format` 을 디렉터리로 돌렸더니 손대지 않은 15파일이 재포맷됐다.** 되돌리고 편집한 3파일만
남겼다. 최종 변경은 4파일(신규 1 포함)이다.

## 확인하지 못한 것

- **브라우저·celery 라이브 대조 없음.** 「Pine A 백테스트 → B 로 수정 → WF 실행」의 실사용 재현은
  하지 않았다. 계약이 워크트리 celery 검증을 금지하고, 이 변경은 worker 진입점이 아니라 service
  순수 경로라 pytest(DB 포함)까지가 이 레인의 증거다. **엔진에 어떤 source 가 갔는지는 spy 로
  쟀고, 그 spy 는 실제 엔진 호출 자리에 있다.**
- **`--deferred-only` 미실행 → e2e 안 돌림.** 계약대로 `--pre-pr` 까지가 몫이다. 유예분은
  `.claude/gates/bl783-stress/deferred.txt` 에 남아 있고, 그것이 남아 있는 한 종결이 아니다.
- **optimizer 의 `engine_version` 가드는 옮기지 않았다.** 범위 밖이고 AC 가 없다. 같은 부류로
  보이지만 **측정하지 않았다** — 판단은 `B-ledger.md` 의 분리 제안에 적었다.

## 변경 파일

| 파일                                                                     | 성격                                                                            |
| ------------------------------------------------------------------------ | ------------------------------------------------------------------------------- |
| `apps/api/src/stress_test/service.py`                                    | 구현 — `_RunContext` 필드 축소 + `_resolve_pinned_pine_source` 신설 + 호출 3곳  |
| `apps/api/tests/stress_test/test_strategy_version_pinning.py`            | **신규** — 핀 4경로 + legacy 경고 + missing-version 가드 (6건)                  |
| `apps/api/tests/stress_test/test_service_walk_forward_routing.py`        | double 수리 — `_bt()` 에 `id`·`strategy_version_id`, `get_version_by_id` 스냅샷 |
| `apps/api/tests/stress_test/test_service_backtest_config_propagation.py` | double 수리 — 핀 UUID + `get_version_by_id` 스냅샷                              |

migration 은 만들지 않았다 — `Backtest.strategy_version_id` 는 PR #650 이 이미 만들었고,
새 컬럼이 필요한 자리는 없었다.
