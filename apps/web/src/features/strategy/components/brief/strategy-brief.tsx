"use client";

// [ADR-040] 전략 브리핑 — 백테스트 제출 **전에** 「이 전략이 무엇을 하는가」를 답한다.
//
// ★층의 권한이 다르다. 여기 있는 것은 **전부 결정론 층**이다(AST · coverage · classifier).
//   판정어(실행 가능 / 미지원 / degraded / Track)는 이 층만 낸다. LLM 해설은 Stage 4 에서
//   별 엔드포인트로 붙고, **그쪽이 죽어도 이 컴포넌트만으로 화면이 완결되어야 한다.**
// ★없는 필드는 그리지 않는다(`_KIT.md` §4.9) — `signals` 가 비는 것은 정상이고
//   (Track S 의 `if cond` 형태), 그때 「신호 없음」이라고 쓰면 거짓이다.

import Link from "next/link";

import { StateBox } from "@/components/state-box";
import { PythonViewPanel } from "@/features/strategy/components/brief/python-view";
import { useStrategyBrief } from "@/features/strategy/hooks";
import { PINE_FUNCTION_LEXICON } from "@/features/strategy/pine-lexicon";
import { isSweepable, type StrategyBrief } from "@/features/strategy/schemas";
import { CHIP_TONE_CLASS, EMPTY_CELL } from "@/lib/labels";

const TRACK_LABEL: Record<"S" | "A" | "M", string> = {
  S: "S · strategy() 선언, 네이티브 실행",
  A: "A · indicator + alert, 가상 strategy 래퍼",
  M: "M · indicator, 지표 pass-through",
};

const ORDER_LABEL: Record<string, string> = {
  "strategy.entry": "진입",
  "strategy.exit": "청산(TP/SL)",
  "strategy.close": "청산",
  "strategy.close_all": "전량 청산",
};

export function StrategyBriefPanel({
  strategyId,
  editHref,
}: {
  strategyId: string;
  /** 줄번호에서 소스로 데려갈 링크. 없으면 줄번호를 텍스트로만 그린다. */
  editHref?: string;
}) {
  const query = useStrategyBrief(strategyId);

  if (query.isPending) {
    return <BriefSkeleton />;
  }
  if (query.isError || !query.data) {
    return (
      <StateBox
        testId="brief-error"
        tone="failed"
        title="브리핑을 불러오지 못했습니다."
        body="전략 소스를 파싱하는 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요."
      />
    );
  }

  return <BriefBody brief={query.data} editHref={editHref} />;
}

