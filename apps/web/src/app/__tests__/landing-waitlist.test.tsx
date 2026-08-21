// 랜딩과 웨이트리스트의 로그인 전 서버 렌더 계약을 고정한다.
// 랜딩은 인증 갈래가 렌더보다 먼저 끝나야 하고, 웨이트리스트는 이메일만 정규화한다.

import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, describe, expect, it, vi } from "vitest";

const landingSectionMocks = vi.hoisted(() => ({
  GeoBlockBanner: vi.fn(),
  LandingCta: vi.fn(),
  LandingFaq: vi.fn(),
  LandingFeatures: vi.fn(),
  LandingFooter: vi.fn(),
  LandingHero: vi.fn(),
  LandingHowItWorks: vi.fn(),
  LandingNav: vi.fn(),
  LandingPerformance: vi.fn(),
  LandingSupport: vi.fn(),
}));

const waitlistMocks = vi.hoisted(() => ({
  WaitlistFormCard: vi.fn(),
}));

vi.mock("@/lib/auth-server", () => ({
  getServerAuth: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  redirect: vi.fn(),
}));

vi.mock("@/components/geo-block-banner", () => ({
  GeoBlockBanner: () => {
    landingSectionMocks.GeoBlockBanner();
    return <span data-testid="landing-GeoBlockBanner" />;
  },
}));

vi.mock("@/features/marketing/components/landing-cta", () => ({
  LandingCta: () => {
    landingSectionMocks.LandingCta();
    return <span data-testid="landing-LandingCta" />;
  },
}));

vi.mock("@/features/marketing/components/landing-faq", () => ({
  LandingFaq: () => {
    landingSectionMocks.LandingFaq();
    return <span data-testid="landing-LandingFaq" />;
  },
}));

vi.mock("@/features/marketing/components/landing-features", () => ({
  LandingFeatures: () => {
    landingSectionMocks.LandingFeatures();
    return <span data-testid="landing-LandingFeatures" />;
  },
}));

vi.mock("@/features/marketing/components/landing-footer", () => ({
  LandingFooter: () => {
    landingSectionMocks.LandingFooter();
    return <span data-testid="landing-LandingFooter" />;
  },
}));

vi.mock("@/features/marketing/components/landing-hero", () => ({
  LandingHero: () => {
    landingSectionMocks.LandingHero();
    return <span data-testid="landing-LandingHero" />;
  },
}));

vi.mock("@/features/marketing/components/landing-how-it-works", () => ({
  LandingHowItWorks: () => {
    landingSectionMocks.LandingHowItWorks();
    return <span data-testid="landing-LandingHowItWorks" />;
  },
}));

vi.mock("@/features/marketing/components/landing-nav", () => ({
  LandingNav: () => {
    landingSectionMocks.LandingNav();
    return <span data-testid="landing-LandingNav" />;
  },
}));

vi.mock("@/features/marketing/components/landing-performance", () => ({
  LandingPerformance: () => {
    landingSectionMocks.LandingPerformance();
    return <span data-testid="landing-LandingPerformance" />;
  },
}));

vi.mock("@/features/marketing/components/landing-support", () => ({
  LandingSupport: () => {
    landingSectionMocks.LandingSupport();
    return <span data-testid="landing-LandingSupport" />;
  },
}));

vi.mock("@/components/exchange-support-table", () => ({
  ExchangeSupportTable: () => <span data-testid="waitlist-ExchangeSupportTable" />,
}));

vi.mock("@/features/waitlist/components/waitlist-faq", () => ({
  WaitlistFaq: () => <span data-testid="waitlist-WaitlistFaq" />,
}));

vi.mock("@/features/waitlist/components/waitlist-form-card", () => ({
  WaitlistFormCard: ({ defaultEmail }: { defaultEmail: string }) => {
    waitlistMocks.WaitlistFormCard(defaultEmail);
    return <span data-testid="waitlist-WaitlistFormCard" />;
  },
}));

vi.mock("@/features/waitlist/components/waitlist-header", () => ({
  WaitlistHeader: () => <span data-testid="waitlist-WaitlistHeader" />,
}));

vi.mock("@/features/waitlist/components/waitlist-hero", () => ({
  WaitlistHero: () => <span data-testid="waitlist-WaitlistHero" />,
}));

vi.mock("@/features/waitlist/components/waitlist-product", () => ({
  WaitlistProduct: () => <span data-testid="waitlist-WaitlistProduct" />,
}));

