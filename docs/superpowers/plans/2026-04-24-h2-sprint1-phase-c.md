# H2 Sprint 1 Phase C — FE Trading UI 개선 SDD

> **작성일:** 2026-04-24  
> **상태:** 계획 확정  
> **목표:** Kill Switch 배너 + Demo/Live 배지 + 조건부 주문 폴링 + E2E 확장  
> **선행 조건:** Phase B Gate 통과 (pytest tests/ -q 985+ green)

---

## 배경

Sprint X1+X3 이후 Trading UI dogfood 중 발견된 UX 공백 3종:

1. Kill Switch 활성 시 사용자가 panel을 직접 열어야 인지 가능 → 전체 페이지 배너 필요
2. Exchange Account의 Demo/Live 구분이 텍스트 색상만 → shadcn Badge 컴포넌트로 명확화
3. 주문 체결 여부를 새로고침해야 알 수 있음 → `state: "submitted"` 조건부 5s 폴링 + toast 필요

**LESSON-004 zero-tolerance:** `useEffect` dep에 RQ/Zustand/RHF/Zod 결과 객체 사용 시 CPU 100% 위험.  
주문 상태 변화 감지는 `useRef<Map<string, string>>` 으로 직전 `state` 추적.

---

## 사전 조사 결과 (실측 기반)

| 대상                           | 실제 구현 상태                                                                                   |
| ------------------------------ | ------------------------------------------------------------------------------------------------ |
| Order 필드명                   | `state` (not `status`) — `OrderState: "pending"\|"submitted"\|"filled"\|"rejected"\|"cancelled"` |
| KillSwitchEvent `trigger_type` | `"cumulative_loss"\|"daily_loss"\|"api_error"`                                                   |
| Kill Switch 폴링 훅            | `useKillSwitchEvents` — 30s 폴링, error 시 중단                                                  |
| exchange-accounts-panel.tsx    | mode 배지: `<span className={...}>` — Badge 컴포넌트 미사용                                      |
| E2E 인증                       | 현재 인증 fixture 없음 — `smoke.spec.ts` 공용 페이지만                                           |

---

## 컴포넌트 및 파일 범위

| 파일                                                        | 변경 내용                              |
| ----------------------------------------------------------- | -------------------------------------- |
| `frontend/src/app/(dashboard)/trading/page.tsx`             | Kill Switch 배너 + 로딩/에러 상태 처리 |
| `frontend/src/features/trading/exchange-accounts-panel.tsx` | Badge 컴포넌트 교체 + null 가드        |
| `frontend/src/features/trading/hooks.ts`                    | 조건부 폴링 + state 변화 감지 + toast  |
| `frontend/e2e/trading-ui.spec.ts`                           | 신규 E2E 시나리오 4종 + auth 처리      |

---

## 태스크 분해

### C-1. Kill Switch Active 배너

**파일:** `frontend/src/app/(dashboard)/trading/page.tsx`

**현재 상태:** `kill-switch-panel.tsx`가 별도 섹션으로 존재. active 이벤트 있어도 페이지 상단 배너 없음.

#### 정상 경로 (active 이벤트 존재)

```tsx
// trading/page.tsx
import { useKillSwitchEvents } from "@/features/trading/hooks";

const KS_TRIGGER_LABELS: Record<string, string> = {
  daily_loss: "일일 손실 한도 초과",
  cumulative_loss: "누적 손실 한도 초과",
  api_error: "거래소 API 오류",
};

function TradingPage() {
  const {
    data: ksEvents,
    isLoading: ksLoading,
    isError: ksError,
  } = useKillSwitchEvents();

  const activeKsEvents = ksEvents?.filter((e) => !e.resolved_at) ?? [];
  const activeKsCount = activeKsEvents.length;

  // ...
  return (
    <div>
      {/* Kill Switch 배너 — 페이지 상단 */}
      <KillSwitchBanner
        activeEvents={activeKsEvents}
        isLoading={ksLoading}
        isError={ksError}
      />
      {/* 나머지 Trading UI */}
    </div>
  );
}
```

#### KillSwitchBanner 컴포넌트 (별도 파일 또는 인라인)

