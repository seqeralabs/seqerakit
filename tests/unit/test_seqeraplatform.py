import unittest
from unittest.mock import MagicMock, patch
from seqerakit import seqeraplatform
from seqerakit.seqeraplatform import CommandError
import json
import subprocess
import os
import logging
from io import StringIO


class TestSeqeraPlatform(unittest.TestCase):
    def setUp(self):
        self.sp = seqeraplatform.SeqeraPlatform(json=True)

    @patch("subprocess.Popen")
    def test_run_with_jsonout_command(self, mock_subprocess):
        mock_pipelines_json = {
            "id": "5lWcpupLHnHkq9fM5JYaOn",
            "computeEnvId": "403VpC7AetAmj42MnMOAwJ",
            "pipeline": "https://github.com/nextflow-io/hello",
            "workDir": "s3://myworkdir/test",
            "revision": "",
            "configText": "",
            "paramsText": "",
            "resume": "false",
            "pullLatest": "false",
            "stubRun": "false",
            "dateCreated": "2023-02-15T13:14:30Z",
        }
        # Mock the stdout of the Popen process
        mock_subprocess.return_value = MagicMock(returncode=0)
        mock_subprocess.return_value.communicate.return_value = (
            json.dumps(mock_pipelines_json).encode(),
            b"",
        )

        # Dynamically get the pipelines command
        command = getattr(self.sp, "pipelines")

        # Run the command with arguments
        result = command("view", "--name", "pipeline_name")

        # Check that Popen was called with the right arguments
        mock_subprocess.assert_called_once_with(
            "tw -o json pipelines view --name pipeline_name",
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            shell=True,
        )

        # Check that the output was decoded correctly
        self.assertEqual(result, mock_pipelines_json)

    def test_resource_exists_error(self):
        with patch("subprocess.Popen") as mock_subprocess:
            # Simulate a 'resource already exists' error
            mock_subprocess.return_value.communicate.return_value = (
                b"ERROR: Resource already exists",
                b"",
            )

            command = getattr(self.sp, "pipelines")

            # Check that the error is raised
            with self.assertRaises(seqeraplatform.ResourceExistsError):
                command("arg1", "arg2")

    def test_resource_exists_error_alt_error(self):
        with patch("subprocess.Popen") as mock_subprocess:
            # Simulate a 'resource already exists' error
            mock_subprocess.return_value.communicate.return_value = (
                b"ERROR: Already a participant",
                b"",
            )

            command = getattr(self.sp, "pipelines")

            # Check that the error is raised
            with self.assertRaises(seqeraplatform.ResourceExistsError):
                command("arg1", "arg2")

    def test_resource_creation_error(self):
        with patch("subprocess.Popen") as mock_subprocess:
            # Simulate a 'resource creation failed' error
            mock_subprocess.return_value.communicate.return_value = (
                b"ERROR: Resource creation failed",
                b"",
            )

            command = getattr(self.sp, "pipelines")

            # Check that the error is raised
            with self.assertRaises(seqeraplatform.CommandError):
                command("import", "my_pipeline.json", "--name", "pipeline_name")

    def test_empty_string_argument(self):
        command = ["--profile", " ", "--config", "my_config"]
        parsed_command = self.sp._check_empty_args(command)
        self.assertEqual(parsed_command, ["--config", "my_config"])

    def test_no_empty_string_argument(self):
        command = ["--profile", "test_profile", "--config", "my_config"]
        try:
            self.sp._check_empty_args(command)
        except ValueError:
            self.fail("_check_empty_args() raised ValueError unexpectedly!")

    def test_json_parsing(self):
        with patch("subprocess.Popen") as mock_subprocess:
            # Mock the stdout of the Popen process to return JSON
            mock_subprocess.return_value = MagicMock(returncode=0)
            mock_subprocess.return_value.communicate.return_value = (
                b'{"key": "value"}',
                b"",
            )

            command = getattr(self.sp, "pipelines")

            # Check that the JSON is parsed correctly
            self.assertEqual(command("arg1", "arg2"), {"key": "value"})


