// 푸시 벨 — 렌더 조건 · 권한 요청 시점 · 로그아웃 정리 등록 (pwa.md §2.7).
// jsdom 에는 serviceWorker·PushManager·Notification 이 없다 → 테스트마다 최소 스텁을 깐다.
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { runBeforeSignOut } from "@/lib/before-sign-out";

import { createPushSubscription, deletePushSubscription, getPushConfig } from "../api";
import { PushBell } from "../components/push-bell";

vi.mock("../api", () => ({
  getPushConfig: vi.fn(),
  createPushSubscription: vi.fn(),
  deletePushSubscription: vi.fn(),
  sendTestPush: vi.fn(),
}));

const getPushConfigMock = vi.mocked(getPushConfig);
const createPushSubscriptionMock = vi.mocked(createPushSubscription);
const deletePushSubscriptionMock = vi.mocked(deletePushSubscription);

const ENDPOINT = "https://fcm.googleapis.com/fcm/send/abc";
const PUBLIC_KEY = "AQID"; // base64url → [1, 2, 3]

const subscription = {
  endpoint: ENDPOINT,
  toJSON: () => ({ endpoint: ENDPOINT, expirationTime: null, keys: { p256dh: "p", auth: "a" } }),
  unsubscribe: vi.fn(async () => true),
};
let deviceSubscription: typeof subscription | null = null;
const pushManager = {
  getSubscription: vi.fn(async () => deviceSubscription),
  subscribe: vi.fn(async (_options: PushSubscriptionOptionsInit) => {
    deviceSubscription = subscription;
    return subscription;
  }),
};
const registration = { pushManager };
const requestPermission = vi.fn(async (): Promise<NotificationPermission> => "granted");
const notificationStub = { permission: "default" as NotificationPermission, requestPermission };

function stubPushSupport() {
  Object.defineProperty(navigator, "serviceWorker", {
    configurable: true,
    value: {
      getRegistration: vi.fn(async () => registration),
      ready: Promise.resolve(registration),
    },
  });
  vi.stubGlobal("PushManager", function PushManager() {});
  vi.stubGlobal("Notification", notificationStub);
}

function renderBell(): void {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={client}>
      <PushBell />
    </QueryClientProvider>,
  );
}

const bell = () => screen.queryByRole("button", { name: "알림 설정" });

beforeEach(() => {
  deviceSubscription = null;
  notificationStub.permission = "default";
  getPushConfigMock.mockResolvedValue({ enabled: true, public_key: PUBLIC_KEY });
  createPushSubscriptionMock.mockResolvedValue({
    id: "00000000-0000-4000-a000-000000000001",
    endpoint: ENDPOINT,
    created_at: "2026-10-02T00:00:00+00:00",
  });
  deletePushSubscriptionMock.mockResolvedValue(undefined);
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  Reflect.deleteProperty(navigator, "serviceWorker");
  vi.clearAllMocks();
});

describe("PushBell — 렌더 조건", () => {
  it("푸시 미지원 브라우저는 벨을 그리지 않고 config 도 묻지 않는다", () => {
    renderBell();

    expect(bell()).toBeNull();
    expect(getPushConfigMock).not.toHaveBeenCalled();
  });

  it("서버 config 가 enabled:false 면 벨을 그리지 않는다", async () => {
    stubPushSupport();
    getPushConfigMock.mockResolvedValue({ enabled: false, public_key: null });

    renderBell();

    await waitFor(() => expect(getPushConfigMock).toHaveBeenCalledTimes(1));
    // 응답이 반영될 틈을 준 뒤에도 없다.
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(bell()).toBeNull();
  });

  it("양성 대조 — 지원 ∧ enabled:true 면 벨을 그린다", async () => {
    stubPushSupport();

    renderBell();

    expect(await screen.findByRole("button", { name: "알림 설정" })).toBeInTheDocument();
  });
});

