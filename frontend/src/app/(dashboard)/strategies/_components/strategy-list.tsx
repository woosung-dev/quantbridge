"use client";

// 전략 목록 — C 디자인 언어 이식 (screen-06). 프로토타입의 시맨틱 CSS(.trades/.chip/.state-box)를
// 소비하되, 열은 실데이터(StrategyListItem)가 받치는 것만 그린다. 프로토타입의 성과 3칸
// (최근 수익률/MDD/샤프)·파라미터 수·백테스트 건수·수명주기 칩(초안/검증됨/배포됨)은 스키마에
// 필드가 0건이라 렌더하지 않는다 (캐논 §4.9 "데이터 모델에 없는 값 = 가짜 데이터").
// 상태 열은 실존 필드 parse_status 를 PARSE_STATUS_LABEL → CHIP_TONE_CLASS 로 파생한다.

import Link from "next/link";
import { useMemo } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { AlertTriangleIcon, CheckIcon, InboxIcon, PlusIcon, RefreshCwIcon } from "lucide-react";

import {
  PARSE_STATUS_FILTER_LABEL,
  PARSE_STATUS_LABEL,
  STRATEGY_LIST_HEADER,
  type ParseStatusFilter,
} from "@/features/strategy/labels";
import { useStrategies } from "@/features/strategy/hooks";
import type { ParseStatus, StrategyListItem, StrategyListQuery } from "@/features/strategy/schemas";
import { formatDateTime } from "@/features/strategy/utils";
import { StateBox } from "@/components/state-box";
import { CHIP_TONE_CLASS, EMPTY_CELL } from "@/lib/labels";

const PAGE_SIZE = 20;
// 목록 조회 엔드포인트 — 에러 상태에 실제 경로를 노출한다 (프로토타입 state-code 관례).
const LIST_ENDPOINT = "GET /api/v1/strategies";

// parse_status 필터 옵션. 프로토타입 상태 필터(수명주기)가 unbacked 라 실존 필드로 대체한다.
const STATUS_FILTERS: ReadonlyArray<{ id: ParseStatusFilter }> = [
  { id: "all" },
  { id: "ok" },
  { id: "unsupported" },
  { id: "error" },
];

