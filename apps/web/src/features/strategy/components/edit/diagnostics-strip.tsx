"use client";

// 저장 전 정적 진단 띠 — C 디자인 언어 이식 (screen-08 §02). 진짜 탭 3종(파싱/파라미터/지표).
// §3-6: role="tablist" + role="tabpanel" 이 적법한 17벌 중 유일한 화면이라 진짜 <Tabs> 를 쓴다.
// 데이터는 편집 버퍼(edit-store) pineSource 를 debounce 후 usePreviewParse 로 재파싱한 결과다.
// 파라미터 표는 [ADR-040] Stage 1 에서 `ParsePreviewResponse.inputs` 가 열리며 실데이터가 됐다.
// 함수 호출 횟수·파싱 소요·사전 버전은 여전히 응답에 없어 미렌더한다(§4.9). 없는 필드는 그리지 않는다.

import { useState } from "react";
import { AlertTriangleIcon, RefreshCwIcon } from "lucide-react";

import { selectPineSource, useEditStore } from "@/features/strategy/edit-store";
import { usePreviewParse } from "@/features/strategy/hooks";
import { PARSE_STATUS_LABEL, UNSUPPORTED_POLICY_NOTE } from "@/features/strategy/labels";
import { type InputDecl, isSweepable, type StrategyResponse } from "@/features/strategy/schemas";
import { useDebouncedValue } from "@/features/strategy/utils";
import { StateBox } from "@/components/state-box";
import { CHIP_TONE_CLASS, EMPTY_CELL } from "@/lib/labels";

type DiagTab = "parse" | "param" | "indicator";
const PARSE_ENDPOINT_TEMPLATE = "POST /api/v1/strategies/parse";

const TABS: ReadonlyArray<{ id: DiagTab; label: string }> = [
  { id: "parse", label: "파싱" },
  { id: "param", label: "파라미터" },
  { id: "indicator", label: "지표" },
];

