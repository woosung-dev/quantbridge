// 프로토타입 런타임 검사 — 실제 렌더 결과에서 가로스크롤/대비/포커스링/모션을 실측한다
//
// 사용법
//   node runtime-check.mjs [파일명...]                       인자 없으면 screen-*.html 17벌 (종전 동작)
//   node runtime-check.mjs --base-url http://localhost:3107 --routes /,/pricing [옵션]
//
// 옵션 (--base-url 모드 전용)
//   --routes /a,/b            검사할 라우트 목록 (생략 시 `/`)
//   --theme light|dark        next-themes localStorage + colorScheme 을 강제한다
//   --storage-state <path>    playwright storageState JSON (Clerk 인증 라우트용)
//
// ★임계값은 로컬 파일 모드와 앱 모드가 **같다**. 이 도구를 앱에 겨누는 유일한 이유가
//   캘리브레이션된 임계값(AA 4.5/3 · canon 5.82 · tiny 9.4px · Tab 30회)을 물려받는 것이다.
//
// 필요: frontend/node_modules 의 playwright
// ★상대 깊이 주의 — 이 파일은 <repo>/docs/reference/design/prototypes/shotgun-2026-07/ 에 있다.
//   `docs/` 재편(fcc36bf7)으로 두 단계 깊어졌는데 import 가 안 따라와서 ERR_MODULE_NOT_FOUND 로
//   기동조차 못 하고 있었다. repo 루트까지는 다섯 단계다.
import { chromium } from '../../../../../apps/web/node_modules/.pnpm/playwright@1.59.1/node_modules/playwright/index.mjs';
import { readdirSync } from 'node:fs';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { dirname, join } from 'node:path';

const HERE = dirname(fileURLToPath(import.meta.url));
const WIDTHS = [1440, 1024, 768, 375];

// `--flag value` / `--flag=value` 둘 다 받는다. 위치 인자는 종전대로 파일명이다.
const opts = {};
const positional = [];
{
  const argv = process.argv.slice(2);
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (!a.startsWith('--')) {
      positional.push(a);
      continue;
    }
    const eq = a.indexOf('=');
    if (eq > -1) opts[a.slice(2, eq)] = a.slice(eq + 1);
    else if (i + 1 < argv.length && !argv[i + 1].startsWith('--')) opts[a.slice(2)] = argv[++i];
    else opts[a.slice(2)] = true;
  }
}
const str = (k) => (typeof opts[k] === 'string' ? opts[k] : null);

const baseUrl = str('base-url') ? str('base-url').replace(/\/+$/, '') : null;
const theme = str('theme');
const storageState = str('storage-state');
const routes = (str('routes') || '')
  .split(',')
  .map((r) => r.trim())
  .filter(Boolean);

// 앱 모드는 dev 서버 JIT 컴파일을 기다려야 한다. 로컬 html 은 종전 값을 그대로 쓴다.
const NAV_TIMEOUT = baseUrl ? 120_000 : 30_000;
const SETTLE_MS = baseUrl ? 1500 : 700;

const files = baseUrl
  ? routes.length
    ? routes
    : ['/']
  : positional.length
    ? positional
    : readdirSync(HERE).filter((f) => /^screen-.*\.html$/.test(f)).sort();

const urlOf = (target) =>
  baseUrl
    ? baseUrl + (target.startsWith('/') ? target : `/${target}`)
    : pathToFileURL(join(HERE, target)).href;

