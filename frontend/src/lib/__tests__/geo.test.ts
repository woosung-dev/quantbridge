// Sprint 11 Phase A — geo.ts unit test.

import { describe, expect, it } from "vitest";

import { isRestrictedCountry, RESTRICTED_COUNTRIES } from "@/lib/geo";

describe("isRestrictedCountry", () => {
  it("returns true for US", () => {
    expect(isRestrictedCountry("US")).toBe(true);
  });

  it("returns true for EU members (DE, FR, IT, ES)", () => {
    expect(isRestrictedCountry("DE")).toBe(true);
    expect(isRestrictedCountry("FR")).toBe(true);
    expect(isRestrictedCountry("IT")).toBe(true);
    expect(isRestrictedCountry("ES")).toBe(true);
  });

  it("returns true for UK (GB) post-Brexit", () => {
    expect(isRestrictedCountry("GB")).toBe(true);
  });

  it("returns false for allowed Asia-Pacific (KR, JP, SG, TW, HK)", () => {
    expect(isRestrictedCountry("KR")).toBe(false);
    expect(isRestrictedCountry("JP")).toBe(false);
    expect(isRestrictedCountry("SG")).toBe(false);
    expect(isRestrictedCountry("TW")).toBe(false);
    expect(isRestrictedCountry("HK")).toBe(false);
  });

  it("returns false for null/undefined/empty", () => {
    expect(isRestrictedCountry(null)).toBe(false);
    expect(isRestrictedCountry(undefined)).toBe(false);
    expect(isRestrictedCountry("")).toBe(false);
  });

  it("is case-insensitive", () => {
    expect(isRestrictedCountry("us")).toBe(true);
    expect(isRestrictedCountry("kr")).toBe(false);
  });

  it("has exactly 29 restricted countries (US + EU27 + GB)", () => {
    expect(RESTRICTED_COUNTRIES.size).toBe(29);
  });
});
