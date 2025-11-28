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
from seqerakit.models.base import SeqeraResource
from pydantic import ValidationError
from abc import ABC, abstractmethod
from typing import Dict, Any, Union, List, Tuple, Type
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

    def execute(self, sp):
        """
        Execute this command using a SeqeraPlatform instance.

        Args:
            sp: SeqeraPlatform instance to execute the command with

        Returns:
            The result of executing the command
        """
        # Get the subcommand method from SeqeraPlatform
        subcommand_method = getattr(sp, self.subcommand.replace("-", "_"))

        # Execute with or without method depending on configuration
        if self.method:
            return subcommand_method(self.method, *self.args)
        else:
            return subcommand_method(*self.args)


class ArgumentBuilder:
    """Helper class to build command arguments in a structured way"""

    def __init__(self):
        self.args: List[str] = []

    def add_flag(self, flag: str, condition: bool = True) -> "ArgumentBuilder":
        """Add a boolean flag if condition is true"""
        if condition:
            self.args.append(f"--{flag}")
        return self

    def add_option(self, key: str, value: Any) -> "ArgumentBuilder":
        """Add a key-value option"""
        if value is not None:
            self.args.extend([f"--{key}", str(value)])
        return self

    def add_positional(self, value: str) -> "ArgumentBuilder":
        """Add a positional argument"""
        self.args.append(str(value))
        return self

    def build(self) -> List[str]:
        """Return the built argument list"""
        return self.args.copy()


class CommandBuilder(ABC):
    """Base class for building commands from Pydantic models"""

    def __init__(
        self, subcommand: str, model_class: Type[SeqeraResource], method: str = "add"
    ):
        self.subcommand = subcommand
        self.model_class = model_class
        self.method = method

    @abstractmethod
    def build_command(self, model_instance: SeqeraResource, sp=None) -> Command:
        """Build a command from validated Pydantic model instance"""
        pass

    def build_command_from_dict(self, item: Dict[str, Any], sp=None) -> Command:
        """
        Fallback method for building commands directly from dicts (for file imports).
        This bypasses Pydantic validation. Can be overridden by subclasses.
        """
        # Default implementation: strip metadata and convert to args
        data = {k: v for k, v in item.items() if k not in ["on_exists", "overwrite"]}
        args = self._dict_to_args(data)
        return Command(subcommand=self.subcommand, method=self.method, args=args)

    def _dict_to_args(self, data: Dict[str, Any]) -> List[str]:
        """Convert a dictionary to CLI arguments"""
        builder = ArgumentBuilder()
        for key, value in data.items():
            if isinstance(value, bool):
                if value:  # Only add flag if True
                    builder.add_flag(key, value)
            elif value is not None:
                builder.add_option(key, value)
        return builder.build()


class GenericCommandBuilder(CommandBuilder):
    """Generic builder that uses model's to_cli_args() method"""

    def build_command(self, model_instance: SeqeraResource, sp=None) -> Command:
        # Simply delegate to the model's to_cli_args() method
        args = model_instance.to_cli_args()

        return Command(subcommand=self.subcommand, method=self.method, args=args)


class TypeBasedCommandBuilder(CommandBuilder):
    """For resources that need type/config-mode/file-path as positional args (credentials, compute-envs, actions)"""

    def build_command(self, model_instance: SeqeraResource, sp=None) -> Command:
        # Use the model's to_cli_args() which already handles positional arguments
        args = model_instance.to_cli_args()

        # Handle params specially if present (convert dict to temp file)
        data = model_instance.input_dict()
        if "params" in data:
            params = data["params"]
            temp_file = utils.create_temp_yaml(params)
            args.extend(["--params-file", temp_file])

        # Determine method based on whether file-path contains .json
        method = "import" if any(".json" in str(v) for v in data.values()) else "add"

        return Command(subcommand=self.subcommand, method=method, args=args)

    def build_command_from_dict(self, item: Dict[str, Any], sp=None) -> Command:
        """Override for file-path imports"""
        builder = ArgumentBuilder()
        data = {k: v for k, v in item.items() if k not in ["on_exists", "overwrite"]}

        # Handle priority arguments first as positional
        priority_keys = ["type", "config-mode", "file-path"]
        for key in priority_keys:
            if key in data:
                builder.add_positional(data.pop(key))

        # Handle remaining arguments
        for key, value in data.items():
            if isinstance(value, bool):
                if value:
                    builder.add_flag(key, value)
            elif value is not None:
                builder.add_option(key, value)

        method = "import" if any(".json" in str(v) for v in item.values()) else "add"
        return Command(subcommand=self.subcommand, method=method, args=builder.build())


