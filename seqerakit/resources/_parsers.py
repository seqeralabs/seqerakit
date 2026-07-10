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
Shared parsing utilities for resource parsers.
"""

from seqerakit import utils


def parse_generic(item, sp=None):
    """
    Generic parser for simple key-value resources.

    Args:
        item: Dictionary from YAML block
        sp: SeqeraPlatform instance (optional, for consistency)

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


def parse_type_based(item, priority_keys=["type", "config-mode", "file-path"], sp=None):
    """
    Parser for resources that use type or file-path (credentials, compute-envs, actions).

    Args:
        item: Dictionary from YAML block
        priority_keys: Keys to process first in order
        sp: SeqeraPlatform instance (optional)

    Returns:
        list: Command line arguments

    Raises:
        ValueError: If neither 'type' nor 'file-path' is present
    """
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
