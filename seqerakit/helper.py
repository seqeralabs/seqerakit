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

from seqerakit import utils
from seqerakit.on_exists import OnExists
from seqerakit.resources import PARSERS

# Re-exports for backward compatibility
from seqerakit.core.yaml_processor import (
    parse_all_yaml,
    parse_yaml_block,
    parse_block,
    parse_generic_block,
    find_name,
    RESOURCE_ORDER,
)

__all__ = [
    "parse_all_yaml",
    "parse_yaml_block",
    "parse_block",
    "parse_generic_block",
    "find_name",
    "RESOURCE_ORDER",
    "utils",
    "PARSERS",
    "OnExists",
]


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
        elif key in ["params", "params-file"]:
            continue  # Handle params after the loop
        elif key == "file-path":
            repo_args.extend([str(value)])
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
