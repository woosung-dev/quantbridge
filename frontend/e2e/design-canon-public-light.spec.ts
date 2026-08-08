// 공개 라우트의 **라이트 테마** 런타임 캐논 감사 ([BL-648])
//
// ★왜 별도 파일인가 (처방 ②).
// 종전에 런타임 캐논 감사는 라이트를 **한 번도** 재지 않았다. `design-canon-audit.ts` 가
// 테마를 강제하지 않고 `app-providers.tsx` 가 `defaultTheme="dark"` 라 4폭이 전부 다크에서
// 돌았다. 그래서 [BL-628](라이트 `--warning` 이 `--warning-subtle` 위에서 5.66)이 등재만 되고
// **어떤 게이트도 물지 않은 채** 배포됐고, 그 앞에는 라이트 AA 하드 실패 116건이 같은
// 구멍으로 공개 4라우트에 나갔다.
//
// 대안 ①(감사 컨텍스트를 테마별 2벌로 돌린다)은 실측으로 기각했다.
//   - `design-canon-calibration.spec.ts` 는 **정적 프로토타입 HTML**(next-themes 없음)을
//     감사하고 다크 정본에서 뜬 canon 카운트 17벌을 **정확히 일치**로 동결한다. 거기에
//     라이트를 얹으면 잴 대상도 없고 그 계약이 깨진다.
//   - `authed-canon-*` 2벌은 `chromium-authed` 몫이고 소크 상태에 결합된다([BL-597]).
//   ⇒ 테마 2벌이 의미를 갖는 대상은 **공개 라우트뿐**이므로 그 범위에만 세운다.
// ②의 위험이던 "감사 로직이 갈린다" 는 코어를 복제하지 않고 `theme` 옵션 하나로
// 매개변수화해 없앴다 — 다크와 라이트는 같은 자를 쓴다.
//
// ★이 파일이 사는 것은 `src/__tests__/light-canon-contrast.test.ts` 가 **못 재는 것**이다.
// 그쪽은 커밋된 토큰값의 순수 계산이라 불투명 hex 짝만 본다. 여기는 실화면 합성이라
// 알파 표면·중첩 레이어·실제 마크업이 만든 조합을 잰다.

import { expect, test } from "@playwright/test";

import {
  auditStatuses,
  auditUrl,
  formatCanonResult,
  hardFailCount,
  minExamined,
  worstCanonRatio,
} from "./design-canon-audit";

const BASE_URL = process.env.PLAYWRIGHT_BASE_URL ?? "http://localhost:3000";

/** 백엔드 부재/개발키 콘솔 소음 필터. `design-canon-public.spec.ts` 와 같은 목록. */
const EXPECTED_CONSOLE = [
  /failed to fetch/i,
  /networkerror/i,
  /net::err_/i,
  /\b40[0-9]\b/,
  /\b50[0-9]\b/,
  /clerk has been loaded/i,
  /development keys/i,
  /\[fast refresh\]/i,
  /access to fetch/i,
];
const ignoreConsole = (t: string) => EXPECTED_CONSOLE.some((re) => re.test(t));

/** 라이트에서 실제로 렌더된 `--bg`. `globals.css :root` 의 `#f4f5f6`. */
const LIGHT_BODY_BG = "rgb(244, 245, 246)";

/**
 * 라우트별 [하드 실패 상한, canon 상한].
 *
 * ★**canon 을 게이트하는 것이 이 파일의 요점이다.** 다크 짝(`design-canon-public.spec.ts`)은
 *   하드 실패만 보고 canon 은 세기만 한다. 그런데 [BL-628] 은 AA(4.5)를 통과하고 캐논(5.82)만
 *   미달인 값이라 **하드 실패 게이트로는 원리상 안 잡힌다** — 실제로 안 잡혔다.
 *   그래서 라이트에서는 canon 을 래칫(현 실측값 고정)으로 건다.
 *   숫자를 올리려면 화면이 나빠졌다는 뜻이므로 근거를 남기고 올려라.
 *
 * 하드 실패는 **5라우트 전부 0** 이라 다크 짝과 같은 상한을 쓴다. canon 잔량은 전부
 * `--text-muted`(#585f68) 가 `--card`/`--bg` 가 **아닌** 표면 위에서 5.60~5.64 로 앉은 것이다.
 *   ★**실측 출처는 아래 `LIGHT_BASELINE` 주석 한 곳뿐이다** — 여기 있던 「dev 3110 ·
 *     1440·375 표본」은 초안 시절 값이라 **거짓**이었다(2026-08-08 `/code-review` 지적).
 *     이 파일의 본 검사는 `auditUrl` 에 `widths` 를 안 주므로 언제나 `CANON_WIDTHS`
 *     **4폭**(1440/1024/768/375)이다. 2폭짜리 래칫 숫자는 이 파일에 없다.
 *   ★이 조합은 `light-canon-contrast.test.ts` 의 PAIRS 에 없다 — 그 파일은
 *     `--text-muted × [--card, --bg]`(6.35/5.92) 만 세므로 **계산으로는 안 보인다.**
 *     실화면 합성이 무엇을 더 잡는지의 실례이고, 토큰을 옮길 일이라 별건([BL-628] 계열)이다.
 */
