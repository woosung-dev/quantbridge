# Step 0: disk-firing-matrix

## 읽어야 할 파일

- `tools/scripts/disk-guard.sh` — **이번 테스트의 대상**. 특히 「발화 판단」 블록(332~348행)과
  파일 상단 「★설계 근거」(32~48행)
- `apps/api/tests/scripts/test_soak_gate_predicate.py` — 이 디렉터리의 테스트 관용구

## 배경

디스크 경보의 발화 조건은 **상태값이 아니라 상태 전이**다. 2026-08-16 codex 적대 리뷰가
「OK 면 무조건 무발화여야 한다」는 P2 를 냈고 **기각**됐다 — 경보만 받고 회복을 못 받으면
사람은 아직 위험한 줄 알고 다음 경보를 「아까 그거」로 읽는다. 그 판정이 스크립트 주석
39~42행에 박혀 있는데 **그것을 지키는 테스트가 0건이다.**

원 사고: 2026-08-14 로컬 Docker VM 이 94% 에서 Redis AOF 쓰기에 실패해 celery 가 통째로
정지했다([BL-736]). 서버도 구조가 같다.

## 작업

`apps/api/tests/scripts/test_disk_guard.py` 를 신설하고 **발화 행렬**을 단언하라.

### 호출 방식 (이 lane 의 유일한 방식 — 여기서 벗어나지 마라)

`df` 를 PATH 스텁으로 갈아끼워 사용률을 완전히 통제한다. `date` 도 스텁해 「오늘」을 고정한다
(안 하면 자정 근처에서 간헐 red 가 된다).

```python
import os, subprocess
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[3] / "tools" / "scripts" / "disk-guard.sh"

def _stub_bin(tmp_path, pct: int, avail_kb: int = 10485760, today: str = "2026-08-20") -> Path:
    """`df` 와 `date` 를 갈아끼운 PATH 디렉터리."""
    d = tmp_path / "bin"; d.mkdir(exist_ok=True)
    # `df -Pk <경로>` 2행 형식 그대로: Filesystem 1024-blocks Used Available Capacity Mounted-on
    (d / "df").write_text(
        "#!/bin/sh\n"
        "echo 'Filesystem 1024-blocks Used Available Capacity Mounted-on'\n"
        f"echo '/dev/sda1 104857600 1 {avail_kb} {pct}% /'\n",
        encoding="utf-8",
    )
    (d / "date").write_text(f"#!/bin/sh\nprintf '%s\\n' '{today}'\n", encoding="utf-8")
    for f in ("df", "date"):
        (d / f).chmod(0o755)
    return d
```

`env` 는 **전부 명시로 덮어라** — 특히 `QB_SOAK_ENV_FILE`. 기본값이 `apps/api/.env.local` 인데
**CI 에는 그 파일이 없다**(로컬 초록 · CI red 의 전형).

```python
env = {
    **os.environ,
    "PATH": f"{stub}:{os.environ['PATH']}",
    "QB_DISK_TARGET": "/",
    "QB_DISK_WARN_PCT": "80",
    "QB_DISK_STATE": str(tmp_path / "state" / "disk-guard.state"),
    "QB_SOAK_ENV_FILE": str(tmp_path / "env.local"),   # 실제 레포 파일을 겨누지 않는다
    "XDG_CONFIG_HOME": str(tmp_path / "xdg"),          # systemd 유닛 조회를 tmp 로 격리
}
```

이 step 은 **전부 `--dry-run`** 으로 돌린다 — 알림을 안 쏘고 상태 파일도 안 쓰므로 발화
판단만 순수하게 관측할 수 있다. 발화하면 stdout 에 `── [dry-run] 보냈을 알림 ──` +
본문이, 무발화면 `── [dry-run] 무발화` 가 찍힌다.

이전 상태는 상태 파일을 **직접 써서** 만든다(`LEVEL=…\nNOTIFIED_DATE=…\n` 두 줄, key=value).

