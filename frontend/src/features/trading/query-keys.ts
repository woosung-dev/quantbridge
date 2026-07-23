// Trading 도메인 query key factory — 서버/클라 공용.
//
// Sprint FE-02: factory 시그니처에 `userId` identity 추가 (Clerk JWT 교체 시 cache 격리).
// 모든 호출부는 `useAuth().userId ?? "anon"` 를 맨 앞 인자로 넘긴다.

export const tradingKeys = {
  all: (userId: string) => ["trading", userId] as const,
  ordersPrefix: (userId: string) => [...tradingKeys.all(userId), "orders"] as const,
  orders: (userId: string, limit: number, states?: readonly string[]) =>
    [...tradingKeys.ordersPrefix(userId), limit, states ?? []] as const,
  killSwitch: (userId: string) =>
    [...tradingKeys.all(userId), "kill-switch"] as const,
  exchangeAccounts: (userId: string) =>
    [...tradingKeys.all(userId), "exchange-accounts"] as const,
  // Wave 2 — 청산가 계약(W-B). LESSON-005: userId 첫 인자. 파라미터는 계산 입력으로 식별.
  liquidation: (
    userId: string,
    params: { symbol: string; side: string; entry_price: string; leverage: number },
  ) =>
    [
      ...tradingKeys.all(userId),
      "liquidation",
      params.symbol,
      params.side,
      params.entry_price,
      params.leverage,
    ] as const,
};
