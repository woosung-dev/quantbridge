// 코크핏 §06 진단 카드의 실제 API·스토어 상태 매핑을 검증한다.
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { AlertTriangleIcon } from "lucide-react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import { ApiError } from "@/lib/api-client";
import {
  DiagnosticCard,
  SessionDiagnostics,
} from "@/app/(dashboard)/trading/_components/session-diagnostics";
import { useAlertRules, useCreateAlertRule, useDeactivateAlertRule } from "@/features/alert-rules/hooks";
import { useLiveSessionPositions } from "@/features/live-sessions/hooks";
import type { LiveSession } from "@/features/live-sessions/schemas";

vi.mock("@/features/live-sessions/hooks", () => ({
  useLiveSessionPositions: vi.fn(),
}));
vi.mock("@/features/alert-rules/hooks", () => ({
  useAlertRules: vi.fn(),
  useCreateAlertRule: vi.fn(),
  useDeactivateAlertRule: vi.fn(),
}));

let realtime = { status: "idle", lastEventTs: null as number | null };
vi.mock("@/features/realtime/store", () => ({
  useRealtimeStore: (selector: (state: typeof realtime) => unknown) => selector(realtime),
  selectRealtimeStatus: (state: typeof realtime) => state.status,
  selectLastRealtimeEventTs: (state: typeof realtime) => state.lastEventTs,
}));

const session: LiveSession = {
  id: "a0000000-0000-4000-8000-000000000001",
  user_id: "a0000000-0000-4000-8000-000000000002",
  strategy_id: "a0000000-0000-4000-8000-000000000003",
  exchange_account_id: "a0000000-0000-4000-8000-000000000004",
  symbol: "BTC/USDT",
  interval: "1m",
  is_active: true,
  last_evaluated_bar_time: null,
  created_at: "2026-07-24T00:00:00Z",
  deactivated_at: null,
};

const mockPositions = vi.mocked(useLiveSessionPositions);
const mockRules = vi.mocked(useAlertRules);
const mockCreateRule = vi.mocked(useCreateAlertRule);
const mockDeactivateRule = vi.mocked(useDeactivateAlertRule);

const refetch = vi.fn();
const mutateAsync = vi.fn();
const deactivate = vi.fn();

function positions(data?: unknown, overrides: Record<string, unknown> = {}) {
  return {
    data,
    isLoading: false,
    isError: false,
    refetch,
    ...overrides,
  } as unknown as ReturnType<typeof useLiveSessionPositions>;
}

function rules(data?: unknown, overrides: Record<string, unknown> = {}) {
  return {
    data,
    isLoading: false,
    isError: false,
    refetch,
    ...overrides,
  } as unknown as ReturnType<typeof useAlertRules>;
}

beforeEach(() => {
  realtime = { status: "idle", lastEventTs: null };
  refetch.mockReset();
  mutateAsync.mockReset();
  deactivate.mockReset();
  mutateAsync.mockResolvedValue({});
  mockPositions.mockReturnValue(positions());
  mockRules.mockReturnValue(rules({ items: [], total: 0 }));
  mockCreateRule.mockReturnValue({ mutateAsync, isPending: false } as never);
  mockDeactivateRule.mockReturnValue({ mutate: deactivate, isPending: false } as never);
});

describe("DiagnosticCard 4상태", () => {
  test("action을 상태 박스 안에 렌더한다", () => {
    render(
      <DiagnosticCard
        title="포지션 동기화"
        subtitle="거래소 대조 조회"
        state="error"
        heading="실패"
        body="다시 확인하세요."
        code="GET /api/v1/live-sessions/id/positions · 503"
        icon={<AlertTriangleIcon />}
        action={<button type="button">다시 시도</button>}
      />,
    );
    expect(screen.getByRole("alert")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "다시 시도" })).toBeInTheDocument();
  });
});

