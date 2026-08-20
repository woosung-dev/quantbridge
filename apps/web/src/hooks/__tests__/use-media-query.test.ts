// useMediaQuery 계약 테스트 — SSR fallback과 MediaQueryList 구독 수명을 고정한다.

import { act, renderHook } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { useMediaQuery } from "../use-media-query";

type ChangeListener = () => void;

function createMediaQueryList(initialMatches: boolean) {
  let changeListener: ChangeListener | undefined;
  const mediaQueryList = {
    matches: initialMatches,
    media: "screen",
    addEventListener: vi.fn((eventName: string, listener: ChangeListener) => {
      if (eventName === "change") {
        changeListener = listener;
      }
    }),
    removeEventListener: vi.fn((eventName: string, listener: ChangeListener) => {
      if (eventName === "change" && changeListener === listener) {
        changeListener = undefined;
      }
    }),
  };

  return {
    mediaQueryList: mediaQueryList as unknown as MediaQueryList,
    setMatches: (matches: boolean) => {
      mediaQueryList.matches = matches;
    },
    getChangeListener: () => changeListener,
    addEventListener: mediaQueryList.addEventListener,
    removeEventListener: mediaQueryList.removeEventListener,
  };
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("useMediaQuery", () => {
  it("matchMedia가 없으면 false를 반환하고 예외를 던지지 않는다", () => {
    vi.stubGlobal("matchMedia", undefined);

    const { result } = renderHook(() => useMediaQuery("(min-width: 768px)"));

    expect(result.current).toBe(false);
  });

  it("matches가 true면 query 문자열을 전달하고 true를 반환한다", () => {
    const mediaQuery = createMediaQueryList(true);
    const matchMediaMock = vi.fn(() => mediaQuery.mediaQueryList);
    vi.stubGlobal("matchMedia", matchMediaMock);

    const { result } = renderHook(() => useMediaQuery("(min-width: 768px)"));

    expect(result.current).toBe(true);
    expect(matchMediaMock).toHaveBeenCalledWith("(min-width: 768px)");
  });

  it("matches가 false면 false를 반환한다", () => {
    const mediaQuery = createMediaQueryList(false);
    vi.stubGlobal("matchMedia", vi.fn(() => mediaQuery.mediaQueryList));

    const { result } = renderHook(() => useMediaQuery("(min-width: 768px)"));

    expect(result.current).toBe(false);
  });

  it("change 이벤트가 오면 최신 matches 값으로 갱신한다", () => {
    const mediaQuery = createMediaQueryList(true);
    vi.stubGlobal("matchMedia", vi.fn(() => mediaQuery.mediaQueryList));
    const { result } = renderHook(() => useMediaQuery("(min-width: 768px)"));
    const listener = mediaQuery.getChangeListener();

    expect(listener).toBeTypeOf("function");

    act(() => {
      mediaQuery.setMatches(false);
      listener?.();
    });

    expect(result.current).toBe(false);
  });

  it("구독과 해제에 같은 change 리스너를 사용한다", () => {
    const mediaQuery = createMediaQueryList(true);
    vi.stubGlobal("matchMedia", vi.fn(() => mediaQuery.mediaQueryList));
    const { unmount } = renderHook(() => useMediaQuery("(min-width: 768px)"));

    expect(mediaQuery.addEventListener).toHaveBeenCalledTimes(1);
    expect(mediaQuery.addEventListener).toHaveBeenCalledWith("change", expect.any(Function));
    const listener = mediaQuery.addEventListener.mock.calls[0]?.[1];

    unmount();

    expect(mediaQuery.removeEventListener).toHaveBeenCalledTimes(1);
    expect(mediaQuery.removeEventListener).toHaveBeenCalledWith("change", listener);
  });

  it("같은 query 재렌더는 유지하고 바뀐 query에서는 한 번만 재구독한다", () => {
    const firstQuery = "(min-width: 768px)";
    const nextQuery = "(min-width: 1024px)";
    const firstMediaQuery = createMediaQueryList(true);
    const nextMediaQuery = createMediaQueryList(false);
    const matchMediaMock = vi.fn((query: string) =>
      query === firstQuery ? firstMediaQuery.mediaQueryList : nextMediaQuery.mediaQueryList,
    );
    vi.stubGlobal("matchMedia", matchMediaMock);
    const { rerender } = renderHook(({ query }) => useMediaQuery(query), {
      initialProps: { query: firstQuery },
    });

    rerender({ query: firstQuery });

    expect(firstMediaQuery.addEventListener).toHaveBeenCalledTimes(1);
    expect(firstMediaQuery.removeEventListener).not.toHaveBeenCalled();

    rerender({ query: nextQuery });

    expect(firstMediaQuery.removeEventListener).toHaveBeenCalledTimes(1);
    expect(nextMediaQuery.addEventListener).toHaveBeenCalledTimes(1);
    expect(matchMediaMock).toHaveBeenCalledWith(nextQuery);
  });
});
