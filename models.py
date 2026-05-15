from dataclasses import dataclass, field


@dataclass
class InstitutionConfig:
    access_token: str
    name: str
    accounts: dict[str, str] = field(default_factory=dict)  # account_id → custom name
