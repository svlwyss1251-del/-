
import re
from datetime import datetime, date

# Simple keyword -> category mapping (expand as needed)
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

def parse_amount(text: str):
    # e.g., "12,300원" -> 12300
    m = re.search(r'([\d,]+)\s*원', text)
    if m:
        return int(m.group(1).replace(",", ""))
    return None

def parse_datetime(text: str, default_year=None):
    """
    Parse formats like '10/07 13:45' optionally with seconds.
    If no year present, assume default_year (or current year).
    """
    m = re.search(r'(?P<md>\d{2}/\d{2})\s+(?P<hm>\d{2}:\d{2}(?::\d{2})?)', text)
    if not m:
        return None
    md = m.group("md")
    hm = m.group("hm")
    if default_year is None:
        default_year = datetime.now().year
    dt_str = f"{default_year}-{md.replace('/', '-')} {hm}"
    # normalize to %Y-%m-%d %H:%M:%S or %H:%M
    try:
        if len(hm.split(":")) == 2:
            return datetime.strptime(dt_str, "%Y-%m-%d %H:%M")
        else:
            return datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None

def parse_card_brand(text: str):
    # [현대카드], [신한카드], [국민카드], [BC카드] ...
    m = re.search(r'\[(.+?)\]', text)
    return m.group(1) if m else ""

def is_cancel(text: str):
    return ("취소" in text) or ("승인취소" in text)

def parse_merchant(text: str):
    """
    Heuristics:
    - Often: [카드] MM/DD HH:MM AMOUNT [일시불|할부] MERCHANT (승인|취소)
    - We'll capture the segment after amount and method up to 승인/취소
    """
    # Try to get substring around the amount
    # Find '원' and take next tokens until '승인' or '취소'
    m_amount = re.search(r'([\d,]+)\s*원\s*(.+?)\s*(승인|취소)', text)
    if m_amount:
        tail = m_amount.group(2).strip()
        # Drop common method words
        tail = re.sub(r'^(일시불|할부\s*\d+|해외승인)\s*', '', tail).strip()
        return tail
    # Fallback: between time and 승인/취소
    m2 = re.search(r'\d{2}/\d{2}\s+\d{2}:\d{2}(?::\d{2})?\s+(.+?)\s*(승인|취소)', text)
    if m2:
        return m2.group(1).strip()
    return ""

def parse_method(text: str):
    m = re.search(r'(일시불|할부\s*\d+|해외승인)', text)
    return m.group(1) if m else "일시불"

def parse_entry(raw_text: str, default_year=None):
    """
    Return a dict with: tx_datetime, amount, merchant, card_or_account, method, type, category
    amount is negative if cancel.
    """
    dt = parse_datetime(raw_text, default_year=default_year)
    amount = parse_amount(raw_text) or 0
    brand = parse_card_brand(raw_text)
    method = parse_method(raw_text)
    cancel = is_cancel(raw_text)
    merchant = parse_merchant(raw_text)

    if cancel:
        amount = -abs(amount)
        typ = "취소"
    else:
        typ = "승인"

    yyyy_mm_dd = dt.strftime("%Y-%m-%d") if dt else ""
    category = guess_category(merchant)

    return {
        "tx_datetime": dt.strftime("%Y-%m-%d %H:%M:%S") if dt else "",
        "amount": amount,
        "merchant": merchant,
        "card_or_account": brand,
        "method": method,
        "type": typ,
        "category": category,
        "currency": "KRW",
        "yyyy_mm_dd": yyyy_mm_dd,
        "raw_text": raw_text
    }
