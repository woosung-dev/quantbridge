// [BL-797] 화면 증거 팩 — 측정 본체. 공개/authed 두 spec 이 **같은 함수**를 부른다.
//
// ★왜 spec 이 아니라 여기 있나. 2026-08-18 에 authed 라우트를 붙이면서 spec 이 둘로 갈렸다
//   (공개는 `setup-identity` 만, authed 는 `setup-authed-reachability` + storageState 를 물어야
//   해서 playwright project 를 나눠야 했다). 측정 본문을 각 spec 에 베끼면 두 벌이 따로 늙는다 —
//   이 레포가 `_base-url.ts` 사본 5벌로 이미 겪은 병이다. 라우트 목록만 다르고 재는 방법은 하나다.
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import path from "node:path";

import { expect, test, type Response } from "@playwright/test";

import {
  BASELINE_PATH,
  evidenceRunDir,
  MEASURED_DIR_NAME,
  type RouteCase,
  type RouteMetrics,
} from "./screen-evidence-shared";

/**
 * 측정 창 — `networkidle`(500ms 무통신) 이후 여유.
 * ★`api-request-dedup.spec.ts` 와 같은 값이다. 이 화면들의 가장 빠른 폴링이 5초라
 *   정상 폴링이 창 안에 들어와 요청 수를 부풀리지 않는다.
 */
const SETTLE_MS = 1_000;

const API_MARKER = "/api/v1/";
/** first-load 번들로 세는 정적 자산. 폰트(woff2)는 뺀다 — 서브셋 개수가 텍스트에 따라 변한다. */
const BUNDLE_ASSET = /\/_next\/static\/.+\.(?:js|css)(?:\?|$)/;

/**
 * ★★**스크린샷 비교 손잡이 — 값의 근거 (AC-2).**
 *
 * `threshold`(픽셀 하나의 YIQ 색차 허용치)는 playwright 기본값 0.2 를 그대로 쓴다. 이것이
 * 안티앨리어싱을 흡수하는 1차 방어선이고, 여기서 걸러진 픽셀은 아래 개수에 아예 안 센다.
 *
 * `maxDiffPixels` 는 **비율이 아니라 절대 개수**여야 한다. 비율로 잡으면 AC-2 양성이 새기
 * 때문이다 — fullPage 스크린샷이 1280×~2000 = 약 256만 픽셀인데, 14px 글자 한 자가 바뀌면
 * 달라지는 픽셀은 100 안팎이라 비율로는 4e-5 다. 흔히 쓰는 `maxDiffPixelRatio: 0.001` 은
 * 2,560 픽셀을 허용하므로 **글자 한 자 변경을 통째로 삼킨다.** 그래서 절대 개수로 잡는다.
 *
 * 값 0 의 근거: 같은 코드로 연속 2회 캡처했을 때 실측 차이가 **0 픽셀**이었다(A-REPORT 의
 * 재현 표 참조 — 프로덕션 빌드라 폰트·애니메이션이 고정된다). 0 보다 크게 잡을 이유가
 * 실측에 없었다. ★흔들리기 시작하면 **값을 올리기 전에 무엇이 흔들리는지 먼저 찾아라** —
 * 임계값을 올리는 것은 판별력을 파는 것이고, 이 게이트는 그것 하나로 존재 이유가 사라진다.
 *
 * ★★authed 라우트가 이 축을 **안 쓰는** 이유가 정확히 그것이다 — 실데이터(시각·가격)가
 *   매 실행 픽셀을 흔드므로 0 을 유지할 수 없고, 값을 올리면 게이트가 아무것도 못 잡는다.
 *   그래서 authed 는 `slug: null`(수치 전용)로 두고 번들·요청 수만 잰다([BL-797]).
 */
const SCREENSHOT_OPTIONS = {
  fullPage: true,
  animations: "disabled",
  caret: "hide",
  maxDiffPixels: 0,
} as const;

const UPDATE = process.env.SCREEN_EVIDENCE_UPDATE === "1";

