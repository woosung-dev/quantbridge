# QuantBridge — 환경 변수 카탈로그

> **목적:** 환경 변수의 의미·획득법·필수 시점 가이드.
> **SSOT:** [`../../.env.example`](../../.env.example) — 본 문서와 충돌 시 `.env.example` 우선.

---

## 1. 기본 원칙

- 모든 환경 변수는 `.env.local` (로컬) 또는 배포 플랫폼 대시보드에서 관리
- 코드에 하드코딩 **절대 금지** (CLAUDE.md Golden Rule)
- 민감 값은 백엔드에서 `SecretStr` 타입으로 선언 (`.ai/stacks/fastapi/backend.md` §2)
- `.env.example`에 없는 변수를 코드에서 참조 금지 (Golden Rule)

### 범례

| 마킹 | 의미 |
|------|------|
| `[필수 Sprint N]` | 해당 sprint부터 실값 필요 |
| `[선택]` | 기본값으로 동작, 고급 설정 시 변경 |
| `[기본값 OK]` | 로컬 개발은 기본값 그대로 사용 |
| `[자동]` | docker-compose가 자동 주입 |

---

## 2. 앱 설정

| 변수 | 마킹 | 설명 |
|------|------|------|
| `APP_NAME` | [기본값 OK] | 표시명 |
| `APP_ENV` | [선택] | `development` / `staging` / `production` |
| `DEBUG` | [선택] | true 시 디버그 로그/리로드 활성 |
| `SECRET_KEY` | [기본값 OK] (프로덕션은 실값) | 세션/토큰 서명. 프로덕션은 `openssl rand -hex 32` |

---

## 3. Clerk 인증 (Sprint 3+)

| 변수 | 마킹 | 설명 / 획득법 |
|------|------|----------------|
| `CLERK_SECRET_KEY` | [필수 Sprint 3] | Clerk Dashboard → API Keys → Secret keys (`sk_test_...`) |
| `CLERK_PUBLISHABLE_KEY` | [필수 Sprint 5 FE] | Clerk Dashboard → API Keys → Publishable keys (`pk_test_...`). 백엔드는 미사용 |
| `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` | [필수 Sprint 5 FE] | 위와 동일 값. Next.js 노출 prefix `NEXT_PUBLIC_*` 필수 |
| `CLERK_WEBHOOK_SECRET` | [필수 Sprint 7] | Webhook 엔드포인트 등록 후 발급되는 `whsec_...`. 로컬/CI는 placeholder OK (테스트는 mock 서명) |

상세 셋업: [`clerk-setup.md`](./clerk-setup.md).

---

## 4. 데이터베이스 (Sprint 3+)

| 변수 | 마킹 | 설명 |
|------|------|------|
| `POSTGRES_USER` | [자동] | docker-compose 자동. compose 외부면 명시 필요 |
| `POSTGRES_PASSWORD` | [자동] | 동일. 로컬 전용 비밀번호 |
| `POSTGRES_DB` | [자동] | 기본 `quantbridge` |
| `DATABASE_URL` | [기본값 OK] | `postgresql+asyncpg://...`. asyncpg 드라이버 필수 |

> TimescaleDB extension은 동일 DB의 `ts` schema에서 사용 (Sprint 5 M2~). 별도 URL 불필요 — `TIMESCALE_URL` 항목은 제거되었음.
> 테스트는 별도 DB `quantbridge_test` 사용. `pytest conftest`가 `DATABASE_URL` 우선.

---

## 5. Redis / Celery (Sprint 4+)

| 변수 | 마킹 | 설명 |
|------|------|------|
| `REDIS_URL` | [기본값 OK] | DB 0 — 캐시 |
| `CELERY_BROKER_URL` | [기본값 OK] | DB 1 — Celery 큐 |
| `CELERY_RESULT_BACKEND` | [기본값 OK] | DB 2 — Celery 결과 |

Redis maxmemory 정책은 compose 파일 (`--maxmemory 512mb --maxmemory-policy allkeys-lru`) 참조.

---

## 6. Backtest (Sprint 4)

| 변수 | 마킹 | 설명 |
|------|------|------|
| `BACKTEST_STALE_THRESHOLD_SECONDS` | [기본값 OK] | RUNNING/CANCELLING 자동 reclaim 임계 (기본 1800s = 30분). Beat 5분 주기 + worker_ready hook 이중 안전망 |
| `OHLCV_FIXTURE_ROOT` | [기본값 OK] | FixtureProvider가 OHLCV CSV 로드하는 경로 |
| `OHLCV_PROVIDER` | [기본값 OK] | `fixture`(기본) \| `timescale`. Sprint 5 M3 도입 — `timescale` 시 CCXT + TimescaleDB cache 사용 |

---

## 7. 암호화 (Sprint 7+ 거래소 연동)

| 변수 | 마킹 | 설명 |
|------|------|------|
| `ENCRYPTION_KEY` | [기본값 OK] (프로덕션 실값) | AES-256-GCM 32-byte. 거래소 API Key 암호화. 프로덕션은 `openssl rand -hex 32` |

> 프로덕션 키 회전 시 데이터 마이그레이션 필요 — Sprint 7+ 절차 정의 예정.

---

## 8. CORS / URL

| 변수 | 마킹 | 설명 |
|------|------|------|
| `FRONTEND_URL` | [기본값 OK] | 백엔드 CORS allowlist |
| `NEXT_PUBLIC_API_URL` | [기본값 OK] | Frontend → Backend HTTP base URL |
| `NEXT_PUBLIC_WS_URL` | [기본값 OK] | Frontend → Backend WebSocket base URL (Sprint 7+) |

---

## 9. 거래소 (Sprint 7+)

| 변수 | 마킹 | 설명 |
|------|------|------|
| `DEFAULT_EXCHANGE` | [기본값 OK] | `bybit` / `binance` / `okx` |

> 거래소별 API Key는 환경 변수가 아니라 사용자별 `exchange_accounts` 테이블에 AES-256 암호화 저장.

---

## 10. 환경별 차이 (현재/계획)

| 환경 | 상태 | 비고 |
|------|------|------|
| local | ✅ 운영 중 | docker-compose + uvicorn + pnpm dev |
| staging | ⏳ 미정 | 배포 전략 결정 후 (`07_infra/deployment-plan.md`) |
| production | ⏳ 미정 | 동일 |

> staging/prod는 `[확인 필요]` — 결정 시 본 문서에 환경별 컬럼 추가.

---

## 11. Secret 관리 원칙

> `.ai/common/global.md` §4 인용.

- **하드코딩 금지** — 모든 키는 환경 변수
- **`SecretStr` 타입** — 백엔드 코드는 Pydantic Settings의 `SecretStr` 사용, `.get_secret_value()`로만 접근
- **AES-256 암호화** — 거래소 API Key는 DB 저장 시 평문 금지
- **`.env.local` 절대 커밋 금지** — `.gitignore`에 등록됨
- **로그에 secret 노출 금지** — `repr(SecretStr)` 사용 시 마스킹됨

---

## 12. 변수 추가 절차

1. `.env.example`에 추가 (의미·필수 시점·획득법 주석 포함)
2. 본 문서 카탈로그 업데이트
3. 백엔드: `backend/src/core/config.py` Settings 클래스에 필드 추가 (`SecretStr` 여부 결정)
4. 프론트: `NEXT_PUBLIC_*` prefix 필요 시 명시
5. 코드 변경과 같은 PR로 묶어 커밋

---

## 변경 이력

- **2026-04-16** — 초안 작성 (Sprint 5 Stage A, `.env.example` 기반)
