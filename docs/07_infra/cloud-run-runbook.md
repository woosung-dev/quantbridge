# Cloud Run Topology Gap Audit + Runbook

> **상태:** Audit / Partial / Follow-up Required
> **목적:** Sprint 30 ε 의 prod-code 자산을 기반으로 BL-071 (Backend 프로덕션 배포) 진입 전 **topology gap audit + dry-run 명령어 sketch + Sprint 34 unresolved gap 목록**을 정리.
> **명시:** 본 runbook 은 "Beta prereq 충분" 또는 "prod ready" 표기를 **하지 않음**. Sprint 34 deploy 실험 prereq 인 unresolved gap (Cloud SQL connector / VPC connector / IAM SA 등) 을 강조.
> **scope:** docs only — 코드 변경 0. dry-run 명령어 sketch 만 (실제 `gcloud run deploy` 실행 없음).
>
> 의존: [`./deployment-plan.md`](./deployment-plan.md), [`../../backend/Dockerfile`](../../backend/Dockerfile), [`../../backend/src/health/router.py`](../../backend/src/health/router.py), [`../../backend/docker-entrypoint.sh`](../../backend/docker-entrypoint.sh), [`../../backend/.env.example`](../../backend/.env.example), [`../../docker-compose.yml`](../../docker-compose.yml)
>
> 작성: 2026-05-05 (Sprint 33 Worker C — codex P1-2 surgery, BL-071 audit)

---

## 1. Background — Sprint 30 ε prod-code 자산

Sprint 30 ε 가 backend 프로덕션 진입 prereq 의 **컨테이너 빌드 + readiness probe** 자산을 완성. 본 runbook 은 그 자산이 Cloud Run 배포에 어디까지 적용 가능한지 audit.

### 1.1. Sprint 30 ε B1 — `backend/Dockerfile` (multi-stage uv builder)

[`backend/Dockerfile`](../../backend/Dockerfile):

- **Stage 1 (builder):** `python:3.12-slim` + uv 공식 binary copy. `pyproject.toml` + `uv.lock` 먼저 layer cache → 코드 후 layer 로 분리. `uv sync --frozen --no-dev`.
- **Stage 2 (runner):** slim runtime + 비root user (`appuser:1000`, CSO-2 정합) + `ENV PORT=8080` (Cloud Run 표준).
- **Entrypoint:** `/app/docker-entrypoint.sh` (role 분기 — `api` / `worker` / `beat` / `migrate`).
- **CMD default:** `api`.

### 1.2. Sprint 30 ε B3 — `/healthz` 3-dep readiness probe

[`backend/src/health/router.py`](../../backend/src/health/router.py):

- **Postgres:** `SELECT 1` round-trip (timeout 5s) — pool_pre_ping 으로 stale 회피.
- **Redis:** lock pool `PING` (timeout 5s).
- **Celery:** `celery_app.control.inspect(timeout=3.0).ping()` — broker 통한 활성 worker 카운트. `asyncio.to_thread` 로 sync inspect 분리.
- **정책:** Celery worker `>= 1` 도 200 조건. 0 worker → 503 (api 인스턴스 단독 부팅 race window 회피 의도).
- 응답 schema: `{"db": "ok"|"fail", "redis": "ok"|"fail", "celery_workers": N, "errors": {...optional...}}`.

### 1.3. Sprint 30 ε B6 — `docker-entrypoint.sh` (alembic advisory lock + role 분기)

[`backend/docker-entrypoint.sh`](../../backend/docker-entrypoint.sh):

- **api role:** `run_alembic_with_lock` (advisory lock key `0x71626730 = 'qbg0'`, timeout 30s) → `uvicorn src.main:app --host 0.0.0.0 --port ${PORT:-8080}`.
- **worker role:** alembic skip + `celery -A src.tasks worker --pool=prefork --concurrency=${CELERY_CONCURRENCY:-4}`.
- **beat role:** alembic skip + `celery -A src.tasks beat`.
- **migrate role:** alembic upgrade head 만 (one-shot, api 와 동일 lock 사용).
- **scope:** prod / container 전용. host 개발 (`make be`) 은 본 entrypoint bypass — 루트 `Makefile` `migrate` / `migrate-isolated` 가 책임 (Sprint 32 BL-168).

### 1.4. 현재 docker-compose 와의 대조

[`docker-compose.yml`](../../docker-compose.yml) 안 backend 관련 service 는 **api 미포함**:

