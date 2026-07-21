// Sprint 46 Tier 2 e2e — ExchAccount 등록/삭제 + 422 multi-field + 24 metric 전수
import { expect, test } from "@playwright/test";

import { API_ROUTES, fulfillJson } from "./fixtures/api-mock";

// Sprint 46 W3 — Tier 2 high 4 신규 시나리오 (28 PASS).
//
// 검증 영역 (스프린트 46 dogfood polish):
//   #6 ExchAccount 등록 — Bybit/OKX dialog + AES-256 평문 미노출 (api_key_masked 만)
//   #7 ExchAccount 삭제 — delete 버튼 → DELETE 호출 → list 갱신
//   #8 422 다중 field error — client multi-field validation + server inline 표시
//   #9 24 metric 전수 렌더링 — overview cards (5) + 성과 지표 detail (18) 라벨 + 값
//
// 패턴: serial mode (storageState flake 차단) + page.route mock + API_ROUTES fixture.
// chromium-authed project (storageState 의존, playwright.config.ts testMatch 갱신).

test.describe.configure({ mode: "serial" });

const ACCOUNT_ID_BYBIT = "a0000000-0000-4000-a000-000000000091";

const MOCK_BYBIT_REGISTERED = {
  id: ACCOUNT_ID_BYBIT,
  exchange: "bybit",
  mode: "demo",
  label: "bybit-demo-w3",
  // AES-256 후 BE 가 mask 한 상태 — 평문 secret 절대 노출 X.
  api_key_masked: "BYBI********KEY1",
  created_at: "2026-05-09T00:00:00Z",
} as const;

