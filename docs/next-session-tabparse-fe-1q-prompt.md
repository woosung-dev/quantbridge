# 다음 세션 시작 프롬프트 — TabParse FE 1질문 UX (Sprint FE-01)

> **용도:** Sprint 8c 완료 직후, FE 따라잡기 차 독립 세션에서 TabParse UX 개선.
> 복붙해서 새 Claude 세션의 첫 메시지로 사용.

---

## 복붙용 프롬프트

```
Sprint 8c 완료 상태 (PR #22 merge 가정, main 기준).
  이번 세션은 **TabParse FE 1질문 UX** (Sprint FE-01, 독립 스코프).

  ## 이 세션의 위치
  - BE 현황: Sprint 7b에서 ParsePreviewResponse.functions_used 포함
  BE 확장 완료. Pine 파싱 결과(에러/경고/감지 함수 목록/메타)는 이미 API로 노출 중.
  - Sprint 7c에서 Strategy CRUD UI 완성 (3 라우트 + Monaco Pine Monarch +
  shadcn/ui 12개 + sonner + Delete 409 archive fallback + design-review 7-pass
  5/10→9/10).
  - Sprint 7b에서 Edit 페이지 TabCode 자동 파싱 + TabParse 4-섹션
  (에러→경고→감지→메타) 기본 UX 완성 (528 BE / 9 FE vitest green).
  - 남은 공백: TabParse가 정적 4-섹션 표시라 **사용자가 내용을 "이해"하고
  confirm하는 대화 흐름이 없음**. 이게 dogfood 시점의 가장 큰 마찰.

  ## 이번 세션 목표 — "1질문 UX"
  파싱 결과를 인터랙티브 대화형 모달로 표시해서, 사용자가:
  1. 감지된 함수 하나씩 자연어 해설로 확인 ("ta.rsi(close, 14) — 14일 RSI 지표
  사용. close 가격으로 모멘텀 측정")
  2. 경고/에러를 "왜 경고냐? 무엇을 해야 하나?" 원인+조치까지 한눈에
  3. 마지막에 "이 전략을 저장할까요?" confirm 한 질문으로 끝내기

  **성공 기준:**
  - Edit 페이지에서 TabParse 탭 클릭 → 정적 4-섹션 대신 대화형 모달(shadcn
  Dialog) 열림
  - 감지된 각 stdlib 함수마다 한 줄 자연어 설명 + "다음" 버튼으로 순차 이동
  - 에러/경고는 "조치 제안" 텍스트 포함 ("parse error line 12: `=>` 문법 필요
  — v4 스크립트는 그대로 두고 v5 호환을 원하면 ta.* prefix 추가")
  - 마지막 화면: "이 전략을 그대로 저장 / 수정하러 돌아가기" 2-버튼
  - FE vitest 유지 (9 green + 신규 3~5건)

  ## 엄수 제약
  - frontend/ 내부만 수정. BE touch 0 (이미 ParsePreviewResponse 완비)
  - shadcn/ui Dialog + 기존 파싱 엔드포인트 재사용 (새 API 금지)
  - 자연어 해설은 하드코딩 테이블 우선 (LLM 호출 금지 — 이번 세션 범위 밖)
  - design-review 1-pass 포함 (gstack /plan-design-review)

  ## 방법론 — superpowers B+ (writing-plans → plan-design-review → executing-plans)

  1. writing-plans (superpowers) →
  docs/superpowers/plans/YYYY-MM-DD-sprint-fe-01-tabparse-1q.md
    - 모달 상태 머신 (step 1..N + final confirm)
    - 자연어 해설 테이블 (stdlib 함수명 → 한 줄 설명)
    - 에러/경고 조치 제안 매핑 테이블
  2. plan-design-review (gstack) — UX 1-pass
    - 대화 흐름의 dead-end / 누락 상태 점검
    - shadcn Dialog 권장 패턴 (mobile responsive 포함)
    - 감지된 함수가 0개/30개일 때 UX (빈 상태 / 긴 리스트)
  3. ExitPlanMode로 사용자 승인
  4. executing-plans (superpowers) — TDD task-by-task (vitest 기반)
  5. 각 task 완료마다 commit
  6. /design-review (gstack) 실행 시점 live 방문 + screenshot 비교

  ## 브랜치 전략
  - 새 브랜치 feat/sprint-fe-01-tabparse-1q (main에서 분기)
  - Sprint 8c는 PR #22로 독립. 이 세션과 충돌 없음.

  ## 선택지 제시 시 별점 추천도 필수

  ## 참조
  - 메모리: project_sprint7c_complete (FE 패턴), feedback_dogfood_first_indie
  - Sprint 7b plan: docs/superpowers/plans/2026-04-17-sprint7b-edit-parse-ux.md
  - Sprint 7c plan: docs/superpowers/plans/2026-04-17-sprint7c-strategy-ui.md

  ## 시작 액션
  1. git checkout main && git pull origin main
  2. git checkout -b feat/sprint-fe-01-tabparse-1q
  3. writing-plans 스킬 invoke → plan file 작성
  4. plan-design-review 스킬 invoke → UX 1-pass 검토 + plan 반영
  5. ExitPlanMode로 승인 → executing-plans 진입
```

---

## 대안 분기 (첫 plan 시점에 재논의 가능)

- **A. 현재 방향 (TabParse 1질문 UX)** ★★★★★ — dogfood-first, FE 따라잡기 명분
- **B. 전체 FE 리프레시** (네비/Dashboard 포함) ★★★☆☆ — scope 넓음, 세션 여러 개 필요
- **C. LLM 해설 도입** (Claude API로 동적 설명) ★★★★☆ — 품질 향상 크지만 이번 세션 범위 밖 권장 (후속 sprint)

---

## 이번 세션 이후 대기 중인 후보

1. **Sprint 7d** — OKX + Trading Sessions (H1 내)
2. **Sprint 8d (pine_v2 H2)** — local history ring + valuewhen cap + user function 호출 사이트 stdlib state isolation
3. **LLM 해설 도입** (위 대안 C) — TabParse 1질문 UX가 깔린 뒤 자연스러운 확장
