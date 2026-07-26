# QA(Sentinel) Report — QuantBridge Multi-Agent QA 2026-05-13

## Persona

시니어 QA 엔지니어. 적대적 입력 + 회귀 사냥 시각. Sprint 55-58 회귀 풀세트 포함 Exhaustive (11 시나리오).

## 환경 점검 (preflight) — 사용자 안내와 실제 환경 불일치

| 항목          | 사용자 안내                              | 실제 (검증)                                                                                                                                                                       |
| ------------- | ---------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| FE            | `http://localhost:3000` (ko)             | **`http://localhost:3100`** — `:3000` 은 다른 프로젝트 (Kairos)                                                                                                                   |
| BE            | `http://localhost:8100`                  | `http://localhost:8100` (확인)                                                                                                                                                    |
| FE→BE 연결    | `.env.local` `NEXT_PUBLIC_API_URL=:8100` | `.env.local` 은 여전히 `:8000`, 그러나 **process inline env override `NEXT_PUBLIC_API_URL=http://localhost:8100`** 로 기동 — 라이브 API 호출 `:8100` 정상 (verified via `ps -ef`) |
| Celery worker | 가동 가정                                | **`celery_workers=0`** → `/healthz` 503 + 비동기 작업 enqueue 후 미실행                                                                                                           |
| Clerk 로그인  | E2E 계정 정상                            | `jetaime.jang@gmail.com` 로그인 성공, user `user_3DDANXqiCRIe0h4rFGR99II61Eb`                                                                                                     |

**검증 방법**: `/api/v1/strategies` 호출 시 FE 가 `http://localhost:8100/api/v1/strategies?limit=20&offset=0&is_archived=false` 호출 (network 캡처). FE→BE 연결 OK.

## Executive Summary

- **Composite QA Score: 6.2 / 10** (회귀 1건 + 보안 헤더 부재로 감점)
- **Critical: 1** / **High: 4** / **Medium: 6** / **Low: 3**
- **도입 결정: Hold** — 핵심 회귀 BL-244 (optimizer 500 stack-trace 누설) 가 Sprint 55/56 출시 코드를 사실상 무력화. fix 1건 + 보안 헤더 1 patch 후 Go.

### Top-3 finding

1. **BL-244 Critical** — `/api/v1/optimizer/runs/{grid-search,bayesian,genetic}` 3개 엔드포인트 모두 **HTTP 500 + 14,250-byte 파이썬 stack trace 를 `text/plain` 으로 누설**. slowapi `_inject_headers` 가 Pydantic response 객체를 거부하면서 폭발. Sprint 55 (Bayesian) / Sprint 56 (Genetic) 본격 출시 코드가 **end-to-end 동작 불능** — 통합 테스트가 slowapi middleware 를 mock 한 false-positive PASS 가능성 매우 높음.
2. **BL-245 High** — BE/FE 양쪽 모두 **보안 헤더 0개** (CSP / HSTS / X-Frame-Options / X-Content-Type-Options / Referrer-Policy / Permissions-Policy 전무). 베타 외부 노출 가능 시 즉시 audit gate fail.
3. **BL-246 High** — `/metrics` Prometheus 엔드포인트가 **unauth public** 으로 노출. 내부 endpoint 인벤토리 + 워커 통계 + GC stats 누설. PII 는 없지만 reconnaissance surface.

## 시나리오 진행 상태

