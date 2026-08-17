# 레인 γ — [BL-786] 목록·배지 API 요청이 전부 쌍으로 나간다

브랜치 `stage/bl786-dupreq` · 워크트리 슬롯 5 (FE `:3105` / BE `:8105`)

## 결론

중복은 **실재하고 프로덕션에도 그대로 나간다.** StrictMode 가 아니다.

원인은 **React Query 키의 첫 인자인 `uid` 가 한 화면 로드 안에서 `"anon"` → 진짜 사용자 id 로
한 번 바뀌는 것**이다. `useAuthCtx()` 는 `useSession()` 이 `/api/auth/get-session` 을 왕복하기
전까지 `uid = "anon"` 을 내고, 키가 `uid` 로 시작하므로(LESSON-005) 모든 목록·배지 쿼리가
**anon 키로 한 번 · 진짜 키로 또 한 번** 나간다. 두 요청은 URL 도 Bearer 토큰도 같아서 서버는
구분할 수 없고 화면도 안 깨진다 — 값만 두 배로 나갔다.

수리 후 브라우저 API 요청은 `/backtests` 10→4, `/dashboard` 15→8, `/strategies` 6~7→3 이다.

## AC 판정

| AC                                            | 판정 | 근거                                                                                     |
| --------------------------------------------- | ---- | ---------------------------------------------------------------------------------------- |
| AC-1 원인 하나로 확정                         | ✅   | 아래 「원인 확정의 근거」 4건 (계측 + 코드 대조)                                         |
| AC-2 개발/프로덕션 양쪽 측정                  | ✅   | 아래 측정표 (dev = `next dev`, prod = `output: standalone` 의 `node server.js`)          |
| AC-3 같은 요청 1회를 재는 테스트              | ✅   | `apps/web/e2e/api-request-dedup.spec.ts` — 단언은 `toBe(1)` / `toEqual([])`, `>= 1` 없음 |
| AC-4 수리 전 red                              | ✅   | 수리 전 코드에서 rc=1 (`/backtests`·`/dashboard` 둘 다 「앵커 요청이 2회 나갔다」)       |
| AC-5 vitest · e2e chromium · e2e design-canon | ✅   | 각각 rc=0 (1420 tests / 4 / 44). `e2e:authed` 는 지시대로 안 돌렸다                      |
| AC-6 화면 안 깨짐                             | ✅   | AC-5 의 두 e2e 레그 + 수리 후 측정에서 목록·배지 요청이 여전히 나가고 렌더된다           |

## 원인 확정의 근거

**⑴ 프로덕션 빌드에서 동일하게 재현된다 → StrictMode 가 아니다.**
`pnpm build` 후 `output: standalone` 산출물(`node .next/standalone/server.js`)로 같은 화면을
열었을 때 요청 수가 개발 서버와 **완전히 같았다**(아래 표). StrictMode 이중 실행은 개발 전용이므로
이 가설은 여기서 죽는다.

**⑵ 컴포넌트 이중 마운트가 아니다.** 로드 후 DOM 실측: `aside.sidebar` 1 · `nav[aria-label="주요 메뉴"]` 1 ·
`#main-content` 1 · `table` 1. 셸도 목록도 한 벌뿐이다.

**⑶ 두 요청은 구분 불가능하게 같다.** `/api/v1/backtests?limit=20&…` 두 건의 전체 헤더를 떠서
비교했을 때 `authorization` Bearer 토큰까지 **완전히 동일**했다. 즉 「서로 다른 신원이 각자 친
것」이 아니다.

**⑷ `uid` 가 실제로 두 값을 지나간다 — 이것이 결정적 관측이다.** `useAuthCtx` 에 일회용 계측을
심어 uid 전이를 타임라인으로 찍었다(계측은 문자열 치환으로 심고 되돌린 뒤 sha256 대조로 복원 확인).

```
+  390ms  [BL786-uid] anon|pending=true
+  392ms  REQ FE/api/auth/get-session
+  432ms  REQ FE/api/auth/token
+  451ms  [BL786-uid] A0mR4N1BkkIpoerowrBwRf0QArwlVSQW|pending=false
+  523ms  REQ BE/api/v1/backtests?limit=20&offset=0&order_by=created_at&order=desc
+  523ms  REQ BE/api/v1/backtests?limit=20&offset=0&order_by=created_at&order=desc
```

두 BE 요청이 같은 ms 에 나가는 이유는 둘 다 `getAuthToken()` 이 해소되기를 기다렸다가 함께
풀리기 때문이다. 「동시에 두 번」이라는 증상이 「두 파동」이라는 원인을 가리고 있었다.