class TeamsCommandBuilder(CommandBuilder):
    """Special handling for teams with members"""

    def build_command(
        self, model_instance: SeqeraResource, sp=None
    ) -> Union[Command, Tuple[Command, List[Command]]]:
        data = model_instance.input_dict()

        # Extract members for separate handling
        members = data.get("members", [])

        # Get base args for team (excluding members)
        # Create a temporary copy without members for to_cli_args
        data_without_members = {k: v for k, v in data.items() if k != "members"}

        # Manually build args since we need to exclude members
        args = []
        for key, value in data_without_members.items():
            if isinstance(value, bool):
                if value:
                    args.append(f"--{key}")
            elif value is not None:
                args.extend([f"--{key}", str(value)])

        main_command = Command(subcommand="teams", method="add", args=args)

        # Build member commands if members exist
        if members:
            members_commands = []
            team_name = data.get("name")
            org_name = data.get("organization")

            for member in members:
                member_args = [
                    "--team",
                    team_name,
                    "--organization",
                    org_name,
                    "add",
                    "--member",
                    member,
                ]

                members_commands.append(
                    Command(subcommand="teams", method="members", args=member_args)
                )

            return (main_command, members_commands)

        return main_command


class PipelineCommandBuilder(CommandBuilder):
    """For pipelines and launch commands with special params handling"""

    def build_command(self, model_instance: SeqeraResource, sp=None) -> Command:
        # Start with the model's to_cli_args() which handles URL/pipeline as positional
        args = model_instance.to_cli_args()

        # Get original data for params handling
        data = model_instance.input_dict()

        # Handle params specially - resolve dataset reference and create temp file
        params = data.get("params")
        params_file = data.get("params-file")

        if params:
            # Resolve dataset reference if sp and workspace are provided
            workspace = data.get("workspace")
            if sp is not None and workspace:
                params = resolve_dataset_reference(params, workspace, sp)

            # Create temp file and add params-file option
            temp_file = utils.create_temp_yaml(params, params_file=params_file)
            args.extend(["--params-file", temp_file])
        elif params_file:
            args.extend(["--params-file", params_file])

        # Determine method (import for JSON files, add otherwise)
        method = "import" if any(".json" in str(v) for v in data.values()) else "add"

        return Command(subcommand=self.subcommand, method=method, args=args)

    def build_command_from_dict(self, item: Dict[str, Any], sp=None) -> Command:
        """Override for file-path imports"""
        builder = ArgumentBuilder()
        data = {k: v for k, v in item.items() if k not in ["on_exists", "overwrite"]}

        # Handle URL/file-path/pipeline as positional
        positional_keys = ["url", "file-path", "pipeline"]
        for key in positional_keys:
            if key in data:
                builder.add_positional(data.pop(key))
                break

        # Handle params
        params = data.pop("params", None)
        params_file = data.pop("params-file", None)

        if params:
            workspace = data.get("workspace")
            if sp is not None and workspace:
                params = resolve_dataset_reference(params, workspace, sp)
            temp_file = utils.create_temp_yaml(params, params_file=params_file)
            builder.add_option("params-file", temp_file)
        elif params_file:
            builder.add_option("params-file", params_file)

        # Handle remaining
        for key, value in data.items():
            if isinstance(value, bool):
                if value:
                    builder.add_flag(key, value)
            elif value is not None:
                builder.add_option(key, value)

        method = "import" if any(".json" in str(v) for v in item.values()) else "add"
        return Command(subcommand=self.subcommand, method=method, args=builder.build())