export function StrategyList() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();

  const statusParam = searchParams.get("parse_status") ?? "all";
  const activeStatus: ParseStatusFilter = STATUS_FILTERS.some((f) => f.id === statusParam)
    ? (statusParam as ParseStatusFilter)
    : "all";

  // BE 는 목록에서 부분 페이지만 반환하므로 client-side filter (현재 페이지 한정).
  // hook query 는 페이지네이션만 → queryKey identity 유지 (H-2 정합).
  const query = useMemo<StrategyListQuery>(
    () => ({ limit: PAGE_SIZE, offset: 0, is_archived: false }),
    [],
  );
  const { data, isLoading, isError, error, refetch } = useStrategies(query);

  // useMemo dep 안정성을 위해 items reference 자체를 memoize (H-1 정합 — RQ data 직접 dep 금지).
  const items = useMemo<readonly StrategyListItem[]>(() => data?.items ?? [], [data?.items]);
  const total = data?.total ?? 0;
  const hasMorePages = total > items.length;
  const filtered =
    activeStatus === "all" ? items : items.filter((s) => s.parse_status === activeStatus);
  const counts = useMemo(() => buildParseStatusCounts(items), [items]);

  const pushStatus = (id: ParseStatusFilter) => {
    const params = new URLSearchParams(searchParams.toString());
    if (id === "all") params.delete("parse_status");
    else params.set("parse_status", id);
    const qs = params.toString();
    router.replace(qs ? `${pathname}?${qs}` : pathname);
  };

  // 헤더 라벨은 스칼라로 푼다. STRATEGY_LIST_HEADER.status 는 헤더 문자열이지만
  // no-raw-enum-labels 가드가 `.status` 로 끝나는 JSX 멤버 체인을 잡으므로 우회한다.
  const {
    name: hName,
    status: hStatus,
    symbolTimeframe: hSymbolTf,
    updatedAt: hUpdatedAt,
    action: hAction,
  } = STRATEGY_LIST_HEADER;

  return (
    <main className="page">
      {/* ===== 목록 헤더 카드 ===== */}
      <section className="card" aria-label="전략 목록 개요">
        <div className="report">
          <div>
            <h1 className="report-title">전략</h1>
            <div className="report-meta">
              <span className="chip">{total}개</span>
              <span className="chip accent">바 단위 이벤트 루프</span>
              <span className="chip">Bybit</span>
            </div>
          </div>
          <div className="report-actions">
            <button className="btn" type="button" onClick={() => refetch()}>
              <RefreshCwIcon aria-hidden="true" />
              목록 새로고침
            </button>
            <Link className="btn btn-primary" href="/strategies/new">
              <PlusIcon aria-hidden="true" />새 전략
            </Link>
          </div>
        </div>
      </section>

      {/* ===== 01 목록 ===== */}
      <section className="section" aria-label="전략 목록">
        <header className="section-head">
          <p className="eyebrow">
            <span className="num">01</span> 목록
          </p>
          <h2 className="section-title">전략 {total}개</h2>
          <p className="section-desc">
            마지막 수정이 최근인 순서로 정렬했습니다. 심볼과 주기는 그 전략에 저장된 기본값입니다.
          </p>
        </header>

        <div className="card">
          <div className="card-head">
            <div>
              <h3 className="card-title">전략 목록</h3>
              <p className="card-sub">
                {items.length}개 표시{hasMorePages ? ` · 전체 ${total}개 중` : ""}
              </p>
            </div>
            <div className="chart-head-actions">
              <div className="tabs" role="group" aria-label="파싱 상태 필터">
                {STATUS_FILTERS.map((f) => {
                  const active = f.id === activeStatus;
                  const isDisabled = hasMorePages && f.id !== "all";
                  return (
                    <button
                      key={f.id}
                      type="button"
                      className={"tab" + (active ? " active" : "")}
                      aria-pressed={active}
                      aria-disabled={isDisabled || undefined}
                      disabled={isDisabled}
                      title={
                        isDisabled
                          ? "현재 페이지(20개)만 필터되므로 비활성화됩니다. Beta 에 서버 필터 추가 예정"
                          : undefined
                      }
                      data-testid={`strategy-filter-${f.id}`}
                      onClick={() => {
                        if (isDisabled) return;
                        pushStatus(f.id);
                      }}
                    >
                      {PARSE_STATUS_FILTER_LABEL[f.id]}
                    </button>
                  );
                })}
              </div>
            </div>
          </div>

          {/* total 은 BE 전역 건수지만 상태 분해는 client-side counts 라 현재 페이지(≤20)만
              반영한다. 페이지가 더 있으면 '이 페이지 기준' 을 붙여 전역 집계로 오인하지 않게 한다. */}
          <p className="runs-summary">
            <span className="mono">{total}</span>개 · {hasMorePages ? "이 페이지 기준 " : ""}
            변환 가능 <span className="mono">{counts.ok}</span> · 일부 미지원{" "}
            <span className="mono">{counts.unsupported}</span> · 오류{" "}
            <span className="mono">{counts.error}</span>
          </p>
          {hasMorePages ? (
            <p className="runs-summary" data-testid="strategy-filter-notice">
              현재 페이지(20개)만 필터됩니다. Beta 에 서버 필터가 추가될 예정입니다.
            </p>
          ) : null}

          {isLoading ? (
            <ListSkeleton />
          ) : isError ? (
            <div className="card-body">
              <StateBox
                tone="failed"
                testId="strategy-error"
                icon={<AlertTriangleIcon />}
                title="목록을 불러오지 못했습니다."
                body={error ? error.message : "네트워크 또는 서버 상태 일시적 오류일 수 있습니다."}
                code={LIST_ENDPOINT}
              >
                <button className="btn btn-ghost" type="button" onClick={() => refetch()}>
                  <RefreshCwIcon aria-hidden="true" />
                  다시 시도
                </button>
              </StateBox>
            </div>
          ) : filtered.length === 0 ? (
            <div className="card-body">
              <StateBox
                testId="strategy-empty"
                icon={<InboxIcon />}
                title={items.length === 0 ? "첫 전략을 등록하세요" : "해당 상태의 전략이 없습니다"}
                body={
                  items.length === 0
                    ? "TradingView Pine Script 를 붙여넣으면 파싱 검사 후 전략으로 저장됩니다."
                    : "다른 상태를 선택하거나 새 전략을 등록하세요."
                }
              >
                {items.length === 0 ? (
                  <Link className="btn btn-primary btn-xs" href="/strategies/new">
                    새 전략 등록
                  </Link>
                ) : (
                  <button
                    className="btn btn-ghost btn-xs"
                    type="button"
                    onClick={() => pushStatus("all")}
                  >
                    전체 보기
                  </button>
                )}
              </StateBox>
            </div>
          ) : (
            <div className="table-wrap">
              <table className="trades runs-table" aria-label={`전략 목록 ${filtered.length}개`}>
                <thead>
                  <tr>
                    <th scope="col">{hName}</th>
                    <th scope="col" className="col-status">
                      {hStatus}
                    </th>
                    <th scope="col">{hSymbolTf}</th>
                    <th scope="col">{hUpdatedAt}</th>
                    <th scope="col">{hAction}</th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.map((s) => {
                    // 라벨·톤은 W1 용어 SSOT 에서만 온다 (원시 enum 렌더 금지 — no-raw-enum-labels 가드).
                    const { label, tone, showCheckIcon } = PARSE_STATUS_LABEL[s.parse_status];
                    return (
                      <tr
                        key={s.id}
                        data-testid={`strategy-row-${s.id}`}
                        data-status={s.parse_status}
                      >
                        <td>
                          <Link className="strat-name" href={`/strategies/${s.id}/edit`}>
                            {s.name}
                          </Link>
                          <span className="strat-id">{s.id.slice(0, 8)}</span>
                        </td>
                        <td className="col-status">
                          <span className={CHIP_TONE_CLASS[tone]}>
                            {showCheckIcon ? <CheckIcon aria-hidden="true" /> : null}
                            {label}
                          </span>
                        </td>
                        {/* 무데이터 셀 — 심볼·주기가 전략에 저장돼 있지 않으면 EMPTY_CELL 로 표기한다. */}
                        <td className="mono-l">
                          {s.symbol || s.timeframe ? (
                            <>
                              {s.symbol ?? EMPTY_CELL} · {s.timeframe ?? EMPTY_CELL}
                            </>
                          ) : (
                            <span title="이 전략에는 심볼과 주기가 저장돼 있지 않습니다.">
                              {EMPTY_CELL}
                            </span>
                          )}
                        </td>
                        <td className="mono-l dim">{formatDateTime(s.updated_at)}</td>
                        <td>
                          <Link className="btn btn-ghost btn-xs" href={`/strategies/${s.id}/edit`}>
                            편집
                          </Link>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </section>
    </main>
  );
}

function buildParseStatusCounts(items: readonly StrategyListItem[]) {
  const result: Record<ParseStatus, number> = { ok: 0, unsupported: 0, error: 0 };
  for (const s of items) result[s.parse_status] += 1;
  return result;
}

// 다음 페이지를 불러오는 동안의 스켈레톤 — 프로토타입 aria-busy tbody 관례 (.sk .sk-cell).
function ListSkeleton() {
  return (
    <div className="table-wrap" data-testid="strategy-skeleton" aria-hidden="true">
      <table className="trades runs-table">
        <tbody>
          {Array.from({ length: 6 }).map((_, i) => (
            <tr key={i}>
              {Array.from({ length: 5 }).map((__, j) => (
                <td key={j}>
                  <span className="sk sk-cell" />
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
