// C 이식 S8 — 세션 진단 카드 4상태(로딩/에러/빈/정상) + §06 진단 섹션 단위 테스트.
// 에러 상태의 실제 엔드포인트 = GET /trading/sessions/{id}/positions · 503 (캐논 §6).

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

  test("error — 실제 엔드포인트(positions · 503) 노출 + role=alert", () => {
    render(
      <DiagnosticCard
        title="포지션 동기화"
        subtitle="거래소 대조 조회"
        state="error"
        heading="포지션을 대조하지 못했습니다."
        body="아직 배선하지 않았습니다."
        code="GET /trading/sessions/sess_8d14/positions · 503"
        icon={<AlertTriangleIcon />}
      />,
    );
    expect(screen.getByRole("alert")).toBeInTheDocument();
    expect(
      screen.getByText("GET /trading/sessions/sess_8d14/positions · 503"),
    ).toBeInTheDocument();
    expect(
      screen.getByText("포지션을 대조하지 못했습니다."),
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
  test("sessionId 없으면 포지션 엔드포인트에 {id} 플레이스홀더", () => {
    render(<SessionDiagnostics />);
    expect(
      screen.getByText("GET /trading/sessions/{id}/positions · 503"),
    ).toBeInTheDocument();
    // 포지션·스트림·알림 3종 진단 카드.
    expect(screen.getByText("포지션 동기화")).toBeInTheDocument();
    expect(screen.getByText("실시간 가격 스트림")).toBeInTheDocument();
    expect(screen.getByText("알림 규칙")).toBeInTheDocument();
  });

  test("sessionId 있으면 실제 id 를 엔드포인트에 박는다", () => {
    render(<SessionDiagnostics sessionId="sess_abcd" />);
    expect(
      screen.getByText("GET /trading/sessions/sess_abcd/positions · 503"),
    ).toBeInTheDocument();
  });
});
