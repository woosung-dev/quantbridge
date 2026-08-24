"use client";

// 라이브 세션 등록 폼 — C 디자인 언어 이식(W3-F, screen-01 §05 세션 관리).
// shadcn Form/Select + SelectWithDisplayName(BL-164 UUID 은닉)은 기능·접근성 때문에 유지하고,
// 스타일 층만 C 규약(.field-label / .input / .notice-inline / .btn)으로 옮겼다.
//
// dogfood UX 유지:
//  - Bybit 데모 한정 안내(가상 자금만, 실제 자금 손실 없음)
//  - 5건 quota 도달 → submit disabled + tooltip
//  - 422 inline error (StrategySettingsRequired / InvalidStrategySettings /
//    AccountModeNotAllowed / LiveSessionQuotaExceeded)
//
// LESSON-004 의무 준수: useEffect dep primitive only.

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodV4Resolver } from "@/lib/zod-v4-resolver";
import { describeApiError } from "@/lib/api-client";
import { toast } from "sonner";

import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { SelectWithDisplayName } from "@/components/ui/select-with-display-name";

import { useRegisterLiveSession } from "../hooks";
import { LiveSessionFormSchema, type LiveSessionForm, type LiveSession } from "../schemas";
import { MAX_LIVE_SESSIONS_PER_USER } from "../utils";

type Props = {
  strategies: ReadonlyArray<{ id: string; name: string }>;
  exchangeAccounts: ReadonlyArray<{
    id: string;
    exchange: string;
    mode: string;
    label?: string | null;
    read_only: boolean | null;
  }>;
  activeSessionsCount: number;
  onSuccess?: (session: LiveSession) => void;
};

// 39행의 `import { type LiveSessionForm }`(타입)과 아래 함수(값)는 TS 의 타입 공간 /
// 값 공간 분리라 충돌이 아니다 — `tsc --noEmit` 이 이미 통과시킨다 (ADR-039).
// biome-ignore lint/suspicious/noRedeclare: Biome 은 그 분리를 못 본다
export function LiveSessionForm({
  strategies,
  exchangeAccounts,
  activeSessionsCount,
  onSuccess,
}: Props) {
  const register = useRegisterLiveSession();
  const [serverError, setServerError] = useState<string | null>(null);

  const isQuotaReached = activeSessionsCount >= MAX_LIVE_SESSIONS_PER_USER;

  // Bybit 데모만 허용 — UI 에서 사전 필터링 + form-level error 도 백업
  const allowedAccounts = exchangeAccounts.filter(
    (a) => a.exchange === "bybit" && a.mode === "demo",
  );
  const selectableAccounts = allowedAccounts.filter((a) => a.read_only !== true);

  const form = useForm<LiveSessionForm>({
    resolver: zodV4Resolver(LiveSessionFormSchema),
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
      toast.success("라이브 세션 시작됨");
      form.reset();
      onSuccess?.(session);
    } catch (err) {
      setServerError(
        describeApiError(err, "세션을 시작하지 못했습니다. 잠시 후 다시 시도해주세요."),
      );
    }
  };

  return (
    <div className="space-y-4">
      {/* Bybit 데모 한정 안내 */}
      <p className="notice-inline" data-testid="live-session-bybit-demo-notice">
        <strong>Bybit 데모 한정</strong>. Bybit 데모 계정만 사용할 수 있습니다. 가상 자금만
        사용하므로 실제 자금 손실은 없습니다.
      </p>

      <Form {...form}>
        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
          <FormField
            control={form.control}
            name="strategy_id"
            render={({ field }) => (
              <FormItem>
                <FormLabel className="field-label">전략</FormLabel>
                <FormControl>
                  {/* BL-164 — SelectWithDisplayName 헬퍼로 통일.
                      render prop 캡슐화로 raw value(UUID) 노출 자동 차단. */}
                  <SelectWithDisplayName
                    options={strategies.map((s) => ({
                      value: s.id,
                      label: s.name,
                    }))}
                    value={field.value}
                    onValueChange={field.onChange}
                    placeholder="전략 선택 (설정 필요)"
                    triggerTestId="live-session-strategy-trigger"
                    ariaLabel="전략 선택"
                  />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
          <FormField
            control={form.control}
            name="exchange_account_id"
            render={({ field }) => (
              <FormItem>
                <FormLabel className="field-label">거래소 계정 (Bybit 데모)</FormLabel>
                <FormControl>
                  {/* BL-164 — SelectWithDisplayName 헬퍼 통일. */}
                  <SelectWithDisplayName
                    options={allowedAccounts.map((a) => ({
                      value: a.id,
                      label: `${a.label ?? `${a.exchange} ${a.mode}`}${
                        a.read_only === true ? " (읽기 전용)" : ""
                      }`,
                      disabled: a.read_only === true,
                    }))}
                    value={field.value}
                    onValueChange={field.onChange}
                    placeholder="Bybit 데모 계정 선택"
                    emptyMessage="Bybit 데모 계정 없음. 먼저 등록해주세요"
                    triggerTestId="live-session-account-trigger"
                    ariaLabel="거래소 계정 선택"
                  />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
          <FormField
            control={form.control}
            name="symbol"
            render={({ field }) => (
              <FormItem>
                <FormLabel className="field-label">심볼</FormLabel>
                <FormControl>
                  <input className="input" placeholder="BTC/USDT" {...field} />
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
                <FormLabel className="field-label">평가 주기</FormLabel>
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
            <p className="notice-inline" role="alert" data-testid="live-session-form-error">
              {serverError}
            </p>
          ) : null}

          <div className="flex items-center justify-between gap-2">
            <p className="field-hint">
              활성 세션 {activeSessionsCount} / {MAX_LIVE_SESSIONS_PER_USER}
            </p>
            <button
              type="submit"
              className="btn btn-primary"
              disabled={register.isPending || isQuotaReached || selectableAccounts.length === 0}
              title={
                isQuotaReached ? `최대 ${MAX_LIVE_SESSIONS_PER_USER}건까지 활성 가능` : undefined
              }
              data-testid="live-session-submit"
            >
              {register.isPending ? "시작 중..." : "라이브 세션 시작"}
            </button>
          </div>
        </form>
      </Form>
    </div>
  );
}
