from pydantic import Field
from typing import Optional
from .base import SeqeraResource

class Studio(SeqeraResource):
    name: str
    compute_env: str = Field(alias="compute-env")
    workspace: Optional[str] = None
    description: Optional[str] = None
    template: Optional[str] = None
    custom_template: Optional[str] = Field(default=None, alias="custom-template")
    conda_env_yml: Optional[str] = Field(default=None, alias="conda-env-yml")
    gpu: Optional[int] = None
    cpu: Optional[int] = None
    memory: Optional[int] = None
    lifespan: Optional[int] = None
    auto_start: Optional[bool] = Field(default=None, alias="auto-start")
    private: Optional[bool] = None
    labels: Optional[str] = None
    wait: Optional[str] = None
    mount_data_uris: Optional[str] = Field(default=None, alias="mount-data-uris")
    mount_data: Optional[str] = Field(default=None, alias="mount-data")
    mount_data_ids: Optional[str] = Field(default=None, alias="mount-data-ids")
    mount_data_resource_refs: Optional[str] = Field(default=None, alias="mount-data-resource-refs")
    overwrite: Optional[bool] = None

    @classmethod
    def from_api_response(cls, data: dict) -> "Studio":
        """Create a Studio instance from API response"""
        return cls(
            name=data.get("name"),
            compute_env=data.get("computeEnv", {}).get("name"),
            workspace=f"{data.get('orgName')}/{data.get('workspaceName')}",
            description=data.get("description"),
            template=data.get("containerImage"),
            cpu=data.get("cpu"),
            memory=data.get("memory"),
            gpu=data.get("gpu")
        )
