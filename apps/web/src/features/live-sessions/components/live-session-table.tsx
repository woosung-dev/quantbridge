"use client";

// 라이브 세션 전체 개요 표 — C 디자인 언어 이식 (S8). 프로토타입 screen-01 §03 의 공용
// .card/.trades 시맨틱 CSS 를 소비한다. 읽기 전용 요약이고, 세션 조작(생성·중단·선택)은
// LiveSessionList 가 맡는다. S7 이 /dashboard 에서 디커플했고 이제 /trading 이 단독 소비자라
// trading/_components 에서 이 도메인 폴더로 옮겨 응집도를 회복했다(같은 LiveSession[] 소비 형제).
// sort: 시작 시각 desc(기본) / 상태 active-first 토글. 정렬은 클라이언트에서만 한다.

import { useMemo, useState } from "react";
import { ArrowUpDown } from "lucide-react";

import { StateBox } from "@/components/state-box";
import { CHIP_TONE_CLASS } from "@/lib/labels";

import { LIVE_SESSION_STATUS_LABEL } from "../labels";
import type { LiveSession } from "../schemas";

type SortMode = "recent" | "active";

interface LiveSessionTableProps {
  sessions: readonly LiveSession[];
  // 부모가 strategy/account display name 매핑 책임.
  resolveStrategyName?: (id: string) => string;
  resolveExchangeLabel?: (id: string) => string;
}

export function LiveSessionTable({
  sessions,
  resolveStrategyName,
  resolveExchangeLabel,
}: LiveSessionTableProps) {
  const [sortMode, setSortMode] = useState<SortMode>("recent");

  const sorted = useMemo(() => {
    const copy = [...sessions];
    if (sortMode === "recent") {
      copy.sort((a, b) => b.created_at.localeCompare(a.created_at));
    } else {
      copy.sort((a, b) => {
        if (a.is_active === b.is_active) {
          return b.created_at.localeCompare(a.created_at);
        }
        return a.is_active ? -1 : 1;
      });
    }
    return copy;
  }, [sessions, sortMode]);

  if (sessions.length === 0) {
    return (
      <div className="card">
        <div className="card-body">
          <StateBox
            title="세션이 없습니다."
            body="아래 폼으로 라이브 세션을 시작하면 이 표에 나타납니다. 종료된 세션도 최근 20건까지 남습니다."
          />
        </div>
      </div>
    );
  }

  return (
    <div className="card" data-testid="live-session-table">
      <div className="card-head">
        <div>
          <h3 className="card-title">라이브 세션 ({sessions.length})</h3>
          <p className="card-sub">
            라이브 세션의 읽기 전용 요약입니다. 활성 세션과 최근 종료된 세션 20건을 함께 보여주고,
            상태 칩으로 구분합니다.
          </p>
        </div>
        <div className="chart-head-actions">
          <button
            type="button"
            onClick={() => setSortMode((m) => (m === "recent" ? "active" : "recent"))}
            className="btn btn-ghost btn-xs"
            data-testid="live-session-sort-toggle"
          >
            <ArrowUpDown aria-hidden="true" />
            {sortMode === "recent" ? "최신 시작순" : "활성 우선"}
          </button>
        </div>
      </div>
      <div className="table-wrap">
        <table className="trades" aria-label={`라이브 세션 ${sessions.length}건`}>
          <thead>
            <tr>
              <th scope="col">상태</th>
              <th scope="col">심볼</th>
              <th scope="col">전략</th>
              <th scope="col">인터벌</th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((s) => {
              // BL-572 — 라벨도 톤도 ../labels 의 SSOT 에서 읽는다. 여기서 문자열을 다시
              // 만들면 같은 세션을 목록 카드와 다른 이름으로 부르게 된다.
              const status = LIVE_SESSION_STATUS_LABEL[s.is_active ? "active" : "ended"];
              return (
                <tr key={s.id}>
                  <td>
                    <span className={CHIP_TONE_CLASS[status.tone]}>{status.label}</span>
                  </td>
                  <td className="mono-l">{s.symbol}</td>
                  <td>
                    {resolveStrategyName?.(s.strategy_id) ?? s.strategy_id.slice(0, 8)}
                    {resolveExchangeLabel ? (
                      <span className="dim"> · {resolveExchangeLabel(s.exchange_account_id)}</span>
                    ) : null}
                  </td>
                  <td className="mono-l dim">{s.interval}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