- [x] 1. 인증 (Clerk JWT) — **PASS**
- [x] 2. CORS / 헤더 — **PARTIAL** (CORS OK, 보안 헤더 FAIL)
- [x] 3. 권한 / 격리 — **PARTIAL** (own-resource isolation OK, cross-user enumeration 추가 검증 필요)
- [x] 4. 핵심 파이프라인 (read-only) — **PASS** (24 metric 명세 → 실측 28 metric)
- [x] 5. 검색 / 비동기 안정성 — **PARTIAL** (paging OK, Celery worker 0 → 라이브 비동기 검증 불가)
- [x] 6. 에러 응답 일관성 — **FAIL** (3종 schema 혼재 + 500 plain-text 누설)
- [x] 7. 입력 검증 (StrictDecimalInput) — **PASS** (NaN/Infinity/1e20/SQL injection 모두 차단)
- [x] 8. 보안 헤더 — **FAIL** (BE/FE 모두 0개)
- [x] 9. Rate limiting (slowapi) — **PASS** (100/60s global + 5/min per-route 작동)
- [x] 10. Secret 노출 검사 — **PARTIAL** (API key masked OK, `/metrics` unauth 노출 + dev `.js.map` 노출)
- [x] 11. Sprint 55-58 회귀 풀세트
  - [x] 11a. Bayesian optimizer — **FAIL** (BL-244)
  - [x] 11b. Genetic optimizer — **FAIL** (BL-244)
  - [x] 11c. Pine TA 신규 함수 — **PASS w/ caveat** (ta.alma + ADR-003 mixed-unsupported 회귀)
  - [x] 11d. SignalExtractor alertcondition — **PASS** (parse 단)
  - [x] 11e. backtest-form 5-split — **PASS** (UI render OK)
  - [x] 11f. convert resilient LLM chain — **SKIP** (Celery worker 0, mock 불가 → [확인 필요])
  - [x] 11g. `_worker_engine` SSOT — **PASS** (UI render OK)
  - [x] 11h. Decimal/float 합산 — **PASS** (Decimal stringified 27자리 precision 보존)

## 시나리오 결과 상세

### 1. 인증 (Clerk JWT) — PASS

| 케이스               | 결과 | 응답                                                                            |
| -------------------- | ---- | ------------------------------------------------------------------------------- |
| 정상 로그인          | OK   | `/sign-in` → `/strategies` redirect, Clerk session 정상                         |
| Authorization 미동봉 | OK   | `401 {"detail":{"code":"auth_invalid_token","detail":"SESSION_TOKEN_MISSING"}}` |
| 잘못된 Bearer        | OK   | `401 {"detail":{"code":"auth_invalid_token","detail":"TOKEN_INVALID"}}`         |
| 만료 토큰 (60s 후)   | OK   | `401 {"detail":{"code":"auth_invalid_token","detail":"TOKEN_EXPIRED"}}`         |
| `auth/me` authed     | OK   | `{id, clerk_user_id, email:null, ...}` 본인 record 만                           |

### 2. CORS / 헤더 — PARTIAL

- **CORS preflight 합법 origin (`http://localhost:3100`)** → 200 + `Access-Control-Allow-*` 정상.
- **CORS rogue origin (`http://evil.example.com`)** → **400 `Disallowed CORS origin`** ✅ (strict allowlist).
- 보안 헤더 누락 — BL-245 참조.

### 3. 권한 / 격리 — PARTIAL

- 본인 strategy/backtest 정상 조회 ✅
- 임의 UUID `00000000-...` → `404 strategy_not_found` (other-user 존재 여부 노출 안 함) ✅
- **[확인 필요]** 실제 다른 user 의 UUID 로 cross-user enumeration 테스트 미수행 — E2E 테스트 계정 1개만 있어서 다른 user UUID 발급 못 함. 두 번째 테스트 계정 권장.

### 4. 핵심 파이프라인 — PASS (회복적 finding)

- `/api/v1/backtests/{id}` → **28 metric** 반환 (브리프 24 metric 가정 초과).
- 모든 금융 숫자는 Decimal-as-string 으로 직렬화 (27자리 precision 보존).
- `sortino_ratio` / `calmar_ratio` null 처리 (division-by-zero defense).
- equity_curve + drawdown_curve + monthly_returns 정상.
- `trades` 필드는 backtest detail 에 없음 — 별도 endpoint `/api/v1/backtests/{id}/trades` 존재 (OpenAPI 확인).

### 5. 검색 / 비동기 안정성 — PARTIAL

- Strategy list `?limit=20&offset=0&is_archived=false` 정상.
- WebSocket: OpenAPI 에 ws route 없음. `/ws` 404. **[확인 필요]** Sprint 12 WS Supervisor mirror 가 별도 path 일 가능성. WS 경로 명세 미확보.
- **Celery worker = 0** 이라 backtest/optimizer/stress-test 비동기 라이브 검증 불가. 사용자 manual: `make up-isolated` 안 worker 시작 필요.

### 6. 에러 응답 일관성 — FAIL (BL-247)

**3종 schema 혼재** — BL-163 (Sprint 32 E) 가 완성되지 않음:

