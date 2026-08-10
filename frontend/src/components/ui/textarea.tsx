// shadcn/ui 생성 원본 Textarea 컴포넌트 — 네이티브 <textarea> 를 그대로 감싼다.
// 이 레포에서 min-height 를 96px(min-h-24)로 오버라이드했다(Sprint 7c T1, 아래 인라인 주석 근거).
import * as React from "react"

import { cn } from "@/lib/utils"

function Textarea({ className, ...props }: React.ComponentProps<"textarea">) {
  return (
    <textarea
      data-slot="textarea"
      className={cn(
        // DESIGN.md: Textarea min-height 96px — Sprint 7c T1 오버라이드
        "flex field-sizing-content min-h-24 w-full rounded-md border border-input bg-transparent px-3 py-2 text-base transition-colors outline-none placeholder:text-muted-foreground focus-visible:border-ring focus-visible:ring-2 focus-visible:ring-ring/40 disabled:cursor-not-allowed disabled:bg-input/50 disabled:opacity-50 aria-invalid:border-destructive aria-invalid:ring-2 aria-invalid:ring-destructive/20 md:text-sm dark:bg-input/30 dark:disabled:bg-input/80 dark:aria-invalid:border-destructive/50 dark:aria-invalid:ring-destructive/40",
        className
      )}
      {...props}
    />
  )
}

export { Textarea }
