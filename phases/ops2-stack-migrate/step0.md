# Step 0: migrate-target-proof

## 읽어야 할 파일

- `tools/scripts/soak-stack.sh:324-410` — `_migrate` **전량**(이번 테스트의 대상)과
  `:545` 의 dispatch 줄(`migrate` 의 인자 개수 계약)
- `apps/api/tests/scripts/test_db_backup_target.py` — **대상 증명**을 재는 선례(같은 계열이다)
- `apps/api/tests/scripts/test_soak_observe.py:19-31` — `tmp_path` 가짜 레포 관용구

## 배경

[BL-743] 이 만든 축이다 — 서버 DB 에 migration 이 도달하지 않던 경로의 수리 산출물이고,
채택된 형태가 **`soak-stack.sh migrate`(기본 dry-run · `--confirm` 이 집행)** 다.
`up` 자동 upgrade 는 **창 중 암묵 DDL** 이라 기각됐다.

★**이 명령은 `docs/status.md` 의 「비목표(불변) — 서버 소크 DB 에 alembic 적용」의 집행
도구다.** 사용자 결정 문구가 「migration 파일 생성·로컬/CI 적용 = 허용 / **서버 소크 DB 에
DDL 적용 = 매번 명시 승인**」이므로, **이 판정이 새면 승인 게이트가 새는 것과 같다.**

`_migrate` 가 지고 있는 fail-closed 셋(전부 codex 적대 리뷰가 만든 것):

- **여분 인자를 삼키지 않는다**(P2) — `migrate --confirm --typo` 가 조용히 집행되면
  운영자는 자기가 준 가드가 걸린 줄 안다
- **history 실패는 「대기 0」이 아니다**(P2) — `alembic history` 가 실패하면 목록이 비어
  보이는데 그것은 「적용할 게 없다」가 아니라 **재지 못한 것**이다
- ★**upgrade 대상이 정말 그 DB 인가를 미리 잰다**(P1) — 사후 재확인만으로는 부족하다.
  `.env.local` 이 다른 DB 를 가리키고 있으면 **그 DB 를 먼저 바꾼 뒤에야** 사후 검사가
  실패하고, **그 DDL 은 되돌릴 수 없다**

`soak-stack-test.sh` 는 [ADR-037] 이 철거했고 지금 테스트는 0건이다.

## 작업

`apps/api/tests/scripts/test_soak_stack_migrate.py` 를 신설한다.
★**`_migrate` 축만 덮는다** — `pin`/`up`/`down`/`commit` 은 이 lane 의 범위가 아니다.

### 호출 방식 (이 lane 의 유일한 방식)

`ROOT`/`SCRIPT_DIR` 파생 경로를 여러 개 쓰므로 **`tmp_path` 가짜 레포**를 만든다.

```
tmp/tools/scripts/soak-stack.sh            ← 진짜 파일 복사
tmp/tools/scripts/assert-main-checkout.sh  ← 스텁(기본 rc=0)
tmp/apps/api/.env.local                    ← 가짜: DATABASE_URL=postgresql+asyncpg://…:5433/quantbridge
tmp/bin/docker                             ← 스텁: `exec … psql` 은 revision, `port` 는 127.0.0.1:5433
tmp/bin/uv                                 ← 스텁: `run alembic heads` · `run alembic history` ·
                                              `run python -m src.scripts.run_alembic_with_lock` 을 갈라 응답 + argv 기록
```

★**`docker`·`uv` 스텁은 선택이 아니다.** 스텁이 없으면 진짜 소크 DB 에 psql 이 나가고
`uv run alembic` 이 이 레포의 마이그레이션을 읽는다.

★**호출 횟수를 기록해라** — `docker exec … alembic_version` 은 **사전·사후 두 번** 불린다.
사후 재확인 케이스는 「1번째 호출과 2번째 호출이 다른 값을 낸다」로 만든다
(선례: `test_soak_observe.py` 의 `DOCKER_STUB_CALLS_FILE`).

### 최소한 이 일곱을 덮어라 (케이스 ≥7)

1. ★**여분 인자 거부** — `migrate --confirm --typo` → rc=1 + 「인자가 너무 많다」.
   `migrate --typo`(단일 미지 인자) → rc=1 + 「알 수 없는 인자」.
   ★두 경우 다 **`docker`·`uv` 호출 0건**(가드가 조회보다 먼저다)
2. ★**`assert-main-checkout.sh` 가 가장 먼저** — 스텁을 rc=1 로 두면 스크립트 rc=2 이고
   `docker` 호출 0건이다
3. **이미 head** — 사전 revision == `alembic heads` → rc=0 + 「이미 head 다」 ·
   ★`run_alembic_with_lock` 미호출
