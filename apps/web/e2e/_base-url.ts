import { lstatSync, readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";

const DEFAULT_FE_PORT = 3100;

function getWorktreeSlot(): number {
  let currentPath = resolve(process.cwd());

  while (true) {
    const slotPath = resolve(currentPath, ".worktree-slot");
    try {
      const contents = readFileSync(slotPath, "utf8");
      const match = contents.match(/^QB_SLOT\s*=\s*(\d+)\s*$/m);
      const slot = match ? Number(match[1]) : NaN;

      if (Number.isSafeInteger(slot) && slot >= 0) {
        return slot;
      }
    } catch {
      // 다음 상위 경로를 시도한다.
    }

    try {
      lstatSync(resolve(currentPath, ".git"));
      break;
    } catch {
      // 저장소 경계를 아직 찾지 못했다.
    }

    const parentPath = dirname(currentPath);
    if (parentPath === currentPath) {
      break;
    }

    currentPath = parentPath;
  }

  return 0;
}

export function getFrontendPort(): number {
  return DEFAULT_FE_PORT + getWorktreeSlot();
}

function getConfiguredBaseURL(): string | undefined {
  const configuredBaseURL = process.env.PLAYWRIGHT_BASE_URL;
  return configuredBaseURL ? configuredBaseURL : undefined;
}

export function getBaseURL(): string {
  return getConfiguredBaseURL() ?? `http://localhost:${getFrontendPort()}`;
}

export function hasConfiguredBaseURL(): boolean {
  return getConfiguredBaseURL() !== undefined;
}
