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
Subclass of SeqeraPlatform class for overriding compute environments subcommand methods.
"""

from pathlib import Path
from seqerakit.seqeraplatform import SeqeraPlatform


class ComputeEnvs(SeqeraPlatform):
    """
    Python wrapper for tw compute-envs export command.
    """

    def export_ce(self, name, *args, **kwargs):
        """
        Export a compute environment
        """
        # create a Path object for the workspace directory
        workspace_dir = Path(self.workspace)

        # create the directory if it doesn't exist
        workspace_dir.mkdir(parents=True, exist_ok=True)

        # define the output file path
        outfile = workspace_dir / f"{name}.json"

        # Build the command
        command = [
            "compute-envs",
            "export",
            "--workspace",
            self.workspace,
            "--name",
            name,
            str(outfile),
        ]

        # Pass the built command to the base class method in SeqeraPlatform
        return self._tw_run(command, *args, **kwargs)
