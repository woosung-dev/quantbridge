# 레인 α 원장 초안 — [BL-784]

아침에 오케스트레이터가 `docs/backlog.md` 에 반영한다. **수치의 정본은 `A-REPORT.md` 다** —
아래는 그것을 참조한다.

## 상태줄 제안

```
**상태:** ✅ **RESOLVED** (2026-08-17, PR 미생성 — 브랜치 `stage/bl784-ratelimit`)
```

## 본문 제안

`apps/api/src/common/rate_limit.py` 의 `default_limits=["100/minute"]` 이 authed 스위트를
429 로 끊고 있었다. 스위트는 한 신원으로 90 테스트를 돌고 페이지마다 BE 요청 4~8건을 내므로
60초 창을 상시 소진한다. 수리는 **e2e 신원 하나만 면제**하는 것이다 — 한도 자체는 [BL-754] 가
세운 프로덕션 방어물이라 건드리지 않았다.

발화 조건은 둘이고 둘 다 필요하다: ⑴ `settings.is_production` 이 거짓 ⑵ 검증된 JWT 의
`email` 이 `E2E_RATE_LIMIT_EXEMPT_EMAIL` 과 일치. 설정이 비면 아무도 면제되지 않고,
`app_env=production` 에 그 값이 있으면 **부팅이 실패**한다(런타임 판정과 별개의 층 —
2026-08-15 에 배포 호스트가 `APP_ENV` 를 안 넣어 `{"env":"development"}` 로 돌던 전력 때문).

판정: authed 연속 3회 rc=0(90 passed) · BE 429 **0건**. 완화의 판별력은 한도를 `5/minute` 로
낮춰 증명했다 — 완화 no-op 이면 429 913건에 8 failed, 완화를 켜면 0건에 90 passed
(수치 전부 `A-REPORT.md` §AC-3 상세).

## 반드시 함께 적을 것 — 코드만 머지하면 안 고쳐진다

`E2E_RATE_LIMIT_EXEMPT_EMAIL` 은 `.env.local` 값이고 그 파일은 커밋 대상이 아니다.
**메인 체크아웃의 `apps/api/.env.local` 에 아래 한 줄을 넣어야 완화가 발화한다.**
안 넣으면 코드는 들어갔는데 authed 는 그대로 흔들린다.

```
E2E_RATE_LIMIT_EXEMPT_EMAIL=e2e@dogfood.local
```

값은 `apps/web/.env.local` 의 `E2E_AUTH_EMAIL` 과 같아야 한다. CI 는 `e2e:authed` 를 돌리지
않으므로 CI secret 은 필요 없다.

## [BL-773] 의 `sprint46-tier1-critical.spec.ts:69` — 이 회차의 실측

직전 회차가 재현하지 못했던 그 테스트는 **이번에 재현됐다.** 한도를 `5/minute` 로 낮춰 429 를
강제한 회차의 실패 8건 안에 그것이 들어 있고, 완화를 켠 같은 조건에서는 통과한다. 완화를 켠
정상 한도 3회에서도 전부 통과했다.

⇒ 직전 회차의 「`page.route()` 로 전수 stub 이라 BE 429 를 안 탄다」는 판단은 **이 테스트에
관해서는 성립하지 않는다.** 그 spec 이 stub 하지 않는 요청이 있어 429 를 탄다.
⇒ [BL-784] 를 닫는 데 이 축이 남은 차단자가 아니다.

## 새로 세울 만한 항목 (오케스트레이터 판단)

**「authed 스위트 red」의 두 번째 원인 — Turbopack 영속 캐시 물림.** 이번 회차에서 3/3 red 가
났고 원인이 rate limit 이 아니었다. `○ Compiling /sign-in/[[...sign-in]] ...` 에서 next-server 가
**CPU 0.0%** 로 멈추고 `global.setup.ts:65` 가 120초 timeout 으로 죽는다 — 그 뒤 89건은
`did not run`. `apps/web/.next` 를 치우면 `/sign-in` 이 0.79초에 컴파일된다.

[BL-784] 와 구분하는 판정식: **실패가 `setup` 단계에서 나고 BE 429 가 0건**이면 캐시 쪽이다.
`docs/lessons.md` 또는 `gates-and-traps.md` 에 한 줄 값어치가 있다고 본다 — 같은 증상에
다른 원인이 둘이라는 것이 이 항목이 넉 달을 끈 이유와 같은 모양이다.
