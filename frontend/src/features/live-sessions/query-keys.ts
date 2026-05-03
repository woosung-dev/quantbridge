// Sprint 26 — Live Sessions query key factory.
//
// LESSON-004 H-2 (frontend.md §3.H-2): JWT accessor (`getToken`) 직접 포함 금지.
// `userId` 를 첫 인자로 — Clerk JWT 교체 시 cache 격리 + queryFn 은 module-level
// factory 를 hooks.ts 에서 호출.

export const liveSessionKeys = {
  all: (userId: string) => ["live-sessions", userId] as const,
  list: (userId: string) =>
    [...liveSessionKeys.all(userId), "list"] as const,
  detail: (userId: string, sessionId: string) =>
    [...liveSessionKeys.all(userId), "detail", sessionId] as const,
  state: (userId: string, sessionId: string) =>
    [...liveSessionKeys.all(userId), "state", sessionId] as const,
  events: (userId: string, sessionId: string) =>
    [...liveSessionKeys.all(userId), "events", sessionId] as const,
};
