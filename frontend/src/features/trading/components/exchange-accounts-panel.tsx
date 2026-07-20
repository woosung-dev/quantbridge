"use client";

// 거래소 계정 패널 — C 디자인 언어 이식 (S8). 공용 .card/.trades/.state-box 시맨틱 CSS 를
// 소비한다. mode(demo/live) 는 EXECUTION_MODE 축이라 칩 톤으로 표기하되 data-tone 을 유지해
// 시맨틱 어서션(리터럴 팔레트 금지)을 지킨다. 4상태(로딩/에러/빈/채움)를 실제로 렌더한다.

import { Trash2Icon, AlertTriangleIcon, InboxIcon, RefreshCwIcon } from "lucide-react";
import { toast } from "sonner";

import { EMPTY_CELL } from "@/lib/labels";

import { useDeleteExchangeAccount, useExchangeAccounts } from "../hooks";
import { RegisterExchangeAccountDialog } from "./register-exchange-account-dialog";

// Demo/Live 배지 — data-tone 은 globals.css [data-tone] 규칙이 색을 결정(리터럴 팔레트 금지).
function ModeBadge({ mode }: { mode: string | null | undefined }) {
  if (mode === "demo") {
    return (
      <span className="chip warn" data-tone="warning">
        DEMO
      </span>
    );
  }
  if (mode === "live") {
    return (
      <span className="chip done" data-tone="success">
        LIVE
      </span>
    );
  }
  return <span className="chip">{(mode ?? "UNKNOWN").toUpperCase()}</span>;
}

export function ExchangeAccountsPanel() {
  const { data, isError, isLoading, refetch } = useExchangeAccounts();
  const deleteAccount = useDeleteExchangeAccount();

  return (
    <div className="card">
      <div className="card-head">
        <div>
          <h3 className="card-title">거래소 계정</h3>
          <p className="card-sub">
            API 키는 AES-256 으로 암호화 저장되며 마스킹해 보여 줍니다.
          </p>
        </div>
        <div className="chart-head-actions">
          <RegisterExchangeAccountDialog />
        </div>
      </div>

      {isLoading || (!data && !isError) ? (
        <div className="card-body">
          <div
            className="sk"
            style={{ height: 80 }}
            aria-label="거래소 계정 불러오는 중"
          />
        </div>
      ) : isError ? (
        <div className="card-body">
          <div className="state-box failed" role="alert" data-testid="accounts-error">
            <span className="state-icon failed" aria-hidden="true">
              <AlertTriangleIcon />
            </span>
            <p className="state-title">거래소 계정 목록을 불러오지 못했습니다.</p>
            <p className="state-body">
              네트워크 또는 인증 문제가 있을 수 있습니다.
            </p>
            <p className="state-code">GET /api/v1/exchange-accounts</p>
            <button className="btn btn-ghost" type="button" onClick={() => refetch()}>
              <RefreshCwIcon aria-hidden="true" />
              다시 시도
            </button>
          </div>
        </div>
      ) : !data || data.length === 0 ? (
        <div className="card-body">
          <div className="state-box" role="status" data-testid="accounts-empty">
            <span className="state-icon" aria-hidden="true">
              <InboxIcon />
            </span>
            <p className="state-title">연결된 거래소 계정이 없습니다.</p>
            <p className="state-body">
              위 &lsquo;계정 추가&rsquo; 버튼으로 거래소 계정을 연결하세요.
            </p>
          </div>
        </div>
      ) : (
        <div className="table-wrap">
          <table className="trades" aria-label={`거래소 계정 ${data.length}개`}>
            <thead>
              <tr>
                <th scope="col">거래소</th>
                <th scope="col">모드</th>
                <th scope="col">라벨</th>
                <th scope="col">API 키</th>
                <th scope="col">액션</th>
              </tr>
            </thead>
            <tbody>
              {data.map((a) => (
                <tr key={a.id}>
                  <td className="mono-l">{a.exchange}</td>
                  <td>
                    <ModeBadge mode={a.mode} />
                  </td>
                  <td>{a.label ?? EMPTY_CELL}</td>
                  <td className="mono-l dim">{a.api_key_masked}</td>
                  <td>
                    <button
                      type="button"
                      className="btn btn-danger"
                      onClick={() =>
                        deleteAccount.mutate(a.id, {
                          onError: () => {
                            toast.error(
                              "거래소 계정 삭제에 실패했습니다. 잠시 후 다시 시도해 주세요.",
                            );
                          },
                        })
                      }
                      disabled={deleteAccount.isPending}
                      aria-label="계정 삭제"
                    >
                      <Trash2Icon aria-hidden="true" />
                      삭제
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
