from pydantic import Field
from typing import Optional
from seqerakit.models.base import SeqeraResource

class ComputeEnv(SeqeraResource):
    type: str
    config_mode: str = Field(alias="config-mode")
    name: str
    credentials: str = Field(alias="credentials")
    workspace: str
    work_dir: str = Field(alias="work-dir")
    region: str
    wave_enabled: Optional[bool] = Field(alias="wave-enabled")
    fusion2_enabled: Optional[bool] = Field(alias="fusion2-enabled")
    nvnme_storage_enabled: Optional[bool] = Field(alias="nvnme-storage-enabled")
    provisioning_model: Optional[str] = Field(alias="provisioning-model")
    instance_types: Optional[list[str]] = Field(alias="instance-types")
    min_cpus: Optional[int] = Field(alias="min-cpus")
    max_cpus: int = Field(alias="max-cpus")
    ebs_auto_scale: Optional[bool] = Field(alias="no-ebs-auto-scale")
    labels: Optional[list[str]] = Field(alias="labels")
    vpc_id: Optional[str] = Field(alias="vpc-id")
    subnets: Optional[list[str]] = Field(alias="subnets")
    security_groups: Optional[list[str]] = Field(alias="security-groups")
    allow_buckets: Optional[list[str]] = Field(alias="allow-buckets")
    ebs_blocksize: Optional[int] = Field(alias="ebs-blocksize")
    head_job_cpus: Optional[int] = Field(alias="head-job-cpus")
    head_job_memory: Optional[int] = Field(alias="head-job-memory")
    gpu: Optional[bool] = Field(alias="gpu")

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