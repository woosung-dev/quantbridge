// Sprint 13 Phase B: dogfood 전용 테스트 주문 다이얼로그(shell).
// production 환경에서는 NEXT_PUBLIC_ENABLE_TEST_ORDER=false(또는 미설정)면 렌더링하지 않는다.
// 스키마는 test-order-schema.ts, HMAC 서명·발송 money-path 는 test-order-webhook.ts 가 맡는다.
// 422/400 등 오류 시 setError("root.serverError")로 form 안에 인라인 표시한다.
"use client";

import { useState } from "react";
import { useForm, useWatch } from "react-hook-form";
import { useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useStrategies } from "@/features/strategy/hooks";
import { readWebhookSecret } from "@/features/strategy/webhook-secret-storage";
import { zodV4Resolver } from "@/lib/zod-v4-resolver";
import type { LiquidationParams } from "../api";
import { useExchangeAccounts, useIsOrderDisabledByKs, useLiquidationInfo } from "../hooks";
import {
  isPositiveDecimalString,
  TEST_ORDER_FORM_SCHEMA,
  type TestOrderFormValues,
} from "./test-order-schema";
import { sendTestOrder } from "./test-order-webhook";

export function TestOrderDialog() {
  // Production guard — env flag 미설정 시 button 자체 미렌더.
  if (process.env.NEXT_PUBLIC_ENABLE_TEST_ORDER !== "true") {
    return null;
  }

  return <TestOrderDialogInner />;
}

