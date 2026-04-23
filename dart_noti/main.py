import asyncio
import signal
import sys

from loguru import logger

from dart_noti.config import get_settings
from dart_noti.services.dart import load_corp_map
from dart_noti import scheduler


def _configure_logging() -> None:
    logger.remove()
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level:<8}</level> | {message}",
        level="INFO",
    )
    logger.add(
        "data/dart_noti.log",
        rotation="10 MB",
        retention="30 days",
        encoding="utf-8",
        level="DEBUG",
    )


async def _main() -> None:
    _configure_logging()
    settings = get_settings()

    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()

    def _handle_signal() -> None:
        logger.info("종료 신호 수신, 스케줄러를 중단합니다.")
        stop_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, _handle_signal)

    try:
        corp_map = await load_corp_map(settings.dart_api_key, settings.watch_corp_codes)
    except Exception as e:
        logger.error(f"corp 매핑 로드 실패: {e}")
        sys.exit(1)

    scheduler_task = asyncio.create_task(scheduler.run(settings, corp_map))
    stop_task = asyncio.create_task(stop_event.wait())

    done, pending = await asyncio.wait(
        {scheduler_task, stop_task},
        return_when=asyncio.FIRST_COMPLETED,
    )

    for task in pending:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    logger.info("dart-noti 종료")


def main() -> None:
    asyncio.run(_main())


if __name__ == "__main__":
    main()