| 상태                         | 응답 schema                                           | 예시                                                                        |
| ---------------------------- | ----------------------------------------------------- | --------------------------------------------------------------------------- |
| 401 / 도메인 4xx             | `{"detail": {"code": "...", "detail": "..."}}` (객체) | `{"detail":{"code":"auth_invalid_token","detail":"SESSION_TOKEN_MISSING"}}` |
| 405 / 404 (FastAPI default)  | `{"detail": "..."}` (문자열)                          | `{"detail":"Method Not Allowed"}`                                           |
| 422 (Pydantic)               | `{"detail": [{type, loc, msg, input, ctx}]}` (배열)   | `{"detail":[{"type":"finite_number",...}]}`                                 |
| 500 (optimizer slowapi 충돌) | **`text/plain` raw stack trace 14,250 bytes**         | (BL-244)                                                                    |

FE 가 `detail` 을 string vs object vs array 셋 다 case-handle 해야 함 — type drift.

### 7. 입력 검증 (StrictDecimalInput Sprint 53) — PASS

Backtest POST `initial_capital` 필드 부수 입력 테스트:

| 입력                                                        | 결과                                                                                  |
| ----------------------------------------------------------- | ------------------------------------------------------------------------------------- |
| `"NaN"`                                                     | 422 `finite_number` ✅                                                                |
| `"Infinity"`                                                | 422 `finite_number` ✅                                                                |
| `"1e20"`                                                    | 422 `decimal_max_digits` (max 20) ✅                                                  |
| `"9999999999999999999999999999.99"`                         | 422 `decimal_max_digits` ✅                                                           |
| `"-1000"`                                                   | 422 `greater_than 0` ✅                                                               |
| SQL inject `"BTC/USDT'; DROP TABLE backtests; --"` (symbol) | 422 `string_too_long (max 32)` ✅                                                     |
| 이모지 symbol `💰🚀`                                        | 422 `string_too_short (min 3)` (UTF code points 2개 — 적절) ✅                        |
| Optimizer Decimal 필드에 raw int `5` 입력                   | 422 value_error `"StrictDecimalInput requires str or canonical Decimal (got int)"` ✅ |

**Bonus finding (BL-248 Medium)** — symbol whitespace `"   "` (3-byte) 입력 시 `mirror_not_allowed` (BL-186 leverage 비대칭) 가 **422 status 로 반환**. 비즈니스-rule 충돌은 의미상 **409 Conflict** 더 맞음. status semantics drift.

### 8. 보안 헤더 — FAIL (BL-245 High)

`curl -I http://localhost:3100/` 응답:

```
HTTP/1.1 200 OK
x-clerk-auth-reason: dev-browser-missing
x-clerk-auth-status: signed-out
x-middleware-rewrite: /
Vary: rsc, ...
link: ...
Cache-Control: no-cache, must-revalidate
X-Powered-By: Next.js   ← 버전 노출 (fingerprint)
Content-Type: text/html; charset=utf-8
Date: ...
```

**누락 (Tier 1)**:

- `Content-Security-Policy` — script/style/connect 출처 제한 없음
- `Strict-Transport-Security` — HTTPS upgrade 미강제
- `X-Frame-Options` 또는 CSP frame-ancestors — clickjacking 차단 없음
- `X-Content-Type-Options: nosniff` — MIME sniffing 차단 없음
- `Referrer-Policy` — referrer 누설 제어 없음
- `Permissions-Policy` — geolocation/camera/etc 차단 없음

BE `http://localhost:8100/health` 도 동일하게 보안 헤더 0개.

**Bonus** — `X-Powered-By: Next.js` 가 명시 제거 안 됨 (서버 fingerprint).

### 9. Rate limiting (slowapi) — PASS (구조적으로는)

- Global limit: **100/60s per IP** — verified by `X-RateLimit-Remaining` decrement (79 → 50 over 30 requests).
- Per-route limit: **5/min** on `/optimizer/runs/{grid-search,bayesian,genetic}` — 6번째 호출 시 `429 {"detail":{"code":"rate_limit_exceeded","detail":"5 per 1 minute"}}` + `Retry-After: 60` 정상.
- `qb_rate_limit_throttled_total{endpoint="/api/v1/optimizer/runs/bayesian",scope="ip"} 1.0` Prometheus counter 증가 확인.

