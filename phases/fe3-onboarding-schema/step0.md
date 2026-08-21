# Step 0: persist-schema

## 읽어야 할 파일

- `apps/web/src/features/onboarding/schemas.ts` — **대상** (23줄)
- `apps/web/src/features/onboarding/types.ts` — `ONBOARDING_VERSION` 상수의 자리
- `apps/web/src/features/onboarding/__tests__/` — 이 디렉터리의 기존 테스트 관용구
- `apps/web/src/lib/zod-v4-resolver.ts` — 이 레포의 Zod v4 사용 관례(2026-08-21 테스트 신설됨)

## 배경

이 스키마는 **zustand `persist` 미들웨어의 rehydrate 단계에서 runtime 검증**을 한다 —
`localStorage` 에서 읽은 값이 이 스키마를 통과하지 못하면 온보딩 진행도를 **reset** 한다.

★**검증이 느슨하면 낡은 payload 가 그대로 살아난다** — 사용자는 존재하지 않는 전략 id 를 든
채로 온보딩 3단계에 떨어지고, 화면은 404 를 낸다. **검증이 과하면 반대로 매번 처음부터** 시작한다.
**테스트는 0건이다** — 어느 쪽인지 아무도 재고 있지 않다.

★**버전 필드가 `z.literal(ONBOARDING_VERSION)` 인 것이 이 스키마의 핵심**이다. 버전을 올리면
옛 payload 가 **자동으로 거부**된다 — 그 계약이 지금 작동하는지 재라.

## 작업

`apps/web/src/features/onboarding/__tests__/schemas.test.ts` 를 신설한다.
`OnboardingStepSchema` · `OnboardingPersistSchema` 를 직접 import 해 `safeParse` 로 잰다(mock 없음).

### 최소한 이 여덟을 덮어라 (케이스 ≥8)

1. ★**유효한 payload 가 통과한다** — `ONBOARDING_VERSION` 을 **import 해서** 쓰고
   `step: "welcome"` · `strategyId`/`backtestId` 는 uuid 문자열 · `startedAt` 은 정수 ⇒ `success`.
   ★**버전 숫자를 리터럴로 적지 마라** — 상수를 import 해야 버전을 올려도 이 테스트가 따라온다
2. ★★**버전 mismatch 는 거부된다** — `version: ONBOARDING_VERSION + 1` 과 `- 1` **둘 다** `success: false`.
   ★**이것이 「버전 올리면 옛 payload 가 죽는다」의 유일한 증거다**
3. ★**`step` 4종이 전부 유효하다** — `welcome`·`strategy`·`backtest`·`result` 를 parametrize 로
   각각 통과시켜라. ★**하나라도 빠뜨리지 마라** — 빠진 값은 사용자를 그 단계에서 reset 시킨다
4. ★**음성 대조 — 목록 밖 `step` 은 거부** — `"done"`·`"WELCOME"`(대문자)·`""` 는 `success: false`
5. ★★**`strategyId`/`backtestId` 는 `null` 이 허용되고 비-uuid 는 거부된다** — `null` ⇒ 통과 ·
   `"not-a-uuid"` ⇒ 거부 · `undefined`(키 자체 없음) ⇒ **거부**(nullable 은 optional 이 아니다).
   ★세 방향을 다 재라 — `.nullable()` 과 `.optional()` 을 헷갈리면 rehydrate 가 조용히 통과한다
6. ★**`startedAt` 경계** — `0` ⇒ 통과(`nonnegative`) · `-1` ⇒ 거부 · `1.5` ⇒ 거부(`int`) ·
   문자열 `"123"` ⇒ 거부. ★**`0` 이 통과해야 한다** — `positive` 로 잘못 쓰면 첫 tick 이 죽는다
7. ★**여분 키는 어떻게 되는가** — `{...valid, extra: 1}` 을 넣고 **지금 동작을 관측해 고정해라**
   (Zod object 는 기본이 strip 이라 통과하고 `data` 에서 `extra` 가 사라질 것이다).
   ★**예상과 다르면 고치지 말고 `summary` 에 적어라** — 재지 않은 기대를 단언으로 쓰지 마라
8. ★**양성 대조** — 두 스키마가 실제 Zod 스키마다(`safeParse` 가 함수) · 유효 케이스의
   `parsed.data` 가 **다섯 키를 그대로** 갖는다(`version`·`step`·`strategyId`·`backtestId`·`startedAt`).
   빈 객체를 통과시키는 상태를 배제한다

## Acceptance Criteria

```bash
cd apps/web && pnpm test -- --run 'src/features/onboarding/__tests__/schemas.test.ts'
cd apps/web && test "$(pnpm exec vitest list 'src/features/onboarding/__tests__/schemas.test.ts' 2>/dev/null | grep -c ' > ')" -ge 8
cd apps/web && pnpm exec eslint 'src/features/onboarding/__tests__/schemas.test.ts'
cd apps/web && pnpm exec tsc --noEmit
```

★두 번째 AC 는 **양성 대조**다. 착수 시점 이 파일은 없으므로 첫 AC 는 rc=1 (red) 다.

## 자기 점검

1. 위 AC 를 직접 실행해 green 을 확인한다. `status` 를 `completed` 로 바꾸지 마라.
2. `summary` 에 케이스 수와 **7번에서 관측한 여분 키 동작**(strip 인지 error 인지)을 남겨라.
3. 사람 개입이 필요하면 `status:"blocked"` 와 `blocked_reason` 을 쓰고 즉시 중단한다.

## 금지사항

- `apps/web/src/features/onboarding/schemas.ts` · `types.ts` 를 **수정하지 마라.**
  결함은 `summary` 한 줄로
- ★**`ONBOARDING_VERSION` 값을 테스트에 리터럴로 복사하지 마라. 이유:** 버전을 올리는 순간
  이 테스트가 **의미 없이** red 가 되거나, 더 나쁘게는 **낡은 버전을 계속 통과**시킨다
- ★**zustand store 를 렌더하지 마라** — 이 lane 은 스키마만 잰다
- ★`apps/web/vitest.config.ts` · `tests/setup.ts` 무변경 (8 lane 동시 실행 중 — 병합 충돌)
- **공용 헬퍼 모듈을 만들지 마라** — 헬퍼는 이 테스트 파일 안에 둬라
- `docs/**` · `phases/**` 무변경. 다른 lane 의 테스트 파일을 만들지 마라
- 커밋하지 마라(커밋은 러너 소관)
