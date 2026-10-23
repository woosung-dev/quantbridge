import type { Order } from "../../schemas";

// 코드 부분 체결 취소·거부는 서버가 실제 체결 증거를 확인한 경우에만 손익을 표시한다.
// 목록·상세·CSV가 같은 판정을 쓰며 서로의 화면 모듈을 import하지 않는다.
export function displayRealizedPnl(order: Order): string | null {
  const recordedFill =
    order.state === "filled" ||
    ((order.state === "cancelled" || order.state === "rejected") &&
      order.has_recorded_fill === true);
  return recordedFill && order.realized_pnl != null ? order.realized_pnl : null;
}

export function realizedPnlSource(order: Order): "confirmed" | "estimated" {
  return order.realized_pnl_synced_at != null ? "confirmed" : "estimated";
}
