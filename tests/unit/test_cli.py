"""
Unit tests for the CLI module using Typer's CliRunner.
These tests verify that the CLI interface works correctly with various
command-line arguments and options.
"""

import unittest
from unittest.mock import patch, MagicMock
from typer.testing import CliRunner
from seqerakit.cli import app, __version__


class TestCLIBasics(unittest.TestCase):
    """Test basic CLI functionality like version and help."""

    def setUp(self):
        self.runner = CliRunner()

    def test_version_flag(self):
        """Test --version flag displays version and exits."""
        result = self.runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert __version__ in result.stdout

    def test_version_short_flag(self):
        """Test -v flag displays version and exits."""
        result = self.runner.invoke(app, ["-v"])
        assert result.exit_code == 0
        assert __version__ in result.stdout

    def test_help_flag(self):
        """Test --help flag displays help text."""
        result = self.runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "Create resources on Seqera Platform" in result.stdout
        assert "--log-level" in result.stdout
        assert "--info" in result.stdout
        assert "--json" in result.stdout
        assert "--dryrun" in result.stdout
        assert "--delete" in result.stdout
        assert "--cli" in result.stdout
        assert "--targets" in result.stdout
        assert "--env-file" in result.stdout
        assert "--on-exists" in result.stdout
        assert "--overwrite" in result.stdout
        assert "--verbose" in result.stdout


class TestCLIInfo(unittest.TestCase):
    """Test --info flag functionality."""

    def setUp(self):
        self.runner = CliRunner()

    @patch("seqerakit.cli.seqeraplatform.SeqeraPlatform")
    def test_info_flag(self, mock_sp_class):
        """Test --info flag calls sp.info() and prints result."""
        mock_sp = MagicMock()
        mock_sp.info.return_value = "Platform info output"
        mock_sp_class.return_value = mock_sp

        result = self.runner.invoke(app, ["--info"])

        assert result.exit_code == 0
        mock_sp.info.assert_called_once()
        assert "Platform info output" in result.stdout

    @patch("seqerakit.cli.seqeraplatform.SeqeraPlatform")
    def test_info_flag_with_dryrun(self, mock_sp_class):
        """Test --info with --dryrun doesn't print output."""
        mock_sp = MagicMock()
        mock_sp.info.return_value = "Platform info output"
        mock_sp_class.return_value = mock_sp

        result = self.runner.invoke(app, ["--info", "--dryrun"])

        assert result.exit_code == 0
        mock_sp.info.assert_called_once()
        # In dryrun mode, the info output should not be printed
        assert "Platform info output" not in result.stdout

    @patch("seqerakit.cli.seqeraplatform.SeqeraPlatform")
    def test_info_flag_with_command_error(self, mock_sp_class):
        """Test --info handles CommandError properly."""
        from seqerakit.seqeraplatform import CommandError

        mock_sp = MagicMock()
        mock_sp.info.side_effect = CommandError("Test error")
        mock_sp_class.return_value = mock_sp

        result = self.runner.invoke(app, ["--info"])

        assert result.exit_code == 1


