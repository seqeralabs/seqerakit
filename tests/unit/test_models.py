"""Unit tests for Pydantic models"""

import pytest
from pydantic import ValidationError
from seqerakit.models import (
    Organization,
    Workspace,
    Team,
    Label,
    Member,
    Participant,
    Credential,
    Dataset,
    Secret,
    Action,
    DataLink,
    Studio,
    Pipeline,
    ComputeEnv,
    Launch,
)


class TestOrganization:
    def test_valid_organization(self):
        org = Organization(name="test-org", full_name="Test Organization")
        assert org.name == "test-org"
        assert org.input_dict() == {
            "name": "test-org",
            "full-name": "Test Organization",
        }

    def test_organization_with_all_fields(self):
        org = Organization(
            name="test-org",
            full_name="Test Organization",
            description="Test description",
            location="Global",
            website="https://example.com",
        )
        result = org.input_dict()
        assert result["name"] == "test-org"
        assert result["description"] == "Test description"
        assert result["location"] == "Global"

    def test_organization_missing_required_field(self):
        with pytest.raises(ValidationError):
            Organization(name="test-org")  # Missing full_name


class TestWorkspace:
    def test_valid_workspace(self):
        ws = Workspace(
            name="test-ws", organization="test-org", full_name="Test Workspace"
        )
        assert ws.name == "test-ws"
        assert ws.input_dict()["organization"] == "test-org"

    def test_workspace_with_visibility(self):
        ws = Workspace(
            name="test-ws",
            organization="test-org",
            full_name="Test Workspace",
            visibility="PRIVATE",
        )
        assert ws.input_dict()["visibility"] == "PRIVATE"


class TestTeam:
    def test_valid_team(self):
        team = Team(name="test-team", organization="test-org")
        assert team.name == "test-team"
        assert team.organization == "test-org"

    def test_team_with_members(self):
        team = Team(
            name="test-team",
            organization="test-org",
            members=["user1@example.com", "user2@example.com"],
        )
        assert len(team.members) == 2


class TestLabel:
    def test_valid_label(self):
        label = Label(name="test-label", workspace="org/workspace", value="test-value")
        assert label.name == "test-label"
        assert label.workspace == "org/workspace"

    def test_label_without_value(self):
        label = Label(name="test-label", workspace="org/workspace")
        assert label.value is None


class TestMember:
    def test_valid_member(self):
        member = Member(user="user@example.com", organization="test-org")
        assert member.user == "user@example.com"


class TestParticipant:
    def test_valid_participant(self):
        participant = Participant(
            name="user@example.com", type="MEMBER", workspace="org/ws"
        )
        assert participant.type == "MEMBER"


class TestCredential:
    def test_aws_credential(self):
        cred = Credential(
            type="aws",
            name="aws-creds",
            access_key="AKIAIOSFODNN7EXAMPLE",
            secret_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
        )
        assert cred.type == "aws"
        result = cred.input_dict()
        assert result["access-key"] == "AKIAIOSFODNN7EXAMPLE"

    def test_google_credential(self):
        cred = Credential(type="google", name="gcp-creds", key="/path/to/key.json")
        assert cred.key == "/path/to/key.json"

    def test_azure_credential(self):
        cred = Credential(
            type="azure",
            name="azure-creds",
            batch_name="mybatch",
            batch_key="key123",
            storage_name="mystorage",
            storage_key="storagekey123",
        )
        result = cred.input_dict()
        assert result["batch-name"] == "mybatch"
        assert result["storage-name"] == "mystorage"


class TestDataset:
    def test_valid_dataset(self):
        dataset = Dataset(
            name="test-dataset",
            workspace="org/ws",
            file_path="/path/to/data.csv",
            header=True,
        )
        assert dataset.name == "test-dataset"
        assert dataset.header is True


class TestSecret:
    def test_valid_secret(self):
        secret = Secret(name="my-secret", workspace="org/ws", value="secret-value")
        assert secret.name == "my-secret"


class TestAction:
    def test_github_action(self):
        action = Action(type="github", name="test-action", pipeline="my-pipeline")
        assert action.type == "github"

    def test_tower_action(self):
        action = Action(type="tower", endpoint="https://example.com/webhook")
        assert action.endpoint == "https://example.com/webhook"


