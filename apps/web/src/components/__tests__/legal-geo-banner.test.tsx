// LegalNoticeBanner·GeoBlockBanner — 법무 링크·접근성·지역 정책 계약 테스트.

import { afterEach, describe, expect, it } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";

import { GeoBlockBanner } from "../geo-block-banner";
import { LegalNoticeBanner } from "../legal-notice-banner";
import { LEGAL_LINKS } from "@/lib/legal-links";

describe("LegalNoticeBanner and GeoBlockBanner", () => {
  afterEach(() => {
    cleanup();
  });

  it("법무 링크 3개가 LEGAL_LINKS를 그대로 사용한다", () => {
    render(<LegalNoticeBanner />);

    const expectedLinks = [
      ["면책조항", LEGAL_LINKS.disclaimer],
      ["이용약관", LEGAL_LINKS.terms],
      ["개인정보 처리방침", LEGAL_LINKS.privacy],
    ] as const;

    expectedLinks.forEach(([name, href]) => {
      expect(screen.getByRole("link", { name })).toHaveAttribute("href", href);
    });
  });

  it("법무 링크 3개가 서로 다른 문서로 연결된다", () => {
    render(<LegalNoticeBanner />);

    const hrefs = screen.getAllByRole("link").map((link) => link.getAttribute("href"));
    expect(new Set(hrefs).size).toBe(3);
  });

  it("투자 자문이 아니라는 고지 문장을 표시한다", () => {
    render(<LegalNoticeBanner />);

    expect(screen.getByRole("note")).toHaveTextContent("투자 자문이 아니");
  });

  it("두 배너 모두 스크린리더용 note 역할을 가진다", () => {
    const legal = render(<LegalNoticeBanner />);
    const geo = render(<GeoBlockBanner />);

    expect(legal.container.querySelectorAll('[role="note"]')).toHaveLength(1);
    expect(geo.container.querySelectorAll('[role="note"]')).toHaveLength(1);
  });

  it("법무 링크 3개가 44px 터치 타겟 클래스를 가진다", () => {
    render(<LegalNoticeBanner />);

    screen.getAllByRole("link").forEach((link) => {
      expect(link).toHaveClass("min-h-11");
    });
  });

  it("지역 배너가 Asia-Pacific 제공 범위와 US·EU 가입 제한을 알린다", () => {
    render(<GeoBlockBanner />);

    const notice = screen.getByRole("note");
    expect(notice).toHaveTextContent("Asia-Pacific");
    expect(notice.textContent).toMatch(/US and EU.*not eligible.*signup/);
  });

  it("두 배너는 서로 다른 안내이며 지역 배너에는 링크가 없다", () => {
    const legalText = render(<LegalNoticeBanner />).container.textContent;
    const geo = render(<GeoBlockBanner />);

    expect(geo.container.textContent).not.toBe(legalText);
    expect(geo.container.querySelectorAll("a")).toHaveLength(0);
  });

  it("두 컴포넌트는 함수이고 비어 있지 않은 안내를 렌더한다", () => {
    expect(typeof LegalNoticeBanner).toBe("function");
    expect(typeof GeoBlockBanner).toBe("function");

    const legal = render(<LegalNoticeBanner />);
    const geo = render(<GeoBlockBanner />);

    expect(legal.container.textContent?.length ?? 0).toBeGreaterThanOrEqual(20);
    expect(geo.container.textContent?.length ?? 0).toBeGreaterThanOrEqual(20);
  });
});
