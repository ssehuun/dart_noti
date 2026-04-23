import asyncio

from loguru import logger

from dart_noti.config import Settings
from dart_noti.services import rss, telegram
from dart_noti.store.seen import SeenStore


async def poll_once(
    settings: Settings,
    corp_map: dict[str, str],
    store: SeenStore,
) -> None:
    disclosures = await rss.fetch_disclosures(corp_map)
    if not disclosures:
        return

    rcp_nos = [d.rcp_no for d in disclosures]
    new_rcp_nos = store.filter_unseen(rcp_nos)
    if not new_rcp_nos:
        logger.debug("새 공시 없음")
        return

    new_set = set(new_rcp_nos)
    new_disclosures = [d for d in disclosures if d.rcp_no in new_set]
    logger.info(f"새 공시 {len(new_disclosures)}건 발송 시작")

    sent: list[str] = []
    for d in new_disclosures:
        ok = await telegram.send_notification(
            settings.telegram_bot_token,
            settings.telegram_chat_id,
            d,
        )
        if ok:
            sent.append(d.rcp_no)

    if sent:
        store.mark_seen(sent)


async def run(settings: Settings, corp_map: dict[str, str]) -> None:
    store = SeenStore(settings.store_path, settings.seen_retention_days)
    store.evict_old()

    logger.info(
        f"스케줄러 시작 — 폴링 주기 {settings.poll_interval_seconds}초 "
        f"/ 감시 종목 {list(corp_map.values())}"
    )

    while True:
        try:
            await poll_once(settings, corp_map, store)
        except Exception as e:
            logger.exception(f"폴링 중 예외 발생: {e}")
        await asyncio.sleep(settings.poll_interval_seconds)
