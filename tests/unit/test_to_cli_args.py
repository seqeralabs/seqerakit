"""
Unit tests for the to_cli_args() method on Pydantic models.
Tests the new architecture where models convert themselves to CLI arguments.
"""

from seqerakit.models import (
    Organization,
    Workspace,
    Pipeline,
    ComputeEnv,
    Credential,
    Action,
    Launch,
    Team,
    Label,
    Member,
    Participant,
    Dataset,
    Secret,
    DataLink,
    Studio,
)


class TestBasicModelsToCliArgs:
    """Test to_cli_args() for models that use the base implementation"""

    def test_organization_to_cli_args(self):
        """Test Organization.to_cli_args()"""
        org = Organization(
            name="test-org",
            full_name="Test Organization",
            description="A test organization",
        )
        args = org.to_cli_args()

        assert "--name" in args
        assert "test-org" in args
        assert "--full-name" in args
        assert "Test Organization" in args
        assert "--description" in args
        assert "A test organization" in args

    def test_workspace_to_cli_args(self):
        """Test Workspace.to_cli_args()"""
        ws = Workspace(
            name="test-ws", full_name="Test Workspace", organization="my-org"
        )
        args = ws.to_cli_args()

        assert "--name" in args
        assert "test-ws" in args
        assert "--full-name" in args
        assert "Test Workspace" in args
        assert "--organization" in args
        assert "my-org" in args

    def test_label_to_cli_args(self):
        """Test Label.to_cli_args()"""
        label = Label(name="env", value="production", workspace="org/workspace")
        args = label.to_cli_args()

        assert "--name" in args
        assert "env" in args
        assert "--value" in args
        assert "production" in args
        assert "--workspace" in args
        assert "org/workspace" in args

    def test_boolean_flags(self):
        """Test that boolean True values become flags"""
        ws = Workspace(
            name="test", full_name="Test", organization="org", visibility="PRIVATE"
        )
        args = ws.to_cli_args()

        # Should have the fields as options
        assert "--name" in args
        assert "--visibility" in args
        assert "PRIVATE" in args

    def test_none_values_excluded(self):
        """Test that None values are excluded from CLI args"""
        org = Organization(
            name="test-org",
            full_name="Test Org",
            # description is None
        )
        args = org.to_cli_args()

        assert "--name" in args
        assert "--full-name" in args
        assert "--description" not in args


class TestCredentialToCliArgs:
    """Test Credential.to_cli_args() with type as positional"""

    def test_aws_credential_to_cli_args(self):
        """Test AWS credential with type as first positional arg"""
        cred = Credential(
            type="aws",
            name="my-aws-cred",
            workspace="org/workspace",
            access_key="AKIAIOSFODNN7EXAMPLE",
            secret_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
        )
        args = cred.to_cli_args()

        # Type should be first positional (not --type)
        assert args[0] == "aws"
        assert "--type" not in args

        # Rest should be options
        assert "--name" in args
        assert "my-aws-cred" in args
        assert "--workspace" in args
        assert "--access-key" in args
        assert "--secret-key" in args

    def test_google_credential_to_cli_args(self):
        """Test Google credential"""
        cred = Credential(
            type="google",
            name="my-gcp-cred",
            workspace="org/workspace",
            key="/path/to/key.json",
        )
        args = cred.to_cli_args()

        assert args[0] == "google"
        assert "--name" in args
        assert "--key" in args


class TestComputeEnvToCliArgs:
    """Test ComputeEnv.to_cli_args() with type and config-mode as positional"""

    def test_compute_env_to_cli_args(self):
        """Test compute env with type and config-mode as positional args"""
        ce = ComputeEnv(
            type="aws-batch",
            config_mode="forge",
            name="my-compute-env",
            workspace="org/workspace",
            work_dir="s3://bucket/work",
            region="us-east-1",
            max_cpus=256,
        )
        args = ce.to_cli_args()

        # First two args should be positional
        assert args[0] == "aws-batch"
        assert args[1] == "forge"
        assert "--type" not in args
        assert "--config-mode" not in args

        # Rest should be options
        assert "--name" in args
        assert "my-compute-env" in args
        assert "--work-dir" in args
        assert "--region" in args
        assert "--max-cpus" in args
        assert "256" in args

    def test_compute_env_with_lists(self):
        """Test compute env with list values (instance-types, subnets, etc.)"""
        ce = ComputeEnv(
            type="aws-batch",
            config_mode="forge",
            name="my-ce",
            workspace="org/ws",
            work_dir="s3://bucket/work",
            region="us-east-1",
            max_cpus=256,
            instance_types=["t3.large", "t3.xlarge"],
            subnets=["subnet-123", "subnet-456"],
        )
        args = ce.to_cli_args()

        # Lists should be converted to comma-separated strings
        assert "--instance-types" in args
        idx = args.index("--instance-types")
        assert args[idx + 1] == "t3.large,t3.xlarge"

        assert "--subnets" in args
        idx = args.index("--subnets")
        assert args[idx + 1] == "subnet-123,subnet-456"