interface LightLimits {
  /** 하드 실패 상한. */
  hardFail: number;
  /** canon 소견 **개수** 상한(래칫). */
  canon: number;
  /**
   * canon 소견 중 **최악(최저) 대비**의 하한(래칫).
   *
   * ★**개수와는 다른 축이다.** dedupe 키가 `color|round(size)|txt[0:20]` 이라 하나가 사라지고
   *   다른 하나가 생기면 개수는 그대로인데 최악값만 나빠질 수 있다. 그 악화를 개수 래칫은
   *   원리상 못 본다(2026-08-08 codex 평가 지적).
   * ★**여유를 두지 않았다** — 현 실측값 그대로다. 여유를 두면 그만큼이 조용히 나빠질 수 있고
   *   그러면 래칫의 뜻이 사라진다. 값이 dedupe 로 안정적이고 뷰포트·모션이 고정돼 있어
   *   재현된다(`reducedMotion: "reduce"` + 고정 4폭).
   * canon 이 비는 라우트는 `null`.
   */
  minContrast: number | null;
  /**
   * 이 라우트가 내야 하는 HTTP status.
   * ★2xx 를 코어에 박지 않은 이유가 여기 있다 — `/qb-canon-404-probe` 는 **404 가 정상**이고
   *   `/maintenance` 는 점검 화면이다. 기대값은 대상마다 다르므로 대상을 아는 이 표가 든다.
   */
  status: number;
  /**
   * 감사가 **최소한 이만큼은 봐야 한다**(모든 폭에서). 빈 DOM·라우트 소멸이 "소견 0" 으로
   * 초록이 되는 fail-open 을 막는 하한이다.
   * ★상한이 아니라 하한이므로 실측치에 **여유를 아래로** 둔다 — 콘텐츠가 늘면 통과해야 하고,
   *   줄어드는 방향만 잡으면 된다. 실측치 자체를 박으면 문구 한 줄 추가에도 red 가 된다.
   */
  minElements: number;
}

/**
 * ★**이 파일의 유일한 실측 출처다.** 2026-08-08, dev 서버 `:3100`, 라이트, `CANON_WIDTHS`
 * **4폭**(1440/1024/768/375 — `auditUrl` 기본값). `minContrast` 는 **그대로**, `minElements` 는
 * 실측치의 약 2/3 로 내려 잡았다(문구 한 줄 추가로 red 가 되면 안 되므로).
 *
 * | 라우트                | status | minExamined 실측 | worstCanon 실측 |
 * | --------------------- | ------ | ---------------- | --------------- |
 * | `/`                   | 200    | 149              | 5.60            |
 * | `/waitlist`           | 200    | 106              | 5.60            |
 * | `/pricing`            | 200    | 165              | 5.60            |
 * | `/maintenance`        | 200    | 30               | 5.60            |
 * | `/qb-canon-404-probe` | 404    | 29               | 5.60            |
 *
 * ★`/maintenance` 는 **200 이다** — "503 점검 화면" 은 화면의 뜻이지 응답 코드가 아니다.
 *   추정으로 503 을 박았으면 이 파일이 거짓 red 로 시작했다. 그래서 재고 적었다.
 * ★두 하한이 서로를 보강한다 — 라우트가 통째로 not-found 로 바뀌면 `status` 가 먼저 잡고,
 *   설령 200 을 유지해도 `/pricing` 하한 110 vs 404 화면 29 라 `minElements` 가 또 잡는다.
 */
const LIGHT_BASELINE: Readonly<Record<string, LightLimits>> = {
  "/": { hardFail: 0, canon: 2, minContrast: 5.6, status: 200, minElements: 100 },
  "/waitlist": { hardFail: 0, canon: 6, minContrast: 5.6, status: 200, minElements: 70 },
  "/pricing": { hardFail: 0, canon: 14, minContrast: 5.6, status: 200, minElements: 110 },
  "/maintenance": { hardFail: 0, canon: 4, minContrast: 5.6, status: 200, minElements: 20 },
  "/qb-canon-404-probe": {
    hardFail: 0,
    canon: 2,
    minContrast: 5.6,
    status: 404,
    minElements: 20,
  },
};