class TestSeqeraPlatformCLIArgs(unittest.TestCase):
    def setUp(self):
        self.cli_args = ["--url", "http://tower-api.com", "--insecure"]
        self.sp = seqeraplatform.SeqeraPlatform(cli_args=self.cli_args)

    @patch("subprocess.Popen")
    def test_cli_args_inclusion(self, mock_subprocess):
        # Mock the stdout of the Popen process
        mock_subprocess.return_value = MagicMock(returncode=0)
        mock_subprocess.return_value.communicate.return_value = (
            json.dumps({"key": "value"}).encode(),
            b"",
        )

        # Call a method
        self.sp.pipelines("view", "--name", "pipeline_name")

        # Extract the command used to call Popen
        called_command = mock_subprocess.call_args[0][0]

        # Check if the cli_args are present in the called command
        for arg in self.cli_args:
            self.assertIn(arg, called_command)

    @patch("subprocess.Popen")
    def test_cli_args_inclusion_ssl_certs(self, mock_subprocess):
        # Add path to custom certs store to cli_args
        self.cli_args.append("-Djavax.net.ssl.trustStore=/absolute/path/to/cacerts")

        # Initialize SeqeraPlatform with cli_args
        seqeraplatform.SeqeraPlatform(cli_args=self.cli_args)

        # Mock the stdout of the Popen process
        mock_subprocess.return_value = MagicMock(returncode=0)
        mock_subprocess.return_value.communicate.return_value = (
            json.dumps({"key": "value"}).encode(),
            b"",
        )

        # Call a method
        self.sp.pipelines("view", "--name", "pipeline_name")

        # Extract the command used to call Popen
        called_command = mock_subprocess.call_args[0][0]

        # Check if the cli_args are present in the called command
        self.assertIn(
            "-Djavax.net.ssl.trustStore=/absolute/path/to/cacerts", called_command
        )

    def test_cli_args_exclusion_of_verbose(self):  # TODO: remove this test once fixed
        # Add --verbose to cli_args
        verbose_args = ["--verbose"]

        # Check if ValueError is raised when initializing SeqeraPlatform with --verbose
        with self.assertRaises(ValueError) as context:
            seqeraplatform.SeqeraPlatform(cli_args=verbose_args)

        # Check the error message
        self.assertEqual(
            str(context.exception),
            "--verbose is not supported as a CLI argument to seqerakit.",
        )

    @patch("subprocess.Popen")
    def test_info_command_construction(self, mock_subprocess):
        # Mock the subprocess call to prevent actual execution
        mock_subprocess.return_value = MagicMock(returncode=0)
        mock_subprocess.return_value.communicate.return_value = (b"", b"")

        self.sp.info()
        called_command = mock_subprocess.call_args[0][0]

        # Check if the constructed command is correct
        expected_command_part = "tw --url http://tower-api.com --insecure info"
        self.assertIn(expected_command_part, called_command)

        # Check if the cli_args are included in the called command
        for arg in self.cli_args:
            self.assertIn(arg, called_command)

    @patch("subprocess.Popen")
    def test_info_command_dryrun(self, mock_subprocess):
        # Initialize SeqeraPlatform with dryrun enabled
        self.sp.dryrun = True
        self.sp.info()

        # Check that subprocess.Popen is not called
        mock_subprocess.assert_not_called()


class TestKitOptions(unittest.TestCase):
    def setUp(self):
        self.dryrun_tw = seqeraplatform.SeqeraPlatform(dryrun=True)

    @patch("subprocess.Popen")
    def test_dryrun_call(self, mock_subprocess):
        # Run a method with dryrun=True
        self.dryrun_tw.pipelines("view", "--name", "pipeline_name")

        # Assert that subprocess.Popen is not called
        mock_subprocess.assert_not_called()