class TestActionToCliArgs:
    """Test Action.to_cli_args() with type as positional"""

    def test_github_action_to_cli_args(self):
        """Test GitHub action"""
        action = Action(
            type="github",
            name="my-action",
            workspace="org/workspace",
            pipeline="my-pipeline",
            url="https://github.com/user/repo",
        )
        args = action.to_cli_args()

        # Type should be first positional
        assert args[0] == "github"
        assert "--type" not in args

        # Rest should be options
        assert "--name" in args
        assert "--pipeline" in args
        assert "--url" in args

    def test_action_params_excluded(self):
        """Test that params are excluded (handled by builder)"""
        action = Action(
            type="github",
            name="my-action",
            workspace="org/workspace",
            params={"key": "value"},
        )
        args = action.to_cli_args()

        # params should not be in args (handled by builder)
        assert "--params" not in args
        assert "key" not in args


class TestPipelineToCliArgs:
    """Test Pipeline.to_cli_args() with URL as positional"""

    def test_pipeline_to_cli_args(self):
        """Test pipeline with URL as first positional arg"""
        pipeline = Pipeline(
            name="my-pipeline",
            url="https://github.com/nextflow-io/hello",
            workspace="org/workspace",
            compute_env="my-compute-env",
            work_dir="s3://bucket/work",
        )
        args = pipeline.to_cli_args()

        # URL should be first positional
        assert args[0] == "https://github.com/nextflow-io/hello"
        assert "--url" not in args

        # Rest should be options
        assert "--name" in args
        assert "my-pipeline" in args
        assert "--workspace" in args
        assert "--compute-env" in args
        assert "--work-dir" in args

    def test_pipeline_params_excluded(self):
        """Test that params and params-file are excluded"""
        pipeline = Pipeline(
            name="my-pipeline",
            url="https://github.com/nextflow-io/hello",
            workspace="org/workspace",
            params_file="/path/to/params.yaml",
        )
        args = pipeline.to_cli_args()

        # params-file should not be in args (handled by builder)
        assert "--params-file" not in args
        assert "/path/to/params.yaml" not in args

    def test_pipeline_with_boolean_flags(self):
        """Test pipeline with boolean flags"""
        pipeline = Pipeline(
            name="my-pipeline",
            url="https://github.com/nextflow-io/hello",
            workspace="org/workspace",
            pull_latest=True,
            stub_run=True,
        )
        args = pipeline.to_cli_args()

        # Boolean True values should become flags
        assert "--pull-latest" in args
        assert "--stub-run" in args


class TestLaunchToCliArgs:
    """Test Launch.to_cli_args() with pipeline as positional"""

    def test_launch_to_cli_args(self):
        """Test launch with pipeline as first positional arg"""
        launch = Launch(
            pipeline="my-pipeline",
            workspace="org/workspace",
            compute_env="my-compute-env",
            work_dir="s3://bucket/work",
        )
        args = launch.to_cli_args()

        # Pipeline should be first positional
        assert args[0] == "my-pipeline"
        assert "--pipeline" not in args

        # Rest should be options
        assert "--workspace" in args
        assert "--compute-env" in args
        assert "--work-dir" in args

    def test_launch_params_excluded(self):
        """Test that params are excluded from launch args"""
        launch = Launch(
            pipeline="my-pipeline",
            workspace="org/workspace",
            params={"input": "s3://bucket/data"},
        )
        args = launch.to_cli_args()

        # params should not be in args (handled by builder)
        assert "--params" not in args
        assert "input" not in args


