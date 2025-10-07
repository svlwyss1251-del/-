import re
from datetime import datetime

# ───────────────────────── 카테고리 규칙 ─────────────────────────
CATEGORY_RULES = [
    ("배달의민족", "배달/식사"),
    ("요기요", "배달/식사"),
    ("쿠팡", "쇼핑"),
    ("이마트24", "편의점"),
    ("GS25", "편의점"),
    ("CU", "편의점"),
    ("스타벅스", "카페"),
    ("STARBUCKS", "카페"),
    ("카카오T", "교통"),
    ("지하철", "교통"),
    ("주유소", "차/주유"),
]

def guess_category(merchant: str) -> str:
    if not merchant:
        return ""
    for kw, cat in CATEGORY_RULES:
        if kw in merchant:
            return cat
    return ""

# ───────────────────── 금액/일시/브랜드/메서드 ─────────────────────
def parse_amount(text: str):
    """
    12,300원 / 12,300 원 / ₩12,300 등을 12300으로.
    """
    m = re.search(r'(?:₩|\b)\s*([\d][\d,]*)\s*원?', text)
    if m:
        return int(m.group(1).replace(",", ""))
    return None

def parse_datetime(text: str, default_year=None):
    """
    '10/07 13:45' 또는 '10/07 13:45:12' 형태.
    연도 없으면 현재 연도를 사용.
    """
    m = re.search(r'(?P<md>\d{2}[/-]\d{2})\s+(?P<hm>\d{2}:\d{2}(?::\d{2})?)', text)
    if not m:
        return None
    md = m.group("md").replace("/", "-")
    hm = m.group("hm")
    if default_year is None:
        default_year = datetime.now().year
    dt_str = f"{default_year}-{md} {hm}"
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(dt_str, fmt)
        except ValueError:
            pass
    return None

def parse_card_brand(text: str):
    """
    [현대카드], [신한카드], [KB국민카드], [BC카드] 등 대괄호 안 첫 구간.
    """
    m = re.search(r'\[([^\[\]]+?)\]', text)
    return m.group(1).strip() if m else ""

def parse_method(text: str):
    """
    일시불 / 할부 N / 해외승인 등.
    """
    m = re.search(r'(일시불|할부\s*\d+|해외승인)', text)
    return m.group(1) if m else "일시불"

def is_cancel(text: str):
    """
    취소 키워드 탐지: 취소, 승인취소, 환불 등.
    """
    return any(k in text for k in ("취소", "승인취소", "환불"))

# ───────────────────────── 상호 추출 ─────────────────────────
def parse_merchant(text: str):
    """
    일반형: [브랜드] MM/DD HH:MM 금액 (일시불|할부..) 상호 (승인|취소)
    1) 금액 뒤 ~ (승인|취소) 사이에서 메서드 단어를 제거하고 상호만 추출
    2) 예비: 시간 뒤 ~ (승인|취소) 사이
    3) 노이즈 괄호/이중공백 정리
    """
    # 금액 뒤 ~ 승인/취소 사이
    m_amount = re.search(r'(?:₩|\b)[\s\d,]*원?\s*(.+?)\s*(승인|취소|승인취소|환불)\b', text)
    if m_amount:
        tail = m_amount.group(1).strip()
        # 결제 방법 단어 제거
        tail = re.sub(r'^(일시불|할부\s*\d+|해외승인)\s*', '', tail).strip()
    else:
        # 시간 뒤 ~ 승인/취소 사이
        m2 = re.search(r'\d{2}[/-]\d{2}\s+\d{2}:\d{2}(?::\d{2})?\s+(.+?)\s*(승인|취소|승인취소|환불)\b', text)
        tail = m2.group(1).strip() if m2 else ""

    # 괄호로 붙은 부가정보 제거 예: "상호명(무슨지점)" → "상호명"
    tail = re.sub(r'\s*\([^)]*\)\s*', ' ', tail)
    # 여러 공백 정리
    tail = re.sub(r'\s{2,}', ' ', tail).strip()
    return tail

# ───────────────────────── 엔트리 파싱 ─────────────────────────
def parse_entry(raw_text: str, default_year=None):
    """
    반환: dict
      - tx_datetime (YYYY-MM-DD HH:MM:SS)
      - yyyy_mm_dd
      - merchant
      - amount (취소는 음수)
      - currency (KRW)
      - card_or_account
      - method
      - type ("승인"/"취소")
      - category (간이 규칙)
      - raw_text
    """
    text = " ".join(raw_text.split())  # 공백 정리

    dt = parse_datetime(text, default_year=default_year)
    amount = parse_amount(text) or 0
    brand = parse_card_brand(text)
    method = parse_method(text)
    cancel = is_cancel(text)
    merchant = parse_merchant(text)

    if cancel:
        amount = -abs(amount)
        typ = "취소"
    else:
        typ = "승인"

    yyyy_mm_dd = dt.strftime("%Y-%m-%d") if dt else ""
    category = guess_category(merchant)

    return {
        "tx_datetime": dt.strftime("%Y-%m-%d %H:%M:%S") if dt else "",
        "yyyy_mm_dd": yyyy_mm_dd,
        "merchant": merchant,
        "amount": amount,
        "currency": "KRW",
        "card_or_account": brand,
        "method": method,
        "type": typ,
        "category": category,
        "raw_text": raw_text,
    }
