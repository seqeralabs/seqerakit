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
Block parser for routing YAML resource blocks to appropriate handlers.
"""

import logging

from seqerakit import seqeraplatform, overwrite
from seqerakit.on_exists import OnExists
from seqerakit.resources import HANDLERS, handle_generic

logger = logging.getLogger(__name__)


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

        # Get handler module for this resource type
        handler_module = HANDLERS.get(block)
        if handler_module and hasattr(handler_module, "handle"):
            handler_module.handle(self.sp, args["cmd_args"])
        else:
            # Fallback to generic handler for simple resources
            handle_generic(self.sp, block, args["cmd_args"])
