# tmux와 함께 사용하기

> [tmux](https://github.com/tmux/tmux) — 터미널 멀티플렉서.
> 세션 영속성 + 스크립팅으로 AI 에이전트 멀티스레드 환경 구축. "터미널을 꺼도 세션은 살아있다."

## 설치

```bash
# macOS
brew install tmux

# Ubuntu/Debian
sudo apt install tmux

# 버전 확인
tmux -V
```

## tmux를 쓰는 이유

일반 터미널(iTerm, Ghostty 등)은 창을 닫으면 프로세스가 종료됩니다.
tmux는 서버-클라이언트 구조로 **터미널을 닫아도 세션이 백그라운드에서 유지**됩니다.

AI 코딩 에이전트 시대에 다시 주목받는 이유:
- 여러 에이전트를 **병렬 실행**하고 세션별로 관리
- `capture-pane` + `send-keys`로 **에이전트 간 컨텍스트 공유**
- 셸 스크립트로 **수십 개 세션을 한 번에 생성** 가능
- SSH 원격 서버에서도 동일하게 동작

## 3계층 구조

```
Session (세션) ─ 프로젝트 단위
  └── Window (윈도우) ─ 탭처럼 전환
       └── Pane (페인) ─ 화면 분할
```

## 필수 명령어

### 세션 관리

```bash
tmux new -s frontend       # 세션 생성
tmux new -s backend -d     # 백그라운드 세션 생성
tmux ls                    # 세션 목록
tmux attach -t frontend    # 세션 접속
tmux kill-session -t backend  # 세션 종료
```

### 단축키 (Prefix: `Ctrl+B`)

| 기능 | 단축키 |
|------|--------|
| **세션** | |
| 세션 목록 + 이동 | `Prefix + S` |
| 세션/윈도우 트리 | `Prefix + W` |
| 세션 이름 변경 | `Prefix + $` |
| 세션에서 빠져나오기 | `Prefix + D` |
| **윈도우** | |
| 새 윈도우 | `Prefix + C` |
| 윈도우 이름 변경 | `Prefix + ,` |
| 다음/이전 윈도우 | `Prefix + N` / `Prefix + P` |
| 특정 윈도우 이동 | `Prefix + [0-9]` |
| **페인** | |
| 수평 분할 (좌우) | `Prefix + %` |
| 수직 분할 (상하) | `Prefix + "` |
| 페인 이동 | `Prefix + 방향키` |
| 페인 전체화면 토글 | `Prefix + Z` |

## 추천 설정 (`~/.tmux.conf`)

```bash
# === Prefix 변경 (Ctrl+B → Ctrl+Space) ===
unbind C-b
set -g prefix C-Space
bind C-Space send-prefix

# === 필수 설정 ===
set -g history-limit 50000          # 로그 버퍼 확대 (기본 2000줄 → 50000줄)
set -g mouse on                     # 마우스 클릭/드래그 활성화
set -g base-index 1                 # 윈도우 인덱스 1부터 시작
setw -g pane-base-index 1           # 페인 인덱스 1부터 시작
set -g renumber-windows on          # 윈도우 삭제 시 번호 재정렬

# === VI 방향키 ===
bind h select-pane -L
bind j select-pane -D
bind k select-pane -U
bind l select-pane -R

# === 더 직관적인 분할 키 ===
bind | split-window -h -c "#{pane_current_path}"
bind - split-window -v -c "#{pane_current_path}"

# === 새 윈도우/페인에서 현재 경로 유지 ===
bind c new-window -c "#{pane_current_path}"
```

> **history-limit 50,000줄은 필수.** AI 에이전트가 긴 로그를 분석할 때 기본 2,000줄로는 부족합니다.

설정 적용: `tmux source-file ~/.tmux.conf`

## AI 에이전트 활용 패턴

### 프로젝트별 자동 환경 구성

```bash
#!/bin/bash
# dev-start.sh — 한 명령어로 개발 환경 전체 구성

SESSION="myproject"

# 세션 생성 + 윈도우 구성
tmux new-session -d -s $SESSION -n "editor"
tmux new-window -t $SESSION -n "server"
tmux new-window -t $SESSION -n "agent"

# 서버 윈도우: 프론트/백엔드 분할
tmux send-keys -t $SESSION:server "cd frontend && npm run dev" C-m
tmux split-window -h -t $SESSION:server
tmux send-keys -t $SESSION:server "cd backend && uvicorn main:app --reload" C-m

# 에이전트 윈도우: Claude Code 실행
tmux send-keys -t $SESSION:agent "claude" C-m

# 첫 번째 윈도우로 이동 후 접속
tmux select-window -t $SESSION:editor
tmux attach -t $SESSION
```

### 에이전트 간 컨텍스트 공유 (`capture-pane`)

```bash
# 서버 로그를 캡처해서 AI 에이전트에게 전달
tmux capture-pane -t server:0.0 -p | tmux load-buffer -
tmux paste-buffer -t agent:0.0

# 또는 파일로 저장 후 전달
tmux capture-pane -t server:0.0 -p -S -100 > /tmp/server-log.txt
# AI에게: "이 로그를 분석해줘: /tmp/server-log.txt"
```

### Cross-Verify 워크플로우 (멀티 에이전트 검증)

```bash
#!/bin/bash
# cross-verify.sh — 3개 AI 에이전트 병렬 검증

SESSION="cross-verify"
PROMPT="$1"  # 분석할 프롬프트

tmux new-session -d -s $SESSION -n "claude"
tmux new-window -t $SESSION -n "codex"
tmux new-window -t $SESSION -n "gemini"

# 각 에이전트에 동일한 프롬프트 전달
tmux send-keys -t $SESSION:claude "claude" C-m
tmux send-keys -t $SESSION:codex "codex" C-m
tmux send-keys -t $SESSION:gemini "gemini" C-m

# 접속
tmux attach -t $SESSION
```

Claude Code가 팀 리드로서 Codex/Gemini 결과를 취합하여 최적 코드를 도출하는 패턴입니다.

## cmux와 병행 사용

cmux의 **세션 영속성 부재**를 tmux가 보완합니다.

### 왜 병행하는가

| 문제 상황 | cmux 단독 | cmux + tmux |
|-----------|-----------|-------------|
| cmux 크래시 | 에이전트 전부 종료 | tmux 세션은 유지 → 재접속 |
| macOS 재시작 | 레이아웃만 복원, 프로세스 종료 | tmux 세션 살아있음 |
| 실수로 창 닫음 | 작업 손실 | `tmux attach`로 복구 |

### 병행 구성법

```bash
# 1단계: tmux 세션을 먼저 생성 (백그라운드 보호망)
tmux new-session -s frontend -d
tmux new-session -s backend -d
tmux new-session -s agents -d

# 2단계: cmux 각 워크스페이스에서 tmux 세션에 attach
# 워크스페이스 1 → tmux attach -t frontend
# 워크스페이스 2 → tmux attach -t backend
# 워크스페이스 3 → tmux attach -t agents
```

```
┌─────────────────────────────────┐
│  cmux (GUI 레이어)               │  ← 알림 링, 브라우저, 시각적 관리
│  ┌───────────────────────────┐  │
│  │  tmux (세션 레이어)         │  │  ← 세션 영속성, 스크립팅
│  │  ┌─────┐ ┌─────┐ ┌─────┐ │  │
│  │  │Agent│ │Agent│ │Agent│ │  │
│  │  └─────┘ └─────┘ └─────┘ │  │
│  └───────────────────────────┘  │
└─────────────────────────────────┘
```

### 역할 분담

- **cmux:** 워크스페이스 시각 관리, 에이전트 알림, 내장 브라우저
- **tmux:** 세션 보호, 스크립트 자동화, `capture-pane` 기반 에이전트 간 통신

## tmux 단독이 더 좋은 경우

- **원격 서버 작업** — SSH 환경에서는 cmux 사용 불가
- **팀 세션 공유** — `tmux attach`로 동일 세션에 여러 명 접속
- **완전 자동화** — cron/systemd로 에이전트 스케줄 실행
- **크로스 플랫폼** — Linux 개발자가 팀에 있을 때
- **장기 안정성** — 며칠간 끊김 없이 에이전트를 돌려야 할 때

## ai-rules와의 관계

| 영역 | ai-rules | tmux | 관계 |
|------|----------|------|------|
| 개발 환경 구성 | 없음 | 세션/윈도우/페인 관리 | tmux 추가 |
| 코딩 규칙 | 스택별 상세 규칙 | 없음 | **ai-rules 전담** |
| 에이전트 병렬 실행 | 없음 | 스크립트 자동화 | tmux 추가 |
| 워크플로우 | global.md Plan→Docs→Review→Implement | 없음 | **ai-rules 전담** |

**충돌 없음.** tmux는 "실행 환경"이고, ai-rules는 "코딩 규칙"입니다.

## 요약

- **4개 명령어**(`new`, `attach`, `ls`, `detach`)만 알면 즉시 사용 가능
- AI 에이전트의 **세션 보호**와 **병렬 실행 환경**을 제공
- cmux와 병행 시 "GUI 편의성 + 세션 안정성"을 모두 확보
- 원격 서버, 팀 협업, 장기 실행에서는 tmux 단독이 최적
