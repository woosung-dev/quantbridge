// 오프라인 배너 — online/offline 단일 구독 (pwa.md §2.6).
import { act, cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { OfflineBanner } from "../components/offline-banner";

function setOnline(online: boolean) {
  vi.spyOn(navigator, "onLine", "get").mockReturnValue(online);
  act(() => {
    window.dispatchEvent(new Event(online ? "online" : "offline"));
  });
}

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe("OfflineBanner", () => {
  it("연결 중에는 그리지 않고, 끊기면 숫자가 최신이 아닐 수 있다고 알리고, 돌아오면 사라진다", () => {
    render(<OfflineBanner />);
    expect(screen.queryByRole("status")).toBeNull();

    setOnline(false);
    expect(screen.getByRole("status")).toHaveTextContent(
      "오프라인 상태입니다. 화면의 숫자가 최신이 아닐 수 있습니다.",
    );

    setOnline(true);
    expect(screen.queryByRole("status")).toBeNull();
  });
});
