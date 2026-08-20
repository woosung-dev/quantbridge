# Step 0: main-checkout-verdict

## 읽어야 할 파일

- `tools/scripts/assert-main-checkout.sh` — **이번 테스트의 대상** (49줄 전량, 주석이 절반)
- `docs/reference/operations/worktree-parallel.md` §2.1 — 이 가드가 막는 사고
- `apps/api/tests/harness/test_execute_commit.py` — `tmp_path` 안에 **진짜 git 저장소**를
  만드는 선례
- `apps/api/tests/scripts/test_soak_gate_predicate.py` — 이 디렉터리의 테스트 관용구

## 배경

이 가드는 [ADR-037] 제로베이스에서 「권한 경계 소품」으로 **살아남은 셋 중 하나**이고,
`mise.toml` 의 **15개 task 가 `run` 첫 줄에서 인라인으로** 부른다. 막는 사고는
「워크트리에서 `mise run up`/`down`/`migrate`/`seed` 를 돌려 **1벌 공유인 컨테이너·앱 DB 를
함께 깨뜨리는 것**」이다.

★설계의 핵심은 **판정 불가를 차단으로 바꾸지 않는 것**이다 — git 이 없거나 레포가 아니면
**통과시킨다**. 그 예외가 없으면 CI·컨테이너에서 정상 타깃이 전부 죽는다.
그리고 슬롯 번호(`QB_SLOT`)로 판정하지 않는다 — 그건 `make QB_SLOT=0` 한 줄로 꺼졌다.
판정 근거는 **git 이다**: 워크트리에서만 `--absolute-git-dir` 과 `--git-common-dir` 이 갈린다.

이 가드가 조용히 「항상 통과」가 되면 2026-07-25 형태의 DB 전소가 다시 가능해진다.
★그런데 테스트가 0건이다.

## 작업

`apps/api/tests/scripts/test_assert_main_checkout.py` 를 신설하고 **판정 4분기**를 단언하라.

### 호출 방식 (이 lane 의 유일한 방식)

판정 근거가 **cwd 의 git** 이므로, 스크립트는 진짜 파일 그대로 두고 `cwd=` 만 바꾼다.

```python
import os, subprocess
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[3] / "tools" / "scripts" / "assert-main-checkout.sh"

def run(cwd: Path, *args, env=None):
    return subprocess.run(["bash", str(SCRIPT), *args], cwd=str(cwd),
                          capture_output=True, text=True, timeout=60, env=env)
```

`tmp_path` 에 진짜 git 저장소를 만들고 `git worktree add` 로 워크트리 하나를 판다:

```python
def _repo(tmp_path) -> tuple[Path, Path]:
    """(메인 체크아웃, 워크트리) — 둘 다 진짜 git 이다."""
    main = tmp_path / "main"; main.mkdir()
    def git(*a, cwd=main):
        subprocess.run(["git", *a], cwd=str(cwd), check=True,
                       capture_output=True, text=True)
    git("init", "-q", "-b", "main")
    git("config", "user.email", "t@example.com")
    git("config", "user.name", "t")
    (main / "f.txt").write_text("x", encoding="utf-8")
    git("add", "f.txt")
    git("commit", "-qm", "init")
    wt = tmp_path / "wt"
    git("worktree", "add", "-q", "-b", "side", str(wt))
    return main, wt
```

★`git commit` 이 필요하다 — 커밋 0개면 `git worktree add` 가 실패한다.
★`git init` 에 `-b main` 을 줘라(기본 브랜치 이름이 환경마다 다르다).

### 최소한 이 다섯을 덮어라

1. **메인 체크아웃 → rc=0** 이고 **아무것도 출력하지 않는다**(stderr 가 비어 있다)
2. ★**워크트리 → rc=1** 이고 stderr 에 ⑴ 준 타깃 이름 ⑵ `mise run <타깃>` 복구 지시
   ⑶ 메인 체크아웃 경로 ⑷ `worktree-parallel.md` 근거 링크가 실린다.
   **네 조각을 다 단언해라** — 사람이 이 메시지만 보고 복구해야 한다
