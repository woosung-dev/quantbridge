# 공개 오픈 직전 보안 체크리스트 (코드 밖 조치)

> **출처**: 2026-11-19 보안 감사 run-1/run-2 (감사 산출물은 레포 밖 `~/audits/quant-bridge/`).
> **언제 쓰나**: Cloudflare Access(이메일 OTP)를 `qb.woosung.dev` 에서 걷어 **가입을 공개로 여는 날**, 그 전에.
> 코드로 막을 수 있는 것은 PR(`fix/security-baseline-20261119`)이 막았다. 여기 남은 것은 **서버·프록시·env·DB·제품 결정**이다.

★**순서가 중요하다.** 1~4 를 끝내기 전에는 Access 를 걷지 마라. 지금 Access 가 이 넷을 대신 막고 있다.

## A. Access 해제 전 필수 (안 하면 오픈 순간 열린다)

### 1. 관리자 이메일 선점 — 코드 미수정 항목
`require_admin` 은 **검증 안 된 JWT `email`** 이 `WAITLIST_ADMIN_EMAILS` 에 있으면 관리자로 본다
(`apps/api/src/waitlist/dependencies.py`). 가입에 이메일 검증이 꺼져 있어(`apps/web/src/lib/auth.ts` `requireEmailVerification: false`)
**그 주소로 먼저 가입한 사람이 관리자**다. Better Auth 는 같은 이메일 재가입을 거부하므로, 운영자가 먼저 쥐고 있으면 막힌다.

```sql
-- 운영 DB, 읽기 전용. 목록의 모든 주소가 나오고, 전부 운영자 본인 계정이어야 한다.
SELECT lower(email), "createdAt" FROM auth_user
 WHERE lower(email) = ANY (ARRAY['<WAITLIST_ADMIN_EMAILS 의 주소들>']);
```
- [ ] 목록의 **모든** 주소가 행으로 나온다 · 전부 본인 계정이다
- [ ] 중장기: 이메일 검증을 켠다(Resend 도메인 검증) — 켜기 전까지 이 항목이 유일한 방어다

### 2. e2e rate-limit 면제 값이 비어 있다
PR 이 「발급자가 localhost 일 때만」으로 좁혔지만, 값 자체가 운영에 있으면 안 된다.
```bash
grep -c '^E2E_RATE_LIMIT_EXEMPT_EMAIL=.\+' apps/api/.env.local   # 값 출력 없이 개수만 — 0 이어야 한다
systemctl --user cat <api 유닛> | grep -c 'E2E_RATE_LIMIT_EXEMPT_EMAIL=.\+'  # 0
```

### 3. `APP_ENV=production` 으로 전환 — **먼저 드라이런**
지금 운영은 `APP_ENV` 미설정 = `development` 라 `Settings._enforce_production_safety`(`apps/api/src/core/config.py`)가 **통째로 꺼져 있다**.
켜면 아래 값이 하나라도 틀릴 때 **부팅이 실패한다** — 그래서 바로 넣지 말고 같은 env 로 먼저 생성만 해 본다.
```bash
cd apps/api && set -a; . ./.env.local; set +a
APP_ENV=production uv run python -c "from src.core.config import Settings; Settings(); print('ok')"
```
통과 조건(검증기가 요구하는 것):
- [ ] `SECRET_KEY` 가 `change-me`/빈 값이 아니다 · `WAITLIST_TOKEN_SECRET` 이 비어 있지 않다
- [ ] `FRONTEND_URL` · `WAITLIST_INVITE_BASE_URL` · `BETTER_AUTH_URL` 에 localhost 가 없다
- [ ] `PROMETHEUS_BEARER_TOKEN` 이 있다 · `E2E_RATE_LIMIT_EXEMPT_EMAIL` 이 비어 있다
- [ ] 드라이런 `ok` → API 유닛과 워커 env 에 `APP_ENV=production` 추가 → 재시작 → `/health` 의 `env` 확인
- [ ] 전환 전이라도 API 호스트 env 의 `DEBUG` 가 비었거나 `false` 인지 확인한다(`.env.example` 기본값은 `true`).
  `FastAPI(debug=True)` 면 Starlette 가 처리 안 된 예외의 **전체 traceback 을 익명 호출자에게** 돌려주고 `unhandled_exc_handler` 를 건너뛴다(run-2 하드닝 메모)

### 4. 실 클라이언트 IP 로 rate limit 이 갈린다
- [ ] API env 에 `TRUSTED_PROXIES=127.0.0.1/32` (cloudflared 가 host 네트워크라 peer 가 루프백이다 — `.env.example` 주석)
  비어 있으면 **전 사용자가 한 버킷**이고, 익명 대기자 신청(5회/시간)도 전역 1버킷이 된다.

