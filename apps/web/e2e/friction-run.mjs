// d1 실사용 마찰 계측기 — 신규 사용자 여정을 대행 주행하며 시계와 막힌 지점을 센다.
//
// 왜 `.mjs` 인가: `playwright.config.ts` 의 `chromium-authed` 가 `testMatch: /\.spec\.ts$/` 라
// spec 파일을 만들면 authed 게이트에 자동 편입된다. 이 러너는 red 를 내는 것이 목적이 아니라
// **세는 것**이므로 게이트가 되면 안 된다. 형태 원형 = `e2e/demo-rehearsal.mjs`.
//
// rc 규약 (이것이 이 러너의 하중 지점이다):
//   0 = 계측에 성공했다. 마찰 건수는 0 일 수도 N 일 수도 있다.
//   2 = 계측을 못 했다 (BE 미도달 · 로그인 실패 · 구간 앵커 부재 · 이벤트 0줄)
// 이 구분이 없으면 「마찰 0건」과 「측정 실패」가 섞인다.
//
// 실행:
//   node e2e/friction-run.mjs --journey=A --run=<라벨>
//   node e2e/friction-run.mjs --journey=B --run=<라벨> [--pine=<경로>]
import { chromium } from "@playwright/test";
import { mkdirSync, writeFileSync, appendFileSync, readFileSync, existsSync } from "node:fs";
import { resolve } from "node:path";

const argv = process.argv.slice(2);
const arg = (k, d) => {
  const hit = argv.find((a) => a.startsWith(`--${k}=`));
  return hit ? hit.slice(k.length + 3) : d;
};
const JOURNEY = (arg("journey", "A") || "A").toUpperCase();
const RUN = arg("run", "dry");
const BASE = process.env.PLAYWRIGHT_BASE_URL ?? "http://localhost:3000";
const STATE = "e2e/.auth/storageState.json";
const PINE = arg("pine", "");
const REPO = resolve(process.cwd(), "../..");
const OUT = `${REPO}/runs/d1-friction/${RUN}-${JOURNEY}`;
mkdirSync(`${OUT}/shots`, { recursive: true });

const EV = `${OUT}/events.ndjson`;
const FR = `${OUT}/friction.ndjson`;
writeFileSync(EV, "");
writeFileSync(FR, "");

const t = () => Date.now();
const T0 = t();
const ev = (o) => appendFileSync(EV, `${JSON.stringify({ ms: t() - T0, ...o })}\n`);
const friction = (o) => appendFileSync(FR, `${JSON.stringify(o)}\n`);

// 시계 — 정의는 계획 §Phase 1. null 은 「그 지점에 도달 못 했다」이고 0 과 다르다.
const clock = {
  t0_parse: null,
  t1_import: null,
  t2_submit: null,
  t3_done_seen: null,
  t4_render: null,
};

let bail = null; // 계측 실패 사유. 채워지면 rc=2.
const die = (why) => {
  bail = why;
  ev({ kind: "ABORT", why });
};

const browser = await chromium.launch();
const ctxOpts = { viewport: { width: 1440, height: 900 } };
if (JOURNEY === "A") {
  if (!existsSync(STATE)) die(`storageState 없음: ${STATE}`);
  else ctxOpts.storageState = STATE;
}
const ctx = await browser.newContext(ctxOpts);
const page = await ctx.newPage();

page.on("console", (m) => {
  if (m.type() === "error") ev({ kind: "console_error", text: m.text().slice(0, 300) });
});
page.on("response", (r) => {
  const u = r.url();
  if (!u.includes("/api/")) return;
  const rec = { kind: "api", status: r.status(), url: u.replace(BASE, "").slice(0, 160) };
  ev(rec);
  const p = rec.url;
  if (p.includes("/strategies/parse") && r.status() === 200) clock.t0_parse ??= t();
  if (/\/api\/v1\/strategies$/.test(p) && r.request().method() === "POST" && r.status() === 201)
    clock.t1_import ??= t();
  if (/\/api\/v1\/backtests$/.test(p) && r.request().method() === "POST" && r.status() === 202)
    clock.t2_submit ??= t();
});

const shot = async (name) => {
  await page.screenshot({ path: `${OUT}/shots/${name}.png` }).catch(() => {});
};

