# Step 0: convert-service

## 읽어야 할 파일

- `apps/api/src/strategy/convert/service.py` (242줄) — **이번 테스트의 대상**
- `apps/api/src/strategy/convert/prompt.py` — `SYSTEM_PROMPT` · `USER_TEMPLATE`
- `apps/api/src/strategy/convert/schemas.py` — `ConvertIndicatorRequest` · `ConvertIndicatorResponse`
- `apps/api/tests/strategy/convert/test_convert_error_leak.py` — ★**[BL-772] 누출 축의 기존 선례.**
  **먼저 읽고 무엇이 이미 커버되는지 확인해라** — 겹치면 그 축은 겨누지 마라
- `apps/api/tests/strategy/convert/test_convert_service.py` — 기존 커버 범위 확인용

## 배경

★★**착수 전 CONTROL 이 전량 스위트 커버리지로 쟀다 (2026-08-21 · `concurrency=greenlet,thread` 교정본):**

```
src/strategy/convert/service.py   104 stmt   35 missed   61%
  miss: 70-72, 75->96, 86-88, 90-91, 99->104, 112-121, 177-206, 220-221, 234, 240
```

★★★**미커버 덩어리 셋이 각각 다른 종류의 위험이다:**

| 구간        | 무엇인가                                                                                                                                                                                            |
| ----------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **177-206** | **`_convert_with_gemini` 본문 전부** — fallback provider 경로가 통째로 무증거다. LLM 응답의 **코드펜스 벗기기**(188-194)와 usage 토큰 `or 0` 폴백 포함                                              |
| **112-121** | ★**[BL-772] 정보 누출 가드.** 주석이 「SDK 예외 문자열(엔드포인트 URL·모델명·요청 ID)을 심지 마라 — provider 이름까지다」라고 못박은 자리인데 **그 계약을 재는 테스트가 이 줄들에 도달하지 않는다** |
| **86-91**   | Anthropic 실패 갈래 2종(`RetryError` / `AnthropicError`) — fallback 이 발화하는 조건                                                                                                                |
| **220-240** | `_heuristic_quality_warnings` 세 갈래(빈 결과 · 드로잉 흔적 잔존 · 원본과 100% 동일)                                                                                                                |

⇒ **지금 `_convert_with_gemini` 를 통째로 지워도, 그리고 113-118 의 `RuntimeError` 문자열에 `exc` 를
끼워 넣어도 스위트는 초록이다.**

★**착수 전 CONTROL 실측 — 구조 (모듈을 직접 읽어 확인했다):**

| 축                   | 관측                                                                                                                                                                                       |
| -------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 키 둘 다 없음        | `RuntimeError("ANTHROPIC_API_KEY 또는 GEMINI_API_KEY 중 하나가 필요합니다. …")`                                                                                                            |
| `mode == "sliced"`   | `SignalExtractor().extract(code, mode="ast")` → **`result.is_runnable` 이면 LLM 없이 즉시 반환**(`input_tokens=0`) / 아니면 `code_to_send = result.sliced_code` + `removed_functions` 경고 |
| Anthropic 실패 3갈래 | `RetryError` → `exc.last_attempt.exception()` / `anthropic.AnthropicError` / `Exception` — 셋 다 `anthropic_error` 에 담고 **fallback 으로 내려간다**                                      |
| Gemini fallback 경고 | `anthropic_error is not None` 일 때만 `"Anthropic 실패 → Gemini fallback"` 을 warnings 에 **추가**                                                                                         |
| Gemini 실패          | `anthropic_error` 있으면 `RuntimeError("양쪽 provider 모두 실패")`, 없으면 `RuntimeError("Gemini 변환 실패")` — **둘 다 `from exc`**                                                       |
| Anthropic 만 실패    | `RuntimeError("Anthropic 변환 실패 (Gemini fallback 미설정)")`                                                                                                                             |
| Gemini 코드펜스      | `converted.startswith("```")` 이면 첫 줄과 **마지막 줄이 ``` 로 시작할 때** 각각 벗긴다                                                                                                    |
| Gemini usage         | `usage.prompt_token_count` / `candidates_token_count` — **`usage` 가 None 이거나 값이 falsy 면 `0`**                                                                                       |
| 품질 경고 3종        | 빈 결과 → 그 한 줄만 **즉시 반환** / `leftover_patterns` 7종 중 포함된 것 나열 / **`len>100` 이고 strip 비교가 같으면** 「100% 동일」                                                      |

