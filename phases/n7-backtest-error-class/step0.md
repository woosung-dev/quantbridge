# Step 0: 바뀌면 안 되는 분기 3개를 **먼저 못박는다**

## 읽어야 할 파일

- **`phases/n7-common.md`** — 이 회차 공통 금지사항·AC 규율. **먼저 읽어라**
- `apps/api/src/backtest/engine/v2_adapter.py` — **이번 lane 의 대상.** 특히 `:89-151`
- `apps/api/src/strategy/pine_v2/compat.py:42-120` — `parse_and_run_v2` 본문.
  **단계 경계가 여기 있다** (읽기 전용 — 고치지 마라)
- `apps/api/tests/backtest/engine/test_fault_injection.py` — **이번 lane 이 키우는 파일**
- `apps/api/src/backtest/engine/types.py:326` — `status` Literal 정의

## 배경 — [BL-383] 이 무엇인가

`v2_adapter.py` 는 `parse_and_run_v2(...)` 한 번의 호출을 `try` 로 감싸고 예외를 4갈래로 나눈다:

| 줄 | 예외 | 지금 status | 옳은가 |
| --- | --- | --- | --- |
| `:119` | `PineRuntimeError` | `"error"` | ✅ 맞다 |
| `:126` | `SyntaxError` | `"parse_failed"` | ✅ 맞다 (진짜 파싱 실패) |
| `:135` | `ValueError` | `"error"` | ✅ 맞다 (데이터 오류 · unknown track) |
| **`:144`** | **`except Exception`** | **`"parse_failed"`** | ❌ **결함** |

`:144` 는 **「우리도 예상 못 한 것」**을 잡는 자리인데 그것을 **「사용자의 Pine 이 파싱에
실패했다」**로 보고한다. 그리고 그 값은 화면에 나간다 —
`apps/api/src/backtest/service.py:421` 이 `f"engine status={outcome.status}"` 를 **사용자에게
보이는 에러 문구**로 쓴다. ⇒ **엔진 버그가 사용자 스크립트 탓으로 표시된다.**

★**단계 경계는 실재한다** (`compat.py`): `classify_script` → `resolve_default_qty` →
`extract_content` 가 **파싱 단계**이고 `TrackRunner.invoke` 가 **실행 단계**다. 그러나 둘은
**한 함수 안**이라 `v2_adapter` 에서는 구분할 수 없다. 그래서 이 lane 의 답은 「단계를
알아낸다」가 아니라 **「모를 때는 사용자 탓으로 돌리지 않는다」**다 (설계 결정 = Step 1).

## 착수 전 실측 (2026-08-24 · CONTROL)

- `test_fault_injection.py` 현재 케이스 수 **6건**, 전건 green
- `parse_failed` 는 레포 전체에서 **`types.py:326` Literal 과 `v2_adapter.py` 밖에 없다.**
  FE(`apps/web/src`)에는 **0건** ⇒ 하류 분기 폭발 반경이 없다
- `types.py:326` Literal 에 `"error"` 가 **이미 있다** ⇒ **타입 변경 불필요**
- `test_fault_injection.py:41-51` `test_parse_and_run_v2_raises_becomes_parse_failed` 가
  `RuntimeError("parse boom")` → `parse_failed` 를 **지금 고정하고 있다**.
  ★**이것이 Step 1 에서 뒤집힐 테스트다 — 「고쳐야 할 red」이지 회귀가 아니다.**

## 작업

1. **위 표를 네가 다시 재라.** 줄 번호는 움직인다. ★**다르면 네 값이 맞다** — `summary` 맨 앞에.
2. **`:119`·`:126`·`:135` 세 분기를 고정하는 테스트를 추가한다** (이 step 의 산출):
   - `PineRuntimeError` → `status == "error"`
   - `SyntaxError` → `status == "parse_failed"` ★**이것이 `parse_failed` 의 생존 증인이다**
   - `ValueError` → `status == "error"`
   - 각 케이스에서 `outcome.result is None` 과 `error` 문자열 전파도 함께 본다
3. ★**이 세 케이스는 지금 전부 green 이어야 한다.** red 가 나면 위 실측이 틀린 것이니
   **소스를 고치지 말고** `summary` 에 적어라 — 그건 이 lane 의 전제가 무너진 것이다.

## Acceptance Criteria

1. `test -f apps/api/tests/backtest/engine/test_fault_injection.py`
2. `cd apps/api && uv run --env-file .env.local pytest tests/backtest/engine/test_fault_injection.py -q`
3. `cd apps/api && test "$(uv run --env-file .env.local pytest tests/backtest/engine/test_fault_injection.py --collect-only -q 2>/dev/null | grep -c '::')" -ge 9`
4. `git diff --quiet -- apps/api/src/backtest/engine/v2_adapter.py`

★**AC 4 — 이 step 은 소스를 안 고친다.** 그물을 먼저 치고 다음 step 에서 고친다.

## `summary` 에 반드시 담을 것

- 재측정한 분기 좌표 4개 (위 표와 다르면 그 차이를 맨 앞에)
- 추가한 케이스 목록과 **각각이 무엇을 고정하는지**
- `SyntaxError → parse_failed` 케이스가 왜 **Step 1 이후에도 살아야 하는지** 한 줄

## 금지사항

- **`v2_adapter.py` 를 이 step 에서 고치지 마라** (AC 4 가 집행한다). 그물이 먼저다.
- **`apps/api/src/strategy/pine_v2/` 를 고치지 마라.** 이유: 거기는 **Pine 인터프리터 SSOT** 이고
  이 lane 의 범위가 아니다. 폭발 반경이 이 회차가 감당할 크기를 넘는다.
- **`types.py` 의 Literal 을 건드리지 마라.** 이유: `"error"` 가 **이미 있다.** 불필요한 변경이다.
- `phases/n7-common.md` 의 공통 금지사항 전부.
- 커밋하지 마라(커밋은 러너 소관).
