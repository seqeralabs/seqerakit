from unittest.mock import patch, mock_open
from seqerakit import helper
from seqerakit.on_exists import OnExists
import yaml
import pytest
from io import StringIO
from unittest.mock import Mock


# Fixture to mock a YAML file
@pytest.fixture
def mock_yaml_file(mocker):
    def _mock_yaml_file(test_data, file_name="mock_file.yaml"):
        # Convert test data to YAML format
        yaml_content = yaml.dump(test_data, default_flow_style=False)
        mock_file = mock_open(read_data=yaml_content)
        mocker.patch("builtins.open", mock_file)

        return file_name

    return _mock_yaml_file


# Fixture to mock SeqeraPlatform instance
@pytest.fixture
def mock_seqera_platform(mocker):
    """Fixture for mocked SeqeraPlatform with common setup."""
    mock_sp = mocker.Mock()

    # Mock the suppress_output context manager
    mock_context = mocker.MagicMock()
    mock_context.__enter__ = mocker.Mock()
    mock_context.__exit__ = mocker.Mock()
    mock_sp.suppress_output.return_value = mock_context

    return mock_sp


def test_create_mock_organization_yaml(mock_yaml_file):
    test_data = {
        "organizations": [
            {
                "name": "test_organization1",
                "full-name": "My test organization 1",
                "description": "My test organization 1",
                "location": "Global",
                "url": "https://example.com",
                "on_exists": "overwrite",
            }
        ]
    }
    expected_block_output = [
        {
            "cmd_args": [
                "--description",
                "My test organization 1",
                "--full-name",
                "My test organization 1",
                "--location",
                "Global",
                "--name",
                "test_organization1",
                "--url",
                "https://example.com",
            ],
            "on_exists": OnExists.OVERWRITE,
        }
    ]
    file_path = mock_yaml_file(test_data)
    print(f"debug - file_path: {file_path}")
    result = helper.parse_all_yaml([file_path])

    assert "organizations" in result
    assert result["organizations"] == expected_block_output


def test_create_mock_workspace_yaml(mock_yaml_file):
    test_data = {
        "workspaces": [
            {
                "name": "test_workspace1",
                "full-name": "My test workspace 1",
                "organization": "my_organization",
                "description": "My test workspace 1",
                "visibility": "PRIVATE",
                "on_exists": "overwrite",
            }
        ]
    }
    expected_block_output = [
        {
            "cmd_args": [
                "--description",
                "My test workspace 1",
                "--full-name",
                "My test workspace 1",
                "--name",
                "test_workspace1",
                "--organization",
                "my_organization",
                "--visibility",
                "PRIVATE",
            ],
            "on_exists": OnExists.OVERWRITE,
        }
    ]

    file_path = mock_yaml_file(test_data)
    result = helper.parse_all_yaml([file_path])

    assert "workspaces" in result
    assert result["workspaces"] == expected_block_output


def test_create_mock_dataset_yaml(mock_yaml_file):
    test_data = {
        "datasets": [
            {
                "name": "test_dataset1",
                "description": "My test dataset 1",
                "workspace": "my_organization/my_workspace",
                "header": True,
                "file-path": "./examples/yaml/datasets/samples.csv",
                "on_exists": "overwrite",
            }
        ]
    }
    expected_block_output = [
        {
            "cmd_args": [
                "./examples/yaml/datasets/samples.csv",
                "--name",
                "test_dataset1",
                "--workspace",
                "my_organization/my_workspace",
                "--description",
                "My test dataset 1",
                "--header",
            ],
            "on_exists": OnExists.OVERWRITE,
        }
    ]

    file_path = mock_yaml_file(test_data)
    result = helper.parse_all_yaml([file_path])

    assert "datasets" in result
    assert result["datasets"] == expected_block_output


