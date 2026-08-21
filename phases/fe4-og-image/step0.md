# Step 0: og-image

## 읽어야 할 파일

- `apps/web/src/app/share/backtests/[token]/opengraph-image.tsx` (162줄) — **이번 테스트의 대상**
- `apps/web/src/lib/brand-palette.ts` — 색 SSOT (하드코딩 hex 금지 근거)
- `apps/web/src/features/backtest/schemas.ts` — `BacktestDetailSchema`
- `apps/web/src/features/backtest/sharpe-convention.ts` — `describeSharpe` (이미 테스트가 있다 — 고치지 마라)
- `apps/web/src/app/share/backtests/[token]/page.tsx` — 같은 토큰을 쓰는 형제 라우트(참고)

## 배경

이 파일은 **공유 링크가 SNS·메신저에 붙을 때 보이는 유일한 그림**이다. 실패해도 사용자에게
아무 신호가 없고(카드가 안 뜰 뿐), 그래서 **조용히 깨진 채로 오래 갈 수 있는 자리**다.

핵심은 **fallback 이다** — `loadDetail()` 이 fetch 실패·비200·스키마 불일치 **셋 다 `null` 로 삼키고**
호출부가 `?? "—"` 로 떨어뜨린다. 이 삼킴이 없으면 공유 카드 생성이 **예외로 죽는다.**

★★**착수 전 CONTROL 프로브 (2026-08-21 실측) — 여기가 이 lane 의 전제다:**

| 잰 것                                                                          | 결과                                                                                                 |
| ------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------- |
| `import("next/og")`                                                            | ✅ 된다 (`ImageResponse` 가 함수다)                                                                  |
| ★**`new ImageResponse(<jsx/>, size)` 를 vitest 에서 실제 실행**                | ★**죽는다** — satori → `sharp` 경로에서 `Error: Unsupported input '...' of type object` (jsdom 환경) |
| ★**`vi.doMock("next/og", ...)` + `vi.resetModules()` 로 생성자 인자 가로채기** | ✅ **된다** — 호출 1회 · **2번째 인자가 `{ width: 1200, height: 630 }`** 였다                        |
| `globalThis.fetch` 를 `{ ok: false }` 로 스텁                                  | ✅ `loadDetail` 이 `null` 로 떨어지고 `ImageResponse` 가 1회 호출됐다                                |

⇒ ★**`ImageResponse` 를 실제로 실행하지 마라. `vi.doMock` 으로 대체해 「무엇을 그리라고 넘겼는가」를 재라.**
`next/og` 는 ESM 이라 mock 이 먹는다(`server-only` 가 CJS 라 mock 이 안 먹던 것과 다르다).

## 작업

`apps/web/src/app/share/backtests/[token]/__tests__/opengraph-image.test.tsx` **하나**를 신설한다.

`next/og` 의 `ImageResponse` 를 **인자를 기록하는 대역**으로 바꾸고, `globalThis.fetch` 를 케이스별로
스텁한다. 넘어온 JSX 트리에서 텍스트를 모으려면 **작은 재귀 수집 헬퍼**를 이 파일 안에 써라
(`children` 을 따라가며 문자열/숫자를 모으는 10줄이면 된다).

### 최소한 이 여덟을 덮어라 (케이스 ≥8)

1. ★**모듈 상수 3종을 고정한다** — `runtime` · `size` · `contentType`.
   ★값은 코드에서 읽어 그대로 박아라. `size` 는 OG 규격이라 바뀌면 카드가 잘린다
2. ★★**`ImageResponse` 의 2번째 인자가 `size` 와 동일 객체값이다** — 상수만 맞고 전달이 어긋나면
   규격이 무의미해진다(CONTROL 프로브에서 `{width:1200, height:630}` 로 확인됨)
3. ★★**fetch 가 던져도 OG 가 던지지 않는다** — `fetch` mock 이 `rejects` 여도 `ImageResponse` 가
   **1회** 호출되고, 수집한 텍스트에 fallback 기호(`"—"`)가 있다
4. ★★**비200 응답도 같은 fallback 이다** — `{ ok: false }` 로 스텁. ⑶과 **같은 마크업**이어야 한다
   (실패 사유를 카드에서 가르면 안 된다)
