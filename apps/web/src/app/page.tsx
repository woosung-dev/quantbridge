// 랜딩 페이지 (/) — C 디자인 언어 이식. 인증 사용자는 /strategies 로 redirect.
// screen-14-landing.html 6섹션 구조: 히어로 → 기능 → 작동 방식 → 지원 현황 → 성능 → FAQ → 시작.
import { redirect } from "next/navigation";
import { getServerAuth } from "@/lib/auth-server";
import { GeoBlockBanner } from "@/components/geo-block-banner";

import { LandingCta } from "@/features/marketing/components/landing-cta";
import { LandingFaq } from "@/features/marketing/components/landing-faq";
import { LandingFeatures } from "@/features/marketing/components/landing-features";
import { LandingFooter } from "@/features/marketing/components/landing-footer";
import { LandingHero } from "@/features/marketing/components/landing-hero";
import { LandingHowItWorks } from "@/features/marketing/components/landing-how-it-works";
import { LandingNav } from "@/features/marketing/components/landing-nav";
import { LandingPerformance } from "@/features/marketing/components/landing-performance";
import { LandingSupport } from "@/features/marketing/components/landing-support";

export default async function LandingPage() {
  const { userId } = await getServerAuth();
  if (userId) {
    redirect("/strategies");
  }

  return (
    <div className="lp-page">
      <GeoBlockBanner />
      <LandingNav />
      <main id="main-content">
        <div className="page">
          <LandingHero />
          <LandingFeatures />
          <LandingHowItWorks />
          <LandingSupport />
          <LandingPerformance />
          <LandingFaq />
          <LandingCta />
          <LandingFooter />
        </div>
      </main>
    </div>
  );
}