describe("PushBell — 권한 요청은 클릭에서만", () => {
  it("렌더·팝오버 열기로는 묻지 않고, 스위치를 눌러야 requestPermission → subscribe → POST", async () => {
    stubPushSupport();
    renderBell();

    fireEvent.click(await screen.findByRole("button", { name: "알림 설정" }));
    const toggle = await screen.findByRole("switch", { name: "이 기기에서 알림 받기" });
    await waitFor(() => expect(toggle).toBeEnabled());
    expect(requestPermission).not.toHaveBeenCalled();
    expect(screen.getByRole("button", { name: "테스트 알림 보내기" })).toBeDisabled();

    fireEvent.click(toggle);

    await waitFor(() => expect(toggle).toHaveAttribute("aria-checked", "true"));
    expect(requestPermission).toHaveBeenCalledTimes(1);
    const options = pushManager.subscribe.mock.calls[0]?.[0];
    expect(options?.userVisibleOnly).toBe(true);
    expect(Array.from(options?.applicationServerKey as Uint8Array)).toEqual([1, 2, 3]);
    expect(createPushSubscriptionMock).toHaveBeenCalledWith(
      { endpoint: ENDPOINT, keys: { p256dh: "p", auth: "a" }, user_agent: expect.any(String) },
      "test-token",
    );
    expect(screen.getByRole("button", { name: "테스트 알림 보내기" })).toBeEnabled();
  });

  it("권한이 denied 면 스위치를 막고 차단 사실을 말한다", async () => {
    stubPushSupport();
    notificationStub.permission = "denied";
    renderBell();

    fireEvent.click(await screen.findByRole("button", { name: "알림 설정" }));

    expect(await screen.findByRole("switch", { name: "이 기기에서 알림 받기" })).toBeDisabled();
    expect(screen.getByText("브라우저 설정에서 알림이 차단되어 있습니다")).toBeInTheDocument();
    expect(requestPermission).not.toHaveBeenCalled();
  });
});

describe("PushBell — 로그아웃 정리 등록", () => {
  it("마운트 동안 runBeforeSignOut 이 이 기기 구독을 끊고 서버 행을 DELETE 한다", async () => {
    stubPushSupport();
    deviceSubscription = subscription;
    renderBell();
    await screen.findByRole("button", { name: "알림 설정" });

    await runBeforeSignOut();

    expect(subscription.unsubscribe).toHaveBeenCalledTimes(1);
    expect(deletePushSubscriptionMock).toHaveBeenCalledWith(ENDPOINT, "test-token");

    // 언마운트하면 등록이 풀린다 — 셸 밖에서 남의 정리가 돌지 않는다.
    cleanup();
    subscription.unsubscribe.mockClear();
    await runBeforeSignOut();
    expect(subscription.unsubscribe).not.toHaveBeenCalled();
  });
});

describe("PushBell — 계정 전환 시 기기 구독 재할당", () => {
  it("granted ∧ 기기 구독 있음 → 마운트 시 현재 사용자로 POST 1회(같은 endpoint), 권한은 묻지 않는다", async () => {
    stubPushSupport();
    notificationStub.permission = "granted";
    deviceSubscription = subscription;

    renderBell();

    await waitFor(() => expect(createPushSubscriptionMock).toHaveBeenCalledTimes(1));
    expect(createPushSubscriptionMock).toHaveBeenCalledWith(
      { endpoint: ENDPOINT, keys: { p256dh: "p", auth: "a" }, user_agent: expect.any(String) },
      "test-token",
    );
    expect(requestPermission).not.toHaveBeenCalled();
  });

  it.each([
    { label: "권한 default", permission: "default" as const, hasSubscription: true },
    { label: "기기 구독 없음", permission: "granted" as const, hasSubscription: false },
  ])("$label 이면 POST 0회", async ({ permission, hasSubscription }) => {
    stubPushSupport();
    notificationStub.permission = permission;
    deviceSubscription = hasSubscription ? subscription : null;

    renderBell();

    // config 가 도착해 effect 가 돌 조건까지 간 뒤 비동기 체인이 끝날 틈을 준다.
    await screen.findByRole("button", { name: "알림 설정" });
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(createPushSubscriptionMock).not.toHaveBeenCalled();
    expect(requestPermission).not.toHaveBeenCalled();
  });
});

describe("PushBell — 번들 경계 (bundle-conditional)", () => {
  it("셸에 실리는 push-bell.tsx 는 Base UI(floating-ui)를 정적 import 하지 않고 팝오버를 지연 로딩한다", () => {
    // ★정적 import 1줄이면 대시보드 14 라우트 전부가 floating-ui 청크(gz ≈23KB)를 받는다 —
    //   VAPID 키가 없어 벨이 0% 렌더되는 서버에서도. 실측 = `pnpm build` 후 client-reference-manifest.
    const source = readFileSync(resolve(__dirname, "../components/push-bell.tsx"), "utf-8");

    expect(source).not.toMatch(/^import [^;]*from "@base-ui\/react/m);
    expect(source).toContain('import("./push-bell-popover")');
  });
});