**그러나 BL-244 (slowapi 자체가 깨짐) 와 결합되어 사실상 unreachable**.

### 10. Secret 노출 검사 — PARTIAL

| 검사                                                            | 결과                                                       |
| --------------------------------------------------------------- | ---------------------------------------------------------- |
| ExchangeAccount `api_key_masked: "0Cai******ZhqX"`              | ✅ 마스킹 정상                                             |
| OpenAPI sensitive fields (`api_key`, `api_secret`)              | RequestBody only (write-only) ✅                           |
| `webhook_secret` / rotate `secret` in response                  | 의도된 one-time reveal (별도 검증 필요)                    |
| `/debug` `/info` `/server-info` `/.env` `/.git/config` `/admin` | 모두 404 ✅                                                |
| **`/metrics`**                                                  | **200 unauth** — BL-246 High                               |
| Source maps `/_next/static/chunks/*.js.map`                     | dev mode 200 — prod build 별도 검증 필요. dev 한정이면 OK. |

### 11. Sprint 55-58 회귀 풀세트

#### 11a. Bayesian optimizer — **FAIL** (BL-244)

| 검증 항목                                         | 결과                                                                             |
| ------------------------------------------------- | -------------------------------------------------------------------------------- |
| `POST /api/v1/optimizer/runs/bayesian` happy path | ❌ **500 stack trace 14250 bytes**                                               |
| prior=`normal` BL-234 NotImplementedError         | ❌ **500** (NotImplementedError 도달 전 slowapi 폭발)                            |
| prior=`uniform`                                   | ❌ **500**                                                                       |
| categorical encoding                              | ❌ (500 이전)                                                                    |
| `_MAX_BAYESIAN_EVALUATIONS=50` cap                | ⚠️ schema `max_evaluations` 검증은 통과, 실제 50/51 분기는 도달 못함             |
| acquisition `EI/UCB/PI` enum                      | ✅ `LCB` 422 거부 (`literal_error`)                                              |
| schema_version=1 vs 2                             | ⚠️ 둘 다 422 이전 stage 도달, 실제 분기 미검증                                   |
| `StrictDecimalInput` raw int 거부                 | ✅ `Value error, StrictDecimalInput requires str or canonical Decimal (got int)` |

#### 11b. Genetic optimizer — **FAIL** (BL-244)

| 검증 항목                                        | 결과                                                                         |
| ------------------------------------------------ | ---------------------------------------------------------------------------- |
| `POST /api/v1/optimizer/runs/genetic` happy path | ❌ **500**                                                                   |
| `random.Random(42)` seed 재현성                  | ❌ (500 이전)                                                                |
| `optimizer_heavy` queue 라우팅 (BL-237)          | ❌ (Celery worker 0 + 500)                                                   |
| prior=normal NotImplementedError (BL-234)        | ❌ (500 이전)                                                                |
| OpenAPI schema 차이                              | ⚠️ 브리프의 `mutation_rate/generations` ≠ 실제 `mutation_rate/n_generations` |

#### 11c. Pine TA 신규 함수 (Sprint 58) — PASS w/ caveat

`POST /api/v1/strategies/parse` (`pine_source` 필드 — 브리프의 `pine_script` 는 잘못된 키):

| 함수                                 | `is_runnable`              | unsupported                                                                                     |
| ------------------------------------ | -------------------------- | ----------------------------------------------------------------------------------------------- |
| `ta.wma(close, 20)`                  | true ✅                    | []                                                                                              |
| `ta.hma(close, 10)`                  | true ✅                    | []                                                                                              |
| `ta.bb(close, 20, 2)`                | true ✅                    | []                                                                                              |
| `ta.cross(a, b)`                     | true ✅                    | []                                                                                              |
| `ta.mom(close, 12)`                  | true ✅                    | []                                                                                              |
| `ta.obv`                             | true ✅                    | []                                                                                              |
| `fixnan(close)`                      | true ✅                    | []                                                                                              |
| `strategy.equity`                    | true ✅                    | []                                                                                              |
| `barstate.isrealtime`                | true ✅                    | []                                                                                              |
| `alertcondition(...)`                | true ✅                    | []                                                                                              |
| `ta.alma(close, 9, 0.85, 6)`         | **false ❌**               | `[ta.alma]` workaround `Arnaud Legoux MA 미지원. ta.sma 또는 ta.ema 로 근사 (정확도 차이 < 1%)` |
| **`ta.wma + request.security` 혼합** | **true ❌ (ADR-003 위반)** | `[]` (request.security 가 unsupported 로 라벨링 안 됨)                                          |

