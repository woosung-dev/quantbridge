// UI store 계약 테스트 — 모바일 drawer 초기값·부분 병합·구독 해제를 고정한다.

import { beforeEach, describe, expect, it, vi } from "vitest";

import { useUiStore } from "../ui-store";

describe("useUiStore", () => {
  beforeEach(() => {
    useUiStore.setState({ mobileNavOpen: false });
  });

  it("실제 zustand 훅 모듈이 drawer 상태와 setter를 노출한다", () => {
    const state = useUiStore.getState();

    expect(useUiStore).toBeTypeOf("function");
    expect(state).toHaveProperty("mobileNavOpen");
    expect(state).toHaveProperty("setMobileNavOpen");
  });

  it("drawer는 닫힌 상태로 시작한다", () => {
    expect(useUiStore.getState().mobileNavOpen).toBe(false);
  });

  it("setter로 drawer를 열고 다시 닫는다", () => {
    useUiStore.getState().setMobileNavOpen(true);
    expect(useUiStore.getState().mobileNavOpen).toBe(true);

    useUiStore.getState().setMobileNavOpen(false);
    expect(useUiStore.getState().mobileNavOpen).toBe(false);
  });

  it("구독자에게 새 상태를 알리고 해제 뒤에는 알리지 않는다", () => {
    const subscriber = vi.fn();
    const unsubscribe = useUiStore.subscribe(subscriber);

    useUiStore.getState().setMobileNavOpen(true);

    expect(subscriber).toHaveBeenCalledTimes(1);
    expect(subscriber.mock.calls[0]?.[0].mobileNavOpen).toBe(true);

    unsubscribe();
    useUiStore.getState().setMobileNavOpen(false);

    expect(subscriber).toHaveBeenCalledTimes(1);
  });

  it("부분 병합 setter 뒤에도 setter를 유지한다", () => {
    useUiStore.getState().setMobileNavOpen(true);

    expect(useUiStore.getState().setMobileNavOpen).toBeTypeOf("function");

    useUiStore.getState().setMobileNavOpen(false);
    expect(useUiStore.getState().mobileNavOpen).toBe(false);
  });
});
