# H2 Sprint 1 Phase A — Dogfood 초기 검증 SDD

> **작성일:** 2026-04-24  
> **상태:** 계획 확정  
> **목표:** Bybit Demo Trading dogfood 첫 주 기반 세팅 완료 + smoke test PASS + baseline 기록

---

## 배경

Path β Stage 2c 2차 완료(PR #67, Mutation Oracle 8/8 GREEN) 이후 H2 첫 dogfood 세션.  
Bybit Demo Trading API 키 발급 완료. `ExchangeMode.demo` 인프라 완전 구축 상태.  
본 Phase A는 코딩보다 환경 검증과 문서 기록이 핵심.

---

## 전제 조건

- Bybit Demo Trading API 키 발급 완료 (mainnet 계정 → API 관리 → Demo Trading 탭)
- Demo 잔고 충전 완료: Demo Trading 진입 → Asset → Demo USDT 무료 지급 클릭
- `docs/07_infra/h1-testnet-dogfood-guide.md` §2 환경 준비 완독
- `docs/guides/dogfood-checklist.md` §1 시작 전 1회 체크 완료

---

## 태스크 분해

### T1. `.env.example` + `.gitignore` 정합 확인

**파일:** `backend/.env.example`

**갭:**

- Kill Switch 관련 환경변수 4개 + Bybit Demo Key 2개 미등록
- `EXCHANGE_PROVIDER` 누락 (코드에서 참조하지만 example에 없음 → Golden Rule 위반)

**추가 내용:**

```env
# Bybit Demo Trading (실제 값은 .env.demo 별도 파일로 관리 — 커밋 금지)
EXCHANGE_PROVIDER=bybit_futures
BYBIT_DEMO_KEY=
BYBIT_DEMO_SECRET=

# Kill Switch 리스크 관리
KILL_SWITCH_CAPITAL_BASE_USD=10000
KILL_SWITCH_DAILY_LOSS_USD=500
KILL_SWITCH_CUMULATIVE_LOSS_PERCENT=5
BYBIT_FUTURES_MAX_LEVERAGE=1
```

**`.gitignore` 검증 (필수):**

```bash
grep ".env.demo" .gitignore || echo "⚠️  .env.demo NOT in .gitignore — 즉시 추가 필요"
```

**완료 기준:**

```bash
grep "KILL_SWITCH" backend/.env.example | wc -l   # 4 이상
grep "EXCHANGE_PROVIDER" backend/.env.example       # 출력 있어야 함
grep ".env.demo" .gitignore                         # 출력 있어야 함
```

---

### T2. 인프라 사전 점검 (Docker / DB / Redis)

**목적:** trading 스키마 4개 테이블 존재, 마이그레이션 최신, 외부 서비스 연결 정상.

#### 2-a. Docker 서비스 기동

```bash
docker compose up -d
docker compose ps   # 모든 서비스 "running" 확인
```

| 예상 서비스              | 상태                   |
| ------------------------ | ---------------------- |
| quant-bridge-db          | running                |
| quant-bridge-redis       | running                |
| quant-bridge-timescaledb | running (또는 db 통합) |

**실패 시:** `docker compose logs <service>` 로 원인 파악. 포트 충돌이면 `lsof -i :5432` 확인.

#### 2-b. TimescaleDB 확장 확인

```sql
-- psql 또는 DBeaver
SELECT extname, extversion FROM pg_extension WHERE extname = 'timescaledb';
-- 결과 없으면: CREATE EXTENSION IF NOT EXISTS timescaledb;
```

#### 2-c. Alembic 마이그레이션 상태 확인 후 적용

```bash
cd backend
uv run alembic current        # 현재 revision 확인
uv run alembic upgrade head   # 최신으로 업그레이드
uv run alembic current        # head 표시되면 성공
```

**마이그레이션 실패 시 롤백:**

```bash
uv run alembic downgrade -1   # 한 단계 되돌리기
# 원인 파악 후 재시도
```

#### 2-d. Trading 스키마 테이블 존재 확인

```sql
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'trading'
ORDER BY table_name;
```

**예상 출력:** `exchange_accounts`, `kill_switch_events`, `orders`, `trading_sessions`

**테이블 미존재 시:** 마이그레이션이 누락된 것. `alembic history` 로 누락 revision 파악.

#### 2-e. Redis 연결 확인

```bash
docker compose exec quant-bridge-redis redis-cli ping
# 기대 출력: PONG
```

**완료 기준:** 4개 테이블 존재 + Redis PONG + alembic current = head

---

### T3. Trading 회귀 테스트

```bash
cd backend
uv run pytest tests/trading/ -v -x
```

**FAIL 시 대응:**

- Kill Switch 관련 실패 → `tests/trading/test_kill_switch.py` 단독 실행으로 격리
- DB 연결 실패 → T2 재확인
- 환경변수 누락 → T1 재확인

**완료 기준:** tests/trading/ 전부 green (exit code 0).

---

### T4. Bybit Demo Smoke Test

**스크립트:** `backend/scripts/bybit_demo_smoke.py` (이미 존재)

#### 4-a. 사전 조건 검증 (스크립트 실행 전)

```bash
# 1. env var 설정 여부 확인
[[ -z "$BYBIT_DEMO_KEY" ]]    && echo "⚠️  BYBIT_DEMO_KEY 미설정" && exit 1
[[ -z "$BYBIT_DEMO_SECRET" ]] && echo "⚠️  BYBIT_DEMO_SECRET 미설정" && exit 1

# 2. .env.demo 파일 경로 로드 (설정된 경우)
[[ -f "backend/.env.demo" ]] && source backend/.env.demo
```

#### 4-b. Smoke Test 실행

```bash
cd backend
uv run python scripts/bybit_demo_smoke.py \
    --api-key "$BYBIT_DEMO_KEY" \
    --api-secret "$BYBIT_DEMO_SECRET" \
    --symbol "BTC/USDT:USDT" \
    --quantity 0.001 \
    --order-type limit
```

**기대 출력:**

```
[PASS] API 연결 OK — server_time: <timestamp>
[PASS] 잔고 확인 OK — USDT available: <amount>
[PASS] order submitted: order_id=<id>, status=pending
[PASS] order cancelled: order_id=<id>
[PASS] DB row exists: trading.orders WHERE exchange_order_id=<id>
```

#### 4-c. 실패 유형별 대응

| 오류                   | 원인                             | 대응                                                       |
| ---------------------- | -------------------------------- | ---------------------------------------------------------- |
| `401 Unauthorized`     | API Key/Secret 오류 또는 만료    | Bybit Demo Trading 탭에서 키 재발급                        |
| `403 Forbidden`        | API Key 권한 미설정 (Trade 없음) | API Key 설정에서 Read + Trade 활성화                       |
| `Balance insufficient` | Demo USDT 미충전                 | Demo Trading → Asset → Demo USDT 지급                      |
| `ConnectionError`      | Bybit API unreachable            | `curl https://api-demo.bybit.com/v5/market/time` 연결 확인 |
| `Rate limit (429)`     | 요청 과다                        | 60초 대기 후 재시도                                        |
| `DB row not found`     | trading.orders 미기록            | DB 연결 T2 재확인                                          |
| **Cancel 실패 (leak)** | 주문이 시장가로 체결될 수 있음   | Bybit Demo UI 수동 취소, `trading.orders` row 상태 확인    |

> ⚠️ **Smoke Test 잔여 주문 정리:** smoke test 스크립트가 반드시 주문을 취소하도록 설계되어야 함. cancel 단계 실패 시 `backend/scripts/cancel_all_demo_orders.py` (없으면 수동 취소) 실행.

**FAIL 시 전체 대응:** `docs/TODO.md` Blocked 섹션에 오류 내용 기록 → Phase B/C 먼저 진행.

---

### T5. API 서버 헬스체크 + Coverage Analyzer 연동 검증

#### 5-a. API 서버 기동 및 헬스체크

```bash
cd backend
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000 &
sleep 3
curl -s http://localhost:8000/health | jq '.status'
# 기대 출력: "ok"
```

#### 5-b. Coverage Analyzer 필드명 확인

> ⚠️ **중요:** Coverage Analyzer의 실제 필드명은 `unsupported_functions`이지 `unsupported_builtins`가 아님.
> `CoverageReport` 데이터클래스: `unsupported_functions`, `unsupported_attributes`, `used_functions`, `used_attributes`

```bash
# CLERK_TOKEN 획득 (Clerk Dashboard → API Keys → Frontend API)
export CLERK_TOKEN="<clerk_jwt_token>"

# request.security 포함 전략 ID 확인 (DB 또는 UI에서)
curl -s \
  -H "Authorization: Bearer $CLERK_TOKEN" \
  "http://localhost:8000/api/v1/strategies/<strategy_id>/parse-preview" \
  | jq '{unsupported_functions: .coverage.unsupported_functions,
          unsupported_attributes: .coverage.unsupported_attributes}'
```

**완료 기준:** 배열 형태로 반환. `request.security` 포함 전략이면 `unsupported_functions` 배열에 포함.

> Phase B-4 작업 전에는 `request.security`가 unsupported_functions에 노출되지 않을 수 있음 — Phase B-4 완료 후 재검증.

---

### T6. Week1 Baseline Skeleton 문서 기록

**파일:** `docs/dev-log/dogfood-week1-path-beta.md` (이미 생성됨)

**기록 절차:**

1. s1_pbr.pine 최근 백테스트 run 결과 UI에서 확인 (`/backtests` 페이지)
2. Sharpe, Win Rate, Max DD, Total Trades 값을 파일에 기입
3. Kill Switch 설정값 (T1에서 정의한 값) 기입
4. Demo 계정 초기 USDT 잔고 기입

**완료 기준:** 파일 내 `—` 자리표시자 대신 실제 값 기입 (첫 백테스트 미실행 시 별도 백테스트 실행).

---

## 완료 기준 (Gate-A)

| 항목           | 검증 명령/방법                                               | 기준                     |
| -------------- | ------------------------------------------------------------ | ------------------------ |
| `.env.example` | `grep "KILL_SWITCH\|EXCHANGE_PROVIDER" backend/.env.example` | 5줄 이상                 |
| `.gitignore`   | `grep ".env.demo" .gitignore`                                | 출력 있음                |
| DB             | SQL 테이블 조회                                              | 4개 테이블 존재          |
| Redis          | `redis-cli ping`                                             | PONG                     |
| Trading 테스트 | `pytest tests/trading/ -v`                                   | 전부 green               |
| Smoke test     | 스크립트 실행                                                | PASS 또는 Blocked 문서화 |
| Health check   | `curl /health`                                               | status: ok               |
| Week1 skeleton | 파일 내 실제 값 기입                                         | — 없음                   |

---

## 에러 에스컬레이션 기준

Phase A에서 아래 상황 발생 시 **즉시 중단 후 사용자 확인**:

- DB 마이그레이션이 `alembic downgrade -1` 후에도 실패
- Smoke test에서 주문 취소 실패 (demo이지만 열린 포지션 존재)
- `trading.orders` 테이블이 존재하지 않아 smoke test DB 검증 불가

---

## 브랜치

`feat/h2s1-dogfood-baseline` → squash merge → `stage/h2-sprint1`

**커밋:**

```
c1 feat(dogfood): .env.example Kill Switch vars + EXCHANGE_PROVIDER + week1 baseline
```
