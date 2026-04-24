// Phase C: stressTestRefetchInterval — terminal status 에서 false, 진행 중 상태에서 polling 유지.
// LESSON-004: useEffect dep 에 data 객체를 넣는 대신, RQ refetchInterval 함수가 q.state.data 를 직접 읽어
//             터미널 전이 시 자동 정지. 본 테스트가 그 불변식을 검증.

import { describe, expect, it } from "vitest";
import type { Query } from "@tanstack/react-query";

import { stressTestRefetchInterval } from "../hooks";
import type { StressTestDetail } from "../schemas";

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
