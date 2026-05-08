// Sprint 43 W13 — /waitlist 외부 첫인상 페이지 (hero + form card + FAQ)
// design source: ui-ux-pro-max master "split-screen value prop + form card" + DESIGN.md 토큰
// 참고: brand-panel.tsx (Sprint 42-polish W1) split layout 패턴

import { WaitlistFaq } from "./_components/waitlist-faq";
import { WaitlistFormCard } from "./_components/waitlist-form-card";
import { WaitlistHero } from "./_components/waitlist-hero";

export default function WaitlistPage() {
  return (
    <main
      id="main-content"
      className="mx-auto max-w-[1200px] px-4 py-10 sm:px-6 sm:py-14 lg:py-20"
    >
      <div className="grid gap-8 lg:grid-cols-[5fr_6fr] lg:gap-12">
        <WaitlistHero />
        <div className="space-y-8">
          <WaitlistFormCard />
          <WaitlistFaq />
        </div>
      </div>
    </main>
  );
}