test.describe("공개 라우트 라이트 테마 캐논 ([BL-648])", () => {
  // ── 위생 — 라이트가 정말 도달하는지부터 못 박는다 ──
  //
  // ★`colorScheme: "light"` **단독으로는 테마가 바뀌지 않는다**(2026-08-08 실측).
  //   `defaultTheme="dark"` 라 저장된 선호값이 없으면 next-themes 가 다크로 고정한다.
  //   이 검사가 없으면 아래 5건이 조용히 **다크를 한 번 더 재고도** 전부 초록이 된다.
  test("라이트 테마가 실제로 렌더에 도달한다 (fail-open 차단)", async ({ browser }) => {
    const res = await auditUrl(browser, `${BASE_URL}/`, {
      label: "/ (theme reachability)",
      widths: [1440],
      theme: "light",
      ignoreConsole,
    });
    process.stdout.write(formatCanonResult(res) + "\n");

    expect(res.themeProbe, "themeProbe 가 비었다 — 감사가 테마를 강제하지 않았다").not.toBeNull();
    expect(res.themeProbe?.htmlClass.split(/\s+/)).toContain("light");
    expect(res.themeProbe?.htmlClass.split(/\s+/)).not.toContain("dark");
    expect(
      res.themeProbe?.bodyBg,
      `body 배경이 라이트 --bg 가 아니다. 다크는 rgb(11, 13, 15) 다 — ` +
        `그 값이 보이면 이 파일 전체가 다크를 재고 있는 것이다.`,
    ).toBe(LIGHT_BODY_BG);
  });

  // ── 본 검사 ──
  for (const [path, limits] of Object.entries(LIGHT_BASELINE)) {
    test(`${path} — 라이트 하드 실패 ≤ ${limits.hardFail} · canon ≤ ${limits.canon}`, async ({
      browser,
    }) => {
      test.setTimeout(120_000);
      const res = await auditUrl(browser, `${BASE_URL}${path}`, {
        label: `${path} (light)`,
        theme: "light",
        ignoreConsole,
      });
      process.stdout.write(formatCanonResult(res) + "\n");

      // ── 도달 확인 (fail-open 차단) ────────────────────────────────────────
      // ★★**이 두 단언이 나머지 셋에 의미를 준다.** 없으면 404·500·빈 fallback 을 재도
      //   `hardFail=0 · canon=0` 이라 전부 초록이다 — 화면이 좋아서가 아니라 잴 것이 없어서.
      expect(
        auditStatuses(res),
        `${path} 가 기대한 HTTP ${limits.status} 를 안 냈다 — 라우트가 사라졌거나 서버가 다른 것을 준다:\n${formatCanonResult(res)}`,
      ).toEqual([limits.status]);
      expect(
        minExamined(res),
        `${path} 에서 감사가 본 텍스트 요소가 하한 미만이다 — 빈 DOM 을 재고 "소견 0" 으로 통과할 뻔했다:\n${formatCanonResult(res)}`,
      ).toBeGreaterThanOrEqual(limits.minElements);

      // ── 본 판정 ─────────────────────────────────────────────────────────
      expect(
        hardFailCount(res),
        `${path} 라이트 하드 실패:\n${formatCanonResult(res)}`,
      ).toBeLessThanOrEqual(limits.hardFail);
      expect(
        res.canon.length,
        `${path} 라이트 canon 래칫 초과 — 라이트 대비가 캐논(5.82) 아래로 내려갔다:\n${formatCanonResult(res)}`,
      ).toBeLessThanOrEqual(limits.canon);

      // 개수 래칫이 못 보는 축 — 최악 대비값의 악화.
      const worst = worstCanonRatio(res);
      if (limits.minContrast !== null) {
        expect(
          worst,
          `${path} canon 최악 대비 래칫 — 개수는 상한 안이어도 **가장 나쁜 값**이 내려갔다:\n${formatCanonResult(res)}`,
        ).not.toBeNull();
        expect(
          worst ?? 0,
          `${path} canon 최악 대비 ${worst} 가 래칫 ${limits.minContrast} 아래다:\n${formatCanonResult(res)}`,
        ).toBeGreaterThanOrEqual(limits.minContrast);
      }
    });
  }
});
