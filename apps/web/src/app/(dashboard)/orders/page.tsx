// 주문(Blotter) 페이지 — 라이브·데모 세션 주문 원장 통합 조회
import type { Metadata } from "next";

import { OrdersBlotter } from "./_components/orders-blotter";

// 페이지 이름 5축 일치(§4.10) — nav · breadcrumb · h1 · 푸터 · <title> 모두 "주문".
export const metadata: Metadata = {
  title: "주문",
};

export default function OrdersPage() {
  return <OrdersBlotter />;
}
