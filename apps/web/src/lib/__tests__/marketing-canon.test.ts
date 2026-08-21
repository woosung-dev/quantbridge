// 마케팅 공동 원장의 파생 관계·불변식 테스트. 화면 렌더링 대신 원장만 직접 검증한다.

import { describe, expect, it } from "vitest";

import {
  EMPTY_CELL,
  EXCHANGE_NO_ENV_TITLE,
  EXCHANGE_NO_SCOPE_TITLE,
  EXCHANGE_SUPPORT,
  EXCHANGE_TABLE_CAPTION,
  PERF_DISCLAIMER,
  PERF_FIGURES,
  ROADMAP_DISCLAIMER,
} from "@/lib/marketing-canon";
import { LEGAL_LINKS } from "@/lib/legal-links";

function parseFigure(value: string): number {
  return Number(value.replace(/[^\d.]/g, ""));
}

describe("marketing canon invariants", () => {
  it("derives the rounded bars-per-second figure from the other two figures", () => {
    const [candleCount, elapsedSeconds, barsPerSecond] = PERF_FIGURES.map(({ value }) =>
      parseFigure(value),
    );

    expect(Math.round(candleCount! / elapsedSeconds!)).toBe(6193);
    expect(Math.round(candleCount! / elapsedSeconds!)).toBe(barsPerSecond);
  });

  it("keeps roadmap rows as environment and scope no-data pairs", () => {
    const roadmapRows = EXCHANGE_SUPPORT.filter(({ status }) => status === "roadmap");

    for (const row of roadmapRows) {
      expect(row.environment).toBeNull();
      expect(row.scope).toBeNull();
    }
  });

  it("keeps supported rows with non-empty environment and scope pairs", () => {
    const supportedRows = EXCHANGE_SUPPORT.filter(({ status }) => status === "supported");

    for (const row of supportedRows) {
      expect(row.environment?.trim()).not.toBe("");
      expect(row.environment).not.toBeNull();
      expect(row.scope?.trim()).not.toBe("");
      expect(row.scope).not.toBeNull();
    }
  });

  it("contains both roadmap and supported rows", () => {
    expect(EXCHANGE_SUPPORT.filter(({ status }) => status === "roadmap").length).toBeGreaterThan(0);
    expect(EXCHANGE_SUPPORT.filter(({ status }) => status === "supported").length).toBeGreaterThan(
      0,
    );
  });

  it("keeps OKX on the roadmap and limits supported exchanges to Bybit", () => {
    const okx = EXCHANGE_SUPPORT.find(({ exchange }) => exchange === "OKX");
    const supportedRows = EXCHANGE_SUPPORT.filter(({ status }) => status === "supported");

    expect(okx).toBeDefined();
    expect(okx?.status).toBe("roadmap");
    for (const row of supportedRows) {
      expect(row.exchange).toBe("Bybit");
    }
  });

  it("keeps the three disclosures non-empty and distinct", () => {
    const disclosures = [ROADMAP_DISCLAIMER, PERF_DISCLAIMER, EXCHANGE_TABLE_CAPTION];

    expect(disclosures.every((disclosure) => disclosure.trim().length > 0)).toBe(true);
    expect(new Set(disclosures)).toHaveLength(3);
  });

  it("attaches a non-empty condition to every performance figure", () => {
    expect(PERF_FIGURES.every(({ note }) => note.trim().length > 0)).toBe(true);
  });

  it("keeps the empty-cell marker and its two explanations distinct", () => {
    expect([...EMPTY_CELL]).toHaveLength(1);
    expect(EMPTY_CELL.trim()).not.toBe("");
    expect(EXCHANGE_NO_ENV_TITLE.trim()).not.toBe("");
    expect(EXCHANGE_NO_SCOPE_TITLE.trim()).not.toBe("");
    expect(EXCHANGE_NO_ENV_TITLE).not.toBe(EXCHANGE_NO_SCOPE_TITLE);
  });

  it("keeps legal links as three distinct internal routes", () => {
    const legalLinkKeys = Object.keys(LEGAL_LINKS).sort();
    const legalLinkPaths = Object.values(LEGAL_LINKS);

    expect(legalLinkKeys).toEqual(["disclaimer", "privacy", "terms"]);
    expect(legalLinkPaths.every((path) => /^\/(?!\/)/.test(path))).toBe(true);
    expect(legalLinkPaths.every((path) => !path.startsWith("http"))).toBe(true);
    expect(new Set(legalLinkPaths)).toHaveLength(3);
  });

  it("loads the expected exchange, performance, and legal-link collections", () => {
    expect(EXCHANGE_SUPPORT.length).toBeGreaterThanOrEqual(5);
    expect(PERF_FIGURES).toHaveLength(3);
    expect(Object.keys(LEGAL_LINKS)).toHaveLength(3);
  });
});