function BriefBody({ brief, editHref }: { brief: StrategyBrief; editHref?: string }) {
  const { parse, orders, signals, track } = brief;
  const blocked = parse.unsupported_calls.length > 0 || parse.unsupported_builtins.length > 0;

  return (
    <div className="brief" data-testid="strategy-brief">
      {/* ── ① 판정 (결정론) — 여기가 유일한 「판정」이다 ── */}
      <div className="brief-verdict">
        <span
          className={parse.is_runnable ? CHIP_TONE_CLASS.done : CHIP_TONE_CLASS.warn}
          data-testid="brief-verdict"
        >
          {parse.is_runnable ? "실행 가능" : "실행 불가"}
        </span>
        {track ? <span className={CHIP_TONE_CLASS.neutral}>{TRACK_LABEL[track]}</span> : null}
        {parse.dogfood_only_warning ? (
          <span className={CHIP_TONE_CLASS.warn}>{parse.dogfood_only_warning}</span>
        ) : null}
      </div>

      {blocked ? (
        <div className="brief-section" data-testid="brief-blocked">
          <p className="metric-group-title">백테스트를 막는 것</p>
          <ul className="brief-list">
            {parse.unsupported_calls.map((c) => (
              <li key={`${c.name}-${c.line}`}>
                <span className="mono">{c.name}</span>
                {c.line !== null ? <SourceLine line={c.line} editHref={editHref} /> : null}
                {c.workaround ? <span className="dim"> · {c.workaround}</span> : null}
              </li>
            ))}
          </ul>
          <p className="strip-note">
            미지원 호출이 하나라도 있으면 <strong>부분 실행하지 않습니다</strong>. 잘못된 결과를
            내는 것보다 멈추는 쪽을 택합니다.
          </p>
        </div>
      ) : null}

      {/* ── ② 구조 (결정론) ── */}
      <div className="brief-section">
        <p className="metric-group-title">파라미터</p>
        {parse.inputs.length === 0 ? (
          <p className="dim">조절할 파라미터를 선언하지 않았습니다.</p>
        ) : (
          <ul className="brief-list" data-testid="brief-params">
            {parse.inputs.map((p) => (
              <li key={p.var_name}>
                <span className="mono">{p.var_name}</span>
                <span className="dim"> = {p.defval ?? EMPTY_CELL}</span>
                <span className="dim"> ({p.input_type})</span>
                {p.title ? <span> · {p.title}</span> : null}
                {isSweepable(p) ? null : <span className="dim"> · 최적화 스윕 불가</span>}
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="brief-section">
        <p className="metric-group-title">사용 지표</p>
        {parse.functions_used.length === 0 ? (
          <p className="dim">감지된 함수가 없습니다.</p>
        ) : (
          <ul className="brief-list" data-testid="brief-indicators">
            {parse.functions_used.map((fn) => {
              // ★해설은 오프라인 결정적 사전이 먼저다 — LLM 은 사전이 못 덮는 것만 맡는다.
              //   `describeFunction` 은 미등록 이름에도 안내 문구를 돌려주므로 그것을 그리면
              //   「해설이 등록되지 않았습니다」가 지표 설명 자리에 앉는다. 사전에 있을 때만 그린다.
              const known = PINE_FUNCTION_LEXICON[fn];
              return (
                <li key={fn}>
                  <span className="mono">{fn}</span>
                  {known ? <span className="dim"> · {known.summary}</span> : null}
                </li>
              );
            })}
          </ul>
        )}
      </div>

      <div className="brief-section">
        <p className="metric-group-title">진입 · 청산</p>
        {orders.length === 0 ? (
          <p className="dim">주문 호출이 없습니다. 이 스크립트는 신호만 냅니다.</p>
        ) : (
          <ul className="brief-list" data-testid="brief-orders">
            {orders.map((o) => (
              <li key={`${o.name}-${o.line}`}>
                <span className={CHIP_TONE_CLASS.neutral}>{ORDER_LABEL[o.name] ?? o.name}</span>{" "}
                <span className="mono">{o.name}</span>
                {o.line !== null ? <SourceLine line={o.line} editHref={editHref} /> : null}
                {o.args.length > 0 ? (
                  <span className="dim mono"> ({o.args.map((a) => a.value).join(", ")})</span>
                ) : null}
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* ★비었으면 절 자체를 그리지 않는다 — 「신호 없음」으로 읽히면 거짓이다. */}
      {signals.length > 0 ? (
        <div className="brief-section">
          <p className="metric-group-title">신호 변수</p>
          <ul className="brief-list" data-testid="brief-signals">
            {signals.map((v) => (
              <li key={v}>
                <span className="mono">{v}</span>
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {parse.declaration ? <SizingSection declaration={parse.declaration} /> : null}

      {/* [ADR-042] 읽기 전용 Python 뷰 — 기본은 접혀 있다. */}
      {brief.python_view ? (
        <div className="brief-section">
          <PythonViewPanel view={brief.python_view} />
        </div>
      ) : null}
    </div>
  );
}

function SizingSection({
  declaration,
}: {
  declaration: NonNullable<StrategyBrief["parse"]["declaration"]>;
}) {
  const hasAny =
    declaration.default_qty_type !== null ||
    declaration.default_qty_value !== null ||
    declaration.pyramiding !== null;
  if (!hasAny) {
    return null;
  }
  return (
    <div className="brief-section" data-testid="brief-sizing">
      <p className="metric-group-title">스크립트가 정한 사이징</p>
      <ul className="brief-list">
        {declaration.default_qty_type !== null ? (
          <li>
            수량 방식 <span className="mono">{declaration.default_qty_type}</span>
            {declaration.default_qty_value !== null ? (
              <span className="mono"> {declaration.default_qty_value}</span>
            ) : null}
          </li>
        ) : null}
        {declaration.pyramiding !== null ? (
          <li>
            피라미딩 <span className="mono">{declaration.pyramiding}</span> · 같은 방향 최대 동시
            진입
          </li>
        ) : null}
      </ul>
    </div>
  );
}

function SourceLine({ line, editHref }: { line: number; editHref?: string }) {
  const label = `L${line}`;
  if (!editHref) {
    return <span className="dim mono"> {label}</span>;
  }
  return (
    <>
      {" "}
      <Link className="mono" href={`${editHref}#L${line}`}>
        {label}
      </Link>
    </>
  );
}

function BriefSkeleton() {
  // 로딩 표현은 스켈레톤 shimmer 하나다 — 맥동 점·블링크 금지(`_KIT.md`).
  return (
    <div className="brief" aria-busy="true" data-testid="brief-skeleton">
      {/* 기존 진단 스켈레톤과 같은 `.sk` 관례를 쓴다 — 새 클래스를 만들지 않는다. */}
      <div className="sk sk-line" style={{ width: "34%" }} aria-hidden="true" />
      <div className="sk sk-line" style={{ width: "82%" }} aria-hidden="true" />
      <div className="sk sk-line" style={{ width: "64%" }} aria-hidden="true" />
      <p className="state-note">전략 소스를 분석하고 있습니다.</p>
    </div>
  );
}
