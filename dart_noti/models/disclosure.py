from datetime import datetime

from pydantic import BaseModel


class Disclosure(BaseModel):
    rcp_no: str       # 접수번호 — 중복 방지 고유 ID
    corp_name: str    # 회사명 (dc:creator)
    corp_code: str    # 고유 종목 코드 (corp_map 역조회, 없으면 빈 문자열)
    market: str       # 시장 구분 (코스닥/유가/기타)
    report_nm: str    # 보고서명 (title에서 파싱)
    rcept_dt: datetime
    url: str
