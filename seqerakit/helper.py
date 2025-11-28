# Copyright 2023, Seqera
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
This file contains helper functions for the library.
Including handling methods for each block in the YAML file, and parsing
methods for each block in the YAML file.
"""
import yaml  # type: ignore
from seqerakit import utils
import sys
import json
from seqerakit.on_exists import OnExists
from seqerakit.models import (
    Pipeline,
    ComputeEnv,
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
    Launch,
)
from pydantic import ValidationError
from abc import ABC, abstractmethod
from typing import Dict, Any, Union, List, Tuple
from dataclasses import dataclass


@dataclass
class Command:
    """Represents a TW command to be executed"""
    subcommand: str
    args: List[str]
    method: str = "add"  # Default method
    
    def to_args_list(self) -> List[str]:
        """Convert to list of arguments for subprocess"""
        if self.method:
            return [self.subcommand, self.method] + self.args
        return [self.subcommand] + self.args


class ArgumentBuilder:
    """Helper class to build command arguments in a structured way"""
    
    def __init__(self):
        self.args: List[str] = []
    
    def add_flag(self, flag: str, condition: bool = True) -> 'ArgumentBuilder':
        """Add a boolean flag if condition is true"""
        if condition:
            self.args.append(f"--{flag}")
        return self
    
    def add_option(self, key: str, value: Any) -> 'ArgumentBuilder':
        """Add a key-value option"""
        if value is not None:
            self.args.extend([f"--{key}", str(value)])
        return self
    
    def add_positional(self, value: str) -> 'ArgumentBuilder':
        """Add a positional argument"""
        self.args.append(str(value))
        return self
    
    def build(self) -> List[str]:
        """Return the built argument list"""
        return self.args.copy()


class CommandBuilder(ABC):
    """Base class for building commands from YAML data"""
    
    @abstractmethod
    def build_command(self, item: Dict[str, Any], sp=None) -> Command:
        """Build a command from YAML item"""
        pass


class GenericCommandBuilder(CommandBuilder):
    def __init__(self, subcommand: str, method: str = "add"):
        self.subcommand = subcommand
        self.method = method
    
    def build_command(self, item: Dict[str, Any], sp=None) -> Command:
        builder = ArgumentBuilder()
        
        for key, value in item.items():
            if isinstance(value, bool):
                builder.add_flag(key, value)
            else:
                builder.add_option(key, value)
        
        return Command(
            subcommand=self.subcommand,
            method=self.method,
            args=builder.build()
        )


class TypeBasedCommandBuilder(CommandBuilder):
    """For resources that need type/config-mode/file-path as positional args"""
    
    def __init__(self, subcommand: str):
        self.subcommand = subcommand
    
    def build_command(self, item: Dict[str, Any], sp=None) -> Command:
        builder = ArgumentBuilder()
        item_copy = item.copy()
        
        # Ensure at least one of 'type' or 'file-path' is present
        if not any(key in item for key in ["type", "file-path"]):
            raise ValueError("Please specify at least 'type' or 'file-path' for creating the resource.")
        
        # Handle priority arguments first
        priority_keys = ["type", "config-mode", "file-path"]
        for key in priority_keys:
            if key in item_copy:
                builder.add_positional(item_copy.pop(key))
        
        # Handle remaining arguments
        for key, value in item_copy.items():
            if isinstance(value, bool):
                builder.add_flag(key, value)
            elif key == "params":
                temp_file = utils.create_temp_yaml(value)
                builder.add_option("params-file", temp_file)
            else:
                builder.add_option(key, value)
        
        # Determine method based on file type
        method = "import" if any(".json" in str(v) for v in item.values()) else "add"
        
        return Command(
            subcommand=self.subcommand,
            method=method,
            args=builder.build()
        )


class TeamsCommandBuilder(CommandBuilder):
    """Special handling for teams with members"""
    
    def build_command(self, item: Dict[str, Any], sp=None) -> Union[Command, Tuple[Command, List[Command]]]:
        builder = ArgumentBuilder()
        cmd_keys = ["name", "organization", "description"]
        members_commands = []
        
        # Build main team command
        for key, value in item.items():
            if key in cmd_keys:
                builder.add_option(key, value)
            elif key == "members":
                # Build member commands
                for member in value:
                    member_builder = ArgumentBuilder()
                    member_builder.add_option("team", item["name"])
                    member_builder.add_option("organization", item["organization"])
                    member_builder.add_positional("add")
                    member_builder.add_option("member", member)
                    
                    members_commands.append(Command(
                        subcommand="teams",
                        method="members",
                        args=member_builder.build()
                    ))
        
        main_command = Command(
            subcommand="teams",
            method="add",
            args=builder.build()
        )
        
        if members_commands:
            return (main_command, members_commands)
        return main_command


class PipelineCommandBuilder(CommandBuilder):
    """For pipelines and launch commands"""
    
    def __init__(self, subcommand: str):
        self.subcommand = subcommand
    
    def build_command(self, item: Dict[str, Any], sp=None) -> Command:
        builder = ArgumentBuilder()
        item_copy = item.copy()
        
        # Handle URL/file-path as positional
        if "url" in item_copy:
            builder.add_positional(item_copy.pop("url"))
        elif "file-path" in item_copy:
            builder.add_positional(item_copy.pop("file-path"))
        elif "pipeline" in item_copy:  # For launch
            builder.add_positional(item_copy.pop("pipeline"))
        
        # Handle params directly without converting to flat list first
        params = item_copy.pop("params", None)
        params_file = item_copy.pop("params-file", None)
        
        if params:
            # Resolve dataset reference if needed
            if sp is not None and item.get("workspace"):
                params = resolve_dataset_reference(params, item["workspace"], sp)
            
            # Create temp file and add params-file option
            temp_file = utils.create_temp_yaml(params, params_file=params_file)
            builder.add_option("params-file", temp_file)
        elif params_file:
            builder.add_option("params-file", params_file)
        
        # Handle remaining options
        for key, value in item_copy.items():
            if isinstance(value, bool):
                builder.add_flag(key, value)
            else:
                builder.add_option(key, value)
        
        # Determine method
        method = "import" if any(".json" in str(v) for v in item.values()) else "add"
        
        return Command(
            subcommand=self.subcommand,
            method=method,
            args=builder.build()
        )


# Registry of command builders
COMMAND_BUILDERS: Dict[str, CommandBuilder] = {
    "credentials": TypeBasedCommandBuilder("credentials"),
    "compute-envs": TypeBasedCommandBuilder("compute-envs"),
    "actions": TypeBasedCommandBuilder("actions"),
    "teams": TeamsCommandBuilder(),
    "pipelines": PipelineCommandBuilder("pipelines"),
    "launch": PipelineCommandBuilder("launch"),
    "datasets": GenericCommandBuilder("datasets"),
    "workspaces": GenericCommandBuilder("workspaces"),
    "organizations": GenericCommandBuilder("organizations"),
    "labels": GenericCommandBuilder("labels"),
    "members": GenericCommandBuilder("members"),
    "participants": GenericCommandBuilder("participants"),
    "secrets": GenericCommandBuilder("secrets"),
    "data-links": GenericCommandBuilder("data-links"),
    "studios": GenericCommandBuilder("studios"),
}


def validate_yaml_block(block_name: str, items: list) -> list:
    """Validate YAML using Pydantic models defined in models/"""
    model_map = {
        "pipelines": Pipeline,
        "compute-envs": ComputeEnv,
        "organizations": Organization,
        "workspaces": Workspace,
        "teams": Team,
        "labels": Label,
        "members": Member,
        "participants": Participant,
        "credentials": Credential,
        "datasets": Dataset,
        "secrets": Secret,
        "actions": Action,
        "data-links": DataLink,
        "studios": Studio,
        "launch": Launch,
    }

    if block_name not in model_map:
        return items  # No validation for unsupported types

    model_class = model_map[block_name]
    validated_items = []

    for item in items:
        # Preserve on_exists and overwrite fields
        on_exists = item.get("on_exists")
        overwrite = item.get("overwrite")

        # Skip validation for items with file-path (JSON import)
        if "file-path" in item:
            validated_items.append(item)
            continue

        try:
            validated_item = model_class(**item)
            result = validated_item.input_dict()

            # Re-add on_exists/overwrite if they were present
            if on_exists is not None:
                result["on_exists"] = on_exists
            if overwrite is not None:
                result["overwrite"] = overwrite

            validated_items.append(result)
        except ValidationError as e:
            raise ValueError(f"Validation error in {block_name}: {e}")

    return validated_items


def parse_block(block_name: str, item: Dict[str, Any], sp=None) -> Dict[str, Any]:
    """Parse a block using command builders"""
    builder = COMMAND_BUILDERS.get(block_name, GenericCommandBuilder(block_name))
    
    # Handle on_exists/overwrite
    item_copy = item.copy()
    overwrite = item_copy.pop("overwrite", None)
    on_exists_str = item_copy.pop("on_exists", "fail")
    
    if overwrite is not None:
        on_exists = OnExists.OVERWRITE if overwrite else OnExists.FAIL
    elif isinstance(on_exists_str, str):
        try:
            on_exists = OnExists[on_exists_str.upper()]
        except KeyError:
            raise ValueError(f"Invalid on_exists option: '{on_exists_str}'")
    else:
        on_exists = on_exists_str
    
    command_result = builder.build_command(item_copy, sp)

    return {
        "cmd_args": command_result,
        "on_exists": on_exists
    }


def parse_yaml_block(yaml_data, block_name, sp=None, name_filter=None):
    # Get the name of the specified block/resource.
    block = yaml_data.get(block_name)

    # If block is not found in the YAML, return an empty list.
    if not block:
        return block_name, []

    # Validate the block using Pydantic models
    validated_block = validate_yaml_block(block_name, block)

    # Initialize an empty list to hold the lists of command line arguments.
    cmd_args_list = []

    # Initialize a set to track the --name values within the block.
    name_values = set()

    # Iterate over each validated item in the block.
    for item in validated_block:
        # Filter by name if name_filter is specified
        item_name = item.get("name") or item.get("user") or item.get("email")
        if name_filter and item_name not in name_filter:
            continue

        cmd_args = parse_block(block_name, item, sp)
        name = find_name(cmd_args)
        if name in name_values:
            raise ValueError(
                f" Duplicate name key specified in config file"
                f" for {block_name}: {name}. Please specify a unique value."
            )
        name_values.add(name)

        cmd_args_list.append(cmd_args)

    # Return the block name and list of command line argument lists.
    return block_name, cmd_args_list


def parse_all_yaml(file_paths, destroy=False, targets=None, target=None, sp=None):
    # If multiple yamls, merge them into one dictionary
    merged_data = {}

    # Special handling for stdin represented by "-"
    if not file_paths or "-" in file_paths:
        # Read YAML directly from stdin
        data = yaml.safe_load(sys.stdin)
        if not data:
            raise ValueError(
                " The input from stdin is empty or does not contain valid YAML data."
            )
        merged_data.update(data)

    for file_path in file_paths:
        if file_path == "-":
            continue
        try:
            with open(file_path, "r") as f:
                data = yaml.safe_load(f)
                if not data:
                    raise ValueError(
                        f" The file '{file_path}' is empty or "
                        "does not contain valid data."
                    )
            # Process each key-value pair in YAML data
            for key, new_value in data.items():
                # Check if key exist in merged_data and
                # new value is a list of dictionaries
                if (
                    key in merged_data
                    and isinstance(new_value, list)
                    and all(isinstance(i, dict) for i in new_value)
                ):
                    # Serialize dictionaries to JSON strings for comparison
                    existing_items = {
                        json.dumps(d, sort_keys=True) for d in merged_data[key]
                    }
                    for item in new_value:
                        # Check if item is not already present in merged data
                        item_json = json.dumps(item, sort_keys=True)
                        if item_json not in existing_items:
                            # Append item to merged data
                            merged_data[key].append(item)
                else:
                    merged_data[key] = new_value

        except FileNotFoundError:
            print(f"Error: The file '{file_path}' was not found.")
            sys.exit(1)

    block_names = list(merged_data.keys())

    # Filter blocks based on targets if provided
    if targets:
        target_blocks = set(targets.split(","))
        block_names = [block for block in block_names if block in target_blocks]

    # Define the order in which the resources should be created.
    resource_order = [
        "organizations",
        "teams",
        "workspaces",
        "labels",
        "members",
        "participants",
        "credentials",
        "compute-envs",
        "secrets",
        "actions",
        "datasets",
        "pipelines",
        "launch",
        "data-links",
        "studios",
    ]

    # Reverse the order of resources to delete if destroy is True
    if destroy:
        resource_order = resource_order[:-1][::-1]

    # Initialize an empty dictionary to hold all the command arguments.
    cmd_args_dict = {}

    # Iterate over each block name in the desired order.
    for block_name in resource_order:
        if block_name in block_names:
            # Parse the block and add its command line arguments to the dictionary.
            block_name, cmd_args_list = parse_yaml_block(merged_data, block_name, sp)
            cmd_args_dict[block_name] = cmd_args_list

    # Return the dictionary of command arguments.
    return cmd_args_dict


def resolve_dataset_reference(params_dict, workspace, sp):
    """
    Resolve dataset reference to URL in params dictionary.

    Args:
        params_dict (dict): Parameters dictionary that might contain dataset reference
        workspace (str): Workspace for the dataset
        sp (SeqeraPlatform): Instance to make CLI calls

    Returns:
        dict: Updated parameters dictionary with dataset URL

    Raises:
        ValueError: If dataset doesn't exist in the workspace or URL cannot be retrieved
    """
    if not params_dict or "dataset" not in params_dict:
        return params_dict

    processed_params = params_dict.copy()
    dataset_name = processed_params["dataset"]

    try:
        # retrieve dataset url
        with sp.suppress_output():
            sp.json = True  # run in json mode
            result = sp.datasets("url", "-n", dataset_name, "-w", workspace)

        if not result or "datasetUrl" not in result:
            raise ValueError(f"No URL found for dataset '{dataset_name}'")

        processed_params["input"] = result["datasetUrl"]
        del processed_params["dataset"]

    except Exception as e:
        raise ValueError(f"Failed to resolve dataset '{dataset_name}': {str(e)}")

    return processed_params


def process_params_dict(params_dict, workspace=None, sp=None, params_file_path=None):
    """
    Process parameters dictionary, resolving dataset references if needed.

    Args:
        params_dict (dict): Parameters dictionary to process
        workspace (str, optional): Workspace for resolving dataset references
        sp (SeqeraPlatform, optional): Instance to make CLI calls
        params_file_path (str, optional): Path to existing params file

    Returns:
        list: Parameter arguments for command line
    """
    params_args = []

    if params_dict:
        # Resolve dataset reference if sp and workspace provided
        if sp is not None and workspace:
            params_dict = resolve_dataset_reference(params_dict, workspace, sp)

        # Create temp file with resolved params
        temp_file_name = utils.create_temp_yaml(
            params_dict, params_file=params_file_path
        )
        params_args.extend(["--params-file", temp_file_name])
    elif params_file_path:
        params_args.extend(["--params-file", params_file_path])

    return params_args


def find_name(cmd_args):
    """
    Find and return the value associated with --name in cmd_args, where cmd_args
    can be a list, a tuple of lists, or nested lists/tuples.

    The function searches for the following keys: --name, --user, --email.

    Parameters:
    - cmd_args: The command arguments (list, tuple, or nested structures).

    Returns:
    - The value associated with the first key found, or None if none are found.
    """
    # Predefined list of keys to search for
    keys = {"--name", "--user", "--email"}

    def search(args):
        it = iter(args)
        for arg in it:
            if isinstance(arg, str) and arg in keys:
                return next(it, None)
            elif isinstance(arg, (list, tuple)):
                result = search(arg)
                if result is not None:
                    return result
        return None

    # Handle new Command structure
    if "cmd_args" in cmd_args:
        command = cmd_args["cmd_args"]
        # Handle tuple of command and member commands (for teams)
        if isinstance(command, tuple):
            main_command, _ = command
            return search(main_command.args if hasattr(main_command, 'args') else main_command)
        # Handle regular Command object
        elif hasattr(command, 'args'):
            return search(command.args)

    # Legacy format
    return search(cmd_args.get("cmd_args", []))


def handle_generic_block(sp, block, cmd_args, method_name="add"):
    """Generic handler for most blocks, with optional method name"""
    method = getattr(sp, block)
    # Extract args from Command object
    if isinstance(cmd_args, Command):
        args = cmd_args.args
        method_name = cmd_args.method
    else:
        args = cmd_args

    if method_name is None:
        method(*args)
    else:
        method(method_name, *args)


def handle_teams(sp, cmd_args):
    """Handler for teams with member management"""
    # Extract command and member commands from tuple
    if isinstance(cmd_args, tuple):
        main_cmd, members_cmd_args = cmd_args
        sp.teams("add", *main_cmd.args)
        for member_cmd in members_cmd_args:
            sp.teams("members", *member_cmd.args)
    elif isinstance(cmd_args, Command):
        sp.teams(cmd_args.method, *cmd_args.args)
    else:
        # Legacy format
        cmd_args_list, members_cmd_args = cmd_args
        sp.teams("add", *cmd_args_list)
        for sublist in members_cmd_args:
            sp.teams("members", *sublist)


def handle_members(sp, cmd_args):
    """Handler for organization members"""
    if isinstance(cmd_args, Command):
        sp.members(cmd_args.method, *cmd_args.args)
    else:
        sp.members("add", *cmd_args)


def handle_participants(sp, cmd_args):
    """Handler for workspace participants with role updates"""
    if isinstance(cmd_args, Command):
        args = cmd_args.args
    else:
        args = cmd_args

    # First add participant without role
    skip_key = "--role"
    new_args = [
        arg
        for i, arg in enumerate(args)
        if not (args[i - 1] == skip_key or arg == skip_key)
    ]
    sp.participants("add", *new_args)
    # Then update with role
    sp.participants("update", *args)


def handle_compute_envs(sp, cmd_args):
    """Handler for compute environments (import vs add)"""
    if isinstance(cmd_args, Command):
        args = cmd_args.args
        method_name = cmd_args.method
    else:
        args = cmd_args
        json_file = any(".json" in arg for arg in args)
        method_name = "import" if json_file else "add"

    sp.compute_envs(method_name, *args)


def handle_pipelines(sp, cmd_args):
    """Handler for pipelines (import vs add)"""
    if isinstance(cmd_args, Command):
        args = cmd_args.args
        method_name = cmd_args.method
    else:
        args = cmd_args
        # Determine method based on args
        method_name = "add"
        for arg in args:
            if ".json" in arg:
                method_name = "import"
                break

    sp.pipelines(method_name, *args)
