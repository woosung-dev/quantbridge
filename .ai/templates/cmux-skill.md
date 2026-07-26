# cmux 스킬 가이드

> 이 내용을 CLAUDE.md 또는 AGENTS.md에 추가하면
> 에이전트가 cmux CLI를 사용하여 병렬 워크플로우를 자율적으로 운영할 수 있습니다.
>
> **전제:** cmux가 설치되어 있고, 환경변수 `CMUX_WORKSPACE_ID`가 설정된 상태여야 합니다.

---

아래를 CLAUDE.md에 복사하세요:

```markdown
## cmux 사용 가이드

이 프로젝트는 cmux 터미널에서 실행됩니다.
환경변수 CMUX_WORKSPACE_ID가 설정되어 있으면 cmux CLI를 사용할 수 있습니다.

### 워크스페이스/pane 관리
- `cmux new-workspace` — 새 탭 생성
- `cmux rename-workspace "이름"` — 탭 이름 변경
- `cmux new-split right` — 오른쪽에 pane 분할
- `cmux new-split down` — 아래로 pane 분할
- `cmux list-surfaces` — 현재 워크스페이스의 surface 목록
- `cmux close-surface <ID>` — surface 닫기

### 다른 pane에 명령어 보내기
- `cmux send --surface <ID> "명령어"` — 특정 surface에 텍스트 전송
- `cmux send-key --surface <ID> enter` — 엔터 키 전송
- `cmux read-screen --surface <ID> --lines 50` — 다른 surface의 화면 읽기

### 진행상황 보고
- `cmux set-progress 0.5 --label "빌드 중"` — 사이드바에 진행률 표시
- `cmux notify --title "완료" --body "테스트 통과"` — 알림 전송
- `cmux log "메시지"` — 사이드바에 로그 기록

### 병렬 워크플로우 패턴

독립 기능을 병렬로 구현할 때:

1. 기능별 worktree 생성: `git worktree add .worktrees/feat-name -b feat/name origin/main`
2. 기능별 워크스페이스 생성: `cmux new-workspace --cwd .worktrees/feat-name`
3. 워커 에이전트 실행: `cmux send --surface <ID> "claude 'feat-name 구현'"` + enter
4. 진행 상황 확인: `cmux read-screen --surface <ID> --lines 30`
5. 완료 후 정리: `cmux close-surface <ID>` + `git worktree remove .worktrees/feat-name`

### 규칙
- 자신이 소유하지 않은 surface에 입력을 보내지 마세요 (사용자가 타이핑 중일 수 있음)
- 작업 완료 후 생성한 surface는 `cmux close-surface`로 정리
- 워커에게 보내는 프롬프트는 구체적으로 작성 (파일 경로, 검증 기준 포함)
- 워커의 작업이 끝나면 `cmux notify`로 알림 전송
```
