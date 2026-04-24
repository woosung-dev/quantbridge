# Grafana Cloud Free 설정 Runbook — QuantBridge Sprint 9 Phase D

## 목표

QuantBridge 백엔드의 Prometheus metrics 를 Grafana Cloud Free 로 수집, 5 패널 대시보드 + 주문 거부율 alert 1개를 구성한다.

관측 대상 5 metrics (단일 프로세스 REGISTRY, Sprint 10+ 에서 multi-process 검토):

| Metric                             | Type      | Labels                 | Source                                            |
| ---------------------------------- | --------- | ---------------------- | ------------------------------------------------- |
| `qb_backtest_duration_seconds`     | Histogram | —                      | `tasks/backtest.py::run_backtest_task`            |
| `qb_order_rejected_total`          | Counter   | `exchange`, `reason`   | `trading/service.py::OrderService.execute`        |
| `qb_kill_switch_triggered_total`   | Counter   | `trigger_type`         | `trading/kill_switch.py::KillSwitchService`       |
| `qb_ccxt_request_duration_seconds` | Histogram | `exchange`, `endpoint` | `trading/providers.py` via `ccxt_timer`           |
| `qb_active_orders`                 | Gauge     | —                      | `trading/service.py` inc + `tasks/trading.py` dec |

**민감 label 없음** (user_id / strategy_id / api_key 금지) — `/metrics` 는 public 노출 가능.

---

## Grafana Cloud Free 한도 (2026 기준)

- Metrics: 10k active series (ingestion)
- Logs: 50 GB
- Traces: 50 GB
- 3 users
- 14일 metrics retention

QuantBridge 5 metrics x label cardinality 는 <50 series 로 10k 여유에 충분하다.

---

## 단계

### 1. 계정 생성

1. https://grafana.com/products/cloud/ → "Start for free"
2. 조직 이름 임의 설정, region `US Central` 권장 (latency 최소화)
3. 이메일 인증 완료 → Stack 자동 생성

### 2. Prometheus remote_write 자격 획득

1. Grafana 포털 → 좌측 메뉴 `Connections` → `Add new connection` → `Prometheus`
2. "Hosted Prometheus Metrics" 선택
3. 아래 4개 값을 메모:
   - **Remote write URL**: e.g. `https://prometheus-prod-XX-prod-us-central-0.grafana.net/api/prom/push`
   - **Username**: stack ID (숫자)
   - **API Key**: `Generate now` → role `MetricsPublisher` → 1회만 노출됨 (복붙)
   - **Grafana URL**: `https://<stack>.grafana.net`

### 3. 백엔드 `PROMETHEUS_BEARER_TOKEN` 생성

`/metrics` endpoint 는 bearer token 으로 보호된다. 강력한 무작위 토큰을 생성:

```bash
openssl rand -hex 32
# → e.g., 9a3f... (64 chars hex)
```

`.env.local` (또는 prod 환경변수):

```
PROMETHEUS_BEARER_TOKEN=9a3f...
```

백엔드 재시작 후 smoke test:

```bash
curl -s http://localhost:8000/metrics
# → 401 (토큰 없음)

curl -s -H "Authorization: Bearer 9a3f..." http://localhost:8000/metrics | grep -c "^# HELP qb_"
# → 5 (5개 metric)
```

### 4. 로컬/staging Prometheus 서버 배치

Grafana Cloud 는 직접 scrape 하지 않으므로 중간에 Prometheus 서버를 둔다.

**Docker 예시** (`prometheus.yml`):

```yaml
global:
  scrape_interval: 15s
  external_labels:
    cluster: "quantbridge-staging" # 환경 구분 label

scrape_configs:
  - job_name: "quantbridge-backend"
    bearer_token: "PASTE_YOUR_PROMETHEUS_BEARER_TOKEN"
    static_configs:
      - targets: ["host.docker.internal:8000"] # local dev
        labels:
          service: "backend"

remote_write:
  - url: "https://prometheus-prod-XX-prod-us-central-0.grafana.net/api/prom/push"
    basic_auth:
      username: "YOUR_STACK_ID"
      password: "YOUR_API_KEY"
```

**docker-compose** 확장 예시 (선택):

```yaml
services:
  prometheus:
    image: prom/prometheus:v2.53.0
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml:ro
    ports:
      - "9090:9090"
```

기동 후 `http://localhost:9090/targets` 에서 `quantbridge-backend` 가 `UP` 상태인지 확인.

### 5. 대시보드 5 패널

Grafana Cloud → `Dashboards` → `New` → `Add visualization`.

#### 패널 1. Backtest duration p95 (Time series)

```promql
histogram_quantile(
  0.95,
  sum(rate(qb_backtest_duration_seconds_bucket[5m])) by (le)
)
```

- Unit: seconds
- Threshold: 120s (주황), 300s (빨강)

#### 패널 2. Order rejected rate by reason (Time series / stacked)

```promql
sum(rate(qb_order_rejected_total[5m])) by (reason)
```

- Legend: `{{reason}}`
- Stack series: normal

#### 패널 3. Kill Switch activations (Stat)

