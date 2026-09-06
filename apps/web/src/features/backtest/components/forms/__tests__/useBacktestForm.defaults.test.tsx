// 백테스트 폼 기본값 계약 — 「pill 이 눌린 것」과 「날짜 필드가 말하는 것」이 같아야 한다.
//
// 왜 이 파일이 생겼나 (2026-09-06 d1 실사용 1차 루프):
//   폼 기본 기간이 `어제 − 181일` 이었는데 로컬 perp 캐시 상한은 2026-08-25 였다.
//   더 나쁜 것은 **두 곳이 서로 다르게 계산**하고 있었다는 점이다 —
//   기본값은 **일 단위**(`setDate(-181)`), preset 은 **월 단위**(`setMonth(-months)`).
//   그래서 "6M" pill 이 눌린 채로 필드는 6개월과 다른 값을 담을 수 있었다.
//   이 테스트는 값을 두 번 적는 대신 **두 표현이 같은 소스에서 나오는지**를 잰다.

import { QueryClientProvider, QueryClient } from "@tanstack/react-query";
import { renderHook } from "@testing-library/react";
import { createElement, type ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
}));

import { calcDateRange } from "../date-preset-pills";
import { useBacktestForm } from "../useBacktestForm";

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return createElement(QueryClientProvider, { client: qc }, children);
}

describe("백테스트 폼 기본 기간", () => {
  it("초기 preset 은 1M 이다", () => {
    const { result } = renderHook(() => useBacktestForm(), { wrapper });
    expect(result.current.datePreset).toBe("1m");
  });

  it("기본 날짜 필드가 눌려 있는 preset 과 정확히 같은 구간을 말한다", () => {
    const { result } = renderHook(() => useBacktestForm(), { wrapper });
    const values = result.current.form.getValues();
    const range = calcDateRange(result.current.datePreset);
    expect(range).not.toBeNull();
    // period_* 는 ISO(UTC) 로 저장되고 preset 은 YMD 다 — 날짜 부분만 비교한다.
    expect(values.period_start.slice(0, 10)).toBe(range?.startDate);
    expect(values.period_end.slice(0, 10)).toBe(range?.endDate);
  });
});
