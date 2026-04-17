"use client";

// Sprint 7c T4 Step 3 — 메타데이터 입력 + 확인 제출.
// react-hook-form + Zod v4 (CreateStrategyRequestSchema.omit pine_source) + comma-split tag input.

import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { Badge } from "@/components/ui/badge";
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
import { Textarea } from "@/components/ui/textarea";
import {
  CreateStrategyRequestSchema,
  type CreateStrategyRequest,
  type ParsePreviewResponse,
} from "@/features/strategy/schemas";
import { PARSE_STATUS_META } from "@/features/strategy/utils";

type MetadataForm = Omit<CreateStrategyRequest, "pine_source">;

export function StepMetadata(props: {
  lastParse: ParsePreviewResponse | null;
  submitting: boolean;
  onBack: () => void;
  onSubmit: (meta: MetadataForm) => void;
}) {
  const form = useForm<MetadataForm>({
    resolver: zodResolver(CreateStrategyRequestSchema.omit({ pine_source: true })),
    defaultValues: {
      name: "",
      description: "",
      symbol: "",
      timeframe: "",
      tags: [],
    },
  });

  return (
    <Form {...form}>
      <form
        onSubmit={form.handleSubmit(props.onSubmit)}
        className="space-y-6"
      >
        <h2 className="font-display text-lg font-semibold">메타데이터 입력</h2>

        {/* 파싱 요약 (읽기전용) */}
        {props.lastParse && (
          <div className="rounded-[var(--radius-md)] border border-[color:var(--border)] bg-[color:var(--bg-alt)] p-4 text-sm">
            <div className="flex flex-wrap items-center gap-2">
              <Badge
                variant="outline"
                data-tone={PARSE_STATUS_META[props.lastParse.status].tone}
              >
                {PARSE_STATUS_META[props.lastParse.status].label}
              </Badge>
              <Badge variant="secondary">Pine {props.lastParse.pine_version}</Badge>
              <span className="text-xs text-[color:var(--text-secondary)]">
                진입 {props.lastParse.entry_count} · 청산 {props.lastParse.exit_count}
              </span>
            </div>
          </div>
        )}

        <FormField
          control={form.control}
          name="name"
          render={({ field }) => (
            <FormItem>
              <FormLabel>이름 *</FormLabel>
              <FormControl>
                <Input placeholder="예: MA Crossover Strategy" maxLength={120} {...field} />
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
                <Textarea
                  rows={3}
                  placeholder="전략의 핵심 아이디어를 간단히..."
                  maxLength={2000}
                  {...field}
                  value={field.value ?? ""}
                />
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
                  <Input placeholder="BTC/USDT" maxLength={32} {...field} value={field.value ?? ""} />
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
                  <Input placeholder="1h, 4h, 1D" maxLength={16} {...field} value={field.value ?? ""} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
        </div>

        {/* 태그: 간단히 comma-separated 문자열을 배열로 변환 */}
        <FormItem>
          <FormLabel>태그 (쉼표로 구분)</FormLabel>
          <FormControl>
            <Input
              placeholder="trend, ema, crossover"
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

        <div className="flex items-center justify-between pt-4">
          <Button type="button" variant="ghost" onClick={props.onBack}>
            ← 이전
          </Button>
          <Button type="submit" disabled={props.submitting}>
            {props.submitting ? "생성 중..." : "전략 생성"}
          </Button>
        </div>
      </form>
    </Form>
  );
}
