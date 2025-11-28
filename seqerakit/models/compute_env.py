from pydantic import Field, field_validator
from typing import Optional, List
from seqerakit.models.base import SeqeraResource

class ComputeEnv(SeqeraResource):
    type: str
    config_mode: str = Field(alias="config-mode")
    name: str
    credentials: Optional[str] = None
    workspace: Optional[str] = None
    work_dir: str = Field(alias="work-dir")
    region: str
    max_cpus: int = Field(alias="max-cpus")
    wave: Optional[bool] = None
    wave_enabled: Optional[bool] = Field(default=None, alias="wave-enabled")
    fusion_v2: Optional[bool] = Field(default=None, alias="fusion-v2")
    fusion2_enabled: Optional[bool] = Field(default=None, alias="fusion2-enabled")
    fast_storage: Optional[bool] = Field(default=None, alias="fast-storage")
    nvnme_storage_enabled: Optional[bool] = Field(default=None, alias="nvnme-storage-enabled")
    snapshots: Optional[bool] = None
    fargate: Optional[bool] = None
    provisioning_model: Optional[str] = Field(default=None, alias="provisioning-model")
    instance_types: Optional[list[str]] = Field(default=None, alias="instance-types")
    min_cpus: Optional[int] = Field(default=None, alias="min-cpus")
    no_ebs_auto_scale: Optional[bool] = Field(default=None, alias="no-ebs-auto-scale")
    labels: Optional[str] = None
    vpc_id: Optional[str] = Field(default=None, alias="vpc-id")
    subnets: Optional[list[str]] = None
    security_groups: Optional[list[str]] = Field(default=None, alias="security-groups")
    allow_buckets: Optional[list[str]] = Field(default=None, alias="allow-buckets")
    ebs_blocksize: Optional[int] = Field(default=None, alias="ebs-blocksize")
    head_job_cpus: Optional[int] = Field(default=None, alias="head-job-cpus")
    head_job_memory: Optional[int] = Field(default=None, alias="head-job-memory")
    gpu: Optional[bool] = None
    wait: Optional[str] = None
    preserve_resources: Optional[bool] = Field(default=None, alias="preserve-resources")

    @field_validator('instance_types', 'subnets', 'security_groups', 'allow_buckets', mode='before')
    @classmethod
    def split_comma_separated(cls, v):
        """Convert comma-separated strings to lists for CLI compatibility"""
        if isinstance(v, str):
            return [item.strip() for item in v.split(',') if item.strip()]
        return v

    def to_cli_args(self) -> List[str]:
        """
        Override to handle type and config-mode as positional arguments.
        Format: tw compute-envs add <type> <config-mode> --name <name> ...
        """
        args = []
        data = self.input_dict().copy()

        # Type and config-mode are positional arguments
        if "type" in data:
            args.append(data.pop("type"))
        if "config-mode" in data:
            args.append(data.pop("config-mode"))

        # Rest as standard options
        for key, value in data.items():
            if isinstance(value, bool):
                if value:
                    args.append(f"--{key}")
            elif isinstance(value, list):
                # Handle lists (instance-types, subnets, etc.)
                args.extend([f"--{key}", ",".join(str(v) for v in value)])
            elif value is not None:
                args.extend([f"--{key}", str(value)])

        return args

    @classmethod
    def from_cli_response(cls, data: dict) -> "ComputeEnv":
        """
        Create a ComputeEnv instance from API response for `tw compute-envs view` data by mapping fields
        """
        config = data.get("config", {})
        forge_config = config.get("forge", {})

        # Extract labels with name=value format and join as comma-separated string
        labels = [
            f"{label['name']}={label['value']}"
            for label in data.get("labels", [])
            if not label.get("resource", True)
        ]
        labels_str = ",".join(sorted(labels)) if labels else None
        
        mapped_data = {
            "name": data.get("name"),
            "type": data.get("discriminator"),
            "config_mode": "forge" if data.get("forge") else "manual",
            "work_dir": config.get("workDir"),
            "region": config.get("region"),
            "wave_enabled": config.get("waveEnabled"),
            "fusion2_enabled": config.get("fusion2Enabled"),
            "nvnme_storage_enabled": config.get("nvnmeStorageEnabled"),
            "provisioning_model": forge_config.get("type"),
            "instance_types": forge_config.get("instanceTypes", []),
            "min_cpus": forge_config.get("minCpus"),
            "max_cpus": forge_config.get("maxCpus"),
            #TODO: add ebs_auto_scale
            "labels": forge_config.get("labels", []),
            "vpc_id": forge_config.get("vpcId"),
            "subnets": forge_config.get("subnets", []),
            "security_groups": forge_config.get("securityGroups", []),
            "allow_buckets": forge_config.get("allowBuckets", []),
            "ebs_blocksize": forge_config.get("ebsBlockSize"),
            "head_job_cpus": config.get("headJobCpus"),
            "head_job_memory": config.get("headJobMemoryMb"),
            "gpu": forge_config.get("gpuEnabled"),
            "ebs_auto_scale": forge_config.get("ebsAutoScale"),
            "labels": labels_str,
        }
        return cls(**mapped_data)