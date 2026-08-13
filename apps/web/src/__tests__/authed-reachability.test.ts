import { describe, expect, it } from "vitest";

import {
  formatAuthedReachabilityFailure,
  isAuthedReachable,
  summarizeAuthedReachability,
} from "../../e2e/authed-reachability";

describe("authed 브라우저 도달성", () => {
  it("status 200과 서브리소스 실패 0건을 도달 가능으로 판정한다", () => {
    const summary = summarizeAuthedReachability(
      [
        {
          w: 1440,
          status: 200,
          examined: 12,
          subresourceFail: 0,
          subresourceFailHosts: [],
          sealed: 0,
        },
      ],
      "http://localhost:3102/trading",
    );

    expect(isAuthedReachable(summary)).toBe(true);
    expect(summary.targetHosts).toEqual(["localhost:3102"]);
  });

  it("브라우저가 기록한 실패 건수와 대상 호스트를 도달 불가 메시지에 남긴다", () => {
    const summary = summarizeAuthedReachability(
      [
        {
          w: 1440,
          status: 200,
          examined: 12,
          subresourceFail: 3,
          subresourceFailHosts: ["localhost:8102"],
          sealed: 0,
        },
        {
          w: 1024,
          status: 503,
          examined: 0,
          subresourceFail: 1,
          subresourceFailHosts: ["localhost:8102", "api.example.test"],
          sealed: 0,
        },
      ],
      "http://localhost:3102/trading",
    );

    expect(isAuthedReachable(summary)).toBe(false);
    expect(formatAuthedReachabilityFailure("/trading", summary)).toBe(
      "/trading — 백엔드 도달 불가. 브라우저 실측: 페이지 응답 비정상 1폭, " +
        "서브리소스 실패 4건. 대상 호스트: api.example.test, localhost:8102.",
    );
  });
});