- `backend-worker` — celery prefork
- `backend-ws-stream` — celery prefork (Q ws_stream, BL-012)
- `backend-beat` — celery beat scheduler

즉 host 개발 환경에서 **api 는 host uvicorn (`make be`) 으로 실행**되고, container 안 worker 와 통신. 이 구조가 Cloud Run 으로 옮겨질 때 api 를 Cloud Run **service** 로 별도 배포해야 한다 (compose 안에 backend-api service 가 정의돼 있지 않다는 점 = Cloud Run 배포 시 새로 작성).

---

## 2. Topology decision matrix — API / Worker / Beat × Cloud Run 옵션

QuantBridge backend 는 3 개의 독립 process (api / worker / beat) + ws_stream queue worker (sub-worker) = 총 **4 process role**. Cloud Run 은 service (HTTP triggered, autoscale) 와 job (one-shot, manual / scheduled trigger) 두 종류 자원 제공. 각 role 별 매핑:

| Role | 옵션 1: Cloud Run service (autoscale) | 옵션 2: Cloud Run job (scheduled) | 옵션 3: Cloud Run service single-instance | 권장 (Sprint 34 실험 1차) |
|------|----------------------------------------|-----------------------------------|-------------------------------------------|---------------------------|
| **api (uvicorn)** | ★★★★★ — HTTP request 가 trigger. cold start tolerable. min-instances=0 가능 (단 healthz Celery 의존 → §3 참조). | ✗ — long-running HTTP server 라 job 에 부적합. | ★★★ — Cloud Run service 의 max-instances=1 로 강제 가능. autoscale 실험 후 결정. | **service (autoscale, min-instances=1)** — healthz Celery 의존 + Beta 초기 일관성 우선. |
| **worker (celery prefork)** | ★★ — HTTP listener 없음 → Cloud Run service 가 부적합 (request-driven 가정 위배). 일부 우회 가능 (no-op HTTP) 하지만 anti-pattern. | ★★★ — job 으로 1회 실행 후 종료 가능하지만 long-running consumer 라 부적합. Cloud Scheduler + job 조합은 batch 용. | ★★★★★ — `min-instances=1, max-instances=1, cpu-throttling=off` 로 항상 실행. Cloud Run 의 idle CPU throttling 은 Celery prefetch 망가뜨림 → off 필수. | **service single-instance (min=max=1, no-throttle)** — long-running consumer 패턴. 또는 Compute Engine VM 으로 외부화 검토. |
| **beat (celery beat scheduler)** | ★ — singleton 보장 어렵다. autoscale 시 다중 beat 동시 실행 위험 (중복 schedule). | ★★ — Cloud Scheduler + job 으로 N 분 주기 trigger 대체 가능 (beat 자체 미사용). 단 reclaim_stale_running 5분 + ws_reconcile 5분 등 schedule 이 ε 안에 hard-coded. | ★★★★★ — `min=max=1` 강제. 현재 docker-compose `backend-beat` 와 동일 패턴. | **service single-instance (min=max=1)** — singleton 보장. 장기적으로 Cloud Scheduler + job 으로 마이그레이션 검토 (operational simplicity). |
| **ws_stream worker (Q ws_stream, prefork concurrency=2)** | ★★ — celery worker 동일. | ★★ — 동일. | ★★★★★ — `backend-ws-stream` 는 Redis lease (BL-011) + worker_process_shutdown signal_all_stop_events (BL-012). singleton service 로 매핑. concurrency=2 = account 수 ≤ 2 까지 지원. | **service single-instance** — Redis lease 가 multi-instance race 방어하지만, 현재 dogfood 1-user 가정 → instance 1개로 충분. |

### 2.1. Trade-off summary

- **autoscale 의 함정:** Cloud Run 은 기본 traffic-driven autoscale + idle CPU throttling. Celery worker 처럼 **HTTP request 없이 background poll 하는 process** 는 throttling 으로 stuck. `--cpu-throttling=off` 필수 (Cloud Run "always allocated CPU" mode = $$ 발생).
- **healthz Celery dep ↔ Cloud Run readiness probe race:** §3 상세.
- **singleton 보장:** beat / ws_stream 는 multi-instance 시 동작 깨짐 (beat = 중복 schedule, ws_stream = Redis lease 가 방어하지만 lease miss 시 race). `min-instances=1, max-instances=1` 강제로 해결.
- **VPC + private DB:** Cloud SQL 또는 Memorystore 는 VPC 안. Cloud Run service 는 **VPC connector** (Serverless VPC Access) 로 VPC 안 자원 접근. connector 없으면 public IP 노출 강제 (security 후퇴).

