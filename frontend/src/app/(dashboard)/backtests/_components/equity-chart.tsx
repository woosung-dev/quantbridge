"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { EquityPoint } from "@/features/backtest/schemas";
import {
  downsampleEquity,
  formatCurrency,
  formatDate,
} from "@/features/backtest/utils";

interface EquityChartProps {
  points: readonly EquityPoint[];
  maxPoints?: number;
}

interface ChartDatum {
  ts: number;
  value: number;
  label: string;
}

/**
 * EquityChart — backtest 의 equity curve 를 line chart 로 렌더.
 *
 * width(-1) warning 회피 전략:
 * - 부모 div 의 실제 width 를 ResizeObserver 로 측정.
 * - width 가 1 이상으로 측정되기 전까지는 ResponsiveContainer 를 mount 하지 않고
 *   동일 크기의 placeholder 만 렌더링 → recharts 가 width=-1 로 자식 차트에 전달하는 것을 차단.
 * - jsdom 환경: ResizeObserver 가 inert 라 width 가 0 으로 유지 → 차트 미마운트 → warning 0건.
 * - 브라우저 환경: layout 측정 후 ResizeObserver 가 width 를 발화 → 정상 mount.
 *
 * LESSON-004 준수:
 * - useEffect dep 에 RQ/Zustand 결과 객체나 unstable function ref 사용 금지.
 * - 본 컴포넌트는 ref + setter 만 클로저 캡처하고 dep array 는 `[]` (primitive 등가).
 */
export function EquityChart({ points, maxPoints = 1000 }: EquityChartProps) {
  const data = useMemo<ChartDatum[]>(() => {
    const sampled = downsampleEquity(points, maxPoints);
    return sampled.map((p) => ({
      ts: new Date(p.timestamp).getTime(),
      value: p.value,
      label: formatDate(p.timestamp),
    }));
  }, [points, maxPoints]);

  // 부모 wrapper 의 실측 width — 0 이면 차트 미마운트.
  const wrapperRef = useRef<HTMLDivElement | null>(null);
  const [hasWidth, setHasWidth] = useState(false);

  useEffect(() => {
    const node = wrapperRef.current;
    if (node === null) {
      return;
    }

    // 1차: 즉시 측정 (CSR 환경에서 layout 이 이미 완료된 경우)
    const initialWidth = node.getBoundingClientRect().width;
    if (initialWidth >= 1) {
      setHasWidth(true);
      return;
    }

    // 2차: ResizeObserver 로 width 측정 후 한 번만 발화.
    // jsdom 에서는 ResizeObserver 가 미정의이거나 inert → catch 로 안전하게 빠짐.
    if (typeof ResizeObserver === "undefined") {
      return;
    }

    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        if (entry.contentRect.width >= 1) {
          setHasWidth(true);
          observer.disconnect();
          break;
        }
      }
    });
    observer.observe(node);
    return () => {
      observer.disconnect();
    };
  }, []); // primitive-only dep array — LESSON-004 준수

  if (data.length === 0) {
    return (
      <div className="flex h-64 items-center justify-center text-sm text-muted-foreground">
        Equity 데이터가 없습니다
      </div>
    );
  }

  return (
    <div ref={wrapperRef} className="h-64 w-full" style={{ minWidth: 0 }}>
      {hasWidth ? (
        <ResponsiveContainer width="100%" height="100%" minWidth={0}>
          <LineChart
            data={data}
            margin={{ top: 12, right: 16, left: 0, bottom: 0 }}
          >
            <CartesianGrid strokeDasharray="3 3" vertical={false} />
            <XAxis
              dataKey="label"
              tick={{ fontSize: 11 }}
              minTickGap={32}
            />
            <YAxis
              tick={{ fontSize: 11 }}
              tickFormatter={(v: number) => formatCurrency(v, 0)}
              width={80}
            />
            <Tooltip
              formatter={(value) =>
                typeof value === "number" ? formatCurrency(value) : String(value)
              }
              labelFormatter={(label) => (label == null ? "" : String(label))}
            />
            <Line
              type="monotone"
              dataKey="value"
              stroke="currentColor"
              strokeWidth={1.5}
              dot={false}
              isAnimationActive={false}
            />
          </LineChart>
        </ResponsiveContainer>
      ) : (
        // 측정 전 placeholder — h-64 w-full 동일 크기로 layout shift 방지
        <div className="h-full w-full" aria-busy="true" />
      )}
    </div>
  );
}
