# `direction` 발산을 원장으로 재판정하는 오프라인 오라클 — 구현과 독립이어야 뜻이 있다
"""`direction` 포지션 발산을 `replay_lag` / `phantom` 으로 가른다 ([BL-591]).

## 왜 필요한가

`qb_live_position_divergence_total{category="direction"}` 은 **낫는 발산과 안 낫는 발산을
한 라벨에 묻는다**:

- **`replay_lag`** — 다음 조정 주기 안에 스스로 낫는다. 무해.
- **`phantom`** — 낫지 않으며 연속 2회 판정으로 세션을 죽인다. 치명.

현행 코드는 이 둘을 **「연속 2회 판정」이라는 타이밍 대리 지표**로만 가른다
(`live_signal.py:3309-3318`). 이 스크립트는 그 대리 지표 대신 **원장**으로 직접 판정해,
프로덕션에 라벨을 넣기 전에 판별식을 검증한다.

★★**「엔진이 앞선다 vs 거래소가 앞선다」로 갈리지 않는다 — 2026-08-05 반증.** 종전 문서는
`phantom` 을 「엔진 시뮬이 체결로 친 주문이 거래소에 아예 없다(엔진이 앞선다)」로 정의했다.
그런데 관측 **19건 전량**이 「크기 같고 부호 반대」인 **반전(side flip)** 이고, 사망 4건을
엔진의 영속 보고서로 부검하니 **방향이 갈렸다**:

- **엔진이 앞선 사망 3건** — `open_trades[].entry_bar` 가 창의 **마지막 봉**이다. 그중 2건은
  엔진의 `entry_price` 가 거래소 resting 주문의 트리거와 **센트 단위로 같다**
  (`64285.81`/트리거 `64285.80` · `63723.69`/`63723.60`) — 엔진만 그 주문을 체결로 쳤다.
- **거래소가 앞선 사망 1건**(`39731d57`) — 엔진 포지션이 두 tick 에서 **비트 단위로 동일**
  (`-0.029722343673419874`)하고 open trade 는 **19봉 전**에 개시됐다. 거래소의 stale stop
  (트리거 `64071.9`)이 혼자 발화했고 엔진은 끝내 안 따라왔다.

⇒ **뿌리는 방향이 아니다. 엔진의 시뮬 stop 과 거래소의 resting stop 이 서로 다른 주문**
(수준도 수명도 다름)**이고, 그래서 양쪽 모두 혼자 발화할 수 있다**는 것이다. 실측: 재발주
때마다 트리거가 평균 **62~271 USDT** 움직이는데 1분봉 range 는 **30~90** 이다.

## 판별식 — 「직접 회복 검사」 (2026-08-05 2차 교체, 현행)

★**앞의 두 식은 전부 대리 지표였다.** 봉경계식은 「얼마나 지났나」를, 재무장식은 「파이프라인이
조정을 끝냈나」를 물었다. 정작 게이트가 알고 싶은 것은 **「이 발산이 나았나」** 하나다.
이 식은 그것을 직접 묻는다 — 원장도, 경과 시간 문턱도 쓰지 않는다.

관측 `T`(세션 `S` · 심볼 `Y` · 봉 간격 `I`), 코퍼스 지평 `C`, 근접 지평 `Hn = 1.5 · I`:

| 조건                                                    | 라벨          | 뜻                                        |
| ------------------------------------------------------- | ------------- | ----------------------------------------- |
| 같은 `(S,Y)` 의 **다음 관측**이 `T + Hn` 이내           | **`phantom`** | 바로 다음 평가에도 어긋나 있었다          |
| 다음 관측이 있고 `T + Hn` 밖                            | `replay_lag`  | 그 사이 나았다 — 뒤의 것은 새 에피소드    |
| 다음 관측 없음 + `T + Hn` 안에 **자동 사망**            | **`phantom`** | 낫지 않았다 — 죽어서 관측이 끊겼다        |
| 다음 관측 없음 + `T + Hn` 안에 `user_stopped`           | (판정 불가)   | 우리가 껐다 — 회복 여부를 알 수 없다      |
| 다음 관측 없음 + `C > T + Hn`                           | `replay_lag`  | 충분히 지켜봤고 다시 안 왔다              |
| 그 외 (**로그 창이 거기서 끝난다**)                     | (판정 불가)   | → `rearm_label` → `horizon_label` 로 강하 |

### 왜 재무장식을 버리는가 — 그쪽은 회복을 확인하지 않는다

재무장 도장 `H` 뒤에 체결 `F` 가 오면 그 발산이 **이후 영영 낫지 않아도** `F >= H` 인 한
계속 `replay_lag` 이다(§아래 종전 판별식 · [ADR-024] §남은 위험). 실측으로도 드러났다 —
`39731d57@16:24:01` 은 재무장식이 `replay_lag` 이라 부르지만 **60초 뒤 사망의 첫 짝**이고,
직전 회차가 「`replay_lag` 12/12 생존은 과장이었다」고 스스로 정정한 그 관측이다.
회복 검사는 그것을 **처음부터** `phantom` 으로 판정한다.

### 오차 방향 — 이 식은 게이트를 **엄격하게** 만든다

n=19 재적용: `phantom` **7 → 8**, 그리고 8은 재무장식의 7을 **완전히 포함**한다(진부분집합).
게이트의 위험 축은 fail-**open** 이다 — `phantom` 이 줄면 `window_start` 가 앞당겨져 누적이
늘고 통과가 쉬워진다(`soak_gate_predicate.py:362,405`). 엄격해지는 교체만이 안전한 교체다.
★창 A 11건(out-of-sample)에서는 회복식 = 봉경계식 **11/11 일치**로 바뀌지 않는다.

### ★대가 — 사망 상관이 더 이상 독립 검사가 아니다

회복식의 `phantom` 은 「다음 tick 도 어긋났다」이고 프로덕션 킬은 「연속 2회 **판정된** tick」
이다. **거의 같은 신호**라 `deaths == deaths_labelled_phantom` 이 동어반복에 가깝다.
⇒ `Summary.death_correlation_holds` 는 **채택 라벨이 아니라 `rearm_label`(없으면
`horizon_label`) 기준**으로 계속 계산한다. 그게 남는 독립 검사다. 채택 라벨 기준은
`adopted_death_correlation` 으로 따로 보고한다.

### ★남는 위험 둘 (숨기지 않는다)

- **`Hn = 1.5 · I` 는 문턱이다.** 실측 분리는 넓다 — 연속 tick 간격 **59.8~60.1초**(I=60) vs
  비연속 최소 **180초**. 90초는 양쪽에 3배 여유다. 그래도 **tick 이 한 번 건너뛰면**
  (`probe_failed`) 120초 뒤 관측이 `replay_lag` 으로 기운다. 그래서 `Summary` 가
  `max_phantom_gap` / `min_replay_lag_gap` / `ambiguous_gap_band` 를 찍어 **분리가
  좁아지는 순간을 보이게** 둔다. 뒤는 `auto_death` 가 받는다.
- **로그 절단.** 창의 마지막 관측은 후속자가 아직 없어 판정 불가이고 재무장식으로 강하한다
  (fail-open). 노출은 게이트 표본 주기(30분) 이하다 — `soak-gate.sh` 는 매 실행이 로그
  **전체**를 재분류하고 게이트는 아카이브 verdict 를 **합집합**으로 모으므로, 앞 실행이
  놓친 `phantom` 을 뒤 실행이 넣으면 `window_start` 가 소급 정정된다.
  ★이 자기치유는 산문이 아니라 `tests/scripts/test_soak_gate_predicate.py` 가 동결한다.

### `unattributed` 는 그대로 둔다 (범위 밖 · 알려진 fail-open)

세션 소유 체결이 없는 관측은 회복식으로도 판정하지 않고 `unattributed` 로 남긴다. 게이트는
`label == "phantom"` 만 실격으로 보므로 이 라벨은 **조용히 무해 취급**된다. 현재 코퍼스
31건에서 0건이라 도달하지 않지만 **fail-open 인 것은 사실이다** — 별도 BL 로 등재한다.

## 종전 판별식 — 「재무장 도장」 (2026-08-05 1차 교체, 이제 병기 라벨)

★**경과 시간은 교란변수였다.** 종전 봉경계식은 「마지막 체결로부터 봉 경계를 넘었는가」로
갈랐다. 그건 **얼마나 지났는가**를 묻는 것이고, 「60초면 엔진이 따라왔어야 한다」를 가정한다.
실측은 그 가정을 부순다 — tick 이 봉 마감 뒤 **10~15초**에 돌고, 조건부 주문의 재발주 주기는
**4~14분**이며, 재발주 때마다 트리거가 평균 **62~271 USDT** 움직인다(1분봉 range 는 30~90).
그래서 봉 하나로는 「조정이 끝났는가」를 판정할 수 없다.

대신 **시스템 자신의 조정 주기**를 쓴다. `conditional_entry_planner.py:502-589` 가

    quantity = |target_position - current_position|

로 수량을 정하고 `current_position` 은 **거래소 REST 읽기**(`live_signal.py:1517-1546`)다.
따라서 원장의 주문 한 행에서

    L      = ledger_net(order.created_at)          # 체결 원장의 부호 있는 순포지션
    target = L + (+qty if side == buy else -qty)   # 그 주문이 겨냥한 포지션

를 계산해 `L != 0` 이고 `sign(target) == -sign(L)` 이고 `|target| ~= |L|` 이면 그 주문은
**반전 주문**이다 — 곧 **파이프라인이 체결을 인지하고 반대편을 다시 무장했다**는 시각 도장이다.
이것을 **재무장 도장**이라 부른다.

관측 시각 `T`, 마지막 세션 소유 체결 `F`, 마지막 재무장 도장 `H` 에 대해

| 조건                | 라벨           | 뜻                                                                |
| ------------------- | -------------- | ----------------------------------------------------------------- |
| `H > F`             | **`phantom`**  | 체결 뒤 재무장을 **끝냈는데도** 어긋나 있다 ⇒ 조정 주기를 넘겼다 |
| `F >= H`            | `replay_lag`   | 마지막 재무장 **뒤에** 거래소가 움직였다 ⇒ 아직 판정할 때가 아니다 |
| 도장이 없다         | (봉경계식으로) | 재무장을 한 번도 못 봤다 — 아래 fallback                          |
| 세션 소유 체결 없음 | `unattributed` | 운영자 청산 등                                                    |

★★★**이건 인과 판정이 아니라 성숙도 프록시다 — 「누가 움직였나」를 말하지 않는다.**
초안에서는 「2배 수량 주문 = 그 순간 엔진과 거래소가 **합의**했다」고 적었는데 **반증됐다**:
`39731d57` 의 `16:24:11` 도장 시점에 엔진은 short(개시 봉 ~16:04), 거래소는 long(16:24:00
체결)으로 **어긋나 있었다**(`live_signal_states.last_strategy_state_report` 실측).
2배 수량은 **거래소 쪽만** 증언한다 — 엔진은 이미 그 방향을 들고 있어도 같은 `trade_id` 로
pending stop 을 다시 무장할 수 있기 때문이다(`strategy_state.py:728-740`).

★**누가 움직였는지의 인과 판정은 엔진의 영속 보고서로만 된다** —
`last_strategy_state_report.open_trades[].entry_bar` 가 창의 마지막 봉이면 그 tick 에 엔진이
움직인 것이다. 단 그 보고서는 **세션당 마지막 tick 한 벌**만 남으므로(같은 행을 덮어쓴다)
과거 관측 전량에는 적용할 수 없다. 그래서 게이트는 프록시를 쓴다.

★**도장이 없으면 종전 봉경계식으로 내려간다**(`horizon_label`). 도장은 「재무장했다」의
양성 증거이지 「어긋났다」의 증거가 아니므로, 증거가 없는 구간을 유령으로 접지 않는다.

★**`unattributed` 는 실재한다** — 운영자 청산 주문은 `idempotency_key` 가 비어 있어 어느
세션에도 귀속되지 않는다. 유령으로도 정상으로도 접지 않는다(`engine_only` 세분화 선례).

★**세션 귀속은 `idempotency_key` 로만 한다.** `trading.orders` 에는 `session_id` 가 없고,
계정으로 귀속하면 [BL-592] 의 `exchange_accounts` 2행 중복에 걸려 **3.7배 부풀려진다.**

## ★종전 두 식은 한쪽으로만 틀린다 — `phantom` 은 믿을 수 있다

- **재무장식** — 도장은 양성 증거다. 반전 주문이 안 나간 구간에는 도장이 안 찍히므로 `H` 가
  과거에 머물고 라벨은 `replay_lag` 쪽으로 기운다 ⇒ **phantom 과소계상**.
- **봉경계식** — `Order.filled_at` 은 거래소 체결시각이 아니라 **우리 관측시각**이다
  (`order_repository.py:53,107,129,212` — 이름과 달리 terminal 시각). 우리 타임스탬프는
  항상 더 늦으므로 `t_fill >= horizon` 이 참으로 기운다 ⇒ **phantom 과소계상**.

⇒ **`phantom` 라벨은 믿을 수 있다** — 이 방향의 오차는 **거짓 사망을 만들지 않는다.**
반대로 「`replay_lag` 이니 무해」는 그만큼 믿을 수 없다. 봉경계식의 실측 최소 여유는
**0.652초**(2026-08-03 23:17)로 경계는 실제로 붙는다.

★**재무장식이 거짓 `phantom` 을 내려면** 마지막 도장 뒤에 **우리 원장에 없는 반전**이
거래소에서 일어나야 한다. 운영자 청산은 포지션을 0 으로 만들 뿐이라 `direction` 이 아니라
`exchange_only`/`engine_only` 로 분류되므로 이 경로가 아니다. 남는 것은 **같은 계정을 쓰는
다른 전략의 반전**이고, 그건 [BL-592] 축의 별개 결함이다.

## ★이 오라클이 증명하는 것과 못 하는 것

판별식을 관측에서 **유도**했으므로 같은 관측에 잘 맞는 것은 검증이 아니다.

★**현행 회복식에서는 사망 상관이 독립 검사가 아니다** — 사망이 「연속 2회 판정된 tick」이라
「다음 tick 도 어긋났나」와 거의 같은 신호다(§판별식 §대가). 그래서 `death_correlation_holds`
는 **`rearm_label` 기준**으로 계속 계산한다. 재무장식은 원장(체결·반전 주문)에서 오고
사망은 tick 연속성에서 오므로 그 둘은 여전히 서로 독립이다.

회복식 자체를 갚는 방법은 셋뿐이다:

1. **out-of-sample** — 창 A 11건에서 봉경계식과 11/11 일치(규칙은 창 B 에서 유도했다).
2. **포함 관계** — 재무장식 `phantom` 집합을 완전히 포함하므로 「느슨해지는 교체」가 아님이
   집합 연산으로 확인된다.
3. **전향 예측** — 나머지는 이것으로만 갚는다.

★검증이 하나 더 있다 — 이 규칙은 **2026-08-04 15:51 이후 관측 8건**에서 유도했는데, 그 앞
창의 **11건**(`.soak/direction-classification-20260804T0630Z.json`)에서는 봉경계식과
**11/11 일치**한다. 그 11건은 out-of-sample 이다.

★그리고 **아니라고 말할 수 있는 것도 재봤다**(2026-08-05) — 엔진이 재생하는 봉(`CCXTProvider`
perp) · 내가 잰 공개 perp · **데모** perp 가 사망 4건의 해당 봉에서 **소수점까지 동일**했다.
스팟만 27~36 USDT 떨어져 있고 체결 조건을 4/4 불만족(BL-530 수리가 유지되고 있다).
⇒ **가격 소스 불일치도, 1분 타이밍도 이 발산의 원인이 아니다.**

## 사용

    QB=/path/to/quant-bridge
    set -a; . $QB/apps/api/.env.local; set +a; cd $QB/backend

    docker logs quantbridge-worker 2>&1 \\
      | uv run python scripts/classify_direction_divergence.py

    uv run python scripts/classify_direction_divergence.py --log /tmp/worker.log --json

★**워커 로그는 컨테이너 수명에 묶여 있다.** 재기동하면 증거가 사라지므로 출력을
`.soak/` 에 남겨라.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
from bisect import bisect_right
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import UUID

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "apps" / "api"))

from sqlalchemy import text  # noqa: E402

from src.tasks._worker_engine import create_worker_engine_and_sm  # noqa: E402

# --- 로그 파싱 -----------------------------------------------------------------
#
# 워커 한 줄: `... live_signal_position_divergence session_id=<uuid> symbol=BTC/USDT
#              category=direction engine_position=-0.03 exchange_position=0.03`
# 앞의 celery prefix 는 포맷이 여러 벌이라 파싱하지 않는다 — ISO 타임스탬프만 집어낸다.
_LINE_PATTERN = re.compile(
    r"live_signal_position_divergence\s+"
    r"session_id=(?P<session>[0-9a-fA-F-]{36})\s+"
    r"symbol=(?P<symbol>\S+)\s+"
    r"category=(?P<category>\w+)\s+"
    r"engine_position=(?P<engine>-?[\d.eE+-]+)\s+"
    r"exchange_position=(?P<exchange>-?[\d.eE+-]+)"
)
# `docker logs --timestamps` 접두 또는 celery 자체 `[YYYY-MM-DD HH:MM:SS,mmm:` 중 첫 매치.
_TS_PATTERN = re.compile(
    r"(?P<date>\d{4}-\d{2}-\d{2})[T ](?P<time>\d{2}:\d{2}:\d{2})[.,](?P<frac>\d+)"
)

# 원장 idempotency key: `live:<session_id>:...`. 프로덕션 파서를 쓰지 않는다 — 이 오라클은
# 검증 대상 코드와 독립이어야 한다.
_IDEM_SESSION_PATTERN = re.compile(r"^live:(?P<session>[0-9a-fA-F-]{36}):")

# ★판별식의 판(版). `--json` 출력과 `.soak/phantom-*.json` 아카이브에 함께 실린다.
#
# 왜 필요한가 — `scripts/soak-gate.sh` 는 **모든** 아카이브의 verdict 를 합집합으로 모으고
# `(시각, 종류, 상세)` 로 dedup 한다. 그래서 **판별식을 개선해 `phantom` 을 하나 취소해도
# 옛 아카이브의 그 라벨이 영원히 남는다** — 실측 2026-08-05: 교체 후 게이트가 여전히
# `phantom` 7건을 보고했고 그중 4건은 새 분류기가 이미 `replay_lag` 으로 판정한 것이었다.
# 방향은 fail-closed(과도하게 엄격) 지만, **개선이 게이트에 반영되지 않는다**는 뜻이다.
# ⇒ 판을 올리면 옛 아카이브를 `.soak/superseded-<판>/` 로 옮긴다([ADR-024] §아카이브 판).
# ★`-ratchet` 접미사 = 채택 규칙이 「앞 식이 실격시킨 것은 사면할 수 없다」로 바뀐 판이다
#   (codex challenge 2026-08-05). 라벨이 달라질 수 있으므로 판을 올린다 — 방향은 **엄격**
#   쪽뿐이라 옛 아카이브를 남겨도 거짓 PASS 는 안 되지만, 판이 섞이면 경고가 떠야 한다.
PREDICATE_VERSION = "2026-08-05-recovery-ratchet"

# 「바로 다음 평가」로 인정하는 간격 상한 = `1.5 × 봉 간격`.
#
# ★문턱인 것은 맞다. [ADR-024] §대안(f) 가 거부한 것은 「**완화**용 문턱」이고 이건 그 반대다 —
#   이 계수를 키우면 `phantom` 이 늘어(엄격) 줄이면 준다(관대). 실측 분리가 넓어서 고른다:
#   연속 tick 간격 59.8~60.1초(I=60) vs 비연속 최소 180초. 90초는 양쪽에 3배 여유다.
#   ★그래도 `Summary` 가 `max_phantom_gap` / `min_replay_lag_gap` / `ambiguous_gap_band` 를
#   찍는다 — 분리가 좁아지면 그 숫자로 먼저 보인다. 이 값을 **눈금 없이** 바꾸지 마라.
_NEXT_TICK_INTERVAL_FACTOR = 1.5

# 애매대 = `(1.5·I, 2.5·I]` — **tick 이 한 번 건너뛰었을 때** 관측이 떨어지는 구간이다
# (`probe_failed` 로 평가 하나가 빠지면 다음 발산은 `2·I` 뒤에 온다). 여기에 표본이 들어오기
# 시작하면 위 계수가 더 이상 안전하지 않다는 신호다.
#
# ★첫 초안은 `3.0` 이었고 실행하자마자 **1건**을 잡았다 — `03:41:50.756 → 03:44:50.701`,
#   간격 **179.94초** = `2.999·I`. 그건 건너뛴 tick 이 아니라 **정상적인 3봉 간격**이고,
#   내가 상한을 근거 없이 잡아서 생긴 거짓 경고였다. 「한 번 건너뜀」이라는 원래 우려를
#   그대로 쓰면 상한은 `2.5·I` 다(그 위는 평가가 둘 이상 빠져야 한다).
#   ★경고를 없애려고 옮긴 게 아니라는 근거: `max_phantom_gap` / `min_replay_lag_gap` 은
#   가공하지 않은 원본이고 이 계수와 무관하게 계속 찍힌다. 실측 분리는 60.02s vs 179.94s.
_AMBIGUOUS_BAND_FACTOR = 2.5

# 반전 주문 판정의 상대 허용오차. 반전 수량은 `|target - current|` 이고 current 는 거래소가
# 수량 스텝(BTC linear = 0.001)으로 양자화한 값이라 `|target|` 과 정확히 같지 않다 — 실측
# `L=+0.030` 에 `sell 0.059` → `target=-0.029` (3.3% 차). 프로덕션이 같은 이유로 쓰는
# `_POSITION_SIZE_REL_TOL`(`live_signal.py:238`)과 같은 5% 를 쓴다. 진짜 부분청산(실측
# 0.001 vs 0.029 = 96.5% 차)과는 여전히 멀리 떨어져 있다.
_REVERSAL_REL_TOL = Decimal("0.05")

_INTERVAL_SECONDS: dict[str, int] = {
    "1m": 60,
    "3m": 180,
    "5m": 300,
    "15m": 900,
    "30m": 1800,
    "1h": 3600,
    "2h": 7200,
    "4h": 14400,
    "1d": 86400,
}


@dataclass(frozen=True)
class DivergenceEvent:
    """로그 한 줄에서 읽은 발산 관측."""

    at: datetime
    session_id: UUID
    symbol: str
    category: str
    engine: float
    exchange: float


@dataclass
class Verdict:
    """한 관측의 재판정 결과.

    라벨이 다섯이다 — **넷을 병기하고 하나를 채택한다.** 지우면 식들이 언제 갈리는지 보이지
    않는다(1차 교체에서 4건, 2차 교체에서 1건이 갈렸다).

    - `label` — **채택**. 회복식이 판정하면 그것, 아니면 `rearm_label`, 그것도 없으면
      `horizon_label`. (`unattributed` 는 어느 식도 판정하지 않고 그대로 통과한다.)
    - `recovery_label` — **현행** 직접 회복 검사. 로그 창이 끝나 후속자를 못 보면 `None`.
    - `rearm_label` — 재무장 도장식(1차 교체). 도장이 없으면 `None`.
      ★**독립 검사(`death_correlation_holds`)는 이 라벨로 계산한다** — 회복식은 사망 규칙과
      거의 같은 신호라 자기 자신을 검증하지 못한다.
    - `horizon_label` — 최초 봉경계식(`t_fill >= floor(관측시각, interval)`).
    - `threshold_label` — 시간문턱식(`경과 < interval`). 참고용 — 채택된 적 없다.
    """

    event: DivergenceEvent
    interval_seconds: int
    horizon: datetime
    last_fill_at: datetime | None
    last_fill_side: str | None
    last_fill_qty: str | None
    last_rearm_at: datetime | None
    next_observation_at: datetime | None
    label: str
    recovery_label: str | None
    rearm_label: str | None
    horizon_label: str
    threshold_label: str
    died_here: bool

    @property
    def gap_seconds(self) -> float | None:
        if self.last_fill_at is None:
            return None
        return (self.event.at - self.last_fill_at).total_seconds()

    @property
    def next_gap_seconds(self) -> float | None:
        """다음 관측까지의 간격 — 회복식의 입력이자 그 문턱의 감사 눈금."""
        if self.next_observation_at is None:
            return None
        return (self.next_observation_at - self.event.at).total_seconds()

    @property
    def independent_label(self) -> str:
        """사망 상관을 계산할 라벨 — 회복식이 아니라 원장 기반 식이다.

        회복식(`다음 tick 도 어긋났나`)은 프로덕션 킬 규칙(`연속 2회 판정된 tick`)과 거의
        같은 신호라, 그것으로 사망 상관을 재면 동어반복이 된다. 재무장식은 **원장**에서
        오고 사망은 **tick 연속성**에서 오므로 그 둘은 서로 독립이다.
        """
        return self.rearm_label if self.rearm_label is not None else self.horizon_label

    def as_dict(self) -> dict[str, Any]:
        return {
            "at": self.event.at.isoformat(),
            "session_id": str(self.event.session_id),
            "engine": self.event.engine,
            "exchange": self.event.exchange,
            "last_fill_at": self.last_fill_at.isoformat() if self.last_fill_at else None,
            "last_fill_side": self.last_fill_side,
            "last_rearm_at": (self.last_rearm_at.isoformat() if self.last_rearm_at else None),
            "next_observation_at": (
                self.next_observation_at.isoformat() if self.next_observation_at else None
            ),
            "gap_seconds": self.gap_seconds,
            "next_gap_seconds": self.next_gap_seconds,
            "horizon": self.horizon.isoformat(),
            "label": self.label,
            "recovery_label": self.recovery_label,
            "rearm_label": self.rearm_label,
            "horizon_label": self.horizon_label,
            "threshold_label": self.threshold_label,
            "died_here": self.died_here,
        }


def _at_from_ts_match(ts_match: re.Match[str]) -> datetime:
    micro = f"{ts_match.group('frac'):0<6}"[:6]
    return datetime.fromisoformat(
        f"{ts_match.group('date')}T{ts_match.group('time')}.{micro}+00:00"
    )


def parse_log_horizon(lines: Sequence[str]) -> datetime | None:
    """로그가 **어디까지 갔는지** — 발산 줄이 아니라 모든 줄에서 최대 타임스탬프를 찾는다.

    ★발산 줄만 보면 창의 끝을 알 수 없다. 마지막 발산 뒤에 조용한 30분이 있었는지
    아니면 로그가 거기서 끝났는지가 **회복식의 판정을 가른다**(전자는 `replay_lag`,
    후자는 판정 불가). 타임스탬프가 없는 줄(트레이스백 연속 줄 등)은 건너뛴다 —
    그러면 지평이 과소평가되고, 그건 **판정 불가가 늘어나는** 방향이라 안전하다.
    """
    latest: datetime | None = None
    for line in lines:
        ts_match = _TS_PATTERN.search(line)
        if ts_match is None:
            continue
        at = _at_from_ts_match(ts_match)
        if latest is None or at > latest:
            latest = at
    return latest


def parse_log(lines: list[str], *, category: str = "direction") -> list[DivergenceEvent]:
    """워커 로그에서 해당 category 의 발산 관측을 뽑는다.

    타임스탬프를 못 읽은 줄은 **버리지 않고 예외로 올린다** — 조용히 빠지면 분모가
    말없이 줄어든다.
    """
    events: list[DivergenceEvent] = []
    for lineno, line in enumerate(lines, start=1):
        match = _LINE_PATTERN.search(line)
        if match is None or match.group("category") != category:
            continue
        ts_match = _TS_PATTERN.search(line)
        if ts_match is None:
            raise ValueError(f"타임스탬프를 못 읽었다 (line {lineno}): {line[:120]!r}")
        at = _at_from_ts_match(ts_match)
        events.append(
            DivergenceEvent(
                at=at,
                session_id=UUID(match.group("session")),
                symbol=match.group("symbol"),
                category=match.group("category"),
                engine=float(match.group("engine")),
                exchange=float(match.group("exchange")),
            )
        )
    return events


def floor_to_interval(at: datetime, interval_seconds: int) -> datetime:
    """`at` 을 봉 경계로 내림 — 엔진의 가시 지평 `last_bar_time + interval` 과 같다."""
    epoch = int(at.timestamp())
    return datetime.fromtimestamp((epoch // interval_seconds) * interval_seconds, tz=UTC)


async def _load_sessions(sm: Any, session_ids: set[UUID]) -> dict[UUID, dict[str, Any]]:
    if not session_ids:
        return {}
    async with sm() as db:
        rows = await db.execute(
            text(
                "SELECT id, interval, symbol, deactivated_at, deactivated_reason "
                "FROM trading.live_signal_sessions WHERE id = ANY(:ids)"
            ),
            {"ids": list(session_ids)},
        )
        return {row.id: dict(row._mapping) for row in rows}


async def _load_orders(sm: Any, symbols: set[str]) -> list[dict[str, Any]]:
    """창 안의 주문을 **상태 불문** 통째로 읽어 파이썬에서 세션 귀속한다.

    ★`state = 'filled'` 로 좁히지 않는다 — 합의 하트비트는 **취소·거절된 주문의 수량**도
    쓴다(수량은 발주 시점에 계산되므로 그 뒤의 운명과 무관하게 그 시점을 증언한다).
    실측 사망 4건 중 3건의 결정적 하트비트가 **끝내 체결되지 않은 주문**이었다.

    SQL 로 `idempotency_key LIKE 'live:<uuid>:%'` 를 세션마다 돌리는 것보다 왕복이 적고,
    귀속 규칙이 한곳(`_IDEM_SESSION_PATTERN`)에만 있게 된다.
    """
    if not symbols:
        return []
    async with sm() as db:
        rows = await db.execute(
            text(
                "SELECT created_at, filled_at, state::text AS state, symbol, "
                "       side::text AS side, quantity, filled_quantity, idempotency_key "
                "FROM trading.orders "
                "WHERE symbol = ANY(:symbols) "
                "ORDER BY created_at"
            ),
            {"symbols": list(symbols)},
        )
        return [dict(row._mapping) for row in rows]


# --- 합의 하트비트 (원장만 쓰는 순수 함수) --------------------------------------


def signed_quantity(order: dict[str, Any]) -> Decimal:
    """이 주문이 **겨냥한** 방향·크기. buy 는 +, sell 은 -.

    ★`quantity`(요청량)다 — 재무장 도장은 **무엇을 주문했나**를 묻지 무엇이 체결됐나를
    묻지 않는다. 원장 순포지션은 `signed_fill` 이 따로 계산한다.
    """
    qty = Decimal(str(order["quantity"]))
    return qty if str(order["side"]) == "buy" else -qty


def is_filled(order: dict[str, Any]) -> bool:
    """이 행이 **실제로 포지션을 만들었나.**

    ★★★**`state == 'filled'` 로 판정하면 안 된다 — 레포 정본이 이미 그렇게 적고 있다**
    (`entry_completeness.attempt_has_fill`): `transition_to_cancelled`/`_rejected` 는
    `filled_quantity` 가 0 이 아니면 체결분을 **보존한 채** 종결하므로 거래소에는 포지션이
    남았는데 상태가 `cancelled` 인 행이 실재한다. 반대로 `filled` 인데 `filled_quantity` 가
    NULL 이면 **판독 불가**이지 전량 체결이 아니다. ⇒ 판정은 **`filled_quantity > 0`** 이다.
    (codex challenge 2026-08-05 적발 — 나는 `state == 'filled'` 로 짰다.)

    ★★그리고 `filled_at IS NOT NULL` 로도 판정하면 안 된다 — 이 컬럼은 이름과 달리
    **terminal 시각**이라 취소·거절에도 채워진다(`order_repository.py:53,107,129,212`).
    실측: 상태 필터를 빼고 원장을 읽자 취소 주문 12건이 체결로 섞여 순포지션이 망가지고
    재무장 도장이 **전건 소실**됐다.

    ★`filled_quantity` 키가 없는 입력(`state` 도 없는 단위 테스트 픽스처)은 호출자가 이미
    체결만 걸러 넘긴 것으로 보고 `quantity` 를 쓴다.
    """
    if order.get("filled_at") is None:
        return False
    if "filled_quantity" in order:
        raw = order["filled_quantity"]
        return raw is not None and Decimal(str(raw)) > 0
    # `filled_quantity` 를 아예 싣지 않는 호출자(단위 테스트 픽스처)는 상태로 판정한다.
    # ★프로덕션 로더는 이제 그 컬럼을 **항상** 싣는다 — 이 갈래로 내려오지 않는다.
    return str(order.get("state", "filled")) == "filled"


def signed_fill(order: dict[str, Any]) -> Decimal:
    """이 주문이 **실제로 움직인** 포지션. 체결분이 없으면 0.

    ★`quantity` 가 아니라 `filled_quantity` 다 — 부분체결이면 요청량과 다르다.
    전체 원장 실측 2026-08-05: `filled` **202행 중 65행**이 `filled_quantity <> quantity` 다
    (단 이 회차 코퍼스 6세션 43행에서는 **0건**이라 19건 판정은 안 바뀐다).
    """
    if not is_filled(order):
        return Decimal("0")
    raw = order.get("filled_quantity")
    if raw is None:
        raw = order["quantity"]
    qty = Decimal(str(raw))
    return qty if str(order["side"]) == "buy" else -qty


def ledger_net_at(
    orders: Sequence[dict[str, Any]], at: datetime, *, exclude: dict[str, Any] | None = None
) -> Decimal:
    """`at` 시점까지 실제로 체결된 분의 부호 있는 순포지션.

    ★`exclude` 는 **자기 자신**을 빼기 위한 것이다 — 시장가 주문은 생성과 terminal 기록이
    같은 시각으로 찍힐 수 있고, 그러면 `filled_at <= created_at` 이 참이 되어 **자기 체결을
    자기 발주 전 원장에 포함**한다(codex challenge 2026-08-05 적발 · 프로덕션 미관측).
    """
    net = Decimal("0")
    for order in orders:
        if exclude is not None and order is exclude:
            continue
        if is_filled(order) and order["filled_at"] <= at:
            net += signed_fill(order)
    return net


def is_rearm_stamp(order: dict[str, Any], ledger_before: Decimal) -> bool:
    """이 주문이 **체결 인지 후 재무장을 끝냈다**는 증거인가.

    반전 주문이면 참이다 — `quantity = |target - current|` 에서 `current` 는 거래소 읽기이므로
    `target` 이 `ledger_before` 의 반대편에 같은 크기로 있다는 것은 **계획기가 그 체결을
    반영한 뒤 반대편을 다시 무장했다**는 뜻이다.

    ★★**엔진의 포지션은 증언하지 않는다.** 초안은 「그러므로 엔진도 같은 쪽에 있었다」고
    적었는데 반증됐다 — 엔진은 이미 그 방향을 들고 있어도 같은 `trade_id` 로 pending stop 을
    다시 무장할 수 있다(`strategy_state.py:728-740`). 실측 `39731d57` `16:24:11`: 엔진 short ·
    거래소 long 인데 이 함수는 참을 낸다. 모듈 docstring §판별식 참조.

    거짓이 되는 경우 — 최초 진입(`ledger_before == 0`) · 크기보정 주문(실측 `0.001`,
    부호가 안 바뀐다) · 부분청산.
    """
    if ledger_before == 0:
        return False
    target = ledger_before + signed_quantity(order)
    if target == 0:
        return False
    if (target > 0) == (ledger_before > 0):
        return False  # 부호가 안 바뀌었다 — 반전이 아니다
    magnitude, before = abs(target), abs(ledger_before)
    return abs(magnitude - before) <= _REVERSAL_REL_TOL * max(magnitude, before)


def find_rearm_stamps(orders: Sequence[dict[str, Any]]) -> list[datetime]:
    """한 (세션, 심볼) 의 주문 흐름에서 재무장 도장 시각을 뽑는다.

    ★`created_at` 이 없는 행은 도장이 될 수 없다 — 발주 시각을 모르면 「그 순간」을
    증언할 수 없다. 조용히 지금으로 치지 않는다.

    ★`exclude=order` — 자기 체결을 자기 발주 전 원장에 넣지 않는다(위 `ledger_net_at`).
    """
    stamps: list[datetime] = []
    for order in orders:
        created_at = order.get("created_at")
        if created_at is None:
            continue
        if is_rearm_stamp(order, ledger_net_at(orders, created_at, exclude=order)):
            stamps.append(created_at)
    return sorted(stamps)


# --- 직접 회복 검사 (원장을 아예 안 쓰는 순수 함수) -----------------------------


def next_tick_horizon_seconds(interval_seconds: int) -> float:
    """「바로 다음 평가」로 인정하는 상한. 한 자리에서만 계산한다."""
    return interval_seconds * _NEXT_TICK_INTERVAL_FACTOR


def recovery_label_for(
    *,
    observed_at: datetime,
    interval_seconds: int,
    next_observation_at: datetime | None,
    deactivated_at: datetime | None,
    deactivated_reason: str | None,
    corpus_end: datetime,
) -> str | None:
    """이 발산이 **다음 평가에 나았는가**. 판정할 수 없으면 `None`.

    원장도 체결 시각도 보지 않는다 — 같은 스트림의 다음 관측이 있느냐만 본다.

    `None` 을 내는 두 자리가 이 식의 전부인 약점이라 **명시적으로** 구분한다:

    - **로그 절단** — 후속자가 아직 태어나지 않았을 수 있다. 노출은 게이트 표본 주기
      이하이고, 아카이브 합집합이 다음 실행에서 소급 정정한다(모듈 docstring §남는 위험).
    - **세션이 우리 손에 꺼졌다**(`user_stopped`) 또는 **사유 미상** — 회복할 기회를
      우리가 뺏은 것이라 「안 나았다」로 접지 않는다. ★사유 NULL 은 실재한다(25세션 중
      12세션, [ADR-024] 창 정의 ①). 추측하지 않고 상위 식에 넘긴다.
    """
    horizon = next_tick_horizon_seconds(interval_seconds)
    if next_observation_at is not None:
        return (
            "phantom"
            if (next_observation_at - observed_at).total_seconds() <= horizon
            else "replay_lag"
        )
    if deactivated_at is not None and (deactivated_at - observed_at).total_seconds() <= horizon:
        if deactivated_reason is None or deactivated_reason == "user_stopped":
            return None  # 회복할 기회를 우리가 뺏었거나 사유를 모른다
        return "phantom"  # 자동 사망 — 낫지 않았고 그래서 관측이 끊겼다
    if (corpus_end - observed_at).total_seconds() > horizon:
        return "replay_lag"  # 충분히 지켜봤고 다시 안 왔다
    return None  # 로그 창이 여기서 끝난다


def next_observation_index(
    events: Sequence[DivergenceEvent],
) -> dict[tuple[UUID, str], list[datetime]]:
    """(세션, 심볼) 별 관측 시각을 **정렬해서** 준다.

    ★입력 순서에 의존하지 않는다 — 호출자가 정렬해 준다는 것은 암묵 계약이고, 그게 흐트러지면
    후속자가 조용히 바뀌어 무해가 유령이 된다(같은 이유로 최신 체결도 `[-1]` 이 아니라 `max`).
    """
    index: dict[tuple[UUID, str], list[datetime]] = {}
    for event in events:
        index.setdefault((event.session_id, event.symbol), []).append(event.at)
    for stamps in index.values():
        stamps.sort()
    return index


def adjudicate(
    events: list[DivergenceEvent],
    sessions: dict[UUID, dict[str, Any]],
    orders: list[dict[str, Any]],
    *,
    corpus_end: datetime,
) -> list[Verdict]:
    """관측마다 후속 관측·세션 소유 최신 체결·최신 재무장 도장을 찾아 라벨을 매긴다.

    `corpus_end` = 관측을 읽어낸 창의 끝(로그의 마지막 타임스탬프 / 아카이브의 `log_to`).
    ★기본값을 주지 않는다 — 안 넘기면 「지금」으로 접히고, 그러면 **로그 절단이 회복으로
    오독**된다. 호출자가 무엇을 봤는지 말하게 강제한다.
    """
    owned: dict[UUID, list[dict[str, Any]]] = {}
    for order in orders:
        key = order["idempotency_key"] or ""
        match = _IDEM_SESSION_PATTERN.match(key)
        if match is None:
            continue  # 원장에 남았지만 세션 귀속 불가 — `unattributed` 의 원인이다
        owned.setdefault(UUID(match.group("session")), []).append(order)

    # (세션, 심볼) 별 하트비트는 관측과 무관하므로 한 번만 계산한다.
    rearm_index: dict[tuple[UUID, str], list[datetime]] = {}
    for session_id, session_orders in owned.items():
        for symbol in {str(o["symbol"]) for o in session_orders}:
            rearm_index[(session_id, symbol)] = find_rearm_stamps(
                [o for o in session_orders if str(o["symbol"]) == symbol]
            )

    observation_index = next_observation_index(events)

    verdicts: list[Verdict] = []
    for event in events:
        sess = sessions.get(event.session_id)
        if sess is None:
            raise ValueError(f"세션 행이 없다: {event.session_id}")
        interval_seconds = _INTERVAL_SECONDS[sess["interval"]]
        horizon = floor_to_interval(event.at, interval_seconds)

        stream = observation_index.get((event.session_id, event.symbol), [])
        after = bisect_right(stream, event.at)
        next_at = stream[after] if after < len(stream) else None

        candidates = [
            f
            for f in owned.get(event.session_id, [])
            if f["symbol"] == event.symbol and is_filled(f) and f["filled_at"] <= event.at
        ]
        # ★`[-1]` 이 아니라 `max` 다 — SQL 이 `ORDER BY` 로 주지만 그건 호출자의
        # 사정이고, 정렬을 암묵 계약으로 두면 순서가 흐트러졌을 때 **갈래가 조용히 뒤집힌다**
        # (오래된 체결을 집으면 무해가 유령이 된다). 단위 테스트가 이걸 잡았다.
        last = max(candidates, key=lambda f: f["filled_at"]) if candidates else None

        stamps = [h for h in rearm_index.get((event.session_id, event.symbol), []) if h <= event.at]
        last_rearm = max(stamps) if stamps else None

        deactivated_at = sess["deactivated_at"]
        deactivated_reason = sess["deactivated_reason"]

        recovery_label: str | None
        rearm_label: str | None
        if last is None:
            # 세션 소유 체결이 없다 — 어느 식도 판정하지 않는다(운영자 청산 등).
            # ★게이트는 `phantom` 만 실격으로 보므로 이 라벨은 조용히 무해 취급된다.
            #   현재 코퍼스에 0건이라 도달하지 않지만 fail-open 인 것은 사실이다(별도 BL).
            label = horizon_label = threshold_label = "unattributed"
            recovery_label = "unattributed"
            rearm_label = "unattributed"
        else:
            horizon_label = "replay_lag" if last["filled_at"] >= horizon else "phantom"
            gap = (event.at - last["filled_at"]).total_seconds()
            threshold_label = "replay_lag" if gap < interval_seconds else "phantom"
            if last_rearm is None:
                # 재무장을 한 번도 못 봤다 — 재무장식은 판정하지 않는다
                # (증거 부재를 유령으로 접지 않는다).
                rearm_label = None
            else:
                rearm_label = "phantom" if last_rearm > last["filled_at"] else "replay_lag"

            recovery_label = recovery_label_for(
                observed_at=event.at,
                interval_seconds=interval_seconds,
                next_observation_at=next_at,
                deactivated_at=deactivated_at,
                deactivated_reason=deactivated_reason,
                corpus_end=corpus_end,
            )
            # 채택 순서 = 회복식 → 재무장식 → 봉경계식. 위가 판정을 못 하면 아래로 내려간다.
            if recovery_label is not None:
                label = recovery_label
            elif rearm_label is not None:
                label = rearm_label
            else:
                label = horizon_label
            # ★★★래칫 — **교체는 앞 판별식이 실격시킨 것을 사면할 수 없다.**
            #
            # 「회복식 phantom ⊇ 재무장식 phantom」은 n=19 에서 **관측된 사실**이지 두 식의
            # 성질이 아니다. codex 적대 리뷰(2026-08-05)가 반례를 냈다 — `probe_failed` 로
            # tick 하나가 빠지면(`live_signal.py:725`, strike 는 보존되고 `direction` 줄은
            # 안 남는다) 다음 관측이 `T+120s` 에 오고, 회복식은 그걸 `replay_lag` 으로 접는다.
            # 재무장식이 `phantom` 이라 해도 채택이 덮어써서 **실격이 하나 사라진다** ⇒
            # `window_start` 가 앞당겨지고 누적이 는다 = **게이트 fail-open**.
            #
            # ⇒ 채택 라벨의 **바닥**을 앞 식으로 깐다. 이 줄이 없으면 판별식 교체가
            # 「관대해지는 방향」으로 갈 수 있고, 그건 이 게이트가 막으려는 바로 그것이다.
            # ★관측 19건에서는 아무것도 바꾸지 않는다(이미 진부분집합이므로) — 이 방어는
            # **관측되지 않은 경로에서만** 발동한다. 그래서 골든이 아니라 전용 테스트가 지킨다.
            if rearm_label == "phantom":
                label = "phantom"

        died_here = (
            deactivated_reason == "position_divergence"
            and deactivated_at is not None
            and abs((deactivated_at - event.at).total_seconds()) <= 1.0
        )

        verdicts.append(
            Verdict(
                event=event,
                interval_seconds=interval_seconds,
                horizon=horizon,
                last_fill_at=last["filled_at"] if last else None,
                last_fill_side=last["side"] if last else None,
                last_fill_qty=str(last["quantity"]) if last else None,
                last_rearm_at=last_rearm,
                next_observation_at=next_at,
                label=label,
                recovery_label=recovery_label,
                rearm_label=rearm_label,
                horizon_label=horizon_label,
                threshold_label=threshold_label,
                died_here=died_here,
            )
        )
    return verdicts


@dataclass
class Summary:
    """식별식 3종의 집계 + 사망 상관.

    ★**사망 상관은 `independent_label`(재무장식 → 봉경계식) 기준으로 잰다.** 채택 라벨인
    회복식은 「다음 tick 도 어긋났나」라 프로덕션 킬(「연속 2회 판정된 tick」)과 거의 같은
    신호이고, 그걸로 사망 상관을 재면 동어반복이 된다. 채택 라벨 기준 값은
    `adopted_*` 로 따로 보고한다 — 지우지 않는다. 둘이 갈리면 그 자체가 정보다.
    """

    counts: dict[str, int] = field(default_factory=dict)
    rearm_counts: dict[str, int] = field(default_factory=dict)
    horizon_counts: dict[str, int] = field(default_factory=dict)
    deaths_total: int = 0
    deaths_labelled_phantom: int = 0
    replay_lag_total: int = 0
    replay_lag_survived: int = 0
    adopted_deaths_labelled_phantom: int = 0
    adopted_replay_lag_total: int = 0
    adopted_replay_lag_survived: int = 0
    predicate_disagreements: int = 0
    rearm_overrides: int = 0
    rearm_undecided: int = 0
    recovery_overrides: int = 0
    recovery_undecided: int = 0
    # ★문턱의 감사 눈금 — 분리가 좁아지면 여기서 먼저 보인다.
    max_phantom_gap: float | None = None
    min_replay_lag_gap: float | None = None
    ambiguous_gap_band: int = 0

    @property
    def death_correlation_holds(self) -> bool:
        """독립 검사 — 원장 기반 라벨(재무장식)이 tick 기반 신호(사망)와 일치하는가."""
        return (
            self.deaths_total == self.deaths_labelled_phantom
            and self.replay_lag_total == self.replay_lag_survived
        )

    @property
    def adopted_death_correlation_holds(self) -> bool:
        """참고 — 채택 라벨 기준. 회복식에서는 거의 동어반복이라 판정에 쓰지 않는다."""
        return (
            self.deaths_total == self.adopted_deaths_labelled_phantom
            and self.adopted_replay_lag_total == self.adopted_replay_lag_survived
        )


def summarize(verdicts: list[Verdict]) -> Summary:
    summary = Summary()
    for verdict in verdicts:
        summary.counts[verdict.label] = summary.counts.get(verdict.label, 0) + 1
        summary.horizon_counts[verdict.horizon_label] = (
            summary.horizon_counts.get(verdict.horizon_label, 0) + 1
        )
        rearm_key = verdict.rearm_label if verdict.rearm_label is not None else "(미판정)"
        summary.rearm_counts[rearm_key] = summary.rearm_counts.get(rearm_key, 0) + 1
        # ★이 불일치는 **봉경계식 vs 시간문턱식** 이다 — 채택 라벨과 비교하면 교체가
        #   이 숫자에 섞여 들어와 옛 관측과 비교할 수 없게 된다. 판이 바뀌어도 불변이다.
        if verdict.horizon_label != verdict.threshold_label:
            summary.predicate_disagreements += 1
        if verdict.rearm_label is None:
            summary.rearm_undecided += 1
        elif verdict.rearm_label != verdict.horizon_label:
            summary.rearm_overrides += 1
        if verdict.recovery_label is None:
            summary.recovery_undecided += 1
        elif verdict.rearm_label is not None and verdict.recovery_label != verdict.rearm_label:
            summary.recovery_overrides += 1

        gap = verdict.next_gap_seconds
        if gap is not None and verdict.recovery_label is not None:
            if verdict.recovery_label == "phantom":
                summary.max_phantom_gap = max(summary.max_phantom_gap or gap, gap)
            elif verdict.recovery_label == "replay_lag":
                summary.min_replay_lag_gap = min(summary.min_replay_lag_gap or gap, gap)
            near = next_tick_horizon_seconds(verdict.interval_seconds)
            if near < gap <= verdict.interval_seconds * _AMBIGUOUS_BAND_FACTOR:
                summary.ambiguous_gap_band += 1

        independent = verdict.independent_label
        if verdict.died_here:
            summary.deaths_total += 1
            if independent == "phantom":
                summary.deaths_labelled_phantom += 1
            if verdict.label == "phantom":
                summary.adopted_deaths_labelled_phantom += 1
        if independent == "replay_lag":
            summary.replay_lag_total += 1
            if not verdict.died_here:
                summary.replay_lag_survived += 1
        if verdict.label == "replay_lag":
            summary.adopted_replay_lag_total += 1
            if not verdict.died_here:
                summary.adopted_replay_lag_survived += 1
    return summary


def render(verdicts: list[Verdict], summary: Summary, corpus_end: datetime) -> str:
    out: list[str] = []
    header = (
        f"{'관측시각(UTC)':<26} {'세션':<9} {'엔진':>10} {'거래소':>8} "
        f"{'다음관측(s)':>12} {'라벨':<12} {'재무장식':<12} {'봉경계식':<12} 사망"
    )
    out.append(header)
    out.append("-" * len(header))
    for verdict in verdicts:
        nxt = verdict.next_gap_seconds
        out.append(
            f"{verdict.event.at.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]:<26} "
            f"{str(verdict.event.session_id)[:8]:<9} "
            f"{verdict.event.engine:>10.6f} {verdict.event.exchange:>8.3f} "
            f"{(f'{nxt:.2f}' if nxt is not None else '-'):>12} "
            f"{verdict.label:<12} {verdict.rearm_label!s:<12} {verdict.horizon_label:<12} "
            f"{'★' if verdict.died_here else ''}"
        )

    out.append("")
    out.append(f"코퍼스 지평: {corpus_end.isoformat()}  (이 뒤는 아직 못 본 시간이다)")
    out.append(
        f"관측 {len(verdicts)}건 — 채택(회복식) "
        + " · ".join(f"{label} {count}" for label, count in sorted(summary.counts.items()))
    )
    out.append(
        "  재무장식이라면 — "
        + " · ".join(f"{label} {count}" for label, count in sorted(summary.rearm_counts.items()))
        + "  |  봉경계식이라면 — "
        + " · ".join(f"{label} {count}" for label, count in sorted(summary.horizon_counts.items()))
    )
    out.append(
        f"  회복식이 재무장식을 뒤집은 관측 {summary.recovery_overrides}건 · "
        f"회복식이 판정 못 해 강하한 관측 {summary.recovery_undecided}건 "
        f"(재무장식 미판정 {summary.rearm_undecided}건)"
    )
    out.append(
        f"문턱 감사: phantom 최대 간격 "
        f"{'-' if summary.max_phantom_gap is None else f'{summary.max_phantom_gap:.2f}s'} · "
        f"replay_lag 최소 간격 "
        f"{'-' if summary.min_replay_lag_gap is None else f'{summary.min_replay_lag_gap:.2f}s'} · "
        f"애매대(1.5~2.5봉 = tick 한 번 건너뜀) {summary.ambiguous_gap_band}건"
        + (" ✓ 분리 유지" if summary.ambiguous_gap_band == 0 else " ⚠ 분리가 좁아졌다")
    )
    out.append(
        f"사망 상관 (독립 검사 — ★재무장식 기준): 사망 {summary.deaths_total}건 중 "
        f"phantom 판정 {summary.deaths_labelled_phantom}건 · "
        f"replay_lag {summary.replay_lag_total}건 중 생존 {summary.replay_lag_survived}건"
    )
    out.append(
        f"  (참고 — 채택 라벨 기준: 사망 {summary.deaths_total}건 중 "
        f"{summary.adopted_deaths_labelled_phantom}건 · replay_lag "
        f"{summary.adopted_replay_lag_total}건 중 생존 {summary.adopted_replay_lag_survived}건. "
        "★회복식은 사망 규칙과 거의 같은 신호라 이 값은 독립 증거가 아니다)"
    )
    out.append(
        f"봉경계식 vs 시간문턱식 불일치: {summary.predicate_disagreements}건"
        + ("" if summary.predicate_disagreements else " (이 창에서는 두 식이 같은 답을 낸다)")
    )
    out.append("")
    if summary.death_correlation_holds:
        out.append("✓ 사망 상관 성립 — 원장 기반 라벨이 tick 기반 신호와 일치한다.")
    else:
        out.append("✗ 사망 상관 불성립 — 판별식을 기각하고 재설계해라.")
    out.append(
        "★적합은 검증이 아니다 — 판별식을 이 관측들에서 유도했다. 갚을 방법은 전향 예측뿐이다."
    )
    return "\n".join(out)


def parse_events_json(blob: dict[str, Any], symbols: dict[UUID, str]) -> list[DivergenceEvent]:
    """이전 `--json` 출력(또는 `.soak/phantom-*.json` 아카이브)에서 관측을 되살린다.

    ★**워커 로그는 컨테이너 수명에 묶인다** — 재기동한 창의 관측은 로그로 다시 읽을 수 없고
    아카이브에만 남는다. 판별식을 바꿀 때 **과거 관측 전량에 재적용**하려면 그 아카이브를
    입력으로 받을 수 있어야 한다(그게 없으면 「바꾸기 전에 과거에 적용했다」를 못 한다).

    `symbol` 은 아카이브에 없으므로 **세션 행에서 가져온다** — 추측하지 않는다.
    """
    events: list[DivergenceEvent] = []
    for entry in blob.get("verdicts", []):
        session_id = UUID(str(entry["session_id"]))
        symbol = symbols.get(session_id)
        if symbol is None:
            raise ValueError(f"세션 행이 없다: {session_id}")
        events.append(
            DivergenceEvent(
                at=datetime.fromisoformat(str(entry["at"])),
                session_id=session_id,
                symbol=symbol,
                category="direction",
                # ★게이트 아카이브(`.soak/phantom-*.json`)는 `engine`/`exchange` 를
                #   **버린다** — `{at, label, session_id}` 만 싣는다. 필수로 읽으면
                #   그 아카이브를 재판정할 수 없다(codex challenge 2026-08-05: KeyError
                #   재현). 라벨은 이 두 값에 의존하지 않으므로(전용 테스트로 고정)
                #   없으면 0 으로 둔다 — 표시에만 쓰인다.
                engine=float(entry.get("engine", 0.0)),
                exchange=float(entry.get("exchange", 0.0)),
            )
        )
    return sorted(events, key=lambda e: e.at)


async def _run(args: argparse.Namespace, raw: str) -> int:
    # 아카이브 입력은 심볼을 안 담으므로 세션 행을 먼저 읽어야 관측을 만들 수 있다.
    # 로그 입력은 반대로 관측을 먼저 만들어야 세션 목록을 안다. 두 경로가 만나는 지점이
    # `events` 이고, 그 전까지는 세션 id 집합만 공유한다.
    archive: dict[str, Any] | None = None
    log_events: list[DivergenceEvent] = []
    # ★창의 끝. 회복식이 「아직 못 본 시간」과 「지켜봤는데 안 왔다」를 가르는 데 쓴다.
    declared_horizon: datetime | None = None
    if args.events_json is not None:
        archive = json.loads(raw)
        if not archive.get("verdicts"):
            print(f"{args.events_json} 에 관측이 없다.", file=sys.stderr)
            return 1
        session_ids = {UUID(str(v["session_id"])) for v in archive["verdicts"]}
        # 게이트 아카이브는 `log_to`, 분류기 `--json` 출력은 `generated_at` 을 싣는다.
        # 둘 다 없으면 아래에서 마지막 관측 시각으로 떨어지고, 그러면 각 스트림의 마지막
        # 관측이 **판정 불가**가 된다 — 모르는 것을 회복으로 접지 않는다.
        raw_horizon = archive.get("log_to") or archive.get("generated_at")
        declared_horizon = datetime.fromisoformat(str(raw_horizon)) if raw_horizon else None
    else:
        lines = raw.splitlines()
        log_events = parse_log(lines, category=args.category)
        if not log_events:
            print(f"category={args.category} 관측이 없다 — 로그 창을 확인해라.", file=sys.stderr)
            return 1
        session_ids = {e.session_id for e in log_events}
        declared_horizon = parse_log_horizon(lines)

    # ★호출자가 창의 끝을 **안다면** 그게 우선이다. `soak-gate.sh` 는 `docker logs
    # --timestamps` 로 `LOG_LAST` 를 이미 갖고 있으면서 분류기에는 타임스탬프 **없이**
    # 파이프한다 — 그러면 지평이 Docker 가 보장하는 로그 끝이 아니라 **앱 줄 정규식이 찾은
    # 마지막 시각**이 되고, 그 포맷은 timezone 을 버리고 UTC 로 강제한다. 무타임스탬프
    # 후행 줄·포맷 변경·비-UTC 워커가 tail 판정을 조용히 바꾼다(codex challenge 2026-08-05 P2).
    # 인자를 받으면 그 경로가 아예 사라진다.
    if args.corpus_end is not None:
        declared_horizon = datetime.fromisoformat(args.corpus_end)

    engine, sm = create_worker_engine_and_sm()
    try:
        sessions = await _load_sessions(sm, session_ids)
        events = (
            parse_events_json(archive, {sid: str(row["symbol"]) for sid, row in sessions.items()})
            if archive is not None
            else log_events
        )
        orders = await _load_orders(sm, {e.symbol for e in events})
    finally:
        await engine.dispose()

    if args.since is not None:
        cutoff = datetime.fromisoformat(args.since)
        events = [e for e in events if e.at >= cutoff]
        if not events:
            print(f"--since {args.since} 뒤에 관측이 없다.", file=sys.stderr)
            return 1

    # 선언된 지평이 마지막 관측보다 앞설 수는 없다(그 관측을 실제로 읽었으므로).
    corpus_end = max([e.at for e in events] + ([declared_horizon] if declared_horizon else []))

    verdicts = adjudicate(events, sessions, orders, corpus_end=corpus_end)
    summary = summarize(verdicts)

    if args.json:
        print(
            json.dumps(
                {
                    "generated_at": datetime.now(UTC).isoformat(),
                    "predicate_version": PREDICATE_VERSION,
                    "corpus_end": corpus_end.isoformat(),
                    "verdicts": [v.as_dict() for v in verdicts],
                    "counts": summary.counts,
                    "rearm_counts": summary.rearm_counts,
                    "horizon_counts": summary.horizon_counts,
                    "recovery_overrides": summary.recovery_overrides,
                    "recovery_undecided": summary.recovery_undecided,
                    "rearm_overrides": summary.rearm_overrides,
                    "rearm_undecided": summary.rearm_undecided,
                    "max_phantom_gap": summary.max_phantom_gap,
                    "min_replay_lag_gap": summary.min_replay_lag_gap,
                    "ambiguous_gap_band": summary.ambiguous_gap_band,
                    "deaths_total": summary.deaths_total,
                    "deaths_labelled_phantom": summary.deaths_labelled_phantom,
                    "replay_lag_total": summary.replay_lag_total,
                    "replay_lag_survived": summary.replay_lag_survived,
                    "adopted_deaths_labelled_phantom": summary.adopted_deaths_labelled_phantom,
                    "adopted_replay_lag_total": summary.adopted_replay_lag_total,
                    "adopted_replay_lag_survived": summary.adopted_replay_lag_survived,
                    "adopted_death_correlation_holds": summary.adopted_death_correlation_holds,
                    "predicate_disagreements": summary.predicate_disagreements,
                    "death_correlation_holds": summary.death_correlation_holds,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        print(render(verdicts, summary, corpus_end))

    return 0 if summary.death_correlation_holds else 2


def main() -> int:
    parser = argparse.ArgumentParser(
        description="`direction` 발산을 원장 체결 시각으로 replay_lag / phantom 재판정한다 ([BL-591])."
    )
    parser.add_argument("--log", help="워커 로그 파일 (기본: stdin)")
    parser.add_argument(
        "--events-json",
        help="이전 --json 출력 / .soak 아카이브에서 관측을 되살려 재판정 (로그 대신)",
    )
    parser.add_argument("--since", help="이 ISO 시각 이후 관측만 (예: 2026-08-03T09:53:00+00:00)")
    parser.add_argument(
        "--corpus-end",
        help="창의 끝(ISO). 회복식이 「나았다」와 「아직 못 봄」을 가르는 경계다. "
        "안 주면 로그 전체의 최대 타임스탬프에서 유도한다 — 호출자가 알면 넘겨라.",
    )
    parser.add_argument(
        "--category", default="direction", help="재판정할 category (기본: direction)"
    )
    parser.add_argument("--json", action="store_true", help="기계용 JSON 출력")
    args = parser.parse_args()
    # 파일 읽기는 이벤트 루프 밖에서 한다 (ruff ASYNC240 — async 안의 blocking IO).
    if args.events_json:
        raw = Path(args.events_json).read_text(encoding="utf-8")
    elif args.log:
        raw = Path(args.log).read_text(encoding="utf-8", errors="replace")
    else:
        raw = sys.stdin.read()
    return asyncio.run(_run(args, raw))


if __name__ == "__main__":
    raise SystemExit(main())
