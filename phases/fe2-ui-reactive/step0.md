# Step 0: store-and-media-query

## 읽어야 할 파일

- `apps/web/src/store/ui-store.ts` — **대상 ⑴** (16줄, zustand)
- `apps/web/src/hooks/use-media-query.ts` — **대상 ⑵** (32줄, `useSyncExternalStore`)
- `apps/web/src/hooks/__tests__/use-invalidating-mutation.test.tsx` — ★**이 디렉터리의 훅 테스트
  관용구다. `renderHook` 사용법을 여기서 보고 같은 모양으로 써라**

## 배경

둘 다 **전역 반응 상태**이고 **테스트 0건**이다(직접 단언 0 — 컴포넌트를 통해 전이적으로만 실행된다).

**⑴ `ui-store.ts`** — 모바일 nav drawer 열림 상태([BL-300]). 데스크톱 sidebar 는 순수 CSS 레일로
대체돼 **런타임 상수 true 였고 호출자가 0이라 삭제**됐다. 남은 것은 `mobileNavOpen` 하나다.

**⑵ `use-media-query.ts`** — SSR-safe 반응형 훅. 헤더가 설계 이유를 적고 있다:

> 서버에서는 false (desktop 기본) 를 반환하여 **hydration mismatch 를 피하고**, 클라이언트 mount 시
> 실제 matchMedia 결과로 동기화된다. `useSyncExternalStore` 를 사용해
> **LESSON-004 (useEffect + setState 케스케이드) 를 원천 차단.**

★**이 레포는 반응형 실측에서 이미 데였다** — 「정확히 768px 에서 min/max 둘 다 참(데드심)」 ·
「Tailwind v4 `max-[N]:` 경계 미포함」. 그 판정이 이 훅을 탄다.
★그리고 [BL-775] 의 원인은 **하이드레이션 경쟁**이었다(리스너가 레이아웃 서브트리에서 늦게 붙는다).
**구독/해제가 짝이 맞는지**를 재는 것이 그 계열의 방어다.

## 작업

**테스트 파일 두 개**를 신설한다. 이 lane 이 소유한 파일은 그 둘뿐이다.
★`src/store/__tests__/` 디렉터리는 **아직 없다.** 만들어라.

### ⑴ `apps/web/src/store/__tests__/ui-store.test.ts` (케이스 ≥4)

★**스토어는 모듈 싱글톤이다** — 케이스 사이에 상태가 샌다.
`beforeEach` 에서 `useUiStore.setState({ mobileNavOpen: false })` 로 되돌려라.
zustand 스토어는 훅이자 객체다 — `useUiStore.getState()` / `.setState()` / `.subscribe()` 를
직접 쓰면 렌더 없이 잴 수 있다.

1. **초기값** — `useUiStore.getState().mobileNavOpen === false`
   (drawer 는 **닫힌 채로 시작**해야 한다. 열린 채 시작하면 첫 페인트에 오버레이가 깔린다)
2. **setter 왕복** — `setMobileNavOpen(true)` → `true`, `setMobileNavOpen(false)` → `false`
3. ★**구독자에게 통지된다** — `subscribe` 로 콜백을 걸고 `setMobileNavOpen(true)` 후
   콜백이 **불렸고** 새 상태가 `true` 인지. ★unsubscribe 뒤에는 **더 이상 안 불린다**(음성 대조)
4. ★**`set({ mobileNavOpen })` 은 다른 키를 지우지 않는다** — setter 호출 뒤에도
   `setMobileNavOpen` 이 **여전히 함수**다(zustand 의 부분 병합 계약).
   전체 치환으로 바뀌면 두 번째 호출부터 런타임 오류가 난다
5. ★**양성 대조** — `useUiStore` 가 함수이고 `getState()` 가 `mobileNavOpen`·`setMobileNavOpen`
   **두 키를 갖는다**(모듈이 실제로 로드됐는지)

### ⑵ `apps/web/src/hooks/__tests__/use-media-query.test.ts` (케이스 ≥6)

`renderHook` 은 `@testing-library/react` 에서 온다.
★**jsdom 에는 `window.matchMedia` 가 없다** — 케이스마다 직접 세워라. 가짜 MediaQueryList 는
`{ matches, media, addEventListener, removeEventListener }` 를 갖춰야 한다.
`vi.stubGlobal("matchMedia", fn)` 을 쓰고 `afterEach` 에서 `vi.unstubAllGlobals()`.

