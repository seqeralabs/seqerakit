from enum import Enum
from typing import Dict, Type, Any
from abc import ABC, abstractmethod
from pydantic import BaseModel
from .seqeraplatform import SeqeraPlatform
from .models import (
    ComputeEnv,
    Pipeline,
    Organization,
    Workspace,
    Team,
    Label,
    Member,
    Participant,
    Credential,
    Dataset,
    Secret,
    Action,
    DataLink,
    Studio,
    SeqeraResource,
)

class ResourceType(Enum):
    COMPUTE_ENV = "compute-envs"
    PIPELINES = "pipelines"
    ORGANIZATIONS = "organizations"
    WORKSPACES = "workspaces"
    TEAMS = "teams"
    LABELS = "labels"
    MEMBERS = "members"
    PARTICIPANTS = "participants"
    CREDENTIALS = "credentials"
    DATASETS = "datasets"
    SECRETS = "secrets"
    ACTIONS = "actions"
    DATA_LINKS = "data-links"
    STUDIOS = "studios"
class ResourceDumper(ABC):
    """Abstract base class for getting API responses and models for resources"""
    
    def __init__(self, sp: SeqeraPlatform):
        # Create a new SeqeraPlatform instance with JSON output enabled
        self.sp = SeqeraPlatform(
            cli_args=sp.cli_args,
            dryrun=sp.dryrun,
            print_stdout=sp.print_stdout,
            json=True
        )

    @abstractmethod
    def get_api_response(self, workspace: str, **kwargs) -> dict:
        """Get response from API for this resource type"""
        pass
        
    @abstractmethod
    def get_model(self) -> Type[SeqeraResource]:
        """Get the Pydantic model for this resource type"""
        pass

class ComputeEnvDumper(ResourceDumper):
    def __init__(self, sp: "SeqeraPlatform"):
        self.sp = sp
        
    def get_api_response(self, workspace: str, **kwargs) -> dict:
        """Get compute environment details using tw compute-envs view"""
        name = kwargs.get("name")
        if not name:
            raise ValueError("name is required for compute environment dump")
        return self.sp.compute_envs("view", "-w", workspace, "-n", name)
    
    def get_model(self) -> Type[BaseModel]:
        return ComputeEnv

class PipelineDumper(ResourceDumper):
    def __init__(self, sp: "SeqeraPlatform"):
        self.sp = SeqeraPlatform(
            cli_args=sp.cli_args,
            dryrun=sp.dryrun,
            print_stdout=sp.print_stdout,
            json=True
        )
        
    def get_api_response(self, workspace: str, **kwargs) -> dict:
        """Get pipeline details using tw pipelines view"""
        name = kwargs.get("name")
        if not name:
            raise ValueError("name is required for pipeline dump")
        return self.sp.pipelines("view", "-w", workspace, "-n", name)
    
    def get_model(self) -> Type[BaseModel]:
        return Pipeline

class OrganizationDumper(ResourceDumper):
    def __init__(self, sp: "SeqeraPlatform"):
        self.sp = SeqeraPlatform(cli_args=sp.cli_args, dryrun=sp.dryrun, print_stdout=sp.print_stdout, json=True)

    def get_api_response(self, workspace: str, **kwargs) -> dict:
        name = kwargs.get("name")
        if not name:
            raise ValueError("name is required for organization dump")
        return self.sp.organizations("view", "-n", name)

    def get_model(self) -> Type[BaseModel]:
        return Organization

class WorkspaceDumper(ResourceDumper):
    def __init__(self, sp: "SeqeraPlatform"):
        self.sp = SeqeraPlatform(cli_args=sp.cli_args, dryrun=sp.dryrun, print_stdout=sp.print_stdout, json=True)

    def get_api_response(self, workspace: str, **kwargs) -> dict:
        return self.sp.workspaces("view", "-w", workspace)

    def get_model(self) -> Type[BaseModel]:
        return Workspace

class TeamDumper(ResourceDumper):
    def __init__(self, sp: "SeqeraPlatform"):
        self.sp = SeqeraPlatform(cli_args=sp.cli_args, dryrun=sp.dryrun, print_stdout=sp.print_stdout, json=True)

    def get_api_response(self, workspace: str, **kwargs) -> dict:
        name = kwargs.get("name")
        org = kwargs.get("organization")
        if not name or not org:
            raise ValueError("name and organization are required for team dump")
        return self.sp.teams("view", "-n", name, "-o", org)

    def get_model(self) -> Type[BaseModel]:
        return Team

