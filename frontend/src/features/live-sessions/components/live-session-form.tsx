"use client";

// Sprint 26 — Live Session 등록 form.
//
// dogfood UX:
//  - amber notice "Bybit Demo 한정 — 가상 자금만 사용. 실제 자금 손실 없음."
//  - 5건 quota 도달 → submit disabled + tooltip
//  - 422 inline error (StrategySettingsRequired / InvalidStrategySettings /
//    AccountModeNotAllowed / LiveSessionQuotaExceeded)
//
// LESSON-004 의무 준수: useEffect dep primitive only.

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
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

import { useRegisterLiveSession } from "../hooks";
import {
  LiveSessionFormSchema,
  type LiveSessionForm,
  type LiveSession,
} from "../schemas";
import { MAX_LIVE_SESSIONS_PER_USER } from "../utils";

type Props = {
  strategies: ReadonlyArray<{ id: string; name: string }>;
  exchangeAccounts: ReadonlyArray<{
    id: string;
    exchange: string;
    mode: string;
    label?: string | null;
  }>;
  activeSessionsCount: number;
  onSuccess?: (session: LiveSession) => void;
};

export function LiveSessionForm({
  strategies,
  exchangeAccounts,
  activeSessionsCount,
  onSuccess,
}: Props) {
  const register = useRegisterLiveSession();
  const [serverError, setServerError] = useState<string | null>(null);

  const isQuotaReached = activeSessionsCount >= MAX_LIVE_SESSIONS_PER_USER;

  // Bybit Demo 만 허용 — UI 에서 사전 필터링 + form-level error 도 백업
  const allowedAccounts = exchangeAccounts.filter(
    (a) => a.exchange === "bybit" && a.mode === "demo",
  );

  const form = useForm<LiveSessionForm>({
    resolver: zodResolver(LiveSessionFormSchema),
    defaultValues: {
      strategy_id: "",
      exchange_account_id: "",
      symbol: "BTC/USDT",
      interval: "1m",
    },
  });

  const onSubmit = async (values: LiveSessionForm) => {
    setServerError(null);
    try {
      const session = await register.mutateAsync(values);
      toast.success("Live Session 시작됨");
      form.reset();
      onSuccess?.(session);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "등록 실패";
      setServerError(msg);
    }
  };

  return (
    <div className="space-y-4">
      {/* Bybit Demo 한정 안내 — Sprint 26 BL-003 mainnet runbook 완료 전까지 */}
      <div
        className="rounded-md border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900 dark:border-amber-700 dark:bg-amber-950 dark:text-amber-200"
        data-testid="live-session-bybit-demo-notice"
      >
        <strong>Bybit Demo 한정</strong> — 가상 자금만 사용. 실제 자금 손실
        없음. (Live mainnet 은 BL-003 runbook 완료 후 단계적 활성화 예정)
      </div>

      <Form {...form}>
        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
          <FormField
            control={form.control}
            name="strategy_id"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Strategy</FormLabel>
                <Select onValueChange={field.onChange} value={field.value}>
                  <FormControl>
                    <SelectTrigger>
                      {/* BL-122 — base-ui Select.Value 가 raw value(UUID) 를 표시.
                          render prop 으로 strategy name 매핑. */}
                      <SelectValue placeholder="전략 선택 (settings 필요)">
                        {(value: string) =>
                          strategies.find((s) => s.id === value)?.name ??
                          "전략 선택 (settings 필요)"
                        }
                      </SelectValue>
                    </SelectTrigger>
                  </FormControl>
                  <SelectContent>
                    {strategies.map((s) => (
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
                <FormLabel>거래소 계정 (Bybit Demo)</FormLabel>
                <Select onValueChange={field.onChange} value={field.value}>
                  <FormControl>
                    <SelectTrigger>
                      <SelectValue placeholder="Bybit Demo 계정 선택">
                        {(value: string) => {
                          const acc = allowedAccounts.find((a) => a.id === value);
                          return acc
                            ? (acc.label ?? `${acc.exchange} ${acc.mode}`)
                            : "Bybit Demo 계정 선택";
                        }}
                      </SelectValue>
                    </SelectTrigger>
                  </FormControl>
                  <SelectContent>
                    {allowedAccounts.length === 0 ? (
                      <SelectItem value="" disabled>
                        Bybit Demo 계정 없음 — 먼저 등록해주세요
                      </SelectItem>
                    ) : (
                      allowedAccounts.map((a) => (
                        <SelectItem key={a.id} value={a.id}>
                          {a.label ?? `${a.exchange} ${a.mode}`}
                        </SelectItem>
                      ))
                    )}
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
                  <Input placeholder="BTC/USDT" {...field} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
          <FormField
            control={form.control}
            name="interval"
            render={({ field }) => (
              <FormItem>
                <FormLabel>평가 주기</FormLabel>
                <Select onValueChange={field.onChange} value={field.value}>
                  <FormControl>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                  </FormControl>
                  <SelectContent>
                    <SelectItem value="1m">1분</SelectItem>
                    <SelectItem value="5m">5분</SelectItem>
                    <SelectItem value="15m">15분</SelectItem>
                    <SelectItem value="1h">1시간</SelectItem>
                  </SelectContent>
                </Select>
                <FormMessage />
              </FormItem>
            )}
          />

          {serverError ? (
            <div
              className="rounded-md border border-destructive bg-destructive/10 p-3 text-sm text-destructive"
              role="alert"
              data-testid="live-session-form-error"
            >
              {serverError}
            </div>
          ) : null}

          <div className="flex items-center justify-between gap-2">
            <p className="text-xs text-muted-foreground">
              활성 session: {activeSessionsCount} / {MAX_LIVE_SESSIONS_PER_USER}
            </p>
            <Button
              type="submit"
              disabled={
                register.isPending ||
                isQuotaReached ||
                allowedAccounts.length === 0
              }
              title={
                isQuotaReached
                  ? `최대 ${MAX_LIVE_SESSIONS_PER_USER}건까지 활성 가능`
                  : undefined
              }
              data-testid="live-session-submit"
            >
              {register.isPending ? "시작 중..." : "Live Session 시작"}
            </Button>
          </div>
        </form>
      </Form>
    </div>
  );
}
