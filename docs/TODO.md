# QuantBridge — TODO

> **Last Updated:** 2026-05-13 (Sprint 59 close-out — 5 PR all merged)
> **Active Sprint:** Sprint 59 완료 — Sprint 60 분기 결정 대기 (Day 7 인터뷰 2026-05-16)
> **Active Branch:** main (close-out PR 머지 후 — PR-E #277 + 본 close-out PR)
> **Sprint type:** Type B (refactor) + Type D (docs / meta cleanup)
> **office-hours 진행:** N (Sprint 59 종료, 6-8주 재평가 cycle 의무)
> **Next Trigger:** dogfood Day 7 인터뷰 (2026-05-16) 결과 + 본인 의지 second gate → Sprint 60 분기 결정 (4-AND gate)

> 사람과 AI 가 공동 관리하는 활성 작업 추적 파일.
> 차단 항목은 `[blocked]` 표시 / 질문은 §Questions / 활성 BL 상세는 [`REFACTORING-BACKLOG.md`](./REFACTORING-BACKLOG.md) / sprint 회고는 [`dev-log/INDEX.md`](./dev-log/INDEX.md).

---

## 활성 sprint 상태

### Sprint 59 (완료, 2026-05-13)

- **PR 묶음 (5 PR squash merge):** #273 (`_worker_engine` SSOT, -163L) + #274 (Pine v1 demolition, -4838L) + #275 (BACKLOG 압축 1028→587L) + #276 (158 BL → 13 Active 트리아주) + #277 (backtest-form 5-split, 866→232L)
- **검증:** BE 회귀 0 (pine_v2 537 PASS / tasks 146 PASS / engine 138 PASS) + FE 회귀 0 (vitest 680 PASS) + ruff/mypy/tsc/lint clean
- **신규 BL:** 0 / Resolved (PR-D 5-rule triage): 158 BL → **13 Active + 8 Deferred + 137 Archived**
- **누적 net deletion:** ~6,000+ lines (메타 노이즈 + dead code + locality 정리)
- **상세:** [`docs/dev-log/2026-05-13-sprint59-close.md`](./dev-log/2026-05-13-sprint59-close.md)
- **13 active BL** (상세 = [`REFACTORING-BACKLOG.md`](./REFACTORING-BACKLOG.md) + [`refactoring-backlog/_archived.md`](./refactoring-backlog/_archived.md) + [`refactoring-backlog/_deferred.md`](./refactoring-backlog/_deferred.md))

### 직전 sprint: Sprint 58 (BL-241/242/243 Pine TA 확장)

- 상세: [`docs/dev-log/2026-05-11-sprint58-close.md`](./dev-log/2026-05-11-sprint58-close.md)

---

## 다음 분기 (Sprint 60)

dogfood Day 7 인터뷰 (2026-05-16, 사용자 manual) 결과 + 본인 의지 second gate 에 따라 4-way 분기:

- **(a)** NPS ≥7 + critical bug 0 + self-assess ≥7 + 본인 의지 → Sprint 60 = **Beta 본격 진입** (BL-070~075 도메인+DNS / BE 프로덕션 배포 / Resend / 캠페인 / 인터뷰 / H2 게이트)
- **(b)** dogfood mixed / no urgent bug → Sprint 60 = 잔여 active BL (BL-003 mainnet runbook / BL-014 partial fill / BL-022 golden / BL-235 N-dim viz / BL-236 objective whitelist)
- **(c)** mainnet trigger 도래 → Sprint 60 = BL-003 / BL-005 mainnet 본격
- **(d)** trust-breaking bug 노출 → Sprint 60 = 그 fix 1 sprint 우선, 후속은 Sprint 61+ 이연

### Sprint 60 첫 step 의무

- Day 7 카톡 인터뷰 결과 정리 (`sprint42-feedback.md` Day 7 row) + Sprint 59 evidence 검토 ([`dev-log/2026-05-13-sprint59-close.md`](./dev-log/2026-05-13-sprint59-close.md))
- 4-AND gate 검증: (a) self-assess ≥7 / (b) BL-178 production BH 정상 / (c) BL-180 hand oracle 8 test GREEN / (d) new P0=0 AND unresolved Sprint-59-caused P1=0
- **Sprint 50/51/52 `result_jsonb` retro-incorrect 안내 유지** — BL-222 fix 이전 CA / PS 결과는 사용자 manual 재실행 권고
- PR-E (5-split) 의 **5분 dev smoke** (LESSON-004 PR 규약, 사용자 manual) — 누락 시 회귀 의무 검증

---

## 상시 활성 컨텍스트 (영구 기록 외 발견 패턴)

- `dogfood Day N` 노트는 sprint 묶음과 별개로 `dev-log/` 에 단독 파일로 보관
- BL-005 (본인 1-2 주 dogfood) trigger 도래 후 H1→H2 gate (self-assessment ≥7) 가 재평가 기준
- `make up-isolated` (3100 / 8100 / 5433 / 6380) 가 다른 웹앱 병렬 시 디폴트
- **Pine SSOT 4 invariant audit** (`tests/strategy/pine_v2/test_ssot_invariants.py`) — supported list 추가 시 4 collection 동시 갱신 의무 자동 검증
- **Surface Trust sub-pillar (Sprint 30 ADR-019)** — Backend Reliability + Risk Management + Security + Surface Trust (가정박스 / 차트 / 24 metric / 거래목록). 측정: PRD 24 metric BE+FE 100% / config 5 가정 FE 100% / lightweight-charts 정합 / dogfood self-assess Day 3 ≥7
- **자율 병렬 sprint Agent worktree 패턴** — 충돌 회피 신규 파일 only / 통합 작업은 메인 세션 후처리 / gh CLI auto-merge --squash / `--no-verify` 1 회 우회 사용자 명시 승인 패턴

---

## 활성 BL 요약 (상세는 [`REFACTORING-BACKLOG.md`](./REFACTORING-BACKLOG.md))

> 본 sprint kickoff 시 백로그 review 의무. 자연어 표현은 컨텍스트 복원성 위해 sprint 회고 안에 유지하되, 새 항목 추가 시 BL ID 부여 후 등록.

핵심 cross-link (Sprint 59 PR-D 트리아주 후):

- **P0 active**: [BL-003](./REFACTORING-BACKLOG.md#bl-003) Bybit mainnet runbook
- **P1 active**: [BL-014](./REFACTORING-BACKLOG.md#bl-014) partial fill / [BL-015](./REFACTORING-BACKLOG.md#bl-015) OKX WS / [BL-022](./REFACTORING-BACKLOG.md#bl-022) golden 재생성 / [BL-023](./REFACTORING-BACKLOG.md#bl-023) KIND-B/C / [BL-024](./REFACTORING-BACKLOG.md#bl-024) real_broker E2E / [BL-025](./REFACTORING-BACKLOG.md#bl-025) autonomous-parallel patch / [BL-026](./REFACTORING-BACKLOG.md#bl-026) mutation fixture
- **P2 active**: [BL-186](./REFACTORING-BACKLOG.md#bl-186) full leverage model / [BL-190](./REFACTORING-BACKLOG.md#bl-190) PDF export / [BL-195](./REFACTORING-BACKLOG.md#bl-195) form animation / [BL-235](./REFACTORING-BACKLOG.md#bl-235) N-dim viz / [BL-236](./REFACTORING-BACKLOG.md#bl-236) objective whitelist
- **Deferred milestone** ([`_deferred.md`](./refactoring-backlog/_deferred.md)): BL-005 본인 dogfood / BL-070~075 Beta 본격 진입 / BL-145 EffectiveLeverageEvaluator
- **Archived 138건** ([`_archived.md`](./refactoring-backlog/_archived.md)): 모든 ✅ Resolved + Sprint 16~30 stale follow-up + P3 전부
- **정합성 audit:** [`04_architecture/architecture-conformance.md`](./04_architecture/architecture-conformance.md) — 15 항목 영구 체크리스트

---

## Test Skip / xfail 추적표 (Sprint 15-C 신설, 2026-04-28)

> 18 skip + 0 fail (Sprint 14 기준). "이 skip 이 왜 존재 + 언제 해소" 명시. 신규 skip 추가 시 본 표 업데이트 의무.

| #    | 위치                                                                                   | 종류                     | 사유                                                                                 | 해소 트리거                                                                  |
| ---- | -------------------------------------------------------------------------------------- | ------------------------ | ------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------- |
| 1    | `tests/backtest/engine/test_golden_backtest.py:19`                                     | `pytestmark.skip`        | legacy golden expectations — pine_v2 `strategy.exit` 지원 + expected 재생성 필요     | pine_v2 strategy.exit 도입 후 golden 재생성                                  |
| 2    | `tests/real_broker/test_webhook_to_filled_e2e.py:31`                                   | `pytestmark.real_broker` | nightly E2E (Bybit Demo 실 호출). `--run-real-broker` flag + `BYBIT_DEMO_*` env 필요 | 매일 nightly cron (`.github/workflows/nightly-real-broker.yml`)              |
| 3    | `tests/real_broker/conftest.py:43`                                                     | `skip_marker`            | 위 #2 의 conftest fallback (env 미주입 시 collection-time skip)                      | 동일                                                                         |
| 4-7  | `tests/strategy/pine_v2/test_trust_layer_parity.py:251/334/357/421`                    | `skipif`                 | Trust Layer fixture (`regen_trust_layer_baseline.py` / 8 mutation set) 미생성        | Path β Stage 2c 2 차 mutation 8/8 도달 (2026-04-23 완료, 회귀로 활성화 검토) |
| 8    | `tests/strategy/pine_v2/test_trust_layer_parity.py:405`                                | `pytest.mark.skip`       | Mutation oracle 은 nightly workflow 또는 `--run-mutations` 수동 (CI default 차단)    | nightly mutation workflow 또는 manual gate                                   |
| 9-15 | `tests/strategy/pine_v2/test_mutation_oracle.py:147/179/212/253/296/328/376/414` (8건) | `skipif`                 | mutation fixture 미생성 시 collection skip                                           | Stage 2c 2 차 fixture 활성화 후 사용 가능 (현재 안전 fallback)               |
| 16   | `tests/strategy/pine_v2/test_mutation_oracle.py:213`                                   | `xfail(strict=False)`    | KIND=B/C 가 NaN-tolerance 한계로 mutation 구분 못 함. strict=False 로 명시           | KIND-B/C 분류 정밀도 향상 (Trust Layer v2 검토)                              |
| 17   | `tests/conftest.py:93`                                                                 | `skip_mutation` autouse  | 모든 `@pytest.mark.mutation` 자동 skip (CI default), `--run-mutations` 시 활성화     | pytest collection-time guard (영구)                                          |
| 18   | (집계 차이)                                                                            | xfail/skip 누적          | pytest collection-time 자동 분기 (real_broker / mutation 기본 차단)                  | 표 업데이트 의무                                                             |

**카테고리:**

- 영구 (정상): #2, #3, #8, #17 — opt-in flag 가 정확한 안전장치
- fixture 활성화 후 자동 해소: #4-7, #9-15 — Path β Stage 2c 2 차 후 회귀 검토 → [BL-026](./REFACTORING-BACKLOG.md#bl-026)
- dette: #1 (golden 재생성) → [BL-022](./REFACTORING-BACKLOG.md#bl-022) / #16 (KIND-B/C 정밀도) → [BL-023](./REFACTORING-BACKLOG.md#bl-023)

**관리 규약:** 신규 skip 추가 시 본 표 동일 PR 업데이트 / 매 sprint 끝 fixture 카테고리 재검토.

---

## Blocked

(현재 없음 — Sprint 58 종료)

---

## Questions

(없음 — 활성 질문 시 추가)

---

## Next Actions

- Sprint 59 진입 = Day 7 인터뷰 2026-05-16 결과 분석 후 결정
- Tier 1 refactor audit (현재 진행 중) → 사용자 승인 후 commit + PR
