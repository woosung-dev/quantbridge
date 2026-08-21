# Step 0: sizing-identity

## 읽어야 할 파일

- `apps/api/src/strategy/pine_v2/sizing.py` (67줄) — **대상 ①**. `extract_pine_default_qty` ·
  `resolve_default_qty`. docstring 에 [BL-188] 우선순위 체인과 [BL-479] fail-closed 근거가 있다
- `apps/api/src/trading/account_identity.py` (70줄) — **대상 ②**. `dedupe_accounts_by_exchange_uid`.
  docstring 에 [BL-605]·[BL-651] 실측 피해 2건과 대표 행 선택 규칙 3개가 있다
- `apps/api/src/strategy/pine_v2/ast_extractor.py` — `extract_content` 가 돌려주는
  `ScriptContent.declaration` 의 필드를 **여기서 확인해라** (`kind` · `default_qty_type` · `default_qty_value`)
- `apps/api/tests/strategy/pine_v2/` — 이 디렉터리의 Pine 소스 작성 관용구를 보고 같은 모양으로 써라

## 배경

둘 다 **순수 판정 함수**인데 테스트가 0건이다(2026-08-21 실측 — 공개 심볼이 `tests/**` 전체에서
**한 번도 언급되지 않는다**). 그리고 둘 다 **틀리면 조용히 돈을 잃는 자리**다.

★★**`sizing.py` 는 주문 수량의 SSOT 다.** 백테스트(`compat.parse_and_run_v2`)와 라이브
(`event_loop.run_live`)가 **같은 함수**를 부른다. 우선순위 체인이 밀리면 백테스트와 실주문이
다른 수량으로 돈다 — 그리고 그 차이는 **체결이 난 뒤에야** 보인다.
★특히 [BL-479] fail-closed: `live_position_size_pct` 만 주고 `initial_capital` 을 빠뜨리면
**조용히 `(None, None)` 을 돌려 `qty=1.0` fallback 으로 실주문이 나가던** 사고가 있었다.
지금은 `ValueError` 로 막는데, **그 방어에 테스트가 없다.**

★★**`account_identity.py` 는 「행」과 「실제 계정」을 가르는 단독 책임이다.**
실측(2026-08-08)으로 같은 `exchange_uid` 를 공유하는 행이 2개 있었고, 그것이
[BL-605](청산 원장 574행 = 287 x 2) · [BL-651](미체결 조건부 2 vs 실제 1) **두 사고**를 냈다.
★docstring 이 대표 행 선택 규칙을 **셋** 적어 뒀는데(⑴ uid None 은 안 묶는다 ⑵ non-`read_only` 우선
⑶ 그 외 입력 순서) **아무도 안 재고 있다.**

★**착수 전 CONTROL 실측 (2026-08-21):** 둘 다 DB·네트워크·celery 를 안 문다.
`account_identity` 는 `src` import **0건**이고, `sizing` 은 `ast_extractor` 하나만 문다.
⇒ **픽스처 없이 순수 호출로 테스트된다.**

## 작업

**테스트 파일 2개**를 신설한다. 하나로 합치지 마라 — 도메인이 다르다.

- `apps/api/tests/strategy/pine_v2/test_default_qty_resolution.py` (케이스 ≥10)
- `apps/api/tests/trading/test_account_identity.py` (케이스 ≥7)

### ① `test_default_qty_resolution.py` — 최소한 이 열

1. ★**Pine 명시 → override.** `strategy(...)` 선언에 `default_qty_type`/`default_qty_value` 가 둘 다
   있으면 form·live 값을 **함께 줘도** Pine 값이 이긴다
2. ★**Pine 미명시 + form 명시 → form 값.** live 값도 함께 줘 봐라
3. ★**Pine·form 미명시 + live pct → `("strategy.percent_of_equity", pct)`**.
   ★두 번째 원소가 `float` 인지도 재라
4. **셋 다 미명시 → `(None, None)`**
5. ★★**[BL-479] fail-closed — `live_position_size_pct` 를 주고 `initial_capital=None` 이면
   `ValueError` 를 던진다.** `pytest.raises` 로 잡고 **메시지에 `BL-479` 가 있는지**까지 봐라.
   ★이 케이스가 없으면 「조용히 `qty=1.0` 으로 실주문」 회귀가 다시 열린다
6. ★**`initial_capital=None` + live pct 도 `None` 이면 `(None, None)`** — ⑸와 갈리는 자리다
   (예외가 아니라 정상 반환이다). 두 케이스를 **함께** 둬야 조건이 `and` 인지 `or` 인지가 잡힌다
7. ★**form 은 type·value 가 **둘 다** 있어야 쓴다** — 하나만 준 두 케이스를 parametrize 로 돌려
   form 을 건너뛰고 다음 단계로 내려간다