def test_create_mock_computeevs_source_yaml(mock_yaml_file, mock_seqera_platform):
    test_data = {
        "compute-envs": [
            {
                "name": "test_computeenv",
                "workspace": "my_organization/my_workspace",
                "credentials": "my_credentials",
                "file-path": "./computeenvs/computeenv.json",
                "wait": "AVAILABLE",
                "fusion-v2": True,
                "fargate": False,
                "on_exists": "overwrite",
            }
        ],
    }

    expected_block_output = [
        {
            "cmd_args": [
                "./computeenvs/computeenv.json",
                "--credentials",
                "my_credentials",
                "--fusion-v2",
                "--name",
                "test_computeenv",
                "--wait",
                "AVAILABLE",
                "--workspace",
                "my_organization/my_workspace",
            ],
            "on_exists": OnExists.OVERWRITE,
        }
    ]

    file_path = mock_yaml_file(test_data)
    result = helper.parse_all_yaml([file_path], sp=mock_seqera_platform)

    assert "compute-envs" in result
    assert result["compute-envs"] == expected_block_output


def test_create_mock_computeevs_cli_yaml(mock_yaml_file):
    test_data = {
        "compute-envs": [
            {
                "name": "test_computeenv",
                "workspace": "my_organization/my_workspace",
                "credentials": "my_credentials",
                "type": "aws-batch",
                "config-mode": "forge",
                "wait": "AVAILABLE",
            }
        ],
    }

    # Get the actual result
    file_path = mock_yaml_file(test_data)
    result = helper.parse_all_yaml([file_path])
    assert "compute-envs" in result
    actual_args = result["compute-envs"][0]["cmd_args"]

    expected_args = {
        "aws-batch",  # type
        "forge",  # config-mode
        "--credentials",
        "my_credentials",
        "--name",
        "test_computeenv",
        "--wait",
        "AVAILABLE",
        "--workspace",
        "my_organization/my_workspace",
    }

    # set for order-independent comparison
    actual_args_set = set(actual_args)

    assert all(arg in actual_args_set for arg in expected_args)
    assert result["compute-envs"][0]["on_exists"] == OnExists.FAIL
    assert len(actual_args) == len(expected_args)


def test_create_mock_pipeline_add_yaml(mock_yaml_file):
    test_data = {
        "pipelines": [
            {
                "name": "test_pipeline1",
                "url": "https://github.com/nf-core/test_pipeline1",
                "workspace": "my_organization/my_workspace",
                "description": "My test pipeline 1",
                "compute-env": "my_computeenv",
                "work-dir": "s3://work",
                "profile": "test",
                "params-file": "./examples/yaml/pipelines/test_pipeline1/params.yaml",
                "config": "./examples/yaml/pipelines/test_pipeline1/config.txt",
                "pre-run": "./examples/yaml/pipelines/test_pipeline1/pre_run.sh",
                "revision": "master",
                "on_exists": "overwrite",
                "stub-run": True,
            }
        ]
    }

    file_path = mock_yaml_file(test_data)
    result = helper.parse_all_yaml([file_path])

    assert "pipelines" in result
    actual_args = result["pipelines"][0]["cmd_args"]

    expected_pairs = {
        "--compute-env": "my_computeenv",
        "--config": "./examples/yaml/pipelines/test_pipeline1/config.txt",
        "--description": "My test pipeline 1",
        "--name": "test_pipeline1",
        "--pre-run": "./examples/yaml/pipelines/test_pipeline1/pre_run.sh",
        "--profile": "test",
        "--revision": "master",
        "--work-dir": "s3://work",
        "--workspace": "my_organization/my_workspace",
        "--params-file": "./examples/yaml/pipelines/test_pipeline1/params.yaml",
    }

    assert "--stub-run" in actual_args
    assert "https://github.com/nf-core/test_pipeline1" in actual_args

    for key, value in expected_pairs.items():
        key_index = actual_args.index(key)
        assert actual_args[key_index + 1] == value

    # Check overwrite flag
    assert result["pipelines"][0]["on_exists"] == OnExists.OVERWRITE


