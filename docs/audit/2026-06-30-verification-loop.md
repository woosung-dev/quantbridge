# 2026-06-30 — Verification Loop (문서 레벨 검증 + 아키텍처 감사)

> `ai-rules/.ai/process/methodology-tooled.md` 6-Stage 도구 매핑을 quant-bridge 에 실제 적용한 검증 루프. **코드 로직 변경 0** (문서/설정/스킬 심볼릭만). codex 4-gate 교차검증. 브랜치 `docs/verification-loop-2026-06-30` (3 commit, 푸시/PR 사용자 승인 대기).

## 범위 & 사용자 결정

- **결정 4종:** (1) kairos 스킬 심볼릭 설치 (2) 문서정리 + 아키텍처 감사(코드 0) (3) CONTEXT.md 생성 (4) 감사 대상 = ~~trading~~ → **backtest** (Phase 0 frame change).
- **방법:** 3 Explore 에이전트 사전조사 → grill-with-docs(Stage 0) → 문서 드리프트 수정 → improve-codebase-architecture(Stage 4, Workflow 4-agent + codex challenge) → cadence 배선. 각 단계 §7.3 circular-trust 차단(codex finding 직접 코드 검증 후 반영).

## Phase 0 — 셋업 & frame change

- **툴 갭 해소:** methodology 가 참조하는 mattpocock `/grill-with-docs`·`/improve-codebase-architecture`·`/zoom-out` 이 quant-bridge 미등록(kairos 전용)이었음 → `~/.claude/skills/` symlink 설치 → 즉시 invocable 발효 확인.
- **★ frame change (§7.1/§7.4):** prereq 스파이크에서 trading 이 **이미 3회 deepen**(05-09/05-15/06-26-deepen-2) 소진 + deepen-2 가 "다음=backtest/optimizer" 권고 발견 → 감사 대상 trading→**backtest**(미감사) 재조정. (서브에이전트의 `2026-06-30-trading-deepen-2.md` 경로 오보도 스파이크가 교정 — 실제 `2026-06-26`.)

## Phase 1 — Stage 0 헌법: CONTEXT.md

- 루트 `CONTEXT.md` 신설 — 6 도메인 용어집 + relationships + example dialogue + **flagged ambiguities 6건**. `02_domain/*` + ADR-003/011/013/018/020 + 코드 교차 ground.
- **codex consult gate → 7건 보정**(전부 직접 코드 검증): Track A/M 에 `library` 포함(`ast_classifier:113`) / Degraded Pine·`allow_degraded_pine` 신설(`backtest/service.py:168`) / LiveSignalSession Bybit-demo 한정(`live_session_service.py:102`) / ExchangeName 신설 + registry SSOT / demo 의미 거래소별 상이(Bybit 실엔진 vs OKX sandbox) / Kill Switch 트리거별 scope / Provider dispatch 튜플 relationship.

## Phase 2 — 문서 드리프트 정리 (확정 건만, surgical)

| 파일                                     | 수정                                                                               | 비고                                                            |
| ---------------------------------------- | ---------------------------------------------------------------------------------- | --------------------------------------------------------------- |
| `04_architecture/system-architecture.md` | L82 `vectorbt 실행`→pine_v2 AST / L143 `vectorbt engine`→pine_v2 event-loop        | 진짜 P0 드리프트(무완화)                                        |
| `04_architecture/data-flow.md`           | L59 `vectorbt engine`→pine_v2 인터프리터 / L83 `strategy_python`→`run_backtest_v2` | **서브에이전트 누락 발견**(트랜스파일 함의 제거)                |
| `dev-log/020-trust-layer-ci-design.md`   | L7 "초안"→"확정(Accepted)"                                                         | Stage 2 구현 증거 검증(ci.yml parity + nightly mutation oracle) |
| `02_domain/domain-overview.md`           | §4.1 FK 표에 phantom 테이블 reconcile 노트                                         | FK 그래프 재작성 회피(erd.md SSOT 위임)                         |
| `02_domain/entities.md`                  | ENT-009 `exchange` 도메인→trading 통합(ADR-018) 경로 정정                          | —                                                               |
| `QUANTBRIDGE_PRD.md`                     | **무수정**                                                                         | 헤더 LEGACY 경고 이미 우수(서브에이전트 과대 플래그 확인)       |

