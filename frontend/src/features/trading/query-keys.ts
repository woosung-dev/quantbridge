// Trading 도메인 query key factory — 서버/클라 공용.
//
// Sprint FE-02: factory 시그니처에 `userId` identity 추가 (Clerk JWT 교체 시 cache 격리).
// 모든 호출부는 `useAuth().userId ?? "anon"` 를 맨 앞 인자로 넘긴다.

export const tradingKeys = {
  all: (userId: string) => ["trading", userId] as const,
  orders: (userId: string, limit: number) =>
    [...tradingKeys.all(userId), "orders", limit] as const,
  killSwitch: (userId: string) =>
    [...tradingKeys.all(userId), "kill-switch"] as const,
  exchangeAccounts: (userId: string) =>
    [...tradingKeys.all(userId), "exchange-accounts"] as const,
};
