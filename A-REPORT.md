# 레인 α 보고 — [BL-784] e2e 신원이 자기 한도에 목이 졸린다

브랜치 `stage/bl784-ratelimit` (워크트리 wt3 · 슬롯 3) · 2026-08-17

## 한 줄

`e2e@dogfood.local` 신원에만 rate limit 을 면제하는 완화를 넣었고, **authed 스위트가 연속 3회
rc=0(90 passed) · BE 429 발생 0건**이다. 완화가 실제로 한도를 푸는지는 한도를 `5/minute` 로
낮춘 대조 2회로 증명했다 — 완화를 no-op 으로 만들면 같은 조건에서 **429 가 913건 나고 8건이
실패**하고, 완화를 켜면 **0건 · 90 passed** 다.

## 무엇을 바꿨나

| 파일                                                | 내용                                                                                                    |
| --------------------------------------------------- | ------------------------------------------------------------------------------------------------------- |
| `apps/api/src/core/config.py`                       | `e2e_rate_limit_exempt_email` 설정 신설(기본 빈 값) + production 에서 값이 있으면 **부팅 실패**         |
| `apps/api/src/common/rate_limit.py`                 | 판정식 `is_rate_limit_exempt_identity()` + `_RateLimitIdentityMiddleware` 에서 slowapi skip 플래그 세팅 |
| `apps/api/src/realtime/auth.py`                     | `verified_claims_or_none()` 신설 · `verified_subject_or_none()` 은 그 얇은 래퍼로                       |
| `.env.example`                                      | `E2E_RATE_LIMIT_EXEMPT_EMAIL` 추가                                                                      |
| `apps/api/tests/common/test_rate_limit_identity.py` | ⑤절 신설 — 배선 4건 + 값 표 12건                                                                        |
| `apps/api/tests/test_config_production_guard.py`    | production 부팅 거부 1건 + baseline 에 "미설정" 강제                                                    |

**완화가 성립하는 조건은 둘이고 둘 다 필요하다.** ⑴ `settings.is_production` 이 거짓 ⑵ 검증된
JWT 의 `email` claim 이 `E2E_RATE_LIMIT_EXEMPT_EMAIL` 과 같다(양쪽 `strip().lower()`).
설정이 비었거나 공백뿐이면 어떤 신원도 통과하지 못한다 — 비교보다 **설정 검사를 먼저** 둔 이유다.

### 설계 판단 세 가지

**⑴ 이메일을 키로 썼다.** `rate_limit_key` 가 쓰는 `sub` 는 Better Auth 가 가입 시 만드는
UUID 라 설정 파일에 적을 수 없다(DB 를 다시 만들면 값이 바뀐다). `email` 은 서명된 payload 안에
있고 `authenticate_token` 이 이미 읽던 claim 이다.

**⑵ 검증을 두 번 하지 않는다.** 면제 판정에 payload 가 필요해서 `verified_claims_or_none` 을
만들고 기존 `verified_subject_or_none` 을 그 래퍼로 바꿨다. 토큰 하나에 crypto 를 두 번 돌리는
것을 피하고, 검증기는 여전히 `realtime/auth.py` 한 곳이다(`apps/api/AGENTS.md` §2).

**⑶ 면제 신호는 `request.state._rate_limiting_complete` 다.** slowapi 소유의 플래그이고,
slowapi 가 **미들웨어 갈래(`middleware.py:44`)와 데코레이터 갈래(`extension.py:730·762`)
양쪽에서** 이 이름을 본다 — 그래서 한 줄이 `default_limits` 와 `@limiter.limit` 을 함께 면제한다.
authed 스위트가 실제로 치는 `/api/v1/backtests` 에 `10/minute` 데코레이터가 붙어 있어 이 점이
필요했다. 이름이 slowapi 것이라 업그레이드에 깨질 수 있지만 **깨지는 방향이 「한도가 다시
걸리는」 쪽**이라 프로덕션 위험은 없고, 깨지면 AC-3 축 테스트가 red 로 알려 준다.

