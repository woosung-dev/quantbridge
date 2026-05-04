"use client";

// Sprint 7c T5: 메타데이터 탭 — react-hook-form + Zod (UpdateStrategyRequestSchema).
// Sprint FE-TradingSession: trading_sessions toggle chip 추가.
// Sprint 27 BL-137: trading settings (leverage / margin_mode / position_size_pct) UI 추가.
//   별도 form (PUT /strategies/{id}/settings) 으로 분리 — 메타데이터(name 등) 와 트랜잭션 분리.

import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
  Form,
  FormControl,
  FormDescription,
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
import { Textarea } from "@/components/ui/textarea";
import {
  useUpdateStrategy,
  useUpdateStrategySettings,
} from "@/features/strategy/hooks";
import {
  type StrategyResponse,
  UpdateStrategyRequestSchema,
  type UpdateStrategyRequest,
  UpdateStrategySettingsRequestSchema,
  type UpdateStrategySettingsRequest,
} from "@/features/strategy/schemas";
import { SessionChips } from "./session-chips";

export function TabMetadata({ strategy }: { strategy: StrategyResponse }) {
  const form = useForm<UpdateStrategyRequest>({
    resolver: zodResolver(UpdateStrategyRequestSchema),
    defaultValues: {
      name: strategy.name,
      description: strategy.description ?? "",
      symbol: strategy.symbol ?? "",
      timeframe: strategy.timeframe ?? "",
      tags: strategy.tags,
      trading_sessions: strategy.trading_sessions ?? [],
    },
  });
  const update = useUpdateStrategy(strategy.id, {
    onSuccess: () => toast.success("메타데이터가 저장되었습니다"),
    onError: (e) => toast.error(`저장 실패: ${e.message}`),
  });

  // Sprint 27 BL-137 — trading settings 별도 form. settings null = unset (Live Session 차단).
  const settingsForm = useForm<UpdateStrategySettingsRequest>({
    resolver: zodResolver(UpdateStrategySettingsRequestSchema),
    defaultValues: {
      schema_version: strategy.settings?.schema_version ?? 1,
      leverage: strategy.settings?.leverage ?? 2,
      margin_mode: strategy.settings?.margin_mode ?? "cross",
      position_size_pct: strategy.settings?.position_size_pct ?? 10,
    },
  });
  const updateSettings = useUpdateStrategySettings(strategy.id, {
    onSuccess: () => toast.success("Trading settings 가 저장되었습니다"),
    onError: (e) => toast.error(`저장 실패: ${e.message}`),
  });

  return (
    <div className="space-y-8">
    <Form {...form}>
      <form
        onSubmit={form.handleSubmit((v) => update.mutate(v))}
        className="max-w-2xl space-y-5"
      >
        <FormField
          control={form.control}
          name="name"
          render={({ field }) => (
            <FormItem>
              <FormLabel>이름</FormLabel>
              <FormControl>
                <Input {...field} value={field.value ?? ""} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        <FormField
          control={form.control}
          name="description"
          render={({ field }) => (
            <FormItem>
              <FormLabel>설명</FormLabel>
              <FormControl>
                <Textarea rows={3} {...field} value={field.value ?? ""} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <FormField
            control={form.control}
            name="symbol"
            render={({ field }) => (
              <FormItem>
                <FormLabel>심볼</FormLabel>
                <FormControl>
                  <Input {...field} value={field.value ?? ""} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
          <FormField
            control={form.control}
            name="timeframe"
            render={({ field }) => (
              <FormItem>
                <FormLabel>타임프레임</FormLabel>
                <FormControl>
                  <Input {...field} value={field.value ?? ""} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
        </div>
        <FormItem>
          <FormLabel>태그 (쉼표로 구분)</FormLabel>
          <FormControl>
            <Input
              defaultValue={strategy.tags.join(", ")}
              onChange={(e) => {
                const tags = e.target.value
                  .split(",")
                  .map((t) => t.trim())
                  .filter(Boolean);
                form.setValue("tags", tags, { shouldDirty: true });
              }}
            />
          </FormControl>
        </FormItem>
        <FormField
          control={form.control}
          name="trading_sessions"
          render={({ field }) => (
            <FormItem>
              <FormLabel>거래 세션</FormLabel>
              <FormControl>
                <SessionChips
                  value={field.value ?? []}
                  onChange={field.onChange}
                />
              </FormControl>
              <FormDescription>
                {(field.value ?? []).length === 0
                  ? "24시간 제한 없음 — 선택 없으면 언제든 주문 실행"
                  : "선택한 세션 시간에만 주문 실행 (BE UTC 필터링)"}
              </FormDescription>
              <FormMessage />
            </FormItem>
          )}
        />
        <div className="pt-2">
          <Button
            type="submit"
            disabled={!form.formState.isDirty || update.isPending}
          >
            {update.isPending ? "저장 중..." : "변경사항 저장"}
          </Button>
        </div>
      </form>
    </Form>

    {/* Sprint 27 BL-137 — Trading Settings (Live Signal Auto-Trading 의무) */}
    <section className="max-w-2xl rounded-md border bg-card p-5">
      <header className="mb-4 space-y-1">
        <h3 className="text-sm font-semibold">Trading Settings</h3>
        <p className="text-xs text-muted-foreground">
          Live Session 시작에 필요한 trading params.
          {strategy.settings == null ? (
            <span className="ml-1 font-medium text-amber-600 dark:text-amber-400">
              · 미설정 (Live Session 차단됨)
            </span>
          ) : null}
        </p>
      </header>
      <Form {...settingsForm}>
        <form
          onSubmit={settingsForm.handleSubmit((v) => updateSettings.mutate(v))}
          className="space-y-5"
        >
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <FormField
              control={settingsForm.control}
              name="leverage"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Leverage (1-125)</FormLabel>
                  <FormControl>
                    <Input
                      type="number"
                      min={1}
                      max={125}
                      step={1}
                      {...field}
                      onChange={(e) =>
                        field.onChange(
                          e.target.value === ""
                            ? undefined
                            : Number(e.target.value),
                        )
                      }
                    />
                  </FormControl>
                  <FormDescription>거래소 마진 배수 (Bybit ≤ 125x)</FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={settingsForm.control}
              name="margin_mode"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Margin Mode</FormLabel>
                  <FormControl>
                    <Select
                      value={field.value}
                      onValueChange={field.onChange}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Margin mode 선택" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="cross">Cross</SelectItem>
                        <SelectItem value="isolated">Isolated</SelectItem>
                      </SelectContent>
                    </Select>
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
          </div>
          <FormField
            control={settingsForm.control}
            name="position_size_pct"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Position Size % (0 &lt; v ≤ 100)</FormLabel>
                <FormControl>
                  {/* step="any" — HTML5 native validation 회피 (min=0.01 + step=0.1
                      조합 시 10 등 정상값이 invalid 처리되어 submit 차단). */}
                  <Input
                    type="number"
                    min={0.01}
                    max={100}
                    step="any"
                    {...field}
                    onChange={(e) =>
                      field.onChange(
                        e.target.value === ""
                          ? undefined
                          : Number(e.target.value),
                      )
                    }
                  />
                </FormControl>
                <FormDescription>
                  가용 잔고 대비 포지션 크기 (100 = all-in)
                </FormDescription>
                <FormMessage />
              </FormItem>
            )}
          />
          <div className="pt-2">
            <Button
              type="submit"
              disabled={
                !settingsForm.formState.isDirty || updateSettings.isPending
              }
            >
              {updateSettings.isPending
                ? "저장 중..."
                : strategy.settings == null
                  ? "Settings 등록"
                  : "Settings 저장"}
            </Button>
          </div>
        </form>
      </Form>
    </section>
    </div>
  );
}