class TestCheckEnvVars(unittest.TestCase):
    def setUp(self):
        self.sp = seqeraplatform.SeqeraPlatform()
        self.original_environ = dict(os.environ)

    def tearDown(self):
        # Restore the original environment after each test
        os.environ.clear()
        os.environ.update(self.original_environ)

    def test_with_set_env_vars(self):
        # Set environment variables for the test
        os.environ["VAR1"] = "value1"

        command = ["tw", "pipelines", "list", "-w", "$VAR1"]
        expected = "tw pipelines list -w $VAR1"
        result = self.sp._check_env_vars(command)
        self.assertEqual(result, expected)

    def test_without_env_vars(self):
        # Test case where there are no environment variables in the command
        command = ["tw", "info"]
        expected = "tw info"  # shlex.quote() will not alter these
        result = self.sp._check_env_vars(command)
        self.assertEqual(result, expected)

    def test_error_raised_for_unset_env_vars(self):
        # Unset environment variables for this test
        unset_var = "{UNSET_VAR}"
        if "UNSET_VAR" in os.environ:
            del os.environ["UNSET_VAR"]

        command = ["tw", "pipelines", "list", "-w", "${UNSET_VAR}"]

        # Assert that EnvironmentError is raised
        with self.assertRaises(EnvironmentError) as context:
            self.sp._check_env_vars(command)
        self.assertEqual(
            str(context.exception), f"Environment variable ${unset_var} not found!"
        )

    def test_special_vars_handling(self):
        os.environ["VAR1"] = "value1"

        test_cases = [
            (
                ["tw", "credentials", "add", "agent", "--work-dir", "$TW_AGENT_WORK"],
                r'tw credentials add agent --work-dir "\\\$TW_AGENT_WORK"',
            ),
            # Mixed case with both types of variables
            (
                [
                    "tw",
                    "credentials",
                    "add",
                    "--var",
                    "$VAR1",
                    "--work-dir",
                    "$TW_AGENT_WORK",
                ],
                r'tw credentials add --var $VAR1 --work-dir "\\\$TW_AGENT_WORK"',
            ),
            # Already escaped variable
            # Preserve variable as is
            (
                ["tw", "credentials", "add", "--var", "\\$SOME_VAR"],
                "tw credentials add --var $SOME_VAR",
            ),
        ]

        for command, expected in test_cases:
            with self.subTest(command=command):
                result = self.sp._check_env_vars(command)
                self.assertEqual(result, expected)

    def test_mixed_env_var_styles(self):
        # Not a valid use case but test handling of diff types
        os.environ["VAR1"] = "value1"
        os.environ["VAR2"] = "value2"
        os.environ["VAR3"] = "value3"

        command = [
            "tw",
            "credentials",
            "add",
            "-w",
            "${VAR1}",
            "--secret-key",
            "%VAR2%",
            "--access-key",
            "$env:VAR3",
        ]
        expected = (
            "tw credentials add -w ${VAR1} --secret-key %VAR2% --access-key $env:VAR3"
        )
        result = self.sp._check_env_vars(command)
        self.assertEqual(result, expected)


