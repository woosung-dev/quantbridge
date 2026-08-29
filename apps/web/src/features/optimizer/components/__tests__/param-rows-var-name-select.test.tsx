import { render, screen, within } from "@testing-library/react";
import { useForm } from "react-hook-form";
import { describe, expect, it } from "vitest";

import type { InputDecl } from "@/features/strategy/schemas";

import { ParamRowsFieldset } from "../param-rows-fieldset";

type FormValues = {
  parameters: Array<{
    var_name: string;
    min: string;
    max: string;
    step: string;
  }>;
};

const EMPTY_ROW = { var_name: "", min: "5", max: "30", step: "1" };

function TestForm({ inputs }: { inputs?: InputDecl[] }) {
  const form = useForm<FormValues>({
    defaultValues: { parameters: [EMPTY_ROW] },
  });

  return (
    <ParamRowsFieldset
      control={form.control}
      register={form.register}
      errors={form.formState.errors}
      legend="파라미터"
      inputs={inputs}
      emptyRow={EMPTY_ROW}
      renderRowCells={(_idx, removeButton) => <div>{removeButton}</div>}
    />
  );
}

const INPUTS: InputDecl[] = [
  { var_name: "length", input_type: "int", defval: "14", title: "기간" },
  { var_name: "source", input_type: "source", defval: "close", title: "소스" },
  { var_name: "threshold", input_type: "float", defval: "1.5", title: null },
];

describe("ParamRowsFieldset var_name 선택", () => {
  it("inputs가 있으면 var_name을 select로 표시하고 모든 선언을 옵션으로 남긴다", () => {
    render(<TestForm inputs={INPUTS} />);

    const select = screen.getByRole("combobox", { name: "변수 이름" });
    expect(select).toHaveValue("");
    expect(within(select).getAllByRole("option")).toHaveLength(4);
    expect(within(select).getByRole("option", { name: "length · 기간" })).toHaveValue("length");
    expect(within(select).getByRole("option", { name: "threshold" })).toHaveValue("threshold");
  });

  it("스윕 불가 input도 input_type 사유와 함께 비활성 옵션으로 남긴다", () => {
    render(<TestForm inputs={INPUTS} />);

    const select = screen.getByRole("combobox", { name: "변수 이름" });
    const unsupported = within(select).getByRole("option", {
      name: "source · 소스 (source: 스윕 불가)",
    });
    expect(unsupported).toBeDisabled();
  });

  it("inputs가 비면 기존 자유 입력을 유지한다", () => {
    render(<TestForm inputs={[]} />);

    expect(screen.getByPlaceholderText("변수 이름 (예: length)")).toBeInTheDocument();
    expect(screen.queryByRole("combobox", { name: "변수 이름" })).not.toBeInTheDocument();
  });
});
