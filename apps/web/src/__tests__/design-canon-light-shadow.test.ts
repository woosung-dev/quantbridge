// [BL-853] 라이트 테마 그림자 — 캐논 `--shadow`/`--shadow-hi` 는 다크 프로토타입 값이라
// `:root` 그대로 두면 라이트 카드가 rgba(0,0,0,.55)+.8 을 쓴다(2026-09-06 실측 · shadcn 카드의 약 10배).
// `:root` 는 design-canon-tokens.test.ts 가 캐논과 byte 동일을 핀으로 잡으므로 수리는
// `html:not(.dark)` 오버라이드(KITPORT 밖)다. 이 테스트는 그 오버라이드가 **존재하고 충분히 옅은지**만 잰다.
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

const GLOBALS_CSS = join(__dirname, "..", "styles", "globals.css");
const KITPORT_END = "KITPORT-END";
const LIGHT_ALPHA_MAX = 0.3;

function lightBlock(): string {
  const css = readFileSync(GLOBALS_CSS, "utf-8");
  const endAt = css.indexOf(KITPORT_END);
  expect(endAt).toBeGreaterThan(0);
  const tail = css.slice(endAt);
  const m = tail.match(/^html:not\(\.dark\)\s*\{[\s\S]*?^\}/m);
  expect(m, "html:not(.dark) 그림자 오버라이드 블록이 KITPORT 아래에 있어야 한다").not.toBeNull();
  return m![0];
}

function alphas(block: string, token: string): number[] {
  const line = block.match(new RegExp(`${token}\\s*:\\s*([^;]+);`));
  expect(line, `${token} 이 라이트 오버라이드에 없다`).not.toBeNull();
  const value = line?.[1] ?? "";
  return [...value.matchAll(/rgba\([^)]*,\s*([\d.]+)\)/g)].map((x) => Number(x[1]));
}

describe("[BL-853] 라이트 테마는 다크 그림자를 쓰지 않는다", () => {
  it.each(["--shadow", "--shadow-hi"])("%s 라이트 알파가 전부 %f 이하다", (token) => {
    const a = alphas(lightBlock(), token);
    expect(a.length).toBeGreaterThanOrEqual(2);
    for (const v of a) expect(v).toBeLessThanOrEqual(LIGHT_ALPHA_MAX);
  });

  it("`:root` 캐논값은 그대로다 — 라이트 수리가 다크를 건드리지 않는다", () => {
    const css = readFileSync(GLOBALS_CSS, "utf-8");
    const root = css.match(/^:root\s*\{[\s\S]*?^\}/m)![0];
    expect(root).toContain(
      "--shadow: 0 1px 2px rgba(0, 0, 0, 0.55), 0 10px 26px -14px rgba(0, 0, 0, 0.8);",
    );
  });
});