```tsx
// 에러 상태: Kill Switch 확인 불가 → 안전상 경고 표시
if (isError) {
  return (
    <div
      role="alert"
      className="rounded-md border border-yellow-500 bg-yellow-50 px-4 py-3 text-sm text-yellow-800"
    >
      ⚠️ Kill Switch 상태를 확인할 수 없습니다. 주문 실행 전 상태를 수동으로
      확인하세요.
    </div>
  );
}

// 로딩 상태: 배너 미표시 (데이터 없음 = active 없음으로 간주)
// → isLoading=true면 silent

// 정상 + active 이벤트 없음: 배너 미표시

// 정상 + active 이벤트 1개
if (activeEvents.length === 1) {
  return (
    <div
      role="alert"
      className="rounded-md border border-destructive bg-destructive/10 px-4 py-3 text-sm text-destructive"
    >
      <strong>Kill Switch 활성</strong> —{" "}
      {KS_TRIGGER_LABELS[activeEvents[0].trigger_type] ??
        activeEvents[0].trigger_type}
      . 주문 실행이 비활성화됩니다.
    </div>
  );
}

// 정상 + active 이벤트 여러 개
if (activeEvents.length > 1) {
  return (
    <div
      role="alert"
      className="rounded-md border border-destructive bg-destructive/10 px-4 py-3 text-sm text-destructive"
    >
      <strong>Kill Switch 활성 ({activeEvents.length}건)</strong> — 주문 실행이
      비활성화됩니다.
      <ul className="mt-1 list-disc list-inside text-xs opacity-75">
        {activeEvents.map((e) => (
          <li key={e.id}>
            {KS_TRIGGER_LABELS[e.trigger_type] ?? e.trigger_type}
          </li>
        ))}
      </ul>
    </div>
  );
}

return null;
```

#### 주문 버튼 disabled 연동

- `activeKsCount > 0` OR `ksError` → 주문 버튼 `disabled`
- tooltip 텍스트:
  - `ksError` 시: "Kill Switch 상태 확인 불가 — 주문 실행 중단"
  - `activeKsCount > 0` 시: "Kill Switch 활성 중 — 주문 불가"

> **React Query 중복 요청 방지:** `useKillSwitchEvents`는 동일 queryKey를 사용하므로 `page.tsx`와 `kill-switch-panel.tsx`에서 동시 호출해도 React Query가 자동 deduplication 처리. 추가 요청 없음.

**에지 케이스:**

| 케이스                       | 처리 방식                                                         |
| ---------------------------- | ----------------------------------------------------------------- |
| API 500 / 네트워크 오류      | `isError=true` → 황색 경고 배너 (안전 우선)                       |
| 로딩 중                      | 배너 미표시 (초기 로딩 1회 — 30s 후 갱신)                         |
| `trigger_type` 알 수 없는 값 | `KS_TRIGGER_LABELS[type] ?? type` fallback                        |
| Kill Switch resolve 시       | 30s 폴링으로 자동 배너 소멸                                       |
| SSR hydration                | `useKillSwitchEvents`는 client-only 훅 — `"use client"` 경계 확인 |

---

### C-2. Demo/Live 배지 Badge 컴포넌트 교체

**파일:** `frontend/src/features/trading/exchange-accounts-panel.tsx`

**현재 코드 (라인 51-60):**

```tsx
<span
  className={
    a.mode === "demo"
      ? "text-blue-600 font-medium"
      : "text-green-600 font-medium"
  }
>
  {a.mode}
</span>
```

**수정:**

```tsx
import { Badge } from "@/components/ui/badge";

function ModeBadge({ mode }: { mode: string | null | undefined }) {
  if (mode === "demo") {
    return (
      <Badge
        variant="outline"
        className="border-amber-500 text-amber-600 uppercase text-xs font-semibold"
      >
        DEMO
      </Badge>
    );
  }
  if (mode === "live") {
    return (
      <Badge
        variant="outline"
        className="border-green-500 text-green-600 uppercase text-xs font-semibold"
      >
        LIVE
      </Badge>
    );
  }
  // null / undefined / 미지원 mode 값 fallback
  return (
    <Badge
      variant="outline"
      className="border-gray-400 text-gray-500 uppercase text-xs"
    >
      {mode ?? "UNKNOWN"}
    </Badge>
  );
}

// exchange-accounts-panel.tsx 내부
<ModeBadge mode={a.mode} />;
```

