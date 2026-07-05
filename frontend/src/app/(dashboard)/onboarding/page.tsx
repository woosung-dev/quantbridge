// Onboarding 페이지 (server) — 4-step wizard 클라이언트 로직은 OnboardingView 로 위임.

import { OnboardingView } from "./_components/onboarding-view";

export default function OnboardingPage() {
  return <OnboardingView />;
}
