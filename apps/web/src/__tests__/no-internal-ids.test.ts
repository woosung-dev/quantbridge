// Sprint 60 S2 — T-3 내부 dev artifact ID (Sprint N / BL-N / ADR-N / vectorbt / pine_v2) UI 노출 회귀 차단 RED test
//
// Multi-Agent QA 2026-05-13 (QA Sentinel + Curious + Casual 3 페르소나 ★★★ 공통 발견):
// /optimizer 페이지 H1 = "Optimizer (Sprint 56)", form 안 "BL-186 후속" / "vectorbt 벡터화
// 엔진 사용", BetaBanner "법무 임시" — 모두 internal dev artifact 가 user-facing UI 에 노출.
// → "internal dev tool" 인상 + 사용자 신뢰 즉시 저하 (Curious NPS 2/10 결정타).
//
// Fix scope: user-facing route inventory (15-25 page, P1-5 채택) 전체 + 도메인 components
// 에서 internal ID regex 0 match. Comment 안 내부 ID 는 OK (JSX text/string 만 차단).
//
// Sprint 60 S2 P1-5 채택 (codex G.0 review) — route inventory 전체 의무.

import { readFileSync, readdirSync, statSync, existsSync } from "node:fs";
import { basename, join, resolve } from "node:path";
import { describe, expect, it } from "vitest";

function walkPagesAndComponents(
  dir: string,
  results: string[] = [],
): string[] {
  for (const entry of readdirSync(dir)) {
    if (entry === "node_modules" || entry === "__tests__" || entry.startsWith(".")) {
      continue;
    }
    const full = join(dir, entry);
    const stat = statSync(full);
    if (stat.isDirectory()) {
      walkPagesAndComponents(full, results);
    } else if (
      stat.isFile() &&
      full.endsWith(".tsx") &&
      !full.endsWith(".test.tsx") &&
      !full.endsWith(".spec.tsx")
    ) {
      const name = basename(full);
      // user-facing 만 — page.tsx / layout.tsx / *_components/*.tsx
      const isUserFacing =
        name === "page.tsx" ||
        name === "layout.tsx" ||
        full.includes("/_components/") ||
        (full.includes("/components/") && !full.includes("/components/ui/")) ||
        full.includes("/features/");
      if (isUserFacing) results.push(full);
    }
  }
  return results;
}

// 내부 dev artifact regex — JSX text content + string literal anywhere (comment 는 stripComments 로 제외)
// codex G.2 P1-1 강화 — embedded `Optimizer (Sprint 56)` / `ADR-013 §6` / `BL-233 self-impl` / `vectorbt 벡터화` 모두 catch
const INTERNAL_ID_PATTERNS: { name: string; regex: RegExp }[] = [
  {
    name: "Sprint N (e.g. 'Sprint 56', 'Sprint 7d+')",
    regex: /\bSprint\s+\d+[a-z]?\+?\b/gi,
  },
  {
    name: "BL-N (backlog id)",
    regex: /\bBL-\d+\b/gi,
  },
  {
    name: "ADR-N (architecture decision record)",
    regex: /\bADR-\d+\b/gi,
  },
  {
    name: "vectorbt (internal lib name)",
    regex: /\bvectorbt\b/gi,
  },
  {
    name: "pine_v2 (internal module name)",
    regex: /\bpine_v2\b/gi,
  },
];

// 스캔 대상 = user-facing page + components (test/storybook 제외)
function getUserFacingFiles(): string[] {
  const root = resolve(__dirname, "..");
  const results: string[] = [];
  for (const subdir of ["app", "components", "features"]) {
    const dir = join(root, subdir);
    if (existsSync(dir)) {
      walkPagesAndComponents(dir, results);
    }
  }
  return results;
}

