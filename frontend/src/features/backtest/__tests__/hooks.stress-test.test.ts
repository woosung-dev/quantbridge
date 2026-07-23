// Phase C: stressTestRefetchInterval — terminal status 에서 false, 진행 중 상태에서 polling 유지.
// LESSON-004: useEffect dep 에 data 객체를 넣는 대신, RQ refetchInterval 함수가 q.state.data 를 직접 읽어
//             터미널 전이 시 자동 정지. 본 테스트가 그 불변식을 검증.

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import { createElement, type ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { Query } from "@tanstack/react-query";

import type * as ApiModule from "../api";
import {
  stressTestKeys,
  stressTestRefetchInterval,
  useLatestStressTest,
} from "../hooks";
import type {
  StressTestDetail,
  StressTestListResponse,
} from "../schemas";

vi.mock("@clerk/nextjs", () => ({
  useAuth: () => ({ userId: "user_1", getToken: async () => "test-token" }),
}));

vi.mock("../api", async (importOriginal) => {
  const actual = await importOriginal<typeof ApiModule>();
  return { ...actual, listStressTests: vi.fn() };
});

import { listStressTests } from "../api";

const listStressTestsMock = vi.mocked(listStressTests);

function makeWrapper(queryClient: QueryClient) {
  return function Wrapper({ children }: { children: ReactNode }) {
    return createElement(QueryClientProvider, { client: queryClient }, children);
  };
}

type MockQuery = Query<StressTestDetail, Error>;

function makeQuery(
  status: MockQuery["state"]["status"],
  data: StressTestDetail | undefined,
): MockQuery {
  return {
    state: {
      status,
      data,
    },
  } as unknown as MockQuery;
}

const DETAIL_QUEUED: StressTestDetail = {
  id: "11111111-1111-4111-8111-111111111111",
  backtest_id: "22222222-2222-4222-8222-222222222222",
  kind: "monte_carlo",
  status: "queued",
  params: {},
  monte_carlo_result: null,
  walk_forward_result: null,
  error: null,
  created_at: "2026-04-24T00:00:00+00:00",
  started_at: null,
  completed_at: null,
};

describe("stressTestRefetchInterval", () => {
  it("returns polling interval when data is undefined (initial fetch)", () => {
    const result = stressTestRefetchInterval(makeQuery("pending", undefined));
    expect(result).toBe(2000);
  });

  it("returns polling interval when status=queued", () => {
    const result = stressTestRefetchInterval(
      makeQuery("success", { ...DETAIL_QUEUED, status: "queued" }),
    );
    expect(result).toBe(2000);
  });

  it("returns polling interval when status=running", () => {
    const result = stressTestRefetchInterval(
      makeQuery("success", { ...DETAIL_QUEUED, status: "running" }),
    );
    expect(result).toBe(2000);
  });

  it("returns false when status=completed (terminal)", () => {
    const result = stressTestRefetchInterval(
      makeQuery("success", { ...DETAIL_QUEUED, status: "completed" }),
    );
    expect(result).toBe(false);
  });

  it("returns false when status=failed (terminal)", () => {
    const result = stressTestRefetchInterval(
      makeQuery("success", { ...DETAIL_QUEUED, status: "failed" }),
    );
    expect(result).toBe(false);
  });

  it("returns false on query error state (무한 루프 방지)", () => {
    const result = stressTestRefetchInterval(makeQuery("error", undefined));
    expect(result).toBe(false);
  });
});

describe("useLatestStressTest", () => {
  beforeEach(() => {
    listStressTestsMock.mockReset();
  });

  it("backtest별 키로 limit=1 최신 항목을 반환한다", async () => {
    const backtestId = "22222222-2222-4222-8222-222222222222";
    const page: StressTestListResponse = {
      items: [
        {
          id: "11111111-1111-4111-8111-111111111111",
          backtest_id: backtestId,
          kind: "monte_carlo",
          status: "completed",
          created_at: "2026-04-24T00:00:00+00:00",
          completed_at: "2026-04-24T00:01:00+00:00",
        },
      ],
      total: 1,
      limit: 1,
      offset: 0,
    };
    listStressTestsMock.mockResolvedValue(page);
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    const { result } = renderHook(() => useLatestStressTest(backtestId), {
      wrapper: makeWrapper(queryClient),
    });

    await waitFor(() => expect(result.current.data).toEqual(page.items[0]));
    expect(listStressTestsMock).toHaveBeenCalledWith(backtestId, 1, "test-token");
    expect(
      queryClient.getQueryData(stressTestKeys.byBacktest("user_1", backtestId)),
    ).toEqual(page.items[0]);
  });

  it("스트레스 테스트가 없으면 null을 반환하고 error 상태가 아니다", async () => {
    const backtestId = "22222222-2222-4222-8222-222222222222";
    listStressTestsMock.mockResolvedValue({
      items: [],
      total: 0,
      limit: 1,
      offset: 0,
    });
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    const { result } = renderHook(() => useLatestStressTest(backtestId), {
      wrapper: makeWrapper(queryClient),
    });

    await waitFor(() => expect(result.current.data).toBeNull());
    expect(result.current.isError).toBe(false);
  });
});
