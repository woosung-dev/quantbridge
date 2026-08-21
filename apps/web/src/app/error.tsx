"use client";
// 루트 에러 바운더리 — screen-13 §02(500) 의 C 언어 구조 이식(W3-H). 앱 셸 밖(app 루트)이라
// 공용 .page 컨테이너로 단독 렌더한다. 제네릭 바운더리라 실패 엔드포인트를 특정할 수 없어
// 프로토타입의 POST /backtests/.../rerun 경로는 인쇄하지 않는다(§4.9). 서버가 준 값만 그린다 —
// 상태 코드 500, 발생 시각(렌더 시각), 요청 ID(error.digest, 없으면 무데이터 셀).
// HTTP 재시도는 리로드일 뿐 트레이딩 주문 재시도(3회 · 지수 백오프)와 다른 개념이라 섞지 않는다(§4.7).

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { toast } from "sonner";
import { HomeIcon, RefreshCwIcon, TriangleAlertIcon } from "lucide-react";

import { StateBox } from "@/components/state-box";
import { InfoIcon } from "@/components/info-icon";
import { EMPTY_CELL } from "@/lib/labels";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("[GlobalError]", error);
  }, [error]);

  // digest 가 있으면 서버 로그 검색 키(요청 ID)로 노출. 없으면 무데이터 셀 — 지어내지 않는다.
  const requestId = error.digest ?? "";
  // 발생 시각 — 렌더 시점 1회 고정(재렌더 흔들림 방지).
  const occurredAt = useMemo(() => formatNowKst(), []);
  // 복사 후 짧게 완료 라벨을 노출한다(무한 애니메이션 없이 상태만 바꾼다).
  const [hasCopied, setHasCopied] = useState(false);
  // "다시 시도" 는 reset() 이 즉시 언마운트할 수도 외부 fetch 가 또 실패할 수도 있어
  // 1.2s 안전판으로 로딩 라벨을 자동 해제한다.
  const [isRetrying, setIsRetrying] = useState(false);

  const handleRetry = () => {
    if (isRetrying) return;
    setIsRetrying(true);
    try {
      reset();
    } finally {
      window.setTimeout(() => setIsRetrying(false), 1200);
    }
  };

  const handleCopy = async () => {
    if (!requestId) return;
    try {
      if (typeof navigator !== "undefined" && navigator.clipboard) {
        await navigator.clipboard.writeText(requestId);
        toast.success("요청 ID를 복사했습니다", { description: requestId });
        setHasCopied(true);
        window.setTimeout(() => setHasCopied(false), 1600);
        return;
      }
      throw new Error("clipboard unavailable");
    } catch {
      toast.error("자동 복사를 못 했습니다", { description: requestId });
    }
  };

  const handleShowLog = () => {
    toast("백엔드 로그 확인 방법", {
      description: requestId
        ? `docker compose logs -f backend 에서 요청 ID ${requestId} 를 검색하면 이 요청의 스택 트레이스만 골라낼 수 있습니다.`
        : "docker compose logs -f backend 로 백엔드 로그를 확인할 수 있습니다.",
    });
  };

  return (
    <main className="page">
      <section className="section" aria-labelledby="err-500-heading">
        <header className="section-head">
          <p className="eyebrow">
            <span className="num">500</span> 서버 오류
          </p>
          <h1 id="err-500-heading" className="section-title">
            요청을 처리하지 못했습니다.
          </h1>
          <p className="section-desc">
            서버가 준 진단 정보만 인쇄합니다. 요청 ID 는 서버가 줄 때만 그리고, 값이 없으면 지어내지
            않고 없다고 표시합니다.
          </p>
        </header>

        <div className="card">
          <div className="card-head">
            <div>
              <h2 className="card-title">요청 처리 실패</h2>
              <p className="card-sub">요청은 서버에 도착했지만 처리 도중 중단되었습니다.</p>
            </div>
            <span className="chip">500</span>
          </div>

          <div className="card-body">
            <StateBox
              tone="failed"
              className="err-hero"
              testId="error-500-state"
              icon={<TriangleAlertIcon aria-hidden="true" />}
              title="서버 내부 오류로 요청을 처리하지 못했습니다."
              body="이 요청은 서버 내부에서 멈췄습니다. 잠시 후 다시 시도하고, 문제가 계속되면 아래 요청 ID 를 로그 검색에 사용하세요."
            />
          </div>

          <div className="trust-grid">
            <div className="trust-col">
              <div className="trust-row">
                <span className="trust-key">상태 코드</span>
                <span className="trust-val">500</span>
              </div>
              <div className="trust-row">
                <span className="trust-key">발생 시각</span>
                <span className="trust-val">{occurredAt}</span>
              </div>
            </div>
            <div className="trust-col">
              <div className="trust-row">
                <span className="trust-key">요청 ID</span>
                {requestId ? (
                  <span className="trust-val">
                    <span data-testid="error-request-id">{requestId}</span>
                    <button
                      type="button"
                      className="copy"
                      aria-label={hasCopied ? "요청 ID 복사 완료" : "요청 ID 복사"}
                      data-copied={hasCopied || undefined}
                      onClick={handleCopy}
                    >
                      {hasCopied ? "복사됨" : "복사"}
                    </button>
                  </span>
                ) : (
                  <span
                    className="trust-val empty"
                    title="서버가 요청 ID(digest)를 반환하지 않았습니다."
                    data-testid="error-request-id-empty"
                  >
                    {EMPTY_CELL}
                  </span>
                )}
              </div>
              <div className="trust-row">
                <span className="trust-key">요청 ID 용도</span>
                <span className="trust-val">서버 로그 검색 키</span>
              </div>
            </div>
          </div>

          <p className="chart-note">
            <InfoIcon />이 페이지는 시스템 전체 상태를 알지 못합니다. 상세 원인은 서버 로그에서
            확인하세요.
          </p>

          <div className="err-actions" role="group" aria-label="복구 동작">
            <button
              type="button"
              className="btn btn-primary"
              onClick={handleRetry}
              disabled={isRetrying}
              data-testid="error-retry-button"
              data-loading={isRetrying || undefined}
            >
              <RefreshCwIcon aria-hidden="true" />
              {isRetrying ? "다시 시도 중" : "다시 시도"}
            </button>
            <Link className="btn" href="/">
              <HomeIcon aria-hidden="true" />
              홈으로
            </Link>
            <button type="button" className="btn btn-ghost" onClick={handleShowLog}>
              로그 확인 방법
            </button>
          </div>
        </div>
      </section>
    </main>
  );
}

// 발생 시각 포맷 — KST 표기.
function formatNowKst(): string {
  const now = new Date();
  const pad = (n: number) => n.toString().padStart(2, "0");
  return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())} ${pad(now.getHours())}:${pad(now.getMinutes())}:${pad(now.getSeconds())} KST`;
}