### 2.2. 권장 1차 실험 토폴로지 (Sprint 34)

```
Cloud Run services (4):
├── quantbridge-api          (autoscale min=1 max=N)
├── quantbridge-worker       (single-instance min=1 max=1 no-throttle)
├── quantbridge-ws-stream    (single-instance min=1 max=1 no-throttle)
└── quantbridge-beat         (single-instance min=1 max=1)

Managed services:
├── Cloud SQL (PostgreSQL 15 + TimescaleDB) — TimescaleDB extension 호환성 [확인 필요]
├── Memorystore Redis (DB 0/1/2/3 use 동일 instance, db number 분리)
└── Secret Manager (CLERK_SECRET_KEY / TRADING_ENCRYPTION_KEYS 등)

Network:
└── Serverless VPC Connector (api/worker/beat ↔ Cloud SQL + Memorystore)
```

**[확인 필요]** TimescaleDB extension 은 Cloud SQL on GCP 에서 공식 지원 X (deployment-plan.md §4 ⚠️). 대안: (1) self-host PostgreSQL on Compute Engine + TimescaleDB Docker, (2) TimescaleDB Cloud (공식 managed), (3) Fly Postgres 이주. 본 결정이 Cloud Run 배포 자체와 분리되며 Sprint 34 prereq.

---

## 3. healthz Celery dependency 검증 — Cloud Run readiness probe race

### 3.1. 현재 정책

[`backend/src/health/router.py`](../../backend/src/health/router.py) L142:

```python
healthy = pg_status == "ok" and redis_status == "ok" and celery_count >= 1
```

= **api 인스턴스 readiness 가 Celery worker `>= 1` 응답에 묶임**. Sprint 30 ε 의도:

> "api 인스턴스 단독 부팅 시점 race window 회피 위해 backend prod 에서는 worker 1+ 필요" (`router.py` L13~14 docstring)

### 3.2. Cloud Run 에서의 영향

Cloud Run service 는 `/healthz` (또는 startup probe) 200 미반환 시 traffic 제외 + restart loop. 본 정책이 의도대로 동작하려면 **worker service 가 api service 보다 먼저 ready** 여야 한다. 그러나 Cloud Run 은:

- service 간 startup ordering 보장 X (각 service 독립 deploy / autoscale)
- 첫 deploy / cold start 시 worker 가 늦게 뜨면 api `/healthz` 503 → restart loop → worker 도 cold start 시도 시 broker 부재로 다시 stuck

### 3.3. 결정 필요 (Beta 진입 전, Sprint 34 prereq)

**옵션 A — 현재 정책 유지 + Cloud Run startup probe 분리:**

- `/healthz` 는 그대로 (3-dep + Celery 의존)
- `/livez` 또는 `/startupz` 신규 endpoint 추가 — Postgres 만 검사 (Celery 의존 X)
- Cloud Run `--liveness-probe` = `/livez`, `--startup-probe` = `/startupz`. `/healthz` 는 internal monitoring (Slack alert 연동) 으로 강등.
- effort: backend code 변경 1~2h + 테스트.

**옵션 B — `/healthz` 정책 완화:**

- Celery worker 0 도 200 (단 errors 필드에 noted). api 는 worker 와 독립적으로 readiness 판단.
- worker readiness 는 별도 `/healthz/worker` endpoint 또는 Celery flower / metrics.
- effort: backend code 변경 < 1h + 테스트 + 문서 업데이트.
- risk: Sprint 30 ε 의 race window 의도 회귀 — 단독 부팅 후 traffic 받는 동안 background task 적재만 됨.

**옵션 C — startup ordering 강제 (Cloud Run job + Cloud Scheduler):**

- worker / beat / ws_stream 을 Cloud Run job 으로 마이그레이션 + Cloud Scheduler trigger. 그러나 long-running consumer 패턴과 부적합 (옵션 2 trade-off 참조).
- 비추천.

**Sprint 34 권장:** **옵션 A** (`/livez` 분리). Cloud Run readiness probe 분리는 GCP best practice 정합. 옵션 B 는 Sprint 30 ε 결정 회귀라 ADR 신규 필요. 본 runbook 의 결정 권한은 **사용자 + tech lead 승인 후** Sprint 34 prereq.

