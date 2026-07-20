// C 디자인 캐논 런타임 감사의 공용 코어 — 프로토타입과 React 앱이 같은 자를 쓰게 한다
//
// 출처는 `docs/prototypes/shotgun-2026-07/runtime-check.mjs` (212줄) 다.
// 그 검사기는 이미 Playwright 기반이고 핵심 로직이 `page.evaluate` 안에서 도는
// URL 무관한 순수 함수였다. 따라서 "새로 만든다" 가 아니라 "다시 겨눈다" 가 맞다.
// AUDIT / MOTION_AUDIT / 포커스링 프로브 / 4폭 은 의미 변경 없이 옮긴 것이다.
//
// ★이 파일이 하나여야 하는 이유.
// 캘리브레이션(`design-canon-calibration.spec.ts`) 은 프로토타입 17벌에서 17/17 을
// 재현해 "자가 맞다" 를 보인다. 그 결과가 React 쪽(`design-canon-app.spec.ts`) 에
// 대해 의미를 가지려면 **두 spec 이 같은 코드를 돌려야** 한다. 사본을 두 벌 두면
// 캘리브레이션은 자기 사본에 대해서만 참이 되고 아무것도 보증하지 못한다.
//
// TS strict(`noUncheckedIndexedAccess`) 때문에 원본 JS 대비 인덱스 접근에
// `?? 0` 폴백이 붙었다. parse() 는 정규식이 매치된 뒤에만 인덱싱하므로
// 폴백이 실제로 쓰이는 경로는 없다 — 동작은 원본과 같다.

import type { Browser, BrowserContextOptions, Page } from "@playwright/test";

/** 원본 `runtime-check.mjs:10` 과 같은 4폭. */
export const CANON_WIDTHS = [1440, 1024, 768, 375] as const;

/** 대비/미세크기 표본을 뜨는 폭. 원본 `:145` 과 같다. */
const SAMPLED_WIDTHS: ReadonlyArray<number> = [1440, 375];

/** 포커스링을 실제 Tab 이동으로 확인하는 폭. 원본 `:152` 과 같다. */
const FOCUS_WIDTH = 1440;

/** 원본 `:154` 과 같은 Tab 횟수. */
const FOCUS_TAB_COUNT = 30;

export interface ContrastFinding {
  text: string;
  color: string;
  size: number;
  ratio: number;
  need: number;
}

export interface TinyFinding {
  text: string;
  size: number;
}

export interface FocusFinding {
  tag: string;
  cls: string;
  label: string;
  visible: boolean;
}

export interface MotionFinding {
  cls: string;
  name: string;
  dur: string;
}

export interface OverflowFinding {
  w: number;
  scrollWidth: number;
  innerWidth: number;
}

/** 한 대상(URL)의 감사 결과 전체. */
export interface CanonAuditResult {
  /** 사람이 읽을 대상 이름. 프로토타입은 파일명, React 는 라우트 경로. */
  label: string;
  url: string;
  overflow: OverflowFinding[];
  contrast: Array<ContrastFinding & { w: number }>;
  canon: Array<ContrastFinding & { w: number }>;
  tiny: Array<TinyFinding & { w: number }>;
  focus: FocusFinding[];
  motion: MotionFinding[];
  console: string[];
}

/**
 * 페이지 안에서 실행되는 진단. 배경을 위로 거슬러 찾아 실제 대비를 계산한다.
 * 원본 `runtime-check.mjs:18-110` 이식.
 */
