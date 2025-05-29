from enum import Enum
from typing import Dict, Type, Any
from .seqeraplatform import SeqeraPlatform
from .models import ComputeEnv, Pipeline, SeqeraResource
from pydantic import BaseModel

# general class for dumping json objects to yaml files depending
# on the subcommand
# e.g. seqerakit dump compute-envs --workspace my-workspace
from enum import Enum
from typing import Type, Dict, Any
from abc import ABC, abstractmethod

class ResourceType(Enum):
    COMPUTE_ENV = "compute-envs"
    PIPELINES = "pipelines"
    # TODO add more resource types here
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

class Dump:
    """Main class for handling resource dumps"""
    
    def __init__(self, sp: "SeqeraPlatform"):
        self.sp = sp
        self._dumpers: Dict[ResourceType, ResourceDumper] = {
            ResourceType.COMPUTE_ENV: ComputeEnvDumper(sp),
            ResourceType.PIPELINES: PipelineDumper(sp),
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

