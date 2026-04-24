from datetime import datetime

from pydantic import BaseModel


class Disclosure(BaseModel):
    rcp_no: str       # 접수번호 — 중복 방지 고유 ID
    corp_name: str    # 회사명 (dc:creator)
    market: str       # 시장 구분 (유가/코스닥/기타)
    report_nm: str    # 보고서명 (title에서 파싱)
    rcept_dt: datetime
    url: str
