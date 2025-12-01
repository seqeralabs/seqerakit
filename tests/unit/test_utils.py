# Copyright 2025, Seqera
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

import os
import unittest
import yaml
from seqerakit.utils import resolve_env_var, create_temp_yaml


class TestResolveEnvVar(unittest.TestCase):
    """Test cases for the resolve_env_var function"""

    def setUp(self):
        """Set up test environment variables"""
        os.environ["TEST_VAR"] = "test_value"
        os.environ["PROJECT_DIR"] = "/path/to/project"
        os.environ["OUTPUT_DIR"] = "/path/to/output"

    def tearDown(self):
        """Clean up test environment variables"""
        # Remove test environment variables
        for var in ["TEST_VAR", "PROJECT_DIR", "OUTPUT_DIR"]:
            if var in os.environ:
                del os.environ[var]

    def test_basic_env_vars(self):
        """Test basic environment variable formats"""
        self.assertEqual(resolve_env_var("$TEST_VAR"), "test_value")
        self.assertEqual(resolve_env_var("${TEST_VAR}"), "test_value")

    def test_escaping(self):
        """Test $$ escaping functionality"""
        self.assertEqual(resolve_env_var("$${projectDir}"), "${projectDir}")
        self.assertEqual(resolve_env_var("$$$${projectDir}"), "$${projectDir}")

    def test_mixed_cases(self):
        """Test combinations of escaped and environment variables"""
        self.assertEqual(
            resolve_env_var("$${projectDir}/${TEST_VAR}"), "${projectDir}/test_value"
        )
        self.assertEqual(
            resolve_env_var("$${projectDir}/${PROJECT_DIR}"),
            "${projectDir}//path/to/project",
        )

    def test_non_env_inputs(self):
        """Test non-environment variable inputs"""
        self.assertEqual(resolve_env_var("plain_string"), "plain_string")
        self.assertEqual(resolve_env_var(""), "")
        self.assertEqual(resolve_env_var(None), None)
        self.assertEqual(resolve_env_var(123), 123)

    def test_missing_env_vars(self):
        """Test missing environment variables raise errors"""
        with self.assertRaises(EnvironmentError):
            resolve_env_var("$MISSING_VAR")
        with self.assertRaises(EnvironmentError):
            resolve_env_var("${MISSING_VAR}")

        # Escaped patterns should not cause errors
        self.assertEqual(resolve_env_var("$${MISSING_VAR}"), "${MISSING_VAR}")

    def test_edge_cases(self):
        """Test edge cases with dollar signs"""
        self.assertEqual(resolve_env_var("$"), "$")
        self.assertEqual(resolve_env_var("$$"), "$")
        self.assertEqual(resolve_env_var("$$$"), "$$")

    def test_nf_reserved_vars(self):
        """Test Nextflow reserved variables"""
        result = resolve_env_var("$${projectDir}/${TEST_VAR}")
        self.assertEqual(result, "${projectDir}/test_value")


class TestCreateTempNestedYaml(unittest.TestCase):
    """Test create_temp_yaml with lists and maps (issue #245)"""

    def setUp(self):
        os.environ["TEST_VAR"] = "test_value"
        os.environ["ENV"] = "production"

    def tearDown(self):
        for var in ["TEST_VAR", "ENV"]:
            if var in os.environ:
                del os.environ[var]

    def test_create_temp_yaml_with_lists_and_maps(self):
        """Test that lists and maps are preserved with env var resolution"""
        params = {
            "map_param": {"key": "$TEST_VAR"},
            "list_parameter": ["value1_${ENV}", "value2_${ENV}"],
            "nested": {"inner_list": ["$TEST_VAR", 42, True]},
            "simple_param": "$TEST_VAR",
        }
        temp_file = create_temp_yaml(params)

        with open(temp_file, "r") as f:
            result = yaml.safe_load(f)

        self.assertEqual(result["map_param"], {"key": "test_value"})
        self.assertEqual(
            result["list_parameter"], ["value1_production", "value2_production"]
        )
        self.assertEqual(result["nested"]["inner_list"], ["test_value", 42, True])
        self.assertEqual(result["simple_param"], "test_value")
        os.unlink(temp_file)


if __name__ == "__main__":
    unittest.main()