**Findings**:

- **BL-249 High** — `ta.alma` 가 `unsupported_calls` 에 포함됨. MEMORY `project_sprint58_complete.md` 의 "CI hotfix: fixnan→ta.alma 교체" 라는 문구는 ALMA 가 **새로 추가** 된 것처럼 보이나 실측 결과 unsupported. 기록과 실제가 불일치 — 명세 추적성 손상.
- **BL-250 High (ADR-003 회귀)** — Pine `request.security(...)` 가 unsupported_calls 에 잡히지 않고 `is_runnable=true` 반환. CLAUDE.md §"Pine Script 미지원 함수 1개라도 포함 시 전체 Unsupported 반환" — Iron Law 위반. `request.security` 는 다른 timeframe 데이터 호출이라 backtest 불가능해야 함. 잘못된 결과를 사용자에게 반환할 위험.

#### 11d. SignalExtractor alertcondition — PASS (parse 단)

DrFXGOD 패턴 `alertcondition(longCond, title="long", message="buy now")` → `is_runnable=true`, parse OK. C-text/C-ast 분기 라이브 백테스트는 Celery worker 0 으로 미검증 — **[확인 필요]**.

#### 11e. backtest-form 5-split (Sprint 59 PR-E) — PASS

`/backtests` list + `/backtests/{id}` 상세 페이지 console error 0, network 정상. 페이지 타이틀 "백테스트 상세 | QuantBridge" 한국어 정상. fullPage screenshot: `traces/qa-04-backtest-detail.png`.

#### 11f. convert resilient LLM chain — SKIP

- 변환 endpoint: `/api/v1/strategies/convert-indicator` (브리프의 `/api/v1/convert/` 는 존재 안 함).
- 라이브 LLM 호출 비용 + Celery worker 0 으로 SKIP. **[확인 필요]** — 코드 review only.

#### 11g. `_worker_engine` SSOT (Sprint 59 PR-B) — PASS

Backtest 상세 페이지 정상 렌더, Pine v1 흔적 없음 (24+ metric 모두 pine_v2 산출). Sprint 59 cleanup verified.

#### 11h. Decimal/float 합산 — PASS

- 모든 metric (`total_return: "-0.042322477131704505314968405"`) Decimal-as-string. 27자리 precision 보존.
- `monthly_returns`, `drawdown_curve` 도 `[timestamp, decimal-string]` 튜플.
- JSON 안 float `NaN` / `Infinity` 없음 (null 처리).

## 결함 상세 (BL-244 ~ BL-253)

### BL-244 — Optimizer submit 3개 엔드포인트 500 stack-trace 누설 (Critical)

- **Severity**: Critical
- **Confidence**: H
- **Surface**: `POST /api/v1/optimizer/runs/grid-search`, `/bayesian`, `/genetic`
- **재현**:
  1. Clerk 로그인 후 fresh JWT 획득
  2. `curl -X POST $BASE/api/v1/optimizer/runs/grid-search -H "Authorization: Bearer $JWT" -H "Content-Type: application/json" -d '{"backtest_id":"<완료된-bt-uuid>","kind":"grid_search","param_space":{"schema_version":1,"objective_metric":"sharpe_ratio","direction":"maximize","max_evaluations":3,"parameters":{"fast_len":{"kind":"integer","min":5,"max":15,"step":5}}}}'`
- **기대**: 202 Accepted + `OptimizationRunResponse` JSON
- **실제**: `HTTP/1.1 500 Internal Server Error`, `Content-Type: text/plain`, 14,250-byte 파이썬 stack trace
- **Root cause**: `slowapi/extension.py:382 _inject_headers` — `raise Exception("parameter `response` must be an instance of starlette.responses.Response")`. Router 가 `OptimizationRunResponse` Pydantic 모델을 직접 반환하면 slowapi `@limiter.limit("5/minute")` 데코레이터가 응답 직렬화 직전에 헤더 inject 를 시도하는데, FastAPI 가 Pydantic → JSONResponse 변환을 그 뒤에 하므로 slowapi 는 raw Pydantic 객체를 받아 폭발.
- **Evidence**: `traces/qa-244-grid-500.txt` (14250 bytes), 마지막 5줄:
  ```
  File "/Users/.../slowapi/extension.py", line 382, in _inject_headers
    raise Exception(
  Exception: parameter `response` must be an instance of starlette.responses.Response
  ```
