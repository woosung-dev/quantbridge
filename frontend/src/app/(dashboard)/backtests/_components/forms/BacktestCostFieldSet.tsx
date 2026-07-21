// 백테스트 폼의 자본과 체결 필드 (초기 자본 + 테이커 수수료 + 슬리피지 + 체결 시점 + 펀딩 안내) — C 디자인 언어 이식(W3-A).
"use client";

import type { UseFormRegister, FieldErrors } from "react-hook-form";

import type { BacktestFormValues } from "@/app/(dashboard)/backtests/_components/forms/useBacktestForm";

interface BacktestCostFieldSetProps {
  register: UseFormRegister<BacktestFormValues>;
  errors: FieldErrors<BacktestFormValues>;
}

export function BacktestCostFieldSet({
  register,
  errors,
}: BacktestCostFieldSetProps) {
  const isCapitalInvalid = Boolean(errors.initial_capital);
  return (
    <section
      aria-label="자본과 체결"
      data-testid="backtest-form-cost-section"
    >
      <div className="field-grid">
        <div className="field">
          <span className="field-reqline">
            <label className="field-label" htmlFor="initial_capital">
              초기 자본
            </label>
            <span className="field-req" aria-hidden="true">필수</span>
          </span>
          <input
            className={isCapitalInvalid ? "input mono invalid" : "input mono"}
            id="initial_capital"
            type="number"
            step="0.01"
            aria-invalid={isCapitalInvalid || undefined}
            {...register("initial_capital", {
              required: "초기 자본을 입력하세요",
              valueAsNumber: true,
              validate: (v) =>
                (Number.isFinite(v) && v > 0) || "0보다 큰 값을 입력하세요",
            })}
          />
          {errors.initial_capital ? (
            <p className="field-error" role="alert">
              <svg
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeLinecap="round"
                strokeLinejoin="round"
                aria-hidden="true"
              >
                <circle cx="12" cy="12" r="9" />
                <line x1="12" y1="7.5" x2="12" y2="13" />
                <line x1="12" y1="16.5" x2="12.01" y2="16.5" />
              </svg>
              {errors.initial_capital.message}
            </p>
          ) : null}
          <p className="field-hint">
            단위는 USDT 입니다. 리포트의 모든 금액과 수익률이 이 값을 기준으로
            계산됩니다.
          </p>
        </div>

        <div className="field">
          <label className="field-label" htmlFor="fill_timing">
            체결 시점
          </label>
          <select
            className="select"
            id="fill_timing"
            {...register("fill_timing")}
          >
            <option value="next_bar_open">시그널 다음 봉 시가</option>
            <option value="bar_close">시그널 봉 종가</option>
          </select>
          <p className="field-hint">
            다음 봉 시가로 체결하면 시그널이 확정된 봉의 종가를 미리 아는 미래
            참조를 막을 수 있습니다.
          </p>
        </div>

        <div className="field">
          <label className="field-label" htmlFor="fees_pct">
            테이커 수수료
          </label>
          <input
            className="input mono"
            id="fees_pct"
            type="number"
            step="0.0001"
            min={0}
            max={0.01}
            {...register("fees_pct", {
              required: "수수료를 입력하세요",
              valueAsNumber: true,
              validate: (v) =>
                (Number.isFinite(v) && v >= 0 && v <= 0.01) ||
                "0 ~ 0.01 (1%) 범위여야 합니다",
            })}
          />
          {errors.fees_pct ? (
            <p className="field-error" role="alert">
              {errors.fees_pct.message}
            </p>
          ) : null}
          <p className="field-hint">
            소수 표기입니다. 0.001 은 0.10% 입니다. Bybit 테이커 기준이며 진입과
            청산 양쪽에 각각 적용합니다.
          </p>
        </div>

        <div className="field">
          <label className="field-label" htmlFor="slippage_pct">
            슬리피지
          </label>
          <input
            className="input mono"
            id="slippage_pct"
            type="number"
            step="0.0001"
            min={0}
            max={0.01}
            {...register("slippage_pct", {
              required: "슬리피지를 입력하세요",
              valueAsNumber: true,
              validate: (v) =>
                (Number.isFinite(v) && v >= 0 && v <= 0.01) ||
                "0 ~ 0.01 (1%) 범위여야 합니다",
            })}
          />
          {errors.slippage_pct ? (
            <p className="field-error" role="alert">
              {errors.slippage_pct.message}
            </p>
          ) : null}
          <p className="field-hint">
            소수 표기입니다. 0.0005 는 0.05% 입니다. 불리한 방향으로만 적용하고
            유리한 체결은 가정하지 않습니다.
          </p>
        </div>

        <div className="field span-2">
          <label className="check-row" htmlFor="funding">
            <input type="checkbox" id="funding" disabled />
            <span>
              <span className="check-title">펀딩 반영</span>
              <span className="check-why">
                지금 설정은 1배 현물 기준이라 펀딩이 발생하지 않습니다. 무기한
                선물 모델이 준비되면 켜집니다.
              </span>
            </span>
          </label>
        </div>
      </div>
    </section>
  );
}
