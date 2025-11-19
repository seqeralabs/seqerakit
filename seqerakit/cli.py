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
This script is used to build a Seqera Platform instance from a YAML configuration file.
Requires a YAML file that defines the resources to be created in Seqera Platform and
the required options for each resource based on the Seqera Platform CLI.
"""

import logging
import sys
import os
from enum import Enum
from typing import Optional, List
from pathlib import Path

import typer

from seqerakit import seqeraplatform, helper, overwrite
from seqerakit.seqeraplatform import (
    ResourceExistsError,
    ResourceNotFoundError,
    CommandError,
)
from seqerakit import __version__
from seqerakit.on_exists import OnExists

logger = logging.getLogger(__name__)


class LogLevel(str, Enum):
    """Logging level options."""

    CRITICAL = "CRITICAL"
    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"
    DEBUG = "DEBUG"


# Create Typer app
app = typer.Typer(
    help="Create resources on Seqera Platform using a YAML configuration file.",
    add_completion=False,
)


def version_callback(value: bool):
    """Display version and exit."""
    if value:
        typer.echo(f"seqerakit {__version__}")
        raise typer.Exit()


class BlockParser:
    """
    Manages blocks of commands defined in a configuration file and calls appropriate
    functions for each block for custom handling of command-line arguments to _tw_run().
    """

    def __init__(self, sp, list_for_add_method):
        """
        Initializes a BlockParser instance.

        Args:
        sp: A Seqera Platform class instance.
        list_for_add_method: A list of blocks that need to be
        handled by the 'add' method.
        """
        self.sp = sp
        self.list_for_add_method = list_for_add_method

        # Create a separate Seqera Platform client instance for overwrite operations.
        # Remove --verbose from cli_args for overwrite operations to avoid JSON parsing conflicts
        overwrite_cli_args = [arg for arg in sp.cli_args if arg != "--verbose"]
        sp_for_overwrite = seqeraplatform.SeqeraPlatform(
            cli_args=overwrite_cli_args,
            dryrun=sp.dryrun,
            json=False,  # Overwrite operations use explicit -o json
        )
        self.overwrite_method = overwrite.Overwrite(sp_for_overwrite)

    def handle_block(self, block, args, destroy=False, dryrun=False):
        # Check if delete is set to True, and call delete handler
        if destroy:
            logging.debug(" The '--delete' flag has been specified.\n")
            self.overwrite_method.handle_overwrite(
                block, args["cmd_args"], on_exists=OnExists.FAIL, destroy=True
            )
            return

        # Handles a block of commands by calling the appropriate function.
        block_handler_map = {
            "teams": (helper.handle_teams),
            "members": (helper.handle_members),
            "participants": (helper.handle_participants),
            "compute-envs": (helper.handle_compute_envs),
            "pipelines": (helper.handle_pipelines),
            "launch": lambda sp, args: helper.handle_generic_block(
                sp, "launch", args, method_name=None
            ),
        }

        # Determine the on_exists behavior (default to FAIL)
        on_exists = OnExists.FAIL

        # Check for global settings (they override block-level settings)
        if (
            hasattr(self.sp, "global_on_exists")
            and self.sp.global_on_exists is not None
        ):
            on_exists = self.sp.global_on_exists
        elif getattr(self.sp, "overwrite", False):
            logging.warning(
                "The '--overwrite' flag is deprecated. "
                "Please use '--on-exists=overwrite' instead."
            )
            on_exists = OnExists.OVERWRITE

        # If no global setting, use block-level setting if provided
        elif "on_exists" in args:
            on_exists_value = args["on_exists"]
            if isinstance(on_exists_value, OnExists):
                on_exists = on_exists_value
            elif isinstance(on_exists_value, str):
                try:
                    on_exists = OnExists[on_exists_value.upper()]
                except KeyError as err:
                    logging.error(f"Invalid on_exists option: {on_exists_value}")
                    raise err

        if not dryrun:
            # Use on_exists.name.lower() only if it's an enum, otherwise use the string
            on_exists_str = (
                on_exists.name.lower() if hasattr(on_exists, "name") else on_exists
            )
            logging.debug(f" on_exists is set to '{on_exists_str}' for {block}\n")
            should_continue = self.overwrite_method.handle_overwrite(
                block, args["cmd_args"], on_exists=on_exists
            )

            # If on_exists is "ignore" and resource exists, skip creation
            if not should_continue:
                return

        if block in self.list_for_add_method:
            helper.handle_generic_block(self.sp, block, args["cmd_args"])
        elif block in block_handler_map:
            block_handler_map[block](self.sp, args["cmd_args"])
        else:
            logger.error(f"Unrecognized resource block in YAML: {block}")


def find_yaml_files(path_list=None):
    """
    Find YAML files in the given path list.

    Args:
        path_list (list, optional): A list of paths to search for YAML files.

    Returns:
        list: A list of YAML files found in the given path list or stdin.
    """

    yaml_files = []
    yaml_exts = ["**/*.[yY][aA][mM][lL]", "**/*.[yY][mM][lL]"]

    if not path_list:
        if sys.stdin.isatty():
            raise ValueError(
                "No YAML(s) provided and no input from stdin. Please provide at least "
                "one YAML configuration file or pipe input from stdin."
            )
        return [sys.stdin]

    for path in path_list:
        if path == "-":
            yaml_files.append(path)
            continue

        path = Path(path)
        if not path.exists():
            raise FileExistsError(f"File {path} does not exist")

        if path.is_file():
            yaml_files.append(str(path))
        elif path.is_dir():
            for ext in yaml_exts:
                yaml_files.extend(str(p) for p in path.rglob(ext))
        else:
            yaml_files.append(str(path))

    return yaml_files


@app.command()
def main(
    yaml: Optional[List[str]] = typer.Argument(
        None,
        help="One or more YAML files with Seqera Platform resource definitions.",
    ),
    log_level: LogLevel = typer.Option(
        LogLevel.INFO,
        "--log-level",
        "-l",
        help="Set the logging level.",
        case_sensitive=False,
    ),
    info: bool = typer.Option(
        False,
        "--info",
        "-i",
        help="Display Seqera Platform information and exit.",
    ),
    json: bool = typer.Option(
        False,
        "--json",
        "-j",
        help="Output JSON format in stdout.",
    ),
    dryrun: bool = typer.Option(
        False,
        "--dryrun",
        "-d",
        help="Print the commands that would be executed.",
    ),
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        "-v",
        callback=version_callback,
        is_eager=True,
        help="Show version number and exit.",
    ),
    delete: bool = typer.Option(
        False,
        "--delete",
        help="Recursively delete resources defined in the YAML files.",
    ),
    cli_args: Optional[List[str]] = typer.Option(
        None,
        "--cli",
        help="Additional Seqera Platform CLI specific options to be passed, "
        "enclosed in double quotes (e.g. '--cli=\"--insecure\"'). Can be specified multiple times.",
    ),
    targets: Optional[str] = typer.Option(
        None,
        "--targets",
        help="Specify the resources to be targeted for creation in a YAML file through "
        "a comma-separated list (e.g. '--targets=teams,participants').",
    ),
    env_file: Optional[str] = typer.Option(
        None,
        "--env-file",
        help="Path to a YAML file containing environment variables for configuration.",
    ),
    on_exists: Optional[str] = typer.Option(
        None,
        "--on-exists",
        help="Globally specifies the action to take if a resource already exists.",
    ),
    overwrite: bool = typer.Option(
        False,
        "--overwrite",
        help="Globally enable overwrite for all resources defined in YAML input(s). "
        "Deprecated: Please use '--on-exists=overwrite' instead.",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        help="Enable verbose output for Seqera Platform CLI.",
    ),
):
    """Create resources on Seqera Platform using a YAML configuration file."""
    logging.basicConfig(level=getattr(logging, log_level.value.upper()))

    # Parse CLI arguments into a list
    cli_args_list = []
    if cli_args:
        for cli_arg in cli_args:
            cli_args_list.extend(cli_arg.split())

    # Add --verbose flag if specified
    if verbose:
        cli_args_list.append("--verbose")

    # Merge environment variables from env_file with existing ones
    # Will prioritize env_file values
    if env_file:
        with open(env_file, "r") as f:
            env_vars = yaml.safe_load(f)
            # Only update environment variables that are explicitly defined in env_file
            for key, value in env_vars.items():
                if value is not None:
                    full_value = os.path.expandvars(str(value))
                    os.environ[key] = full_value

    sp = seqeraplatform.SeqeraPlatform(cli_args=cli_args_list, dryrun=dryrun, json=json)
    sp.overwrite = overwrite  # If global overwrite is set

    # Validate on_exists parameter
    if on_exists:
        try:
            sp.global_on_exists = OnExists[on_exists.upper()]
        except KeyError:
            valid_options = [e.name.lower() for e in OnExists]
            logging.error(
                f"Invalid on_exists option: {on_exists}. "
                f"Valid options are: {', '.join(valid_options)}"
            )
            raise typer.Exit(code=1)
    else:
        sp.global_on_exists = None

    # If the info flag is set, run 'tw info'
    try:
        if info:
            result = sp.info()
            if not dryrun:
                print(result)
            return
    except CommandError as e:
        logging.error(e)
        raise typer.Exit(code=1)

    yaml_files = find_yaml_files(yaml)

    block_manager = BlockParser(
        sp,
        [
            "organizations",  # all use method.add
            "workspaces",
            "labels",
            "credentials",
            "secrets",
            "actions",
            "datasets",
            "studios",
            "data-links",
        ],
    )

    # Parse the YAML file(s) by blocks
    # and get a dictionary of command line arguments
    try:
        cmd_args_dict = helper.parse_all_yaml(
            yaml_files, destroy=delete, targets=targets, sp=sp
        )
        for block, args_list in cmd_args_dict.items():
            for args in args_list:
                block_manager.handle_block(block, args, destroy=delete, dryrun=dryrun)
    except (ResourceExistsError, ResourceNotFoundError, CommandError, ValueError) as e:
        logging.error(e)
        raise typer.Exit(code=1)


def run():
    """Entry point for the CLI application."""
    app()


if __name__ == "__main__":
    run()
