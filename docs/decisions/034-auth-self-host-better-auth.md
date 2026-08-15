# ADR-034 — 인증을 Clerk 에서 self-host Better Auth 로 옮긴다

- **Status:** Accepted (2026-08-17)
- **회차:** auth-selfhost
- **관련:** [ADR-001](001-tech-stack.md)(해당 행 Superseded) · [ADR-033](033-db-hosting-self-host-timescaledb.md) ·
  [BL-070]·[BL-071]·[BL-072] · [BL-261]·[BL-320]·[BL-321]·[BL-347]·[BL-352] · [BL-753] · [BL-770]

## Context

Beta 진입 3종의 실질은 [BL-071] 「백엔드 프로덕션 배포」였고, 착수 실측에서 그 항목의 남은 일이
**「Clerk 을 production 인스턴스로 승격」**이라는 것이 드러났다. 사용자 결정은 승격이 아니라
**공급자를 걷어내고 self-host 로 가는 것**이었다.

이 결정은 [ADR-033](033-db-hosting-self-host-timescaledb.md)(DB self-host)과 같은 방향이되
근거가 다르다. DB 는 **관리형이 기술적으로 막혀서**(TimescaleDB TSL 라이선스) 자체 운영이
남은 유일한 길이었다. 인증은 관리형이 잘 돌고 있었고, 옮기는 이유는 **소유권**이다 —
`CLERK_SECRET_KEY` 는 `.env.prod.example` 의 [validator 강제] 4종 중 하나였고, 공개 전환은
곧 그 공급자에 사용자 신원을 영구히 위탁한다는 뜻이었다.

## Decision

**Better Auth(`1.6.29`, MIT)를 Next.js 앱 안에 얹어 자체 인증 서버로 쓴다.**
브라우저↔Next 는 세션 쿠키, Next↔FastAPI 는 **JWT Bearer** 다. FastAPI 는 `/api/auth/jwks` 의
공개 키로 검증만 하고 **비밀을 하나도 쥐지 않는다.**

## 왜 이 모양인가 — 결정 9개

### D1. Better Auth 는 Next route handler 로 얹는다

`app/api/auth/[...all]/route.ts` + `toNextJsHandler(auth)` 가 공식 방식이고 Next 16 은
peerDependency·문서 양쪽에서 정식 지원이다. 별도 Node 서비스로 분리하는 길도 문서에 있으나
(클라이언트 `baseURL` 원격 지정) 컨테이너·systemd 유닛·터널 라우트가 하나씩 늘 뿐 사용자 2명에서
얻는 것이 없다.

★**대가 — FE 컨테이너가 처음으로 DB 커넥션을 갖는다.** 이 레포에서 `apps/web` 에 route handler 는
0건이었고 DB 접속도 0건이었다. 둘로 좁힌다:
⑴ `auth_*` 5테이블에만 권한이 있는 **전용 PG 롤**의 DSN 만 준다(`BETTER_AUTH_DATABASE_URL`).
⑵ 서버 DB 는 `127.0.0.1:5433` **루프백** publish 라 브리지에서 못 닿는다 — FE 스택을
base compose 네트워크(`quantbridge_quantbridge`, 2026-08-17 서버 실측)에 **external 로 attach** 한다.
★소크 창은 여전히 안 끊긴다 — external network 는 `-p quantbridge-fe down` 이 제거하지 않고,
서비스도 볼륨도 겹치지 않는다. 창을 끊는 것은 `soak-stack.sh pin`/`down` 과 DB 실격뿐이다.

### D2. 스키마 DDL 의 정본은 alembic 이다

Better Auth 의 `migrate` CLI 는 Kysely 로 DB 를 직접 친다. 이 레포 규약은 「서버 소크 DB DDL =
`soak-stack.sh migrate --confirm` + 매번 명시 승인」이다([BL-743]). 그래서
`@better-auth/cli generate` 로 **SQL 을 뽑아** alembic revision(`20260817_0001`)으로 옮기고,
`src/auth/better_auth_tables.py` 가 그 결과를 metadata 에 선언한다(우리 코드는 읽지도 쓰지도 않는다).

