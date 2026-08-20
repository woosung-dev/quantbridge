# Step 0: ref-predicates

## 읽어야 할 파일

- `tools/scripts/lib/pre-push-ref-guard.sh` — **이번 테스트의 대상** (132줄 전량, 절반이 근거 주석)
- `.husky/pre-push` — 이 라이브러리를 실제로 소싱해 쓰는 유일한 집행 경로
- `apps/api/tests/scripts/test_assert_main_checkout.py` — 이 디렉터리의 테스트 관용구
  (`subprocess.run` + `parents[4]` + 케이스당 함수 1개)

## 배경

이 파일은 **Golden Rule(`main` 직접 push 영구 차단)의 집행기**다. [ADR-037] 제로베이스에서
「권한 경계 소품」으로 살아남았지만, **그 판정을 재던 짝 하네스 `pre-push-guard-test.sh` 는
철거됐다.** 지금 테스트는 0건이고 파일 헤더 7행은 아직 그 철거된 하네스를 가리킨다.

★**철거된 감시가 남긴 주석은 「지금도 지켜진다」의 근거가 아니다** — 2026-08-20 회차가
`db-backup.sh --help` 에서 정확히 같은 병을 잡았다.

이 파일이 기록하는 **문서화된 사고 2건**([BL-554]·[BL-555] codex 적대 리뷰):

- **G1 P1** — 화이트리스트를 `local_ref` 로 먼저 태우면 `git push origin feat/foo:main` 이
  통과한다(stdin 은 local=`refs/heads/feat/foo` · **remote=`refs/heads/main`**). 실제 원격 main
  갱신이 그대로 나가는 fail-open 이다
- **G1 P2** — 삭제 판정이 sha 길이를 안 보면 `0`·`000` 같은 malformed 입력이 삭제로 인정돼
  fail-open 이 된다

이 step 은 **헬퍼 5개(순수 술어)** 를 고정한다. 조합 판정(`qb_push_ref_verdict`)은 step 1 이다.

## 작업

`apps/api/tests/scripts/test_pre_push_ref_guard.py` 를 신설한다.

### 호출 방식 (이 lane 의 유일한 방식)

대상은 **source 전용 라이브러리**이고 진입점이 없다. 진짜 파일을 그대로 소싱해 함수를 부른다.

```python
import subprocess
from pathlib import Path

LIB = Path(__file__).resolve().parents[4] / "tools" / "scripts" / "lib" / "pre-push-ref-guard.sh"


def call(fn: str, *args: str, shell: str = "sh") -> subprocess.CompletedProcess[str]:
    """술어를 1회 호출한다. 판정은 종료 코드다 (stdout 은 verdict 함수에서만 쓴다)."""
    script = f'. "$1"; shift; {fn} "$@"'
    return subprocess.run(
        [shell, "-c", script, "x", str(LIB), *args],
        capture_output=True, text=True, timeout=60,
    )
```

★**기본 인터프리터는 `sh` 다** — 헤더 계약이 「POSIX sh 전용. 훅은 `sh -e` 로 돈다」이고,
집행 경로(`.husky/pre-push`)가 그것이다. `bash` 로만 재면 계약 위반(`[[ ]]`·배열)이 초록으로 샌다.

### 최소한 이 여덟을 덮어라 (케이스 ≥8)

1. **`qb_ref_is_protected` 양성** — `refs/heads/main` · `refs/heads/master` · 접두사 없는
   `main` · `master` 넷 다 rc=0 (`${1#refs/heads/}` 라 양쪽 표기를 다 받는다)
2. ★**`qb_ref_is_protected` 음성** — `refs/heads/mainline` · `refs/heads/main-2` ·
   `refs/heads/feat/main` · `refs/heads/notmain` 은 rc=1. **접두사 일치로 퍼지면 안 된다**
