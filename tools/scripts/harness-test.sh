#!/usr/bin/env bash
# harness 어댑터 하네스 — 「상류는 pristine 인가」와 「우리 어댑터가 실제로 덮는가」 둘만 잰다.
#
# ★이 파일은 [ADR-033] 의 계약을 집행한다. 계약은 둘이다:
#   ⑴ `tools/vendor/harness/` 는 상류 da676bc6 **바이트 그대로**다 (수정 0줄)
#   ⑵ 우리 차이는 전량 `tools/scripts/qb_harness.py` 안에 있고 그것이 테스트로 고정돼 있다
#
# ★네트워크 0 · docker 0. 다른 10종 하네스와 같은 규약이다.
# ★fail-open 금지 — uv 가 없으면 skip 이 아니라 **빨강**이다. 이 레포가 반복해 덴 자리다.
#
# 정본: docs/decisions/033-harness-readopt-codex.md · .harness/README.md
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT" || exit 1

rc=0
fail() { printf '  ✗ %s\n' "$1"; rc=1; }
ok() { printf '  ✓ %s\n' "$1"; }

printf '\n▶ harness — 상류 pristine 무결성\n'

# ── 케이스 ① 상류 2벌이 da676bc6 바이트 그대로인가 ─────────────────────────
# 상류는 라이선스가 없고(license=null) 2026-04-14 이후 커밋이 0이다. 우리가 그 시점을
# 못 박아 두지 않으면 「누가 이 파일을 고쳤는가」를 판정할 근거가 사라진다.
declare -a VENDOR_SHA=(
  "83b5375b8ec5be63a8624451c6ad636b295a8fac4ab8ccfb5af6fb2b4bcee572  tools/vendor/harness/execute.py"
  "0fffa6dee2226f7491f099a857b40d7334f8610e1fa9d8e1c3c16c9a2a916649  tools/vendor/harness/test_execute.py"
)
for entry in "${VENDOR_SHA[@]}"; do
  want="${entry%% *}"; file="${entry##* }"
  if [ ! -f "$file" ]; then fail "$file 이 없다 — 어댑터가 로드조차 못 한다"; continue; fi
  got="$(shasum -a 256 "$file" | cut -d' ' -f1)"
  if [ "$got" = "$want" ]; then ok "pristine $file"
  else fail "$file 이 상류 da676bc6 과 다르다 (got ${got:0:16}… want ${want:0:16}…) — 벤더는 수정 0줄이다"; fi
done

# ── 케이스 ② 어댑터가 벤더를 실제로 참조하는가 ─────────────────────────────
# 어댑터가 벤더 대신 사본을 들고 있으면 ①의 고정이 무의미해진다.
if grep -q 'tools" / "vendor" / "harness" / "execute.py"' tools/scripts/qb_harness.py; then
  ok "어댑터가 tools/vendor/harness/execute.py 를 참조한다"
else
  fail "어댑터가 벤더 pristine 을 안 본다 — ① 고정이 무의미해진다"
fi

# ── 케이스 ③ 인라인 포크 잔재가 없는가 (음성 대조) ─────────────────────────
# 2026-08-15 이전 판은 tools/scripts/execute.py 를 직접 고쳤다. 그 파일이 살아 있으면
# 러너가 둘이 되고 어느 쪽이 도는지 사람이 못 읽는다.
if [ -e tools/scripts/execute.py ] || [ -e tools/scripts/test_execute.py ]; then
  fail "인라인 포크 잔재가 있다 — tools/scripts/execute.py 계열은 어댑터로 대체됐다"
else
  ok "인라인 포크 잔재 0건"
fi

# ── 케이스 ④·⑤ pytest 2벌 ─────────────────────────────────────────────────
# ★uv 가 없으면 skip 하지 않는다. 「검사기를 부르는 경로가 죽으면 검사기는 0을 잰다」
#   (LESSON-101). CI documentation 잡에 setup-uv 가 배선돼 있어야 한다.
if ! command -v uv >/dev/null 2>&1; then
  fail "uv 가 없다 — pytest 2벌을 못 돌린다. CI 라면 setup-uv 배선이 빠진 것이다(skip 아님)"
else
  printf '\n▶ harness — pytest\n'
  if uv run --no-project --with pytest pytest tools/vendor/harness/test_execute.py -q >/tmp/qbh_up.$$ 2>&1; then
    ok "상류 51건 (pristine 소스 + pristine 테스트 = 벤더 무결성)"
  else
    fail "상류 테스트 실패 — 벤더가 훼손됐다"; tail -5 /tmp/qbh_up.$$
  fi
  if uv run --no-project --with pytest pytest tools/scripts/test_qb_harness.py -q >/tmp/qbh_ad.$$ 2>&1; then
    ok "어댑터 16건 (우리가 덮은 것만)"
  else
    fail "어댑터 테스트 실패"; tail -8 /tmp/qbh_ad.$$
  fi
  rm -f /tmp/qbh_up.$$ /tmp/qbh_ad.$$
fi

printf '\n'
if [ "$rc" = 0 ]; then echo "✓ harness 하네스 통과 — 상류 pristine · 어댑터 계약 유지"
else echo "✗ harness 하네스 실패"; fi
exit "$rc"
