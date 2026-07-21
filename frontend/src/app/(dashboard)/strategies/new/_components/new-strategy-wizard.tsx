"use client";

// 새 전략 만들기 — C 디자인 언어 이식 (screen-07). 프로토타입의 좌(기본정보 + Pine 소스) /
// 우(파싱 결과) 단일 페이지 레이아웃을 따른다. 이전 스텝 위저드(method/code/metadata step)는 폐기.
// 초기 자본 필드는 CreateStrategyRequest 에 대응 필드가 0건이라 렌더하지 않는다(§4.9).
// draft(localStorage) 복원과 create/parse 훅은 그대로 보존한다.

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@clerk/nextjs";
import { toast } from "sonner";
import { SaveIcon, SearchIcon } from "lucide-react";

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { PineEditor } from "@/components/monaco/pine-editor";
import { useCreateStrategy, useParseStrategy, usePreviewParse } from "@/features/strategy/hooks";
import { handleMutationError } from "@/features/strategy/error-handler";
import { useDebouncedValue } from "@/features/strategy/utils";
import {
  clearOtherUsersDrafts,
  clearWizardDraft,
  saveWizardDraft,
  useAutoSaveDraft,
  useDraftSnapshot,
} from "@/features/strategy/draft";

import { ParseResultPanel } from "./parse-result-panel";

const SYMBOL_OPTIONS = ["BTC/USDT", "ETH/USDT", "SOL/USDT"] as const;
const TIMEFRAME_OPTIONS = ["15m", "1h", "4h", "1d"] as const;

