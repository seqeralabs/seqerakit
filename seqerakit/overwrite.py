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

import json
from seqerakit import utils
from seqerakit.seqeraplatform import ResourceExistsError
from seqerakit.on_exists import OnExists
import logging


class Overwrite:
    """
    Manages overwrite functionality for Seqera Platform resources.

    # TODO: When overwrite functionality becomes native to CLI,
    we can remove this class.
    """

    # Define blocks for simple overwrite with --name and --workspace
    generic_deletion = [
        "credentials",
        "secrets",
        "compute-envs",
        "datasets",
        "actions",
        "pipelines",
        "studios",
    ]

    # Define valid on_exists options as enum values
    VALID_ON_EXISTS_OPTIONS = [e.name.lower() for e in OnExists]

    def __init__(self, sp):
        """
        Initializes an Overwrite instance.

        Args:
        sp: A SeqeraPlatform class instance.

        Attributes:
        sp: A SeqeraPlatform class instance used to execute CLI commands.
        cached_jsondata: A cached placeholder for JSON data. Default value is None.
        block_jsondata: A dictionary to store JSON data for each block.
        Key is the block name, and value is the corresponding JSON data.
        """
        self.sp = sp
        self.cached_jsondata = None
        self.block_jsondata = {}  # New dict to hold JSON data per block

        # Define special handlers for resources deleted with specific args
        self.block_operations = {
            "organizations": {
                "keys": ["name"],
                "method_args": self._get_organization_args,
                "name_key": "orgName",
            },
            "labels": {
                "keys": ["name", "value", "workspace"],
                "method_args": lambda args: self._get_id_resource_args("labels", args),
                "name_key": "name",
            },
            "members": {
                "keys": ["user", "organization"],
                "method_args": self._get_members_args,
                "name_key": "email",
            },
            "teams": {
                "keys": ["name", "organization"],
                "method_args": self._get_team_args,
                "name_key": "name",
            },
            "participants": {
                "keys": ["name", "type", "workspace"],
                "method_args": self._get_participant_args,
                "name_key": "email",
            },
            "workspaces": {
                "keys": ["name", "organization"],
                "method_args": self._get_workspace_args,
                "name_key": "workspaceName",
            },
            "data-links": {
                "keys": ["name", "workspace"],
                "method_args": lambda args: self._get_id_resource_args(
                    "data-links", args
                ),
                "name_key": "name",
            },
        }

        # Initialize the generic deletion handlers upfront
        for block in self.generic_deletion:
            self.block_operations[block] = {
                "keys": ["name", "workspace"],
                "method_args": self._get_generic_deletion_args,
                "name_key": "name",
            }

    def handle_overwrite(
        self, block, args, on_exists=OnExists.FAIL, destroy=False, overwrite=None
    ):
        """
        Handles resource existence behavior for Seqera Platform resources.

        Args:
            block: The resource block type (e.g., "organizations", "teams")
            args: Command line arguments for the resource
            on_exists: How to handle existing resources. Options:
                - OnExists.FAIL (default): Raise an error if resource exists
                - OnExists.IGNORE: Skip creation if resource exists
                - OnExists.OVERWRITE: Delete existing resource and create new one
            destroy: Whether to delete the resource
            overwrite: Legacy parameter for backward compatibility
        """
        # Convert string to enum if needed
        if isinstance(on_exists, str):
            try:
                on_exists = OnExists[on_exists.upper()]
            except KeyError:
                raise ValueError(
                    f"Invalid on_exists option: {on_exists}. "
                    f"Valid options are: {', '.join(self.VALID_ON_EXISTS_OPTIONS)}"
                )

        # For backward compatibility
        if overwrite is not None:
            on_exists = OnExists.OVERWRITE if overwrite else OnExists.FAIL

        if block in self.block_operations:
            operation = self.block_operations[block]
            keys_to_get = operation["keys"]
            self.cached_jsondata, sp_args = self._get_json_data(
                block, args, keys_to_get
            )

            if block == "participants":
                if sp_args.get("type") == "TEAM":
                    self.block_operations["participants"]["name_key"] = "teamName"
                else:
                    self.block_operations["participants"]["name_key"] = "email"
            elif block == "members":
                # Rename the user key to name to correctly index JSON data
                sp_args["name"] = sp_args.pop("user")

            if self.check_resource_exists(operation["name_key"], sp_args):
                # Handle based on on_exists parameter
                if on_exists == OnExists.OVERWRITE:
                    logging.info(
                        f" The attempted {block} resource already exists."
                        " Overwriting.\n"
                    )
                    self.delete_resource(block, operation, sp_args)
                elif on_exists == OnExists.IGNORE:
                    logging.info(
                        f" The {block} resource already exists." " Skipping creation.\n"
                    )
                    return False
                elif destroy:
                    logging.info(f" Deleting the {block} resource.")
                    self.delete_resource(block, operation, sp_args)
                else:  # fail
                    raise ResourceExistsError(
                        f"The {block} resource already exists and "
                        "will not be created. Please set 'on_exists: overwrite' "
                        "to replace the resource or set 'on_exists: ignore' to "
                        "ignore this error.\n"
                    )
            return True
        return True

    def _get_organization_args(self, args):
        """
        Returns a list of arguments for the delete() method for organizations.
        """
        return ("delete", "--name", args["name"])

    def _get_team_args(self, args):
        """
        Returns a list of arguments for the delete() method for teams. The teamId
        used to delete will be retrieved using the find_key_value_in_dict() method.
        """
        jsondata = self.block_jsondata.get("teams", None)

        if not jsondata:
            json_method = getattr(self.sp, "-o json")
            with self.sp.suppress_output():
                json_out = json_method("teams", "list", "-o", args["organization"])
            self.block_jsondata["teams"] = json_out
        else:
            json_out = jsondata

        # Get the teamId from the json data
        team_id = utils.find_key_value_in_dict(
            json.loads(json_out), "name", utils.resolve_env_var(args["name"]), "teamId"
        )
        return ("delete", "--id", str(team_id), "--organization", args["organization"])

    def _get_members_args(self, args):
        """
        Returns a list of arguments for the delete() method for members.
        """
        return (
            "delete",
            "--user",
            args["name"],
            "--organization",
            args["organization"],
        )

    def _get_participant_args(self, args):
        """
        Returns a list of arguments for the delete() method for participants.
        Works for both teams and members where if the type is TEAM, the teamName
        is used to delete, and if the type is MEMBER, the email is used to delete.
        """
        method_args = (
            "delete",
            "--name",
            args["name"],
            "--type",
            args["type"],
            "--workspace",
            args["workspace"],
        )
        return method_args

    def _get_workspace_args(self, args):
        """
        Returns a list of arguments for the delete() method for workspaces. The
        workspaceId used to delete will be retrieved using the _find_workspace_id()
        method.
        """
        workspace_id = self._find_workspace_id(args["organization"], args["name"])
        return ("delete", "--id", str(workspace_id))

    def _get_id_resource_args(self, resource_type, args):
        """
        Returns a list of arguments for the delete() method for labels. The
        label_id used to delete will be retrieved using the _find_id() method.
        """
        if resource_type == "labels":
            resource_id = self._find_id(resource_type, args["name"], args["value"])
        else:  # data-links
            resource_id = self._find_id(resource_type, args["name"])

        return ("delete", "--id", str(resource_id), "-w", args["workspace"])

    def _get_generic_deletion_args(self, args):
        """
        Returns a list of arguments for the delete() method for resources that
        are deleted with --name and --workspace.
        """
        return (
            "delete",
            "--name",
            args["name"],
            "--workspace",
            args["workspace"],
        )

    def _get_json_data(self, block, args, keys_to_get):
        """
        For the specified keys in the operations dictionary, get the values from
        the command line arguments and return a dictionary of values.

        Also, gets json data from Seqera Platform by calling the list() method
        once and caches the json data for that block in self.block_jsondata.
        If the block data already exists, it will be retrieved from the dictionary
        instead of calling the list().

        Returns a tuple of json data and a dictionary of values to run delete() on.
        """
        json_method = getattr(self.sp, "-o json")
        sp_args = []  # Default value for sp_args

        # Get values from args
        if block == "teams":
            sp_args = self._get_values_from_cmd_args(args[0], keys_to_get)
        else:
            sp_args = self._get_values_from_cmd_args(args, keys_to_get)

        # Generate cache key including workspace/organization
        cache_key = block
        if block in Overwrite.generic_deletion or block in {
            "participants",
            "labels",
            "data-links",
        }:
            if sp_args.get("workspace"):
                cache_key = f"{block}:{sp_args['workspace']}"
        elif block in {"members", "workspaces", "teams"}:
            if sp_args.get("organization"):
                cache_key = f"{block}:{sp_args['organization']}"

        # Check if block data already exists in cache
        if cache_key in self.block_jsondata:
            self.cached_jsondata = self.block_jsondata[cache_key]
        else:
            # Fetch the data if it does not exist
            if block == "teams":
                with self.sp.suppress_output():
                    self.cached_jsondata = json_method(
                        block, "list", "-o", sp_args["organization"]
                    )
            elif block in Overwrite.generic_deletion or block in {
                "participants",
                "labels",
                "data-links",
            }:
                with self.sp.suppress_output():
                    self.cached_jsondata = json_method(
                        block, "list", "-w", sp_args["workspace"]
                    )
            elif block == "members" or block == "workspaces":
                with self.sp.suppress_output():
                    self.cached_jsondata = json_method(
                        block, "list", "-o", sp_args["organization"]
                    )
            else:
                with self.sp.suppress_output():
                    self.cached_jsondata = json_method(block, "list")

            # Store data with the proper cache key
            self.block_jsondata[cache_key] = self.cached_jsondata

        return self.cached_jsondata, sp_args

    def check_resource_exists(self, name_key, sp_args):
        """
        Check if a resource exists in Seqera Platform by looking for the name and value
        in the json data generated from the list() method.
        """
        return utils.check_if_exists(
            self.cached_jsondata, name_key, utils.resolve_env_var(sp_args["name"])
        )

    def delete_resource(self, block, operation, sp_args):
        """
        Delete a resource in Seqera Platform by calling the delete() method and
        arguments defined in the operation dictionary.
        """
        method_args = operation["method_args"](sp_args)
        method = getattr(self.sp, block)
        method(*method_args)

    def _get_values_from_cmd_args(self, cmd_args, keys):
        """
        Return a dictionary of values from a list of command line arguments based
        on a input list of keys.
        """
        values = {key: None for key in keys}
        key = None

        for arg in cmd_args:
            if arg.startswith("--"):
                key = arg[2:]
            else:
                if key and key in keys:
                    values[key] = arg
                key = None
        return values

    def _find_workspace_id(self, organization, workspace_name):
        """
        Custom method to find a workspace ID in a nested dictionary with a given
        organization name and workspace name. This ID will be used to delete the
        workspace.
        """
        jsondata = json.loads(self.cached_jsondata)
        workspaces = jsondata["workspaces"]

        for workspace in workspaces:
            if workspace.get("orgName") == utils.resolve_env_var(
                organization
            ) and workspace.get("workspaceName") == utils.resolve_env_var(
                workspace_name
            ):
                workspace_id = workspace.get("workspaceId")
                return workspace_id
        return None

    def _find_id(self, resource_type, name, value=None):
        """
        Finds the unique identifier (ID) for a Seqera Platform resource by searching
        through the cached JSON data. This method is necessary because certain Platform
        resources must be deleted using their ID rather than their name.

        Args:
            resource_type (str): Type of resource to search for. Currently supports:
                - 'labels': Platform labels that require both name and value matching
                - 'data-links': Data link resources that only require name matching
            name (str): Name of the resource to find
            value (str, optional): For labels only, the value field that must match
                along with the name. Defaults to None for non-label resources.

        Returns:
            str: The unique identifier (ID) of the matching resource if found
            None: If no matching resource is found

        Note:
            - For labels, both name and value must match to find the correct ID
            - For data-links, only the name needs to match
            - The method uses cached JSON data from previous API calls to avoid
              redundant requests to the Platform
        """
        jsondata = json.loads(self.cached_jsondata)
        json_key = "dataLinks" if resource_type == "data-links" else resource_type
        resources = jsondata[json_key]

        for resource in resources:
            if resource_type == "labels":
                if resource.get("name") == utils.resolve_env_var(name) and resource.get(
                    "value"
                ) == utils.resolve_env_var(value):
                    return resource.get("id")
            elif resource_type == "data-links":
                if resource.get("name") == utils.resolve_env_var(name):
                    return resource.get("id")
        return None
