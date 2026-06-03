"""Запис у Google Sheets через service account."""
import json
import datetime
import gspread
from google.oauth2.service_account import Credentials
import config as C

SCOPES = ["https://www.googleapis.com/auth/spreadsheets",
          "https://www.googleapis.com/auth/drive"]

IMG_H = 80  # висота рядка з картинкою, px


def open_sheet():
    info = json.loads(C.GOOGLE_CREDENTIALS_JSON)
    creds = Credentials.from_service_account_info(info, scopes=SCOPES)
    return gspread.authorize(creds).open_by_key(C.GOOGLE_SHEET_ID)


def _img(url):
    """Формула-картинка в клітинці (підлаштовується під розмір клітинки)."""
    return f'=IMAGE("{url}";4;{IMG_H};{IMG_H})' if url else ""


def _set_row_heights(sh, ws, start, count, px=IMG_H):
    if count <= 0:
        return
    sh.batch_update({"requests": [{
        "updateDimensionProperties": {
            "range": {"sheetId": ws.id, "dimension": "ROWS",
                      "startIndex": start - 1, "endIndex": start - 1 + count},
            "properties": {"pixelSize": px}, "fields": "pixelSize"}}]})


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
    """Універсальний запис таблиці (кампанії / дні / місяці) зі значеннями + рядок ВСЬОГО."""
    ws = sh.worksheet(tab)
    ws.batch_clear([f"A4:H{4 + 20000}"])
    block = [list(r) for r in rows]
    if total and rows:
        s = sum(r[1] for r in rows); im = sum(r[2] for r in rows)
        cl = sum(r[3] for r in rows); re = sum(r[4] for r in rows)
        cpr = round(s / re, 2) if re else 0.0
        ctr = round(cl / im, 4) if im else 0.0
        cpc = round(s / cl, 2) if cl else 0.0
        block.append(["ВСЬОГО", round(s, 2), int(im), int(cl), int(re), cpr, ctr, cpc])
    if block:
        ws.update(f"A4:H{3 + len(block)}", block, value_input_option="USER_ENTERED")


def write_campaign_tab(sh, tab, campaigns, creatives):
    """Вкладка JOB/TG: кампанії + ВСЬОГО, нижче секція ТОП КРЕАТИВИ з картинками."""
    write_table(sh, tab, campaigns, total=True)
    ws = sh.worksheet(tab)
    base = 4 + len(campaigns) + (1 if campaigns else 0)
    cs = base + 2
    ws.update(f"A{cs}:F{cs}", [["ТОП КРЕАТИВИ", "", "", "", "", ""]], value_input_option="USER_ENTERED")
    ws.update(f"A{cs + 1}:F{cs + 1}",
              [["Оголошення", "Витрати, $", "Кліки", "Результати", "Ціна за рез., $", "Креатив"]],
              value_input_option="USER_ENTERED")
    if creatives:
        body = [[c[0], c[1], c[2], c[3], c[4], _img(c[5])] for c in creatives]
        first = cs + 2
        ws.update(f"A{first}:F{first + len(body) - 1}", body, value_input_option="USER_ENTERED")
        _set_row_heights(sh, ws, first, len(body))


def write_all_creatives(sh, creatives):
    ws = sh.worksheet("Креативи")
    ws.batch_clear(["A4:H100000"])
    if creatives:
        body = [[c[0], c[1], c[2], c[3], c[4], c[5], c[6], _img(c[7])] for c in creatives]
        ws.update(f"A4:H{3 + len(body)}", body, value_input_option="USER_ENTERED")
        _set_row_heights(sh, ws, 4, len(body))
