// Sprint 13 Phase B test — Test Order Dialog (dogfood-only).
//
// 검증 범위:
//  1) Form validation — 필수 필드 비어있을 때 inline error
//  2) Webhook secret 캐시 없음 → guidance message + dialog 유지 + fetch 미발송
//  3) HMAC golden vector — BE 와 동일 hex (codex G.0 2차 P1)
//  4) Happy path — 201 응답 → toast + 캐시 무효화 + dialog 닫힘
//  5) 422 응답 → root.serverError inline 표시

import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import * as React from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

// ── 환경 변수 setup: dialog production guard 통과 ──
beforeEach(() => {
  vi.stubEnv("NEXT_PUBLIC_ENABLE_TEST_ORDER", "true");
  vi.stubEnv("NEXT_PUBLIC_API_URL", "http://localhost:8000");
});
afterEach(() => {
  vi.unstubAllEnvs();
  vi.restoreAllMocks();
});

// ── Strategy / Trading hook mocks ──
const STRATEGY_ID = "11111111-1111-4111-a111-111111111111";
const ACCOUNT_ID = "550e8400-e29b-41d4-a716-446655440000";

vi.mock("@/features/strategy/hooks", () => ({
  useStrategies: () => ({
    data: {
      items: [
        {
          id: STRATEGY_ID,
          name: "Sample Strategy",
        },
      ],
      total: 1,
    },
    isLoading: false,
    isError: false,
  }),
}));

// G.4 P1 #5 — KS active 시 submit 차단을 위해 useIsOrderDisabledByKs mock 도 노출.
const isKsDisabledMock = vi.fn(() => false);
vi.mock("../../hooks", () => ({
  useExchangeAccounts: () => ({
    data: [
      {
        id: ACCOUNT_ID,
        exchange: "bybit",
        mode: "demo",
        label: "main",
        api_key_masked: "***",
        created_at: "2026-04-26T00:00:00Z",
      },
    ],
    isLoading: false,
    isError: false,
  }),
  useIsOrderDisabledByKs: () => isKsDisabledMock(),
}));

// ── webhook-secret-storage mock ──
const readWebhookSecretMock = vi.fn();
vi.mock("@/features/strategy/webhook-secret-storage", () => ({
  readWebhookSecret: (id: string) => readWebhookSecretMock(id),
}));

// ── sonner toast mock ──
const toastSuccessMock = vi.fn();
vi.mock("sonner", () => ({
  toast: {
    success: (...args: unknown[]) => toastSuccessMock(...args),
    error: vi.fn(),
    warning: vi.fn(),
  },
}));

// ── Clerk mock (불필요하지만 strategy hooks import 시 안전) ──
vi.mock("@clerk/nextjs", () => ({
  useAuth: () => ({ userId: "u1", getToken: async () => "test-token" }),
}));

// ── Select 컴포넌트를 native <select> 로 mock — base-ui 의 비결정적 popup 회피 ──
vi.mock("@/components/ui/select", () => {
  type Props = React.PropsWithChildren<{
    onValueChange?: (v: string) => void;
    value?: string;
    placeholder?: string;
    [key: string]: unknown;
  }>;

  // 단순화: SelectContext 로 onValueChange 전달 → SelectItem 이 button 으로 렌더.
  const SelectCtx = React.createContext<{
    onValueChange?: (v: string) => void;
  }>({});

  const Select = ({ children, onValueChange }: Props) => (
    <SelectCtx.Provider value={{ onValueChange }}>
      <div data-testid="mock-select">{children}</div>
    </SelectCtx.Provider>
  );
  const SelectTrigger = ({ children }: Props) => <div>{children}</div>;
  const SelectValue = ({ placeholder }: Props) => <span>{placeholder}</span>;
  const SelectContent = ({ children }: Props) => <div>{children}</div>;
  const SelectItem = ({
    value,
    children,
  }: Props & { value: string }) => {
    const ctx = React.useContext(SelectCtx);
    return (
      <button
        type="button"
        data-mock-select-item
        data-value={value}
        onClick={() => ctx.onValueChange?.(value)}
      >
        {children}
      </button>
    );
  };

  return { Select, SelectTrigger, SelectValue, SelectContent, SelectItem };
});

// ── crypto.randomUUID 결정적 mock ──
const FIXED_UUID = "abcdef00-0000-4000-a000-000000000000";
beforeEach(() => {
  vi.spyOn(crypto, "randomUUID").mockReturnValue(FIXED_UUID);
});

import { TestOrderDialog } from "../test-order-dialog";

function renderDialog() {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={qc}>
      <TestOrderDialog />
    </QueryClientProvider>,
  );
}

function openDialog() {
  fireEvent.click(screen.getByRole("button", { name: /^테스트 주문$/ }));
}

async function fillForm() {
  // strategy + exchange Select (mocked native button)
  const items = await screen.findAllByText(
    (_, el) => el?.getAttribute("data-mock-select-item") !== null,
  );
  // 첫 번째 = "Sample Strategy", 두 번째 = "bybit / demo (main)"
  if (items.length < 2) {
    throw new Error(`expected ≥2 select items, got ${items.length}`);
  }
  const strategyItem = items[0]!;
  const accountItem = items[1]!;
  fireEvent.click(strategyItem);
  fireEvent.click(accountItem);
  fireEvent.change(screen.getByLabelText(/수량/), {
    target: { value: "0.001" },
  });
}

function clickSubmit() {
  fireEvent.click(screen.getByRole("button", { name: /^발송$/ }));
}

