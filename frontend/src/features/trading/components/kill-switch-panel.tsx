"use client";

// 킬 스위치 상태 패널 — C 디자인 언어 이식 (S8). 프로토타입 screen-01 §04 리스크 가드의
// 공용 .card/.state-box 시맨틱 CSS 를 소비한다. active(resolved_at IS NULL) 이벤트가 있으면
// destructive state-box + 해결 버튼, 없으면 평온한 "이상 없음". 상태 enum 은 라벨 SSOT 를
// 거칠 필요가 없다(트리거 라벨은 배너가 담당하고 여기선 값·임계만 인쇄).

import { AlertTriangleIcon, ShieldCheckIcon } from "lucide-react";

import { KILL_SWITCH_LABEL } from "../labels";
import { useKillSwitchEvents, useResolveKillSwitchEvent } from "../hooks";

export function KillSwitchPanel() {
  const { data, isError } = useKillSwitchEvents();
  const resolve = useResolveKillSwitchEvent();

  if (isError) {
    return (
      <div className="card">
        <div className="card-body">
          <div className="state-box failed" role="alert">
            <span className="state-icon failed" aria-hidden="true">
              <AlertTriangleIcon />
            </span>
            <p className="state-title">
              킬 스위치 상태를 불러오지 못했습니다.
            </p>
            <p className="state-body">
              주문을 내기 전에 상태를 확인하세요.
            </p>
            <p className="state-code">GET /api/v1/kill-switch/events</p>
          </div>
        </div>
      </div>
    );
  }
  if (!data) return null;

  const active = data.items.filter((e) => !e.resolved_at);
  const hasActiveDanger = active.length > 0;

  return (
    <div
      className="card"
      data-testid="kill-switch-panel"
      data-state={hasActiveDanger ? "active" : "ok"}
    >
      <div className="card-head">
        <div>
          <h3 className="card-title">{KILL_SWITCH_LABEL.feature}</h3>
          <p className="card-sub">
            손실·마진·포지션 한도 위반 시 자동 주문을 차단하는 리스크 게이트입니다.
          </p>
        </div>
        <span className={hasActiveDanger ? "chip warn" : "chip"}>
          {hasActiveDanger ? `활성 ${active.length}` : "대기"}
        </span>
      </div>

      {!hasActiveDanger ? (
        <div className="card-body">
          <p className="ks-ok">
            <ShieldCheckIcon aria-hidden="true" />
            이상 없음
          </p>
        </div>
      ) : (
        <div className="card-body">
          <div className="state-box failed" role="alert">
            <p className="state-title">
              킬 스위치 활성. 자동 주문이 중지됩니다.
            </p>
            <ul className="ks-list">
              {active.map((e) => (
                <li key={e.id} className="ks-row">
                  <span className="mono">
                    {e.trigger_type}: {e.trigger_value} / {e.threshold}
                  </span>
                  {/* Wave 2 — 모바일 터치타겟 확보용 공용 .btn (min-height 38px). */}
                  <button
                    type="button"
                    className="btn btn-danger btn-xs"
                    onClick={() => resolve.mutate(e.id)}
                    disabled={resolve.isPending}
                  >
                    {resolve.isPending ? "처리 중…" : "해결"}
                  </button>
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}
    </div>
  );
}
