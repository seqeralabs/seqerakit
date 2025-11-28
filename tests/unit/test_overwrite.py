import unittest
from unittest.mock import Mock, patch
import json
from seqerakit.overwrite import Overwrite
from seqerakit.seqeraplatform import ResourceExistsError
from seqerakit.on_exists import OnExists


class TestOverwrite(unittest.TestCase):
    def setUp(self):
        self.mock_sp = Mock()

        # Mock context manager for suppress_output
        self.mock_sp.suppress_output.return_value.__enter__ = Mock()
        self.mock_sp.suppress_output.return_value.__exit__ = Mock()

        self.overwrite = Overwrite(self.mock_sp)

        self.sample_teams_json = json.dumps(
            {"teams": [{"name": "test-team", "teamId": "123", "orgName": "test-org"}]}
        )

        self.sample_workspace_json = json.dumps(
            {
                "workspaces": [
                    {
                        "workspaceId": "456",
                        "workspaceName": "test-workspace",
                        "orgName": "test-org",
                    }
                ]
            }
        )

        self.sample_labels_json = json.dumps(
            {"labels": [{"id": "789", "name": "test-label", "value": "test-value"}]}
        )

    def test_handle_overwrite_generic_deletion(self):
        # Test for credentials, secrets, compute-envs, datasets, actions, pipelines
        args = ["--name", "test-resource", "--workspace", "test-workspace"]

        self.mock_sp.__getattr__("-o json").return_value = json.dumps(
            {"name": "test-resource"}
        )

        self.overwrite.handle_overwrite(
            "credentials", args, on_exists=OnExists.OVERWRITE
        )

        self.mock_sp.credentials.assert_called_with(
            "delete", "--name", "test-resource", "--workspace", "test-workspace"
        )

    def test_handle_overwrite_resource_exists_no_overwrite(self):
        args = ["--name", "test-resource", "--workspace", "test-workspace"]

        # Mock JSON response indicating resource exists
        self.mock_sp.__getattr__("-o json").return_value = json.dumps(
            {"name": "test-resource"}
        )

        with self.assertRaises(ResourceExistsError):
            self.overwrite.handle_overwrite(
                "credentials", args, on_exists=OnExists.FAIL
            )

    def test_team_deletion(self):
        args = {"name": "test-team", "organization": "test-org"}

        json_method_mock = Mock(side_effect=lambda *args: self.sample_teams_json)

        self.mock_sp.configure_mock(**{"-o json": json_method_mock})

        team_args = self.overwrite._get_team_args(args)

        self.assertEqual(
            team_args, ("delete", "--id", "123", "--organization", "test-org")
        )

        json_method_mock.assert_called_with("teams", "list", "-o", "test-org")

        # Test caching behavior
        # Second call should use cached data
        team_args_cached = self.overwrite._get_team_args(args)

        # Should return same result
        self.assertEqual(
            team_args_cached, ("delete", "--id", "123", "--organization", "test-org")
        )

        # But json_mock should only have been called once
        self.assertEqual(json_method_mock.call_count, 1)

    def test_workspace_deletion(self):
        args = ["--name", "test-workspace", "--organization", "test-org"]

        self.mock_sp.__getattr__("-o json").return_value = self.sample_workspace_json

        self.overwrite.handle_overwrite(
            "workspaces", args, on_exists=OnExists.OVERWRITE
        )

        self.mock_sp.workspaces.assert_called_with("delete", "--id", "456")

    def test_label_deletion(self):
        args = [
            "--name",
            "test-label",
            "--value",
            "test-value",
            "--workspace",
            "test-workspace",
        ]

        self.mock_sp.__getattr__("-o json").return_value = self.sample_labels_json

        self.overwrite.handle_overwrite("labels", args, on_exists=OnExists.OVERWRITE)

        self.mock_sp.labels.assert_called_with(
            "delete", "--id", "789", "-w", "test-workspace"
        )

    def test_participant_deletion(self):
        team_args = [
            "--name",
            "test-team",
            "--type",
            "TEAM",
            "--workspace",
            "test-workspace",
        ]

        self.mock_sp.__getattr__("-o json").return_value = json.dumps(
            {"teamName": "test-team"}
        )

        self.overwrite.handle_overwrite(
            "participants", team_args, on_exists=OnExists.OVERWRITE
        )

        self.mock_sp.participants.assert_called_with(
            "delete",
            "--name",
            "test-team",
            "--type",
            "TEAM",
            "--workspace",
            "test-workspace",
        )

    @patch("seqerakit.utils.resolve_env_var")
    def test_organization_deletion_with_env_var(self, mock_resolve_env_var):
        args = ["--name", "${ORG_NAME}"]

        # Setup environment variable mock
        mock_resolve_env_var.side_effect = lambda x: (
            "resolved-org-name" if x == "${ORG_NAME}" else x
        )

        # Create a mock for the json method that returns our JSON data
        # The JSON response needs to match what check_if_exists method looks for
        json_method_mock = Mock(
            side_effect=lambda *args: json.dumps(
                {"organizations": [{"orgName": "resolved-org-name"}]}
            )
        )

        self.mock_sp.configure_mock(**{"-o json": json_method_mock})

        self.overwrite.handle_overwrite(
            "organizations", args, on_exists=OnExists.OVERWRITE
        )

        mock_resolve_env_var.assert_any_call("${ORG_NAME}")

        self.mock_sp.organizations.assert_called_with("delete", "--name", "${ORG_NAME}")

    def test_handle_on_exists_overwrite(self):
        # Test for credentials, secrets, compute-envs, datasets, actions, pipelines
        args = ["--name", "test-resource", "--workspace", "test-workspace"]

        self.mock_sp.__getattr__("-o json").return_value = json.dumps(
            {"name": "test-resource"}
        )

        # Test with on_exists='overwrite'
        self.overwrite.handle_overwrite("credentials", args, on_exists="overwrite")

        self.mock_sp.credentials.assert_called_with(
            "delete", "--name", "test-resource", "--workspace", "test-workspace"
        )

    def test_handle_on_exists_ignore(self):
        # Test for credentials with on_exists='ignore'
        args = ["--name", "test-resource", "--workspace", "test-workspace"]

        self.mock_sp.__getattr__("-o json").return_value = json.dumps(
            {"name": "test-resource"}
        )

        # Test with on_exists='ignore'
        result = self.overwrite.handle_overwrite(
            "credentials", args, on_exists="ignore"
        )

        # Should return False to indicate creation should be skipped
        self.assertFalse(result)

        # Should not call delete
        self.mock_sp.credentials.assert_not_called()

    def test_handle_on_exists_fail(self):
        args = ["--name", "test-resource", "--workspace", "test-workspace"]

        # Mock JSON response indicating resource exists
        self.mock_sp.__getattr__("-o json").return_value = json.dumps(
            {"name": "test-resource"}
        )

        # Test with on_exists='fail' (default)
        with self.assertRaises(ResourceExistsError):
            self.overwrite.handle_overwrite("credentials", args, on_exists="fail")

        # Should not call delete
        self.mock_sp.credentials.assert_not_called()

    def test_handle_invalid_on_exists(self):
        args = ["--name", "test-resource", "--workspace", "test-workspace"]

        # Test with invalid on_exists value
        with self.assertRaises(ValueError):
            self.overwrite.handle_overwrite(
                "credentials", args, on_exists="invalid_option"
            )

    def test_backward_compatibility_overwrite(self):
        args = ["--name", "test-resource", "--workspace", "test-workspace"]

        self.mock_sp.__getattr__("-o json").return_value = json.dumps(
            {"name": "test-resource"}
        )

        # Test with legacy overwrite=True parameter
        self.overwrite.handle_overwrite("credentials", args, overwrite=True)

        self.mock_sp.credentials.assert_called_with(
            "delete", "--name", "test-resource", "--workspace", "test-workspace"
        )

    def test_backward_compatibility_no_overwrite(self):
        args = ["--name", "test-resource", "--workspace", "test-workspace"]

        # Mock JSON response indicating resource exists
        self.mock_sp.__getattr__("-o json").return_value = json.dumps(
            {"name": "test-resource"}
        )

        # Test with legacy overwrite=False parameter
        with self.assertRaises(ResourceExistsError):
            self.overwrite.handle_overwrite("credentials", args, overwrite=False)

    def test_multi_workspace_resource_check(self):
        """Test that resources are correctly tracked per workspace."""
        # Setup mock responses for different workspaces
        workspace1_json = json.dumps({"name": "resource-in-workspace1"})
        workspace2_json = json.dumps({"name": "resource-in-workspace2"})

        # Configure mock to return different data based on workspace
        def mock_json_response(*args, **kwargs):
            if args[2] == "-w" and args[3] == "org1/workspace1":
                return workspace1_json
            elif args[2] == "-w" and args[3] == "org2/workspace2":
                return workspace2_json
            return json.dumps({})

        json_method_mock = Mock(side_effect=mock_json_response)
        self.mock_sp.configure_mock(**{"-o json": json_method_mock})

        # Check first workspace - should find resource-in-workspace1
        args1 = ["--name", "resource-in-workspace1", "--workspace", "org1/workspace1"]
        with self.assertRaises(ResourceExistsError):
            self.overwrite.handle_overwrite("credentials", args1)

        # Should find resource-in-workspace2, not resource-in-workspace1
        args2 = ["--name", "resource-in-workspace1", "--workspace", "org2/workspace2"]
        self.overwrite.handle_overwrite("credentials", args2)  # Should not raise error

        # Verify both workspaces were queried
        json_method_mock.assert_any_call("credentials", "list", "-w", "org1/workspace1")
        json_method_mock.assert_any_call("credentials", "list", "-w", "org2/workspace2")

        # Check a resource that exists in workspace2
        args3 = ["--name", "resource-in-workspace2", "--workspace", "org2/workspace2"]
        with self.assertRaises(ResourceExistsError):
            self.overwrite.handle_overwrite("credentials", args3)


# TODO: tests for destroy and JSON caching

if __name__ == "__main__":
    unittest.main()
