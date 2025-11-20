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
YAML processing and orchestration for seqerakit configuration files.

This module handles:
- Loading and merging multiple YAML files
- Ordering resource creation according to dependencies
- Parsing individual resource blocks
"""

import sys
import json
import yaml  # type: ignore

from seqerakit.resources import PARSERS
from seqerakit.on_exists import OnExists


# Define the order in which the resources should be created.
# This order respects dependencies (e.g., organizations before workspaces).
RESOURCE_ORDER = [
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


def parse_all_yaml(file_paths, destroy=False, targets=None, sp=None):
    """
    Parse and merge multiple YAML configuration files.

    This function:
    1. Loads and merges multiple YAML files
    2. Filters blocks based on targets if provided
    3. Orders resources according to RESOURCE_ORDER
    4. Parses each block into command arguments

    Args:
        file_paths (list): List of file paths to YAML files, or ["-"] for stdin
        destroy (bool): If True, reverse resource order for deletion
        targets (str): Comma-separated list of resource types to process
        sp: SeqeraPlatform instance for dataset resolution

    Returns:
        dict: Dictionary mapping resource types to lists of parsed command arguments

    Raises:
        ValueError: If YAML data is empty or invalid
        FileNotFoundError: If specified file does not exist
    """
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

    # Use RESOURCE_ORDER for ordering
    resource_order = RESOURCE_ORDER.copy()

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


def parse_yaml_block(yaml_data, block_name, sp=None):
    """
    Parse a single resource block from YAML data.

    Args:
        yaml_data (dict): Merged YAML data
        block_name (str): Name of the resource block (e.g., 'organizations')
        sp: SeqeraPlatform instance for dataset resolution

    Returns:
        tuple: (block_name, list of parsed command arguments)

    Raises:
        ValueError: If duplicate names found within a block
    """
    # Get the name of the specified block/resource.
    block = yaml_data.get(block_name)

    # If block is not found in the YAML, return an empty list.
    if not block:
        return block_name, []

    # Initialize an empty list to hold the lists of command line arguments.
    cmd_args_list = []

    # Initialize a set to track the --name values within the block.
    name_values = set()

    # Iterate over each item in the block.
    # TODO: fix for resources that can be duplicate named in an org
    for item in block:
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


def parse_block(block_name, item, sp=None):
    """
    Parse a single resource item into command arguments.

    This function:
    1. Extracts on_exists/overwrite settings
    2. Uses resource-specific parser if available
    3. Falls back to generic parser for unknown resources

    Args:
        block_name (str): Name of the resource type
        item (dict): Resource configuration from YAML
        sp: SeqeraPlatform instance for dataset resolution

    Returns:
        dict: Dictionary with 'cmd_args' and 'on_exists' keys

    Raises:
        ValueError: If on_exists option is invalid
    """
    # Get parser module for this resource type
    parser_module = PARSERS.get(block_name)

    # Get on_exists setting with backward compatibility for overwrite
    overwrite = item.pop("overwrite", None)
    on_exists_str = item.pop("on_exists", "fail")

    # Determine final on_exists value
    if overwrite is not None:
        # overwrite takes precedence for backward compatibility
        on_exists = OnExists.OVERWRITE if overwrite else OnExists.FAIL
    elif isinstance(on_exists_str, str):
        try:
            on_exists = OnExists[on_exists_str.upper()]
        except KeyError:
            raise ValueError(
                f"Invalid on_exists option: '{on_exists_str}'. "
                f"Valid options are: "
                f"{', '.join(behaviour.name.lower() for behaviour in OnExists)}"
            )
    else:
        # Use directly if already an enum
        on_exists = on_exists_str

    # Use resource-specific parser if available, otherwise generic
    if parser_module:
        cmd_args = parser_module.parse(item, sp)
    else:
        # Fallback to generic parsing for unknown resource types
        cmd_args = parse_generic_block(item, sp)

    return {"cmd_args": cmd_args, "on_exists": on_exists}


def parse_generic_block(item, sp=None):
    """
    Generic parser for resources without specific parsing logic.

    This is a fallback parser that converts dictionary keys to CLI flags.

    Args:
        item (dict): Resource configuration
        sp: SeqeraPlatform instance (unused, for signature compatibility)

    Returns:
        list: Command line arguments
    """
    cmd_args = []
    for key, value in item.items():
        # Skip None values
        if value is None:
            continue
        elif isinstance(value, bool):
            if value:
                cmd_args.append(f"--{key}")
        else:
            cmd_args.extend([f"--{key}", str(value)])
    return cmd_args


def find_name(cmd_args):
    """
    Find and return the value associated with --name, --user, or --email in cmd_args.

    This function supports nested structures (lists, tuples) and is used to
    detect duplicate resources within a block.

    Args:
        cmd_args (dict): Dictionary with 'cmd_args' key containing arguments

    Returns:
        str or None: The value associated with the first key found, or None
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

    return search(cmd_args.get("cmd_args", []))
