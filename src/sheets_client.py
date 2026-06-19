"""Запис у Google Sheets через service account."""
import re
import json
import datetime
import gspread
from google.oauth2.service_account import Credentials
import config as C

SCOPES = ["https://www.googleapis.com/auth/spreadsheets",
          "https://www.googleapis.com/auth/drive"]

IMG_H = 80
NAVY = {"red": 0.043, "green": 0.121, "blue": 0.227}
LBLUE = {"red": 0.839, "green": 0.894, "blue": 0.941}
WHITE = {"red": 1, "green": 1, "blue": 1}


def open_sheet():
    info = json.loads(C.GOOGLE_CREDENTIALS_JSON)
    creds = Credentials.from_service_account_info(info, scopes=SCOPES)
    return gspread.authorize(creds).open_by_key(C.GOOGLE_SHEET_ID)


def _img(url):
    return f'=IMAGE("{url}";4;{IMG_H};{IMG_H})' if url else ""


def _norm_date(v):
    """Витягти YYYY-MM-DD з різних форматів (ISO, DD.MM.YYYY, дата-час)."""
    s = str(v).strip()
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", s)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    m = re.search(r"(\d{2})[./](\d{2})[./](\d{4})", s)  # DD.MM.YYYY або DD/MM/YYYY
    if m:
        return f"{m.group(3)}-{m.group(2)}-{m.group(1)}"
    return s[:10]


def _fmt_req(ws, r0, r1, c0, c1, bg=None, bold=False, color=None):
    """repeatCell-запит форматування (0-based, напіввідкритий інтервал рядків/колонок)."""
    cell = {}
    if bg:
        cell["backgroundColor"] = bg
    tf = {}
    if bold:
        tf["bold"] = True
    if color:
        tf["foregroundColor"] = color
    if tf:
        cell["textFormat"] = tf
    return {"repeatCell": {
        "range": {"sheetId": ws.id, "startRowIndex": r0, "endRowIndex": r1,
                  "startColumnIndex": c0, "endColumnIndex": c1},
        "cell": {"userEnteredFormat": cell},
        "fields": "userEnteredFormat(backgroundColor,textFormat)"}}


def _height_req(ws, row, count, px=IMG_H):
    return {"updateDimensionProperties": {
        "range": {"sheetId": ws.id, "dimension": "ROWS",
                  "startIndex": row - 1, "endIndex": row - 1 + count},
        "properties": {"pixelSize": px}, "fields": "pixelSize"}}


def write_raw(sh, rows):
    ws = sh.worksheet("raw_meta")
    ws.batch_clear(["A2:K100000"])
    if rows:
        ws.update(f"A2:K{1 + len(rows)}", rows, value_input_option="USER_ENTERED")


def write_overview(sh, job, tg):
    ws = sh.worksheet("Огляд")
    ws.update("B5:B11", [[v] for v in job], value_input_option="USER_ENTERED")
    ws.update("E5:E11", [[v] for v in tg], value_input_option="USER_ENTERED")
    now = datetime.datetime.utcnow() + datetime.timedelta(hours=3)
    ws.update_acell("B2", now.strftime("%Y-%m-%d %H:%M") + " (Київ)")


def write_table(sh, tab, rows, total=True):
    ws = sh.worksheet(tab)
    ws.batch_clear([f"A4:H{4 + 20000}"])
    block = [list(r) for r in rows]
    if total and rows:
        s = sum(r[1] for r in rows); im = sum(r[2] for r in rows)
        cl = sum(r[3] for r in rows); re = sum(r[4] for r in rows)
        block.append(["ВСЬОГО", round(s, 2), int(im), int(cl), int(re),
                      round(s / re, 2) if re else 0.0,
                      round(cl / im, 4) if im else 0.0,
                      round(s / cl, 2) if cl else 0.0])
    if block:
        ws.update(f"A4:H{3 + len(block)}", block, value_input_option="USER_ENTERED")