export function NewStrategyWizard() {
  const router = useRouter();
  const { userId } = useAuth();

  const [name, setName] = useState("");
  const [symbol, setSymbol] = useState<string>(SYMBOL_OPTIONS[0]);
  const [timeframe, setTimeframe] = useState<string>(TIMEFRAME_OPTIONS[1]);
  const [description, setDescription] = useState("");
  const [pineSource, setPineSource] = useState("");

  // Draft 복원 — render-time 에 localStorage 를 derive (LESSON-004, set-state-in-effect 금지).
  const availableDraft = useDraftSnapshot(userId);
  const [promptDismissed, setPromptDismissed] = useState(false);
  const shouldPromptRestore =
    !promptDismissed &&
    availableDraft !== null &&
    (availableDraft.pineSource.trim().length > 0 || Boolean(availableDraft.metadata.name));

  // 계정 전환 대비 — 다른 userId 의 잔여 draft 를 best-effort 로 정리.
  useEffect(() => {
    if (!userId) return;
    clearOtherUsersDrafts(userId);
  }, [userId]);

  useAutoSaveDraft(userId, {
    method: "direct",
    pineSource,
    metadata: { name, description, symbol, timeframe },
  });

  // 파싱 — debounce 후 자동(useQuery, StrictMode 안전) + ⌘+Enter 수동(mutation).
  const debounced = useDebouncedValue(pineSource, 300);
  const autoParse = usePreviewParse(debounced);
  const manualParse = useParseStrategy();
  const parseResult = manualParse.data ?? autoParse.data ?? null;
  const parseLoading = manualParse.isPending || autoParse.isFetching;
  const parseError = (manualParse.error ?? autoParse.error)?.message ?? null;

  const create = useCreateStrategy();

  const trimmedName = name.trim();
  const canSave =
    trimmedName.length > 0 &&
    pineSource.trim().length > 0 &&
    parseResult?.status === "ok" &&
    parseResult.unsupported_builtins.length === 0;

  const handleSave = () => {
    if (!canSave || create.isPending) return;
    create.mutate(
      {
        name: trimmedName,
        description: description.trim() ? description.trim() : null,
        symbol: symbol || null,
        timeframe: timeframe || null,
        tags: [],
        pine_source: pineSource,
      },
      {
        onSuccess: (data) => {
          clearWizardDraft(userId);
          toast.success(`"${data.name}" 전략이 생성되었습니다`);
          // Sprint 14 Phase A: webhook plaintext 1회 노출을 위해 편집 화면 webhook 컨텍스트로 진입.
          router.push(`/strategies/${data.id}/edit?tab=webhook`);
        },
        onError: (err) => handleMutationError(err),
      },
    );
  };

  const handleSaveDraft = () => {
    saveWizardDraft(userId, {
      method: "direct",
      pineSource,
      metadata: { name, description, symbol, timeframe },
    });
    toast.success("초안을 저장했습니다");
  };

  const handleRestore = () => {
    if (availableDraft) {
      setPineSource(availableDraft.pineSource);
      if (availableDraft.metadata.name) setName(availableDraft.metadata.name);
      if (availableDraft.metadata.description) setDescription(availableDraft.metadata.description);
      if (availableDraft.metadata.symbol) setSymbol(availableDraft.metadata.symbol);
      if (availableDraft.metadata.timeframe) setTimeframe(availableDraft.metadata.timeframe);
    }
    setPromptDismissed(true);
  };

  const handleDiscardDraft = () => {
    clearWizardDraft(userId);
    setPromptDismissed(true);
  };

  return (
    <main className="page">
      {/* ===== 화면 헤더 ===== */}
      <section className="card" aria-label="새 전략 개요">
        <div className="report">
          <div>
            <h1 className="report-title">새 전략</h1>
            <div className="report-meta">
              <span className="chip">{symbol}</span>
              <span className="chip">{timeframe}</span>
              <span className="chip">Bybit</span>
              <span className="chip accent">바 단위 이벤트 루프</span>
            </div>
          </div>
          <div className="report-actions">
            <Link className="btn btn-ghost" href="/strategies">
              취소
            </Link>
            <button className="btn" type="button" onClick={handleSaveDraft}>
              <SaveIcon aria-hidden="true" />
              초안 저장
            </button>
          </div>
        </div>
      </section>

      <div className="create-grid">
        {/* ============ 좌: 입력 ============ */}
        <div className="create-col">
          {/* ===== 01 기본 정보 ===== */}
          <section className="section" aria-label="기본 정보">
            <header className="section-head">
              <p className="eyebrow">
                <span className="num">01</span> 기본 정보
              </p>
              <h2 className="section-title">전략 메타데이터</h2>
              <p className="section-desc">
                여기서 고른 심볼과 타임프레임이 백테스트와 주문에 그대로 쓰입니다.
              </p>
            </header>

            <div className="card">
              <div className="card-body">
                <div className="field-grid">
                  <div className="field span-2">
                    <label className="field-label" htmlFor="f-name">
                      전략 이름
                    </label>
                    <input
                      className="input"
                      id="f-name"
                      type="text"
                      maxLength={120}
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      placeholder="예: MA Crossover Strategy"
                    />
                    <span className="field-hint">목록과 리포트 제목에 그대로 표시됩니다.</span>
                  </div>

                  <div className="field">
                    <label className="field-label" htmlFor="f-symbol">
                      심볼
                    </label>
                    <select
                      className="select"
                      id="f-symbol"
                      value={symbol}
                      onChange={(e) => setSymbol(e.target.value)}
                    >
                      {SYMBOL_OPTIONS.map((s) => (
                        <option key={s} value={s}>
                          {s}
                        </option>
                      ))}
                    </select>
                    <span className="field-hint">연결된 거래소는 Bybit 하나입니다.</span>
                  </div>

                  <div className="field">
                    <label className="field-label" htmlFor="f-tf">
                      타임프레임
                    </label>
                    <select
                      className="select"
                      id="f-tf"
                      value={timeframe}
                      onChange={(e) => setTimeframe(e.target.value)}
                    >
                      {TIMEFRAME_OPTIONS.map((t) => (
                        <option key={t} value={t}>
                          {t}
                        </option>
                      ))}
                    </select>
                    <span className="field-hint">봉 하나가 곧 인터프리터의 한 스텝입니다.</span>
                  </div>

                  <div className="field span-2">
                    <label className="field-label" htmlFor="f-desc">
                      설명
                    </label>
                    <textarea
                      className="textarea"
                      id="f-desc"
                      maxLength={2000}
                      value={description}
                      onChange={(e) => setDescription(e.target.value)}
                      placeholder="이 전략으로 검증하려는 가설을 적어 두면 나중에 결과와 비교하기 쉽습니다."
                    />
                    <span className="field-hint">선택 항목입니다. 나중에 수정할 수 있습니다.</span>
                  </div>
                </div>
              </div>
            </div>
          </section>

          {/* ===== 02 Pine 소스 ===== */}
          <section className="section" aria-label="Pine 소스">
            <header className="section-head">
              <p className="eyebrow">
                <span className="num">02</span> Pine 소스
              </p>
              <h2 className="section-title">스크립트 붙여넣기</h2>
              <p className="section-desc">
                TradingView 에서 복사한 Pine 원문을 그대로 붙여넣습니다. 변환하지 않고 원문을
                보관합니다.
              </p>
            </header>

            <div className="card">
              <div className="card-head">
                <div>
                  <h3 className="card-title">Pine Script 원문</h3>
                  <p className="card-sub">바 단위 이벤트 루프 · ⌘+Enter 로 즉시 파싱</p>
                </div>
                <div className="toolbar">
                  <button
                    className="btn btn-primary"
                    type="button"
                    onClick={() => pineSource.trim() && manualParse.mutate(pineSource)}
                    disabled={pineSource.trim().length === 0}
                  >
                    <SearchIcon aria-hidden="true" />
                    파싱 검사
                  </button>
                </div>
              </div>

              <div className="card-body">
                <div className="editor-shell">
                  <PineEditor
                    value={pineSource}
                    onChange={setPineSource}
                    onTriggerParse={() => pineSource.trim() && manualParse.mutate(pineSource)}
                    height={360}
                  />
                </div>
              </div>

              <p className="disclaimer">
                <span>
                  실제 판정은 서버의 지원 함수 사전으로 결정되며, 원문은 변환 없이 바 단위 이벤트 루프
                  엔진이 그대로 실행합니다.
                </span>
              </p>
            </div>
          </section>
        </div>

        {/* ============ 우: 파싱 결과 ============ */}
        <div className="create-col">
          <section className="section" aria-label="파싱 결과">
            <header className="section-head">
              <p className="eyebrow">
                <span className="num">03</span> 파싱 결과
              </p>
              <h2 className="section-title">지원 여부 판정</h2>
              <p className="section-desc">
                붙여넣은 스크립트를 서버가 파싱해 지원 여부를 판정합니다.
              </p>
            </header>

            <ParseResultPanel
              result={parseResult}
              loading={parseLoading}
              error={parseError}
              onSave={handleSave}
              saving={create.isPending}
              canSave={canSave}
            />
          </section>
        </div>
      </div>

      {/* Draft 복원 Dialog */}
      <Dialog
        open={shouldPromptRestore}
        onOpenChange={(open) => {
          if (!open) setPromptDismissed(true);
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>이어서 작성하시겠어요?</DialogTitle>
            <DialogDescription>
              {availableDraft &&
                `${new Date(availableDraft.savedAt).toLocaleString("ko-KR")}에 작성 중이던 초안이 있습니다.`}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <button className="btn btn-ghost" type="button" onClick={handleDiscardDraft}>
              새로 시작
            </button>
            <button className="btn btn-primary" type="button" onClick={handleRestore}>
              이어서 작성
            </button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </main>
  );
}