# Model mapping for validation
MODEL_MAP: Dict[str, Type[SeqeraResource]] = {
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

# Registry of command builders with their associated models
COMMAND_BUILDERS: Dict[str, CommandBuilder] = {
    "credentials": TypeBasedCommandBuilder("credentials", Credential),
    "compute-envs": TypeBasedCommandBuilder("compute-envs", ComputeEnv),
    "actions": TypeBasedCommandBuilder("actions", Action),
    "teams": TeamsCommandBuilder("teams", Team),
    "pipelines": PipelineCommandBuilder("pipelines", Pipeline),
    "launch": PipelineCommandBuilder("launch", Launch),
    "datasets": GenericCommandBuilder("datasets", Dataset),
    "workspaces": GenericCommandBuilder("workspaces", Workspace),
    "organizations": GenericCommandBuilder("organizations", Organization),
    "labels": GenericCommandBuilder("labels", Label),
    "members": GenericCommandBuilder("members", Member),
    "participants": GenericCommandBuilder("participants", Participant),
    "secrets": GenericCommandBuilder("secrets", Secret),
    "data-links": GenericCommandBuilder("data-links", DataLink),
    "studios": GenericCommandBuilder("studios", Studio),
}


def validate_and_build_model(
    block_name: str, item: Dict[str, Any]
) -> Tuple[SeqeraResource, Dict[str, Any]]:
    """
    Validate a single YAML item using its Pydantic model and return the model instance.

    Returns:
        Tuple of (validated_model_instance, metadata_dict)
        metadata_dict contains on_exists and overwrite settings
    """
    if block_name not in MODEL_MAP:
        raise ValueError(f"No model defined for block type: {block_name}")

    model_class = MODEL_MAP[block_name]

    # Extract metadata that shouldn't be validated by the model
    metadata = {
        "on_exists": item.get("on_exists"),
        "overwrite": item.get("overwrite"),
    }

    # Skip validation for items with file-path (JSON import)
    # For these, create a minimal model instance just for structure
    if "file-path" in item:
        # Create a pass-through dict-based approach for file imports
        # We'll handle this specially in parse_block
        return None, metadata

    try:
        # Create and validate the model instance
        validated_model = model_class(**item)
        return validated_model, metadata
    except ValidationError as e:
        raise ValueError(f"Validation error in {block_name}: {e}")


def parse_block(block_name: str, item: Dict[str, Any], sp=None) -> Dict[str, Any]:
    """
    Parse a YAML block item into a command using Pydantic models and command builders.

    Args:
        block_name: The type of resource (e.g., "pipelines", "teams")
        item: The raw YAML item dictionary
        sp: Optional SeqeraPlatform instance for API calls

    Returns:
        Dictionary with 'cmd_args' (Command object) and 'on_exists' (OnExists enum)
    """
    # Validate and build Pydantic model
    model_instance, metadata = validate_and_build_model(block_name, item)

    # Handle on_exists/overwrite from metadata
    overwrite = metadata.get("overwrite")
    on_exists_str = metadata.get("on_exists")

    # Determine on_exists value with proper default
    if overwrite is not None:
        on_exists = OnExists.OVERWRITE if overwrite else OnExists.FAIL
    elif on_exists_str is not None:
        if isinstance(on_exists_str, str):
            try:
                on_exists = OnExists[on_exists_str.upper()]
            except KeyError:
                raise ValueError(f"Invalid on_exists option: '{on_exists_str}'")
        else:
            on_exists = on_exists_str
    else:
        # Default to FAIL if neither overwrite nor on_exists is specified
        on_exists = OnExists.FAIL

    # Get the appropriate command builder
    builder = COMMAND_BUILDERS.get(block_name)
    if not builder:
        # Fallback to generic builder if no specific builder exists
        if block_name in MODEL_MAP:
            builder = GenericCommandBuilder(block_name, MODEL_MAP[block_name])
        else:
            raise ValueError(f"No command builder found for: {block_name}")

    # Handle file-path imports specially (no validation, pass through)
    if model_instance is None:
        # For file imports, build command directly from dict
        command_result = builder.build_command_from_dict(item, sp)
    else:
        # Use validated Pydantic model
        command_result = builder.build_command(model_instance, sp)

    return {"cmd_args": command_result, "on_exists": on_exists}


def parse_yaml_block(yaml_data, block_name, sp=None, name_filter=None):
    """
    Parse a YAML block into a list of commands.

    Args:
        yaml_data: The full YAML data dictionary
        block_name: The resource type to process (e.g., "pipelines", "teams")
        sp: Optional SeqeraPlatform instance for API calls
        name_filter: Optional list of names to filter resources

    Returns:
        Tuple of (block_name, list of command dictionaries)
    """
    # Get the specified block/resource
    block = yaml_data.get(block_name)

    # If block is not found in the YAML, return an empty list
    if not block:
        return block_name, []

    # Initialize list to hold command line arguments
    cmd_args_list = []

    # Track name values to detect duplicates
    name_values = set()

    # Iterate over each item in the block
    for item in block:
        # Filter by name if name_filter is specified
        item_name = item.get("name") or item.get("user") or item.get("email")
        if name_filter and item_name not in name_filter:
            continue

        # Parse the item using Pydantic validation and command builders
        cmd_args = parse_block(block_name, item, sp)

        # Check for duplicate names
        name = find_name(cmd_args)
        if name in name_values:
            raise ValueError(
                f" Duplicate name key specified in config file"
                f" for {block_name}: {name}. Please specify a unique value."
            )
        name_values.add(name)

        cmd_args_list.append(cmd_args)

    # Return the block name and list of command line argument lists
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

    NOTE: This function is kept for backward compatibility with tests.
    New code should use the integrated params handling in PipelineCommandBuilder.

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
            return search(
                main_command.args if hasattr(main_command, "args") else main_command
            )
        # Handle regular Command object
        elif hasattr(command, "args"):
            return search(command.args)

    # Legacy format
    return search(cmd_args.get("cmd_args", []))


def handle_generic_block(sp, block, cmd_args, method_name="add"):
    """Generic handler for most blocks, with optional method name"""
    if isinstance(cmd_args, Command):
        # Use the new execute method
        return cmd_args.execute(sp)
    else:
        # Legacy support for raw args
        method = getattr(sp, block)
        if method_name is None:
            method(*cmd_args)
        else:
            method(method_name, *cmd_args)


def handle_teams(sp, cmd_args):
    """Handler for teams with member management"""
    # Extract command and member commands from tuple
    if isinstance(cmd_args, tuple):
        main_cmd, members_cmd_args = cmd_args
        # Execute main team command
        if isinstance(main_cmd, Command):
            main_cmd.execute(sp)
        else:
            sp.teams("add", *main_cmd)

        # Execute member commands
        for member_cmd in members_cmd_args:
            if isinstance(member_cmd, Command):
                member_cmd.execute(sp)
            else:
                sp.teams("members", *member_cmd)
    elif isinstance(cmd_args, Command):
        cmd_args.execute(sp)
    else:
        # Legacy format
        cmd_args_list, members_cmd_args = cmd_args
        sp.teams("add", *cmd_args_list)
        for sublist in members_cmd_args:
            sp.teams("members", *sublist)


def handle_members(sp, cmd_args):
    """Handler for organization members"""
    if isinstance(cmd_args, Command):
        cmd_args.execute(sp)
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
        cmd_args.execute(sp)
    else:
        args = cmd_args
        json_file = any(".json" in arg for arg in args)
        method_name = "import" if json_file else "add"
        sp.compute_envs(method_name, *args)


def handle_pipelines(sp, cmd_args):
    """Handler for pipelines (import vs add)"""
    if isinstance(cmd_args, Command):
        cmd_args.execute(sp)
    else:
        args = cmd_args
        # Determine method based on args
        method_name = "add"
        for arg in args:
            if ".json" in arg:
                method_name = "import"
                break
        sp.pipelines(method_name, *args)