class TestCLIArguments(unittest.TestCase):
    """Test CLI argument parsing."""

    def setUp(self):
        self.runner = CliRunner()

    @patch("seqerakit.cli.seqeraplatform.SeqeraPlatform")
    @patch("seqerakit.cli.find_yaml_files")
    @patch("seqerakit.cli.helper.parse_all_yaml")
    @patch("seqerakit.cli.BlockParser")
    def test_log_level_option(
        self, mock_parser, mock_parse_yaml, mock_find, mock_sp_class
    ):
        """Test --log-level option accepts valid log levels."""
        mock_sp = MagicMock()
        mock_sp_class.return_value = mock_sp
        mock_find.return_value = ["test.yaml"]
        mock_parse_yaml.return_value = {}

        for level in ["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"]:
            result = self.runner.invoke(app, ["--log-level", level, "test.yaml"])
            assert result.exit_code == 0

    @patch("seqerakit.cli.seqeraplatform.SeqeraPlatform")
    @patch("seqerakit.cli.find_yaml_files")
    @patch("seqerakit.cli.helper.parse_all_yaml")
    @patch("seqerakit.cli.BlockParser")
    def test_json_flag(self, mock_parser, mock_parse_yaml, mock_find, mock_sp_class):
        """Test --json flag is passed to SeqeraPlatform."""
        mock_sp = MagicMock()
        mock_sp_class.return_value = mock_sp
        mock_find.return_value = ["test.yaml"]
        mock_parse_yaml.return_value = {}

        result = self.runner.invoke(app, ["--json", "test.yaml"])

        assert result.exit_code == 0
        mock_sp_class.assert_called_once()
        call_kwargs = mock_sp_class.call_args[1]
        assert call_kwargs["json"] is True

    @patch("seqerakit.cli.seqeraplatform.SeqeraPlatform")
    @patch("seqerakit.cli.find_yaml_files")
    @patch("seqerakit.cli.helper.parse_all_yaml")
    @patch("seqerakit.cli.BlockParser")
    def test_dryrun_flag(self, mock_parser, mock_parse_yaml, mock_find, mock_sp_class):
        """Test --dryrun flag is passed to SeqeraPlatform."""
        mock_sp = MagicMock()
        mock_sp_class.return_value = mock_sp
        mock_find.return_value = ["test.yaml"]
        mock_parse_yaml.return_value = {}

        result = self.runner.invoke(app, ["--dryrun", "test.yaml"])

        assert result.exit_code == 0
        mock_sp_class.assert_called_once()
        call_kwargs = mock_sp_class.call_args[1]
        assert call_kwargs["dryrun"] is True

    @patch("seqerakit.cli.seqeraplatform.SeqeraPlatform")
    @patch("seqerakit.cli.find_yaml_files")
    @patch("seqerakit.cli.helper.parse_all_yaml")
    @patch("seqerakit.cli.BlockParser")
    def test_delete_flag(self, mock_parser, mock_parse_yaml, mock_find, mock_sp_class):
        """Test --delete flag is passed to parse_all_yaml."""
        mock_sp = MagicMock()
        mock_sp_class.return_value = mock_sp
        mock_find.return_value = ["test.yaml"]
        mock_parse_yaml.return_value = {}

        result = self.runner.invoke(app, ["--delete", "test.yaml"])

        assert result.exit_code == 0
        mock_parse_yaml.assert_called_once()
        call_kwargs = mock_parse_yaml.call_args[1]
        assert call_kwargs["destroy"] is True

    @patch("seqerakit.cli.seqeraplatform.SeqeraPlatform")
    @patch("seqerakit.cli.find_yaml_files")
    @patch("seqerakit.cli.helper.parse_all_yaml")
    @patch("seqerakit.cli.BlockParser")
    def test_multiple_cli_args(
        self, mock_parser, mock_parse_yaml, mock_find, mock_sp_class
    ):
        """Test multiple --cli arguments are combined."""
        mock_sp = MagicMock()
        mock_sp_class.return_value = mock_sp
        mock_find.return_value = ["test.yaml"]
        mock_parse_yaml.return_value = {}

        result = self.runner.invoke(
            app, ["--cli", "--insecure", "--cli", "--verbose", "test.yaml"]
        )

        assert result.exit_code == 0
        mock_sp_class.assert_called_once()
        call_kwargs = mock_sp_class.call_args[1]
        # Both --cli values should be in cli_args
        assert "--insecure" in call_kwargs["cli_args"]
        assert "--verbose" in call_kwargs["cli_args"]

    @patch("seqerakit.cli.seqeraplatform.SeqeraPlatform")
    @patch("seqerakit.cli.find_yaml_files")
    @patch("seqerakit.cli.helper.parse_all_yaml")
    @patch("seqerakit.cli.BlockParser")
    def test_verbose_flag(self, mock_parser, mock_parse_yaml, mock_find, mock_sp_class):
        """Test --verbose flag adds --verbose to cli_args."""
        mock_sp = MagicMock()
        mock_sp_class.return_value = mock_sp
        mock_find.return_value = ["test.yaml"]
        mock_parse_yaml.return_value = {}

        result = self.runner.invoke(app, ["--verbose", "test.yaml"])

        assert result.exit_code == 0
        mock_sp_class.assert_called_once()
        call_kwargs = mock_sp_class.call_args[1]
        assert "--verbose" in call_kwargs["cli_args"]

    @patch("seqerakit.cli.seqeraplatform.SeqeraPlatform")
    @patch("seqerakit.cli.find_yaml_files")
    @patch("seqerakit.cli.helper.parse_all_yaml")
    @patch("seqerakit.cli.BlockParser")
    def test_targets_option(
        self, mock_parser, mock_parse_yaml, mock_find, mock_sp_class
    ):
        """Test --targets option is passed to parse_all_yaml."""
        mock_sp = MagicMock()
        mock_sp_class.return_value = mock_sp
        mock_find.return_value = ["test.yaml"]
        mock_parse_yaml.return_value = {}

        result = self.runner.invoke(app, ["--targets", "teams,workspaces", "test.yaml"])

        assert result.exit_code == 0
        mock_parse_yaml.assert_called_once()
        call_kwargs = mock_parse_yaml.call_args[1]
        assert call_kwargs["targets"] == "teams,workspaces"


