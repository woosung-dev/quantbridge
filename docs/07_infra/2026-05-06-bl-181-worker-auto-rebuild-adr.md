# 본 ADR — BL-181 Sprint 38 Docker worker auto-rebuild on src 변경 결정 (isolated mode 한정)

# BL-181 Docker worker auto-rebuild on src 변경 — ADR (Sprint 38)

| 항목      | 값                                                            |
| --------- | ------------------------------------------------------------- |
| 일자      | 2026-05-06                                                    |
| 스프린트  | 38                                                            |
| 워커      | C (cmux 자율 병렬)                                            |
| 결정자    | woo sung                                                      |
| 상태      | Accepted                                                      |
| 관련      | Sprint 35 BL-178, Sprint 37 BL-188a, Sprint 38 plan v3 §C     |

## 배경

Sprint 35 BL-178 / Sprint 37 BL-188a 에서 Docker worker stale 재발 패턴 발견. PR merge → host 의 backend src 는 최신이지만, `quantbridge-worker` 컨테이너는 image build 시점 코드 그대로 → "왜 fix 가 적용 안 됐지" 사용자 hotfix 분량 +30 분/회.

dogfood Day 1~7 에 worker 관련 부하가 늘면서 빈도 증가. 매 PR 마다 `make up-isolated-build` 을 강제하기엔 cycle time 영향 크다.

## 결정

**isolated mode 한정** — `docker-compose.isolated.yml` 의 3 서비스 (`backend-worker`, `backend-ws-stream`, `backend-beat`) 에 다음 override 적용.

1. `volumes: ./backend/src:/app/src:ro` bind-mount 추가 — host src 가 SoT, container 는 read-only 마운트.
2. `command:` 를 `uv run watchfiles --filter python "<celery 명령>" /app/src` 로 wrap — `*.py` 변경 감지 시 watchfiles 가 자동으로 자식 프로세스 재시작.
3. `Makefile up-isolated-watch` 신규 타깃 — `docker compose -f ... -f docker-compose.isolated.yml up -d --build backend-worker backend-ws-stream backend-beat`.
4. `scripts/sentinel_bl181_worker_reload.sh` — backend src 안에 marker 작성 → 5s 대기 → `docker logs` 에서 reload 흔적 grep → exit 0/1.

## ws-stream prefork fact 정정 (codex iter 2 P1 #14)

codex iter 2 P1 #14 에서 "ws-stream solo pool" 가정 → wrong.
실제 base `docker-compose.yml` 검증 결과:

```
backend-ws-stream:
  command: uv run celery -A src.tasks.celery_app worker -Q ws_stream --pool=prefork --concurrency=2 --loglevel=info
```

Sprint 24 BL-012 에서 `--pool=solo` 의 한계 (worker_process_shutdown signal 미수신) 해소 위해 prefork 복귀했음. 본 ADR override 도 동일하게 `--pool=prefork --concurrency=2` 유지.

## container_name 충돌 — base + isolated 동시 운영 금지

base mode (`make up`) + isolated mode (`make up-isolated`) 동시 운영 시 `quantbridge-worker` / `quantbridge-ws-stream` / `quantbridge-beat` / `quantbridge-db` / `quantbridge-redis` container_name 충돌 (base / isolated 가 동일 이름 고정).

본 sprint scope = **isolated mode only auto-rebuild**. base mode 는 production 정합 (no bind-mount, image rebuild 의무) 그대로 유지. `make up` 과 `make up-isolated*` 은 mutually exclusive.

`docker ps` 로 base 컨테이너 잔존 확인 후 `make down` 으로 정리한 다음 `make up-isolated-watch` 진입할 것.

## isolated.yml 자체가 watch 모드 — 의도된 디자인

`docker-compose.isolated.yml` 안에 watchfiles override 와 bind-mount 를 직접 넣었으므로 `make up-isolated` / `make dev-isolated` 도 watchfiles 동작. 이는 의도. 본 sprint 의 디자인 결정은 "**isolated mode 전체가 auto-rebuild 한다**" — base mode 는 production 정합 그대로. `make up-isolated-watch` 는 단지 3 서비스만 build/up 하는 alias (DB/Redis 변경 X 시 빠른 부팅).

만약 향후 "watch opt-in" 을 위해 모드 분리가 필요하면 별도 override file (`docker-compose.watch.yml`) 로 빼고 `up-isolated-watch` 만 그것을 merge 하도록 변경 가능 (별도 ADR).

## OUT of scope (별도 ADR 필요)

- `docker-compose.yml` (production) 변경 — production 배포 환경에서는 git post-merge hook 또는 CI/CD 가 자동 image rebuild 수행하는 게 맞음. compose file 직접 변경 X.
- GH Actions / git post-merge hook 자동 rebuild — Sprint 39+.
- backend host uvicorn dev 서버 reload — 이미 `uvicorn --reload` 옵션 존재.
- pip install / `uv add` 후 reload — 의존성 변화는 image rebuild 의무. 본 ADR 은 `*.py` source change 한정.

## 검증

- `docker compose -f docker-compose.yml -f docker-compose.isolated.yml config` parse OK.
- `make up-isolated-watch` 부팅 5 분 내 success (3 서비스 healthy / running).
- `bash scripts/sentinel_bl181_worker_reload.sh` exit 0 (marker 변경 → reload 감지).

## 한계

- bind-mount RO — host 가 SoT 라 read-only 안전, 단 컨테이너 안에서 src 에 write 시도하면 PermissionError.
- `uv add` / pip 신규 패키지는 watchfiles reload 가 아니라 image rebuild 가 의무 (본 ADR scope 외).
- watchfiles 가 prefork worker 의 자식 프로세스 graceful shutdown 을 보장하지 않음 — celery task 가 in-flight 일 때 reload 발생 시 task 손실 가능. 단 isolated mode 는 dogfood 전용이라 in-flight task 분량 미미.
- macOS Docker Desktop bind-mount 의 inotify 신호 latency (보통 1~3 s) — sentinel 의 5s sleep 으로 흡수.
