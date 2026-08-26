"use client";

// [ADR-042] Pine AST 를 옮긴 **읽기 전용** Python 뷰.
//
// ★★이 코드는 실행되지 않는다. 화면이 그 사실을 **본문 위에서 먼저** 말해야 한다 —
//   Python 처럼 생긴 것을 보여 주면서 「실행됩니다」라고 오해할 여지를 남기면 안 된다.
// ★의미 보존을 보증하지 않는 **읽기용 근사**라 진실은 언제나 원본 Pine 이다. 그래서 왼쪽
//   거터에 **원본 Pine 줄번호**를 붙여 둔다 — 대응을 모르는 줄은 비운다(지어내지 않는다).

import { useMemo, useState } from "react";

import type { PythonView } from "@/features/strategy/schemas";

export function PythonViewPanel({ view }: { view: PythonView }) {
  const [open, setOpen] = useState(false);

  // source_map 은 `[python 줄, pine 줄]` 이고 python 줄은 1-based 다.
  const pineLineFor = useMemo(() => {
    const m = new Map<number, number>();
    for (const [py, pine] of view.source_map) {
      m.set(py, pine);
    }
    return m;
  }, [view.source_map]);

  const lines = useMemo(() => view.code.replace(/\n$/, "").split("\n"), [view.code]);

  if (!open) {
    return (
      <button type="button" className="btn btn-ghost btn-xs" onClick={() => setOpen(true)}>
        파이썬으로 보기
      </button>
    );
  }

  return (
    <div className="brief-section" data-testid="python-view">
      <div className="brief-verdict">
        <p className="metric-group-title">파이썬으로 보기</p>
        <button type="button" className="btn btn-ghost btn-xs" onClick={() => setOpen(false)}>
          접기
        </button>
      </div>

      {/* ★본문보다 먼저 온다 — 스크롤 없이 읽히는 자리여야 한다. */}
      <p className="strip-note" data-testid="python-view-disclaimer">
        <strong>실행되는 코드가 아닙니다.</strong> 원본 Pine 을 읽기 쉽게 옮긴 것이고, 실제로 도는
        것은 Pine 인터프리터입니다. 왼쪽 숫자는 <strong>원본 Pine 의 줄번호</strong>입니다.
      </p>

      {view.unrendered > 0 ? (
        <p className="strip-note" data-testid="python-view-preserved">
          {`${view.unrendered}곳은 파이썬으로 옮기지 못해 원본 Pine 을 주석으로 남겼습니다.`} 지운
          것이 아니라 그대로 두었습니다.
        </p>
      ) : null}

      <div className="table-wrap">
        <pre className="python-view">
          <code>
            {lines.map((line, i) => {
              const pine = pineLineFor.get(i + 1);
              return (
                // biome-ignore lint/suspicious/noArrayIndexKey: 줄 번호가 곧 정체성인 정적 목록이다.
                <span className="python-view-line" key={`${i}-${line}`}>
                  <span className="python-view-gutter" aria-hidden="true">
                    {pine ?? ""}
                  </span>
                  <span className="python-view-code">{line || " "}</span>
                </span>
              );
            })}
          </code>
        </pre>
      </div>
    </div>
  );
}
