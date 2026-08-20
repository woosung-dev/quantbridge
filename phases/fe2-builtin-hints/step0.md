# Step 0: hint-lookup

## 읽어야 할 파일

- `apps/web/src/lib/unsupported-builtin-hints.ts` — **이번 테스트의 대상** (247줄)
- `apps/web/src/components/form-error-inline.tsx` — 유일한 소비자. 어떤 모양으로 쓰이는지 보라
- `apps/web/src/lib/__tests__/geo.test.ts` — 이 디렉터리의 테스트 관용구

## 배경

BE 가 `StrategyNotRunnable.detail.unsupported_builtins` 로 「이 빌트인들 때문에 못 돌린다」를
내면, 이 모듈이 그것을 **사용자가 읽을 수 있는 사유**로 바꾼다. 화면에 그대로 나가는 문장이다.

★**category 가 셋인 이유가 Trust Layer 다** — `corruption`(결과 부정확 risk) ·
`noop`(단순 미구현) · `alternative`(대체 함수 권장). `heikinashi`·`request.security` 같은 것은
**조용한 데이터 오염 위험** 때문에 일부러 unsupported 로 남겼고, 사용자에게 **정확한 사유를 명시**
하는 것이 그 결정의 절반이다(Sprint 21 codex G.0 P1 #2).

**테스트는 0건이다.** 화면에 나가는 문장과 분류를 아무도 재고 있지 않다.

★**BE 가 SSOT 다** — 이 파일 주석이 「backend 의 `coverage._UNSUPPORTED_WORKAROUNDS` SSOT 와
일관 (BE 단독 SSOT — FE 는 추가 정보 제공만)」이라 적었다. 이 lane 은 **FE 의 변환 규칙만** 잰다.
BE 목록과의 대조는 이 lane 의 일이 아니다(그건 별도 축이다).

## 작업

`apps/web/src/lib/__tests__/unsupported-builtin-hints.test.ts` 를 신설한다.
`getUnsupportedBuiltinHint` · `getUnsupportedBuiltinHints` 를 직접 import 해 부른다(mock 없음).

### 최소한 이 일곱을 덮어라 (케이스 ≥7)

1. **적중 — corruption** — `getUnsupportedBuiltinHint("heikinashi")` 가
   `{ name: "heikinashi", hint: <비어있지 않은 문자열>, category: "corruption" }`.
   ★`name` 이 **인자로 준 그 문자열 그대로** 실려 나오는지 단언해라(`{ name, ...meta }` 계약)
2. **적중 — noop** — `"barcolor"` 또는 `"timeframe.period"` 가 `category: "noop"`
3. **적중 — alternative** — `"ta.wma"` 또는 `"ta.obv"` 가 `category: "alternative"`
4. ★**미적중 fallback** — `"currency.USDXYZ123"` 처럼 목록에 없는 이름은
   `category: "noop"` 이고 `hint` 가 **그 이름으로 시작**한다(`` `${name} — 미지원 빌트인 …` ``).
   ★**fallback 이 던지지 않는다**는 것이 계약이다 — BE 가 새 빌트인을 내도 화면이 죽으면 안 된다
5. ★★**프로토타입 오염 방어 — 음성 대조** — `getUnsupportedBuiltinHint("constructor")` ·
   `"toString"` · `"__proto__"` 를 부르면 **fallback 이 나와야 한다**(`category: "noop"` ·
   `hint` 가 이름으로 시작). `_HINTS` 는 객체 리터럴이라 `Object.prototype` 의 키가 **적중처럼
   보일 수 있다.** 지금 무엇이 나오는지 재고, **fallback 이 아니면 고치지 말고 `summary` 에 적어라**
6. **빈 문자열** — `getUnsupportedBuiltinHint("")` 도 던지지 않고 fallback 을 낸다
7. ★**목록 변환** — `getUnsupportedBuiltinHints(["heikinashi", "nope1"])` 가 **길이 2** 이고
   순서가 보존되며 첫째는 적중, 둘째는 fallback.
   ★**`names.map(getUnsupportedBuiltinHint)` 는 map 이 `(value, index, array)` 3개를 넘긴다** —
   두 번째 인자가 무시된다는 것을 재라: `["a","b","c"]` 를 넣어 **셋 다 fallback 이고 name 이
   각각 "a","b","c"** 인지 (index 가 섞여 들어가면 여기서 깨진다)
8. **빈 배열** — `getUnsupportedBuiltinHints([])` 는 `[]`
9. ★**양성 대조 — 실제로 이 모듈을 부르고 있는지 재라.** 두 export 가 함수임을 단언하고,
   케이스 1~3 이 **fallback 이 아닌** 경로를 탔음을(`hint` 가 `"— 미지원 빌트인"` 을 포함하지
   않음) 함께 단언한다. 이것이 없으면 「전부 fallback」인데도 통과할 수 있다

## Acceptance Criteria

```bash
cd apps/web && pnpm test -- --run src/lib/__tests__/unsupported-builtin-hints.test.ts
cd apps/web && test "$(pnpm exec vitest list src/lib/__tests__/unsupported-builtin-hints.test.ts 2>/dev/null | grep -c ' > ')" -ge 7
cd apps/web && pnpm exec eslint src/lib/__tests__/unsupported-builtin-hints.test.ts
cd apps/web && pnpm exec tsc --noEmit
```

★두 번째 AC 는 **양성 대조**다. 착수 시점 이 파일은 없으므로 첫 AC 는 rc=1 (red) 다.

## 자기 점검

1. 위 AC 를 직접 실행해 green 을 확인한다. `status` 를 `completed` 로 바꾸지 마라.
2. `summary` 에 **다음 step 이 쓸 것**을 남겨라 — 케이스 5 에서 실제로 관측한 결과(프로토타입 키가
   fallback 을 냈는가 아닌가)와 케이스 수.
3. 사람 개입이 필요하면 `status:"blocked"` 와 `blocked_reason` 을 쓰고 즉시 중단한다.

## 금지사항

- `apps/web/src/lib/unsupported-builtin-hints.ts` 를 **수정하지 마라.** 결함은 `summary` 한 줄로
- ★**hint 문장을 테스트에 통째로 복사해 오지 마라. 이유:** 소스를 그대로 베낀 단언은 항진명제이고,
  문구가 바뀌면 의미와 무관하게 red 가 난다. **성질**(비어있지 않다 · 이름으로 시작한다 ·
  category 값)을 재라
- ★`apps/web/vitest.config.ts` · `tests/setup.ts` 무변경 (8 lane 동시 실행 중 — 병합 충돌)
- **공용 헬퍼 모듈을 만들지 마라** — 헬퍼는 이 테스트 파일 안에 둬라
- `docs/**` · `phases/**` 무변경. 다른 lane 의 테스트 파일을 만들지 마라
- 커밋하지 마라(커밋은 러너 소관)