## B. Cloudflare (`qb-api.woosung.dev` 는 지금도 Access 밖이다)

- [ ] **요청 본문 크기**: 플랜 기본값(Free/Pro 100MB)에 기대지 말고 WAF 규칙으로 API 본문을 1MB 정도로 막는다.
  코드 상한은 웹훅 64KB · Pine 원본 100,000자다.
  ★웹훅 말고는 **앱에 본문 크기 상한이 없다**. FastAPI 는 JWT 검사·rate limit 데코레이터보다 먼저 본문 전체를 읽고 JSON 을 디코드한다.
  그래서 401/422 로 끝나는 요청은 익명이라도 rate limit 에 안 잡힌다(run-2 needs_validation). 지금은 이 WAF 규칙이 유일한 상한이다.
  코드로 막으려면 가장 바깥에 본문 크기 ASGI 미들웨어(예: 1MB, 413)를 둔다
- [ ] **익명 경로 rate limit 규칙**: `/healthz`, `/api/v1/webhooks/*`, `/api/v1/waitlist` — 앱 rate limit 면제(`/healthz`·웹훅)거나 IP 단위다
- [ ] Access 를 걷을 때 **범위를 확인**: FE 전체를 걷는지, `/api/auth/*` 만 여는지. 1·2 를 끝낸 뒤에만
- [ ] `cloudflare/cloudflared:latest` 를 버전 태그로 고정 · 터널 토큰을 커맨드라인 대신 `TUNNEL_TOKEN` env 로

## C. DB

- [ ] 앱 롤에 `idle_in_transaction_session_timeout` 확인(`SHOW ...`). WS 커넥션 점유는 PR 이 고쳤지만, 다른 경로의 방어선이다
- [ ] 앱 롤 `statement_timeout`·`temp_file_limit` 확인. 백테스트 갭 탐지(`generate_series`)가 기간에 비례한다(PR 이 10년으로 상한).
  넣는다면 가장 긴 정상 쿼리를 먼저 재고 그보다 크게
- [ ] FE 의 `BETTER_AUTH_DATABASE_URL` 이 앱 롤이 아니라 **`qb_auth` 전용 롤**인지 (`better-auth-setup.md`)
- [ ] `POSTGRES_PASSWORD` 가 compose 기본값 `password` 가 아니다

## D. CORS · 쿠키 · 헤더

- [ ] `FRONTEND_URL` = `https://qb.woosung.dev` 정확히 (CORS 단일 origin · WS Origin 비교가 이 값 하나에 걸린다)
- [ ] `BETTER_AUTH_URL` 이 https → Better Auth 가 `Secure` 쿠키를 쓴다. 브라우저 개발자도구에서 세션 쿠키 `Secure; HttpOnly; SameSite=Lax` 확인
- [ ] CSP 헤더 없음(`apps/web/next.config.ts`) — 지금 XSS 싱크는 못 찾았지만, 오픈 후 첫 하드닝 후보

## E. 큐 · 비용 · 제품 결정

- [ ] **Celery**: 백테스트·스트레스와 주문 실행이 **같은 2칸 기본 큐**다. 분리하려면 라우트와 워커 커맨드(서버 compose)를 **같은 배포에** 바꿔야 한다
  — 라우트만 바꾸면 소비자 없는 큐로 주문이 안 나간다. 이번 PR 은 건드리지 않았다
- [ ] **1분봉 백테스트 비용**: 기간 상한(3653일)은 **일수**만 센다. `1m` × 10년 ≈ 526만 봉을 갭 탐지·CCXT 수집·적재·메모리 로드까지 한 번에 처리한다.
  게다가 `backtest.run` 에는 time limit 이 없다(옵티마이저·스트레스에는 있다). 최소 조치는 `backtest.run` 에 `soft_time_limit`/`time_limit` 을 다는 것이다.
  봉 수 상한((기간 ÷ 봉 길이) ≤ N)은 실제 쓰는 1분봉 기간을 재 본 뒤 정한다. 운영 `OHLCV_PROVIDER` 와 `ts.ohlcv` 1m 행 수 확인부터(run-2 needs_validation)
- [ ] **LLM**: `LLM_PROVIDER_ORDER` 를 켤지 · 가입자가 아무 카탈로그 모델로 바꿀 수 있게 둘지(`strategy/narrative/catalog.py` `resolve_override`) 결정.
  켠다면 각 provider 콘솔에 **월 지출 한도**
- [ ] 대기자 신청이 409/202 로 「이미 신청한 이메일」을 알려 준다 — 제품상 비밀인지 결정
- [ ] Redis `requirepass` (지금은 루프백 바인딩)
- [ ] `AGENTS.md` §1 · `docs/PRD.md` 의 「Beta 외부 공개 안 연다」 문장을 오픈 결정에 맞게 바꾼다
