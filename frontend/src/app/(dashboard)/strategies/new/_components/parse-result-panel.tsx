"use client";

// 전략 파싱 결과 패널 — C 디자인 언어 이식 (screen-07 §03). 공용 .card/.kpi/.meter/.metric-group/
// .state-box 를 소비한다. 서버 응답(ParsePreviewResponse)이 받치는 값만 그린다.
// 프로토타입의 "N회" 함수 호출 횟수는 functions_used 가 이름 배열이라 개수 데이터가 없어
// 미렌더하고 함수명만 나열한다(§4.9). 파라미터 표는 스키마에 파라미터 필드가 0건이라 미렌더한다.

import { AlertTriangleIcon, CheckIcon } from "lucide-react";

import { PARSE_STATUS_LABEL, UNSUPPORTED_POLICY_NOTE } from "@/features/strategy/labels";
import type { ParsePreviewResponse } from "@/features/strategy/schemas";
import { StateBox } from "@/components/state-box";
import { CHIP_TONE_CLASS, EMPTY_CELL } from "@/lib/labels";

const PARSE_ENDPOINT = "POST /api/v1/strategies/parse";

interface ParseResultPanelProps {
  result: ParsePreviewResponse | null;
  loading: boolean;
  error?: string | null;
  /** 전략 저장 트리거. 파싱이 지원됨이고 이름이 채워졌을 때만 활성화된다. */
  onSave?: () => void;
  saving?: boolean;
  canSave?: boolean;
}

export function ParseResultPanel({
  result,
  loading,
  error = null,
  onSave,
  saving = false,
  canSave = false,
}: ParseResultPanelProps) {
  const supported = result?.status === "ok" && (result?.unsupported_builtins.length ?? 0) === 0;

  return (
    <div className="card" aria-live="polite" aria-label="파싱 결과">
      <div className="card-head">
        <div>
          <h3 className="card-title">판정 결과</h3>
          <p className="card-sub">붙여넣은 스크립트 기준</p>
        </div>
        {!loading && !error && result && supported ? (
          <span className={CHIP_TONE_CLASS.done}>
            <CheckIcon aria-hidden="true" />
            지원됨
          </span>
        ) : null}
      </div>

      <div className="card-body">
        {error ? (
          <RequestErrorState message={error} />
        ) : loading ? (
          <ParseSkeleton />
        ) : !result ? (
          <EmptyHint />
        ) : supported ? (
          <SupportedBody result={result} onSave={onSave} saving={saving} canSave={canSave} />
        ) : (
          <UnsupportedBody result={result} />
        )}
      </div>
    </div>
  );
}

// 요청 자체가 실패(네트워크/500)한 상태. 파싱 미지원(200 판정)과 구분해 엔드포인트를 노출한다.
function RequestErrorState({ message }: { message: string }) {
  return (
    <StateBox
      tone="failed"
      testId="parse-request-error"
      icon={<AlertTriangleIcon />}
      title="파싱 요청이 실패했습니다."
      body={message}
      code={PARSE_ENDPOINT}
    />
  );
}

function ParseSkeleton() {
  return (
    <div aria-busy="true" data-testid="parse-skeleton">
      <div className="sk-bars" aria-hidden="true">
        {[52, 74, 36, 84, 48, 62, 40, 70].map((h, i) => (
          <span key={i} className="sk" style={{ height: `${h}%` }} />
        ))}
      </div>
      <div className="sk sk-line" style={{ width: "58%" }} aria-hidden="true" />
      <p className="state-note">파싱 중입니다. 보통 1초 안에 끝납니다.</p>
    </div>
  );
}

function EmptyHint() {
  return (
    <StateBox
      testId="parse-empty"
      title="아직 파싱 결과가 없습니다."
      body="왼쪽에 Pine 스크립트를 붙여넣으면 지원 여부를 여기서 판정합니다."
    />
  );
}