class TestDataLink:
    def test_valid_datalink(self):
        dl = DataLink(
            name="test-datalink",
            uri="s3://bucket/path",
            provider="aws",
            workspace="org/ws",
        )
        assert dl.provider == "aws"
        assert dl.uri == "s3://bucket/path"


class TestStudio:
    def test_valid_studio(self):
        studio = Studio(
            name="test-studio",
            compute_env="my-compute-env",
            template="public/rstudio:latest",
            cpu=4,
            memory=8192,
        )
        result = studio.input_dict()
        assert result["compute-env"] == "my-compute-env"
        assert result["cpu"] == 4

    def test_studio_with_mount_data(self):
        studio = Studio(
            name="test-studio",
            compute_env="my-compute-env",
            mount_data_ids="v1-user-123",
        )
        result = studio.input_dict()
        assert result["mount-data-ids"] == "v1-user-123"


class TestPipeline:
    def test_valid_pipeline(self):
        pipeline = Pipeline(
            name="test-pipeline",
            url="https://github.com/nextflow-io/hello",
            workspace="org/ws",
        )
        assert pipeline.name == "test-pipeline"
        assert pipeline.url == "https://github.com/nextflow-io/hello"

    def test_pipeline_with_all_options(self):
        pipeline = Pipeline(
            name="test-pipeline",
            url="https://github.com/nextflow-io/hello",
            workspace="org/ws",
            compute_env="my-compute-env",
            work_dir="s3://bucket/work",
            profile="test",
            revision="main",
            pull_latest=True,
        )
        result = pipeline.input_dict()
        assert result["compute-env"] == "my-compute-env"
        assert result["work-dir"] == "s3://bucket/work"
        assert result["pull-latest"] is True


class TestComputeEnv:
    def test_valid_compute_env(self):
        ce = ComputeEnv(
            type="aws-batch",
            config_mode="forge",
            name="test-ce",
            work_dir="s3://bucket/work",
            region="us-east-1",
            max_cpus=100,
        )
        assert ce.type == "aws-batch"
        result = ce.input_dict()
        assert result["config-mode"] == "forge"
        assert result["max-cpus"] == 100

    def test_compute_env_with_fusion_and_wave(self):
        ce = ComputeEnv(
            type="aws-batch",
            config_mode="forge",
            name="test-ce",
            work_dir="s3://bucket/work",
            region="us-east-1",
            max_cpus=100,
            fusion_v2=True,
            wave=True,
            fargate=True,
        )
        result = ce.input_dict()
        assert result["fusion-v2"] is True
        assert result["wave"] is True
        assert result["fargate"] is True

    def test_compute_env_missing_required_field(self):
        with pytest.raises(ValidationError):
            ComputeEnv(
                type="aws-batch",
                config_mode="forge",
                name="test-ce",
                # Missing work_dir, region, max_cpus
            )


class TestLaunch:
    def test_valid_launch(self):
        launch = Launch(
            pipeline="https://github.com/nextflow-io/hello",
            workspace="org/ws",
            compute_env="my-compute-env",
        )
        assert launch.pipeline == "https://github.com/nextflow-io/hello"

    def test_launch_with_params(self):
        launch = Launch(
            pipeline="my-pipeline",
            workspace="org/ws",
            params={"input": "s3://bucket/data", "outdir": "s3://bucket/results"},
        )
        assert launch.params["input"] == "s3://bucket/data"


class TestInputDictExcludesNone:
    """Test that input_dict() excludes None values"""

    def test_organization_excludes_none(self):
        org = Organization(name="test", full_name="Test Org")
        result = org.input_dict()
        assert "description" not in result
        assert "location" not in result

    def test_pipeline_excludes_none(self):
        pipeline = Pipeline(name="test", url="https://example.com")
        result = pipeline.input_dict()
        assert "workspace" not in result
        assert "compute-env" not in result


class TestDumpDictIncludesNone:
    """Test that dump_dict() includes None values"""

    def test_organization_includes_none(self):
        org = Organization(name="test", full_name="Test Org")
        result = org.dump_dict()
        assert "description" in result
        assert result["description"] is None

    def test_pipeline_includes_none(self):
        pipeline = Pipeline(name="test", url="https://example.com")
        result = pipeline.dump_dict()
        assert "workspace" in result
        assert result["workspace"] is None
