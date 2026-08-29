"use client";

// 새 전략 만들기 — C 디자인 언어 이식 (screen-07). 프로토타입의 좌(기본정보 + Pine 소스) /
// 우(파싱 결과) 단일 페이지 레이아웃을 따른다. 이전 스텝 위저드(method/code/metadata step)는 폐기.
// 초기 자본 필드는 CreateStrategyRequest 에 대응 필드가 0건이라 렌더하지 않는다(§4.9).
// draft(localStorage) 복원과 create/parse 훅은 그대로 보존한다.

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { FileCode2Icon, FolderOpenIcon, InfoIcon, SaveIcon, SearchIcon } from "lucide-react";

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { PineEditor } from "@/components/monaco/pine-editor";
import { StateBox } from "@/components/state-box";
import { useAuthCtx } from "@/hooks/use-auth-ctx";
import { formatDateTime } from "@/features/backtest/utils";
import { useCreateStrategy, useParseStrategy, usePreviewParse } from "@/features/strategy/hooks";
import { handleMutationError } from "@/features/strategy/error-handler";
import { useDebouncedValue } from "@/features/strategy/utils";
import { PINE_FUNCTION_LEXICON } from "@/features/strategy/pine-lexicon";
import {
  clearOtherUsersDrafts,
  clearWizardDraft,
  saveWizardDraft,
  useAutoSaveDraft,
  useDraftSnapshot,
} from "@/features/strategy/draft";

import { GenerateWithAI } from "@/features/strategy/components/new/generate-with-ai";
import { ParseResultPanel } from "./parse-result-panel";

const SYMBOL_OPTIONS = ["BTC/USDT", "ETH/USDT", "SOL/USDT"] as const;
const TIMEFRAME_OPTIONS = ["15m", "1h", "4h", "1d"] as const;

// 지원 함수 사전(04 진단) — pine-lexicon 정적 상수를 삽입 순서대로 나열한다. 동기 데이터라
// 로딩/스켈레톤 상태가 없다(§4.9 가짜 로딩 금지). 실제 지원 여부 판정은 서버 파서가 한다.
const LEXICON_ENTRIES = Object.entries(PINE_FUNCTION_LEXICON);
// 레포 내 실존 예제 스크립트. apps/web/public/samples/ema-crossover.pine (정적 자산).
const EXAMPLE_PINE_URL = "/samples/ema-crossover.pine";

