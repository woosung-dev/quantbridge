# Deferred Refactoring Backlog

> Sprint 59 PR-D 트리아주 결과 — trigger 미도래지만 의도적 부활 가능성 보존. 본 BL 들은 명확한 외부 조건 (사용자 의지 / 사업 단계) 충족 시 main BACKLOG 로 row 이동.
>
> archived = 의도적 폐기 또는 stale. deferred = "조건 충족 시 의도적 부활". 부활 trigger 명시 의무.
>
> **Sprint 59 deferred 일자:** 2026-05-13.

## Beta 본격 진입 milestone (BL-070~075)

> **Trigger:** BL-005 self-assessment ≥ 7/10 통과 + 본인 의지 second gate (Sprint 47 close-out 결정). 6-8주마다 재평가.
> **Est:** 4~8h + DNS 전파 24h. A·B·C 상호 의존, 개별 진행 시 재작업 2~3배 → 번들 처리 필수.
> **상세 sub-task:** TODO.md L748~801 보존.

| ID     | 제목                                                                  | Sub-task  | Est                                | 출처                              |
| ------ | --------------------------------------------------------------------- | --------- | ---------------------------------- | --------------------------------- |
| BL-070 | A. 도메인 + DNS + (옵션) Cloudflare                                   | A1~A3 (3) | 1-2h + 24h DNS                     | TODO.md L750-755                  |
| BL-071 | B. Backend 프로덕션 배포                                              | B1~B9 (9) | 2~4h                               | TODO.md L756-783                  |
| BL-072 | C. Resend 이메일 + Waitlist 활성화                                    | C1~C6 (6) | 1-2h + 24h verify                  | TODO.md L784-801                  |
| BL-073 | Twitter/X #buildinpublic 캠페인 시작                                  | —         | S (사용자 수동)                    | BL-070~072 완료 후                |
| BL-074 | Beta 인터뷰 3명 × 3회 (narrowest wedge 60% 검증)                      | —         | L (사용자 수동, 9 interview slots) | BL-073 후 + 5~10명 onboarding 후  |
| BL-075 | H2 진입 게이트 설계 (`/office-hours` Q4 + MC / Walk-Forward 우선순위) | —         | M (3-5h)                           | BL-005 self-assessment ≥7/10 직후 |

## 본인 dogfood (BL-005)

| ID     | 제목                           | Trigger                                                              | Est                       | 출처         |
| ------ | ------------------------------ | -------------------------------------------------------------------- | ------------------------- | ------------ |
| BL-005 | 본인 실자본 1~2주 dogfood 운영 | BL-001~004 모두 완료 + self-assessment ≥7/10 + 본인 의지 second gate | L (≥14 days, 사용자 수동) | TODO.md L652 |

## H1 → H2 prerequisite

| ID     | 제목                                                           | Trigger                   | Est      | 출처                                           |
| ------ | -------------------------------------------------------------- | ------------------------- | -------- | ---------------------------------------------- |
| BL-145 | EffectiveLeverageEvaluator (Cross Margin position aggregation) | Sprint 30+ Phase 2 prereq | M (3-4h) | Sprint 28 Slice 4 T3 deferred (BL-004 sibling) |

## 부활 정책

- 본 파일의 BL 은 trigger 명시. trigger 도래 시 메인 세션에서 row 를 [`../REFACTORING-BACKLOG.md`](../REFACTORING-BACKLOG.md) main table 로 이동 + status `🟡 In progress (Sprint NN)` 마킹.
- 6-8주마다 본 파일 재평가 (사용자 의지 second gate). 의지 X 명시 시 그대로 보존.
- grep 가능: `grep -r "BL-070" docs/refactoring-backlog/` 또는 `grep BL-005 docs/`.
