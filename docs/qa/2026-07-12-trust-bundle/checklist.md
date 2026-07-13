# A+B+C Trust 번들 — Checklist

## Phase 0 — Preflight

- [x] PR #425 머지 확인 (main @9398a36)
- [x] baseline pytest 815 passed 실측
- [x] stage/trust-bundle + feat 브랜치 셋업
- [x] Task B 엔진-diff-0 사전확정

## PR-1 (A) — BL-405 (재분류: not-a-bug, 엔진 무변경)

- [x] TV 시멘틱 리서치 (Workflow, 인용) → **전제 반증 발견**
- [x] 코퍼스 영향 조사 (Workflow) → 골든 관측 무영향 확인
- [x] 사용자 결정: BL-405 폐기 + TV정합 회귀테스트
- [x] 회귀 테스트 `test_na_bool_tv_parity.py` (13건) 작성 + 그린
- [x] 부수 edge(bool[n] 범위밖) 발견 → 관측등가 잠금 + BL-409(b) 등재
- [x] 주석 정정 (interpreter `_eval_compare` + stdlib crossover 3종)
- [x] 백로그 BL-405 CLOSED 재분류 + BL-409 등재
- [x] report.md §4.2 erratum
- [ ] 게이트: 전체 pine_v2 스위트 그린 + trust-layer 골든/parity 바이트 동일
- [ ] 커밋 + push + PR 본문(보고서급) → CI green 후 stage 머지

## PR-2 (B) — 사이징 정규화 리런

- [ ] `--normalized` 하니스 (config-only, 엔진 diff 0)
- [ ] Pine>form 우선순위 스크립트별 명시
- [ ] 8종 × {1h,4h} × {2024,recent} 리런 (최종 엔진)
- [ ] 정규화 전/후 비교표 + 국면 민감도 + 데모후보 판정
- [ ] (선택) WFO/stress 1건
- [ ] 커밋 + PR

## PR-3 (C) — FE 신뢰/폴리시

- [ ] BL-402 4사이트 SelectWithDisplayName
- [ ] BL-408 폴리시 6건
- [ ] BL-407 낙폭 축 눈금
- [ ] tsc + lint + unit 그린
- [ ] Playwright 실 UI (이름표시/다크·라이트/console error 0)
- [ ] 커밋 + PR

## 최종

- [ ] 3 PR 링크 + before/after 표 + 오라클 결과 + 리스크 요약
