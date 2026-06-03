"""Обробка сирих insights: класифікація, витяг результатів, агрегація."""
import config as C


def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def _extract_result(actions, vertical):
    """З масиву actions дістаємо кількість результату за пріоритетним списком типів."""
    if not actions:
        return 0.0
    by_type = {a.get("action_type"): _num(a.get("value")) for a in actions}
    for at in C.RESULT_ACTIONS.get(vertical, []):
        if at in by_type:
            return by_type[at]
    return 0.0


def build_rows(insights, thumbs):
    """
    Перетворює сирі insights у рядки для raw_meta.
    Колонки: vertical, campaign, adset, ad_name, ad_id,
             spend, impressions, clicks, results, result_type, thumb_url
    """
    rows = []
    for r in insights:
        camp = r.get("campaign_name", "")
        vert = C.classify(camp)
        ad_id = r.get("ad_id", "")
        spend = round(_num(r.get("spend")), 2)
        impr = int(_num(r.get("impressions")))
        # линк-кліки точніші для CTR/CPC; якщо нема — загальні clicks
        clicks = int(_num(r.get("inline_link_clicks")) or _num(r.get("clicks")))
        results = int(_extract_result(r.get("actions"), vert))
        rows.append([
            vert, camp, r.get("adset_name", ""), r.get("ad_name", ""), ad_id,
            spend, impr, clicks, results,
            C.RESULT_LABEL.get(vert, "Результати"),
            thumbs.get(ad_id, ""),
        ])
    return rows


def campaigns_breakdown(rows, vertical):
    """Унікальні кампанії напряму з агрегованими метриками. Динамічно — нові кампанії підхоплюються самі."""
    agg = {}
    for x in rows:
        if x[0] != vertical:
            continue
        camp = x[1]
        d = agg.setdefault(camp, {"spend": 0.0, "impr": 0, "clicks": 0, "results": 0})
        d["spend"] += x[5]; d["impr"] += x[6]; d["clicks"] += x[7]; d["results"] += x[8]
    out = []
    for camp, d in agg.items():
        spend, impr, clicks, res = round(d["spend"], 2), d["impr"], d["clicks"], d["results"]
        cpr = round(spend / res, 2) if res else 0.0
        ctr = round(clicks / impr, 4) if impr else 0.0
        cpc = round(spend / clicks, 2) if clicks else 0.0
        out.append([camp, spend, impr, clicks, res, cpr, ctr, cpc])
    out.sort(key=lambda r: r[1], reverse=True)  # за витратами
    return out


def top_creatives(rows, vertical, limit):
    """Топ-N оголошень напряму за кількістю результатів (потім за витратами)."""
    sub = [x for x in rows if x[0] == vertical]
    sub.sort(key=lambda x: (x[8], x[5]), reverse=True)
    out = []
    for x in sub[:limit]:
        spend, clicks, results = x[5], x[7], x[8]
        cpr = round(spend / results, 2) if results else 0.0
        out.append([x[3], spend, clicks, results, cpr, x[10]])  # ad_name, spend, clicks, results, cost/res, thumb
    return out


def all_creatives(rows):
    """Усі креативи (обидва напрями) для вкладки 'Креативи', відсортовані за витратами."""
    sub = [x for x in rows if x[0] in ("JOB", "TG")]
    sub.sort(key=lambda x: x[5], reverse=True)
    out = []
    for x in sub:
        spend, clicks, results = x[5], x[7], x[8]
        cpr = round(spend / results, 2) if results else 0.0
        out.append([x[0], x[1], x[3], spend, clicks, results, cpr, x[10]])
    return out