def test_create_mock_teams_yaml(mock_yaml_file):
    test_data = {
        "teams": [
            {
                "name": "test_team1",
                "organization": "my_organization",
                "description": "My test team 1",
                "members": ["user1@org.io"],
                "on_exists": "overwrite",
            },
        ]
    }
    expected_block_output = [
        {
            "cmd_args": (
                [
                    "--description",
                    "My test team 1",
                    "--name",
                    "test_team1",
                    "--organization",
                    "my_organization",
                ],
                [
                    [
                        "--team",
                        "test_team1",
                        "--organization",
                        "my_organization",
                        "add",
                        "--member",
                        "user1@org.io",
                    ]
                ],
            ),
            "on_exists": OnExists.OVERWRITE,
        }
    ]

    file_path = mock_yaml_file(test_data)
    result = helper.parse_all_yaml([file_path])

    assert "teams" in result
    assert result["teams"] == expected_block_output


def test_create_mock_members_yaml(mock_yaml_file):
    test_data = {"members": [{"user": "bob@myorg.io", "organization": "myorg"}]}
    expected_block_output = [
        {
            "cmd_args": [
                "--organization",
                "myorg",
                "--user",
                "bob@myorg.io",
            ],
            "on_exists": OnExists.FAIL,
        }
    ]
    file_path = mock_yaml_file(test_data)
    result = helper.parse_all_yaml([file_path])

    assert "members" in result
    assert result["members"] == expected_block_output


def test_create_mock_studios_yaml(mock_yaml_file):
    test_data = {
        "studios": [
            {
                "name": "test_studio1",
                "workspace": "my_organization/my_workspace",
                "template": "public.seqera.io/public/data-studio-rstudio:4.4.1",
                "compute-env": "my_computeenv",
                "cpu": 2,
                "memory": 4096,
                "autoStart": False,
                "on_exists": "overwrite",
                "mount-data-ids": "v1-user-bf73f9d33997f93a20ee3e6911779951",
            }
        ]
    }

    expected_block_output = [
        {
            "cmd_args": [
                "--compute-env",
                "my_computeenv",
                "--cpu",
                "2",
                "--memory",
                "4096",
                "--mount-data-ids",
                "v1-user-bf73f9d33997f93a20ee3e6911779951",
                "--name",
                "test_studio1",
                "--template",
                "public.seqera.io/public/data-studio-rstudio:4.4.1",
                "--workspace",
                "my_organization/my_workspace",
            ],
            "on_exists": OnExists.OVERWRITE,
        }
    ]

    file_path = mock_yaml_file(test_data)
    result = helper.parse_all_yaml([file_path])
    print(f"debug - result: {result}")
    assert "studios" in result
    assert result["studios"] == expected_block_output


def test_create_mock_data_links_yaml(mock_yaml_file):
    test_data = {
        "data-links": [
            {
                "name": "test_data_link1",
                "workspace": "my_organization/my_workspace",
                "provider": "aws",
                "credentials": "my_credentials",
                "uri": "s3://scidev-playground-eu-west-2/esha/nf-core-scrnaseq/",
                "on_exists": "overwrite",
            }
        ]
    }
    expected_block_output = [
        {
            "cmd_args": [
                "--credentials",
                "my_credentials",
                "--name",
                "test_data_link1",
                "--provider",
                "aws",
                "--uri",
                "s3://scidev-playground-eu-west-2/esha/nf-core-scrnaseq/",
                "--workspace",
                "my_organization/my_workspace",
            ],
            "on_exists": OnExists.OVERWRITE,
        }
    ]
    file_path = mock_yaml_file(test_data)
    result = helper.parse_all_yaml([file_path])
    assert "data-links" in result
    assert result["data-links"] == expected_block_output


