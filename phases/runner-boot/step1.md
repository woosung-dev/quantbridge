# Step 1: context-builders

## 읽어야 할 파일

- `tools/harness/execute.py` — `_stamp` (`:132-133`) · `_read_json`/`_write_json` (`:124-130`) ·
  `_load_guardrails` 정상 경로 (`:197-204`) · `_save_run` (`:237-239`)
- `apps/api/tests/harness/test_execute_boot.py` — **step 0 이 만든 그 파일**. 여기에 이어 쓴다

## 배경

step 0 이 거부 경로를 깔았다. 남은 것은 **정상 경로의 형식 계약**이다. 이것들은 작지만
전부 다른 것의 전제다 — 타임스탬프는 원장의 시간 축이고, JSON 쓰기 형식은 한글 요약이
`\uXXXX` 로 깨지지 않게 하는 유일한 방어이며, 가드레일 조립 결과는 모든 step 프롬프트의 앞머리다.

## 작업

`test_execute_boot.py` 에 이어서 최소 네 축을 더 단언하라:

1. **타임스탬프는 KST** — `_stamp()` 결과가 `+0900` 으로 끝나고 `%Y-%m-%dT%H:%M:%S%z` 로
   파싱된다. ★현재 시각을 하드코딩해 비교하지 마라 — 형식과 오프셋만 봐라
2. **JSON 쓰기 형식** — `_write_json` 은 한글을 이스케이프하지 않고(`ensure_ascii=False`)
   들여쓰기 2칸이며 **파일 끝에 개행**이 붙는다. `_read_json` 으로 왕복해도 값이 보존된다
3. **가드레일 조립** — `_load_guardrails()` 결과에 **4축 파일의 내용이 전부** 들어 있고
   각 절이 그 파일 경로를 제목으로 갖는다. ★파일 4개의 내용을 서로 다르게 만들어
   「하나만 읽고 4번 붙였다」를 배제해라
4. **run 산출 저장** — `_save_run` 이 `phases/<dir>/runs/step{N}-attempt{A}.json` 경로에
   쓰고, `runs/` 가 없으면 만든다

★`runs/` 는 `.gitignore` 의 `phases/*/runs/` 가 막는다 — 테스트가 만드는 것은 `tmp_path`
아래이므로 무관하지만, 진짜 `phases/` 아래에 쓰는 테스트를 만들지 마라.

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
cd apps/api && test "$(uv run --env-file .env.local pytest tests/harness/test_execute_boot.py --collect-only -q 2>/dev/null | grep -c '::')" -ge 8
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