4. ★★**history fail-closed** — ⑴ `alembic history` 가 rc≠0 ⑵ rc=0 인데 **출력이 빈 경우**
   둘 다 **rc=2** 이고 upgrade 미호출. 「0 항목」을 「할 일 없음」으로 읽으면 안 된다
5. ★★**대상 증명 — `DATABASE_URL` 이 published port 와 불일치하면 rc=1** 이고
   ★**upgrade 가 호출되지 않는다**(DDL 이 나가기 **전**이다). `docker port` 스텁이
   `127.0.0.1:5433` 을 주는데 `.env.local` 은 `:5432` 를 가리키게 만들어라.
   **이 케이스가 이 lane 의 이유다**
6. **dry-run 정상** — 위 전제가 다 맞고 `--confirm` 이 없으면 rc=0 · 「dry-run 이다」 ·
   「적용 대상」 ✓ 줄 · ★**upgrade 미호출**
7. ★**적용 대기 개수** — `alembic history` 출력에 **이미 적용된 전이까지 섞어** 주고,
   출력의 「적용 대기 N 항목」이 **`<cur> -> …` 줄까지만** 세는지 단언해라.
   (`-r A:B` 는 A 를 **포함**하므로 그 아래는 이미 적용된 것이다 — 초판이 여기서 2를 찍었다)
8. **`--confirm` 집행 경로** — upgrade 스텁이 rc=0 이고 사후 revision 이 head 와 **같으면**
   rc=0 + `✓ cur → after`. 사후 revision 이 **다르면 rc=1** + 「다른 DB 에 적용됐다」
9. ★**양성 대조 — `--help` 범위 정합.** dispatch 의 `sed -n '2,26p' "$0"` 가 헤더와 맞는지
   (파일에서 `^#` 가 아닌 첫 줄이 몇 행인지 직접 재서) 단언해라. ★**이 스크립트는 맞다** —
   같은 축에서 어긋난 사례(`db-backup.sh` 65행 vs `'2,59p'`, `soak-restart.sh` 34행 vs `'2,40p'`)와
   대조되는 **양성 대조**다. 「이 검사가 어긋남을 잡을 수 있다」의 증인이 된다

★**실패원을 하나만 남겨라** — 5번을 잴 때 history·heads·assert 스텁은 전부 **정상 경로**로
두고 `.env.local` 의 포트만 어긋나게 해라. 여러 개가 동시에 실패하면 rc=1 이 어디서 왔는지
못 가른다(4회차에 변이 하나가 정확히 그래서 초록으로 샜다).

## Acceptance Criteria

```bash
cd apps/api && uv run --env-file .env.local pytest tests/scripts/test_soak_stack_migrate.py -q
cd apps/api && test "$(uv run --env-file .env.local pytest tests/scripts/test_soak_stack_migrate.py --collect-only -q 2>/dev/null | grep -c '::')" -ge 7
cd apps/api && uv run ruff check tests/scripts/
```

★두 번째 AC 는 **양성 대조**다. 착수 시점 이 파일은 없으므로 첫 AC 는 rc=4 (red) 다.

## 자기 점검

1. 위 AC 를 직접 실행해 green 을 확인한다. `status` 를 `completed` 로 바꾸지 마라.
2. ★**진짜 DB 에 DDL 이 안 나갔는지 확인해라** — 모든 케이스가 가짜 레포 + PATH 스텁을 탄다.
   `uv` 스텁이 없는 케이스가 하나라도 있으면 그것은 사고다.
3. `summary` 에 `uv` 스텁이 가른 서브커맨드 3종과 `docker` 스텁의 호출 순서를 남겨라.

## 금지사항

- `tools/scripts/soak-stack.sh` **수정 금지.** 결함은 `@pytest.mark.xfail(strict=True)`
- ★**`pin`/`up`/`down` 을 실행하지 마라.** 이유: 소크 스택을 올리고 내린다. `_migrate` 만 부른다
- ★**진짜 `uv run alembic` 을 부르지 마라** — 이 레포의 마이그레이션을 읽고, `--confirm`
  갈래에서는 **진짜 DB 에 upgrade 를 건다**. 반드시 PATH 스텁이다
- ★**레포의 `apps/api/.env.local` 을 읽지 마라** — 가짜 레포 안의 파일이다(**CI 엔 없다**)
- 공용 헬퍼 모듈 금지 · `conftest.py`·`shards.json`·`docs/**` 무변경 · DB 픽스처 금지
- 커밋하지 마라. macOS bash 3.2 · ubuntu bash 5 양쪽 통과
