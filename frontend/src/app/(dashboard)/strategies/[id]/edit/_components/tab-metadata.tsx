"use client";

// 메타데이터 편집 — C 디자인 언어 이식 (screen-08 보존 기능). 프로토타입 screen-08 은 메타데이터
// 편집을 그리지 않지만, 이름/심볼/주기/태그/세션과 trading settings 는 실기능이라 C 카드로 보존한다.
// react-hook-form + Zod(UpdateStrategyRequestSchema / UpdateStrategySettingsRequestSchema) 유지.

import { zodV4Resolver } from "@/lib/zod-v4-resolver";
import { useForm, useWatch } from "react-hook-form";
import { toast } from "sonner";

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
    resolver: zodV4Resolver(UpdateStrategyRequestSchema),
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
    onSuccess: () => toast.success("메타데이터를 저장했습니다"),
    onError: (e) => toast.error(`저장 실패: ${e.message}`),
  });

  // Sprint 27 BL-137 — trading settings 별도 form. settings null = unset (Live Session 차단).
  const settingsForm = useForm<UpdateStrategySettingsRequest>({
    resolver: zodV4Resolver(UpdateStrategySettingsRequestSchema),
    defaultValues: {
      schema_version: strategy.settings?.schema_version ?? 1,
      leverage: strategy.settings?.leverage ?? 2,
      margin_mode: strategy.settings?.margin_mode ?? "cross",
      position_size_pct: strategy.settings?.position_size_pct ?? 10,
      max_trigger_breach_pct: strategy.settings?.max_trigger_breach_pct ?? null,
      // BL-516 — UI 입력은 없다(캡은 기본 비활성). 다만 여기서 값을 보존하지 않으면
      // 저장 시 기존 값이 null 로 덮인다.
      max_reversal_overshoot_ratio: strategy.settings?.max_reversal_overshoot_ratio ?? null,
      fill_timing: strategy.settings?.fill_timing ?? "bar_close",
    },
  });
  const updateSettings = useUpdateStrategySettings(strategy.id, {
    onSuccess: () => toast.success("트레이딩 설정을 저장했습니다"),
    onError: (e) => toast.error(`저장 실패: ${e.message}`),
  });

  // React Compiler 호환 — form.watch() 는 memoize 불가라 useWatch 구독 훅을 쓴다.
  const tradingSessions = useWatch({ control: form.control, name: "trading_sessions" }) ?? [];
  const nameError = form.formState.errors.name?.message;
  // BL-570 — 이 폼은 검증 탈락을 어디에도 그리지 않아 저장이 조용히 죽었다.
  const settingsErrors = settingsForm.formState.errors;

  return (
    <>
      {/* ===== 메타데이터 ===== */}
      <div className="card">
        <div className="card-body">
          <form onSubmit={form.handleSubmit((v) => update.mutate(v))}>
            <div className="field-grid">
              <div className="field span-2">
                <label className="field-label" htmlFor="m-name">
                  이름
                </label>
                <input
                  className="input"
                  id="m-name"
                  type="text"
                  maxLength={120}
                  {...form.register("name")}
                />
                {nameError ? <span className="field-error">{nameError}</span> : null}
              </div>
              <div className="field span-2">
                <label className="field-label" htmlFor="m-desc">
                  설명
                </label>
                <textarea
                  className="textarea"
                  id="m-desc"
                  maxLength={2000}
                  {...form.register("description")}
                />
              </div>
              <div className="field">
                <label className="field-label" htmlFor="m-symbol">
                  심볼
                </label>
                <input className="input" id="m-symbol" type="text" maxLength={32} {...form.register("symbol")} />
              </div>
              <div className="field">
                <label className="field-label" htmlFor="m-tf">
                  타임프레임
                </label>
                <input className="input" id="m-tf" type="text" maxLength={16} {...form.register("timeframe")} />
              </div>
              <div className="field span-2">
                <label className="field-label" htmlFor="m-tags">
                  태그
                </label>
                <input
                  className="input"
                  id="m-tags"
                  type="text"
                  defaultValue={strategy.tags.join(", ")}
                  placeholder="쉼표로 구분 (예: trend, ema)"
                  onChange={(e) => {
                    const tags = e.target.value
                      .split(",")
                      .map((t) => t.trim())
                      .filter(Boolean);
                    form.setValue("tags", tags, { shouldDirty: true });
                  }}
                />
              </div>
              <div className="field span-2">
                <span className="field-label">거래 세션</span>
                <SessionChips
                  value={tradingSessions}
                  onChange={(next) =>
                    form.setValue("trading_sessions", next, { shouldDirty: true })
                  }
                />
                <span className="field-hint">
                  {tradingSessions.length === 0
                    ? "선택하지 않으면 24시간 제한 없이 주문을 실행합니다."
                    : "선택한 세션 시간에만 주문을 실행합니다. 서버가 UTC 로 필터링합니다."}
                </span>
              </div>
            </div>
            <div className="form-actions">
              <button
                className="btn btn-primary"
                type="submit"
                disabled={!form.formState.isDirty || update.isPending}
              >
                {update.isPending ? "저장 중" : "변경사항 저장"}
              </button>
            </div>
          </form>
        </div>
      </div>

      {/* ===== 트레이딩 설정 ===== */}
      <div className="card" style={{ marginTop: "16px" }}>
        <div className="card-head">
          <div>
            <h3 className="card-title">트레이딩 설정</h3>
            <p className="card-sub">
              라이브 세션 시작에 필요한 값입니다.
              {strategy.settings == null ? " 아직 설정하지 않아 라이브 세션이 차단됩니다." : ""}
            </p>
          </div>
        </div>
        <div className="card-body">
          {/* BL-570 — onInvalid 를 반드시 넘긴다. 이걸 빼면 검증 탈락이 화면에 아무 흔적도
              남기지 않는다(요청 0 · 토스트 0 · 에러 0). 필드 에러 렌더는 아래 각 field 에 있다. */}
          <form
            onSubmit={settingsForm.handleSubmit(
              (v) => updateSettings.mutate(v),
              () => toast.error("저장하지 못했습니다: 입력값을 확인해 주세요"),
            )}
          >
            <div className="field-grid">
              <div className="field">
                <label className="field-label" htmlFor="s-lev">
                  레버리지 (1 ~ 125)
                </label>
                <input
                  className="input mono"
                  id="s-lev"
                  type="number"
                  min={1}
                  max={125}
                  step={1}
                  {...settingsForm.register("leverage", { valueAsNumber: true })}
                />
                {settingsErrors.leverage?.message ? (
                  <span className="field-error">{settingsErrors.leverage.message}</span>
                ) : null}
                <span className="field-hint">거래소 마진 배수입니다. Bybit 은 최대 125배입니다.</span>
              </div>
              <div className="field">
                <label className="field-label" htmlFor="s-margin">
                  마진 모드
                </label>
                <select className="select" id="s-margin" {...settingsForm.register("margin_mode")}>
                  <option value="cross">교차 (Cross)</option>
                  <option value="isolated">격리 (Isolated)</option>
                </select>
              </div>
              <div className="field span-2">
                <label className="field-label" htmlFor="s-size">
                  포지션 크기 % (0 초과 100 이하)
                </label>
                <input
                  className="input mono"
                  id="s-size"
                  type="number"
                  min={0.01}
                  max={100}
                  step="any"
                  {...settingsForm.register("position_size_pct", { valueAsNumber: true })}
                />
                {settingsErrors.position_size_pct?.message ? (
                  <span className="field-error">{settingsErrors.position_size_pct.message}</span>
                ) : null}
                <span className="field-hint">가용 잔고 대비 포지션 크기입니다. 100 이면 전액입니다.</span>
              </div>
              <div className="field">
                <label className="field-label" htmlFor="s-trigger-breach-cap">
                  트리거 돌파 상한 (%)
                </label>
                <input
                  className="input mono"
                  id="s-trigger-breach-cap"
                  type="number"
                  min={0}
                  step="any"
                  {...settingsForm.register("max_trigger_breach_pct", {
                    // ★BL-570 — RHF 는 registration 시점에 **DOM 문자열이 아니라 defaultValue 를
                    //   그대로** setValueAs 에 넘긴다(`setFieldValue` → `getFieldValueAs`).
                    //   그래서 `""` 만 거르면 `null` 이 새어 `Number(null) === 0` 이 되고,
                    //   zod `.gt(0)` 이 그 0 을 거부해 저장이 **조용히 죽었다**. 빈 값 3종을 모두 건다.
                    setValueAs: (value) =>
                      value === "" || value === null || value === undefined ? null : Number(value),
                  })}
                />
                {settingsErrors.max_trigger_breach_pct?.message ? (
                  <span className="field-error">
                    {settingsErrors.max_trigger_breach_pct.message}
                  </span>
                ) : null}
                {/* ★min={0} 이라 브라우저는 0 을 받아주지만 스키마는 `.gt(0)` 라 거부한다.
                    UI 가 0 을 허용하는 것처럼 보이지 않도록 힌트에 적는다. */}
                <span className="field-hint">비워두면 제한 없음입니다. 값을 넣으려면 0 보다 커야 합니다.</span>
              </div>
              <div className="field">
                <label className="field-label" htmlFor="s-fill-timing">
                  체결 시점
                </label>
                <select
                  className="select"
                  id="s-fill-timing"
                  {...settingsForm.register("fill_timing")}
                >
                  <option value="bar_close">시그널 봉 종가</option>
                  <option value="next_bar_open">시그널 다음 봉 시가</option>
                </select>
                <span className="field-hint">
                  다음 봉 시가를 선택하면 진입과 청산이 모두 한 bar 늦게 체결됩니다. 손절 청산도 지연될 수 있습니다.
                </span>
              </div>
            </div>
            <div className="form-actions">
              <button
                className="btn btn-primary"
                type="submit"
                disabled={!settingsForm.formState.isDirty || updateSettings.isPending}
              >
                {updateSettings.isPending
                  ? "저장 중"
                  : strategy.settings == null
                    ? "설정 등록"
                    : "설정 저장"}
              </button>
            </div>
          </form>
        </div>
      </div>
    </>
  );
}
