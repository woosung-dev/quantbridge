# Step 0: backup-status-freshness

## 읽어야 할 파일

- `tools/scripts/db-backup.sh:544-612` — `_installed_execstart` · `_status`(이번 step 의 대상)
- `tools/scripts/db-backup.sh:462-535` — `_install` 이 **굽는 유닛 파일 형식**.
  ★`--install` 을 실행해서 만들지 마라 — 실행자의 진짜 systemd 를 건드린다
- `apps/api/tests/scripts/test_db_backup_target.py` — **같은 대상의 앞 회차 테스트**.
  ★그 파일을 수정하지도, 거기서 import 하지도 마라(다른 축이고 lane 규약이 금지한다)

## 배경

[BL-767] 이 만든 백업 축의 **잔여**다. 2026-08-20 4회차가 dispatch 인자 계약과
`_prove_target`(대상 증명)을 덮었고, 남은 것이 **`--status` 신선도 · `_retain` 보관 정책 ·
`_upload` prefix 경계** 셋이다. 이 step 은 첫째, step 1 이 나머지 둘이다.

★**「타이머가 waiting」은 건강 신호가 아니다**([BL-737]). 2026-08-13 재배치가 스크립트를
옮기자 soak-watch 유닛은 **41시간 동안 rc=127 로 죽었고 알림은 0줄**이었다. `db-backup` 은
같은 형태의 systemd 타이머로 돌고, 그래서 같은 신선도 판정을 자기 `--status` 에 달았다.
**그 판정을 재는 것은 지금 아무것도 없다.**

★4회차가 이 파일에서 **실제로 어긋난 축 하나**를 잡았다 — `--help` 의 `sed -n '2,59p'` 가
**65행짜리 헤더**를 잘라 60~64행을 못 찍는다. 그 결함은 `test_db_backup_target.py` 에
`xfail(strict=True)` 로 이미 고정돼 있다. **같은 것을 다시 만들지 마라**(중복 xfail 은
수리 시 두 파일이 함께 XPASS 로 red 가 된다).

## 작업

`apps/api/tests/scripts/test_db_backup_retain.py` 를 신설한다.

### 호출 방식 (이 step 의 유일한 방식)

`_status` 는 **파일만 읽는다** — `_wire_docker` 를 부르지 않는다. 그래서 **진짜 스크립트를
그대로 실행**하고 env 로 두 경로만 옮기면 된다.

```python
SCRIPT = Path(__file__).resolve().parents[4] / "tools" / "scripts" / "db-backup.sh"

def run_status(tmp_path, xdg: Path, backup_dir: Path):
    env = {**os.environ, "XDG_CONFIG_HOME": str(xdg), "QB_BACKUP_DIR": str(backup_dir)}
    return subprocess.run(["bash", str(SCRIPT), "--status"],
                          capture_output=True, text=True, timeout=60, env=env)
```

유닛 파일은 `xdg/systemd/user/dev.quantbridge.db-backup.service` 에 **손으로** 쓴다.
`_installed_execstart` 의 `sed` 식은 `^ExecStart=/bin/bash (.*) run$` 다 — ★**끝의 ` run` 까지
일치해야 뽑힌다.** 알람 유닛은 `dev.quantbridge.db-backup-alarm.service` 이고 **존재 여부만** 본다.

★`--status` 는 앞부분에서 `systemctl` 을 부를 수 있다(있으면 타이머 줄). **타이머 절은
단언 대상이 아니다** — OS 마다 다르다. 재는 것은 신선도 줄들과 **종료 코드**다.

### 최소한 이 여섯을 덮어라 (케이스 ≥6)

1. **유닛 부재 → rc=1** + 「설치된 유닛이 없다」
2. ★**`ExecStart` 가 없는 파일을 가리킴 → rc=1** + 「rc=127 로 죽는다」 ([BL-737] 그 자체)
3. **`ExecStart` 가 다른(실재하는) 파일 → rc=1** + 「이 파일이 아니다」 +
   **설치본·현재본 두 경로가 모두 출력**된다
4. ★**정상 — `ExecStart` 가 진짜 `db-backup.sh` + 알람 유닛 존재 + 백업 파일 1개 이상 → rc=0.**
   **이 양성 대조가 없으면 「항상 rc=1」인 판정기도 1~3을 통과한다**
5. **알람 유닛 부재 → rc=1** + 「백업이 죽어도 조용하다」 취지.
   ★`ExecStart` 는 정상인 상태에서 재라 — **실패원을 하나만 남긴다**
6. **백업 파일 축** — ⑴ `QB_BACKUP_DIR` 이 없는 디렉터리 → rc=1 + 「디렉터리가 없다」
   ⑵ 있는데 `quantbridge-*.dump` 가 0개 → rc=1 + 「하나도 없다」
   ⑶ ★파일이 있으면 **보관 개수**가 찍히고, `.meta` 가 있으면 **그 내용이 들여쓰여 출력**된다
   (`ls -1t` 로 최근 것을 고른다 — 두 개를 mtime 을 갈라 두고 **최근 것**이 찍히는지 재라)

★**`ExecStart` 의 ` run` 접미 계약도 한 줄 재라** — `ExecStart=/bin/bash <경로>` 로만
(끝에 ` run` 없이) 쓴 유닛에서 `_installed_execstart` 가 **빈 문자열**을 내 「설치된 유닛이
없다」로 떨어지는지. 유닛 형식이 바뀌면 신선도 판정이 통째로 무증거가 된다는 뜻이다.

## Acceptance Criteria

```bash
cd apps/api && uv run --env-file .env.local pytest tests/scripts/test_db_backup_retain.py -q
cd apps/api && test "$(uv run --env-file .env.local pytest tests/scripts/test_db_backup_retain.py --collect-only -q 2>/dev/null | grep -c '::')" -ge 6
cd apps/api && uv run ruff check tests/scripts/
```

★두 번째 AC 는 **양성 대조**다. 착수 시점 이 파일은 없으므로 첫 AC 는 rc=4 (red) 다.

## 자기 점검

1. 위 AC 를 직접 실행해 green 을 확인한다. `status` 를 `completed` 로 바꾸지 마라.
2. ★**`~/.config/systemd/user/` 와 `/opt/backups` 에 아무것도 안 생겼는지 확인해라** —
   env 두 개를 `tmp_path` 로 준 상태여야 한다.
3. `summary` 에 유닛 파일 2종의 **정확한 줄 모양**을 남겨라 — step 1 이 쓰지는 않지만
   회귀 시 진단이 빨라진다.

## 금지사항

- `tools/scripts/db-backup.sh` **수정 금지.** 결함은 `@pytest.mark.xfail(strict=True)`
- ★**`--install`/`--uninstall`/`run`/`verify-restore` 를 실행하지 마라.** 이유: 설치는
  `systemctl --user` 로 진짜 타이머를 만들고, `run` 은 **진짜 DB 를 덤프하고 OCI 에 올린다**.
  이 step 은 `--status` 하나만 부른다
- ★**`apps/api/tests/scripts/test_db_backup_target.py` 를 수정하거나 import 하지 마라** —
  같은 대상이지만 다른 축이고, 그 파일에 이미 있는 `--help` xfail 을 **중복으로 만들지 마라**
- 공용 헬퍼 모듈 금지 · `conftest.py`·`shards.json`·`docs/**` 무변경 · DB 픽스처 금지
- 커밋하지 마라. macOS bash 3.2 · ubuntu bash 5 양쪽 통과
