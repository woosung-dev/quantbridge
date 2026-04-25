// Sprint 11 Phase C: Waitlist React Query key factory.
// Public waitlist POST 는 mutation only — admin 조회만 key factory 필요.

import type { WaitlistStatus } from "./schemas";

export const waitlistKeys = {
  all: (userId: string) => ["waitlist", userId] as const,
  adminLists: (userId: string) =>
    [...waitlistKeys.all(userId), "admin", "list"] as const,
  adminList: (
    userId: string,
    query: { status?: WaitlistStatus; limit?: number; offset?: number },
  ) => [...waitlistKeys.adminLists(userId), query] as const,
};
