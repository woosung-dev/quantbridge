// CCXT unified 심볼을 Bybit ticker raw 심볼로 변환한다.
export function toBybitTickerSymbol(symbol: string): string {
  return symbol.split(":", 1)[0]!.replace("/", "").toUpperCase();
}