def test_empty_yaml_file(mock_yaml_file):
    test_data = {}
    file_path = mock_yaml_file(test_data)

    with pytest.raises(ValueError) as e:
        helper.parse_all_yaml([file_path])
    assert f"The file '{file_path}' is empty or does not contain valid data." in str(
        e.value
    )


def test_empty_stdin_file():
    # Prepare the mock to simulate empty stdin
    with patch("sys.stdin", StringIO("")):
        # Use '-' to indicate that stdin should be read
        with pytest.raises(ValueError) as e:
            helper.parse_all_yaml(["-"])
        assert (
            "The input from stdin is empty or does not contain valid YAML data."
            in str(e.value)
        )


def test_stdin_yaml_file():
    # Prepare the mock to simulate stdin
    yaml_data = """
compute-envs:
  - name: test_computeenv
    config-mode: forge
    workspace: my_organization/my_workspace
    credentials: my_credentials
    type: aws-batch
    wait: AVAILABLE
        """
    with patch("sys.stdin", StringIO(yaml_data)):
        result = helper.parse_all_yaml(["-"])

    expected_block_output = [
        {
            "cmd_args": [
                "aws-batch",
                "forge",
                "--name",
                "test_computeenv",
                "--workspace",
                "my_organization/my_workspace",
                "--credentials",
                "my_credentials",
                "--wait",
                "AVAILABLE",
            ],
            "on_exists": OnExists.FAIL,
        }
    ]
    assert "compute-envs" in result
    assert result["compute-envs"] == expected_block_output


def test_error_type_yaml_file(mock_yaml_file):
    test_data = {
        "compute-envs": [
            {
                "name": "test_computeenv",
                "workspace": "my_organization/my_workspace",
                "credentials": "my_credentials",
                "wait": "AVAILABLE",
            }
        ],
    }
    file_path = mock_yaml_file(test_data)

    with pytest.raises(ValueError) as e:
        helper.parse_all_yaml([file_path])
    assert (
        "Please specify at least 'type' or 'file-path' for creating the resource."
        in str(e.value)
    )


def test_error_duplicate_name_yaml_file(mock_yaml_file):
    test_data = {
        "compute-envs": [
            {
                "name": "test_computeenv",
                "workspace": "my_organization/my_workspace",
                "credentials": "my_credentials",
                "type": "aws-batch",
                "config-mode": "forge",
                "wait": "AVAILABLE",
            },
            {
                "name": "test_computeenv",
                "workspace": "my_organization/my_workspace",
                "credentials": "my_credentials",
                "type": "aws-batch",
                "config-mode": "forge",
                "wait": "AVAILABLE",
            },
        ],
    }
    file_path = mock_yaml_file(test_data)

    with pytest.raises(ValueError) as e:
        helper.parse_all_yaml([file_path])
    assert (
        "Duplicate name key specified in config file for "
        "compute-envs: test_computeenv in my_organization/my_workspace. "
        "Please specify a unique value." in str(e.value)
    )


def test_duplicate_name_different_workspaces_allowed(mock_yaml_file):
    """Test that duplicate names are allowed across different workspaces."""
    test_data = {
        "compute-envs": [
            {
                "name": "SharedCE",
                "workspace": "my_organization/team1",
                "credentials": "my_credentials",
                "type": "aws-batch",
                "config-mode": "forge",
            },
            {
                "name": "SharedCE",
                "workspace": "my_organization/team2",
                "credentials": "my_credentials",
                "type": "aws-batch",
                "config-mode": "forge",
            },
            {
                "name": "SharedCE",
                "workspace": "my_organization/team3",
                "credentials": "my_credentials",
                "type": "aws-batch",
                "config-mode": "forge",
            },
        ],
    }
    file_path = mock_yaml_file(test_data)

    # Should not raise - duplicate names are allowed in different workspaces
    result = helper.parse_all_yaml([file_path])
    assert "compute-envs" in result
    assert len(result["compute-envs"]) == 3


