// [BL-797] `screen-evidence-lib.mjs` 의 타입 선언.
//
// ★왜 `.d.mts` 인가. 이 레포의 `tsconfig.json` 은 `allowJs: false` 라 `.ts` 테스트가 `.mjs` 를
//   그냥 import 하면 typecheck 가 깨진다. 그렇다고 라이브러리를 `.ts` 로 쓰면 오케스트레이터
//   (`node scripts/screen-evidence.mjs`)가 로더 없이 못 읽는다. `moduleResolution: "bundler"` 는
//   `foo.mjs` 를 볼 때 `foo.d.mts` 를 먼저 찾으므로 이 파일이 그 틈을 메운다.
export interface RouteMetrics {
  firstLoadBytes: number;
  /** `null` = 대조 제외(authed — 실측상 비결정. 자세한 근거는 `screen-evidence-shared.ts`). */
  apiRequests: number | null;
  /** `null` = 대조 제외. 계수기 생존 검사는 spec 의 `> 0` 앵커가 진다. */
  totalRequests: number | null;
  /** 스냅샷 파일 이름. `null` = **수치 전용 라우트**(화면 축을 재지 않는다 — [BL-797] authed). */
  screenshot: string | null;
  /** 로그인 상태로 잰 라우트인가. 러너가 leg 범위를 가르는 데 쓴다([BL-797]). */
  authed?: boolean;
}

export interface ScreenshotRef {
  basePath: string;
  headPath: string;
  changed: boolean;
}

export interface ReportRow {
  route: string;
  screen: string;
  bundle: string;
  apiRequests: string;
  totalRequests: string;
  changed: boolean;
}

export const MIN_ROWS: number;
export function formatKb(bytes: unknown): string;
export function formatKbDelta(before: unknown, after: unknown): string;
export function formatCountDelta(before: unknown, after: unknown): string;
export function blobUrl(repoSlug: string, ref: string, filePath: string): string;
export function buildReport(input: {
  before: Record<string, RouteMetrics>;
  after: Record<string, RouteMetrics>;
  /** `null` 값 = 수치 전용 라우트. **키 자체의 부재는 에러**다(측정 실패와 구분한다). */
  screenshots: Record<string, ScreenshotRef | null>;
  repoSlug: string;
  baseRef: string;
  headRef: string;
  notes?: string[];
}): { markdown: string; rows: ReportRow[]; changedCount: number };