★**`anthropic` · `genai` SDK 클라이언트는 함수 본문에서 생성된다**(`anthropic.Anthropic(api_key=…)` ·
`genai.Client(api_key=…)`). mock 은 그 생성자를 겨눠라. **`_call_anthropic` 은 `@retry` 가 붙어 있다** —
직접 부르면 재시도가 돈다(테스트가 느려진다).

## 작업

`apps/api/tests/strategy/convert/test_convert_service_fallback.py` **하나**를 신설한다.
`anthropic.Anthropic` 과 `genai.Client` 를 mock 한다. **진짜 LLM API 를 부르지 마라(네트워크 0).**

### 최소한 이 열을 덮어라 (케이스 ≥10)

1. ★★★**[BL-772] — Gemini 실패 시 `RuntimeError` 문자열에 SDK 예외 내용이 안 실린다.**
   Gemini 를 **URL·모델명·요청ID 를 담은 예외**로 실패시키고, 밖으로 나온 `RuntimeError` 의 **문자열에
   그 토큰들이 없는지** 재라. ★`__cause__` 에는 있어도 된다(로그용) — **메시지에만 없으면 된다**
2. ★★★**같은 축의 200 응답 판** — Anthropic 이 실패하고 Gemini 가 성공하면 warnings 에
   `"Anthropic 실패 → Gemini fallback"` **만** 들어가고 **SDK 예외 문자열이 안 들어간다**
3. ★★**양쪽 실패 → `RuntimeError("양쪽 provider 모두 실패")`** · **Gemini 만 있고 실패 →
   `RuntimeError("Gemini 변환 실패")`** — 두 갈래가 **다른 메시지**임을 재라
4. ★**Anthropic 만 설정 + 실패 → `RuntimeError("Anthropic 변환 실패 (Gemini fallback 미설정)")`**
5. ★★**키 둘 다 없음 → `RuntimeError`** (LLM 호출 0회)
6. ★★**`_convert_with_gemini` 정상 경로** — 응답 텍스트가 그대로 `converted_code` 이고
   warnings 첫 줄이 `f"Gemini {model} 로 변환 완료 (fallback)"` 이다.
   ★**`USER_TEMPLATE.format(code=…)` 과 `SYSTEM_PROMPT` 가 실제로 전달되는지**도 재라
7. ★★**Gemini 코드펜스 벗기기** — ` ```pine ` 로 시작하고 ` ``` ` 로 끝나는 응답에서 **양쪽이 벗겨진다**.
   ★**앞만 있고 뒤가 없는 경우**도 재라(뒤 조건이 독립이다)
8. ★★**Gemini usage 폴백** — `usage_metadata` 가 `None` 일 때와 토큰 값이 `None` 일 때 **둘 다 `0`** 이다
9. ★★**`_heuristic_quality_warnings` 3갈래** — ⑴ 빈/공백 결과면 **그 한 줄만** 나오고 뒤 검사를 안 한다
   (드로잉 흔적이 있어도 안 나온다 — **즉시 반환을 재는 축**) ⑵ `leftover_patterns` 중 **여러 개가
   걸리면 전부 나열**된다 ⑶ **길이 100 초과 + strip 동일**이면 「100% 동일」 경고.
   ★**길이 100 이하면 안 나오는지**도 재라(경계)
10. ★★**`mode="sliced"` 이고 `is_runnable` 이면 LLM 을 **0회** 부른다** — `input_tokens == 0` 이고
    warnings 가 `"AST 슬라이싱으로 직접 실행 가능한 코드 추출 (LLM 미사용)"` 이다.
    ★**LLM mock 이 안 불렸음을 단언해라** — 이것이 비용 축이다
11. ★**Anthropic 실패 3갈래가 전부 fallback 으로 내려간다** — `RetryError` · `AnthropicError` ·
    일반 `Exception`. ★`RetryError` 는 `exc.last_attempt.exception()` 을 꺼내는지 **관측해서 박아라**

