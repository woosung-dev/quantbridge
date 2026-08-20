# Step 0: vitals-axes

## 읽어야 할 파일

- `tools/scripts/ledger-vitals.sh` — **이번 테스트의 대상** (114줄 전량)
- `apps/api/tests/scripts/test_soak_gate_predicate.py` — 이 디렉터리의 테스트 관용구
  (한국어 1줄 헤더 + 한국어 docstring · DB 픽스처 미사용 선언)

## 배경

`ledger-vitals.sh` 는 [ADR-037] 제로베이스에서 **살아남은 유일한 원장 기계 게이트**다
(감사기 9종이 철거되고 이것 하나가 슬림 복귀했다). pre-commit 이 이것을 부른다.
★**그런데 이 판정기 자신의 테스트가 0건이다.** 3축 중 하나가 조용히 무증거가 되면
원장 부식이 그대로 통과한다.

판정은 전부 awk 다 — 코드펜스 토글 · `~~` 취소선 · 백틱 짝수/홀수 · 표 구분행 인식.
이 종류는 **입력 한 줄 차이로 판별력이 사라지는데 초록은 그대로 난다.**

## 작업

`apps/api/tests/scripts/test_ledger_vitals.py` 를 신설하고 **축 ①·②** 를 단언하라.

### 호출 방식 (이 lane 의 유일한 방식)

스크립트는 테스트 오버라이드를 **argv 플래그로만** 받는다 (env 오버라이드는 집행 경로의
게이트 백도어라 의도적으로 없다 — 스크립트 12~14행 주석).

```python
import subprocess
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[3] / "tools" / "scripts" / "ledger-vitals.sh"

def run(status_text: str, backlog_text: str, tmp_path) -> subprocess.CompletedProcess[str]:
    s = tmp_path / "status.md"; s.write_text(status_text, encoding="utf-8")
    b = tmp_path / "backlog.md"; b.write_text(backlog_text, encoding="utf-8")
    return subprocess.run(
        ["bash", str(SCRIPT), "--status-file", str(s), "--backlog-file", str(b)],
        capture_output=True, text=True, timeout=60,
    )
```

★`SCRIPT` 경로가 맞는지 **먼저 확인해라** — 테스트 파일은
`apps/api/tests/scripts/` 에 있으므로 레포 루트는 `parents[3]` 이다. 틀리면 전건 실패한다.

### 최소한 이 여섯을 덮어라

축 ① — 살아 있는 `다음 행동 =` 이 파일 전체에서 ≤1 인가:

1. **1개면 rc=0, 2개면 rc=1** — 위반 시 stdout 에 `✗ ①` 과 개수가 실린다
2. **취소선 안쪽은 안 센다** — `~~다음 행동 = 옛것~~` 이 있는 줄 + 살아 있는 것 1개 → rc=0.
   판정은 매치 **앞쪽**의 `~~` 개수 홀짝이다(같은 줄에 둘이 섞이는 형태를 만들어 봐라)
3. **인라인 코드 안쪽은 안 센다** — `` `다음 행동 =` `` 는 인용이라 안 센다
4. **코드펜스 안쪽은 안 센다** — ` ``` ` 로 감싼 블록 안의 `다음 행동 =` 는 제외.
   ★들여쓰기된 펜스와 `> ` 인용부 뒤 펜스도 토글된다(스크립트가 `^[ \t>]*(```|~~~)` 로 잡는다)

축 ② — ⓪ 표 데이터 행 ≥3 인가:

5. **3행이면 rc=0, 2행이면 rc=1** — `### ⓪ …` 헤딩 아래 파이프 표
6. **머리행·구분행은 데이터로 안 센다** — 머리행 1 + 구분행 1 + 데이터 3 = 통과이고,
   머리행 1 + 구분행 1 + 데이터 2 = rc=1 이어야 한다. ★그리고 `###` 헤딩이 `⓪` 를 담지
   않으면 그 아래 표는 아예 안 센다(다른 섹션의 표가 정족수를 채워 주면 안 된다)

★축 ①·② 를 한 번에 재지 마라 — **다른 축이 red 라서 rc=1 인 것**을 그 축의 판별로 오독한다.
축 ② 를 잴 때 status 본문의 「다음 행동 =」은 정확히 1개, 축 ① 을 잴 때 ⓪ 표는 3행으로
고정해 두는 픽스처 헬퍼를 파일 안에 둬라. `backlog.md` 는 축 ③ 이 조용하도록 빈 문자열이나
RESOLVED 없는 최소 본문으로 준다.

## Acceptance Criteria

```bash
cd apps/api && uv run --env-file .env.local pytest tests/scripts/test_ledger_vitals.py -q
cd apps/api && test "$(uv run --env-file .env.local pytest tests/scripts/test_ledger_vitals.py --collect-only -q 2>/dev/null | grep -c '::')" -ge 6
cd apps/api && uv run ruff check tests/scripts/
```

★두 번째 AC 는 **양성 대조**다 — 「0건이니 통과」를 막는다. 착수 시점 이 파일은 없으므로
첫 AC 는 rc=4 (red) 다. 그것이 이 AC 의 판별력 증거다.

## 자기 점검

1. 위 AC 를 직접 실행해 green 을 확인한다. ★최종 판정은 러너가 재실행해 내린다 —
   `status` 를 `completed` 로 바꾸지 마라.
2. 각 케이스가 **의도한 축 때문에** red/green 인지 확인한다 — stdout 의 `✗ ①` / `✗ ②`
   문자열까지 단언해라. rc 만 보면 다른 축의 실패를 자기 축으로 오독한다.
3. 사람 개입이 필요하면 `status:"blocked"` 와 `blocked_reason` 을 쓰고 즉시 중단한다.

## 금지사항

- `tools/scripts/ledger-vitals.sh` 를 **수정하지 마라.** 이유: 다른 lane 5벌이 같은 회차에서
  같은 디렉터리를 읽고 있고, 스크립트 수리는 이번 회차 범위 밖이다. 결함을 찾으면
  `@pytest.mark.xfail(reason="…")` 로 두고 `index.json` 의 `summary` 에 한 줄로 적어라
- `conftest.py` 를 만들거나 수정하지 마라. **공용 헬퍼 모듈도 만들지 마라.** 이유: 6 lane 이
  같은 파일을 동시에 만들어 머지 충돌한다. 픽스처·헬퍼는 **이 테스트 파일 안에** 로컬로 둬라
- `apps/api/tests/shards.json` 을 만지지 마라. 이유: 샤드 `c` 의 `paths:["tests"]` 가
  `tests/scripts/` 를 이미 덮는다(실측 확인됨)
- **진짜 `docs/status.md`·`docs/backlog.md` 를 겨누지 마라.** 반드시 `tmp_path` 파일과
  `--status-file`/`--backlog-file` 을 써라. 이유: 그 둘은 이 레포의 원장이고, 판정 대상이
  실제 원장이면 테스트가 원장 내용에 따라 흔들린다
- **env 오버라이드를 새로 만들지 마라** — 스크립트가 argv 로만 받는 것은 의도된 설계다
- DB 픽스처를 쓰지 마라(`tests/conftest.py::_test_engine` 은 autouse 가 아니다).
  `docs/**` 를 만지지 마라. 커밋하지 마라(커밋은 러너 소관이다)