def test_targets_specified():
    #  mock YAML data
    yaml_data = """
organizations:
  - name: org1
    description: Organization 1
workspaces:
  - name: workspace1
    organization: org1
    description: Workspace 1
pipelines:
  - name: pipeline1
    workspace: workspace1
    description: Pipeline 1
"""
    with patch("builtins.open", lambda f, _: StringIO(yaml_data)):
        result = helper.parse_all_yaml(
            ["dummy_path.yaml"], targets="organizations,workspaces"
        )

    expected_organizations_output = [
        {
            "cmd_args": ["--name", "org1", "--description", "Organization 1"],
            "on_exists": OnExists.FAIL,
        }
    ]
    expected_workspaces_output = [
        {
            "cmd_args": [
                "--name",
                "workspace1",
                "--organization",
                "org1",
                "--description",
                "Workspace 1",
            ],
            "on_exists": OnExists.FAIL,
        }
    ]
    # Check that only 'organizations' and 'workspaces' are in the result
    assert "organizations" in result
    assert result["organizations"] == expected_organizations_output
    assert "workspaces" in result
    assert result["workspaces"] == expected_workspaces_output
    assert "pipelines" not in result


def test_no_targets_specified():
    yaml_data = """
organizations:
  - name: org1
    description: Organization 1
workspaces:
  - name: workspace1
    organization: org1
    description: Workspace 1
pipelines:
  - name: pipeline1
    workspace: workspace1
    description: Pipeline 1
"""
    with patch("builtins.open", lambda f, _: StringIO(yaml_data)):
        result = helper.parse_all_yaml(["dummy_path.yaml"])

    # Check that all blocks are in the result
    assert "organizations" in result
    assert "workspaces" in result
    assert "pipelines" in result


def test_target_with_name_filter():
    """Test --target option filters resources by name."""
    yaml_data = """
pipelines:
  - name: pipeline1
    workspace: workspace1
    description: Pipeline 1
  - name: pipeline2
    workspace: workspace1
    description: Pipeline 2
  - name: pipeline3
    workspace: workspace1
    description: Pipeline 3
"""
    with patch("builtins.open", lambda f, _: StringIO(yaml_data)):
        result = helper.parse_all_yaml(
            ["dummy_path.yaml"], target=["pipelines=pipeline1"]
        )

    assert "pipelines" in result
    assert len(result["pipelines"]) == 1
    # Check that only pipeline1 is in the result
    cmd_args = result["pipelines"][0]["cmd_args"]
    assert "--name" in cmd_args
    name_index = cmd_args.index("--name")
    assert cmd_args[name_index + 1] == "pipeline1"


def test_target_with_multiple_names():
    """Test --target option with comma-separated names."""
    yaml_data = """
pipelines:
  - name: pipeline1
    workspace: workspace1
    description: Pipeline 1
  - name: pipeline2
    workspace: workspace1
    description: Pipeline 2
  - name: pipeline3
    workspace: workspace1
    description: Pipeline 3
"""
    with patch("builtins.open", lambda f, _: StringIO(yaml_data)):
        result = helper.parse_all_yaml(
            ["dummy_path.yaml"], target=["pipelines=pipeline1,pipeline3"]
        )

    assert "pipelines" in result
    assert len(result["pipelines"]) == 2

    # Extract names from results
    names = []
    for pipeline in result["pipelines"]:
        cmd_args = pipeline["cmd_args"]
        name_index = cmd_args.index("--name")
        names.append(cmd_args[name_index + 1])

    assert "pipeline1" in names
    assert "pipeline3" in names
    assert "pipeline2" not in names