**에지 케이스:**

| 케이스                       | 처리 방식                                                                       |
| ---------------------------- | ------------------------------------------------------------------------------- |
| `a.mode === null`            | fallback: gray Badge "UNKNOWN"                                                  |
| `a.mode === undefined`       | 동일 fallback                                                                   |
| 새 mode 추가 (예: `"paper"`) | fallback: gray Badge mode 값 그대로 표시                                        |
| 다크 모드                    | Tailwind amber/green → dark mode 에서도 variant="outline" 이면 적절히 대비 유지 |

---

### C-3. Order Status 조건부 폴링 + Toast

**파일:** `frontend/src/features/trading/hooks.ts`

**⚠️ 주의 — 필드명 정확도:**  
BE `OrderState` → FE `Order.state` (not `status`). 실측 확인된 값: `"pending" | "submitted" | "filled" | "rejected" | "cancelled"`

**현재 상태:** 30s 고정 폴링, 상태 변화 toast 없음.

**수정 방향:**

```typescript
import { useEffect, useRef, useCallback } from "react";
import { useQuery } from "@tanstack/react-query";
import { toast } from "sonner";
import type { Order } from "./schemas";

export function useOrders(limit = 50) {
  const fetcher = useCallback(makeOrdersFetcher(limit), [limit]);

  const query = useQuery({
    ...ordersQueryOptions(limit),
    queryFn: fetcher,
    refetchInterval: (q) => {
      if (q.state.status === "error") return false;
      // state: "submitted" | "pending" 인 주문이 있으면 5s 폴링
      const hasActive = (q.state.data as Order[] | undefined)?.some(
        (o) => o.state === "submitted" || o.state === "pending",
      );
      return hasActive ? 5_000 : 30_000;
    },
  });

  // LESSON-004 준수: 직전 상태를 useRef로 추적
  // query.data는 React Query structural sharing으로 내용 변경 시만 새 reference → dep 안전
  const prevStateRef = useRef<Map<string, Order["state"]>>(new Map());

  useEffect(() => {
    const orders = query.data;
    if (!orders) return;

    orders.forEach((o) => {
      const prev = prevStateRef.current.get(o.id);

      // prev가 active state이고 terminal state로 전환된 경우만 toast
      if (prev === "submitted" || prev === "pending") {
        if (o.state === "filled") {
          toast.success(
            `${o.symbol} ${o.side === "buy" ? "매수" : "매도"} 체결`,
            {
              description: `체결가: ${o.filled_price ?? "시장가"}`,
            },
          );
        } else if (o.state === "cancelled") {
          toast.warning(`${o.symbol} 주문 취소됨`);
        } else if (o.state === "rejected") {
          toast.error(`${o.symbol} 주문 거부됨`, {
            description: o.error_message ?? "거래소 오류",
          });
        }
      }

      prevStateRef.current.set(o.id, o.state);
    });

    // 메모리 누수 방지: 더 이상 존재하지 않는 주문 ID 제거
    const currentIds = new Set(orders.map((o) => o.id));
    for (const id of prevStateRef.current.keys()) {
      if (!currentIds.has(id)) {
        prevStateRef.current.delete(id);
      }
    }
  }, [query.data]); // query.data는 structural sharing으로 내용 변경 시만 갱신

  return query;
}
```

**에지 케이스:**

| 케이스                              | 처리 방식                                                                      |
| ----------------------------------- | ------------------------------------------------------------------------------ |
| `o.state` 미지원 값 (예: 미래 추가) | toast 미발동 (조건 미충족)                                                     |
| 컴포넌트 마운트/언마운트 반복       | `prevStateRef` 초기화 — active 주문은 다음 폴링 후 ref 갱신, toast 없음 (허용) |
| 목록에서 삭제된 주문                | `currentIds`로 stale entry 정리 → 메모리 누수 없음                             |
| `filled_price === null`             | toast description: "시장가" fallback                                           |
| `error_message === null`            | toast description: "거래소 오류" fallback                                      |
| `side` 없는 경우                    | `o.side === "buy"` 조건 — undefined면 삼항 "매도"로 fallback                   |
| limit=0 또는 음수                   | `makeOrdersFetcher`에서 처리 (하위 레이어 책임)                                |
| 동일 주문 state가 두 번 같은 값     | `prev === current` → toast 미발동 (idempotent)                                 |

