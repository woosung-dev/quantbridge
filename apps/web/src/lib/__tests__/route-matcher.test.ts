// route-matcher 순수 함수 계약 고정 테스트 — 구 Clerk 매처 의미를 그대로 지킨다(ADR-034).

import { describe, expect, it } from "vitest";

import { createRouteMatcher } from "@/lib/route-matcher";

describe("createRouteMatcher", () => {
  it("exports a factory that returns a matcher function", () => {
    expect(createRouteMatcher).toBeTypeOf("function");
    expect(createRouteMatcher(["/pricing"])).toBeTypeOf("function");
  });

  it("matches an exact pathname", () => {
    const matchesPricing = createRouteMatcher(["/pricing"]);

    expect(matchesPricing("/pricing")).toBe(true);
  });

  it("anchors matches at the pathname start", () => {
    const matchesPricing = createRouteMatcher(["/pricing"]);

    expect(matchesPricing("/foo/pricing")).toBe(false);
  });

  it("anchors matches at the pathname end", () => {
    const matchesPricing = createRouteMatcher(["/pricing"]);

    expect(matchesPricing("/pricing/extra")).toBe(false);
  });

  it("keeps regex groups active in supplied patterns", () => {
    // 의도된 as-is 이식 — 바꾸려면 ADR-034 를 다시 열어라.
    const matchesSignIn = createRouteMatcher(["/sign-in(.*)"]);

    expect(matchesSignIn("/sign-in")).toBe(true);
    expect(matchesSignIn("/sign-in/foo")).toBe(true);
    expect(matchesSignIn("/sign-inXYZ")).toBe(true);
  });

  it("keeps a dot active as a regex wildcard", () => {
    const matchesDotPattern = createRouteMatcher(["/a.c"]);

    expect(matchesDotPattern("/abc")).toBe(true);
    expect(matchesDotPattern("/a.c")).toBe(true);
  });

  it("matches when any supplied pattern matches", () => {
    const matchesEither = createRouteMatcher(["/a", "/b"]);

    expect(matchesEither("/a")).toBe(true);
    expect(matchesEither("/b")).toBe(true);
    expect(matchesEither("/c")).toBe(false);
  });

  it("returns false for every pathname with an empty pattern list", () => {
    const matchesNothing = createRouteMatcher([]);

    expect(matchesNothing("")).toBe(false);
    expect(matchesNothing("/")).toBe(false);
    expect(matchesNothing("/pricing")).toBe(false);
  });

  it("matches an empty pathname only with an empty pattern", () => {
    const matchesEmpty = createRouteMatcher([""]);

    expect(matchesEmpty("")).toBe(true);
    expect(matchesEmpty("/")).toBe(false);
  });

  it("reuses compiled matchers without cross-matcher state", () => {
    const matchesX = createRouteMatcher(["/x(.*)"]);
    const matchesY = createRouteMatcher(["/y"]);

    expect(matchesX("/xa")).toBe(true);
    expect(matchesX("/xa")).toBe(true);
    expect(matchesY("/y")).toBe(true);
    expect(matchesX("/xa")).toBe(true);
  });
});
