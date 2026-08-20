# Step 1: backup-prove-target

## 읽어야 할 파일

- `tools/scripts/db-backup.sh` — `_wire_docker`(104~120행) · `_docker_inspect`(122) ·
  `_psql`(126) · ★**`_prove_target`(135~204행)** · `_run` 진입부(220~226행)
- `apps/api/tests/scripts/test_db_backup_target.py` — **앞 step 이 만든 파일. 이어 붙인다**

## 배경

★**`_prove_target` 이 이 스크립트에서 가장 중요한 절이다.** base/isolated/soak compose 3벌이
`container_name: quantbridge-db` 를 **공유**하므로 「지금 떠 있는 것」이 백업 대상이 된다.
격리/테스트 DB 를 떠 놓고 백업을 돌리면 **정상으로 보이는 쓸모없는 덤프**가 쌓인다 —
조용한 실패라 사고가 날 때까지 아무도 모른다.

2026-08-16 codex 적대 리뷰가 여기서 P1 을 잡았다: 포트만 대조하면 **한 컨테이너 안에 DB 가
여럿일 때 포트는 같은데 이름이 다를 수 있다.** 그래서 `DATABASE_URL` 의 DB 이름까지 본다.
그 수리를 지키는 테스트가 지금 0건이다.

★그리고 이 스크립트의 **최대 위험**은 백업 자체가 아니라 컨테이너 생명주기다 —
`up`/`down`/`restart`/`stop`/`start` 는 [BL-003] 24시간 소크 창을 **끊는다**. 백업 한 번이
소크 며칠을 지운다. 그래서 「docker 인자 전수 기록」 축이 필요하다.

## 작업

`apps/api/tests/scripts/test_db_backup_target.py` 에 **`_prove_target` 거부 행렬 + docker 인자
금지어 0회**를 이어 붙여라. 앞 step 의 `_env`/`run` 헬퍼를 재사용한다(새 헬퍼 모듈 금지).

### 호출 방식 — `docker` PATH 스텁

`db-backup.sh run` 을 부르면 `_wire_docker` → `_prove_target` 순으로 간다. `docker` 를 스텁으로
갈아끼워 첫 인자로 분기시켜라. **스텁은 받은 인자 전부를 로그 파일에 append 한다.**

```python
def _docker_stub(tmp_path, *, status="running", image="timescale/timescaledb:2.17.2-pg16",
                 env_lines="POSTGRES_USER=quantbridge\nPOSTGRES_DB=quantbridge",
                 psql_out="quantbridge|2.17.2|16.4", psql_rc=0, port="0.0.0.0:5432") -> Path:
    """`docker` 를 갈아끼운 PATH 디렉터리. 인자는 tmp_path/docker-args.log 에 전수 기록."""
```

스텁이 답해야 하는 호출은 넷뿐이다 — 스크립트를 읽고 **정확한 `--format` 문자열**에
맞춰라(추측하지 말고 `_docker_inspect` 호출부를 그대로 봐라):

- `docker version --format …` → 아무 문자열 + exit 0 (`_wire_docker` 의 데몬 도달 확인)
- `docker inspect <이름> --format '{{.State.Status}}'` → `status`
- `docker inspect <이름> --format '{{.Config.Image}}'` → `image`
- `docker inspect <이름> --format '{{range .Config.Env}}{{println .}}{{end}}'` → `env_lines`
- `docker exec <이름> psql …` → `psql_out` / `psql_rc`
- `docker port <이름> 5432/tcp` → `port`

★`_docker_inspect` 는 실패해도 `|| true` 라 **빈 문자열 + rc 0** 이다 — 「컨테이너 없음」은
스텁이 `.State.Status` 에 **빈 문자열**을 내는 것으로 만든다.

`QB_ENV_FILE` 파일에는 `DATABASE_URL=postgresql+asyncpg://u:p@localhost:5432/quantbridge` 를 쓴다.

### 최소한 이 아홉을 덮어라 (앞 step 5건과 합쳐 ≥9)

`_prove_target` 거부 — **rc 값까지 정확히 단언해라.** rc=2 는 「전제 미충족(측정 못 함)」,
rc=1 은 「실패·거부」이고 둘은 뜻이 다르다:

