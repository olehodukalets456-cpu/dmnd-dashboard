"""DMND Meta Ads → Google Sheets. JOB/TG: кампанії, дні, місяці, креативи по сегментах."""
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
    sheets.write_raw(sh, T.raw_rows(norm, images))
    sheets.write_overview(sh, T.vertical_totals(norm, "JOB"), T.vertical_totals(norm, "TG"))

    for vert, tab, day_tab, mon_tab in [
        ("JOB", "JOB", "JOB_дні", "JOB_місяці"),
        ("TG", "TG", "TG_дні", "TG_місяці"),
    ]:
        log.info("Пишу %s...", vert)
        sheets.write_campaign_tab(sh, tab,
                                  T.campaigns_breakdown(norm, vert),
                                  T.creatives_by_segment(norm, images, vert),
                                  vert)
        if vert == "TG":
            # TG по днях: з TG_MANUAL_DATE підписки вводяться вручну й зберігаються між синками
            sheets.write_tg_day_table(sh, day_tab, T.by_period(norm, vert, "day"), C.TG_MANUAL_DATE)
        else:
            sheets.write_table(sh, day_tab, T.by_period(norm, vert, "day"))
        sheets.write_table(sh, mon_tab, T.by_period(norm, vert, "month"))

    sheets.write_all_creatives(sh, T.all_creatives(norm, images))
    log.info("Готово ✅")


if __name__ == "__main__":
    main()
