# Sprint 37 — polish iter 5 Master Retrospective

**기간:** 2026-05-06 (단일 세션 + dogfood Day 7 측정 + 사용자 직접 hotfix `6434a1d` 발견)
**브랜치:** `main @ 96ad8ab` (7 PR 전부 머지 — #159/#160/#161/#162/#163/#164/#166)
**입력:** Sprint 36 Day 7 ≤6/10 → office-hours D 옵션 + spot-equivalent 결정 → Sprint 37 = polish iter 5
**Sprint 38 분기 결정:** **polish iter 6** (Day 7 self-assess 6/10 → gate (a) FAIL, Sprint 36 동일 점수 +1 미달성)

---

## 0. Sprint 37 7 PR 통합

```
96ad8ab PR #166 chore(sprint37): BL-187a + BL-188a + step hotfix (PR #165 conflict 해결 rebase)
0115aff PR #164 chore(sprint37): 백테스트 폼 simplify — leverage/funding 제거 + Spot-equivalent info row (BL-187)
b9dc5f7 PR #163 chore(infra): pre-push hook branch-prefix 화이트리스트 (Sprint 33 isolation 개선)
88511c5 PR #159 feat(sprint37): BL-185 Pine 포지션 사이징 spot-equivalent (PR1/3)
0089955 PR #161 feat(sprint37): BL-184 Equity / Buy&Hold curve PnL 시작점 정렬 (FE-only)
29242cd PR #160 feat(sprint37): MonteCarloSummaryTable 4 통계 노출 (BL-183, PR3/3)
f0c547c PR #162 chore(sprint37): BL-184/185/186 등록 + AGENTS 갱신 (PR4 docs)
```

**총 7 PR** (feat 3 + chore 3 + docs 1). PR #163 (infra hook 화이트리스트) 은 Sprint 33 worker isolation 개선 follow-up 으로 본 sprint 시점 묶어 머지.

---

## 1. 출발점 — office-hours D 옵션 + spot-equivalent 결정

### office-hours session (2026-05-06 오전)

- **Sprint 37 = polish iter 5** (Sprint 36 Day 7 ≤6/10 gate (a) FAIL + BL-183 발견)
- **D 옵션 (포지션 사이징 spot-equivalent foundation 우선)** 채택 — leverage/funding/liquidation 풀 모델은 BL-186 후속 deferred
- **3 PR open 병렬 작업** (BL-185 BE foundation + BL-184 FE PnL 정렬 + BL-183 MC 4 통계 표) — codex Phase 3.5 GO_WITH_FIXES 5 영역 surgery 적용
- **office-hours design doc**: `~/.gstack/projects/quant-bridge/woosung-main-design-20260506-084244.md`

### codex Phase 3.5 5 surgery 핵심 반영

- **in-loop running_equity** (codex 권장): `default_qty_type = percent_of_equity` 시 매 bar 갱신 equity 기반 quantity 산출 (entry-only running_equity 부족)
- **FE-only normalize** (codex 권장): BE BH curve absolute capital format 보존 — metrics/MC/stress 입력 안전 / FE `normalizeToPnlCurve` idempotent helper 만 PnL 정렬
- **leverage/funding UI cleanup** (사용자 통찰): initial_capital 배수로 우회 가능 + simple liquidation 도 trust 갉아먹음 → Sprint 37 EXCLUDE
- **SSOT explicit**: BL-185 default_qty_type `percent_of_equity / cash / fixed` 3종 명시 in-loop
- **별도 MC 테이블**: `MonteCarloSummaryTable` 컴포넌트 분리 (`MonteCarloFanChart` chart 책임 분리 유지)

---

## 2. PR별 핵심 변경

### PR #159 BL-185 — Pine 포지션 사이징 spot-equivalent (BE foundation)

- `qty=1` hardcode → `default_qty_type/value` 3종 (`percent_of_equity` / `cash` / `fixed`) in-loop
- BE pytest 626 → 633 (+7)
- **leverage / funding / liquidation EXCLUDE** (사용자 통찰 + Sprint 37 scope 경계). 풀 모델은 BL-186 후속.
- 변경 파일: `backend/src/strategy/pine_v2/types.py` + `engine/types.py` + `engine/v2_adapter.py` + `service.py`

### PR #161 BL-184 — Equity / Buy&Hold curve PnL 시작점 정렬 (FE-only)

- `normalizeToPnlCurve` idempotent helper — equity[0] = 0 시작 (TradingView 표준 정합)
- BE BH curve absolute capital format 보존 (codex 권장 — metrics/MC/stress 입력 안전)
- FE vitest 415 → 424 (+9)
- 변경 파일: `frontend/src/components/charts/equity-chart.tsx` + helper

### PR #160 BL-183 — MonteCarloSummaryTable 4 통계 노출

- `MonteCarloSummaryTable` 컴포넌트 신규 — CI 95% 하한/상한 / median_final_equity / MDD p95 4 통계 숫자 테이블
- `MonteCarloFanChart` chart 책임 분리 유지
- BE `MonteCarloResult` 계산값 활용 (BE 변경 X)
- FE vitest +9 (BL-184 와 합산)
- 변경 파일: `frontend/src/app/(dashboard)/backtests/[id]/_components/monte-carlo-summary-table.tsx` (NEW) + `monte-carlo-fan-chart.tsx`

### PR #162 docs — BL-184/185/186 등록 + AGENTS 갱신

- `docs/REFACTORING-BACKLOG.md` BL-184/185/186 신규 등록 + BL-150/176 Resolved 갱신
- `AGENTS.md` "현재 컨텍스트" Sprint 36 → Sprint 37 transition

### PR #163 infra — pre-push hook branch-prefix 화이트리스트

- Sprint 33 worker isolation 영구 차단 mechanism 개선 — `chore/`, `feat/`, `fix/`, `docs/`, `test/` 등 화이트리스트 prefix 만 push 허용
- 메인 worktree 이외 branch swap 시 push 거부 정책 강화

### PR #164 BL-187 — 백테스트 폼 simplify

- 백테스트 폼 `leverage / include_funding` input 제거 (Image 5 Live Settings vs Image 6 백테스트 UI 혼란 — 사용자 명시)
- "모델: Spot-equivalent" visible info row 추가 (assumptions-card)
- ui-ux-pro-max 옵션 2 채택 — payload default 자동 채움 (graceful upgrade 보존)
- 변경 파일: `frontend/src/app/(dashboard)/backtests/_components/backtest-form.tsx` + `assumptions-card.tsx`

### PR #166 BL-187a + BL-188a + step hotfix (PR #165 conflict 해결 rebase)

4 commits squash:

| commit    | 내용                                                                                          |
| --------- | --------------------------------------------------------------------------------------------- |
| `5e652f7` | `MonteCarloSummaryTable` testid 추가 (BL-187 dogfood Playwright 검증 보강)                    |
| `62325bb` | BL-187a — 라벨 "Spot-equivalent" → "1x · 롱/숏" + assumptions-card 의 레버리지/펀딩 row 제거  |
| `c90077e` | BL-188a — 백테스트 폼 default_qty 입력 + Pine override priority chain (Pine 명시 > 폼 > None) |
| `299958f` | **BL-188a hotfix — `default_qty_value` input `step="0.01"` → `"any"` (사용자 직접 발견)**     |

**BL-187a 사용자 명시:** "Spot" 단어 오해 (현물 = 롱만) + "레버리지 부분 일단 빼" → 라벨 simplify + assumptions-card row 제거.

**BL-188a:** PR #164 머지 후 worker rebuild 누락 시 Pine 미명시 + qty=1.0 silent fallback 으로 image 12 -249% MDD 노출 → 폼 입력 default `percent_of_equity 10%` 로 silent fallback 차단 + Pine override priority chain 정합.

---

## 3. PR #165 conflict 해결 패턴 (LESSON 후보)

### 발생

PR #164 squash 머지 시점 = `3b25aed` (BL-187 본체) 만 PR head. 이후 추가 commits push (testid `5e652f7` + BL-187a `62325bb` + BL-188a `c90077e`) + 사용자 hotfix `6434a1d` push. PR #165 가 **5 commits 모두 포함** 했으나 첫 commit `3b25aed` 가 main 의 squash `0115aff` 와 이중 적용 시도 → conflict.

### 해결

```bash
# PR #165 close → 새 branch rebase
git checkout chore/sprint37-bl187-form-simplify
git rebase --onto origin/main 3b25aed   # 첫 commit drop + 4 commits 만 main 위 깨끗 rebase
git checkout -b chore/sprint37-followup-resolved
git push -u origin chore/sprint37-followup-resolved   # PR #166 재생성
```

### 의의

- squash merge 후 **추가 commits 가 같은 branch 에 push 된 PR** = 이중 적용 충돌 표준 패턴
- 해결 = `--onto` 로 squash 된 commit drop + 새 branch push (기존 PR close)
- LESSON 후보: squash merge 후 follow-up 이 필요하면 **새 branch 분기** + 기존 branch 의 squash 된 commit 재사용 X

---

## 4. 사용자 직접 hotfix `6434a1d` 발견 (LESSON 후보)

### 발생 패턴

dogfood Day 7 검증 시 사용자가 백테스트 폼 `default_qty_value` 입력 (`percent_of_equity` 모드) 시 정수 20 입력 → HTML5 validation 거짓 reject:

```
유효한 값 2개는 19.9901 및 20.0001 입니다.
```

### Root cause

`<input type="number" step="0.01" min="0.0001">` 조합 시:

- `step="0.01"` 누적 시 floating point 오차 (`0.0001 + 0.01 * N` 가 정확한 정수 정렬 X)
- min=0.0001 + step=0.01 = "허용값은 0.0001, 0.0101, 0.0201, ... 19.9901, 20.0001, ..." → **정수 20 = 거짓 reject**

### Hotfix

```diff
- step="0.01"
+ step="any"
```

`step="any"` = Pine `default_qty_value` 의미와 정합 (임의 양수 허용 — 30, 0.01, 0.5 등 모든 양수). step 제약 자체가 부적절.

### 의의 (LESSON 후보)

- **agent QA depth 부족 패턴** — UI input HTML5 validation 누적 floating point 오차는 사전 detection 어려움
- **사용자 직접 dogfood 발견 의무** = critical regression 마지막 gate (Sprint 33 lesson #6 재확인)
- **예방 패턴**: 임의 양수 입력 컴포넌트는 `step="any"` 디폴트 / step 제약은 격자 의도 명시일 때만

---

## 5. Day 7 4중 AND gate 결과

| Gate    | 항목                                                 | 결과            | 근거                                                                                    |
| ------- | ---------------------------------------------------- | --------------- | --------------------------------------------------------------------------------------- |
| **(a)** | self-assess ≥7/10 (근거 ≥3 줄)                       | **FAIL (6/10)** | Sprint 36 동일 점수 — Sprint 37 polish iter 5 가 +1 기여 부족                           |
| (b)     | BL-178 production BH curve 정상 (3 backtest != null) | ✅ PASS         | worker rebuild 후 screenshot 02 비-null + Day 7 P-1 PASS                                |
| (c)     | BL-180 hand oracle 8 test all GREEN                  | ✅ PASS         | PR #155 (Sprint 35) 이후 유지 — `tests/backtest/test_golden_oracle_minimal.py`          |
| (d)     | Sprint-37-caused P0=0 + P1=0 + 기존 deferred 명시    | ✅ PASS         | 신규 BL-186 deferred 명시 / BL-188 narrowest wedge 후보 등록 / Sprint 37 신규 P0/P1 = 0 |

### Day 7 self-assess 6/10 근거 3줄

> **사용자 final pass 입력 후 보정** — 아래는 dogfood Day 7 (Sprint 36) entry + Sprint 37 PR/BL 변동 기반 default 추정.

1. **BL-188 (Live Settings ↔ 백테스트 mirror) 미진행 = 사용자 직접 명시한 trust 갭 잔존** — 백테스트 폼 `default_qty` 입력 정합화는 됐으나 Live Session Trading Settings 와 mirror 까지는 분리. 사용자 직관 = "Live 의 Trading Settings 가 백테스트에 적용되어야 한다".
2. **사용자 직접 hotfix `6434a1d` 발생 = agent QA 검증 누락** — UI input `step="0.01"` floating point 거짓 reject 가 dogfood Day 7 시점 사용자 입력 실패로만 발견. agent 사전 detection 부재 (Playwright MCP 자동화 시점 cover 안 됨).
3. **BL-186 풀 leverage / funding / mm / liquidation 풀 모델 deferred** — Sprint 37 BL-185 spot-equivalent foundation 채택 후 풀 모델 미진행. dogfood 사용자 trust 측면에서 "스팟 동등 = 단순화" 인정하나 +1 기여 부족.

### → 4중 AND gate (a) FAIL → Sprint 38 = polish iter 6

**BL-003 (Bybit mainnet runbook) + BL-005 본격 (1-2주 mainnet)** = gate 전체 통과 후로 deferred 유지. Sprint 38 narrowest wedge 후보 = BL-188 / BL-181 / 기타 BL (close-out 후 office-hours 결정).

---

## 6. BL 변동

### Resolved (Sprint 37)

| BL ID   | 내용                                                       | PR   |
| ------- | ---------------------------------------------------------- | ---- |
| BL-183  | MC 4 통계 테이블 FE 노출                                   | #160 |
| BL-184  | Equity/BH curve PnL 시작점 정렬                            | #161 |
| BL-185  | Pine 포지션 사이징 spot-equivalent foundation              | #159 |
| BL-187  | 백테스트 폼 simplify (leverage/funding row 제거)           | #164 |
| BL-187a | 라벨 simplify + assumptions-card row 제거                  | #166 |
| BL-188a | 백테스트 폼 default_qty 입력 + Pine override + step hotfix | #166 |

### 신규 등록

| BL ID  | Priority | Trigger                            | Est          | 내용                                                                                                              |
| ------ | -------- | ---------------------------------- | ------------ | ----------------------------------------------------------------------------------------------------------------- |
| BL-186 | P2       | Sprint 38+ deferred                | M-L (16-24h) | Full leverage + funding + mm + liquidation 풀 모델 (BL-185 foundation 위)                                         |
| BL-188 | P1       | **Sprint 38 narrowest wedge 후보** | M (8-12h)    | 백테스트 폼 ↔ Live Session Trading Settings mirror (옵션 C — Position Size / Sessions auto-fetch + Pine override) |

### 합계 변동

- 시작 = **89 active BL** (Sprint 36 종료 시점, PR #162 머지 후 BL-184/185/186 등록 결과)
- Resolved 6건 (-6) + 신규 4건 (+4 = BL-187 + BL-187a + BL-188 + BL-188a, BL-184/185/186 은 PR #162 시 이미 등록됨)
- **종료 = 87 active BL**

---

## 7. 신규 lesson 후보 (Sprint 38+ 검증)

> `.ai/project/lessons.md` 영구 승격 검토 대상.

1. **squash merge 후 follow-up = 새 branch 분기 의무 (PR #165 conflict 해결 패턴)** — squash 된 commit 이 추가 commits 와 함께 같은 branch 에 push 시 이중 적용 충돌. 해결 = `git rebase --onto origin/main <squashed-commit>` + 새 branch push (기존 PR close).
2. **`<input type="number">` 임의 양수 = `step="any"` 디폴트 (사용자 hotfix `6434a1d` 패턴)** — `step=0.01` + `min=0.0001` 누적 floating point 오차 = 정수 거짓 reject. step 제약은 격자 의도 명시일 때만 (예: 가격 tick size).
3. **dogfood = critical regression 마지막 gate (BL-188a hotfix 사용자 직접 발견)** — Playwright MCP 자동화 + agent QA 가 cover 못하는 UI 누적 오차 / 사용자 의도 mismatch 는 dogfood 만 detection 가능. Sprint 33 lesson #6 (이미 영구 룰) 재확인.
4. **office-hours D 옵션 + EXCLUDE 패턴 효과** — leverage/funding/liquidation 풀 모델 deferred (BL-186) + spot-equivalent foundation 채택 = "trust 갉아먹는 partial impl" 회피. simple liquidation 도 정확하지 않으면 trust 갉아먹음 (사용자 통찰).

---

## 8. dual metric

- **7 PR** (#159~#162 + #163 + #164 + #166, feat 3 + chore 3 + docs 1)
- **backend pytest 626 → 633 (+7)** (BL-185 in-loop running_equity + 3 default_qty_type)
- **frontend vitest 415 → 424 (+9)** (BL-184 normalizeToPnlCurve + BL-183 MonteCarloSummaryTable + BL-187/187a/188a)
- **mypy 0 / ruff 0 / tsc 0 / eslint 0**
- **codex Phase 3.5 surgery 5 영역** (in-loop running_equity / FE-only normalize / leverage UI cleanup / SSOT explicit / 별도 MC 테이블)
- **Day 7 self-assess 6/10** (gate (a) FAIL — Sprint 36 동일 점수, +1 미달성)
- **사용자 직접 hotfix 1건** (`6434a1d` = `default_qty_value` step="any" — agent QA 누락 패턴)
- **PR #165 → #166 conflict 해결 1건** (`git rebase --onto origin/main 3b25aed` 패턴)
- **Stretch BL-181 (Docker worker auto-rebuild) = 미착수** — Sprint 38 polish iter 6 후보 유지

---

## 9. Sprint 38 narrowest wedge 후보 3안

> 본 master 기록용. 최종 결정은 close-out PR 머지 후 별도 office-hours session.

| 후보   | 명칭                                   | Est       | 추천도 | 근거                                                                     |
| ------ | -------------------------------------- | --------- | ------ | ------------------------------------------------------------------------ |
| BL-188 | Live Settings ↔ 백테스트 mirror        | M (8-12h) | ★★★★★  | 사용자 직접 trust 갭 명시 + dogfood 가치 ↑ + Day 7 self-assess +1 가능성 |
| BL-181 | Docker worker auto-rebuild on PR merge | M (3-4h)  | ★★★★☆  | BL-178/188a 재발 패턴 차단 / infra debt / 사용자 망각 silent stale 방지  |
| BL-003 | Bybit mainnet runbook + smoke 스크립트 | M (4-5h)  | ★★☆☆☆  | gate 전체 통과 후로 deferred 유지 (Sprint 38 후보 X — Day 7 (a) FAIL)    |

**default 권장:** BL-188 (사용자 직접 trust 갭 + Surface Trust pillar 직접 + dogfood 가치 ↑) — 단 사용자 office-hours 결정 우선.

---

## Cross-link

- handoff memory: `~/.claude/projects/-Users-woosung-project-agy-project-quant-bridge/memory/project_sprint37_day7_handoff.md`
- Sprint 36 dogfood Day 7 entry: `docs/dev-log/2026-05-06-dogfood-day7-sprint36.md` (BL-183 발견 + Day 7 ≤6/10 borderline)
- 직전 Sprint 35 retro (master 포맷 차용): `docs/dev-log/2026-05-05-sprint35-master-retrospective.md`
- office-hours design doc: `~/.gstack/projects/quant-bridge/woosung-main-design-20260506-084244.md`
- BACKLOG: `docs/REFACTORING-BACKLOG.md` (BL-183/184/185/187/187a/188a Resolved + BL-186/188 신규 deferred)
- Playwright Day 7 screenshots: `.claude/playwright-day7/01-04-*.png`
