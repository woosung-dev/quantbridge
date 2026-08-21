// 얇은 dashboard route — 정적 metadata와 단일 feature view 위임 배선을 함께 고정한다.

import type { Metadata } from "next";
import type { ComponentType } from "react";
import { afterEach, beforeEach, describe, expect, it, vi, type Mock } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";

const mocks = vi.hoisted(() => ({
  dashboardCockpit: vi.fn(),
  waitlistAdminView: vi.fn(),
  optimizerPageView: vi.fn(),
  ordersBlotter: vi.fn(),
  tradingCockpit: vi.fn(),
  backtestForm: vi.fn(),
  newStrategyWizard: vi.fn(),
}));

vi.mock("@/features/dashboard/components/dashboard-cockpit", () => ({
  DashboardCockpit: mocks.dashboardCockpit,
}));
vi.mock("@/features/waitlist/components/admin/waitlist-admin-view", () => ({
  WaitlistAdminView: mocks.waitlistAdminView,
}));
vi.mock("@/features/optimizer/components/optimizer-page-view", () => ({
  OptimizerPageView: mocks.optimizerPageView,
}));
vi.mock("@/features/trading/components/orders/orders-blotter", () => ({
  OrdersBlotter: mocks.ordersBlotter,
}));
vi.mock("@/features/trading/components/trading-cockpit", () => ({
  TradingCockpit: mocks.tradingCockpit,
}));
vi.mock("@/features/backtest/components/forms/backtest-form", () => ({
  BacktestForm: mocks.backtestForm,
}));
vi.mock("@/features/strategy/components/new/new-strategy-wizard", () => ({
  NewStrategyWizard: mocks.newStrategyWizard,
}));

import DashboardPage, { metadata as dashboardMetadata } from "../dashboard/page";
import * as dashboardRouteModule from "../dashboard/page";
import AdminWaitlistPage, { metadata as adminWaitlistMetadata } from "../admin/waitlist/page";
import * as adminWaitlistRouteModule from "../admin/waitlist/page";
import OptimizerPage, { metadata as optimizerMetadata } from "../optimizer/page";
import * as optimizerRouteModule from "../optimizer/page";
import OrdersPage, { metadata as ordersMetadata } from "../orders/page";
import * as ordersRouteModule from "../orders/page";
import TradingPage, { metadata as tradingMetadata } from "../trading/page";
import * as tradingRouteModule from "../trading/page";
import NewBacktestPage, { metadata as newBacktestMetadata } from "../backtests/new/page";
import * as newBacktestRouteModule from "../backtests/new/page";
import NewStrategyPage, { metadata as newStrategyMetadata } from "../strategies/new/page";
import * as newStrategyRouteModule from "../strategies/new/page";

type ThinRoute = {
  name: string;
  Page: ComponentType;
  metadata: Metadata;
  module: object;
  viewMock: Mock;
  markerTestId: string;
  markerText: string;
};

const THIN_ROUTES: readonly ThinRoute[] = [
  {
    name: "/dashboard",
    Page: DashboardPage,
    metadata: dashboardMetadata,
    module: dashboardRouteModule,
    viewMock: mocks.dashboardCockpit,
    markerTestId: "thin-route-dashboard-cockpit",
    markerText: "DashboardCockpit marker",
  },
  {
    name: "/admin/waitlist",
    Page: AdminWaitlistPage,
    metadata: adminWaitlistMetadata,
    module: adminWaitlistRouteModule,
    viewMock: mocks.waitlistAdminView,
    markerTestId: "thin-route-waitlist-admin-view",
    markerText: "WaitlistAdminView marker",
  },
  {
    name: "/optimizer",
    Page: OptimizerPage,
    metadata: optimizerMetadata,
    module: optimizerRouteModule,
    viewMock: mocks.optimizerPageView,
    markerTestId: "thin-route-optimizer-page-view",
    markerText: "OptimizerPageView marker",
  },
  {
    name: "/orders",
    Page: OrdersPage,
    metadata: ordersMetadata,
    module: ordersRouteModule,
    viewMock: mocks.ordersBlotter,
    markerTestId: "thin-route-orders-blotter",
    markerText: "OrdersBlotter marker",
  },
  {
    name: "/trading",
    Page: TradingPage,
    metadata: tradingMetadata,
    module: tradingRouteModule,
    viewMock: mocks.tradingCockpit,
    markerTestId: "thin-route-trading-cockpit",
    markerText: "TradingCockpit marker",
  },
  {
    name: "/backtests/new",
    Page: NewBacktestPage,
    metadata: newBacktestMetadata,
    module: newBacktestRouteModule,
    viewMock: mocks.backtestForm,
    markerTestId: "thin-route-backtest-form",
    markerText: "BacktestForm marker",
  },
  {
    name: "/strategies/new",
    Page: NewStrategyPage,
    metadata: newStrategyMetadata,
    module: newStrategyRouteModule,
    viewMock: mocks.newStrategyWizard,
    markerTestId: "thin-route-new-strategy-wizard",
    markerText: "NewStrategyWizard marker",
  },
];

beforeEach(() => {
  THIN_ROUTES.forEach((route) => {
    route.viewMock.mockReset();
    route.viewMock.mockImplementation(() => (
      <div data-testid={route.markerTestId}>{route.markerText}</div>
    ));
  });
});

afterEach(cleanup);

describe("dashboard thin routes", () => {
  it.each(THIN_ROUTES)("%s renders without throwing", ({ Page }) => {
    render(<Page />);

    expect(document.body.textContent?.trim()).not.toBe("");
  });

  it.each(THIN_ROUTES)("%s renders only its delegated view", (route) => {
    render(<route.Page />);

    expect(screen.getAllByTestId(route.markerTestId)).toHaveLength(1);
    THIN_ROUTES.filter((otherRoute) => otherRoute !== route).forEach((otherRoute) => {
      expect(screen.queryAllByTestId(otherRoute.markerTestId)).toHaveLength(0);
    });
  });

  it.each(THIN_ROUTES)("%s has a non-empty static metadata title", ({ metadata }) => {
    expect(typeof metadata.title).toBe("string");
    expect((metadata.title as string).trim()).not.toBe("");
  });

  it("uses seven distinct page titles", () => {
    const titles = THIN_ROUTES.map(({ metadata }) => metadata.title as string);

    expect(new Set(titles)).toHaveLength(THIN_ROUTES.length);
  });

  it.each(THIN_ROUTES)("%s leaves the QuantBridge suffix to the root template", ({ metadata }) => {
    expect(metadata.title).not.toContain("QuantBridge");
  });

  it.each(THIN_ROUTES)("%s does not export generateMetadata", ({ module }) => {
    expect("generateMetadata" in module).toBe(false);
  });

  it.each(THIN_ROUTES)("%s is not an async page function", ({ Page }) => {
    expect(Page.constructor.name).not.toBe("AsyncFunction");
  });

  it.each(THIN_ROUTES)("%s forwards no props to its delegated view", (route) => {
    render(<route.Page />);

    expect(route.viewMock).toHaveBeenCalledTimes(1);
    const receivedProps = route.viewMock.mock.calls[0]?.[0] as Record<string, unknown> | undefined;
    expect(receivedProps).toBeDefined();
    const { children: _children, ...viewProps } = receivedProps ?? {};
    expect(viewProps).toEqual({});
  });
});
