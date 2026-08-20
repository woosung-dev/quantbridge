# Step 1: retain-and-upload-prefix

## 읽어야 할 파일

- `tools/scripts/db-backup.sh:318-343` — `_upload` · `_retain` (이번 step 의 대상)
- `tools/scripts/db-backup.sh:614-644` — dispatch. ★아래 「호출 방식」이 이것에 기댄다
- `apps/api/tests/scripts/test_db_backup_retain.py` — step 0 이 만든 파일. **여기에 덧붙인다**

## 배경

`_retain` 은 **보관 정책의 전부**다 — `+${RETAIN_DAYS}` 경과분을 지우고 남은 개수를 로그로
남긴다. 이것이 조용히 어긋나면 두 방향으로 다 아프다: 너무 넓으면 **어제 백업이 사라지고**,
너무 좁으면 디스크가 찬다(이 서버는 [BL-736]·[BL-768] 로 이미 디스크 경보를 달았다).

`_upload` 의 `QB_BACKUP_PREFIX` 는 **남의 버킷을 빌려 쓰는 경계**다(2026-08-16 실측 —
이 VM 의 Instance Principal 은 `manage objects` 는 있는데 **버킷 생성 권한이 없어**
다른 앱의 `truewords-backups` 를 공유하고 있다). 경계가 **파일명 규칙에만** 의존하면
저쪽이 규칙을 바꾸는 순간 섞인다. ★**슬래시는 `_upload` 가 붙인다** — 호출자가 넣고
안 넣고에 따라 경로가 갈리면 안 된다.

★둘 다 `run` 서브커맨드 경유라 CLI 로는 **진짜 덤프 없이 못 부른다.** 아래 방식으로 함수만 부른다.

## 작업

step 0 의 파일에 덧붙인다. **누적 케이스 ≥10.**

### 호출 방식 (이 step 의 유일한 방식) — ★2026-08-20 실측으로 확인된 것

dispatch 의 `-h | --help` 갈래는 **`exit` 하지 않는다.** 그래서 `--help` 를 주고 **소싱**하면
스크립트가 함수를 전부 정의한 채 돌아온다:

```python
SNIPPET = 'set -- --help; . "$0" > /dev/null 2>&1; set +e; _retain'
subprocess.run(["bash", "-c", SNIPPET, str(SCRIPT)], env=..., capture_output=True, text=True)
```

- `$0` 가 스크립트 절대경로라 `${BASH_SOURCE[0]}` 파생 경로(`SCRIPT_DIR`·`ROOT`)가 정상으로 잡힌다
- ★**`set -euo pipefail` 이 소싱한 셸에 그대로 걸린다** — 함수를 부르기 전에 `set +e` 를 해라
- ★**`_wire_docker` 를 부르지 마라** — `SUDO` 는 톱레벨에서 `""` 이고 그 상태가 우리가 원하는
  것이다. `_wire_docker` 를 부르면 진짜 docker 데몬을 찾고, 없으면 `sudo` 로 승급하려 든다
- ★**이 문장을 믿지 말고 먼저 한 번 재라**(`--help` 갈래에 `exit` 가 생겼으면 이 방식은 죽는다).
  안 되면 그 사실을 `summary` 에 적고 `blocked` 가 아니라 **다른 방식**을 찾아라

`_retain` 은 `QB_BACKUP_DIR`·`QB_BACKUP_RETAIN_DAYS`, `_upload` 는 `QB_OCI_BIN`·
`QB_BACKUP_BUCKET`·`QB_BACKUP_PREFIX` 를 톱레벨에서 읽는다 — **소싱 시점의 env 가 값을 정한다.**

### `_retain` — 최소한 이 축들

1. ★**경과분만 지운다** — `mtime` 을 `RETAIN_DAYS + 16일` 전으로 만든 `.dump` 는 사라지고,
   **1일 전** `.dump` 는 남는다. (`os.utime` 으로 만든다. `find -mtime +N` 은 **N일 초과**다)
2. ★**`.meta` 짝도 함께 지운다** — 오래된 `quantbridge-*.dump.meta` 도 대상이다.
   짝이 남으면 `--status` 가 없는 덤프의 메타를 찍는다
