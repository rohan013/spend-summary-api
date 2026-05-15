import json
from pathlib import Path
from typing import Protocol

from models import InstitutionConfig


class TokenStore(Protocol):
    def list_institutions(self) -> list[InstitutionConfig]: ...


class JSONTokenStore:
    def __init__(self, path: Path = Path("tokens.json")):
        self.path = path

    def list_institutions(self) -> list[InstitutionConfig]:
        return [
            InstitutionConfig(
                access_token=v["access_token"],
                name=v["name"],
                accounts=v.get("accounts", {}),
            )
            for v in self._load().values()
        ]

    def _load(self) -> dict:
        if not self.path.exists():
            raise FileNotFoundError(f"{self.path} not found — run setup_accounts.py first.")
        return json.loads(self.path.read_text())

    def load_raw(self) -> dict:
        """Return the raw dict for admin scripts that need slug-level access."""
        return self._load()

    def save_raw(self, data: dict) -> None:
        """Persist the raw dict. Used by setup_accounts.py."""
        self.path.write_text(json.dumps(data, indent=2) + "\n")
