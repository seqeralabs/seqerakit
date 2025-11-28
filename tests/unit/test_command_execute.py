"""
Unit tests for the Command.execute() method.
Tests the new architecture where Command objects can execute themselves.
"""
import pytest
from unittest.mock import Mock, MagicMock
from seqerakit.helper import Command
from seqerakit.seqeraplatform import SeqeraPlatform


class TestCommandExecute:
    """Test Command.execute() method"""

    def test_execute_with_method(self):
        """Test executing a command with a method (e.g., 'add')"""
        # Create a mock SeqeraPlatform instance
        sp = Mock(spec=SeqeraPlatform)
        sp.pipelines = Mock(return_value="success")

        # Create a command
        cmd = Command(
            subcommand="pipelines",
            method="add",
            args=["https://github.com/nextflow-io/hello", "--name", "test-pipeline"]
        )

        # Execute the command
        result = cmd.execute(sp)

        # Verify the correct method was called with correct args
        sp.pipelines.assert_called_once_with(
            "add",
            "https://github.com/nextflow-io/hello",
            "--name",
            "test-pipeline"
        )
        assert result == "success"

    def test_execute_without_method(self):
        """Test executing a command without a method"""
        sp = Mock(spec=SeqeraPlatform)
        sp.launch = Mock(return_value="launched")

        # Launch doesn't use a method
        cmd = Command(
            subcommand="launch",
            method=None,
            args=["my-pipeline", "--workspace", "org/ws"]
        )

        result = cmd.execute(sp)

        # Should call without the method parameter
        sp.launch.assert_called_once_with(
            "my-pipeline",
            "--workspace",
            "org/ws"
        )
        assert result == "launched"

    def test_execute_with_hyphenated_subcommand(self):
        """Test executing a command with hyphenated subcommand"""
        sp = Mock(spec=SeqeraPlatform)
        sp.compute_envs = Mock(return_value="created")

        cmd = Command(
            subcommand="compute-envs",
            method="add",
            args=["aws-batch", "forge", "--name", "my-ce"]
        )

        result = cmd.execute(sp)

        # Hyphen should be converted to underscore for Python method name
        sp.compute_envs.assert_called_once_with(
            "add",
            "aws-batch",
            "forge",
            "--name",
            "my-ce"
        )
        assert result == "created"

    def test_execute_with_import_method(self):
        """Test executing a command with 'import' method"""
        sp = Mock(spec=SeqeraPlatform)
        sp.pipelines = Mock(return_value="imported")

        cmd = Command(
            subcommand="pipelines",
            method="import",
            args=["pipeline.json"]
        )

        result = cmd.execute(sp)

        sp.pipelines.assert_called_once_with("import", "pipeline.json")
        assert result == "imported"

    def test_execute_credentials(self):
        """Test executing a credentials command"""
        sp = Mock(spec=SeqeraPlatform)
        sp.credentials = Mock(return_value="added")

        cmd = Command(
            subcommand="credentials",
            method="add",
            args=["aws", "--name", "my-aws-cred", "--access-key", "AKIATEST"]
        )

        result = cmd.execute(sp)

        sp.credentials.assert_called_once_with(
            "add",
            "aws",
            "--name",
            "my-aws-cred",
            "--access-key",
            "AKIATEST"
        )
        assert result == "added"

    def test_execute_teams_members(self):
        """Test executing a teams members command"""
        sp = Mock(spec=SeqeraPlatform)
        sp.teams = Mock(return_value="member added")

        cmd = Command(
            subcommand="teams",
            method="members",
            args=["--team", "my-team", "--organization", "my-org", "add", "--member", "user@example.com"]
        )

        result = cmd.execute(sp)

        sp.teams.assert_called_once_with(
            "members",
            "--team",
            "my-team",
            "--organization",
            "my-org",
            "add",
            "--member",
            "user@example.com"
        )
        assert result == "member added"

    def test_execute_with_empty_args(self):
        """Test executing a command with no arguments"""
        sp = Mock(spec=SeqeraPlatform)
        sp.organizations = Mock(return_value="listed")

        cmd = Command(
            subcommand="organizations",
            method="list",
            args=[]
        )

        result = cmd.execute(sp)

        sp.organizations.assert_called_once_with("list")
        assert result == "listed"

    def test_execute_data_links(self):
        """Test executing a data-links command (hyphenated name)"""
        sp = Mock(spec=SeqeraPlatform)
        sp.data_links = Mock(return_value="created")

        cmd = Command(
            subcommand="data-links",
            method="add",
            args=["--name", "my-link", "--workspace", "org/ws"]
        )

        result = cmd.execute(sp)

        sp.data_links.assert_called_once_with(
            "add",
            "--name",
            "my-link",
            "--workspace",
            "org/ws"
        )
        assert result == "created"


