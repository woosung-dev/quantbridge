// [BL-797] 화면 증거 팩 — spec 이 쓰는 경로·타입. 값의 정본은 `screen-evidence.config.json` 이다.
import path from "node:path";

import config from "./screen-evidence.config.json";

/** `apps/web` 절대경로. spec 이 어느 cwd 에서 불려도 같은 곳을 가리켜야 한다. */
export const WEB_ROOT = path.resolve(__dirname, "..");

export const BASELINE_PATH = path.resolve(WEB_ROOT, config.baseline);
export const MEASURED_DIR_NAME = config.measuredDir;

/**
 * 회차별 산출 디렉터리 (AC-1 — 산출물 경로가 결정적이어야 한다).
 *
 * ★`PW_ARTIFACT_RUN` 을 그대로 쓴다. playwright 의 `outputDir` 겹과 같은 값으로 묶어 두면
 *   한 회차의 trace·스크린샷·측정 JSON 이 한 폴더에 모이고, 다음 회차가 그것을 안 지운다
 *   ([LESSON-117] — 「한 번 더 돌려 확인」이 앞선 실패의 증거를 파괴한 사고).
 */
export function evidenceRunDir(): string {
  const raw = process.env.PW_ARTIFACT_RUN?.trim();
  const run = raw ? raw.replace(/[^A-Za-z0-9._-]/g, "-") : "local";
  return path.resolve(WEB_ROOT, config.outputRoot, /^\.+$/.test(run) ? "-" : run);
}

export interface RouteMetrics {
  /**
   * 그 화면이 받은 `/_next/static/**.{js,css}` 의 **전송 바이트** 합.
   * ★`content-length` 가 아니다 — Next 는 정적 자산을 gzip 청크로 보내서 그 헤더가 안 붙는다.
   *   playwright 의 `request().sizes().responseBodySize`(회선을 지난 바이트)를 쓴다.
   */
  firstLoadBytes: number;
  /** 측정 창 안에서 브라우저가 낸 `/api/v1/` 요청 건수. */
  apiRequests: number;
  /** 측정 창 안의 **전체** 요청 건수. 계수기 생존 앵커 겸 화면의 총 대가. */
  totalRequests: number;
  /** 스냅샷 파일 이름 (플랫폼 접미 제외). */
  screenshot: string;
}