function TestOrderDialogInner() {
  const [open, setOpen] = useState(false);
  const qc = useQueryClient();
  const ksDisabled = useIsOrderDisabledByKs();
  const strategiesQuery = useStrategies({
    limit: 100,
    offset: 0,
    is_archived: false,
  });
  const accountsQuery = useExchangeAccounts();

  const form = useForm<TestOrderFormValues>({
    resolver: zodV4Resolver(TEST_ORDER_FORM_SCHEMA),
    defaultValues: {
      strategy_id: "",
      exchange_account_id: "",
      symbol: "BTCUSDT",
      side: "buy",
      sizing_mode: "quantity",
      quantity: "",
      risk_percent: "",
      take_profit: "",
      stop_loss: "",
      reduce_only: false,
      realized_pnl: "",
    },
  });
  // useWatch — React Compiler 호환(form.watch 는 memoize 불가 경고). 변경 시 re-render.
  const sizingMode = useWatch({ control: form.control, name: "sizing_mode" });
  const symbolWatch = useWatch({ control: form.control, name: "symbol" });
  const sideWatch = useWatch({ control: form.control, name: "side" });
  const strategyIdWatch = useWatch({
    control: form.control,
    name: "strategy_id",
  });
  const reduceOnlyWatch = useWatch({
    control: form.control,
    name: "reduce_only",
  });

  // BL-474 — 이 주문이 **어느 시장으로 나가는지** 를 발송 전에 보여준다.
  // 라우팅은 서버가 전략 Live Settings 로 결정한다(`webhook.resolve_trading_params`).
  // 추가 페치 0 — settings 는 이미 목록 응답에 실려 있다.
  const selectedStrategy = strategiesQuery.data?.items.find((s) => s.id === strategyIdWatch);
  const liveSettings = selectedStrategy?.settings ?? null;

  // Wave 2 청산가 미리보기 — 주문 payload 와 무관한 참고용 로컬 입력(예상 진입가 · 레버리지).
  // form schema/HMAC 서명에 포함되지 않는다(택배 발송 body 불변). 두 값이 유효할 때만
  // useLiquidationInfo 가 발사 → BE 순수 계산. 비거나 무효면 미발사(콘솔에러 0).
  //
  // BL-474 — 레버리지 기본값을 전략 설정에서 가져온다. 이전엔 여기 아무 숫자나 넣어도
  // 주문과 무관했는데 주문 레버리지처럼 보였다. 사용자 입력이 있으면 그쪽이 이긴다.
  // ★render-time 파생 — useEffect + RQ data dep 은 H-1 위반(무한 루프).
  const [previewEntryPrice, setPreviewEntryPrice] = useState("");
  const [previewLeverage, setPreviewLeverage] = useState("");
  const effectiveLeverage =
    previewLeverage.length > 0
      ? previewLeverage
      : liveSettings != null
        ? String(liveSettings.leverage)
        : "";
  const liqEntryValid = isPositiveDecimalString(previewEntryPrice);
  const liqLeverageValid = /^\d+$/.test(effectiveLeverage) && Number(effectiveLeverage) > 0;
  const liqParams: LiquidationParams | null =
    symbolWatch.length > 0 && liqEntryValid && liqLeverageValid
      ? {
          symbol: symbolWatch,
          side: sideWatch,
          entry_price: previewEntryPrice,
          leverage: Number(effectiveLeverage),
        }
      : null;
  const { data: liquidation } = useLiquidationInfo(liqParams);

  const onSubmit = async (values: TestOrderFormValues): Promise<void> => {
    // G.4 P1 #5 fix: KS active 시 submit 차단 (CSS pointer-events 만으로는
    // keyboard activation / Dialog 안에서 활성화된 KS 우회 가능).
    if (ksDisabled) {
      form.setError("root.serverError", {
        type: "manual",
        message: "Kill Switch 가 활성화된 상태로는 주문을 발송할 수 없습니다.",
      });
      return;
    }
    // G.4 P2 #6 fix: 재submit 시 stale 422 message 제거.
    form.clearErrors("root.serverError");

    const secret = readWebhookSecret(values.strategy_id);
    if (!secret) {
      form.setError("root.serverError", {
        type: "manual",
        message:
          "Webhook secret 캐시 없음. 전략 편집 화면 → §05 Webhook 카드 → " +
          "'Secret 회전' 실행 후 다시 시도하세요 (평문 secret 은 회전 직후에만 " +
          "브라우저에 캐시됩니다).",
      });
      return;
    }

    const result = await sendTestOrder(values, secret);
    if (!result.ok) {
      form.setError("root.serverError", {
        type: "manual",
        message: result.message,
      });
      return;
    }

    toast.success("테스트 주문 발송됨", {
      description: result.orderHint ?? undefined,
    });
    // tradingKeys.orders 는 (userId, limit) 인자가 필요한 factory 라
    // 모든 user/limit variation 을 한 번에 무효화하기 위해 prefix ["trading"] 사용.
    qc.invalidateQueries({ queryKey: ["trading"] });
    form.reset();
    setOpen(false);
  };

  const rootError = form.formState.errors.root?.serverError?.message;

  return (
    <>
      <Button size="sm" variant="outline" onClick={() => setOpen(true)}>
        테스트 주문
      </Button>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="sm:max-w-md">
          {/* Sprint 44 W C4 — header / desc / form / footer stagger entrance (50/100/150/200ms) */}
          <DialogHeader className="qb-dialog-stagger-1">
            <DialogTitle>테스트 주문 (dogfood-only)</DialogTitle>
            <DialogDescription>
              브라우저에서 webhook secret 으로 HMAC 서명 후 발송합니다. 실제 거래소로 주문이
              전달되니 demo 계정에서만 사용하세요.
            </DialogDescription>
          </DialogHeader>
          <Form {...form}>
            <form
              onSubmit={form.handleSubmit(onSubmit)}
              className="space-y-4 qb-dialog-stagger-3"
              noValidate
            >
              <FormField
                control={form.control}
                name="strategy_id"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>전략</FormLabel>
                    <Select onValueChange={field.onChange} value={field.value}>
                      <FormControl>
                        <SelectTrigger>
                          <SelectValue placeholder="전략 선택" />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        {strategiesQuery.data?.items.map((s) => (
                          <SelectItem key={s.id} value={s.id}>
                            {s.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <FormMessage />
                  </FormItem>
                )}
              />
              {/* BL-474 — 라우팅 표면화. 이 다이얼로그로 낸 주문이 라이브 신호와
                  다른 시장(spot)으로 나가면서 청산 원장·코크핏 어디에도 안 잡히던
                  적이 있다. 서버가 무엇으로 결정하는지 발송 전에 보여준다. */}
              {strategyIdWatch.length > 0 ? (
                liveSettings != null ? (
                  <p
                    data-testid="routing-badge"
                    className="rounded-md border border-dashed px-3 py-2 text-xs text-muted-foreground"
                  >
                    라우팅{" "}
                    <span className="font-mono font-semibold text-foreground">
                      Linear Perp · {liveSettings.leverage}x · {liveSettings.margin_mode}
                    </span>{" "}
                    (전략 Live Settings 를 서버가 적용합니다)
                  </p>
                ) : (
                  <p
                    role="alert"
                    data-testid="routing-warning"
                    className="rounded-md border border-destructive/30 bg-destructive-light px-3 py-2 text-xs text-destructive"
                  >
                    이 전략은 Live Settings(레버리지 · 마진 모드)가 없어 주문이 422 로 거부됩니다.
                    전략 편집 → 트레이딩 설정에서 먼저 지정하세요.
                  </p>
                )
              ) : null}
              <FormField
                control={form.control}
                name="exchange_account_id"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>거래소 계정</FormLabel>
                    <Select onValueChange={field.onChange} value={field.value}>
                      <FormControl>
                        <SelectTrigger>
                          <SelectValue placeholder="계정 선택" />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        {accountsQuery.data?.map((a) => (
                          <SelectItem key={a.id} value={a.id}>
                            {a.exchange} / {a.mode}
                            {a.label ? ` (${a.label})` : ""}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="symbol"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>심볼</FormLabel>
                    <FormControl>
                      <Input placeholder="BTCUSDT" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="side"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>방향</FormLabel>
                    <FormControl>
                      <fieldset className="flex gap-4" aria-label="주문 방향">
                        <label className="flex items-center gap-2 text-sm">
                          <input
                            type="radio"
                            value="buy"
                            checked={field.value === "buy"}
                            onChange={() => field.onChange("buy")}
                          />
                          Buy
                        </label>
                        <label className="flex items-center gap-2 text-sm">
                          <input
                            type="radio"
                            value="sell"
                            checked={field.value === "sell"}
                            onChange={() => field.onChange("sell")}
                          />
                          Sell
                        </label>
                      </fieldset>
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              {/* Wave 2 — 사이징 방식 택일. 수량 직접 ↔ 리스크 %(서버 권위). */}
              <FormField
                control={form.control}
                name="sizing_mode"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>사이징 방식</FormLabel>
                    <FormControl>
                      <fieldset className="flex flex-wrap gap-4" aria-label="사이징 방식">
                        <label className="flex min-h-11 items-center gap-2 text-sm">
                          <input
                            type="radio"
                            value="quantity"
                            checked={field.value === "quantity"}
                            onChange={() => field.onChange("quantity")}
                          />
                          직접 입력
                        </label>
                        <label className="flex min-h-11 items-center gap-2 text-sm">
                          <input
                            type="radio"
                            value="risk_percent"
                            checked={field.value === "risk_percent"}
                            onChange={() => field.onChange("risk_percent")}
                          />
                          리스크 %
                        </label>
                      </fieldset>
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              {/* BL-474 — 수량은 두 모드 모두 필수다. 서버는 수량을 계산하지 않고
                  상한만 검사한다(`_validate_position_size`). 이전 문구는 "서버가
                  계산합니다" 라고 했지만 그런 코드는 없었고, risk% 모드로 보낸
                  payload 는 quantity 누락으로 401 이었다. */}
              <FormField
                control={form.control}
                name="quantity"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>수량 (Decimal)</FormLabel>
                    <FormControl>
                      <Input inputMode="decimal" placeholder="0.001" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              {sizingMode === "risk_percent" ? (
                <FormField
                  control={form.control}
                  name="risk_percent"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>리스크 % (수량 상한 검증)</FormLabel>
                      <FormControl>
                        <Input inputMode="decimal" placeholder="1.0" {...field} />
                      </FormControl>
                      <p className="text-xs text-muted-foreground">
                        서버가 자본 × 리스크% ÷ |진입가 − 손절가| 로 상한을 구해 위 수량이 넘으면
                        거부합니다. 손절가가 있어야 계산됩니다.
                      </p>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              ) : null}
              {/* Wave 2 — bracket TP/SL (둘 다 optional). */}
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <FormField
                  control={form.control}
                  name="take_profit"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>익절가 TP (선택)</FormLabel>
                      <FormControl>
                        <Input inputMode="decimal" placeholder="예: 55000" {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={form.control}
                  name="stop_loss"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>손절가 SL (선택)</FormLabel>
                      <FormControl>
                        <Input inputMode="decimal" placeholder="예: 48000" {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>
              {/* Wave 2 — reduce-only (청산 전용 주문). */}
              <FormField
                control={form.control}
                name="reduce_only"
                render={({ field }) => (
                  <FormItem>
                    <FormControl>
                      <label className="flex min-h-11 cursor-pointer items-center gap-2 text-sm">
                        <input
                          type="checkbox"
                          checked={field.value}
                          onChange={(e) => field.onChange(e.target.checked)}
                        />
                        reduce-only (청산 전용 — 포지션만 줄임)
                      </label>
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              {/* BL-474 — 청산 주문의 전략 추정 손익. 파서(`webhook.py:114-117`)는
                  진작부터 읽고 있었고 다이얼로그만 안 보냈다. 이 값이 있어야
                  `realized_pnl IS NOT NULL AND synced_at IS NULL` = "추정" 상태가
                  생겨, 스윕이 확정으로 바꾸기 전/후를 화면에서 대조할 수 있다.
                  진입 주문엔 의미가 없고 kill-switch 가 SUM 하므로 청산일 때만 노출. */}
              {reduceOnlyWatch ? (
                <FormField
                  control={form.control}
                  name="realized_pnl"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>실현 손익 (선택 · 전략 추정값)</FormLabel>
                      <FormControl>
                        <Input
                          inputMode="decimal"
                          placeholder="예: -12.5 (손실은 음수)"
                          {...field}
                        />
                      </FormControl>
                      <p className="text-xs text-muted-foreground">
                        거래소가 확정하기 전까지 표시될 추정값입니다. 스윕이 확정 손익으로
                        교체합니다.
                      </p>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              ) : null}
              {/* Wave 2 — 청산가 미리보기(참고용). 주문 body 와 무관한 로컬 입력. */}
              <div className="space-y-3 rounded-md border border-dashed p-3">
                <p className="text-sm font-medium">청산가 미리보기 (참고용)</p>
                <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                  <div className="space-y-1">
                    <label htmlFor="liq-preview-entry" className="text-sm font-medium">
                      예상 진입가
                    </label>
                    <Input
                      id="liq-preview-entry"
                      inputMode="decimal"
                      placeholder="예: 50000"
                      value={previewEntryPrice}
                      onChange={(e) => setPreviewEntryPrice(e.target.value)}
                    />
                  </div>
                  <div className="space-y-1">
                    <label htmlFor="liq-preview-leverage" className="text-sm font-medium">
                      레버리지 (배)
                      {liveSettings != null ? (
                        <span className="ml-1 font-normal text-muted-foreground">
                          · 전략 설정 {liveSettings.leverage}x
                        </span>
                      ) : null}
                    </label>
                    <Input
                      id="liq-preview-leverage"
                      inputMode="numeric"
                      placeholder="예: 10"
                      value={effectiveLeverage}
                      onChange={(e) => setPreviewLeverage(e.target.value)}
                    />
                  </div>
                </div>
                {liquidation ? (
                  <p data-testid="liquidation-preview" className="text-sm text-foreground">
                    예상 청산가{" "}
                    <span className="font-mono font-semibold">{liquidation.liquidation_price}</span>{" "}
                    <span className="text-muted-foreground">
                      (진입가 대비 {liquidation.distance_pct}%)
                    </span>
                  </p>
                ) : (
                  <p className="text-xs text-muted-foreground">
                    심볼·방향 선택 후 예상 진입가와 레버리지를 입력하면 청산가를 표시합니다.
                  </p>
                )}
              </div>
              {rootError ? (
                <p
                  role="alert"
                  className="qb-form-slide-down rounded-md border border-destructive/30 bg-destructive-light px-3 py-2 text-sm text-destructive"
                >
                  {rootError}
                </p>
              ) : null}
              <div className="qb-dialog-stagger-4 flex justify-end gap-2 pt-2">
                <Button type="button" variant="ghost" onClick={() => setOpen(false)}>
                  취소
                </Button>
                <Button
                  type="submit"
                  disabled={form.formState.isSubmitting || ksDisabled}
                  aria-disabled={ksDisabled || undefined}
                >
                  {ksDisabled ? (
                    "Kill Switch 활성화"
                  ) : form.formState.isSubmitting ? (
                    <span className="inline-flex items-center gap-2">
                      {/* spinner inline — 150ms 전 click 직후부터 동작 시인성 */}
                      <span
                        aria-hidden
                        className="size-3 animate-spin rounded-full border-2 border-current border-t-transparent"
                      />
                      발송 중...
                    </span>
                  ) : (
                    "발송"
                  )}
                </Button>
              </div>
            </form>
          </Form>
        </DialogContent>
      </Dialog>
    </>
  );
}
