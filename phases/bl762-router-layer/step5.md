# Step 5: boundary-lock-ast — 계층 경계를 AST 테스트로 못박는다

이전 step 들이 **[BL-762]** 의 본체를 끝냈다 — `apps/api/src/trading/router.py` 의
`Repository()` 직접 조립이 11 → 0 이 됐다. 이 step 은 **그 상태가 되돌아가지 않게** 하는
회귀 테스트를 세운다.

★**grep 으로 재지 마라.** `grep -c 'Repository('` 는 `import OrderRepository as _OR` 한 줄이면
0 이 된다(문자열 검사는 우회 가능하다). 계약은 `ast` 파싱으로 재고, grep 은 보조로만 쓴다.

## 읽어야 할 파일

- `apps/api/tests/common/test_metric_guard_census.py` — 이 레포에서 **AST 로 소스를 검사하는
  기존 관용구**다. `_source_trees()` 수집 방식과 `test_protected_site_list_is_not_vacuous`
  (공허화 방지 = 양성 대조)를 그대로 미러해라
- `apps/api/src/trading/router.py`(리팩터 후 상태) · `apps/api/src/trading/dependencies.py`
- `apps/api/AGENTS.md` §3 — 레이어 규칙 원문

## 작업

신규 파일 **하나만** 만든다: `apps/api/tests/trading/test_router_layer_boundary.py`

검사 대상은 `apps/api/src/*/router.py` **전량**이다(2026-08-19 실측: 9파일, 라우트 62개).
파일마다 `ast.parse` 한 뒤 다음 3종을 단언한다. 이름은 아래를 그대로 쓴다:

1. `test_routers_do_not_instantiate_repositories`
   - `ast.walk` 로 모든 `ast.Call` 을 돌며 호출 대상 이름이 `Repository` 로 끝나면 위반.
     `func` 가 `ast.Name` 인 경우와 `ast.Attribute` 인 경우를 **둘 다** 본다
     (`OrderRepository(...)` 와 `repositories.OrderRepository(...)`).
   - 위반이 있으면 `파일:줄번호:이름` 목록을 담아 assert 로 터뜨린다.
   - 실패 메시지에 「Repository 조립은 `dependencies.py` 가 유일한 자리다 (AGENTS.md §3)」를 적어라.

2. `test_routers_do_not_take_async_session`
   - 모듈 안에 `get_async_session` 이라는 이름이 **import 되거나 참조되면** 위반
     (`ast.ImportFrom`/`ast.Import` 의 alias 이름 + `ast.Name`/`ast.Attribute` 참조).
   - 함수 인자 annotation 에 `AsyncSession` 이 나오면 위반
     (`ast.arg.annotation` 을 `ast.unparse` 해서 `AsyncSession` 포함 여부로 판정).

3. `test_router_scan_is_not_vacuous` — ★**양성 대조**. 대상에 실제로 닿았음을 증명한다.
   - 수집된 router 파일이 **8개 이상**이고, 모든 파일이 파싱에 성공했다.
   - `@router.<method>(...)` 데코레이터가 붙은 함수(동기/비동기 모두)의 총합이 **55개 이상**이다.
   - 그중 `src/trading/router.py` 한 파일이 **20개 이상**을 갖는다.
   - 이 셋 중 하나라도 어긋나면 「경로가 틀려 0건이라 통과」한 것이므로 red 여야 한다.
     (2026-08-19 실측치: 파일 9 · 총 라우트 62 · trading 23)

경로는 테스트 파일 위치에서 `Path(__file__).resolve().parents[2] / "src"` 처럼 파생시켜라 —
cwd 에 의존하는 상대 경로를 쓰지 마라(러너는 레포 루트에서 돈다).

## Acceptance Criteria

```bash
cd apps/api && uv run --env-file .env.local pytest tests/trading/test_router_layer_boundary.py -q
cd apps/api && n=$(uv run --env-file .env.local pytest tests/trading/test_router_layer_boundary.py --collect-only -q 2>/dev/null | grep -c '::test_'); echo "collected=$n"; test "$n" -ge 3
n=$(grep -c 'Repository(' apps/api/src/trading/router.py); echo "remaining=$n"; test "$n" = "0"
cd apps/api && uv run --env-file .env.local pytest -q
cd apps/api && uv run ruff check .
```

마지막 AC 는 **BE 전량 회귀**다(2026-08-19 실측 4830 passed / 384s).

## 금지사항

- **문자열 검사(`grep`·`"Repository(" in text`)로 계약을 재지 마라.** 이유: `as` 별칭 한 줄로
  우회된다. 판정은 AST 여야 한다.
- **양성 대조를 빼지 마라.** 이유: 부재 단언은 경로 오타 하나로 「0건이니 통과」하는
  항진명제가 된다 — 이 레포는 그 사고를 여러 번 겪었다.
- **다른 도메인의 라우터를 「고치지」 마라.** 지금 위반이 0건이므로 코드 수정은 필요 없다.
  만약 위반이 나오면 그것은 이전 step 의 회귀다 — 그 자리를 고쳐라.
- `src/` 아래에 새 파일을 만들지 마라(이 step 은 테스트만 추가한다).
- 커밋하지 마라(커밋은 러너 소관).
