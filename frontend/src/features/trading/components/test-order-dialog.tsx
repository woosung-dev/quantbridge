"use client";

// Sprint 13 Phase B: dogfood-only Test Order Dialog.
//
// 보안 trade-off (dogfood-only):
// - production env 에서는 NEXT_PUBLIC_ENABLE_TEST_ORDER=false (또는 미설정).
// - sessionStorage 캐시된 webhook secret 으로 browser-side HMAC 서명 → 외부 노출 금지.
// - apiFetch helper 우회 — body 직렬화 drift 방지 위해 raw fetch + 단일 bodyStr 사용.
// - 422/400 등 error 시 setError("root.serverError") 로 form 안에 inline 표시.

import { useState } from "react";
import { useForm, type FieldValues, type Resolver } from "react-hook-form";
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
import { useExchangeAccounts, useIsOrderDisabledByKs } from "../hooks";

const TEST_ORDER_FORM_SCHEMA = z.object({
  strategy_id: z.string().min(1, "전략을 선택하세요."),
  exchange_account_id: z.string().min(1, "거래소 계정을 선택하세요."),
  symbol: z.string().min(1, "심볼을 입력하세요."),
  side: z.enum(["buy", "sell"]),
  quantity: z
    .string()
    .min(1, "수량을 입력하세요.")
    .refine(
      (v) => {
        if (!/^\d*\.?\d+$/.test(v)) return false;
        return Number(v) > 0;
      },
      { message: "수량은 0보다 큰 숫자여야 합니다." },
    ),
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
      quantity: "",
    },
  });

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

    const payload = {
      symbol: values.symbol,
      side: values.side,
      type: "market",
      quantity: values.quantity,
      exchange_account_id: values.exchange_account_id,
    };
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
      toast.success("테스트 주문 발송됨");
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
          <DialogHeader>
            <DialogTitle>테스트 주문 (dogfood-only)</DialogTitle>
            <DialogDescription>
              브라우저에서 webhook secret 으로 HMAC 서명 후 발송합니다.
              실제 거래소로 주문이 전달되니 demo 계정에서만 사용하세요.
            </DialogDescription>
          </DialogHeader>
          <Form {...form}>
            <form
              onSubmit={form.handleSubmit(onSubmit)}
              className="space-y-4"
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
              {rootError ? (
                <p
                  role="alert"
                  className="text-sm text-[color:var(--destructive)]"
                >
                  {rootError}
                </p>
              ) : null}
              <div className="flex justify-end gap-2 pt-2">
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => setOpen(false)}
                >
                  취소
                </Button>
                <Button
                  type="submit"
                  disabled={form.formState.isSubmitting || ksDisabled}
                  aria-disabled={ksDisabled || undefined}
                >
                  {ksDisabled
                    ? "Kill Switch 활성화"
                    : form.formState.isSubmitting
                      ? "발송 중..."
                      : "발송"}
                </Button>
              </div>
            </form>
          </Form>
        </DialogContent>
      </Dialog>
    </>
  );
}
