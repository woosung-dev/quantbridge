// Onboarding 페이지 (server) — 4-step wizard 클라이언트 로직은 OnboardingView 로 위임.
import type { Metadata } from "next";

import { OnboardingView } from "@/features/onboarding/components/onboarding-view";

// 온보딩 화면(h1 "온보딩" 과 정합). 브랜드 접미는 root template.
export const metadata: Metadata = {
  title: "온보딩",
};

export default function OnboardingPage() {
  return <OnboardingView />;
}
