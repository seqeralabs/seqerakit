from typing import Optional
from .base import SeqeraResource


class Member(SeqeraResource):
    user: str
    organization: str
    overwrite: Optional[bool] = None

    @classmethod
    def from_api_response(cls, data: dict) -> "Member":
        """Create a Member instance from API response"""
        return cls(user=data.get("email"), organization=data.get("orgName"))