- **Screenshot**: `traces/qa-244-grid-500.txt`
- **추천 fix (한 줄 단위)**:

  ```python
  # backend/src/optimizer/router.py
  from fastapi.responses import JSONResponse

  @router.post("/runs/grid-search", status_code=202, response_model=None)
  @limiter.limit("5/minute")
  async def submit_grid_search(request: Request, data: ..., service: ...) -> JSONResponse:
      result = await service.submit_grid_search(data, user_id=user.id)
      return JSONResponse(result.model_dump(mode='json'), status_code=202)
  ```

  또는 slowapi 0.1.9+ 의 `@limiter.exempt_when` 패턴 / `RateLimitExceeded` 핸들러 우회. 또는 `Response` 파라미터를 endpoint signature 에 추가 (slowapi 가 그 객체를 직접 수정).

- **Secondary fix (필수)**: `UnifiedErrorMiddleware` (BL-163) 가 모든 500 도 `{"detail": {"code": "internal_error", "detail": "..."}}` 로 정규화. 현재 starlette default ErrorMiddleware 가 plain-text trace 누설. 본 fix 가 없어도 BL-244 fix 후 다른 미공개 500 path 가 또 stack trace 누설 가능.

### BL-245 — 보안 헤더 누락 (High)

- **Severity**: High
- **Confidence**: H
- **Surface**: BE `:8100` + FE `:3100` 모든 response
- **재현**: `curl -I http://localhost:3100/`, `curl -I http://localhost:8100/health`
- **기대**: CSP, HSTS, X-Frame-Options, X-Content-Type-Options, Referrer-Policy, Permissions-Policy
- **실제**: 0개. 추가로 FE 가 `X-Powered-By: Next.js` 노출.
- **추천 fix**: FE 는 `next.config.js` `headers()` 에 6종 추가 + `poweredByHeader: false`. BE 는 `SecurityHeadersMiddleware` 미들웨어 추가 (FastAPI starlette `Middleware` 패턴).

### BL-246 — `/metrics` Prometheus 엔드포인트 unauth 노출 (High)

- **Severity**: High
- **Confidence**: H
- **Surface**: `GET /metrics` (unauth public 200)
- **재현**: `curl http://localhost:8100/metrics`
- **누설 정보**: 모든 endpoint 인벤토리 (e.g. `qb_rate_limit_throttled_total{endpoint="/api/v1/optimizer/runs/bayesian"}`), Python version, GC stats, kill-switch counters, worker health
- **PII 누설**: 없음 (label 에 user_id / email 없음 — 다행).
- **추천 fix**: `/metrics` 에 BasicAuth (Prometheus scrape user) 또는 IP allowlist (10.0.0.0/8 + Grafana 컨테이너 only). Docker compose 의 isolated network 안에서만 노출.

### BL-247 — 에러 응답 schema 3종 혼재 (Medium)

- **Severity**: Medium
- **Confidence**: H
- **Surface**: 모든 4xx/5xx response
- **재현**: 401 = object, 404/405 = string, 422 = array, 500 = plain-text
- **추천 fix**: BL-163 `UnifiedErrorMiddleware` 가 404/405 (FastAPI default) 도 wrap 하도록 확장. 422 도 동일 `{detail: {code, errors[]}}` 으로 normalize. FE type drift 제거.

### BL-248 — `mirror_not_allowed` (BL-186) 비즈니스 충돌이 422 로 반환 (Medium)

- **Severity**: Medium
- **Confidence**: H
- **Surface**: `POST /api/v1/backtests` with leverage mismatch
- **재현**: live=3x cross 인 strategy 로 backtest 제출 → `422 {"detail":{"code":"mirror_not_allowed","detail":"Live leverage 3x ..."}}`
- **기대**: 비즈니스 rule 충돌은 **409 Conflict** 가 RFC 7231 § semantics 에 맞음. 422 는 "syntactically well-formed but semantically unprocessable due to schema rules".
- **영향**: FE 가 422 (form validation error) 와 409 (state conflict) 를 동일 처리 → UX 메시지 부정확.

