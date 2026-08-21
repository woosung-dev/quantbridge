// QueryProvider 데이터 페칭 정책과 브라우저 싱글톤 계약을 고정한다.

import { useQueryClient } from "@tanstack/react-query";
import type { QueryClient } from "@tanstack/react-query";
import { cleanup, render, screen } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { AppProviders } from "../app-providers";
import { QueryProvider } from "../query-provider";

const { devtoolsSpy } = vi.hoisted(() => ({ devtoolsSpy: vi.fn() }));

vi.mock("@tanstack/react-query-devtools", () => ({
  ReactQueryDevtools: (props: unknown) => {
    devtoolsSpy(props);
    return null;
  },
}));

function Probe({ onClient }: { onClient: (client: QueryClient) => void }) {
  onClient(useQueryClient());
  return <div data-testid="probe" />;
}

function renderQueryProvider(
  Provider: ({ children }: { children: ReactNode }) => ReactNode = QueryProvider,
): QueryClient {
  let client: QueryClient | undefined;

  render(
    <Provider>
      <Probe onClient={(receivedClient) => (client = receivedClient)} />
    </Provider>,
  );

  if (!client) {
    throw new Error("QueryProvider did not provide a QueryClient");
  }

  return client;
}

afterEach(() => {
  cleanup();
  vi.unstubAllEnvs();
  vi.unstubAllGlobals();
  vi.resetModules();
  devtoolsSpy.mockReset();
});

describe("QueryProvider", () => {
  it("query staleTime은 정책값 60초다", () => {
    const client = renderQueryProvider();

    expect(client.getDefaultOptions().queries?.staleTime).toBe(60_000);
  });

  it("query gcTime은 정책값 5분이다", () => {
    const client = renderQueryProvider();

    expect(client.getDefaultOptions().queries?.gcTime).toBe(300_000);
  });

  it("query retry는 한 번이다", () => {
    const client = renderQueryProvider();

    expect(client.getDefaultOptions().queries?.retry).toBe(1);
  });

  it("창 포커스 때 query를 다시 조회하지 않는다", () => {
    const client = renderQueryProvider();

    expect(client.getDefaultOptions().queries?.refetchOnWindowFocus).toBe(false);
  });

  it("mutation retry는 중복 발주 방지를 위해 0이다", () => {
    const client = renderQueryProvider();

    expect(client.getDefaultOptions().mutations?.retry).toBe(0);
  });

  it("브라우저에서는 unmount 후에도 같은 QueryClient 싱글톤을 제공한다", () => {
    const firstClient = renderQueryProvider();

    cleanup();

    const secondClient = renderQueryProvider();

    expect(secondClient).toBe(firstClient);
  });

  it("children을 렌더한다", () => {
    renderQueryProvider();

    expect(screen.getByTestId("probe")).toBeInTheDocument();
  });

  it("production에서는 Devtools를 붙이지 않는다", async () => {
    vi.stubEnv("NODE_ENV", "production");
    vi.resetModules();
    const { QueryProvider: ProductionQueryProvider } = await import("../query-provider");

    renderQueryProvider(ProductionQueryProvider);

    expect(devtoolsSpy).not.toHaveBeenCalled();
  });

  it("development에서는 Devtools를 붙인다", async () => {
    vi.stubEnv("NODE_ENV", "development");
    vi.resetModules();
    const { QueryProvider: DevelopmentQueryProvider } = await import("../query-provider");

    renderQueryProvider(DevelopmentQueryProvider);

    expect(devtoolsSpy).toHaveBeenCalledOnce();
  });

  it("AppProviders 배선도 QueryClient를 제공한다", () => {
    vi.stubGlobal(
      "matchMedia",
      vi.fn(() => ({
        matches: false,
        media: "",
        onchange: null,
        addListener: vi.fn(),
        removeListener: vi.fn(),
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        dispatchEvent: vi.fn(),
      })),
    );
    const client = renderQueryProvider(AppProviders);

    expect(client).toBeDefined();
  });

  it("프로브는 실제 QueryClient 인스턴스를 받는다", () => {
    const client = renderQueryProvider();

    expect(client.getDefaultOptions).toEqual(expect.any(Function));
  });
});
