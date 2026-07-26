# QuantBridge — 배포 계획 (Draft)

> **상태:** Draft — 프로덕션 결정 미정 항목 다수 `[확인 필요]`.
> **목적:** 배포 옵션 비교 + 결정 게이트 정리.
> 의존: [`../04_architecture/system-architecture.md`](../04_architecture/system-architecture.md), [`../06_devops/docker-compose-guide.md`](../06_devops/docker-compose-guide.md)

---

## 1. 현재 상태

- 인프라: **dev only** — `docker compose up -d` (DB + Redis)
- 배포 환경: 미구축
- CI: GitHub Actions (lint/type/test), CD 미설정

---

## 2. 배포 옵션 비교

| 항목 | A. Vercel + Cloud Run | B. Docker + K8s (GKE/EKS) | C. Fly.io |
|------|------------------------|-----------------------------|-----------|
| Frontend (Next.js 16) | Vercel native | Cloud Build → K8s deployment | Fly machines |
| Backend (FastAPI) | Cloud Run (auto-scale) | K8s deployment + HPA | Fly machines |
| Celery Worker | Cloud Run job 또는 Compute Engine | K8s deployment | Fly machines |
| DB (PostgreSQL + TimescaleDB) | Cloud SQL (TS extension 제한) 또는 self-host | self-host on K8s 또는 Cloud SQL | Fly Postgres + TS extension |
| Redis | Memorystore | self-host 또는 ElastiCache | Fly Redis |
| 운영 부담 | 낮음 | 높음 | 중간 |
| 비용 (MAU 1K 기준) | $50~150/월 [가정] | $200~500/월 [가정] | $30~100/월 [가정] |
| TimescaleDB 호환 | ⚠️ Cloud SQL extension 제한 | ✅ self-host 자유 | ✅ Fly Postgres TS extension |
| MVP 적합도 | ⭐⭐⭐⭐ | ⭐⭐ (오버엔지니어링) | ⭐⭐⭐⭐ |

> 비용은 모두 [가정] — 실 트래픽으로 측정 후 갱신.

---

## 3. 결정 게이트

```mermaid
flowchart TB
    Start[배포 결정 시작]
    MAU{MAU 1K 이전?}
    Simple[A 또는 C]
    Heavy[B K8s 검토]
    TS{TimescaleDB 필수?}
    SelfHost[self-host PG 또는 Fly]
    Managed[Cloud SQL + Citus 검토]

    Start --> MAU
    MAU -->|Yes| Simple
    MAU -->|No (성장 후)| Heavy
    Simple --> TS
    Heavy --> TS
    TS -->|Yes (Sprint 5+)| SelfHost
    TS -->|No| Managed
```

### 의사결정 트리거

- **MAU 1K** 이전: 단순 옵션 (A/C) — 운영 부담 최소화
- **MAU 1K~10K**: A/C 유지, scaling 검증
- **MAU 10K+** 또는 **multi-region**: K8s 검토

> 현재 단계: pre-MVP — 옵션 A 또는 C 우선 검토.

---

## 4. DB 호스팅 옵션

| 옵션 | TimescaleDB | 비용 | 운영 |
|------|-------------|------|------|
| Self-hosted (Compute Engine + Docker) | ✅ 자유 | 저 | 백업/모니터링 직접 |
| Cloud SQL (GCP) | ⚠️ 제한 (extension 미공식) | 중 | managed |
| Neon (Serverless PG) | ❌ TS 미지원 | 저 | managed |
| Fly Postgres | ✅ TS extension 지원 | 저 | managed (Fly 종속) |
| TimescaleDB Cloud (공식) | ✅ 최적 | 중~고 | managed |

**현재 결정:** TimescaleDB hypertable 필수 (REQ-MD-01) → Self-hosted 또는 Fly Postgres 또는 TimescaleDB Cloud `[확인 필요]`.

> Sprint 5 시점에 OHLCV 실데이터 적재 시 측정 후 결정.

---

## 5. Secret 관리

| 옵션 | 장점 | 단점 |
|------|------|------|
| 배포 플랫폼 대시보드 (Vercel/Fly/Cloud Run secrets) | 간단, 통합 | 플랫폼 종속 |
| HashiCorp Vault | 강력, 회전 정책 | 운영 부담 |
| GCP Secret Manager / AWS Secrets Manager | managed, IAM 통합 | 플랫폼 종속 + 비용 |

**현재 권장:** 플랫폼 대시보드 (`[확인 필요]`). 이유:
- MVP 단계 단순 운영
- ENCRYPTION_KEY 등 회전이 필요한 키만 별도 관리 검토

> 거래소 API Key는 환경 변수가 아니라 사용자별 DB 컬럼 (AES-256). ENCRYPTION_KEY만 환경 변수.

---

## 6. CDN / Edge

- Frontend (Next.js 16): Vercel Edge Network 또는 Cloudflare CDN `[확인 필요]`
- 정적 자산: Next.js 자체 처리 (이미지 최적화 포함)

---

## 7. 도메인 / TLS

- 도메인: 미정 `[확인 필요]`
- TLS: Vercel/Fly/Cloud Run 자동, 또는 Cloudflare 통합
- HTTPS 강제 (HSTS) — 표준 적용 예정

---

## 8. 배포 자동화

### 계획

- **GitHub Actions trigger:** push to `main` → staging deploy
- **Production:** tag `v*.*.*` → manual approval → deploy
- **Migration:** Docker entrypoint에서 `alembic upgrade head` 자동
- **Rollback:** 배포 플랫폼 1-click rollback + DB downgrade 절차 별도

### Migration 절차

> 데이터 파괴 변경은 2단계 배포 (`.ai/stacks/fastapi/backend.md` §9):
> 1. 코드에서 사용 중단
> 2. 다음 배포에서 컬럼/테이블 삭제

---

## 9. 환경 분리

| 환경 | 도메인 | DB | Clerk | 비고 |
|------|--------|----|----|-----|
| local | localhost | docker compose | dev (test keys) | 개발자 머신 |
| staging | TBD | TBD | dev 또는 별도 | PR preview 대안 검토 |
| production | TBD | TBD | prod (live keys) | 실 사용자 |

> staging 도입 시점 `[확인 필요]` — 보통 베타 출시 시점.

---

## 10. 결정 대기 항목 (`[확인 필요]`)

| 항목 | 의존 sprint | 책임 |
|------|--------------|------|
| 배포 플랫폼 (A/B/C) | Sprint 7~8 | 사용자 결정 |
| DB 호스팅 (Self/Fly/TSCloud) | Sprint 5+ OHLCV 측정 후 | 사용자 결정 |
| Secret 관리 도구 | Sprint 7+ | 사용자 결정 |
| 도메인 | Sprint 7+ | 사용자 결정 |
| Staging 도입 시점 | Sprint 8+ | 사용자 결정 |
| Production 모니터링 도구 | [`./observability-plan.md`](./observability-plan.md) | 사용자 결정 |

---

## 11. 참고

- ADR-001 기술 스택: [`../dev-log/001-tech-stack.md`](../dev-log/001-tech-stack.md)
- Compose: [`../06_devops/docker-compose-guide.md`](../06_devops/docker-compose-guide.md)
- Observability: [`./observability-plan.md`](./observability-plan.md)
- Runbook: [`./runbook.md`](./runbook.md)

---

## 변경 이력

- **2026-04-16** — Draft 초안 작성 (Sprint 5 Stage A)
