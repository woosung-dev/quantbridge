# pre-push ref 판정 — **순수 함수만**. git 호출·부작용 없음. (BL-554 · BL-555)
#
# 왜 별 파일인가
#   `.husky/pre-push` 는 **메인 워크트리에서만** 판정 분기를 탄다(git_dir == git_common_dir).
#   판정을 훅 안에 인라인으로 두면 워커 워크트리에서는 그 분기를 안 타서 **로직이 아예 안 돈다** —
#   즉 시험할 수 없다. 판정을 여기로 빼서 훅과 하네스(scripts/pre-push-guard-test.sh)가
#   **같은 한 벌**을 쓴다.
#
# 계약
#   - POSIX sh 전용. 훅은 `sh -e` 로 돈다(husky `.husky/_/h`) — `[[ ]]` · 배열 · `<()` 금지.
#   - git 을 호출하지 않는다. 입력은 인자뿐이고 출력은 stdout 문자열 1 개다.
#   - `set -e` 아래에서 source 되므로 문장 형태의 `[ ... ] && cmd` 를 쓰지 않는다(if 로 쓴다).
#   - ★판정 **순서**가 곧 보호다. qb_push_ref_verdict 주석을 먼저 읽어라.

# main/master — 영구 금지 대상. bypass 로 뚫을 수 없다 (Golden Rule).
qb_ref_is_protected() {  # <ref>
  case "${1#refs/heads/}" in
    main|master) return 0 ;;
    *) return 1 ;;
  esac
}

# 브랜치 ref 인가 (태그·notes·기타 ref 를 브랜치 규칙에서 빼기 위해 쓴다).
qb_ref_is_head_ref() {  # <ref>
  case "$1" in
    refs/heads/?*) return 0 ;;
    *) return 1 ;;
  esac
}

# 태그 ref 인가.
#
# ★태그 push 정책 (BL-554 R1-④ — 왜 허용인가)
#   이 훅이 지키는 것은 둘이다: (1) main 직접 push 금지, (2) 워커 격리(메인 체크아웃에서 워커
#   브랜치를 밀지 않기). 태그는 **브랜치가 아니라서 둘 중 어느 것도 아니다** — 태그를 밀어도
#   원격 브랜치가 생기지 않고 main 이 갱신되지 않는다. 그래서 릴리스 태깅(`git push --tags`,
#   `git push origin v1.2.3`)을 막을 근거가 없고, 막으면 **조용한 회귀**가 된다(관례 작업마다
#   bypass 를 요구하면 그 습관화가 BL-555 가 없애려던 것을 되살린다).
#   ★단 **양쪽이 다 태그일 때만** 태그로 취급한다. `refs/heads/feat/foo:refs/tags/x` 처럼 한쪽만
#   태그면 태그 규칙을 주지 않고 아래 일반 규칙(화이트리스트 → bypass → 차단)으로 흘려보낸다 —
#   교차 refspec 으로 규칙을 골라 타는 길을 열지 않는다(R0 의 codex G1 P1 과 같은 이유).
#   삭제는 허용한다. `git push origin --delete v1.2.3` 은 명시적으로 그 refspec 을 타이핑해야
#   나오는 것이라 오발사 위험이 낮고, 태그 삭제는 main 보호와 무관하다.
#   [확인 필요] 원격 릴리스 태그를 **강제로 옮기는** 것(force update)은 여기서 구분하지 않는다 —
#   그건 조상 관계를 봐야 해서 git 호출이 필요하고, 이 파일은 순수 함수 계약이다. 지금 이 레포에
#   태그 사용처가 없어 미룬다.
qb_ref_is_tag_ref() {  # <ref>
  case "$1" in
    refs/tags/?*) return 0 ;;
    *) return 1 ;;
  esac
}