### 최소한 이 여섯을 덮어라

1. **OK → WARN 전이 = 발화** (상태 파일 없음 + 85% ≥ 임계 80) — 본문에 `🟠` 와 `임계 80% 를 넘었다`
2. **WARN 유지 · 같은 날 = 무발화** (`LEVEL=WARN` + `NOTIFIED_DATE=<오늘>`)
3. **WARN 유지 · 다른 날 = 재고지** (`NOTIFIED_DATE=1970-01-01`) — 본문에 `재고지`
4. ★**WARN → OK 전이 = 회복 발화** (`LEVEL=WARN` + 사용률 10%) — 본문에 `🟢` 와 `회복`.
   **이것이 2026-08-16 codex P2 기각의 축이다**
5. **OK 유지 = 무발화** (`LEVEL=OK` + 사용률 10%)
6. **경계값** — `PCT == WARN_PCT` 는 `-ge` 비교라 **WARN 이다**(80% / 임계 80 → 발화).
   그리고 79% / 임계 80 은 OK 다. 둘을 같이 재라(off-by-one 이 이 판정의 유일한 산술이다)

★2·5 는 **무발화**를 재는 케이스다. 「본문이 안 실렸다」만 보지 말고 stdout 에
`무발화` 문자열이 있는지까지 단언해라 — 스크립트가 아예 죽어도 「본문 없음」은 참이다.

## Acceptance Criteria

```bash
cd apps/api && uv run --env-file .env.local pytest tests/scripts/test_disk_guard.py -q
cd apps/api && test "$(uv run --env-file .env.local pytest tests/scripts/test_disk_guard.py --collect-only -q 2>/dev/null | grep -c '::')" -ge 6
cd apps/api && uv run ruff check tests/scripts/
```

★두 번째 AC 는 **양성 대조**다. 착수 시점 이 파일은 없으므로 첫 AC 는 rc=4 (red) 다.

## 자기 점검

1. 위 AC 를 직접 실행해 green 을 확인한다. `status` 를 `completed` 로 바꾸지 마라.
2. **스텁이 실제로 걸렸는지 확인해라** — 사용률 값을 바꾸면 판정이 따라 바뀌는지 본다.
   진짜 `df` 가 불렸는데 우연히 통과하는 것이 이 lane 의 가장 큰 위험이다.
3. 사람 개입이 필요하면 `status:"blocked"` 와 `blocked_reason` 을 쓰고 즉시 중단한다.

## 금지사항

- `tools/scripts/disk-guard.sh` 와 `tools/scripts/lib/notify-telegram.sh` 를 **수정하지 마라.**
  결함을 찾으면 `@pytest.mark.xfail(reason="…")` + `summary` 한 줄
- **`--install` / `--uninstall` 을 실행하지 마라.** 이유: 실행자의 `systemd user` 디렉터리에
  유닛을 쓰고 `systemctl --user enable --now` 를 부른다. 이 step 은 발화 판단만 본다
- **진짜 텔레그램을 쏘지 마라** — 이 step 은 전부 `--dry-run` 이라 발송 경로에 안 들어가지만,
  비-dry-run 을 쓰게 되면 반드시 `QB_DISK_NOTIFY_CMD` 주입 seam 을 통해라
- `awk`·`sed`·`grep` 을 스텁하지 마라 — 스크립트의 판정 자체가 그것들이다. 스텁 대상은
  `df`·`date` 뿐이다
- `conftest.py`·공용 헬퍼 모듈·`shards.json`·`docs/**` 무변경. DB 픽스처 금지. 커밋하지 마라
- GNU 전용/BSD 전용 옵션을 스텁에 쓰지 마라 — 이 테스트는 macOS bash 3.2 와 ubuntu bash 5
  양쪽에서 통과해야 한다(CI 는 ubuntu 에서 전량 pytest 를 돈다)
