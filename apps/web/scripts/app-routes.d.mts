// [BL-856] `app-routes.mjs` 의 타입 선언.
//
// ★왜 `.d.mts` 인가 — `screen-evidence-lib.d.mts` 와 같은 이유다. 이 레포의 `tsconfig.json` 은
//   `allowJs: false` 라 `.ts` 테스트가 `.mjs` 를 그냥 import 하면 typecheck 가 깨진다. 그렇다고
//   유틸을 `.ts` 로 쓰면 러너가 로더 없이 못 읽는다. `moduleResolution: "bundler"` 가 `foo.mjs` 를
//   볼 때 `foo.d.mts` 를 먼저 찾으므로 이 파일이 그 틈을 메운다.

/** App Router 디렉터리 경로 → 라우트 패턴. `(group)`·`[[...x]]` 는 사라지고 `[id]` 는 `:id` 가 된다. */
export function toRoutePattern(dirPath: string): string;

/** `appDir` 아래 `page.tsx` 가 만드는 라우트 패턴 전량 (정렬·중복 제거). */
export function listAppRoutes(appDir: string): string[];

/** `:id` 자리를 값으로 채운다. 못 채운 자리가 남으면 throw. */
export function resolveRoute(pattern: string, values: Record<string, string | number>): string;

/** 동적 자리를 가진 라우트인가 (= 정적 목록으로는 도달할 수 없는가). */
export function isDynamic(pattern: string): boolean;