## Acceptance Criteria

```bash
cd apps/api && uv run --env-file .env.local pytest tests/strategy/convert/test_convert_service_fallback.py -q
cd apps/api && test "$(uv run --env-file .env.local pytest tests/strategy/convert/test_convert_service_fallback.py --collect-only -q 2>/dev/null | grep -c '::')" -ge 10
cd apps/api && uv run --env-file .env.local pytest tests/strategy/convert -q
cd apps/api && uv run ruff check tests/strategy/convert/test_convert_service_fallback.py && uv run ruff format --check tests/strategy/convert/test_convert_service_fallback.py
```

★2번째 AC 는 **양성 대조**다. 착수 시점 이 파일은 없으므로 첫 AC 는 **rc=4**(CONTROL 실측 2026-08-21).
★`--env-file .env.local` 을 빼지 마라 — DB 가드가 rc=3 으로 거부한다.

## 자기 점검

1. 위 AC 를 직접 실행해 green 을 확인한다. ★최종 판정은 러너가 재실행해 내린다 —
   `status` 를 `completed` 로 바꾸지 마라.
2. `summary` 에 케이스 수와 **⑾의 `RetryError` 관측 결과**, 그리고 **기존 `test_convert_error_leak.py` 와
   겹친 축이 있었는지**를 남겨라.
3. 사람 개입이 필요하면 `status:"blocked"` 와 `blocked_reason` 을 쓰고 즉시 중단한다.

## 금지사항

- ★**`src/strategy/convert/service.py` · `prompt.py` 를 수정하지 마라.** 이유: 이 회차의 계약은
  「테스트만 추가하고 대상 소스는 0줄 변경」이다. **[BL-772] 누출을 발견하면 고치지 말고
  `status:"blocked"` + `blocked_reason`** 으로 멈춰라 — 보안 축은 사람 diff 를 거쳐야 한다
- ★★**진짜 Anthropic·Gemini API 를 부르지 마라(네트워크 0).** 이유: 8 lane 이 동시에 돌고,
  실 API 는 비용과 비결정성을 만든다. `anthropic.Anthropic` 과 `genai.Client` 생성자를 mock 해라
- ★**`_call_anthropic` 을 직접 부르지 마라** — `@retry(stop_after_attempt(3), wait_exponential)` 이 붙어 있어
  테스트가 수 초씩 늘어난다. `convert()` 를 통해 재고, 실패를 만들려면 **client 쪽**을 던지게 해라
- ★★**`xfail(strict=True)` 를 쓰지 마라. 이유:** 「제품 코드가 지금 틀렸다」를 원장에 박는 주장인데
  **AC·변이·사람 diff 세 층이 전부 통과시킨다**([LESSON-121]). 근거는 `summary` 에 적고 테스트는 지금 동작을 고정해라
- ★**재지 않은 값을 단언하지 마라.** 이유: step 의 산문은 세션에게 AC 와 구별되지 않는다([LESSON-122]).
  위 표는 CONTROL 이 모듈을 읽고 확인한 것이고, 「관측해서 박아라」라고 쓴 것은 **먼저 돌려 보고** 써라
- ★**`tests/strategy/convert/` 의 기존 3파일을 수정하지 마라** — 이 lane 소유가 아니다
- ★**`SignalExtractor` 를 겨누지 마라** — `tests/strategy/pine_v2/test_signal_extractor.py` 소관이다.
  ⑽ 에서는 그것을 **mock 하거나** `is_runnable` 이 참이 되는 입력을 써라
- ★**`conftest.py` · `pyproject.toml` · `shards.json` 무변경**(8 lane 동시 실행 — 병합 충돌)
- **공용 헬퍼 모듈을 만들지 마라** — fake client/response 는 이 테스트 파일 안에 둬라
- **새 pytest 마커를 쓰지 마라** — `--strict-markers` 라 `pyproject.toml` 을 함께 고쳐야 하고 그것이 공유 파일이다
- `docs/**` · `phases/**` 무변경. 다른 lane 의 테스트 파일을 만들지 마라
- 커밋하지 마라(커밋은 러너 소관)
