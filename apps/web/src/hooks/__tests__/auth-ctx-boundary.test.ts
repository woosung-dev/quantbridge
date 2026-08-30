import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { describe, expect, it } from "vitest";

const WEB_ROOT = resolve(__dirname, "../../..");

describe("AuthCtx 공급자 경계", () => {
  it("AccountButton은 Better Auth useSession 대신 AuthCtx seam만 사용한다", () => {
    const source = readFileSync(
      resolve(WEB_ROOT, "src/components/layout/account-button.tsx"),
      "utf-8",
    );

    expect(source).toContain('import { useAuthCtx } from "@/hooks/use-auth-ctx";');
    expect(source).not.toContain("useSession");
  });
});