export function DiagnosticsStrip({ strategy }: { strategy: StrategyResponse }) {
  const pineSource = useEditStore(selectPineSource);
  const debounced = useDebouncedValue(pineSource, 500);
  const preview = usePreviewParse(debounced);
  const live = preview.data ?? null;
  const [tab, setTab] = useState<DiagTab>("parse");

  const status = live?.status ?? strategy.parse_status;
  const supportedCount = live?.functions_used.length ?? 0;
  const unsupportedCount = live?.unsupported_builtins.length ?? 0;
  const detected = supportedCount + unsupportedCount;
  const pct = detected > 0 ? Math.round((supportedCount / detected) * 100) : 100;
  const verdictTone = live && unsupportedCount === 0 && live.status === "ok" ? "done" : "warn";

  return (
    <div className="card">
      <div className="card-head strip-head">
        <div>
          <h3 className="card-title">정적 진단</h3>
          <p className="card-sub">
            {preview.isFetching
              ? "편집 중인 소스를 다시 파싱하고 있습니다."
              : "편집 중인 소스 기준"}
          </p>
        </div>
        <div className="strip-head-right">
          <div className="tabs" role="tablist" aria-label="진단 항목">
            {TABS.map((t) => (
              <button
                key={t.id}
                id={`diag-tab-${t.id}`}
                className={`tab${tab === t.id ? " active" : ""}`}
                role="tab"
                type="button"
                aria-selected={tab === t.id}
                aria-controls={`diag-panel-${t.id}`}
                onClick={() => setTab(t.id)}
              >
                {t.label}
              </button>
            ))}
          </div>
          <div className="verdict">
            <p className="kpi-label">지원 판정</p>
            <p className="kpi-value mono">
              {supportedCount} / {detected}
            </p>
            <div className={verdictTone === "done" ? "meter bull" : "meter"}>
              <span style={{ width: `${pct}%` }} />
            </div>
            <p className="kpi-foot">
              감지된 함수 <span className="mono">{detected}종</span> 대비 지원{" "}
              <span className="mono">{pct}%</span>
            </p>
          </div>
        </div>
      </div>

      {/* (a) 파싱 탭 */}
      <div
        className="strip-body"
        id="diag-panel-parse"
        role="tabpanel"
        // ★WAI-ARIA APG(Tabs) — 포커스 가능한 요소가 없는 tabpanel 은 tabindex=0 이어야 키보드로
        //   도달·스크롤할 수 있다. 원본 규칙 jsx-a11y/no-noninteractive-tabindex 는 이 자리를
        //   `roles:["tabpanel"]` 로 기본 면제하는데 Biome 포팅에는 그 옵션이 없어 잡는다(2026-08-22 실측).
        // biome-ignore lint/a11y/noNoninteractiveTabindex: 위 근거 — 규칙이 아니라 이 자리가 옳다.
        tabIndex={0}
        aria-labelledby="diag-tab-parse"
        hidden={tab !== "parse"}
      >
        {preview.isFetching && !live ? (
          <ParseSkeleton />
        ) : preview.isError ? (
          <StateBox
            tone="failed"
            testId="diag-parse-error"
            icon={<AlertTriangleIcon />}
            title="파싱 요청이 실패했습니다."
            body="편집 중인 소스를 다시 파싱하지 못했습니다. 직전 판정 값으로 표시 중입니다."
            code={`${PARSE_ENDPOINT_TEMPLATE} · ${(preview.error as Error).message}`}
          >
            <button className="btn btn-ghost" type="button" onClick={() => preview.refetch()}>
              <RefreshCwIcon aria-hidden="true" />
              다시 시도
            </button>
          </StateBox>
        ) : !live ? (
          <StateBox
            testId="diag-parse-empty"
            title="아직 파싱 결과가 없습니다."
            body="위 편집기에 Pine 소스를 입력하면 저장 전 정적 분석 결과를 여기서 확인합니다."
          />
        ) : (
          <div className="strip-3" data-testid="diag-parse-result">
            <div className="strip-col">
              <p className="strip-col-title">판정</p>
              <div className="metric">
                <span className="metric-label">지원 여부</span>
                <span className={CHIP_TONE_CLASS[verdictTone]}>
                  {PARSE_STATUS_LABEL[status].label}
                </span>
              </div>
              <div className="metric">
                <span className="metric-label">Pine 버전</span>
                <span className="metric-value">{live.pine_version}</span>
              </div>
            </div>
            <div className="strip-col">
              <p className="strip-col-title">에러 · 경고</p>
              <div className="metric">
                <span className="metric-label">에러</span>
                <span className="metric-value">{live.errors.length}</span>
              </div>
              <div className="metric">
                <span className="metric-label">경고</span>
                <span className="metric-value">{live.warnings.length}</span>
              </div>
            </div>
            <div className="strip-col">
              <p className="strip-col-title">미지원 함수</p>
              {unsupportedCount === 0 ? (
                <p className="strip-note">미지원 함수가 없습니다. 백테스트를 실행할 수 있습니다.</p>
              ) : (
                <>
                  <ul className="unsupported">
                    {live.unsupported_builtins.map((fn) => (
                      <li key={fn}>
                        <span className="mono">{fn}</span>
                      </li>
                    ))}
                  </ul>
                  <p className="strip-note">{UNSUPPORTED_POLICY_NOTE}</p>
                </>
              )}
            </div>
          </div>
        )}
      </div>

      {/* (b) 파라미터 탭 — `inputs` 실데이터([ADR-040] Stage 1). */}
      <div
        className="strip-body"
        id="diag-panel-param"
        role="tabpanel"
        // ★WAI-ARIA APG(Tabs) — 포커스 가능한 요소가 없는 tabpanel 은 tabindex=0 이어야 키보드로
        //   도달·스크롤할 수 있다. 원본 규칙 jsx-a11y/no-noninteractive-tabindex 는 이 자리를
        //   `roles:["tabpanel"]` 로 기본 면제하는데 Biome 포팅에는 그 옵션이 없어 잡는다(2026-08-22 실측).
        // biome-ignore lint/a11y/noNoninteractiveTabindex: 위 근거 — 규칙이 아니라 이 자리가 옳다.
        tabIndex={0}
        aria-labelledby="diag-tab-param"
        hidden={tab !== "param"}
      >
        {!live ? (
          <StateBox
            testId="diag-param-empty"
            title="아직 파싱된 파라미터가 없습니다."
            body="소스를 파싱하면 input 선언 목록이 여기에 표시됩니다."
          />
        ) : live.inputs.length === 0 ? (
          <StateBox
            testId="diag-param-none"
            title="input 선언이 없습니다."
            body="이 전략은 조절할 파라미터를 선언하지 않았습니다. 최적화·파라미터 안정성 분석의 대상이 아닙니다."
          />
        ) : (
          <ParameterTable inputs={live.inputs} />
        )}
      </div>

      {/* (c) 지표 탭 */}
      <div
        className="strip-body"
        id="diag-panel-indicator"
        role="tabpanel"
        // ★WAI-ARIA APG(Tabs) — 포커스 가능한 요소가 없는 tabpanel 은 tabindex=0 이어야 키보드로
        //   도달·스크롤할 수 있다. 원본 규칙 jsx-a11y/no-noninteractive-tabindex 는 이 자리를
        //   `roles:["tabpanel"]` 로 기본 면제하는데 Biome 포팅에는 그 옵션이 없어 잡는다(2026-08-22 실측).
        // biome-ignore lint/a11y/noNoninteractiveTabindex: 위 근거 — 규칙이 아니라 이 자리가 옳다.
        tabIndex={0}
        aria-labelledby="diag-tab-indicator"
        hidden={tab !== "indicator"}
      >
        {!live ? (
          <StateBox
            testId="diag-indicator-empty"
            title="아직 감지된 함수가 없습니다."
            body="소스를 파싱하면 감지된 함수 목록이 여기에 표시됩니다."
          />
        ) : (
          <>
            <div className="metric-groups">
              <div className="metric-group">
                <p className="metric-group-title">감지된 함수 {supportedCount}종</p>
                {live.functions_used.length === 0 ? (
                  <div className="metric">
                    <span className="metric-label dim">감지된 함수가 없습니다.</span>
                  </div>
                ) : (
                  live.functions_used.map((fn) => (
                    <div className="metric" key={fn}>
                      <span className="metric-label mono">{fn}</span>
                    </div>
                  ))
                )}
              </div>
              <div className="metric-group">
                <p className="metric-group-title">판정 요약</p>
                <div className="metric">
                  <span className="metric-label">지원 함수</span>
                  <span className="metric-value">{supportedCount}</span>
                </div>
                <div className="metric">
                  <span className="metric-label">미지원 함수</span>
                  <span className="metric-value">{unsupportedCount}</span>
                </div>
                <div className="metric">
                  <span className="metric-label">진입 시그널</span>
                  <span className="metric-value">{live.entry_count}</span>
                </div>
                <div className="metric">
                  <span className="metric-label">청산 시그널</span>
                  <span className="metric-value">{live.exit_count}</span>
                </div>
                {/* 무데이터 셀 — 총 호출·파싱 소요·사전 버전은 응답에 필드가 없어 표기하지 않는다. */}
                <div className="metric">
                  <span className="metric-label">파싱 소요</span>
                  <span
                    className="metric-value empty"
                    title="서버 응답에 파싱 소요 시간 필드가 없습니다."
                  >
                    {EMPTY_CELL}
                  </span>
                </div>
              </div>
            </div>
            <p className="strip-note">{UNSUPPORTED_POLICY_NOTE}</p>
          </>
        )}
      </div>
    </div>
  );
}

