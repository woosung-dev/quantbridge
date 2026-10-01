// QuantBridge 서비스 워커 — 정본 `docs/architecture/pwa.md` §2.3 (설치 · 오프라인 안내 · 웹 푸시).
//
// ★데이터를 캐시하지 않는다. 캐시에 들어가는 것은 `/offline` 한 장과 아이콘뿐이다.
//   `/api/*`·RSC·정적 자산은 `respondWith` 하지 않는다 — 낡은 금융 숫자를 최신처럼 보이는 것이
//   이 제품이 가장 피해야 할 결함이다(PRD §1). 런타임 `cache.put` 을 넣지 마라(AC-5 가 잰다).
// ★이 파일을 바꾸면 CACHE 버전을 올린다 — activate 가 옛 버전을 지운다.

const CACHE = "qb-shell-v1";
const OFFLINE_URL = "/offline";
const FALLBACK_URL = "/dashboard";
// §2.1 아이콘 — 전부 루트 경로(하위 폴더면 proxy 가 `/sign-in` 으로 보낸다).
const PRECACHE = [
  OFFLINE_URL,
  "/icon-192.png",
  "/icon-512.png",
  "/icon-maskable-512.png",
  "/apple-icon.png",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches
      .open(CACHE)
      .then((cache) => cache.addAll(PRECACHE))
      .then(() => self.skipWaiting()),
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((names) =>
        Promise.all(
          names
            .filter((name) => name.startsWith("qb-shell-") && name !== CACHE)
            .map((name) => caches.delete(name)),
        ),
      )
      .then(() => self.clients.claim()),
  );
});

// 내비게이션만 — network-first, 실패하면 캐시의 `/offline`. 그 외 요청은 브라우저 기본 경로.
self.addEventListener("fetch", (event) => {
  if (event.request.mode !== "navigate") return;
  event.respondWith(
    fetch(event.request).catch(async () => {
      const offline = await caches.match(OFFLINE_URL, { cacheName: CACHE });
      return offline ?? Response.error();
    }),
  );
});

// §4.3 페이로드 `{title, body, url, tag}`. 파싱이 실패하면 기본 문구로 띄운다(무음 푸시 금지).
self.addEventListener("push", (event) => {
  let payload = {};
  try {
    payload = event.data ? event.data.json() : {};
  } catch {
    payload = {};
  }
  const title =
    typeof payload.title === "string" && payload.title ? payload.title : "QuantBridge 알림";
  const options = {
    body: typeof payload.body === "string" ? payload.body : "새 알림이 있습니다",
    icon: "/icon-192.png",
    badge: "/icon-192.png",
    data: { url: typeof payload.url === "string" ? payload.url : FALLBACK_URL },
  };
  if (typeof payload.tag === "string" && payload.tag) options.tag = payload.tag;
  event.waitUntil(self.registration.showNotification(title, options));
});

/** 같은 origin 경로만 연다 — 아니면 `/dashboard`(페이로드가 외부 URL 을 열게 두지 않는다). */
function sameOriginUrl(raw) {
  try {
    const url = new URL(typeof raw === "string" ? raw : FALLBACK_URL, self.location.origin);
    if (url.origin === self.location.origin) return url.href;
  } catch {
    // 아래 기본값으로 떨어진다.
  }
  return new URL(FALLBACK_URL, self.location.origin).href;
}

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const target = sameOriginUrl(event.notification.data?.url);
  event.waitUntil(
    self.clients.matchAll({ type: "window", includeUncontrolled: true }).then((windows) => {
      const open = windows.find((client) => client.url === target);
      return open ? open.focus() : self.clients.openWindow(target);
    }),
  );
});
