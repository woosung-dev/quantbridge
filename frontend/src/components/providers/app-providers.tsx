import { ClerkProvider } from "@clerk/nextjs";
import type { ReactNode } from "react";
import { QueryProvider } from "./query-provider";

// 앱 레벨 Provider 체인 — ClerkProvider가 바깥, React Query가 안쪽
export function AppProviders({ children }: { children: ReactNode }) {
  return (
    <ClerkProvider>
      <QueryProvider>{children}</QueryProvider>
    </ClerkProvider>
  );
}
