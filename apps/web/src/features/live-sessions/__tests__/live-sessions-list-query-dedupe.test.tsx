// BL-423 — 같은 화면이 라이브 세션 목록을 **한 번만** 가져오는지.
//
// 고치기 전 상태: `trading-cockpit` 이 `useLiveSessions()`(활성만), 그 안의 `LiveSessionList` 가
// `useLiveSessions(true)`(비활성 포함) 를 써서 queryKey 가 `list` / `listWithInactive` 로 갈렸다.
// React Query 는 키가 다르면 다른 쿼리이므로 **같은 화면에서 목록 요청이 두 벌** 나갔다.
//
// 이 파일은 그 기전을 직접 잰다 — 대조군(키가 갈린 경우 2회)을 함께 둬서 "1회" 가 우연이
// 아님을 보인다. 그리고 cockpit 이 실제로 `true` 를 넘기는지 소스로 래칫을 건다(기전을 고쳐도
// 호출부가 되돌아가면 무의미하므로).

import { readFileSync } from "node:fs";
import path from "node:path";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { authMockState } from "@/lib/__mocks__/auth-client";

// 이 파일의 단언이 이 uid 로 만든 queryKey 를 본다 — 전역 인증 mock 기본값(`user-1`)과
// 다르므로 여기서 명시한다(ADR-034).
authMockState.userId = "test-user";


const listLiveSessionsMock = vi.fn();

vi.mock("../api", () => ({
  listLiveSessions: (...args: unknown[]) => listLiveSessionsMock(...args),
  // hooks.ts 가 import 하는 나머지는 이 테스트에서 안 쓰지만 stub 이 필요하다.
  getLiveSessionState: vi.fn(),
  listLiveSessionEvents: vi.fn(),
  getLiveSessionOutcomeParity: vi.fn(),
  getLiveSessionPositions: vi.fn(),
  getAccountPositions: vi.fn(),
  closePosition: vi.fn(),
  registerLiveSession: vi.fn(),
  deactivateLiveSession: vi.fn(),
}));

import { useLiveSessions } from "../hooks";
import { liveSessionKeys } from "../query-keys";

/** 소스 래칫이 **코드**만 보게 한다 — 블록 주석과 줄 주석을 지운다. */
function stripComments(source: string): string {
  return source.replace(/\/\*[\s\S]*?\*\//g, "").replace(/(^|[^:])\/\/.*$/gm, "$1");
}

const COCKPIT = path.resolve(
  __dirname,
  "../../../app/(dashboard)/trading/_components/trading-cockpit.tsx",
);

function makeClient() {
  // 한 화면 = 한 QueryClient. 두 훅이 이 캐시를 공유한다.
  return new QueryClient({
    defaultOptions: { queries: { retry: false, refetchInterval: false } },
  });
}

function wrapper(client = makeClient()) {
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
  };
}

describe("라이브 세션 목록 쿼리 (BL-423)", () => {
  beforeEach(() => {
    listLiveSessionsMock.mockReset();
    listLiveSessionsMock.mockResolvedValue({ items: [], total: 0 });
  });

  it("두 소비자가 같은 인자를 쓰면 요청은 1회 (지금의 cockpit + list)", async () => {
    const { result } = renderHook(
      () => {
        const cockpit = useLiveSessions(true);
        const list = useLiveSessions(true);
        return { cockpit, list };
      },
      { wrapper: wrapper() },
    );

    await waitFor(() => expect(result.current.cockpit.isSuccess).toBe(true));
    await waitFor(() => expect(result.current.list.isSuccess).toBe(true));

    expect(listLiveSessionsMock).toHaveBeenCalledTimes(1);
    expect(listLiveSessionsMock).toHaveBeenCalledWith("test-token", true);
  });

  it("대조군 — 인자가 갈리면 요청이 2회 (고치기 전 상태)", async () => {
    const { result } = renderHook(
      () => {
        const cockpit = useLiveSessions(false);
        const list = useLiveSessions(true);
        return { cockpit, list };
      },
      { wrapper: wrapper() },
    );

    await waitFor(() => expect(result.current.cockpit.isSuccess).toBe(true));
    await waitFor(() => expect(result.current.list.isSuccess).toBe(true));

    expect(listLiveSessionsMock).toHaveBeenCalledTimes(2);
  });

  it("★`list` 무효화가 `listWithInactive` 까지 갱신한다 — 세션이 죽었을 때 목록이 따라온다", async () => {
    // 실시간 `session_state` 핸들러와 등록/중단 mutation 은 전부
    // `liveSessionKeys.list(uid)` 만 무효화한다(`features/realtime/handlers.ts`).
    // `listWithInactive` 가 `list` 의 **자식 키**라서 prefix 매칭으로 함께 갱신되는데,
    // 이걸 형제 키로 "정리" 하면 세션이 fail-closed 로 죽어도 화면 목록이 그대로 남는다 —
    // BL-423 이 고치려던 실패 모양 그 자체다. 그래서 여기서 성질을 못 박는다.
    expect(liveSessionKeys.listWithInactive("u")).toEqual([
      ...liveSessionKeys.list("u"),
      "with-inactive",
    ]);

    const client = makeClient();
    const { result } = renderHook(() => useLiveSessions(true), {
      wrapper: wrapper(client),
    });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(listLiveSessionsMock).toHaveBeenCalledTimes(1);

    await client.invalidateQueries({ queryKey: liveSessionKeys.list("test-user") });

    await waitFor(() => expect(listLiveSessionsMock).toHaveBeenCalledTimes(2));
  });

  it("cockpit 이 비활성 포함으로 호출한다 — 호출부 래칫", () => {
    // ★주석을 걷어내고 잰다. 이 래칫은 **호출부**를 재야 하는데 종전에는 파일 원문을 그대로
    // 훑어서 산문에 그 호출 형태를 인용하기만 해도 빨개졌다(2026-08-09 실측 — BL-533 이
    // 미러 state 를 지우며 남긴 「예전에는 활성만 조회했다」 설명이 이 래칫에 걸렸다).
    // 반대 방향 오류가 더 나쁘다 — 주석에 형태만 적어두면 양성 단언이 **코드 없이도** 만족된다.
    const source = stripComments(readFileSync(COCKPIT, "utf8"));

    expect(source).toContain("useLiveSessions(true)");
    // 인자 없는 호출로 되돌아가면 키가 다시 갈린다.
    expect(source).not.toContain("useLiveSessions()");
  });

  it("★활성 전용 소비자가 넓어진 목록을 쓰지 않는다 — quota·KPI 래칫", () => {
    // 목록을 비활성까지 넓히면서 생긴 위험: `sessionItems` 를 활성 카운트로 쓰면
    // **최근 종료 세션 5건만으로 quota(≤5)가 잠긴다** — 새 세션을 못 시작한다.
    // KPI 타일도 같은 함정이다. 둘 다 `activeSessions` 를 쓰는지 소스로 못 박는다.
    const source = readFileSync(COCKPIT, "utf8");

    expect(source).toContain("activeSessionsCount={activeSessions.length}");
    expect(source).not.toContain("sessionItems.length");
    // 활성만 필요한 포지션 대조표도 그대로여야 한다.
    expect(source).toContain("sessions={activeSessions}");
  });
});
