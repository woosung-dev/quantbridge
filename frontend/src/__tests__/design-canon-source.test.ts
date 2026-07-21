// 커밋된 소스 텍스트의 캐논 위반 3종을 동결하는 정적 래칫 (이식 seam #3)
//
// 검사 대상.
//   1. 반경 스케일 — `rounded-2xl`/`rounded-3xl` + `rounded-[Npx]` 리터럴. S9 가 비운다.
//   2. 하드코딩 hex — 토큰 정의 계층(`brand-palette.ts`) 밖의 색 리터럴. layout 2건은 S1a.
//   3. 노출 em-dash — 산문에 쓰인 em-dash. S1b ④ 가 판단해 줄인다.
//
// ★grep 만으로 판정하지 않는다 (함정 #5). 아래 `stripComments` 로 주석을 공백 치환한 뒤
// 스캔한다. 이 단계 없이는 `PR #171`(3자리 hex 로 오검) · 주석 안 hex · 주석 안 em-dash 가
// 전부 거짓양성으로 잡힌다. calibration 으로 실증했다 (2026-07-20).
//
// ★em-dash 래칫은 "회귀 동결" 이지 "100건 전부 슬롭" 이라는 판정이 아니다.
// 현재 100건 안에는 정당한 것이 섞여 있다 —
//   - `unsupported-builtin-hints.ts` 29건 = hint 데이터의 절 구분자
//   - `privacy/page.tsx` 6건 = `<strong>Clerk</strong> — 인증` 정의 목록
//   - `kill-switch-modal.tsx` 는 S8 에서 삭제됐다 (죽은 파일). allowlist 에서 함께 제거.
// 이 가드의 역할은 **새 노출 em-dash 를 막는 것** 뿐이다. 어느 것을 실제로 고칠지는
// S1b 의 사람 판단이며, 그때 아래 allowlist 를 함께 줄인다.
//
// 래칫 규율 (기존 `design-canon-tokens.test.ts` 와 동일).
//   - 파일별 카운트가 정확히 일치해야 한다. 늘면 "새 위반", 줄면 "allowlist 갱신하라".
//   - allowlist 에 없는 파일에 위반이 있으면 즉시 빨개진다.

import { readFileSync, readdirSync, statSync } from "node:fs";
import { join, resolve } from "node:path";

import { describe, expect, it } from "vitest";

const SRC = resolve(__dirname, "..");

/**
 * 코드에서 주석을 공백으로 치환한다. 문자열/템플릿 내부의 `//` 는 주석이 아니므로 보존한다
 * (예: `"http://..."`). 문자열 내용은 노출 텍스트일 수 있어 그대로 남긴다.
 *
 * JSX 텍스트의 슬래시(`2/3`)나 `{/* *​/}` 까지 완벽히 처리하진 않지만, 우리가 거르려는
 * 대상(코드 주석에 박힌 hex/em-dash)에는 충분하다. calibration 으로 검증했다.
 */
function stripComments(src: string): string {
  let out = "";
  let i = 0;
  const n = src.length;
  type State = "code" | "line" | "block" | "sq" | "dq" | "tpl";
  let state: State = "code";
  while (i < n) {
    const c = src[i];
    const c2 = src[i + 1];
    if (state === "code") {
      if (c === "/" && c2 === "/") {
        state = "line";
        out += "  ";
        i += 2;
        continue;
      }
      if (c === "/" && c2 === "*") {
        state = "block";
        out += "  ";
        i += 2;
        continue;
      }
      if (c === "'") state = "sq";
      else if (c === '"') state = "dq";
      else if (c === "`") state = "tpl";
      out += c;
      i++;
      continue;
    }
    if (state === "line") {
      if (c === "\n") {
        state = "code";
        out += c;
      } else out += " ";
      i++;
      continue;
    }
    if (state === "block") {
      if (c === "*" && c2 === "/") {
        state = "code";
        out += "  ";
        i += 2;
        continue;
      }
      out += c === "\n" ? "\n" : " ";
      i++;
      continue;
    }
    // 문자열/템플릿 — 이스케이프는 통째로 넘긴다.
    if (c === "\\") {
      out += c + (c2 ?? "");
      i += 2;
      continue;
    }
    if (
      (state === "sq" && c === "'") ||
      (state === "dq" && c === '"') ||
      (state === "tpl" && c === "`")
    ) {
      state = "code";
    }
    out += c;
    i++;
  }
  return out;
}

