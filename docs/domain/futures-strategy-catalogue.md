# 선물 추세 전략 30종의 실행 규칙

원천은 각 지표의 공식 정의다. 아래 진입·무효화 조합은 QuantBridge가 검증할 연구 변형이며,
원저자의 완성 전략 또는 수익성 보장을 뜻하지 않는다. 규칙 데이터와 실행 가능한 개발 명세의
정본은 `tools/research/strategy_catalogue30.py`다. 생성 평가에 개발 정답 명세를 넣지 않는다.

## 모든 전략에 적용하는 주문·청산

1. 완료 봉에서 의도를 정하고 다음 봉 시가에 진입한다. 실제 진입가를 E라 한다.
2. 신호 봉과 바로 이전 완료 봉의 극값을 참조한다. 롱은 최저 L에 대해 R=1.1×(E−L), 숏은 최고 H에 대해 R=1.1×(H−E)다. R≤0은 진입하지 않는다.
3. SL은 손실 방향 1R, 최초 수량 50% 반익절은 이익 방향 1.5R에서 한 번이다.
4. 2R 수익에서 비용 전 본절을 보호하고, 이후 극값에서 2R 거리로 SL을 유리한 방향으로만 이동한다.
5. 무효화는 잔량 전체 청산이다. 반대 진입은 청산·보호 주문 취소 확인 뒤 새 세대로 반전한다. 같은 방향 반복 신호는 수량과 초기 R을 바꾸지 않는다.

[가정] 10%는 가격 자체의 10%가 아니라 **진입가와 두 봉 극값 사이 거리의 10% 버퍼**다.
분할 최소 수량을 충족하지 못하면 주문하지 않는다. 수수료·슬리피지·펀딩은 수익에서 별도 차감한다.
HA나 미완료 상위 봉의 합성 가격으로 체결하지 않는다.

## 방법별 조건

