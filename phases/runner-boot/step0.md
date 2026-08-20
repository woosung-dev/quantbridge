# Step 0: boot-refusals

## 읽어야 할 파일

- `tools/harness/execute.py` — `StepExecutor.__init__` (`:96-120`) ·
  `_load_guardrails` (`:197-204`) · `run()` 의 blocker 검사 (`:360-362`)
- `.claude/commands/harness.md` — 러너 저작 규약

## 배경

이 러너는 **시작하지 않는 것**으로 여러 사고를 막는다 — `ac` 없는 step 은 판정 불가라
자기채점으로의 회귀이고, 가드레일 4축이 없으면 무근거 주입이며, `error`·`blocked` 상태의
step 이 남아 있으면 사람이 검시하지 않은 트리 위에서 다시 도는 것이다.

★**거부는 조용히 사라지기 쉬운 계약이다.** 조건문 하나가 뒤집혀도 정상 경로는 그대로 돌아
아무도 모른다. 이 step 이 그 거부들을 못박는다.

## 작업

`apps/api/tests/harness/test_execute_boot.py` 를 신설하고 **거부 경로**를 단언하라.

최소한 이 넷을 덮어라:

1. **phase 디렉터리 부재** — 없는 이름으로 `StepExecutor(...)` 를 만들면 `SystemExit` 이고
   메시지에 그 경로가 들어간다
2. **`index.json` 부재** — 디렉터리는 있는데 `index.json` 이 없으면 `SystemExit`
3. **`ac` 배열 부재** — step 하나라도 `ac` 가 없거나 빈 배열이면 `SystemExit` 이고,
   메시지에 **그 step 번호**가 들어간다. ★`ac` 가 있는 step 만 있으면 통과해야 한다(음성 대조)
4. **가드레일 4축** — `CONTEXT.md` · `AGENTS.md` · `apps/api/AGENTS.md` · `apps/web/AGENTS.md`
   중 **하나라도** 없으면 `_load_guardrails` 가 `SystemExit` 이다. 넷을 각각 하나씩 지워
   네 경우 모두 거부되는지 봐라 — 「하나만 검사하고 통과」를 잡는 유일한 방법이다

여유가 있으면 `run()` 의 blocker 검사(`error`·`blocked` 상태 step 이 있으면 시작 거부)도 덮어라.

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
cd apps/api && uv run --env-file .env.local pytest tests/harness/test_execute_boot.py -q
cd apps/api && test "$(uv run --env-file .env.local pytest tests/harness/test_execute_boot.py --collect-only -q 2>/dev/null | grep -c '::')" -ge 4
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