/** `src/` 아래 프로덕션 `.ts`/`.tsx` 전부. 테스트·스토리는 제외. */
function productionFiles(): string[] {
  const results: string[] = [];
  const walk = (dir: string) => {
    for (const entry of readdirSync(dir)) {
      if (entry === "node_modules" || entry === "__tests__" || entry.startsWith(".")) continue;
      const full = join(dir, entry);
      const stat = statSync(full);
      if (stat.isDirectory()) walk(full);
      else if (
        /\.(ts|tsx)$/.test(full) &&
        !/\.(test|spec)\.(ts|tsx)$/.test(full)
      ) {
        results.push(full);
      }
    }
  };
  walk(SRC);
  return results.sort();
}

const rel = (abs: string) => abs.slice(SRC.length + 1);

/** 파일별 위반 카운트를 센다. `count` 는 주석 제거된 소스에서 위반 수를 반환한다. */
function scanByFile(files: string[], count: (stripped: string) => number): Map<string, number> {
  const byFile = new Map<string, number>();
  for (const abs of files) {
    const c = count(stripComments(readFileSync(abs, "utf-8")));
    if (c > 0) byFile.set(rel(abs), c);
  }
  return byFile;
}

/**
 * 래칫 대조. 정확 일치를 요구한다.
 * @returns `{ grown, shrunk }` — grown = 새 위반, shrunk = 고쳐졌으니 allowlist 갱신 대상.
 */
function diffRatchet(
  actual: Map<string, number>,
  allowed: ReadonlyArray<readonly [string, number]>,
): { grown: string[]; shrunk: string[] } {
  const allowMap = new Map(allowed);
  const grown: string[] = [];
  const shrunk: string[] = [];
  for (const [file, n] of actual) {
    const a = allowMap.get(file) ?? 0;
    if (n > a) grown.push(`${file}: ${n} > 허용 ${a}`);
  }
  for (const [file, a] of allowMap) {
    const n = actual.get(file) ?? 0;
    if (n < a) shrunk.push(`${file}: ${n} < 허용 ${a}`);
  }
  return { grown, shrunk };
}

// ── 카운터 정의 ──────────────────────────────────────────────────────────────

/** `rounded-2xl` / `rounded-3xl` + `rounded-[Npx]` 리터럴. 토큰 var() 기반은 정당하므로 제외. */
const RADIUS = /rounded-(2xl|3xl)\b|rounded-\[[0-9.]+px\]/g;
const countRadius = (s: string) => (s.match(RADIUS) ?? []).length;

/** `#RGB` ~ `#RRGGBBAA` 색 리터럴. */
const HEX = /#[0-9a-fA-F]{3,8}\b/g;
const countHex = (s: string) => (s.match(HEX) ?? []).length;

/**
 * 산문에 쓰인 em-dash — 앞뒤 중 한쪽이라도 단어문자(한글/라틴/숫자)면 산문으로 본다.
 * `<td>—</td>` 같은 고립 플레이스홀더(양쪽 다 비단어)는 정당하므로 세지 않는다.
 */
const WORD = /[\p{L}\p{N}]/u;
function countProseEmDash(s: string): number {
  let cnt = 0;
  for (let i = s.indexOf("—"); i !== -1; i = s.indexOf("—", i + 1)) {
    const prev = s.slice(Math.max(0, i - 3), i).replace(/\s/g, "").slice(-1);
    const next = s.slice(i + 1, i + 4).replace(/\s/g, "").slice(0, 1);
    if (WORD.test(prev || "") || WORD.test(next || "")) cnt++;
  }
  return cnt;
}

// ── allowlist (2026-07-20 calibration 실측) ──────────────────────────────────

