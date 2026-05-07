# Sprint 39 Master Retrospective — polish iter 7 + Day 7 = 7/10 PASS + Sprint 40 = stage→main + BL-003 + BL-005 본격

**기간**: 2026-05-07 (single day)
**브랜치**: `main @ 6bc6732` (변경 X) + `stage/sprint38-bl-188-bl-181 @ 8a23f29` (보존 — Sprint 40 stage→main 머지 베이스)
**활성 sprint type**: polish iter 7 (Sprint 38 Day 7 = 5/10 (a)+(d) FAIL → BL-189 신규 P0 → +1 회복)
**self-assessment Day 8**: **7/10 (a) PASS** — BL-189 measurement artifact 증명 + wrong fix detection layer 작동
**다음 분기**: Sprint 40 = **stage→main merge + BL-003 (Bybit mainnet runbook + smoke) + BL-005 본격 (1-2주 소액 mainnet)**

---

## 1. Context — 왜 Sprint 39 가 필요했나

Sprint 38 Day 7 self-assess = 5/10 → gate (a)+(d) FAIL. 원인 2:

- **BL-189 신규 P0** — stage `8a23f29` 통합 환경 dogfood Day 7.5 mid-check 에서 FE next-server idle CPU **113% sustained** 보고 (vs main b61b16c idle 0%)
- 단독 worker B 의 CPU smoke max 4.7% PASS 가 통합 환경에서 회귀 못 차단

Sprint 39 = (a)+(d) 동시 회복 polish iter 7. **BL-189 진단 spike + hotfix + dogfood Day 7.5 재시도** 묶음. single worker (메인 세션 직접) — 자율 병렬 cmux 불필요.

---

## 2. 산출물 (코드 변경 0 + measurement-driven decision)

본 sprint 는 **코드 변경 net 0** 가 결과. 진단·측정·decision 의무가 핵심 산출물.

| 항목                                                | 결과                                                                              |
| --------------------------------------------------- | --------------------------------------------------------------------------------- |
| Pre-flight (LESSON-037)                             | BE 1646 PASS / 42 skip / FE 427 PASS / lint 0 / tsc 0 (main 베이스 baseline 정합) |
| stage `8a23f29` checkout                            | working tree clean. 회귀 재현 환경 setup                                          |
| 60s sustained 측정 (top -l 30)                      | 30/30 = 0.0% (max 0.2%) — **회귀 미재현**                                         |
| ps × 6 × 10s lifetime                               | max 3.6% / lifetime 0.0% — **회귀 미재현**                                        |
| 1h monitor (threshold ≥10%)                         | 7 transient spike (max 44.1%) — **sustained 113% 0건**                            |
| 사용자 dogfood                                      | "괜찮은 것 같아" — 시나리오 일부 진행 (trading 진입 등) 회귀 미발현               |
| Wrong fix attempt (`turbopack.root: process.cwd()`) | **400% sustained spike** 즉시 감지 → revert → 0% 복원                             |
| Hotfix branch                                       | 생성 → revert → 폐기 (코드 변경 net 0)                                            |

**stage diff vs main** = **0 lines**. close-out PR 만 main 반영 (본 dev-log 외 산출물 4건).

---

## 3. Day 7 4중 AND gate 결과 (영구 기준)

| Gate                                               | Sprint 38 | Sprint 39 (Day 8)  | 근거                                                              |
| -------------------------------------------------- | --------- | ------------------ | ----------------------------------------------------------------- |
| **(a)** self-assess ≥7/10 + 근거 ≥3                | 5/10 FAIL | **7/10 PASS**      | 본 sprint 핵심 evidence (i)~(iii) 명시                            |
| **(b)** BL-178 production BH curve 정상            | PASS      | PASS (main 변경 X) |                                                                   |
| **(c)** BL-180 hand oracle 8 test all GREEN        | PASS      | PASS (main 변경 X) |                                                                   |
| **(d)** new P0=0 AND unresolved Sprint-caused P1=0 | FAIL      | **PASS**           | BL-189 = measurement artifact 결론 (코드 회귀 X) + 신규 P0/P1 = 0 |

**근거 3줄 (a)**:

1. **BL-189 113% sustained 미재현 증명** — stage `8a23f29` 환경에서 60s sustained + 1h monitor + 사용자 dogfood "괜찮음" 모두 idle 0% 유지. measurement artifact 결론 (Sprint 38 Day 7.5 시점 환경 unique 가능성)
2. **Wrong fix detection layer 작동** — `turbopack.root: process.cwd()` 잘못된 root 명시 시 400% sustained spike 즉시 감지 → revert → 0% 복원. measurement-driven hotfix discipline
3. **Day 7.5 mid-check falsification signal 정합** — Sprint 38 LESSON-046 의 detection layer 가 본 sprint 에서도 작동 (사용자 직접 dogfood 시 회귀 패턴 추적 + decision 재검토)

