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
Parser for launch resources.
"""

from seqerakit.resources._parsers import process_params_dict


def parse(item, sp=None):
    """
    Parse launch YAML block into CLI arguments.

    Launch supports 'pipeline', 'url' for specifying what to run,
    and can include 'params' or 'params-file' for pipeline parameters.

    Args:
        item: Dictionary from YAML block
        sp: SeqeraPlatform instance (optional, used for dataset resolution)

    Returns:
        list: Command line arguments
    """
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


def handle(sp, args):
    """
    Execute tw CLI commands for launch resource.

    Launch uses direct method call without 'add' subcommand.

    Args:
        sp: SeqeraPlatform instance
        args: Command line arguments list
    """
    sp.launch(*args)
