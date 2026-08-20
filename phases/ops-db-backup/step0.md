# Step 0: backup-dispatch-contract

## 읽어야 할 파일

- `tools/scripts/db-backup.sh` — **이번 테스트의 대상**. 이 step 은 **맨 끝 dispatch `case`
  (615~644행)** 와 파일 상단 헤더 주석(2~65행)만 본다
- `apps/api/tests/scripts/test_soak_gate_predicate.py` — 이 디렉터리의 테스트 관용구

## 배경

이 스크립트는 서버 systemd 타이머가 6시간마다 무인으로 부른다. 인자 계약이 느슨하면
**타이머가 조용히 엉뚱한 모드로 돈다.** 그래서 모든 서브커맨드가 인자 개수를 못박고 있다.

★그리고 헤더 주석과 `--help` 사이에 **이미 드리프트가 나 있다** — `--help` 는
`sed -n '2,59p' "$0"` 로 찍는데 헤더 주석은 **65행까지** 있다. 60~64행(「자격증명은 파일이
아니라 컨테이너에서 읽는다」 · 「파이프로 rc 를 가리지 않는다」)이 `--help` 에서 잘려 나온다.
스크립트 자신이 dispatch 자리에 「★헤더 주석에 줄을 더하면 이 범위를 함께 옮겨라
(짝 하네스가 잰다)」고 적어 뒀고, **그 짝 하네스는 [ADR-037] 로 철거됐다.** 감시가 사라진 뒤
실제로 밀린 것이다. 이 step 이 그 사실을 관측 가능하게 만든다.

## 작업

`apps/api/tests/scripts/test_db_backup_target.py` 를 신설하고 **dispatch 인자 계약**을 단언하라.

### 호출 방식

이 step 은 docker 에 닿지 않는 경로만 본다 — dispatch `case` 가 인자 개수를 먼저 보고
`die` 하므로 `_wire_docker` 까지 가지 않는다. 그래도 **환경은 전부 tmp 로 덮어라**
(다음 step 과 헬퍼를 공유하고, 실수로 진짜 경로를 겨누는 것을 구조적으로 막는다).

```python
import os, subprocess
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[3] / "tools" / "scripts" / "db-backup.sh"

def _env(tmp_path, extra=None):
    env = {
        **os.environ,
        "QB_BACKUP_DIR": str(tmp_path / "backups"),   # 쓰기 가능해야 sudo 분기를 안 탄다
        "QB_ENV_FILE": str(tmp_path / "env.local"),   # 기본값은 apps/api/.env.local — CI 에는 없다
        "QB_DB_CONTAINER": "qb-test-db",
        "QB_OCI_BIN": str(tmp_path / "bin" / "oci"),
        "QB_SKIP_UPLOAD": "1",
    }
    env.update(extra or {})
    return env

def run(tmp_path, *args, extra_env=None):
    (tmp_path / "backups").mkdir(exist_ok=True)
    return subprocess.run(
        ["bash", str(SCRIPT), *args],
        capture_output=True, text=True, timeout=60,
        env=_env(tmp_path, extra_env),
    )
```

### 최소한 이 다섯을 덮어라

1. **서브커맨드는 인자 개수를 못박는다** — `run extra` · `--install extra` · `--uninstall extra` ·
   `--status extra` 는 전부 **rc=1** 이고 stderr 에 「인자를 받지 않는다」. `verify-restore` 는
   **정확히 1개**라 0개도 2개도 rc=1 이다. (파라미터라이즈로 한 테스트에 묶어도 되지만
   **AC 수집 개수가 늘도록** `pytest.mark.parametrize` 를 써라 — 케이스마다 별 항목으로 센다)
2. **알 수 없는 인자 → rc=1** 이고 stderr 에 사용법 목록(`run / verify-restore <덤프> /
--install / --uninstall / --status / --help`)이 실린다. **인자 없이 호출**해도 같다
   (`case "${1:-}"` 의 `*)` 분기 — 「인자 생략 = 아무것도 안 함」이 아니다)
3. **`--help` 는 rc=0** 이고 stdout 에 사용법 블록(`tools/scripts/db-backup.sh run`)과
   환경변수 목록(`QB_BACKUP_DIR`)이 실린다
4. ★**`--help` 는 헤더의 마지막 줄까지 찍지 못한다 (현재 드리프트 고정)** —
   `--help` 출력에 `0바이트 덤프가 쌓이면` 은 **있고**, `자격증명은 파일이 아니라` 는 **없다**.
   이 케이스는 **`@pytest.mark.xfail(strict=True, reason=…)` 로 「헤더 전량이 나와야 한다」를
   단언하는 형태로 써라** — 지금은 xfail 이고, 누군가 `sed` 범위를 고치면 XPASS 로 red 가 나서
   이 테스트를 함께 갱신하게 된다. reason 에 「`sed -n '2,59p'` vs 헤더 65행」을 적어라
5. **양성 대조 — `--help` 가 실제로 이 파일의 헤더를 찍고 있다**: `--help` stdout 의 첫 줄이
   `tools/scripts/db-backup.sh` 의 2번째 줄과 같다. 이것이 없으면 4번의 「없다」 단언이
   **아무것도 안 찍혀도 참**이 된다

## Acceptance Criteria

```bash
cd apps/api && uv run --env-file .env.local pytest tests/scripts/test_db_backup_target.py -q
cd apps/api && test "$(uv run --env-file .env.local pytest tests/scripts/test_db_backup_target.py --collect-only -q 2>/dev/null | grep -c '::')" -ge 5
cd apps/api && uv run ruff check tests/scripts/
```

★두 번째 AC 는 **양성 대조**다. 착수 시점 이 파일은 없으므로 첫 AC 는 rc=4 (red) 다.

## 자기 점검

1. 위 AC 를 직접 실행해 green 을 확인한다. `status` 를 `completed` 로 바꾸지 마라.
2. `xfail` 케이스가 **xfail 로 뜨는지**(XPASS 가 아닌지) 확인해라 — `pytest -rxX` 로 본다.
3. 사람 개입이 필요하면 `status:"blocked"` 와 `blocked_reason` 을 쓰고 즉시 중단한다.

## 금지사항

- `tools/scripts/db-backup.sh` 를 **수정하지 마라.** 특히 4번의 `sed` 범위를 고치지 마라 —
  드리프트 수리는 이번 회차 범위 밖이고, 이 step 의 산출은 그것을 **관측 가능하게** 만드는 것이다
- **`run` / `verify-restore` / `--install` / `--uninstall` 을 인자 개수가 맞는 형태로 실행하지
  마라.** 이유: 인자가 맞으면 `_wire_docker` → 진짜 `docker` 로 들어간다. 이 step 은
  dispatch 만 본다(대상 증명은 다음 step 이 docker 스텁으로 한다)
- `conftest.py`·공용 헬퍼 모듈·`shards.json`·`docs/**` 무변경. DB 픽스처 금지. 커밋하지 마라
- macOS bash 3.2 · ubuntu bash 5 양쪽에서 통과해야 한다(CI 는 ubuntu 에서 전량 pytest)
