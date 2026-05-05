"use client";

// Sprint 33 BL-164 — UUID/raw value 노출 차단용 통일 Select 헬퍼.
//
// 문제:
//   base-ui `<Select.Value>` 는 raw value (UUID 등) 를 그대로 표시한다.
//   render prop 으로 매핑할 수 있지만 호출처마다 패턴이 분기되어
//   미적용 시 사용자에게 UUID 가 노출되는 회귀 위험이 상시 존재.
//
// 해결:
//   options(value+label) 를 받아 trigger 에서 label, content 에서도 label 을
//   동일하게 렌더하는 헬퍼. render prop 캡슐화로 호출처 실수를 차단.
//
// 사용:
//   <SelectWithDisplayName
//     options={strategies.map((s) => ({ value: s.id, label: s.name }))}
//     value={field.value}
//     onValueChange={field.onChange}
//     placeholder="전략 선택"
//     emptyMessage="전략 없음 — 먼저 등록해주세요"
//     ariaLabel="전략 선택"
//   />
//
// 비고:
//   - react-hook-form `Controller`/`FormField` 와 호환되도록 value/onValueChange
//     를 외부 API 로 노출.
//   - `triggerTestId` 로 테스트 hook (default: 미설정).
//   - `disabled` 옵션은 base-ui SelectItem 의 native disabled prop 으로 매핑.

import * as React from "react";

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

export type SelectOption = {
  value: string;
  label: string;
  disabled?: boolean;
};

export type SelectWithDisplayNameProps = {
  options: ReadonlyArray<SelectOption>;
  value: string;
  onValueChange: (value: string) => void;
  placeholder: string;
  /** options 가 빈 배열일 때 비활성 항목으로 표시할 안내 문구. */
  emptyMessage?: string;
  /** trigger 에 부여할 className. */
  className?: string;
  /** trigger 의 data-testid (테스트용 hook). */
  triggerTestId?: string;
  /** trigger 의 접근성 라벨. FormLabel 이 별도면 생략 가능. */
  ariaLabel?: string;
  /** 비활성화. */
  disabled?: boolean;
  /**
   * 제공 시 선택 값이 있을 때 ✕ 버튼을 렌더한다.
   * 호출자가 nullable/optional 동선을 소유 — 이 컴포넌트는 전달만 한다.
   * BL-176: sentinel/nullable 변환 없이 clear 동선 추가.
   */
  onClear?: () => void;
  /** onClear 버튼의 접근성 라벨 (기본: "선택 해제"). */
  clearAriaLabel?: string;
};

/**
 * UUID/raw value 노출을 차단하는 통일 Select 컴포넌트.
 *
 * `<SelectValue>` 의 render prop 을 내부에 캡슐화하여
 * options 배열의 label 을 trigger 에 표시한다.
 */
export function SelectWithDisplayName({
  options,
  value,
  onValueChange,
  placeholder,
  emptyMessage,
  className,
  triggerTestId,
  ariaLabel,
  disabled,
  onClear,
  clearAriaLabel = "선택 해제",
}: SelectWithDisplayNameProps) {
  // value → label 빠른 조회. options 길이가 짧으므로 매 render O(N) 도 무방.
  const selectedLabel = React.useMemo(
    () => options.find((opt) => opt.value === value)?.label,
    [options, value],
  );

  // base-ui onValueChange 시그니처: (v: string | null) → 외부에는 string 만 노출.
  // Sprint 33 BL-176 hotfix (dogfood Day 6 발견): v=null 은 base-ui 의 transient
  // clear/uncontrolled state. null → "" 변환 시 form 의 zod UUID schema 가
  // invalid_format ZodError raise (`exchange_account_id` 등). null 시 callback
  // skip 하여 form 의 prior valid value 보존. 사용자 의도적 unset 은 별도 clear
  // 버튼 추가가 정합 (현재 form 은 unset 동선 X).
  const handleValueChange = React.useCallback(
    (v: string | null) => {
      if (v === null) return;
      onValueChange(v);
    },
    [onValueChange],
  );

  const showClearButton = Boolean(onClear) && Boolean(value);

  return (
    <div className="relative flex items-center">
      <Select
        value={value}
        onValueChange={handleValueChange}
        disabled={disabled}
      >
        <SelectTrigger
          className={showClearButton ? `pr-8 ${className ?? ""}`.trim() : className}
          data-testid={triggerTestId}
          aria-label={ariaLabel}
        >
          {/* render prop 캡슐화 — UUID 노출 자동 차단.
              value 가 비어있거나 options 에서 못 찾으면 placeholder 표시. */}
          <SelectValue placeholder={placeholder}>
            {() => selectedLabel ?? placeholder}
          </SelectValue>
        </SelectTrigger>
        <SelectContent>
          {options.length === 0 && emptyMessage ? (
            <SelectItem value="__empty__" disabled>
              {emptyMessage}
            </SelectItem>
          ) : (
            options.map((opt) => (
              <SelectItem key={opt.value} value={opt.value} disabled={opt.disabled}>
                {opt.label}
              </SelectItem>
            ))
          )}
        </SelectContent>
      </Select>
      {showClearButton && (
        <button
          type="button"
          aria-label={clearAriaLabel}
          data-testid={triggerTestId ? `${triggerTestId}-clear` : undefined}
          className="absolute right-8 flex h-4 w-4 items-center justify-center rounded-full text-muted-foreground hover:text-foreground focus:outline-none"
          onClick={(e) => {
            e.stopPropagation();
            onClear?.();
          }}
        >
          ✕
        </button>
      )}
    </div>
  );
}
