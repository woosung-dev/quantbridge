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
  /**
    * 측정 창 안에서 브라우저가 낸 `/api/v1/` 요청 건수.
    * ★`null` = **대조하지 않는다**(측정을 안 했다는 뜻이 아니다). authed 라우트가 그렇다 —
    *   아래 `totalRequests` 주석의 실측 참조.
    */
  apiRequests: number | null;
  /**
   * 측정 창 안의 **전체** 요청 건수. 계수기 생존 앵커 겸 화면의 총 대가.
   * ★★`null` = 대조 제외. 2026-08-18 실측이 그것을 강제했다 — 같은 커밋·같은 빌드로 연속 2회
   *   재면 authed 라우트의 요청 수가 **±1 로 흔들린다**(`/backtests` 5→4 · `/optimizer` 5→6).
   *   같은 실행에서 `firstLoadBytes` 는 **비트 단위로 같았다**(371891→371891 · 414513→414513).
   *   ⇒ 원장이 「번들 + 요청 수」로 적어 둔 authed 축은 **번들만** 성립한다. 요청 수를 그대로
   *   대조하면 게이트가 매 실행 거짓 red 를 내고, 그러면 사람이 게이트를 끈다.
   *   ★계수기가 죽는 것은 spec 의 `> 0` 하드 앵커가 막는다 — **버리는 것은 「정확한 수」의
   *   대조뿐이고 「셌다는 사실」은 여전히 검사한다.**
   */
  totalRequests: number | null;
  /**
   * 스냅샷 파일 이름 (플랫폼 접미 제외).
   * ★`null` = **수치 전용 라우트** — 화면 축을 재지 않는다([BL-797] authed 확장). authed 화면은
   *   실데이터가 픽셀을 흔들어 `maxDiffPixels: 0` 과 상극이라 번들 바이트와 요청 수만 잰다.
   */
  screenshot: string | null;
  /**
   * 이 라우트를 로그인 상태로 쟀는가.
   * ★baseline 에 남는 이유는 **러너가 leg 범위를 알아야** 하기 때문이다 — 공개 전용 실행이
   *   authed 행까지 「안 쟀다」로 잡아 죽거나, 반대로 `:update` 가 그 행을 지우면 안 된다.
   */
  authed?: boolean;
}

/** 측정 대상 라우트 하나. */
export interface RouteCase {
  /** baseline JSON 의 키이자 표의 행 이름. */
  path: string;
  /**
   * 스냅샷 파일 이름(확장자 제외). 경로 구분자를 못 쓰므로 따로 둔다.
   * ★`null` = **수치 전용** — 화면 축을 재지 않는다. authed 라우트가 그렇다.
   */
  slug: string | null;
  /** 이 실행이 실제로 그 화면을 그렸다는 증거. 없으면 「변화 없음」이 아니라 **측정 실패**다. */
  anchor: string;
  /**
   * 로그인 상태로 재는 라우트인가.
   * ★켜면 두 앵커가 추가된다 — ⑴ 최종 pathname 이 `path` 와 같아야 한다(세션이 없으면
   *   `proxy.ts` 가 `/sign-in` 으로 튕기는데, 그 화면도 제목에 "QuantBridge" 가 있어
   *   제목 앵커만으로는 **로그인 실패를 못 가린다**) ⑵ `/api/v1/` 요청이 1건 이상이어야 한다
   *   (데이터 화면이 API 를 한 번도 안 부를 수 없다 — 공개 라우트의 실측 0 과 대칭을 이루는
   *   authed 쪽 계수기 생존 앵커다).
   */
  authed?: boolean;
}