3. ★**이름 규칙 밖은 건드리지 않는다** — 같은 디렉터리의 `other-20260101.dump` ·
   `notes.txt` 는 아무리 오래돼도 남는다. **이 음성 대조가 판별력이다**
4. **로그 한 줄** — 「N일 경과분 **삭제 개수**」와 「현재 보관 **개수**」가 실제 파일 수와 맞는다.
   ★보관 개수는 `.dump` 만 센다(`.meta` 는 안 센다)
5. **하위 디렉터리로 내려가지 않는다** — `-maxdepth 1` 이라 `sub/quantbridge-*.dump` 는 남는다

### `_upload` — 최소한 이 축들

6. **prefix 없음** — `QB_BACKUP_PREFIX=""` 면 `--name` 이 **basename 그대로**다
7. ★**prefix 정규화** — `qb` 와 `qb/` 를 각각 줬을 때 `--name` 이 **둘 다 `qb/<basename>`** 이다
   (`qb//<basename>` 이 나오면 안 된다). ★이 두 줄이 「슬래시는 여기서 붙인다」 계약이다
8. **argv 계약** — 스텁이 받은 인자에 `os object put`·`--auth instance_principal`·
   `--bucket-name <BUCKET>`·`--file <절대경로>`·`--force` 가 있다
9. **rc 전달** — OCI 스텁이 rc≠0 이면 `_upload` 도 그 rc 를 낸다
10. ★**양성 대조 — 스텁이 실제로 불렸다.** 기록 파일이 존재하고 비어 있지 않음을 먼저
    단언한 뒤 내용을 본다. 「`--name` 에 `//` 가 없다」는 **호출이 0건이어도 참**이다

★`QB_OCI_BIN` 스텁은 argv 전량을 파일에 기록하고 `OCI_STUB_RC`(기본 0)로 종료하게 만들어라.
**진짜 `/usr/local/bin/oci` 가 있는 머신에서 기본값이 그것을 부른다** — env 를 반드시 줘라.

## Acceptance Criteria

```bash
cd apps/api && uv run --env-file .env.local pytest tests/scripts/test_db_backup_retain.py -q
cd apps/api && test "$(uv run --env-file .env.local pytest tests/scripts/test_db_backup_retain.py --collect-only -q 2>/dev/null | grep -c '::')" -ge 10
cd apps/api && uv run ruff check tests/scripts/
```

## 자기 점검

1. 위 AC 를 직접 실행해 green 을 확인한다. `status` 를 `completed` 로 바꾸지 마라.
2. ★**step 0 의 케이스를 지우지 마라** — 누적 ≥10 은 step 0 의 ≥6 을 포함한 수다.
3. ★**진짜 백업 디렉터리(`/opt/backups`)와 OCI 에 닿지 않았는지 확인해라.**
4. `summary` 에 소싱 기법이 실제로 통했는지(`--help` 갈래에 `exit` 가 없는지) 한 줄 남겨라.

## 금지사항

- `tools/scripts/db-backup.sh` **수정 금지.** 결함은 `@pytest.mark.xfail(strict=True)`
- ★**`_wire_docker`·`_run`·`_verify_restore`·`_prove_target` 을 부르지 마라.** 이유: 진짜
  docker 데몬·진짜 DB·`sudo` 승급이 걸린다. 이 step 은 `_retain`·`_upload` 둘만 부른다
- ★**`sudo` 를 부르는 경로를 만들지 마라** — `QB_BACKUP_DIR` 은 반드시 `tmp_path`(쓰기 가능)다
- ★**진짜 OCI CLI 를 부르지 마라** — `QB_OCI_BIN` 을 스텁으로 고정한다
- `test_db_backup_target.py` 수정·import 금지 · 공용 헬퍼 모듈 금지
- `conftest.py`·`shards.json`·`docs/**` 무변경 · DB 픽스처 금지 · 커밋하지 마라
- macOS bash 3.2 · ubuntu bash 5 양쪽 통과 (★`find -mtime` 의 GNU/BSD 차이를 밟지 않도록
  경계값에서 **하루 이상** 떨어뜨려 재라)
