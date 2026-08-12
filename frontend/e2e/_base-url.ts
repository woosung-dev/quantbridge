import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const DEFAULT_FE_PORT = 3100;

function getWorktreeSlot(): number {
  const slotPaths = [
    resolve(process.cwd(), "../.worktree-slot"),
    resolve(process.cwd(), ".worktree-slot"),
  ];

  for (const slotPath of slotPaths) {
    try {
      const contents = readFileSync(slotPath, "utf8");
      const match = contents.match(/^QB_SLOT\s*=\s*(\d+)\s*$/m);
      const slot = match ? Number(match[1]) : NaN;

      if (Number.isSafeInteger(slot) && slot >= 0) {
        return slot;
      }
    } catch {
      // 다음 후보 경로를 시도한다.
    }
  }

  return 0;
}

export function getFrontendPort(): number {
  return DEFAULT_FE_PORT + getWorktreeSlot();
}

export function getBaseURL(): string {
  return process.env.PLAYWRIGHT_BASE_URL ?? `http://localhost:${getFrontendPort()}`;
}

export function hasConfiguredBaseURL(): boolean {
  return Boolean(process.env.PLAYWRIGHT_BASE_URL);
}
