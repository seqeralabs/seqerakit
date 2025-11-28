from pydantic import Field
from typing import Optional
from .base import SeqeraResource

class Label(SeqeraResource):
    name: str
    workspace: str
    value: Optional[str] = None
    overwrite: Optional[bool] = None

    @classmethod
    def from_api_response(cls, data: dict) -> "Label":
        """Create a Label instance from API response"""
        return cls(
            name=data.get("name"),
            value=data.get("value"),
            workspace=f"{data.get('orgName')}/{data.get('workspaceName')}"
        )
