import asyncio
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import parse_qs, urlparse
from urllib.request import urlopen

from loguru import logger

from dart_noti.models.disclosure import Disclosure

RSS_URL = "https://dart.fss.or.kr/api/todayRSS.xml"
_DC = "{http://purl.org/dc/elements/1.1/}"
_TIMEOUT = 10


def _fetch_xml() -> bytes:
    with urlopen(RSS_URL, timeout=_TIMEOUT) as resp:  # noqa: S310
        return resp.read()


def _parse_rcp_no(url: str) -> str:
    params = parse_qs(urlparse(url).query)
    return params.get("rcpNo", [""])[0]


def _parse_report_nm(title: str) -> str:
    """'(시장)회사명 - 보고서명' 형식에서 보고서명만 추출합니다."""
    parts = title.split(" - ", 1)
    return parts[1] if len(parts) == 2 else title


def _parse_item(item: ET.Element, corp_map: dict[str, str]) -> Disclosure | None:
    link = item.findtext("link", "").strip()
    rcp_no = _parse_rcp_no(link)
    if not rcp_no:
        return None

    creator = item.findtext(f"{_DC}creator", "").strip()
    title = item.findtext("title", "").strip()
    category = item.findtext("category", "").strip()
    pub_date_str = item.findtext("pubDate", "").strip()

    try:
        rcept_dt = parsedate_to_datetime(pub_date_str).astimezone(timezone.utc)
    except Exception:
        rcept_dt = datetime.now(timezone.utc)

    # corp_code는 corp_map에서 역조회 (없으면 빈 문자열)
    name_to_code = {v: k for k, v in corp_map.items()}
    corp_code = name_to_code.get(creator, "")

    return Disclosure(
        rcp_no=rcp_no,
        corp_name=creator,
        corp_code=corp_code,
        market=category,
        report_nm=_parse_report_nm(title),
        rcept_dt=rcept_dt,
        url=link,
    )


def _parse_feed(xml_bytes: bytes, corp_map: dict[str, str]) -> list[Disclosure]:
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as e:
        logger.error(f"RSS XML 파싱 실패: {e}")
        return []

    results: list[Disclosure] = []
    for item in root.findall(".//item"):
        disclosure = _parse_item(item, corp_map)
        if disclosure is not None:
            results.append(disclosure)
    return results


def filter_by_corp(
    disclosures: list[Disclosure], corp_names: set[str]
) -> list[Disclosure]:
    return [d for d in disclosures if d.corp_name in corp_names]


async def fetch_disclosures(corp_map: dict[str, str]) -> list[Disclosure]:
    """RSS 피드를 비동기로 가져와 파싱합니다. corp_map에 있는 종목만 반환합니다."""
    try:
        xml_bytes = await asyncio.to_thread(_fetch_xml)
    except Exception as e:
        logger.error(f"RSS 피드 요청 실패: {e}")
        return []

    all_disclosures = _parse_feed(xml_bytes, corp_map)
    watched_names = set(corp_map.values())
    matched = filter_by_corp(all_disclosures, watched_names)

    logger.debug(f"RSS: 전체 {len(all_disclosures)}건 → 관심 종목 {len(matched)}건")
    return matched