class TestTeamToCliArgs:
    """Test Team model (members are handled separately by builder)"""

    def test_team_without_members(self):
        """Test team without members"""
        team = Team(name="my-team", organization="my-org", description="Test team")
        args = team.to_cli_args()

        assert "--name" in args
        assert "my-team" in args
        assert "--organization" in args
        assert "my-org" in args
        assert "--description" in args

    def test_team_with_members(self):
        """Test that members are included in to_cli_args (builder will handle separately)"""
        team = Team(
            name="my-team",
            organization="my-org",
            members=["user1@example.com", "user2@example.com"],
        )
        args = team.to_cli_args()

        # Members should be in the args (as a comma-separated list)
        # The builder will handle creating separate member commands
        assert "--members" in args
        idx = args.index("--members")
        assert args[idx + 1] == "user1@example.com,user2@example.com"


class TestOtherModels:
    """Test other models using base to_cli_args()"""

    def test_member_to_cli_args(self):
        """Test Member model"""
        member = Member(user="user@example.com", organization="my-org")
        args = member.to_cli_args()

        assert "--user" in args
        assert "user@example.com" in args
        assert "--organization" in args

    def test_participant_to_cli_args(self):
        """Test Participant model"""
        participant = Participant(
            name="user@example.com", type="member", workspace="org/workspace"
        )
        args = participant.to_cli_args()

        assert "--name" in args
        assert "user@example.com" in args
        assert "--type" in args
        assert "member" in args
        assert "--workspace" in args
        assert "org/workspace" in args

    def test_dataset_to_cli_args(self):
        """Test Dataset model"""
        dataset = Dataset(
            name="my-dataset",
            workspace="org/workspace",
            file_path="/path/to/dataset.csv",
        )
        args = dataset.to_cli_args()

        assert "--name" in args
        assert "my-dataset" in args
        assert "--workspace" in args
        assert "org/workspace" in args
        assert "--file-path" in args
        assert "/path/to/dataset.csv" in args

    def test_secret_to_cli_args(self):
        """Test Secret model"""
        secret = Secret(
            name="my-secret", workspace="org/workspace", value="secret-value"
        )
        args = secret.to_cli_args()

        assert "--name" in args
        assert "--workspace" in args
        assert "--value" in args

    def test_datalink_to_cli_args(self):
        """Test DataLink model"""
        datalink = DataLink(name="my-datalink", uri="s3://bucket/data", provider="aws")
        args = datalink.to_cli_args()

        assert "--name" in args
        assert "my-datalink" in args
        assert "--uri" in args
        assert "s3://bucket/data" in args
        assert "--provider" in args
        assert "aws" in args

    def test_studio_to_cli_args(self):
        """Test Studio model"""
        studio = Studio(name="my-studio", compute_env="my-compute-env")
        args = studio.to_cli_args()

        assert "--name" in args
        assert "my-studio" in args
        assert "--compute-env" in args
        assert "my-compute-env" in args


class TestEdgeCases:
    """Test edge cases and special scenarios"""

    def test_empty_strings_excluded(self):
        """Test that empty strings are still included (they're not None)"""
        org = Organization(
            name="test",
            full_name="Test",
            description="",  # Empty string
        )
        args = org.to_cli_args()

        # Empty string should still be included
        assert "--description" in args
        idx = args.index("--description")
        assert args[idx + 1] == ""

    def test_zero_values_included(self):
        """Test that zero values are included"""
        ce = ComputeEnv(
            type="aws-batch",
            config_mode="forge",
            name="test",
            workspace="org/ws",
            work_dir="s3://bucket",
            region="us-east-1",
            max_cpus=256,
            min_cpus=0,  # Zero should be included
        )
        args = ce.to_cli_args()

        assert "--min-cpus" in args
        idx = args.index("--min-cpus")
        assert args[idx + 1] == "0"

    def test_false_boolean_excluded(self):
        """Test that False boolean values are excluded"""
        pipeline = Pipeline(
            name="test",
            url="https://github.com/test/repo",
            workspace="org/ws",
            pull_latest=False,
        )
        args = pipeline.to_cli_args()

        # False values should not create flags
        assert "--pull-latest" not in args

    def test_hyphenated_field_names(self):
        """Test that field aliases with hyphens work correctly"""
        pipeline = Pipeline(
            name="test",
            url="https://github.com/test/repo",
            workspace="org/ws",
            compute_env="my-ce",  # Uses alias "compute-env"
            work_dir="s3://bucket",  # Uses alias "work-dir"
        )
        args = pipeline.to_cli_args()

        # Should use aliased names
        assert "--compute-env" in args
        assert "--work-dir" in args
        # Should not use Python names
        assert "--compute_env" not in args
        assert "--work_dir" not in args
