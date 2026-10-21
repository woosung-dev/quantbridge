# 공통 격리 코드 실행기

Python은 기존 `quantbridge-python-runner:local` 이미지를 재사용한다. TypeScript는
`sh infra/code-runner/build.sh`로 빌드한다. Node 버전은 루트 `mise.toml`, TypeScript는
FE `pnpm-lock.yaml`의 확정 버전에서 읽으며 별도 버전 상수를 두지 않는다.

Linux Docker의 gVisor `runsc`가 반드시 필요하다. Docker endpoint는 연구 명령의 셸에만
설정하고 앱 환경·전역 context를 바꾸지 않는다. 호스트 소스 실행·일반 runc fallback은 없다.
컨테이너에 호스트 경로·Docker socket·앱 키·주문 권한을 전달하지 않는다.

두 언어 모두 `init {type, protocol:1, source, params}` 후 `bar {type, bar, position}`를 받는다.
선택적 language는 trusted factory의 언어와 같아야 한다. Python은 `on_bar(ctx,state)`,
TypeScript는 `export function onBar(ctx: Context,state: Record<string,unknown>): Intent`다.
`init(params)`는 선택이며 상태 객체를 반환한다. `ctx.history`는 현재 완료봉을 포함한다.
TS의 `Bar`, `Position`, `Context`, `Intent`는 전역 타입으로 제공하며 import가 필요 없다.
출력은 `{action:"hold"|"long"|"short"|"close"}`만 허용한다. 청산 가격·수량·손익은
공통 리스크 원장이 결정하며 사용자 코드가 지정하면 실패한다.

Python 외부 패키지는 보존 이미지의 numpy/pandas로 고정한다. TS 외부 패키지는 없으며
고정 tsc로 strict 검사·JS 생성을 완료해야 실행한다. 실행 중 패키지 설치는 불가능하다.
TypeScript 컴파일도 같은 격리·전체 기한에 포함하며 컴파일 자체는 최대 60초다.
네트워크 차단·읽기 전용 root·non-root·1CPU·1GiB·PID64·출력 16MiB·최대 900초는
기존 transport와 같다. 오류·출력 위반·시간초과 시 transport와 컨테이너를 닫는다.
