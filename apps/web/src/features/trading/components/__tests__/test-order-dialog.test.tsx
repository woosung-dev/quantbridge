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

// BL-474 — settings(leverage/margin_mode)가 라우팅 배지의 입력이라 mock 이 그걸
// 실어야 한다. 목록을 교체 가능한 mock 으로 둔 이유 = settings 없는 전략 케이스를
// 별도 테스트에서 보려면 items 배열 자체를 갈아야 하는데, fillForm 이 select item
// 인덱스로 전략/계정을 고르므로 항목 수가 바뀌면 다른 테스트가 전부 어긋난다.
const STRATEGY_WITH_SETTINGS = {
  id: STRATEGY_ID,
  name: "Sample Strategy",
  settings: {
    schema_version: 1,
    leverage: 2,
    margin_mode: "isolated" as const,
    position_size_pct: 0.01,
  },
};
const strategiesMock = vi.fn<() => { items: unknown[]; total: number }>(() => ({
  items: [STRATEGY_WITH_SETTINGS],
  total: 1,
}));
vi.mock("@/features/strategy/hooks", () => ({
  useStrategies: () => ({
    data: strategiesMock(),
    isLoading: false,
    isError: false,
  }),
}));

// G.4 P1 #5 — KS active 시 submit 차단을 위해 useIsOrderDisabledByKs mock 도 노출.
const isKsDisabledMock = vi.fn(() => false);
const exchangeAccountsMock = vi.fn<
  () => Array<{
    id: string;
    exchange: string;
    mode: string;
    label: string;
    api_key_masked: string;
    created_at: string;
  }>