# 허용 prefix. `stage/*` 는 ADR-017 이 정한 이 레포의 통합 브랜치다 (BL-555) — 없어서
# 관례대로 만든 브랜치를 밀 때마다 QB_PRE_PUSH_BYPASS=1 이 필요했고, bypass 를 습관화하면
# 그 플래그가 지켜야 할 것(워커 워크트리에서의 오발사)까지 함께 무뎌진다.
qb_ref_is_whitelisted() {  # <ref>
  case "${1#refs/heads/}" in
    stage/*|feat/*|fix/*|chore/*|docs/*|test/*|refactor/*|hotfix/*) return 0 ;;
    *) return 1 ;;
  esac
}

# 삭제 push 인가. git 은 삭제를 local_ref=`(delete)` + local_sha=0…0 으로 준다.
# ★sha 는 **길이까지** 본다. `0`·`000` 같은 짧은 값을 삭제로 인정하면 malformed 입력에서
#   fail-open 이 된다 (codex G1 P2).
qb_ref_is_delete() {  # <local_ref> <local_sha>
  if [ "$1" = "(delete)" ]; then
    return 0
  fi
  _qb_sha="$2"
  if [ "${#_qb_sha}" -lt 40 ]; then
    return 1
  fi
  case "$_qb_sha" in
    *[!0]*) return 1 ;;
  esac
  return 0
}

# (local_ref, local_sha, remote_ref, remote_sha, bypass) → 판정 문자열 1 개
#   allow-tag | allow-tag-delete | allow-delete | allow-whitelist | allow-bypass
#   deny-main | deny-arbitrary
#
# ★순서가 보호다. main/master 는 **remote_ref 로 가장 먼저** 본다.
#   `git push origin feat/foo:main` 의 stdin 은 local=refs/heads/feat/foo · **remote=refs/heads/main**
#   이다. 화이트리스트를 local_ref 로 먼저 태우면 실제 원격 main 갱신이 그대로 나간다 = fail-open.
#
#   ① remote 가 main/master              → deny-main       (갱신이든 삭제든. bypass 불가)
#   ② remote 가 refs/tags/* 이고
#        삭제                            → allow-tag-delete
#        local 도 refs/tags/*            → allow-tag        (릴리스 태깅. 근거는 qb_ref_is_tag_ref 주석)
#      한쪽만 태그면 태그 규칙을 주지 않고 아래로 흘려보낸다
#   ③ 삭제 + remote 가 refs/heads/*      → allow-delete    (BL-554 — 남의 브랜치 삭제는 main push 가 아니다)
#   ④ remote **와** local 둘 다 화이트리스트 → allow-whitelist
#      ★둘 다 본다. local 만 보면 `feat/foo:refs/heads/wip-x` 로 임의 원격 ref 를 만들 수 있고,
#        그건 현재 동작(현재 브랜치 기준)보다 느슨하다 (codex G1 P1).
#   ⑤ bypass=1                           → allow-bypass
#   ⑥ 그 외                              → deny-arbitrary  (bypass 안내)
#
# remote_sha($4)는 쓰지 않는다 — 인터페이스를 git 이 주는 4-튜플과 같게 두려고 받는다.
qb_push_ref_verdict() {  # <local_ref> <local_sha> <remote_ref> <remote_sha> [bypass]
  _qb_l="$1"; _qb_lsha="$2"; _qb_r="$3"; _qb_bypass="${5:-0}"

  if qb_ref_is_protected "$_qb_r"; then
    echo "deny-main"
    return 0
  fi
  if qb_ref_is_tag_ref "$_qb_r"; then                                    # ★R1-④ 변이 지점
    if qb_ref_is_delete "$_qb_l" "$_qb_lsha"; then
      echo "allow-tag-delete"
      return 0
    fi
    if qb_ref_is_tag_ref "$_qb_l"; then
      echo "allow-tag"
      return 0
    fi
  fi
  if qb_ref_is_delete "$_qb_l" "$_qb_lsha" && qb_ref_is_head_ref "$_qb_r"; then
    echo "allow-delete"
    return 0
  fi
  if qb_ref_is_whitelisted "$_qb_r" && qb_ref_is_whitelisted "$_qb_l"; then
    echo "allow-whitelist"
    return 0
  fi
  if [ "$_qb_bypass" = "1" ]; then
    echo "allow-bypass"
    return 0
  fi
  echo "deny-arbitrary"
}
