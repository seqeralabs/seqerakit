"""
Unit tests for the CLI module using Typer's CliRunner.
These tests verify that the CLI interface works correctly with various
command-line arguments and options.
"""

import pytest
from unittest.mock import patch, MagicMock
from typer.testing import CliRunner
from seqerakit.cli import app, __version__
from seqerakit.seqeraplatform import (
    CommandError,
    ResourceExistsError,
    ResourceNotFoundError,
)
from seqerakit.on_exists import OnExists


# Fixtures


@pytest.fixture
def runner():
    """Create a CliRunner instance for testing."""
    return CliRunner()


@pytest.fixture
def mock_seqera_platform():
    """Mock SeqeraPlatform class with common setup."""
    with patch("seqerakit.cli.seqeraplatform.SeqeraPlatform") as mock_sp_class:
        mock_sp = MagicMock()
        mock_sp_class.return_value = mock_sp
        yield mock_sp_class, mock_sp


@pytest.fixture
def mock_yaml_processing():
    """Mock YAML processing functions."""
    with patch("seqerakit.cli.find_yaml_files") as mock_find, patch(
        "seqerakit.cli.helper.parse_all_yaml"
    ) as mock_parse, patch("seqerakit.cli.BlockParser") as mock_parser:
        mock_find.return_value = ["test.yaml"]
        mock_parse.return_value = {}
        yield mock_find, mock_parse, mock_parser


# Basic CLI Tests


@pytest.mark.parametrize("flag", ["--version", "-v"])
def test_version_flag(runner, flag):
    """Test version flags display version and exit."""
    result = runner.invoke(app, [flag])
    assert result.exit_code == 0
    assert __version__ in result.stdout


def test_help_flag(runner):
    """Test --help flag displays help text."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Create resources on Seqera Platform" in result.stdout

    # Verify all major options are documented
    expected_options = [
        "--log-level",
        "--info",
        "--json",
        "--dryrun",
        "--delete",
        "--cli",
        "--targets",
        "--env-file",
        "--on-exists",
        "--overwrite",
        "--verbose",
    ]
    for option in expected_options:
        assert option in result.stdout


# Info Flag Tests


def test_info_flag(runner, mock_seqera_platform):
    """Test --info flag calls sp.info() and prints result."""
    mock_sp_class, mock_sp = mock_seqera_platform
    mock_sp.info.return_value = "Platform info output"

    result = runner.invoke(app, ["--info"])

    assert result.exit_code == 0
    mock_sp.info.assert_called_once()
    assert "Platform info output" in result.stdout


def test_info_flag_with_dryrun(runner, mock_seqera_platform):
    """Test --info with --dryrun doesn't print output."""
    mock_sp_class, mock_sp = mock_seqera_platform
    mock_sp.info.return_value = "Platform info output"

    result = runner.invoke(app, ["--info", "--dryrun"])

    assert result.exit_code == 0
    mock_sp.info.assert_called_once()
    # In dryrun mode, the info output should not be printed
    assert "Platform info output" not in result.stdout


def test_info_flag_with_command_error(runner, mock_seqera_platform):
    """Test --info handles CommandError properly."""
    mock_sp_class, mock_sp = mock_seqera_platform
    mock_sp.info.side_effect = CommandError("Test error")

    result = runner.invoke(app, ["--info"])

    assert result.exit_code == 1


# Argument Parsing Tests


@pytest.mark.parametrize("level", ["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"])
def test_log_level_option(runner, mock_seqera_platform, mock_yaml_processing, level):
    """Test --log-level option accepts valid log levels."""
    result = runner.invoke(app, ["--log-level", level, "test.yaml"])
    assert result.exit_code == 0


def test_json_flag(runner, mock_seqera_platform, mock_yaml_processing):
    """Test --json flag is passed to SeqeraPlatform."""
    mock_sp_class, mock_sp = mock_seqera_platform

    result = runner.invoke(app, ["--json", "test.yaml"])

    assert result.exit_code == 0
    mock_sp_class.assert_called_once()
    call_kwargs = mock_sp_class.call_args[1]
    assert call_kwargs["json"] is True


def test_dryrun_flag(runner, mock_seqera_platform, mock_yaml_processing):
    """Test --dryrun flag is passed to SeqeraPlatform."""
    mock_sp_class, mock_sp = mock_seqera_platform

    result = runner.invoke(app, ["--dryrun", "test.yaml"])

    assert result.exit_code == 0
    mock_sp_class.assert_called_once()
    call_kwargs = mock_sp_class.call_args[1]
    assert call_kwargs["dryrun"] is True


def test_delete_flag(runner, mock_seqera_platform, mock_yaml_processing):
    """Test --delete flag is passed to parse_all_yaml."""
    mock_find, mock_parse, mock_parser = mock_yaml_processing

    result = runner.invoke(app, ["--delete", "test.yaml"])

    assert result.exit_code == 0
    mock_parse.assert_called_once()
    call_kwargs = mock_parse.call_args[1]
    assert call_kwargs["destroy"] is True


