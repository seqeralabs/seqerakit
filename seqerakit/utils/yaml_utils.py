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
YAML parsing utilities for seqerakit.
"""

import json
import sys
import yaml  # type: ignore


def load_and_merge_yaml_files(file_paths):
    """
    Load and merge multiple YAML files into a single dictionary.

    Args:
        file_paths: List of file paths to load. "-" represents stdin.

    Returns:
        dict: Merged YAML data from all files.

    Raises:
        ValueError: If YAML data is empty or invalid.
        FileNotFoundError: If a file is not found.
    """
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

    return merged_data


def filter_blocks_by_targets(block_names, targets):
    """
    Filter block names based on comma-separated target list.

    Args:
        block_names: List of block names to filter.
        targets: Comma-separated string of target block names.

    Returns:
        list: Filtered list of block names.
    """
    if not targets:
        return block_names

    target_blocks = set(targets.split(","))
    return [block for block in block_names if block in target_blocks]


def get_resource_order(destroy=False):
    """
    Get the order in which resources should be processed.

    Args:
        destroy: If True, returns reverse order for deletion.

    Returns:
        list: Ordered list of resource type names.
    """
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

    return resource_order
