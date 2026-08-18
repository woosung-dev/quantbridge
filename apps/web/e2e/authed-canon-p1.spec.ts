// P1 4라우트의 디자인 캐논 baseline 측정 + 래칫 (이식 seam #1, 로컬 전용)
//
// `design-canon-audit.ts` 를 React 앱에 조준한다. 캘리브레이션(`design-canon-calibration`)이
// 같은 코어를 프로토타입 17벌에서 17/17 재현했으므로, 여기서 잡히는 것은 감사 코어의 흠이
// 아니라 앱의 현재 상태다.
//
// ★왜 `chromium-authed` 인가 (그리고 왜 이름이 design-canon-* 이 아닌가).
// P1 4라우트는 전부 로그인 뒤 화면이라 CI 에서 못 돈다. 파일명을 `design-canon-*` 로 하면
// `chromium-design-canon`(CI·무인증) 프로젝트가 매치해 sign-in 리다이렉트로 실패한다.
// 그래서 `authed-canon-p1` 로 두고 `chromium-authed`(storageState + setup 의존, 로컬
// `pnpm e2e:authed` 전용)에 배선한다.
//
// baseline 은 이식 전(pre-C) UI 의 상태다. S5~S8 이 라우트를 하나씩 다시 그리며 아래
// allowlist 를 줄인다. canon 은 하드 실패가 아니라 지표다 (audit 코어 주석 참조).
//
// ★측정 조건은 이제 **주석이 아니라 단정**이다 (아래 DATA_PRECONDITION).
//   종전에는 조건을 여기 적어 두기만 했고 아무도 확인하지 않았다. 그래서 데이터가 비면
//   `hardFailCount` 가 **렌더된 것**의 소견만 세므로 표가 통째로 사라져도 `0 ≤ 0` 이었다.
//   `/backtests/:id/trades` 만 `test.skip` 으로 노랗게 넘어갔고 나머지 셋은 **초록**이었다.
//   ⇒ 감사 커버리지가 조용히 증발하는 자리다.
//
// ★2026-08-10 실측으로 갱신. 종전 주석의 「/backtests 6건(완료 3·실패 3)」은 이미 거짓이었다
//   (실측 7건 전건 완료 · 실패 0 · 체결 3,233). 그래서 **개수를 동결하지 않는다** — 세는 것은
//   「있는가」이지 「몇 개인가」가 아니다. 개수는 시드마다 움직이고, 움직일 때마다 이 주석이
//   다시 거짓이 된다.
//   /dashboard 는 여전히 활성 세션 0(빈 코크핏)이라 데이터 전제를 걸지 않는다.

import { existsSync } from "node:fs";
import { resolve } from "node:path";

import { expect, test, type Browser } from "@playwright/test";

import { getBaseURL } from "./_base-url";
import { assertAuthedReachability } from "./authed-reachability-assert";
import { auditUrl, formatCanonResult, hardFailCount, minExamined } from "./design-canon-audit";

const BASE_URL = getBaseURL();
const STORAGE_STATE = resolve(__dirname, ".auth/storageState.json");

/**
 * 백엔드 부재/개발키에서 나오는 콘솔 소음은 캐논 위반이 아니다. 단 BL-421 이후
 * 4xx 브로드 패턴은 제거 — 404 는 어떤 형태로도 허용하지 않는다 (`live-smoke.spec.ts`
 * 의 공개 전용 필터보다 좁다). 기동 안 한 채 돌려도 앱 결함만 남게 한다.
 */
const EXPECTED_CONSOLE = [
  /failed to fetch/i,
  /networkerror/i,
  /failed to load resource.*\b40[13]\b/i,
  // 리소스 로드 429(레이트리밋)만 무시한다 — 연속 4폭 감사가 백엔드를 치면 나는 스위트 환경
  // 아티팩트다. 이 필터는 pageerror 에도 적용되므로(design-canon-audit.ts), 렌더 예외 속 429 를
  // 삼키지 않도록 "Failed to load resource … 429" 콘솔 메시지에만 좁힌다.
  /failed to load resource.*429/i,
  // ★★**그 밖의 5xx 는 더 이상 무시하지 않는다** ([BL-807], 2026-08-18). 종전의 맨 `/\b50[0-9]\b/` 는
  //   ⑴ 앵커가 없어 **본문의 아무 세 자리 50x 숫자**까지 삼켰고 ⑵ 바로 위 4xx 필터가
  //   `failed to load resource.*` 로 좁혀져 있는 것과 **비대칭**이었으며 ⑶ 무엇보다 BE 500 은
  //   「백엔드 부재 소음」이 아니라 **앱 결함**이다. 부재는 위의 `failed to fetch`·`networkerror`
  //   가 이미 덮는다. 이 필터 때문에 「행은 DB 에 있는데 화면이 빈다」가 세 케이스에서
  //   **원인이 안 보인 채** 반복됐다 — 실제 원인은 상세 API 의 500 이었다.
  /development keys/i,
  /\[fast refresh\]/i,
  /access to fetch/i, // CORS 차단 (백엔드 origin 미일치 시)
];
/**
 * 거래소 **포지션 조회의 503 만** 좁게 면제한다 (2026-08-19 CI 실측, [BL-807]).
 *
 * CI 러너에는 실제 거래소 연결이 없어 `GET /api/v1/exchange-accounts/{id}/positions` 가 CCXT
 * 실패로 503 을 낸다 — BE 의 **정직한 동작**이고 앱 결함이 아니다. 하드 실패로 세면 `/trading`
 * 캐논은 거래소 없이 영영 CI 에서 못 돈다.
 *
 * ★★**첫 판은 발화조차 못 했다.** 콘솔 원문 하나만 보는 정규식에 URL 조각을 적어 넣었는데,
 *   `ignoreConsole` 이 받는 것은 **브라우저 원문**이고 리포트의 `<- <url>` 은 그 뒤에 붙는다.
 *   내 국소 검사는 리포트 문자열을 먹여 true 였다 — **실제 경로가 지나지 않는 검사**였다.
 *   ⇒ 출처 URL 을 **둘째 인자로** 받아 판정한다. 텍스트의 503 과 URL 의 엔드포인트가
 *   **둘 다** 맞을 때만 면제되므로 사거리가 원문 밖으로 새지 않는다.
 */
