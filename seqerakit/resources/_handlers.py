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
Shared handler utilities for resource execution.
"""


def handle_generic(sp, block, args, method_name="add"):
    """
    Generic handler for simple resources.

    Args:
        sp: SeqeraPlatform instance
        block: Resource block name (e.g., 'organizations', 'workspaces')
        args: Command line arguments
        method_name: Method to call on the resource (default: 'add')

    Examples:
        handle_generic(sp, 'organizations', ['--name', 'myorg'])
        # Executes: tw organizations add --name myorg

        handle_generic(sp, 'launch', ['pipeline', '--workspace', 'ws'], method_name=None)
        # Executes: tw launch pipeline --workspace ws
    """
    method = getattr(sp, block)
    if method_name is None:
        method(*args)
    else:
        method(method_name, *args)
