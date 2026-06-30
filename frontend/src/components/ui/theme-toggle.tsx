"use client";
// 라이트/다크 테마 토글 버튼 (next-themes)
// 아이콘 표시는 .dark 클래스 기반 CSS(dark: 변형)로 처리 → mounted state 불필요.
// (react-hooks/set-state-in-effect / H-3 회피 + hydration mismatch 0: 두 아이콘 모두
//  DOM 에 존재하고 CSS 가시성만 .dark 로 분기. .dark 는 next-themes pre-paint 스크립트가 설정.)
import { Moon, Sun } from "lucide-react";
import { useTheme } from "next-themes";
import { cn } from "@/lib/utils";

export function ThemeToggle({ className }: { className?: string }) {
  const { setTheme } = useTheme();

  const handleToggle = () => {
    // 현재 DOM 의 실제 테마(next-themes 가 <html> 에 설정)를 읽어 반전
    const isDark = document.documentElement.classList.contains("dark");
    setTheme(isDark ? "light" : "dark");
  };

  return (
    <button
      type="button"
      onClick={handleToggle}
      aria-label="라이트/다크 테마 전환"
      title="라이트/다크 테마 전환"
      className={cn(
        "inline-flex h-11 w-11 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-muted hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
        className,
      )}
    >
      <Sun className="h-5 w-5 dark:hidden" aria-hidden="true" />
      <Moon className="hidden h-5 w-5 dark:block" aria-hidden="true" />
      <span className="sr-only">테마 전환</span>
    </button>
  );
}
