"""Запис у Google Sheets через service account."""
import json
import datetime
import gspread
from google.oauth2.service_account import Credentials
import config as C

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


def _client():
    info = json.loads(C.GOOGLE_CREDENTIALS_JSON)
    creds = Credentials.from_service_account_info(info, scopes=SCOPES)
    return gspread.authorize(creds)


def open_sheet():
    return _client().open_by_key(C.GOOGLE_SHEET_ID)


def write_raw(sh, rows):
    ws = sh.worksheet("raw_meta")
    ws.batch_clear(["A2:K100000"])
    if rows:
        end = 1 + len(rows)
        ws.update(f"A2:K{end}", rows, value_input_option="USER_ENTERED")


def write_vertical_tab(sh, tab, campaigns, creatives):
    """
    Малює вкладку напряму (JOB/TG): рядки кампаній (з даними), рядок ВСЬОГО,
    далі секція 'ТОП КРЕАТИВИ'. Перемальовується повністю щоразу — нові кампанії
    з'являються самі.
    Колонки кампаній: Кампанія | Витрати | Покази | Кліки | Результати | Ціна/рез | CTR | CPC
    """
    ws = sh.worksheet(tab)
    ws.batch_clear([f"A4:H{4 + 5000}"])

    block = []
    # рядки кампаній
    for c in campaigns:
        block.append(c)  # [camp, spend, impr, clicks, res, cpr, ctr, cpc]
    # рядок ВСЬОГО
    n = len(campaigns)
    if n:
        first, last = 4, 4 + n - 1
        total = [
            "ВСЬОГО",
            f"=SUM(B{first}:B{last})", f"=SUM(C{first}:C{last})",
            f"=SUM(D{first}:D{last})", f"=SUM(E{first}:E{last})",
            f"=IFERROR(B{last + 1}/E{last + 1},0)",
            f"=IFERROR(D{last + 1}/C{last + 1},0)",
            f"=IFERROR(B{last + 1}/D{last + 1},0)",
        ]
        block.append(total)

    if block:
        end = 4 + len(block) - 1
        ws.update(f"A4:H{end}", block, value_input_option="USER_ENTERED")

    # секція креативів — нижче рядка ВСЬОГО з відступом
    cs = 4 + len(block) + 2
    ws.update(f"A{cs}:F{cs}", [["ТОП КРЕАТИВИ", "", "", "", "", ""]],
              value_input_option="USER_ENTERED")
    ws.update(f"A{cs + 1}:F{cs + 1}",
              [["Оголошення", "Витрати, $", "Кліки", "Результати", "Ціна за рез., $", "Прев'ю (URL)"]],
              value_input_option="USER_ENTERED")
    if creatives:
        ce = cs + 2 + len(creatives) - 1
        ws.update(f"A{cs + 2}:F{ce}", creatives, value_input_option="USER_ENTERED")


def write_all_creatives(sh, creatives):
    ws = sh.worksheet("Креативи")
    ws.batch_clear(["A4:H100000"])
    if creatives:
        end = 3 + len(creatives)
        ws.update(f"A4:H{end}", creatives, value_input_option="USER_ENTERED")


def write_timestamp(sh):
    ws = sh.worksheet("Огляд")
    now = datetime.datetime.utcnow() + datetime.timedelta(hours=3)  # Kyiv ≈ UTC+3
    ws.update_acell("B2", now.strftime("%Y-%m-%d %H:%M") + " (Київ)")
