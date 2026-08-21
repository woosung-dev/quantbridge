"use client";

// 전략 편집 — C 디자인 언어 이식 (screen-08). 단일 페이지: 헤더 + 01 소스(Monaco) +
// 02 진단(진짜 탭) + 03 실행 설정 + 04 메타데이터 + 05 Webhook. 편집 버퍼는 Zustand edit-store,
// 저장/되돌리기/삭제는 헤더에서 담당한다. 프로토타입 고정 실행 가정(수수료/슬리피지/체결 시점/
// 펀딩/마지막 백테스트)은 per-strategy 필드가 아니라 백테스트 시점 값이라 미렌더한다(§4.9).

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import {
  AlertTriangleIcon,
  CheckIcon,
  CopyIcon,
  PlayIcon,
  RotateCcwIcon,
  SaveIcon,
  Trash2Icon,
} from "lucide-react";
import { toast } from "sonner";

import {
  selectIsDirty,
  selectPineSource,
  selectStrategyId,
  useEditStore,
} from "@/features/strategy/edit-store";
import { useStrategy, useUpdateStrategy } from "@/features/strategy/hooks";
import { PARSE_STATUS_LABEL } from "@/features/strategy/labels";
import type { MarginMode } from "@/features/strategy/schemas";
import { formatDateTime } from "@/features/strategy/utils";
import { StateBox } from "@/components/state-box";
import { CHIP_TONE_CLASS, EMPTY_CELL } from "@/lib/labels";

import { DeleteDialog } from "./delete-dialog";
import { DiagnosticsStrip } from "./diagnostics-strip";
import { EditorMonacoWrapper } from "./editor-monaco-wrapper";
import { TabMetadata } from "./tab-metadata";
import { TabWebhook } from "./tab-webhook";

const MARGIN_MODE_LABEL: Record<MarginMode, string> = {
  cross: "교차 (Cross)",
  isolated: "격리 (Isolated)",
};
const EDITOR_META_SKELETON_KEYS = ["meta-1", "meta-2", "meta-3", "meta-4", "meta-5"] as const;
const EDITOR_SETTING_SKELETON_LINES = [
  { key: "setting-1", width: "72%", marginTop: 0 },
  { key: "setting-2", width: "64%", marginTop: 10 },
  { key: "setting-3", width: "56%", marginTop: 10 },
  { key: "setting-4", width: "48%", marginTop: 10 },
] as const;