1. ★**`matchMedia` 가 없으면 false 를 낸다** — `window.matchMedia` 를 지운 상태에서
   `renderHook(() => useMediaQuery("(min-width: 768px)"))` 가 **던지지 않고** `false`.
   ★**서버·구형 환경 방어이고, 던지면 페이지가 죽는다**
2. **`matches: true` 면 true** — 가짜가 true 를 내면 훅도 true
3. **`matches: false` 면 false**
4. ★★**`change` 이벤트로 값이 바뀐다** — 등록된 리스너를 붙잡아 두고,
   `matches` 를 뒤집은 뒤 리스너를 호출하면(`act(() => listener())`) 훅 값이 **바뀐다**.
   ★이것이 `useSyncExternalStore` 배선을 재는 유일한 케이스다 — 나머지는 초기 스냅샷만 잰다
5. ★★**구독/해제가 짝이 맞는다** — `addEventListener` 가 `"change"` 로 **1회** 불리고,
   `unmount()` 후 `removeEventListener` 가 **같은 함수 참조로** 1회 불린다.
   ★참조가 다르면 리스너가 영영 남아 누수가 된다([BL-775] 계열)
6. ★**query 가 바뀌면 재구독한다** — `rerender` 로 query 문자열을 바꾸면
   옛 구독이 해제되고 새 query 로 `matchMedia` 가 다시 불린다(`useCallback` 의존성 계약).
   ★**같은 query 로 rerender 하면 재구독이 일어나지 않는다**(음성 대조) — 매 렌더 재구독은
   무한 루프의 입구다
7. ★**양성 대조 — `matchMedia` 가 실제로 그 query 문자열을 받았다** —
   `expect(matchMediaMock).toHaveBeenCalledWith("(min-width: 768px)")`.
   이것이 없으면 훅이 인자를 무시해도 통과한다

## Acceptance Criteria

```bash
cd apps/web && pnpm test -- --run src/store/__tests__/ui-store.test.ts src/hooks/__tests__/use-media-query.test.ts
cd apps/web && test "$(pnpm exec vitest list src/store/__tests__/ui-store.test.ts 2>/dev/null | grep -c ' > ')" -ge 4
cd apps/web && test "$(pnpm exec vitest list src/hooks/__tests__/use-media-query.test.ts 2>/dev/null | grep -c ' > ')" -ge 6
cd apps/web && pnpm exec eslint src/store/__tests__/ui-store.test.ts src/hooks/__tests__/use-media-query.test.ts
cd apps/web && pnpm exec tsc --noEmit
```

★2·3번 AC 는 **파일별 양성 대조**다. 한 파일에 몰아 쓰면 다른 파일이 비어도 통과하므로 갈라 뒀다.
착수 시점 두 파일은 없으므로 첫 AC 는 rc=1 (red) 다.

## 자기 점검

1. 위 AC 를 직접 실행해 green 을 확인한다. `status` 를 `completed` 로 바꾸지 마라.
2. `summary` 에 파일별 케이스 수와 **⑵-6 에서 관측한 재구독 횟수**를 남겨라.
3. 사람 개입이 필요하면 `status:"blocked"` 와 `blocked_reason` 을 쓰고 즉시 중단한다.

## 금지사항

- `apps/web/src/store/ui-store.ts` · `src/hooks/use-media-query.ts` 를 **수정하지 마라.**
  결함은 `summary` 한 줄로
- ★**`vi.stubGlobal` 로 세운 `matchMedia` 를 되돌려라**(`vi.unstubAllGlobals()`).
  이유: 같은 vitest 프로세스를 다른 테스트 파일과 공유하므로 전역 오염이 번진다
- ★**스토어 상태를 `beforeEach` 에서 되돌려라** — 모듈 싱글톤이라 케이스 순서에 결과가 의존한다
  (이 레포는 「순서 의존이라 red 가 비결정적」을 이미 밟았다)
- ★**컴포넌트를 렌더하지 마라** — `renderHook` 까지다. 화면 조립은 다른 축이다
- ★`apps/web/vitest.config.ts` · `tests/setup.ts` 무변경 (8 lane 동시 실행 중 — 병합 충돌)
- **공용 헬퍼 모듈을 만들지 마라** — 두 테스트 파일이 각자 자기 헬퍼를 갖는다(파일을 셋으로 늘리지 마라)
- `docs/**` · `phases/**` 무변경. 다른 lane 의 테스트 파일을 만들지 마라
- 커밋하지 마라(커밋은 러너 소관)
