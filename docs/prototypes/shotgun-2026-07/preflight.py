# C 디자인 언어 프로토타입 정적 검사기 — 빌더 자기보고 대신 실측으로 판정한다
"""
사용법.
  python3 preflight.py screen-01-trading-cockpit.html [--marketing]
  python3 preflight.py --all
  python3 preflight.py --all --json

--marketing 는 앱 셸/상태 4종 요구를 면제한다(랜딩·로그인·프라이싱·웨이트리스트).
종료 코드 1 = FAIL 존재.
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
KIT = HERE / "_kit.html"

# variant-c 정본 팔레트. 여기 없는 hex 가 나오면 보고한다.
PALETTE = {
    "#0b0d0f", "#101214", "#141619", "#1a1d21", "#1e2226", "#22262b", "#31363d",
    "#e8eaed", "#a6adb5", "#8b939c",
    "#f08c2e", "#f79d4d", "#1a1006",
    "#2dd4a7", "#f6685e", "#e5a93d", "#6aa2f7",
}
BANNED_HEX = {"#565d66"}

DASH_ENTITIES = ["&mdash;", "&ndash;", "&#8212;", "&#8211;", "&#x2014;", "&#x2013;",
                 "&#X2014;", "&#X2013;", "&horbar;", "&#45;&#45;"]


# ---------------------------------------------------------------- 유틸
def strip_regions(text):
    """주석/style/script 를 같은 길이의 공백으로 치환해 줄번호를 보존한다."""
    def blank(m):
        return re.sub(r"[^\n]", " ", m.group(0))
    text = re.sub(r"<!--.*?-->", blank, text, flags=re.S)
    text = re.sub(r"<style\b.*?</style>", blank, text, flags=re.S | re.I)
    text = re.sub(r"<script\b.*?</script>", blank, text, flags=re.S | re.I)
    return text


def visible_text_spans(nostyle):
    """(줄번호, 텍스트) 목록. 태그 밖 텍스트 + 사용자에게 노출되는 속성값."""
    out = []
    line = 1
    i = 0
    n = len(nostyle)
    buf = []
    buf_line = 1
    while i < n:
        ch = nostyle[i]
        if ch == "<":
            if buf:
                s = "".join(buf)
                if s.strip():
                    out.append((buf_line, s))
                buf = []
            j = nostyle.find(">", i)
            if j == -1:
                break
            tag = nostyle[i:j + 1]
            for attr in ("aria-label", "title", "placeholder", "alt", "aria-description"):
                for m in re.finditer(attr + r'\s*=\s*"([^"]*)"', tag):
                    if m.group(1).strip():
                        out.append((line, m.group(1)))
            line += tag.count("\n")
            i = j + 1
            buf_line = line
            continue
        if ch == "\n":
            line += 1
        if not buf:
            buf_line = line
        buf.append(ch)
        i += 1
    if buf and "".join(buf).strip():
        out.append((buf_line, "".join(buf)))
    return out


def srgb(c):
    c = c / 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def lum(hexstr):
    h = hexstr.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    r, g, b = (int(h[k:k + 2], 16) for k in (0, 2, 4))
    return 0.2126 * srgb(r) + 0.7152 * srgb(g) + 0.0722 * srgb(b)


def contrast(a, b):
    la, lb = lum(a), lum(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def lines_of(text, needle, flags=0):
    hits = []
    for m in re.finditer(needle, text, flags):
        hits.append(text[:m.start()].count("\n") + 1)
    return hits


# ---------------------------------------------------------------- 검사 본체
class Report:
    def __init__(self, name):
        self.name = name
        self.items = []

    def add(self, level, code, msg, lines=None):
        self.items.append({"level": level, "code": code, "msg": msg,
                           "lines": sorted(set(lines or []))[:20]})

    def fail(self, *a, **k):
        self.add("FAIL", *a, **k)

    def warn(self, *a, **k):
        self.add("WARN", *a, **k)

    @property
    def fails(self):
        return [i for i in self.items if i["level"] == "FAIL"]

    @property
    def warns(self):
        return [i for i in self.items if i["level"] == "WARN"]


def check(path, marketing=False):
    raw = Path(path).read_text(encoding="utf-8")
    rep = Report(Path(path).name)
    nostyle = strip_regions(raw)
    spans = visible_text_spans(nostyle)

    style_m = re.search(r"<style\b[^>]*>(.*?)</style>", raw, re.S | re.I)
    css_raw = style_m.group(1) if style_m else ""
    # CSS 주석은 같은 길이 공백으로 (줄번호 보존). 주석 속 문구가 규칙 위반으로 오탐되던 문제.
    css = re.sub(r"/\*.*?\*/", lambda m: re.sub(r"[^\n]", " ", m.group(0)), css_raw, flags=re.S)
    css_off = style_m.start(1) if style_m else 0

    MARK = "PAGE-SPECIFIC"
    # 마커는 CSS 주석 안에 있으므로 위치는 원본에서 찾는다. 주석 blank 는 길이를 보존하므로 인덱스는 그대로 유효하다.
    mark_i = css_raw.find(MARK)
    shared_css = css_raw[:mark_i] if mark_i >= 0 else css_raw
    page_css = css[mark_i:] if mark_i >= 0 else ""

    # ---- C1 노출 카피 대시
    dash_lines, dash_samples = [], []
    for ln, txt in spans:
        t = txt.strip()
        if t in ("—", "–"):
            continue  # KPI 무데이터 관례
        for ch in ("—", "–"):
            if ch in t:
                dash_lines.append(ln)
                dash_samples.append(t[:60])
    if dash_lines:
        rep.fail("C1-dash", "노출 카피에 em/en dash: " + " | ".join(dash_samples[:4]), dash_lines)
    ent_lines = []
    for ent in DASH_ENTITIES:
        ent_lines += lines_of(nostyle, re.escape(ent))
    if ent_lines:
        rep.fail("C1-entity", "노출 카피에 대시 HTML 엔티티", ent_lines)

    # ---- C2 금지 색
    for bad in BANNED_HEX:
        ls = lines_of(raw, re.escape(bad), re.I)
        if ls:
            rep.fail("C2-banned-hex", f"금지 색 {bad} (2.92:1) 사용", ls)

    # ---- C3 팔레트 밖 hex + 대비
    for m in re.finditer(r"#[0-9a-fA-F]{3,8}\b", page_css):
        hx = m.group(0).lower()
        if len(hx) not in (4, 7):
            continue
        if hx in PALETTE or hx in BANNED_HEX:
            continue
        ln = raw[:css_off + m.start()].count("\n") + 1
        ctx = page_css[max(0, m.start() - 60):m.start()]
        is_text = bool(re.search(r"(^|[;{\s])(color|fill|stroke)\s*:[^;{]*$", ctx))
        c_card = contrast(hx, "#141619")
        if is_text and c_card < 4.5:
            rep.fail("C3-contrast", f"{hx} 텍스트 대비 {c_card:.2f}:1 (카드 위 4.5 미만)", [ln])
        else:
            rep.warn("C3-offpalette", f"팔레트 밖 색 {hx} (카드 대비 {c_card:.2f}:1)", [ln])
    for m in re.finditer(r'style="[^"]*(?:color|fill)\s*:\s*(#[0-9a-fA-F]{3,6})', raw):
        hx = m.group(1).lower()
        if hx in PALETTE:
            continue
        ln = raw[:m.start()].count("\n") + 1
        c_card = contrast(hx, "#141619")
        lvl = rep.fail if c_card < 4.5 else rep.warn
        lvl("C3-inline", f"인라인 {hx} 대비 {c_card:.2f}:1", [ln])

    # ---- C4 outline 무력화
    for m in re.finditer(r"outline\s*:\s*(none|0)\b", css, re.I):
        ln = raw[:css_off + m.start()].count("\n") + 1
        ctx = css[max(0, m.start() - 260):m.start()]
        sel = ctx.split("}")[-1].strip().splitlines()
        sel = sel[-1] if sel else ""
        if ".searchbox input" in ctx and ":focus-within" in css:
            rep.warn("C4-outline-ok", f"허용된 outline:none (.searchbox input, :focus-within 보상) — {sel[:50]}", [ln])
        else:
            rep.fail("C4-outline", f"outline 무력화 (보상 없음) — 셀렉터 근처: {sel[:60]}", [ln])

    # ---- C5 아이콘 레일 접근성
    nav_items = re.findall(r"<a\b[^>]*class=\"nav-item[^\"]*\"[^>]*>", raw)
    if not marketing:
        if len(nav_items) != 6:
            rep.fail("C5-nav-count", f"사이드바 nav-item 6개여야 하는데 {len(nav_items)}개", [])
        missing = [t for t in nav_items if "aria-label" not in t]
        if missing:
            rep.fail("C5-nav-aria", f"aria-label 없는 nav-item {len(missing)}개 (1024px 이하에서 이름 소실)", [])
        act = [t for t in nav_items if "active" in t]
        if len(act) != 1:
            rep.fail("C5-nav-active", f"active nav-item 이 정확히 1개여야 하는데 {len(act)}개", [])
        elif 'aria-current="page"' not in act[0]:
            rep.fail("C5-nav-current", "active nav-item 에 aria-current=\"page\" 없음", [])
    # display:none 으로 숨는 요소에 label 만 있고 aria 가 없는 버튼
    for m in re.finditer(r"<button\b(?![^>]*aria-label)[^>]*>(.*?)</button>", raw, re.S):
        inner = re.sub(r"<[^>]+>", "", re.sub(r"<svg\b.*?</svg>", "", m.group(1), flags=re.S))
        if not inner.strip():
            ln = raw[:m.start()].count("\n") + 1
            rep.warn("C5-iconbtn", "텍스트 없는 아이콘 button 에 aria-label 없음", [ln])

    # ---- C6 정직성
    for pat, msg in [(r"벡터화", "'벡터화' 표기 (ADR-011 위반, 엔진은 바 단위 이벤트 루프)"),
                     (r"vectori[sz]", "'vectorized' 표기 (ADR-011 위반)")]:
        ls = [ln for ln, t in spans if re.search(pat, t, re.I)]
        if ls:
            rep.fail("C6-engine", msg, ls)

    # ---- C7 가공 인물 / 가짜 소셜프루프
    NAMEPAT = r"[김이박최정강조윤장임한오서신권황안송류전홍고문양손배백허유남심노하곽성차주우구민][가-힣]{2}"
    PERSON_CTX = r"(님|씨|고객|후기|리뷰|사용자님|트레이더|매니저|담당자|작성자|@)"
    for ln, t in spans:
        s_ = t.strip()
        if re.fullmatch(NAMEPAT, s_):
            rep.warn("C7-person", f"가공 인물 의심 (단독 이름 텍스트) '{s_}'", [ln])
            continue
        for m in re.finditer(NAMEPAT + r"\s*" + PERSON_CTX, s_):
            rep.warn("C7-person", f"가공 인물 의심 '{m.group(0)}'", [ln])
    if not marketing and "woosung" not in raw:
        rep.warn("C7-user", "계정 이름 'woosung' 이 없음 (실제 사용자여야 함)", [])

    # ---- C8 폰트 실제 로드
    for needle, label in [("pretendard", "Pretendard"), ("Archivo", "Archivo"), ("IBM+Plex+Mono", "IBM Plex Mono")]:
        if not re.search(r'<link[^>]*' + re.escape(needle), raw, re.I):
            rep.fail("C8-font", f"{label} <link> 미로드", [])

    # ---- C9 모션 무력화
    rm = re.search(r"@media\s*\(prefers-reduced-motion:\s*reduce\)\s*\{(.*?)\n  \}", css, re.S)
    rm_body = rm.group(1) if rm else ""
    if not rm:
        rep.fail("C9-rm", "prefers-reduced-motion 블록 없음", [])
    else:
        for cls in [".rise", ".sk"]:
            if cls not in rm_body:
                rep.fail("C9-rm-cls", f"reduced-motion 블록에 {cls} 명시적 무력화 없음", [])
        if 'class="draw' in raw or "draw" in page_css:
            if ".draw" not in rm_body:
                rep.fail("C9-rm-draw", "draw 애니메이션을 쓰면서 reduced-motion 무력화 없음", [])
    for m in re.finditer(r"animation\s*:[^;]*infinite", css, re.I):
        seg_ = m.group(0)
        ln = raw[:css_off + m.start()].count("\n") + 1
        if "shimmer" not in seg_:
            rep.fail("C14-fakelive", f"무한 반복 애니메이션 (가짜 라이브/펄스 의심): {seg_[:60]}", [ln])
    for m in re.finditer(r"animation-duration\s*:\s*([0-9.]+)s", page_css):
        if float(m.group(1)) > 1.0:
            ln = raw[:css_off + mark_i + m.start()].count("\n") + 1
            rep.warn("C9-slow", f"1초 초과 애니메이션 {m.group(1)}s — 주 데이터를 가리면 안 됨", [ln])

    # ---- C10 반경 단일 토큰
    bad_radius = []
    for m in re.finditer(r"border-radius\s*:\s*([^;}]+)", css):
        val = m.group(1).strip()
        ln = raw[:css_off + m.start()].count("\n") + 1
        toks = [t for t in re.split(r"\s+", val) if t]
        for t in toks:
            if t in ("0", "0px", "var(--r)"):
                continue
            bad_radius.append((ln, val))
            break
    if bad_radius:
        rep.fail("C10-radius", "반경 토큰 이탈: " + " | ".join(f"{v}" for _, v in bad_radius[:6]),
                 [l for l, _ in bad_radius])

    # ---- C11 상태 4종
    if not marketing:
        if 'role="alert"' not in raw:
            rep.fail("C11-alert", 'role="alert" 에러 상태 없음', [])
        if not re.search(r"(GET|POST|PUT|PATCH|DELETE)\s+/[^\s<]+[^<]*·\s*\d{3}", raw):
            rep.fail("C11-endpoint", "에러 상태에 실제 엔드포인트 + HTTP 코드 표기 없음", [])
        if not re.search(r"다시 시도|재시도", raw):
            rep.fail("C11-retry", "재시도 액션 없음", [])
        if not re.search(r'class="[^"]*\bsk\b', raw):
            rep.fail("C11-skeleton", "스켈레톤(.sk) 미구현", [])
        if len(re.findall(r'class="[^"]*state-box', raw)) < 2:
            rep.fail("C11-empty", "빈 상태 미구현 (state-box 2개 미만)", [])
        if not re.search(r">\s*—\s*<", raw):
            rep.fail("C11-nodata", "무데이터 셀(—) 없음", [])

    # ---- C12 테이블 가로 스크롤 래퍼
    tables = len(re.findall(r"<table\b", raw))
    wraps = len(re.findall(r'class="[^"]*table-wrap', raw))
    if tables > wraps:
        rep.fail("C12-tablewrap", f"table {tables}개 중 table-wrap {wraps}개만 감쌈", [])

    # ---- C13 차트 축 선형성
    for sm in re.finditer(r"<svg\b.*?</svg>", raw, re.S):
        block = sm.group(0)
        base_ln = raw[:sm.start()].count("\n") + 1
        pairs = []
        for tm in re.finditer(
                r'<text[^>]*class="axis-text"[^>]*y="([\d.]+)"[^>]*text-anchor="end"[^>]*>([^<]+)</text>', block):
            label = tm.group(2).strip().replace(",", "").replace("%", "").replace("+", "")
            try:
                pairs.append((float(label), float(tm.group(1))))
            except ValueError:
                pass
        if len(pairs) >= 3:
            pairs.sort()
            xs = [p[0] for p in pairs]
            ys = [p[1] for p in pairs]
            slope = (ys[-1] - ys[0]) / (xs[-1] - xs[0]) if xs[-1] != xs[0] else 0
            worst = 0.0
            for v, y in pairs:
                pred = ys[0] + slope * (v - xs[0])
                worst = max(worst, abs(pred - y))
            if worst > 1.6:
                rep.fail("C13-axis", f"y축 비선형: 라벨 대비 픽셀 최대 편차 {worst:.1f}px", [base_ln])

    # ---- C15/C19 문서 기본
    tm = re.search(r"<title>(.*?)</title>", nostyle, re.S | re.I)  # 주석 안의 <title> 안내 문구 오탐 차단
    if not tm:
        rep.fail("C15-title", "<title> 없음", [])
    elif "화면명" in tm.group(1):
        rep.fail("C15-title", "<title> 플레이스홀더 미치환", [nostyle[:tm.start()].count("\n") + 1])
    if not re.search(r'<html[^>]*lang="ko"', raw):
        rep.fail("C19-lang", 'html lang="ko" 없음', [])
    if not re.search(r'<html[^>]*class="dark"', raw):
        rep.fail("C19-dark", 'html class="dark" 없음', [])

    # ---- C16/C17 공용 CSS 무결성
    if KIT.exists():
        kit_raw = KIT.read_text(encoding="utf-8")
        km = re.search(r"<style\b[^>]*>(.*?)</style>", kit_raw, re.S | re.I)
        kit_css = km.group(1) if km else ""
        kit_mark = kit_css.find(MARK)
        kit_shared = kit_css[:kit_mark] if kit_mark >= 0 else kit_css
        if mark_i < 0:
            rep.fail("C17-marker", "PAGE-SPECIFIC 마커 없음 (공용 CSS 무결성 검증 불가)", [])
        elif shared_css.strip() != kit_shared.strip():
            ka = kit_shared.strip().splitlines()
            fa = shared_css.strip().splitlines()
            diff_at = next((i for i in range(min(len(ka), len(fa))) if ka[i] != fa[i]), min(len(ka), len(fa)))
            rep.fail("C16-kitdrift",
                     f"공용 CSS 가 _kit.html 과 다름 (kit {len(ka)}행 / 파일 {len(fa)}행, 첫 차이 {diff_at + 1}행). "
                     f"화면 고유 CSS 는 PAGE-SPECIFIC 아래에만.", [])

    # ---- C22 다크 전용 약속
    for m in re.finditer(r"(#fff\b|#ffffff\b|:\s*white\b)", page_css, re.I):
        ln = raw[:css_off + mark_i + m.start()].count("\n") + 1
        rep.warn("C22-white", f"page CSS 에 순백 {m.group(0)} (다크 전용 커밋먼트)", [ln])

    # ---- C20 중복 id
    ids = re.findall(r'\sid="([^"]+)"', raw)
    dup = {i for i in ids if ids.count(i) > 1}
    if dup:
        rep.fail("C20-dupid", "중복 id: " + ", ".join(sorted(dup)), [])

    return rep


def main():
    args = [a for a in sys.argv[1:]]
    as_json = "--json" in args
    marketing_flag = "--marketing" in args
    args = [a for a in args if not a.startswith("--")]
    if "--all" in sys.argv:
        targets = sorted(HERE.glob("screen-*.html"))
    else:
        targets = [Path(a) for a in args]
    if not targets:
        print("대상 파일이 없습니다.")
        return 0

    MARKETING = {"screen-14", "screen-15", "screen-16", "screen-17"}
    reports = []
    for t in targets:
        mk = marketing_flag or any(t.name.startswith(p) for p in MARKETING)
        reports.append(check(t, marketing=mk))

    if as_json:
        print(json.dumps([{"file": r.name, "items": r.items} for r in reports], ensure_ascii=False, indent=1))
    else:
        for r in reports:
            status = "FAIL" if r.fails else ("WARN" if r.warns else "PASS")
            print(f"\n=== {r.name} :: {status} (fail {len(r.fails)} / warn {len(r.warns)}) ===")
            for i in r.items:
                ln = (" L" + ",".join(map(str, i["lines"]))) if i["lines"] else ""
                print(f"  [{i['level']}] {i['code']}{ln} — {i['msg']}")
    return 1 if any(r.fails for r in reports) else 0


if __name__ == "__main__":
    sys.exit(main())
