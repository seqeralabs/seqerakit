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
Parser for actions resources.
"""

from seqerakit.resources._parsers import parse_type_based


def parse(item, sp=None):
    """
    Parse actions YAML block into CLI arguments.

    Actions require either 'type' or 'file-path' to be specified.

    Args:
        item: Dictionary from YAML block
        sp: SeqeraPlatform instance (optional)

    Returns:
        list: Command line arguments

    Raises:
        ValueError: If neither 'type' nor 'file-path' is present
    """
    return parse_type_based(item, sp=sp)