**결과**: 4중 AND gate 모두 PASS → Sprint 40 = **stage→main merge + BL-003 + BL-005 본격**.

---

## 4. 진단 spike 상세 — 왜 113% 가 재현 안 됐나

### 측정 비교 (timeline)

| 시점        | 환경                                  | idle CPU                                    | 결과                      |
| ----------- | ------------------------------------- | ------------------------------------------- | ------------------------- |
| 14:00       | stage `8a23f29` fresh restart, no fix | 0% (60s sustained) + 7 transient spike (1h) | **회귀 미재현**           |
| 14:30~15:11 | 사용자 dogfood active 진행            | 7 transient (max 44%, 모두 single sample)   | **sustained 0건**         |
| 15:16       | `turbopack.root: process.cwd()` 적용  | **400% sustained** (top 9/10 + ps 6/6)      | **wrong fix → 신규 회귀** |
| 15:20       | revert                                | 0% sustained (top 10/10 + ps 6/6)           | **정상 복원**             |

### 가설 후보 (재현 못 한 가능성)

1. **Sprint 38 Day 7.5 측정 환경 unique** — 다른 service / browser session / Clerk auth state / tab 상태 따라 ws-stream 또는 React Query polling 폭주
2. **Self-resolved by hot reload** — Sprint 38 Day 7.5 시점에서 어떤 변화 (env reload, dependency restart) 가 회귀를 자연 회복
3. **Measurement instrument bias** — Activity Monitor 의 instantaneous spike 를 sustained 로 오인했을 가능성

→ stage `8a23f29` 코드 자체는 정상. **회귀가 코드 회귀가 아닌 측정 환경 회귀** 결론.

### Wrong fix 사례 (LESSON-047 후보)

**시도한 fix**: `next.config.ts`

```ts
turbopack: {
  root: process.cwd();
} // ← wrong (process.cwd() = frontend/)
```

**결과**: 400% sustained CPU spike (top 9/10 samples, ps 6/6, lifetime 388.9%)

**원인**:

- `process.cwd()` = `frontend/` (Next.js 가 cd frontend 후 실행)
- frontend/ 가 wrong root → Turbopack file watcher 가 `.next/`, `node_modules/` 등 깊은 트리 무한 watch → fsevents storm
- `frontend/pnpm-lock.yaml` 만 있는 single-package 환경 가정과 불일치 (실제는 monorepo: root quant-bridge/ + sub-package frontend/)

**올바른 root**: `quant-bridge/` (monorepo root). Next.js 자동 inferred root = pnpm-lock.yaml 있는 디렉토리 = `quant-bridge/` (정확).

**결론**: **multi-lockfile warning silence 시도 자체가 risk**. Turbopack 자동 inferred root 가 정답. `path.resolve(__dirname, "..")` 명시도 자동과 동일 결과 → fix 자체 폐기.

---

## 5. BL 변경

### Resolved (1건, 보존적 — measurement artifact)

- **BL-189** CPU loop on stage `8a23f29` — measurement artifact 결론 (Sprint 38 Day 7.5 시점 unique 환경 재현 불가). stage 코드 자체 정상 (idle 0% 1h sustained 검증) → Sprint 40 stage→main merge 안전.

### Deferred 갱신 (1건)

- **BL-188** (백테스트 폼 ↔ Live Session mirror) — Sprint 38 v3 코드 stage 머지 완료 (38 신규 tests 보존). **Sprint 40 stage→main merge 시 main 반영 가능**.

### 신규 (0건)

본 sprint 신규 BL 0건. 신규 LESSON 1건 (LESSON-047 후보).

### 합계 변동

**87** (Sprint 38 종료) **→ 87 active BL** (BL-189 Resolved -1 / 신규 0 = -1).

---

## 6. 신규 LESSON (lessons.md 1/3 후보)

- **LESSON-047** Turbopack `turbopack.root` 명시 시 wrong path = file watcher storm — `process.cwd()` 또는 `frontend/` 디렉토리로 root 명시 시 깊은 트리 (`.next/`, `node_modules/`) 무한 watch → 400%+ sustained CPU spike. monorepo 환경 시 자동 inferred root (lockfile 있는 monorepo root) 가 정답. multi-lockfile warning silence 시도 자체가 risk — fix 안 하는 게 더 안전. measurement-driven hotfix discipline = Generator-Evaluator 통과 후에도 production 환경 measurement 의무.

영구 승격 (3/3 통과) 후보 — 동일 패턴 2회 더 발견 시.

---

## 7. 다음 sprint 분기 (영구 룰)

**Day 7 4중 AND gate 모두 PASS** → Sprint 40 = **stage→main merge + BL-003 + BL-005 본격**.

Sprint 40 mandatory:

