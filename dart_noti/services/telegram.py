import asyncio

from loguru import logger
from telegram import Bot
from telegram.constants import ParseMode
from telegram.error import TelegramError

from dart_noti.models.disclosure import Disclosure

_MAX_RETRIES = 3
_RETRY_DELAY = 5.0


def _format_message(d: Disclosure) -> str:
    market_tag = f"[{d.market}] " if d.market else ""
    date_str = d.rcept_dt.strftime("%Y-%m-%d %H:%M KST")
    return (
        f"<b>{market_tag}{d.corp_name}</b>\n"
        f"{d.report_nm}\n"
        f"{date_str}\n"
        f'<a href="{d.url}">공시 보기</a>'
    )


async def send_notification(token: str, chat_id: str, disclosure: Disclosure) -> bool:
    text = _format_message(disclosure)

    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            async with Bot(token=token) as bot:
                await bot.send_message(
                    chat_id=chat_id,
                    text=text,
                    parse_mode=ParseMode.HTML,
                    disable_web_page_preview=True,
                )
            logger.info(f"알림 발송 완료: {disclosure.corp_name} / {disclosure.rcp_no}")
            return True
        except TelegramError as e:
            logger.warning(f"Telegram 발송 실패 ({attempt}/{_MAX_RETRIES}): {e}")
            if attempt < _MAX_RETRIES:
                await asyncio.sleep(_RETRY_DELAY)

    logger.error(f"알림 발송 최종 실패: {disclosure.rcp_no}")
    return False
