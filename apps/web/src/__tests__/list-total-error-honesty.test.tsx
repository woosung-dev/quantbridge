// 목록 헤더의 total — 오류 상태에서 "0" 을 그리지 않는다 (LESSON-039 Surface Trust).
//
// ★두 feature(backtest·strategy)에 걸친 불변식이라 `src/__tests__/` 가 자리다 —
//   한쪽 feature 의 테스트 디렉터리에 두면 그 테스트가 남의 feature 를 import 하게 된다.
//
// ★왜 필요한가 (2026-08-30 아키텍처 감사). 두 목록 다 `const total = data?.total ?? 0` 이라
//   쿼리가 실패하면 `data` 가 undefined 가 되어 헤더가 **확신에 찬 "0건"/"0개"** 를 그렸다.
//   사용자는 "백엔드가 죽었다" 와 "아직 하나도 안 만들었다" 를 구분할 수 없다.
//   같은 값을 dashboard-cockpit 은 이미 `StatValue` 로 감싸 지키고 있었다.

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: vi.fn() }),
  usePathname: () => "/backtests",
  useSearchParams: () => new URLSearchParams(),
}));

const mockUseBacktests = vi.fn();
const mockUseStrategies = vi.fn();
vi.mock("@/features/backtest/hooks", () => ({
  useBacktests: (...args: unknown[]) => mockUseBacktests(...args),
}));
vi.mock("@/features/strategy/hooks", () => ({
  useStrategies: (...args: unknown[]) => mockUseStrategies(...args),
}));

import { BacktestList } from "@/features/backtest/components/backtest-list";
import { StrategyList } from "@/features/strategy/components/strategy-list";

const qc = () =>
  new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });

const renderWithQc = (ui: React.ReactElement) =>
  render(<QueryClientProvider client={qc()}>{ui}</QueryClientProvider>);

const errored = {
  data: undefined,
  isLoading: false,
  isError: true,
  error: new Error("boom"),
  refetch: vi.fn(),
};
const empty = {
  data: { items: [], total: 0 },
  isLoading: false,
  isError: false,
  error: null,
  refetch: vi.fn(),
};

beforeEach(() => {
  mockUseStrategies.mockReturnValue({ ...empty });
  mockUseBacktests.mockReturnValue({ ...empty });
});
afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("목록 헤더 total — 오류와 성공-0 을 가른다", () => {
  it("백테스트: 오류일 때 '0건' 대신 '확인 불가' 를 그린다", () => {
    mockUseBacktests.mockReturnValue({ ...errored });

    renderWithQc(<BacktestList />);

    expect(screen.queryAllByText(/실행\s*0\s*건/)).toHaveLength(0);
    expect(screen.getAllByText("확인 불가").length).toBeGreaterThan(0);
  });

  it("음성 대조 — 백테스트: 성공-0 은 '0건' 을 그대로 그린다", () => {
    mockUseBacktests.mockReturnValue({ ...empty });

    renderWithQc(<BacktestList />);

    expect(screen.getAllByText(/실행\s*0\s*건/).length).toBeGreaterThan(0);
    expect(screen.queryAllByText("확인 불가")).toHaveLength(0);
  });

  it("전략: 오류일 때 '0개' 대신 '확인 불가' 를 그린다", () => {
    mockUseStrategies.mockReturnValue({ ...errored });

    renderWithQc(<StrategyList />);

    expect(screen.queryAllByText(/전략\s*0\s*개/)).toHaveLength(0);
    expect(screen.getAllByText("확인 불가").length).toBeGreaterThan(0);
  });

  it("음성 대조 — 전략: 성공-0 은 '0개' 를 그대로 그린다", () => {
    mockUseStrategies.mockReturnValue({ ...empty });

    renderWithQc(<StrategyList />);

    expect(screen.getAllByText(/전략\s*0\s*개/).length).toBeGreaterThan(0);
    expect(screen.queryAllByText("확인 불가")).toHaveLength(0);
  });
});
