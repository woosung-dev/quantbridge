// 백테스트 레버리지와 격리마진 가정을 입력·고지하는 필드셋.
"use client";

import { useWatch, type Control, type FieldErrors, type UseFormRegister } from "react-hook-form";

import type { BacktestFormValues } from "@/app/(dashboard)/backtests/_components/forms/useBacktestForm";

interface BacktestLeverageFieldSetProps {
  control: Control<BacktestFormValues>;
  register: UseFormRegister<BacktestFormValues>;
  errors: FieldErrors<BacktestFormValues>;
}

export function BacktestLeverageFieldSet({
  control,
  register,
  errors,
}: BacktestLeverageFieldSetProps) {
  const leverage = useWatch({ control, name: "leverage" });
  const hasMarginModel = Number.isFinite(leverage) && leverage > 1;

  return (
    <section
      className="sizing-block"
      aria-label="백테스트 레버리지"
      data-testid="backtest-form-leverage-section"
    >
      <div className="sizing-head">
        <div>
          <h3 className="sizing-title">백테스트 레버리지</h3>
          <p className="sizing-sub">백테스트의 필요 증거금과 청산가 가정입니다.</p>
        </div>
      </div>

      <div className="field sizing-narrow">
        <label className="field-label" htmlFor="leverage">
          레버리지 (배)
        </label>
        <input
          className={errors.leverage ? "input mono invalid" : "input mono"}
          id="leverage"
          type="number"
          min={1}
          max={125}
          step="0.01"
          aria-invalid={errors.leverage ? true : undefined}
          {...register("leverage", {
            required: "레버리지를 입력하세요",
            valueAsNumber: true,
            validate: (value) =>
              (Number.isFinite(value) && value >= 1 && value <= 125) || "1 ~ 125 범위여야 합니다",
          })}
        />
        {errors.leverage ? (
          <p className="field-error" role="alert">
            {errors.leverage.message}
          </p>
        ) : null}
        <p className="field-hint">1.00배부터 125.00배까지 소수 배수를 입력할 수 있습니다.</p>
      </div>

      {hasMarginModel ? (
        <section
          className="model-note"
          aria-label="레버리지 모델 고지"
          data-testid="backtest-leverage-notice"
        >
          <span className="model-title">격리마진 모델 고지</span>
          <p>필요 증거금 = 포지션가치의 {(100 / leverage).toFixed(1)}%</p>
          <p>청산가는 진입가에서 약 {((1 / leverage - 0.005) * 100).toFixed(2)}% 역행 지점</p>
          <p>
            플랫 유지증거금률 0.5% · 단일 tier · 격리마진 · Bybit 기준. 실제 거래소는 tier 별
            유지증거금률과 파산수수료가 달라 청산가가 다를 수 있습니다.
          </p>
          <p>
            레버리지는 주문 수량을 바꾸지 않습니다(TradingView·MT5 와 동일). 필요 증거금과 청산가만
            정합니다. 노출을 키우려면 주문 크기를 올리세요.
          </p>
          <p>
            TradingView 는 마진콜 시 포지션 일부만 청산하지만, 이 백테스트는 Bybit 격리마진처럼 <strong>전량 청산</strong>합니다.
          </p>
          <p>
            증거금 충분 여부는 수수료·슬리피지를 차감하기 전 자본으로 판정합니다. 거래가 쌓일수록
            실제 순자산보다 낙관적으로 평가됩니다.
          </p>
          <p>이 값은 백테스트 가정입니다. 전략의 Live Settings 레버리지와 별개입니다.</p>
        </section>
      ) : null}
    </section>
  );
}