3. **인자를 생략하면 타깃 이름이 `이 타깃` 으로 대체된다** (워크트리에서, rc=1)
4. ★**음성 대조 ⑴ — git 저장소가 아닌 디렉터리 → rc=0.**
   (`tmp_path/plain` 같은 빈 디렉터리에서. ★`tmp_path` 자체가 다른 저장소 **안**이 아닌지
   확인해라 — pytest 의 `tmp_path` 는 보통 `/private/var/...` 라 안전하지만, 확실히 하려면
   그 디렉터리에서 `git rev-parse --absolute-git-dir` 이 실패하는지 테스트 안에서 먼저 재라)
5. ★**음성 대조 ⑵ — `git` 이 PATH 에 없으면 rc=0.**
   `env` 에 `PATH` 를 `git` 이 없는 디렉터리 하나로 좁혀서 워크트리 안에서 돌려라
   (`bash` 는 절대경로로 부르므로 PATH 가 좁아도 스크립트는 뜬다. `/usr/bin` 을 통째로
   빼면 `git` 뿐 아니라 다른 것도 사라지니, **빈 tmp 디렉터리 하나만** PATH 로 줘라).
   ★4·5 가 이 lane 의 판별력이다 — 이 둘이 없으면 **「항상 rc=1」인 가드**도 1~3 을 통과한다

★2 의 반대 방향도 한 줄 재라: **워크트리에서 rc=1 인데 메인에서 rc=0** 인 것을 같은
테스트 안에서 연달아 확인하면 「환경 때문에 우연히 갈렸다」를 배제할 수 있다.

## Acceptance Criteria

```bash
cd apps/api && uv run --env-file .env.local pytest tests/scripts/test_assert_main_checkout.py -q
cd apps/api && test "$(uv run --env-file .env.local pytest tests/scripts/test_assert_main_checkout.py --collect-only -q 2>/dev/null | grep -c '::')" -ge 5
cd apps/api && uv run ruff check tests/scripts/
```

★두 번째 AC 는 **양성 대조**다. 착수 시점 이 파일은 없으므로 첫 AC 는 rc=4 (red) 다.

## 자기 점검

1. 위 AC 를 직접 실행해 green 을 확인한다. `status` 를 `completed` 로 바꾸지 마라.
2. ★**만든 워크트리를 정리해라** — `tmp_path` 는 pytest 가 지우지만 `git worktree add` 는
   메인 저장소의 `.git/worktrees/` 에 등록을 남긴다. 그 메인 저장소도 `tmp_path` 안이므로
   함께 사라진다 — **진짜 레포에 `git worktree add` 를 하지 않는 것**이 그 전제다. 확인해라:
   테스트 후 `git worktree list` 에 새 항목이 없어야 한다.
3. 사람 개입이 필요하면 `status:"blocked"` 와 `blocked_reason` 을 쓰고 즉시 중단한다.

## 금지사항

- `tools/scripts/assert-main-checkout.sh` 를 **수정하지 마라.** 결함을 찾으면
  `@pytest.mark.xfail(reason="…")` + `summary` 한 줄
- ★**진짜 레포에 `git worktree add` 를 하지 마라.** 이유: 지금 이 회차가 워크트리 6벌을
  동시에 쓰고 있고, 슬롯 관리(`.worktree-slot`)와 충돌한다. 반드시 `tmp_path` 안의
  새 저장소에만 만들어라
- **`mise run` 을 실행하지 마라** — 이 가드를 부르는 쪽이라 진짜 컨테이너·DB 를 건드린다
- `git` 을 스텁하지 마라 — 판정 근거 자체가 git 이다. 5번은 스텁이 아니라
  **PATH 에서 없애는** 방식이다
- `conftest.py`·공용 헬퍼 모듈·`shards.json`·`docs/**` 무변경. DB 픽스처 금지. 커밋하지 마라
- macOS bash 3.2 · ubuntu bash 5 양쪽에서 통과해야 한다