class TestCommandToArgsList:
    """Test Command.to_args_list() method"""

    def test_to_args_list_with_method(self):
        """Test converting command to args list with method"""
        cmd = Command(
            subcommand="pipelines",
            method="add",
            args=["https://github.com/test/repo", "--name", "test"]
        )

        args_list = cmd.to_args_list()

        assert args_list == [
            "pipelines",
            "add",
            "https://github.com/test/repo",
            "--name",
            "test"
        ]

    def test_to_args_list_without_method(self):
        """Test converting command to args list without method"""
        cmd = Command(
            subcommand="launch",
            method=None,
            args=["my-pipeline", "--workspace", "org/ws"]
        )

        args_list = cmd.to_args_list()

        assert args_list == [
            "launch",
            "my-pipeline",
            "--workspace",
            "org/ws"
        ]

    def test_to_args_list_empty_args(self):
        """Test converting command with no args"""
        cmd = Command(
            subcommand="organizations",
            method="list",
            args=[]
        )

        args_list = cmd.to_args_list()

        assert args_list == ["organizations", "list"]


class TestCommandIntegration:
    """Integration tests for Command with real command patterns"""

    def test_pipeline_command_pattern(self):
        """Test realistic pipeline command"""
        sp = Mock(spec=SeqeraPlatform)
        sp.pipelines = Mock(return_value="pipeline created")

        # Simulate what PipelineCommandBuilder would create
        cmd = Command(
            subcommand="pipelines",
            method="add",
            args=[
                "https://github.com/nextflow-io/hello",
                "--name", "hello",
                "--workspace", "demo/test",
                "--compute-env", "my-compute-env",
                "--params-file", "/tmp/params.yaml"
            ]
        )

        result = cmd.execute(sp)

        assert result == "pipeline created"
        assert sp.pipelines.call_count == 1

    def test_compute_env_command_pattern(self):
        """Test realistic compute-env command"""
        sp = Mock(spec=SeqeraPlatform)
        sp.compute_envs = Mock(return_value="compute env created")

        # Simulate what TypeBasedCommandBuilder would create
        cmd = Command(
            subcommand="compute-envs",
            method="add",
            args=[
                "aws-batch",
                "forge",
                "--name", "my-ce",
                "--workspace", "demo/test",
                "--work-dir", "s3://bucket/work",
                "--region", "us-east-1",
                "--max-cpus", "256"
            ]
        )

        result = cmd.execute(sp)

        assert result == "compute env created"
        sp.compute_envs.assert_called_once()

    def test_teams_with_members_pattern(self):
        """Test realistic teams command with members"""
        sp = Mock(spec=SeqeraPlatform)
        sp.teams = Mock(return_value="operation completed")

        # Main team command
        team_cmd = Command(
            subcommand="teams",
            method="add",
            args=["--name", "dev-team", "--organization", "acme-corp"]
        )

        # Member commands
        member1_cmd = Command(
            subcommand="teams",
            method="members",
            args=["--team", "dev-team", "--organization", "acme-corp", "add", "--member", "user1@example.com"]
        )

        member2_cmd = Command(
            subcommand="teams",
            method="members",
            args=["--team", "dev-team", "--organization", "acme-corp", "add", "--member", "user2@example.com"]
        )

        # Execute all commands
        team_cmd.execute(sp)
        member1_cmd.execute(sp)
        member2_cmd.execute(sp)

        # Should have been called 3 times total
        assert sp.teams.call_count == 3

    def test_credential_command_pattern(self):
        """Test realistic credential command"""
        sp = Mock(spec=SeqeraPlatform)
        sp.credentials = Mock(return_value="credential added")

        # Simulate what TypeBasedCommandBuilder would create for AWS credential
        cmd = Command(
            subcommand="credentials",
            method="add",
            args=[
                "aws",  # Type as positional
                "--name", "my-aws-cred",
                "--workspace", "demo/test",
                "--access-key", "AKIAIOSFODNN7EXAMPLE",
                "--secret-key", "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
            ]
        )

        result = cmd.execute(sp)

        assert result == "credential added"
        # Verify first arg after method is the type
        call_args = sp.credentials.call_args[0]
        assert call_args[0] == "add"
        assert call_args[1] == "aws"
