"use client";

// Sprint 7c T5: 메타데이터 탭 — react-hook-form + Zod (UpdateStrategyRequestSchema).
// Sprint FE-TradingSession: trading_sessions toggle chip 추가.

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
import { Textarea } from "@/components/ui/textarea";
import { useUpdateStrategy } from "@/features/strategy/hooks";
import {
  type StrategyResponse,
  UpdateStrategyRequestSchema,
  type UpdateStrategyRequest,
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

  return (
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
  );
}
