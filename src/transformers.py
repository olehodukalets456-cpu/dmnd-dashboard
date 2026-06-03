"""Обробка денних insights: класифікація, агрегація, сегменти з неймінга кампаній."""
import config as C

GEO_MAP = {"UKR": "UA"}
_DROP = {"JOB", "LEADS", "BUYERS", "FORMS", "TG", "SUBSCRIBE"}


def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def _result(actions, vertical):
    if not actions:
        return 0.0
    by = {a.get("action_type"): _num(a.get("value")) for a in actions}
    for at in C.RESULT_ACTIONS.get(vertical, []):
        if at in by:
            return by[at]
    return 0.0


def _metrics(spend, impr, clicks, res):
    spend = round(spend, 2)
    cpr = round(spend / res, 2) if res else 0.0
    ctr = round(clicks / impr, 4) if impr else 0.0
    cpc = round(spend / clicks, 2) if clicks else 0.0
    return spend, int(impr), int(clicks), int(res), cpr, ctr, cpc


def segment(campaign, vertical):
    """Сегмент із неймінга: TG -> ГЕО (UA/PL/GE), JOB -> байєр (FB/Google) або перший токен."""
    name = campaign or ""
    if vertical == "TG":
        parts = name.split("|")
        if len(parts) >= 2:
            geo = parts[1].split("-")[0].strip().upper()
            geo = GEO_MAP.get(geo, geo)
            return geo or "—"
        return "—"
    if vertical == "JOB":
        low = name.lower()
        if "facebook" in low:
            return "FB байєр"
        if "google" in low:
            return "Google байєр"
        toks = [t.strip() for t in name.replace("-", "|").split("|") if t.strip()]
        rest = [t for t in toks if t.upper() not in _DROP]
        return rest[0] if rest else "інше"
    return "інше"


def normalize(insights):
    out = []
    for r in insights:
        camp = r.get("campaign_name", "")
        vert = C.classify(camp)
        clicks = _num(r.get("inline_link_clicks")) or _num(r.get("clicks"))
        out.append({
            "date": r.get("date_start", ""),
            "vertical": vert,
            "campaign": camp,
            "segment": segment(camp, vert),
            "adset": r.get("adset_name", ""),
            "ad_name": r.get("ad_name", ""),
            "ad_id": r.get("ad_id", ""),
            "spend": _num(r.get("spend")),
            "impr": _num(r.get("impressions")),
            "clicks": clicks,
            "results": _result(r.get("actions"), vert),
        })
    return out


def _agg(items, key):
    g = {}
    for it in items:
        k = key(it)
        d = g.setdefault(k, {"spend": 0.0, "impr": 0.0, "clicks": 0.0, "results": 0.0, "ref": it})
        d["spend"] += it["spend"]; d["impr"] += it["impr"]
        d["clicks"] += it["clicks"]; d["results"] += it["results"]
    return g


def raw_rows(norm, images):
    g = _agg(norm, lambda it: it["ad_id"])
    rows = []
    for ad_id, d in g.items():
        ref = d["ref"]
        spend, impr, clicks, res, *_ = _metrics(d["spend"], d["impr"], d["clicks"], d["results"])
        rows.append([ref["vertical"], ref["campaign"], ref["adset"], ref["ad_name"], ad_id,
                     spend, impr, clicks, res, C.RESULT_LABEL.get(ref["vertical"], "Результати"),
                     images.get(ad_id, "")])
    return rows


def vertical_totals(norm, vertical):
    items = [it for it in norm if it["vertical"] == vertical]
    s = sum(i["spend"] for i in items); im = sum(i["impr"] for i in items)
    cl = sum(i["clicks"] for i in items); re = sum(i["results"] for i in items)
    return list(_metrics(s, im, cl, re))


def campaigns_breakdown(norm, vertical):
    items = [it for it in norm if it["vertical"] == vertical]
    g = _agg(items, lambda it: it["campaign"])
    out = [[camp, *_metrics(d["spend"], d["impr"], d["clicks"], d["results"])] for camp, d in g.items()]
    out.sort(key=lambda r: r[1], reverse=True)
    return out


def by_period(norm, vertical, period):
    items = [it for it in norm if it["vertical"] == vertical]
    keyf = (lambda it: it["date"]) if period == "day" else (lambda it: it["date"][:7])
    g = _agg(items, keyf)
    out = [[k, *_metrics(d["spend"], d["impr"], d["clicks"], d["results"])] for k, d in g.items() if k]
    out.sort(key=lambda r: r[0])
    return out


def creatives_by_segment(norm, images, vertical):
    """{сегмент: [рядки крео]} — ВСІ креативи, згруповані за сегментом, відсортовані за результатами."""
    items = [it for it in norm if it["vertical"] == vertical]
    by_ad = _agg(items, lambda it: it["ad_id"])
    seg = {}
    for ad_id, d in by_ad.items():
        ref = d["ref"]
        spend, impr, clicks, res, cpr, *_ = _metrics(d["spend"], d["impr"], d["clicks"], d["results"])
        seg.setdefault(ref["segment"], []).append(
            [ref["ad_name"], spend, clicks, res, cpr, images.get(ad_id, "")])
    # сортуємо крео всередині сегмента за результатами, сегменти — за сумарними витратами
    groups = []
    for s, rows in seg.items():
        rows.sort(key=lambda r: (r[3], r[1]), reverse=True)
        groups.append((s, rows, sum(r[1] for r in rows)))
    groups.sort(key=lambda g: g[2], reverse=True)
    return [(s, rows) for s, rows, _ in groups]


def all_creatives(norm, images):
    items = [it for it in norm if it["vertical"] in ("JOB", "TG")]
    g = _agg(items, lambda it: it["ad_id"])
    out = []
    for ad_id, d in g.items():
        ref = d["ref"]
        spend, impr, clicks, res, cpr, *_ = _metrics(d["spend"], d["impr"], d["clicks"], d["results"])
        out.append([ref["vertical"], ref["segment"], ref["campaign"], ref["ad_name"],
                    spend, clicks, res, cpr, images.get(ad_id, "")])
    out.sort(key=lambda r: r[4], reverse=True)
    return out