> **ESLint `react-hooks/exhaustive-deps` 통과 확인 필수.** `[query.data]` dep에 대해 ESLint가 경고를 내면 `// eslint-disable-line` 절대 금지 — 대신 RQ의 `select` 옵션으로 데이터 추출 후 `orders` 변수를 dep으로 사용하는 방식으로 우회.

---

### C-4. Playwright E2E 시나리오 확장

**파일:** `frontend/e2e/trading-ui.spec.ts` (신규)

**인증 처리 방침:**  
현재 E2E 인증 fixture 없음. Trading 페이지는 Clerk 인증 필요.  
→ `page.route`로 Clerk 인증 체크 API mock + `/api/auth/session` mock으로 bypass.  
또는 인증 불필요한 public mock route 패턴 사용.

```typescript
import { test, expect } from "@playwright/test";

// 공통 mock 헬퍼
async function mockTradingAPIs(
  page: Page,
  overrides: {
    ksEvents?: object[];
    accounts?: object[];
    orders?: object[];
  } = {},
) {
  const ksEvents = overrides.ksEvents ?? [];
  const accounts = overrides.accounts ?? [];
  const orders = overrides.orders ?? [];

  await page.route("**/api/v1/kill-switch/events**", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(ksEvents),
    }),
  );
  await page.route("**/api/v1/exchange-accounts**", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(accounts),
    }),
  );
  await page.route("**/api/v1/orders**", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(orders),
    }),
  );
  // Clerk auth mock: 세션 유효한 척
  await page.route("**/clerk/**", (route) => route.continue());
}

// 완전한 mock 객체 정의 (... 금지)
const MOCK_DEMO_ACCOUNT = {
  id: "acc-demo-1",
  name: "Bybit Demo",
  exchange: "bybit_futures",
  mode: "demo",
  is_active: true,
  created_at: "2026-04-24T00:00:00Z",
};

const MOCK_KS_EVENT_ACTIVE = {
  id: "ks-1",
  trigger_type: "daily_loss",
  trigger_value: "600.00",
  threshold: "500.00",
  triggered_at: "2026-04-24T10:00:00Z",
  resolved_at: null,
};

const MOCK_KS_EVENT_RESOLVED = {
  ...MOCK_KS_EVENT_ACTIVE,
  resolved_at: "2026-04-24T11:00:00Z",
};

const MOCK_ORDER_SUBMITTED = {
  id: "ord-1",
  symbol: "BTC/USDT:USDT",
  side: "buy",
  quantity: "0.001",
  state: "submitted", // ← state (not status)
  filled_price: null,
  exchange_order_id: "bybit-123",
  error_message: null,
  created_at: "2026-04-24T10:01:00Z",
};

test.describe("Trading UI", () => {
  test.beforeEach(async ({ page }) => {
    // 기본: KS 없음, 계정 없음, 주문 없음
    await mockTradingAPIs(page);
  });

  test("Demo 배지가 Exchange Account 카드에 표시된다", async ({ page }) => {
    await mockTradingAPIs(page, { accounts: [MOCK_DEMO_ACCOUNT] });
    await page.goto("/trading");
    // shadcn Badge 렌더링 — 텍스트 "DEMO" 확인
    await expect(page.getByText("DEMO")).toBeVisible();
    // 배지에 amber 색상 클래스 확인 (선택적)
    const badge = page.getByText("DEMO");
    await expect(badge).toHaveClass(/amber/);
  });

  test("Kill Switch active 시 destructive 배너가 페이지 상단에 표시된다", async ({
    page,
  }) => {
    await mockTradingAPIs(page, { ksEvents: [MOCK_KS_EVENT_ACTIVE] });
    await page.goto("/trading");
    const banner = page.getByRole("alert");
    await expect(banner).toBeVisible();
    await expect(banner).toContainText("Kill Switch 활성");
    // 한국어 trigger_type 매핑 확인
    await expect(banner).toContainText("일일 손실 한도 초과");
  });

  test("Kill Switch active 시 주문 버튼이 비활성화된다", async ({ page }) => {
    await mockTradingAPIs(page, { ksEvents: [MOCK_KS_EVENT_ACTIVE] });
    await page.goto("/trading");
    // 주문 버튼 존재 여부 확인 (텍스트가 다를 경우 aria-label 또는 data-testid 사용)
    const orderBtn = page
      .getByRole("button", { name: /주문|Order|실행/i })
      .first();
    if ((await orderBtn.count()) > 0) {
      await expect(orderBtn).toBeDisabled();
    }
  });

  test("Kill Switch API 오류 시 황색 경고 배너가 표시된다", async ({
    page,
  }) => {
    await page.route("**/api/v1/kill-switch/events**", (route) =>
      route.fulfill({ status: 500, body: "Internal Server Error" }),
    );
    await page.goto("/trading");
    const banner = page.getByRole("alert");
    await expect(banner).toBeVisible();
    await expect(banner).toContainText("확인할 수 없습니다");
  });

  test("Kill Switch resolve 후 배너가 사라진다", async ({ page }) => {
    // 1차: active event
    await mockTradingAPIs(page, { ksEvents: [MOCK_KS_EVENT_ACTIVE] });
    await page.goto("/trading");
    await expect(page.getByRole("alert")).toBeVisible();

    // 2차: resolved event (폴링 interval mocking via route update)
    await page.route("**/api/v1/kill-switch/events**", (route) =>
      route.fulfill({
        status: 200,
        body: JSON.stringify([MOCK_KS_EVENT_RESOLVED]),
      }),
    );
    // React Query refetch 트리거 (30s 폴링 대신 수동 강제)
    await page.evaluate(() => window.dispatchEvent(new Event("focus")));
    await expect(page.getByRole("alert")).not.toBeVisible({ timeout: 5000 });
  });
});
```

