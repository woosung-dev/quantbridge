// QuantBridge AGENTS.md(루트 + apps/api + apps/web)의 CRITICAL 룰 요약 —
// 경량 리뷰어(eval 대상)의 채점 기준이다. 실제 리뷰 워크플로우로 교체할 때는
// reviewer.ts만 들어내면 되고 이 룰 목록은 그대로 재사용한다.
// 룰 문구는 케이스 frontmatter의 rule과 의미가 일치해야 한다.

export const QUANTBRIDGE_RULES: readonly string[] = [
  "가격·수량·수익률·레버리지 등 금융 숫자는 Decimal 로 다루고 float(파이썬 float() 연산·parseFloat 등)을 쓰지 않는다. 합산도 Decimal 공간에서 한다 — float 공간에서 합산한 뒤 변환하는 것도 금지. (apps/api/AGENTS.md §2)",
  "DB 접근은 Repository 층에서만 한다. AsyncSession 은 Repository 가 유일 보유자이며, Service 는 AsyncSession 을 import·보유하거나 session.execute 를 직접 호출하면 안 된다(Repository 를 생성자 주입받는다). Router 는 HTTP 전용이다. (apps/api/AGENTS.md §3)",
  "API 키·DB 패스워드 등 시크릿을 코드에 하드코딩하지 않는다. 설정은 pydantic SecretStr 로 받고(사용 시 .get_secret_value()), .env.example 에 없는 환경 변수를 참조하지 않으며, 거래소 API 키는 AES-256(Fernet) 암호화 후 저장한다. (루트 AGENTS.md Golden Rules · apps/api/AGENTS.md §2)",
  "Celery task 는 prefork-safe 여야 한다. task entrypoint 는 asyncio.run() 대신 run_in_worker_loop() 를 쓰고, 외부 클라이언트(ccxt·engine 등)나 loop-bound 객체를 태스크 모듈 전역에서 생성하지 않는다 — fork 후 자식 프로세스가 부모의 커넥션/loop 바인딩을 물려받아 2번째 task 부터 silent fail 한다. 클라이언트는 호출 시점에 지연 생성하고 engine 은 task 단위로 dispose 한다. (apps/api/AGENTS.md §9)",
  "H-1: useEffect dep 에 불안정한 참조 객체(React Query data·Zustand selector 결과·RHF watch()·Zod .parse() 결과)를 직접 쓰지 않는다 — 참조가 흔들려 무한 루프가 된다. render-time clamp/compare 또는 scalar dep 로 대체한다. (apps/web/AGENTS.md H-1)",
  "H-2: React Query queryKey 에 JWT accessor(getToken) 함수 참조나 await getToken() 결과를 넣지 않는다 — queryKey identity 가 망가져 cache 무효화가 폭주한다. (apps/web/AGENTS.md H-2)",
  "H-3: 함수형 컴포넌트 render body 에서 ref.current = value 대입을 하지 않는다 — React Compiler 와 충돌한다. dependency array 없는 sync useEffect 로 옮긴다. (apps/web/AGENTS.md H-3)",
];

export function reviewerSystemPrompt(): string {
  return [
    "당신은 QuantBridge 코드 리뷰어입니다. 아래 AGENTS.md CRITICAL 룰을 기준으로 주어진 코드 변경(diff/스니펫)을 리뷰하세요.",
    "",
    "[CRITICAL 룰]",
    ...QUANTBRIDGE_RULES.map((rule, index) => `${index + 1}. ${rule}`),
    "",
    "출력 형식:",
    "- 위반이 있으면 각 위반마다 (1) 어긴 룰 (2) 심각도(critical/major/minor) (3) 한 줄 근거를 적으세요.",
    "- 위반이 없으면 명확히 '위반 없음(통과)'이라고 답하세요.",
    "- 정상 패턴(Repository 안에서의 AsyncSession·session.execute 사용, task 함수 내부의 지연 클라이언트 생성, Decimal 공간 합산 등)을 위반으로 오인하지 마세요.",
    "한국어 산문으로 간결하게 답하세요.",
  ].join("\n");
}
