from pydantic import Field
from typing import Optional, List
from .base import SeqeraResource

class Pipeline(SeqeraResource):
    name: str
    url: str
    workspace: Optional[str] = None
    description: Optional[str] = None
    labels: Optional[str] = None
    compute_env: Optional[str] = Field(default=None, alias="compute-env")
    work_dir: Optional[str] = Field(default=None, alias="work-dir")
    profile: Optional[str] = None
    params_file: Optional[str] = Field(default=None, alias="params-file")
    revision: Optional[str] = None
    config: Optional[str] = None
    pre_run: Optional[str] = Field(default=None, alias="pre-run")
    post_run: Optional[str] = Field(default=None, alias="post-run")
    pull_latest: Optional[bool] = Field(default=None, alias="pull-latest")
    stub_run: Optional[bool] = Field(default=None, alias="stub-run")
    main_script: Optional[str] = Field(default=None, alias="main-script")
    entry_name: Optional[str] = Field(default=None, alias="entry-name")
    schema_name: Optional[str] = Field(default=None, alias="schema-name")
    user_secrets: Optional[str] = Field(default=None, alias="user-secrets")
    workspace_secrets: Optional[str] = Field(default=None, alias="workspace-secrets")

    def to_cli_args(self) -> List[str]:
        """
        Override to handle URL as positional argument.
        Format: tw pipelines add <url> --name <name> --workspace <workspace> ...

        Note: params and params-file are excluded here as they require special handling
        (dataset resolution, temp file creation) in the CommandBuilder.
        """
        args = []
        data = self.input_dict().copy()

        # URL is the first positional argument
        if "url" in data:
            args.append(data.pop("url"))

        # Remove params-related fields - they'll be handled by the builder
        data.pop("params", None)
        data.pop("params-file", None)

        # Rest as standard options
        for key, value in data.items():
            if isinstance(value, bool):
                if value:
                    args.append(f"--{key}")
            elif value is not None:
                args.extend([f"--{key}", str(value)])

        return args

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