"use client";

// Sprint 52 BL-223 — Param Stability MVP form (2개 var_name x 3 value preset).
// codex G.0 P1 정정: hardcoded preset 불가 (BE 가 Pine InputDecl.var_name cross-check).
// 사용자가 strategy 의 InputDecl 변수명을 직접 입력 + 3 value preset. dogfood sample 한정.
// 자유 grid 또는 strategy input metadata 자동 선택 UI 는 별도 BL (Sprint 53+ Phase 3 prep).

import { useState } from "react";

import { Button } from "@/components/ui/button";

interface Props {
  backtestId: string;
  onSubmit: (payload: {
    backtest_id: string;
    params: { param_grid: Record<string, string[]> };
  }) => void;
  isSubmitting: boolean;
  onCancel: () => void;
}

const DEFAULT_VAR1 = "emaPeriod";
const DEFAULT_VAR1_VALUES: readonly [string, string, string] = ["10", "20", "30"];
const DEFAULT_VAR2 = "stopLossPct";
const DEFAULT_VAR2_VALUES: readonly [string, string, string] = ["1.0", "2.0", "3.0"];

type Triple = readonly [string, string, string];

export function ParamStabilityForm({
  backtestId,
  onSubmit,
  isSubmitting,
  onCancel,
}: Props) {
  const [var1Name, setVar1Name] = useState(DEFAULT_VAR1);
  const [var1Values, setVar1Values] = useState<Triple>(DEFAULT_VAR1_VALUES);
  const [var2Name, setVar2Name] = useState(DEFAULT_VAR2);
  const [var2Values, setVar2Values] = useState<Triple>(DEFAULT_VAR2_VALUES);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit({
      backtest_id: backtestId,
      params: {
        param_grid: {
          [var1Name]: [...var1Values],
          [var2Name]: [...var2Values],
        },
      },
    });
  };

  const isInvalid =
    var1Name.trim().length === 0 ||
    var2Name.trim().length === 0 ||
    var1Name.trim() === var2Name.trim() ||
    var1Values.some((v) => v.trim().length === 0) ||
    var2Values.some((v) => v.trim().length === 0);

  return (
    <form
      onSubmit={handleSubmit}
      data-testid="param-stability-form"
      className="space-y-3 rounded-lg border bg-muted/30 p-4"
    >
      <p className="text-sm text-muted-foreground">
        Pine 전략의 <code>input.int</code> / <code>input.float</code> 변수 2개를
        지정하면 9-cell 조합으로 실행됩니다. 변수명은 Pine 코드의{" "}
        <code>strategyVar = input.int(...)</code> 좌변 이름과 동일해야 합니다.
      </p>
      <ParamRow
        label="변수 1"
        name={var1Name}
        values={var1Values}
        onNameChange={setVar1Name}
        onValuesChange={setVar1Values}
      />
      <ParamRow
        label="변수 2"
        name={var2Name}
        values={var2Values}
        onNameChange={setVar2Name}
        onValuesChange={setVar2Values}
      />
      <div className="flex gap-2">
        <Button type="submit" disabled={isInvalid || isSubmitting}>
          {isSubmitting ? "제출 중…" : "Param Stability 실행"}
        </Button>
        <Button
          type="button"
          variant="outline"
          onClick={onCancel}
          disabled={isSubmitting}
        >
          취소
        </Button>
        {var1Name.trim() === var2Name.trim() && var1Name.trim().length > 0 ? (
          <p className="text-sm text-destructive">
            두 변수 이름은 서로 달라야 합니다.
          </p>
        ) : null}
      </div>
    </form>
  );
}

interface RowProps {
  label: string;
  name: string;
  values: Triple;
  onNameChange: (v: string) => void;
  onValuesChange: (v: Triple) => void;
}

function ParamRow({
  label,
  name,
  values,
  onNameChange,
  onValuesChange,
}: RowProps) {
  return (
    <div className="grid grid-cols-1 gap-2 md:grid-cols-4">
      <label className="flex flex-col text-sm">
        <span className="text-xs text-muted-foreground">{label} 변수명</span>
        <input
          type="text"
          value={name}
          onChange={(e) => onNameChange(e.target.value)}
          className="rounded border bg-background px-2 py-1"
          aria-label={`${label} 변수명`}
        />
      </label>
      {(["0", "1", "2"] as const).map((idx) => {
        const i = Number(idx) as 0 | 1 | 2;
        return (
          <label key={idx} className="flex flex-col text-sm">
            <span className="text-xs text-muted-foreground">값 {i + 1}</span>
            <input
              type="text"
              value={values[i]}
              onChange={(e) => {
                const next: Triple = [
                  i === 0 ? e.target.value : values[0],
                  i === 1 ? e.target.value : values[1],
                  i === 2 ? e.target.value : values[2],
                ];
                onValuesChange(next);
              }}
              className="rounded border bg-background px-2 py-1"
              aria-label={`${label} 값 ${i + 1}`}
            />
          </label>
        );
      })}
    </div>
  );
}
