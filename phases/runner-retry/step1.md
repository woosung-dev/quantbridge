# Step 1: step-exit-paths

## 읽어야 할 파일

- `tools/harness/execute.py` — `_execute_step` (`:302-352`) · `_preamble` (`:214-233`) ·
  `_step_context` (`:206-212`) · `run()` 의 blocker 검사 (`:360-362`)
- `apps/api/tests/harness/test_execute_retry.py` — **step 0 이 만든 네 파일**. 여기에 이어 쓴다

## 배경

step 0 이 「몇 번 부르나」를 깔았다. 남은 것은 **어떻게 끝나나**다. `_execute_step` 의 출구는
셋이고 각각 종료 코드가 다르다 — 성공(반환) · 3회 실패(`status="error"` + rc 1) ·
세션의 blocked 선언(rc 2). 그리고 실패한 시도의 사유는 **다음 시도 프리앰블에 실려야** 한다.
그 되먹임이 끊기면 재시도가 같은 실패를 3번 반복한다.

## 작업

`test_execute_retry.py` 에 이어서 최소 네 축을 더 단언하라:

1. **error 출구** — 3회 모두 실패하면 `SystemExit` 의 code 가 **1** 이고,
   `index.json` 의 그 step 이 `status="error"` · `error_message` 에 `[3회 시도 후 실패]`
   문구를 갖는다. 최상위 `phases/index.json` 도 `status="error"` 로 따라간다
2. **blocked 존중** — 가짜 codex 가 `index.json` 의 step 에 `status="blocked"` 와
   `blocked_reason` 을 써넣으면, 러너는 **AC 를 돌리지 않고** 종료하며 `SystemExit` code 가 **2** 다
3. **되먹임** — 1회차 실패 사유 문자열이 **2회차 프리앰블에 들어간다**
   (`_preamble` 의 `prev_error` 절. 가짜 codex 가 받은 프롬프트를 파일로 남겨 확인해라)
4. **이전 step 누적** — `_step_context` 는 `status=="completed"` 이고 `summary` 가 있는
   step 만 줄로 만든다. pending·summary 없는 step 은 빠진다

### 격리 방법 (4 lane 공통 — 이 방식에서 벗어나지 마라)

러너는 패키지가 아니라 레포 루트의 스크립트다. 파일 경로로 로드해라:

```python
import importlib.util
from pathlib import Path

_SRC = Path(__file__).resolve().parents[4] / "tools" / "harness" / "execute.py"
_SPEC = importlib.util.spec_from_file_location("qb_harness_execute", _SRC)
ex = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(ex)
```

루트는 모듈 전역이므로 `monkeypatch` 로 갈아끼운 뒤 인스턴스를 만들어라:

```python
monkeypatch.setattr(ex, "ROOT", tmp_path)
executor = ex.StepExecutor("<phase-dir-name>")
```

★**`_root` 를 문자열로 두지 마라.** `_state_files()` 가 `Path.relative_to(self._root)` 를
쓴다 — 문자열이면 거기서 깨진다. `tmp_path`(Path) 그대로 써라.

★`StepExecutor.__init__` 은 `ac` 배열이 없는 step 을 거부한다 — 픽스처의 **모든** step 에
`ac` 를 넣어라.

★진짜 `codex` CLI 를 부르지 마라. 필요하면 `ex.CODEX_CMD` 를 가짜 명령으로 갈아끼우거나
(`[*CODEX_CMD, prompt]` 로 호출된다) `_invoke_codex` 자체를 monkeypatch 해라.

## Acceptance Criteria

```bash
cd apps/api && uv run --env-file .env.local pytest tests/harness/test_execute_retry.py -q
cd apps/api && test "$(uv run --env-file .env.local pytest tests/harness/test_execute_retry.py --collect-only -q 2>/dev/null | grep -c '::')" -ge 8
cd apps/api && uv run ruff check tests/harness/
```

★두 번째 AC 는 **양성 대조**다 — 「0건이니 통과」를 막는다.

## 금지사항

- `tools/harness/execute.py` 를 **수정하지 마라.** 이유: 다른 lane 3벌이 같은 파일을 동시에
  읽고 있고, 러너 수리는 이번 회차 범위 밖이다. 결함을 발견하면
  `@pytest.mark.xfail(reason="…")` 로 두고 `index.json` 의 `summary` 에 한 줄로 적어라
- `conftest.py` 를 만들거나 수정하지 마라. 이유: 4 lane 이 같은 파일을 동시에 만들어 머지
  충돌한다. 픽스처·헬퍼는 **이 테스트 파일 안에** 로컬로 둬라
- `apps/api/tests/shards.json` 을 만지지 마라. 이유: 샤드 `c` 의 `paths:["tests"]` 가
  `tests/harness/` 를 이미 덮는다(실측 확인됨)
- 다른 lane 의 테스트 파일(`test_execute_ac.py` · `test_execute_retry.py` ·
  `test_execute_commit.py` · `test_execute_boot.py` 중 네 것이 아닌 것)을 만들지 마라
- `docs/**` 를 만지지 마라. 커밋하지 마라(커밋은 러너 소관이다)