def test_multiple_cli_args(runner, mock_seqera_platform, mock_yaml_processing):
    """Test multiple --cli arguments are combined."""
    mock_sp_class, mock_sp = mock_seqera_platform

    result = runner.invoke(
        app, ["--cli", "--insecure", "--cli", "--verbose", "test.yaml"]
    )

    assert result.exit_code == 0
    mock_sp_class.assert_called_once()
    call_kwargs = mock_sp_class.call_args[1]
    # Both --cli values should be in cli_args
    assert "--insecure" in call_kwargs["cli_args"]
    assert "--verbose" in call_kwargs["cli_args"]


def test_verbose_flag(runner, mock_seqera_platform, mock_yaml_processing):
    """Test --verbose flag adds --verbose to cli_args."""
    mock_sp_class, mock_sp = mock_seqera_platform

    result = runner.invoke(app, ["--verbose", "test.yaml"])

    assert result.exit_code == 0
    mock_sp_class.assert_called_once()
    call_kwargs = mock_sp_class.call_args[1]
    assert "--verbose" in call_kwargs["cli_args"]


def test_targets_option(runner, mock_seqera_platform, mock_yaml_processing):
    """Test --targets option is passed to parse_all_yaml."""
    mock_find, mock_parse, mock_parser = mock_yaml_processing

    result = runner.invoke(app, ["--targets", "teams,workspaces", "test.yaml"])

    assert result.exit_code == 0
    mock_parse.assert_called_once()
    call_kwargs = mock_parse.call_args[1]
    assert call_kwargs["targets"] == "teams,workspaces"


# OnExists Tests


@pytest.mark.parametrize("option", ["fail", "ignore", "overwrite"])
def test_on_exists_valid_option(
    runner, mock_seqera_platform, mock_yaml_processing, option
):
    """Test --on-exists with valid options."""
    mock_sp_class, mock_sp = mock_seqera_platform

    result = runner.invoke(app, ["--on-exists", option, "test.yaml"])

    assert result.exit_code == 0
    assert mock_sp.global_on_exists == OnExists[option.upper()]


def test_on_exists_invalid_option(runner):
    """Test --on-exists with invalid option exits with error."""
    with patch("seqerakit.cli.seqeraplatform.SeqeraPlatform"), patch(
        "seqerakit.cli.find_yaml_files"
    ) as mock_find:
        mock_find.return_value = ["test.yaml"]

        result = runner.invoke(app, ["--on-exists", "invalid", "test.yaml"])

        assert result.exit_code == 1


def test_overwrite_flag(runner, mock_seqera_platform, mock_yaml_processing):
    """Test deprecated --overwrite flag sets overwrite attribute."""
    mock_sp_class, mock_sp = mock_seqera_platform

    result = runner.invoke(app, ["--overwrite", "test.yaml"])

    assert result.exit_code == 0
    assert mock_sp.overwrite is True


# YAML File Handling Tests


def test_single_yaml_file(runner, mock_seqera_platform, mock_yaml_processing):
    """Test passing a single YAML file."""
    mock_find, mock_parse, mock_parser = mock_yaml_processing

    result = runner.invoke(app, ["test.yaml"])

    assert result.exit_code == 0
    mock_find.assert_called_once_with(["test.yaml"])


def test_multiple_yaml_files(runner, mock_seqera_platform):
    """Test passing multiple YAML files."""
    with patch("seqerakit.cli.find_yaml_files") as mock_find, patch(
        "seqerakit.cli.helper.parse_all_yaml"
    ) as mock_parse, patch("seqerakit.cli.BlockParser"):
        mock_find.return_value = ["test1.yaml", "test2.yaml", "test3.yaml"]
        mock_parse.return_value = {}

        result = runner.invoke(app, ["test1.yaml", "test2.yaml", "test3.yaml"])

        assert result.exit_code == 0
        mock_find.assert_called_once_with(["test1.yaml", "test2.yaml", "test3.yaml"])


def test_stdin_dash_argument(runner, mock_seqera_platform, mock_yaml_processing):
    """Test passing '-' to read from stdin."""
    mock_find, mock_parse, mock_parser = mock_yaml_processing

    result = runner.invoke(app, ["-"])

    assert result.exit_code == 0
    mock_find.assert_called_once_with(["-"])


def test_no_yaml_files_with_tty(runner):
    """Test error when no YAML files provided and stdin is a TTY."""
    with patch("seqerakit.cli.seqeraplatform.SeqeraPlatform"), patch(
        "seqerakit.cli.find_yaml_files"
    ) as mock_find:
        mock_find.side_effect = ValueError(
            "No YAML(s) provided and no input from stdin"
        )

        result = runner.invoke(app, [])

        assert result.exit_code == 1


# Error Handling Tests


@pytest.mark.parametrize(
    "error_class,error_msg",
    [
        (ResourceExistsError, "Resource already exists"),
        (ResourceNotFoundError, "Resource not found"),
        (CommandError, "Command failed"),
        (ValueError, "Invalid value"),
    ],
)
def test_error_handling(runner, mock_seqera_platform, error_class, error_msg):
    """Test various error types are handled properly."""
    with patch("seqerakit.cli.find_yaml_files") as mock_find, patch(
        "seqerakit.cli.helper.parse_all_yaml"
    ) as mock_parse:
        mock_find.return_value = ["test.yaml"]
        mock_parse.side_effect = error_class(error_msg)

        result = runner.invoke(app, ["test.yaml"])

        assert result.exit_code == 1
