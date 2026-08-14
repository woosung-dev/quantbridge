// authed 도달성 **요약·판정 함수**의 판별력을 잰다 (§8.6 — 양성·음성 쌍)

import { describe, expect, it } from "vitest";

import {
  formatAuthedReachabilityFailure,
  isAuthedReachable,
  summarizeAuthedReachability,
} from "../../e2e/authed-reachability";
import type { NavProbe } from "../../e2e/design-canon-audit";

function probe(over: Partial<NavProbe> = {}): NavProbe {
  return {
    w: 1440,
    status: 200,
    examined: 12,
    subresourceFail: 0,
    subresourceFailHosts: [],
    transportFail: 0,
    transportFailHosts: [],
    sealed: 0,
    ...over,
  };
}

const URL_UNDER_AUDIT = "http://localhost:3105/trading";

describe("authed 브라우저 도달성", () => {
  it("★양성 — status 200 · 전송 실패 0건은 도달 가능이다", () => {
    const s = summarizeAuthedReachability([probe(), probe({ w: 375 })], URL_UNDER_AUDIT);
    expect(s.probeCount).toBe(2);
    expect(s.transportFailCount).toBe(0);
    expect(isAuthedReachable(s)).toBe(true);
  });

  it("★양성 — 4xx·429 서브리소스 응답은 도달성을 깎지 않는다 (응답 = 도달의 증거)", () => {
    const s = summarizeAuthedReachability(
      [probe({ subresourceFail: 7, subresourceFailHosts: ["localhost:8102"] })],
      URL_UNDER_AUDIT,
    );
    expect(s.transportFailCount).toBe(0);
    expect(isAuthedReachable(s)).toBe(true);
  });

  it("★음성 — 전송 실패는 도달 불가이고 실패 호스트를 모은다", () => {
    const s = summarizeAuthedReachability(
      [
        probe({ transportFail: 9, transportFailHosts: ["localhost:8102"] }),
        probe({ w: 375, transportFail: 7, transportFailHosts: ["localhost:8102"] }),
      ],
      URL_UNDER_AUDIT,
    );
    expect(s.transportFailCount).toBe(16);
    expect(s.targetHosts).toEqual(["localhost:8102"]);
    expect(isAuthedReachable(s)).toBe(false);
    expect(formatAuthedReachabilityFailure("/trading", s)).toMatch(/전송 실패 16건/);
  });

  it("★음성 — 문서 status 가 200 이 아니면 도달 불가다", () => {
    const s = summarizeAuthedReachability([probe({ status: 503 })], URL_UNDER_AUDIT);
    expect(s.statusFailureCount).toBe(1);
    expect(isAuthedReachable(s)).toBe(false);
  });

  it("★음성 — probe 0 건은 도달 가능이 아니고, 문구도 「도달 불가」로 단정하지 않는다", () => {
    const s = summarizeAuthedReachability([], URL_UNDER_AUDIT);
    expect(isAuthedReachable(s)).toBe(false);
    const msg = formatAuthedReachabilityFailure("/trading", s);
    expect(msg).toMatch(/관측하지 못했다/);
    expect(msg).not.toMatch(/백엔드 도달 불가/);
    // 실패 호스트가 없으므로 감사 대상(프론트) 호스트로 떨어진다 — 그것을 「실패 호스트」로 부르지 않는다.
    expect(s.targetHosts).toEqual(["localhost:3105"]);
  });
});