> **본 runbook 작성 시점에는 결정 X.** Sprint 34 deploy 실험 첫 주 안 (사용자 검토) 결정. 결정 전까지 Cloud Run 배포 진행 시 readiness probe restart loop 위험 명시.

---

## 4. Env 매핑 — `.env.example` → Cloud Run

[`backend/.env.example`](../../backend/.env.example) 의 환경변수를 Cloud Run service 의 (1) `--set-env-vars` (plain), (2) `--update-secrets` (Secret Manager mount), (3) Cloud SQL Auth Proxy / VPC connector (네트워크) 로 매핑.

### 4.1. 매핑 표

| `.env.example` key | 매핑 방식 | Cloud Run flag | 비고 |
|--------------------|-----------|----------------|------|
| `APP_NAME` | env var (plain) | `--set-env-vars=APP_NAME=QuantBridge` | |
| `APP_ENV` | env var (plain) | `--set-env-vars=APP_ENV=production` | dev → prod 변경 |
| `DEBUG` | env var (plain) | `--set-env-vars=DEBUG=false` | prod false 강제 |
| `SECRET_KEY` | **Secret Manager** | `--update-secrets=SECRET_KEY=quantbridge-secret-key:latest` | 32+ byte random |
| `CLERK_SECRET_KEY` | **Secret Manager** | `--update-secrets=CLERK_SECRET_KEY=clerk-secret-key:latest` | sk_live_… (prod tier) |
| `CLERK_WEBHOOK_SECRET` | **Secret Manager** | `--update-secrets=CLERK_WEBHOOK_SECRET=clerk-webhook-secret:latest` | rotate 시 grace period |
| `WEBHOOK_SECRET_GRACE_SECONDS` | env var | `--set-env-vars=WEBHOOK_SECRET_GRACE_SECONDS=3600` | |
| `DATABASE_URL` | **연결자별 분기** | (1) Cloud SQL Auth Proxy: `postgresql+asyncpg://user:pass@/dbname?host=/cloudsql/PROJECT:REGION:INSTANCE` (2) VPC + private IP: `postgresql+asyncpg://user:pass@10.x.x.x:5432/quantbridge` | TimescaleDB extension 호환성 별개 결정 |
| `REDIS_URL` | env var (private IP) | `--set-env-vars=REDIS_URL=redis://10.x.x.x:6379/0` | Memorystore + VPC connector 필수 |
| `CELERY_BROKER_URL` | env var | `--set-env-vars=CELERY_BROKER_URL=redis://10.x.x.x:6379/1` | 동일 instance, db 1 |
| `CELERY_RESULT_BACKEND` | env var | `--set-env-vars=CELERY_RESULT_BACKEND=redis://10.x.x.x:6379/2` | 동일 instance, db 2 |
| `REDIS_LOCK_URL` | env var | `--set-env-vars=REDIS_LOCK_URL=redis://10.x.x.x:6379/3` | 동일 instance, db 3 |
| `SLACK_WEBHOOK_URL` | **Secret Manager** | `--update-secrets=SLACK_WEBHOOK_URL=slack-webhook:latest` | 비공개 |
| `TRADING_ENCRYPTION_KEYS` | **Secret Manager** | `--update-secrets=TRADING_ENCRYPTION_KEYS=trading-encryption-keys:latest` | Fernet, rotation 시 csv (Sprint 6+) |
| `EXCHANGE_PROVIDER` | env var (DEPRECATED) | 생략 가능 — Sprint 23+ 제거 예정 | |
| `BYBIT_FUTURES_MAX_LEVERAGE` | env var | `--set-env-vars=BYBIT_FUTURES_MAX_LEVERAGE=20` | |
| `BYBIT_DEMO_KEY` / `BYBIT_DEMO_SECRET` | **Secret Manager** | `--update-secrets=BYBIT_DEMO_KEY=bybit-demo-key:latest,BYBIT_DEMO_SECRET=bybit-demo-secret:latest` | dogfood 사용자만 등록 |
| `BYBIT_DEMO_API_KEY_TEST` / `..._SECRET_TEST` | env var (CI only) | prod 미적용 | nightly CI 전용 |
| `OHLCV_PROVIDER` | env var | `--set-env-vars=OHLCV_PROVIDER=timescale` | |
| `OHLCV_FIXTURE_ROOT` | env var | `--set-env-vars=OHLCV_FIXTURE_ROOT=/app/data/fixtures/ohlcv` | container path |
| `DEFAULT_EXCHANGE` | env var | `--set-env-vars=DEFAULT_EXCHANGE=bybit` | |
| `PINE_ALERT_HEURISTIC_MODE` | env var | `--set-env-vars=PINE_ALERT_HEURISTIC_MODE=strict` | |
| `KILL_SWITCH_*` (4건) | env var | `--set-env-vars=KILL_SWITCH_CUMULATIVE_LOSS_PERCENT=10.0,...` | |
| `BACKTEST_STALE_THRESHOLD_SECONDS` | env var | `--set-env-vars=BACKTEST_STALE_THRESHOLD_SECONDS=1800` | |
| `TRUSTED_PROXIES` | env var | `--set-env-vars=TRUSTED_PROXIES=<Cloudflare IPs CSV>` | BL-070 Cloudflare 결정 후 채움 |
| `PROMETHEUS_BEARER_TOKEN` | **Secret Manager** | `--update-secrets=PROMETHEUS_BEARER_TOKEN=prometheus-bearer:latest` | Grafana Cloud Agent 와 동일 값 |
| `RESEND_API_KEY` | **Secret Manager** | `--update-secrets=RESEND_API_KEY=resend-api-key:latest` | BL-072 Resend prereq |
| `WAITLIST_TOKEN_SECRET` | **Secret Manager** | `--update-secrets=WAITLIST_TOKEN_SECRET=waitlist-token-secret:latest` | BL-072 |
| `WAITLIST_ADMIN_EMAILS` | env var | `--set-env-vars=WAITLIST_ADMIN_EMAILS=...` | CSV |
| `WAITLIST_INVITE_BASE_URL` | env var | `--set-env-vars=WAITLIST_INVITE_BASE_URL=https://<domain>/invite` | BL-070 도메인 결정 후 |
| `FRONTEND_URL` | env var | `--set-env-vars=FRONTEND_URL=https://<domain>` | CORS, BL-070 도메인 결정 후 |