// comment 라인 (// 또는 /* */ 또는 JSX {/* */} 또는 JSDoc * line) 제거 — JSX text/string 만 검사
function stripComments(content: string): string {
  // /* ... */ block comment 제거 (multiline + JSX block comment {/* ... */})
  let cleaned = content.replace(/\{?\/\*[\s\S]*?\*\/\}?/g, "");
  // line-by-line filter
  cleaned = cleaned
    .split("\n")
    .map((line) => {
      const trimmed = line.trimStart();
      // JSDoc `* line` (block comment 안 continuation) — block 제거 후 잔존 가능
      if (trimmed.startsWith("*")) return "";
      // line comment `// ...`
      const idx = line.indexOf("//");
      if (idx < 0) return line;
      const before = line.slice(0, idx);
      const quoteCount = (before.match(/["'`]/g) || []).length;
      if (quoteCount % 2 === 1) return line; // string literal 안 '//' 보존
      return before;
    })
    .join("\n");
  return cleaned;
}

describe("BL-265/280/303 — no internal dev artifact IDs in user-facing UI (★★★ 3-persona common)", () => {
  const files = getUserFacingFiles();

  it("route inventory returns reasonable file count (P1-5 sanity)", () => {
    expect(files.length).toBeGreaterThan(14);
    expect(files.length).toBeLessThan(300); // features/ + _components 합 ~155
  });

  // codex G.2 P2-3 채택 — critical route 명시 포함 의무
  it("critical user-facing routes are scanned (codex G.2 P2-3)", () => {
    const required = [
      "/app/page.tsx",
      "/brand-panel.tsx",
      "/optimizer/page.tsx",
      "/backtest-form.tsx",
      "/strategies/new",
      "/terms/page.tsx",
      "/disclaimer/page.tsx",
      "/legal-notice-banner.tsx",
      "/features/live-sessions",
    ];
    for (const req of required) {
      const matched = files.some((f) => f.includes(req));
      expect(matched, `critical route missing from inventory: ${req}`).toBe(
        true,
      );
    }
  });

  for (const { name, regex } of INTERNAL_ID_PATTERNS) {
    it(`no JSX/string content matches ${name}`, () => {
      const violations: { file: string; samples: string[] }[] = [];
      for (const file of files) {
        if (!existsSync(file)) continue;
        const raw = readFileSync(file, "utf-8");
        const cleaned = stripComments(raw);
        // content-wide — codex G.2 재호출 P1-2 채택: multi-line JSX text 도 검출
        // 휴리스틱: match 의 absolute position 기준 가장 가까운 `>` (before)/`<` (after) 또는 quote 검사
        const userFacingMatches: string[] = [];
        const globalRegex = new RegExp(regex.source, regex.flags);
        let m: RegExpExecArray | null;
        while ((m = globalRegex.exec(cleaned)) !== null) {
          const matched = m[0];
          const matchStart = m.index;
          const before = cleaned.slice(Math.max(0, matchStart - 500), matchStart);
          const after = cleaned.slice(
            matchStart + matched.length,
            matchStart + matched.length + 500,
          );
          // (a) string literal context — match 가 lin 안 unmatched quote 뒤
          const lineStart = cleaned.lastIndexOf("\n", matchStart - 1) + 1;
          const beforeOnLine = cleaned.slice(lineStart, matchStart);
          const quotesBefore = (beforeOnLine.match(/["'`]/g) || []).length;
          const inString = quotesBefore % 2 === 1;
          // (b) JSX text context — match 의 nearest `>` (before) 다음 + nearest `<` (after) 앞
          const gtBeforeIdx = before.lastIndexOf(">");
          const ltBeforeIdx = before.lastIndexOf("<");
          const isJsxText = gtBeforeIdx > ltBeforeIdx && after.indexOf("<") >= 0;
          if (inString || isJsxText) {
            userFacingMatches.push(matched);
          }
        }
        if (userFacingMatches.length > 0) {
          violations.push({
            file: file.replace(/.*\/quant-bridge\//, ""),
            samples: userFacingMatches.slice(0, 3),
          });
        }
      }
      expect(
        violations,
        `BL-265/280/303 — internal artifact ${name} found in user-facing UI:\n${violations
          .map((v) => `  ${v.file}: ${v.samples.join(", ")}`)
          .join("\n")}`,
      ).toEqual([]);
    });
  }
});
