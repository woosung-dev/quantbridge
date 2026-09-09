// 화면 리뷰 커버리지 래칫 ([BL-856])
//
// ★왜 필요한가 — 2026-09-06 전 화면 스윕이 **손으로 적은 라우트 목록**으로 돌았고,
//   id/토큰이 URL 에 필요한 6개가 통째로 빠졌다. 빠졌다는 사실도 몰랐다 — 그 회차는
//   덮은 범위를 21개로 셌는데 실제 `page.tsx` 는 26개였다. 목록을 만드는 스크립트는
//   scratchpad 에서 돌고 커밋되지 않아 다음 회차가 고칠 대상조차 없었다.
//
// ⇒ 목록이 아니라 **분류**를 커밋한다. `page.tsx` 가 하나 늘면 `listAppRoutes()` 가
//   즉시 그것을 돌려주고, 아래 두 표 어디에도 없는 라우트는 이 테스트가 red 로 잡는다.
//   「사람이 안 봤다」가 조용히 통과하지 않는 것이 이 파일의 유일한 목적이다.
//
// ★이 래칫은 **봤는지**를 재지, 화면이 좋은지를 재지 않는다. 품질 축은 사람이 본다.
//
// 자매 검사 — `e2e/authed-canon-remaining.spec.ts` 는 기계 축(하드 실패 수)을 재지만
// 정적 목록이라 동적 라우트를 원리상 못 본다. 그 사각이 이 항목을 만들었다.

import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import {
  isDynamic,
  listAppRoutes,
  resolveRoute,
  toRoutePattern,
} from "../../scripts/app-routes.mjs";

const APP_DIR = resolve(__dirname, "../app");

/**
 * 사람이 실제로 열어 본 라우트. 값 = 마지막으로 본 회차.
 * ★여기에 줄을 추가하는 것은 「봤다」는 선언이다. 안 보고 추가하지 마라.
 */
const REVIEWED: Record<string, string> = {
  "/": "2026-09-06",
  "/pricing": "2026-09-06",
  "/waitlist": "2026-09-06",
  "/disclaimer": "2026-09-06",
  "/terms": "2026-09-06",
  "/privacy": "2026-09-06",
  "/maintenance": "2026-09-06",
  "/not-available": "2026-09-06",
  "/sign-in": "2026-09-06",
  "/sign-up": "2026-09-06",
  "/dashboard": "2026-09-06",
  "/onboarding": "2026-09-06",
  "/strategies": "2026-09-06",
  "/strategies/new": "2026-09-06",
  "/backtests": "2026-09-06",
  "/backtests/new": "2026-09-06",
  "/optimizer": "2026-09-06",
  "/trading": "2026-09-06",
  "/orders": "2026-09-06",
  "/admin/waitlist": "2026-09-06",
  // 2026-09-08 회차가 실데이터로 연 6종 중 5종 ([BL-856]).
  "/backtests/:id": "2026-09-08",
  "/backtests/:id/trades": "2026-09-08",
  "/optimizer/:id": "2026-09-08",
  "/strategies/:id/edit": "2026-09-08",
  "/share/backtests/:token": "2026-09-08",
};

/**
 * 아직 못 연 라우트와 **그 이유**. 이유가 없으면 그냥 안 본 것이다.
 * ★비어 있는 것이 목표다. 채워 두고 잊는 자리가 아니다.
 */
const UNREVIEWED: Record<string, string> = {
  "/invite/:token":
    "픽스처 0행 — waitlist_applications 가 비어 있어 실데이터로 열 수 없다 (2026-09-08 실측)",
};

describe("[BL-856] 화면 리뷰 커버리지", () => {
  const routes = listAppRoutes(APP_DIR);

  it("앱이 라우트를 갖고 있다 — 글롭이 조용히 0을 돌려주면 이 래칫은 아무것도 안 잰다", () => {
    expect(routes.length).toBeGreaterThan(20);
  });

  it("모든 라우트가 REVIEWED 또는 UNREVIEWED 로 분류돼 있다", () => {
    const unclassified = routes.filter((r) => !(r in REVIEWED) && !(r in UNREVIEWED));
    expect(
      unclassified,
      `분류되지 않은 라우트 ${unclassified.length}건.\n` +
        "화면을 열어 보고 REVIEWED 에 날짜와 함께 넣거나, 못 여는 이유를 UNREVIEWED 에 적어라.\n" +
        `${unclassified.map((r) => `  - ${r}`).join("\n")}`,
    ).toEqual([]);
  });

  it("분류표에 앱에 없는 라우트가 남아 있지 않다 (라우트가 사라지면 줄도 지운다)", () => {
    const known = new Set(routes);
    const stale = [...Object.keys(REVIEWED), ...Object.keys(UNREVIEWED)].filter(
      (r) => !known.has(r),
    );
    expect(stale, `앱에 없는 라우트가 분류표에 남아 있다: ${stale.join(", ")}`).toEqual([]);
  });

  it("동적 라우트가 정적 목록으로는 도달 불가라는 것을 표가 안다", () => {
    // 2026-09-06 스윕이 놓친 6개는 전부 이 집합이었다. 수가 줄면(= 라우트가 사라지면)
    // 위 stale 검사가 잡고, 늘면 unclassified 검사가 잡는다.
    const dynamic = routes.filter(isDynamic);
    expect(dynamic.length).toBeGreaterThan(0);
    for (const r of dynamic) {
      expect(r in REVIEWED || r in UNREVIEWED, `${r} 가 분류되지 않았다`).toBe(true);
    }
  });
});

describe("app-routes 유틸", () => {
  it("라우트 그룹과 optional catch-all 은 URL 에서 사라진다", () => {
    expect(toRoutePattern("/(auth)/sign-in/[[...sign-in]]")).toBe("/sign-in");
    expect(toRoutePattern("/(dashboard)/backtests/[id]/trades")).toBe("/backtests/:id/trades");
    expect(toRoutePattern("")).toBe("/");
  });

  it("id 주입은 빈 자리를 남기지 않는다", () => {
    expect(resolveRoute("/backtests/:id/trades", { id: "abc" })).toBe("/backtests/abc/trades");
    expect(() => resolveRoute("/backtests/:id", {})).toThrow(/못 채웠다/);
  });
});
