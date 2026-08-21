// [BL-784] 관측 모드(`PW_ARTIFACT_RUN`)가 만든 `outputDir` 이 `test-results/` **밖**을 못 가리키게 동결한다.
//
// ★왜 필요한가. playwright 는 매 실행의 setup 에서 `outputDir` 을 **통째로 지운다**
//   (`runner/tasks.js` `createRemoveOutputDirsTask`). 그래서 이 경로가 소스 트리를 가리키면
//   e2e 를 한 번 돌리는 것만으로 그 디렉터리가 사라진다. [BL-784] 가 찾아낸 바로 그 기전이
//   증거가 아니라 **코드**를 겨누는 형태다.
//
// ★codex 적대 리뷰(2026-08-17)가 실제로 잡은 자리다. `sanitizeArtifactSegment` 는
//   `[^A-Za-z0-9._-]` 를 치환하는데 `.` 이 허용 문자라 `..` 가 **그대로 통과**했고,
//   `test-results/../chromium` = `apps/web/chromium` 이 됐다. 당시의 배선 테스트
//   (`e2e-project-wiring.test.ts`, ADR-037 철거)는 환경 변수 없이 config 를 import 해 이 경로를 안 지났다 —
//   「가드가 있다」가 아니라 「그 경로가 지나는가」로 재라는 규칙(apps/api/AGENTS.md §10.1)의 사례다.
//
// ★config 를 **파싱하지 않고 import** 한다. 정규식을 여기에 다시 쓰면 실제 배선이 아니라
//   내 복사본을 검사하게 된다.

import path from "node:path";

import { afterEach, describe, expect, it, vi } from "vitest";

const WEB_ROOT = path.resolve(__dirname, "../..");
const ARTIFACT_ROOT = path.join(WEB_ROOT, "test-results");

/** `PW_ARTIFACT_RUN` 을 정하고 config 를 **다시** 평가한다 (모듈 캐시를 비운다). */
async function loadProjects(runName: string) {
  vi.resetModules();
  vi.stubEnv("PW_ARTIFACT_RUN", runName);
  const mod = await import("../../playwright.config");
  const projects = mod.default.projects ?? [];
  expect(projects.length).toBeGreaterThan(0); // ★빈 배열이면 아래 단언이 전부 공허하다
  return projects;
}

afterEach(() => {
  vi.unstubAllEnvs();
  vi.resetModules();
});

describe("PW_ARTIFACT_RUN outputDir 격리", () => {
  it("미설정이면 기본 동작이다 — outputDir 없음 · trace retain-on-failure", async () => {
    const projects = await loadProjects("");
    for (const project of projects) {
      expect(project.outputDir, `${project.name} 는 outputDir 을 갖지 않아야 한다`).toBeUndefined();
    }

    vi.resetModules();
    vi.stubEnv("PW_ARTIFACT_RUN", "");
    const mod = await import("../../playwright.config");
    expect(mod.default.use?.trace).toBe("retain-on-failure");
  });

  it("정상 이름이면 회차·project 두 겹으로 나뉜다", async () => {
    const projects = await loadProjects("gate-load-2");
    for (const project of projects) {
      expect(project.outputDir).toBe(`test-results/gate-load-2/${project.name}`);
    }
  });

  // ★이 케이스가 codex 가 잡은 결함이다. 수리 전에는 `test-results/../chromium` 이 나왔다.
  it.each([
    ["..", "상위 탈출"],
    [".", "현재 디렉터리"],
    ["../..", "두 단계 탈출"],
    ["a/../..", "경로 조각"],
  ])("%s (%s) 를 줘도 test-results/ 밖으로 나가지 않는다", async (evil) => {
    const projects = await loadProjects(evil);
    for (const project of projects) {
      const resolved = path.resolve(WEB_ROOT, project.outputDir as string);
      expect(
        resolved.startsWith(ARTIFACT_ROOT + path.sep),
        `${project.name}: ${project.outputDir} → ${resolved} 가 test-results/ 밖이다`,
      ).toBe(true);
    }
  });
});