// ── A0 — 이 회차의 최대 관측량: 온보딩에 도달할 수 있나 ────────────────────────
async function countOnboardingLinks() {
  const counts = {};
  for (const route of ["/strategies", "/dashboard", "/backtests"]) {
    const res = await page.goto(BASE + route, { waitUntil: "domcontentloaded", timeout: 90_000 });
    await page.waitForTimeout(2500);
    counts[route] = {
      http: res?.status() ?? null,
      onboardingLinks: await page.locator('a[href="/onboarding"]').count(),
    };
  }
  ev({ kind: "A0_reachability", counts });
  const total = Object.values(counts).reduce((s, c) => s + c.onboardingLinks, 0);
  if (total === 0) {
    friction({
      id: "FR-A0-01",
      screen: "/strategies · /dashboard · /backtests",
      intent: "신규 사용자가 온보딩(5분 코스)에 들어간다",
      observed: `세 화면 전부에서 a[href="/onboarding"] 개수 = 0 (실측 ${JSON.stringify(counts)})`,
      evidence: [
        "apps/web/src/features/dashboard/components/dashboard-nav-list.tsx:32-37",
        "apps/web/src/app/(auth)/sign-up/[[...sign-up]]/page.tsx:17",
      ],
      workaround: "url-direct — URL 을 직접 입력해야만 도달한다",
      cost_s: null,
      severity: "blocker",
    });
  }
  return total;
}

// ── Journey A — 온보딩 위저드 ──────────────────────────────────────────────
async function journeyA() {
  await countOnboardingLinks();

  const res = await page.goto(`${BASE}/onboarding`, {
    waitUntil: "domcontentloaded",
    timeout: 90_000,
  });
  ev({ kind: "goto", route: "/onboarding", http: res?.status() ?? null });
  const panel = page.locator('[data-testid="onboarding-step-panel"]');
  try {
    await panel.waitFor({ state: "visible", timeout: 30_000 });
  } catch {
    return die("/onboarding 패널이 30초 안에 안 떴다");
  }
  await shot("a1-welcome");
  ev({ kind: "step", step: await panel.getAttribute("data-step") });

  const wallStart = t(); // T_wall 시작 — 위저드를 실제로 시작한 순간
  await page.locator('button[aria-label="다음 단계로 진행"]').click();
  await page.waitForTimeout(700);
  ev({ kind: "step", step: await panel.getAttribute("data-step") });
  await shot("a2-strategy");

  await page.locator('button[aria-label="샘플 전략 등록 및 다음 단계"]').click();
  try {
    await page.locator('[data-testid="onboarding-step-panel"][data-step="backtest"]').waitFor({
      state: "visible",
      timeout: 60_000,
    });
  } catch {
    await shot("a2-fail");
    return die("샘플 전략 등록 후 backtest 스텝으로 안 넘어갔다");
  }
  await shot("a3-backtest");

  // step-3 은 자동 실행이고, 완료되면 `onBacktestReady` 가 **즉시 step-4 로 넘긴다**
  // (`step-3-backtest.tsx:88-92`). 따라서 step-3 의 `.ob-run-done` 은 스쳐 지나가므로
  // 앵커로 쓸 수 없다 — 2026-09-06 t0-1 주행이 그것으로 300초를 태웠다.
  // 화면이 결과를 실제로 보인 시각 = step-4 패널이다.
  try {
    await page
      .locator('[data-testid="onboarding-step-panel"][data-step="result"]')
      .waitFor({ state: "visible", timeout: 300_000 });
    clock.t4_render = t();
  } catch {
    await shot("a3-timeout");
    friction({
      id: "FR-A3-01",
      screen: "/onboarding (step 3)",
      intent: "샘플 전략의 30일 백테스트 결과를 본다",
      observed: "300초 안에 step-4(result) 패널이 안 나타났다",
      evidence: ["apps/web/src/features/onboarding/components/step-3-backtest.tsx:150-157"],
      workaround: "none",
      cost_s: 300,
      severity: "blocker",
    });
    return die("백테스트 완료 앵커 타임아웃");
  }
  await shot("a4-result");

  await page.waitForTimeout(1500);
  const step = await panel.getAttribute("data-step");
  const stats = await page
    .locator(".ob-stat")
    .allTextContents()
    .catch(() => []);
  ev({ kind: "A4_result", step, stats: stats.map((s) => s.replace(/\s+/g, " ").trim()) });
  ev({ kind: "T_wall", ms: t() - wallStart });
  return t() - wallStart;
}

