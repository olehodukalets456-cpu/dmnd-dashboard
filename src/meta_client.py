"""Робота з Meta Graph API: insights на рівні оголошень + прев'ю креативів."""
import time
import requests
import config as C

BASE = f"https://graph.facebook.com/{C.GRAPH_VERSION}"


def _get(url, params, tries=4):
    for i in range(tries):
        r = requests.get(url, params=params, timeout=60)
        if r.status_code == 200:
            return r.json()
        # rate limit / тимчасові помилки — чекаємо й пробуємо ще
        if r.status_code in (400, 429, 500, 503) and i < tries - 1:
            time.sleep(3 * (i + 1))
            continue
        raise RuntimeError(f"Meta API {r.status_code}: {r.text[:400]}")
    raise RuntimeError("Meta API: вичерпано спроби")


def fetch_insights(since, until):
    """Insights на рівні ad за період. Повертає список рядків (dict)."""
    url = f"{BASE}/act_{C.META_AD_ACCOUNT_ID}/insights"
    params = {
        "access_token": C.META_ACCESS_TOKEN,
        "level": "ad",
        "time_range": f'{{"since":"{since}","until":"{until}"}}',
        "fields": ",".join([
            "campaign_name", "adset_name", "ad_name", "ad_id",
            "spend", "impressions", "clicks", "inline_link_clicks",
            "actions",
        ]),
        "limit": 200,
    }
    rows, page = [], _get(url, params)
    rows.extend(page.get("data", []))
    # пагінація
    while page.get("paging", {}).get("next"):
        page = _get(page["paging"]["next"], {})
        rows.extend(page.get("data", []))
    return rows


def fetch_thumbnails(ad_ids):
    """Повертає {ad_id: thumbnail_url} для списку оголошень."""
    out = {}
    # тягнемо пачками по 50
    for i in range(0, len(ad_ids), 50):
        chunk = ad_ids[i:i + 50]
        url = f"{BASE}/"
        params = {
            "access_token": C.META_ACCESS_TOKEN,
            "ids": ",".join(chunk),
            "fields": "creative{thumbnail_url}",
        }
        try:
            data = _get(url, params)
        except RuntimeError:
            continue
        for ad_id, obj in data.items():
            thumb = (obj.get("creative") or {}).get("thumbnail_url", "")
            if thumb:
                out[ad_id] = thumb
    return out
