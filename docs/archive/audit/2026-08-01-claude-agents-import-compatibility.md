# Claude Code의 `AGENTS.md` 공유 방식 확인

**확인일:** 2026-08-01  
**범위:** Anthropic 공식 Claude Code 문서와 저장소 루트 `CLAUDE.md`·`AGENTS.md`만 대조.

## 결론

네. 루트 `CLAUDE.md`에 코드 펜스·인라인 코드 밖의 평문 한 줄 `@AGENTS.md`만 두면 Claude Code가 해당 파일을 import하여 세션 시작 시 읽는다. 이는 추측이나 관찰 결과가 아니라 Anthropic이 `AGENTS.md` 호환용으로 명시한 방식이다. Claude Code가 `AGENTS.md`를 자동 탐색하는 것은 아니며, **`CLAUDE.md`를 읽고 그 안의 import를 확장**하는 동작이다. [공식 문서 — AGENTS.md](https://code.claude.com/docs/en/memory#agentsmd)

## 문서화된 동작

- `@path/to/import`는 `CLAUDE.md` 어디에서나 import를 선언한다. 상대 경로는 작업 디렉터리가 아니라 **그 import를 쓴 파일 기준**이므로, 루트 `CLAUDE.md`의 `@AGENTS.md`는 루트 `AGENTS.md`를 가리킨다. 상대·절대 경로 모두 가능하며 재귀 import는 최대 4 hop이다. 백틱 안의 `@AGENTS.md`는 import되지 않는다. [공식 문서 — Import additional files](https://code.claude.com/docs/en/memory#import-additional-files)
- import 내용은 참조한 `CLAUDE.md`와 함께 시작 시 확장·로드된다. import 다음에 Claude 전용 지침을 쓰면 그 지침은 import된 내용 **뒤에** 붙는다. `CLAUDE.md` 계층은 덮어쓰기가 아니라 모두 결합되며, 상위 디렉터리에서 현재 작업 디렉터리 순으로 들어온다. 같은 디렉터리에서는 `CLAUDE.local.md`가 뒤에 붙는다. [공식 문서 — How CLAUDE.md files load](https://code.claude.com/docs/en/memory#how-claudemd-files-load)

## 이 저장소와 선택 기준

현재 루트는 `CLAUDE.md -> AGENTS.md` 심볼릭 링크다(두 파일의 내용은 동일). 이것도 Anthropic이 공식 예시로 든 지원 방식이며, Claude 전용 내용을 추가할 필요가 없다면 유효하다. 다만 Windows에서는 심볼릭 링크 생성에 Administrator 권한 또는 Developer Mode가 필요하므로, 플랫폼·Git 링크 설정 차이를 피하고 앞으로 Claude 전용 지침을 덧붙일 여지를 남기려면 일반 파일 `CLAUDE.md`에 아래 한 줄을 두는 편이 더 이식성 높은 선택이다. 반대로 Unix 전용이고 완전 동일 본문을 보장하려는 목적이면 현 링크를 유지해도 된다. [공식 문서 — AGENTS.md 및 symlink 예시](https://code.claude.com/docs/en/memory#agentsmd)

```md
@AGENTS.md
```
