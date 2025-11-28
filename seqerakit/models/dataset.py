from pydantic import Field
from typing import Optional
from .base import SeqeraResource


class Dataset(SeqeraResource):
    name: str
    workspace: str
    file_path: str = Field(alias="file-path")
    description: Optional[str] = None
    header: Optional[bool] = None
    overwrite: Optional[bool] = None

    @classmethod
    def from_api_response(cls, data: dict) -> "Dataset":
        """Create a Dataset instance from API response"""
        return cls(
            name=data.get("name"),
            workspace=f"{data.get('orgName')}/{data.get('workspaceName')}",
            file_path="",  # Not available in API response
            description=data.get("description"),
            header=data.get("header"),
        )