## 수용 기준별 판정

| AC                            | 판정 | 근거                                                                                                                                                                                                                     |
| ----------------------------- | ---- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| AC-1 완화가 e2e 신원에만      | ✅   | `test_only_the_e2e_identity_is_relaxed` — 같은 요청을 두 신원으로. e2e = `[200]×5`, 일반 = `[200, 429]`                                                                                                                  |
| AC-2 프로덕션 구성에서 미발화 | ✅   | `test_production_config_never_relaxes`(같은 설정·같은 신원, `app_env` 만 production → `[200, 429]`) + `test_unset_exemption_relaxes_nobody` + 값 표 12건 + `test_production_rejects_e2e_rate_limit_exemption`(부팅 거부) |
| AC-3 판별력(낮춘 한도)        | ✅   | 아래 「AC-3 상세」                                                                                                                                                                                                       |
| AC-4 authed 연속 3회 rc=0     | ✅   | 3/3 rc=0 · 90 passed · 224s / 215s / 211s                                                                                                                                                                                |
| AC-5 전량 BE pytest ≥4759     | ✅   | rc=0 · **4776 passed**, 32 skipped, 400.60s                                                                                                                                                                              |
| AC-6 429 발생 0건             | ✅   | AC-4 3회 전 구간 BE 접근로그 429 **0건** · slowapi `exceeded at endpoint` **0건**                                                                                                                                        |

기록 위치: AC-4 = `apps/web/test-results/ac4-relaxed-summary.txt` + 회차별
`ac4-relaxed-{1,2,3}-authed.log` + `test-results/ac4-relaxed-{1,2,3}/chromium-authed/results.json`.

### AC-3 상세 — 같은 한도, 완화만 뒤집었다

`default_limits` 를 `100/minute` → `5/minute` 로 낮춘 상태에서 완화 여부만 바꿔 authed 를 각 1회.

| 조건                      | rc  | 결과                                 | BE 429  |
| ------------------------- | --- | ------------------------------------ | ------- |
| 5/minute · 완화 **no-op** | 1   | 8 failed · 4 did not run · 78 passed | **913** |
| 5/minute · 완화 **활성**  | 0   | **90 passed**                        | **0**   |

429 가 난 엔드포인트 상위: `/api/v1/strategies` 322 · `/api/v1/backtests` 254 ·
`/api/v1/orders` 237 · `/api/v1/live-sessions` 45.

★no-op 회차에서 실패한 8건에 **`sprint46-tier1-critical.spec.ts:69`** 이 들어 있다 —
[BL-773] 회차에서 최초로 실패한 그 테스트다. 즉 한도를 낮춰 429 를 강제하면 그 테스트가
다시 실패하고, 완화를 켜면 통과한다.

## 표적 변이표

`apps/api/src/common/rate_limit.py` 에 문자열 치환으로 심고 문자열 치환으로 되돌린 뒤
sha256 으로 복원을 확인했다(`git checkout` 미사용). 앵커는 매번 1건임을 확인했다.

| 변이                                        | 기대     | 실측   | red 가 난 테스트                                                                         |
| ------------------------------------------- | -------- | ------ | ---------------------------------------------------------------------------------------- |
| M1 「프로덕션이 아니다」 판정 제거          | AC-2 red | ✅ red | `test_production_config_never_relaxes` + 값 표 양성 3건                                  |
| M2 「이 신원이다」 판정 제거(`return True`) | AC-1 red | ✅ red | `test_only_the_e2e_identity_is_relaxed` · `..._covers_decorated_routes` + 값 표 음성 3건 |
| M3 완화를 no-op                             | AC-3 red | ✅ red | pytest 2건 + **e2e 축 8 failed / 913×429**(위 표)                                        |

