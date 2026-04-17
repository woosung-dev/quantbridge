// Trading 도메인 query key factory — 서버/클라 공용.

export const tradingKeys = {
  all: ["trading"] as const,
  orders: (limit: number) => [...tradingKeys.all, "orders", limit] as const,
  killSwitch: () => [...tradingKeys.all, "kill-switch"] as const,
  exchangeAccounts: () => [...tradingKeys.all, "exchange-accounts"] as const,
};