describe("SessionDiagnostics", () => {
  test("세션 미선택이면 포지션과 알림을 빈 상태로 안내한다", () => {
    render(<SessionDiagnostics session={null} />);
    expect(screen.getByText("세션을 선택하면 거래소 포지션을 대조합니다.")).toBeInTheDocument();
    expect(screen.getByText("세션을 선택하면 이 세션의 알림 규칙을 확인합니다.")).toBeInTheDocument();
  });

  test("포지션과 알림 조회 중에는 각 카드가 로딩 상태가 된다", () => {
    mockPositions.mockReturnValue(positions(undefined, { isLoading: true }));
    mockRules.mockReturnValue(rules(undefined, { isLoading: true }));
    render(<SessionDiagnostics session={session} />);
    expect(screen.getByLabelText("포지션 동기화, 불러오는 중")).toBeInTheDocument();
    expect(screen.getByLabelText("알림 규칙, 불러오는 중")).toBeInTheDocument();
  });

  test("포지션 match는 거래소 수량과 대조 시각을 그대로 표시한다", () => {
    mockPositions.mockReturnValue(
      positions({
        supported: true,
        fetched_at: "2026-07-24T12:00:00Z",
        positions: [{ side: "long", size: "0.25" }],
        diff: { verdict: "match" },
      }),
    );
    render(<SessionDiagnostics session={session} />);
    expect(screen.getByText("거래소와 일치")).toBeInTheDocument();
    expect(screen.getByText(/대조 시각 2026-07-24T12:00:00Z · 거래소 수량 long 0.25/)).toBeInTheDocument();
  });

  test("포지션 오류는 실제 경로 코드와 재시도 action을 표시한다", () => {
    mockPositions.mockReturnValue(positions(undefined, { isError: true }));
    render(<SessionDiagnostics session={session} />);
    expect(
      screen.getByText(`GET /api/v1/live-sessions/${session.id}/positions · 503`),
    ).toBeInTheDocument();
    fireEvent.click(screen.getAllByRole("button", { name: "다시 시도" })[0]!);
    expect(refetch).toHaveBeenCalledOnce();
  });

  test("포지션 미지원 사유를 정직하게 표시한다", () => {
    mockPositions.mockReturnValue(
      positions({ supported: false, reason: "spot_position_api_unsupported" }),
    );
    render(<SessionDiagnostics session={session} />);
    expect(screen.getByText("현물 세션의 포지션 대조는 아직 지원하지 않습니다.")).toBeInTheDocument();
  });

  test("알림 규칙이 없으면 인라인 생성 버튼을 표시하고 loss_limit payload를 보낸다", async () => {
    render(<SessionDiagnostics session={session} />);
    fireEvent.click(screen.getByRole("button", { name: "알림 규칙 만들기" }));
    fireEvent.change(screen.getByLabelText("손실 한도 (%)"), { target: { value: "5" } });
    fireEvent.click(screen.getByRole("button", { name: "알림 규칙 저장" }));
    await waitFor(() =>
      expect(mutateAsync).toHaveBeenCalledWith({
        rule_type: "loss_limit",
        threshold_percent: "5",
        channel: "telegram",
      }),
    );
  });

  test("손실 한도 100% 초과는 필드 오류를 보이고 요청하지 않는다", async () => {
    render(<SessionDiagnostics session={session} />);
    fireEvent.click(screen.getByRole("button", { name: "알림 규칙 만들기" }));
    fireEvent.change(screen.getByLabelText("손실 한도 (%)"), { target: { value: "100.01" } });
    fireEvent.click(screen.getByRole("button", { name: "알림 규칙 저장" }));

    expect(await screen.findByText("손실 한도는 100% 이하여야 합니다.")).toBeInTheDocument();
    expect(mutateAsync).not.toHaveBeenCalled();
  });

  test("알림 규칙 409는 중복 활성 규칙 안내를 표시한다", async () => {
    mutateAsync.mockRejectedValue(
      new ApiError(409, "unknown_error", "conflict", {
        detail: { code: "alert_rule_already_active" },
      }),
    );
    render(<SessionDiagnostics session={session} />);
    fireEvent.click(screen.getByRole("button", { name: "알림 규칙 만들기" }));
    fireEvent.change(screen.getByLabelText("손실 한도 (%)"), { target: { value: "5" } });
    fireEvent.click(screen.getByRole("button", { name: "알림 규칙 저장" }));
    expect(await screen.findByText("이미 같은 유형의 활성 규칙이 있습니다.")).toBeInTheDocument();
  });

  test("활성 규칙은 저장값을 요약하고 해제 action을 제공한다", () => {
    mockRules.mockReturnValue(
      rules({
        items: [
          {
            id: "a0000000-0000-4000-8000-000000000010",
            rule_type: "loss_limit",
            threshold_percent: "5",
            channel: "telegram",
          },
        ],
        total: 1,
      }),
    );
    render(<SessionDiagnostics session={session} />);
    expect(screen.getByText("규칙 1개 활성")).toBeInTheDocument();
    expect(screen.getByText("손실 한도 5% · telegram")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "해제" }));
    expect(deactivate).toHaveBeenCalledWith("a0000000-0000-4000-8000-000000000010");
  });

  test("활성 규칙이 있어도 생성 폼을 열 수 있다", () => {
    mockRules.mockReturnValue(
      rules({
        items: [
          {
            id: "a0000000-0000-4000-8000-000000000010",
            rule_type: "watchdog",
            threshold_percent: null,
            channel: "telegram",
          },
        ],
        total: 1,
      }),
    );
    render(<SessionDiagnostics session={session} />);

    fireEvent.click(screen.getByRole("button", { name: "알림 규칙 만들기" }));

    expect(screen.getByRole("button", { name: "알림 규칙 만들기 닫기" })).toBeInTheDocument();
    expect(screen.getByLabelText("손실 한도 (%)")).toBeInTheDocument();
  });

  test("활성 규칙의 Numeric threshold 끝 0을 숨긴다", () => {
    mockRules.mockReturnValue(
      rules({
        items: [
          {
            id: "a0000000-0000-4000-8000-000000000010",
            rule_type: "loss_limit",
            threshold_percent: "5.00000000",
            channel: "telegram",
          },
        ],
        total: 1,
      }),
    );
    render(<SessionDiagnostics session={session} />);

    expect(screen.getByText("손실 한도 5% · telegram")).toBeInTheDocument();
  });

  test.each([
    ["authed", "실시간 스트림 연결됨"],
    ["connecting", "실시간 스트림에 연결하고 있습니다."],
    ["idle", "실시간 스트림이 설정되지 않았습니다."],
    ["closed", "실시간 스트림 연결이 끊겼습니다."],
  ])("실시간 %s 상태를 %s로 표시한다", (status, heading) => {
    realtime = { status, lastEventTs: null };
    render(<SessionDiagnostics session={session} />);
    expect(screen.getByText(new RegExp(heading))).toBeInTheDocument();
  });
});
