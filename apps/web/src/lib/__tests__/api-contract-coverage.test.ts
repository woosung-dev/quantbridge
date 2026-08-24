import { existsSync, readdirSync } from "node:fs";
import { resolve } from "node:path";

import { describe, expect, it } from "vitest";

const FEATURES_ROOT = resolve(__dirname, "../../features");
const CONTRACT_TEST_PATH = "__tests__/api-contract.test.ts";

// 빈 배열이 정상이다. 면제할 feature를 추가할 때는 이유를 바로 위에 남긴다.
// ★비어 있는 동안 「allowlist 의 feature 가 실재한다」 검사를 두지 마라 — 빈 배열을 필터하면
//   결과가 **언제나** `[]` 라 판별력이 0이다(2026-08-24 제거). 항목이 생기면 함께 되살려라.
const _ALLOWLIST_NO_CONTRACT: readonly string[] = [];

type FeatureSnapshot = {
  featureNames: string[];
  apiFeatureNames: string[];
};

function readFeatureSnapshot(): FeatureSnapshot {
  const featureNames = readdirSync(FEATURES_ROOT, { withFileTypes: true })
    .filter((entry) => entry.isDirectory())
    .map((entry) => entry.name)
    .sort();

  const apiFeatureNames = featureNames.filter((featureName) =>
    existsSync(resolve(FEATURES_ROOT, featureName, "api.ts")),
  );

  return { featureNames, apiFeatureNames };
}

function missingContractTests(snapshot: FeatureSnapshot): string[] {
  return snapshot.apiFeatureNames.filter(
    (featureName) =>
      !_ALLOWLIST_NO_CONTRACT.includes(featureName) &&
      !existsSync(resolve(FEATURES_ROOT, featureName, CONTRACT_TEST_PATH)),
  );
}

describe("feature API 계약 테스트 커버리지 가드", () => {
  it("feature와 api.ts 대상 디렉터리를 실제로 스캔한다", () => {
    const snapshot = readFeatureSnapshot();

    expect(snapshot.featureNames.length).toBeGreaterThanOrEqual(10);
    expect(snapshot.apiFeatureNames.length).toBeGreaterThanOrEqual(5);
  });

  it("api.ts를 가진 모든 feature에는 계약 테스트가 있다", () => {
    expect(missingContractTests(readFeatureSnapshot())).toEqual([]);
  });
});
