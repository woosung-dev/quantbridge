# QuantBridge — Better Auth 셋업·운영 가이드

> **목적:** 자체 인증(Better Auth) 설정·배포·검증 절차. 결정 근거는
> [ADR-034](../../decisions/034-auth-self-host-better-auth.md).
> **SSOT:** 라이브러리 문서는 https://www.better-auth.com/docs · 본 문서는 QuantBridge 통합 관점.
> **환경 변수 카탈로그:** [`env-vars.md`](./env-vars.md) §3
>
> ★이 문서는 2026-08-17 에 `clerk-setup.md` 를 대체했다. 구 문서 원문 =
> `git show 9920bf9a:docs/reference/operations/clerk-setup.md`.

---

## 1. 구조 — 무엇이 어디서 도는가

```
브라우저 ──세션 쿠키──→ Next.js (apps/web)  ← 인증 서버 본체
                          │  /api/auth/[...all]   로그인·가입·세션·JWKS
                          │  auth_user / auth_session / auth_account / auth_verification / auth_jwks
                          ↓ (BETTER_AUTH_DATABASE_URL — auth_* 전용 롤)
                       Postgres
브라우저 ──Bearer JWT──→ FastAPI (apps/api)
                          └ JWKS 공개 키로 **검증만** 한다. 시크릿 0개.
```

**두 구간의 자격증명이 다르다.** 브라우저↔Next 는 쿠키, Next↔FastAPI 는 JWT 다.
헷갈리면 「왜 쿠키가 있는데 401 인가」에서 시간을 태운다.

| 축            | 값                                                                   |
| ------------- | -------------------------------------------------------------------- |
| 알고리즘      | **EdDSA (Ed25519)** — 라이브러리 기본. 양쪽을 함께 바꾸지 않으면 401 |
| JWT 만료      | **15분** (기본). 클라이언트가 캐시하고 만료 1분 전 갱신              |
| 세션 만료     | 7일 (기본) · `updateAge` 1일                                         |
| `sub`         | Better Auth `user.id` = 우리 `users.auth_subject`                    |
| `iss` / `aud` | 둘 다 `BETTER_AUTH_URL`                                              |
| 비밀번호 해시 | scrypt · **`auth_account.password`** 에 저장(`auth_user` 아니다)     |

---

## 2. 최초 1회 — 로컬

```bash
# ① 시크릿 생성
openssl rand -base64 32        # → BETTER_AUTH_SECRET

# ② apps/web/.env.local
BETTER_AUTH_SECRET=<위 값>
BETTER_AUTH_URL=http://localhost:3000
BETTER_AUTH_DATABASE_URL=postgresql://quantbridge:<pw>@localhost:5433/quantbridge
E2E_AUTH_EMAIL=e2e@dogfood.local
E2E_AUTH_PASSWORD=<8자 이상>

# ③ apps/api/.env.local
BETTER_AUTH_URL=http://localhost:3000

# ④ 스키마 — alembic 이 정본이다. Better Auth CLI 로 DB 를 치지 마라(§5)
cd apps/api && set -a; . ./.env.local; set +a && uv run alembic upgrade head
```

★`BETTER_AUTH_DATABASE_URL` 은 `postgresql://` 이다 — `+asyncpg` 를 붙이지 마라(그건 SQLAlchemy 방언이다).

---

## 3. 최초 1회 — 서버 (전용 DB 롤)

FE 컨테이너는 인터넷 표면이다. **앱 DB 롤을 주지 마라.**

```sql
-- 서버 DB 에서 1회. ★DDL 이므로 사용자 승인 뒤에 실행한다.
CREATE ROLE qb_auth LOGIN PASSWORD '<openssl rand -hex 24>';
GRANT CONNECT ON DATABASE quantbridge TO qb_auth;
GRANT USAGE ON SCHEMA public TO qb_auth;
GRANT SELECT, INSERT, UPDATE, DELETE
  ON auth_user, auth_session, auth_account, auth_verification, auth_jwks TO qb_auth;
```

**음성 대조(의무)** — 이 롤로 우리 도메인 테이블이 안 보여야 한다:

```bash
PGPASSWORD=... psql -h 127.0.0.1 -p 5433 -U qb_auth -d quantbridge \
  -c 'SELECT count(*) FROM users;'      # → permission denied for table users
```

루트 `.env` 에 세 값을 넣는다 — `BETTER_AUTH_SECRET` · `BETTER_AUTH_URL` ·
`BETTER_AUTH_DATABASE_URL`(위 `qb_auth` DSN). compose 가 `:?required` 로 강제한다.

`apps/api/.env.local` 에는 두 줄:

```
BETTER_AUTH_URL=https://qb.woosung.dev
BETTER_AUTH_JWKS_URL=http://quantbridge-frontend:3000/api/auth/jwks
```

★JWKS 를 **터널로 왕복시키지 마라.** 컨테이너 내부 주소를 쓰면 Cloudflare 왕복이 사라지고
FE 가 재기동 중일 때의 실패 표면도 좁아진다. FE 스택은 base compose 네트워크에 attach 돼 있다.

---

## 4. 배포 절차 (FE 재빌드가 반드시 붙는다)