### 4.2. Secret Manager 정책

- **secret 분리:** key 당 secret 1개 (rotation 단위 분리). version 은 `:latest` alias.
- **IAM:** Cloud Run service account (§6 SA) 에 `roles/secretmanager.secretAccessor` 부여.
- **monitor:** Secret Manager 접근 audit log → Cloud Logging.
- **rotation:** Fernet (`TRADING_ENCRYPTION_KEYS`) 는 csv 다중 키 지원 (Sprint 6+). Clerk webhook secret 도 grace period 패턴 (env `WEBHOOK_SECRET_GRACE_SECONDS=3600`).

### 4.3. 단일 Secret Manager mount vs 다중 secret

- **권장:** 다중 secret (위 표). 이유: rotation 단위 분리 + IAM granularity + audit log clarity.
- **anti-pattern:** `.env` 단일 secret 으로 통합 (rotation 시 전부 영향).

---

## 5. Deploy step (dry-run only) — `gcloud run deploy --no-traffic --dry-run` sketch

> **본 절은 명령어 sketch + 예상 결과만 문서화. 실제 실행 X.** Sprint 34 실험 시 사용자 + tech lead 승인 후 실행.

### 5.1. Prereq (gcloud CLI 가정 — Sprint 34 실험 시점)

```bash
# 1. gcloud auth + project 설정
gcloud auth login
gcloud config set project <PROJECT_ID>
gcloud config set run/region asia-northeast3   # Seoul

# 2. Artifact Registry 생성 (이미지 push 대상)
gcloud artifacts repositories create quantbridge \
  --repository-format=docker \
  --location=asia-northeast3

# 3. Docker buildx + push (multi-arch optional)
cd backend
docker buildx build \
  --platform linux/amd64 \
  -t asia-northeast3-docker.pkg.dev/<PROJECT_ID>/quantbridge/backend:sprint30-eps \
  --push .
```

**예상 결과:** Artifact Registry 에 `backend:sprint30-eps` 이미지 push. 약 200~400MB (slim runner).

### 5.2. api service dry-run

