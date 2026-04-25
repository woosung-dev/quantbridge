// Sprint 11 Phase A — 지원 제외 국가 목록 (US + EU 27 + UK).
// Backend `src/auth/service.py::RESTRICTED_COUNTRIES` 와 동기 유지 필수.

export const RESTRICTED_COUNTRIES: ReadonlySet<string> = new Set([
  // United States
  "US",
  // EU 27 (2026-04 기준)
  "AT",
  "BE",
  "BG",
  "HR",
  "CY",
  "CZ",
  "DK",
  "EE",
  "FI",
  "FR",
  "DE",
  "GR",
  "HU",
  "IE",
  "IT",
  "LV",
  "LT",
  "LU",
  "MT",
  "NL",
  "PL",
  "PT",
  "RO",
  "SK",
  "SI",
  "ES",
  "SE",
  // United Kingdom (post-Brexit, FCA 규제)
  "GB",
]);

export function isRestrictedCountry(country: string | null | undefined): boolean {
  if (!country) return false;
  return RESTRICTED_COUNTRIES.has(country.toUpperCase());
}
