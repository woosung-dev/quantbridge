# Phase C 라이브 QA 보고서 (audit 2026-05-30 deferred)

> **일자**: 2026-05-30
> **범위**: audit `2026-05-30-full-inspection.md` Phase C (MCP Playwright 라이브) 의 deferred 실행 + S5/S6/S7 (#315/#316/#318) 머지 후 라이브 재검증
> **환경**: FE `:3100` + BE `:8100` (격리 stack, PG `:5433` / Redis `:6380` / Celery worker 0)
> **결과**: ✅ 8 페이지 검증 통과 + 🚨 **1 신규 P1 발견 + hotfix (#319) 머지 완료**
> **머지 후 main**: `7c07cbe` (PR #315~#319 누적 5건)

---

## 1. 환경 & 도구

| 항목     | 값                                                                           |
| -------- | ---------------------------------------------------------------------------- |
| Frontend | Next.js dev (`make fe-isolated`) `:3100`                                     |
| Backend  | uvicorn (`make be-isolated`) `:8100` — healthz `db ok / redis ok / celery 0` |
| Database | TimescaleDB `:5433` (docker isolated)                                        |
| Redis    | `:6380` (docker isolated)                                                    |
| Browser  | Playwright MCP (Chromium)                                                    |
| Auth     | Clerk dev key (test 계정 `qa_phasec+clerk_test@example.com` / 코드 `424242`) |
| 시점     | main `18d482e` (S5~S7 머지 직후)                                             |

**참고**: Celery worker 0 = backtest/optimizer 실제 실행 불가하나 UI navigation + form UX 검증은 가능.

---

## 2. Coverage 매트릭스

| #   | 페이지 / 플로우                                     | 결과    | 비고                                                                |
| --- | --------------------------------------------------- | ------- | ------------------------------------------------------------------- |
| 1   | `/` landing (desktop 1280)                          | ✅      | hero · 핵심 기능 · 가격 · FAQ 정상                                  |
| 2   | `/` landing (mobile 375)                            | ✅      | 단일 column reflow, no horizontal overflow                          |
| 3   | `/optimizer` (unauth) → `/sign-in?redirect_url=...` | ✅      | proxy.ts middleware 정상                                            |
| 4   | `/sign-in` Clerk widget                             | ✅      | "Development mode" badge (BL-320 production 시 자동 해소)           |
| 5   | `/sign-up` → email verify → `/strategies`           | ✅      | Clerk test 코드 `424242` 정상                                       |
| 6   | `/strategies` empty state                           | ✅      | "첫 전략을 만들어보세요" CTA + 필터 toolbar                         |
| 7   | `/trading` 4 KPI cards + tabs + 거래소 계정         | ✅      | KPI 0/0/정상/0 + "API Key 미등록"                                   |
| 8   | **/optimizer S7-B picker**                          | ✅      | "완료된 백테스트 없음" placeholder 정확 표시 (이전: raw UUID input) |
| 9   | **/trading 계정 추가 dialog S7-A**                  | 🚨 → ✅ | OKX passphrase 검증 silent bypass → hotfix #319 → inline 표시       |
| 10  | `/waitlist`, `/privacy`, `/terms`, `/disclaimer`    | ✅      | 공개 페이지 정상                                                    |

---

## 3. ★ 신규 발견 P1 — S7-A regression (Phase C 핵심 가치)

### 증상

- **재현 경로**: `/trading` → "계정 추가" → 거래소 `OKX` 선택 → API Key/Secret 입력 → passphrase 비운 채 "등록" click.
- **이전 거동** (S7 PR #318 머지 직후): console 에 `ZodError unhandled raise` ("OKX 계정은 Passphrase 가 필수입니다") + **FormMessage 미표시** = 사용자 무피드백 (S7-A schema fix 의 silent bypass).
- **fix 후 거동** (#319 머지): Passphrase 라벨 빨간색 + input border 빨간색 + 아래 "OKX 계정은 Passphrase 가 필수입니다" 빨간 inline alert 표시.

### Evidence

- `11-s7a-okx-passphrase-missing.png` — fix 전 (no inline error, dialog 그대로)
- `12-s7a-hotfix-validated.png` — fix 후 (빨간 FormMessage 정상 표시)

### 근본 원인

`register-exchange-account-dialog.tsx` 가 평범한 `zodResolver` (`@hookform/resolvers/zod@3.10.0`) 사용 → Zod v4 의 superRefine custom issue (`{ code: "custom", path: [...] }`) 를 RHF `errors` 로 매핑 못함 → ZodError 가 caller 까지 throw 되어 unhandled.

`test-order-dialog.tsx` 는 이미 inline custom `zodV4Resolver` 로 우회 — register-exchange-account-dialog 만 패턴 미적용.

### Fix (PR #319, commit `7c07cbe`)

1. `frontend/src/lib/zod-v4-resolver.ts` 신규 — 공유 `zodV4Resolver` helper (test-order-dialog 의 inline 버전 추출).
2. `register-exchange-account-dialog.tsx`: `zodResolver` → `zodV4Resolver` 교체.
3. 테스트: 실패한 jsdom 통합 case 제거 (Base UI Select onValueChange jsdom 미동작 한계). schema unit test 4건 + Playwright 라이브 evidence 로 검증 충분.

### 왜 unit test 가 못 잡았는가

- `superRefine` 자체는 schema-level test (`RegisterAccountRequestSchema.safeParse`) 에서 정상 작동 (issue 가 반환됨) → 4건 test PASS.
- 그러나 _dialog → form → resolver → RHF errors → FormMessage_ 통합 wiring 은 jsdom 에서 검증 불가 (Base UI Select `onValueChange` 가 jsdom 환경에서 호출 안 됨 → OKX 선택 자체가 안 됨).
- **결론**: schema unit test 가 PASS 여도 실제 UI 표시는 fail 가능. 라이브 환경 검증 의무.

---

## 4. LESSON-068 (★★★ 공통 발견 패턴) 4번째 누적

| #     | 발견 시점                                        | 패턴                                              |
| ----- | ------------------------------------------------ | ------------------------------------------------- |
| 1     | Sprint 60 (2026-05-14) → Sprint 61 QA            | Casual PASS / Mobile PARTIAL 2건 false positive   |
| 2     | Sprint 61 (2026-05-17) → Sprint 62 QA            | BL-350/354 ★★★ 공통 P0 (Optimizer Zod error 도배) |
| 3     | Sprint 62 (2026-05-17) → Beta 진입 결정          | (별도 재측정 skip, 본인 의지 gate 통과)           |
| **4** | **Sprint 63 S7 (#318, 2026-05-30) → Phase C QA** | **S7-A regression — schema fix 가 silent bypass** |

**LESSON-068 정식 승격 의무 조건 = 3/3 → 4/4 누적**. 다음 sprint cycle 진입 시 `.ai/common/global.md` 또는 `.ai/project/lessons.md` 정식 등재 권고.

핵심 교훈: **머지된 fix 의 _라이브 환경 재검증_** 이 unit test green 만으로는 잡지 못하는 통합 wiring 결함을 발견한다.

---

## 5. 추가 발견 (P2/P3, 별도 트리아주)

| ID 후보   | 위치                                           | 내용                                                            | 우선순위                               |
| --------- | ---------------------------------------------- | --------------------------------------------------------------- | -------------------------------------- |
| BL-신규-A | `register-exchange-account-dialog.tsx` Select  | Base UI "uncontrolled Select after initialized" console warning | P3 (controlled Select 로 마이그레이션) |
| BL-신규-B | `test-order-dialog.tsx` inline `zodV4Resolver` | 공유 helper 로 마이그레이션 (PR #319 footnote 명시)             | P3 (refactor)                          |
| BL-신규-C | `/pricing` → `/#pricing` anchor redirect       | 의도된 동작이나 SEO 측면 `/pricing` 별도 page 검토              | P3 (UX 결정)                           |
| 확인됨    | BL-320 "Development mode" Clerk badge          | production deploy 시 자동 해소 (기존 묶음)                      | (자동 해소)                            |

---

## 6. Coverage 미커버 (다음 세션 권고)

본 세션은 **navigation + form UX** 만 검증. 다음 영역은 별도 라이브 QA 필요:

1. **백테스트 실행 → 24 metric 표시** — Celery worker 가동 필요 (S1 P1-5 `avg_holding_hours` 정상 표시 확인)
2. **Optimizer Grid/Bayesian/Genetic 실행** — Celery + 실 백테스트 필요 (S3 WF backtest_config 전파 / S4 Categorical reject)
3. **Webhook payload 처리** — `parse_tv_payload` 비숫자 입력 → 401 (S6 InvalidOperation catch)
4. **mainnet money path** — 실 거래소 credentials 필요 (S5 webhook realized_pnl / market notional / canceled reconcile)
5. **모바일 페이지 내부 터치 ≥44pt** — Sprint 61~62 fix 회귀 (BL-339/356~359)

---

## 7. 결론

- **본 라이브 QA 가 한 P1 발견 + hotfix close-out** = audit Phase F P1 7/7 close-out + Phase C 검증까지 정합 회복.
- main `7c07cbe` = Beta 본격 진입 prep 완료 상태 유지 (P0 = 0, P1 fix-merged 7/7).
- LESSON-068 4번째 누적 — 라이브 QA 의무화 패턴 정식 승격 권고.
- 남은 Beta 진입 blocker = G1/G7/G8 + BL-070/072 (USER-DECIDE / 외부 인프라).