```bash
gcloud run deploy quantbridge-api \
  --image=asia-northeast3-docker.pkg.dev/<PROJECT_ID>/quantbridge/backend:sprint30-eps \
  --args="api" \
  --port=8080 \
  --min-instances=1 \
  --max-instances=10 \
  --cpu=1 --memory=1Gi \
  --service-account=quantbridge-sa@<PROJECT_ID>.iam.gserviceaccount.com \
  --vpc-connector=quantbridge-connector \
  --vpc-egress=private-ranges-only \
  --add-cloudsql-instances=<PROJECT_ID>:asia-northeast3:quantbridge-pg \
  --set-env-vars=APP_ENV=production,DEBUG=false,DATABASE_URL=...,REDIS_URL=... \
  --update-secrets=SECRET_KEY=quantbridge-secret-key:latest,CLERK_SECRET_KEY=clerk-secret-key:latest,TRADING_ENCRYPTION_KEYS=trading-encryption-keys:latest \
  --no-traffic \
  --dry-run
```

**예상 결과 (dry-run):** validation 통과 시 spec YAML 출력 + "Service would be deployed". 실제 traffic 미할당 (`--no-traffic`).

**주의:** `gcloud run deploy --dry-run` flag 는 GA 가 아니라 alpha/beta `gcloud beta run deploy ...` 로 제공될 수 있음 [확인 필요]. 미지원 시 대안:

- `gcloud run services replace <yaml>` 로 spec 만 검증 (`--dry-run` 지원)
- 또는 staging project 별도 생성 후 실제 deploy → smoke → tear down

### 5.3. worker service dry-run

```bash
gcloud run deploy quantbridge-worker \
  --image=asia-northeast3-docker.pkg.dev/<PROJECT_ID>/quantbridge/backend:sprint30-eps \
  --args="worker" \
  --no-cpu-throttling \
  --min-instances=1 --max-instances=1 \
  --cpu=1 --memory=1Gi \
  --service-account=quantbridge-sa@<PROJECT_ID>.iam.gserviceaccount.com \
  --vpc-connector=quantbridge-connector \
  --vpc-egress=private-ranges-only \
  --add-cloudsql-instances=<PROJECT_ID>:asia-northeast3:quantbridge-pg \
  --set-env-vars=APP_ENV=production,CELERY_CONCURRENCY=4,DATABASE_URL=...,CELERY_BROKER_URL=... \
  --update-secrets=TRADING_ENCRYPTION_KEYS=trading-encryption-keys:latest \
  --no-traffic \
  --dry-run
```

**예상 결과:** worker 는 HTTP listener 없음 → Cloud Run 이 dummy port (8080) 에 listen 강제. entrypoint 가 celery 만 실행 → Cloud Run health check fail 가능. **워크어라운드:** worker container 안에 sidecar HTTP server 추가 (예: Python `http.server`) 또는 celery healthcheck endpoint 노출. **이 워크어라운드 자체가 Sprint 34 unresolved gap (§6).**

### 5.4. beat service dry-run

```bash
gcloud run deploy quantbridge-beat \
  --image=asia-northeast3-docker.pkg.dev/<PROJECT_ID>/quantbridge/backend:sprint30-eps \
  --args="beat" \
  --no-cpu-throttling \
  --min-instances=1 --max-instances=1 \
  --cpu=0.5 --memory=512Mi \
  --service-account=quantbridge-sa@<PROJECT_ID>.iam.gserviceaccount.com \
  --vpc-connector=quantbridge-connector \
  --no-traffic \
  --dry-run
```

**예상 결과:** beat 도 HTTP listener 없음 — worker 와 동일 워크어라운드 필요.

### 5.5. ws-stream service dry-run

```bash
gcloud run deploy quantbridge-ws-stream \
  --image=asia-northeast3-docker.pkg.dev/<PROJECT_ID>/quantbridge/backend:sprint30-eps \
  --command="uv" \
  --args="run,celery,-A,src.tasks.celery_app,worker,-Q,ws_stream,--pool=prefork,--concurrency=2,--loglevel=info" \
  --no-cpu-throttling \
  --min-instances=1 --max-instances=1 \
  ...
```

**주의:** ws_stream 는 `docker-entrypoint.sh` role 분기에 미포함 → entrypoint bypass + 직접 command override 필요. **이 부분이 Sprint 34 unresolved gap (§6) — entrypoint 에 `ws-stream` role 추가 또는 별도 wrapper 필요.**

---

## 6. Sprint 34 unresolved gap 목록 (필수)

본 runbook 의 dry-run sketch 가 실제 실행되기 전에 해소해야 하는 gap. 각 gap 별 추정 effort + Beta 진입 전 prereq 등급.

