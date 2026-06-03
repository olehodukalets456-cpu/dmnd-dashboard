"""
DMND Meta Ads → Google Sheets.
Тягне insights (з дати старту по сьогодні), класифікує JOB/TG,
пише raw_meta + топ-креативи + зведення.
"""
import datetime
import logging
import config as C
import meta_client as meta
import transformers as T
import sheets_client as sheets

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(message)s")
log = logging.getLogger("dmnd")


def main():
    until = datetime.date.today().isoformat()
    log.info("Період: %s → %s", C.SYNC_SINCE, until)

    log.info("Тягну insights з Meta...")
    insights = meta.fetch_insights(C.SYNC_SINCE, until)
    log.info("  отримано рядків: %d", len(insights))

    ad_ids = [r.get("ad_id") for r in insights if r.get("ad_id")]
    log.info("Тягну прев'ю креативів (%d)...", len(ad_ids))
    thumbs = meta.fetch_thumbnails(ad_ids)
    log.info("  прев'ю: %d", len(thumbs))

    rows = T.build_rows(insights, thumbs)

    log.info("Пишу в Google Sheets...")
    sh = sheets.open_sheet()
    sheets.write_raw(sh, rows)
    sheets.write_vertical_tab(sh, "JOB",
                              T.campaigns_breakdown(rows, "JOB"),
                              T.top_creatives(rows, "JOB", C.TOP_CREATIVES))
    sheets.write_vertical_tab(sh, "TG",
                              T.campaigns_breakdown(rows, "TG"),
                              T.top_creatives(rows, "TG", C.TOP_CREATIVES))
    sheets.write_all_creatives(sh, T.all_creatives(rows))
    sheets.write_timestamp(sh)
    log.info("Готово ✅")


if __name__ == "__main__":
    main()
