from pydantic import Field
from typing import Optional
from .base import SeqeraResource

class Credential(SeqeraResource):
    """Base credential model with type-specific fields"""
    type: str
    name: str
    workspace: Optional[str] = None
    overwrite: Optional[bool] = None

    # AWS credentials
    access_key: Optional[str] = Field(default=None, alias="access-key")
    secret_key: Optional[str] = Field(default=None, alias="secret-key")
    assume_role_arn: Optional[str] = Field(default=None, alias="assume-role-arn")

    # Google credentials
    key: Optional[str] = None

    # Azure credentials
    batch_key: Optional[str] = Field(default=None, alias="batch-key")
    batch_name: Optional[str] = Field(default=None, alias="batch-name")
    storage_key: Optional[str] = Field(default=None, alias="storage-key")
    storage_name: Optional[str] = Field(default=None, alias="storage-name")

    # GitHub/GitLab/Bitbucket/Gitea credentials
    username: Optional[str] = None
    password: Optional[str] = None
    token: Optional[str] = None

    # SSH credentials
    private_key: Optional[str] = Field(default=None, alias="private-key")
    passphrase: Optional[str] = None

    # K8s credentials
    kubeconfig: Optional[str] = None

    # Tower Agent credentials
    connection_id: Optional[str] = Field(default=None, alias="connection-id")
    work_dir: Optional[str] = Field(default=None, alias="work-dir")

    # Container Registry credentials
    registry_server: Optional[str] = Field(default=None, alias="registry-server")

    @classmethod
    def from_api_response(cls, data: dict) -> "Credential":
        """Create a Credential instance from API response"""
        provider = data.get("provider", "").lower()

        mapped_data = {
            "type": provider,
            "name": data.get("name"),
            "workspace": f"{data.get('orgName')}/{data.get('workspaceName')}"
        }

        keys = data.get("keys", {})
        if provider == "aws":
            mapped_data["access_key"] = keys.get("accessKey")
            mapped_data["assume_role_arn"] = keys.get("assumeRoleArn")
        elif provider == "google":
            pass  # key file path not returned in API
        elif provider == "azure":
            mapped_data["batch_name"] = keys.get("batchName")
            mapped_data["storage_name"] = keys.get("storageName")

        return cls(**mapped_data)
