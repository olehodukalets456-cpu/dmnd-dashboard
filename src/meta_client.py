"""Meta Graph API: денні insights на рівні оголошень + повне зображення креатива."""
import time
import requests
import config as C

BASE = f"https://graph.facebook.com/{C.GRAPH_VERSION}"


def _get(url, params, tries=4):
    for i in range(tries):
        r = requests.get(url, params=params, timeout=60)
        if r.status_code == 200:
            return r.json()
        if r.status_code in (400, 429, 500, 503) and i < tries - 1:
            time.sleep(3 * (i + 1))
            continue
        raise RuntimeError(f"Meta API {r.status_code}: {r.text[:400]}")
    raise RuntimeError("Meta API: вичерпано спроби")


def fetch_insights(since, until):
    """Денні insights на рівні ad (time_increment=1). Кожен рядок = оголошення за один день."""
    url = f"{BASE}/act_{C.META_AD_ACCOUNT_ID}/insights"
    params = {
        "access_token": C.META_ACCESS_TOKEN,
        "level": "ad",
        "time_range": f'{{"since":"{since}","until":"{until}"}}',
        "time_increment": 1,
        "fields": ",".join([
            "date_start", "campaign_name", "adset_name", "ad_name", "ad_id",
            "spend", "impressions", "clicks", "inline_link_clicks", "actions",
        ]),
        "limit": 500,
    }
    rows, page = [], _get(url, params)
    rows.extend(page.get("data", []))
    while page.get("paging", {}).get("next"):
        page = _get(page["paging"]["next"], {})
        rows.extend(page.get("data", []))
    return rows



def fetch_insights_geo(since, until):
    """Insights з розбивкою по країні юзера (breakdowns=country), агреговано за період."""
    url = f"{BASE}/act_{C.META_AD_ACCOUNT_ID}/insights"
    params = {
        "access_token": C.META_ACCESS_TOKEN,
        "level": "ad",
        "time_range": f'{{"since":"{since}","until":"{until}"}}',
        "breakdowns": "country",
        "fields": ",".join([
            "campaign_name", "ad_id",
            "spend", "impressions", "clicks", "inline_link_clicks", "actions",
        ]),
        "limit": 500,
    }
    rows, page = [], _get(url, params)
    rows.extend(page.get("data", []))
    while page.get("paging", {}).get("next"):
        page = _get(page["paging"]["next"], {})
        rows.extend(page.get("data", []))
    return rows


def fetch_images(ad_ids):
    """{ad_id: url} — повне зображення креатива (image_url), fallback на thumbnail_url."""
    out = {}
    for i in range(0, len(ad_ids), 50):
        chunk = ad_ids[i:i + 50]
        params = {
            "access_token": C.META_ACCESS_TOKEN,
            "ids": ",".join(chunk),
            "fields": "creative{image_url,thumbnail_url}",
        }
        try:
            data = _get(f"{BASE}/", params)
        except RuntimeError:
            continue
        for ad_id, obj in data.items():
            cr = obj.get("creative") or {}
            url = cr.get("image_url") or cr.get("thumbnail_url") or ""
            if url:
                out[ad_id] = url
    return out
