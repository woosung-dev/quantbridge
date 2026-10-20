# 전략 작성 화면 계약

`/strategies/new`는 TradingView Pine 원문을 등록하고 서버의 지원 여부 판정을 확인하는 화면이다. 화면 구조와 시각 언어는 [DESIGN.md](../../DESIGN.md)의 Precision Instrument v3와 [screen-07 프로토타입](../design/prototypes/shotgun-2026-07/screen-07-strategy-create.html)을 따른다. 이 문서는 UX 상태와 FE 동작 경계를 기록한다.

구현 기준은 `new-strategy-wizard.tsx`, `parse-result-panel.tsx`, `features/strategy/hooks.ts`, `features/strategy/draft.ts`, `components/monaco/pine-editor.tsx`, `styles/globals.css`다.

## 초안

- 초안은 서버가 아니라 현재 브라우저의 `localStorage`에 user ID별로 저장된다. 키는 `sprint7c:strategy-wizard-draft:v1:<userId>`이고, 저장 데이터는 버전 1이며 30일 뒤 만료된다. 기기나 브라우저 사이에는 동기화되지 않는다.
- 초안 복원/폐기 선택 전에는 autosave가 멈춘다. X/Escape로 복원 창만 닫아도 기존 초안 보호는 계속된다. 이름 또는 Pine 원문을 새로 입력하면 이번 세션을 시작한 것으로 보고 autosave를 재개한다. 설명·심볼·타임프레임만 바꾸면 gate를 열지 않는다. 이는 아직 선택하지 않은 prior Pine 원문을 메타데이터 변경만으로 덮지 않기 위한 동작이다.
- autosave gate가 열린 뒤에는 이름, 설명, 심볼, 타임프레임, Pine 원문 중 변경된 값이 있으면 최신 값 전체를 500ms debounce로 저장한다. gate가 닫힌 동안의 metadata 변경은 저장하지 않는다. `초안 저장`은 현재 값을 즉시 쓴다. 브라우저 저장소 사용이 제한되면 자동 저장/삭제가 누락될 수 있고, 읽기는 초안 없음(`null`)으로 처리한다.
- 마운트 전에 의미 있는 기존 초안이 있으면 복원 대화상자를 먼저 연다. 복원/폐기 선택 전에는 자동 저장을 멈춰 이전 값을 새 빈 폼으로 덮지 않는다. `이어서 작성`은 원문과 존재하는 메타데이터를 폼에 복원하고 저장을 재개한다. `새로 시작`은 기존 키를 지우고 새 세션 저장을 재개한다.
- X/Escape로 대화상자를 닫는 것은 복원/폐기 선택으로 취급하지 않는다. 프롬프트만 숨기고 자동 저장은 계속 중지한다. 이전 초안은 진단의 `저장된 초안` 카드에서 `이어서 작성` 또는 `지금 다시 저장`으로 처리할 수 있다.
- 복원 창이 닫힌 뒤 설명·심볼·타임프레임만 변경하면 autosave는 계속 멈춰 이전 초안 원문을 보존한다. 사용자가 이름이나 Pine 원문에 새 값을 입력하거나 명시적으로 초안 동작을 선택한 뒤 autosave가 재개된다.

복원 대화상자 숨김 상태와 초안 결정 상태는 별개다. `restorePromptHidden`은 X/Escape 닫힘만 반영하고, `promptDismissed`는 복원/폐기 또는 새 이름/Pine 입력으로 이번 세션을 시작했음을 반영한다. 자동 저장 gate가 열린 뒤에는 `useAutoSaveDraft`가 이름·설명·심볼·타임프레임·Pine 원문의 변경을 추적한다.

## 현재 원문 파싱

