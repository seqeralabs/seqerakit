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

from contextlib import contextmanager
import os
import shlex
import logging
import subprocess
import re
import json


class SeqeraPlatform:
    """
    A Python class that serves as a wrapper for 'tw' CLI commands. # TODO update

    The class enables the execution of 'tw' commands in an object-oriented manner.
    You can call any subcommand of 'tw' as a method on instances of this class.
    The arguments of the subcommand can be passed as arguments to the method.

    Each command is run in a subprocess, with the output being captured and returned.
    """

    class TwCommand:
        def __init__(self, tw_instance, cmd):
            self.tw_instance = tw_instance
            self.cmd = cmd

        def __call__(self, *args, **kwargs):
            command = self.cmd.split()
            command.extend(args)
            return self.tw_instance._tw_run(command, **kwargs)

    # Constructs a new SeqeraPlatform instance
    def __init__(self, cli_args=None, dryrun=False, print_stdout=True, json=False):
        if cli_args and "--verbose" in cli_args:
            raise ValueError(
                "--verbose is not supported as a CLI argument to seqerakit."
            )
        self.cli_args = cli_args or []
        self.dryrun = dryrun
        self.print_stdout = print_stdout
        self.json = json
        self._suppress_output = False

    def _construct_command(self, cmd, *args, **kwargs):
        command = ["tw"] + self.cli_args

        if self.json:
            command.extend(["-o", "json"])

        command.extend(cmd)
        command.extend(args)

        if kwargs.get("config"):
            command.append(f"--config={kwargs['config']}")

        if "params_file" in kwargs:
            command.append(f"--params-file={kwargs['params_file']}")

        # Filter out empty arguments
        command = self._check_empty_args(command)

        return self._check_env_vars(command)

    def _check_empty_args(self, command):
        filtered_command = []
        i = 0
        while i < len(command):
            current_arg = command[i]

            # Check if this is a parameter (starts with --) and has a value after it
            if i < len(command) - 1 and current_arg.startswith("--"):
                next_arg = command[i + 1]

                # If the next argument is None or an empty string
                # skip both the parameter and its value
                if next_arg is None or (
                    isinstance(next_arg, str) and next_arg.strip() == ""
                ):
                    i += 2  # Skip both the parameter and its empty value
                    continue
                else:
                    # Keep both the parameter and its non-empty value
                    filtered_command.append(current_arg)
                    filtered_command.append(next_arg)
                    i += 2
            else:
                # Not a parameter-value pair, just add it to the filtered command
                filtered_command.append(current_arg)
                i += 1

        return filtered_command

    # Checks environment variables to see that they are set accordingly
    def _check_env_vars(self, command):
        full_cmd_parts = []
        shell_constructs = {"|", ">", "<", "$(", "&", "&&", "`"}
        special_vars = {"$TW_AGENT_WORK"}

        # Define the patterns and extraction methods for variable types
        env_var_patterns = {
            "powershell": (r"\$env:[\w]+", lambda var: var.replace("$env:", "")),
            "windows": (r"%[\w]+%", lambda var: var.strip("%")),
            "unix": (r"\$\{[\w]+\}|\$[^e][\w]*", lambda var: re.sub(r"[${}]", "", var)),
        }

        for arg in command:
            # Handle special variables that should be escaped not interpolated to bash
            if arg in special_vars:
                full_cmd_parts.append(f'"\\\\\\${arg.lstrip("$")}"')
                continue

            # Skip interpolation for explicitly escaped vars
            if arg.startswith("\\") or (arg.startswith("'") and arg.endswith("'")):
                full_cmd_parts.append(arg.lstrip("\\").strip("'"))
                continue

            if any(construct in arg for construct in shell_constructs):
                full_cmd_parts.append(arg)
                continue

            # Finally, handle environment var interpolation
            if "$" in arg or "%" in arg:
                processed_arg = arg

                for pattern, extractor in env_var_patterns.values():
                    for env_var in re.findall(pattern, arg):
                        var_name = extractor(env_var)

                        # Check variable exists
                        if var_name not in os.environ:
                            raise EnvironmentError(
                                f"Environment variable {env_var} not found!"
                            )

                full_cmd_parts.append(processed_arg)
                continue

            full_cmd_parts.append(shlex.quote(arg))

        return " ".join(full_cmd_parts)

    # Executes a 'tw' command in a subprocess and returns the output.
    def _execute_command(self, full_cmd, to_json=False, print_stdout=True):
        logging.info(f" Running command: {full_cmd}")
        process = subprocess.Popen(
            full_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True
        )
        stdout, _ = process.communicate()
        stdout = stdout.decode("utf-8").strip()

        should_print = (
            print_stdout if print_stdout is not None else self.print_stdout
        ) and not self._suppress_output

        # Do not print output in logging if self.json is enabled
        if should_print and not self.json:
            logging.info(f" Command output: {stdout}")

        # Try JSON parsing first
        if self.json or to_json:
            try:
                out = json.loads(stdout)
                if should_print:
                    print(json.dumps(out))
                return out
            except json.JSONDecodeError:
                pass

        if process.returncode != 0:
            self._handle_command_errors(stdout)

        if should_print:
            print(stdout)
        return stdout

    def _handle_command_errors(self, stdout):
        # Check for specific tw cli error patterns and raise custom exceptions
        if re.search(
            r"ERROR: .*already (exists|a participant)", stdout, flags=re.IGNORECASE
        ):
            raise ResourceExistsError(
                "Resource already exists. Please delete first or set 'overwrite: true'"
            )
        elif re.search(r"ERROR: .*not found", stdout, flags=re.IGNORECASE):
            raise ResourceNotFoundError(f"Resource not found: '{stdout}'")
        else:
            raise CommandError(
                f"Command failed: '{stdout}'. Check your input and try again."
            )

    def _tw_run(self, cmd, *args, **kwargs):
        print_stdout = kwargs.pop("print_stdout", None)
        full_cmd = self._construct_command(cmd, *args, **kwargs)
        if not full_cmd or self.dryrun:
            logging.info(f"DRYRUN: Running command {full_cmd}")
            return None
        return self._execute_command(full_cmd, kwargs.get("to_json"), print_stdout)

    @contextmanager
    def suppress_output(self):
        original_suppress = self._suppress_output
        self._suppress_output = True
        try:
            yield
        finally:
            self._suppress_output = original_suppress

    # Allow any 'tw' subcommand to be called as a method.
    def __getattr__(self, cmd):
        if cmd == "info":
            return lambda *args, **kwargs: self._tw_run(
                ["info"], *args, **kwargs, print_stdout=False
            )
        if cmd == "-o json":
            return lambda *args, **kwargs: self._tw_run(
                ["-o", "json"] + list(args), **kwargs
            )
        return self.TwCommand(self, cmd.replace("_", "-"))


class CommandError(Exception):
    pass


class ResourceExistsError(Exception):
    pass


class ResourceNotFoundError(Exception):
    pass
