// 백테스트 폼의 주문 크기 source 필드 (Sprint 38 BL-188 v3) — Sprint 59 PR-E split.
"use client";

import { useWatch, type Control, type UseFormRegister, type UseFormSetValue, type FieldErrors } from "react-hook-form";

import { Input } from "@/components/ui/input";

import { LiveSettingsBadge, type SizingSource } from "./live-settings-badge";
import { PositionSizeSlider } from "./position-size-slider";
import type { BacktestFormValues } from "./useBacktestForm";

interface BacktestSizingFieldSetProps {
  control: Control<BacktestFormValues>;
  register: UseFormRegister<BacktestFormValues>;
  setValue: UseFormSetValue<BacktestFormValues>;
  errors: FieldErrors<BacktestFormValues>;
  liveLeverage: number | null;
  livePct: number | null;
}

export function BacktestSizingFieldSet({
  control,
  register,
  setValue,
  errors,
  liveLeverage,
  livePct,
}: BacktestSizingFieldSetProps) {
  const sizingSource = useWatch({ control, name: "sizing_source" });
  const watchedQtyType = useWatch({ control, name: "default_qty_type" });
  const watchedQtyValue = useWatch({ control, name: "default_qty_value" });
  const watchedCapital = useWatch({ control, name: "initial_capital" });

  return (
    <section
      className="border-t pt-4"
      aria-label="주문 크기 source"
      data-testid="backtest-form-sizing-source-section"
    >
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-sm font-medium">주문 크기 source</h3>
        <LiveSettingsBadge
          source={sizingSource}
          liveLeverage={liveLeverage}
          livePct={livePct}
        />
      </div>

      {sizingSource === "pine" ? (
        <p className="mb-3 text-xs text-muted-foreground">
          Pine code <code>strategy(default_qty_type=...)</code> 명시 — Pine
          override 가 우선 적용됩니다. 폼 입력 비활성화.
        </p>
      ) : sizingSource === "live_blocked_leverage" ? (
        <p className="mb-3 text-xs text-muted-foreground">
          Live leverage {liveLeverage ?? 0}x — backtest 1x equity-basis 와
          비대칭으로 mirror 차단. Manual 입력만 가능.
        </p>
      ) : (
        <div className="mb-3 flex flex-col gap-1.5">
          <label htmlFor="sizing_source" className="text-xs">
            source 선택
          </label>
          <select
            id="sizing_source"
            data-testid="sizing-source-select"
            className="h-10 rounded-md border bg-background px-3 text-sm"
            value={sizingSource}
            onChange={(e) => {
              const next = e.target.value as SizingSource;
              if (next === "live") {
                setValue("sizing_source", "live", { shouldDirty: true });
                setValue("position_size_pct", livePct ?? null, {
                  shouldDirty: true,
                });
              } else {
                setValue("sizing_source", "manual", { shouldDirty: true });
                setValue("position_size_pct", null, { shouldDirty: true });
              }
            }}
          >
            <option value="manual">Manual 입력 (form 우선)</option>
            {livePct != null && liveLeverage === 1 ? (
              <option value="live">Live mirror (Strategy.settings)</option>
            ) : null}
          </select>
        </div>
      )}

      {sizingSource === "live" ? (
        <div className="flex flex-col gap-1.5">
          <label htmlFor="position_size_pct" className="text-sm">
            Live position_size_pct (%, Live mirror)
          </label>
          <Input
            id="position_size_pct"
            type="number"
            step="any"
            min={0}
            max={100}
            readOnly
            data-testid="position-size-pct-input"
            {...register("position_size_pct", {
              valueAsNumber: true,
            })}
          />
          <p className="text-xs text-muted-foreground">
            Strategy.settings.position_size_pct 와 동일. 변경하려면 Manual 로
            전환 또는 Strategy 편집.
          </p>
          {errors.position_size_pct ? (
            <p className="text-xs text-destructive">
              {errors.position_size_pct.message}
            </p>
          ) : null}
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div className="flex flex-col gap-1.5">
            <label htmlFor="default_qty_type" className="text-sm">
              type
            </label>
            <select
              id="default_qty_type"
              className="h-10 rounded-md border bg-background px-3 text-sm disabled:opacity-50"
              disabled={sizingSource === "pine"}
              data-testid="default-qty-type-select"
              {...register("default_qty_type", {
                required:
                  sizingSource === "pine"
                    ? false
                    : "주문 크기 type 을 선택하세요",
              })}
            >
              <option value="strategy.percent_of_equity">
                자기자본 % (percent_of_equity)
              </option>
              <option value="strategy.cash">고정 USDT (cash)</option>
              <option value="strategy.fixed">고정 수량 (fixed)</option>
            </select>
            {errors.default_qty_type ? (
              <p className="text-xs text-destructive">
                {errors.default_qty_type.message}
              </p>
            ) : null}
          </div>
          <div className="flex flex-col gap-1.5">
            <label htmlFor="default_qty_value" className="text-sm">
              value
            </label>
            <Input
              id="default_qty_value"
              type="number"
              step="any"
              min={0}
              disabled={sizingSource === "pine"}
              data-testid="default-qty-value-input"
              {...register("default_qty_value", {
                required:
                  sizingSource === "pine"
                    ? false
                    : "주문 크기 값을 입력하세요",
                valueAsNumber: true,
                validate: (v) =>
                  sizingSource === "pine" ||
                  (Number.isFinite(v) && v > 0) ||
                  "양수여야 합니다",
              })}
            />
            {errors.default_qty_value ? (
              <p className="text-xs text-destructive">
                {errors.default_qty_value.message}
              </p>
            ) : null}
          </div>
        </div>
      )}

      {/* Sprint 42-polish W4 — percent_of_equity 일 때 슬라이더로 직접 조작. */}
      {sizingSource !== "pine" &&
      sizingSource !== "live" &&
      watchedQtyType === "strategy.percent_of_equity" ? (
        <div className="mt-4">
          <PositionSizeSlider
            value={
              Number.isFinite(watchedQtyValue) && watchedQtyValue > 0
                ? Math.min(100, Math.max(1, Number(watchedQtyValue)))
                : 10
            }
            onChange={(v) =>
              setValue("default_qty_value", v, { shouldDirty: true })
            }
            capitalUsd={
              Number.isFinite(watchedCapital) ? Number(watchedCapital) : null
            }
            label="포지션 사이즈"
            unit="%"
            min={1}
            max={100}
            step={1}
          />
        </div>
      ) : null}
    </section>
  );
}