- 원문 변경 뒤 300ms debounce로 자동 파싱한다. 자동 요청은 공백과 줄바꿈을 포함한 원문 그대로 서버에 보내고, 사용자 ID와 원문 전체로 React Query 캐시를 구분한다. 빈 원문인지 확인할 때만 trim을 사용한다. `파싱 검사`와 Monaco의 `⌘/Ctrl+Enter`는 현재 원문을 즉시 다시 파싱한다. 예제 버튼은 확인 대화상자 없이 Pine 원문을 예제 코드로 바꾼다.
- 화면 결과·오류·저장 가능 여부는 현재 원문 문자열과 정확히 같은 요청에서만 읽는다. debounce 대기 중이거나 다른 원문 요청이 늦게 끝나도 이전 판정으로 현재 원문을 저장하지 않는다. 오래된 요청을 취소하는 계약은 아니다.
- 요청 자체가 실패하면 한국어 요청 실패 상태와 서버 메시지, endpoint를 보인다. 서버가 파싱 응답으로 구문 오류를 돌려주면 한국어 안내와 구조화된 행 위치를 먼저 보이고, 서버가 준 오류 코드·메시지는 `서버 진단 보기` 아래 접어 둔다. 화면이 메시지 문자열에서 행 번호를 추측하지 않는다. 현재 원문을 다시 검사할 수 있고 원문을 바꾸면 이전 원문의 오류/판정은 적용되지 않는다.
- 작성 화면은 서버가 준 안전한 양의 정수 행에만 `N행으로 이동`을 제공한다. 이동은 해당 Monaco 행을 먼저 선택하고 focus한 뒤 원문 영역을 기존 상단 여백으로 스크롤한다. 행이 현재 모델 끝을 넘으면 마지막 행으로 제한하고, 에디터/모델이 아직 없으면 원문 영역에 스크롤을 유발하지 않도록 focus한 뒤 스크롤한다.
- 새 전략 저장 버튼은 이름과 원문이 비어 있지 않고, 현재 판정이 `ok`이며 미지원 함수가 없을 때만 활성화된다. 서버의 파싱 지원 여부 판정은 로컬 함수 사전과 별개다.

## Monaco와 선택 기능

- Monaco는 `next/dynamic`과 `ssr: false`로 지연 로드한다. 마운트 시 `⌘/Ctrl+Enter` 명령을 한 번 등록하고, `onTriggerParse`의 최신 콜백은 effect에서 ref에 동기화한다. 렌더 중 ref를 쓰지 않으며, 명령이 오래된 원문 핸들러를 호출하지 않게 한다.
- Monaco의 Pine 라인 번호 색은 dark/light `BRAND_PALETTE.textMuted`를 사용해 각 gutter 배경에서 본문 텍스트 대비를 유지한다.
- `AI 초안 작성 (선택)`은 기본 접힘이다. 펼치기만으로는 API 요청을 하지 않는다. 설명을 입력한 뒤 `AI 로 만들기`를 누르면 생성 요청을 시작한다. 결과는 저장되지 않으며, 실행 가능한 결과에서 `이 Pine 코드 쓰기`를 눌러 편집기에 넣는다. 이후 파싱 판정은 편집기의 현재 원문 기준으로 다시 수행한다.

## 이동과 작은 화면

- Pine 원문이 있을 때 `판정 결과 보기` 링크가 `#strategy-parse-result`로 이동하고, 판정 헤더의 `원문 다시 보기` 링크가 `#strategy-pine-source`로 돌아간다. 두 섹션은 `tabIndex={-1}`로 포커스 이동을 허용한다.
- Monaco에서 키보드로 나가는 화면 힌트는 `Mac Ctrl+Shift+M / Windows·Linux Ctrl+M 후 Tab`이다.
- 04 진단에는 정적 Pine 지원 함수 사전과 현재 브라우저의 저장 초안 카드가 있다. 사전은 화면에서 실제 항목을 렌더하며, 초안 카드는 브라우저 저장 상태에 따라 이어쓰기/즉시저장 또는 빈 상태를 보여준다. 두 정보 묶음은 ‘준비 중’ 상태로 표시하지 않는다.
- 화면 너비 1200px 이하에서는 입력/판정 열을 세로로 쌓고, 768px 이하에서는 메타데이터와 진단 카드를 한 열로 배치한다. 같은 모바일 구간의 버튼·입력·선택 컨트롤과 AI 접기 요약은 최소 높이 44px이다. 설명 textarea의 최소 높이는 92px이며 세로 크기 조절을 허용한다.
- 두 anchor 대상의 CSS `scroll-margin-top`은 고정 상단바 토큰(`--topbar-h`)에 20px 여유를 더한다. 모바일 조작 컨트롤과 AI 접기 요약은 최소 44px 높이를 유지한다.

## 구현 리뷰 기준

React 성능 검토는 관련 규칙만 적용한다: effect 의존성은 원시 값으로 한정하고(`rerender-dependencies`), Monaco 명령 핸들러는 ref로 최신 값을 읽으며(`advanced-event-handler-refs`), Monaco는 필요한 시점에 동적 로드한다(`bundle-dynamic-imports`). 초안 키는 버전이 있다. [draft.ts](../../apps/web/src/features/strategy/draft.ts)의 snapshot `localStorage` 접근 실패는 `null`로 처리하고 캐시 값에 fallback하지 않는다. clear 함수는 저장소 접근 실패를 best-effort로 처리하며 subscriber 알림은 저장소 예외 경계 밖에서 수행한다. 저장소 접근이 차단되면 draft 저장·삭제 지속성은 보장되지 않는다(`client-localstorage-schema`).
