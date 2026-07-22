// 백테스트 폼의 주문 크기 방식 필드 (Sprint 38 BL-188 v3) — C 디자인 언어 이식(W3-A). 로직·testid 보존.
"use client";

import { useWatch, type Control, type UseFormRegister, type UseFormSetValue, type FieldErrors } from "react-hook-form";

import { LiveSettingsBadge, type SizingSource } from "@/app/(dashboard)/backtests/_components/live-settings-badge";
import { PositionSizeSlider } from "@/app/(dashboard)/backtests/_components/forms/position-size-slider";
import type { BacktestFormValues } from "@/app/(dashboard)/backtests/_components/forms/useBacktestForm";

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
      className="sizing-block"
      aria-label="주문 크기 방식"
      data-testid="backtest-form-sizing-source-section"
    >
      <div className="sizing-head">
        <div>
          <h3 className="card-title">주문 크기 방식</h3>
          <p className="card-sub">진입할 때마다 얼마를 쓸지 정합니다.</p>
        </div>
        <LiveSettingsBadge
          source={sizingSource}
          liveLeverage={liveLeverage}
          livePct={livePct}
        />
      </div>

      {sizingSource === "pine" ? (
        <p className="field-hint">
          Pine 코드가 <code>strategy(default_qty_type=...)</code> 를 명시했습니다.
          Pine 지정이 우선 적용되어 폼 입력은 비활성화됩니다.
        </p>
      ) : sizingSource === "live_blocked_leverage" ? (
        <p className="field-hint">
          Live 레버리지 {liveLeverage ?? 0}x 는 백테스트의 1배 자기자본 기준과
          비대칭이라 미러를 차단했습니다. 수동 입력만 가능합니다.
        </p>
      ) : (
        <div className="field sizing-narrow">
          <label className="field-label" htmlFor="sizing_source">
            입력 방식
          </label>
          <select
            className="select"
            id="sizing_source"
            data-testid="sizing-source-select"
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
            <option value="manual">수동 입력 (폼 우선)</option>
            {livePct != null && liveLeverage === 1 ? (
              <option value="live">Live 미러 (전략 설정값)</option>
            ) : null}
          </select>
        </div>
      )}

      {sizingSource === "live" ? (
        <div className="field sizing-gap sizing-narrow">
          <label className="field-label" htmlFor="position_size_pct">
            Live 포지션 비율 (%)
          </label>
          <input
            className="input mono"
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
          <p className="field-hint">
            전략 설정의 포지션 비율과 같습니다. 바꾸려면 수동 입력으로 전환하거나
            전략을 편집하세요.
          </p>
          {errors.position_size_pct ? (
            <p className="field-error" role="alert">
              {errors.position_size_pct.message}
            </p>
          ) : null}
        </div>
      ) : (
        <div className="field-grid sizing-gap">
          <div className="field">
            <label className="field-label" htmlFor="default_qty_type">
              주문 크기 기준
            </label>
            <select
              className="select"
              id="default_qty_type"
              disabled={sizingSource === "pine"}
              data-testid="default-qty-type-select"
              {...register("default_qty_type", {
                required:
                  sizingSource === "pine"
                    ? false
                    : "주문 크기 기준을 선택하세요",
              })}
            >
              <option value="strategy.percent_of_equity">자기자본 비율</option>
              <option value="strategy.cash">고정 금액 (USDT)</option>
              <option value="strategy.fixed">고정 수량</option>
            </select>
            {errors.default_qty_type ? (
              <p className="field-error" role="alert">
                {errors.default_qty_type.message}
              </p>
            ) : null}
          </div>
          <div className="field">
            <label className="field-label" htmlFor="default_qty_value">
              값
            </label>
            <input
              className="input mono"
              id="default_qty_value"
              type="number"
              step="any"
              min={0}
              disabled={sizingSource === "pine"}
              data-testid="default-qty-value-input"
              {...register("default_qty_value", {
                required:
                  sizingSource === "pine" ? false : "주문 크기 값을 입력하세요",
                valueAsNumber: true,
                validate: (v) =>
                  sizingSource === "pine" ||
                  (Number.isFinite(v) && v > 0) ||
                  "양수여야 합니다",
              })}
            />
            {errors.default_qty_value ? (
              <p className="field-error" role="alert">
                {errors.default_qty_value.message}
              </p>
            ) : null}
          </div>
        </div>
      )}

      {/* 자기자본 비율일 때 슬라이더로 직접 조작. */}
      {sizingSource !== "pine" &&
      sizingSource !== "live" &&
      watchedQtyType === "strategy.percent_of_equity" ? (
        <div className="sizing-gap sizing-narrow">
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
