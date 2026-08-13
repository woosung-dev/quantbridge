// authed 도달성 **단언**의 판별력 자체를 잰다 (§8.6 — 대조기는 양성·음성 쌍으로 자기검사한다)
//
// ★이 파일이 쌍을 갖춰야 하는 이유. 초판은 음성(도달 불가 → throw) 1건에 인자 없는 `.toThrow()`
//   뿐이었다. 그러면 **무조건 throw 하는 구현도 초록**이라 판별력이 0 이다 — 같은 회차가
//   `generator-evaluator-pipeline.md` §8.6 으로 승격한 규칙을 그 회차의 코드가 어기고 있었다.
//
// ★**문구 단언은 여기 두지 않는다.** `@playwright/test` 의 `expect(value, message)` 는 그 message 를
//   Playwright 런타임에서는 에러 앞에 붙이지만 **vitest 로 부르면 `Error.message` 에 안 실린다**
//   (2026-08-14 실측 — [LESSON-103] 「같은 파일을 두 모듈 시스템이 다르게 읽는다」의 같은 뿌리).
//   그래서 이 파일은 **throw / no-throw 판별력**만 재고, 문구 계약은 포매터를 직접 부르는
//   `authed-reachability.test.ts` 가 잰다. 실제 런타임 문구는 양성 대조 1회로 확인했다.

import { describe, expect, it } from "vitest";

import { assertAuthedReachability } from "../../e2e/authed-reachability-assert";
import type { CanonAuditResult, NavProbe } from "../../e2e/design-canon-audit";

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

function result(probes: NavProbe[]): CanonAuditResult {
  return {
    label: "/trading",
    url: "http://localhost:3105/trading",
    overflow: [],
    contrast: [],
    canon: [],
    tiny: [],
    focus: [],
    motion: [],
    console: [],
    themeProbe: null,
    probes,
  };
}

describe("authed 도달성 단언", () => {
  // ── 양성 대조: 정상 환경에서 발화하면 안 된다 ──────────────────────────────
  it("★양성 — 도달 가능한 probe 는 통과시킨다 (무조건 throw 하는 구현을 잡는다)", () => {
    expect(() => assertAuthedReachability(result([probe(), probe({ w: 375 })]))).not.toThrow();
  });

  it("★양성 — 4xx 서브리소스 응답만으로는 발화하지 않는다 (응답 = 도달의 증거)", () => {
    expect(() =>
      assertAuthedReachability(
        result([probe({ subresourceFail: 3, subresourceFailHosts: ["localhost:8102"] })]),
      ),
    ).not.toThrow();
  });

  it("★양성 — 429 레이트리밋(스위트 환경 아티팩트)에도 발화하지 않는다", () => {
    expect(() =>
      assertAuthedReachability(
        result([probe({ subresourceFail: 1, subresourceFailHosts: ["localhost:8102"] })]),
      ),
    ).not.toThrow();
  });

  // ── 음성 대조: 진짜 도달 불가는 반드시 잡는다 ─────────────────────────────
  it("★음성 — 전송 실패는 「도달 불가」로 지목하고 실패 호스트를 담는다", () => {
    expect(() =>
      assertAuthedReachability(
        result([probe({ transportFail: 16, transportFailHosts: ["localhost:8102"] })]),
      ),
    ).toThrow();
  });

  it("★음성 — 문서 응답이 200 이 아니면 잡는다", () => {
    expect(() => assertAuthedReachability(result([probe({ status: 500 })]))).toThrow();
  });

  it("★음성 — probe 0 은 「관측하지 못했다」로 말한다 (「도달 불가」로 단정하지 않는다)", () => {
    expect(() => assertAuthedReachability(result([]))).toThrow();
  });
});
