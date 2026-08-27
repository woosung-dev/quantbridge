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

  // ★버튼을 두 상태에서 **계속 마운트**한다. 조기 반환으로 버튼을 갈아치우면 누른 순간
  //   그 엘리먼트가 사라져 포커스가 <body> 로 유실되고, 키보드 사용자는 문서 처음으로 튕긴다.
  return (
    <div className="brief-section" data-testid="python-view">
      <div className="brief-verdict">
        <p className="metric-group-title">파이썬으로 보기</p>
        <button
          type="button"
          className="btn btn-ghost btn-xs"
          aria-expanded={open}
          aria-controls="python-view-body"
          onClick={() => setOpen((v) => !v)}
        >
          {open ? "접기" : "펼치기"}
        </button>
      </div>
      <div id="python-view-body" hidden={!open}>
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

        {/* ★가로 스크롤 영역은 키보드로도 스크롤돼야 한다(WCAG 2.1.1 · 기법 G202) — 그러려면
            스크롤하는 요소가 포커스를 받아야 한다. `role="region"` 을 흉내 내는 대신 시맨틱
            `<section>` 을 쓰고 스크롤을 그쪽으로 옮긴다(Biome useSemanticElements 권고). */}
        {/* biome-ignore lint/a11y/noNoninteractiveTabindex: 위 근거 — 스크롤 영역은 포커스 가능해야 한다. */}
        <section className="table-wrap" tabIndex={0} aria-label="파이썬 뷰 코드">
          <pre className="python-view">
            <code>
              {lines.map((line, i) => {
                const pine = pineLineFor.get(i + 1);
                return (
                  // biome-ignore lint/suspicious/noArrayIndexKey: 줄 번호가 곧 정체성인 정적 목록이다.
                  <span className="python-view-line" key={`${i}-${line}`}>
                    {/* ★안내문이 「왼쪽 숫자는 원본 Pine 줄번호」라고 말하는데 aria-hidden 이면
                      스크린리더에는 그 숫자가 존재하지 않는다. 이 뷰의 신뢰 장치가 바로 이 대응이다. */}
                    <span className="python-view-gutter">
                      {pine ? <span className="sr-only">원본 {pine}행 </span> : null}
                      <span aria-hidden="true">{pine ?? ""}</span>
                    </span>
                    <span className="python-view-code">{line || " "}</span>
                  </span>
                );
              })}
            </code>
          </pre>
        </section>
      </div>
    </div>
  );
}