8. ★**Pine 도 type·value 가 둘 다 있어야 쓴다** — 하나만 있는 소스로 확인
9. ★**`extract_pine_default_qty` — `strategy` 가 아닌 스크립트(`indicator`)는 `(None, None)`**
10. ★**`default_qty_value` 가 숫자로 파싱되지 않으면 값이 `None` 이 된다**(던지지 않는다).
    ★**Pine 소스 문자열은 최소한으로 써라** — 전략 로직을 복사해 오면 인터프리터 개정마다
    의미 없이 red 가 난다. ★결과값을 손으로 추측해 적지 말고 **관측한 것을 박아라**

### ② `test_account_identity.py` — 최소한 이 일곱

계정은 `exchange_uid` · `read_only` 두 속성만 있는 **작은 더미 클래스**(또는 `SimpleNamespace`)로 충분하다.

1. ★**같은 uid 두 행 → 1행만 남는다**
2. ★★**`uid` 가 `None` 인 행은 서로 묶지 않는다** — `None` 이 셋이면 셋 다 남는다.
   ★**미상인 것들을 한 덩어리로 접으면 서로 다른 실제 계정이 조용히 사라진다**(docstring ⑴)
3. ★★**같은 uid 안에서 `read_only=True` 행이 먼저 와도 대표는 non-`read_only` 행이다**(⑵).
   read_only 행이 대표가 되면 스윕 결과가 전량 `unknown` 이 된다
4. ★**둘 다 non-`read_only` 면 입력 순서상 먼저 온 행이 대표다**(⑶ — 호출부가 `created_at asc`)
5. ★★**출력 순서는 각 uid 가 **처음 등장한 자리**를 지킨다** — 대표가 뒤 행으로 교체돼도 자리는
   앞에 남는다. uid 를 A,B,A 순으로 주고 결과가 A,B 인지 재라(호출부의 순서 가정)
6. ★**`read_only` 가 `None` 인 행의 처리** — `True` 가 아닌 값으로 취급되는지 **관측해서 박아라**
   (코드가 `is True` / `is not True` 로 비교한다)
7. ★**빈 리스트는 빈 리스트** + **중복이 없으면 입력 그대로 나온다**(길이·순서·원소 동일성).
   ★**이것이 양성 대조다** — dedupe 가 과하게 접는 것을 잡는다

## Acceptance Criteria

```bash
cd apps/api && uv run --env-file .env.local pytest tests/strategy/pine_v2/test_default_qty_resolution.py tests/trading/test_account_identity.py -q
cd apps/api && test "$(uv run --env-file .env.local pytest tests/strategy/pine_v2/test_default_qty_resolution.py --collect-only -q 2>/dev/null | grep -c '::')" -ge 10
cd apps/api && test "$(uv run --env-file .env.local pytest tests/trading/test_account_identity.py --collect-only -q 2>/dev/null | grep -c '::')" -ge 7
cd apps/api && uv run ruff check tests/strategy/pine_v2/test_default_qty_resolution.py tests/trading/test_account_identity.py
```

★2·3번째 AC 는 **파일별 양성 대조**다. 착수 시점 두 파일은 없으므로 첫 AC 는 rc=4 (CONTROL 실측 2026-08-21).
★`--env-file .env.local` 을 빼지 마라 — DB 가드가 rc=3 으로 거부한다.

## 자기 점검

1. 위 AC 를 직접 실행해 green 을 확인한다. ★최종 판정은 러너가 재실행해 내린다 —
   `status` 를 `completed` 로 바꾸지 마라.
2. `summary` 에 파일별 케이스 수와 **①⑩·②⑥에서 실제로 관측한 동작**을 남겨라.
3. 사람 개입이 필요하면 `status:"blocked"` 와 `blocked_reason` 을 쓰고 즉시 중단한다.

## 금지사항

- ★**`src/strategy/pine_v2/sizing.py` · `src/trading/account_identity.py` 를 수정하지 마라.**
  이유: 이 회차의 계약은 「테스트만 추가하고 대상 소스는 0줄 변경」이다. 결함은 `summary` 또는 `blocked` 로
- ★★**`xfail(strict=True)` 를 쓰지 마라. 이유:** 그것은 「제품 코드가 지금 틀렸다」를 원장에 박는
  주장인데 **AC·변이·사람 diff 세 층이 전부 통과시킨다**([LESSON-121] — 1차에서 3건 중 1건이 phantom
  이었다). 틀렸다고 판단되면 `summary` 에 근거와 함께 적고 **테스트는 지금 동작을 고정**해라
- ★**DB 를 치지 마라** — 둘 다 순수 함수다. 세션·엔진·픽스처가 필요하면 대상을 잘못 읽은 것이다
- ★**`conftest.py` · `shards.json` 무변경**(8 lane 동시 실행 — 병합 충돌)
- **공용 헬퍼 모듈을 만들지 마라** — 더미 클래스는 각 테스트 파일 안에 둬라
- `docs/**` · `phases/**` 무변경. 다른 lane 의 테스트 파일을 만들지 마라
- 커밋하지 마라(커밋은 러너 소관)