**⑸ 코드 대조가 같은 결론을 낸다 — 그리고 왜 화면마다 배수가 달랐는지도 설명한다.**
`/strategies` 는 pre-fix 에 목록 요청이 **1회**였는데 `/backtests` 는 **2회**였다. 두 페이지의
SSR prefetch 키를 비교하면 갈린 이유가 나온다.

- `strategies/page.tsx` 의 prefetch 키 = `{limit, offset, is_archived, order_by, order}` — 클라이언트 키와 **일치**.
  → anon 키만 빗나가 1회.
- `backtests/page.tsx` 의 prefetch 키 = `{limit, offset}` — 클라이언트는 `order_by`·`order` 까지 넣어 **불일치**.
  → anon 키도 진짜 키도 빗나가 2회. 게다가 **SSR 이 친 요청 자체가 통째로 버려지고 있었다.**

## AC-2 — 개발/프로덕션 측정표

한 화면 로드에서 **브라우저가 낸** `/api/v1/*` 요청 수. `page.on("request")` 로 세고
`networkidle` + 여유까지 관측. 같은 로그인 신원·같은 BE(`:8105`).

| 화면          | dev 수리 전 | prod 수리 전 | dev 수리 후 | prod 수리 후 |
| ------------- | ----------- | ------------ | ----------- | ------------ |
| `/backtests`  | 10          | 10           | **4**       | **4**        |
| `/dashboard`  | 15          | 15           | **8**       | **8**        |
| `/strategies` | 6           | 7            | **3**       | **3**        |

수리 전 개별 URL 은 **전부 정확히 2회**였다(예외 2건: `/dashboard` 의 `optimizer/runs` 와
`/strategies` 의 목록 — 둘 다 1회). 수리 후에는 **전부 1회**다.

★**dev 와 prod 가 같다는 것이 이 표의 요점이다.** [BL-784] 의 산술은 「개발/e2e 에서만 두 배」로
바뀌지 않는다 — 실사용자도 대시보드를 열 때마다 같은 쿼리를 두 번 보내고 있었고, 수리는 e2e 와
실사용자에게 **똑같이** 효과가 있다.

`/backtests` 는 SSR 이 낸 요청까지 세면 BE 히트가 **11 → 5** 다(수리 전 = 버려진 SSR 1 + 브라우저 10,
수리 후 = 소비되는 SSR 1 + 브라우저 4).

## 수리

**⑴ SSR 이 아는 신원을 첫 렌더에 넘긴다** — 이것이 중복의 본체를 없앤다.

- `apps/web/src/components/providers/server-identity-provider.tsx` (신규) — SSR 의 `userId` 를
  클라이언트 트리로 넘기는 context.
- `apps/web/src/app/(dashboard)/layout.tsx` — `getServerAuth()` 로 값을 받아 셸을 감싼다.
  `getServerAuth` 는 `React.cache` 라 같은 요청의 페이지 호출과 왕복을 공유한다(추가 비용 없음).
- `apps/web/src/hooks/use-auth-ctx.ts` — 세션이 `isPending` 인 동안만 그 값을 쓴다.
  **세션이 도착한 뒤에는 항상 세션이 정본**이다(로그아웃이 낡은 SSR 값에 가려지면 안 된다).
  `apps/web/AGENTS.md` 의 「클라이언트는 `useAuthCtx()` 하나만 쓴다」 seam 은 그대로다 — 변경은 이 한 파일 안이다.

**⑵ `/backtests` 의 prefetch 키를 클라이언트 키와 같은 생성자에서 만든다** — SSR 요청이 버려지던 축.

- `apps/web/src/features/backtest/list-query.ts` (신규) — `buildBacktestListQuery()` 가
  목록 queryKey/파라미터의 **유일한** 생성자. `features/strategy/sort.ts` 가 이미 쓰던 관례를 그대로 따랐다.
- `backtests/page.tsx` 와 `backtest-list.tsx` 가 **둘 다 그 함수를 부른다.** 페이지는 이제
  `searchParams` 를 읽는다(정렬이 URL 에 있을 때도 키가 맞아야 하므로).

동작 변경은 없다 — 정렬 기본값·URL 해석·목록 표시는 그대로고, 바뀐 것은 **어느 캐시 항목에
들어가는가**뿐이다.

## AC-3 검사면

`apps/web/e2e/api-request-dedup.spec.ts` — `/backtests`·`/dashboard` 각각에 대해 세 가지를 단언한다.

1. **앵커 요청이 정확히 1회.** 앵커는 [BL-786] 이 지목한 내비 배지 프로브들이다.
   앵커가 하나도 안 보이면 「중복 없음」이 아니라 **측정 실패**로 red — 빈 입력이 초록으로 새는 길을 막았다.