const EXCHANGE_POSITIONS_PATH = /\/exchange-accounts\/[^/]+\/positions(?:\?|$)/;
const isExchangePositions503 = (text: string, originUrl?: string) =>
  /\b503\b/.test(text) && originUrl !== undefined && EXCHANGE_POSITIONS_PATH.test(originUrl);

const ignoreConsole = (t: string, originUrl?: string) =>
  EXPECTED_CONSOLE.some((re) => re.test(t)) || isExchangePositions503(t, originUrl);

/**
 * P1 4라우트 하드 실패 allowlist (2026-07-20 실측 baseline). S5~S8 이 줄인다.
 * nextjs-portal(dev 오버레이) 제외 후 남은 실제 앱 결함만이다.
 *   - /dashboard 0 — 깨끗.
 *   - /backtests 0 — S5 C 이식 완료. 375px 가로 오버플로는 .table-wrap 스크롤 컨테이너가
 *     해소한다(표는 컨테이너 안에서 스크롤, 페이지 본문은 넘치지 않는다).
 *   - /backtests/:id/trades 0 — S6 C 이식 완료. 검색·기간 시작·기간 종료 입력이 공용
 *     .input 스타일을 소비하며 :focus-visible 카퍼 링을 받는다(outline-none 제거).
 *   - /trading 0 — S8 C 이식 완료. base-ui 탭(outline-none 인 포커스가능 Tabs.Panel div,
 *     내용이 "Kill Switch…")을 번호 섹션 단일 스크롤로 대체해 그 포커스가능 div 를 없앴다.
 *     공용 .btn/.card 만 포커스를 받고 언레이어드 전역 :focus-visible 카퍼 링이 전부 걸린다.
 */
const HARDFAIL_ALLOWLIST: Readonly<Record<string, number>> = {
  "/dashboard": 0,
  "/backtests": 0,
  "/backtests/:id/trades": 0,
  "/trading": 0,
};

const auditOptions = {
  contextOptions: { storageState: STORAGE_STATE },
  ignoreConsole,
} as const;

/**
 * 라우트가 **실제로 무언가를 그리는지** 확인할 선택자.
 *
 * ★없으면 `test.skip` 이 아니라 시끄럽게 실패한다. 잔여 spec(`authed-canon-remaining`)이
 * 같은 함정을 이미 이렇게 막았다 — 패턴이 레포 안에 있었고 이 파일만 안 따라갔다.
 * `/dashboard` 는 활성 세션 0 이 baseline 이라 여기 없다.
 */
const DATA_PRECONDITION: Readonly<Record<string, { selector: string; why: string }>> = {
  "/backtests": {
    selector: 'a[href^="/backtests/"]',
    why: "백테스트 목록이 비었다. 캐논 감사가 볼 표가 없다 (`mise run seed` 로 시딩하라)",
  },
  "/trading": {
    selector: 'table[aria-label^="거래소 계정"] tbody tr',
    why: "등록된 거래소 계정이 없다. /trading 이 빈 상태만 그린다 (`mise run seed`)",
  },
};

/** 감사와 별개 컨텍스트로 한 번 열어 선택자를 센다. 감사 결과에는 DOM 이 없다. */
async function countOn(browser: Browser, url: string, selector: string): Promise<number> {
  const context = await browser.newContext({ storageState: STORAGE_STATE });
  try {
    const page = await context.newPage();
    await page.goto(url, { waitUntil: "load" });
    // ★★고정 1.5초였다 ([BL-807], 2026-08-18). dev 콜드 컴파일 + 세션 왕복 + API 왕복이 그
    //   안에 안 끝나면 「데이터가 없다」와 「아직 안 왔다」가 **같은 0** 으로 보인다. 이 파일의
    //   발견 단계와 형제 spec 은 이미 25초 `waitForSelector` 를 쓰는데 여기만 안 썼다.
    //   ★타임아웃을 삼키는 것은 의도다 — 「몇 행인가」의 판정은 **호출부의 단언**이 진다.
    //     여기서 던지면 0 행과 미도달이 다시 한 덩어리가 된다.
    await page.waitForSelector(selector, { timeout: 20_000 }).catch(() => {});
    return await page.locator(selector).count();
  } finally {
    await context.close();
  }
}

