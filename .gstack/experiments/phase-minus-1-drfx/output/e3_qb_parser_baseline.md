# E3 — 현재 QB 파서 baseline 커버리지

| 파일 | 크기 | version | normalize | lex | parse | stdlib | 실패 단계 |
|------|:---:|:--:|:--:|:--:|:--:|:--:|------|
| i1_utbot.pine | 1781B | ✅ | ❌ | — | — | — | `normalize` PineUnsupportedError: 'tickerid'은(는) v4 전용 기능으로 자동 변환이 지원되지 않습니다. |
| i2_luxalgo.pine | 3903B | ✅ | ✅ | ✅ | ❌ | — | `parse` PineParseError: 예상치 못한 토큰 LBRACKET('[') |
| i3_drfx.pine | 38308B | ✅ | ✅ | ❌ | — | — | `lex` PineLexError: 인식할 수 없는 문자 '#' (라인 53, 컬럼 16) |
| s1_pbr.pine | 828B | ✅ | ✅ | ✅ | ✅ | ❌ | `stdlib` PineUnsupportedError: function not supported: ta.pivothigh |
| s2_utbot.pine | 2784B | ✅ | ❌ | — | — | — | `normalize` PineUnsupportedError: 'tickerid'은(는) v4 전용 기능으로 자동 변환이 지원되지 않습니다. |
| s3_rsid.pine | 6555B | ✅ | ✅ | ❌ | — | — | `lex` PineLexError: 인식할 수 없는 문자 '#' (라인 40, 컬럼 43) |

## 단계별 실패 상세

### i1_utbot.pine @ `normalize`
```
PineUnsupportedError: 'tickerid'은(는) v4 전용 기능으로 자동 변환이 지원되지 않습니다.
```

### i2_luxalgo.pine @ `parse`
```
PineParseError: 예상치 못한 토큰 LBRACKET('[')
```

### i3_drfx.pine @ `lex`
```
PineLexError: 인식할 수 없는 문자 '#' (라인 53, 컬럼 16)
```

### s1_pbr.pine @ `stdlib`
```
PineUnsupportedError: function not supported: ta.pivothigh
```

### s2_utbot.pine @ `normalize`
```
PineUnsupportedError: 'tickerid'은(는) v4 전용 기능으로 자동 변환이 지원되지 않습니다.
```

### s3_rsid.pine @ `lex`
```
PineLexError: 인식할 수 없는 문자 '#' (라인 40, 컬럼 43)
```