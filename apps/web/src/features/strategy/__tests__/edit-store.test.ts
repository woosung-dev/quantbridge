import { beforeEach, describe, expect, it } from "vitest";

import {
  selectIsDirty,
  selectLastSavedAt,
  selectPineSource,
  selectServerSnapshot,
  selectStrategyId,
  useEditStore,
} from "@/features/strategy/edit-store";

const SOURCE_A = "//@version=5\nstrategy('A')";
const SOURCE_B = "//@version=5\nstrategy('B')";

function resetStore() {
  useEditStore.setState({
    strategyId: null,
    pineSource: "",
    serverSnapshot: "",
    lastSavedAt: null,
  });
}

describe("useEditStore", () => {
  beforeEach(() => {
    resetStore();
  });

  it("has clean initial state", () => {
    const s = useEditStore.getState();
    expect(selectStrategyId(s)).toBeNull();
    expect(selectPineSource(s)).toBe("");
    expect(selectServerSnapshot(s)).toBe("");
    expect(selectLastSavedAt(s)).toBeNull();
    expect(selectIsDirty(s)).toBe(false);
  });

  it("loadServerSnapshot sets both buffers and clears dirty", () => {
    useEditStore.getState().loadServerSnapshot("uuid-1", SOURCE_A);
    const s = useEditStore.getState();
    expect(selectStrategyId(s)).toBe("uuid-1");
    expect(selectPineSource(s)).toBe(SOURCE_A);
    expect(selectServerSnapshot(s)).toBe(SOURCE_A);
    expect(selectIsDirty(s)).toBe(false);
    expect(selectLastSavedAt(s)).toBeNull();
  });

  it("setPineSource flips isDirty when diverging from server snapshot", () => {
    useEditStore.getState().loadServerSnapshot("uuid-1", SOURCE_A);
    useEditStore.getState().setPineSource(SOURCE_B);
    expect(selectIsDirty(useEditStore.getState())).toBe(true);
    expect(selectPineSource(useEditStore.getState())).toBe(SOURCE_B);
  });

  it("setPineSource flips isDirty back to false when restored to server snapshot", () => {
    useEditStore.getState().loadServerSnapshot("uuid-1", SOURCE_A);
    useEditStore.getState().setPineSource(SOURCE_B);
    expect(selectIsDirty(useEditStore.getState())).toBe(true);
    useEditStore.getState().setPineSource(SOURCE_A);
    expect(selectIsDirty(useEditStore.getState())).toBe(false);
  });

  it("markSaved updates lastSavedAt and realigns server snapshot", () => {
    useEditStore.getState().loadServerSnapshot("uuid-1", SOURCE_A);
    useEditStore.getState().setPineSource(SOURCE_B);
    const savedAt = new Date("2026-04-19T00:00:00Z");
    useEditStore.getState().markSaved(savedAt);
    const s = useEditStore.getState();
    expect(selectLastSavedAt(s)).toBe(savedAt);
    expect(selectServerSnapshot(s)).toBe(SOURCE_B);
    expect(selectIsDirty(s)).toBe(false);
  });

  it("resetDirty rolls pineSource back to server snapshot", () => {
    useEditStore.getState().loadServerSnapshot("uuid-1", SOURCE_A);
    useEditStore.getState().setPineSource(SOURCE_B);
    useEditStore.getState().resetDirty();
    const s = useEditStore.getState();
    expect(selectPineSource(s)).toBe(SOURCE_A);
    expect(selectIsDirty(s)).toBe(false);
  });
});