| # | Gap | 추정 effort | Beta prereq 등급 | 비고 |
|---|-----|-------------|------------------|------|
| **G1** | **TimescaleDB extension on Cloud SQL** — Cloud SQL PostgreSQL 은 TimescaleDB 공식 미지원. self-host vs TimescaleDB Cloud vs Fly Postgres 결정 [확인 필요] | M (3~5h 결정 + 1주 마이그레이션 PoC) | **P0 blocker** | deployment-plan.md §4 ⚠️ |
| **G2** | **Serverless VPC Connector 생성** — Cloud Run ↔ Memorystore Redis + Cloud SQL private IP 연결. /28 subnet 할당 + IAM 설정. | S (1~2h) | **P0 blocker** | GCP managed |
| **G3** | **IAM Service Account 설계** — `quantbridge-sa` 신규 + Secret Manager + Cloud SQL + Memorystore 권한 최소화. Workload Identity 또는 SA key 결정. | S (2~3h) | **P0 blocker** | CSO security review 필요 |
| **G4** | **Cloud SQL connector vs private IP** — Cloud Run 의 `--add-cloudsql-instances` (Auth Proxy unix socket) vs VPC private IP 직접 접속 결정. async driver (asyncpg) 호환성 [확인 필요]. | S (1~2h test) | **P0 blocker** | Sprint 30 ε 의 asyncpg 와 Cloud SQL Auth Proxy unix socket 호환성 검증 필수 |
| **G5** | **Secret Manager secret 생성 + IAM** — 표 §4.1 의 8+ secret 생성 + version 관리. | S (2~3h, 사용자 manual) | **P0 blocker** | rotation 정책 사전 결정 |
| **G6** | **Custom domain + HTTPS** — BL-070 (도메인 + DNS + Cloudflare) 완료 후 Cloud Run domain mapping + SSL cert 자동 발급. | S (1h + 24h DNS) | **P0 blocker** | BL-070 의존 |
| **G7** | **healthz Celery dep 정책 결정 (§3.3)** — 옵션 A `/livez` 분리 vs 옵션 B 정책 완화. backend code 변경 1~2h. | S (1~2h code + 결정 0.5h) | **P0 blocker** | §3.3 사용자 + tech lead 결정 prereq |
| **G8** | **worker / beat / ws-stream HTTP listener 워크어라운드** — Cloud Run 이 dummy port listen 강제. sidecar HTTP server 추가 또는 별도 hosting (Compute Engine VM). | M (3~5h sidecar 또는 1일 VM 마이그레이션) | **P0 blocker** | §5.3 / §5.4 / §5.5 |
| **G9** | **`docker-entrypoint.sh` 에 ws-stream role 추가** — 현재 api / worker / beat / migrate 만 분기. ws_stream queue worker 분기 신규. | S (0.5~1h code + 테스트) | **P1** | §5.5 |
| **G10** | **Cloud Run cold start 영향 분석** — api service min-instances=1 비용 vs cold start latency. Beta 초기 사용자 피드백 의존. | M (1주 측정) | **P1** | dogfood Beta 진입 후 측정 |
| **G11** | **Cloud Logging + Slack alert 매핑** — 현재 SLACK_WEBHOOK_URL alert 가 Cloud Logging sink + Pub/Sub + Cloud Function 으로 라우팅 필요. | S (2~3h) | **P1** | 기존 Sprint 12 Slack alert 자산 재사용 |
| **G12** | **Cloud SQL backup + PITR 정책** — 자동 백업 + Point-in-Time Recovery 활성화. cost 검토. | S (1h) | **P1** | data loss 방어 |
| **G13** | **Memorystore size 결정 + maxmemory-policy** — 현재 docker-compose `--maxmemory 512mb --maxmemory-policy allkeys-lru`. Memorystore 는 size 미리 선정 + LRU 정책 동일. | S (0.5~1h) | **P1** | |
| **G14** | **CI/CD pipeline (GitHub Actions → Artifact Registry → Cloud Run)** — 현재 GitHub Actions 가 lint/test 만. Cloud Run 자동 deploy workflow 신규. | M (3~5h) | **P2** | 수동 deploy 도 Beta 가능, 자동화는 Sprint 34 후반 |
| **G15** | **Observability — Grafana Cloud Agent on Cloud Run** — 현재 host metric scrape 가정. Cloud Run sidecar pattern 검토 또는 Cloud Monitoring 으로 전환. | M (3~5h) | **P2** | PROMETHEUS_BEARER_TOKEN 매핑 후속 |
| **G16** | **Cost ceiling + budget alert** — Beta 초기 GCP 비용 예측 + budget alert 설정. | S (1h) | **P2** | 예산 초과 시 trigger |

