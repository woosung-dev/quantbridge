import type { CodeExecutionSummary as Summary } from "../schemas";
import { formatDateTime } from "../utils";

const CHECKPOINT_LABEL = {
  warmup: "워밍업",
  prepared: "의도 저장 · 전달 대기",
  delivered: "의도 전달 완료",
  blocked: "평가 차단",
};

export function CodeExecutionSummary({ summary }: { summary: Summary }) {
  return (
    <div className="mt-3 rounded-md border p-3 text-xs" data-testid="code-execution-summary">
      <p className="font-medium">코드 실행 · 영속 원장</p>
      <p className="mt-1">
        {summary.checkpoint_status ? CHECKPOINT_LABEL[summary.checkpoint_status] : "첫 평가 대기"}
        {" · "}
        {formatDateTime(summary.last_bar_time)}
        {summary.last_intent ? ` · 의도 ${summary.last_intent}` : ""}
      </p>
      <p className="mt-1">
        버전 {summary.version_id ?? "—"} · 세대 {summary.risk_generation ?? "—"}
      </p>
      <p className="mt-1">
        원장 잔량 {summary.position_quantity ?? "—"} · 방향 {summary.direction ?? "—"}
        {" · "}진입 VWAP {summary.entry_vwap ?? "—"} · 고정 R {summary.fixed_r ?? "—"}
      </p>
      <p className="mt-1">
        {summary.protection_pending ? "보호 ACK 대기" : "보호 변경 대기 없음"}
        {summary.trailing_active ? " · 트레일 활성" : ""}
        {summary.pending_reversal ? ` · ${summary.pending_reversal} 반전 대기` : ""}
      </p>
      {summary.new_entries_blocked || summary.failure_reason ? (
        <p className="mt-1 text-destructive" role="status">
          새 진입 차단{summary.failure_reason ? ` · ${summary.failure_reason}` : ""}
        </p>
      ) : null}
      <p className="mt-1 text-muted-foreground">
        의도 전달은 체결 완료를 뜻하지 않습니다. 손익은 실제 체결 주문을 기준으로 집계합니다.
      </p>
    </div>
  );
}
