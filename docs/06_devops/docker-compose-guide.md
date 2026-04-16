# QuantBridge — Docker Compose 가이드

> **목적:** 로컬 dev compose 운영 가이드.
> **SSOT:** [`../../docker-compose.yml`](../../docker-compose.yml). 본 문서는 의도/조작법.
> 셋업: [`../05_env/local-setup.md`](../05_env/local-setup.md)

---

## 1. 서비스 구성

| 서비스 | 이미지 | 컨테이너 명 | 포트 | 헬스체크 | 영속 볼륨 |
|--------|--------|--------------|------|----------|------------|
| `db` | `timescale/timescaledb:2.14.2-pg15` | `quantbridge-db` | 5432 | `pg_isready` | `db-data` |
| `redis` | `redis:7-alpine` | `quantbridge-redis` | 6379 | `redis-cli ping` | `redis-data` |

> Frontend, Backend API/Worker는 현재 compose 외부에서 직접 실행. Sprint 5에서 worker를 compose에 통합 예정 (Open Issue #11).

---

## 2. 자주 쓰는 명령

```bash
# 시작 (background)
docker compose up -d

# 상태 확인 (healthy 여부)
docker compose ps

# 로그 (실시간)
docker compose logs -f db
docker compose logs -f redis

# 중지 (볼륨 보존)
docker compose down

# 중지 + 볼륨 삭제 (DB 초기화)
docker compose down -v

# 단일 서비스 재시작
docker compose restart db

# 컨테이너 내부 진입
docker compose exec db bash
docker compose exec db psql -U quantbridge -d quantbridge
docker compose exec redis redis-cli
```

---

## 3. 데이터 영속성

### 볼륨

- `db-data` — PostgreSQL 데이터 디렉토리
- `redis-data` — Redis AOF (append-only file)

> `docker compose down -v`는 두 볼륨 모두 삭제. **개발 데이터 손실 주의.**

### Redis 영속화

`compose.yml`에서 `redis-server --appendonly yes --maxmemory 512mb --maxmemory-policy allkeys-lru` 설정.

- AOF 활성 → 컨테이너 재시작 시 데이터 복구
- maxmemory 초과 시 LRU eviction (캐시는 손실 가능, Celery 큐는 별도 DB로 분리)

### Redis DB 분리

| DB # | 용도 | 환경 변수 |
|------|------|-----------|
| 0 | 캐시 | `REDIS_URL` |
| 1 | Celery 브로커 | `CELERY_BROKER_URL` |
| 2 | Celery 결과 백엔드 | `CELERY_RESULT_BACKEND` |

---

## 4. PostgreSQL + TimescaleDB

### 단일 인스턴스 운영

OHLCV 시계열 hypertable과 일반 도메인 테이블을 **같은 DB**에서 운영:

- 도메인 테이블 (`users`, `strategies`, `backtests`, ...) — public schema
- 시계열 (`ohlcv`, `funding_rates`) — TimescaleDB hypertable (Sprint 5 활성)

### TimescaleDB extension 활성화

`docker/db/init/` 디렉토리 (compose가 마운트)의 SQL 스크립트가 컨테이너 첫 부팅 시 실행.

> [확인 필요] `docker/db/init/` 내용 — extension 자동 활성화 스크립트 존재 여부. 누락 시 `CREATE EXTENSION IF NOT EXISTS timescaledb;` 추가 필요. Sprint 5 도입 시점에 검증.

### 테스트 DB 분리

- 로컬 dev: `quantbridge`
- pytest: `quantbridge_test` (CI에서 services로 별도 spinup)

---

## 5. 초기화 / 리셋 절차

### DB 완전 초기화 (테이블 + 데이터 삭제)
```bash
docker compose down -v
docker compose up -d
cd backend && uv run alembic upgrade head
```

### Redis 캐시 flush
```bash
docker compose exec redis redis-cli -n 0 FLUSHDB   # 캐시만
docker compose exec redis redis-cli -n 1 FLUSHDB   # Celery 큐만
docker compose exec redis redis-cli FLUSHALL       # 전체
```

> Celery 큐 flush는 in-flight task 손실 — 워커 정지 후 실행 권장.

---

## 6. Healthcheck 동작

| 서비스 | 명령 | interval | retries |
|--------|------|----------|---------|
| `db` | `pg_isready -U quantbridge -d quantbridge` | 10s | 5 |
| `redis` | `redis-cli ping` | 10s | 5 |

> healthy 도달 후에만 백엔드/워커 기동 권장 (current dev: 사용자 수동 순서).

---

## 7. 네트워크

`quantbridge` bridge 네트워크 — 모든 서비스가 연결됨. 외부에서는 publish된 포트(5432, 6379)로 접근.

> compose 내부 서비스 간 호스트명: `db`, `redis` (서비스 명 그대로).
> 외부 (uvicorn 로컬 실행) → `localhost:5432`.

---

## 8. Sprint 5+ 확장 계획

| 항목 | 추가될 서비스 | 비고 |
|------|----------------|------|
| Celery worker | `worker` | API와 동일 이미지, prefork pool, `--concurrency=4` |
| Celery beat | `beat` | stale reclaim, market_data sync 스케줄 |
| (선택) FE | `frontend` | dev는 호스트에서 실행 권장 (HMR 속도) |

---

## 9. 자주 발생하는 문제

### 9.1 포트 충돌 (5432/6379 이미 사용 중)
- 호스트의 PostgreSQL/Redis 종료 또는 compose의 `ports` 매핑 변경
- 예: `"5433:5432"` 후 `DATABASE_URL`도 `5433`으로 수정

### 9.2 healthcheck failing
- 컨테이너 로그 확인: `docker compose logs db`
- 디스크 공간 부족, 권한 문제, 메모리 한계 등 점검

### 9.3 마이그레이션 후 데이터 깨짐
- 로컬: `docker compose down -v` 후 재기동 + `alembic upgrade head`
- 프로덕션: 절대 `down -v` 금지. `alembic downgrade` + 백업 복원

---

## 10. 참고

- Compose 파일: [`../../docker-compose.yml`](../../docker-compose.yml)
- 환경 변수: [`../05_env/env-vars.md`](../05_env/env-vars.md)
- ADR-002 병렬 스캐폴딩: [`../dev-log/002-parallel-scaffold-strategy.md`](../dev-log/002-parallel-scaffold-strategy.md)

---

## 변경 이력

- **2026-04-16** — 초안 작성 (Sprint 5 Stage A)
