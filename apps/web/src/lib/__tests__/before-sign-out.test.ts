// 로그아웃 직전 정리 seam — best-effort 계약(실패·지연이 로그아웃을 막지 않는다, pwa.md §2.7).
import { afterEach, describe, expect, it, vi } from "vitest";

import { runBeforeSignOut, setBeforeSignOut } from "../before-sign-out";

afterEach(() => {
  setBeforeSignOut(null);
  vi.useRealTimers();
  vi.restoreAllMocks();
});

describe("runBeforeSignOut", () => {
  it("등록된 정리를 기다린다 (양성 대조)", async () => {
    const cleanup = vi.fn(async () => {});
    setBeforeSignOut(cleanup);

    await runBeforeSignOut();

    expect(cleanup).toHaveBeenCalledTimes(1);
  });

  it("정리가 끝나지 않아도 2초 뒤에는 돌아온다", async () => {
    vi.useFakeTimers();
    setBeforeSignOut(() => new Promise<void>(() => {}));
    let done = false;

    const run = runBeforeSignOut().then(() => {
      done = true;
    });
    await vi.advanceTimersByTimeAsync(1_999);
    expect(done).toBe(false);
    await vi.advanceTimersByTimeAsync(1);
    await run;
    expect(done).toBe(true);
  });

  it("정리가 throw 해도 삼킨다 — 로그아웃이 그 예외로 멈추지 않는다", async () => {
    vi.spyOn(console, "warn").mockImplementation(() => {});
    setBeforeSignOut(async () => {
      throw new Error("boom");
    });

    await expect(runBeforeSignOut()).resolves.toBeUndefined();
  });

  it("등록이 없으면 아무것도 하지 않는다", async () => {
    await expect(runBeforeSignOut()).resolves.toBeUndefined();
  });
});
