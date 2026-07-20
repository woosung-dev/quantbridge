// 프로토타입 런타임 검사 — 실제 렌더 결과에서 가로스크롤/대비/포커스링/모션을 실측한다
// 사용법: node runtime-check.mjs [파일명...]   (인자 없으면 screen-*.html 전부)
// 필요: frontend/node_modules 의 playwright
import { chromium } from '../../../frontend/node_modules/.pnpm/playwright@1.59.1/node_modules/playwright/index.mjs';
import { readdirSync } from 'node:fs';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { dirname, join } from 'node:path';

const HERE = dirname(fileURLToPath(import.meta.url));
const WIDTHS = [1440, 1024, 768, 375];

const targets = process.argv.slice(2).filter((a) => !a.startsWith('--'));
const files = targets.length
  ? targets
  : readdirSync(HERE).filter((f) => /^screen-.*\.html$/.test(f)).sort();

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
    let base = { r: 11, g: 13, b: 15, a: 1 };
    const stack = [];
    for (let n = el; n && n.nodeType === 1; n = n.parentElement) {
      const c = parse(getComputedStyle(n).backgroundColor);
      if (c && c.a > 0) stack.push(c);
      if (c && c.a === 1) break;
    }
    for (let i = stack.length - 1; i >= 0; i--) base = over(stack[i], base);
    return base;
  };

  const out = { overflow: null, contrast: [], tiny: [] };
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
    const need = large ? 3 : 4.5;
    const key = cs.color + '|' + Math.round(size) + '|' + txt.slice(0, 20);
    if (cr < need && !seen.has(key)) {
      seen.add(key);
      out.contrast.push({ text: txt.slice(0, 42), color: cs.color, size, ratio: +cr.toFixed(2), need });
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

const browser = await chromium.launch();
const results = [];

for (const file of files) {
  const url = pathToFileURL(join(HERE, file)).href;
  const res = { file, overflow: [], contrast: [], tiny: [], focus: [], motion: [], console: [] };

  for (const w of WIDTHS) {
    const ctx = await browser.newContext({ viewport: { width: w, height: 900 }, deviceScaleFactor: 1 });
    const page = await ctx.newPage();
    page.on('console', (m) => {
      if (m.type() === 'error') res.console.push(`${w}px ${m.text().slice(0, 120)}`);
    });
    page.on('pageerror', (e) => res.console.push(`${w}px ${String(e).slice(0, 120)}`));
    await page.goto(url, { waitUntil: 'load' });
    await page.waitForTimeout(700);

    const a = await page.evaluate(AUDIT);
    if (a.overflow.scrollWidth > a.overflow.innerWidth + 1) {
      res.overflow.push({ w, scrollWidth: a.overflow.scrollWidth });
    }
    if (w === 1440 || w === 375) {
      a.contrast.forEach((c) => res.contrast.push({ w, ...c }));
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
  const rctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, reducedMotion: 'reduce' });
  const rpage = await rctx.newPage();
  await rpage.goto(url, { waitUntil: 'load' });
  await rpage.waitForTimeout(400);
  res.motion = await rpage.evaluate(MOTION_AUDIT);
  await rctx.close();

  results.push(res);
  const bad =
    res.overflow.length + res.contrast.length + res.focus.length + res.motion.length + res.console.length;
  console.log(
    `${bad === 0 ? 'PASS' : 'FAIL'}  ${file}  overflow=${res.overflow.length} contrast=${res.contrast.length} focus=${res.focus.length} motion=${res.motion.length} console=${res.console.length} tiny=${res.tiny.length}`,
  );
  if (res.overflow.length) console.log('   overflow:', JSON.stringify(res.overflow));
  res.contrast.slice(0, 8).forEach((c) => console.log(`   contrast ${c.w}px ${c.ratio}:1 (${c.need} 필요) ${c.color} ${c.size}px "${c.text}"`));
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