// 페이지 안에서 실행되는 진단. 배경을 위로 거슬러 찾아 실제 대비를 계산한다.
const AUDIT = () => {
  const parse = (c) => {
    const m = c.match(/rgba?\(([^)]+)\)/);
    if (!m) return null;
    const p = m[1].split(',').map((x) => parseFloat(x));
    return { r: p[0], g: p[1], b: p[2], a: p.length > 3 ? p[3] : 1 };
  };
  const over = (fg, bg) => ({
    r: fg.r * fg.a + bg.r * (1 - fg.a),
    g: fg.g * fg.a + bg.g * (1 - fg.a),
    b: fg.b * fg.a + bg.b * (1 - fg.a),
    a: 1,
  });
  const lin = (v) => {
    v /= 255;
    return v <= 0.04045 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4);
  };
  const lum = (c) => 0.2126 * lin(c.r) + 0.7152 * lin(c.g) + 0.0722 * lin(c.b);
  const ratio = (a, b) => {
    const [x, y] = [lum(a), lum(b)].sort((p, q) => q - p);
    return (x + 0.05) / (y + 0.05);
  };
  const bgOf = (el) => {
    // 최종 배경은 html/body 의 실제 계산값에서 받는다. 다크 #0b0d0f 를 상수로 박아두면
    // 라이트 화면에서 대비가 전부 뒤집혀 계산된다.
    const rootBg =
      parse(getComputedStyle(document.body).backgroundColor) ||
      parse(getComputedStyle(document.documentElement).backgroundColor);
    let base = rootBg && rootBg.a === 1 ? rootBg : { r: 11, g: 13, b: 15, a: 1 };
    const stack = [];
    for (let n = el; n && n.nodeType === 1; n = n.parentElement) {
      const c = parse(getComputedStyle(n).backgroundColor);
      if (c && c.a > 0) stack.push(c);
      if (c && c.a === 1) break;
    }
    for (let i = stack.length - 1; i >= 0; i--) base = over(stack[i], base);
    return base;
  };

  const out = { overflow: null, contrast: [], canon: [], tiny: [] };
  out.overflow = {
    scrollWidth: document.documentElement.scrollWidth,
    innerWidth: window.innerWidth,
    bodyScroll: document.body.scrollWidth,
  };

  const seen = new Set();
  document.querySelectorAll('body *').forEach((el) => {
    const txt = Array.from(el.childNodes)
      .filter((n) => n.nodeType === 3)
      .map((n) => n.textContent.trim())
      .join(' ')
      .trim();
    if (!txt) return;
    const cs = getComputedStyle(el);
    if (cs.visibility === 'hidden' || cs.display === 'none' || parseFloat(cs.opacity) < 0.15) return;
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
    const key = cs.color + '|' + Math.round(size) + '|' + txt.slice(0, 20);
    if (cr < need && !seen.has(key)) {
      seen.add(key);
      out.contrast.push({ text: txt.slice(0, 42), color: cs.color, size, ratio: +cr.toFixed(2), need });
    } else if (cr < canonNeed && !seen.has('c' + key)) {
      seen.add('c' + key);
      out.canon.push({ text: txt.slice(0, 42), color: cs.color, size, ratio: +cr.toFixed(2), need: canonNeed });
    }
    if (size < 9.4 && !seen.has('t' + key)) { // C 정본 최소치 0.68rem=9.52px 보다 작은 것만
      seen.add('t' + key);
      out.tiny.push({ text: txt.slice(0, 30), size });
    }
  });
  return out;
};

const MOTION_AUDIT = () => {
  const bad = [];
  document.querySelectorAll('.rise, .sk, .draw').forEach((el) => {
    const cs = getComputedStyle(el);
    const dur = (cs.animationDuration || '0s').split(',').map((d) => parseFloat(d) || 0);
    if (cs.animationName !== 'none' && Math.max(...dur) > 0.01) {
      bad.push({ cls: el.className.toString().slice(0, 40), name: cs.animationName, dur: cs.animationDuration });
    }
  });
  return bad;
};

console.log(
  baseUrl
    ? `대상: ${baseUrl} · 라우트 ${files.length}개 · theme=${theme ?? '(앱 기본값)'} · storageState=${storageState ? 'yes' : 'no'}`
    : `대상: 로컬 html ${files.length}벌 (${HERE})`,
);

const browser = await chromium.launch();
const results = [];

// 테마·인증은 컨텍스트 옵션으로만 준다 — 페이지 안의 판정 로직(AUDIT)은 URL 도 테마도 모른다.
const contextOptions = (extra) => ({
  deviceScaleFactor: 1,
  ...(storageState ? { storageState } : {}),
  ...(theme ? { colorScheme: theme } : {}),
  ...extra,
});
// next-themes(attribute="class", storageKey 기본값 "theme") 를 pre-paint 단계에서 고정한다.
const applyTheme = async (ctx) => {
  if (!theme) return;
  await ctx.addInitScript((t) => {
    try {
      window.localStorage.setItem('theme', t);
    } catch {
      /* file:// 등 storage 불가 컨텍스트 — colorScheme 만으로 간다 */
    }
  }, theme);
};

// 앱 모드 pre-warm — dev 서버 첫 컴파일(5~30초)이 폭별 측정에 섞이지 않게 한 번 데운다.
if (baseUrl) {
  const wctx = await browser.newContext(contextOptions({ viewport: { width: 1440, height: 900 } }));
  await applyTheme(wctx);
  const wpage = await wctx.newPage();
  for (const target of files) {
    try {
      await wpage.goto(urlOf(target), { waitUntil: 'load', timeout: NAV_TIMEOUT });
      await wpage.waitForTimeout(500);
    } catch (e) {
      console.log(`   pre-warm 실패 ${target}: ${String(e).slice(0, 100)}`);
    }
  }
  await wctx.close();
}