export function EditorView({ id }: { id: string }) {
  const router = useRouter();
  const params = useSearchParams();
  const [deleteOpen, setDeleteOpen] = useState(
    params.get("action") === "delete" || params.get("action") === "archive",
  );

  const { data: strategy, isLoading, isError } = useStrategy(id);

  const storeStrategyId = useEditStore(selectStrategyId);
  const isDirty = useEditStore(selectIsDirty);
  const pineSource = useEditStore(selectPineSource);
  const setPineSource = useEditStore((s) => s.setPineSource);
  const loadServerSnapshot = useEditStore((s) => s.loadServerSnapshot);
  const markSaved = useEditStore((s) => s.markSaved);
  const resetDirty = useEditStore((s) => s.resetDirty);

  // 서버 strategy 로 store 초기화 (primitive dep 만, actions 는 불변 참조).
  const serverPineSource = strategy?.pine_source;
  const serverStrategyId = strategy?.id;
  useEffect(() => {
    if (serverStrategyId && typeof serverPineSource === "string") {
      if (storeStrategyId !== serverStrategyId) {
        loadServerSnapshot(serverStrategyId, serverPineSource);
      }
    }
  }, [serverStrategyId, serverPineSource, storeStrategyId, loadServerSnapshot]);

  // URL ?action=archive/delete — 마운트 후 param 변경도 render-time reset (H-1: set-state-in-effect 금지).
  const action = params.get("action");
  const actionRequested = action === "delete" || action === "archive";
  const [prevActionRequested, setPrevActionRequested] = useState(actionRequested);
  if (actionRequested !== prevActionRequested) {
    setPrevActionRequested(actionRequested);
    if (actionRequested) setDeleteOpen(true);
  }

  // ?tab=webhook 딥링크(생성 직후 진입) — webhook 섹션으로 스크롤.
  const webhookRef = useRef<HTMLElement | null>(null);
  const wantsWebhook = params.get("tab") === "webhook";
  useEffect(() => {
    if (wantsWebhook && webhookRef.current) {
      webhookRef.current.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }, [wantsWebhook, isLoading]);

  // isDirty 동안 tab close/refresh 경고.
  useEffect(() => {
    if (!isDirty) return;
    const handleBeforeUnload = (event: BeforeUnloadEvent) => event.preventDefault();
    window.addEventListener("beforeunload", handleBeforeUnload);
    return () => window.removeEventListener("beforeunload", handleBeforeUnload);
  }, [isDirty]);

  const update = useUpdateStrategy(id, {
    onSuccess: () => {
      markSaved(new Date());
      toast.success("저장했습니다");
    },
    onError: (e) => toast.error(`저장 실패: ${e.message}`),
  });

  const handleSave = () => {
    if (!isDirty || update.isPending) return;
    update.mutate({ pine_source: pineSource });
  };

  const handleCopySource = async () => {
    try {
      await navigator.clipboard.writeText(pineSource);
      toast.success("소스를 복사했습니다");
    } catch {
      toast.error("클립보드 복사 실패");
    }
  };

  if (isLoading) {
    return <EditorSkeleton />;
  }

  if (isError || !strategy) {
    return (
      <main className="page">
        <section className="card">
          <div className="card-body">
            <StateBox
              tone="failed"
              testId="strategy-not-found"
              icon={<AlertTriangleIcon />}
              title="전략을 찾을 수 없습니다."
              body="전략이 삭제되었거나 접근 권한이 없을 수 있습니다."
              code={`GET /api/v1/strategies/${id}`}
            >
              <Link className="btn btn-ghost" href="/strategies">
                전략 목록으로
              </Link>
            </StateBox>
          </div>
        </section>
      </main>
    );
  }

  const parseChip = PARSE_STATUS_LABEL[strategy.parse_status];
  const lineCount = pineSource.length === 0 ? 0 : pineSource.split("\n").length;
  const settings = strategy.settings ?? null;
  const sessions = strategy.trading_sessions ?? [];

  return (
    <main className="page">
      {/* ===== 헤더 ===== */}
      <section className="card" aria-label="전략 개요">
        <div className="report">
          <div>
            <h1 className="report-title">{strategy.name}</h1>
            <div className="report-meta">
              <span className="chip">{strategy.id.slice(0, 8)}</span>
              <span className={CHIP_TONE_CLASS[parseChip.tone]}>
                {parseChip.showCheckIcon ? <CheckIcon aria-hidden="true" /> : null}
                {parseChip.label}
              </span>
              <span className="chip">{strategy.symbol ?? EMPTY_CELL}</span>
              <span className="chip">{strategy.timeframe ?? EMPTY_CELL}</span>
              <span className="chip">Pine {strategy.pine_version}</span>
              {strategy.is_archived ? <span className="chip">보관됨</span> : null}
              {isDirty ? (
                <span className="chip warn" data-testid="unsaved-chip">
                  저장되지 않은 변경
                </span>
              ) : null}
            </div>
          </div>
          <div className="report-actions">
            <button
              className="btn btn-ghost"
              type="button"
              onClick={resetDirty}
              disabled={!isDirty}
            >
              <RotateCcwIcon aria-hidden="true" />
              되돌리기
            </button>
            <Link className="btn" href={`/backtests/new?strategy_id=${strategy.id}`}>
              <PlayIcon aria-hidden="true" />
              백테스트 실행
            </Link>
            <button
              className="btn btn-primary"
              type="button"
              onClick={handleSave}
              disabled={!isDirty || update.isPending}
              aria-busy={update.isPending || undefined}
            >
              <SaveIcon aria-hidden="true" />
              {update.isPending ? "저장 중" : "저장"}
            </button>
            <button className="btn btn-danger" type="button" onClick={() => setDeleteOpen(true)}>
              <Trash2Icon aria-hidden="true" />
              삭제
            </button>
          </div>
        </div>
      </section>

      {/* ===== 01 소스 ===== */}
      <section className="section" aria-label="Pine 소스">
        <header className="section-head">
          <p className="eyebrow">
            <span className="num">01</span> 소스
          </p>
          <h2 className="section-title">Pine 소스 {lineCount}줄</h2>
          <p className="section-desc">
            저장하면 이 소스를 다시 파싱하고, 배포된 데모 세션의 전략도 같은 소스로 교체됩니다.
          </p>
        </header>

        <div className="card">
          <div className="card-head">
            <div>
              <h3 className="card-title">Pine Script 원문</h3>
              <p className="card-sub">
                마지막 저장 {formatDateTime(strategy.updated_at)} · 바 단위 이벤트 루프
              </p>
            </div>
            <div className="toolbar">
              <button
                className="btn btn-ghost"
                type="button"
                onClick={handleCopySource}
                aria-label="소스 전체 복사"
              >
                <CopyIcon aria-hidden="true" />
                복사
              </button>
            </div>
          </div>

          <div className="card-body">
            <EditorMonacoWrapper
              fileName="strategy.pine"
              versionLabel={`Pine ${strategy.pine_version}`}
              value={pineSource}
              onChange={setPineSource}
              height={480}
            />
          </div>

          <p className="code-foot">
            Pine {strategy.pine_version} · {lineCount}줄 · UTF-8 · 편집 즉시 위 진단에서
            재파싱됩니다.
          </p>
        </div>
      </section>

      {/* ===== 02 진단 ===== */}
      <section className="section" aria-label="진단">
        <header className="section-head">
          <p className="eyebrow">
            <span className="num">02</span> 진단
          </p>
          <h2 className="section-title">저장 전 정적 분석</h2>
          <p className="section-desc">파싱 결과와 감지된 함수를 저장 전에 먼저 확인합니다.</p>
        </header>
        <DiagnosticsStrip strategy={strategy} />
      </section>

      {/* ===== 03 실행 설정 ===== */}
      <section className="section" aria-label="실행 설정">
        <header className="section-head">
          <p className="eyebrow">
            <span className="num">03</span> 실행 설정
          </p>
          <h2 className="section-title">이 전략에 저장된 실행 조건</h2>
          <p className="section-desc">
            백테스트와 데모 주문에 쓰이는 값입니다. 수수료와 슬리피지, 체결 시점 같은 실행 가정은
            전략이 아니라 백테스트를 실행할 때 정하므로 여기 표시하지 않습니다.
          </p>
        </header>

        <div className="card">
          <div className="trust-grid">
            <div className="trust-col">
              <div className="trust-row">
                <span className="trust-key">심볼</span>
                <span className="trust-val">{strategy.symbol ?? EMPTY_CELL}</span>
              </div>
              <div className="trust-row">
                <span className="trust-key">타임프레임</span>
                <span className="trust-val">{strategy.timeframe ?? EMPTY_CELL}</span>
              </div>
              <div className="trust-row">
                <span className="trust-key">거래소</span>
                <span className="trust-val">Bybit</span>
              </div>
              <div className="trust-row">
                <span className="trust-key">Pine 버전</span>
                <span className="trust-val">{strategy.pine_version}</span>
              </div>
              <div className="trust-row">
                <span className="trust-key">엔진</span>
                <span className="trust-val">바 단위 이벤트 루프</span>
              </div>
            </div>
            <div className="trust-col">
              <div className="trust-row">
                <span className="trust-key">레버리지</span>
                <span className="trust-val">
                  {settings ? (
                    `${settings.leverage}배`
                  ) : (
                    <span title="트레이딩 설정이 아직 등록되지 않았습니다.">{EMPTY_CELL}</span>
                  )}
                </span>
              </div>
              <div className="trust-row">
                <span className="trust-key">마진 모드</span>
                <span className="trust-val">
                  {settings ? (
                    MARGIN_MODE_LABEL[settings.margin_mode]
                  ) : (
                    <span title="트레이딩 설정이 아직 등록되지 않았습니다.">{EMPTY_CELL}</span>
                  )}
                </span>
              </div>
              <div className="trust-row">
                <span className="trust-key">포지션 크기</span>
                <span className="trust-val">
                  {settings ? (
                    `자본의 ${settings.position_size_pct}%`
                  ) : (
                    <span title="트레이딩 설정이 아직 등록되지 않았습니다.">{EMPTY_CELL}</span>
                  )}
                </span>
              </div>
              <div className="trust-row">
                <span className="trust-key">거래 세션</span>
                <span className="trust-val">
                  {sessions.length === 0 ? "제한 없음" : sessions.join(" · ")}
                </span>
              </div>
              <div className="trust-row">
                <span className="trust-key">펀딩 반영</span>
                <span className="trust-val">미반영</span>
              </div>
            </div>
          </div>
          <p className="disclaimer">
            <span>
              미지원 함수가 하나라도 있으면 부분 실행 없이 전체를 지원되지 않음으로 처리합니다.
              원문은 변환 없이 바 단위 이벤트 루프 엔진이 그대로 실행합니다.
            </span>
          </p>
        </div>
      </section>

      {/* ===== 04 메타데이터 ===== */}
      <section className="section" aria-label="메타데이터">
        <header className="section-head">
          <p className="eyebrow">
            <span className="num">04</span> 메타데이터
          </p>
          <h2 className="section-title">이름 · 심볼 · 태그 · 트레이딩 설정</h2>
          <p className="section-desc">전략의 표시 정보와 라이브 세션 파라미터를 수정합니다.</p>
        </header>
        <TabMetadata strategy={strategy} />
      </section>

      {/* ===== 05 Webhook ===== */}
      <section className="section" aria-label="Webhook" ref={webhookRef}>
        <header className="section-head">
          <p className="eyebrow">
            <span className="num">05</span> Webhook
          </p>
          <h2 className="section-title">외부 신호 수신 주소</h2>
          <p className="section-desc">
            TradingView alert 나 외부 시스템이 이 전략으로 신호를 보내는 주소와 secret 을
            관리합니다.
          </p>
        </header>
        <TabWebhook strategyId={strategy.id} />
      </section>

      <DeleteDialog
        open={deleteOpen}
        onOpenChange={setDeleteOpen}
        strategyId={strategy.id}
        strategyName={strategy.name}
        onDone={() => {
          toast.success("전략을 삭제했습니다");
          router.push("/strategies");
        }}
        onArchived={() => {
          toast.success("전략을 보관했습니다");
          setDeleteOpen(false);
          router.refresh();
        }}
      />
    </main>
  );
}

// 로딩 스켈레톤 — 로드 완료 레이아웃의 주요 블록(헤더 제목+칩 행 · 소스 에디터 프레임 ·
// 진단 스트립 · 실행 설정 그리드)의 자리를 예약해 레이아웃 점프를 줄인다
// (backtest-detail-view 의 DetailSkeleton 선례).
function EditorSkeleton() {
  return (
    <main className="page" aria-busy="true" data-testid="strategy-editor-skeleton">
      {/* 헤더 — 제목 줄 + 칩 행 */}
      <section className="card" aria-hidden="true">
        <div className="report">
          <div>
            <span className="sk" style={{ display: "block", width: 220, height: 32 }} />
            <div className="report-meta">
              {EDITOR_META_SKELETON_KEYS.map((key) => (
                <span
                  key={key}
                  className="sk"
                  style={{ display: "block", width: 74, height: 26 }}
                />
              ))}
            </div>
          </div>
        </div>
      </section>
      {/* 01 소스 — Monaco 프레임 자리. 에디터 본체 480 + 파일탭 toolbar 36 + 보더 2 ≈ 518
          (EditorMonacoWrapper 가 toolbar 를 얹으므로 480 만 예약하면 ~37px 점프가 남는다) */}
      <section className="section" aria-hidden="true">
        <div className="card">
          <div className="card-body">
            <span className="sk" style={{ display: "block", height: 518 }} />
          </div>
        </div>
      </section>
      {/* 02 진단 — 스트립 자리 */}
      <section className="section" aria-hidden="true">
        <div className="card">
          <div className="card-body">
            <span className="sk sk-line" style={{ width: "60%" }} />
          </div>
        </div>
      </section>
      {/* 03 실행 설정 — 그리드 카드 자리 */}
      <section className="section" aria-hidden="true">
        <div className="card">
          <div className="card-body">
            {EDITOR_SETTING_SKELETON_LINES.map((line) => (
              <span
                key={line.key}
                className="sk sk-line"
                style={{ width: line.width, marginTop: line.marginTop }}
              />
            ))}
          </div>
        </div>
      </section>
    </main>
  );
}