function ParameterTable({ inputs }: { inputs: readonly InputDecl[] }) {
  const sweepable = inputs.filter(isSweepable).length;

  return (
    <>
      <div className="table-wrap">
        <table className="trades" aria-label={`파라미터 ${inputs.length}개`}>
          <thead>
            <tr>
              <th scope="col">이름</th>
              <th scope="col">설명</th>
              <th scope="col">타입</th>
              <th scope="col" className="num">
                기본값
              </th>
              <th scope="col">스윕</th>
            </tr>
          </thead>
          <tbody>
            {inputs.map((p) => (
              <tr key={p.var_name}>
                {/* ★var_name 을 가공하지 마라 — 이것이 최적화가 쓰는 override 키다. */}
                <td className="mono">{p.var_name}</td>
                <td>{p.title ?? <span className="empty">{EMPTY_CELL}</span>}</td>
                <td className="mono">{p.input_type}</td>
                <td className="num mono">
                  {p.defval ?? <span className="empty">{EMPTY_CELL}</span>}
                </td>
                <td>
                  {isSweepable(p) ? (
                    <span className={CHIP_TONE_CLASS.done}>가능</span>
                  ) : (
                    <span
                      className={CHIP_TONE_CLASS.warn}
                      title={`최적화는 input.int / input.float 만 스윕합니다. 이 항목은 ${p.input_type} 입니다.`}
                    >
                      불가
                    </span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="strip-note">
        {`${inputs.length}개 중 ${sweepable}개를 최적화·파라미터 안정성 분석에서 스윕할 수 있습니다. `}
        나머지는 백테스트에서 기본값으로 실행됩니다.
      </p>
    </>
  );
}

function ParseSkeleton() {
  return (
    <div className="strip-3" aria-busy="true" data-testid="diag-parse-skeleton">
      <div className="strip-col">
        <p className="strip-col-title">지표 미리보기</p>
        <div className="sk-bars" aria-hidden="true">
          {[44, 70, 33, 86, 52, 64, 38, 76].map((h) => (
            <span key={h} className="sk" style={{ height: `${h}%` }} />
          ))}
        </div>
        <div className="sk sk-line" style={{ width: "56%" }} aria-hidden="true" />
        <p className="state-note">소스를 파싱하고 있습니다. 보통 1초 안에 끝납니다.</p>
      </div>
    </div>
  );
}
