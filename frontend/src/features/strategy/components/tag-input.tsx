"use client";

// Sprint FE-D: chip-style tag input.
// Controlled — Enter / comma / Tab 으로 chip 추가, Backspace(빈 input) 로 마지막 chip 제거.
// shadcn 토큰 (border / ring / input) 사용, 하드코딩 색상 금지.

import { useState, type KeyboardEvent } from "react";
import { XIcon } from "lucide-react";

import { cn } from "@/lib/utils";

export interface TagInputProps {
  value: string[];
  onChange: (next: string[]) => void;
  placeholder?: string;
  maxTags?: number;
  id?: string;
  className?: string;
}

export function TagInput({
  value,
  onChange,
  placeholder,
  maxTags,
  id,
  className,
}: TagInputProps) {
  const [draft, setDraft] = useState("");

  const commit = (): boolean => {
    const trimmed = draft.trim();
    if (trimmed.length === 0) return false;
    if (value.includes(trimmed)) {
      setDraft("");
      return false;
    }
    if (typeof maxTags === "number" && value.length >= maxTags) {
      return false;
    }
    onChange([...value, trimmed]);
    setDraft("");
    return true;
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key === "Enter" || event.key === ",") {
      event.preventDefault();
      commit();
      return;
    }
    if (event.key === "Tab") {
      if (draft.trim().length > 0) {
        event.preventDefault();
        commit();
      }
      return;
    }
    if (event.key === "Backspace" && draft === "" && value.length > 0) {
      event.preventDefault();
      onChange(value.slice(0, -1));
    }
  };

  const removeAt = (index: number) => {
    onChange(value.filter((_, i) => i !== index));
  };

  return (
    <div
      role="group"
      aria-label="태그"
      className={cn(
        "flex flex-wrap items-center gap-2 rounded-[var(--radius-md)] border border-input bg-transparent px-3 py-2 text-sm shadow-xs focus-within:ring-2 focus-within:ring-ring focus-within:ring-offset-2",
        className,
      )}
    >
      {value.map((tag, index) => (
        <span
          key={`${tag}-${index}`}
          data-slot="tag-chip"
          className="inline-flex items-center gap-1 rounded-full bg-secondary px-2 py-0.5 text-xs font-medium text-secondary-foreground"
        >
          <span>{tag}</span>
          <button
            type="button"
            aria-label={`${tag} 태그 제거`}
            onClick={() => removeAt(index)}
            className="inline-flex size-4 items-center justify-center rounded-full text-secondary-foreground/70 transition-colors hover:bg-secondary-foreground/10 hover:text-secondary-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            <XIcon aria-hidden className="size-3" />
          </button>
        </span>
      ))}
      <input
        id={id}
        type="text"
        value={draft}
        placeholder={value.length === 0 ? placeholder : undefined}
        onChange={(event) => setDraft(event.target.value)}
        onKeyDown={handleKeyDown}
        onBlur={() => {
          if (draft.trim().length > 0) commit();
        }}
        className="min-w-[120px] flex-1 bg-transparent text-sm outline-none placeholder:text-muted-foreground"
      />
    </div>
  );
}
