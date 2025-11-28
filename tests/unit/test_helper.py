"""Simplified unit tests for helper functions with Pydantic models"""
from unittest.mock import patch, mock_open
from seqerakit import helper
from seqerakit.on_exists import OnExists
import yaml
import pytest
from io import StringIO


@pytest.fixture
def mock_yaml_file(mocker):
    """Fixture to mock a YAML file"""

    def _mock_yaml_file(test_data, file_name="mock_file.yaml"):
        yaml_content = yaml.dump(test_data, default_flow_style=False)
        mock_file = mock_open(read_data=yaml_content)
        mocker.patch("builtins.open", mock_file)
        return file_name

    return _mock_yaml_file


@pytest.fixture
def mock_seqera_platform(mocker):
    """Fixture for mocked SeqeraPlatform"""
    mock_sp = mocker.Mock()
    mock_context = mocker.MagicMock()
    mock_context.__enter__ = mocker.Mock()
    mock_context.__exit__ = mocker.Mock()
    mock_sp.suppress_output.return_value = mock_context
    return mock_sp


class TestValidation:
    """Test Pydantic validation in parse_all_yaml"""

    def test_valid_organization(self, mock_yaml_file):
        test_data = {
            "organizations": [
                {
                    "name": "test_org",
                    "full-name": "Test Organization",
                    "description": "Test description",
                }
            ]
        }
        file_path = mock_yaml_file(test_data)
        result = helper.parse_all_yaml([file_path])

        assert "organizations" in result
        assert len(result["organizations"]) == 1
        # Verify validation occurred and fields are present
        assert result["organizations"][0]["on_exists"] == OnExists.FAIL

    def test_valid_workspace(self, mock_yaml_file):
        test_data = {
            "workspaces": [
                {
                    "name": "test_ws",
                    "full-name": "Test Workspace",
                    "organization": "test_org",
                }
            ]
        }
        file_path = mock_yaml_file(test_data)
        result = helper.parse_all_yaml([file_path])

        assert "workspaces" in result
        assert len(result["workspaces"]) == 1

    def test_valid_pipeline(self, mock_yaml_file):
        test_data = {
            "pipelines": [
                {
                    "name": "test_pipeline",
                    "url": "https://github.com/nextflow-io/hello",
                    "workspace": "org/workspace",
                }
            ]
        }
        file_path = mock_yaml_file(test_data)
        result = helper.parse_all_yaml([file_path])

        assert "pipelines" in result
        assert len(result["pipelines"]) == 1

    def test_invalid_pipeline_missing_url(self, mock_yaml_file):
        """Test that validation catches missing required fields"""
        test_data = {
            "pipelines": [
                {
                    "name": "test_pipeline",
                    # Missing required 'url' field
                    "workspace": "org/workspace",
                }
            ]
        }
        file_path = mock_yaml_file(test_data)

        with pytest.raises(ValueError, match="Validation error in pipelines"):
            helper.parse_all_yaml([file_path])

    def test_invalid_organization_missing_full_name(self, mock_yaml_file):
        """Test that validation catches missing required fields"""
        test_data = {
            "organizations": [
                {
                    "name": "test_org",
                    # Missing required 'full-name' field
                }
            ]
        }
        file_path = mock_yaml_file(test_data)

        with pytest.raises(ValueError, match="Validation error in organizations"):
            helper.parse_all_yaml([file_path])


class TestOnExists:
    """Test on_exists handling"""

    def test_on_exists_overwrite(self, mock_yaml_file):
        test_data = {
            "organizations": [
                {
                    "name": "test_org",
                    "full-name": "Test Org",
                    "on_exists": "overwrite",
                }
            ]
        }
        file_path = mock_yaml_file(test_data)
        result = helper.parse_all_yaml([file_path])

        assert result["organizations"][0]["on_exists"] == OnExists.OVERWRITE

    def test_on_exists_ignore(self, mock_yaml_file):
        test_data = {
            "organizations": [
                {"name": "test_org", "full-name": "Test Org", "on_exists": "ignore"}
            ]
        }
        file_path = mock_yaml_file(test_data)
        result = helper.parse_all_yaml([file_path])

        assert result["organizations"][0]["on_exists"] == OnExists.IGNORE

    def test_overwrite_flag_legacy(self, mock_yaml_file):
        """Test legacy 'overwrite' boolean flag"""
        test_data = {
            "organizations": [
                {"name": "test_org", "full-name": "Test Org", "overwrite": True}
            ]
        }
        file_path = mock_yaml_file(test_data)
        result = helper.parse_all_yaml([file_path])

        assert result["organizations"][0]["on_exists"] == OnExists.OVERWRITE