class TestSeqeraPlatformOutputHandling(unittest.TestCase):
    def setUp(self):
        self.sp = seqeraplatform.SeqeraPlatform()
        # Set up logging to capture output
        self.log_capture = StringIO()
        self.log_handler = logging.StreamHandler(self.log_capture)
        logging.getLogger().addHandler(self.log_handler)
        logging.getLogger().setLevel(logging.INFO)

    def tearDown(self):
        logging.getLogger().removeHandler(self.log_handler)
        logging.getLogger().setLevel(logging.NOTSET)

    @patch("subprocess.Popen")
    def test_suppress_output(self, mock_subprocess):
        mock_subprocess.return_value = MagicMock(returncode=0)
        mock_subprocess.return_value.communicate.return_value = (
            b'{"key": "value"}',
            b"",
        )

        log_capture = StringIO()
        logging.getLogger().addHandler(logging.StreamHandler(log_capture))

        with self.sp.suppress_output():
            self.sp.pipelines("list")

        log_contents = log_capture.getvalue()
        self.assertIn("Running command:", log_contents)
        self.assertNotIn("Command output:", log_contents)

    @patch("subprocess.Popen")
    def test_suppress_output_context(self, mock_subprocess):
        mock_subprocess.return_value = MagicMock(returncode=0)
        mock_subprocess.return_value.communicate.return_value = (
            b'{"key": "value"}',
            b"",
        )

        # Test that stdout is suppressed within the context manager
        with self.sp.suppress_output():
            result = self.sp._execute_command("tw pipelines list", to_json=True)
        self.assertEqual(result, {"key": "value"})

        # Test that stdout is not suppressed outside the context manager
        result = self.sp._execute_command("tw pipelines list", to_json=True)
        self.assertEqual(result, {"key": "value"})

    @patch("subprocess.Popen")
    def test_json_output_handling(self, mock_subprocess):
        mock_subprocess.return_value = MagicMock(returncode=0)
        mock_subprocess.return_value.communicate.return_value = (
            b'{"key": "value"}',
            b"",
        )

        result = self.sp._execute_command("tw pipelines list", to_json=True)
        self.assertEqual(result, {"key": "value"})

        result = self.sp._execute_command("tw pipelines list", to_json=False)
        self.assertEqual(result, '{"key": "value"}')

        _sp = seqeraplatform.SeqeraPlatform(json=True)
        result = _sp._execute_command("tw pipelines list", to_json=False)
        self.assertEqual(result, {"key": "value"})

        result = _sp._execute_command("tw pipelines list", to_json=True)
        self.assertEqual(result, {"key": "value"})

    @patch("subprocess.Popen")
    def test_print_stdout_override(self, mock_subprocess):
        mock_subprocess.return_value = MagicMock(returncode=0)
        mock_subprocess.return_value.communicate.return_value = (b"output", b"")

        # Test with print_stdout=True
        self.sp._execute_command("tw pipelines list", print_stdout=True)
        log_output = self.log_capture.getvalue()
        self.assertIn("Command output: output", log_output)

        self.log_capture.truncate(0)
        self.log_capture.seek(0)

        self.sp._execute_command("tw pipelines list", print_stdout=False)
        log_output = self.log_capture.getvalue()
        self.assertNotIn("Command output: output", log_output)

    @patch("subprocess.Popen")
    def test_error_handling_with_suppressed_output(self, mock_subprocess):
        mock_subprocess.return_value = MagicMock(returncode=1)
        mock_subprocess.return_value.communicate.return_value = (
            b"ERROR: Something went wrong",
            b"",
        )

        with self.assertRaises(seqeraplatform.CommandError):
            with self.sp.suppress_output():
                self.sp._execute_command("tw pipelines list")

    @patch("subprocess.Popen")
    def test_json_parsing_error(self, mock_subprocess):
        mock_subprocess.return_value = MagicMock(returncode=0)
        mock_subprocess.return_value.communicate.return_value = (b"Invalid JSON", b"")

        result = self.sp._execute_command("tw pipelines list", to_json=True)

        self.assertEqual(result, "Invalid JSON")  # Should return raw stdout
        mock_subprocess.assert_called_once_with(
            "tw pipelines list",
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            shell=True,
        )

    @patch("subprocess.Popen")
    def test_json_parsing_failure_fallback(self, mock_subprocess):
        mock_subprocess.return_value = MagicMock(returncode=0)
        mock_subprocess.return_value.communicate.return_value = (b"Invalid JSON", b"")

        result = self.sp._execute_command("tw pipelines list", to_json=True)

        self.assertEqual(result, "Invalid JSON")

    @patch("subprocess.Popen")
    def test_error_with_nonzero_return_code(self, mock_subprocess):
        mock_subprocess.return_value = MagicMock(returncode=1)
        mock_subprocess.return_value.communicate.return_value = (
            b"ERROR: Something went wrong",
            b"",
        )

        with self.assertRaises(CommandError):
            self.sp._execute_command("tw pipelines list")

    @patch("subprocess.Popen")
    def test_correct_logging(self, mock_subprocess):
        mock_subprocess.return_value = MagicMock(returncode=0)
        mock_subprocess.return_value.communicate.return_value = (b"Command output", b"")

        with patch("logging.info") as mock_logging:
            # Test with JSON enabled
            self.sp.json = True
            self.sp._execute_command("tw pipelines list")
            mock_logging.assert_called_once_with(" Running command: tw pipelines list")

            mock_logging.reset_mock()

            # Test with JSON disabled
            self.sp.json = False
            self.sp._execute_command("tw pipelines list")
            mock_logging.assert_any_call(" Command output: Command output")


if __name__ == "__main__":
    unittest.main()