def write_tg_day_table(sh, tab, rows, manual_date):
    """TG по днях: дні з manual_date і пізніше — колонки 'Результати' (E) та 'Ціна за рез.' (F)
    вносяться ВРУЧНУ. Скрипт їх НЕ перезаписує: зчитує наявні значення і повертає назад,
    нові дати приходять порожні. Витрати/кліки/CTR/CPC тягнуться як завжди."""
    ws = sh.worksheet(tab)

    # 1) зчитати наявні ручні значення по даті: {YYYY-MM-DD: (Результати, Ціна)}
    existing = {}
    try:
        cur = ws.get_values("A4:F100000")
    except Exception:
        cur = []
    for r in cur:
        if not r or not r[0] or str(r[0]).strip() == "ВСЬОГО":
            continue
        key = _norm_date(r[0])
        e = r[4] if len(r) > 4 else ""
        f = r[5] if len(r) > 5 else ""
        existing[key] = (e, f)

    # 2) зібрати блок; для ручних днів підставити збережені значення
    def _n(x):
        try:
            return float(x)
        except (TypeError, ValueError):
            return 0.0

    block = []
    for row in rows:
        row = list(row)
        key = _norm_date(row[0])
        if key >= manual_date:
            e, f = existing.get(key, ("", ""))
            row[4] = e   # Результати — ручне, зберігаємо
            row[5] = f   # Ціна за рез. — ручне, зберігаємо
        block.append(row)

    # 3) ВСЬОГО (підписки враховують і ручні значення, що вже введені)
    if block:
        s = sum(_n(r[1]) for r in block); im = sum(_n(r[2]) for r in block)
        cl = sum(_n(r[3]) for r in block); re = sum(_n(r[4]) for r in block)
        block.append(["ВСЬОГО", round(s, 2), int(im), int(cl),
                      int(re) if re else "",
                      round(s / re, 2) if re else "",
                      round(cl / im, 4) if im else 0.0,
                      round(s / cl, 2) if cl else 0.0])

    ws.batch_clear([f"A4:H{4 + 20000}"])
    if block:
        ws.update(f"A4:H{3 + len(block)}", block, value_input_option="USER_ENTERED")


def write_campaign_tab(sh, tab, campaigns, seg_groups, vertical):
    """JOB/TG: таблиця кампаній + ВСЬОГО, нижче КРЕАТИВИ ПО СЕГМЕНТАХ (всі крео, з картинками)."""
    write_table(sh, tab, campaigns, total=True)
    ws = sh.worksheet(tab)

    base = 4 + len(campaigns) + (1 if campaigns else 0)
    cs = base + 2  # рядок заголовка секції
    ws.batch_clear([f"A{cs}:F{cs + 20000}"])

    block = [["КРЕАТИВИ ПО СЕГМЕНТАХ", "", "", "", "", ""],
             ["Оголошення", "Витрати, $", "Кліки", "Результати", "Ціна за рез., $", "Креатив"]]
    divider_rows, image_rows = [], []
    for seg, rows in seg_groups:
        label = f"ГЕО: {seg}" if vertical == "TG" else f"Сегмент: {seg}"
        divider_rows.append(cs + len(block))
        block.append([label, "", "", "", "", ""])
        for r in rows:
            image_rows.append(cs + len(block))
            block.append([r[0], r[1], r[2], r[3], r[4], _img(r[5])])

    ws.update(f"A{cs}:F{cs + len(block) - 1}", block, value_input_option="USER_ENTERED")

    reqs = [
        _fmt_req(ws, cs - 1, cs, 0, 6, bold=True, color=NAVY),                 # title
        _fmt_req(ws, cs, cs + 1, 0, 6, bg=NAVY, bold=True, color=WHITE),       # header
    ]
    for dr in divider_rows:
        reqs.append(_fmt_req(ws, dr - 1, dr, 0, 6, bg=LBLUE, bold=True))
    for ir in image_rows:
        reqs.append(_height_req(ws, ir, 1))
    if reqs:
        sh.batch_update({"requests": reqs})


def write_all_creatives(sh, creatives):
    ws = sh.worksheet("Креативи")
    ws.batch_clear(["A4:I100000"])
    if creatives:
        body = [[c[0], c[1], c[2], c[3], c[4], c[5], c[6], c[7], _img(c[8])] for c in creatives]
        ws.update(f"A4:I{3 + len(body)}", body, value_input_option="USER_ENTERED")
        sh.batch_update({"requests": [_height_req(ws, 4, len(body))]})