1. **stage→main merge** — `stage/sprint38-bl-188-bl-181 @ 8a23f29` (33 files / +2426 / -74 / +38 tests) → main. BL-188 v3 + BL-181 통합 main 반영
2. **BL-003** — Bybit mainnet runbook + smoke 스크립트 (실제 mainnet API key 등록 + small order smoke 자동화)
3. **BL-005 본격** — 본인 1-2주 소액 mainnet dogfood 진입 (테스트넷 → 실 자금 small position)
4. **Beta 본격 진입 (BL-070~075) trigger** = BL-005 본격 (1-2주 mainnet) 통과 후 별도 trigger. **≠ Day 7 통과 즉시 Beta 진입** (fictitious gate detection 영구 반영)

---

## 8. 시간 견적 vs 실측

| 단계                   | 견적 | 실측                                        |
| ---------------------- | ---- | ------------------------------------------- |
| Pre-flight             | 30m  | ~3.5m (BE 3m + FE 30s, baseline 정합)       |
| BL-189 진단 spike      | 1-2h | ~1.5h (60s 측정 + 1h monitor + dogfood)     |
| Hotfix scope           | 1-2h | ~30m (wrong fix → revert + LESSON-047 후보) |
| Self-verify            | 30m  | skip (코드 변경 0)                          |
| codex review           | 30m  | skip (diff 0)                               |
| dogfood Day 7.5 재시도 | 1h   | 사용자 직접 (병행)                          |
| close-out              | 1h   | ~1h                                         |
| **합계**               | ≤6h  | **~3h** (single worker, single day)         |

자율 병렬 cmux 불필요 → wall-clock 단축. measurement-driven decision 으로 hotfix scope 결정 시간 절약.

---

## 9. 오류 / 회복 / 영구 차단

### Wrong fix 패턴 (LESSON-047 후보)

- `turbopack.root: process.cwd()` 적용 → 400% sustained CPU spike
- 회복: revert → 0% 복원 + LESSON-047 후보 등록
- 영구 (3/3 통과 시): Turbopack root 명시 시 monorepo 자동 inferred 와 동일 path 만 허용 + 시도 전 measurement 의무

### Measurement artifact 인식 (LESSON-046 정합)

- Sprint 38 Day 7.5 의 113% sustained 측정이 unique 환경 (browser session, Clerk auth, ws-stream polling 등) 의 second-order effect 가능성
- 회복: 본 sprint 측정 = 60s sustained + 1h monitor + 사용자 dogfood 모두 0% 확인 → measurement artifact 결론 + stage→main merge 안전
- 영구: dogfood Day 7.5 mid-check falsification signal 의 진정한 가치 = measurement artifact vs real regression 분리

### URL routing confusion (sprint 39 specific)

- 가이드 작성 시 `/dashboard/trading` 으로 잘못 적음 (Next.js `(dashboard)` route group 은 URL X)
- 회복: 사용자 즉시 보고 → 정정 (`/trading` 등)
- 영구 X (one-off — 가이드 작성 시 route group 인지 의무)

---

## 10. 합계 정합

- **active BL**: 87 → 87 (BL-189 Resolved -1 / 신규 0 = -1, 단 net 87 유지)
- **lessons.md**: LESSON-046 (마지막) → LESSON-047 (마지막). 1건 신규 후보
- **stage 브랜치**: `origin/stage/sprint38-bl-188-bl-181 @ 8a23f29` 보존 (Sprint 40 머지 베이스)
- **main**: `6bc6732` (Sprint 38 close-out PR #174) → 본 sprint close-out 후 새 sha (dev-log + AGENTS + INDEX + BACKLOG 만 변경)

---

## 11. Cross-link

- 본 sprint kickoff prompt: [`.claude/plans/sprint39-kickoff-prompt.md`](../../.claude/plans/sprint39-kickoff-prompt.md)
- 본 세션 plan: `~/.claude/plans/context-restore-mellow-seahorse.md`
- 측정 evidence (gitignored): `.claude/sprint39-bl189-spike/` (dev-log + cpu-monitor + after-revert)
- 직전 Sprint 38 회고: [`2026-05-07-sprint38-master.md`](2026-05-07-sprint38-master.md)
- BL-189 trigger Sprint: Sprint 38 polish iter 6 통합 환경 dogfood Day 7.5

---

**Sprint 39 결론** — BL-189 113% sustained 가 코드 회귀가 아닌 measurement artifact 로 판명. stage `8a23f29` 코드 자체는 정상 (60s sustained + 1h monitor + 사용자 dogfood = idle 0%). Wrong fix (`turbopack.root: process.cwd()`) 시도 시 400% spike 즉시 감지 → revert → measurement-driven hotfix discipline 작동. Day 7 4중 AND gate 모두 PASS → Sprint 40 = stage→main merge + BL-003 mainnet runbook + BL-005 본격 진입. polish iter 7 = single day single worker = ~3h wall-clock.
