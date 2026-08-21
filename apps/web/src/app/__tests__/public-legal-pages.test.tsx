// 공개 법무 페이지 — 로그인 전 화면의 구조·연락 경로·라우트 정합성을 고정한다.

import type { ComponentType } from "react";
import { afterEach, describe, expect, it } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";

import DisclaimerPage, { metadata as disclaimerMetadata } from "../disclaimer/page";
import NotAvailablePage, { metadata as notAvailableMetadata } from "../not-available/page";
import PrivacyPage, { metadata as privacyMetadata } from "../privacy/page";
import TermsPage, { metadata as termsMetadata } from "../terms/page";
import { LEGAL_LINKS } from "@/lib/legal-links";

type PublicPage = {
  name: string;
  route: string;
  Page: ComponentType;
};

const LEGAL_PAGES: readonly PublicPage[] = [
  { name: "Disclaimer", route: "/disclaimer", Page: DisclaimerPage },
  { name: "Terms", route: "/terms", Page: TermsPage },
  { name: "Privacy", route: "/privacy", Page: PrivacyPage },
];

const PUBLIC_PAGES: readonly PublicPage[] = [
  ...LEGAL_PAGES,
  { name: "Not available", route: "/not-available", Page: NotAvailablePage },
];

const LEGAL_METADATA = [
  { name: "Disclaimer", metadata: disclaimerMetadata },
  { name: "Terms", metadata: termsMetadata },
  { name: "Privacy", metadata: privacyMetadata },
];

// ★[BL-816] 종결(2026-08-21) — 종전엔 `not-available` 만 metadata 가 없어서 이 테스트가
//   「export 하지 않는다」를 **결함 계약**으로 고정하고 있었다. 수리와 함께 그 케이스가
//   red 로 뒤집혔고(예측대로), 이제 **넷을 같은 자리에서** 잰다.
const PUBLIC_METADATA = [
  ...LEGAL_METADATA,
  { name: "Not available", metadata: notAvailableMetadata },
];

afterEach(() => cleanup());

describe("공개 법무 페이지", () => {
  it.each(PUBLIC_PAGES)("$name 페이지가 비어 있지 않게 렌더된다", ({ Page }) => {
    render(<Page />);

    const bodyText = document.body.textContent?.trim() ?? "";
    expect(bodyText).not.toBe("");
  });

  it.each(PUBLIC_PAGES)("$name 페이지에 비어 있지 않은 제목이 있다", ({ Page }) => {
    render(<Page />);

    const headings = screen.getAllByRole("heading");
    expect(headings.every((heading) => (heading.textContent?.trim().length ?? 0) > 0)).toBe(true);
  });

  it.each(PUBLIC_METADATA)("$name metadata에 비어 있지 않은 title이 있다", ({ metadata }) => {
    expect(typeof metadata.title).toBe("string");
    expect((metadata.title as string).trim()).not.toBe("");
  });

  it("공개 4종 metadata title은 서로 다르다", () => {
    const titles = PUBLIC_METADATA.map(({ metadata }) => metadata.title);

    expect(new Set(titles)).toHaveLength(4);
  });

  it("★not-available 도 자기 제목을 갖는다 — root template 의 default 로 새지 않는다", () => {
    // [BL-816]: metadata 가 없으면 root layout 의 `title.default` 가 적용돼 이 화면이
    // 다른 모든 페이지와 같은 "QuantBridge" 로 나간다(빈 <title> 이 아니다).
    // geo-block L2 착지점이라 제한 국가 방문자가 처음이자 유일하게 보는 화면이다.
    expect(notAvailableMetadata.title).toBe("Not available in your region");
  });

  it("not-available은 지역 제한 안내와 이메일 연락 수단을 제공한다", () => {
    render(<NotAvailablePage />);

    expect(screen.getByText(/아시아-태평양 지역/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "hello@quantbridge.ai" })).toHaveAttribute(
      "href",
      "mailto:hello@quantbridge.ai",
    );
  });

  it("법무 3종은 서로 다른 본문을 렌더한다", () => {
    const bodyTexts = LEGAL_PAGES.map(({ Page }) => {
      render(<Page />);
      const bodyText = document.body.textContent?.trim() ?? "";
      cleanup();
      return bodyText;
    });

    expect(new Set(bodyTexts)).toHaveLength(3);
  });

  it.each(LEGAL_PAGES)("$name 본문은 최소 200자다", ({ Page }) => {
    render(<Page />);

    const bodyText = document.body.textContent?.trim() ?? "";
    expect(bodyText.length).toBeGreaterThanOrEqual(200);
  });

  it("새 탭 외부 링크가 있으면 noopener를 포함한다", () => {
    PUBLIC_PAGES.forEach(({ Page }) => render(<Page />));

    const externalLinks = document.querySelectorAll<HTMLAnchorElement>('a[target="_blank"]');
    // target="_blank" 링크가 0건이면 이 검증은 통과한다. 그 경우 링크 안전성은 판별하지 않는다.
    externalLinks.forEach((link) => {
      expect(link.rel.split(/\s+/)).toContain("noopener");
    });
  });

  it("LEGAL_LINKS는 렌더한 법무 페이지 집합의 실재 경로를 가리킨다", () => {
    LEGAL_PAGES.forEach(({ Page }) => render(<Page />));

    expect(screen.getAllByTestId("legal-page-shell")).toHaveLength(3);
    expect(Object.values(LEGAL_LINKS)).toEqual(["/disclaimer", "/terms", "/privacy"]);
    expect(new Set(Object.values(LEGAL_LINKS))).toEqual(
      new Set(LEGAL_PAGES.map(({ route }) => route)),
    );
  });
});
