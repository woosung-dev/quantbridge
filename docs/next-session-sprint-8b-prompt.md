# 다음 세션 시작 프롬프트 — Sprint 8b Option A

> **작성일:** 2026-04-18 (Sprint 8a Tier-0 완료 시점)
> **용도:** 새 Claude Code 세션 시작 시 첫 메시지로 복사·붙여넣기
> **목적:** Sprint 8b 초입 (Tier-1 가상 strategy 래퍼 + Tier-0 렌더링 scope A) 즉시 진입

---

## 🚀 프롬프트 (아래 코드블록 전체 복사)

```
Sprint 8a Tier-0 완료 상태 (PR #20 merged `08c6388`, 2026-04-18).
**Sprint 8b 초입 — Option A 진행해줘.** ADR-011 로드맵의 다음 블록.

## 이 세션의 위치
- 엔진(pynescript) + 아키텍처(ADR-011 3-Track) = Phase -1에서 이미 확정
- Tier 0~5 로드맵 내 Sprint 8a(Tier 0 부분 + Tier 3) 완료 → **Sprint 8b (Tier 1 + Tier 0 렌더링 + Tier 3 확장)** 진입

## 목표 2가지 (병렬 가능, 독립적)

### 🎯 1. Tier-1 가상 strategy 래퍼 자동 생성 (ADR-011 §2.1.4, 차별화 핵심)
`indicator() + alert()` 스크립트를 자동 `strategy()` 실행 경로로 변환.
- alert_hook.collect_alerts() 결과 → strategy.entry/close 호출 매핑
- signal 기반 연결: long_entry → strategy.entry("L", long), short_entry → ..., long_exit → strategy.close("L") 등
- discrepancy=True alert은 경고 기록 후 condition_signal 우선 (v1 정책)
- **성공 기준:** i1_utbot.pine 실행 시 2개 alertcondition(UT Long/Short)이 자동 매매 시뮬레이션으로 변환되어 거래 시퀀스 생성

### 🏗 2. Tier-0 렌더링 scope A (box/label/line/table 좌표 getter)
ADR-011 §2.0.4 "범위 A" 엄수 — 좌표 저장 + getter만, 실제 차트 렌더링은 NOP.
- box.new / get_top / get_bottom / delete / set_right
- line.new / get_price / delete / set_x1 · y1 등
- label.new / set_x · set_y / get_x / delete
- table.new / cell / cell_set_bgcolor (메모리 stub)
- **성공 기준:** i2_luxalgo.pine 실행 시 line.get_price() 좌표 재참조로 entry 조건 판단 작동 + 거래 시퀀스 생성

### 최종 목표
6 corpus 실행 매트릭스 **2/6 → 4/6** (i1_utbot + i2_luxalgo 추가)

## 엄수 제약
- **pine_v2/ 모듈 기반.** 기존 pine/ 모듈은 touch 0 (dogfood 복구 경로 보호)
- **H1 MVP scope 준수** (#19 PR) — trail_points / qty_percent / pyramiding / strategy.entry(limit=) 여전히 H2+ 이연
- **pynescript LGPL 격리** — import 6 파일 경계 유지 (parser_adapter / ast_metrics / ast_classifier / alert_hook / ast_extractor / interpreter)
- **ruff/mypy clean** + 기존 526 regression green 유지

## 방법론 — superpowers
1. **writing-plans 스킬로 plan 먼저 작성** (`docs/superpowers/plans/YYYY-MM-DD-sprint-8b-tier1-rendering.md`)
   - Tier-1 가상 strategy 래퍼 task breakdown
   - Tier-0 렌더링 scope A task breakdown
   - 병렬 가능 항목 표시
2. **ExitPlanMode로 사용자 승인** 받기
3. **executing-plans 스킬로 task-by-task 진행** — TDD (test 먼저 → 구현 → verification)
4. 각 task 완료마다 commit (체크포인트)

## 선택지 제시 시 **별점 추천도 필수** (메모리 규칙 참조)
`| 추천도 | 옵션 | 이유 |` 형식 테이블.

## 참조
- 메모리: Sprint 8a Tier-0 완료 (project_sprint8a_tier0_complete.md) — 8 레이어 Foundation 상세
- 세션 HTML 보고서: `docs/reports/session-2026-04-18-sprint-8a-tier0.html` (1111 lines)
- 최종 보고서: `docs/dev-log/012-sprint-8a-tier0-final-report.md`
- ADR-011: `docs/dev-log/011-pine-execution-strategy-v4.md` (+ §13 Phase -1 amendment)
- 아키텍처: `docs/04_architecture/pine-execution-architecture.md`

## 시작 액션
1. `git pull origin main` + `git log --oneline -3` 확인
2. writing-plans 스킬 invoke → plan file 작성
3. 사용자에게 plan 승인 요청 (ExitPlanMode)
4. 승인 후 executing-plans로 진입
```

---

## 📌 사용법

1. 새 Claude Code 세션 시작
2. 위 코드블록 전체 복사 → 첫 메시지로 붙여넣기
3. Claude가 자동으로: `git pull` → plan file 작성 → 승인 요청 → 실행

## 🔗 관련 파일
- 이 파일: `docs/next-session-sprint-8b-prompt.md`
- docs/TODO.md의 "Next Actions" 섹션에도 이 파일 링크 추가됨
