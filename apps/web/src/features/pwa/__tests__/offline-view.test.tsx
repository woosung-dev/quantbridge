// 오프라인 안내 — 새로고침이 JS 없이 **현재 URL 을 쿼리까지** 다시 연다 (pwa.md §2.4).
// ★SW 가 내주는 캐시 HTML 은 오프라인에서 청크를 못 받아 하이드레이션되지 않는다 → onClick 금지.
//   이름 없는 GET 폼은 쿼리를 `?` 로 지운다(`/backtests/new?x=1` → `/backtests/new?`) — 그 회귀를 막는다.
import { cleanup, render, screen } from "@testing-library/react";
import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, describe, expect, it } from "vitest";

import { OfflineView } from "../components/offline-view";

afterEach(() => {
  cleanup();
  window.history.replaceState({}, "", "/");
});

describe("OfflineView", () => {
  it("서버 HTML 에 빈 href 링크가 실린다 — 폼도 클라이언트 핸들러도 없다", () => {
    const html = renderToStaticMarkup(<OfflineView />);

    expect(html).toContain("오프라인 상태입니다");
    expect(html).toMatch(/<a [^>]*href=""[^>]*>.*새로고침<\/a>/);
    expect(html).not.toContain("<form");
  });

  it("새로고침 링크는 사용자가 가려던 주소를 쿼리까지 그대로 가리킨다", () => {
    // SW 는 응답만 `/offline` 으로 바꾸고 주소창은 원래 경로다.
    window.history.replaceState({}, "", "/backtests/new?x=1");
    render(<OfflineView />);

    // ★role 로 찾지 않는다 — dom-testing-library(aria-query `constraints: ["set"]`)는 빈 href 의 `<a>` 를
    //   link 로 세지 않는다. 브라우저(HTML-AAM: href 속성이 있으면 link)와 다른 판정이라 텍스트로 찾는다.
    const link = screen.getByText("새로고침").closest("a");
    expect(link).not.toBeNull();
    const target = new URL(link!.href);
    expect(`${target.pathname}${target.search}`).toBe("/backtests/new?x=1");
  });
});
