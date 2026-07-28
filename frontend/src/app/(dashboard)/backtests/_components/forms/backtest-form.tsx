// 백테스트 설정 폼 — C 디자인 언어 이식(W3-A, screen-05). 좌 폼(전략/시장/자본) + 우 sticky 요약.
// 폼 검증·제출·훅(useBacktestForm)과 fieldset 로직은 그대로 보존하고 프레젠테이션만 재스킨한다.
// 스키마가 받치지 않는 값(예상 소요 시간·결측 봉 점검)은 그리지 않는다(§4.9). 거래소는 Bybit 고정.
"use client";

import Link from "next/link";
import { toast } from "sonner";
import { AlertTriangleIcon, InboxIcon, RefreshCwIcon } from "lucide-react";

import { FormErrorInline } from "@/components/form-error-inline";
import { InfoIcon } from "@/components/info-icon";
import { StateBox } from "@/components/state-box";
import { EMPTY_CELL } from "@/lib/labels";
import { NEW_BACKTEST_LABEL } from "@/features/backtest/labels";
import { formatDateTime } from "@/features/backtest/utils";
import { useStrategies } from "@/features/strategy/hooks";
import { PARSE_STATUS_LABEL } from "@/features/strategy/labels";
import type { StrategyListItem } from "@/features/strategy/schemas";

import { BacktestCostFieldSet } from "@/app/(dashboard)/backtests/_components/forms/BacktestCostFieldSet";
import { BacktestLeverageFieldSet } from "@/app/(dashboard)/backtests/_components/forms/BacktestLeverageFieldSet";
import { BacktestSessionFieldSet } from "@/app/(dashboard)/backtests/_components/forms/BacktestSessionFieldSet";
import { BacktestSizingFieldSet } from "@/app/(dashboard)/backtests/_components/forms/BacktestSizingFieldSet";
import { BacktestTradingSessionsFieldSet } from "@/app/(dashboard)/backtests/_components/forms/BacktestTradingSessionsFieldSet";
import {
  SetupSummaryAside,
  TIMEFRAME_BARS_PER_DAY,
  barCount,
  diffDays,
} from "@/app/(dashboard)/backtests/_components/setup-summary-aside";
import { useBacktestForm } from "@/app/(dashboard)/backtests/_components/forms/useBacktestForm";

const FORM_ID = "backtest-setup-form";
// 목록 조회 엔드포인트 — 에러 상태에 실제 경로를 노출한다 (프로토타입 state-code 관례).
const STRATEGY_ENDPOINT = "GET /api/v1/strategies";