절차 자체는 [`frontend-deploy.md`](./frontend-deploy.md) §3.3 과 같다. 인증이 들어오면서
**서버 쪽에 두 단계가 추가**된다:

1. 맥에서 `pnpm build` → `docker build` → `docker save | ssh docker load`
2. **alembic 적용** — `tools/scripts/soak-stack.sh migrate`(dry-run) → 승인 → `--confirm`
3. `QB_FRONTEND_TAG` 갱신 → `docker compose -f infra/compose/docker-compose.frontend.yml -p quantbridge-fe up -d`
4. **API 유닛 재시작** — `systemctl --user restart quantbridge-api.service`
   (★2026-08-16 [BL-762] — 이 단계가 절차에서 빠져 고쳐 둔 보안이 발효하지 않은 전례가 있다)
5. read-back (§6)

---

## 5. 라이브러리 버전을 올릴 때 (이 결정의 유일한 부채)

Better Auth 가 스키마를 바꾸면 **우리 alembic 이 그걸 모른다.** 올릴 때마다 대조해라:

```bash
cd apps/web
BETTER_AUTH_DATABASE_URL=<로컬 DSN> BETTER_AUTH_URL=http://localhost:3000 \
BETTER_AUTH_SECRET=generate-only \
  npx --yes @better-auth/cli@latest generate --config src/lib/auth.ts --output /tmp/ba.sql -y
# → /tmp/ba.sql 이 비어 있으면 변화 없음. 무언가 나오면 alembic revision 으로 옮기고
#   src/auth/better_auth_tables.py 선언도 함께 고친다.
cd ../api && set -a; . ./.env.local; set +a && uv run alembic check   # rc=0 이어야 한다
```

★`generate` 는 **DB 에 붙는다**(Kysely 인트로스펙션). 로컬 개발 DB 를 쓰고 서버를 가리키지 마라.
★`@better-auth/cli migrate` 는 **쓰지 않는다** — 서버 DDL 은 alembic 하나만 친다(ADR-034 §D2).

---

## 6. 검증 (순서 있음)

```bash
# ① JWKS 가 공개돼 있고 EdDSA 키가 들어 있다
curl -s https://qb.woosung.dev/api/auth/jwks | python3 -m json.tool | head
#    → {"keys":[{"crv":"Ed25519","kty":"OKP",...}]}

# ② 로그인 → 토큰 발급 → 그 토큰으로 API 가 열린다
#    ★브라우저에서 로그인한 뒤 개발자도구로 `/api/auth/token` 을 부르는 것이 가장 빠르다.
curl -s -H "Authorization: Bearer <token>" https://qb-api.woosung.dev/api/v1/auth/me

# ③ 음성 대조 — 아무 토큰이나 통과하지 않는다
curl -s -o /dev/null -w '%{http_code}\n' \
  -H "Authorization: Bearer garbage" https://qb-api.woosung.dev/api/v1/auth/me   # → 401
```

★★**`/health` 200 은 아무 증거가 아니다**([BL-625]). **로그인 → `/strategies` 렌더 →
`/trading` 세션 진단 패널의 WS 상태 `authed`** 까지 가야 검증이다.

---

## 7. 함정 (실측으로 물린 것)

★**`BETTER_AUTH_URL` 이 FE·BE 에서 어긋나면 전건 401 이다.** JWT 의 `iss`/`aud` 가 그 값이고
FastAPI 가 같은 값으로 검증한다. 증상은 「로그인은 되는데 화면이 비어 있다」로 보인다.

★**JWT 만료가 15분이다.** 장시간 열어 둔 탭의 WebSocket 은 재인증을 타야 한다 —
`ws-client.ts` 의 `authFailureRetries` 가 그 경로다. WS 가 조용히 죽으면 여기부터 의심해라.

★**`python-jose` 로는 검증할 수 없다** — EdDSA 미지원이다(실측). `pyjwt[crypto]` 를 쓴다.

★**`e2e:authed` 의 `.env.local` 로더는 `global.setup.ts` 자신이다.**
`playwright.config.ts` 에는 dotenv 가 없다. 종전에는 `clerkSetup()` 이 우연히 그 일을 하고
있었고, 그것을 걷어낼 때 **조용히 사라질 뻔했다**.

★**새 로그인은 빈 계정을 만든다.** 기존 사용자의 데이터를 보려면 `auth_subject` 를 이어야 한다 —
`apps/api/scripts/link_auth_subject.py --list` 로 보고, `--confirm` 으로 잇는다(승인 필요).

★**geo-block L3 은 이제 진짜로 발화한다.** 제한 국가에서 가입하면 `databaseHooks.user.create.before`
가 `false` 를 돌려 계정이 만들어지지 않는다. 로컬에서는 `CF-IPCountry` 헤더가 없어 통과한다 —
그것이 정상이고, 그래서 이 축의 음성 대조는 헤더를 **직접 넣어** 재야 한다.

---

## 8. 관련 문서

- 결정 근거: [ADR-034](../../decisions/034-auth-self-host-better-auth.md)
- FE 배포: [`frontend-deploy.md`](./frontend-deploy.md) · 환경 변수: [`env-vars.md`](./env-vars.md)
- geo-block 3계층: [`security/geo-block-setup.md`](./security/geo-block-setup.md)
