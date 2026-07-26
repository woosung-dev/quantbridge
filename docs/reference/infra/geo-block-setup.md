# Geo-block Setup Runbook (Sprint 11 Phase A)

> **Created:** 2026-04-25 (H2 Sprint 11 Phase A)
> **Owner:** 본인
> **Depends on:** Cloudflare (WAF Free plan) · Clerk · Vercel (or Cloudflare Pages)

QuantBridge Beta 는 아시아 태평양 지역에서만 제공. US/EU 차단을 **3 계층 방어**로 구현한다.

| 계층   | 위치                                 | 메커니즘                                                  | 우회 가능성                 | 관리                   |
| ------ | ------------------------------------ | --------------------------------------------------------- | --------------------------- | ---------------------- |
| **L1** | Cloudflare WAF (Edge)                | IP geolocation 기반 block                                 | 낮음 (VPN 가능)             | 수동 설정 (본 runbook) |
| **L2** | Next.js `proxy.ts`                   | CF-IPCountry / X-Vercel-IP-Country header redirect        | 중간 (header 스푸핑)        | 코드 자동              |
| **L3** | Clerk webhook (`POST /auth/webhook`) | `public_metadata.country` 검증 + `GeoBlockedCountryError` | 낮음 (서명검증된 서버-서버) | 코드 자동              |

---

## L1: Cloudflare WAF Custom Rule

### 전제

- Cloudflare 무료 요금제로 충분 (Custom WAF Rule 5개 허용, 본 사례 1개만 사용).
- DNS 가 Cloudflare 를 통해 proxied 되어야 함 (orange cloud 🟠).

### 설정 절차

1. Cloudflare Dashboard → 대상 도메인 → **Security** → **WAF** → **Custom rules** → **Create rule**.
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
curl -I -H "CF-IPCountry: KR" https://quantbridge.ai/

# 차단 US (예상 403 from Cloudflare)
curl -I -H "CF-IPCountry: US" https://quantbridge.ai/

# /not-available 은 통과
curl -I -H "CF-IPCountry: US" https://quantbridge.ai/not-available
```

> **참고:** Cloudflare 는 클라이언트 TCP 연결의 실 IP 로 geolocation 을 판단. `CF-IPCountry` 헤더는 edge 에서 덧붙는 결과물이라 curl 로는 완전한 재현 어려움. 실제 우회 테스트는 VPN 사용.

---

## L2: Next.js `proxy.ts`

Next.js 16 App Router 에서는 `proxy.ts` (기존 `middleware.ts` 후속) 에서 geo header 기반 redirect 구현. Sprint 11 Phase A 에서 `frontend/src/proxy.ts` 에 추가됨 (`isRestrictedCountry` 호출).

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

## L3: Clerk webhook — `country_code` 저장 + 차단

`backend/src/auth/service.py::handle_clerk_event` 가 `user.created` 이벤트 수신 시:

1. `public_metadata.country` 추출 → 2 자리 ISO 3166-1 alpha-2 정규화.
2. `RESTRICTED_COUNTRIES` (US + EU 27 + GB) 에 포함 시 `GeoBlockedCountryError(country)` raise → 400 `geo_blocked_country`.
3. 아니면 `users.country_code` 컬럼 저장.

### Clerk Dashboard 연동

Clerk 은 기본적으로 `public_metadata.country` 를 설정하지 않는다. FE signup 플로우에서 명시적으로 주입해야 함.

**추천 구현 (Next.js signup 페이지):**

```typescript
// 가입 완료 전, Clerk SignUp 의 publicMetadata 설정
const country = /* Cloudflare CF-IPCountry 또는 브라우저 geolocation */;
await signUp.update({ publicMetadata: { country } });
```

또는 Clerk webhook 의 secondary enforcement 로 활용 (IP 경로 우회 방지).

### Clerk Sign-up restriction (ideal, 별도 설정)

Clerk Dashboard → **Sign-up & sign-in** → **Restrictions** → country-based allowlist. 아시아 태평양만 허용 (KR, JP, SG, TW, HK, TH, VN, PH, MY, ID, AU, NZ, IN 등).

> **주의:** Clerk 의 country restriction 은 billing tier 에 따라 제공 여부 상이. Free tier 에서는 manual 적용 필요.

---

## Monitoring

### Grafana Cloud — geo 차단 카운터 (follow-up)

Sprint 11 Phase A 는 metric 을 추가하지 않음. 후속 Phase/Sprint 에서:

- `qb_geo_block_redirect_total{layer="L2", country}` — proxy.ts 에서 redirect 발생
- `qb_geo_block_rejected_total{layer="L3", country}` — webhook 에서 400 응답

추가 시 `backend/src/common/metrics.py` 확장.

---

## Rollback

### L1 (Cloudflare)

Custom rule 을 **Disable** 토글. DNS / 트래픽 영향 없음.

### L2 (proxy.ts)

`frontend/src/proxy.ts` 에서 geo check 블록 제거 + redeploy. 또는 `isRestrictedCountry` 상시 `false` 반환하도록 hotfix.

### L3 (Clerk webhook)

`backend/src/auth/service.py` 에서 `GeoBlockedCountryError` raise 조건을 주석 처리. 다음 배포에서 반영.

모든 계층 동시 롤백은 정책 변경 (Beta scope 확장) 시에만.

---

## H2 말 확장 — Asia-Pacific allow list 재확인

H2 말 (~2026-06-30) 정식 법무 검토 시점에 `RESTRICTED_COUNTRIES` 목록을 재검증. 특히:

- **홍콩 (HK)** — 중국 특수 지위 재검토 필요
- **러시아 (RU)** — 제재 상황 반영
- **이란/북한** — OFAC 이중 확인

그 전까지 Phase A 목록 그대로 유지.
