// PWA manifest 색 드리프트 방지 (pwa.md §2.1) — 정적 JSON 이라 brand-palette 를 import 할 수 없다.
// 팔레트를 바꾸고 manifest 를 잊으면 설치 앱의 스플래시·타이틀바만 옛 색으로 남는다.
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { describe, expect, it } from "vitest";

import { BRAND_PALETTE } from "@/lib/brand-palette";

const MANIFEST_PATH = resolve(__dirname, "../../../../public/manifest.webmanifest");
const manifest = JSON.parse(readFileSync(MANIFEST_PATH, "utf-8")) as Record<string, unknown>;

describe("manifest.webmanifest", () => {
  it("background_color 와 theme_color 가 기본 테마(dark) 배경 BRAND_PALETTE.dark.bg 와 같다", () => {
    const darkBg = BRAND_PALETTE.dark.bg.toLowerCase();
    expect(String(manifest.background_color).toLowerCase()).toBe(darkBg);
    expect(String(manifest.theme_color).toLowerCase()).toBe(darkBg);
  });
});
