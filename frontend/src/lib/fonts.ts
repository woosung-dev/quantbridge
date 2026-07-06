// next/font 로더 SSOT — Precision Instrument 타이포 (Archivo 디스플레이 / IBM Plex Mono 숫자)
//
// 모듈로 분리하는 이유: Monaco 에디터는 CSS 변수를 캔버스 글리프 측정에서 해석하지
// 못해 `ibmPlexMono.style.fontFamily`(next/font 가 생성한 해시 family 문자열)를
// 직접 받아야 한다 (components/monaco/pine-editor.tsx 소비).
// 본문(Pretendard Variable)은 next/font 가 아니라 pretendard 패키지의
// dynamic-subset CSS 로 로드 — globals.css @import 참조 (2.3MB 단일 preload 회피).

import { Archivo, IBM_Plex_Mono } from "next/font/google";

export const archivo = Archivo({
  subsets: ["latin"],
  weight: ["500", "600", "700"],
  variable: "--font-archivo",
  display: "swap",
});

export const ibmPlexMono = IBM_Plex_Mono({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  variable: "--font-mono-code",
  display: "swap",
});