test.describe("P1 4라우트 디자인 캐논 baseline (이식 seam #1, 로컬 전용)", () => {
  // storageState 부재 시 조용한 skip 이 아니라 시끄럽게 실패시킨다(운영계약 §3ⓒ — skip 침묵 통과 방지).
  test("사전조건 — storageState 존재", () => {
    expect(
      existsSync(STORAGE_STATE),
      `storageState 없음 (${STORAGE_STATE}) — chromium-authed-setup 프로젝트를 먼저 실행하라 (pnpm e2e:authed).`,
    ).toBe(true);
  });

  for (const path of ["/dashboard", "/backtests", "/trading"] as const) {
    test(`${path} — 하드 실패 ≤ allowlist`, async ({ browser }) => {
      test.setTimeout(180_000);

      const res = await auditUrl(browser, `${BASE_URL}${path}`, { label: path, ...auditOptions });
      process.stdout.write(formatCanonResult(res) + "\n");
      assertAuthedReachability(res);

      const precondition = DATA_PRECONDITION[path];
      if (precondition) {
        const count = await countOn(browser, `${BASE_URL}${path}`, precondition.selector);
        expect(count, `${path} 데이터 전제 미충족 — ${precondition.why}`).toBeGreaterThan(0);
      }

      // ★「감사를 못 했다」와 「깨끗하다」를 가른다. `hardFailCount` 는 렌더된 것의 소견만
      //   세므로 아무것도 안 그려지면 언제나 0 이다. 코어가 이 값을 내주고 있었는데
      //   이 파일은 로그로만 찍고 아무도 단정하지 않았다.
      expect(
        minExamined(res),
        `${path} — 감사가 본 텍스트 요소가 0개다. 초록이 아니라 미측정이다:\n${formatCanonResult(res)}`,
      ).toBeGreaterThan(0);

      expect(
        hardFailCount(res),
        `${path} 하드 실패:\n${formatCanonResult(res)}`,
      ).toBeLessThanOrEqual(HARDFAIL_ALLOWLIST[path] ?? 0);
    });
  }

  test("/backtests/:id/trades — 하드 실패 ≤ allowlist", async ({ browser }) => {
    test.setTimeout(180_000);

    // backtest id 를 하드코딩하지 않는다 (환경마다 다르다). /backtests 에서 런타임 발견.
    const discovery = await browser.newContext({ storageState: STORAGE_STATE });
    const dpage = await discovery.newPage();
    await dpage.goto(`${BASE_URL}/backtests`, { waitUntil: "load" });
    // ★고정 대기 → 셀렉터 대기 ([BL-807]). 부재 판정은 아래 `expect(href).toBeTruthy()` 가 진다.
    await dpage.waitForSelector('a[href^="/backtests/"]', { timeout: 25_000 }).catch(() => {});
    const href = await dpage.locator('a[href^="/backtests/"]').evaluateAll((els) => {
      const re = /^\/backtests\/[0-9a-f-]{36}$/;
      const found = (els as HTMLAnchorElement[]).find((a) => re.test(new URL(a.href).pathname));
      return found ? new URL(found.href).pathname : null;
    });
    await discovery.close();

    // ★종전에는 `test.skip` 이었다. 데이터가 없으면 노랗게 넘어갔고, 그 순간 이 라우트의
    //   캐논 커버리지는 0 인데 스위트는 실패를 보고하지 않았다.
    expect(
      href,
      "완료된 백테스트 상세 링크를 찾지 못했다 — 캐논 감사가 볼 원장이 없다 (`mise run seed`)",
    ).toBeTruthy();

    // 상세가 있어도 체결이 0행이면 원장 표가 그려지지 않는다. 링크 존재만으로는 부족하다.
    const tradeRows = await countOn(
      browser,
      `${BASE_URL}${href}/trades`,
      '[data-testid="trade-detail-table"] tbody tr',
    );
    expect(tradeRows, `${href}/trades 에 체결 행이 없다 — 표가 통째로 비어 있다`).toBeGreaterThan(
      0,
    );

    const res = await auditUrl(browser, `${BASE_URL}${href}/trades`, {
      label: `${href}/trades`,
      ...auditOptions,
    });
    process.stdout.write(formatCanonResult(res) + "\n");
    assertAuthedReachability(res);
    expect(
      minExamined(res),
      `/trades — 감사가 본 텍스트 요소가 0개다. 초록이 아니라 미측정이다:\n${formatCanonResult(res)}`,
    ).toBeGreaterThan(0);
    expect(hardFailCount(res), `/trades 하드 실패:\n${formatCanonResult(res)}`).toBeLessThanOrEqual(
      HARDFAIL_ALLOWLIST["/backtests/:id/trades"] ?? 0,
    );
  });
});