2. **SSR 이 hydrate 로 넘긴 요청은 브라우저에서 0회.** 이것이 ⑵ 축(prefetch 키 정렬)을 지키는 면이다.
3. **어떤 URL 도 2회 이상 나가지 않았다.**

측정 창은 `networkidle` + 1초다. 이 화면들의 가장 빠른 폴링이 5초(`ORDERS_REFETCH_INTERVAL_ACTIVE_MS`)라
정상 폴링이 창에 들어와 중복으로 오판되지 않는다.

★레인 파일이 경고한 「`>= 1` 로 느슨하게 쓰면 판별력을 잃는다」는 **심지 않았다** — 단언은 전부
`toBe(1)` / `toEqual([])` 이고, 그 성질을 M1·M2 두 변이가 실증한다.

## 표적 변이

| 변이                                                                     | 기대     | 실측                                                                                            |
| ------------------------------------------------------------------------ | -------- | ----------------------------------------------------------------------------------------------- |
| M1 — `use-auth-ctx.ts` 의 신원 시드를 되돌린다(중복 부활)                | AC-3 red | **red** (rc=1) — `/backtests` 앵커 2회 · `/dashboard` 앵커 2회                                  |
| M2 — `backtests/page.tsx` 의 prefetch 키를 `{limit, offset}` 로 되돌린다 | AC-3 red | **red** (rc=1) — `/backtests` hydration 축 위반. `/dashboard` 는 green(그 축이 없다 — 기대대로) |

두 변이 모두 문자열 치환으로 심고 문자열 치환으로 되돌린 뒤, **심을 때 쓰지 않은 방법(sha256 대조)**
으로 복원을 확인했다. 두 파일 다 변이 전 해시로 정확히 복귀했다.

## 게이트

| 게이트                                    | rc                         |
| ----------------------------------------- | -------------------------- |
| `pnpm exec vitest run`                    | 0 (220 files / 1420 tests) |
| `pnpm e2e` (chromium)                     | 0 (4 passed)               |
| `pnpm e2e:design-canon`                   | 0 (44 passed)              |
| `final-gates.sh --run bl786-dup --pre-pr` | 아래 「마감」 참조         |

## 확인하지 못한 것

- **`e2e:authed` 전량은 안 돌렸다.** 레인 지시(AC-5)다. 새 spec 은 `chromium-authed` project 소속이라
  파일 지정으로만 돌렸고, 통합 후 전량 실행은 아침 오케스트레이터 몫이다.
- **프로덕션 측정 하네스의 `setup-authed-reachability` 가 내 임시 standalone 서버에서 실패한다.**
  `/trading` 에서 `subresourceFail` 이 호스트 `localhost:3105` 로 잡힌다. 다만 ⒜ **수리 전에도
  똑같이 실패했고** ⒝ 같은 실행의 캐논 감사 자체는 `PASS`(examined=703, console=0) 이며
  ⒞ HTML 이 참조하는 정적 자산 30건을 직접 쳐 보면 **전부 200** 이다. 원인은 규명하지 못했다.
  프로덕션 측정은 수리 전·후 **양쪽 다** `--no-deps` 로 같은 조건에서 냈으므로 비교는 성립한다.
  개발 서버에서는 이 setup 이 정상 통과한다.
- **`/strategies` 수리 전 요청 수가 dev 6 · prod 7 로 갈린 이유.** 목록 요청(`limit=20`)이 prod 에서는
  1회 관측됐고 dev 에서는 0회였다. 다른 두 화면은 dev/prod 가 완전히 일치했다. 이 1건의 차이는
  설명하지 못했다 — 수리 후에는 양쪽 다 3 이다.
- **다른 화면(`/trading`·`/orders`·`/optimizer`)은 재지 않았다.** 원인이 `useAuthCtx` 한 곳이라
  전 화면에 같은 방식으로 걸리지만, 측정한 것은 위 세 화면뿐이다.

## 범위 밖 (건드리지 않음)

레이트리밋 본체 · `playwright.config.ts` · FE 의 `Retry-After` 존중 · `docs/backlog.md`·`status.md`·`lessons.md`.

## 마감

커밋 3건, push 하지 않았다.

```
a59c2ac6 test(e2e): assert SSR-prefetched list is not re-fetched by the browser (BL-786)
66b684bc fix(web): seed React Query identity from SSR so list/badge requests stop firing twice (BL-786)
b3de1c3c wip(e2e): add per-screen API request dedup gate (BL-786) — red before fix
```
