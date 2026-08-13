// dogfood-restore D1 — 샤프 지수를 컨벤션 SSOT 없이 인쇄하는 회귀 가드.
//
// 왜 필요한가. `sharpe_ratio()` 는 degenerate 실행(거래 0 · 자본 평탄)에서
// **의도적으로 `Decimal("0")` + convention `"unavailable"`** 을 반환한다
// (`backend/src/backtest/engine/metrics.py:76-103`). None 을 반환하면 optimizer
// dead branch 가 되살아나고 FE `.toFixed(2)` 가 깨지기 때문이다. 그래서 값만 보고
// null 검사만 하면 **degenerate 를 자신만만한 `0.00` 으로 인쇄**한다 — 같은
// 백테스트를 리포트는 `—` 로, 대시보드는 `0.00` 으로 보여주는 모순이 된다.
//
// 실제로 이 가드 없이 5곳이 우회하고 있었다(대시보드 · 전략목록 셀 · 전략목록 CSV ·
// share 페이지 · OG 이미지). 계획 단계에서 4곳으로 셌다가 CSV 를 놓쳤다 —
// 사람이 세면 빠진다는 근거 그 자체다.
//
// ★규칙 선택의 근거. 처음엔 "`sharpe_ratio … .toFixed(` 가 한 줄에" 로 잡으려 했으나
// 실측하니 **5곳 중 2곳만** 검출됐다. 나머지는 값을 다른 변수에 옮기거나(`num(sharpe)`)
// 헬퍼를 거쳐(`fmt(toNum(...))`) 포맷해서 한 줄 정규식을 빠져나간다. 그래서 포맷
// 지점이 아니라 **접근 지점**을 잰다 — `.sharpe_ratio` 를 읽는 파일은 컨벤션 SSOT 를
// 반드시 import 해야 한다. 이 규칙은 수정 전 5곳 전부에 RED 다.

import { readFileSync, readdirSync, statSync } from "node:fs";
import { join, relative, resolve } from "node:path";
import { describe, expect, it } from "vitest";

const SRC_ROOT = resolve(__dirname, "..");

// 멤버 접근만 — `objective_metric: "sharpe_ratio"` 같은 문자열 리터럴이나
// 유니온 타입 멤버, 객체 키(`sharpe_ratio:`)는 대상이 아니다. `?.` 도 `.` 로 끝나
// 함께 걸린다.
const MEMBER_ACCESS = /\.\s*sharpe_ratio\b/;
const SSOT_IMPORT = /\bdescribeSharpe\b/;

// 여기서 `sharpe_ratio` 는 지표 **값**이 아니라 optimizer objective-metric 의
// **식별자**다(라벨 맵 키 / `<option value>`). 컨벤션과 무관하다.
const ALLOWED = new Set(
  [
    "features/backtest/sharpe-convention.ts", // SSOT 자신
    "features/optimizer/labels.ts",
    "features/optimizer/components/optimizer-form-fields.tsx",
  ].map((p) => resolve(SRC_ROOT, p)),
);

const SKIP_DIRS = new Set(["__tests__", "node_modules", ".next"]);

function walk(dir: string, out: string[] = []): string[] {
  for (const entry of readdirSync(dir)) {
    const full = join(dir, entry);
    if (statSync(full).isDirectory()) {
      if (!SKIP_DIRS.has(entry)) walk(full, out);
    } else if (/\.tsx?$/.test(entry)) {
      out.push(full);
    }
  }
  return out;
}

describe("샤프 지수는 describeSharpe 를 거쳐야 한다", () => {
  it(".sharpe_ratio 를 읽는 파일은 컨벤션 SSOT 를 import 한다", () => {
    const violations: string[] = [];
    for (const file of walk(SRC_ROOT)) {
      if (ALLOWED.has(file)) continue;
      const source = readFileSync(file, "utf-8");
      if (!MEMBER_ACCESS.test(source)) continue;
      if (SSOT_IMPORT.test(source)) continue;
      violations.push(relative(SRC_ROOT, file));
    }
    expect(
      violations,
      `describeSharpe 없이 .sharpe_ratio 를 읽는다:\n${violations.join("\n")}`,
    ).toEqual([]);
  });
});
