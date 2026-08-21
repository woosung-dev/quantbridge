# Step 0: query-client-policy

## 읽어야 할 파일

- `apps/web/src/components/providers/query-provider.tsx` — **대상** (56줄)
- `apps/web/src/components/providers/app-providers.tsx` — 함께 재는 대상 (28줄)
- `apps/web/src/hooks/__tests__/use-invalidating-mutation.test.tsx` — ★**이 레포에서
  QueryClient 를 다루는 테스트 관용구다. 먼저 읽어라**

## 배경

`QueryProvider` 는 **이 앱의 데이터 페칭 정책 SSOT** 다 — `staleTime` 60초 · `gcTime` 5분 ·
`retry` 1 · `refetchOnWindowFocus: false` · mutation `retry: 0`. **테스트 0건이다.**

★**정책이 조용히 바뀌면 증상이 화면이 아니라 요금과 부하로 나온다** — `refetchOnWindowFocus` 가
켜지면 탭을 돌아올 때마다 전량 재조회하고, mutation `retry` 가 켜지면 **주문이 두 번 나갈 수 있다.**

★**싱글톤 분기가 진짜 로직이다** — 주석이 근거를 적고 있다: 서버는 매 요청 새 client(요청 간 격리) ·
브라우저는 싱글톤(React Suspend 시 재생성 방지). 이 분기가 뒤집히면 **요청끼리 캐시를 공유**한다.

## 작업

`apps/web/src/components/providers/__tests__/query-provider.test.tsx` 를 신설한다.

★**정책 값은 `QueryClient` 인스턴스에서 읽어라** — `client.getDefaultOptions()` 가 설정을 그대로 준다.
컴포넌트를 렌더한 뒤 `QueryClientProvider` 가 받은 client 를 잡는 방법:
`useQueryClient()` 를 부르는 **작은 프로브 컴포넌트**를 `QueryProvider` 의 children 으로 넣어라.

```tsx
function Probe({ onClient }: { onClient: (c: QueryClient) => void }) {
  onClient(useQueryClient());
  return <div data-testid="probe" />;
}
```

★**`jsdom` 에서는 `typeof window !== "undefined"` 다** — 즉 **브라우저 갈래만 직접 잴 수 있다.**
서버 갈래(`isServerEnv`)는 모듈 로드 시점에 굳으므로 **재려 하지 마라**(억지로 재려면 전역을
지워야 하고 그 자체가 다른 것을 깬다). 대신 **「브라우저에서 싱글톤이다」를 확실히 재고**,
서버 갈래는 `summary` 에 「미검증 — jsdom 에서 도달 불가」라고 적어라.
★**이것이 이 lane 의 정직성 축이다 — 못 잰 것을 잰 것처럼 적지 마라.**

### 최소한 이 일곱을 덮어라 (케이스 ≥7)

1. ★**query 기본값 4종** — `staleTime === 60_000` · `gcTime === 300_000` · `retry === 1` ·
   `refetchOnWindowFocus === false`. ★**숫자를 리터럴로 단언해라** — 이 값들은 정책이고
   바뀌면 사람이 판정해야 한다
2. ★★**mutation `retry === 0`** — 별도 케이스로 떼라. **주문 재시도가 켜지는 것이 이 파일에서
   가장 비싼 회귀**다(중복 발주)
3. ★★**브라우저 싱글톤** — `QueryProvider` 를 **두 번 렌더**(unmount 후 재렌더)해도 프로브가 받는
   client 가 **같은 인스턴스**다(`toBe`). ★참조 동일성으로 재라 — 값 비교는 이것을 못 잡는다
4. ★**children 이 실제로 렌더된다** — 프로브 `data-testid` 가 문서에 있다.
   Provider 가 children 을 삼키면 앱이 통째로 빈다
5. ★**Devtools 는 development 에서만 붙는다** — `vi.stubEnv("NODE_ENV", "production")` +
   `vi.resetModules()` 후 렌더하면 devtools 가 **없고**, `"development"` 면 **있다**.
   ★두 방향을 다 재라 — 한 방향만 재면 「항상 없다」 구현도 통과한다.
   ★devtools 를 못 찾겠으면 `vi.mock("@tanstack/react-query-devtools", …)` 로 감시 가능한
   더미를 넣어 **호출 여부**로 재라(그쪽이 DOM 탐색보다 튼튼하다)
6. ★**`AppProviders` 가 QueryProvider 를 감싼다** — `app-providers.tsx` 를 렌더해도
   프로브가 QueryClient 를 받는다(배선 확인). ★이것이 없으면 QueryProvider 는 옳은데
   **아무도 안 쓰는** 상태를 못 잡는다
7. ★**양성 대조** — 프로브가 받은 것이 실제 `QueryClient` 인스턴스다(`getDefaultOptions` 가 함수).
   mock 이 잘못 걸려 빈 객체를 받는 상태를 배제한다

★`afterEach` 에서 `cleanup()` · `vi.unstubAllEnvs()` · `vi.resetModules()` 를 걸어라.

## Acceptance Criteria

```bash
cd apps/web && pnpm test -- --run 'src/components/providers/__tests__/query-provider.test.tsx'
cd apps/web && test "$(pnpm exec vitest list 'src/components/providers/__tests__/query-provider.test.tsx' 2>/dev/null | grep -c ' > ')" -ge 7
cd apps/web && pnpm exec eslint 'src/components/providers/__tests__/query-provider.test.tsx'
cd apps/web && pnpm exec tsc --noEmit
```

★두 번째 AC 는 **양성 대조**다. 착수 시점 이 파일은 없으므로 첫 AC 는 rc=1 (red) 다.

## 자기 점검

1. 위 AC 를 직접 실행해 green 을 확인한다. `status` 를 `completed` 로 바꾸지 마라.
2. `summary` 에 케이스 수와 **서버 갈래를 못 잰 사실**을 명시해라.
3. 사람 개입이 필요하면 `status:"blocked"` 와 `blocked_reason` 을 쓰고 즉시 중단한다.

## 금지사항

- `query-provider.tsx` · `app-providers.tsx` 를 **수정하지 마라.** 결함은 `summary` 한 줄로
- ★**서버 갈래를 재려고 `globalThis.window` 를 지우지 마라** — jsdom 전역을 망가뜨려
  같은 파일의 다른 케이스가 비결정적으로 깨진다. 못 잰 것은 못 쟀다고 적어라
- ★**진짜 네트워크 요청을 내지 마라** — 이 lane 은 client 설정만 잰다. `useQuery` 를 부르지 마라
- ★`apps/web/vitest.config.ts` · `tests/setup.ts` 무변경 (8 lane 동시 실행 중 — 병합 충돌)
- **공용 헬퍼 모듈을 만들지 마라** — 프로브 컴포넌트는 이 테스트 파일 안에 둬라
- `docs/**` · `phases/**` 무변경. 다른 lane 의 테스트 파일을 만들지 마라
- 커밋하지 마라(커밋은 러너 소관)
