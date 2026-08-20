# Step 0: anchor-contract

## 읽어야 할 파일

- `apps/web/src/lib/route-matcher.ts` — **이번 테스트의 대상** (14줄. 주석이 절반이고 그것이 계약이다)
- `apps/web/src/proxy.ts` — 이 술어를 쓰는 유일한 호출부. **패턴 목록의 모양**을 보라
- `apps/web/src/lib/__tests__/geo.test.ts` — 이 디렉터리의 테스트 관용구

## 배경

이 파일은 **구 Clerk `createRouteMatcher` 의 자리**다([ADR-034]). 헤더가 설계 의도를 못박고 있다:

> 패턴 문자열은 종전 `proxy.ts` 의 것을 **그대로** 옮겨 왔다. 리뷰어가 두 목록을 눈으로 대조할 수
> 있게 형태를 바꾸지 않은 것이 이 파일의 유일한 설계 의도다.
> ★패턴은 **이미 정규식 조각**이다(`/sign-in(.*)`). 이스케이프하지 않는다 — 종전 Clerk 매처와
> 같은 문자열을 같은 뜻으로 읽기 위해서다. 그래서 패턴에 임의의 사용자 입력을 넣지 마라.

**테스트는 0건이고 어떤 테스트도 이 파일을 import 하지 않는다**(2026-08-21 전이 폐포 실측).
14줄이지만 이 술어가 틀리면 **인증 경계가 통째로 틀린다** — `proxy.ts` 의 공개 라우트 판정과
geo 면제 판정이 둘 다 이것을 탄다.

★**이 step 의 목적은 「고치는 것」이 아니라 「지금 의미를 고정하는 것」이다.** 아래 케이스 중
몇 개는 「버그처럼 보이는」 동작을 그대로 박는다. **그것이 의도다** — 나중에 누가 의미를 바꾸면
red 가 나서 사람이 판정하게 된다.

## 작업

`apps/web/src/lib/__tests__/route-matcher.test.ts` 를 신설한다.
`createRouteMatcher` 를 직접 import 해서 부른다(mock 없음 — 순수 함수다).

### 최소한 이 열을 덮어라 (케이스 ≥10)

1. **정확 일치** — `createRouteMatcher(["/pricing"])` 는 `/pricing` 만 true
2. ★**앞 앵커** — `/foo/pricing` 은 **false**. `^` 가 붙는다는 계약이다
3. ★**뒤 앵커** — `/pricing/extra` 는 **false**. `$` 가 붙는다는 계약이다
4. ★★**패턴은 이스케이프되지 않는다 — `(.*)` 는 정규식으로 산다.**
   `["/sign-in(.*)"]` 는 `/sign-in` (빈 문자열 매치) · `/sign-in/foo` · **`/sign-inXYZ`** 셋 다 true.
   ★`/sign-inXYZ` 가 true 인 것은 **의외지만 지금 동작이고 Clerk 시절과 같다.**
   이 케이스에 「의도된 as-is 이식 — 바꾸려면 [ADR-034] 를 다시 열어라」 주석을 달아라
5. ★**`.` 도 정규식으로 산다** — `["/a.c"]` 는 `/abc` **true**, `/a.c` 도 true.
   리터럴 점이 아니라는 것이 「임의의 사용자 입력을 넣지 마라」 경고의 근거다
6. **다중 패턴 = OR** — `["/a", "/b"]` 는 `/a`·`/b` true, `/c` false
7. **빈 목록** — `createRouteMatcher([])` 는 무엇을 줘도 **항상 false** (`some` 의 빈 배열)
8. **빈 pathname** — `[""]` 는 `""` 에만 true, `/` 는 false
9. ★**컴파일은 1회다** — 같은 매처를 두 번 불러도 결과가 같고, **서로 다른 매처가 서로를
   오염시키지 않는다**(`lastIndex` 오염 회귀 방지 — `g` 플래그가 없다는 계약).
   `["/x(.*)"]` 매처로 `/xa` 를 **연속 3회** 검사해 3번 다 true 인지 재라
10. ★**양성 대조 — 실제로 이 모듈을 부르고 있는지 재라.** `createRouteMatcher` 가 함수이고
    반환값도 함수임을 한 케이스에서 단언한다. import 오타로 아무것도 안 불린 채 통과할 수 없게 한다

★**`proxy.ts` 의 패턴 목록을 이 파일에 복사해 오지 마라. 이유:** 낡은 사본이 된다.
목록 자체의 검증은 `fe2-proxy-gate` lane 이 `proxy()` 를 직접 불러서 한다. 이 lane 은 **컴파일러**만 잰다.

## Acceptance Criteria

```bash
cd apps/web && pnpm test -- --run src/lib/__tests__/route-matcher.test.ts
cd apps/web && test "$(pnpm exec vitest list src/lib/__tests__/route-matcher.test.ts 2>/dev/null | grep -c ' > ')" -ge 10
cd apps/web && pnpm exec eslint src/lib/__tests__/route-matcher.test.ts
cd apps/web && pnpm exec tsc --noEmit
```

★두 번째 AC 는 **양성 대조**다. 착수 시점 이 파일은 없으므로 첫 AC 는 rc=1 (red) 다.

## 자기 점검

1. 위 AC 를 직접 실행해 green 을 확인한다. `status` 를 `completed` 로 바꾸지 마라.
2. `summary` 에 케이스 수와 **「의외지만 고정한」 동작 목록**을 남겨라.
3. 사람 개입이 필요하면 `status:"blocked"` 와 `blocked_reason` 을 쓰고 즉시 중단한다.

## 금지사항

- `apps/web/src/lib/route-matcher.ts` 를 **수정하지 마라.** 특히 `/sign-inXYZ` 가 매치되는 것을
  「고치지」 마라 — 그것은 [ADR-034] 가 의도한 as-is 이식이고, 바꾸면 인증 경계가 조용히 이동한다
- ★`apps/web/vitest.config.ts` · `tests/setup.ts` 무변경 (8 lane 동시 실행 중 — 병합 충돌)
- **공용 헬퍼 모듈을 만들지 마라** — 같은 이유다
- `docs/**` · `phases/**` 무변경. 다른 lane 의 테스트 파일을 만들지 마라
- 커밋하지 마라(커밋은 러너 소관)