function SupportedBody({
  result,
  onSave,
  saving,
  canSave,
}: {
  result: ParsePreviewResponse;
  onSave?: () => void;
  saving?: boolean;
  canSave?: boolean;
}) {
  const supportedCount = result.functions_used.length;
  const unsupportedCount = result.unsupported_builtins.length;
  const detected = supportedCount + unsupportedCount;
  const pct = detected > 0 ? Math.round((supportedCount / detected) * 100) : 100;

  return (
    <div data-testid="parse-supported">
      <div className="parse-kpi">
        <p className="kpi-label">지원 판정</p>
        <p className="kpi-value mono">
          {supportedCount} / {detected}
        </p>
        <div className="meter">
          <span style={{ width: `${pct}%` }} />
        </div>
        <p className="kpi-foot">
          감지된 함수 <span className="mono">{detected}종</span> 대비 지원{" "}
          <span className="mono">{pct}%</span>
        </p>
      </div>

      <div className="parse-body">
        <div className="metric-group">
          <p className="metric-group-title">감지된 함수</p>
          {result.functions_used.length === 0 ? (
            <div className="metric">
              <span className="metric-label dim">감지된 함수가 없습니다.</span>
            </div>
          ) : (
            result.functions_used.map((fn) => (
              <div className="metric" key={fn}>
                <span className="metric-label mono">{fn}</span>
              </div>
            ))
          )}
        </div>

        <div className="metric-group">
          <p className="metric-group-title">시그널</p>
          <div className="metric">
            <span className="metric-label">진입 시그널</span>
            <span className="metric-value">{result.entry_count}</span>
          </div>
          <div className="metric">
            <span className="metric-label">청산 시그널</span>
            <span className="metric-value">{result.exit_count}</span>
          </div>
          {/* 무데이터 셀 — Pine strategy() 에 심볼 인자가 없어 위 기본 정보에서 고른 값을 쓴다. */}
          <div className="metric">
            <span className="metric-label">심볼 기본값</span>
            <span
              className="metric-value empty"
              title="Pine 스크립트에는 심볼이 없습니다. 위 기본 정보에서 고른 값을 씁니다."
            >
              {EMPTY_CELL}
            </span>
          </div>
          {/* 파라미터 표는 스키마에 파라미터 필드가 0건이라 렌더하지 않는다(§4.9). */}
          <p className="metric-note">
            추출된 파라미터 표는 서버 응답에 파라미터 필드가 없어 표시하지 않습니다.
          </p>
        </div>
      </div>

      <button
        className="btn btn-primary btn-block"
        type="button"
        onClick={onSave}
        disabled={!canSave || saving}
        data-testid="parse-save"
      >
        {saving ? "저장 중" : "전략으로 저장"}
      </button>
      {!canSave ? (
        <p className="metric-note" style={{ textAlign: "center" }}>
          전략 이름을 입력하면 저장할 수 있습니다.
        </p>
      ) : null}
    </div>
  );
}

// 파싱이 미지원(unsupported) 또는 오류(error) 판정을 낸 상태. 200 판정이므로 HTTP 코드는 없다.
function UnsupportedBody({ result }: { result: ParsePreviewResponse }) {
  const label = PARSE_STATUS_LABEL[result.status].label;
  const hasUnsupported = result.unsupported_builtins.length > 0;
  return (
    <div className="state-box failed" role="alert" data-testid="parse-unsupported">
      <span className="state-icon failed" aria-hidden="true">
        <AlertTriangleIcon />
      </span>
      <p className="state-title">
        {hasUnsupported ? "이 스크립트는 아직 지원되지 않습니다." : label}
      </p>
      {hasUnsupported ? (
        <>
          <p className="state-body">미지원 함수 {result.unsupported_builtins.length}개를 찾았습니다.</p>
          <ul className="unsupported">
            {result.unsupported_builtins.map((fn) => (
              <li key={fn}>
                <span className="mono">{fn}</span>
              </li>
            ))}
          </ul>
        </>
      ) : null}
      {result.errors.length > 0 ? (
        <ul className="unsupported">
          {result.errors.map((e, i) => (
            <li key={`${e.code}-${i}`}>
              <span className="mono">{e.line != null ? `L${e.line}` : e.code}</span>
              {e.message}
            </li>
          ))}
        </ul>
      ) : null}
      <p className="state-body">{UNSUPPORTED_POLICY_NOTE}</p>
    </div>
  );
}