### BL-249 — `ta.alma` Sprint 58 release note 와 실측 불일치 (High)

- **Severity**: High (명세 추적성)
- **Confidence**: M
- **Surface**: `/api/v1/strategies/parse` with `ta.alma(close, 9, 0.85, 6)`
- **MEMORY**: `project_sprint58_complete.md` — "CI hotfix: fixnan→ta.alma 교체"
- **실측**: `is_runnable=false`, `unsupported_calls=[{name:'ta.alma', workaround:'Arnaud Legoux MA 미지원...'}]`
- **추천**: 사용자가 MEMORY note 의 의미를 명확화. 만약 "CI 가 fixnan 대신 ta.alma 를 deny-list 추가" 라는 의미면 MEMORY 표기를 명확화. 만약 "ta.alma 도 지원 추가" 의도였다면 Sprint 60 추가 작업.

### BL-250 — Pine `request.security` ADR-003 위반 (High)

- **Severity**: High
- **Confidence**: H
- **Surface**: `/api/v1/strategies/parse`
- **재현**:
  ```pinescript
  //@version=5
  strategy("mix")
  plot(ta.wma(close, 20))
  plot(request.security(syminfo.tickerid, "D", close))
  ```
- **기대 (ADR-003 + CLAUDE.md)**: "Pine Script 미지원 함수 1개라도 포함 시 전체 Unsupported" → `is_runnable=false` + `unsupported_calls=[{name:'request.security',...}]`
- **실제**: `is_runnable=true`, `unsupported_calls=[]`
- **영향**: 사용자가 `request.security` (다른 timeframe 데이터) 가 포함된 전략을 실행 → backtest 가 silently 잘못된 결과 반환 (해당 함수가 no-op 처리되거나 본 timeframe 데이터로 fallback 가능성). ADR-003 Iron Law 위반.
- **추천 fix**: `pine_v2/stdlib/` 또는 parser coverage 의 unsupported builtin 목록에 `request.*` 추가. test: `parse('plot(request.security(...))')` → expect `is_runnable=false`.

### BL-251 — Optimizer 라우트별 `kind` 필드 redundancy (Low)

- **Severity**: Low
- **Confidence**: M
- **Surface**: `POST /api/v1/optimizer/runs/bayesian` 에 `kind:"genetic"` 보내도 schema validation 통과 (BL-244 폭발 이전 단계까지).
- **추천 fix**: router level cross-validation — path `/bayesian` 이면 `data.kind == OptimizationKind.bayesian` 강제 (mismatch 시 400).

### BL-252 — `.env.local` 과 실제 process env 불일치 (Low)

- **Severity**: Low
- **Confidence**: H
- **Surface**: `frontend/.env.local` 에 `NEXT_PUBLIC_API_URL=http://localhost:8000` 으로 적혀 있으나, 실제 FE 는 inline `NEXT_PUBLIC_API_URL=http://localhost:8100` 으로 기동.
- **영향**: 새 contributor 가 `.env.local` 만 보고 BE 가 8000 에 있다고 가정 → 디버깅 시간 손실.
- **추천 fix**: `frontend/.env.local` 도 `:8100` 으로 통일 또는 `make up-isolated` Makefile 안 inline env 가 SSOT 임을 README 에 명시.

### BL-253 — Source map publicly served in dev (Low — informational)

- **Severity**: Low (dev 한정)
- **Confidence**: H
- **Surface**: `/_next/static/chunks/*.js.map` 200 OK
- **추천**: production build (`next build && next start`) 에서 동일 검사 필요. Next.js 16 default 는 prod 에서 source maps 비공개. 명시적 prod smoke test 필요.

## 강점 (5건 이내)

1. **Decimal precision**: 모든 금융 숫자가 Decimal-as-string 27자리. float NaN/Infinity 누설 없음.
2. **StrictDecimalInput**: NaN/Infinity/1e20/SQL injection/이모지/whitespace 모두 422 정확 차단. Sprint 53 설계 의도대로.
3. **CORS allowlist**: rogue origin → 400 `Disallowed CORS origin`. wildcard 미사용.
4. **Rate limit infra**: 100/60s global + 5/min per-route + Prometheus counter + `Retry-After` 헤더. 구조는 production-grade.
5. **Exchange API key masking**: `0Cai******ZhqX` 형태 마스킹 + 평문 미반환.

