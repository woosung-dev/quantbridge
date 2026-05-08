// 랜딩 페이지 (인증 사용자 자동 /strategies redirect + hero + features)
import Link from "next/link";
import { redirect } from "next/navigation";
import { auth } from "@clerk/nextjs/server";

import { GeoBlockBanner } from "@/components/geo-block-banner";

import { LandingFeatures } from "./_components/landing-features";
import { LandingHero } from "./_components/landing-hero";

const TRUST_BRANDS = [
  "Binance",
  "Bybit",
  "OKX",
  "Upbit",
  "Bithumb",
  "Coinbase",
] as const;

export default async function LandingPage() {
  const { userId } = await auth();
  if (userId) {
    redirect("/strategies");
  }

  return (
    <>
      <GeoBlockBanner />
      <main id="main-content" className="bg-[color:var(--bg)]">
        <LandingHero />
        <section
          aria-label="연동 거래소"
          className="border-y border-[color:var(--bg-alt)] bg-[#F8FAFC] px-6 py-8 text-center"
        >
          <p className="text-sm text-[color:var(--text-muted)]">
            100+ 거래소와 연동
          </p>
          <div className="mt-4 flex flex-wrap justify-center gap-3">
            {TRUST_BRANDS.map((b) => (
              <span
                key={b}
                className="rounded-full border border-[color:var(--border)] bg-[color:var(--bg-alt)] px-4 py-1.5 font-mono text-xs font-medium text-[color:var(--text-muted)]"
              >
                {b}
              </span>
            ))}
          </div>
        </section>
        <LandingFeatures />
        <section className="bg-white px-6 py-20 text-center">
          <h2 className="font-display text-3xl font-bold text-[color:var(--text-primary)] md:text-4xl">
            지금 바로 시작하세요
          </h2>
          <p className="mx-auto mt-3 max-w-[480px] text-base text-[color:var(--text-secondary)]">
            Bybit Demo Trading 환경에서 위험 없이 전략을 검증합니다.
          </p>
          <Link
            href="/sign-up"
            className="mt-8 inline-flex h-12 items-center gap-2 rounded-md bg-[color:var(--primary)] px-8 text-sm font-semibold text-white shadow-[0_4px_14px_rgba(37,99,235,0.25)] transition-all duration-200 hover:-translate-y-px hover:scale-[1.02] hover:bg-[color:var(--primary-hover)] hover:shadow-[0_6px_20px_rgba(37,99,235,0.35)]"
          >
            무료로 가입하기
          </Link>
        </section>
      </main>
    </>
  );
}