5. ★★**스키마 불일치도 같은 fallback 이다** — `{ ok: true, json: () => ({엉뚱한: "모양"}) }` 로 스텁해
   `BacktestDetailSchema.parse` 가 던지게 만든다. 셋(⑶⑷⑸)이 **모두 같은 결과**인지 비교해라
6. ★★**정상 응답이면 실제 값이 그려진다** — 스키마를 통과하는 최소 객체를 주고 `symbol` ·
   `timeframe` 이 수집한 텍스트에 있다. ★**이것이 양성 대조다** — ⑶~⑸만 있으면 「항상 `—`」인
   구현도 전건 통과한다
7. ★**토큰이 URL 인코딩된다** — `token` 을 `"a/b?c=1"` 처럼 주고 `fetch` 가 받은 URL 에
   `encodeURIComponent` 결과가 들어 있다(경로 탈출·쿼리 주입 방지). ★`cache: "no-store"` 가
   함께 넘어가는지도 관측해 단언해라(공유 카드가 낡은 값으로 굳는 것을 막는 옵션이다)
8. ★**퍼센트 포맷이 비정상 입력을 `"—"` 로 떨어뜨린다** — `total_return` 이 `null`·`NaN`·
   숫자 아닌 문자열일 때 수집 텍스트에 `NaN` 이나 `Infinity` 가 **없다**.
   ★스키마가 그런 값을 애초에 막으면 그 사실을 `summary` 에 적고 케이스를 조정해라

## Acceptance Criteria

```bash
cd apps/web && pnpm test -- --run 'src/app/share/backtests/[token]/__tests__/opengraph-image.test.tsx'
cd apps/web && test "$(pnpm exec vitest list 'src/app/share/backtests/[token]/__tests__/opengraph-image.test.tsx' 2>/dev/null | grep -c ' > ')" -ge 8
cd apps/web && pnpm exec eslint 'src/app/share/backtests/[token]/__tests__/opengraph-image.test.tsx'
cd apps/web && pnpm exec tsc --noEmit
```

★경로에 `[token]` 대괄호가 있으므로 **작은따옴표**로 감쌌다. `\"` 로 바꾸지 마라(러너의 `bash -c` 에서 죽는다).
★2번째 AC 는 **양성 대조**다. 착수 시점 이 파일은 없으므로 첫 AC 는 rc=1 (CONTROL 실측 2026-08-21).

## 자기 점검

1. 위 AC 를 직접 실행해 green 을 확인한다. ★최종 판정은 러너가 재실행해 내린다 —
   `status` 를 `completed` 로 바꾸지 마라.
2. `summary` 에 케이스 수와 **⑹에서 스키마를 통과시킨 최소 객체의 모양**, **⑻이 실제로 잰 것**을 남겨라.
3. 사람 개입이 필요하면 `status:"blocked"` 와 `blocked_reason` 을 쓰고 즉시 중단한다.

## 금지사항

- ★**`opengraph-image.tsx` 를 수정하지 마라.** 이유: 이 회차의 계약은 「테스트만 추가하고 대상 소스는
  0줄 변경」이다. 결함은 `summary` 또는 `blocked` 로
- ★★**`new ImageResponse(...)` 를 실제로 실행하지 마라. 이유:** 위 표대로 vitest 에서 `sharp` 가
  `Unsupported input` 으로 죽는다(CONTROL 실측). 대역으로 인자만 가로채라
- ★★**색 hex 를 테스트에 리터럴로 적지 마라. 이유:** 항진명제가 되고 팔레트 개정마다 red 가 난다.
  색을 재려면 `BRAND_PALETTE` 를 import 해 비교해라
- ★**`describeSharpe` 의 출력 규칙을 이 테스트에서 다시 재지 마라** — `sharpe-convention` 은 이미
  자기 테스트가 있고 이 lane 소유가 아니다. **넘어간 값이 그려졌는지만** 봐라
- ★**진짜 네트워크를 치지 마라** — `globalThis.fetch` 를 반드시 스텁하고 `afterEach` 에서 복원해라
- ★`apps/web/vitest.config.ts` · `tests/stubs/**` · `tests/setup.ts` **무변경**(8 lane 동시 — 병합 충돌)
- **공용 헬퍼 모듈을 만들지 마라** — 수집 헬퍼는 이 테스트 파일 안에 둬라
- `docs/**` · `phases/**` 무변경. 다른 lane 의 테스트 파일을 만들지 마라
- 커밋하지 마라(커밋은 러너 소관)