class LabelDumper(ResourceDumper):
    def __init__(self, sp: "SeqeraPlatform"):
        self.sp = SeqeraPlatform(cli_args=sp.cli_args, dryrun=sp.dryrun, print_stdout=sp.print_stdout, json=True)

    def get_api_response(self, workspace: str, **kwargs) -> dict:
        name = kwargs.get("name")
        if not name:
            raise ValueError("name is required for label dump")
        return self.sp.labels("view", "-n", name, "-w", workspace)

    def get_model(self) -> Type[BaseModel]:
        return Label

class DatasetDumper(ResourceDumper):
    def __init__(self, sp: "SeqeraPlatform"):
        self.sp = SeqeraPlatform(cli_args=sp.cli_args, dryrun=sp.dryrun, print_stdout=sp.print_stdout, json=True)

    def get_api_response(self, workspace: str, **kwargs) -> dict:
        name = kwargs.get("name")
        if not name:
            raise ValueError("name is required for dataset dump")
        return self.sp.datasets("view", "-n", name, "-w", workspace)

    def get_model(self) -> Type[BaseModel]:
        return Dataset

class SecretDumper(ResourceDumper):
    def __init__(self, sp: "SeqeraPlatform"):
        self.sp = SeqeraPlatform(cli_args=sp.cli_args, dryrun=sp.dryrun, print_stdout=sp.print_stdout, json=True)

    def get_api_response(self, workspace: str, **kwargs) -> dict:
        name = kwargs.get("name")
        if not name:
            raise ValueError("name is required for secret dump")
        return self.sp.secrets("view", "-n", name, "-w", workspace)

    def get_model(self) -> Type[BaseModel]:
        return Secret

class DataLinkDumper(ResourceDumper):
    def __init__(self, sp: "SeqeraPlatform"):
        self.sp = SeqeraPlatform(cli_args=sp.cli_args, dryrun=sp.dryrun, print_stdout=sp.print_stdout, json=True)

    def get_api_response(self, workspace: str, **kwargs) -> dict:
        name = kwargs.get("name")
        if not name:
            raise ValueError("name is required for data-link dump")
        return self.sp.data_links("view", "-n", name, "-w", workspace)

    def get_model(self) -> Type[BaseModel]:
        return DataLink

class StudioDumper(ResourceDumper):
    def __init__(self, sp: "SeqeraPlatform"):
        self.sp = SeqeraPlatform(cli_args=sp.cli_args, dryrun=sp.dryrun, print_stdout=sp.print_stdout, json=True)

    def get_api_response(self, workspace: str, **kwargs) -> dict:
        name = kwargs.get("name")
        if not name:
            raise ValueError("name is required for studio dump")
        return self.sp.studios("view", "-n", name, "-w", workspace)

    def get_model(self) -> Type[BaseModel]:
        return Studio

class Dump:
    """Main class for handling resource dumps"""

    def __init__(self, sp: "SeqeraPlatform"):
        self.sp = sp
        self._dumpers: Dict[ResourceType, ResourceDumper] = {
            ResourceType.COMPUTE_ENV: ComputeEnvDumper(sp),
            ResourceType.PIPELINES: PipelineDumper(sp),
            ResourceType.ORGANIZATIONS: OrganizationDumper(sp),
            ResourceType.WORKSPACES: WorkspaceDumper(sp),
            ResourceType.TEAMS: TeamDumper(sp),
            ResourceType.LABELS: LabelDumper(sp),
            ResourceType.DATASETS: DatasetDumper(sp),
            ResourceType.SECRETS: SecretDumper(sp),
            ResourceType.DATA_LINKS: DataLinkDumper(sp),
            ResourceType.STUDIOS: StudioDumper(sp),
        }
    
    def dump_resource(self, resource_type: str, workspace: str, **kwargs) -> dict:
        """
        Dump a resource to YAML-compatible dictionary
        
        Args:
            resource_type: Type of resource to dump (e.g., "compute-envs", "pipelines")
            workspace: Workspace name
            **kwargs: Additional arguments (e.g., name of resource)
            
        Returns:
            Dict containing the YAML-compatible representation of the resource
        """
        try:
            resource_enum = ResourceType(resource_type)
        except ValueError:
            raise ValueError(f"Unsupported resource type: {resource_type}")
            
        dumper = self._dumpers[resource_enum]
        response = dumper.get_api_response(workspace, **kwargs)
        model = dumper.get_model()
        instance = model.from_api_response(response)
        
        # Use dump_dict() to include None values for complete output
        return instance.dump_dict()

