# Step 1: push-verdict-order

## 읽어야 할 파일

- `tools/scripts/lib/pre-push-ref-guard.sh` — 특히 `qb_push_ref_verdict` 위의 **판정 순서 주석**
  (①~⑥). 그 순서가 곧 보호다
- `apps/api/tests/scripts/test_pre_push_ref_guard.py` — step 0 이 만든 파일. **여기에 덧붙인다**

## 배경

`qb_push_ref_verdict` 는 `(local_ref, local_sha, remote_ref, remote_sha, bypass)` 5-튜플을
받아 판정 문자열 **7종** 중 하나를 stdout 으로 낸다:

```
allow-tag | allow-tag-delete | allow-delete | allow-whitelist | allow-bypass
deny-main | deny-arbitrary
```

★**순서가 보호다.** `main`/`master` 를 **`remote_ref` 로 가장 먼저** 본다 — 화이트리스트를
`local_ref` 로 먼저 태우면 `git push origin feat/foo:main` 이 그대로 나간다(codex G1 P1).
그리고 ④ 는 **remote 와 local 을 둘 다** 화이트리스트로 본다 — local 만 보면
`feat/foo:refs/heads/wip-x` 로 임의 원격 ref 를 만들 수 있어 현재 동작보다 느슨해진다.

이 두 fail-open 은 **한 번 있었던 것을 수리한 것**이고, 그 수리를 지키던 하네스는 철거됐다.

## 작업

step 0 의 파일에 `qb_push_ref_verdict` 판정을 덧붙인다. **누적 케이스 ≥14.**

### 호출 방식

step 0 의 헬퍼를 그대로 쓰되 **stdout 을 읽는 판정용**을 하나 더 만든다:

```python
def verdict(local_ref, local_sha, remote_ref, remote_sha, bypass="0") -> str:
    r = call("qb_push_ref_verdict", local_ref, local_sha, remote_ref, remote_sha, bypass)
    assert r.returncode == 0, r.stderr
    return r.stdout.strip()
```

`SHA = "a" * 40`(정상 갱신) · `ZERO = "0" * 40`(삭제) 두 상수면 족하다.

### 최소한 이 축들을 덮어라

1. ★**G1 P1 — `feat/foo:main` 은 `deny-main`.**
   `verdict("refs/heads/feat/foo", SHA, "refs/heads/main", SHA) == "deny-main"`.
   **이 한 줄이 이 lane 의 이유다**
2. ★**bypass 로 뚫리지 않는다** — 같은 입력에 `bypass="1"` 을 줘도 `deny-main`
3. **삭제로도 뚫리지 않는다** — `local=("(delete)", ZERO)` · remote=`refs/heads/main` → `deny-main`.
   `master` 도 같은 축으로 한 줄
4. **`allow-tag-delete`** — remote=`refs/tags/v1.2.3` · local=`(delete)`/`ZERO`
5. **`allow-tag`** — 양쪽 다 `refs/tags/*`
6. ★**한쪽만 태그면 태그 규칙을 주지 않는다** — local=`refs/heads/feat/foo` ·
   remote=`refs/tags/x` → **`deny-arbitrary`**(bypass 0). 같은 입력에 bypass=1 이면
   `allow-bypass`. 교차 refspec 으로 규칙을 골라 타는 길이 없다는 단언이다
7. **`allow-delete`** — local=`(delete)`/`ZERO` · remote=`refs/heads/somebody-else`
8. **`allow-whitelist`** — 양쪽 다 `refs/heads/feat/...`
9. ★**G1 P1 ② — remote 만 비화이트리스트면 거부.**
   local=`refs/heads/feat/foo` · remote=`refs/heads/wip-x` → `deny-arbitrary`
   (**local 만 보는 구현이면 여기서 `allow-whitelist` 가 난다**)
10. **`allow-bypass`** — 위 9 와 같은 입력 + `bypass="1"`
11. **`deny-arbitrary`** — 화이트리스트 밖 + bypass 없음(기본 갈래)
12. ★**`remote_sha`(4번째 인자)는 판정에 쓰이지 않는다** — 같은 튜플에서 remote_sha 만
    바꿔 **판정이 동일**함을 단언한다(인터페이스를 git 의 4-튜플과 같게 두려고 받는 인자다)
13. ★**양성 대조 — 판정 문자열은 7종 집합 안에 있다.** 위 케이스들이 실제로 낸 값을 모아
    `set(...) <= {7종}` 이고 **비어 있지 않음**을 단언해라. 빈 집합이 부분집합으로 통과하는
    항진명제를 만들지 마라
14. ★**순서 증명 — 같은 refspec 이 두 규칙에 동시에 걸릴 때 어느 쪽이 이기는가.**
    local·remote 가 **둘 다 화이트리스트인데 remote 가 `main`** 일 수는 없으므로,
    대신 **삭제 ∧ 태그**(local=`(delete)`, remote=`refs/tags/x`)가 `allow-tag-delete` 이고
    **삭제 ∧ head**(remote=`refs/heads/x`)가 `allow-delete` 임을 나란히 단언해 ②가 ③보다
    앞이라는 것을 고정해라

★가능하면 `pytest.mark.parametrize` 로 **(5-튜플 → 기대 판정)** 표 하나를 만들어라 —
판정 순서가 바뀌면 표의 여러 줄이 함께 red 가 되어 진단이 쉽다.

## Acceptance Criteria

```bash
cd apps/api && uv run --env-file .env.local pytest tests/scripts/test_pre_push_ref_guard.py -q
cd apps/api && test "$(uv run --env-file .env.local pytest tests/scripts/test_pre_push_ref_guard.py --collect-only -q 2>/dev/null | grep -c '::')" -ge 14
cd apps/api && uv run ruff check tests/scripts/
```

## 자기 점검

1. 위 AC 를 직접 실행해 green 을 확인한다. `status` 를 `completed` 로 바꾸지 마라.
2. ★**step 0 의 케이스를 지우지 마라** — 누적 ≥14 는 step 0 의 ≥8 을 포함한 수다.
3. `summary` 에 판정 7종 중 **실제로 덮은 것**을 적어라.

## 금지사항

- 대상 스크립트 **수정 금지**(결함은 `xfail(strict=True)`) · `.husky/**` 무변경
- ★**진짜 `git push` 금지** — 이 lane 은 git 을 호출하지 않는다
- 공용 헬퍼 모듈 금지 · `conftest.py`·`shards.json`·`docs/**` 무변경 · DB 픽스처 금지
- 커밋하지 마라. macOS bash 3.2 · ubuntu bash 5 · `/bin/sh` 통과