export const AUDIT = () => {
  const parse = (c: string) => {
    const m = c.match(/rgba?\(([^)]+)\)/);
    if (!m?.[1]) return null;
    const p = m[1].split(",").map((x) => parseFloat(x));
    return {
      r: p[0] ?? 0,
      g: p[1] ?? 0,
      b: p[2] ?? 0,
      a: p.length > 3 ? (p[3] ?? 1) : 1,
    };
  };
  type Rgba = { r: number; g: number; b: number; a: number };
  const over = (fg: Rgba, bg: Rgba): Rgba => ({
    r: fg.r * fg.a + bg.r * (1 - fg.a),
    g: fg.g * fg.a + bg.g * (1 - fg.a),
    b: fg.b * fg.a + bg.b * (1 - fg.a),
    a: 1,
  });
  const lin = (v: number) => {
    v /= 255;
    return v <= 0.04045 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4);
  };
  const lum = (c: Rgba) => 0.2126 * lin(c.r) + 0.7152 * lin(c.g) + 0.0722 * lin(c.b);
  const ratio = (a: Rgba, b: Rgba) => {
    const sorted = [lum(a), lum(b)].sort((p, q) => q - p);
    const x = sorted[0] ?? 0;
    const y = sorted[1] ?? 0;
    return (x + 0.05) / (y + 0.05);
  };
  const bgOf = (el: Element): Rgba => {
    // 최종 배경은 html/body 의 실제 계산값에서 받는다. 다크 #0b0d0f 를 상수로 박아두면
    // 라이트 화면에서 대비가 전부 뒤집혀 계산된다.
    const rootBg =
      parse(getComputedStyle(document.body).backgroundColor) ||
      parse(getComputedStyle(document.documentElement).backgroundColor);
    let base: Rgba = rootBg && rootBg.a === 1 ? rootBg : { r: 11, g: 13, b: 15, a: 1 };
    const stack: Rgba[] = [];
    for (let n: Element | null = el; n && n.nodeType === 1; n = n.parentElement) {
      const c = parse(getComputedStyle(n).backgroundColor);
      if (c && c.a > 0) stack.push(c);
      if (c && c.a === 1) break;
    }
    for (let i = stack.length - 1; i >= 0; i--) {
      const layer = stack[i];
      if (layer) base = over(layer, base);
    }
    return base;
  };

  const out = {
    overflow: {
      scrollWidth: document.documentElement.scrollWidth,
      innerWidth: window.innerWidth,
      bodyScroll: document.body.scrollWidth,
    },
    contrast: [] as ContrastFinding[],
    canon: [] as ContrastFinding[],
    tiny: [] as TinyFinding[],
  };

  const seen = new Set<string>();
  document.querySelectorAll("body *").forEach((el) => {
    const txt = Array.from(el.childNodes)
      .filter((n) => n.nodeType === 3)
      .map((n) => (n.textContent ?? "").trim())
      .join(" ")
      .trim();
    if (!txt) return;
    const cs = getComputedStyle(el);
    if (cs.visibility === "hidden" || cs.display === "none" || parseFloat(cs.opacity) < 0.15) return;
    if (el.closest('[aria-hidden="true"]')) return; // 장식 요소는 대비 대상이 아니다
    const r = el.getBoundingClientRect();
    if (r.width < 1 || r.height < 1) return;
    const fg0 = parse(cs.color);
    if (!fg0) return;
    const bg = bgOf(el);
    const fg = fg0.a < 1 ? over(fg0, bg) : fg0;
    const size = parseFloat(cs.fontSize);
    const weight = parseInt(cs.fontWeight, 10) || 400;
    const large = size >= 24 || (size >= 18.66 && weight >= 700);
    const cr = ratio(fg, bg);
    // WCAG AA = 하드 실패. 캐논은 별도 등급으로 "센다"(자동 실패시키지 않는다).
    //
    // 캐논 정의값 = 다크 정본의 최약 텍스트 --ink-3 #8b939c 가 --card #141619 위에서 갖는 값
    //            = 5.827427...  (문서의 "5.83" 은 반올림 표기다)
    // 임계를 5.83 으로 두면 캐논을 정의하는 토큰 자신이 걸린다. 5.82 로 둔다.
    //
    // 이 캐논은 "카드 위" 기준이다. --card-2 / --card-3 같은 중첩 표면에서는 같은 토큰이
    // 5.44 / 5.15 로 내려가며, 다크 정본도 원래 그렇다. 따라서 canon 은 하드 실패가 아니라
    // 지표이고, 판정 기준은 "라이트가 다크 짝보다 나쁘지 않은가" 라는 상대 비교다.
    const need = large ? 3 : 4.5;
    const canonNeed = large ? 3 : 5.82;
    const key = cs.color + "|" + Math.round(size) + "|" + txt.slice(0, 20);
    if (cr < need && !seen.has(key)) {
      seen.add(key);
      out.contrast.push({ text: txt.slice(0, 42), color: cs.color, size, ratio: +cr.toFixed(2), need });
    } else if (cr < canonNeed && !seen.has("c" + key)) {
      seen.add("c" + key);
      out.canon.push({ text: txt.slice(0, 42), color: cs.color, size, ratio: +cr.toFixed(2), need: canonNeed });
    }
    if (size < 9.4 && !seen.has("t" + key)) {
      // C 정본 최소치 0.68rem=9.52px 보다 작은 것만
      seen.add("t" + key);
      out.tiny.push({ text: txt.slice(0, 30), size });
    }
  });
  return out;
};