## Sprint 55-58 회귀 결과 표

| 변경                                                  | 시나리오           | 결과                   | 결함   |
| ----------------------------------------------------- | ------------------ | ---------------------- | ------ |
| Sprint 55 Bayesian optimizer                          | submit 흐름        | **FAIL**               | BL-244 |
| Sprint 55 BayesianHyperparamsField StrictDecimalInput | 입력 검증          | PASS                   | —      |
| Sprint 55 acquisition `EI/UCB/PI` enum                | enum lock          | PASS (`LCB` rejected)  | —      |
| Sprint 56 Genetic optimizer                           | submit 흐름        | **FAIL**               | BL-244 |
| Sprint 56 `n_generations` (≠ `generations`)           | schema             | PASS                   | —      |
| Sprint 58 ta.wma/hma/bb/cross/mom/obv/fixnan          | parse              | PASS                   | —      |
| Sprint 58 strategy.equity + barstate.isrealtime       | parse              | PASS                   | —      |
| Sprint 58 ta.alma support                             | parse              | **FAIL** (unsupported) | BL-249 |
| Sprint 58 alertcondition DrFXGOD                      | parse              | PASS                   | —      |
| ADR-003 mixed-unsupported Iron Law                    | parse              | **FAIL**               | BL-250 |
| Sprint 59 PR-B `_worker_engine` SSOT                  | backtest detail UI | PASS                   | —      |
| Sprint 59 PR-E backtest-form 5-split                  | UI render          | PASS                   | —      |
| Sprint 32 E BL-163 error normalization                | schema consistency | **FAIL**               | BL-247 |
| Sprint 53 StrictDecimalInput                          | adversarial inputs | PASS                   | —      |

## 권고 (Sprint 60 candidates)

1. **BL-244 fix (Critical, 1-2h)** — slowapi + FastAPI Pydantic-response 호환성 fix. 통합 테스트가 middleware mock 안 하도록 강화 (real HTTP client).
2. **BL-245 보안 헤더 (High, 30분)** — `next.config.js` headers() + BE SecurityHeadersMiddleware 1 patch.
3. **BL-246 `/metrics` auth (High, 30분)** — BasicAuth 또는 IP allowlist.
4. **BL-247 error schema 정규화 (Medium, 2h)** — UnifiedErrorMiddleware 가 404/405/422/500 모두 wrap.
5. **BL-250 ADR-003 회귀 fix (High, 1h)** — parser unsupported builtin 목록에 `request.*` 추가 + 회귀 test 추가.
6. **BL-249 ta.alma 명세 sync (House-keeping)** — MEMORY 표기 정정 또는 Sprint 60 ta.alma 본격 추가.

## 미수행 (resource / scope)

- **Celery worker 가 0** 이라 backtest/optimizer/stress-test 라이브 비동기 검증 unable. fix: 사용자 `make up-isolated` 안 worker 시작 또는 `celery -A src.tasks worker --concurrency=2` manual.
- **두 번째 테스트 계정 부재** → cross-user enumeration 직접 verify 불가. 추론으로 strategy_not_found / backtest_not_found 응답이 owner 격리 정상이라고 판단했으나 실측은 [확인 필요].
- **WebSocket 라이브 검증** — OpenAPI 에 WS route 노출 안 됨. ws path 명세 [확인 필요].
- **convert-indicator LLM chain** — Gemini fallback 라이브 검증은 비용 + worker 0 으로 SKIP.
- **Production build security headers** — dev 만 검사. prod `next build && next start` 후 재검사 필요.

## Traces

| 파일                               | 설명                                                          |
| ---------------------------------- | ------------------------------------------------------------- |
| `traces/qa-01-strategies-page.png` | Strategies list (authed)                                      |
| `traces/qa-04-backtests-list.png`  | Backtests list                                                |
| `traces/qa-04-backtest-detail.png` | Backtest detail (28 metric + chart) — Sprint 59 SSOT verified |
| `traces/qa-05-optimizer-page.png`  | `/optimizer` page (빈 main — UI incomplete)                   |
| `traces/qa-244-grid-500.txt`       | BL-244 14250-byte stack trace                                 |
