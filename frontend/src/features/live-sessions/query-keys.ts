// Sprint 26 — Live Sessions query key factory.
//
// LESSON-004 H-2 (frontend.md §3.H-2): JWT accessor (`getToken`) 직접 포함 금지.
// `userId` 를 첫 인자로 — Clerk JWT 교체 시 cache 격리 + queryFn 은 module-level
// factory 를 hooks.ts 에서 호출.

export const liveSessionKeys = {
  all: (userId: string) => ["live-sessions", userId] as const,
  list: (userId: string) => [...liveSessionKeys.all(userId), "list"] as const,
  listWithInactive: (userId: string) =>
    [...liveSessionKeys.list(userId), "with-inactive"] as const,
  detail: (userId: string, sessionId: string) =>
    [...liveSessionKeys.all(userId), "detail", sessionId] as const,
  state: (userId: string, sessionId: string) =>
    [...liveSessionKeys.all(userId), "state", sessionId] as const,
  outcomeParity: (userId: string, sessionId: string) =>
    [...liveSessionKeys.all(userId), "outcome-parity", sessionId] as const,
  events: (userId: string, sessionId: string) =>
    [...liveSessionKeys.all(userId), "events", sessionId] as const,
  positionsPrefix: (userId: string) => [...liveSessionKeys.all(userId), "positions"] as const,
  positions: (userId: string, sessionId: string) =>
    [...liveSessionKeys.positionsPrefix(userId), sessionId] as const,
  // BL-498 — 계정 스코프 포지션. `positionsPrefix` 아래 두어 청산 성공 시 기존
  // invalidate 가 세션 표와 계정 표를 **함께** 무효화하게 한다(둘이 같은 포지션을
  // 보여주므로 한쪽만 갱신되면 화면이 서로 모순된다).
  accountPositions: (userId: string, accountId: string) =>
    [...liveSessionKeys.positionsPrefix(userId), "account", accountId] as const,
};