>(() => [
  {
    id: ACCOUNT_ID,
    exchange: "bybit",
    mode: "demo",
    label: "main",
    api_key_masked: "***",
    created_at: "2026-04-26T00:00:00Z",
  },
]);
// Wave 2 — 청산가 미리보기 hook 반환값 제어용 mock.
const liquidationMock = vi.fn<() => { data: unknown }>(() => ({
  data: undefined,
}));
vi.mock("../../hooks", () => ({
  useExchangeAccounts: () => ({
    data: exchangeAccountsMock(),
    isLoading: false,
    isError: false,
  }),
  useIsOrderDisabledByKs: () => isKsDisabledMock(),
  // Wave 2 — 청산가 미리보기 hook. 기본은 미발사(data undefined)로 mock.
  useLiquidationInfo: () => liquidationMock(),
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
  const SelectItem = ({ value, children }: Props & { value: string }) => {
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
  strategiesMock.mockReturnValue({ items: [STRATEGY_WITH_SETTINGS], total: 1 });
  exchangeAccountsMock.mockReturnValue([
    {
      id: ACCOUNT_ID,
      exchange: "bybit",
      mode: "demo",
      label: "main",
      api_key_masked: "***",
      created_at: "2026-04-26T00:00:00Z",
    },
  ]);
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
  it("Bybit Demo 외 legacy 계정은 주문 대상 select에 넣지 않는다", () => {
    exchangeAccountsMock.mockReturnValue([
      {
        id: ACCOUNT_ID,
        exchange: "bybit",
        mode: "demo",
        label: "main",
        api_key_masked: "***",
        created_at: "2026-04-26T00:00:00Z",
      },
      {
        id: "legacy-live",
        exchange: "bybit",
        mode: "live",
        label: "legacy",
        api_key_masked: "***",
        created_at: "2026-04-26T00:00:00Z",
      },
    ]);

    renderDialog();
    openDialog();

    expect(screen.getByText("bybit / demo (main)")).toBeInTheDocument();
    expect(screen.queryByText("bybit / live (legacy)")).not.toBeInTheDocument();
  });

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
      expect(screen.getByText(/Webhook secret 캐시 없음/)).toBeInTheDocument();
    });
    expect(screen.getByText(/테스트 주문 \(dogfood-only\)/)).toBeInTheDocument();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("HMAC compute matches BE golden vector (hex)", async () => {
    // codex G.0 2차 P1 critical: BE/FE byte-level drift 차단.
    // Python: hmac.new(b"test_secret_abc",
    //   '{"symbol":"BTCUSDT","side":"buy","type":"market","quantity":"0.001","exchange_account_id":"550e8400-e29b-41d4-a716-446655440000"}'.encode(),
    //   hashlib.sha256).hexdigest()
    const EXPECTED_HEX = "e4afb16c0e07eaf8ed219a072b59a47ae7619231c03cace98b376795901031e5";

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
      json: async () => {
        throw new SyntaxError("empty body");
      },
    } as unknown as Response);
    vi.stubGlobal("fetch", fetchMock);

    renderDialog();
    openDialog();
    await fillForm();
    clickSubmit();

    await waitFor(() => {
      expect(toastSuccessMock).toHaveBeenCalled();
    });
    // Sprint 21 BL-093: 1번째 arg 는 "테스트 주문 발송됨" 유지 (regression).
    // body json parsing 실패 시 idempotency_key fallback (FIXED_UUID slice -8).
    const [arg0, arg1] = toastSuccessMock.mock.calls[0] as [
      string,
      { description?: string } | undefined,
    ];
    expect(arg0).toBe("테스트 주문 발송됨");
    expect(arg1?.description).toContain("client #");
    expect(arg1?.description).toContain(FIXED_UUID.slice(-8));

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [calledUrl, calledInit] = fetchMock.mock.calls[0] as [string, RequestInit];
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
      expect(screen.queryByText(/테스트 주문 \(dogfood-only\)/)).not.toBeInTheDocument();
    });
  });

  // Sprint 21 BL-093 — broker order id 가 response body 에 있을 때 toast description
  // 에 #${id.slice(-8)} 노출. dogfood Day 0 7번 N (사용자 "주문창이 안 보여서 된거긴한것
  // 같은데?") 해소: order id 마지막 8자 → OrdersPanel BrokerBadge / Bybit Demo UI 매칭.
  it("happy path with json body — toast description shows broker id last 8", async () => {
    readWebhookSecretMock.mockReturnValue("test_secret_abc");
    const realOrderId = "bybit-real-order-1234567-x9y8z7w6v5u4";
    const fetchMock = vi.fn().mockResolvedValue({
      status: 201,
      text: async () => "",
      json: async () => ({
        id: realOrderId,
        symbol: "BTCUSDT",
      }),
    } as unknown as Response);
    vi.stubGlobal("fetch", fetchMock);

    renderDialog();
    openDialog();
    await fillForm();
    clickSubmit();

    await waitFor(() => {
      expect(toastSuccessMock).toHaveBeenCalled();
    });
    const [, arg1] = toastSuccessMock.mock.calls[0] as [
      string,
      { description?: string } | undefined,
    ];
    // broker order id 마지막 8자 노출 (#prefix). client fallback 안 사용.
    expect(arg1?.description).toBe(`#${realOrderId.slice(-8)}`);
    expect(arg1?.description).not.toContain("client");
  });

  it("422 → setError root.serverError → form-level inline error", async () => {
    readWebhookSecretMock.mockReturnValue("test_secret_abc");
    const fetchMock = vi.fn().mockResolvedValue({
      status: 422,
      text: async () => '{"detail":"Missing required field: exchange_account_id"}',
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
    expect(screen.getByText(/테스트 주문 \(dogfood-only\)/)).toBeInTheDocument();
  });

  // Sprint 14 Phase B-1 — WebCrypto 미지원 / SubtleCrypto throw 시 unhandled
  // promise rejection 방지. form error inline 표시 + dialog 유지 + fetch 미호출.
  it("WebCrypto subtle.sign throws → inline error + dialog stays + no fetch", async () => {
    isKsDisabledMock.mockReturnValue(false);
    readWebhookSecretMock.mockReturnValue("test_secret_abc");
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    // crypto.subtle.sign mock — 첫 호출에서 throw (구식 브라우저 / non-HTTPS / 정책).
    vi.spyOn(crypto.subtle, "sign").mockRejectedValue(new Error("SubtleCrypto unavailable"));

    renderDialog();
    openDialog();
    await fillForm();
    clickSubmit();

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent(/암호화 처리 실패/);
    });
    expect(fetchMock).not.toHaveBeenCalled();
    // dialog 유지
    expect(screen.getByText(/테스트 주문 \(dogfood-only\)/)).toBeInTheDocument();
  });

  // Wave 2 — TP/SL 입력 시 payload 에 값 있을 때만 append (기본 5필드 순서 보존).
  it("TP/SL + reduce_only 입력 시 payload append", async () => {
    isKsDisabledMock.mockReturnValue(false);
    readWebhookSecretMock.mockReturnValue("test_secret_abc");
    const fetchMock = vi.fn().mockResolvedValue({
      status: 201,
      text: async () => "",
      json: async () => {
        throw new SyntaxError("empty body");
      },
    } as unknown as Response);
    vi.stubGlobal("fetch", fetchMock);

    renderDialog();
    openDialog();
    await fillForm();
    fireEvent.change(screen.getByLabelText(/익절가/), {
      target: { value: "55000" },
    });
    fireEvent.change(screen.getByLabelText(/손절가/), {
      target: { value: "48000" },
    });
    fireEvent.click(screen.getByLabelText(/reduce-only/));
    clickSubmit();

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledTimes(1);
    });
    const [, calledInit] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(calledInit.body).toBe(
      JSON.stringify({
        symbol: "BTCUSDT",
        side: "buy",
        type: "market",
        quantity: "0.001",
        exchange_account_id: ACCOUNT_ID,
        take_profit: "55000",
        stop_loss: "48000",
        reduce_only: true,
      }),
    );
  });

  // BL-474 — risk% 는 quantity 를 **대체하지 않는다**. 백엔드
  // `_validate_position_size` 는 상한만 검사하고 수량을 만들지 않으므로, 이전
  // 계약(quantity 미전송)은 서버에서 401 로 죽는 죽은 경로였다.
  it("risk% 모드 → quantity + risk_percent 를 함께 전송 (상한 검증)", async () => {
    isKsDisabledMock.mockReturnValue(false);
    readWebhookSecretMock.mockReturnValue("test_secret_abc");
    const fetchMock = vi.fn().mockResolvedValue({
      status: 201,
      text: async () => "",
      json: async () => {
        throw new SyntaxError("empty body");
      },
    } as unknown as Response);
    vi.stubGlobal("fetch", fetchMock);

    renderDialog();
    openDialog();
    await fillForm();
    // 사이징 방식 = 리스크 %
    fireEvent.click(screen.getByLabelText(/리스크 %$/));
    fireEvent.change(screen.getByLabelText(/리스크 % \(수량 상한 검증\)/), {
      target: { value: "1.5" },
    });
    // 손절가 없이는 서버가 상한을 못 구해 가드가 조용히 skip 된다 → 폼이 요구한다.
    fireEvent.change(screen.getByLabelText(/손절가/), {
      target: { value: "48000" },
    });
    clickSubmit();

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledTimes(1);
    });
    const [, calledInit] = fetchMock.mock.calls[0] as [string, RequestInit];
    const body = JSON.parse(calledInit.body as string) as Record<string, unknown>;
    expect(body.quantity).toBe("0.001");
    expect(body.risk_percent).toBe("1.5");
  });

  it("risk% 모드 + 손절가 없음 → inline error + fetch 미호출", async () => {
    isKsDisabledMock.mockReturnValue(false);
    readWebhookSecretMock.mockReturnValue("test_secret_abc");
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);

    renderDialog();
    openDialog();
    await fillForm();
    fireEvent.click(screen.getByLabelText(/리스크 %$/));
    fireEvent.change(screen.getByLabelText(/리스크 % \(수량 상한 검증\)/), {
      target: { value: "1.5" },
    });
    clickSubmit();

    await waitFor(() => {
      expect(screen.getByText(/리스크 % 상한 검증에는 손절가가 필요합니다/)).toBeInTheDocument();
    });
    expect(fetchMock).not.toHaveBeenCalled();
  });

  // Wave 2 — risk% 모드에서 risk_percent 비면 inline error + fetch 미호출.
  it("risk% 모드 빈 값 → inline error + fetch 미호출", async () => {
    isKsDisabledMock.mockReturnValue(false);
    readWebhookSecretMock.mockReturnValue("test_secret_abc");
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);

    renderDialog();
    openDialog();
    await fillForm();
    fireEvent.click(screen.getByLabelText(/리스크 %$/));
    clickSubmit();

    await waitFor(() => {
      expect(screen.getByText(/리스크 %를 입력하세요/)).toBeInTheDocument();
    });
    expect(fetchMock).not.toHaveBeenCalled();
  });

  // ── BL-474 — 라우팅 표면화 + 추정 손익 주입 ──

  it("전략 선택 시 라우팅 배지에 Linear Perp · 레버리지 · 마진모드 표시", async () => {
    readWebhookSecretMock.mockReturnValue("test_secret_abc");
    renderDialog();
    openDialog();
    await fillForm();

    const badge = await screen.findByTestId("routing-badge");
    expect(badge).toHaveTextContent(/Linear Perp/);
    expect(badge).toHaveTextContent(/2x/);
    expect(badge).toHaveTextContent(/isolated/);
    expect(screen.queryByTestId("routing-warning")).not.toBeInTheDocument();
  });

  it("Live Settings 없는 전략 → 422 경고 배너 (발송은 막지 않음)", async () => {
    // 정책을 FE 에도 복제하면 반드시 어긋난다. 공개 ingress 라 서버가 권위 —
    // 여기서는 경고만 하고 실제 거부는 422 로 확인한다.
    strategiesMock.mockReturnValue({
      items: [{ id: STRATEGY_ID, name: "No Settings Strategy", settings: null }],
      total: 1,
    });
    readWebhookSecretMock.mockReturnValue("test_secret_abc");
    renderDialog();
    openDialog();
    await fillForm();

    const warning = await screen.findByTestId("routing-warning");
    expect(warning).toHaveTextContent(/Live Settings/);
    expect(screen.queryByTestId("routing-badge")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: /^발송$/ })).not.toBeDisabled();
  });

  it("청산가 미리보기 레버리지 기본값 = 전략 settings.leverage", async () => {
    readWebhookSecretMock.mockReturnValue("test_secret_abc");
    renderDialog();
    openDialog();
    await fillForm();

    await waitFor(() => {
      expect(screen.getByLabelText(/레버리지 \(배\)/)).toHaveValue("2");
    });
  });

  it("reduce_only 체크 시에만 실현 손익 입력 노출 + payload 말미 append", async () => {
    isKsDisabledMock.mockReturnValue(false);
    readWebhookSecretMock.mockReturnValue("test_secret_abc");
    const fetchMock = vi.fn().mockResolvedValue({
      status: 201,
      text: async () => "",
      json: async () => {
        throw new SyntaxError("empty body");
      },
    } as unknown as Response);
    vi.stubGlobal("fetch", fetchMock);

    renderDialog();
    openDialog();
    await fillForm();
    // 진입 주문에는 의미가 없어 노출되지 않는다.
    expect(screen.queryByLabelText(/실현 손익/)).not.toBeInTheDocument();

    fireEvent.click(screen.getByLabelText(/reduce-only/));
    fireEvent.change(await screen.findByLabelText(/실현 손익/), {
      target: { value: "-12.5" },
    });
    clickSubmit();

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledTimes(1);
    });
    const [, calledInit] = fetchMock.mock.calls[0] as [string, RequestInit];
    // append-only — 기본 5필드 순서 보존 (HMAC 골든벡터 불변).
    expect(calledInit.body).toBe(
      JSON.stringify({
        symbol: "BTCUSDT",
        side: "buy",
        type: "market",
        quantity: "0.001",
        exchange_account_id: ACCOUNT_ID,
        reduce_only: true,
        realized_pnl: "-12.5",
      }),
    );
  });

  it("실현 손익은 음수를 허용하고 비숫자는 거부", async () => {
    isKsDisabledMock.mockReturnValue(false);
    readWebhookSecretMock.mockReturnValue("test_secret_abc");
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);

    renderDialog();
    openDialog();
    await fillForm();
    fireEvent.click(screen.getByLabelText(/reduce-only/));
    fireEvent.change(await screen.findByLabelText(/실현 손익/), {
      target: { value: "abc" },
    });
    clickSubmit();

    await waitFor(() => {
      expect(screen.getByText(/실현 손익은 숫자여야 합니다/)).toBeInTheDocument();
    });
    expect(fetchMock).not.toHaveBeenCalled();
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

  // Wave 2 — 청산가 미리보기: useLiquidationInfo 가 data 를 반환하면 예상 청산가 렌더.
  it("청산가 미리보기 — data 있으면 예상 청산가 + 거리 표시", async () => {
    liquidationMock.mockReturnValue({
      data: {
        symbol: "BTCUSDT",
        entry_price: "50000",
        side: "buy",
        leverage: 10,
        liquidation_price: "45500",
        maintenance_margin_rate: "0.005",
        distance_pct: "9.0",
      },
    });

    renderDialog();
    openDialog();

    const preview = await screen.findByTestId("liquidation-preview");
    expect(preview).toHaveTextContent("45500");
    expect(preview).toHaveTextContent("9.0");

    // 다른 테스트에 누수 방지 — 기본 미발사 상태로 복구.
    liquidationMock.mockReturnValue({ data: undefined });
  });
});
