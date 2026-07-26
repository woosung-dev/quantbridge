# cmux와 함께 사용하기

> [cmux](https://github.com/manaflow-ai/cmux) — AI 코딩 에이전트 전용 macOS 터미널.
> Ghostty 기반 네이티브 앱. 알림 링 + 내장 브라우저 + Socket API. "터미널을 AI 에이전트 시대에 맞게 재설계."

## 설치

```bash
# Homebrew (권장)
brew tap manaflow-ai/cmux
brew install --cask cmux

# 업데이트
brew upgrade --cask cmux
```

또는 [DMG 다운로드](https://github.com/manaflow-ai/cmux/releases/latest/download/cmux-macos.dmg) 후 응용 프로그램 폴더로 드래그.

요구사항: macOS 14.0 이상 (Apple Silicon / Intel)

## cmux를 쓰는 이유

여러 AI 에이전트를 동시에 돌릴 때, 기존 터미널로는 **"어떤 에이전트가 뭘 기다리는지"** 파악이 어렵습니다.
cmux는 이 문제를 GUI 레벨에서 해결합니다:

- **알림 링** — 에이전트 입력 대기 시 패널에 파란색 링 표시
- **내장 브라우저** — AI가 직접 브라우저를 조작 (클릭, 폼 입력, JS 실행)
- **Socket API / CLI** — 프로그래밍 방식으로 터미널 제어

## 3계층 구조

```
Workspace (워크스페이스) ─ 프로젝트 단위
  └── Tab/Surface (탭) ─ 탭처럼 전환
       └── Pane (페인) ─ 화면 분할
```

## 핵심 단축키

| 기능 | 단축키 |
|------|--------|
| 새 워크스페이스 | `Cmd + N` |
| 새 탭 | `Cmd + T` |
| 수평 분할 (좌우) | `Cmd + D` |
| 수직 분할 (상하) | `Cmd + Shift + D` |
| 내장 브라우저 열기 | `Cmd + Shift + L` |
| 알림 패널 | `Cmd + I` |
| 최근 알림으로 이동 | `Cmd + Shift + U` |

## 핵심 기능

### 알림 시스템

여러 에이전트에게 동시에 작업을 시켜놓으면:
- 작업 완료 시 **탭이 반짝임**
- 상단 알림 탭에서 **진행 상황 및 결과 요약**
- macOS 네이티브 데스크톱 알림 지원

### 내장 브라우저

크로미움 기반 브라우저가 터미널 내부에 탑재:
- 개발자 도구 사용 가능
- AI 에이전트에게 **브라우저 제어권 위임** 가능
- 예: "특정 문서 페이지에 접속해서 내용 캡처해서 정리해줘"

### CLI 제어

```bash
cmux tree                  # 현재 워크스페이스/페인 구조 확인
cmux workspace create      # 워크스페이스 생성
cmux send-keys             # 특정 페인에 키 입력 전달
```

에이전트가 `cmux` 명령어를 사용하여 다른 워크스페이스의 로그를 읽어오는 등 **세션 간 컨텍스트 공유**가 가능합니다.

### Claude Code Teams 지원

```bash
cmux claude-teams          # 팀 모드 한 명령으로 실행
```

팀메이트가 네이티브 분할로 생성되며, 사이드바 메타데이터와 알림이 표시됩니다.

### SSH 원격 지원

```bash
cmux ssh user@remote       # 원격 워크스페이스 생성
```

브라우저 패인이 원격 네트워크를 통해 라우팅되어 `localhost`가 정상 동작합니다.

## 한계점

- **세션 영속성 없음** — 터미널을 닫으면 레이아웃은 복원되지만 실행 중이던 프로세스는 종료
- **macOS 전용** — Windows, Linux 미지원
- **초기 버전** — 아직 불안정한 부분 존재

> 세션 영속성 문제는 [tmux와 병행 사용](./with-tmux.md#cmux와-병행-사용)으로 해결할 수 있습니다.

## AI 에이전트 활용 패턴

### 멀티 에이전트 병렬 작업

```
워크스페이스 1: Frontend
  ├── 페인 1: npm run dev (서버)
  └── 페인 2: claude (에이전트 — 프론트엔드 작업)

워크스페이스 2: Backend
  ├── 페인 1: uvicorn main:app (서버)
  └── 페인 2: claude (에이전트 — 백엔드 작업)

워크스페이스 3: Review
  └── 페인 1: claude (에이전트 — 코드 리뷰)
```

에이전트가 입력 대기 상태가 되면 알림 링이 표시되어 즉시 확인 가능.

### 브라우저 연동 디버깅

1. `Cmd + Shift + L`로 내장 브라우저 열기
2. 개발 서버 URL 접속
3. AI 에이전트에게 "브라우저에서 이 버튼 클릭하고 콘솔 에러 확인해줘" 요청
4. 에이전트가 브라우저를 직접 조작하여 디버깅

## Ghostty 설정 호환

기존 Ghostty 설정(`~/.config/ghostty/config`)의 테마와 글꼴을 그대로 사용합니다.

## ai-rules와의 관계

| 영역 | ai-rules | cmux | 관계 |
|------|----------|------|------|
| 개발 환경 UI | 없음 | 워크스페이스, 알림, 브라우저 | cmux 추가 |
| 코딩 규칙 | 스택별 상세 규칙 | 없음 | **ai-rules 전담** |
| 에이전트 제어 | 없음 | CLI + Socket API | cmux 추가 |
| 워크플로우 | global.md Plan→Docs→Review→Implement | 없음 | **ai-rules 전담** |

**충돌 없음.** cmux는 "실행 환경의 GUI"이고, ai-rules는 "코딩 규칙"입니다.

## 요약

- AI 에이전트를 **여러 개 동시에** 돌릴 때 시각적 관리에 최적
- **내장 브라우저 + AI 제어**는 cmux만의 고유 강점
- **세션 영속성이 없으므로** 장시간 작업 시 [tmux 병행](./with-tmux.md#cmux와-병행-사용) 권장
- macOS 전용이므로 팀/서버 환경에서는 tmux 필수