def test_target_multiple_resource_types():
    """Test multiple --target options for different resource types."""
    yaml_data = """
organizations:
  - name: org1
    description: Organization 1
  - name: org2
    description: Organization 2
pipelines:
  - name: pipeline1
    workspace: workspace1
    description: Pipeline 1
  - name: pipeline2
    workspace: workspace1
    description: Pipeline 2
"""
    with patch("builtins.open", lambda f, _: StringIO(yaml_data)):
        result = helper.parse_all_yaml(
            ["dummy_path.yaml"],
            target=["organizations=org1", "pipelines=pipeline2"],
        )

    assert "organizations" in result
    assert len(result["organizations"]) == 1
    assert "pipelines" in result
    assert len(result["pipelines"]) == 1

    # Verify correct items were selected
    org_args = result["organizations"][0]["cmd_args"]
    assert org_args[org_args.index("--name") + 1] == "org1"

    pipeline_args = result["pipelines"][0]["cmd_args"]
    assert pipeline_args[pipeline_args.index("--name") + 1] == "pipeline2"


def test_process_params_dict_basic():
    """Test basic params dictionary processing without dataset resolution."""
    params = {"input": "s3://bucket/data", "outdir": "s3://bucket/results"}

    result = helper.process_params_dict(params)
    assert len(result) == 2
    assert result[0] == "--params-file"
    # The second argument should be a path to a temp file
    assert result[1].endswith(".yaml")


def test_process_params_dict_with_file_path():
    result = helper.process_params_dict(None, params_file_path="path/to/params.yaml")
    assert result == ["--params-file", "path/to/params.yaml"]


def test_process_params_dict_empty():
    assert helper.process_params_dict(None) == []
    assert helper.process_params_dict({}) == []


def test_resolve_dataset_reference(mocker, mock_yaml_file, mock_seqera_platform):
    """Test dataset URL resolution."""
    mock_seqera_platform.datasets.return_value = {
        "datasetUrl": "https://api.cloud.seqera.io/datasets/123"
    }

    params = {"dataset": "my_dataset_name"}
    mock_yaml_file(params, "params.yaml")

    result = helper.resolve_dataset_reference(
        params, "org/workspace", mock_seqera_platform
    )

    assert "dataset" not in result
    assert result["input"] == "https://api.cloud.seqera.io/datasets/123"

    mock_seqera_platform.datasets.assert_called_once_with(
        "url", "-n", "my_dataset_name", "-w", "org/workspace"
    )


def test_resolve_dataset_reference_error(mocker, mock_seqera_platform):
    """Test dataset resolution error handling."""
    mock_seqera_platform.datasets.return_value = None

    params = {"dataset": "nonexistent_dataset"}
    workspace = "org/workspace"

    with pytest.raises(
        ValueError, match="No URL found for dataset 'nonexistent_dataset'"
    ):
        helper.resolve_dataset_reference(params, workspace, mock_seqera_platform)


def test_process_params_dict_with_dataset_resolution(mocker, mock_seqera_platform):
    """Test full params processing with dataset resolution."""
    mock_seqera_platform.datasets.return_value = {
        "datasetUrl": "https://api.cloud.seqera.io/datasets/123"
    }

    params = {"dataset": "my_dataset", "outdir": "s3://bucket/results"}

    result = helper.process_params_dict(
        params, workspace="org/workspace", sp=mock_seqera_platform
    )

    assert len(result) == 2
    assert result[0] == "--params-file"

    # verify temp param file contents
    with open(result[1], "r") as f:
        written_params = yaml.safe_load(f)
        assert written_params["input"] == "https://api.cloud.seqera.io/datasets/123"
        assert written_params["outdir"] == "s3://bucket/results"
        assert "dataset" not in written_params


def test_handle_compute_envs_with_primary():
    mock_sp = Mock()
    mock_compute_envs = Mock()
    mock_sp.compute_envs = mock_compute_envs

    args = [
        "aws-batch",
        "forge",
        "--name",
        "test_computeenv",
        "--workspace",
        "my_organization/my_workspace",
        "--credentials",
        "my_credentials",
        "--primary",
    ]

    helper.handle_compute_envs(mock_sp, args)

    # Verify compute env was created first
    expected_add_args = [
        "aws-batch",
        "forge",
        "--name",
        "test_computeenv",
        "--workspace",
        "my_organization/my_workspace",
        "--credentials",
        "my_credentials",
    ]
    mock_compute_envs.assert_any_call("add", *expected_add_args)

    mock_compute_envs.assert_any_call(
        "primary",
        "set",
        "--name",
        "test_computeenv",
        "--workspace",
        "my_organization/my_workspace",
    )

    assert mock_compute_envs.call_count == 2


