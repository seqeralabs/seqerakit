from pydantic import Field
from typing import Optional
from .base import SeqeraResource

class Team(SeqeraResource):
    name: str
    organization: str
    description: Optional[str] = None
    members: Optional[list[str]] = None
    overwrite: Optional[bool] = None

    @classmethod
    def from_api_response(cls, data: dict) -> "Team":
        """Create a Team instance from API response"""
        return cls(
            name=data.get("name"),
            organization=data.get("orgName"),
            description=data.get("description")
        )