**총합:** 16 gap. P0 blocker 8건 (G1~G8) — Sprint 34 deploy 실험 진입 전 모두 해소 필수.

---

## 7. Sprint 34 deploy 실험 plan sketch

본 runbook 의 dry-run sketch 가 실제 deploy 로 진행되는 순서. **Beta 본격 진입 결정 후 Sprint 34 첫 주에 실험.**

### 7.1. Phase 1 — prereq 해소 (G1~G8 P0 blocker, 1~2주)

1. **W1 D1~2:** G1 TimescaleDB hosting 결정 (사용자 + tech lead) + PoC.
2. **W1 D3~4:** G3 IAM SA 설계 + G5 Secret Manager 생성 (사용자 manual).
3. **W1 D5:** G2 VPC Connector + G4 Cloud SQL connector 검증 (asyncpg 호환성).
4. **W2 D1:** G7 healthz 정책 결정 + `/livez` 분리 backend code (PR 1건).
5. **W2 D2~3:** G8 worker / beat HTTP listener 워크어라운드 (sidecar PoC) + G9 ws-stream role 추가.
6. **W2 D4:** G6 BL-070 도메인 + Cloud Run domain mapping.

### 7.2. Phase 2 — staging deploy + smoke (1주)

7. **W3 D1:** Artifact Registry 이미지 push (`backend:sprint34-staging-1`).
8. **W3 D2:** api / worker / beat / ws-stream 4 service `--no-traffic` deploy.
9. **W3 D3:** smoke test — `/healthz` / `/livez` 200 + Backtest 1건 E2E + Trading 1건 entry (Demo).
10. **W3 D4:** Slack alert + Cloud Logging 검증.
11. **W3 D5:** load test (1 RPS sustained 1h) + cost 측정.

### 7.3. Phase 3 — prod 진입 (1~2일)

12. **W4 D1:** traffic 100% 전환 (`gcloud run services update-traffic`).
13. **W4 D1~2:** 24h smoke + canary monitoring.
14. **W4 D2:** 사용자 + tech lead 최종 승인 + BL-071 ✅ Resolved 마킹.

### 7.4. Phase 4 — Beta 본격 진입 prereq 정합

- BL-070 ✅ (도메인 + DNS) + BL-071 ✅ (본 runbook + Sprint 34 deploy) + BL-072 ✅ (Resend) → **Beta 캠페인 (BL-073) trigger**.
- 본 runbook 의 G10~G16 P1/P2 gap 은 Beta 진입 후 점진 해소.

### 7.5. roll-back plan

- staging 단계: tear down (`gcloud run services delete`) + Cloud SQL snapshot restore.
- prod 진입 후: traffic split 10% → 0% (`gcloud run services update-traffic --to-revisions=PREV=100,LATEST=0`) + Slack alert.

---

## 8. 참고 cross-link

- [`./deployment-plan.md`](./deployment-plan.md) — Cloud Run vs Fly.io vs K8s 비교
- [`./runbook.md`](./runbook.md) — 일반 운영 runbook
- [`../REFACTORING-BACKLOG.md`](../REFACTORING-BACKLOG.md) BL-070 / BL-071 / BL-072
- [`../../backend/Dockerfile`](../../backend/Dockerfile) — Sprint 30 ε B1
- [`../../backend/src/health/router.py`](../../backend/src/health/router.py) — Sprint 30 ε B3
- [`../../backend/docker-entrypoint.sh`](../../backend/docker-entrypoint.sh) — Sprint 30 ε B6
- [`../../backend/.env.example`](../../backend/.env.example) — env Single Source of Truth
- [`../../docker-compose.yml`](../../docker-compose.yml) — 현재 service topology

---

## 9. 본 runbook 의 결정 권한 명시

- 본 runbook 은 **audit + plan sketch**. "Beta prereq 충분" 또는 "prod ready" 표기 **하지 않음**.
- §3.3 healthz 정책 / §6 G1 TimescaleDB hosting / §6 G7 backend code 변경 등 **모든 결정은 사용자 + tech lead 승인 후** Sprint 34 prereq.
- dry-run 명령어 (§5) 는 sketch 만. 실제 `gcloud` 실행은 사용자 명시 승인 후.
- Sprint 33 안에서는 **추가 코드 변경 X** — 본 runbook 만 산출.
