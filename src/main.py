"""DMND Meta Ads → Google Sheets. Денна/місячна розбивка JOB і TG + креативи-картинки."""
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

    insights = meta.fetch_insights(C.SYNC_SINCE, until)
    log.info("Денних рядків з Meta: %d", len(insights))
    norm = T.normalize(insights)

    ad_ids = list({it["ad_id"] for it in norm if it["ad_id"]})
    images = meta.fetch_images(ad_ids)
    log.info("Зображень креативів: %d", len(images))

    sh = sheets.open_sheet()
    log.info("Пишу raw_meta...")
    sheets.write_raw(sh, T.raw_rows(norm, images))

    log.info("Пишу Огляд...")
    sheets.write_overview(sh, T.vertical_totals(norm, "JOB"), T.vertical_totals(norm, "TG"))

    for vert, tab, day_tab, mon_tab in [
        ("JOB", "JOB", "JOB_дні", "JOB_місяці"),
        ("TG", "TG", "TG_дні", "TG_місяці"),
    ]:
        log.info("Пишу %s...", vert)
        sheets.write_campaign_tab(sh, tab,
                                  T.campaigns_breakdown(norm, vert),
                                  T.top_creatives(norm, images, vert, C.TOP_CREATIVES))
        sheets.write_table(sh, day_tab, T.by_period(norm, vert, "day"))
        sheets.write_table(sh, mon_tab, T.by_period(norm, vert, "month"))

    log.info("Пишу Креативи...")
    sheets.write_all_creatives(sh, T.all_creatives(norm, images))
    log.info("Готово ✅")


if __name__ == "__main__":
    main()
