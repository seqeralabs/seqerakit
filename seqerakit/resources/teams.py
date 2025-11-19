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
Parser for teams resources.
"""


def parse(item, sp=None):
    """
    Parse teams YAML block into CLI arguments.

    Teams support a 'members' key that generates separate member addition commands.

    Args:
        item: Dictionary from YAML block
        sp: SeqeraPlatform instance (optional)

    Returns:
        tuple: (team_cmd_args, members_cmd_args_list)
            - team_cmd_args: List of arguments for team creation
            - members_cmd_args_list: List of argument lists for adding members
    """
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


def handle(sp, args):
    """
    Execute tw CLI commands for teams resource.

    Teams require two-phase execution:
    1. Create the team
    2. Add each member to the team

    Args:
        sp: SeqeraPlatform instance
        args: Tuple of (team_cmd_args, members_cmd_args_list)
    """
    cmd_args, members_cmd_args = args
    sp.teams("add", *cmd_args)
    for sublist in members_cmd_args:
        sp.teams("members", *sublist)