`C`는 종가, `H/L`은 고가/저가다. 교차는 전봉 이하→현재 초과(상향), 전봉 이상→현재 미만(하향)이다.
EMA는 대상 Pine 엔진의 SMA seed, RSI는 Wilder seed와 평탄 구간 100 계약을 따른다.
본 평가의 유한 신호 비교는 [수치 계약 v2](../development/sol-strategy-lab.md#평가와-재현)의
epsilon 동률을 적용한다. UTC timestamp는 봉 시작이며 신호는 그 봉 완료 뒤 확정한다.
같은 봉의 양방향 진입은 보류하며, 반대 진입 → 보유 방향 무효화 → 유지 순으로 결정한다.

| ID | 방법 | 롱 진입 | 숏 진입 | 롱 / 숏 무효화 | 공식 지표 정의 | 명세 컴파일 |
| --- | --- | --- | --- | --- | --- | --- |
| 01 | EMA 20/50 교차 | EMA20이 EMA50을 상향 교차 | EMA20이 EMA50을 하향 교차 | EMA20<EMA50 / EMA20>EMA50 | [공식 문서](https://www.tradingview.com/support/solutions/43000592270-exponential-moving-average/) | 세 언어 지원 |
| 02 | EMA 추세 눌림 복귀 | EMA20>EMA50, 전봉 C<=전봉 EMA20, 현재 C>EMA20 | EMA20<EMA50, 전봉 C>=전봉 EMA20, 현재 C<EMA20 | C<EMA50 / C>EMA50 | [공식 문서](https://www.tradingview.com/support/solutions/43000592270-exponential-moving-average/) | 세 언어 지원 |
| 03 | Donchian 20 돌파 | C가 현재봉 제외 직전20봉 최고가 상향 교차 | C가 현재봉 제외 직전20봉 최저가 하향 교차 | C<직전20봉 채널 중간값 / C>직전20봉 채널 중간값 | [공식 문서](https://www.tradingview.com/support/solutions/43000502253-donchian-channels-dc/) | 세 언어 지원 |
| 04 | Turtle 55/20 | C가 현재봉 제외 직전55봉 최고가 상향 교차 | C가 현재봉 제외 직전55봉 최저가 하향 교차 | C<현재봉 제외 직전20봉 최저가 / C>현재봉 제외 직전20봉 최고가 | [공식 문서](https://www.tradingview.com/support/solutions/43000502253-donchian-channels-dc/) | 세 언어 지원 |
| 05 | Supertrend 전환 | ATR10x3 Supertrend가 하락에서 상승 regime으로 확정 전환 | ATR10x3 Supertrend가 상승에서 하락 regime으로 확정 전환 | Supertrend 하락 regime / Supertrend 상승 regime | [공식 문서](https://www.tradingview.com/support/solutions/43000634738-supertrend/) | 명시적 미지원 |
| 06 | DMI ADX 추세 | DMI14 +DI가 -DI 상향 교차하고 ADX14>25 | -DI가 +DI 상향 교차하고 ADX14>25 | +DI<-DI 또는 ADX<20 / -DI<+DI 또는 ADX<20 | [공식 문서](https://www.tradingview.com/support/solutions/43000589099-average-directional-index-adx/) | 명시적 미지원 |
| 07 | Ichimoku 구름 확인 | 9전환선이 26기준선 상향 교차하고 C가 표시구름 위 | 9전환선이 26기준선 하향 교차하고 C가 표시구름 아래 | 기준선 하회 또는 구름 진입 / 기준선 상회 또는 구름 진입 | [공식 문서](https://www.tradingview.com/support/solutions/43000589152-ichimoku-cloud/) | 명시적 미지원 |
| 08 | Keltner 추세 돌파 | C가 EMA20+2ATR20 상향 교차하고 EMA20 상승 | C가 EMA20-2ATR20 하향 교차하고 EMA20 하락 | C<EMA20 / C>EMA20 | [공식 문서](https://www.tradingview.com/support/solutions/43000502266-keltner-channels-kc/) | 세 언어 지원 |
| 09 | Bollinger squeeze 돌파 | BB20x2 bandwidth가 이전120봉 최소 이하가 된 후5봉 이내 상단 상향 돌파 | 같은 squeeze 후5봉 이내 하단 하향 돌파 | C<SMA20 / C>SMA20 | [공식 문서](https://www.tradingview.com/support/solutions/43000501840-bollinger-bands-bb/) | 명시적 미지원 |
| 10 | ATR 확장 돌파 | C가 전봉C+0.5*전봉ATR20 상향 교차 | C가 전봉C-0.5*전봉ATR20 하향 교차 | C<EMA20 / C>EMA20 | [공식 문서](https://www.tradingview.com/support/solutions/43000501823-average-true-range-atr/) | 세 언어 지원 |
| 11 | RSI 중심선 추세 | RSI14가50 상향 교차하고 C>EMA200 | RSI14가50 하향 교차하고 C<EMA200 | RSI<45 또는 C<EMA200 / RSI>55 또는 C>EMA200 | [공식 문서](https://www.tradingview.com/support/solutions/43000502338-relative-strength-index-rsi/) | 세 언어 지원 |
| 12 | Stochastic RSI 추세 | StochRSI14/14/3/3 K가 D 상향 교차,K<=20,C>EMA200 | K가 D 하향 교차,K>=80,C<EMA200 | 반대K/D교차와 K<50 또는 C<EMA200 / 반대K/D교차와 K>50 또는 C>EMA200 | [공식 문서](https://www.tradingview.com/support/solutions/43000502333-stochastic-rsi-stoch-rsi/) | 명시적 미지원 |
| 13 | MACD signal 추세 | MACD12/26이 signal9 상향 교차하고 C>EMA200 | MACD12/26이 signal9 하향 교차하고 C<EMA200 | 반대교차 또는 C<EMA200 / 반대교차 또는 C>EMA200 | [공식 문서](https://www.tradingview.com/support/solutions/43000502344-moving-average-convergence-divergence-macd-indicator/) | 세 언어 지원 |
| 14 | MACD 영선 교차 | MACD12/26이0 상향 교차 | MACD12/26이0 하향 교차 | MACD<0 / MACD>0 | [공식 문서](https://www.tradingview.com/support/solutions/43000502344-moving-average-convergence-divergence-macd-indicator/) | 세 언어 지원 |
| 15 | ROC 추세 확인 | ROC12가0 상향 교차하고 C>SMA50 | ROC12가0 하향 교차하고 C<SMA50 | ROC<0 또는 C<SMA50 / ROC>0 또는 C>SMA50 | [공식 문서](https://www.tradingview.com/support/solutions/43000502343-rate-of-change-roc/) | 세 언어 지원 |
| 16 | RSI 확정 pivot 다이버전스 | RSI14의3/3확정pivot에서 가격저점하락/RSI저점상승 후 확인봉C>직전H | 가격고점상승/RSI고점하락 후 확인봉C<직전L | 둘째 pivot 저점 이탈 / 둘째 pivot 고점 이탈 | [공식 문서](https://www.tradingview.com/support/solutions/43000502338-relative-strength-index-rsi/) | 명시적 미지원 |
| 17 | Stochastic 추세 재개 | Stoch14/3/3 K가D 상향 교차,50<=K<=80,C>EMA200 | K가D 하향 교차,20<=K<=50,C<EMA200 | 반대교차 또는 C<EMA200 / 반대교차 또는 C>EMA200 | [공식 문서](https://www.tradingview.com/support/solutions/43000502332-stochastic-stoch/) | 세 언어 지원 |
| 18 | CCI 추세 확장 | CCI20이+100 상향 교차,C>EMA200 | CCI20이-100 하향 교차,C<EMA200 | CCI<0 또는 C<EMA200 / CCI>0 또는 C>EMA200 | [공식 문서](https://www.tradingview.com/support/solutions/43000502001-commodity-channel-index-cci/) | 세 언어 지원 |
| 19 | Williams R 복귀 | WPR14가-80 상향 교차,C>EMA200 | WPR14가-20 하향 교차,C<EMA200 | WPR<-80 또는 C<EMA200 / WPR>-20 또는 C>EMA200 | [공식 문서](https://www.tradingview.com/support/solutions/43000501985-williams-r-r/) | 세 언어 지원 |
| 20 | TSI 추세 전환 | TSI25/13이 자신의EMA7 상향 교차,TSI>0 | TSI25/13이 자신의EMA7 하향 교차,TSI<0 | 반대교차 또는 TSI<0 / 반대교차 또는 TSI>0 | [공식 문서](https://www.tradingview.com/support/solutions/43000592290-true-strength-index/) | 명시적 미지원 |
| 21 | UTC 일중 VWAP 복귀 | C>EMA200,UTC일중VWAP 상승,C가VWAP 상향 교차 | C<EMA200,UTC일중VWAP 하락,C가VWAP 하향 교차 | C<VWAP / C>VWAP | [공식 문서](https://www.tradingview.com/support/solutions/43000502018-volume-weighted-average-price-vwap/) | 세 언어 지원 |
| 22 | Anchored VWAP 돌파 | 사전고정UTC anchor AVWAP 상향교차,C>EMA200,C>직전20봉HH | AVWAP 하향교차,C<EMA200,C<직전20봉LL | C<AVWAP / C>AVWAP | [공식 문서](https://www.tradingview.com/support/solutions/43000669764-anchored-vwap-drawing-tool/) | 세 언어 지원 |
| 23 | OBV 확인 돌파 | C>EMA200,C>직전20봉HH,OBV>OBV의SMA20 | C<EMA200,C<직전20봉LL,OBV<OBV의SMA20 | C<EMA50 또는 OBV<OBV의SMA20 / C>EMA50 또는 OBV>OBV의SMA20 | [공식 문서](https://www.tradingview.com/support/solutions/43000502593-on-balance-volume-obv/) | 세 언어 지원 |
| 24 | CMF 추세 재개 | EMA20>EMA50,CMF20이+0.05 상향교차 | EMA20<EMA50,CMF20이-0.05 하향교차 | CMF<0 또는 EMA20<EMA50 / CMF>0 또는 EMA20>EMA50 | [공식 문서](https://help.chaikinanalytics.com/en_US/knowledge-center/chaikin-money-flow) | 세 언어 지원 |
| 25 | MFI 눌림 복귀 | C>상승EMA200,MFI14가20 상향교차 | C<하락EMA200,MFI14가80 하향교차 | C<EMA200 또는 MFI<20 / C>EMA200 또는 MFI>80 | [공식 문서](https://www.tradingview.com/support/solutions/43000502348-money-flow-mfi/) | 세 언어 지원 |
| 26 | Aroon 추세 시작 | Aroon25 Up이Down 상향교차,Up>=70,Down<=30 | Down이Up 상향교차,Down>=70,Up<=30 | Up<50 또는 Down>Up / Down<50 또는 Up>Down | [공식 문서](https://www.tradingview.com/support/solutions/43000501801-aroon-indicator/) | 세 언어 지원 |
| 27 | 선형회귀 채널 복귀 | 50봉OLS기울기>0,전봉C<=전봉잔차2sd하단,현재C>현재하단 | 기울기<0,전봉C>=전봉상단,현재C<현재상단 | 기울기<=0 또는 C<하단 / 기울기>=0 또는 C>상단 | [공식 문서](https://www.tradingview.com/support/solutions/43000644936-linear-regression/) | 세 언어 지원 |
| 28 | Heikin Ashi 추세 확인 | 실제C>EMA200,HA양봉2개가처음연속확정 | 실제C<EMA200,HA음봉2개가처음연속확정 | HA음봉 확정 / HA양봉 확정 | [공식 문서](https://www.tradingview.com/pine-script-docs/concepts/non-standard-charts-data/) | 세 언어 지원 |
| 29 | Chandelier 추세 전환 | C가전봉LL22+3ATR22 상향교차,C>EMA200 | C가전봉HH22-3ATR22 하향교차,C<EMA200 | C<전봉HH22-3ATR22 / C>전봉LL22+3ATR22 | [공식 문서](https://www.tradingview.com/support/solutions/43000773013-chandelier-exit/) | 세 언어 지원 |
| 30 | 완료4h EMA regime | 직전완료4h C>4hEMA200,1hEMA9가EMA21 상향교차 | 직전완료4h C<4hEMA200,1hEMA9가EMA21 하향교차 | 완료4h regime하락 또는 1hEMA9<EMA21 / 완료4h regime상승 또는 1hEMA9>EMA21 | [공식 문서](https://www.tradingview.com/pine-script-docs/concepts/other-timeframes-and-data/) | 명시적 미지원 |

09의 squeeze는 현재봉을 제외한 이전 유효 bandwidth 120개와 비교한다. event 봉에는 진입하지
않고 이후 1..5봉의 첫 돌파를 포지션과 무관하게 한 번 소비한다. 새 event는 창을 재설정한다.
16의 RSI strict 3/3 pivot은 우측 3봉 완료 후 확정하며 같은 유형의 연속 pivot 간격은 3..60봉이다.
확정 다음 봉 한 번만 확인하고, 보유 중 같은 방향 신호도 최신 둘째 pivot의 무효화 기준을 갱신한다.
초기 R은 바꾸지 않는다. 22의 anchor는 `2026-01-01T00:00:00Z`로 고정하고 그 봉부터 포함한다.
30은 03:00 시작 1h봉 완료 시 00:00~04:00의 완료 4h봉을 즉시 참조한다.
22는 anchor부터의 누적 이력, 30은 완료 4h봉 200개가 필요하다. 제품 초기화의 200개 1h봉만으로
두 전략의 준비를 보장하지 않는다([운영 측정 범위](../development/sol-operational-gate.md)).

## 스크립트와 검증의 경계

- Pine은 실제 `pine_v2`, Python은 CPython, TypeScript는 strict 컴파일 후 Node로 실행한다. 의도 출력만 허용하며 SL/TP·수량은 공통 원장이 소유한다.
- 명세 컴파일 지원 22종의 개발 스크립트는 `compile_strategy(StrategySpec.model_validate(candidate["reference_spec"]), language)`로 생성한다. 이 코드는 컴파일러 검증용이며 LLM의 정확도 점수로 사용하지 않는다.
- 직접 생성 A, 공개 오류 수정 B, 명세 생성 C의 실제 Sol 산출물은 `sol_strategy_lab.py`가 `runs/`에 원문·요청·usage·소스 hash와 함께 저장한다. 미지원·시간 초과·실패도 분모에 남긴다.
- 의미 검증은 별도 `strategy_oracle.py` 수식, 외부 포지션을 통제한 양방향·무효화 시험, 거래 원장 비교, 미래 봉 추가·재실행 검사를 사용한다. 기준 식이나 관찰 기회가 없는 항목은 통과로 바꾸지 않는다.
- 원장 비교의 범위는 독립 신호 + 공유 broker다. 실제 Bybit 데모 체결 관측과 과거 경제 분석을 같은 증거로 취급하지 않는다.

상세 실행·평가 계약은 [Sol 전략 실행 계약](../development/sol-strategy-lab.md)과
[ADR-046](../adr/046-generated-strategy-language-evaluation.md)에 있다.
