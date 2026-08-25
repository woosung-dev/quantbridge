# Step 1: offload-parse-to-threadpool

## 읽어야 할 파일

- 앞 step 의 `summary`(고른 엔드포인트 · 테스트 함수 이름 3개)
- `apps/api/src/strategy/service.py:129-176`(`_parse`) · `:200-220` · `:222-263` · `:349-389`
- `apps/api/src/health/router.py:113` — 레포의 유일한 선례
- `apps/api/AGENTS.md` — 3-Layer 경계와 async 규약

## 작업

`_parse` 의 CPU 구간을 스레드풀로 옮겨 이벤트 루프를 놓아 준다.

★**시그니처 수준 지시** — 구현은 재량이되 아래 계약을 벗어나지 마라:

- `_parse` 자체의 **반환 튜플 형태를 바꾸지 마라.** 호출부 3곳이 언패킹하고 있다.
- 옮길 대상은 **CPU 를 잡는 부분**이다. `_parse` 안에는 regex 근사 수집(`_detect_version` ·
  `_strip_comments` · `findall` · `_collect_functions`)도 있는데 그것은 싸다. **`parse_to_ast(source)`
  호출이 병목**이다 — 통째로 옮기든 그 한 줄만 옮기든, 어느 쪽인지와 이유를 docstring 에 적어라.
- `run_in_threadpool`(`starlette.concurrency`) 또는 `asyncio.to_thread` 중 하나를 쓴다.
  ★**레포 선례는 `health/router.py:113` 하나뿐이므로 이것은 사실상 신설 패턴이다** —
  거기서 쓴 쪽을 따르는 것을 기본으로 하고, 다르게 골랐다면 이유를 적어라.
- 호출부 3곳(`parse_preview:201` · `create:231` · `update:375`)이 **전부** 새 경로를 지나야 한다.
  하나만 고치면 나머지 둘이 계속 막는다.
- **예외 전파를 바꾸지 마라.** `_parse` 는 지금 모든 예외를 잡아 `ParseStatus.error` 로 바꾼다
  (`:153` `except Exception`). 스레드풀 경유 후에도 같은 분기가 같은 결과를 내야 한다 —
  기존 테스트(`tests/strategy/test_strategies_parse.py`)가 그 계약의 증인이다.

그리고 step 0 의 단언 3종을 **뒤집는다**: 이제 블로킹 스텁을 넣어도 하트비트 틱이 목표에 도달해야 한다.
양성 대조(테스트 2)와 경로 도달 단언(테스트 3)은 **그대로 유지**해라 — 뒤집는 것은 테스트 1뿐이다.

★테스트 1 의 이름과 docstring 도 새 사실에 맞게 고쳐라. 「막힌다」를 단언하던 이름이 「안 막힌다」를
단언하면 다음 사람이 반대로 읽는다.

## Acceptance Criteria

```
cd apps/api && set -a; . ./.env.local; set +a; uv run pytest tests/strategy/test_parse_event_loop_blocking.py -q
cd apps/api && set -a; . ./.env.local; set +a; uv run pytest tests/strategy -q
cd apps/api && uv run mypy src/strategy/service.py
cd apps/api && uv run ruff check src/strategy tests/strategy
```

## 자기 점검

1. 위 AC 를 직접 실행해 green 을 확인한다. `status` 를 `completed` 로 바꾸지 마라.
2. `summary` 에 ⑴ 고른 수단(`run_in_threadpool` / `to_thread`)과 이유 ⑵ 옮긴 범위(한 줄인지 `_parse`
   전체인지) ⑶ 호출부 3곳이 전부 새 경로를 지나는지 ⑷ ★**스레드풀 크기 상한이 무엇인지**
   (기본 anyio 스레드 한도) 와 그것이 동시 파스 요청에 어떤 뜻인지를 적어라.
3. 규약: `apps/api/AGENTS.md`.
4. 사람 개입이 필요하면 `status:"blocked"` + `blocked_reason` 후 즉시 중단.

## 금지사항

- **`src/strategy/pine_v2/` 를 만지지 마라.** 이유: 다른 lane 이 동시에 그 디렉터리를 수정 중이다.
- **rate limit 이나 길이 상한을 새로 넣지 마라.** 이유: 파스 엔드포인트에 그 둘이 없는 것은 사실이고
  별건으로 원장에 오르지만, 이 step 의 범위는 **블로킹 하나**다. 범위를 넓히면 되돌리기가 비싸진다.
- **예외 처리 분기를 「개선」하지 마라.** 이유: `except Exception` 이 넓은 것은 기존 계약이고,
  좁히면 기존 테스트가 무엇 때문에 움직였는지 갈리지 않는다.
- 경과 시간(초)을 단언하지 마라.
- 커밋하지 마라(커밋은 러너 소관).
