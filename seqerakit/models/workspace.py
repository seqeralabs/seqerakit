from pydantic import Field
from typing import Optional
from .base import SeqeraResource


class Workspace(SeqeraResource):
    name: str
    organization: str
    full_name: str = Field(alias="full-name")
    description: Optional[str] = None
    visibility: Optional[str] = None
    overwrite: Optional[bool] = None

    @classmethod
    def from_api_response(cls, data: dict) -> "Workspace":
        """Create a Workspace instance from API response"""
        return cls(
            name=data.get("workspaceName"),
            organization=data.get("orgName"),
            full_name=data.get("fullName"),
            description=data.get("description"),
            visibility=data.get("visibility"),
        )
