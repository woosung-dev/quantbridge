# QuantBridge Frontend — 런타임 전용 이미지 (빌드는 이 안에서 하지 않는다)
#
# ★왜 멀티스테이지 빌드가 아닌가 — 서버(오라클 A1)는 2 OCPU 를 다른 프로젝트와 공유하고
#   그 위에서 [BL-003] 소크가 돌고 있다. 빌드가 CPU 를 먹으면 소크 워커가 굶는다.
#   그래서 `pnpm build` 는 맥에서 돌리고 이 이미지는 산출물만 담는다.
#   전제: `cd frontend && pnpm build` 가 선행돼 `.next/standalone` 이 존재한다.
#
# ★아키텍처 — 맥(darwin/arm64) → 서버(aarch64) 동일. `--platform linux/arm64` 로 빌드하면
#   에뮬레이션 없이 네이티브로 만들어진다.
#
# 사용법:
#   cd frontend && pnpm build
#   docker build --platform linux/arm64 -t quantbridge-frontend:<tag> .
#   docker save quantbridge-frontend:<tag> | gzip | ssh <서버> 'gunzip | docker load'
FROM node:22-alpine

WORKDIR /app

ENV NODE_ENV=production
# standalone 의 server.js 가 읽는 두 변수. HOSTNAME 을 0.0.0.0 으로 두지 않으면
# 컨테이너 안 루프백에만 바인딩돼 publish 한 포트로 못 들어온다.
ENV PORT=3000
ENV HOSTNAME=0.0.0.0

# ★복사 순서가 곧 구조다 — standalone 은 server.js + 최소 node_modules 만 담고
#   정적 자산(.next/static)과 public 은 별도로 얹어야 한다(Next 공식 규약).
COPY .next/standalone ./
COPY .next/static ./.next/static
COPY public ./public

EXPOSE 3000

CMD ["node", "server.js"]
