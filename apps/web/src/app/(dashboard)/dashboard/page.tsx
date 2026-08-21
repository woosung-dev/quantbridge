// 포트폴리오 개요 코크핏 — 라이브 세션/백테스트/전략 집계 플래그십 페이지
import type { Metadata } from "next";

import { DashboardCockpit } from "@/features/dashboard/components/dashboard-cockpit";

// 페이지 이름 5축 일치(§4.10) — h1·<title> 모두 "워크스페이스"(dashboard-cockpit.tsx SSOT).
export const metadata: Metadata = {
  title: "워크스페이스",
};

export default function DashboardPage() {
  return <DashboardCockpit />;
}