class TestCLIOnExists(unittest.TestCase):
    """Test --on-exists and --overwrite flags."""

    def setUp(self):
        self.runner = CliRunner()

    @patch("seqerakit.cli.seqeraplatform.SeqeraPlatform")
    @patch("seqerakit.cli.find_yaml_files")
    @patch("seqerakit.cli.helper.parse_all_yaml")
    @patch("seqerakit.cli.BlockParser")
    def test_on_exists_valid_option(
        self, mock_parser, mock_parse_yaml, mock_find, mock_sp_class
    ):
        """Test --on-exists with valid options."""
        from seqerakit.on_exists import OnExists

        mock_sp = MagicMock()
        mock_sp_class.return_value = mock_sp
        mock_find.return_value = ["test.yaml"]
        mock_parse_yaml.return_value = {}

        for option in ["fail", "ignore", "overwrite"]:
            result = self.runner.invoke(app, ["--on-exists", option, "test.yaml"])
            assert result.exit_code == 0
            assert mock_sp.global_on_exists == OnExists[option.upper()]
            mock_sp_class.reset_mock()

    @patch("seqerakit.cli.seqeraplatform.SeqeraPlatform")
    @patch("seqerakit.cli.find_yaml_files")
    def test_on_exists_invalid_option(self, mock_find, mock_sp_class):
        """Test --on-exists with invalid option exits with error."""
        mock_sp = MagicMock()
        mock_sp_class.return_value = mock_sp
        mock_find.return_value = ["test.yaml"]

        result = self.runner.invoke(app, ["--on-exists", "invalid", "test.yaml"])

        assert result.exit_code == 1

    @patch("seqerakit.cli.seqeraplatform.SeqeraPlatform")
    @patch("seqerakit.cli.find_yaml_files")
    @patch("seqerakit.cli.helper.parse_all_yaml")
    @patch("seqerakit.cli.BlockParser")
    def test_overwrite_flag(
        self, mock_parser, mock_parse_yaml, mock_find, mock_sp_class
    ):
        """Test deprecated --overwrite flag sets overwrite attribute."""
        mock_sp = MagicMock()
        mock_sp_class.return_value = mock_sp
        mock_find.return_value = ["test.yaml"]
        mock_parse_yaml.return_value = {}

        result = self.runner.invoke(app, ["--overwrite", "test.yaml"])

        assert result.exit_code == 0
        assert mock_sp.overwrite is True


class TestCLIYAMLFiles(unittest.TestCase):
    """Test YAML file argument handling."""

    def setUp(self):
        self.runner = CliRunner()

    @patch("seqerakit.cli.seqeraplatform.SeqeraPlatform")
    @patch("seqerakit.cli.find_yaml_files")
    @patch("seqerakit.cli.helper.parse_all_yaml")
    @patch("seqerakit.cli.BlockParser")
    def test_single_yaml_file(
        self, mock_parser, mock_parse_yaml, mock_find, mock_sp_class
    ):
        """Test passing a single YAML file."""
        mock_sp = MagicMock()
        mock_sp_class.return_value = mock_sp
        mock_find.return_value = ["test.yaml"]
        mock_parse_yaml.return_value = {}

        result = self.runner.invoke(app, ["test.yaml"])

        assert result.exit_code == 0
        mock_find.assert_called_once_with(["test.yaml"])

    @patch("seqerakit.cli.seqeraplatform.SeqeraPlatform")
    @patch("seqerakit.cli.find_yaml_files")
    @patch("seqerakit.cli.helper.parse_all_yaml")
    @patch("seqerakit.cli.BlockParser")
    def test_multiple_yaml_files(
        self, mock_parser, mock_parse_yaml, mock_find, mock_sp_class
    ):
        """Test passing multiple YAML files."""
        mock_sp = MagicMock()
        mock_sp_class.return_value = mock_sp
        mock_find.return_value = ["test1.yaml", "test2.yaml", "test3.yaml"]
        mock_parse_yaml.return_value = {}

        result = self.runner.invoke(app, ["test1.yaml", "test2.yaml", "test3.yaml"])

        assert result.exit_code == 0
        mock_find.assert_called_once_with(["test1.yaml", "test2.yaml", "test3.yaml"])

    @patch("seqerakit.cli.seqeraplatform.SeqeraPlatform")
    @patch("seqerakit.cli.find_yaml_files")
    @patch("seqerakit.cli.helper.parse_all_yaml")
    @patch("seqerakit.cli.BlockParser")
    def test_stdin_dash_argument(
        self, mock_parser, mock_parse_yaml, mock_find, mock_sp_class
    ):
        """Test passing '-' to read from stdin."""
        mock_sp = MagicMock()
        mock_sp_class.return_value = mock_sp
        mock_find.return_value = ["-"]
        mock_parse_yaml.return_value = {}

        result = self.runner.invoke(app, ["-"])

        assert result.exit_code == 0
        mock_find.assert_called_once_with(["-"])

    @patch("seqerakit.cli.seqeraplatform.SeqeraPlatform")
    @patch("seqerakit.cli.find_yaml_files")
    def test_no_yaml_files_with_tty(self, mock_find, mock_sp_class):
        """Test error when no YAML files provided and stdin is a TTY."""
        mock_sp = MagicMock()
        mock_sp_class.return_value = mock_sp
        mock_find.side_effect = ValueError(
            "No YAML(s) provided and no input from stdin"
        )

        result = self.runner.invoke(app, [])

        assert result.exit_code == 1