/**
 * reduced-motion 누수 검사. 원본 `runtime-check.mjs:112-122` 이식.
 * `prefers-reduced-motion: reduce` 컨텍스트에서 애니메이션이 여전히 도는지 본다.
 */
export const MOTION_AUDIT = () => {
  const bad: MotionFinding[] = [];
  document.querySelectorAll(".rise, .sk, .draw").forEach((el) => {
    const cs = getComputedStyle(el);
    const dur = (cs.animationDuration || "0s").split(",").map((d) => parseFloat(d) || 0);
    if (cs.animationName !== "none" && Math.max(...dur) > 0.01) {
      bad.push({
        cls: el.className.toString().slice(0, 40),
        name: cs.animationName,
        dur: cs.animationDuration,
      });
    }
  });
  return bad;
};

/**
 * 현재 포커스된 요소에 보이는 링이 있는지. 원본 `runtime-check.mjs:156-174` 이식.
 * 자기 outline · 조상 outline · box-shadow 중 하나라도 있으면 보인다고 본다.
 */
export const FOCUS_PROBE = (): FocusFinding | null => {
  const el = document.activeElement;
  if (!el || el === document.body) return null;
  const cs = getComputedStyle(el);
  const ow = parseFloat(cs.outlineWidth) || 0;
  const hasOutline = ow > 0 && cs.outlineStyle !== "none";
  let ancestorRing = false;
  for (let n = el.parentElement; n; n = n.parentElement) {
    const acs = getComputedStyle(n);
    if ((parseFloat(acs.outlineWidth) || 0) > 0 && acs.outlineStyle !== "none") ancestorRing = true;
  }
  const shadow = cs.boxShadow && cs.boxShadow !== "none";
  return {
    tag: el.tagName.toLowerCase(),
    cls: (el.className || "").toString().slice(0, 36),
    label: (el.getAttribute("aria-label") || el.textContent || "").trim().slice(0, 26),
    visible: hasOutline || ancestorRing || !!shadow,
  };
};

export interface AuditOptions {
  /** 사람이 읽을 대상 이름. 생략하면 URL. */
  label?: string;
  /** load 이후 정착 대기. 원본은 700ms 고정(`:139`). */
  settleMs?: number;
  /** 검사 폭. 기본 4폭. */
  widths?: ReadonlyArray<number>;
  /** 컨텍스트 생성 옵션 — React authed 라우트의 storageState 주입용. */
  contextOptions?: BrowserContextOptions;
  /**
   * 정착 후 감사 직전 훅. 데이터 의존 화면에서 로딩이 끝나기를 기다리는 용도.
   * 프로토타입은 정적 HTML 이라 쓰지 않는다.
   */
  prepare?: (page: Page) => Promise<void>;
  /** true 를 주면 그 콘솔 에러는 집계하지 않는다. 백엔드 부재 소음 제외용. */
  ignoreConsole?: (text: string) => boolean;
}

/**
 * 대상 하나를 4폭 + reduced-motion 으로 감사한다.
 * 원본 `runtime-check.mjs:127-189` 의 루프 이식.
 */