1. **컨테이너 없음 → rc=2** (`.State.Status` 빈 문자열)
2. **running 이 아님 → rc=2** (`exited`)
3. ★**이미지가 timescaledb 계열이 아님 → rc=1** (`postgres:16`) — 덤프는 만들어지지만
   hypertable 이 없는 다른 DB 다
4. **`POSTGRES_USER`/`POSTGRES_DB` 를 못 읽음 → rc=2** (env 줄이 비었을 때)
5. **psql 이 실패 → rc=2** (`psql_rc=1`)
6. **`current_database()` 불일치 → rc=1** (`psql_out` 의 첫 칸이 다른 이름)
7. **timescaledb 확장 없음 → rc=1** (`psql_out` 의 둘째 칸이 빈 문자열)
8. **`DATABASE_URL` 포트 불일치 → rc=1** (published port 5432 인데 URL 은 `:5433/`)
9. ★**포트는 같은데 DB 이름이 다름 → rc=1** (URL 이 `:5432/another_db`) —
   **2026-08-16 codex P1 의 수리 축이다.** stderr 에 `앱이 쓰지 않는 DB` 가 실린다
10. **양성 대조 — 전부 맞으면 stdout 에 `대상 증명 ✓`** 가 찍힌다. ★그 뒤 `_run` 이
    pg_dump 로 계속 가서 결국 실패하는 것은 **정상이다** — rc 를 단언하지 말고
    `대상 증명 ✓` 문자열만 단언해라 (덤프 경로는 이 lane 범위 밖)
11. ★**docker 인자 금지어 0회** — 위 케이스 전부를 돈 뒤 `docker-args.log` 를 읽어
    첫 인자가 `up`·`down`·`start`·`stop`·`restart` 인 호출이 **한 건도 없다**를 단언해라.
    그리고 **양성 대조**로 로그가 비어 있지 않은지(≥1행) 함께 단언해라 —
    빈 로그에도 「금지어 0회」는 참이다

## Acceptance Criteria

```bash
cd apps/api && uv run --env-file .env.local pytest tests/scripts/test_db_backup_target.py -q
cd apps/api && test "$(uv run --env-file .env.local pytest tests/scripts/test_db_backup_target.py --collect-only -q 2>/dev/null | grep -c '::')" -ge 9
cd apps/api && uv run ruff check tests/scripts/
```

## 자기 점검

1. 위 AC 를 직접 실행해 green 을 확인한다. `status` 를 `completed` 로 바꾸지 마라.
2. ★**스텁이 실제로 걸렸는지 확인해라** — `docker-args.log` 가 생겼는지 본다.
   진짜 `docker` 가 없는 머신에서는 `_wire_docker` 가 sudo 를 찾다 rc=2 로 죽어 **모든
   케이스가 우연히 rc=2 로 통과**한다. 그것이 이 lane 의 가장 큰 위양성이다.
   3·6·7·8·9 가 **rc=1** 이라는 단언이 그 위양성을 갈라 준다 — 반드시 rc 를 정확히 단언해라.
3. 사람 개입이 필요하면 `status:"blocked"` 와 `blocked_reason` 을 쓰고 즉시 중단한다.

## 금지사항

- `tools/scripts/db-backup.sh` 를 **수정하지 마라**
- ★**`--install` / `--uninstall` / `verify-restore` 본체를 실행하지 마라.** 이유: 전자 둘은
  실행자의 systemd user 디렉터리에 쓰고, 후자는 throwaway DB 를 만들고 지운다.
  스텁 깊이가 판정력보다 커진다
- ★**진짜 docker 데몬에 닿게 하지 마라** — 반드시 PATH 스텁을 통해라. 진짜 컨테이너
  `quantbridge-db` 가 이 머신에서 돌고 있을 수 있고, 소크 창이 그 위에 있다
- `QB_BACKUP_DIR` 을 `/opt/backups`(기본값)로 두지 마라 — 반드시 `tmp_path` 아래로
- `sudo` 를 요구하는 상태를 만들지 마라 — `QB_BACKUP_DIR` 은 쓰기 가능해야 한다
- `conftest.py`·공용 헬퍼 모듈·`shards.json`·`docs/**` 무변경. DB 픽스처 금지. 커밋하지 마라
- 앞 step 이 만든 테스트를 지우거나 이름을 바꾸지 마라 — AC 수집 하한이 누적값(≥9)이다