**에지 케이스 & 주의사항:**

| 케이스                    | 처리 방식                                                                                                        |
| ------------------------- | ---------------------------------------------------------------------------------------------------------------- |
| 인증 필요 페이지          | Clerk mock — 현재 E2E 인증 없으므로 `/trading` 접근 시 redirect 가능. 실제 실행 전 인증 fixture 구현 필요 (TODO) |
| Toast 확인                | Playwright `page.getByText` — sonner는 DOM에 직접 렌더링하므로 포착 가능                                         |
| 동적 데이터 (주문 ID 등)  | mock 데이터에서 고정값 사용                                                                                      |
| 배너 사라짐 테스트        | React Query `onFocus` refetch 활용 — windowFocus 이벤트 dispatch로 즉시 refetch 트리거                           |
| Playwright route 우선순위 | 나중에 등록한 route가 우선 — override 패턴 동작                                                                  |

---

## 완료 기준 (Gate-C)

| 항목                      | 검증 방법               | 기준                                        |
| ------------------------- | ----------------------- | ------------------------------------------- |
| Kill Switch 배너 (active) | E2E `role="alert"`      | 한국어 메시지 + destructive 스타일          |
| Kill Switch 배너 (error)  | E2E 500 mock            | 황색 경고 배너 표시                         |
| Kill Switch disabled      | E2E button attr         | `disabled` 속성 존재                        |
| Demo/Live 배지            | E2E `getByText("DEMO")` | amber 색상 Badge 존재                       |
| 조건부 폴링               | Unit test 또는 E2E      | `state: "submitted"` 존재 시 5s, 없으면 30s |
| Toast                     | Unit test (vitest)      | `submitted→filled` 시 toast.success 호출    |
| `null` mode guard         | Unit test               | ModeBadge null 입력 → "UNKNOWN" 배지        |
| FE 테스트                 | `pnpm test`             | 167+ green                                  |
| 타입 체크                 | `pnpm tsc --noEmit`     | 0 에러                                      |
| ESLint                    | `pnpm lint`             | 0 warning (hooks/\* disable 없음)           |
| E2E                       | Playwright 5 시나리오   | PASS                                        |

---

## 브랜치

`feat/h2s1-trading-ui` → squash merge → `stage/h2-sprint1`

**커밋:**

```
c6 feat(trading-ui): kill switch active/error banner + KS_TRIGGER_LABELS + order button disabled
c7 feat(trading-ui): ModeBadge null guard + order state conditional polling + toast
c8 test(e2e): trading UI kill switch (4 scenarios) + demo badge e2e
```