export async function auditUrl(
  browser: Browser,
  url: string,
  options: AuditOptions = {},
): Promise<CanonAuditResult> {
  const {
    label = url,
    settleMs = 700,
    widths = CANON_WIDTHS,
    contextOptions = {},
    prepare,
    ignoreConsole,
  } = options;

  const res: CanonAuditResult = {
    label,
    url,
    overflow: [],
    contrast: [],
    canon: [],
    tiny: [],
    focus: [],
    motion: [],
    console: [],
  };

  for (const w of widths) {
    const ctx = await browser.newContext({
      ...contextOptions,
      viewport: { width: w, height: 900 },
      deviceScaleFactor: 1,
    });
    const page = await ctx.newPage();
    page.on("console", (m) => {
      if (m.type() !== "error") return;
      const text = m.text();
      if (ignoreConsole?.(text)) return;
      res.console.push(`${w}px ${text.slice(0, 120)}`);
    });
    page.on("pageerror", (e) => {
      const text = String(e);
      if (ignoreConsole?.(text)) return;
      res.console.push(`${w}px ${text.slice(0, 120)}`);
    });

    await page.goto(url, { waitUntil: "load" });
    await page.waitForTimeout(settleMs);
    if (prepare) await prepare(page);

    const a = await page.evaluate(AUDIT);
    if (a.overflow.scrollWidth > a.overflow.innerWidth + 1) {
      res.overflow.push({ w, scrollWidth: a.overflow.scrollWidth, innerWidth: a.overflow.innerWidth });
    }
    if (SAMPLED_WIDTHS.includes(w)) {
      a.contrast.forEach((c) => res.contrast.push({ w, ...c }));
      a.canon.forEach((c) => res.canon.push({ w, ...c }));
      a.tiny.forEach((t) => res.tiny.push({ w, ...t }));
    }

    // 포커스 링 — 실제 Tab 이동으로 확인
    if (w === FOCUS_WIDTH) {
      await page.evaluate(() => document.body.focus());
      for (let i = 0; i < FOCUS_TAB_COUNT; i++) {
        await page.keyboard.press("Tab");
        const f = await page.evaluate(FOCUS_PROBE);
        if (f && !f.visible) res.focus.push(f);
      }
    }
    await ctx.close();
  }

  // reduced motion
  const rctx = await browser.newContext({
    ...contextOptions,
    viewport: { width: 1440, height: 900 },
    reducedMotion: "reduce",
  });
  const rpage = await rctx.newPage();
  await rpage.goto(url, { waitUntil: "load" });
  await rpage.waitForTimeout(400);
  res.motion = await rpage.evaluate(MOTION_AUDIT);
  await rctx.close();

  return res;
}

/**
 * 하드 실패 건수. 원본 `runtime-check.mjs:191-192` 과 같은 정의다.
 * ★canon 은 여기 들어가지 않는다 — 다크 정본도 중첩 표면에서 걸리므로
 * 하드 실패로 쓰면 게이트가 무의미해진다. canon 은 별도 지표로 추적한다.
 */
export function hardFailCount(res: CanonAuditResult): number {
  return (
    res.overflow.length +
    res.contrast.length +
    res.focus.length +
    res.motion.length +
    res.console.length
  );
}

/** 원본 `runtime-check.mjs:193-202` 과 같은 한 줄 요약 + 상세. 출력을 그대로 기록하기 위함. */
export function formatCanonResult(res: CanonAuditResult): string {
  const bad = hardFailCount(res);
  const lines = [
    `${bad === 0 ? "PASS" : "FAIL"}  ${res.label}  overflow=${res.overflow.length} contrast=${res.contrast.length} focus=${res.focus.length} motion=${res.motion.length} canon=${res.canon.length} console=${res.console.length} tiny=${res.tiny.length}`,
  ];
  if (res.overflow.length) lines.push(`   overflow: ${JSON.stringify(res.overflow)}`);
  res.contrast
    .slice(0, 8)
    .forEach((c) =>
      lines.push(`   contrast ${c.w}px ${c.ratio}:1 (${c.need} 필요) ${c.color} ${c.size}px "${c.text}"`),
    );
  res.canon
    .slice(0, 4)
    .forEach((c) =>
      lines.push(`   canon ${c.w}px ${c.ratio}:1 (${c.need} 필요) ${c.color} ${c.size}px "${c.text}"`),
    );
  res.focus.slice(0, 8).forEach((f) => lines.push(`   focus 링 없음: ${f.tag}.${f.cls} "${f.label}"`));
  res.motion
    .slice(0, 5)
    .forEach((m) => lines.push(`   reduced-motion 누수: ${m.cls} ${m.name} ${m.dur}`));
  res.console.slice(0, 5).forEach((c) => lines.push(`   console: ${c}`));
  res.tiny.slice(0, 4).forEach((t) => lines.push(`   11px 미만 텍스트: ${t.size}px "${t.text}"`));
  return lines.join("\n");
}
