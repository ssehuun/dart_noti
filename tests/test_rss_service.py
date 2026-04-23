import pytest
from unittest.mock import AsyncMock, patch

from dart_noti.services.rss import (
    _parse_feed,
    _parse_rcp_no,
    _parse_report_nm,
    filter_by_corp,
    fetch_disclosures,
)
from tests.conftest import CORP_MAP, SAMPLE_RSS_XML


def test_parse_rcp_no():
    url = "https://dart.fss.or.kr/api/link.jsp?rcpNo=20260423001234"
    assert _parse_rcp_no(url) == "20260423001234"


def test_parse_rcp_no_missing():
    assert _parse_rcp_no("https://dart.fss.or.kr/api/link.jsp") == ""


def test_parse_report_nm():
    title = "(코스닥)알엔티엑스 - [기재정정]주요사항보고서(전환사채권발행결정)"
    assert _parse_report_nm(title) == "[기재정정]주요사항보고서(전환사채권발행결정)"


def test_parse_report_nm_no_separator():
    title = "단순 제목"
    assert _parse_report_nm(title) == "단순 제목"


def test_parse_feed_count():
    disclosures = _parse_feed(SAMPLE_RSS_XML, CORP_MAP)
    assert len(disclosures) == 3


def test_parse_feed_fields():
    disclosures = _parse_feed(SAMPLE_RSS_XML, CORP_MAP)
    samsung = next(d for d in disclosures if d.corp_name == "삼성전자")
    assert samsung.rcp_no == "20260423005678"
    assert samsung.corp_code == "00126380"
    assert samsung.market == "유가"
    assert samsung.report_nm == "반기보고서"
    assert samsung.url == "https://dart.fss.or.kr/api/link.jsp?rcpNo=20260423005678"


def test_parse_feed_unknown_corp():
    disclosures = _parse_feed(SAMPLE_RSS_XML, CORP_MAP)
    unknown = next(d for d in disclosures if d.corp_name == "알엔티엔스")
    assert unknown.corp_code == ""  # corp_map에 없으므로 빈 문자열


def test_filter_by_corp():
    disclosures = _parse_feed(SAMPLE_RSS_XML, CORP_MAP)
    watched = {"삼성전자", "카카오"}
    filtered = filter_by_corp(disclosures, watched)
    assert len(filtered) == 2
    names = {d.corp_name for d in filtered}
    assert names == {"삼성전자", "카카오"}


@pytest.mark.asyncio
async def test_fetch_disclosures_mocked():
    with patch("dart_noti.services.rss._fetch_xml", return_value=SAMPLE_RSS_XML):
        result = await fetch_disclosures(CORP_MAP)
    # CORP_MAP에 삼성전자, 카카오만 있으므로 2건만 반환
    assert len(result) == 2
    corp_names = {d.corp_name for d in result}
    assert corp_names == {"삼성전자", "카카오"}


@pytest.mark.asyncio
async def test_fetch_disclosures_network_error():
    with patch("dart_noti.services.rss._fetch_xml", side_effect=OSError("network")):
        result = await fetch_disclosures(CORP_MAP)
    assert result == []


def test_parse_feed_invalid_xml():
    result = _parse_feed(b"not xml at all", CORP_MAP)
    assert result == []
