// Sonner Toaster 래퍼 — Sprint 44 W C3: theme="light" 고정 (LESSON-054 mental model 일관성).
// duration 표준 (success 3000 / error 5000), entrance/close hover 는 globals.css .cn-toast 에서 처리.
"use client"

import { Toaster as Sonner, type ToasterProps } from "sonner"
import { CircleCheckIcon, InfoIcon, TriangleAlertIcon, OctagonXIcon, Loader2Icon } from "lucide-react"

const Toaster = ({ ...props }: ToasterProps) => {
  return (
    <Sonner
      // light theme 고정 — 단일 페이지 다크 절대 금지 (LESSON-054).
      // useTheme 의존 제거 (system → dark 변환 시 mental model drift).
      theme="light"
      className="toaster group"
      icons={{
        success: (
          <CircleCheckIcon className="size-4" />
        ),
        info: (
          <InfoIcon className="size-4" />
        ),
        warning: (
          <TriangleAlertIcon className="size-4" />
        ),
        error: (
          <OctagonXIcon className="size-4" />
        ),
        loading: (
          <Loader2Icon className="size-4 animate-spin" />
        ),
      }}
      style={
        {
          "--normal-bg": "var(--popover)",
          "--normal-text": "var(--popover-foreground)",
          "--normal-border": "var(--border)",
          "--border-radius": "var(--radius-md)",
        } as React.CSSProperties
      }
      toastOptions={{
        // duration 표준: success/info/loading 은 sonner 기본(4000) 보다 짧게, error/warning 은 길게.
        // type 별 기본 = props 로 override 가능. close button hover 는 globals.css .cn-toast 처리.
        duration: 3000,
        classNames: {
          toast: "cn-toast",
          error: "cn-toast",
          success: "cn-toast",
          warning: "cn-toast",
          info: "cn-toast",
        },
      }}
      {...props}
    />
  )
}

export { Toaster }
