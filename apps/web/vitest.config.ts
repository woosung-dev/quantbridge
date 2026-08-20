import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import { fileURLToPath } from "node:url";
import path from "node:path";

const dirname = path.dirname(fileURLToPath(import.meta.url));

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./tests/setup.ts"],
    include: ["src/**/*.{test,spec}.{ts,tsx}", "tests/**/*.{test,spec}.{ts,tsx}"],
    css: true,
    // ★2026-08-11 — FE 커버리지는 여기 배선되기 전까지 **측정 자체가 없었다**(BE 는 CI 90%
    //   래칫이 있다). 이 회차는 **측정만** 한다.
    //
    // ★★`thresholds` 를 넣지 마라. 첫 수치가 낮으면 형식이 되고 높으면 판별력이 없다.
    //   문턱은 다음 회차가 실측 분포를 보고 정한다.
    //
    // `all` 기본값(true) 을 그대로 쓴다 — 테스트가 한 번도 import 하지 않은 파일까지
    //   0% 로 분모에 넣는다. 이게 없으면 「테스트가 건드린 파일만」 재게 되어 커버리지가
    //   올라갈수록 분모가 커지는 역설이 생기고, 새 미커버 파일을 추가해도 수치가
    //   안 내려간다(= 판별력 0). 실측 음성 대조로 확인했다.
    coverage: {
      provider: "v8",
      reporter: ["text-summary", "json-summary"],
      include: ["src/**/*.{ts,tsx}"],
      exclude: ["src/**/*.d.ts", "src/**/*.{test,spec}.{ts,tsx}", "src/**/__tests__/**"],
    },
  },
  resolve: {
    alias: {
      "@": path.resolve(dirname, "./src"),
      // ★`server-only` 는 vitest 에서 top-level throw 다(exports 맵이 `react-server` 조건에서만
      //   빈 모듈을 준다). `vi.mock` 으로는 못 막는다 — CJS 외부화라 Node 의 require 가 먼저 돈다.
      //   근거·범위는 `tests/stubs/server-only.ts` 헤더에 있다.
      "server-only": path.resolve(dirname, "./tests/stubs/server-only.ts"),
    },
  },
});
