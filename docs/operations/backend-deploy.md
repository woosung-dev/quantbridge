# QuantBridge — BE 배포·롤백 런북 (ADR-043 · 2026-09-10)

> **대상:** `truewords-oracle` 의 `~/quantbridge`. Celery 서비스 4개(워커 3 + beat 1) + db + redis 는 compose,
> API 는 호스트 `quantbridge-api.service`([BL-865] 컨테이너화 대기).
> **정본:** 이 문서 + `tools/scripts/deploy.sh` + `tools/scripts/host-bootstrap.sh` + `infra/compose/docker-compose{,.server}.yml`.
> **원문 tombstone:** 소크 런북판(pin·창·3층 compose · 85줄) = `git show c488b545:docs/operations/backend-deploy.md`.

## 1. 이 배포가 무엇인가 (그리고 무엇이 아닌가)

**맞다** — main 에 머지된 커밋의 **이미지**(`ghcr.io/woosung-dev/quantbridge-backend:sha-<7>`, `release.yml` 이 만든다)를
서버가 받아 워커 4개를 하나씩 교체하고, 호스트 API 를 재시작하는 절차다. **자동이다** — 머지마다 `deploy.sh <sha>` 가 돈다(PR-3 이후).

**아니다** — 서버에서 빌드하지 않는다(2 OCPU 공유). DDL 을 자동으로 넣지 않는다. 소크 창·pin 은 없다([ADR-043]).

## 2. 구조

```text
main 머지 ──release.yml(arm64)──▶ GHCR :sha-<7>
                 │
                 └──deploy job(ssh, forced command)──▶ ~/quantbridge/tools/scripts/deploy.sh <sha>
      ① git pull --ff-only            (compose·스크립트만 — 코드는 이미지 안)
      ② 24h 무실격                     trading.live_signal_sessions.deactivated_reason ∈ 8종 → 1건이라도 있으면 rc 2 + 텔레그램
      ③ DDL 대조                       이미지 `alembic heads` == DB `alembic_version` ? 아니면 rc 2 「DDL 필요」 + 텔레그램
      ④ docker compose pull
      ⑤ 워커 롤링                      beat → optimizer-heavy → worker → ws-stream (`up -d --no-deps`, stop_grace_period 준수)
      ⑥ FE up -d                       (`docker-compose.frontend.yml`, 같은 sha 태그)
      ⑦ 호스트 API                     uv sync → `import src.main` probe → systemctl --user restart quantbridge-api.service
      ⑧ /health → docker-reclaim.sh --confirm → 텔레그램 요약
```

- 서버 compose 호출 = `docker compose --project-directory . -f infra/compose/docker-compose.yml -f infra/compose/docker-compose.server.yml`
  (`--project-directory` 는 스크립트가 넣는다 — 손으로 칠 때만 빼먹지 마라, ADR-029).
- 매매는 재시작을 견딘다 — `acks_late`·`reject_on_worker_lost`·ws lease 60s·reconcile 5분. 2026-09-03 호스트 재부팅 실측.

## 3. 사람이 하는 것

| 상황 | 명령 |
| --- | --- |
| 상태 보기 | `tools/scripts/deploy.sh --status` |
| 무엇이 바뀔지만 | `tools/scripts/deploy.sh --dry-run <sha>` |
| **DDL 이 있는 배포**(자동이 rc 2 로 멈췄다) | `tools/scripts/deploy.sh --migrate <sha>` — `db-backup.sh run` 선행 → 이미지 안 `run_alembic_with_lock` → 재확인. ★**매번 명시 승인**([BL-743]) |
| 롤백 | `tools/scripts/deploy.sh <이전 sha>` — 이미지 3세대는 서버에 남아 있고(`docker-reclaim`) 그 밖은 GHCR 에서 받는다 |
| 호스트 전용 설정(재구축 시) | `tools/scripts/host-bootstrap.sh --install` — `/etc/docker/daemon.json`(json-file 10m×3) · journald `SystemMaxUse=500M`. `--status` 가 드리프트를 잰다 |
| 회수 타이머 | `tools/scripts/docker-reclaim.sh --install`(주간) |

★**의존성을 넘는 롤백도 된다** — 이미지에 구워져 있다. 종전 「pyproject 를 넘는 롤백은 이 경로로 할 수 없다」는 사라졌다.
★**DB 롤백**(백업 복원 · alembic downgrade)은 종전대로 **[확인 필요] 절차**다 — 원문 tombstone 의 §3.4⑶⑷ 를 보되 실행 전 별도 승인.

## 4. 검증 (배포 직후)

```bash
ssh truewords-oracle 'bash -lc "cd ~/quantbridge && tools/scripts/deploy.sh --status"'
# 기대: 워커 4개 image = ghcr.io/…:sha-<배포 sha> · alembic head == DB · 24h 실격 0 · API active · /health 200
```

## 5. 함정 (전부 실측)

- ★**ssh 는 `bash -lc` 로 감싼다** — 비로그인 셸엔 `uv` PATH 가 없다.
- ★**compose 프로젝트명은 체크아웃 basename 에서 파생한다**(`~/quantbridge` → `quantbridge`). FE 는 `quantbridge_quantbridge` 네트워크를 하드코딩한다.
  진짜 판별자 = `docker network ls`.
- ★**`.env` 의 인라인 주석을 값에 섞지 마라** — 401 이 아니라 500 이 된다(`frontend-deploy.md`).
- ★**`/healthz` 가 아니라 `/health`** — `/healthz` 는 celery inspect 12초 상한에 걸려 503 이 정상이다.
- ★**GHCR 패키지가 private 이면 pull 이 막힌다** — 첫 push 뒤 패키지 설정에서 public 확인(레포가 공개라 노출 증가 0).
- ★**자동 배포가 멈춘 것은 실패가 아니다** — rc 2 = 「24h 실격 있음」 또는 「DDL 필요」. 텔레그램에 사유가 온다. 후자는 §3 의 `--migrate`.

## 6. 관련 문서

[ADR-043](../adr/043-deploy-pipeline-images-replace-soak-pin.md) · [frontend-deploy.md](./frontend-deploy.md) · [better-auth-setup.md](./better-auth-setup.md) · [ADR-033](../adr/033-db-hosting-self-host-timescaledb.md) · [ci-cd.md](../development/ci-cd.md)
