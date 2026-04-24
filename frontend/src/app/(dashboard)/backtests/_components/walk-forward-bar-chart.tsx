"use client";

// Phase C: Walk-Forward bar chart — IS vs OOS return per fold + degradation ratio.
// - degradation_ratio 는 문자열 (BE 가 Decimal or "Infinity" 로 직렬화).
// - valid_positive_regime === false 이면 "N/A" 표기 (손실 구간).
// - was_truncated 이면 folds/total_possible_folds 비율 노출.

import { useEffect, useMemo, useRef, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { WalkForwardResult } from "@/features/backtest/schemas";

interface Props {
  result: WalkForwardResult;
}

interface BarDatum {
  fold: string;
  IS: number;
  OOS: number;
}

export function WalkForwardBarChart({ result }: Props) {
  const data = useMemo<BarDatum[]>(() => {
    return result.folds.map((f) => ({
      fold: `fold ${f.fold_index + 1}`,
      IS: f.in_sample_return * 100,
      OOS: f.out_of_sample_return * 100,
    }));
  }, [result]);

  const degradationText = useMemo(() => {
    if (!result.valid_positive_regime) {
      return "Degradation ratio: N/A (손실 구간 포함)";
    }
    return `Degradation ratio (IS/OOS): ${result.degradation_ratio}`;
  }, [result.valid_positive_regime, result.degradation_ratio]);

  const truncationText =
    result.was_truncated && result.total_possible_folds > 0
      ? ` · ${result.folds.length}/${result.total_possible_folds} folds 표시`
      : "";

  // jsdom width(-1) warning 회피.
  const wrapperRef = useRef<HTMLDivElement | null>(null);
  const [hasWidth, setHasWidth] = useState(false);

  useEffect(() => {
    const node = wrapperRef.current;
    if (node === null) return;
    const initial = node.getBoundingClientRect().width;
    if (initial >= 1) {
      setHasWidth(true);
      return;
    }
    if (typeof ResizeObserver === "undefined") return;
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
    return () => observer.disconnect();
  }, []); // LESSON-004 준수

  if (data.length === 0) {
    return (
      <div>
        <p className="text-sm text-muted-foreground">
          Walk-Forward fold 데이터가 없습니다.
        </p>
      </div>
    );
  }

  return (
    <div>
      <p className="mb-2 text-sm text-muted-foreground">
        {degradationText}
        {truncationText}
      </p>
      <div
        ref={wrapperRef}
        className="h-80 w-full overflow-x-auto"
        style={{ minWidth: 0 }}
      >
        {hasWidth ? (
          <div className="h-full min-w-[600px]">
            <ResponsiveContainer width="100%" height="100%" minWidth={0}>
              <BarChart
                data={data}
                margin={{ top: 12, right: 16, bottom: 24, left: 8 }}
              >
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="fold" tick={{ fontSize: 11 }} />
                <YAxis
                  tick={{ fontSize: 11 }}
                  tickFormatter={(v: number) => `${v.toFixed(1)}%`}
                  width={70}
                />
                <Tooltip
                  formatter={(value) =>
                    typeof value === "number"
                      ? `${value.toFixed(2)}%`
                      : String(value)
                  }
                />
                <Legend verticalAlign="top" height={28} />
                <Bar dataKey="IS" fill="#8884d8" name="In-sample" isAnimationActive={false} />
                <Bar dataKey="OOS" fill="#82ca9d" name="Out-of-sample" isAnimationActive={false} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <div className="h-full w-full" aria-busy="true" />
        )}
      </div>
    </div>
  );
}
