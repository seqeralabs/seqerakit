from pydantic import Field
from typing import Optional
from .base import SeqeraResource

class Action(SeqeraResource):
    """Pipeline action model - supports both GitHub and Tower actions"""
    type: str
    name: Optional[str] = None
    workspace: Optional[str] = None
    overwrite: Optional[bool] = None

    # GitHub action fields
    pipeline: Optional[str] = None
    url: Optional[str] = None
    hook_url: Optional[str] = Field(default=None, alias="hook-url")
    hook_method: Optional[str] = Field(default=None, alias="hook-method")

    # Tower action fields
    endpoint: Optional[str] = None

    # Common action fields
    event: Optional[str] = None
    launch: Optional[bool] = None
    params: Optional[dict] = None

    @classmethod
    def from_api_response(cls, data: dict) -> "Action":
        """Create an Action instance from API response"""
        source = data.get("source", {})
        return cls(
            type=data.get("type"),
            name=data.get("name"),
            workspace=f"{data.get('orgName')}/{data.get('workspaceName')}",
            pipeline=data.get("pipeline"),
            event=data.get("event"),
            endpoint=source.get("endpoint"),
            url=source.get("url")
        )
