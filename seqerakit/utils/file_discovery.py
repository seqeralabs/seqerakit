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
File discovery utilities for locating YAML configuration files.
"""

import sys
from pathlib import Path


def find_yaml_files(path_list=None):
    """
    Find YAML files in the given path list.

    This function supports multiple input methods:
    - Individual YAML files
    - Directories (recursively searches for YAML files)
    - stdin (via "-" argument or when no arguments provided)

    Args:
        path_list (list, optional): A list of paths to search for YAML files.
            Can include files, directories, or "-" for stdin.

    Returns:
        list: A list of YAML file paths found in the given path list, or [stdin]
            if reading from standard input.

    Raises:
        ValueError: If no paths provided and stdin is a TTY (interactive terminal).
        FileExistsError: If a specified path does not exist.

    Examples:
        >>> find_yaml_files(["config.yaml"])
        ['config.yaml']

        >>> find_yaml_files(["configs/"])
        ['configs/org.yaml', 'configs/workspace.yaml']

        >>> find_yaml_files(["-"])
        [<stdin>]
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
