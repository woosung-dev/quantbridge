# Step 0: ac-verdict-core

## 읽어야 할 파일

- `tools/harness/execute.py` — **이번 테스트의 대상**. 특히 `StepExecutor._run_ac` (`:264-281`)
  와 `_save_run` (`:237-239`). 파일 상단 docstring 의 「수리 ①」이 이 함수의 존재 이유다
- `.claude/commands/harness.md` — 러너 저작 규약(§C-5a~5e)

## 배경

이 러너의 판정 주체는 **러너 자신**이다. 원본(jha0313/finsight)은 step 세션이 써넣은
`"completed"` 를 그대로 믿었다 — 코드를 쓴 쪽이 자기 채점을 했다. 우리는 `index.json` 각
step 의 `ac` 배열을 러너가 `bash -c` 로 돌려 **exit code 로만** 판정한다.

★**그 판정 함수에 테스트가 0건이다.** `_run_ac` 가 조용히 고장 나면 이 레포의 모든 무인
회차가 거짓 초록을 낸다. 이번 step 이 그 바닥을 깐다.

## 작업

`apps/api/tests/harness/test_execute_ac.py` 를 신설하고 `_run_ac` 의 **핵심 계약**을 단언하라.

최소한 이 넷을 덮어라:

1. **전건 통과** — `ac` 의 모든 커맨드가 rc=0 이면 `(True, "")` 를 돌려준다
2. **하나라도 실패하면 실패** — rc≠0 인 커맨드가 있으면 첫 항이 `False` 이고,
   실패 사유 문자열에 **rc 값과 실패한 커맨드 원문**이 함께 들어간다
3. **실행 위치** — 커맨드는 `self._root` 를 cwd 로 돌아간다
   (tmp 루트에 파일을 만드는 커맨드를 AC 로 주고 그 자리에 생겼는지 본다)
4. **검시 산출 보존** — 실패 시 `phases/<dir>/runs/step{N}-attempt{A}.json` 이 생기고
   그 안에 `acFailed`(커맨드) · `rc` · `tail`(리스트) 키가 있다

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

★`StepExecutor.__init__` 은 가드레일 4축(`CONTEXT.md` · `AGENTS.md` · `apps/api/AGENTS.md` ·
`apps/web/AGENTS.md`)이 **없어도** 통과한다(그 검사는 `_load_guardrails` 에 있다). 하지만
`ac` 배열이 없는 step 은 거부한다 — 픽스처의 모든 step 에 `ac` 를 넣어라.

## Acceptance Criteria

```bash
cd apps/api && uv run --env-file .env.local pytest tests/harness/test_execute_ac.py -q
cd apps/api && test "$(uv run --env-file .env.local pytest tests/harness/test_execute_ac.py --collect-only -q 2>/dev/null | grep -c '::')" -ge 4
cd apps/api && uv run ruff check tests/harness/
```

★두 번째 AC 는 **양성 대조**다 — 「0건이니 통과」를 막는다. 착수 시점 이 파일은 없으므로
첫 AC 는 rc=4 (red) 다. 그것이 이 AC 의 판별력 증거다.

## 금지사항

- `tools/harness/execute.py` 를 **수정하지 마라.** 이유: 다른 lane 3벌이 같은 파일을 동시에
  읽고 있고, 러너 수리는 이번 회차 범위 밖이다. 결함을 발견하면
  `@pytest.mark.xfail(reason="…")` 로 두고 `index.json` 의 `summary` 에 한 줄로 적어라
- `conftest.py` 를 만들거나 수정하지 마라. 이유: 4 lane 이 같은 파일을 동시에 만들어 머지
  충돌한다. 픽스처·헬퍼는 **이 테스트 파일 안에** 로컬로 둬라
- `apps/api/tests/shards.json` 을 만지지 마라. 이유: 샤드 `c` 의 `paths:["tests"]` 가
  `tests/harness/` 를 이미 덮는다(실측 확인됨)
- `docs/**` 를 만지지 마라. 커밋하지 마라(커밋은 러너 소관이다)
- 진짜 `codex` CLI 를 부르는 테스트를 쓰지 마라 — 이 step 은 `_run_ac` 만 본다
