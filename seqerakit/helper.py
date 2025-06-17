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


def parse_yaml_block(yaml_data, block_name, sp=None):
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


def parse_all_yaml(file_paths, destroy=False, targets=None, sp=None):
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


def parse_block(block_name, item, sp=None):
    # Define the mapping from block names to functions.
    block_to_function = {
        "credentials": lambda x, s: parse_type_block(x, sp=s),
        "compute-envs": lambda x, s: parse_type_block(x, sp=s),
        "actions": lambda x, s: parse_type_block(x, sp=s),
        "teams": parse_teams_block,
        "datasets": parse_datasets_block,
        "pipelines": lambda x, s: parse_pipelines_block(x, sp=s),
        "launch": parse_launch_block,
    }

    # Use the generic block function as a default.
    parse_fn = block_to_function.get(block_name, parse_generic_block)

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

    cmd_args = parse_fn(item, sp) if "lambda" in str(parse_fn) else parse_fn(item)

    return {"cmd_args": cmd_args, "on_exists": on_exists}


# Parsers for certain blocks of yaml that require handling
# for structuring command line arguments in a certain way


def parse_generic_block(item, sp=None):
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


def parse_type_block(item, priority_keys=["type", "config-mode", "file-path"], sp=None):
    cmd_args = []

    # Ensure at least one of 'type' or 'file-path' is present
    if not any(key in item for key in ["type", "file-path"]):
        raise ValueError(
            "Please specify at least 'type' or 'file-path' for creating the resource."
        )

    # Process priority keys first
    for key in priority_keys:
        if key in item and item[key] is not None:
            cmd_args.append(str(item[key]))
            del item[key]  # Remove the key to avoid repeating in args

    for key, value in item.items():
        # Skip None values
        if value is None:
            continue
        elif isinstance(value, bool):
            if value:
                cmd_args.append(f"--{key}")
        elif key == "params":
            temp_file_name = utils.create_temp_yaml(value)
            cmd_args.extend(["--params-file", temp_file_name])
        else:
            cmd_args.extend([f"--{key}", str(value)])
    return cmd_args


def parse_teams_block(item, sp=None):
    # Keys for each list
    cmd_keys = ["name", "organization", "description"]
    members_keys = ["name", "organization", "members"]

    cmd_args = []
    members_cmd_args = []

    for key, value in item.items():
        # Skip None values
        if value is None:
            continue
        if key in cmd_keys:
            cmd_args.extend([f"--{key}", str(value)])
        elif key in members_keys and key == "members":
            for member in value:
                members_cmd_args.append(
                    [
                        "--team",
                        str(item["name"]),
                        "--organization",
                        str(item["organization"]),
                        "add",
                        "--member",
                        str(member),
                    ]
                )
    return (cmd_args, members_cmd_args)


def parse_datasets_block(item, sp=None):
    cmd_args = []
    for key, value in item.items():
        # Skip None values
        if value is None:
            continue
        if key == "file-path":
            cmd_args.extend(
                [
                    str(item["file-path"]),
                    "--name",
                    str(item["name"]),
                    "--workspace",
                    str(item["workspace"]),
                    "--description",
                    str(item["description"]),
                ]
            )
        if key == "header" and value is True:
            cmd_args.append("--header")
    return cmd_args


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

        # Create temp file with params
        temp_file_name = utils.create_temp_yaml(
            params_dict, params_file=params_file_path
        )
        params_args.extend(["--params-file", temp_file_name])
    elif params_file_path:
        params_args.extend(["--params-file", params_file_path])

    return params_args


def parse_pipelines_block(item, sp=None):
    """Parse pipeline block."""
    cmd_args = []
    repo_args = []

    for key, value in item.items():
        # Skip None values
        if value is None:
            continue
        if key == "url":
            repo_args.extend([str(value)])
        elif key == "params":
            continue  # Handle params after the loop
        elif key == "file-path":
            repo_args.extend([str(value)])
        elif isinstance(value, bool):
            if value:
                cmd_args.append(f"--{key}")
        else:
            cmd_args.extend([f"--{key}", str(value)])

    params_args = process_params_dict(
        item.get("params"), workspace=item.get("workspace"), sp=sp
    )

    combined_args = cmd_args + repo_args + params_args
    return combined_args


def parse_launch_block(item, sp=None):
    """Parse launch block."""
    cmd_args = []
    repo_args = []

    for key, value in item.items():
        # Skip None values
        if value is None:
            continue
        if key == "pipeline" or key == "url":
            repo_args.extend([str(value)])
        elif key in ["params", "params-file"]:
            continue  # Handle params after the loop
        elif isinstance(value, bool):
            if value:
                cmd_args.append(f"--{key}")
        else:
            cmd_args.extend([f"--{key}", str(value)])

    params_args = process_params_dict(
        item.get("params"),
        workspace=item.get("workspace"),
        sp=sp,
        params_file_path=item.get("params-file"),
    )

    combined_args = cmd_args + repo_args + params_args
    return combined_args


# Handlers to call the actual sp method,based on the block name.
# Certain blocks required special handling and combination of methods.


def handle_generic_block(sp, block, args, method_name="add"):
    # Generic handler for most blocks, with optional method name
    method = getattr(sp, block)
    if method_name is None:
        method(*args)
    else:
        method(method_name, *args)


def handle_teams(sp, args):
    cmd_args, members_cmd_args = args
    sp.teams("add", *cmd_args)
    for sublist in members_cmd_args:
        sp.teams("members", *sublist)


def handle_participants(sp, args):
    # Generic handler for blocks with a key to skip
    method = getattr(sp, "participants")
    skip_key = "--role"
    new_args = [
        arg
        for i, arg in enumerate(args)
        if not (args[i - 1] == skip_key or arg == skip_key)
    ]
    method("add", *new_args)
    method("update", *args)


def handle_compute_envs(sp, args):
    json_file = any(".json" in arg for arg in args)
    method = getattr(sp, "compute_envs")

    # Check if primary flag is provided
    set_primary = "--primary" in args
    if set_primary:
        name = args[args.index("--name") + 1]
        workspace = args[args.index("--workspace") + 1]
        args = [arg for arg in args if arg != "--primary"]

    method("import" if json_file else "add", *args)

    if set_primary:
        method("primary", "set", "--name", name, "--workspace", workspace)


def handle_pipelines(sp, args):
    method = getattr(sp, "pipelines")
    for arg in args:
        # Check if arg is a url or a json file.
        # If it is, use the appropriate method and break.
        if utils.is_url(arg):
            method("add", *args)
            break
        elif ".json" in arg:
            method("import", *args)
            break
    else:  # No break occurred
        method("add", *args)


def handle_members(sp, args):
    method = getattr(sp, "members")

    # Check if role is specified in args
    has_role = "--role" in args
    role_value = None

    if has_role:
        role_index = args.index("--role")
        role_value = args[role_index + 1]
        args = [
            arg for i, arg in enumerate(args) if i != role_index and i != role_index + 1
        ]
    method("add", *args)

    # Then update with role if provided
    if has_role and role_value:
        method("update", *args, "--role", role_value)


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

    return search(cmd_args.get("cmd_args", []))