M1 은 `test_production_config_never_relaxes` 만이 아니라 값 표의 **양성 케이스**를 함께 죽인다 —
production 에서는 표의 참 케이스까지 전부 거짓이어야 한다는 단언이 같은 테스트 안에 있다.

## 확인하지 못한 것 · 남은 것

**⑴ 메인 체크아웃의 `.env.local` 은 내가 안 건드렸다.** 완화는 `E2E_RATE_LIMIT_EXEMPT_EMAIL`
이 채워져야 발화하는데, 내가 채운 것은 **워크트리 wt3 의 `apps/api/.env.local` 하나**다.
`.env.local` 은 커밋 대상이 아니므로, 메인에서 게이트를 도는 사람이 그 줄을 안 넣으면
**코드는 머지됐는데 authed 는 그대로 흔들린다.** 아침에 넣을 한 줄:

```
E2E_RATE_LIMIT_EXEMPT_EMAIL=e2e@dogfood.local     # apps/api/.env.local (메인 체크아웃)
```

값은 `apps/web/.env.local` 의 `E2E_AUTH_EMAIL` 과 같아야 한다. CI 는 `e2e:authed` 를 돌리지
않으므로(`ci.yml` 에 그 잡이 없다) CI secret 은 필요 없다.

**⑵ 다른 레인과 Redis 버킷을 공유한다.** `be-isolated` 는 모든 슬롯이 `redis://localhost:6380/3`
을 쓴다. 이번 측정 중 형제 레인이 authed 를 돌리지 않아 오염은 없었지만(429 0건이 그 증거다),
두 레인이 같은 신원으로 동시에 돌면 버킷이 겹친다. 이번 회차에서 검증하지 않았다.

**⑶ 429 계수는 BE 접근 로그 기준이다.** `qb_rate_limit_throttled_total` 메트릭으로 교차
확인하지 않았다 — `/metrics` 가 이 워크트리에서 `PROMETHEUS_BEARER_TOKEN` 미설정이라 401 이다.
접근 로그와 slowapi WARN 두 축이 모두 0 이라 그대로 뒀다.

**⑷ celery 를 타는 경로는 검증 대상이 아니었다.** 워크트리에서 금지이고, `/healthz` 는
`celery_workers: 0` 으로 503 이다(그 밖의 축은 `db: ok · redis: ok`). authed 스위트 90건은
이 상태에서 전건 통과한다.

## 회차 중 밟은 환경 함정 — 원인이 아니었지만 증상이 같았다

authed 가 **3/3 red** 로 나온 구간이 있었고 원인은 rate limit 이 아니라 **Turbopack 영속
캐시가 물린 것**이었다. 증상은 `○ Compiling /sign-in/[[...sign-in]] ...` 에서 멈춘 채
next-server 가 **CPU 0.0%** 로 대기하고, `global.setup.ts:65` 의 `page.goto('/sign-in')` 이
120초 timeout 으로 죽는 것이다(그 뒤 89건은 `did not run`). `curl /sign-in` 은 240초를 넘겨도
응답이 없었고, 메모리는 55% 여유 · 디스크는 99% 사용(14GiB 여유)이었다.

`apps/web/.next` 를 치우고 dev 서버를 다시 띄우자 `/sign-in` 이 **0.79초**에 컴파일됐고 그
뒤 3회가 전부 green 이다. **「authed 스위트 red」에는 [BL-784] 말고 이 원인도 있다** —
구분점은 실패가 `setup` 단계에서 나고 429 가 0건이라는 것이다.

(부수 사실: 처음 띄운 dev 서버는 세션 도구의 백그라운드 수명에 묶여 9분 만에 죽었다.
`nohup … & disown` 으로 다시 띄운 뒤로는 안 죽었다. 레포와 무관한 실행 환경 사정이다.)

## 게이트

`mise exec -- tools/scripts/final-gates.sh --run bl784-fix --pre-pr` — 결과는 커밋 로그와
`.claude/gates/bl784-fix/` 참조. 신호 게이트 4종은 유예되며 아침 몫이다.
