from typing import Optional
from .base import SeqeraResource


class Secret(SeqeraResource):
    name: str
    workspace: Optional[str] = None
    value: Optional[str] = None
    overwrite: Optional[bool] = None

    @classmethod
    def from_api_response(cls, data: dict) -> "Secret":
        """Create a Secret instance from API response"""
        return cls(
            name=data.get("name"),
            workspace=f"{data.get('orgName')}/{data.get('workspaceName')}",
        )
