// shadcn Input — DESIGN.md §7.3 + §8.1 토큰 정합 (transition 200ms / focus ring primary)
import * as React from "react"
import { Input as InputPrimitive } from "@base-ui/react/input"

import { cn } from "@/lib/utils"

function Input({ className, type, ...props }: React.ComponentProps<"input">) {
  return (
    <InputPrimitive
      type={type}
      data-slot="input"
      className={cn(
        // DESIGN.md §7.3: Input min-height 48px (WCAG 터치) + radius-sm 6px (rounded-sm)
        // DESIGN.md §8.1 transition 200ms ease (border-color + ring + bg) — motion-reduce 자동 비활성
        "h-12 w-full min-w-0 rounded-sm border border-input bg-transparent px-3 py-2 text-base transition-[color,border-color,box-shadow,background-color] duration-200 ease-out outline-none file:inline-flex file:h-8 file:border-0 file:bg-transparent file:text-sm file:font-medium file:text-foreground placeholder:text-muted-foreground hover:border-border-dark focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 disabled:pointer-events-none disabled:cursor-not-allowed disabled:bg-input/50 disabled:opacity-50 aria-invalid:border-destructive aria-invalid:ring-3 aria-invalid:ring-destructive/20 motion-reduce:transition-none md:text-sm dark:bg-input/30 dark:disabled:bg-input/80 dark:aria-invalid:border-destructive/50 dark:aria-invalid:ring-destructive/40",
        className
      )}
      {...props}
    />
  )
}

export { Input }
