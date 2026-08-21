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
//
// ── 판정 계약 (2026-08-12 명시화 · [BL-708] step 3) ──────────────────────────
//
// 대상이 **커밋된 정적 HTML** 이지 앱이 아니므로, 앱 spec(`design-canon-public` ·
// `authed-canon-p1`)과 계약이 같을 이유가 없다. 저쪽은 백엔드 부재 소음을 `ignoreConsole` 로
// 빼지만 **여기는 아무것도 빼지 않는다.** 대신 코어가 `file://` 대상의 원격 요청을 goto 전에
// 봉인하므로(step 2 `sealRemoteSubresources`) 제3자 CDN 이 판정에 아예 안 들어온다.
// 즉 여기서 「하드 실패 0」은 **「프로토타입이 자기 바이트만으로 렌더됐을 때 0」** 이라는 뜻이다.
//
//   ㅇ 하드 실패로 **세는 것** (코어 `hardFailCount()` 5항과 1:1)
//     overflow · contrast(WCAG AA) · focus 링 부재 · reduced-motion 누수 · 콘솔 에러
//   ㅇ **안 세는 것**
//     canon(하드 실패가 아니라 **드리프트 지표** — 아래 표와 정확히 일치하는지만 본다) ·
//     tiny(9.4px 미만 텍스트 — 리포트에만 남는다)
//   ㅇ 함께 단언하는 것 (「0 건」이 무증거가 되지 않게)
//     4폭 도달 · 폭마다 status 200 · `minExamined>0` · 로컬 서브리소스 실패 0 ·
//     봉인이 실제로 걸림(`sealed>0`)
//
// ★계약을 **느슨하게 하지 않았다.** 종전 단언 2줄(하드 실패 0 · canon 정확 일치)은 문자 그대로
//   남기고 도달 증거만 얹었다. 얹은 이유는 종전 계약에 실제 구멍이 있었기 때문이다 —
//   canon·contrast 표본은 `SAMPLED_WIDTHS`(1440·375)에서만 뜬다(`design-canon-audit.ts:24`).
//   따라서 **1024·768 이 조용히 빠져도** canon 합계가 그대로라 두 단언이 모두 초록이었다.
//   이제 폭별 probe 를 직접 센다.
//   ★말이 아니라 변이로 확인했다(2026-08-12). `auditUrl` 에 `widths: [1440, 375]` 를 심어
//     1024·768 을 떨어뜨리자 리포트는 `screen-15-login.html … canon=2 console=0` = **종전 계약
//     그대로 초록**이었고(하드 실패 0 · canon 기준선 2 일치), red 를 낸 것은 새로 얹은 도달
//     단언 하나뿐이었다. 변이 도달은 같은 리포트의 `examined=["1440px:40","375px:37"]`
//     (2폭만 남음)로 확인했다.
//
// ★**WARN 강등([BL-708] 권장 접근 ⑵)은 채택하지 않는다.** 실측이 반대 방향을 가리켰다.
//   2026-08-12 전량 실행에서 19벌의 하드 축이 전부 0(특히 contrast 0건)이고, 관측된 **최저
//   대비는 4.92:1** 이다 — 하드 문턱 4.5 까지 여유가 **0.42** 뿐이다. 문턱 ±0.5 밴드는
//   4.0~5.0 을 덮으므로 **그 여유를 통째로 삼킨다**: 4.92 짜리 텍스트가 진짜로 4.5 밑으로
//   내려가는 회귀(= 실제 WCAG AA 위반)가 WARN 으로 강등돼 게이트를 통과한다.
//   게다가 ⑵ 가 겨눈 플레이크의 기전은 문턱 근접이 아니라 **원격 폰트 404** 였고(step 1·2 실측),
//   그것은 봉인으로 구조적으로 제거됐다. 밴드는 이미 없는 병에 판별력을 지불하는 셈이다.
//
// ── 반복 안정성 근거 — 다시 유도하지 마라 ────────────────────────────────────
//
// 2026-08-12, 같은 커밋 · **독립 프로세스** 실행 결과:
//   - 봉인 **전** 3회 — 초록1/red2. red 는 매번 **다른 파일·다른 폭**에서 났고 정체는 전부
//     `fonts.gstatic.com` archivo woff2 **404** 하나였다(콘솔 에러 = 하드 실패 1건).
//   - 봉인 **후**(step 2) 3회 — rc=0/0/0 · `22 passed` ×3 · ANSI 제거 후 감사 출력 112줄 전문 동일.
//   - 본 계약 명시 **후**(step 3) 3회 — rc=0/0/0 · `22 passed` ×3. 요약·도달 줄 38 줄(19벌 ×2)이
//     ANSI 제거·정렬 후 3회 **전문 동일**했다. 19벌 전 폭이 `status=200` · `subresourceFail=0` ·
//     `sealed=2` 로 일정하고, 파일별 최저 canon 대비는 4.92 / 5.41 / 5.44 세 값에만 나타난다
//     (13벌 / 2벌 / 4벌).
// ⇒ 회차를 가르던 축은 네트워크 **하나**였고 지금은 닫혀 있다. 이 재현을 다시 돌려 확인하지 마라.
//   판정이 또 갈리면 그것은 **새 원인**이다 — [BL-708] 본문의 「소수 폰트 크기(10.08px)가
//   안티에일리어싱에 흔들린다」 가설은 step 2 가 이미 반증했다(10.08px 는 `rem` 산술의 결정적 산물).

