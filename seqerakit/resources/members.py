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
Parser for members resources.
"""

from seqerakit.resources._parsers import parse_generic


def parse(item, sp=None):
    """
    Parse members YAML block into CLI arguments.

    Args:
        item: Dictionary from YAML block
        sp: SeqeraPlatform instance (optional)

    Returns:
        list: Command line arguments
    """
    return parse_generic(item, sp)


def handle(sp, args):
    """
    Execute tw CLI commands for members resource.

    Members require two-phase execution due to CLI limitation:
    1. Add member without --role flag
    2. Update member with --role flag

    Args:
        sp: SeqeraPlatform instance
        args: Command line arguments list
    """
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
