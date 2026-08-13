// Sprint 60 S2 — T-2 가짜 marketing 수치 + testimonial + Disclaimer 자가 명시 회귀 차단 RED test
//
// Multi-Agent QA 2026-05-13 (Curious persona, BL-270/271/273) 발견:
// landing/auth/legal 페이지에 hardcoded fake metrics (10,000+ 트레이더 / $2.4B 거래량 /
// 99.97% uptime / 156 거래소) + 가짜 testimonial ("김지훈/박민하") + Disclaimer
// "법적 효력 제한적" 자가 명시 → 한국 표시광고법 위반 가능 + 신뢰 영구 파괴.
//
// Fix scope: user-facing 페이지 (app/) + landing components 에서 known fake string 0 match.
// Beta 자기 명시 ("Beta — early dogfooder") 만 정직 표시 유지.
//
// Sprint 60 S2 P1-6 채택 (codex G.0 review) — 섹션 기반 assertion 으로 false-positive 회피.

import { readFileSync, readdirSync, statSync, existsSync } from "node:fs";
import { join, resolve } from "node:path";
import { describe, expect, it } from "vitest";

function walkSync(
  dir: string,
  extensions: string[],
  results: string[] = [],
): string[] {
  for (const entry of readdirSync(dir)) {
    if (entry === "node_modules" || entry === "__tests__" || entry.startsWith(".")) {
      continue;
    }
    const full = join(dir, entry);
    const stat = statSync(full);
    if (stat.isDirectory()) {
      walkSync(full, extensions, results);
    } else if (
      stat.isFile() &&
      extensions.some((ext) => full.endsWith(ext)) &&
      !full.endsWith(".test.ts") &&
      !full.endsWith(".test.tsx") &&
      !full.endsWith(".spec.ts")
    ) {
      results.push(full);
    }
  }
  return results;
}

// known fake marketing strings — Multi-Agent QA 발견 + codex G.2 P1-2 확장
const FAKE_MARKETING_STRINGS = [
  // 수치 (BL-270)
  "10,000+",
  "10000+",
  "$2.4B",
  "2.4B",
  "99.97%",
  "99.97",
  "156+ 거래소",
  "156 거래소",
  "100+ 거래소", // codex G.2 P1-2
  "7,234",
  "7234",
  // testimonial (BL-271)
  "김지훈",
  "박민하",
  // Disclaimer 자가 명시 (BL-273)
  "법적 효력 제한적",
  "법무 임시",
  // codex G.2 P1-2 — hardcoded dashboard mock values (without "예시" / "샘플" label)
  "$124,580",
  "+$2,340",
  "7일 연속 수익",
  // Enterprise SLA 보증 (unsubstantiated claim)
  "SLA 보장",
];

// 스캔 대상 = user-facing page + landing components (test/storybook 제외)
function getUserFacingFiles(): string[] {
  const root = resolve(__dirname, "..");
  const exts = [".tsx", ".ts"];
  const results: string[] = [];
  for (const subdir of ["app", "components", "features"]) {
    const dir = join(root, subdir);
    if (existsSync(dir)) {
      walkSync(dir, exts, results);
    }
  }
  return results;
}

describe("BL-270/271/273 — no fake marketing in user-facing UI", () => {
  const files = getUserFacingFiles();

  it("inventory scan returns > 0 files (sanity)", () => {
    expect(files.length).toBeGreaterThan(20);
  });

  for (const fakeStr of FAKE_MARKETING_STRINGS) {
    it(`no file contains fake marketing string ${JSON.stringify(fakeStr)}`, () => {
      const matches: string[] = [];
      for (const file of files) {
        if (!existsSync(file)) continue;
        const content = readFileSync(file, "utf-8");
        if (content.includes(fakeStr)) {
          matches.push(file);
        }
      }
      expect(
        matches,
        `BL-270/271/273 — fake marketing ${JSON.stringify(fakeStr)} found in:\n${matches.join("\n")}`,
      ).toEqual([]);
    });
  }
});
