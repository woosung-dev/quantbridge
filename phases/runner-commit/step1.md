# Step 1: branch-and-state-index

## 읽어야 할 파일

- `tools/harness/execute.py` — `_checkout_branch` (`:140-154`) · `_update_step` (`:283-288`) ·
  `_update_top_index` (`:290-300`)
- `apps/api/tests/harness/test_execute_commit.py` — **step 0 이 만든 그 파일**. 여기에 이어 쓴다

## 배경

step 0 이 커밋 분리를 깔았다. 남은 것은 **브랜치와 상태 파일** 축이다. 브랜치 이름이 어긋나면
러너가 남의 브랜치에 커밋하고, 최상위 `phases/index.json` 이 안 따라오면 다음 세션이 끝난
phase 를 미완으로 읽는다.

## 작업

`test_execute_commit.py` 에 이어서 최소 네 축을 더 단언하라:

1. **브랜치 이름 규약** — `_checkout_branch` 가 만드는 이름은 `feat/harness-<phase>` 이고
   여기서 `<phase>` 는 **`index.json` 의 `phase` 값**이다(디렉터리명이 아니다).
   ★`feat/` 접두는 pre-push ref 가드 화이트리스트라 협상 불가다
2. **이미 그 브랜치면 아무것도 하지 않는다** — HEAD 가 이미 대상 브랜치일 때 checkout 을
   부르지 않는다
3. **최상위 인덱스 갱신** — `_update_top_index("completed")` 가 해당 `dir` 항목의 `status` 를
   바꾸고 `completed_at` 을 채운다. `"error"` 는 `failed_at`, `"blocked"` 는 `blocked_at` 이다.
   ★다른 phase 항목은 건드리지 않는다 — **이것이 병렬 lane 의 머지 안전을 지탱하는 계약이다**
4. **최상위 인덱스가 없으면 조용히 통과** — `phases/index.json` 이 없을 때 예외를 던지지 않는다

`_update_step` 은 지정한 step 번호의 항목만 갱신하고 나머지 step 은 그대로임을 함께 단언해라.

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
cd apps/api && test "$(uv run --env-file .env.local pytest tests/harness/test_execute_commit.py --collect-only -q 2>/dev/null | grep -c '::')" -ge 8
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
