from unittest.mock import patch

import pytest

from dart_noti.services.rss import (
    _parse_feed,
    _parse_rcp_no,
    _parse_report_nm,
    fetch_disclosures,
)
from tests.conftest import SAMPLE_RSS_XML


def test_parse_rcp_no():
    url = "https://dart.fss.or.kr/api/link.jsp?rcpNo=20260423001234"
    assert _parse_rcp_no(url) == "20260423001234"


def test_parse_rcp_no_missing():
    assert _parse_rcp_no("https://dart.fss.or.kr/api/link.jsp") == ""


def test_parse_report_nm():
    title = "(코스닥)알엔티엑스 - [기재정정]주요사항보고서(전환사채권발행결정)"
    assert _parse_report_nm(title) == "[기재정정]주요사항보고서(전환사채권발행결정)"


def test_parse_report_nm_no_separator():
    assert _parse_report_nm("단순 제목") == "단순 제목"


def test_parse_feed_count():
    disclosures = _parse_feed(SAMPLE_RSS_XML)
    assert len(disclosures) == 3


def test_parse_feed_fields():
    disclosures = _parse_feed(SAMPLE_RSS_XML)
    samsung = next(d for d in disclosures if d.corp_name == "삼성전자")
    assert samsung.rcp_no == "20260423005678"
    assert samsung.market == "유가"
    assert samsung.report_nm == "반기보고서"
    assert samsung.url == "https://dart.fss.or.kr/api/link.jsp?rcpNo=20260423005678"


def test_parse_feed_invalid_xml():
    assert _parse_feed(b"not xml") == []


@pytest.mark.asyncio
async def test_fetch_disclosures_filters_market():
    with patch("dart_noti.services.rss._fetch_xml", return_value=SAMPLE_RSS_XML):
        result = await fetch_disclosures()
    # 유가(삼성전자) + 코스닥(알엔티엔스) = 2건, 기타(유동화전문회사) 제외
    assert len(result) == 2
    markets = {d.market for d in result}
    assert markets == {"유가", "코스닥"}
    assert all(d.corp_name != "유동화전문회사" for d in result)


@pytest.mark.asyncio
async def test_fetch_disclosures_network_error():
    with patch("dart_noti.services.rss._fetch_xml", side_effect=OSError("network")):
        result = await fetch_disclosures()
    assert result == []