★**부채 1건** — Better Auth 버전을 올릴 때 `generate` 를 다시 돌려 대조해야 한다.
절차는 [`better-auth-setup.md`](../reference/operations/better-auth-setup.md) §5.

### D3. `users` 와 합치지 않는다 — `clerk_user_id` → `auth_subject` 하나만 바꾼다

기존 `users` 를 Better Auth 의 `user` 로 재사용하는 **공식 레시피는 문서에 없다**(Auth.js
마이그레이션 가이드조차 비교표만 준다). 게다가 비밀번호는 `user` 가 아니라 **`account.password`**
에 산다. ⇒ Better Auth 는 `auth_*` 5테이블을 갖고, 우리 `users` 는 그대로 두되 외부 ID 컬럼만
`auth_subject VARCHAR(64) UK` 로 rename 한다. FastAPI 는 JWT `sub` 로 지금과 **동형으로**
`get_or_create` 한다.

★이게 가능한 이유는 Sprint 4 가 이미 **내부 PK 와 외부 ID 를 분리**해 뒀기 때문이다
(`users.id` = UUID PK). FK 7곳 전부 `users.id` 를 보므로 **이 전환의 DB 파급이 컬럼 1개다.**

### D4. `pyjwt[crypto]` 를 넣고 `python-jose` 를 뺀다 — 의존성 순증 0

`python-jose` 는 **EdDSA 를 지원하지 않는다**(실측: `ALGORITHMS.SUPPORTED` 에 ES/RS/HS 만).
Better Auth JWT 플러그인 기본이 EdDSA/Ed25519 라 그대로는 못 쓴다. 그리고 그 패키지는
`src` 에서 **사용처가 0건**이었다. PyJWT 의 `PyJWKClient` 는 kid 조회·캐시·미상 kid 재조회를
제공한다 — 손으로 짜면 fail-open 검증기가 나온다.
실제 제거 10 패키지(`clerk-backend-api`·`svix`·`python-jose`·전이 7종) vs 추가 1.

### D5. 브라우저는 쿠키, 백엔드는 Bearer JWT

`apiFetch(path,{token})`(`lib/api-client.ts:66`)와 `ws-client` 의 `{type:"auth",token}` 계약이
**그대로**라 feature hooks 100+ 지점이 무변경이다. 토큰 기본 만료가 15분이라 클라이언트가
캐시하고 동시 요청을 하나로 접는다(`lib/auth-client.ts`).

### D6. 탈퇴는 `DELETE /api/v1/auth/me` 로 재이식한다 — 이 결정의 최대 위험

Clerk `user.deleted` 웹훅은 **「돈을 멈추는」 유일한 입구**였다(2026-08-15 surface-truth S3 P1):
계정 잠금 + 전략 archive + **라이브 세션 전량 비활성** + **웹훅 시크릿 revoke** 를 한 트랜잭션으로
닫는다. 공급자를 바꾸면 그 입구가 조용히 사라진다. **안에서 하는 일은 한 줄도 바꾸지 않았고**,
회귀 테스트 `test_user_deleted_stops_trading.py` 를 새 엔드포인트로 재조준한 것이 이 단위의 수용 기준이다.

### D7. geo-block L3 을 처음으로 실재하게 만든다

★★**L3 은 한 번도 발화한 적이 없었다.** `auth/service.py:_extract_country` 는 Clerk webhook 의
`public_metadata.country` 를 읽었는데 **그 값을 넣는 코드가 `apps/web` 어디에도 없었다**(grep 0건).
테스트는 페이로드를 자기가 만들어 초록이었다. Better Auth 는 Next 안에서 돌아 가입 요청의
`CF-IPCountry` 를 **직접 본다** — `databaseHooks.user.create.before` 가 정문이고, 백엔드는 JWT
payload 의 `country` 로 첫 프로비저닝 시점에 백스톱을 둔다.

### D8. 이번 회차 인증 방식은 이메일 + 비밀번호 하나다

