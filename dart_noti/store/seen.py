import json
from datetime import datetime, timedelta, timezone
from pathlib import Path


class SeenStore:
    """발송 완료 공시의 rcp_no를 JSON 파일에 영속화해 중복 발송을 방지합니다."""

    def __init__(self, path: Path, retention_days: int = 90) -> None:
        self._path = path
        self._retention_days = retention_days
        self._seen: dict[str, str] = {}  # rcp_no → ISO 날짜 문자열
        self._load()

    def _load(self) -> None:
        if self._path.exists():
            try:
                self._seen = json.loads(self._path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                self._seen = {}

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            json.dumps(self._seen, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def is_seen(self, rcp_no: str) -> bool:
        return rcp_no in self._seen

    def filter_unseen(self, rcp_nos: list[str]) -> list[str]:
        return [r for r in rcp_nos if r not in self._seen]

    def mark_seen(self, rcp_nos: list[str]) -> None:
        now = datetime.now(timezone.utc).isoformat()
        for rcp_no in rcp_nos:
            self._seen[rcp_no] = now
        self._save()

    def evict_old(self) -> None:
        """보존 기간이 지난 이력을 삭제합니다."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=self._retention_days)
        before = len(self._seen)
        self._seen = {
            k: v
            for k, v in self._seen.items()
            if datetime.fromisoformat(v) >= cutoff
        }
        if len(self._seen) != before:
            self._save()
