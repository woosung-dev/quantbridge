# Geo-block Setup Runbook (Sprint 11 Phase A)

> **Created:** 2026-04-25 (H2 Sprint 11 Phase A)
> **Owner:** 본인
> **Depends on:** Cloudflare (WAF Free plan) · Better Auth 가입 훅 ([ADR-034](../../adr/034-auth-self-host-better-auth.md))

QuantBridge Beta 는 아시아 태평양 지역에서만 제공. US/EU 차단을 **3 계층 방어**로 구현한다.

| 계층   | 위치                             | 메커니즘                                                              | 우회 가능성          | 관리                   |
| ------ | -------------------------------- | --------------------------------------------------------------------- | -------------------- | ---------------------- |
| **L1** | Cloudflare WAF (Edge)            | IP geolocation 기반 block                                             | 낮음 (VPN 가능)      | 수동 설정 (본 runbook) |
| **L2** | Next.js `proxy.ts`               | CF-IPCountry / X-Vercel-IP-Country header redirect                    | 중간 (header 스푸핑) | 코드 자동              |
| **L3** | Better Auth 가입 훅 + API 백스톱 | `CF-IPCountry` → 가입 거부 · JWT `country` → `GeoBlockedCountryError` | 낮음 (서버-서버)     | 코드 자동              |

---

## L1: Cloudflare WAF Custom Rule

### 전제

- Cloudflare 무료 요금제로 충분 (Custom WAF Rule 5개 허용, 본 사례 1개만 사용).
- DNS 가 Cloudflare 를 통해 proxied 되어야 함 (orange cloud 🟠).

### 설정 절차

