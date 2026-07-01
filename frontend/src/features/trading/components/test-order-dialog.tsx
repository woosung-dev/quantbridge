"use client";

// Sprint 13 Phase B: dogfood-only Test Order Dialog.
//
// 보안 trade-off (dogfood-only):
// - production env 에서는 NEXT_PUBLIC_ENABLE_TEST_ORDER=false (또는 미설정).
// - sessionStorage 캐시된 webhook secret 으로 browser-side HMAC 서명 → 외부 노출 금지.
// - apiFetch helper 우회 — body 직렬화 drift 방지 위해 raw fetch + 단일 bodyStr 사용.
// - 422/400 등 error 시 setError("root.serverError") 로 form 안에 inline 표시.

import { useState } from "react";
import { useForm, useWatch, type FieldValues, type Resolver } from "react-hook-form";
import { useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { z, type core } from "zod/v4";

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
import { getApiBase, readErrorBody } from "@/lib/api-base";
import type { LiquidationParams } from "../api";
import {
  useExchangeAccounts,
  useIsOrderDisabledByKs,
  useLiquidationInfo,
} from "../hooks";

// 양수 Decimal 문자열 판정 — 수량/TP/SL/risk% 공용.
function isPositiveDecimalString(v: string): boolean {
  if (!/^\d*\.?\d+$/.test(v)) return false;
  return Number(v) > 0;
}

// Wave 2 — sizing 택일(수량 직접 ↔ risk% 서버 권위) + bracket TP/SL + reduce-only.
// risk_percent 는 W-A `OrderRequest.risk_percent`(Decimal,%) 계약 (미머지 → 서버 사이징은 Phase 3).
const TEST_ORDER_FORM_SCHEMA = z
  .object({
    strategy_id: z.string().min(1, "전략을 선택하세요."),
    exchange_account_id: z.string().min(1, "거래소 계정을 선택하세요."),
    symbol: z.string().min(1, "심볼을 입력하세요."),
    side: z.enum(["buy", "sell"]),
    sizing_mode: z.enum(["quantity", "risk_percent"]),
    // sizing 택일로 quantity/risk_percent 가 조건부 unmount → RHF 가 값을 제거할 수 있어
    // `.default("")` 로 undefined 를 "" 로 흡수 (없으면 z.string() 이 silent "Required" 발생).
    quantity: z.string().default(""),
    risk_percent: z.string().default(""),
    take_profit: z.string().default(""),
    stop_loss: z.string().default(""),
    reduce_only: z.boolean().default(false),
  })
  .superRefine((data, ctx) => {
    if (data.sizing_mode === "quantity") {
      if (data.quantity.length === 0) {
        ctx.addIssue({
          code: "custom",
          path: ["quantity"],
          message: "수량을 입력하세요.",
        });
      } else if (!isPositiveDecimalString(data.quantity)) {
        ctx.addIssue({
          code: "custom",
          path: ["quantity"],
          message: "수량은 0보다 큰 숫자여야 합니다.",
        });
      }
    } else {
      if (data.risk_percent.length === 0) {
        ctx.addIssue({
          code: "custom",
          path: ["risk_percent"],
          message: "리스크 %를 입력하세요.",
        });
      } else if (
        !isPositiveDecimalString(data.risk_percent) ||
        Number(data.risk_percent) > 100
      ) {
        ctx.addIssue({
          code: "custom",
          path: ["risk_percent"],
          message: "리스크 %는 0 초과 100 이하 숫자여야 합니다.",
        });
      }
    }
    if (data.take_profit.length > 0 && !isPositiveDecimalString(data.take_profit)) {
      ctx.addIssue({
        code: "custom",
        path: ["take_profit"],
        message: "익절가는 0보다 큰 숫자여야 합니다.",
      });
    }
    if (data.stop_loss.length > 0 && !isPositiveDecimalString(data.stop_loss)) {
      ctx.addIssue({
        code: "custom",
        path: ["stop_loss"],
        message: "손절가는 0보다 큰 숫자여야 합니다.",
      });
    }
  });

type TestOrderFormValues = z.infer<typeof TEST_ORDER_FORM_SCHEMA>;

// Zod v4 + RHF 호환 custom resolver. `@hookform/resolvers/zod@3.10.0` 가
// `error.errors` (Zod v3) 를 검사해서 v4 의 `error.issues` 를 throw 하는 호환성
// 이슈를 우회하기 위함. issues → RHF errors 매핑.
function zodV4Resolver<TValues extends FieldValues>(
  schema: z.ZodType<TValues>,
): Resolver<TValues> {
  const resolver: Resolver<TValues> = async (values) => {
    const parsed = await schema.safeParseAsync(values);
    if (parsed.success) {
      return { values: parsed.data as TValues, errors: {} };
    }
    const errors: Record<string, { type: string; message: string }> = {};
    for (const issue of parsed.error.issues as core.$ZodIssue[]) {
      const path = issue.path.join(".");
      if (!errors[path]) {
        errors[path] = { type: issue.code, message: issue.message };
      }
    }
    return {
      values: {},
      // RHF nested errors path 는 flat key (예: "quantity") 이므로 cast 안전.
      errors: errors as unknown as Awaited<
        ReturnType<Resolver<TValues>>
      >["errors"],
    };
  };
  return resolver;
}

// Sprint 14 Phase B-3 — getApiBase helper 통합 (3 곳 일관성 + trailing slash strip).
const API_BASE_URL = getApiBase();

// ArrayBuffer → lowercase hex string. Python `.hexdigest()` 호환.
function bufferToHex(buf: ArrayBuffer): string {
  return Array.from(new Uint8Array(buf))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

async function computeHmacSha256Hex(
  secret: string,
  bodyStr: string,
): Promise<string> {
  const encoder = new TextEncoder();
  const key = await crypto.subtle.importKey(
    "raw",
    encoder.encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"],
  );
  const sigBuf = await crypto.subtle.sign(
    "HMAC",
    key,
    encoder.encode(bodyStr),
  );
  return bufferToHex(sigBuf);
}

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
    },
  });
  // useWatch — React Compiler 호환(form.watch 는 memoize 불가 경고). 변경 시 re-render.
  const sizingMode = useWatch({ control: form.control, name: "sizing_mode" });
  const symbolWatch = useWatch({ control: form.control, name: "symbol" });
  const sideWatch = useWatch({ control: form.control, name: "side" });

  // Wave 2 청산가 미리보기 — 주문 payload 와 무관한 참고용 로컬 입력(예상 진입가 · 레버리지).
  // form schema/HMAC 서명에 포함되지 않는다(택배 발송 body 불변). 두 값이 유효할 때만
  // useLiquidationInfo 가 발사 → BE 순수 계산. 비거나 무효면 미발사(콘솔에러 0).
  const [previewEntryPrice, setPreviewEntryPrice] = useState("");
  const [previewLeverage, setPreviewLeverage] = useState("");
  const liqEntryValid = isPositiveDecimalString(previewEntryPrice);
  const liqLeverageValid =
    /^\d+$/.test(previewLeverage) && Number(previewLeverage) > 0;
  const liqParams: LiquidationParams | null =
    symbolWatch.length > 0 && liqEntryValid && liqLeverageValid
      ? {
          symbol: symbolWatch,
          side: sideWatch,
          entry_price: previewEntryPrice,
          leverage: Number(previewLeverage),
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
          "Webhook secret 캐시 없음. Strategy 페이지에서 Rotate 후 다시 시도하세요.",
      });
      return;
    }

    // 기본 5필드 순서 보존(symbol/side/type/quantity/exchange_account_id) — 기존 HMAC
    // golden vector + body 정확매칭 테스트 유지. risk% 모드면 quantity 대신 risk_percent
    // (서버 권위 사이징). optional Wave1 필드는 값이 있을 때만 append.
    const payload: Record<string, unknown> = {
      symbol: values.symbol,
      side: values.side,
      type: "market",
    };
    if (values.sizing_mode === "quantity") {
      payload.quantity = values.quantity;
    } else {
      payload.risk_percent = values.risk_percent;
    }
    payload.exchange_account_id = values.exchange_account_id;
    if (values.take_profit.length > 0) {
      payload.take_profit = values.take_profit;
    }
    if (values.stop_loss.length > 0) {
      payload.stop_loss = values.stop_loss;
    }
    if (values.reduce_only) {
      payload.reduce_only = true;
    }
    // ── 핵심: bodyStr 은 단 1회만 직렬화. HMAC 입력과 fetch body 가 동일 byte. ──
    const bodyStr = JSON.stringify(payload);

    // Sprint 14 Phase B-1 — WebCrypto error 처리. 구식 브라우저 / non-HTTPS local /
    // SubtleCrypto 미지원 환경에서 unhandled promise rejection 방지.
    let hmacHex: string;
    let idempotencyKey: string;
    try {
      hmacHex = await computeHmacSha256Hex(secret, bodyStr);
      idempotencyKey = crypto.randomUUID();
    } catch (err) {
      const message = err instanceof Error ? err.message : "WebCrypto 처리 실패";
      form.setError("root.serverError", {
        type: "manual",
        message:
          `암호화 처리 실패: ${message}. ` +
          "브라우저가 WebCrypto (SubtleCrypto) 를 지원하지 않거나 " +
          "HTTPS / localhost 가 아닌 환경입니다.",
      });
      return;
    }

    const url = `${API_BASE_URL}/api/v1/webhooks/${values.strategy_id}?token=${hmacHex}&Idempotency-Key=${idempotencyKey}`;

    let res: Response;
    try {
      res = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: bodyStr,
      });
    } catch (err) {
      const message = err instanceof Error ? err.message : "네트워크 오류";
      form.setError("root.serverError", {
        type: "manual",
        message: `네트워크 오류: ${message}`,
      });
      return;
    }

    if (res.status === 201) {
      // Sprint 21 BL-093 — success confirmation 강화: order id 마지막 8자 또는
      // client-side idempotency_key 마지막 8자 노출 → 사용자가 OrdersPanel /
      // Bybit Demo UI 와 매칭 가능 (dogfood Day 0 7번 N 해소).
      let orderHint: string | null = null;
      try {
        const body = (await res.json()) as Record<string, unknown> | null;
        const id = body?.id ?? body?.order_id ?? body?.exchange_order_id;
        if (typeof id === "string" && id.length > 0) {
          orderHint = `#${id.slice(-8)}`;
        }
      } catch {
        // body 가 JSON 이 아니거나 빈 응답 — fallback 으로 idempotency_key 사용
      }
      if (!orderHint && idempotencyKey) {
        orderHint = `client #${idempotencyKey.slice(-8)}`;
      }
      toast.success("테스트 주문 발송됨", {
        description: orderHint ?? undefined,
      });
      // tradingKeys.orders 는 (userId, limit) 인자가 필요한 factory 라
      // 모든 user/limit variation 을 한 번에 무효화하기 위해 prefix ["trading"] 사용.
      qc.invalidateQueries({ queryKey: ["trading"] });
      form.reset();
      setOpen(false);
      return;
    }

    // Sprint 14 Phase B-4 — error body size cap + JSON detail 정규화.
    // FastAPI HTTPException detail 우선, JSON 아니면 text 8KB cap.
    const detail = await readErrorBody(res);
    let bodyText: string;
    if (detail && typeof detail === "object") {
      const detailField = (detail as { detail?: unknown }).detail;
      if (typeof detailField === "string" && detailField.length > 0) {
        bodyText = detailField;
      } else {
        bodyText = JSON.stringify(detail);
      }
    } else if (typeof detail === "string" && detail.length > 0) {
      bodyText = detail;
    } else {
      bodyText = "응답 본문 없음";
    }
    form.setError("root.serverError", {
      type: "manual",
      message: `요청 실패 (${res.status}): ${bodyText}`,
    });
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
              브라우저에서 webhook secret 으로 HMAC 서명 후 발송합니다.
              실제 거래소로 주문이 전달되니 demo 계정에서만 사용하세요.
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
                    <Select
                      onValueChange={field.onChange}
                      value={field.value}
                    >
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
              <FormField
                control={form.control}
                name="exchange_account_id"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>거래소 계정</FormLabel>
                    <Select
                      onValueChange={field.onChange}
                      value={field.value}
                    >
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
                      <fieldset
                        className="flex gap-4"
                        aria-label="주문 방향"
                      >
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
                      <fieldset
                        className="flex flex-wrap gap-4"
                        aria-label="사이징 방식"
                      >
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
              {sizingMode === "quantity" ? (
                <FormField
                  control={form.control}
                  name="quantity"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>수량 (Decimal)</FormLabel>
                      <FormControl>
                        <Input
                          inputMode="decimal"
                          placeholder="0.001"
                          {...field}
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              ) : (
                <FormField
                  control={form.control}
                  name="risk_percent"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>리스크 % (자동 사이징)</FormLabel>
                      <FormControl>
                        <Input
                          inputMode="decimal"
                          placeholder="1.0"
                          {...field}
                        />
                      </FormControl>
                      <p className="text-xs text-muted-foreground">
                        수량은 서버가 잔고·리스크 기준으로 계산합니다 (서버 권위 사이징).
                      </p>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              )}
              {/* Wave 2 — bracket TP/SL (둘 다 optional). */}
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <FormField
                  control={form.control}
                  name="take_profit"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>익절가 TP (선택)</FormLabel>
                      <FormControl>
                        <Input
                          inputMode="decimal"
                          placeholder="예: 55000"
                          {...field}
                        />
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
                        <Input
                          inputMode="decimal"
                          placeholder="예: 48000"
                          {...field}
                        />
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
              {/* Wave 2 — 청산가 미리보기(참고용). 주문 body 와 무관한 로컬 입력. */}
              <div className="space-y-3 rounded-md border border-dashed p-3">
                <p className="text-sm font-medium">청산가 미리보기 (참고용)</p>
                <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                  <div className="space-y-1">
                    <label
                      htmlFor="liq-preview-entry"
                      className="text-sm font-medium"
                    >
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
                    <label
                      htmlFor="liq-preview-leverage"
                      className="text-sm font-medium"
                    >
                      레버리지 (배)
                    </label>
                    <Input
                      id="liq-preview-leverage"
                      inputMode="numeric"
                      placeholder="예: 10"
                      value={previewLeverage}
                      onChange={(e) => setPreviewLeverage(e.target.value)}
                    />
                  </div>
                </div>
                {liquidation ? (
                  <p
                    data-testid="liquidation-preview"
                    className="text-sm text-foreground"
                  >
                    예상 청산가{" "}
                    <span className="font-mono font-semibold">
                      {liquidation.liquidation_price}
                    </span>{" "}
                    <span className="text-muted-foreground">
                      (진입가 대비 {liquidation.distance_pct}%)
                    </span>
                  </p>
                ) : (
                  <p className="text-xs text-muted-foreground">
                    심볼·방향 선택 후 예상 진입가와 레버리지를 입력하면 청산가를
                    표시합니다.
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
                <Button
                  type="button"
                  variant="ghost"
                  onClick={() => setOpen(false)}
                >
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
