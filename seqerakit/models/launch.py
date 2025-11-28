from pydantic import Field
from typing import Optional, List
from .base import SeqeraResource


class Launch(SeqeraResource):
    """Launch configuration model"""

    pipeline: str
    workspace: Optional[str] = None
    params_file: Optional[str] = Field(default=None, alias="params-file")
    params: Optional[dict] = None
    compute_env: Optional[str] = Field(default=None, alias="compute-env")
    name: Optional[str] = None
    work_dir: Optional[str] = Field(default=None, alias="work-dir")
    profile: Optional[str] = None
    revision: Optional[str] = None
    wait: Optional[str] = None
    labels: Optional[str] = None
    launch_container: Optional[str] = Field(default=None, alias="launch-container")
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
    disable_optimization: Optional[bool] = Field(
        default=None, alias="disable-optimization"
    )

    def to_cli_args(self) -> List[str]:
        """
        Override to handle pipeline as positional argument.
        Format: tw launch <pipeline> --workspace <workspace> ...

        Note: params and params-file are excluded here as they require special handling
        (dataset resolution, temp file creation) in the CommandBuilder.
        """
        args = []
        data = self.input_dict().copy()

        # Pipeline is the first positional argument
        if "pipeline" in data:
            args.append(data.pop("pipeline"))

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