describe("TestOrderDialog", () => {
  it("validates empty fields — inline error 표시 + fetch 미호출", async () => {
    readWebhookSecretMock.mockReturnValue("test_secret_abc");
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);

    renderDialog();
    openDialog();

    // 빈 채로 submit — Zod refine + min(1) 모두 트리거.
    await act(async () => {
      clickSubmit();
    });

    await waitFor(() => {
      expect(screen.getByText(/전략을 선택하세요/)).toBeInTheDocument();
    });
    expect(screen.getByText(/거래소 계정을 선택하세요/)).toBeInTheDocument();
    expect(screen.getByText(/수량을 입력하세요/)).toBeInTheDocument();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("no cached secret → guidance message + dialog stays + no fetch", async () => {
    readWebhookSecretMock.mockReturnValue(null);
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);

    renderDialog();
    openDialog();
    await fillForm();
    clickSubmit();

    await waitFor(() => {
      expect(
        screen.getByText(/Webhook secret 캐시 없음/),
      ).toBeInTheDocument();
    });
    expect(
      screen.getByText(/테스트 주문 \(dogfood-only\)/),
    ).toBeInTheDocument();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("HMAC compute matches BE golden vector (hex)", async () => {
    // codex G.0 2차 P1 critical: BE/FE byte-level drift 차단.
    // Python: hmac.new(b"test_secret_abc",
    //   '{"symbol":"BTCUSDT","side":"buy","type":"market","quantity":"0.001","exchange_account_id":"550e8400-e29b-41d4-a716-446655440000"}'.encode(),
    //   hashlib.sha256).hexdigest()
    const EXPECTED_HEX =
      "e4afb16c0e07eaf8ed219a072b59a47ae7619231c03cace98b376795901031e5";

    const secret = "test_secret_abc";
    const bodyStr = JSON.stringify({
      symbol: "BTCUSDT",
      side: "buy",
      type: "market",
      quantity: "0.001",
      exchange_account_id: "550e8400-e29b-41d4-a716-446655440000",
    });

    const enc = new TextEncoder();
    const key = await crypto.subtle.importKey(
      "raw",
      enc.encode(secret),
      { name: "HMAC", hash: "SHA-256" },
      false,
      ["sign"],
    );
    const sig = await crypto.subtle.sign("HMAC", key, enc.encode(bodyStr));
    const hex = Array.from(new Uint8Array(sig))
      .map((b) => b.toString(16).padStart(2, "0"))
      .join("");

    expect(hex).toBe(EXPECTED_HEX);
  });

  it("happy path — 201 → toast + invalidate + close dialog", async () => {
    readWebhookSecretMock.mockReturnValue("test_secret_abc");
    const fetchMock = vi.fn().mockResolvedValue({
      status: 201,
      text: async () => "",
    } as Response);
    vi.stubGlobal("fetch", fetchMock);

    renderDialog();
    openDialog();
    await fillForm();
    clickSubmit();

    await waitFor(() => {
      expect(toastSuccessMock).toHaveBeenCalledWith("테스트 주문 발송됨");
    });

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [calledUrl, calledInit] = fetchMock.mock.calls[0] as [
      string,
      RequestInit,
    ];
    expect(calledUrl).toContain(`/api/v1/webhooks/${STRATEGY_ID}?token=`);
    expect(calledUrl).toContain(`Idempotency-Key=${FIXED_UUID}`);
    expect(calledInit.method).toBe("POST");
    // bodyStr 단일 직렬화 — HMAC 입력과 동일 byte 순서
    expect(calledInit.body).toBe(
      JSON.stringify({
        symbol: "BTCUSDT",
        side: "buy",
        type: "market",
        quantity: "0.001",
        exchange_account_id: ACCOUNT_ID,
      }),
    );

    await waitFor(() => {
      expect(
        screen.queryByText(/테스트 주문 \(dogfood-only\)/),
      ).not.toBeInTheDocument();
    });
  });

  it("422 → setError root.serverError → form-level inline error", async () => {
    readWebhookSecretMock.mockReturnValue("test_secret_abc");
    const fetchMock = vi.fn().mockResolvedValue({
      status: 422,
      text: async () =>
        '{"detail":"Missing required field: exchange_account_id"}',
    } as Response);
    vi.stubGlobal("fetch", fetchMock);

    renderDialog();
    openDialog();
    await fillForm();
    clickSubmit();

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent(/요청 실패 \(422\)/);
    });
    expect(toastSuccessMock).not.toHaveBeenCalled();
    expect(
      screen.getByText(/테스트 주문 \(dogfood-only\)/),
    ).toBeInTheDocument();
  });

  // G.4 P1 #5 — KS active 시 submit 차단 (CSS pointer-events 만으론 키보드/직접 호출 우회 가능).
  it("KS active → submit button disabled + onSubmit 차단 + inline error", async () => {
    isKsDisabledMock.mockReturnValue(true);
    readWebhookSecretMock.mockReturnValue("test_secret_abc");
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);

    renderDialog();
    openDialog();
    await fillForm();

    // submit button 자체가 disabled 상태 + 라벨 변경
    const submitBtn = screen.getByRole("button", { name: /Kill Switch 활성화/ });
    expect(submitBtn).toBeDisabled();

    // 강제 클릭 시도 (disabled 우회를 위해 form submit event 사용)
    const form = submitBtn.closest("form");
    if (form) {
      await act(async () => {
        fireEvent.submit(form);
      });
    }

    // fetch 절대 호출되지 않음 + inline error 표시
    expect(fetchMock).not.toHaveBeenCalled();
    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent(/Kill Switch/);
    });
  });
});
