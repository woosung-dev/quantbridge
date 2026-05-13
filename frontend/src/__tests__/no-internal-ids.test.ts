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
        full.includes("/components/layout/") ||
        full.includes("/features/");
      if (isUserFacing) results.push(full);
    }
  }
  return results;
}

// 내부 dev artifact regex — JSX text content + string literal 만 매칭 (comment 는 OK)
// pattern: 'Sprint N', "Sprint N", `Sprint N`, >Sprint N< (JSX text), 'BL-N', 'ADR-N', 'vectorbt', 'pine_v2'
const INTERNAL_ID_PATTERNS: { name: string; regex: RegExp }[] = [
  {
    name: "Sprint N (e.g. 'Sprint 56', 'Sprint 7d')",
    // 'Sprint NN' inside string literal or JSX text — exclude '*/' or '//' lines
    regex: /(['"`>])\s*Sprint\s+\d+[a-z]?\+?\s*[<'"`)]/gi,
  },
  {
    name: "BL-N (backlog id)",
    regex: /(['"`>])\s*BL-\d+\s*[<'"`)]/gi,
  },
  {
    name: "ADR-N (architecture decision record)",
    regex: /(['"`>])\s*ADR-\d+\s*[<'"`)]/gi,
  },
  {
    name: "vectorbt (internal lib name)",
    // JSX text 또는 string literal
    regex: /(['"`>])\s*vectorbt\s*[<'"`)]/gi,
  },
  {
    name: "pine_v2 (internal module name)",
    regex: /(['"`>])\s*pine_v2\s*[<'"`)]/gi,
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

// comment 라인 (// 또는 /* */) 제거 — JSX text/string 만 검사
function stripComments(content: string): string {
  // /* ... */ block comment 제거 (multiline)
  let cleaned = content.replace(/\/\*[\s\S]*?\*\//g, "");
  // // line comment 제거 (line by line)
  cleaned = cleaned
    .split("\n")
    .map((line) => {
      const idx = line.indexOf("//");
      if (idx < 0) return line;
      // 'http://' 같은 URL 안 '//' 보호 — string literal 안이면 보존
      const before = line.slice(0, idx);
      const quoteCount = (before.match(/["'`]/g) || []).length;
      if (quoteCount % 2 === 1) return line; // 인용부호 안 '//' = string literal 의 일부
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

  for (const { name, regex } of INTERNAL_ID_PATTERNS) {
    it(`no JSX/string content matches ${name}`, () => {
      const violations: { file: string; samples: string[] }[] = [];
      for (const file of files) {
        if (!existsSync(file)) continue;
        const raw = readFileSync(file, "utf-8");
        const cleaned = stripComments(raw);
        const matches = cleaned.match(regex);
        if (matches && matches.length > 0) {
          violations.push({
            file: file.replace(/.*\/quant-bridge\//, ""),
            samples: matches.slice(0, 3),
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
