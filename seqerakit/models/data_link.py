from typing import Optional
from .base import SeqeraResource


class DataLink(SeqeraResource):
    name: str
    uri: str
    provider: str
    workspace: Optional[str] = None
    description: Optional[str] = None
    credentials: Optional[str] = None
    overwrite: Optional[bool] = None

    @classmethod
    def from_api_response(cls, data: dict) -> "DataLink":
        """Create a DataLink instance from API response"""
        return cls(
            name=data.get("name"),
            uri=data.get("uri"),
            provider=data.get("provider"),
            workspace=f"{data.get('orgName')}/{data.get('workspaceName')}",
            description=data.get("description"),
            credentials=data.get("credentials", {}).get("name"),
        )
