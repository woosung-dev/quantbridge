"use client";

import { memo } from "react";
import { CopyIcon } from "lucide-react";
import { toast } from "sonner";
import { selectPineSource, useEditStore } from "@/features/strategy/edit-store";
import type { StrategyResponse } from "@/features/strategy/schemas";
import { formatDateTime } from "@/features/strategy/utils";
import { EditorMonacoWrapper } from "./editor-monaco-wrapper";

// 타이핑 구독은 소스 영역에 한정한다. 부모의 저장·삭제 상태는 에디터를 다시 그리지 않는다.
export const EditorSourceSection = memo(function EditorSourceSection({
  strategy,
}: {
  strategy: StrategyResponse;
}) {
  const pineSource = useEditStore(selectPineSource);
  const setPineSource = useEditStore((s) => s.setPineSource);
  const lineCount = pineSource.length === 0 ? 0 : pineSource.split("\n").length;
  const handleCopySource = async () => {
    try {
      await navigator.clipboard.writeText(useEditStore.getState().pineSource);
      toast.success("소스를 복사했습니다");
    } catch {
      toast.error("클립보드 복사 실패");
    }
  };
  return (
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
          Pine {strategy.pine_version} · {lineCount}줄 · UTF-8 · 편집 즉시 위 진단에서 재파싱됩니다.
        </p>
      </div>
    </section>
  );
});
