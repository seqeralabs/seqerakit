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
import os
from enum import Enum
from typing import Optional, List

import typer

from seqerakit import seqeraplatform, helper
from seqerakit.seqeraplatform import (
    ResourceExistsError,
    ResourceNotFoundError,
    CommandError,
)
from seqerakit import __version__
from seqerakit.on_exists import OnExists
from seqerakit.core.block_parser import BlockParser
from seqerakit.utils.file_discovery import find_yaml_files

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