```promql
sum(increase(qb_kill_switch_triggered_total[1h])) by (trigger_type)
```

- Display: single stat with sparkline
- Colors: `cumulative_loss=red`, `daily_loss=orange`, `api_error=yellow`

#### 패널 4. CCXT p95 latency by exchange/endpoint (Heatmap or Time series)

```promql
histogram_quantile(
  0.95,
  sum(rate(qb_ccxt_request_duration_seconds_bucket[5m])) by (le, exchange, endpoint)
)
```

- Unit: seconds
- Legend: `{{exchange}} / {{endpoint}}`
- 경보 힌트: `create_order` p95 > 2s 시 네트워크/exchange 문제

#### 패널 5. Active orders (Gauge / Time series)

```promql
qb_active_orders
```

- Unit: short
- 드리프트(crash로 gauge 증감이 맞지 않음) 모니터링용 — H2+ 에서 DB count 로 resync 추가 예정.

### 6. Alert rule: 주문 거부율 > 10%

Grafana Cloud → `Alerting` → `Alert rules` → `New rule`.

- **Name**: `QuantBridge / Order rejected rate > 10%`
- **Query (A)**:
  ```promql
  (
    sum(rate(qb_order_rejected_total[5m]))
  )
  /
  (
    sum(rate(qb_order_rejected_total[5m]))
    +
    sum(rate(qb_ccxt_request_duration_seconds_count{endpoint="create_order"}[5m]))
  )
  ```
  rationale: 거부 / (거부 + 성공 주문) 의 비율. `qb_ccxt_request_duration_seconds_count{endpoint="create_order"}` 는 성공한 exchange submit 수 (proxy).
- **Condition**: `A > 0.1` (10%)
- **For**: `5m` (5분 지속 시 fire)
- **Notifications**: Slack / Discord / 이메일 웹훅 (사용자 환경에 맞게)
- **Labels**: `severity=warning`, `service=backend`

### 7. 검증 체크리스트

- [ ] `curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/metrics` → HTTP 200, `# HELP qb_` 5개 이상
- [ ] Prometheus `http://localhost:9090/targets` → `quantbridge-backend UP`
- [ ] Grafana Cloud `Explore` → `qb_backtest_duration_seconds_count` 쿼리 → 데이터 포인트 수신
- [ ] 테스트 reject 이벤트 (e.g., leverage=50 POST /api/v1/orders) → 1~2분 후 패널 2 에 spike
- [ ] Alert rule 상태 `OK` → 인위적으로 trigger (leverage cap 연속 호출) → `Firing`

---

## 보안 참고

| 항목                      | 값                     | 주의                                           |
| ------------------------- | ---------------------- | ---------------------------------------------- |
| `PROMETHEUS_BEARER_TOKEN` | `openssl rand -hex 32` | `.env.local` / prod 환경변수. git commit 금지. |
| Grafana Cloud API Key     | Grafana 포털에서 발급  | bearer token 과 **다른 값**. rotate 가능.      |
| 민감 label                | 없음                   | metrics 는 public noise OK (CSO-review PASS).  |
| Remote write URL          | 공개 endpoint          | TLS 필수 (https).                              |

토큰 rotation 절차:

1. 새 토큰 생성 후 `PROMETHEUS_BEARER_TOKEN` 업데이트
2. Prometheus `scrape_configs.bearer_token` 동시 교체
3. 백엔드 재시작 → Prometheus reload (`SIGHUP`)
4. 구 토큰은 즉시 무효 (grace 불필요)

### /metrics 네트워크 보호

`/metrics` endpoint 는 `bearer_token` 인증 외에 rate limit 가 없습니다. `generate_latest()` 는 모든 metric 을 매 요청마다 직렬화하므로 외부 스캐너가 폭주 호출할 경우 성능 영향이 있습니다. 프로덕션에서는 아래 중 하나 이상 권장:

- **Private network**: Grafana Agent 를 QuantBridge 백엔드와 동일 VPC/Kubernetes 네임스페이스에 배치하고 `/metrics` 를 외부 노출하지 않음.
- **Nginx rate limit**: `limit_req zone=metrics burst=5 nodelay;` (upstream 앞단)
- **Cloudflare WAF rule**: `/metrics` path 에 대해 rate limit + allowed IP (Grafana Cloud IP 목록) 제한.
- **bearer_token rotation**: 90일 주기 rotation (이미 §토큰 생성/로테이션 에 기술).

위 방어가 미구현 상태에서는 Grafana Cloud Free 의 공개 Prometheus remote_write endpoint 에 직접 push 하는 pattern (QuantBridge → Grafana agent 없이) 을 고려.

---

## 추후 확장 (Sprint 10+)

- Multi-process mode: Celery worker 다중 프로세스에서 metric aggregate (prometheus_client `multiprocess` module)
- OpenTelemetry tracing 연동: 주문 실행 trace → Grafana Tempo
- Logs shipping: `docker compose` structured logs → Grafana Loki
- Alert rule 추가: Kill Switch fire, CCXT p95 latency > 2s, active_orders drift (Gauge vs DB count)