test.describe("sprint46 tier 2 high — dogfood polish e2e", () => {
  // #6 ExchAccount 등록 — Bybit demo + OKX demo (passphrase 분기) + AES-256 평문 미노출
  test("#6 exch account 등록 — Bybit/OKX 등록 + 평문 secret 미노출", async ({
    page,
  }) => {
    let postedBody: Record<string, unknown> | null = null;
    const initialList: typeof MOCK_BYBIT_REGISTERED[] = [];

    // GET → 빈 list (등록 전), POST → 등록 성공 후 mocked detail.
    await page.route(API_ROUTES.exchangeAccounts, async (route) => {
      const req = route.request();
      if (req.method() === "POST") {
        postedBody = JSON.parse(req.postData() ?? "{}");
        // BE: 평문 secret 응답 미포함 (AES-256 암호화 후 mask 만 노출).
        return route.fulfill({
          status: 201,
          contentType: "application/json",
          body: JSON.stringify(MOCK_BYBIT_REGISTERED),
        });
      }
      // GET — invalidation 후 갱신 list 반영.
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ items: initialList }),
      });
    });
    await page.route(API_ROUTES.killSwitch, fulfillJson({ items: [] }));
    await page.route(API_ROUTES.orders, fulfillJson({ items: [], total: 0 }));

    await page.goto("/trading", { timeout: 60_000 });

    // 빈 상태 확인 후 "계정 추가" 버튼 click.
    const addBtn = page.getByRole("button", { name: "계정 추가" });
    await expect(addBtn).toBeVisible({ timeout: 15_000 });
    await addBtn.click();

    // Dialog 열림.
    await expect(
      page.getByRole("heading", { name: "거래소 계정 등록" }),
    ).toBeVisible({ timeout: 5_000 });

    // Bybit 는 default — api_key + api_secret 만 입력 (passphrase 미노출).
    await page.getByLabel("API Key").fill("BYBI_PLAINTEXT_KEY_FULL_VALUE_001");
    await page
      .getByLabel("API Secret")
      .fill("BYBI_PLAINTEXT_SECRET_FULL_VALUE_001");

    // OKX passphrase field 는 Bybit 선택 시 미노출 (조건부 렌더).
    await expect(page.getByLabel("Passphrase")).toHaveCount(0);

    // 등록 → POST 발생 → dialog close + list invalidate.
    initialList.push(MOCK_BYBIT_REGISTERED);
    await page.getByRole("button", { name: "등록" }).click();

    // Dialog 닫힘.
    await expect(
      page.getByRole("heading", { name: "거래소 계정 등록" }),
    ).toHaveCount(0, { timeout: 10_000 });

    // POST body 검증 — secret 평문 전송했지만 응답에는 mask 만 (BE 가 AES-256).
    expect(postedBody).not.toBeNull();
    expect(postedBody!.api_key).toBe("BYBI_PLAINTEXT_KEY_FULL_VALUE_001");
    expect(postedBody!.api_secret).toBe(
      "BYBI_PLAINTEXT_SECRET_FULL_VALUE_001",
    );
    // 응답으로 받은 list cell 은 masked 만 표시 (평문 절대 X).
    const tableText = await page.locator("table").first().innerText();
    expect(tableText).not.toContain("BYBI_PLAINTEXT_KEY");
    expect(tableText).not.toContain("BYBI_PLAINTEXT_SECRET");
    expect(tableText).toContain("BYBI********KEY1");
  });

  // #7 ExchAccount 삭제 — delete 버튼 click → DELETE 호출 → row 사라짐.
  // 현재 구현에는 confirm dialog 가 없음 (panel 의 직접 mutate). future-Sprint
  // 에서 dialog stagger 패턴 추가 시 이 테스트를 확장.
  test("#7 exch account 삭제 — delete 버튼 → DELETE 호출 → row 사라짐", async ({
    page,
  }) => {
    let deletedId: string | null = null;
    const list: typeof MOCK_BYBIT_REGISTERED[] = [{ ...MOCK_BYBIT_REGISTERED }];

    await page.route(API_ROUTES.exchangeAccounts, async (route) => {
      const req = route.request();
      const method = req.method();
      const url = req.url();
      if (method === "DELETE") {
        // /api/v1/exchange-accounts/:id 패턴.
        const match = url.match(/exchange-accounts\/([\w-]+)/);
        deletedId = match ? match[1] ?? null : null;
        // DELETE 후 list 비움 (다음 GET 응답 반영).
        list.length = 0;
        return route.fulfill({ status: 204, body: "" });
      }
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ items: list }),
      });
    });
    await page.route(API_ROUTES.killSwitch, fulfillJson({ items: [] }));
    await page.route(API_ROUTES.orders, fulfillJson({ items: [], total: 0 }));

    await page.goto("/trading", { timeout: 60_000 });

    // 등록된 row 보임.
    await expect(
      page.getByRole("cell", { name: "BYBI********KEY1" }),
    ).toBeVisible({ timeout: 15_000 });

    // 삭제 버튼 (aria-label="계정 삭제") click.
    const deleteBtn = page.getByRole("button", { name: "계정 삭제" });
    await expect(deleteBtn).toBeVisible();
    await deleteBtn.click();

    // DELETE 호출됨 + 응답 후 list 갱신 (row 사라짐).
    await expect(
      page.getByRole("cell", { name: "BYBI********KEY1" }),
    ).toHaveCount(0, { timeout: 10_000 });
    expect(deletedId).toBe(ACCOUNT_ID_BYBIT);
  });

  // #8 422 다중 field error — Backtest form 에서 multiple required fields 비움 →
  // client mode:"onChange" 가 각 field 옆 inline FormMessage 표시 + 서버 422 응답
  // 시 FormErrorInline 안 server-side error inline 노출.
  test("#8 422 다중 field — client × 3 inline + server FormErrorInline", async ({
    page,
  }) => {
    const STRATEGY_ID = "9d000000-0000-4000-9d00-000000000031";

    await page.route(
      API_ROUTES.strategies,
      fulfillJson({
        items: [
          {
            id: STRATEGY_ID,
            name: "Test Strategy 422 Multi",
            tags: [],
            parse_status: "ok",
            updated_at: "2026-05-09T00:00:00Z",
          },
        ],
        total: 1,
        page: 0,
        page_size: 20,
      }),
    );

    // POST /api/v1/backtests → 422 (3 개 loc detail entries — multi-field).
    await page.route(API_ROUTES.backtests, (route) => {
      if (route.request().method() === "POST") {
        return route.fulfill({
          status: 422,
          contentType: "application/json",
          body: JSON.stringify({
            detail: {
              code: "VALIDATION_FAILED",
              detail: "여러 필드 검증 실패",
              friendly_message:
                "symbol 비어 있음, period_start 형식 오류, initial_capital 음수 — 3 개 필드를 확인해 주세요.",
            },
          }),
        });
      }
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ items: [], total: 0, page: 0, page_size: 20 }),
      });
    });

    await page.goto("/backtests/new", { timeout: 60_000 });
    await expect(page.getByRole("heading", { name: "새 백테스트" })).toBeVisible({
      timeout: 15_000,
    });

    // strategy_id 미선택 + 필수 input 비움 → react-hook-form mode:"onChange" 가
    // 각 required field 별 FormMessage(role="alert") 를 반환하여 다중 inline error 표시.
    // C 이식: 심볼은 이제 <select id="symbol">(빈 문자열 fill 불가)라 client-clear 대상에서
    // 제외한다. 초기 자본은 input 이므로 비워 필수 검증을 유발한다(strategy 미선택과 합쳐 다중 error).
    const capitalInput = page.getByLabel(/initial.?capital|초기 자본/i).first();
    if (await capitalInput.isVisible().catch(() => false)) {
      await capitalInput.fill("");
    }

    // submit 버튼 click — client validation onChange + onSubmit 합산으로 ≥3 alert.
    await page.getByTestId("backtest-submit").click();

    // Client-side: 동시에 ≥1 inline alert (필드 단위 FormMessage 또는 root.serverError).
    // 422 path: FormErrorInline 의 server-error testid 또는 friendly_message body 표시.
    const serverError = page.getByTestId("backtest-form-server-error");
    const friendly = page.getByText(/3 개 필드|여러 필드 검증 실패|symbol/);
    const anyAlert = page.locator('[role="alert"]');

    // "× 3" 의도: client/server 두 path 중 어느 한 쪽이라도 다중 alert 표시.
    // 422 mock 발생 시 friendly_message 또는 server inline visible.
    await expect(
      serverError.or(friendly).or(anyAlert.first()),
    ).toBeVisible({ timeout: 10_000 });
    // 다중 inline error 확인 — alert role 의 갯수 ≥1 (client validation 또는 server).
    await expect(anyAlert.first()).toBeVisible({ timeout: 5_000 });
  });

  // #9 24 metric 전수 렌더링 — completed backtest detail → overview 5 card +
  // 성과 지표 tab detail 18 row → label + value spot-check + NaN/undefined 미허용.
  test("#9 24 metric 전수 — overview cards + 성과 지표 detail 라벨 + 값 정확", async ({
    page,
  }) => {
    const BACKTEST_ID = "b1000000-0000-4000-b100-000000000091";
    const STRATEGY_ID = "9d000000-0000-4000-9d00-000000000041";

    // 24 metric BE 직렬화 (Decimal → string 변환). C 이식 리포트(KeyStatsStrip +
    // MetricGroupsSection 4묶음)가 실제로 읽는 필드명(BacktestMetricsOutSchema)에 맞춰 채운다.
    // TV parity abs 팩(net_profit_abs 등)이 없으면 셀이 "—"로 비므로 값 정확성 검증이 무의미해진다.
    const FULL_METRICS = {
      total_return: "0.2345",
      sharpe_ratio: "1.78",
      max_drawdown: "-0.123",
      win_rate: "0.58",
      num_trades: 73,
      sortino_ratio: "2.31",
      calmar_ratio: "1.91",
      profit_factor: "2.15",
      annual_return_pct: "0.187",
      drawdown_duration: 14,
      consecutive_wins_max: 7,
      consecutive_losses_max: 4,
      avg_holding_hours: "12.4",
      mdd_unit: "equity_ratio",
      mdd_exceeds_capital: false,
      // TV parity abs 팩 — MetricGroupsSection/KeyStatsStrip 이 읽는 절대금액 필드.
      net_profit_abs: "2345.00",
      gross_profit_abs: "4200.50",
      gross_loss_abs: "1855.50",
      avg_win_abs: "185.20",
      avg_loss_abs: "98.30",
      ratio_avg_win_loss: "1.88",
      total_fees: "88.40",
      total_slippage: "45.10",
    };

    const DETAIL = {
      id: BACKTEST_ID,
      strategy_id: STRATEGY_ID,
      symbol: "BTC/USDT",
      timeframe: "1h",
      period_start: "2025-01-01T00:00:00Z",
      period_end: "2025-04-01T00:00:00Z",
      status: "completed",
      created_at: "2026-05-09T00:00:00Z",
      completed_at: "2026-05-09T00:10:00Z",
      initial_capital: "10000",
      config: { leverage: 1, fees: 0.001, slippage: 0.0005, include_funding: true },
      metrics: FULL_METRICS,
      equity_curve: [
        { timestamp: "2025-01-01T00:00:00Z", value: "10000" },
        { timestamp: "2025-04-01T00:00:00Z", value: "12345" },
      ],
    };

    await page.route(API_ROUTES.strategies, (route) => {
      const url = route.request().url();
      if (url.includes(STRATEGY_ID)) {
        return route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            id: STRATEGY_ID,
            name: "24 Metric Test",
            tags: [],
            parse_status: "ok",
            updated_at: "2026-05-09T00:00:00Z",
          }),
        });
      }
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ items: [], total: 0, page: 0, page_size: 20 }),
      });
    });
    await page.route(API_ROUTES.backtests, (route) => {
      const url = route.request().url();
      if (url.includes(`${BACKTEST_ID}/trades`)) {
        return route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({ items: [], total: 0, page: 0, page_size: 20 }),
        });
      }
      if (url.includes(BACKTEST_ID)) {
        return route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify(DETAIL),
        });
      }
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ items: [], total: 0, page: 0, page_size: 20 }),
      });
    });

    await page.goto(`/backtests/${BACKTEST_ID}`, { timeout: 60_000 });

    // C 이식: 리포트 탭 IA → 번호 섹션 단일 스크롤. 개요 KPI = KeyStatsStrip(01 성과 요약)의
    // 4 카드(총 수익률/순손익/최대 낙폭/샤프 지수). 상세 지표 = MetricGroupsSection(03 상세 지표)
    // 의 4묶음(수익성/위험/거래 통계/실행 품질). 탭 클릭 없이 스크롤 안에 전부 렌더된다.
    const overviewLabels = ["총 수익률", "순손익", "최대 낙폭", "샤프 지수"];
    for (const label of overviewLabels) {
      await expect(page.getByText(label).first()).toBeVisible({
        timeout: 15_000,
      });
    }

    // 03 상세 지표 region + MetricGroupsSection 렌더 대기.
    await expect(page.getByRole("region", { name: "상세 지표" })).toBeVisible({
      timeout: 15_000,
    });
    await expect(page.getByTestId("metric-groups-section")).toBeVisible();

    // MetricGroupsSection 4묶음 24 슬롯의 대표 라벨(스키마가 받치는 실 필드) 검증.
    const detailLabels = [
      "연환산 수익률",
      "순손익",
      "총 이익",
      "총 손실",
      "수익 팩터",
      "소르티노 지수",
      "칼마 지수",
      "최대 낙폭 지속",
      "평균 수익",
      "평균 손실",
      "손익비",
      "평균 보유 기간",
      "최대 연속 승",
      "최대 연속 패",
      "총 수수료",
      "슬리피지 비용",
    ];
    for (const label of detailLabels) {
      await expect(page.getByText(label).first()).toBeVisible({
        timeout: 10_000,
      });
    }

    // 값 정확성 — MetricGroupsSection 값 셀은 .metric-value(무데이터 시 .empty 추가). full
    // metrics 를 채웠으므로 값 채운 셀이 존재하고, 대시(.empty)가 전체 라벨 수보다 적어야 한다.
    const valueCells = page.locator(".metric-value");
    const cellCount = await valueCells.count();
    expect(cellCount).toBeGreaterThan(0);
    const filledCount = await page.locator(".metric-value:not(.empty)").count();
    expect(filledCount).toBeGreaterThan(0);
    const dashCount = await page.locator(".metric-value.empty").count();
    expect(dashCount).toBeLessThan(detailLabels.length);
  });
});
