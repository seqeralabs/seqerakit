from pydantic import Field
from typing import Optional
from .base import SeqeraResource

class Participant(SeqeraResource):
    name: str
    type: str
    workspace: str
    role: Optional[str] = None
    overwrite: Optional[bool] = None

    @classmethod
    def from_api_response(cls, data: dict) -> "Participant":
        """Create a Participant instance from API response"""
        name = data.get("email") if data.get("memberType") == "MEMBER" else data.get("teamName")
        return cls(
            name=name,
            type=data.get("memberType"),
            workspace=f"{data.get('orgName')}/{data.get('workspaceName')}",
            role=data.get("wspRole")
        )