3. **`qb_ref_is_head_ref`** — `refs/heads/x` → 0 · `refs/heads/` (빈 이름) → 1 ·
   `refs/tags/v1` → 1 · `HEAD` → 1
4. **`qb_ref_is_tag_ref`** — `refs/tags/v1` → 0 · `refs/tags/` → 1 · `refs/heads/v1` → 1
5. **`qb_ref_is_whitelisted` 전건** — `stage/ feat/ fix/ chore/ docs/ test/ refactor/ hotfix/`
   **8개 접두사를 하나도 빠뜨리지 말고** 각각 rc=0 (parametrize)
6. ★**`qb_ref_is_whitelisted` 음성** — `feature/x`(목록에 없다) · `wip-x` · `main` ·
   빈 문자열은 rc=1. **`feature/` 를 통과시키면 안 된다** — 목록은 `feat/` 다
7. ★**`qb_ref_is_delete` — sha 길이 축**(G1 P2). `(delete)` + 임의 sha → 0 ·
   `0`×40 → 0 · **`000` → 1** · `0`×39 → 1 · `0`×40 중 한 글자가 `1` → 1 ·
   `0`×41 → 0. **짧은 sha 가 삭제로 인정되면 fail-open 이다**
8. ★**양성 대조 — 소싱이 실제로 됐는지 재라.** `sh -c '. lib; type qb_push_ref_verdict …'`
   로 **5개 술어 + verdict 함수 6개가 전부 정의됐음**을 한 케이스에서 단언한다.
   이것이 없으면 경로 오타로 아무것도 안 불린 채 rc 만 맞아 통과할 수 있다

★**`sh -e` 계약도 한 줄 재라** — `sh -e -c '. lib; qb_ref_is_whitelisted refs/heads/wip-x'`
가 **소싱 도중에 죽지 않는지**(rc 가 1 이고 stderr 에 syntax 오류가 없는지). 헤더가
「`set -e` 아래에서 source 되므로 문장 형태의 `[ ... ] && cmd` 를 쓰지 않는다」고 적은 계약이다.

## Acceptance Criteria

```bash
cd apps/api && uv run --env-file .env.local pytest tests/scripts/test_pre_push_ref_guard.py -q
cd apps/api && test "$(uv run --env-file .env.local pytest tests/scripts/test_pre_push_ref_guard.py --collect-only -q 2>/dev/null | grep -c '::')" -ge 8
cd apps/api && uv run ruff check tests/scripts/
```

★두 번째 AC 는 **양성 대조**다. 착수 시점 이 파일은 없으므로 첫 AC 는 rc=4 (red) 다.

## 자기 점검

1. 위 AC 를 직접 실행해 green 을 확인한다. `status` 를 `completed` 로 바꾸지 마라.
2. `summary` 에 **다음 step 이 쓸 것**을 남겨라 — 헬퍼 호출부의 시그니처와 케이스 수.
3. 사람 개입이 필요하면 `status:"blocked"` 와 `blocked_reason` 을 쓰고 즉시 중단한다.

## 금지사항

- `tools/scripts/lib/pre-push-ref-guard.sh` 를 **수정하지 마라.** 결함을 찾으면
  `@pytest.mark.xfail(strict=True, reason="…")` + `summary` 한 줄
- ★**진짜 `git push` 를 하지 마라.** 이유: 이 훅이 지키는 것이 원격 main 이다.
  이 lane 은 술어 함수만 부른다 — git 을 아예 호출하지 않는다
- ★**`.husky/**` 를 건드리지 마라\*\* — 집행 경로라 고치면 이 워크트리의 커밋이 막힌다
- **공용 헬퍼 모듈을 만들지 마라**(다른 lane 과 동시에 도는 중이다). `conftest.py`·
  `shards.json`·`docs/**` 무변경. DB 픽스처 금지
- 커밋하지 마라(커밋은 러너 소관)
- macOS bash 3.2 · ubuntu bash 5 · `/bin/sh` 세 곳에서 통과해야 한다