1. Cloudflare Dashboard(https://dash.cloudflare.com/) → `woosung.dev` → **Security** → **WAF**
   → **Custom rules** → **Create rule**. Expression 은 **Edit expression** 으로 텍스트 모드에서 붙여넣는다.
2. Rule name: `QuantBridge — US/EU geo block`
3. Expression (Edit in Expression Editor):
   ```
   (ip.geoip.country in {"US" "GB" "AT" "BE" "BG" "HR" "CY" "CZ" "DK" "EE" "FI" "FR" "DE" "GR" "HU" "IE" "IT" "LV" "LT" "LU" "MT" "NL" "PL" "PT" "RO" "SK" "SI" "ES" "SE"}) and (http.request.uri.path ne "/not-available") and (not starts_with(http.request.uri.path, "/api/webhooks/"))
   ```
4. **Action:** `Block`.
5. Deploy.

### 우회 테스트 (실측)

```bash
# 정상 KR (예상 200)
curl -I -H "CF-IPCountry: KR" https://qb.woosung.dev/

# 차단 US (예상 403 from Cloudflare)
curl -I -H "CF-IPCountry: US" https://qb.woosung.dev/

# /not-available 은 통과
curl -I -H "CF-IPCountry: US" https://qb.woosung.dev/not-available
```

> **참고:** Cloudflare 는 클라이언트 TCP 연결의 실 IP 로 geolocation 을 판단. `CF-IPCountry` 헤더는 edge 에서 덧붙는 결과물이라 curl 로는 완전한 재현 어려움. 실제 우회 테스트는 VPN 사용.

---

## L0(선행): Cloudflare Access 제거 — 공개 전환

★**Access 가 걸려 있는 동안은 L1 을 시험할 수 없다** — 모든 요청이 OTP 화면에서 멈춘다.
Zero Trust(https://one.dash.cloudflare.com/) → **Access** → **Applications** → `qb.woosung.dev`
→ **Delete**. ★**정책만 지우지 마라** — 앱이 남아 있으면 계속 막는다.
★**`qb-api.woosung.dev` 에는 걸지 마라**(걸려 있으면 함께 제거) — Access 는 브라우저
리다이렉트로 인증하는데 XHR 도 FE 컨테이너의 SSR 헤어핀도 그것을 못 따라간다. API 의 문은
Bearer JWT 다(`frontend-deploy.md` §2).

확인: 시크릿 창에서 `https://qb.woosung.dev` → OTP 없이 로그인 페이지가 떠야 한다.

---

## L2: Next.js `proxy.ts`

Next.js 16 App Router 에서는 `proxy.ts` (기존 `middleware.ts` 후속) 에서 geo header 기반 redirect 구현. Sprint 11 Phase A 에서 `apps/web/src/proxy.ts` 에 추가됨 (`isRestrictedCountry` 호출).

### 동작

- Cloudflare: `CF-IPCountry` 헤더 자동 주입 (orange cloud 경유).
- Vercel Deploy: `X-Vercel-IP-Country` 헤더 자동 주입.
- 두 헤더 중 하나라도 restricted → `/not-available` 리다이렉트 (302).
- 공개/webhook 경로 (`/`, `/not-available`, `/api/webhooks/*`) 는 예외.

### 검증

```bash
pnpm dev
curl -I -H "CF-IPCountry: US" http://localhost:3000/strategies
# 예상: 302 Location: /not-available
```

---

## L3: 가입 훅 — `country_code` 저장 + 차단 (★2026-08-17 [ADR-034] 로 실재하게 됐다)

★★**2026-08-17 실측 — 이 계층은 그때까지 한 번도 발화한 적이 없다.**
종전 L3 는 Clerk webhook 의 `public_metadata.country` 를 읽었는데, 그 값을 **넣는 코드가
`apps/web` 어디에도 없었다**(grep 0건). 아래 「추천 구현」 코드 블록이 문서에만 있고 코드에
없었던 것이다. 백엔드 테스트는 페이로드를 자기가 만들어 초록이었다 —
`apps/api/AGENTS.md` §10「가드는 **그 경로가 지나는가**로 재라」의 교과서적 사례다.

지금은 인증 서버가 우리 Next 앱 안에 있어서 **가입 요청의 헤더를 직접 본다.**

### 정문 — Better Auth 가입 훅 (`apps/web/src/lib/auth.ts`)

`databaseHooks.user.create.before` 가 `CF-IPCountry`(없으면 `X-Vercel-IP-Country`)를 읽어
`isRestrictedCountry()` 면 **`false` 를 돌려 계정 생성 자체를 막는다.** 통과하면 그 값을
`auth_user.country` 에 적고, JWT `definePayload` 가 `country` 클레임으로 싣는다.

### 백스톱 — FastAPI 첫 프로비저닝 (`apps/api/src/auth/service.py::get_or_create`)

JWT payload 의 `country` 를 2자리로 정규화해 `RESTRICTED_COUNTRIES`(US + EU 27 + GB) 면
`GeoBlockedCountryError` → 400 `geo_blocked_country`. 통과하면 `users.country_code` 에 저장.

★**차단은 최초 프로비저닝 시점뿐이다.** 이미 있는 사용자는 국가로 쫓아내지 않는다(정책 유지).
★**국가를 모르는 토큰은 차단하지 않는다.** 헤더 없는 로컬 개발과 기존 사용자를 막으면 이 계층이
「전건 차단」이 되어 판별력이 0 이 된다 — 회귀 테스트가 그 음성 대조를 들고 있다
(`tests/auth/test_country_code_validation.py`).

---

## Monitoring

### Grafana Cloud — geo 차단 카운터 (follow-up)

Sprint 11 Phase A 는 metric 을 추가하지 않음. 후속 Phase/Sprint 에서:

- `qb_geo_block_redirect_total{layer="L2", country}` — proxy.ts 에서 redirect 발생
- `qb_geo_block_rejected_total{layer="L3", country}` — webhook 에서 400 응답

추가 시 `apps/api/src/common/metrics.py` 확장.

---

## Rollback

### L1 (Cloudflare)

Custom rule 을 **Disable** 토글. DNS / 트래픽 영향 없음.

### L2 (proxy.ts)

`apps/web/src/proxy.ts` 에서 geo check 블록 제거 + redeploy. 또는 `isRestrictedCountry` 상시 `false` 반환하도록 hotfix.

### L3 (가입 훅 + API 백스톱)

`apps/web/src/lib/auth.ts` 의 `databaseHooks.user.create.before` 에서 차단 분기를 제거(정문)하고,
`apps/api/src/auth/service.py::get_or_create` 의 `GeoBlockedCountryError` raise 조건을 함께 푼다(백스톱).
★두 곳 다 풀어야 한다 — 한쪽만 풀면 가입은 되는데 첫 API 호출에서 400 이 난다.

모든 계층 동시 롤백은 정책 변경 (Beta scope 확장) 시에만.

---

## H2 말 확장 — Asia-Pacific allow list 재확인

H2 말 (~2026-06-30) 정식 법무 검토 시점에 `RESTRICTED_COUNTRIES` 목록을 재검증. 특히:

- **홍콩 (HK)** — 중국 특수 지위 재검토 필요
- **러시아 (RU)** — 제재 상황 반영
- **이란/북한** — OFAC 이중 확인

그 전까지 Phase A 목록 그대로 유지.
