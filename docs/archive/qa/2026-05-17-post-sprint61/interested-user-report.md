# Curious 재측정 — Sprint 61 fix-first 효과 검증

**일자**: 2026-05-17 (Sprint 61 PR #288 main @`26b7486` + BL-348/349 hotfix `9103134`)
**환경**: Isolated mode (FE :3100 / BE :8100, Next.js 16 Turbopack)
**페르소나**: Curious — 도구 도입 검토 의사결정자
**깊이**: Standard (~45-60분 cap)
**Pre baseline**: 2026-05-17 1차 Curious **6.5 / 10 Maybe** (BL-317~326 10건)
**측정자**: Multi-Agent QA Curious 2.0 (Playwright/browse only — DevTools/API 직접 호출 금지)

---

## Executive Summary

| 차원                       | Pre (1차)      | Post (2차)              | △        |
| -------------------------- | -------------- | ----------------------- | -------- |
| **Composite Curious 점수** | **6.5** / 10   | **8.0** / 10            | **+1.5** |
| **도입 결정**              | Maybe (조건부) | **Yes (가벼운 조건부)** | ⬆ 회복   |
| **친구 추천도**            | ★★★ / 5        | **★★★★** / 5            | +1       |
| **결제 의사**              | 50% 손실       | ~85% 회복               | ⬆ 회복   |

**Sprint 61 fix 효과 = 5/7 PASS / 1/7 PARTIAL / 1/7 DEFER**.

**그러나 신규 P0 결함 BL-350** 발견 — Optimizer 페이지 첫 진입 시 **Zod validation error JSON 풀텍스트 그대로 노출** (수십 줄). 잠재 고객 시선에서 "broken UI" 인상 결정적. **Sprint 62 즉시 hotfix 권고**.

---

## Sprint 61 fix 효과 — 페르소나 view (Iron table)

| BL                               | 1차 결과                          | 2차 결과 (직접 검증)                             | 회복       | 증거                                                                                               |
| -------------------------------- | --------------------------------- | ------------------------------------------------ | ---------- | -------------------------------------------------------------------------------------------------- |
| **BL-319+348 Clerk redirect**    | accounts.dev FAIL (-3 신뢰)       | **자체 도메인 PASS**                             | ✅         | `/backtests` `/trading` `/strategies` `/optimizer` 4/4 → `localhost:3100/sign-in?redirect_url=...` |
| **BL-328 koKR**                  | 영어 form FAIL                    | **한국어 PASS**                                  | ✅         | "로그인 / 이메일 주소 / 비밀번호 / 계속 / 회원가입 / 비밀번호를 잊으셨나요? / 다른 방법 사용하기"  |
| **BL-321 application name**      | "quant-bridge" slug FAIL          | "**quant-bridge에 로그인**" 여전                 | ⚠️ PARTIAL | `curious-04-signin-koKR.png` 시각 확인. 사용자 dashboard manual 미진행.                            |
| **BL-320 Development mode 배지** | 노출 (P1 신뢰 차단)               | 노출 (defer Sprint 62 production)                | ⏭️ DEFER   | dev instance 정상 표시. production deploy 시점 자동 해소 약속.                                     |
| **BL-322 hero copy**             | "TradingView 전략 업로드하면" GAP | "**Pine Script 코드를 붙여넣으면**" PASS         | ✅         | landing `/` text 직접 확인                                                                         |
| **BL-323 Optimizer 메뉴**        | 사이드바 부재                     | **"최적화" 노출 + click → /optimizer 진입** PASS | ✅         | `curious-06-after-login.png` 사이드바 4 메뉴                                                       |
| **BL-327 KPI tooltip**           | 없음                              | **8개 KPI 한국어 educational tooltip PASS**      | ✅         | "샤프 비율 — 변동성 대비 초과수익. 1 이상 양호..." 등                                              |

**Score**: PASS **5** / PARTIAL **1** / DEFER **1** = 회복 비율 **5/7 = 71%**.

---

## 첫인상 (5초 / 30초 / 1분 룰)

| 차원                 | Pre (1차)                  | Post (2차) | △                                         |
| -------------------- | -------------------------- | ---------- | ----------------------------------------- |
| Landing 5초 인상     | 7 / 10                     | **8** / 10 | +1                                        |
| 30초 가치제안 명료성 | 8 / 10                     | **9** / 10 | +1 ("Pine Script 코드 붙여넣으면" 정직화) |
| 1분 신뢰감           | 5 / 10 (accounts.dev 충격) | **8** / 10 | +3 (자체 도메인 + 한국어 form)            |
| 결제 의향            | 4 / 10                     | **8** / 10 | +4                                        |
| 추천 의향            | 6 / 10                     | **8** / 10 | +2                                        |

---

## 도입 결정 회복

**Pre (1차)**: **Maybe — Clerk dev 도메인 leak 으로 50% 결제 의사 손실**. 조건부 Yes (production Clerk + 한국어 + landing 정직화).

**Post (2차)**: **Yes (가벼운 조건부)**.

- ✅ **결정적 회복 요인**: Clerk redirect 자체 도메인 + koKR 적용으로 신뢰 회복.
- ✅ **landing 정직화**: "Pine Script 코드를 붙여넣으면" — 잠재 고객이 가장 싫어하는 거짓 GAP 제거.
- ✅ **사이드바 Optimizer 노출**: 핵심 기능 가시화로 product depth 인상.
- ✅ **KPI tooltip educational**: 학습 곡선 완화, 진지한 트레이더에게 호의적 신호.
- ⚠️ **잔존 우려 (가벼운 조건)**: (1) Clerk widget header "quant-bridge에 로그인" slug 여전 (5분 dashboard manual). (2) Optimizer 페이지 Zod error 도배 (P0 hotfix).
- 🟡 **Production deploy 완료 시점**: Development mode 배지 사라지면 9 / 10 까지 회복 가능.

**친구 추천도**: ★★★ → **★★★★ / 5** (+1). "베타이긴 한데 한국어 + 정직한 카피 + 자체 도메인 — 다시 보러 갈만함."

---

## 신규 결함 (BL-350~)

### BL-350 P0 [Curious] Optimizer 페이지 진입 시 Zod validation error JSON 풀텍스트 노출

**증거**: `screenshots/curious-07-optimizer-page.png`
**경로**: 로그인 → 사이드바 "최적화" 클릭 → `/optimizer` 진입
**현상**: 페이지 상단에 정상 form 노출되지만, **"최근 실행 목록 로드 실패: [ { "expected": "number", "code": "invalid_type", "path": ["items", 0, "param_space", "bayesian_n_initial_random"], "message": "Invalid input: expected number, received null" }, ... ]"** 형태의 Zod schema validation error JSON 이 **약 20+ row 그대로 본문 텍스트** 로 도배됨.

**root cause 가설** (페르소나 추론, 코드 0 touch):

- Sprint 50/51/52 의 result_jsonb retro-incorrect row (사용자 manual 재실행 안 한 row) + Sprint 53/54/55 grammar tightening (`bayesian_n_initial_random` non-null + `bayesian_acquisition` enum EI/UCB/PI + `population_size` non-null + `n_generations` non-null) 의 합집합 결과.
- FE `/optimizer/runs` listing endpoint 가 Zod parse FAIL → error catch 시 fallback rendering 이 raw error JSON 을 그대로 본문 노출.

**페르소나 시선**: "이거 production 인가? 알파 단계?" — 잠재 고객 신뢰 결정적 손상.
**Severity**: **P0** (도입 결정 차단 가능).
**권고 fix**:

1. Catch 시 raw error JSON 노출 금지 → user-friendly "이전 데이터 schema 불일치로 일부 row 가 표시되지 않습니다" + Sentry log 별도.
2. backend `/optimizer/runs` listing 시 Zod parse FAIL row 자동 skip + `WARN log`. row-level resilience.
3. (사용자 manual) Sprint 50/51/52 의 result_jsonb retro row 재실행 또는 archive.

### BL-351 P2 [Curious] Clerk koKR localization 누락 spot — Apple/Google SSO aria-label

**증거**: `snapshot -i` 결과 `@e6 "Sign in with Apple Apple"` / `@e7 "Sign in with Google Google"` (visible label "Apple" / "Google" 은 한국어 화면에 align, 단 aria-label `"Sign in with Apple"` 영어 잔존).
**현상**: 시각적으로 "Apple / Google" 버튼만 보이므로 user-facing 영향 낮음. screen reader 접근성에서 영어 mix.
**Severity**: **P2** (cosmetic + 접근성 minor).
**권고**: `@clerk/localizations.koKR` 의 `socialButtonsBlockButton: "{{provider}}로 로그인"` 매핑 명시 또는 next-intl override.

### BL-352 P3 [Curious] BL-321 application name dashboard manual 미진행 — Clerk widget header "quant-bridge에 로그인" 잔존

**증거**: `screenshots/curious-04-signin-koKR.png` 시각 확인 — 사이드 panel 헤더가 **"quant-bridge에 로그인"** (slug). 의도 = "**QuantBridge** 에 로그인".
**근본**: Sprint 61 fix 가 "사용자 manual" 로 분류 — Clerk dashboard 의 Application Name 필드를 `quant-bridge` → `QuantBridge` 변경하면 자동 반영. 코드 fix 불가.
**Severity**: **P3** (사용자 manual 1분 작업).
**권고**: 사용자에게 명시적 todo 알림 (TODO.md 또는 Sprint 62 first-step). 미진행 시 production 배포 후에도 잔존.

---

## 시나리오별 cap 시간 + 산출

| 시나리오                        | cap             | 실측      | 산출                              |
| ------------------------------- | --------------- | --------- | --------------------------------- |
| 1. Sprint 61 fix 효과 직접 검증 | 25-30분         | ~22분     | Iron table 7건 + 9 스크린샷       |
| 2. 도입 결정 회복 평가          | 15-20분         | ~10분     | 도입 결정 + 추천 의향 변화        |
| 3. 신규 결함 검출               | 5-10분          | ~8분      | BL-350 P0 + BL-351 P2 + BL-352 P3 |
| **합계**                        | **45-60분 cap** | **~40분** | within budget                     |

---

## Summary

- **Composite Curious 점수**: **8.0 / 10** (Pre 6.5 → +1.5).
- **회복도**: PASS **5** / PARTIAL **1** / DEFER **1** = **71% Sprint 61 fix 목표 달성**.
- **도입 결정**: Maybe → **Yes (가벼운 조건부)** — Clerk dev surface 회복 + landing 정직화로 신뢰 임계 통과.
- **친구 추천도**: ★★★ → ★★★★ (+1).
- **결제 의사**: 50% 손실 → ~85% 회복 (Optimizer Zod error 가 잔존 15% 차감).
- **신규 BL**: 3건 (BL-350 P0 / BL-351 P2 / BL-352 P3).

### Sprint 62 권고

1. **즉시 hotfix**: **BL-350 Optimizer Zod error JSON 노출** (P0, 잠재 고객 결정 차단). 사용자 결정 부담 = ★★★★★ Yes.
2. **사용자 1분 manual**: **BL-352 Clerk dashboard Application Name** `quant-bridge` → `QuantBridge`. 도입 완료 후 production deploy 시점 의무.
3. **defer Sprint 63+**: BL-320 Development mode 배지 (production deploy 시 자동 해소) + BL-351 SSO aria-label (P2 cosmetic).
4. **현재 상태로 Beta 본격 진입 가능 여부**: ⚠️ **BL-350 fix 후 진입 권고**. Optimizer 가 marketing 의 핵심 차별점 (Grid / Bayesian / Genetic 3종) 인데 첫 진입 broken 인상 = 결정적 차단.

**최종 verdict**: Sprint 61 fix 는 **본질적 신뢰 회복에 성공** (Clerk + landing + sidebar + tooltip). 그러나 새로 노출된 Optimizer Zod error 가 회복 효과를 부분 상쇄. **BL-350 hotfix 후 Composite 9.0 / 10 도달 가능**.

---

_Multi-Agent QA Curious 2.0 — Sprint 61 fix-first 효과 재측정 (Standard depth, 2026-05-17)_