`requireEmailVerification: false` 로 시작한다 — Resend 도메인 검증(사용자 수동)이 배포를
막지 않게 하기 위해서다. 검증 메일·매직링크·소셜은 [BL-072] 와 함께 켠다.

### D9. 사용자 2명은 CSV 대량 이관을 하지 않는다

공식 Clerk 마이그레이션 가이드는 CSV export + 스크립트이고 「모든 세션이 무효화된다」고 명시한다.
우리는 실사용자 2명(데이터 보유 1명)이고 `users.email` 이 **2행 모두 NULL** 이라 Clerk 밖에
identity 가 없다. ⇒ 새로 가입한 뒤 그 `sub` 를 기존 행에 잇는다 —
`apps/api/scripts/link_auth_subject.py`(기본 dry-run, `--confirm` 이 집행).

## 대가 (숨기지 않는다)

| 축                  | 이전 (Clerk)                                | 이후 (Better Auth)                                        |
| ------------------- | ------------------------------------------- | --------------------------------------------------------- |
| 로그인 UI           | `<SignIn/>` 프리빌트                        | **우리가 만든다** — 프리빌트 컴포넌트가 없다              |
| MFA · 소셜 · 패스키 | 대시보드 토글                               | 플러그인 배선이 필요하다 (이번 회차 범위 밖)              |
| 비밀번호 유출 대응  | 공급자가 처리                               | **우리 책임** (`haveibeenpwned` 플러그인이 있으나 미배선) |
| 가용성              | 공급자 SLA                                  | FE 컨테이너가 죽으면 로그인도 죽는다                      |
| 백엔드 시크릿       | `CLERK_SECRET_KEY` × (API + 워커 4)         | **0개** — 공개 키 검증                                    |
| 빌드 의존           | CI 가 `NEXT_PUBLIC_CLERK_*` secret 2종 필요 | **0개**                                                   |
| 비용                | 사용자 수에 따라 증가                       | 0 (같은 호스트)                                           |

## 기각한 대안

| 안                              | 기각 사유                                                                                                          |
| ------------------------------- | ------------------------------------------------------------------------------------------------------------------ |
| Clerk production 인스턴스 승격  | 원래 계획이었고 기술적으로 가장 싸다. 사용자 결정으로 기각 — 공개 전환이 곧 신원의 영구 위탁이다                   |
| Better Auth 를 별도 Node 서비스 | 문서상 지원된다(클라이언트 `baseURL` 원격). FE 컨테이너에 DB 를 안 줘도 되지만 운영 표면이 하나 는다 → D1 ⑴로 대체 |
| FastAPI 에 인증을 직접 구현     | 세션·해싱·토큰 회전·이메일 흐름을 전부 짓는다. 사용자 지시가 Better Auth 였고, 직접 구현이 더 안전할 근거가 없다   |
| Better Auth 를 ES256 으로 낮춤  | `python-jose` 를 남길 수 있다. 얻는 것이 없고 라이브러리 기본값에서 벗어난다 → D4 로 대체                          |

## 되돌리기

`git revert` + `alembic downgrade -1` 이면 컬럼 이름과 테이블 5개가 돌아간다. 단
**사용자는 다시 로그인해야 한다**(세션 체계가 다르다). Clerk 계정은 이 회차에 삭제하지 않았으므로
구 `auth_subject` 값이 남아 있는 동안에는 되돌리기가 실제로 성립한다 —
★**Clerk 애플리케이션을 지우기 전에 이 문장을 다시 읽어라.**

## 출처

- Better Auth 공식 문서(`https://www.better-auth.com/docs`) — Next 통합 · JWT 플러그인 · DB 개념 ·
  쿠키 · 옵션 레퍼런스 · Clerk 마이그레이션 가이드.
- 버전·peerDependency 는 npm 레지스트리 실측(`better-auth@1.6.29`, 2026-08-14 발행).
- ★가격·기능 서술에는 유효기간이 있다. 대안을 재판정할 때 다시 확인해라.