## Phase 3 — backtest 1차 deepen (BL 등재만, 코드 0)

ultracode Workflow 4-agent fan-out + 합성 → 후보 6 → **codex challenge**(540k, 실제 파일·테스트 전수 정독).

| 후보                                 | 처분                              | →                          |
| ------------------------------------ | --------------------------------- | -------------------------- |
| C4 sizing-canonical typed seam       | KEEP(최강)                        | **BL-387** (P2 money-path) |
| C2 BacktestMetrics 4-site multi-SSOT | KEEP(강화, codex 4번째 site 발견) | **BL-388** (P2)            |
| C1 finance-math 추출                 | KEEP(codex DOWNGRADE 정정)        | **BL-389** (P3)            |
| C6 exit fill_type 중복 위임          | KEEP                              | **BL-390** (P3)            |
| C5 equity↔PnL reconciliation oracle  | DOWNGRADE                         | **BL-391** (P3 test-first) |
| C3 idempotency dual-lock 통합        | **KILL**(over-engineering)        | **ADR-021**                |

- **★ codex factual 오인 차단:** codex 가 phantom `engine/metrics.py` 존재를 근거로 C1 DOWNGRADE → `ls` 검증 = **부재**, finance-math 10fn 전부 v2_adapter L707-912 → **KEEP 정정**. adversarial finding 도 코드 대조 의무(§7.3).
- STOP 조건 해당 없음(backtest 46 test, refactor-safe). 45 → **50 active BL**.

## Phase 4 — cadence 배선

- `AGENTS.md`(=.claude/CLAUDE.md) 온보딩 첫 step 에 **CONTEXT.md 추가**(4종).
- `.ai/common/global.md §7.5` 에 methodology Stage 0/4 도구 invocable 화 + CONTEXT.md 신설 + improve-codebase-architecture↔deepen-modules 상호보완 노트.

## 검증 증거

- **codex 4-gate:** Phase1 consult(CONTEXT.md 7보정) + Phase3 challenge(6후보 처분) + (Phase2/4 = 본 번들 일관성, 아래 G-gate) — 전 finding 직접 코드 검증.
- **코드 로직 0:** `git diff main --name-only` 에 `backend/src`·`frontend/src` 0건 (3 commit 전부 docs/설정/스킬).
- **드리프트 grep:** `docs/04_architecture/` 잔여 vectorbt-as-engine 표기 0 (지표전용/conformance/migration-history 맥락만 보존).

## Decision Log

| #   | 결정                       | 근거                                           |
| --- | -------------------------- | ---------------------------------------------- |
| D1  | kairos 스킬 심볼릭 설치    | methodology 그대로 invocable, 일회성           |
| D2  | 감사 대상 trading→backtest | trading 3회 소진(frame change), deepen-2 권고  |
| D3  | PRD 무수정                 | 헤더 LEGACY 경고 이미 정확                     |
| D4  | ADR-020 초안→확정          | Stage 2 CI parity + nightly mutation 구현 증거 |
| D5  | C3 KILL + ADR-021          | 의도적 dual-lock layered, 재제안 차단          |
| D6  | C1 KEEP(codex 정정)        | metrics.py 부재 직접 검증                      |
| D7  | FK 표 노트만(재작성 X)     | erd.md SSOT, 오류 위험 회피                    |

## Deferred / 다음

- **다음 deepen 권고:** optimizer 또는 stress_test (Iron Law = 새 session). optimizer = coverage <70% STOP 가능성 선확인.
- **BL-391/C5** = test-first(좁은 equity↔PnL oracle), BL-389 와 묶음 권장.
- **사용자 manual:** 브랜치 `docs/verification-loop-2026-06-30` 푸시/PR 승인 / `.ai/` 마스터 ai-rules repo 미러(LESSON-068 sync) / methodology 스킬은 다음 세션부터 Skill 등록 발효(이번 세션 = 직접 호출).
