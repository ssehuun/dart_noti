from unittest.mock import MagicMock, patch

import pytest

from dart_noti.services.dart import load_corp_map


def _make_fake_corp_list(corps: list[tuple[str, str]]) -> MagicMock:
    """(corp_code, corp_name) 튜플 목록으로 fake CorpList를 만듭니다."""
    fake_corps = []
    for code, name in corps:
        m = MagicMock()
        m.corp_code = code
        m.corp_name = name
        fake_corps.append(m)

    corp_list = MagicMock()
    corp_list.__iter__ = MagicMock(return_value=iter(fake_corps))
    return corp_list


@pytest.mark.asyncio
async def test_load_corp_map_found():
    fake_list = _make_fake_corp_list([
        ("00126380", "삼성전자"),
        ("00401731", "카카오"),
        ("99999999", "다른회사"),
    ])

    with patch("dart_noti.services.dart.dart") as mock_dart:
        mock_dart.get_corp_list.return_value = fake_list
        result = await load_corp_map("fake_key", ["00126380", "00401731"])

    assert result == {"00126380": "삼성전자", "00401731": "카카오"}


@pytest.mark.asyncio
async def test_load_corp_map_missing_code():
    fake_list = _make_fake_corp_list([
        ("00126380", "삼성전자"),
    ])

    with patch("dart_noti.services.dart.dart") as mock_dart:
        mock_dart.get_corp_list.return_value = fake_list
        result = await load_corp_map("fake_key", ["00126380", "00000000"])

    assert "00126380" in result
    assert "00000000" not in result
