"""Обробка денних insights: класифікація, агрегація per-ad / по днях / по місяцях."""
import config as C


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


def normalize(insights):
    """Денні рядки → уніфікований список dict із полями для подальшої агрегації."""
    out = []
    for r in insights:
        camp = r.get("campaign_name", "")
        vert = C.classify(camp)
        clicks = _num(r.get("inline_link_clicks")) or _num(r.get("clicks"))
        out.append({
            "date": r.get("date_start", ""),
            "vertical": vert,
            "campaign": camp,
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
    """Групує items за функцією key → суми spend/impr/clicks/results + перший рядок як зразок."""
    g = {}
    for it in items:
        k = key(it)
        d = g.setdefault(k, {"spend": 0.0, "impr": 0.0, "clicks": 0.0, "results": 0.0, "ref": it})
        d["spend"] += it["spend"]; d["impr"] += it["impr"]
        d["clicks"] += it["clicks"]; d["results"] += it["results"]
    return g


def raw_rows(norm, images):
    """raw_meta: один рядок на оголошення (сума по днях)."""
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
    spend, impr, clicks, res, cpr, ctr, cpc = _metrics(s, im, cl, re)
    return [spend, impr, clicks, res, cpr, ctr, cpc]


def campaigns_breakdown(norm, vertical):
    items = [it for it in norm if it["vertical"] == vertical]
    g = _agg(items, lambda it: it["campaign"])
    out = []
    for camp, d in g.items():
        out.append([camp, *_metrics(d["spend"], d["impr"], d["clicks"], d["results"])])
    out.sort(key=lambda r: r[1], reverse=True)
    return out


def by_period(norm, vertical, period):
    """period='day' → по датах; period='month' → по місяцях (YYYY-MM)."""
    items = [it for it in norm if it["vertical"] == vertical]
    keyf = (lambda it: it["date"]) if period == "day" else (lambda it: it["date"][:7])
    g = _agg(items, keyf)
    out = []
    for k, d in g.items():
        if not k:
            continue
        out.append([k, *_metrics(d["spend"], d["impr"], d["clicks"], d["results"])])
    out.sort(key=lambda r: r[0])
    return out


def _creatives(norm, images, filt=None):
    items = norm if filt is None else [it for it in norm if it["vertical"] == filt]
    g = _agg(items, lambda it: it["ad_id"])
    out = []
    for ad_id, d in g.items():
        ref = d["ref"]
        spend, impr, clicks, res, cpr, *_ = _metrics(d["spend"], d["impr"], d["clicks"], d["results"])
        out.append({"vertical": ref["vertical"], "campaign": ref["campaign"], "ad_name": ref["ad_name"],
                    "spend": spend, "clicks": clicks, "results": res, "cpr": cpr,
                    "thumb": images.get(ad_id, "")})
    return out


def top_creatives(norm, images, vertical, limit):
    cr = _creatives(norm, images, vertical)
    cr.sort(key=lambda x: (x["results"], x["spend"]), reverse=True)
    return [[c["ad_name"], c["spend"], c["clicks"], c["results"], c["cpr"], c["thumb"]] for c in cr[:limit]]


def all_creatives(norm, images):
    cr = [c for c in _creatives(norm, images) if c["vertical"] in ("JOB", "TG")]
    cr.sort(key=lambda x: x["spend"], reverse=True)
    return [[c["vertical"], c["campaign"], c["ad_name"], c["spend"], c["clicks"], c["results"], c["cpr"], c["thumb"]]
            for c in cr]