class TestCLIErrorHandling(unittest.TestCase):
    """Test error handling in CLI."""

    def setUp(self):
        self.runner = CliRunner()

    @patch("seqerakit.cli.seqeraplatform.SeqeraPlatform")
    @patch("seqerakit.cli.find_yaml_files")
    @patch("seqerakit.cli.helper.parse_all_yaml")
    def test_resource_exists_error(self, mock_parse_yaml, mock_find, mock_sp_class):
        """Test ResourceExistsError is handled properly."""
        from seqerakit.seqeraplatform import ResourceExistsError

        mock_sp = MagicMock()
        mock_sp_class.return_value = mock_sp
        mock_find.return_value = ["test.yaml"]
        mock_parse_yaml.side_effect = ResourceExistsError("Resource already exists")

        result = self.runner.invoke(app, ["test.yaml"])

        assert result.exit_code == 1

    @patch("seqerakit.cli.seqeraplatform.SeqeraPlatform")
    @patch("seqerakit.cli.find_yaml_files")
    @patch("seqerakit.cli.helper.parse_all_yaml")
    def test_resource_not_found_error(self, mock_parse_yaml, mock_find, mock_sp_class):
        """Test ResourceNotFoundError is handled properly."""
        from seqerakit.seqeraplatform import ResourceNotFoundError

        mock_sp = MagicMock()
        mock_sp_class.return_value = mock_sp
        mock_find.return_value = ["test.yaml"]
        mock_parse_yaml.side_effect = ResourceNotFoundError("Resource not found")

        result = self.runner.invoke(app, ["test.yaml"])

        assert result.exit_code == 1

    @patch("seqerakit.cli.seqeraplatform.SeqeraPlatform")
    @patch("seqerakit.cli.find_yaml_files")
    @patch("seqerakit.cli.helper.parse_all_yaml")
    def test_command_error(self, mock_parse_yaml, mock_find, mock_sp_class):
        """Test CommandError is handled properly."""
        from seqerakit.seqeraplatform import CommandError

        mock_sp = MagicMock()
        mock_sp_class.return_value = mock_sp
        mock_find.return_value = ["test.yaml"]
        mock_parse_yaml.side_effect = CommandError("Command failed")

        result = self.runner.invoke(app, ["test.yaml"])

        assert result.exit_code == 1

    @patch("seqerakit.cli.seqeraplatform.SeqeraPlatform")
    @patch("seqerakit.cli.find_yaml_files")
    @patch("seqerakit.cli.helper.parse_all_yaml")
    def test_value_error(self, mock_parse_yaml, mock_find, mock_sp_class):
        """Test ValueError is handled properly."""
        mock_sp = MagicMock()
        mock_sp_class.return_value = mock_sp
        mock_find.return_value = ["test.yaml"]
        mock_parse_yaml.side_effect = ValueError("Invalid value")

        result = self.runner.invoke(app, ["test.yaml"])

        assert result.exit_code == 1


if __name__ == "__main__":
    unittest.main()
