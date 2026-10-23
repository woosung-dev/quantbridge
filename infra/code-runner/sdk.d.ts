/** 가격·수량은 decimal 문자열이며 history는 현재 완료봉을 포함한다. */
type Bar = {
  index: number;
  timestamp: string;
  open: string;
  high: string;
  low: string;
  close: string;
  volume: string;
};
type Position = {
  size: string;
  direction: "flat" | "long" | "short";
  average_price: string | null;
};
type Context = {
  bar: Bar;
  history: Bar[];
  position: Position;
  params: Record<string, unknown>;
};
type Intent = { action: "hold" | "long" | "short" | "close" };
