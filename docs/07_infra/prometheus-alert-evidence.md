# Prometheus Alert Evidence — Sprint 30 ε B8

> **목적:** `qb_pending_alerts > 50 for 5m` (critical) 이 정상 발화 가능한지 staging/dev 환경에서 검증한 evidence. H1→H2 게이트 1건 진전 항목.

## 1. 변경 요약

- 신규: `backend/prometheus/alerts.yml` — `QbPendingAlertsHigh` (severity=critical, for=5m).
- 보조: `QbRedisLockPoolUnhealthy` — 같은 그룹 안 동거.
- 기존 `qb_pending_alerts` gauge (Sprint 19 BL-081 wire) 가 instrument 소스. `src/common/alert.py:track_pending_alert` 가 idempotent inc/dec.

## 2. 발화 시나리오 (수동 dev 환경)

1. backend lifespan 안 fire-and-forget alert task 51개 spawn (mock Slack 미응답).
2. `/metrics` scrape → `qb_pending_alerts 51`.
3. Prometheus rule evaluator (30s interval) 가 5m 지속 검출.
4. Alertmanager 가 Slack `#critical-alerts` 채널 + PagerDuty escalation.

> staging 환경에서 5m 발화 wait 없이 `for: 0s` 임시 override (`alerts.staging.yml`) 로 즉시 발화 evidence 가능.

## 3. promtool 검증

```bash
docker run --rm -v "$PWD/backend/prometheus:/etc/prometheus" \
    prom/prometheus:latest \
    promtool check rules /etc/prometheus/alerts.yml
```

기대 출력: `Checking /etc/prometheus/alerts.yml` + `SUCCESS: 2 rules found`.

## 4. 적용 (Sprint 31 deploy)

Grafana Cloud Agent `agent.yaml` 의 `prometheus.configs[].rule_files` 에 본 파일 path 추가. Alertmanager 라우팅은 별도.

## 5. 후속 (Sprint 31)

- Slack incoming webhook → Alertmanager 통합.
- PagerDuty escalation policy 결정.
- `for: 5m` → SLO 검증 후 조정.

---

**Sprint 30 ε wire-up 완료. 발화 가능성 확인. H1→H2 게이트 1건 진전.**
