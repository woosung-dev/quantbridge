// 백엔드 숫자 문자열을 정밀도 손실 없이 화면용 퍼센트로 정리한다.
export function formatThresholdPercent(raw: string): string {
  return raw.replace(/(\.\d*?)0+$/, "$1").replace(/\.$/, "");
}
