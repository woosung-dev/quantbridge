// 상태 박스 크로스페이지 프리미티브 (S9 추출) — 에러/빈 상태의 .state-box 골격.
// S5·S6·S7·S8 이 같은 구조(state-icon + state-title + state-body + 선택 state-code + 액션)를
// 반복 렌더했다(LESSON-063 크로스페이지 프리미티브 우회). 마크업을 한 곳으로 모은다.
// DOM(클래스·role·testid)은 기존과 바이트 동일하게 보존한다 — tone=failed 는 role=alert +
// state-box/state-icon 에 failed 를 붙이고, 그 외(neutral)는 role=status 다.

import type { ReactNode } from "react";

interface StateBoxProps {
  /** neutral = 빈/무데이터(state-box · role=status), failed = 에러(state-box failed · role=alert). */
  tone?: "neutral" | "failed";
  /** 아이콘 엘리먼트. 넘기면 state-icon 래퍼로 감싼다. 생략하면 아이콘 없는 안내 박스. */
  icon?: ReactNode;
  title: ReactNode;
  body?: ReactNode;
  /** 에러 상태의 엔드포인트 경로 등(state-code). */
  code?: ReactNode;
  /** 액션 버튼/링크. body·code 뒤에 붙는다. */
  children?: ReactNode;
  testId?: string;
  /** 공용 .state-box 위에 얹을 화면 전용 클래스(예: 에러 3종의 .err-hero). 생략 시 기존 출력 그대로. */
  className?: string;
}

export function StateBox({
  tone = "neutral",
  icon,
  title,
  body,
  code,
  children,
  testId,
  className,
}: StateBoxProps) {
  const isFailed = tone === "failed";
  const base = isFailed ? "state-box failed" : "state-box";
  return (
    <div
      className={className ? `${base} ${className}` : base}
      role={isFailed ? "alert" : "status"}
      data-testid={testId}
    >
      {icon != null && (
        <span
          className={isFailed ? "state-icon failed" : "state-icon"}
          aria-hidden="true"
        >
          {icon}
        </span>
      )}
      <p className="state-title">{title}</p>
      {body != null && <p className="state-body">{body}</p>}
      {code != null && <p className="state-code">{code}</p>}
      {children}
    </div>
  );
}
