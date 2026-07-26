# BL-181 Docker worker auto-rebuild on src 변경 — Plan (Sprint 38 Worker C)

## TDD 모드
**동시 (concurrent)** — infra change. pure shell + YAML + Makefile + sentinel script. hook/state/effect 없음. 단위 테스트 대상 없고, 검증은 docker compose config + 부팅 + sentinel exit 0 으로 대체.

## 목표
isolated mode 한정으로 backend src 의 host 변경이 worker / ws-stream / beat 컨테이너 안에 자동 반영되도록 한다 (수동 rebuild 제거).

## 단계 분해

1. **watchfiles dep 검증/추가** — `backend/pyproject.toml` main group 에 `watchfiles>=1.1.1` 보장. `uv sync --all-extras --dev` 통과.
2. **`docker-compose.isolated.yml` 3 서비스 override** — `backend-worker`, `backend-ws-stream`, `backend-beat` 각각에 `volumes: ./backend/src:/app/src:ro` bind-mount + `command:` 를 `uv run watchfiles --filter python "<celery cmd>" /app/src` 로 wrap.
3. **`Makefile up-isolated-watch` 신규 타깃** — `docker compose -f docker-compose.yml -f docker-compose.isolated.yml up -d --build backend-worker backend-ws-stream backend-beat`.
4. **`scripts/sentinel_bl181_worker_reload.sh`** — backend src 에 marker 작성 → 5 초 대기 → worker logs 에서 reload 흔적 grep → exit 0/1.
5. **ADR `docs/07_infra/2026-05-06-bl-181-worker-auto-rebuild-adr.md`** — 결정 / ws-stream prefork fact 정정 / container_name 충돌 명시 / out-of-scope.
6. **부팅 검증** — `make down-isolated || true` → `make up-isolated-watch` → 30s sleep → 컨테이너 UP.
7. **sentinel 검증** — `bash scripts/sentinel_bl181_worker_reload.sh` exit 0.
8. **Evaluator dispatch** — `superpowers:code-reviewer` cold-start, isolation=worktree.

## Out of scope
- production `docker-compose.yml` 변경 (별도 ADR 필요)
- GH Actions / git post-merge hook 자동 rebuild (Sprint 39+)
- backend host uvicorn dev 서버 reload (이미 `--reload` 옵션 있음)
- pip install / uv add 후 reload (image rebuild 가 의무)

## 검증 기준
- `docker compose -f docker-compose.yml -f docker-compose.isolated.yml config` parse OK
- `make up-isolated-watch` 부팅 5 분 내 success
- `bash scripts/sentinel_bl181_worker_reload.sh` exit 0
- Evaluator cold-start PASS
- codex G.4 P1 0 critical
