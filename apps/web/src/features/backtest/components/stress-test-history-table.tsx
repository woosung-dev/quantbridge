// [BL-414] 한 백테스트의 스트레스 테스트 **이력** 표.
//
// 종전 패널은 최신 1건만 그렸다. 스트레스 테스트는 같은 백테스트에 몇 번이고 돌릴 수
// 있고 종류가 4종이라, 최신 1건만 보이면 "몬테카를로를 돌렸는데 어제 돌린 워크포워드는
// 어디 갔나" 가 화면에서 답이 안 나온다.
//
// 표시 규약 둘.
//   ⑴ 종류·상태는 원시 enum 이 아니라 라벨 SSOT 를 거친다 (`no-raw-enum-labels` 가드).
//   ⑵ ★지표가 **없는 것**과 **0 인 것**을 같게 그리지 않는다. 실패·미완료 행의 지표 칸은
//     `EMPTY_CELL` 이다 — [BL-465] 에서 파산한 계좌가 양수 샤프를 보여준 것이 이 구분을
//     놓친 결과였다.

"use client";

import { Button } from "@/components/ui/button";
import {
  STRESS_TEST_HEADLINE_METRIC_LABEL,
  STRESS_TEST_HISTORY_HEADER,
  STRESS_TEST_HISTORY_LABEL,
  STRESS_TEST_KIND_LABEL,
  STRESS_TEST_STATUS_LABEL,
} from "@/features/backtest/labels";
import type {
  StressTestHeadlineMetric,
  StressTestSummary,
} from "@/features/backtest/schemas";
import { formatDateTime, formatPercent } from "@/features/backtest/utils";
import { CHIP_TONE_CLASS, EMPTY_CELL, labelOf, statusLabelOf } from "@/lib/labels";

export interface StressTestHistoryTableProps {
  readonly items: readonly StressTestSummary[];
  /** 지금 상세 패널이 그리고 있는 실행. 없으면 null. */
  readonly selectedId: string | null;
  readonly onSelect: (stressTestId: string) => void;
  readonly isLoading: boolean;
  readonly isError: boolean;
}

/**
 * 대표 지표 1칸의 표기. 값이 없으면 `EMPTY_CELL`, 있으면 "이름 값" 이다.
 * 지표마다 단위가 다르므로 포맷도 지표별로 갈린다 — MDD 는 비율이라 %, 나머지는 배수/지수다.
 */
export function formatHeadlineMetric(
  metric: StressTestHeadlineMetric | null,
): string {
  if (metric === null) return EMPTY_CELL;
  const name = labelOf(
    STRESS_TEST_HEADLINE_METRIC_LABEL,
    metric.key,
    "stress-test-headline-metric",
  );
  // 열화 비율은 Decimal("Infinity") 를 문자열 "Infinity" 로 저장한다 (BE
  // WalkForwardResultOut docstring). Number() 가 Infinity 로 살아나긴 하지만
  // toFixed 가 "Infinity" 를 그대로 뱉으므로 화면 기호로 바꿔 준다.
  if (metric.value === "Infinity") {
    return `${name} ${STRESS_TEST_HISTORY_LABEL.infinity}`;
  }
  const parsed = Number(metric.value);
  if (!Number.isFinite(parsed)) return EMPTY_CELL;
  const shown =
    metric.key === "max_drawdown_p95"
      ? formatPercent(parsed, 2)
      : parsed.toFixed(2);
  return `${name} ${shown}`;
}

export function StressTestHistoryTable({
  items,
  selectedId,
  onSelect,
  isLoading,
  isError,
}: StressTestHistoryTableProps) {
  if (isError) {
    return (
      <p className="text-sm text-destructive">
        {STRESS_TEST_HISTORY_LABEL.loadFailed}
      </p>
    );
  }

  if (isLoading && items.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">
        {STRESS_TEST_HISTORY_LABEL.loading}
      </p>
    );
  }

  if (items.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">
        {STRESS_TEST_HISTORY_LABEL.empty}
      </p>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table
        className="w-full min-w-[600px] text-sm"
        aria-label={STRESS_TEST_HISTORY_LABEL.caption}
      >
        <thead>
          <tr className="border-b text-left text-xs text-muted-foreground">
            <th className="p-2 font-medium" scope="col">
              {STRESS_TEST_HISTORY_HEADER.kindColumn}
            </th>
            <th className="p-2 font-medium" scope="col">
              {STRESS_TEST_HISTORY_HEADER.statusColumn}
            </th>
            <th className="p-2 font-medium" scope="col">
              {STRESS_TEST_HISTORY_HEADER.metricColumn}
            </th>
            <th className="p-2 font-medium" scope="col">
              {STRESS_TEST_HISTORY_HEADER.createdAtColumn}
            </th>
            <th className="p-2 font-medium" scope="col">
              {STRESS_TEST_HISTORY_HEADER.actionColumn}
            </th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => {
            const statusLabel = statusLabelOf(
              STRESS_TEST_STATUS_LABEL,
              item.status,
              "stress-test-status",
            );
            const isSelected = item.id === selectedId;
            return (
              <tr
                key={item.id}
                data-testid="stress-test-history-row"
                aria-current={isSelected ? "true" : undefined}
                className={isSelected ? "border-b bg-muted/50" : "border-b"}
              >
                <td className="p-2">
                  {labelOf(
                    STRESS_TEST_KIND_LABEL,
                    item.kind,
                    "stress-test-kind",
                  )}
                </td>
                <td className="p-2">
                  <span className={CHIP_TONE_CLASS[statusLabel.tone]}>
                    {statusLabel.label}
                  </span>
                </td>
                <td className="p-2 tabular-nums" data-testid="stress-test-history-metric">
                  {formatHeadlineMetric(item.headline_metric)}
                </td>
                <td className="p-2 whitespace-nowrap">
                  {formatDateTime(item.created_at)}
                </td>
                <td className="p-2">
                  <Button
                    type="button"
                    variant={isSelected ? "secondary" : "outline"}
                    size="sm"
                    disabled={isSelected}
                    onClick={() => onSelect(item.id)}
                  >
                    {isSelected
                      ? STRESS_TEST_HISTORY_LABEL.selected
                      : STRESS_TEST_HISTORY_LABEL.select}
                  </Button>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
