// Phase C: stressTestRefetchInterval — terminal status 에서 false, 진행 중 상태에서 polling 유지.
// LESSON-004: useEffect dep 에 data 객체를 넣는 대신, RQ refetchInterval 함수가 q.state.data 를 직접 읽어
//             터미널 전이 시 자동 정지. 본 테스트가 그 불변식을 검증.

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import { createElement, type ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { authMockState } from "@/lib/__mocks__/auth-client";

// 이 파일의 단언이 이 uid 로 만든 queryKey 를 본다 — 전역 인증 mock 기본값(`user-1`)과
// 다르므로 여기서 명시한다(ADR-034).
authMockState.userId = "user_1";

import type { Query } from "@tanstack/react-query";

import type * as ApiModule from "../api";
import {
  stressTestHistoryRefetchInterval,
  stressTestKeys,
  stressTestRefetchInterval,
  useStressTestHistory,
} from "../hooks";
import type {
  StressTestDetail,
  StressTestListResponse,
  StressTestSummary,
} from "../schemas";

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

function makeSummary(
  id: string,
  backtestId: string,
  status: StressTestSummary["status"],
): StressTestSummary {
  return {
    id,
    backtest_id: backtestId,
    kind: "monte_carlo",
    status,
    created_at: "2026-04-24T00:00:00+00:00",
    completed_at: status === "completed" ? "2026-04-24T00:01:00+00:00" : null,
    headline_metric: null,
  };
}

describe("useStressTestHistory", () => {
  beforeEach(() => {
    listStressTestsMock.mockReset();
  });

  // [BL-414] — 종전 훅은 `limit=1` 로 최신 1건만 가져왔고, 그것이 화면이 이력을
  // 못 보여준 뿌리였다. 여기서 재는 것은 "1보다 큰 페이지를 요청한다" 이다.
  it("backtest별 키로 한 페이지 전체를 반환한다", async () => {
    const backtestId = "22222222-2222-4222-8222-222222222222";
    const page: StressTestListResponse = {
      items: [
        makeSummary("11111111-1111-4111-8111-111111111111", backtestId, "completed"),
        makeSummary("11111111-1111-4111-8111-111111111112", backtestId, "failed"),
      ],
      total: 2,
      limit: 20,
      offset: 0,
    };
    listStressTestsMock.mockResolvedValue(page);
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    const { result } = renderHook(() => useStressTestHistory(backtestId), {
      wrapper: makeWrapper(queryClient),
    });

    await waitFor(() => expect(result.current.data).toEqual(page));
    expect(listStressTestsMock).toHaveBeenCalledWith(backtestId, 20, "test-token");
    expect(
      queryClient.getQueryData(stressTestKeys.byBacktest("user_1", backtestId)),
    ).toEqual(page);
  });

  it("스트레스 테스트가 없으면 빈 페이지를 반환하고 error 상태가 아니다", async () => {
    const backtestId = "22222222-2222-4222-8222-222222222222";
    listStressTestsMock.mockResolvedValue({
      items: [],
      total: 0,
      limit: 20,
      offset: 0,
    });
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    const { result } = renderHook(() => useStressTestHistory(backtestId), {
      wrapper: makeWrapper(queryClient),
    });

    await waitFor(() => expect(result.current.data?.items).toEqual([]));
    expect(result.current.isError).toBe(false);
  });
});

// 이력 폴링 — 상세와 달리 "행 하나라도 진행 중" 이 조건이다. 안 그러면 상세는 "완료"를
// 그리는데 같은 화면의 이력 행은 "대기"로 남는다.
describe("stressTestHistoryRefetchInterval", () => {
  const BT = "22222222-2222-4222-8222-222222222222";

  function pageQuery(
    items: StressTestSummary[],
  ): Query<StressTestListResponse, Error> {
    return {
      state: { status: "success", data: { items, total: items.length, limit: 20, offset: 0 } },
    } as unknown as Query<StressTestListResponse, Error>;
  }

  it("모든 행이 종결 상태면 폴링하지 않는다", () => {
    expect(
      stressTestHistoryRefetchInterval(
        pageQuery([
          makeSummary("11111111-1111-4111-8111-111111111111", BT, "completed"),
          makeSummary("11111111-1111-4111-8111-111111111112", BT, "failed"),
        ]),
      ),
    ).toBe(false);
  });

  it("진행 중인 행이 하나라도 있으면 폴링한다", () => {
    expect(
      stressTestHistoryRefetchInterval(
        pageQuery([
          makeSummary("11111111-1111-4111-8111-111111111111", BT, "completed"),
          makeSummary("11111111-1111-4111-8111-111111111112", BT, "running"),
        ]),
      ),
    ).toBe(2000);
  });
});
