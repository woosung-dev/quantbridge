# Step 1: ac-sequence-and-timeout

## 읽어야 할 파일

- `tools/harness/execute.py` — `StepExecutor._run_ac` (`:264-281`) · `AC_TIMEOUT` (`:59`)
- `apps/api/tests/harness/test_execute_ac.py` — **step 0 이 만든 네 파일**. 여기에 이어 쓴다

## 배경

step 0 이 「통과/실패」 축을 깔았다. 남은 것은 **순서와 시간** 축이다. `_run_ac` 는 AC 를
순차로 돌다가 첫 실패에서 즉시 돌아온다 — 그 조기 반환이 깨지면 실패한 뒤에도 나머지 AC 가
돌아 검시 로그가 오염된다. 그리고 `AC_TIMEOUT`(기본 900s)을 넘긴 커맨드는 예외가 아니라
**판정 실패**로 흡수돼야 한다.

## 작업

`test_execute_ac.py` 에 이어서 최소 세 축을 더 단언하라:

1. **조기 반환** — AC 3개 중 두 번째가 rc≠0 일 때 **세 번째는 실행되지 않는다.**
   부작용으로 관측해라(세 번째 AC 가 파일을 만들게 하고, 그 파일이 없음을 단언)
2. **tail 상한** — 실패 커맨드가 40줄을 넘게 출력하면 저장된 `tail` 은 **마지막 40줄**이다
3. **타임아웃** — `AC_TIMEOUT` 을 아주 작게 갈아끼우고 그보다 오래 도는 커맨드를 주면
   예외가 밖으로 새지 않고 `(False, "AC timeout …")` 로 돌아온다.
   ★`ex.AC_TIMEOUT` 은 모듈 전역이라 `monkeypatch.setattr` 로 바꿀 수 있다.
   ★테스트가 오래 걸리지 않게 타임아웃은 1초 안쪽으로 잡아라

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
cd apps/api && uv run --env-file .env.local pytest tests/harness/test_execute_ac.py -q
cd apps/api && test "$(uv run --env-file .env.local pytest tests/harness/test_execute_ac.py --collect-only -q 2>/dev/null | grep -c '::')" -ge 7
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
