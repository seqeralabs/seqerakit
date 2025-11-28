from pydantic import Field
from typing import Optional
from .base import SeqeraResource


class Organization(SeqeraResource):
    name: str
    full_name: str = Field(alias="full-name")
    description: Optional[str] = None
    location: Optional[str] = None
    website: Optional[str] = None
    overwrite: Optional[bool] = None

    @classmethod
    def from_api_response(cls, data: dict) -> "Organization":
        """Create an Organization instance from API response"""
        return cls(
            name=data.get("name"),
            full_name=data.get("fullName"),
            description=data.get("description"),
            location=data.get("location"),
            website=data.get("website"),
        )
