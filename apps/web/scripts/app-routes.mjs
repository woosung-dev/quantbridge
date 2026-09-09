// 앱의 라우트 목록을 **파일 시스템에서** 만든다.
//
// ★왜 이 파일이 있나 — 2026-09-06 전 화면 스윕이 라우트를 **손으로 적은 목록**으로 돌았고,
//   id/토큰이 URL 에 필요한 6개가 통째로 빠졌다. 빠진 줄도 몰랐다(21개를 25개로 셌다).
//   같은 회차의 스윕 스크립트는 scratchpad 에서 돌고 **커밋되지 않아** 다음 회차가 재사용할 수도,
//   고칠 수도 없었다. ⇒ 재발 조건은 「정적 목록」이 아니라 **「목록을 만드는 코드가 레포 밖에 산 것」**이다.
//
// 그래서 목록이 아니라 **목록을 만드는 함수**를 커밋한다. `page.tsx` 가 하나 늘면
// `listAppRoutes()` 가 즉시 그것을 돌려주고, 분류되지 않은 라우트는 래칫이 red 로 잡는다
// (`src/__tests__/app-routes.test.ts`).

import { readdirSync } from "node:fs";
import { join } from "node:path";

/** `page.tsx` 를 가진 디렉터리를 전부 찾는다. */
function findPageDirs(dir, rel = "") {
  const out = [];
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    if (!entry.isDirectory()) {
      if (entry.name === "page.tsx") out.push(rel);
      continue;
    }
    out.push(...findPageDirs(join(dir, entry.name), `${rel}/${entry.name}`));
  }
  return out;
}

/**
 * App Router 의 디렉터리 경로를 라우트 패턴으로 바꾼다.
 *
 * - `(group)`      → 사라진다 (URL 에 안 나온다)
 * - `[[...slug]]`  → 사라진다 (부모 경로 자신이 매치된다 — `/sign-in` 이 그 예다)
 * - `[...slug]`    → `:slug*`
 * - `[id]`         → `:id`
 */
export function toRoutePattern(dirPath) {
  const segments = dirPath
    .split("/")
    .filter(Boolean)
    .filter((s) => !(s.startsWith("(") && s.endsWith(")")))
    .filter((s) => !(s.startsWith("[[") && s.endsWith("]]")))
    .map((s) => {
      if (s.startsWith("[...") && s.endsWith("]")) return `:${s.slice(4, -1)}*`;
      if (s.startsWith("[") && s.endsWith("]")) return `:${s.slice(1, -1)}`;
      return s;
    });
  return segments.length === 0 ? "/" : `/${segments.join("/")}`;
}

/** 앱이 실제로 가진 라우트 패턴 전량. 정렬해서 돌려준다. */
export function listAppRoutes(appDir) {
  return [...new Set(findPageDirs(appDir).map(toRoutePattern))].sort();
}

/** `:id` 같은 자리를 실제 값으로 채운다. 채우지 못한 자리가 남으면 던진다. */
export function resolveRoute(pattern, values) {
  const filled = pattern.replace(/:([A-Za-z0-9_]+)\*?/g, (whole, name) => {
    const v = values[name];
    if (v === undefined) return whole;
    return String(v);
  });
  if (filled.includes(":")) {
    throw new Error(
      `resolveRoute: ${pattern} 의 자리를 못 채웠다 — 값이 없는 키가 있다 (${filled})`,
    );
  }
  return filled;
}

/** 동적 자리를 가진 라우트인가 (= 정적 목록으로는 도달할 수 없는 라우트인가). */
export function isDynamic(pattern) {
  return pattern.includes(":");
}
