// 캘리브레이션 — 감사 코어를 known-good 산출물(프로토타입)에 먼저 돌려 자를 검증한다
//
// ★순서가 핵심이다. 이 spec 은 React 보다 **먼저** 돈다.
// `design-canon-audit.ts` 가 `runtime-check.mjs` 의 이식본이므로, 같은 입력(프로토타입
// 17벌)에 같은 출력(17/17 PASS + 동일 canon 카운트)을 내야 한다. 재현되지 않으면
// **이식이 틀린 것이지 React 가 틀린 게 아니다.** 그 구분을 못 하면 앱에 없는 결함을
// 쫓게 된다 (지난 세션에 이 절차로 검사기 자체 버그 4개를 잡았다).
//
// 대상은 커밋된 정적 HTML 이라 dev 서버도 백엔드도 인증도 필요 없다.
// 따라서 CI 에서 그대로 돈다 — 감사 코어를 누가 건드리면 즉시 빨개진다.

import { existsSync, readdirSync } from "node:fs";
import { resolve } from "node:path";
import { pathToFileURL } from "node:url";

import { expect, test } from "@playwright/test";

import { auditUrl, formatCanonResult, hardFailCount } from "./design-canon-audit";

const PROTOTYPE_DIR = resolve(__dirname, "../../docs/reference/design/prototypes/shotgun-2026-07");

/**
 * 2026-07-20 실측 기준선. `node docs/reference/design/prototypes/shotgun-2026-07/runtime-check.mjs` 출력.
 *
 * canon 은 하드 실패가 아니라 지표라 여기서 **정확히 일치**를 요구한다.
 * 프로토타입은 확정된 시각 정본이므로 이 수가 바뀌었다면 둘 중 하나다.
 *   (a) 프로토타입이 의도적으로 바뀌었다 → 이 표를 같이 갱신한다
 *   (b) 감사 코어가 틀어졌다 → 코어를 고친다
 * 어느 쪽인지 판단하지 않고 표를 맞추면 검사기가 자기 자신을 정당화하게 된다.
 */
const CANON_BASELINE: Readonly<Record<string, number>> = {
  "screen-01-trading-cockpit.html": 41,
  "screen-02-dashboard.html": 27,
  "screen-03-backtests-list.html": 29,
  "screen-04-trade-detail.html": 21,
  "screen-05-backtest-setup.html": 7,
  "screen-06-strategies-list.html": 25,
  "screen-07-strategy-create.html": 7,
  "screen-08-strategy-editor.html": 9,
  "screen-09-optimizer-list.html": 25,
  "screen-10-optimizer-detail.html": 31,
  "screen-11-orders.html": 33,
  "screen-12-onboarding.html": 25,
  "screen-13-error-pages.html": 7,
  "screen-14-landing.html": 8,
  "screen-15-login.html": 2,
  "screen-16-pricing.html": 8,
  "screen-17-waitlist.html": 8,
};

/** 라이트 2벌. `bgOf()` 의 배경 역전 처리를 실제로 태우는 유일한 대상이다. */
const LIGHT_BASELINE: Readonly<Record<string, number>> = {
  "light-01-report.html": 13,
  "light-02-trading-cockpit.html": 13,
};

/** 디렉터리에서 실제로 발견한 화면 파일. 원본 `runtime-check.mjs:15` 와 같은 글롭. */
function discoverScreens(): string[] {
  return readdirSync(PROTOTYPE_DIR)
    .filter((f) => /^screen-.*\.html$/.test(f))
    .sort();
}

// ── 위생 메타테스트 ──────────────────────────────────────────────────────────
// 인벤토리가 조용히 비면 아래 캘리브레이션은 0건을 돌고 그린이 된다.
// `src/__tests__/no-internal-ids.test.ts` 가 쓰는 방어(개수 + 명시 열거)를 그대로 쓴다.
test.describe("위생 — 캘리브레이션 대상이 실제로 존재한다", () => {
  test("프로토타입 디렉터리가 존재한다", () => {
    expect(
      existsSync(PROTOTYPE_DIR),
      `프로토타입 경로가 없다: ${PROTOTYPE_DIR}. 이식 정본이 사라졌거나 경로가 바뀌었다`,
    ).toBe(true);
  });

  test("화면 17벌을 전부 발견한다", () => {
    const found = discoverScreens();
    expect(
      found.length,
      `화면 파일 수가 17이 아니다. 발견: ${found.join(", ")}`,
    ).toBe(17);
    // 개수만 세면 이름이 통째로 바뀌어도 통과한다. 기준선 키와 1:1 인지까지 본다.
    expect(found).toEqual(Object.keys(CANON_BASELINE).sort());
  });

  test("라이트 2벌을 전부 발견한다", () => {
    for (const file of Object.keys(LIGHT_BASELINE)) {
      expect(existsSync(resolve(PROTOTYPE_DIR, file)), `${file} 없음`).toBe(true);
    }
  });
});

// ── 캘리브레이션 본체 ────────────────────────────────────────────────────────
test.describe("캘리브레이션 — 다크 정본 17벌", () => {
  for (const [file, expectedCanon] of Object.entries(CANON_BASELINE)) {
    test(`${file} — 하드 실패 0 · canon ${expectedCanon}`, async ({ browser }) => {
      test.setTimeout(180_000); // 4폭 × (goto + 정착) + Tab 30회 + reduced-motion

      const url = pathToFileURL(resolve(PROTOTYPE_DIR, file)).href;
      const res = await auditUrl(browser, url, { label: file });

      // 출력을 그대로 기록한다 — 재현했다는 주장의 근거가 리포트에 남아야 한다.
      // `console.log` 가 아니라 stdout 직접 쓰기다. 이건 디버그 로그가 아니라
      // 검사기의 산출물이며, no-console 룰이 막으려는 대상이 아니다.
      process.stdout.write(formatCanonResult(res) + "\n");

      expect(
        hardFailCount(res),
        `${file} 이 하드 실패했다. runtime-check.mjs 는 PASS 였으므로 이식된 감사 코어가 틀렸다:\n${formatCanonResult(res)}`,
      ).toBe(0);

      expect(
        res.canon.length,
        `${file} canon 카운트가 기준선과 다르다. 프로토타입이 바뀌었는지 감사 코어가 틀어졌는지 먼저 판별하라`,
      ).toBe(expectedCanon);
    });
  }
});

test.describe("캘리브레이션 — 라이트 2벌", () => {
  for (const [file, expectedCanon] of Object.entries(LIGHT_BASELINE)) {
    test(`${file} — 하드 실패 0 · canon ${expectedCanon}`, async ({ browser }) => {
      test.setTimeout(180_000);

      const url = pathToFileURL(resolve(PROTOTYPE_DIR, file)).href;
      const res = await auditUrl(browser, url, { label: file });

      process.stdout.write(formatCanonResult(res) + "\n");

      expect(
        hardFailCount(res),
        `${file} 이 하드 실패했다:\n${formatCanonResult(res)}`,
      ).toBe(0);
      expect(res.canon.length, `${file} canon 카운트가 기준선과 다르다`).toBe(expectedCanon);
    });
  }
});