/** 반경 리터럴. S9 가 전부 비운다. */
const RADIUS_ALLOWLIST: ReadonlyArray<readonly [string, number]> = [
  // W3-E: onboarding option-card-radio 의 rounded-[10px] 를 var(--r) 로 교체해 0 이 됐다
  // (self focus ring 제거 + C 토큰 정합). 래칫 하강 완료 → 항목 제거.
  // 에러 3종(error.tsx 500 · not-found.tsx 404 · maintenance/page.tsx 503) + 구 컴포넌트
  // error-illustration/error-recovery-box 는 W3-H 에서 screen-13 C 구조로 재스킨하며 반경
  // 리터럴을 var(--r) 시맨틱 소비로 전부 해소했다(구 컴포넌트 2벌은 삭제). 래칫 하강 완료.
  ["app/share/backtests/[token]/_components/share-not-found-state.tsx", 1],
  ["app/share/backtests/[token]/_components/share-revoked-state.tsx", 1],
  ["app/waitlist/_components/waitlist-form-card.tsx", 2],
  ["app/waitlist/_components/waitlist-hero.tsx", 1],
  ["components/skeleton.tsx", 1],
  ["components/tape/pnl-tape.tsx", 1],
  ["components/tape/tape-progress.tsx", 1],
];

/**
 * 하드코딩 hex. `brand-palette.ts`(토큰 정의 SSOT)는 스캔에서 아예 제외한다 — 설계상 hex 집합.
 *   - layout 2건 = S1a 가 `BRAND_PALETTE.dark.bg/light.bg` 참조로 교체 완료 (2026-07-20, 0으로 내림).
 *   - monaco 4건 = Monaco 에디터 테마 색(에디터 API 가 hex 문자열을 받는다). P1 밖, 이연.
 */
const HEX_EXCLUDED = new Set(["lib/brand-palette.ts"]);
const HEX_ALLOWLIST: ReadonlyArray<readonly [string, number]> = [
  ["components/monaco/pine-language.ts", 4],
];

/**
 * 노출 산문 em-dash. ★회귀 동결이지 슬롭 판정이 아니다 (파일 상단 주석 참조).
 * S1b ④ 가 실제로 고칠 것을 골라 줄인다.
 */
const EM_DASH_ALLOWLIST: ReadonlyArray<readonly [string, number]> = [
  ["app/(auth)/_components/brand-panel.tsx", 2],
  // assumptions-card.tsx (구 2건)는 W2 리포트 상세 이식에서 trust-grid 재스킨과 함께 산문
  // em-dash 를 마침표로 교정해 0 이 됐다 → 항목 제거(래칫 하강).
  ["app/(dashboard)/backtests/_components/charts/cost-assumption-heatmap.tsx", 1],
  ["app/(dashboard)/backtests/_components/charts/drawdown-pane.tsx", 1],
  ["app/(dashboard)/backtests/_components/charts/equity-pane.tsx", 1],
  ["app/(dashboard)/backtests/_components/charts/param-stability-heatmap.tsx", 1],
  // W3-A: backtest-form(구 3) · BacktestSizingFieldSet(구 2) · live-settings-badge(구 1)은
  // screen-05 C 이식에서 산문 em-dash 를 마침표·가운뎃점으로 교정해 0 이 됐다 → 항목 제거(래칫 하강).
  ["app/(dashboard)/backtests/_components/monte-carlo-summary-table.tsx", 3],
  ["app/(dashboard)/backtests/_components/report/benchmark-floating-bars.tsx", 1],
  // detailed-results-section.tsx (구 1건)은 W2 에서 심화 분석 시각 카드로 재편하며 벤치마킹
  // 캡션의 em-dash 를 제거해 0 이 됐다 → 항목 제거(래칫 하강).
  ["app/(dashboard)/backtests/_components/report/runup-drawdown-section.tsx", 2],
  ["app/(dashboard)/backtests/_components/report/trade-pnl-pane.tsx", 1],
  // W3-B: strategies em-dash 5건 해소. parse-panel/tab-parse/parse-preview-panel 삭제 +
  // tab-metadata/parse-result-panel C 재작성으로 노출 em-dash 0건 → allowlist 에서 제거.
  // W3-C: optimizer 5파일(bayesian/genetic chart · grid heatmap · pair-selector · oos)도 C 이식에서
  // 노출 산문 em-dash 전부 해소(한국어 카피 교체 + aria-label em-dash 제거) → allowlist 에서 제거.
  ["app/_components/landing-bento.tsx", 1],
  ["app/_components/landing-hero.tsx", 1],
  ["app/disclaimer/page.tsx", 1],
  ["app/privacy/page.tsx", 6], // 정의 목록 (Clerk — 인증). 정당
  ["app/share/backtests/[token]/page.tsx", 2],
  ["app/terms/page.tsx", 1],
  ["components/form-error-inline.tsx", 1],
  ["components/legal-notice-banner.tsx", 1],
  ["components/monaco/pine-language.ts", 3],
  ["features/backtest/utils.ts", 2],
  ["features/live-sessions/components/activity-timeline-chart.tsx", 3],
  ["features/trading/components/test-order-dialog.tsx", 1],
  ["lib/api-base.ts", 1],
  ["lib/unsupported-builtin-hints.ts", 29], // hint 데이터의 절 구분자. 구조적, 슬롭 아님
];

