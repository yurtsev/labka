from dataclasses import dataclass


@dataclass(frozen=True)
class NewAdmin:
    last_name: str
    first_name: str
    middle_name: str | None
    email: str
    password: str
