from pydantic import Field
from typing import Optional
from .base import SeqeraResource

class Pipeline(SeqeraResource):
    name: str
    workspace: str
    work_dir: Optional[str] = Field(default="", alias="work-dir", serialization_alias="workDir")
    revision: Optional[str] = Field(default="", alias="revision")
    profile: Optional[str] = Field(default="standard", alias="profile")
    compute_env: Optional[str] = Field(default="", alias="compute-env")
    url: Optional[str] = Field(default="", serialization_alias="pipeline")
    labels: Optional[str] = None
    config_text: Optional[str] = Field(None, alias="config-text", serialization_alias="configText")
    params_text: Optional[str] = Field(None, alias="params-text", serialization_alias="paramsText")
    pull_latest: Optional[bool] = Field(default=False, alias="pull-latest", serialization_alias="pullLatest")
    
    class Config:
        extra = "ignore"
        populate_by_alias = True

    def dump_dict(self) -> dict:
        """For dumping - includes all fields even if None"""
        return self.dict(by_alias=True, exclude_none=False)
    
    def input_dict(self) -> dict:
        """For input processing - excludes None values"""
        return self.dict(by_alias=True, exclude_none=True)

        
    @classmethod
    def from_api_response(cls, data: dict) -> "Pipelines":
        """
        Create a Pipeline instance from API response data by mapping fields
        """
        info = data.get("info", {})
        launch = data.get("launch", {})
        
        # Get values first
        work_dir = launch.get("workDir", "")
        compute_env_name = launch.get("computeEnv", {}).get("name", "")
        
        # Extract labels
        labels = [
            f"{label['name']}={label['value']}"
            for label in info.get("labels", [])
            if not label.get("resource", True)
        ]
        labels_str = ",".join(sorted(labels)) if labels else None
        
        mapped_data = {
            "name": info.get("name", ""),
            "workspace": f"{info.get('orgName', '')}/{info.get('workspaceName', '')}",
            "work_dir": work_dir,
            "revision": launch.get("revision", ""),
            "profile": launch.get("configProfiles", ["standard"])[0] if launch.get("configProfiles") else "standard",
            "compute_env": compute_env_name,
            "url": launch.get("pipeline", ""),
            "labels": labels_str,
            "config_text": launch.get("configText"),
            "params_text": launch.get("paramsText"),
            "pull_latest": launch.get("pullLatest", False)
        }
        return cls(**mapped_data)