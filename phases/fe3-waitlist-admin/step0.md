# Step 0: waitlist-header-and-admin

## 읽어야 할 파일

- `apps/web/src/features/waitlist/components/admin/waitlist-admin-view.tsx` — **대상 ⑴** (132줄)
- `apps/web/src/features/waitlist/components/waitlist-header.tsx` — **대상 ⑵** (52줄)
- `apps/web/src/features/waitlist/components/__tests__/` · `admin/__tests__/` —
  ★**이 디렉터리의 기존 테스트 관용구. 먼저 읽고 mock 방식을 그대로 따라라**

## 배경

**Waitlist 는 Beta 진입 축의 사용자 표면**이다([BL-072]). 승인 흐름이 조용히 깨지면
**가입 신청이 쌓이는데 아무도 승인되지 않고**, 그 상태는 화면을 안 보면 알 수 없다.
두 컴포넌트 다 **어떤 테스트도 import 하지 않는다**(전이 폐포 실측 2026-08-21).

★**`WaitlistAdminView` 가 하는 일은 판정이다** — 필터(`pending` 기본) · 검색 · 승인 mutation 의
성공/실패 토스트. `ApiError` 를 잡아 사람이 읽을 메시지로 바꾸는 지점이 여기다.

## 작업

**테스트 파일 두 개**를 신설한다. 이 lane 이 소유한 파일은 그 둘뿐이다.

### ⑴ `apps/web/src/features/waitlist/components/admin/__tests__/waitlist-admin-view.test.tsx` (케이스 ≥7)

★**훅 2종과 toast 를 mock 해라. 이유:** 진짜 훅은 FastAPI 를 치고 `sonner` 는 DOM 포털을 연다.

```ts
const useAdminWaitlistList = vi.fn();
const useApproveWaitlist = vi.fn();
vi.mock("@/features/waitlist/hooks", () => ({
  useAdminWaitlistList: (...a: unknown[]) => useAdminWaitlistList(...a),
  useApproveWaitlist: (...a: unknown[]) => useApproveWaitlist(...a),
}));
const toastSuccess = vi.fn();
const toastError = vi.fn();
vi.mock("sonner", () => ({
  toast: { success: toastSuccess, error: toastError },
}));
```

★하위 컴포넌트(`WaitlistFilterBar`·`WaitlistStatsStrip`·`WaitlistTable`)는 **식별 가능한 더미**로
mock 해라 — 그래야 「어느 상태에서 무엇이 렌더되나」를 잴 수 있다.

1. ★**로딩 — `isPending: true` 면 스켈레톤이 뜨고 표는 없다**
2. ★**에러 — `error` 가 있으면 사람이 읽을 메시지가 뜨고 던지지 않는다**
3. ★**기본 필터는 `pending`** — `useAdminWaitlistList` 가 받은 query 에 `pending` 이 들어간다.
   ★**기본값이 틀리면 관리자가 승인 대기열을 못 본다**
4. ★**검색어가 query 로 전달된다** — 입력 후 훅 인자에 그 문자열이 들어간다(디바운스가 있으면
   `summary` 에 적고 그 형태로 재라)
5. ★★**승인 성공 → `toast.success`** · **실패(`ApiError`) → `toast.error`**.
   ★**두 방향을 다 재라** — 한쪽만 재면 「항상 성공 토스트」 구현도 통과한다
6. ★**데이터 0건 — 빈 상태에서 던지지 않는다**(목록이 `[]`)
7. ★**양성 대조** — 두 훅 mock 이 실제로 불렸고 렌더 `textContent` 가 비어 있지 않다

### ⑵ `apps/web/src/features/waitlist/components/__tests__/waitlist-header.test.tsx` (케이스 ≥6)

`next/link` 와 `ThemeToggle` 은 그대로 둬도 렌더된다(필요하면 `ThemeToggle` 만 더미로).

1. ★**던지지 않고 렌더되고 `textContent` 가 비어 있지 않다**(양성 대조)
2. ★**브랜드 링크가 있고 `href` 가 앱 내부 경로다**(`/` 로 시작한다 — 외부 URL 이면 안 된다)
3. ★**`banner` 또는 `header` 시맨틱이다** — 랜드마크가 없으면 스크린리더가 건너뛴다
4. ★**`ThemeToggle` 이 렌더된다** — 배선 확인
5. ★**링크가 중복되지 않는다** — 같은 `href` 가 두 번 나오지 않는다
6. ★**음성 대조 — 인증 전 화면이다** — 로그아웃·대시보드 같은 **authed 전용 링크가 없다**.
   이 헤더는 **로그인 이전** 화면의 것이다(있으면 `summary` 에 적어라)

## Acceptance Criteria

```bash
cd apps/web && pnpm test -- --run 'src/features/waitlist/components/__tests__/waitlist-header.test.tsx' 'src/features/waitlist/components/admin/__tests__/waitlist-admin-view.test.tsx'
cd apps/web && test "$(pnpm exec vitest list 'src/features/waitlist/components/__tests__/waitlist-header.test.tsx' 2>/dev/null | grep -c ' > ')" -ge 6
cd apps/web && test "$(pnpm exec vitest list 'src/features/waitlist/components/admin/__tests__/waitlist-admin-view.test.tsx' 2>/dev/null | grep -c ' > ')" -ge 7
cd apps/web && pnpm exec eslint 'src/features/waitlist/components/__tests__/waitlist-header.test.tsx' 'src/features/waitlist/components/admin/__tests__/waitlist-admin-view.test.tsx'
cd apps/web && pnpm exec tsc --noEmit
```

★2·3번 AC 는 **파일별** 양성 대조다. 한 파일에 몰아 쓰면 다른 파일이 비어도 통과한다.

## 자기 점검

1. 위 AC 를 직접 실행해 green 을 확인한다. `status` 를 `completed` 로 바꾸지 마라.
2. `summary` 에 파일별 케이스 수와 **⑴-4 의 디바운스 유무**를 남겨라.
3. 사람 개입이 필요하면 `status:"blocked"` 와 `blocked_reason` 을 쓰고 즉시 중단한다.

## 금지사항

- 두 대상과 하위 컴포넌트·훅을 **수정하지 마라.** 결함은 `summary` 한 줄로
- ★**진짜 네트워크 요청을 내지 마라** — 훅 mock 없이 렌더하지 마라
- ★**진짜 `sonner` 를 쓰지 마라** — 포털이 DOM 에 남아 뒤 케이스를 오염시킨다
- ★`apps/web/vitest.config.ts` · `tests/setup.ts` 무변경 (8 lane 동시 실행 중 — 병합 충돌)
- **공용 헬퍼 모듈을 만들지 마라** — 두 파일이 각자 자기 더미를 갖는다(파일을 셋으로 늘리지 마라)
- `docs/**` · `phases/**` 무변경. 다른 lane 의 테스트 파일을 만들지 마라
- 커밋하지 마라(커밋은 러너 소관)
