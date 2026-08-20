# Step 0: codex-invoke-and-retry

## 읽어야 할 파일

- `tools/harness/execute.py` — `_invoke_codex` (`:241-262`) · `_execute_step` (`:302-352`) ·
  `MAX_RETRIES` (`:93`) · `CODEX_TIMEOUT` (`:58`). 파일 상단 docstring 의 「수리 ②」가 이 축이다
- `.claude/commands/harness.md` — 러너 저작 규약

## 배경

★**[ADR-030] 파일럿 B 를 죽인 것이 바로 이 자리다.** 원본은 `subprocess.run(timeout=…)` 의
`TimeoutExpired` 를 잡지 않아 30분 초과 시 러너가 크래시하고 작업 트리가 dirty 로 남았다.
우리는 그것을 포착해 「실패 사유」로 흡수하도록 고쳤는데, **그 수리에 테스트가 0건이다.**

## 작업

`apps/api/tests/harness/test_execute_retry.py` 를 신설하고 codex 호출과 재시도 축을 단언하라.

최소한 이 넷을 덮어라:

1. **정상 호출** — rc=0 이면 `(True, "")` 이고 `runs/step{N}-attempt{A}.json` 에
   `exitCode`·`stdout`·`stderr` 가 남는다
2. **비정상 종료** — rc≠0 이면 첫 항이 `False` 이고 사유에 **rc 값**이 들어간다
3. **TimeoutExpired 포착** — `CODEX_TIMEOUT` 을 작게 갈아끼우고 그보다 오래 도는 가짜
   codex 를 주면 **예외가 밖으로 새지 않고** `(False, "… TimeoutExpired")` 로 돌아오며,
   `runs/` 에 `error` 키가 남는다
4. **재시도 횟수** — codex 가 계속 실패할 때 `_execute_step` 이 codex 를 **정확히
   `MAX_RETRIES`(3)회** 부른다. 호출 횟수를 세라

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
cd apps/api && test "$(uv run --env-file .env.local pytest tests/harness/test_execute_retry.py --collect-only -q 2>/dev/null | grep -c '::')" -ge 4
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