def test_create_mock_computeevs_with_snapshots_true(mock_yaml_file):
    """Test that snapshots: true adds --snapshots CLI flag."""
    test_data = {
        "compute-envs": [
            {
                "name": "test_computeenv",
                "workspace": "my_organization/my_workspace",
                "credentials": "my_credentials",
                "type": "aws-batch",
                "config-mode": "forge",
                "snapshots": True,
                "wait": "AVAILABLE",
            }
        ],
    }

    file_path = mock_yaml_file(test_data)
    result = helper.parse_all_yaml([file_path])

    assert "compute-envs" in result
    actual_args = result["compute-envs"][0]["cmd_args"]

    # snapshots: true should add --snapshots CLI flag
    assert "--snapshots" in actual_args

    # Other expected args should still be present
    expected_args = {
        "aws-batch",
        "forge",
        "--name",
        "test_computeenv",
        "--workspace",
        "my_organization/my_workspace",
        "--credentials",
        "my_credentials",
        "--wait",
        "AVAILABLE",
        "--snapshots",
    }

    actual_args_set = set(actual_args)
    assert all(arg in actual_args_set for arg in expected_args)


def test_create_mock_computeevs_with_snapshots_false(mock_yaml_file):
    """Test that snapshots: false doesn't add --snapshots CLI flag."""
    test_data = {
        "compute-envs": [
            {
                "name": "test_computeenv",
                "workspace": "my_organization/my_workspace",
                "credentials": "my_credentials",
                "type": "aws-batch",
                "config-mode": "forge",
                "snapshots": False,
                "wait": "AVAILABLE",
            }
        ],
    }

    file_path = mock_yaml_file(test_data)
    result = helper.parse_all_yaml([file_path])

    assert "compute-envs" in result
    actual_args = result["compute-envs"][0]["cmd_args"]

    # snapshots: false should not add --snapshots CLI flag
    assert "--snapshots" not in actual_args

    # Other expected args should still be present
    expected_args = {
        "aws-batch",
        "forge",
        "--name",
        "test_computeenv",
        "--workspace",
        "my_organization/my_workspace",
        "--credentials",
        "my_credentials",
        "--wait",
        "AVAILABLE",
    }

    actual_args_set = set(actual_args)
    assert all(arg in actual_args_set for arg in expected_args)


def test_create_mock_computeevs_with_snapshots_alternative(mock_yaml_file):
    """Test that alternative snapshots field works."""
    test_data = {
        "compute-envs": [
            {
                "name": "test_computeenv",
                "workspace": "my_organization/my_workspace",
                "credentials": "my_credentials",
                "type": "aws-batch",
                "config-mode": "forge",
                "snapshots": True,
                "wait": "AVAILABLE",
            }
        ],
    }

    file_path = mock_yaml_file(test_data)
    result = helper.parse_all_yaml([file_path])

    assert "compute-envs" in result
    actual_args = result["compute-envs"][0]["cmd_args"]

    # snapshots: true should be converted to --snapshots CLI flag
    assert "--snapshots" in actual_args

    # Other expected args should still be present
    expected_args = {
        "aws-batch",
        "forge",
        "--name",
        "test_computeenv",
        "--workspace",
        "my_organization/my_workspace",
        "--credentials",
        "my_credentials",
        "--wait",
        "AVAILABLE",
        "--snapshots",
    }

    actual_args_set = set(actual_args)
    assert all(arg in actual_args_set for arg in expected_args)
