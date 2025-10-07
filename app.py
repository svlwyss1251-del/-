
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import sqlite3, os
from datetime import datetime, date
from urllib.parse import urlencode
from parse import parse_entry

APP_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(APP_DIR, "expense.db")

app = FastAPI(title="Expense Tracker (KR)")
app.mount("/static", StaticFiles(directory=os.path.join(APP_DIR, "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(APP_DIR, "templates"))

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute("""
    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tx_datetime TEXT,
        yyyy_mm_dd TEXT,
        merchant TEXT,
        amount INTEGER,
        currency TEXT,
        card_or_account TEXT,
        method TEXT,
        type TEXT,
        category TEXT,
        raw_text TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)
    conn.commit()
    conn.close()

@app.on_event("startup")
def startup_event():
    init_db()

@app.get("/", response_class=HTMLResponse)
def home(request: Request, date_str: str | None = None):
    if not date_str:
        date_str = date.today().strftime("%Y-%m-%d")
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM transactions WHERE yyyy_mm_dd=? ORDER BY tx_datetime DESC",
        (date_str,)
    ).fetchall()
    total = conn.execute(
        "SELECT COALESCE(SUM(amount),0) as s FROM transactions WHERE yyyy_mm_dd=?",
        (date_str,)
    ).fetchone()["s"]
    # category totals
    cat_rows = conn.execute(
        "SELECT category, COALESCE(SUM(amount),0) as s, COUNT(*) as c FROM transactions WHERE yyyy_mm_dd=? GROUP BY category ORDER BY s DESC",
        (date_str,)
    ).fetchall()
    conn.close()
    return templates.TemplateResponse("index.html", {
        "request": request,
        "date_str": date_str,
        "rows": rows,
        "total": total,
        "cat_rows": cat_rows,
    })

@app.post("/ingest")
async def ingest(raw_text: str = Form(...)):
    # parse and insert
    entry = parse_entry(raw_text)
    conn = get_db()
    conn.execute("""
        INSERT INTO transactions (tx_datetime, yyyy_mm_dd, merchant, amount, currency, card_or_account, method, type, category, raw_text)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        entry["tx_datetime"], entry["yyyy_mm_dd"], entry["merchant"], entry["amount"], entry["currency"],
        entry["card_or_account"], entry["method"], entry["type"], entry["category"], entry["raw_text"]
    ))
    conn.commit()
    conn.close()
    # redirect to the date view
    q = urlencode({"date_str": entry["yyyy_mm_dd"]})
    return RedirectResponse(url=f"/?{q}", status_code=303)

@app.post("/ingest-json")
async def ingest_json(payload: dict):
    raw_text = payload.get("raw_text", "")
    entry = parse_entry(raw_text)
    conn = get_db()
    conn.execute("""
        INSERT INTO transactions (tx_datetime, yyyy_mm_dd, merchant, amount, currency, card_or_account, method, type, category, raw_text)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        entry["tx_datetime"], entry["yyyy_mm_dd"], entry["merchant"], entry["amount"], entry["currency"],
        entry["card_or_account"], entry["method"], entry["type"], entry["category"], entry["raw_text"]
    ))
    conn.commit()
    conn.close()
    return JSONResponse({"ok": True, "entry": entry})

@app.get("/seed")
def seed():
    samples = [
        "[현대카드] 10/07 13:45 12,300원 일시불 CU당산점 승인",
        "[신한카드] 10/07 08:12 5,500원 카카오T 서울택시 승인",
        "[국민카드] 10/06 19:03 18,000원 일시불 배달의민족 승인",
        "[현대카드] 10/06 19:05 18,000원 취소 배달의민족",
        "[STARBUCKS] 10/05 09:10 4,800원 일시불 STARBUCKS 영등포 승인"
    ]
    conn = get_db()
    for s in samples:
        from parse import parse_entry
        e = parse_entry(s)
        conn.execute("""
        INSERT INTO transactions (tx_datetime, yyyy_mm_dd, merchant, amount, currency, card_or_account, method, type, category, raw_text)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            e["tx_datetime"], e["yyyy_mm_dd"], e["merchant"], e["amount"], e["currency"],
            e["card_or_account"], e["method"], e["type"], e["category"], e["raw_text"]
        ))
    conn.commit()
    conn.close()
    return {"ok": True, "added": len(samples)}