import { existsSync, readdirSync } from "node:fs";
import { resolve } from "node:path";
import { pathToFileURL } from "node:url";

import { expect, test } from "@playwright/test";

import {
  auditUrl,
  CANON_WIDTHS,
  formatCanonResult,
  hardFailCount,
  minExamined,
  type CanonAuditResult,
} from "./design-canon-audit";

const PROTOTYPE_DIR = resolve(__dirname, "../../../docs/design/prototypes/shotgun-2026-07");

/**
 * 2026-07-20 실측 기준선. `node docs/design/prototypes/shotgun-2026-07/runtime-check.mjs` 출력.
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

// ── 판정 계약 구현 ───────────────────────────────────────────────────────────
// 위 계약을 **한 곳**에 둔다. 다크 17벌과 라이트 2벌이 같은 계약을 쓰는지 사람이 두 블록을
// 눈으로 대조해야 하면, 한쪽만 조용히 느슨해져도 안 보인다.

/** 하드 실패로 세는 축 5종. 코어 `hardFailCount()` 의 항과 1:1 이다. */
function hardFailAxes(res: CanonAuditResult): Record<string, number> {
  return {
    overflow: res.overflow.length,
    contrast: res.contrast.length,
    focus: res.focus.length,
    motion: res.motion.length,
    console: res.console.length,
  };
}

const NO_HARD_FAIL: Readonly<Record<string, number>> = {
  overflow: 0,
  contrast: 0,
  focus: 0,
  motion: 0,
  console: 0,
};

/** 이 spec 의 판정 계약 전문. 다크·라이트 두 블록이 같은 함수를 부른다. */
function assertCalibrationContract(
  file: string,
  res: CanonAuditResult,
  expectedCanon: number,
): void {
  const report = formatCanonResult(res);

  // ① 도달 — 「0 건」이 「안 재서 없다」가 아님을 먼저 증명한다.
  //    폭·status·서브리소스 실패를 한 배열로 비교하면 폭이 빠진 것도 같이 잡힌다.
  expect(
    res.probes.map((p) => `${p.w}px:${p.status}:${p.subresourceFail}`),
    `${file}: 4폭 전부를 status 200 · 로컬 서브리소스 실패 0 으로 돌지 못했다:\n${report}`,
  ).toEqual(CANON_WIDTHS.map((w) => `${w}px:200:0`));

  expect(
    minExamined(res),
    `${file}: 어느 폭에서 텍스트를 한 건도 재지 못했다:\n${report}`,
  ).toBeGreaterThan(0);

  // 봉인이 실제로 걸렸는가. `subresourceFail=0` 만으로는 「봉인돼서 0」과 「그 순간 CDN 이
  // 멀쩡해서 0」이 구분되지 않는다 — 후자라면 계약이 다시 제3자에 매인 것이고, 이 spec 을
  // 플레이크로 만든 상태가 그대로 돌아온다.
  expect(
    res.probes.map((p) => p.sealed > 0),
    `${file}: 원격 봉인이 안 걸린 폭이 있다 (hermetic 계약 파손):\n${report}`,
  ).toEqual(CANON_WIDTHS.map(() => true));

  // ② 하드 실패 0 — 축 분해와 코어 총합을 **둘 다** 본다. 분해는 「어느 축인가」를 말하고,
  //    총합은 코어가 6번째 축을 추가했을 때 이 spec 이 조용히 낡는 것을 막는다.
  expect(
    hardFailAxes(res),
    `${file} 이 하드 실패했다. runtime-check.mjs 는 PASS 였으므로 이식된 감사 코어가 틀렸다:\n${report}`,
  ).toEqual(NO_HARD_FAIL);

  expect(
    hardFailCount(res),
    `${file}: 코어 하드 실패 총합이 0 이 아니다. 위 축 분해가 초록인데 여기가 red 면 코어에 새 축이 생긴 것이다:\n${report}`,
  ).toBe(0);

  // ③ canon 은 하드 실패가 아니라 지표다 — 기준선과 **정확히 일치**만 본다.
  expect(
    res.canon.length,
    `${file} canon 카운트가 기준선과 다르다. 프로토타입이 바뀌었는지 감사 코어가 틀어졌는지 먼저 판별하라:\n${report}`,
  ).toBe(expectedCanon);
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
    expect(found.length, `화면 파일 수가 17이 아니다. 발견: ${found.join(", ")}`).toBe(17);
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

      assertCalibrationContract(file, res, expectedCanon);
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

      // 라이트 2벌도 **같은 계약**이다. 종전에는 여기 단언이 다크와 따로 적혀 있어
      // 메시지가 더 얇았고, 한쪽만 손대면 갈라질 수 있었다.
      assertCalibrationContract(file, res, expectedCanon);
    });
  }
});
