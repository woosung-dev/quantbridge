// C 이식 S8 — 세션 진단 카드 4상태(로딩/에러/빈/정상) + §06 진단 섹션 단위 테스트.
// DiagnosticCard 는 실제 에러+엔드포인트를 받을 수 있는 범용 프리미티브지만, SessionDiagnostics
// 는 포지션 대조 API 가 없어 지어낸 엔드포인트를 노출하지 않고 '미제공' 상태로 둔다(정직성 우선).

import { render, screen } from "@testing-library/react";
import { AlertTriangleIcon } from "lucide-react";

import {
  DiagnosticCard,
  SessionDiagnostics,
} from "@/app/(dashboard)/trading/_components/session-diagnostics";

describe("DiagnosticCard 4상태", () => {
  test("loading — 스켈레톤 + aria-busy", () => {
    render(
      <DiagnosticCard
        title="포지션 동기화"
        subtitle="거래소 대조 조회"
        state="loading"
        heading="불러오는 중"
        body="연결하고 있습니다."
        icon={<AlertTriangleIcon />}
      />,
    );
    const card = screen.getByTestId("diag-loading");
    expect(card).toHaveAttribute("aria-busy", "true");
    expect(screen.getByText("연결하고 있습니다.")).toBeInTheDocument();
  });

  test("error — 실제 엔드포인트 코드 노출 + role=alert", () => {
    // 프리미티브 자체는 실제 에러+엔드포인트를 받을 수 있다(실재하는 /orders 경로로 예시).
    render(
      <DiagnosticCard
        title="주문 원장"
        subtitle="주문 조회"
        state="error"
        heading="주문을 불러오지 못했습니다."
        body="일시적 오류일 수 있습니다."
        code="GET /api/v1/trading/orders · 503"
        icon={<AlertTriangleIcon />}
      />,
    );
    expect(screen.getByRole("alert")).toBeInTheDocument();
    expect(
      screen.getByText("GET /api/v1/trading/orders · 503"),
    ).toBeInTheDocument();
    expect(
      screen.getByText("주문을 불러오지 못했습니다."),
    ).toBeInTheDocument();
  });

  test("empty — 상태 박스 + role=status", () => {
    render(
      <DiagnosticCard
        title="알림 규칙"
        subtitle="이 세션 전용"
        state="empty"
        heading="알림 규칙이 없습니다."
        body="규칙을 걸 수 있습니다."
        icon={<AlertTriangleIcon />}
      />,
    );
    expect(screen.getByTestId("diag-empty")).toBeInTheDocument();
    expect(screen.getByText("알림 규칙이 없습니다.")).toBeInTheDocument();
  });

  test("ok — 상태 박스(정상) 렌더", () => {
    render(
      <DiagnosticCard
        title="데이터 갱신"
        subtitle="폴링"
        state="ok"
        heading="정상"
        body="폴링 스냅샷으로 갱신합니다."
        icon={<AlertTriangleIcon />}
      />,
    );
    expect(screen.getByTestId("diag-ok")).toBeInTheDocument();
    expect(screen.getByText("정상")).toBeInTheDocument();
  });
});

describe("SessionDiagnostics 섹션", () => {
  test("포지션 대조는 지어낸 엔드포인트 대신 '미제공' 상태로 정직하게 둔다", () => {
    render(<SessionDiagnostics />);
    // 존재하지 않는 positions 엔드포인트·상태코드를 노출하지 않는다.
    expect(screen.queryByText(/\/positions/)).not.toBeInTheDocument();
    expect(screen.queryByText(/· 503/)).not.toBeInTheDocument();
    // 미제공 상태를 정직하게 표기한다.
    expect(
      screen.getByText("포지션 대조는 아직 제공되지 않습니다."),
    ).toBeInTheDocument();
    // 포지션·스트림·알림 3종 진단 카드.
    expect(screen.getByText("포지션 동기화")).toBeInTheDocument();
    expect(screen.getByText("실시간 가격 스트림")).toBeInTheDocument();
    expect(screen.getByText("알림 규칙")).toBeInTheDocument();
  });
});
