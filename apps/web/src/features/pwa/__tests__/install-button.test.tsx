// 설치 버튼 — `beforeinstallprompt` 모듈 단일 구독 + 1회용 프롬프트 (pwa.md §2.6).
// ★보관소는 모듈 평가 시점에 리스너를 붙인다 — 테스트마다 모듈을 새로 평가해 상태를 격리한다.
import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

type InstallButtonModule = typeof import("../components/install-button");

let InstallButton: InstallButtonModule["InstallButton"];
let addEventListenerSpy: ReturnType<typeof vi.spyOn>;

function fireBeforeInstallPrompt() {
  const event = new Event("beforeinstallprompt", { cancelable: true }) as Event & {
    prompt: ReturnType<typeof vi.fn>;
  };
  event.prompt = vi.fn(async () => ({ outcome: "dismissed" }));
  act(() => {
    window.dispatchEvent(event);
  });
  return event;
}

beforeEach(async () => {
  vi.resetModules();
  addEventListenerSpy = vi.spyOn(window, "addEventListener");
  ({ InstallButton } = await import("../components/install-button"));
});

afterEach(() => {
  cleanup();
  addEventListenerSpy.mockRestore();
});

describe("InstallButton", () => {
  it("버튼이 N개 마운트돼도 window 의 beforeinstallprompt 리스너는 1개다", () => {
    render(
      <>
        <InstallButton />
        <InstallButton />
        <InstallButton />
      </>,
    );

    const calls = (type: string) =>
      addEventListenerSpy.mock.calls.filter(([eventType]) => eventType === type);
    expect(calls("beforeinstallprompt")).toHaveLength(1);
    expect(calls("appinstalled")).toHaveLength(1);

    // 양성 대조 — 리스너 하나가 세 구독자 모두에게 전달한다.
    fireBeforeInstallPrompt();
    expect(screen.getAllByRole("button", { name: "앱 설치" })).toHaveLength(3);
  });

  it("이벤트가 없으면 그리지 않는다", () => {
    render(<InstallButton />);
    expect(screen.queryByRole("button", { name: "앱 설치" })).toBeNull();
  });

  it("클릭하면 prompt() 를 한 번 부르고, 결과와 무관하게 이벤트를 폐기해 버튼이 사라진다", () => {
    render(<InstallButton />);
    const event = fireBeforeInstallPrompt();
    expect(event.defaultPrevented).toBe(true);

    fireEvent.click(screen.getByRole("button", { name: "앱 설치" }));

    expect(event.prompt).toHaveBeenCalledTimes(1);
    expect(screen.queryByRole("button", { name: "앱 설치" })).toBeNull();
  });

  it("appinstalled 가 오면 숨긴다", () => {
    render(<InstallButton />);
    fireBeforeInstallPrompt();
    expect(screen.getByRole("button", { name: "앱 설치" })).toBeInTheDocument();

    act(() => {
      window.dispatchEvent(new Event("appinstalled"));
    });

    expect(screen.queryByRole("button", { name: "앱 설치" })).toBeNull();
  });

  it("이미 설치된 창(display-mode: standalone)에서는 이벤트가 있어도 그리지 않는다", () => {
    const matchMedia = vi.fn((query: string) => ({ matches: query.includes("standalone") }));
    vi.stubGlobal("matchMedia", matchMedia);
    try {
      render(<InstallButton />);
      fireBeforeInstallPrompt();
      expect(screen.queryByRole("button", { name: "앱 설치" })).toBeNull();
      expect(matchMedia).toHaveBeenCalledWith("(display-mode: standalone)");
    } finally {
      vi.unstubAllGlobals();
    }
  });
});
