"use client";

// 세션 부가 진단 (코크핏 §06) — C 디자인 언어 이식 (S8). 프로토타입 screen-01 §06 처럼
// 스키마가 받치지 않는 표면(포지션 대조·실시간 스트림·알림 규칙)을 감추지 않고 정직하게
// 미제공/에러/빈/정상 상태로 노출한다(캐논 §4.9 · §6). 공용 .diag/.state-box/.sk 를 소비한다.
//   - 포지션 동기화: 열린 포지션을 거래소에서 직접 대조하는 API 가 아직 없다. 백엔드엔
//     GET /live-sessions/{id}/state 만 있고 포지션 대조 엔드포인트는 미구현이다. 캐논 §6 의
//     프로토타입 표기(엔드포인트+상태코드 노출)와 충돌하면 '실제 API 부재' 쪽이 정직성
//     우선이라, 지어낸 GET .../positions · 503 대신 '미제공' 상태로 둔다(가짜 코드·경로 제거).

import type { ReactNode } from "react";
import {
  AlertTriangleIcon,
  BellIcon,
  ClockIcon,
  LayersIcon,
  WifiIcon,
} from "lucide-react";

import { StateBox } from "@/components/state-box";

export type DiagnosticState = "loading" | "error" | "empty" | "ok";

const STATE_ARIA: Record<DiagnosticState, string> = {
  loading: "불러오는 중",
  error: "불러오기 실패",
  empty: "비어 있음",
  ok: "정상",
};

export interface DiagnosticCardProps {
  title: string;
  subtitle: string;
  state: DiagnosticState;
  heading: string;
  body: string;
  /** error 상태에서 노출하는 실제 엔드포인트 + 상태코드. */
  code?: string;
  /** error/empty/ok 상태 아이콘. */
  icon: ReactNode;
}

/** 4상태(로딩/에러/빈/정상)를 렌더하는 진단 카드 프리미티브. */
export function DiagnosticCard({
  title,
  subtitle,
  state,
  heading,
  body,
  code,
  icon,
}: DiagnosticCardProps) {
  return (
    <article
      className="card diag"
      aria-label={`${title}, ${STATE_ARIA[state]}`}
      aria-busy={state === "loading" || undefined}
      data-testid={`diag-${state}`}
    >
      <div className="card-head">
        <div>
          <h3 className="card-title">{title}</h3>
          <p className="card-sub">{subtitle}</p>
        </div>
      </div>
      <div className="card-body">
        {state === "loading" ? (
          <>
            <div className="sk" style={{ height: 96 }} aria-hidden="true" />
            <div className="sk sk-line" style={{ width: "72%" }} aria-hidden="true" />
            <p className="state-note">
              <ClockIcon aria-hidden="true" />
              {body}
            </p>
          </>
        ) : (
          <StateBox
            tone={state === "error" ? "failed" : "neutral"}
            icon={state === "error" ? <AlertTriangleIcon /> : icon}
            title={heading}
            body={body}
            code={state === "error" && code ? code : undefined}
          />
        )}
      </div>
    </article>
  );
}

/** 코크핏 §06 진단 3종. 셋 다 스키마가 받치지 않는 표면이라 미제공/미연결로 정직하게 둔다. */
export function SessionDiagnostics() {
  return (
    <div className="diag-row">
      <DiagnosticCard
        title="포지션 동기화"
        subtitle="거래소 대조 조회"
        state="empty"
        icon={<LayersIcon />}
        heading="포지션 대조는 아직 제공되지 않습니다."
        body="열린 포지션을 거래소에서 직접 대조하는 API 가 아직 없습니다. 확인할 수 없는 값을 지어내지 않으려고 포지션 표를 두지 않고 미제공으로 둡니다."
      />
      <DiagnosticCard
        title="실시간 가격 스트림"
        subtitle="WebSocket 시세 구독"
        state="empty"
        icon={<WifiIcon />}
        heading="실시간 스트림이 연결되지 않았습니다."
        body="실시간 시세는 WebSocket 과 Zustand 캐시로 따로 배선합니다. 지금 이 코크핏의 값은 폴링 스냅샷이라 새로고침을 눌러야 갱신됩니다."
      />
      <DiagnosticCard
        title="알림 규칙"
        subtitle="이 세션에만 적용됩니다."
        state="empty"
        icon={<BellIcon />}
        heading="알림 규칙이 없습니다."
        body="손실 한도 접근이나 워치독 중단처럼 화면을 보고 있지 않을 때 알아야 할 사건에 규칙을 걸 수 있습니다. 이 기능은 아직 제공되지 않습니다."
      />
    </div>
  );
}
