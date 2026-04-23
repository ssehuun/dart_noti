import asyncio

import dart_fss as dart
from loguru import logger


def _load_corp_map_sync(api_key: str, corp_codes: list[str]) -> dict[str, str]:
    """dart-fss로 corp_code → corp_name 매핑 테이블을 구축합니다 (동기, 1회 실행)."""
    dart.set_api_key(api_key)
    logger.info("DART corp 목록 다운로드 중... (최초 실행 시 수 초 소요)")
    corp_list = dart.get_corp_list()

    target = set(corp_codes)
    corp_map: dict[str, str] = {}

    for corp in corp_list:
        if corp.corp_code in target:
            corp_map[corp.corp_code] = corp.corp_name
            if len(corp_map) == len(target):
                break

    missing = target - set(corp_map.keys())
    if missing:
        logger.warning(f"corp_code를 찾지 못했습니다: {missing}")

    logger.info(f"corp 매핑 완료: {corp_map}")
    return corp_map


async def load_corp_map(api_key: str, corp_codes: list[str]) -> dict[str, str]:
    return await asyncio.to_thread(_load_corp_map_sync, api_key, corp_codes)
