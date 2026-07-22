// 트레이딩 코크핏 라우트 — C 디자인 언어 이식 (S8). 프로토타입 screen-01 구조를 소비하는
// 단일 클라이언트 코크핏(TradingCockpit)에 렌더를 위임한다. 라우트 레벨 예외는 error.tsx,
// 초기 로딩은 loading.tsx 가 처리한다.

import type { Metadata } from "next";

import { TradingCockpit } from "./_components/trading-cockpit";

export const metadata: Metadata = {
  title: "트레이딩",
};

export default function TradingPage() {
  return <TradingCockpit />;
}
