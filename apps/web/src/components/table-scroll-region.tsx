// 가로 스크롤 표 래퍼 — 캐논 `.table-wrap`(_KIT.md 하드 제약 #14) + 키보드 도달성.
//
// ★왜 컴포넌트인가. `.table-wrap` 은 `overflow-x` 만 갖고 내부에 포커스 가능한 요소가 없어서
//   **키보드 사용자가 넘친 열에 도달할 수 없다**(WCAG 2.1.1 · axe `scrollable-region-focusable`,
//   serious). 2026-09-06 실측에서 375px 의 /pricing·/waitlist·/trading 과 /strategies/new 가
//   전부 걸렸다. 처방은 `tabindex="0"` 하나인데, 그것을 쓰는 곳마다 Biome 의
//   `noNoninteractiveTabindex` 와 부딪힌다. 억제 주석을 6곳에 흩는 대신 여기 한 곳에 둔다.
//
// ★`div` 가 아니라 `section` 이다 — 이름 없는 `div`(role=generic)에는 `aria-label` 을 붙일 수
//   없고(Biome `useAriaPropsSupportedByRole`), 탭이 멈췄는데 이름이 없으면 무엇에 멈춘 건지
//   읽히지 않는다. `section` + `aria-label` 은 암묵 `region` 롤이라 `role` 을 손으로 안 적어도 된다.
import type { ReactNode } from "react";

export function TableScrollRegion({
  label,
  className,
  testId,
  children,
}: {
  /** 이 스크롤 영역이 무엇인지. 탭이 여기 멈췄을 때 읽히는 이름이다. */
  label: string;
  className?: string;
  testId?: string;
  children: ReactNode;
}) {
  return (
    <section
      className={className ? `table-wrap ${className}` : "table-wrap"}
      // biome-ignore lint/a11y/noNoninteractiveTabindex: 스크롤 컨테이너는 tabindex=0 이 있어야 키보드로 스크롤된다(WCAG 2.1.1 · axe scrollable-region-focusable). 위젯화가 아니다.
      tabIndex={0}
      aria-label={label}
      data-testid={testId}
    >
      {children}
    </section>
  );
}
