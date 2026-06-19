"""Налаштування синку DMND Meta Ads → Google Sheets."""
import os

# --- секрети з оточення (GitHub Secrets) ---
META_ACCESS_TOKEN = os.environ["META_ACCESS_TOKEN"]
META_AD_ACCOUNT_ID = os.environ["META_AD_ACCOUNT_ID"].replace("act_", "")
GOOGLE_SHEET_ID = os.environ["GOOGLE_SHEET_ID"]
GOOGLE_CREDENTIALS_JSON = os.environ["GOOGLE_CREDENTIALS_JSON"]

# --- період ---
SYNC_SINCE = "2026-05-25"          # дата старту запуску
# SYNC_UNTIL рахується автоматично = сьогодні

# --- Meta API ---
GRAPH_VERSION = "v21.0"


# --- класифікація кампаній за префіксом до першого пайпа ---
# "JOB | LEADS | ..." -> JOB ; "TG | UKR - ..." -> TG ; решта -> other
def classify(campaign_name: str) -> str:
    if not campaign_name:
        return "other"
    head = campaign_name.split("|")[0].strip().upper()
    if head.startswith("JOB"):
        return "JOB"
    if head.startswith("TG"):
        return "TG"
    return "other"


# --- які типи дій (actions) рахуємо як "результат" для кожного напряму ---
# Meta повертає масив actions з різними action_type. Беремо перший знайдений зі списку.
RESULT_ACTIONS = {
    "JOB": [
        "lead",
        "onsite_conversion.lead_grouped",
        "offsite_conversion.fb_pixel_lead",
        "complete_registration",
        "offsite_conversion.fb_pixel_complete_registration",
    ],
    "other": ["lead", "offsite_conversion.fb_pixel_lead"],
}

# --- TG: результат залежить від дати ---
# до TG_SWITCH_DATE рахуємо ЛІДИ, з цієї дати — ПІДПИСКИ НА САЙТІ
TG_SWITCH_DATE = "2026-06-02"

# з TG_MANUAL_DATE TG-результат (підписки) ВНОСИТЬСЯ ВРУЧНУ у вкладку TG_дні.
# Скрипт його НЕ тягне з Meta і НЕ перезаписує (зчитує наявне й повертає назад).
TG_MANUAL_DATE = "2026-06-15"

TG_LEAD_ACTIONS = [
    "lead",
    "offsite_conversion.fb_pixel_lead",
    "onsite_conversion.lead_grouped",
]
TG_SUBSCRIBE_ACTIONS = [
    "offsite_conversion.fb_pixel_custom",          # кастомна подія підписки (твій кабінет)
    "offsite_conversion.fb_pixel_custom.Subscribe",
    "offsite_conversion.fb_pixel_subscribe",
    "subscribe",
    "onsite_conversion.subscribe",
    "offsite_conversion.custom.Subscribe",
]

# людська назва результату для відображення
RESULT_LABEL = {"JOB": "Заявки", "TG": "Підписки/ліди", "other": "Результати"}

# скільки топ-креативів писати у вкладки JOB/TG
TOP_CREATIVES = 10
