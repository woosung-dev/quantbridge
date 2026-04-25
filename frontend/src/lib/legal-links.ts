// Sprint 11 Phase B — 법무 페이지 링크 상수. 공통 footer/banner 에서 재사용.

export const LEGAL_LINKS = {
  disclaimer: "/disclaimer",
  terms: "/terms",
  privacy: "/privacy",
} as const;

export type LegalLinkKey = keyof typeof LEGAL_LINKS;