export function BacktestForm() {
  const strategiesQuery = useStrategies({ limit: 100, offset: 0, is_archived: false });
  const {
    form,
    handleSubmit,
    onSubmit,
    submitError,
    convertResult,
    setConvertResult,
    datePreset,
    setDatePreset,
    handleDatePreset,
    strategy,
    liveLeverage,
    livePct,
    create,
  } = useBacktestForm();

  const {
    register,
    setValue,
    control,
    formState: { errors, isSubmitting },
  } = form;

  const strategyItems: StrategyListItem[] = strategiesQuery.data?.items ?? [];
  // Aside 와 헤더 칩만 form-level watch (RHF stable getter). 각 fieldset 은 자체 useWatch 로 dep 분리(H-1).
  const watchedSymbol = form.watch("symbol");
  const watchedTimeframe = form.watch("timeframe");
  const watchedPeriodStart = form.watch("period_start");
  const watchedPeriodEnd = form.watch("period_end");
  const watchedCapital = form.watch("initial_capital");
  const watchedPositionPct = form.watch("position_size_pct");
  const watchedLeverage = form.watch("leverage");
  const watchedFees = form.watch("fees_pct");
  const watchedSlippage = form.watch("slippage_pct");
  const watchedFillTiming = form.watch("fill_timing");
  const watchedQtyType = form.watch("default_qty_type");
  const watchedQtyValue = form.watch("default_qty_value");
  const sizingSource = form.watch("sizing_source");
  const selectedStrategy = form.watch("strategy_id");
  const selectedItem = strategyItems.find((s) => s.id === selectedStrategy);
  const selectedStrategyName = selectedItem?.name;

  // 계산 요약(§02 calc-strip). 폼 값에서 순수 파생 가능한 값만 (검산: days × bars/day).
  const spanDays = diffDays(watchedPeriodStart, watchedPeriodEnd);
  const spanBars = barCount(spanDays, watchedTimeframe);
  const barsPerDay = TIMEFRAME_BARS_PER_DAY[watchedTimeframe];

  const errorCount = Object.keys(errors).length;
  const editHref = selectedStrategy
    ? `/strategies/${selectedStrategy}/edit?tab=parse`
    : null;

  return (
    <main className="page">
      {/* ===== 화면 헤더 ===== */}
      <section className="card" aria-label="새 백테스트 설정 개요">
        <div className="report">
          <div>
            <h1 className="report-title">{NEW_BACKTEST_LABEL.heading}</h1>
            <div className="report-meta">
              <span className="chip">{selectedStrategyName ?? "전략 미선택"}</span>
              <span className="chip">{watchedSymbol}</span>
              <span className="chip">{watchedTimeframe}</span>
              <span className="chip">Bybit</span>
              <span className="chip accent">바 단위 이벤트 루프</span>
            </div>
          </div>
          <div className="report-actions">
            <Link className="btn btn-ghost" href="/backtests">
              취소
            </Link>
            {editHref ? (
              <Link className="btn" href={editHref}>
                전략 코드 보기
              </Link>
            ) : null}
          </div>
        </div>
      </section>

      <div className="setup-grid" data-testid="backtest-form-layout">
        {/* ==================== 좌 · 폼 ==================== */}
        <form
          id={FORM_ID}
          className="setup-main"
          onSubmit={handleSubmit(onSubmit)}
          aria-label="backtest-form"
        >
          {/* ===== 01 전략 ===== */}
          <section className="section" aria-label="전략 선택">
            <header className="section-head">
              <p className="eyebrow">
                <span className="num">01</span> 전략
              </p>
              <h2 className="section-title">실행할 전략</h2>
              <p className="section-desc">
                백테스트는 Pine 파일을 파싱한 결과를 그대로 실행합니다. 파싱 상태가
                지원됨이 아니면 실행할 수 없습니다.
              </p>
            </header>

            <div className="card">
              <div className="card-head">
                <div>
                  <h3 className="card-title">전략 선택</h3>
                  <p className="card-sub">워크스페이스에 저장된 전략 중에서 고릅니다.</p>
                </div>
              </div>

              {/* strategy_id 는 어느 상태에서든 폼에 등록돼 있어야 제출 검증이 걸린다. */}
              <input
                type="hidden"
                {...register("strategy_id", { required: "전략을 선택하세요" })}
              />

              {strategiesQuery.isLoading ? (
                <div
                  className="card-body"
                  data-testid="strategy-select-skeleton"
                  aria-busy="true"
                >
                  <div className="sk" style={{ height: 38 }} aria-hidden="true" />
                  <p className="state-note">
                    <svg
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      aria-hidden="true"
                    >
                      <circle cx="12" cy="12" r="9" />
                      <polyline points="12 7 12 12 15.5 14" />
                    </svg>
                    저장된 전략을 불러오는 중입니다.
                  </p>
                </div>
              ) : strategiesQuery.isError ? (
                <div className="card-body">
                  <StateBox
                    tone="failed"
                    testId="strategy-select-error"
                    icon={<AlertTriangleIcon />}
                    title="전략 목록을 불러오지 못했습니다."
                    body="데이터 서비스가 응답하지 않습니다. 전략을 고를 수 없어 실행을 시작할 수 없습니다."
                    code={`${STRATEGY_ENDPOINT} · 503`}
                  >
                    <button
                      className="btn btn-ghost"
                      type="button"
                      onClick={() => strategiesQuery.refetch?.()}
                    >
                      <RefreshCwIcon aria-hidden="true" />
                      다시 시도
                    </button>
                  </StateBox>
                </div>
              ) : strategyItems.length === 0 ? (
                <div className="card-body">
                  <StateBox
                    testId="strategy-select-empty"
                    icon={<InboxIcon />}
                    title="저장된 전략이 없습니다."
                    body="먼저 Pine 전략을 하나 저장해야 백테스트를 실행할 수 있습니다."
                  >
                    <Link className="btn btn-primary btn-xs" href="/strategies/new">
                      새 전략 만들기
                    </Link>
                  </StateBox>
                </div>
              ) : (
                <>
                  <div className="card-body">
                    <div className="field">
                      <span className="field-reqline">
                        <label className="field-label" htmlFor="strategy-select">
                          전략
                        </label>
                        <span className="field-req" aria-hidden="true">필수</span>
                      </span>
                      <select
                        className="select"
                        id="strategy-select"
                        value={selectedStrategy || ""}
                        onChange={(e) =>
                          setValue("strategy_id", e.target.value, {
                            shouldValidate: true,
                          })
                        }
                      >
                        <option value="" disabled>
                          전략을 선택하세요
                        </option>
                        {strategyItems.map((s) => (
                          <option key={s.id} value={s.id}>
                            {s.name}
                          </option>
                        ))}
                      </select>
                      {errors.strategy_id ? (
                        <p className="field-error" role="alert">
                          {errors.strategy_id.message}
                        </p>
                      ) : null}
                      <p className="field-hint">
                        전략을 바꾸면 아래 심볼과 기본값이 그 전략의 저장값으로 다시
                        채워집니다.
                      </p>
                    </div>
                  </div>

                  {selectedItem ? (
                    <div className="mg2">
                      <div>
                        <p className="metric-group-title">선택한 전략</p>
                        <div className="metric">
                          <span className="metric-label">심볼</span>
                          <span className="metric-value">
                            {selectedItem.symbol ?? EMPTY_CELL}
                          </span>
                        </div>
                        <div className="metric">
                          <span className="metric-label">주기</span>
                          <span className="metric-value">
                            {selectedItem.timeframe ?? EMPTY_CELL}
                          </span>
                        </div>
                      </div>
                      <div>
                        <p className="metric-group-title">상태</p>
                        <div className="metric">
                          <span className="metric-label">마지막 수정</span>
                          <span className="metric-value">
                            {selectedItem.updated_at
                              ? formatDateTime(selectedItem.updated_at)
                              : EMPTY_CELL}
                          </span>
                        </div>
                        <div className="metric">
                          <span className="metric-label">파싱 상태</span>
                          <span className="metric-value">
                            {PARSE_STATUS_LABEL[selectedItem.parse_status].label}
                          </span>
                        </div>
                      </div>
                    </div>
                  ) : null}
                </>
              )}

              <p className="chart-note">
                <InfoIcon />
                미지원 Pine 함수가 하나라도 들어 있으면 부분 실행 없이 전체를
                지원되지 않음으로 처리합니다. 잘못된 결과를 만드는 것보다 낫다고
                봅니다.
              </p>
            </div>
          </section>

          {/* ===== 02 시장과 기간 ===== */}
          <section className="section" aria-label="시장과 기간">
            <header className="section-head">
              <p className="eyebrow">
                <span className="num">02</span> 시장과 기간
              </p>
              <h2 className="section-title">어떤 데이터로 돌릴까요?</h2>
              <p className="section-desc">
                기간과 주기를 고르면 실행할 봉 수가 결정됩니다. 봉 수는 소요 시간과
                결과의 표본 크기를 함께 결정합니다.
              </p>
            </header>

            <div className="card">
              <div className="card-head">
                <div>
                  <h3 className="card-title">시장과 기간</h3>
                  <p className="card-sub">Bybit 공개 OHLCV 를 그대로 사용합니다.</p>
                </div>
              </div>

              <div className="card-body">
                <BacktestSessionFieldSet
                  control={control}
                  register={register}
                  setValue={setValue}
                  errors={errors}
                  datePreset={datePreset}
                  setDatePreset={setDatePreset}
                  onDatePreset={handleDatePreset}
                />
              </div>

              <div className="calc-strip">
                <div className="calc-cell">
                  <p className="calc-label">기간</p>
                  <p
                    className={spanDays != null ? "calc-value" : "calc-value empty"}
                    title={
                      spanDays == null
                        ? "시작일과 종료일이 정해져야 기간을 계산합니다."
                        : undefined
                    }
                  >
                    {spanDays != null ? `${spanDays}일` : EMPTY_CELL}
                  </p>
                  {spanDays != null ? (
                    <p className="calc-foot">
                      {watchedPeriodStart} 부터 {watchedPeriodEnd} 까지
                    </p>
                  ) : null}
                </div>
                <div className="calc-cell">
                  <p className="calc-label">실행할 봉 수</p>
                  <p
                    className={spanBars != null ? "calc-value" : "calc-value empty"}
                    title={
                      spanBars == null
                        ? "기간과 타임프레임이 정해져야 봉 수를 계산합니다."
                        : undefined
                    }
                  >
                    {spanBars != null ? `${spanBars.toLocaleString()}개` : EMPTY_CELL}
                  </p>
                  {spanBars != null && barsPerDay != null ? (
                    <p className="calc-foot">
                      {spanDays}일 × {barsPerDay} ({watchedTimeframe} 봉)
                    </p>
                  ) : null}
                </div>
              </div>

              <p className="chart-note">
                <InfoIcon />
                현재 연결된 거래소는 Bybit 하나입니다. 다른 거래소의 체결 결과는 이
                실행으로 알 수 없습니다.
              </p>
            </div>
          </section>

          {/* ===== 03 자본과 체결 가정 ===== */}
          <section className="section" aria-label="자본과 체결 가정">
            <header className="section-head">
              <p className="eyebrow">
                <span className="num">03</span> 자본과 체결 가정
              </p>
              <h2 className="section-title">결과를 바꾸는 가정</h2>
              <p className="section-desc">
                수익률이 달라지는 이유는 대부분 여기 있습니다. 리포트에도 같은 값이
                그대로 인쇄됩니다.
              </p>
            </header>

            <div className="card">
              <div className="card-head">
                <div>
                  <h3 className="card-title">자본과 체결</h3>
                  <p className="card-sub">모든 금액 단위는 USDT 입니다.</p>
                </div>
              </div>

              <div className="card-body">
                <BacktestCostFieldSet
                  register={register}
                  errors={errors}
                  fillTiming={watchedFillTiming}
                  liveFillTiming={strategy?.settings?.fill_timing ?? null}
                />

                <BacktestLeverageFieldSet
                  control={control}
                  register={register}
                  errors={errors}
                />

                <BacktestSizingFieldSet
                  control={control}
                  register={register}
                  setValue={setValue}
                  errors={errors}
                  liveLeverage={liveLeverage}
                  livePct={livePct}
                />

                <BacktestTradingSessionsFieldSet
                  control={control}
                  setValue={setValue}
                />
              </div>
            </div>

            <FormErrorInline
              error={submitError}
              editStrategyHref={editHref}
              testIdPrefix="backtest-form"
              indicatorCode={strategy?.pine_source ?? null}
              onConverted={setConvertResult}
            />

            {/* pine-compat-experiment — AI 변환 결과 (검토 후 새 전략으로 저장). */}
            {convertResult ? (
              <div className="card" style={{ marginTop: 16 }}>
                <div className="card-body">
                  <p className="notice-inline">
                    <svg
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      aria-hidden="true"
                    >
                      <path d="M10.3 3.9 1.9 18a2 2 0 0 0 1.7 3h16.8a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z" />
                      <line x1="12" y1="9" x2="12" y2="13.5" />
                      <line x1="12" y1="17" x2="12.01" y2="17" />
                    </svg>
                    AI 변환 결과입니다. 검토한 뒤 새 전략으로 저장하세요.
                  </p>
                  {convertResult.warnings.length > 0 ? (
                    <ul className="unsupported">
                      {convertResult.warnings.map((w, i) => (
                        <li key={i}>{w}</li>
                      ))}
                    </ul>
                  ) : null}
                  <textarea
                    className="textarea"
                    readOnly
                    value={convertResult.converted_code}
                    rows={12}
                  />
                  <div className="state-actions">
                    <button
                      type="button"
                      className="btn btn-ghost btn-xs"
                      onClick={() => {
                        void navigator.clipboard.writeText(
                          convertResult.converted_code,
                        );
                        toast.success("클립보드에 복사됨");
                      }}
                    >
                      클립보드에 복사
                    </button>
                  </div>
                </div>
              </div>
            ) : null}
          </section>
        </form>

        {/* ==================== 우 · 요약 ==================== */}
        <aside className="setup-side">
          <section className="section" aria-label="실행 요약">
            <header className="section-head">
              <p className="eyebrow">
                <span className="num">04</span> 요약
              </p>
              <h2 className="section-title">실행 요약</h2>
              <p className="section-desc">지금 화면의 값 그대로입니다.</p>
            </header>

            <SetupSummaryAside
              formId={FORM_ID}
              strategyName={selectedStrategyName}
              submitting={isSubmitting || create.isPending}
              errorCount={errorCount}
              formValues={{
                symbol: watchedSymbol,
                timeframe: watchedTimeframe,
                period_start: watchedPeriodStart,
                period_end: watchedPeriodEnd,
                initial_capital: watchedCapital,
                position_size_pct: watchedPositionPct,
                default_qty_type: watchedQtyType,
                default_qty_value: watchedQtyValue,
                sizing_source: sizingSource,
                leverage: watchedLeverage,
                fees_pct: watchedFees,
                slippage_pct: watchedSlippage,
                fill_timing: watchedFillTiming,
              }}
            />
          </section>
        </aside>
      </div>
    </main>
  );
}