class TestDuplicateNames:
    """Test duplicate name detection"""

    def test_duplicate_pipeline_names(self, mock_yaml_file):
        test_data = {
            "pipelines": [
                {
                    "name": "duplicate",
                    "url": "https://github.com/test/repo1",
                },
                {
                    "name": "duplicate",
                    "url": "https://github.com/test/repo2",
                },
            ]
        }
        file_path = mock_yaml_file(test_data)

        with pytest.raises(ValueError, match="Duplicate name"):
            helper.parse_all_yaml([file_path])

    def test_duplicate_organization_names(self, mock_yaml_file):
        test_data = {
            "organizations": [
                {"name": "duplicate", "full-name": "Org 1"},
                {"name": "duplicate", "full-name": "Org 2"},
            ]
        }
        file_path = mock_yaml_file(test_data)

        with pytest.raises(ValueError, match="Duplicate name"):
            helper.parse_all_yaml([file_path])


class TestDatasetResolution:
    """Test dataset URL resolution"""

    def test_resolve_dataset_reference(self, mock_seqera_platform):
        mock_seqera_platform.datasets.return_value = {
            "datasetUrl": "https://api.cloud.seqera.io/datasets/123"
        }

        params = {"dataset": "my_dataset"}
        result = helper.resolve_dataset_reference(
            params, "org/workspace", mock_seqera_platform
        )

        assert "dataset" not in result
        assert result["input"] == "https://api.cloud.seqera.io/datasets/123"

    def test_resolve_dataset_error(self, mock_seqera_platform):
        mock_seqera_platform.datasets.return_value = None

        params = {"dataset": "nonexistent"}

        with pytest.raises(ValueError, match="No URL found"):
            helper.resolve_dataset_reference(
                params, "org/workspace", mock_seqera_platform
            )


class TestTargets:
    """Test selective resource processing"""

    def test_targets_specified(self):
        yaml_data = """
organizations:
  - name: org1
    full-name: Organization 1
workspaces:
  - name: workspace1
    organization: org1
    full-name: Workspace 1
pipelines:
  - name: pipeline1
    url: https://github.com/test/repo
"""
        with patch("builtins.open", lambda f, _: StringIO(yaml_data)):
            result = helper.parse_all_yaml(
                ["dummy.yaml"], targets="organizations,workspaces"
            )

        assert "organizations" in result
        assert "workspaces" in result
        assert "pipelines" not in result

    def test_no_targets_all_processed(self):
        yaml_data = """
organizations:
  - name: org1
    full-name: Organization 1
workspaces:
  - name: workspace1
    organization: org1
    full-name: Workspace 1
"""
        with patch("builtins.open", lambda f, _: StringIO(yaml_data)):
            result = helper.parse_all_yaml(["dummy.yaml"])

        assert "organizations" in result
        assert "workspaces" in result


class TestEmptyFiles:
    """Test error handling for empty files"""

    def test_empty_yaml_file(self, mock_yaml_file):
        test_data = {}
        file_path = mock_yaml_file(test_data)

        with pytest.raises(ValueError, match="empty or does not contain valid data"):
            helper.parse_all_yaml([file_path])

    def test_empty_stdin(self):
        with patch("sys.stdin", StringIO("")):
            with pytest.raises(
                ValueError, match="empty or does not contain valid YAML data"
            ):
                helper.parse_all_yaml(["-"])


class TestStdin:
    """Test stdin input"""

    def test_stdin_yaml(self):
        yaml_data = """
organizations:
  - name: test_org
    full-name: Test Organization
"""
        with patch("sys.stdin", StringIO(yaml_data)):
            result = helper.parse_all_yaml(["-"])

        assert "organizations" in result
        assert len(result["organizations"]) == 1


class TestProcessParamsDict:
    """Test params dictionary processing"""

    def test_basic_params(self):
        params = {"input": "s3://bucket/data", "outdir": "s3://bucket/results"}
        result = helper.process_params_dict(params)

        assert len(result) == 2
        assert result[0] == "--params-file"
        assert result[1].endswith(".yaml")

    def test_params_with_file_path(self):
        result = helper.process_params_dict(None, params_file_path="path/to/params.yaml")
        assert result == ["--params-file", "path/to/params.yaml"]

    def test_empty_params(self):
        assert helper.process_params_dict(None) == []
        assert helper.process_params_dict({}) == []

    def test_params_with_dataset_resolution(self, mock_seqera_platform):
        mock_seqera_platform.datasets.return_value = {
            "datasetUrl": "https://api.cloud.seqera.io/datasets/123"
        }

        params = {"dataset": "my_dataset", "outdir": "s3://bucket/results"}
        result = helper.process_params_dict(
            params, workspace="org/workspace", sp=mock_seqera_platform
        )

        assert len(result) == 2
        assert result[0] == "--params-file"

        # Verify resolved params in temp file
        with open(result[1], "r") as f:
            written_params = yaml.safe_load(f)
            assert written_params["input"] == "https://api.cloud.seqera.io/datasets/123"
            assert "dataset" not in written_params