function readBaseline(): Record<string, RouteMetrics> {
  if (!existsSync(BASELINE_PATH)) return {};
  const parsed = JSON.parse(readFileSync(BASELINE_PATH, "utf8")) as {
    routes?: Record<string, RouteMetrics>;
  };
  return parsed.routes ?? {};
}

/** 라우트 목록 하나를 measure→대조 테스트로 등록한다. spec 파일은 목록만 넘긴다. */
export function registerScreenEvidenceTests(title: string, routes: readonly RouteCase[]): void {
  test.describe(title, () => {
    for (const route of routes) {
      test(`${route.path} — ${route.slug === null ? "번들·요청 수" : "화면·번들·요청 수"}를 재고 baseline 과 대조한다`, async ({
        page,
      }) => {
        test.setTimeout(120_000);

        // ★**수치 전용은 authed 에만 허용한다** (codex 적대 리뷰 P2, 2026-08-19). 둘이 안 묶여
        //   있으면 공개 라우트의 `slug` 가 실수로 `null` 이 된 채 `:update` 를 돌렸을 때
        //   스냅샷 baseline 이 `null` 로 바뀌고, 그 뒤 그 화면의 **픽셀 회귀가 통째로
        //   「—(수치 전용)」으로 처리**된다. 화면 축이 조용히 사라지는 그 경로를 여기서 막는다.
        expect(
          route.authed === true || route.slug !== null,
          `${route.path}: 공개 라우트인데 \`slug: null\`(수치 전용)이다. 화면 축이 통째로 빠진다 — ` +
            "실데이터가 픽셀을 흔드는 authed 라우트에만 허용된다.",
        ).toBe(true);

        let capturing = true;
        let apiRequests = 0;
        let totalRequests = 0;
        const failedResponses: string[] = [];
        const bundleResponses: Response[] = [];

        // ★계수 방식은 `api-request-dedup.spec.ts` 를 그대로 재사용한다 — 새로 발명하지 않는다.
        // ★★전체 요청 수를 **같이** 센다. 이유는 둘이다.
        //   ⑴ 판별력 — 공개 라우트는 `/api/v1/` 요청이 실측 **0건**이라(2026-08-17) API 축만 두면
        //      계수기를 통째로 떼어내도 `0 == 0` 으로 초록이다. 이 레포가 소크 게이트 C4 와
        //      `tool-pin-audit` 에서 두 번 밟은 「볼 것이 없으면 통과」가 그대로 재현된다.
        //   ⑵ 전체 요청 수 자체가 화면의 대가다 — 폰트 서브셋·이미지·chunk 가 늘면 여기서 보인다.
        page.on("request", (req) => {
          if (!capturing) return;
          totalRequests += 1;
          if (req.url().includes(API_MARKER)) apiRequests += 1;
        });

        // ★핸들러는 **동기**로 둔다. 안에서 await 하면 그 이어지는 부분이 `capturing = false`
        //   **뒤에** 돌 수 있고, 그러면 측정 창 밖의 응답이 바이트에 섞인다.
        //   크기는 창을 닫은 뒤 한꺼번에 센다.
        page.on("response", (res) => {
          if (!capturing) return;
          const url = res.url();
          // ★[BL-786] 의 성질을 버리지 않는다 — 실패 응답은 「중복」도 「변화」도 아니라 **측정 오염**이다.
          //   React Query 의 재시도가 요청 수를 부풀리고, 실패한 자산은 바이트에서 통째로 빠진다.
          if (res.status() >= 400 && (url.includes(API_MARKER) || BUNDLE_ASSET.test(url)))
            failedResponses.push(`${res.status()} ${res.request().method()} ${url}`);
          else if (BUNDLE_ASSET.test(url)) bundleResponses.push(res);
        });

        await page.goto(route.path, { timeout: 60_000 });
        await page.waitForLoadState("networkidle", { timeout: 60_000 });
        await page.waitForTimeout(SETTLE_MS);
        capturing = false;

        // ★`content-length` 는 못 쓴다 — Next 는 `compress: true` 라 정적 자산을 gzip 청크로
        //   보내고 그때 그 헤더가 아예 안 붙는다(2026-08-17 실측: 자산 13/13 전부 없음).
        //   `request().sizes().responseBodySize` 는 **회선을 지난 바이트**라 압축 후 크기이고,
        //   같은 입력·같은 zlib 설정이면 실행마다 같다. 이것이 「사용자가 받는 양」의 정본이다.
        const sizes = await Promise.all(bundleResponses.map((res) => res.request().sizes()));
        const firstLoadBytes = sizes.reduce((sum, s) => sum + s.responseBodySize, 0);
        const zeroSized = sizes
          .map((s, i) => (s.responseBodySize > 0 ? null : bundleResponses[i]?.url()))
          .filter((u): u is string => u !== null);

        // ⑴ 측정 오염 — 중복·변화 판정보다 **먼저** 온다. 사람이 다음에 할 일이 다르다.
        expect(
          failedResponses,
          `${route.path}: 측정 창 안에서 실패 응답이 났다 — 요청 수와 번들 바이트를 신뢰할 수 없다.\n` +
            `이것은 「화면이 달라졌다」가 아니라 **측정 오염**이다.\n${failedResponses.join("\n")}`,
        ).toEqual([]);

        // ⑵ 계측기가 실제로 무언가를 봤다. **0 을 「가벼워졌다」로 인쇄하지 않는다.**
        expect(
          await page.title(),
          `${route.path}: 앵커(\`${route.anchor}\`)가 제목에 없다 — 이 실행은 그 화면을 그리지 못했다.`,
        ).toContain(route.anchor);

        // ⑵-a authed 전용 앵커 둘. ★제목만으로는 로그인 실패를 못 가린다 — `/sign-in` 도
        //     제목에 "QuantBridge" 를 달고, 세션이 없으면 `proxy.ts` 가 거기로 튕긴다.
        if (route.authed) {
          expect(
            new URL(page.url()).pathname,
            `${route.path}: 로그인 상태가 아니다 — \`${page.url()}\` 로 튕겼다. ` +
              "storageState 가 없거나 만료됐다(setup project 를 먼저 돌려라).",
          ).toBe(route.path);
          expect(
            apiRequests,
            `${route.path}: \`/api/v1/\` 요청이 0건이다. 데이터 화면이 API 를 한 번도 안 부를 수 없다 — ` +
              "빈 상태만 그렸거나(BE 부재·데이터 없음) 계수기가 죽었다. **authed 쪽 계수기 생존 앵커다.**",
          ).toBeGreaterThan(0);
        }

        expect(
          firstLoadBytes,
          `${route.path}: first-load 자산 바이트가 0 이다. Next 라우트가 JS 0 바이트일 수 없다 — ` +
            `계측기가 응답을 못 봤거나(\`page.on("response")\` 가 떨어졌다) 자산 패턴이 안 맞는다.`,
        ).toBeGreaterThan(0);
        expect(
          zeroSized,
          `${route.path}: 전송 바이트가 0 인 자산이 있다 — 캐시 적중이거나 크기를 못 읽었다. ` +
            `그 자산의 무게가 표에서 통째로 빠진다.\n${zeroSized.join("\n")}`,
        ).toEqual([]);
        expect(
          bundleResponses.length,
          `${route.path}: \`/_next/static/**.{js,css}\` 응답을 한 건도 못 봤다 — 자산 패턴이 안 맞거나 계측기가 떨어졌다.`,
        ).toBeGreaterThan(0);
        // ★요청 계수기의 생존 앵커. 이것이 없으면 `page.on("request")` 를 떼도 API 축이 0→0 이라 초록이다.
        expect(
          totalRequests,
          `${route.path}: 요청을 한 건도 못 셌다 — \`page.on("request")\` 가 안 붙었거나 측정 창이 닫힌 뒤 열렸다. ` +
            "요청 수 0 은 「가벼운 화면」이 아니라 **계측 실패**다.",
        ).toBeGreaterThan(0);

        // ⑶ 화면 — 커밋된 baseline PNG 와 대조. `--update-snapshots` 가 갱신한다.
        // ★★`expect.soft` 다. 세 축(화면·번들·요청)은 **서로 독립된 증거**인데 hard 로 두면
        //   화면이 걸리는 순간 뒤의 수치 대조가 실행조차 안 돼서, 사람은 red 를 한 번 받고
        //   고친 뒤 다음 축의 red 를 또 받는다. 어차피 rc 는 같으므로 한 번에 다 보여준다.
        //   ★위 ⑴⑵ 는 hard 로 둔다 — 그것들은 「측정이 실패했다」라서 이어서 재 봐야 쓰레기다.
        if (route.slug !== null) {
          await expect.soft(page).toHaveScreenshot(`${route.slug}.png`, SCREENSHOT_OPTIONS);
        }

        // ⑷ 측정값을 파일로 남긴다. 오케스트레이터가 이것으로 baseline JSON 을 만든다.
        const measuredDir = path.join(evidenceRunDir(), MEASURED_DIR_NAME);
        mkdirSync(measuredDir, { recursive: true });
        // ★★authed 라우트의 요청 수는 **대조에서 뺀다**(`null`). 2026-08-18 실측 — 같은 커밋·같은
        //   빌드로 연속 2회 재면 `/backtests` 5→4 · `/optimizer` 5→6 으로 흔들렸고, 같은 실행에서
        //   `firstLoadBytes` 는 **비트 단위로 같았다**. 원장이 「번들 + 요청 수」로 적은 authed 축은
        //   실측상 **번들만** 성립한다. ★위 ⑵-a 의 `> 0` 앵커는 그대로 남으므로 「계수기가 죽었다」는
        //   여전히 잡힌다 — 버리는 것은 「정확한 수」의 대조뿐이다.
        const volatileCounts = route.authed === true;
        const measured: RouteMetrics = {
          firstLoadBytes,
          apiRequests: volatileCounts ? null : apiRequests,
          totalRequests: volatileCounts ? null : totalRequests,
          screenshot: route.slug === null ? null : `${route.slug}.png`,
          ...(route.authed ? { authed: true } : {}),
        };
        // ★파일 이름은 slug 가 아니라 **경로에서 파생**한다 — 수치 전용 라우트에는 slug 가 없다.
        const fileStem =
          route.path.replace(/[^A-Za-z0-9._-]/g, "-").replace(/^-+|-+$/g, "") || "root";
        writeFileSync(
          path.join(measuredDir, `${fileStem}.json`),
          `${JSON.stringify({ path: route.path, ...measured }, null, 2)}\n`,
          "utf8",
        );

        // ⑸ baseline 대조. 갱신 모드에서는 건너뛴다 — 그때는 이 값이 곧 새 baseline 이다.
        if (UPDATE) return;
        const baseline = readBaseline()[route.path];
        expect(
          baseline,
          `${route.path}: baseline 에 이 라우트가 없다. \`pnpm screen-evidence:update\` 로 만들어라.`,
        ).toBeTruthy();
        expect
          .soft(
            {
              firstLoadBytes,
              apiRequests: volatileCounts ? null : apiRequests,
              totalRequests: volatileCounts ? null : totalRequests,
            },
            `${route.path}: 측정값이 커밋된 baseline 과 다르다.\n` +
              `  first-load  ${baseline?.firstLoadBytes} → ${firstLoadBytes} 바이트\n` +
              (volatileCounts
                ? `  API 요청     ${apiRequests} 건 · 전체 요청 ${totalRequests} 건 (★대조 제외 — 실측상 비결정)\n`
                : `  API 요청     ${baseline?.apiRequests} → ${apiRequests} 건\n` +
                  `  전체 요청    ${baseline?.totalRequests} → ${totalRequests} 건\n`) +
              "화면을 의도적으로 바꿨다면 `pnpm screen-evidence:update` 로 baseline 을 갱신해라 — " +
              "그 갱신분이 곧 PR 이 인쇄할 **after** 다.",
          )
          .toEqual({
            firstLoadBytes: baseline?.firstLoadBytes,
            apiRequests: baseline?.apiRequests ?? null,
            totalRequests: baseline?.totalRequests ?? null,
          });
      });
    }
  });
}
