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
Parser for compute-envs resources.
"""

from seqerakit.resources._parsers import parse_type_based


def parse(item, sp=None):
    """
    Parse compute-envs YAML block into CLI arguments.

    Compute environments require either 'type' or 'file-path' to be specified.

    Args:
        item: Dictionary from YAML block
        sp: SeqeraPlatform instance (optional)

    Returns:
        list: Command line arguments

    Raises:
        ValueError: If neither 'type' nor 'file-path' is present
    """
    return parse_type_based(item, sp=sp)


def handle(sp, args):
    """
    Execute tw CLI commands for compute-envs resource.

    Compute environments support:
    1. JSON file import: Uses 'import' method instead of 'add'
    2. Custom --primary flag: Sets compute env as primary after creation

    Args:
        sp: SeqeraPlatform instance
        args: Command line arguments list
    """
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