export function NewStrategyWizard() {
  const router = useRouter();
  const { userId } = useAuthCtx();

  const [name, setName] = useState("");
  const [symbol, setSymbol] = useState<string>(SYMBOL_OPTIONS[0]);
  const [timeframe, setTimeframe] = useState<string>(TIMEFRAME_OPTIONS[1]);
  const [description, setDescription] = useState("");
  const [pineSource, setPineSource] = useState("");

  // 파일 열기(로컬 파일 선택 → 소스 주입) + 예제 불러오기(정적 자산 fetch → 소스 주입).
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [exampleLoading, setExampleLoading] = useState(false);

  // Draft 복원 — render-time 에 localStorage 를 derive (LESSON-004, set-state-in-effect 금지).
  const availableDraft = useDraftSnapshot(userId);
  // 의미 있는 초안 = 원문 또는 이름이 있는 것. 자동 저장이 만드는 빈 초안(원문·이름 없음)은
  // 저장된 작업이 없는 것과 같으므로 04 진단 카드에서 빈 상태로 취급한다(복원 Dialog 와 같은 게이트).
  const hasMeaningfulDraft =
    availableDraft !== null &&
    (availableDraft.pineSource.trim().length > 0 || Boolean(availableDraft.metadata.name));
  const [promptDismissed, setPromptDismissed] = useState(false);
  const shouldPromptRestore = !promptDismissed && hasMeaningfulDraft;

  // ★복원 모달은 **이전 세션의** 초안에만 뜬다(BL-823). useDraftSnapshot 이 라이브 구독이라
  //   useAutoSaveDraft/수동 저장이 방금 쓴 「지금 세션의」 초안을 즉시 되읽는다 — 이 세션에서
  //   저장을 만들 수 있는 입력이 시작되면 게이트를 닫는다. 전부 이벤트 핸들러 안 setState 다
  //   (H-1: 구독 결과를 dep 로 갖는 effect 를 쓰면 dev 전용 무한 루프가 된다).
  const applyPineSource = (value: string) => {
    setPineSource(value);
    setPromptDismissed(true);
  };

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
    setPromptDismissed(true);
    toast.success("초안을 저장했습니다");
  };

  const handleOpenFile = () => fileInputRef.current?.click();

  const handleFileChange = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    event.target.value = ""; // 같은 파일 재선택 허용
    if (!file) return;
    try {
      const text = await file.text();
      applyPineSource(text);
      toast.success(`"${file.name}" 을 불러왔습니다`);
    } catch {
      toast.error("파일을 읽지 못했습니다");
    }
  };

  const handleLoadExample = async () => {
    setExampleLoading(true);
    try {
      const res = await fetch(EXAMPLE_PINE_URL);
      if (!res.ok) throw new Error(`샘플 응답 ${res.status}`);
      const text = await res.text();
      applyPineSource(text);
      toast.success("예제 스크립트를 불러왔습니다");
    } catch {
      toast.error("예제를 불러오지 못했습니다");
    } finally {
      setExampleLoading(false);
    }
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
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept=".pine,.txt,text/plain"
                    onChange={handleFileChange}
                    hidden
                    data-testid="pine-file-input"
                  />
                  <button className="btn btn-ghost" type="button" onClick={handleOpenFile}>
                    <FolderOpenIcon aria-hidden="true" />
                    파일 열기
                  </button>
                  <button
                    className="btn btn-ghost"
                    type="button"
                    onClick={handleLoadExample}
                    disabled={exampleLoading}
                  >
                    <FileCode2Icon aria-hidden="true" />
                    예제 불러오기
                  </button>
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
                    onChange={applyPineSource}
                    onTriggerParse={() => pineSource.trim() && manualParse.mutate(pineSource)}
                    height={360}
                  />
                </div>
              </div>

              <p className="disclaimer">
                <span>
                  실제 판정은 서버의 지원 함수 사전으로 결정되며, 원문은 변환 없이 바 단위 이벤트
                  루프 엔진이 그대로 실행합니다.
                </span>
              </p>
            </div>

            {/* [ADR-041] 자연어 → 전략 생성. ★결과는 **바로 저장되지 않는다** —
                `applyPineSource` 로 편집기에 넣을 뿐이고 판정은 위 03 파싱 결과가 다시 낸다. */}
            <GenerateWithAI symbol={symbol} timeframe={timeframe} onUsePine={applyPineSource} />
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
              indicatorCode={pineSource}
              onConverted={(result) => {
                applyPineSource(result.converted_code);
                if (result.warnings.length > 0) {
                  toast.info(result.warnings.join("\n"));
                }
              }}
            />
          </section>
        </div>
      </div>

      {/* ===== 04 진단 ===== */}
      <section className="section" aria-label="진단">
        <header className="section-head">
          <p className="eyebrow">
            <span className="num">04</span> 진단
          </p>
          <h2 className="section-title">준비 중이거나 비어 있는 항목</h2>
          <p className="section-desc">
            지원 함수 사전과 저장된 초안은 아직 준비되지 않았거나 비어 있는 상태도 감추지 않고
            그대로 보여줍니다.
          </p>
        </header>

        <div className="diag-2">
          {/* (a) 지원 함수 사전 — pine-lexicon 정적 목록 (backed) */}
          <article className="card diag" aria-label="지원 함수 사전">
            <div className="card-head">
              <div>
                <h3 className="card-title">지원 함수 사전</h3>
                <p className="card-sub">
                  바 단위 이벤트 루프가 해석하는 함수 {LEXICON_ENTRIES.length}종
                </p>
              </div>
            </div>
            <div className="card-body">
              <ul className="lexicon-list" data-testid="lexicon-list">
                {LEXICON_ENTRIES.map(([fnName, desc]) => (
                  <li key={fnName}>
                    <code className="mono">{fnName}</code>
                    <span>{desc.summary}</span>
                  </li>
                ))}
              </ul>
              <p className="state-note">
                <InfoIcon aria-hidden="true" />
                미지원 함수가 하나라도 있으면 부분 실행 없이 전체를 지원되지 않음으로 처리합니다.
              </p>
            </div>
          </article>

          {/* (b) 저장된 초안 — localStorage draft (이 브라우저에만 남음) */}
          <article className="card diag" aria-label="저장된 초안">
            <div className="card-head">
              <div>
                <h3 className="card-title">저장된 초안</h3>
                <p className="card-sub">이 브라우저에만 남습니다.</p>
              </div>
            </div>
            <div className="card-body">
              {hasMeaningfulDraft && availableDraft ? (
                <div className="draft-present" data-testid="draft-present">
                  <p className="draft-meta">
                    {formatDateTime(availableDraft.savedAt)}에 저장한 초안이 있습니다.
                    {availableDraft.metadata.name ? ` 이름 "${availableDraft.metadata.name}".` : ""}
                  </p>
                  <div className="draft-actions">
                    <button className="btn btn-ghost btn-xs" type="button" onClick={handleRestore}>
                      이어서 작성
                    </button>
                    <button
                      className="btn btn-ghost btn-xs"
                      type="button"
                      onClick={handleSaveDraft}
                    >
                      <SaveIcon aria-hidden="true" />
                      지금 다시 저장
                    </button>
                  </div>
                </div>
              ) : (
                <StateBox
                  testId="draft-empty"
                  icon={<SaveIcon />}
                  title="저장된 초안이 없습니다."
                  body="지금 입력한 내용을 초안으로 두면 파싱 검사에 실패해도 원문이 남습니다."
                >
                  <button className="btn btn-ghost" type="button" onClick={handleSaveDraft}>
                    <SaveIcon aria-hidden="true" />
                    현재 입력을 초안으로 저장
                  </button>
                </StateBox>
              )}
            </div>
          </article>
        </div>
      </section>

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
                `${formatDateTime(availableDraft.savedAt)}에 작성 중이던 초안이 있습니다.`}
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