import * as LandingPageModule from "../page";
import LandingPage from "../page";
import WaitlistPage, { metadata as waitlistMetadata } from "../waitlist/page";
import { getServerAuth } from "@/lib/auth-server";
import { redirect } from "next/navigation";

const mockedGetServerAuth = vi.mocked(getServerAuth);
const mockedRedirect = vi.mocked(redirect);

const LANDING_SECTION_NAMES = [
  "GeoBlockBanner",
  "LandingNav",
  "LandingHero",
  "LandingFeatures",
  "LandingHowItWorks",
  "LandingSupport",
  "LandingPerformance",
  "LandingFaq",
  "LandingCta",
  "LandingFooter",
] as const;

async function renderAnonymousLanding(): Promise<string> {
  mockedGetServerAuth.mockResolvedValue({ userId: null, token: null });
  const page = await LandingPage();
  return renderToStaticMarkup(page);
}

async function renderWaitlist(searchParams: unknown): Promise<string> {
  const page = await WaitlistPage({
    searchParams: Promise.resolve(searchParams as { email?: string }),
  });
  return renderToStaticMarkup(page);
}

afterEach(() => vi.resetAllMocks());

describe("랜딩 페이지의 인증 전 서버 렌더", () => {
  it("userId 가 있으면 정확히 한 번 /strategies 로 redirect 한다", async () => {
    mockedGetServerAuth.mockResolvedValue({ userId: "user-123", token: "token" });

    await LandingPage();

    expect(mockedRedirect).toHaveBeenCalledOnce();
    expect(mockedRedirect).toHaveBeenCalledWith("/strategies");
  });

  it("redirect 가 던지면 랜딩 섹션을 렌더하지 않고 즉시 끝난다", async () => {
    const redirectSignal = new Error("NEXT_REDIRECT");
    mockedGetServerAuth.mockResolvedValue({ userId: "user-123", token: "token" });
    mockedRedirect.mockImplementation(() => {
      throw redirectSignal;
    });

    await expect(LandingPage()).rejects.toThrow(redirectSignal);

    expect(mockedRedirect).toHaveBeenCalledOnce();
    for (const name of LANDING_SECTION_NAMES) {
      expect(landingSectionMocks[name]).not.toHaveBeenCalled();
    }
  });

  it("userId 가 null 이면 redirect 하지 않고 랜딩을 렌더한다", async () => {
    const html = await renderAnonymousLanding();

    expect(mockedRedirect).not.toHaveBeenCalled();
    expect(html).not.toBe("");
  });

  it("skip link 목적지 #main-content 를 가진다", async () => {
    const html = await renderAnonymousLanding();

    expect(html).toContain('id="main-content"');
  });

  it("page.tsx 가 조립하는 모든 마케팅 섹션을 렌더한다", async () => {
    await renderAnonymousLanding();

    for (const name of LANDING_SECTION_NAMES) {
      expect(landingSectionMocks[name]).toHaveBeenCalledOnce();
    }
  });

  it("제한 지역 안내용 GeoBlockBanner 를 렌더한다", async () => {
    await renderAnonymousLanding();

    expect(landingSectionMocks.GeoBlockBanner).toHaveBeenCalledOnce();
  });
});

describe("웨이트리스트 이메일 프리필", () => {
  it("단일 email 쿼리를 WaitlistFormCard 로 그대로 전달한다", async () => {
    await renderWaitlist({ email: "a@b.co" });

    expect(waitlistMocks.WaitlistFormCard).toHaveBeenCalledOnce();
    expect(waitlistMocks.WaitlistFormCard).toHaveBeenCalledWith("a@b.co");
  });

  it.each([
    ["email 값 undefined", { email: undefined }],
    ["배열", { email: ["a@b.co"] }],
    ["email 키 없음", {}],
  ])("%s 입력은 빈 문자열로 정규화한다", async (_label, searchParams) => {
    await renderWaitlist(searchParams);

    expect(waitlistMocks.WaitlistFormCard).toHaveBeenCalledOnce();
    expect(waitlistMocks.WaitlistFormCard).toHaveBeenCalledWith("");
  });
});

describe("마케팅 페이지 메타데이터", () => {
  it("웨이트리스트 title·description 은 비어 있지 않고 랜딩은 metadata 를 내보내지 않는다", () => {
    expect(waitlistMetadata.title).toBeTruthy();
    expect(waitlistMetadata.description).toBeTruthy();

    // root layout title template 이 이미 브랜드명을 붙인다.
    // 랜딩이 title 을 내보내지 않아 "QuantBridge · QuantBridge" 중복을 막는다.
    expect(LandingPageModule).not.toHaveProperty("metadata");
  });
});
