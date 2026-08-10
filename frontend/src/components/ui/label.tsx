// shadcn/ui(base-nova 프리셋) 생성 원본 Label 컴포넌트 — Base UI 에는 별도 Label
// primitive 가 없어(Field.Label 로만 존재) 네이티브 <label> 을 그대로 감싼다.
// 이 레포에서 별도 커스터마이즈 없음.
"use client"

import * as React from "react"

import { cn } from "@/lib/utils"

function Label({ className, ...props }: React.ComponentProps<"label">) {
  return (
    <label
      data-slot="label"
      className={cn(
        "flex items-center gap-2 text-sm leading-none font-medium select-none group-data-[disabled=true]:pointer-events-none group-data-[disabled=true]:opacity-50 peer-disabled:cursor-not-allowed peer-disabled:opacity-50",
        className
      )}
      {...props}
    />
  )
}

export { Label }