// ── Journey B — 실제 신규 사용자 ───────────────────────────────────────────
async function journeyB() {
  const email = `d1-${Date.now()}@dogfood.local`;
  const password = "d1-local-password-2026";

  await page.goto(`${BASE}/sign-up`, { waitUntil: "domcontentloaded", timeout: 90_000 });
  const wallStart = t();
  await page
    .locator('input[name="name"]')
    .fill("d1 runner")
    .catch(() => {});
  await page.locator('input[type="email"]').fill(email);
  await page.locator('input[type="password"]').first().fill(password);
  await page.locator('button[type="submit"]').click();
  // 착지점은 고정값으로 단정하지 않고 **기록**한다 — 2026-09-06 수리로 `/strategies` 에서
  // `/onboarding` 으로 바뀌었고, 계측기가 옛 값을 기다리다 멈춘 전례가 이 줄의 이유다.
  try {
    await page.waitForURL(/\/(strategies|onboarding)/, { timeout: 60_000 });
  } catch {
    await shot("b0-fail");
    return die(`가입 후 앱 내부로 안 갔다 (현재 ${page.url()})`);
  }
  const landedOn = page.url().replace(BASE, "");
  ev({ kind: "B0_signup", email, landedOn });
  await page.waitForTimeout(2000);
  await shot("b0-landing");

  // 수동 임포트 경로를 재는 것이 B 의 목적이므로 목록으로 간다(온보딩은 A 가 잰다).
  await page.goto(`${BASE}/strategies`, { waitUntil: "domcontentloaded", timeout: 90_000 });
  await page.waitForTimeout(2500);
  await shot("b1-empty");
  const emptyBox = await page.locator('[data-testid="strategy-empty"]').count();
  const onboardingLinks = await page.locator('a[href="/onboarding"]').count();
  ev({ kind: "B1_landing", emptyBox, onboardingLinks });

  // B2 — Pine 임포트
  await page.goto(`${BASE}/strategies/new`, { waitUntil: "domcontentloaded", timeout: 90_000 });
  await page.waitForTimeout(2000);
  const pinePath = PINE || `${REPO}/apps/web/public/samples/ema-crossover.pine`;
  if (!existsSync(pinePath)) return die(`Pine 파일 없음: ${pinePath}`);
  await page.locator('[data-testid="pine-file-input"]').setInputFiles(pinePath);
  try {
    await page
      .locator('[data-testid="parse-supported"], [data-testid="parse-unsupported"]')
      .first()
      .waitFor({ state: "visible", timeout: 90_000 });
  } catch {
    await shot("b2-fail");
    return die("파싱 결과 패널이 안 떴다");
  }
  await shot("b2-parsed");
  const supported = await page.locator('[data-testid="parse-supported"]').count();
  ev({ kind: "B2_parse", supported });

  const saveBtn = page.locator('[data-testid="parse-save"]');
  if ((await saveBtn.count()) === 0) {
    friction({
      id: "FR-B3-01",
      screen: "/strategies/new",
      intent: "파싱한 전략을 저장한다",
      observed: "parse-save 버튼이 렌더되지 않았다 (미지원 빌트인 또는 이름 미입력)",
      evidence: ["apps/web/src/features/strategy/components/new/new-strategy-wizard.tsx:106-110"],
      workaround: "none",
      cost_s: null,
      severity: "blocker",
    });
    return die("저장 버튼 부재");
  }
  // 이름 입력은 `new-strategy-wizard.tsx:241` 의 `id="f-name"` 하나다.
  // 2026-09-06 t0-B1 이 이 셀렉터를 못 찾아 `canSave` 가 false 인 채 저장 버튼을 눌렀다.
  await page.locator("input#f-name").fill(`d1 run ${RUN}`);
  await page.waitForTimeout(400);
  await saveBtn.click();
  try {
    await page.waitForURL(/\/strategies\/[0-9a-f-]+\/edit/, { timeout: 60_000 });
  } catch {
    await shot("b3-fail");
    return die(`저장 후 편집 화면으로 안 갔다 (${page.url()})`);
  }
  const strategyId = (page.url().match(/strategies\/([0-9a-f-]+)\//) || [])[1] ?? null;
  ev({ kind: "B3_saved", strategyId, url: page.url().replace(BASE, "") });
  await shot("b3-saved");

  // B4 — 백테스트 폼. 여기서 prefill·기본값을 관측한다.
  await page.goto(`${BASE}/backtests/new?strategy_id=${strategyId}`, {
    waitUntil: "domcontentloaded",
    timeout: 90_000,
  });
  await page
    .locator('[data-testid="backtest-form-layout"]')
    .waitFor({ state: "visible", timeout: 60_000 })
    .catch(() => {});
  await page.waitForTimeout(2500);
  const defaults = {
    symbol: await page
      .locator("select#symbol, select[name='symbol']")
      .first()
      .inputValue()
      .catch(() => null),
    timeframe: await page
      .locator("select#timeframe, select[name='timeframe']")
      .first()
      .inputValue()
      .catch(() => null),
    start: await page
      .locator("input#period_start, input[name='period_start']")
      .first()
      .inputValue()
      .catch(() => null),
    end: await page
      .locator("input#period_end, input[name='period_end']")
      .first()
      .inputValue()
      .catch(() => null),
    activePreset: await page
      .locator('[data-testid^="date-preset-"][aria-pressed="true"]')
      .first()
      .getAttribute("data-testid")
      .catch(() => null),
  };
  ev({ kind: "B5_form_defaults", defaults });
  await shot("b5-form");

  await page.locator('[data-testid="backtest-submit"]').click();
  await page.waitForTimeout(3000);
  const errCard = await page.locator('[data-testid^="backtest-form-server-error"]').count();
  if (errCard > 0) {
    const txt = (
      await page
        .locator('[data-testid^="backtest-form-server-error"]')
        .first()
        .innerText()
        .catch(() => "")
    )
      .replace(/\s+/g, " ")
      .slice(0, 300);
    friction({
      id: "FR-B6-01",
      screen: "/backtests/new",
      intent: "임포트한 전략을 기본값 그대로 백테스트한다",
      observed: `제출이 서버 오류 카드로 막혔다: "${txt}"`,
      evidence: ["apps/api/src/backtest/service.py:169-198"],
      workaround: "none",
      cost_s: null,
      severity: "blocker",
    });
    await shot("b6-error");
    return die("백테스트 제출이 422 로 막혔다");
  }
  try {
    await page.waitForURL(/\/backtests\/[0-9a-f-]+/, { timeout: 60_000 });
  } catch {
    await shot("b6-fail");
    return die(`제출 후 상세로 안 갔다 (${page.url()})`);
  }
  try {
    await page
      .locator('[data-testid="backtest-report-shell"]')
      .waitFor({ state: "visible", timeout: 300_000 });
    clock.t4_render = t();
  } catch {
    await shot("b7-timeout");
    friction({
      id: "FR-B7-01",
      screen: "/backtests/{id}",
      intent: "백테스트 결과 리포트를 본다",
      observed: "300초 안에 backtest-report-shell 이 안 나타났다",
      evidence: ["apps/web/src/features/backtest/hooks.ts:69"],
      workaround: "none",
      cost_s: 300,
      severity: "blocker",
    });
    return die("리포트 렌더 타임아웃");
  }
  await shot("b7-report");
  ev({ kind: "T_wall", ms: t() - wallStart });
  return t() - wallStart;
}

let wall = null;
try {
  wall = JOURNEY === "A" ? await journeyA() : await journeyB();
} catch (e) {
  die(`예외: ${String(e).slice(0, 300)}`);
}

const evLines = readFileSync(EV, "utf8").trim().split("\n").filter(Boolean).length;
if (evLines === 0) die("events 0줄 — 계측기가 죽었다(마찰 0 이 아니다)");

const frLines = readFileSync(FR, "utf8").trim().split("\n").filter(Boolean).length;
const timings = {
  journey: JOURNEY,
  run: RUN,
  base: BASE,
  t_wall_ms: typeof wall === "number" ? wall : null,
  clock_rel_ms: Object.fromEntries(
    Object.entries(clock).map(([k, v]) => [k, v === null ? null : v - T0]),
  ),
  t4_minus_t2_ms: clock.t4_render && clock.t2_submit ? clock.t4_render - clock.t2_submit : null,
  t2_minus_t1_ms: clock.t2_submit && clock.t1_import ? clock.t2_submit - clock.t1_import : null,
  friction_count: frLines,
  event_lines: evLines,
  measured: bail === null,
  abort_reason: bail,
};
writeFileSync(`${OUT}/timings.json`, `${JSON.stringify(timings, null, 2)}\n`);
console.log(JSON.stringify(timings, null, 2));

await ctx.close();
await browser.close();
process.exit(bail === null ? 0 : 2);