for (const file of files) {
  const url = urlOf(file);
  const res = { file, overflow: [], contrast: [], canon: [], tiny: [], focus: [], motion: [], console: [] };

  for (const w of WIDTHS) {
    const ctx = await browser.newContext(contextOptions({ viewport: { width: w, height: 900 } }));
    await applyTheme(ctx);
    const page = await ctx.newPage();
    page.on('console', (m) => {
      if (m.type() === 'error') res.console.push(`${w}px ${m.text().slice(0, 120)}`);
    });
    page.on('pageerror', (e) => res.console.push(`${w}px ${String(e).slice(0, 120)}`));
    await page.goto(url, { waitUntil: 'load', timeout: NAV_TIMEOUT });
    await page.waitForTimeout(SETTLE_MS);

    const a = await page.evaluate(AUDIT);
    if (a.overflow.scrollWidth > a.overflow.innerWidth + 1) {
      res.overflow.push({ w, scrollWidth: a.overflow.scrollWidth });
    }
    if (w === 1440 || w === 375) {
      a.contrast.forEach((c) => res.contrast.push({ w, ...c }));
      a.canon.forEach((c) => res.canon.push({ w, ...c }));
      a.tiny.forEach((t) => res.tiny.push({ w, ...t }));
    }

    // 포커스 링 — 실제 Tab 이동으로 확인
    if (w === 1440) {
      await page.evaluate(() => document.body.focus());
      for (let i = 0; i < 30; i++) {
        await page.keyboard.press('Tab');
        const f = await page.evaluate(() => {
          const el = document.activeElement;
          if (!el || el === document.body) return null;
          const cs = getComputedStyle(el);
          const ow = parseFloat(cs.outlineWidth) || 0;
          const hasOutline = ow > 0 && cs.outlineStyle !== 'none';
          let ancestorRing = false;
          for (let n = el.parentElement; n; n = n.parentElement) {
            const acs = getComputedStyle(n);
            if ((parseFloat(acs.outlineWidth) || 0) > 0 && acs.outlineStyle !== 'none') ancestorRing = true;
          }
          const shadow = cs.boxShadow && cs.boxShadow !== 'none';
          return {
            tag: el.tagName.toLowerCase(),
            cls: (el.className || '').toString().slice(0, 36),
            label: (el.getAttribute('aria-label') || el.textContent || '').trim().slice(0, 26),
            visible: hasOutline || ancestorRing || shadow,
          };
        });
        if (f && !f.visible) res.focus.push(f);
      }
    }
    await ctx.close();
  }

  // reduced motion
  const rctx = await browser.newContext(
    contextOptions({ viewport: { width: 1440, height: 900 }, reducedMotion: 'reduce' }),
  );
  await applyTheme(rctx);
  const rpage = await rctx.newPage();
  await rpage.goto(url, { waitUntil: 'load', timeout: NAV_TIMEOUT });
  await rpage.waitForTimeout(400);
  res.motion = await rpage.evaluate(MOTION_AUDIT);
  await rctx.close();

  results.push(res);
  // canon 은 집계에서 뺀다. 다크 정본도 중첩 표면에서 걸리므로 하드 실패로 쓰면 게이트가 무의미해진다.
  const bad =
    res.overflow.length + res.contrast.length + res.focus.length + res.motion.length + res.console.length;
  console.log(
    `${bad === 0 ? 'PASS' : 'FAIL'}  ${file}  overflow=${res.overflow.length} contrast=${res.contrast.length} focus=${res.focus.length} motion=${res.motion.length} canon=${res.canon.length} console=${res.console.length} tiny=${res.tiny.length}`,
  );
  if (res.overflow.length) console.log('   overflow:', JSON.stringify(res.overflow));
  res.contrast.slice(0, 8).forEach((c) => console.log(`   contrast ${c.w}px ${c.ratio}:1 (${c.need} 필요) ${c.color} ${c.size}px "${c.text}"`));
  res.canon.slice(0, 4).forEach((c) => console.log(`   canon ${c.w}px ${c.ratio}:1 (${c.need} 필요) ${c.color} ${c.size}px "${c.text}"`));
  res.focus.slice(0, 8).forEach((f) => console.log(`   focus 링 없음: ${f.tag}.${f.cls} "${f.label}"`));
  res.motion.slice(0, 5).forEach((m) => console.log(`   reduced-motion 누수: ${m.cls} ${m.name} ${m.dur}`));
  res.console.slice(0, 5).forEach((c) => console.log(`   console: ${c}`));
  res.tiny.slice(0, 4).forEach((t) => console.log(`   11px 미만 텍스트: ${t.size}px "${t.text}"`));
}

await browser.close();

const failed = results.filter(
  (r) => r.overflow.length + r.contrast.length + r.focus.length + r.motion.length + r.console.length > 0,
);
console.log(`\n총 ${results.length}개 중 ${results.length - failed.length}개 통과.`);
if (failed.length) console.log('실패: ' + failed.map((f) => f.file).join(', '));
process.exit(failed.length ? 1 : 0);
