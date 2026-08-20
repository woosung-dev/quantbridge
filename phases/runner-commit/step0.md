# Step 0: two-stage-commit

## 읽어야 할 파일

- `tools/harness/execute.py` — `_commit` (`:161-193`) · `_state_files` (`:156-159`).
  파일 상단 docstring 의 「수리 ④」가 이 축이다
- `.claude/commands/harness.md` — 러너 저작 규약

## 배경

러너는 step 마다 커밋을 **둘로 나눈다** — 코드 커밋 하나, 하네스 상태 커밋 하나. 섞으면
step diff 가 「무엇을 고쳤나」를 잃는다. 실측 회귀가 있다: 커밋 `36e8732a` 는
`feat(...): step 5` 에 `index.json` 6줄이 동승했다. 그 분리에 **테스트가 0건이다.**

## 작업

`apps/api/tests/harness/test_execute_commit.py` 를 신설하고 2단 커밋 계약을 단언하라.

최소한 이 넷을 덮어라:

1. **코드 커밋에 상태가 안 섞인다** — 코드 파일과 `index.json` 2종이 함께 변경된 상태에서
   `_commit("feat: x")` 를 부르면, 그 메시지의 커밋에 담긴 파일 목록에
   `phases/<dir>/index.json` 과 `phases/index.json` 이 **없다**
2. **상태는 뒤따르는 커밋에** — 같은 호출이 만든 두 번째 커밋의 메시지가
   `chore(<phase>): harness state` 이고 거기에 상태 파일 2종이 담긴다
3. **코드 변경이 없으면 원래 메시지를 쓴다** — 상태 파일만 바뀐 경우 상태 커밋이
   `chore(...): harness state` 가 아니라 **호출자가 준 메시지 그대로**다
   (`blocked`·`completed` 표시가 그 경우다 — 무엇을 기록한 커밋인지를 잃지 않기 위함)
4. **반환값** — 커밋이 하나라도 생기면 `True`, 변경이 전혀 없으면 `False`

### git 픽스처

`_run_git` 은 `cwd=self._root` 로 진짜 git 을 부른다. `tmp_path` 에서 `git init` 하고
`user.email`·`user.name` 을 로컬 설정한 뒤 최초 커밋 하나를 만들어라. `git log --name-only`
또는 `git show --stat` 로 커밋에 담긴 파일을 확인하면 된다.
★전역 git 설정에 의존하지 마라 — `git -C <tmp> config user.email …` 로 그 저장소에만 박아라.

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
cd apps/api && uv run --env-file .env.local pytest tests/harness/test_execute_commit.py -q
cd apps/api && test "$(uv run --env-file .env.local pytest tests/harness/test_execute_commit.py --collect-only -q 2>/dev/null | grep -c '::')" -ge 4
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