// ── 검사 ──────────────────────────────────────────────────────────────────────

const files = productionFiles();

describe("C 디자인 언어 소스 텍스트 정적 래칫 (이식 seam #3)", () => {
  it("위생 — 프로덕션 소스를 실제로 스캔했다", () => {
    expect(files.length).toBeGreaterThan(200);
  });

  it("stripComments 가 문자열 안 슬래시를 주석으로 오인하지 않는다", () => {
    // 회귀 방어 — URL 의 // 를 지우면 뒤 코드가 통째로 사라진다.
    const kept = stripComments(`const u = "http://x.dev"; const hex = "#abcdef";`);
    expect(kept).toContain("http://x.dev");
    expect(kept).toContain("#abcdef");
    // 라인 주석은 지운다.
    expect(stripComments(`const a = 1; // #ffffff PR #171`)).not.toContain("#ffffff");
  });

  describe("반경 스케일 (S9 가 비운다)", () => {
    const actual = scanByFile(files, countRadius);
    it("allowlist 밖의 새 반경 리터럴이 없다", () => {
      const { grown } = diffRatchet(actual, RADIUS_ALLOWLIST);
      expect(grown, `새 rounded-2xl/3xl/[Npx]:\n${grown.join("\n")}`).toEqual([]);
    });
    it("고쳤으면 RADIUS_ALLOWLIST 도 줄였다", () => {
      const { shrunk } = diffRatchet(actual, RADIUS_ALLOWLIST);
      expect(shrunk, `줄었으니 allowlist 갱신:\n${shrunk.join("\n")}`).toEqual([]);
    });
  });

  describe("하드코딩 hex (layout 2건 S1a)", () => {
    const scanned = files.filter((f) => !HEX_EXCLUDED.has(rel(f)));
    const actual = scanByFile(scanned, countHex);
    it("brand-palette.ts 를 스캔 대상에서 제외했다 (정의 계층)", () => {
      expect(scanned.length).toBe(files.length - HEX_EXCLUDED.size);
    });
    it("allowlist 밖의 새 hex 리터럴이 없다", () => {
      const { grown } = diffRatchet(actual, HEX_ALLOWLIST);
      expect(grown, `토큰 정의 밖 하드코딩 hex:\n${grown.join("\n")}`).toEqual([]);
    });
    it("고쳤으면 HEX_ALLOWLIST 도 줄였다", () => {
      const { shrunk } = diffRatchet(actual, HEX_ALLOWLIST);
      expect(shrunk, `줄었으니 allowlist 갱신:\n${shrunk.join("\n")}`).toEqual([]);
    });
  });

  describe("노출 산문 em-dash (회귀 동결 · S1b ④ 가 감축)", () => {
    const actual = scanByFile(files, countProseEmDash);
    it("allowlist 밖의 새 노출 em-dash 가 없다", () => {
      const { grown } = diffRatchet(actual, EM_DASH_ALLOWLIST);
      expect(grown, `새 노출 산문 em-dash:\n${grown.join("\n")}`).toEqual([]);
    });
    it("줄였으면 EM_DASH_ALLOWLIST 도 갱신했다", () => {
      const { shrunk } = diffRatchet(actual, EM_DASH_ALLOWLIST);
      expect(shrunk, `줄었으니 allowlist 갱신:\n${shrunk.join("\n")}`).toEqual([]);
    });
  });
});
