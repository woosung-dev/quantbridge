/**
 * 사용자 거래 경로의 제품 정책 SSOT.
 *
 * 목록 응답은 기존 데이터 호환을 위해 legacy exchange/mode 값을 계속 받을 수 있다.
 * 단, 잔고·포지션·주문·새 라이브 세션의 대상에는 Bybit Demo만 들어갈 수 있다.
 */
export type ExchangeAccountCandidate = {
  exchange: string;
  mode: string;
};

export function isBybitDemoAccount(account: ExchangeAccountCandidate): boolean {
  return account.exchange === "bybit" && account.mode === "demo";
}
