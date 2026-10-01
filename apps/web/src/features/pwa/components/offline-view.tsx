// 오프라인 안내 화면 본문 — 서비스 워커가 내비게이션 실패 시 내주는 캐시 사본(pwa.md §2.4).
// 서버 fetch 0 · 인증 0 · 클라이언트 JS 0. ★JS 0 이 요점이다: 오프라인에서 캐시 HTML 이 열리면
//   `/_next/static` 청크는 못 받아 하이드레이션이 안 된다. 그래서 새로고침은 onClick 이 아니라
//   **`href=""` 링크**다 — 빈 상대 URL 은 현재 문서 주소(쿼리 포함, 프래그먼트 제외)로 풀려
//   그 주소로 다시 내비게이션한다(→ SW network-first). 주소창은 사용자가 가려던 경로 그대로다
//   (SW 가 응답만 바꿔 준다). ★GET 폼으로 되돌리지 마라 — 이름 없는 폼 제출은 쿼리를 `?` 로 지운다.

import { RefreshCwIcon, WifiOff } from "lucide-react";

export function OfflineView() {
  return (
    <main id="main-content" className="page">
      <section className="section" aria-labelledby="offline-heading">
        <div className="state-box">
          <WifiOff aria-hidden="true" />
          <h1 id="offline-heading" className="section-title">
            오프라인 상태입니다
          </h1>
          <p className="section-desc">연결되면 다시 시도하세요</p>
          <a
            className="btn btn-primary"
            // ★`useValidAnchor` 는 `href="#"` 처럼 **버튼 노릇을 하는 가짜 링크**를 막는 규칙이다. 이 링크는
            //   진짜 내비게이션이고, 쿼리를 보존하며 현재 주소를 다시 여는 상대 URL 은 빈 문자열뿐이다
            //   (`?`·`.` 는 쿼리·경로를 바꾼다). JS 0 이라 `location.reload()` 도 못 쓴다.
            // biome-ignore lint/a11y/useValidAnchor: 위 근거 — 빈 href = 현재 URL(쿼리 포함) 재요청.
            href=""
          >
            <RefreshCwIcon aria-hidden="true" />
            새로고침
          </a>
        </div>
      </section>
    </main>
  );
}
