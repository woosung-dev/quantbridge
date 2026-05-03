# Sprint 24b — Track 1 Backend E2E 자동 dogfood

**날짜**: 2026-05-03 (Sprint 22+23+24a main 머지 완료 직후, PR #95)
**브랜치**: `stage/h2-sprint24b` (main 에서 새 cascade)
**범위**: Track 1 자동 dogfood 6 시나리오 + entry script (Sprint 24 의 Track 1, BL 등록 없음 — 순수 자동 회귀 가드)

---

## §1. 배경

Sprint 22+23+24a cascade main 머지 완료 (PR #95). 사용자 dogfood Day 2-7 늦추는 동안 AI 가 진행할 next workflow phase 의 Track 1. Sprint 24a (Track 2 WS 안정화) 이미 완료, 본 sprint 가 Sprint 24 의 Track 1 마무리.

dogfood Day 2-7 critical path 6 시나리오 자동 회귀 가드:

- 매 sprint 끝 자동 실행 → Pain 사전 감지
- 사용자 본인 dogfood (BL-005) 와 병렬 진행 시 시너지

---

## §2. Implementation

### Phase C.1 — `test_auto_dogfood.py` 6 시나리오

**신규**: `backend/tests/integration/test_auto_dogfood.py` (`pytestmark = pytest.mark.integration`)

| #   | 시나리오                            | 검증 대상                                                     |
| --- | ----------------------------------- | ------------------------------------------------------------- |
| 1   | strategy_with_webhook_secret_atomic | Sprint 13 broken bug 회귀 (DB row 정합)                       |
| 2   | backtest_engine_smoke               | run_backtest_v2 import + Pine v5 detection                    |
| 3   | order_dispatch_snapshot             | Sprint 22+23 BL-091/102 (JSONB + dispatch helper)             |
| 4   | snapshot_drift_rejected             | Sprint 23 G.2 P1 #1 (split-brain prevention, SQL UPDATE 시뮬) |
| 5   | multi_account_dispatch              | Sprint 24a BL-011/012 (bybit + okx 동시 + lease key 격리)     |
| 6   | summary_parse_smoke                 | 자동 summary JSON schema (codex G.0 P1 #5)                    |

**검증**: 6 시나리오 모두 PASS (`--run-integration` flag 명시), ruff 0 / mypy 0.

**Service direct call 패턴**: Clerk auth 우회. HTTP route + Clerk JWT 는 별도 e2e (`test_trading_e2e.py`) 가 가드.

### Phase C.2 — `run_auto_dogfood.py` entry script

**신규**: `backend/scripts/run_auto_dogfood.py`

- `subprocess.run(["uv", "run", "pytest", "--run-integration", ...])` 명시 호출 (codex G.0 P2 #3)
- pytest stdout 텍스트 파싱 (PASSED/FAILED count + scenario marker substring)
- **별도 summary 산출물 2건** (codex G.0 P1 #5 — `dogfood_report._async_generate()` 와 분리):
  - `docs/reports/auto-dogfood/<YYYY-MM-DD>.json` — pytest 결과 + 시나리오 metadata
  - `docs/reports/auto-dogfood/<YYYY-MM-DD>.html` — 사람 친화적 요약 (table + tail logs)

**사용법**:

```bash
make up-isolated  # 격리 stack
TEST_DATABASE_URL=postgresql+asyncpg://quantbridge:password@localhost:5433/quantbridge \
TEST_REDIS_LOCK_URL=redis://localhost:6380/3 \
python backend/scripts/run_auto_dogfood.py
```

---

## §3. codex Generator-Evaluator

### 3.1 G.0 (medium) — Sprint 24 plan v2 시점에 이미 적용 (Track 1+2 통합)

P1 #5 (dogfood_report 재사용 과장) + P2 #2 (multi-account scenario) + P2 #3 (--run-integration subprocess) 모두 본 sprint 24b 에 그대로 반영.

### 3.2 G.2 (high reasoning, 1 iter, ~38k tokens)

**Verdict**: FIX FIRST → P1 #3 즉시 fix, P1 #1+#2 + P2 4건 → BL-112~115 신규.

**P1 3건**:

| ID  | 발견                                                                      | 본 sprint 처리                                                                                            |
| --- | ------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------- |
| #1  | scenario 2 가 실제 backtest 실행 안 함 (callable + \_detect_version 만)   | 🔜 BL-112 신규 (Sprint 25+, P2 S)                                                                         |
| #2  | scenario 3 Order 직접 INSERT — service auto-fill path 우회                | 🔜 BL-113 신규 (Sprint 25+, P2 S)                                                                         |
| #3  | scenario 6 가 `_build_summary` 직접 호출 안 함 (sample_report hard-coded) | ✅ Phase D 즉시 fix — `_build_summary(rc=1, fake_stdout, "")` 호출 + counts/exit_code/scenario count 검증 |

**P2 4건**:

- #1: runner cwd 가정 → BL 미등록 (단순 사용 시점 처리)
- #2: stdout 텍스트 파싱 fragility (pytest-json-report) → BL-114 (P3 S 30m)
- #3: report artifacts .gitignore → 즉시 처리 (.gitignore 추가)
- #4: HTML output 미escape (script injection) → BL-115 (P3 S 15m)

**False Alarms**: service direct call 한계는 docstring 명시 + 별도 commit-spy / route test 가 가드.

---

## §4. 검증 결과

### 자동 검증

```
TEST_DATABASE_URL=...localhost:5433/quantbridge \
TEST_REDIS_LOCK_URL=...localhost:6380/3 \
uv run pytest --run-integration tests/integration/test_auto_dogfood.py -v
```

- **6 시나리오 100% PASS** (0.5s)
- ruff 0 / mypy 0 (147 src files)

### 라이브 검증 (사용자 후속)

```bash
python backend/scripts/run_auto_dogfood.py
# stdout: 시나리오별 PASS/FAIL + Total: 6/6 PASS
# JSON: docs/reports/auto-dogfood/<date>.json
# HTML: docs/reports/auto-dogfood/<date>.html
```

---

## §5. 신규 BL 등록 / 변동

### Resolved

본 sprint 는 BL 직접 처리 안 함 (자동 회귀 가드). Sprint 22+23+24a 의 검증 자동화.

### 등록 (codex G.2 결과)

- BL-112 (P2 S 1-2h, G.2 P1 #1) — scenario2 backtest 실제 실행
- BL-113 (P2 S 1-2h, G.2 P1 #2) — scenario3 OrderService.execute 통한 검증
- BL-114 (P3 S 30m, G.2 P2 #2) — pytest-json-report 또는 JUnit XML
- BL-115 (P3 S 15m, G.2 P2 #4) — HTML output html.escape

### 합계

기존 67 BL → Sprint 24b 후 **71 BL** (등록 4건, Resolved 0건).

---

## §6. Sprint 25+ 계획

- BL-005 사용자 본인 dogfood Day 2-7 (1-2주, AI 가 대체 불가)
  - 본 sprint 의 자동 dogfood 가 매 commit 회귀 가드
- BL-104/105/106/107 Sprint 23 후속 cleanup
- BL-108/109/110/111 Sprint 24a 후속 (G.2 P2)
- BL-014 partial fill cumExecQty
- BL-015 OKX private WS

---

## §7. 참조

- Sprint 24 plan v2 (Track 1+2 통합): `~/.claude/plans/claude-plans-h2-sprint-22-prompt-md-elegant-cerf.md`
- Sprint 24a dev-log (Track 2): `docs/dev-log/2026-05-03-sprint24a-ws-stability.md`
- BL 상세: `docs/REFACTORING-BACKLOG.md`
