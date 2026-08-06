// 모든 e2e spec 이 playwright project 에 **정확히 하나** 물려 있는지 동결한다.
//
// ★왜 필요한가. `playwright.config.ts` 의 project 는 `testMatch` 정규식으로 spec 을 고른다.
// 그 목록이 **파일명 열거식**이면, 새 spec 을 추가하고 목록에 안 적었을 때 그 spec 은
// **발견조차 되지 않는다** — 테스트가 0건 실행돼도 playwright 는 초록이다. 설정 파일의
// 주석이 스스로 그 위험을 경고하고 있었다("열거식 testMatch 라 파일명을 여기 넣지 않으면
// spec 이 발견조차 안 된다 (coverage 함정)"). 실제로 `sprint55-optimizer-bayesian` 이
// 고아가 된 전력이 있다.
//
// ★반대 방향도 막는다. 한 spec 이 **두 project** 에 물리면 같은 테스트가 중복 실행된다.
// 이 감사를 처음 돌렸을 때 `live-smoke.spec.ts` 가 정확히 그 상태였다 —
// `chromium` 의 `/smoke\.spec\.ts$/` 가 앵커가 없어 `live-smoke.spec.ts` 까지 잡았고,
// 전용 project(`chromium-live-smoke`)와 겹쳤다. 그래서 `pnpm e2e` 가 live-smoke 를
// 매번 덤으로 돌리고 있었다.
//
// ★이 테스트는 config 를 **파싱**하지 않고 **import** 한다 — 정규식을 문자열로 다시 쓰면
// 실제 배선이 아니라 내 복사본을 검사하게 된다(이 레포가 반복해서 밟은 함정).

import { readdirSync } from "node:fs";
import path from "node:path";

import { describe, expect, it } from "vitest";

import config from "../../playwright.config";

const E2E_DIR = path.resolve(__dirname, "../../e2e");

/** `e2e/` 안의 spec 파일명 (하위 디렉터리의 fixture/helper 는 spec 이 아니다). */
function specFiles(): string[] {
  return readdirSync(E2E_DIR)
    .filter((f) => f.endsWith(".spec.ts"))
    .sort();
}

/** playwright 가 그 파일을 이 project 에 넣는가 — testMatch/testIgnore 를 실제 값으로 평가. */
function matches(pattern: unknown, relPath: string): boolean {
  if (pattern instanceof RegExp) return pattern.test(relPath);
  if (Array.isArray(pattern)) return pattern.some((p) => matches(p, relPath));
  if (typeof pattern === "string") return relPath.endsWith(pattern);
  return false;
}

function owningProjects(relPath: string): string[] {
  return (config.projects ?? [])
    .filter((p) => {
      const name = p.name ?? "";
      if (name === "setup") return false; // global.setup.ts 전용 — spec 이 아니다
      if (!matches(p.testMatch, relPath)) return false;
      if (p.testIgnore && matches(p.testIgnore, relPath)) return false;
      return true;
    })
    .map((p) => p.name ?? "(unnamed)");
}

describe("e2e project 배선", () => {
  it("모든 spec 이 정확히 한 project 에 속한다", () => {
    const files = specFiles();
    expect(files.length).toBeGreaterThan(10); // 음성 대조 — 수집이 죽으면 여기서 잡는다

    const orphans: string[] = [];
    const duplicates: Array<[string, string[]]> = [];

    for (const f of files) {
      const owners = owningProjects(`e2e/${f}`);
      if (owners.length === 0) orphans.push(f);
      else if (owners.length > 1) duplicates.push([f, owners]);
    }

    expect(
      { orphans, duplicates },
      `고아(어느 project 에도 안 물려 실행조차 안 됨): ${JSON.stringify(orphans)}\n` +
        `중복(두 project 에서 같은 spec 을 돌림): ${JSON.stringify(duplicates)}`,
    ).toEqual({ orphans: [], duplicates: [] });
  });

  it("authed project 는 열거식이 아니라 잔여 전체를 가져간다", () => {
    // ★열거식으로 되돌아가면 새 authed spec 이 다시 조용히 누락된다.
    //   `testMatch` 에 개별 파일명이 나열돼 있으면 빨개진다.
    const authed = (config.projects ?? []).find((p) => p.name === "chromium-authed");
    expect(authed, "chromium-authed project 가 사라졌다").toBeTruthy();

    const src = String(authed?.testMatch);
    expect(
      src.includes("trading-ui") || src.includes("dogfood-flow"),
      `chromium-authed.testMatch 가 파일명을 열거하고 있다: ${src}\n` +
        "잔여 전체를 가져가고 다른 project 몫만 testIgnore 로 빼는 형태여야 한다.",
    ).toBe(false);
  });
});
