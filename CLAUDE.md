# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

seqerakit is a Python wrapper for the Seqera Platform CLI (`tw`) that automates the creation and management of Seqera Platform resources via YAML configuration files. It provides an Infrastructure-as-Code approach for managing organizations, workspaces, compute environments, pipelines, and other Seqera Platform entities.

**Key Technologies:**

- Python 3.8+ with Typer for CLI framework
- PyYAML for configuration parsing
- pytest for testing
- uv for dependency management (recommended)

## Development Setup

### Quick Start

```bash
# Install dependencies and run (uv recommended)
uv run seqerakit --help

# For development with hot-reload
uv sync
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### Running Tests

```bash
# Run all tests
uv run pytest

# Run specific test file
uv run pytest tests/unit/test_cli.py

# Run with verbose output
uv run pytest -v

# Run tests matching a pattern
uv run pytest -k "test_name_pattern"
```

### Code Quality

```bash
# Install pre-commit hooks (runs Black and Ruff)
pre-commit install

# Run pre-commit manually on all files
pre-commit run --all-files
```

### Environment Variables Required

- `TOWER_ACCESS_TOKEN`: Required for authentication with Seqera Platform
- `TOWER_API_ENDPOINT`: Optional, defaults to `https://api.cloud.seqera.io`

## Architecture

### Core Components

**1. CLI Entry Point (`cli.py`)**

- Built with Typer framework (modern CLI replacing argparse)
- Main command: `seqerakit [yaml_files] [options]`
- Handles argument parsing, logging, and orchestration
- Key class: `BlockParser` - routes YAML blocks to appropriate handlers

**2. SeqeraPlatform Wrapper (`seqeraplatform.py`)**

- Core wrapper around `tw` CLI commands
- Implements dynamic method dispatch: any `tw` subcommand can be called as a method
- Example: `sp.pipelines.add()` executes `tw pipelines add`
- Handles subprocess execution, output capture, and error handling
- Custom exceptions: `ResourceExistsError`, `ResourceNotFoundError`, `CommandError`

**3. YAML Processing (`helper.py`)**

- Functions for parsing YAML blocks into CLI arguments
- Merges multiple YAML files
- Handles environment variable interpolation
- Special handlers for complex resources (teams, compute-envs, pipelines)

**4. Resource Management (`overwrite.py`)**

- Implements `on_exists` behavior: `fail`, `ignore`, `overwrite`
- Checks if resources exist before creation
- Handles deletion and recreation for overwrite scenarios
- Different deletion strategies for different resource types

**5. Specialized Handlers**

- `computeenvs.py`: Handles JSON config files for compute environments
- `pipelines.py`: Manages pipeline parameters and params-file merging
- `utils.py`: Shared utilities for argument parsing

### Data Flow

1. **Input**: YAML file(s) or stdin → `find_yaml_files()`
2. **Parse**: YAML → dict of blocks → `parse_all_yaml()`
3. **Route**: Each block → `BlockParser.handle_block()`
4. **Check**: Resource exists? → `Overwrite.handle_overwrite()` (handles on_exists logic)
5. **Execute**: Build `tw` command → `SeqeraPlatform._tw_run()`
6. **Output**: JSON to stdout (if `--json`) or text to stderr

### Key Design Patterns

**Dynamic Method Dispatch**

```python
# sp.pipelines.add(...) translates to "tw pipelines add ..."
def __getattr__(self, cmd):
    return self.TwCommand(self, cmd.replace("_", "-"))
```

**Block Handler Registration**

```python
# In BlockParser.__init__, resources are categorized:
list_for_add_method = [
    "organizations", "workspaces", "labels",
    "credentials", "secrets", "actions", ...
]
# These use generic "tw <resource> add" pattern

# Special handlers for complex logic:
block_handler_map = {
    "teams": handle_teams,
    "compute-envs": handle_compute_envs,
    "pipelines": handle_pipelines,
}
```

**on_exists Behavior Hierarchy**

1. Global CLI flag (`--on-exists`) takes precedence
2. Block-level `on_exists` in YAML (per resource)
3. Default: `fail`

## Common Development Tasks

### Adding a New Resource Type

1. Add resource to appropriate list in `BlockParser.__init__`:

   - Simple resources → `list_for_add_method`
   - Complex resources → `block_handler_map` with custom handler

2. If complex, create handler in `helper.py`:

   ```python
   def handle_new_resource(sp, cmd_args):
       # Custom logic for resource creation
       pass
   ```

3. Add deletion logic in `overwrite.py`:

   ```python
   # Add to Overwrite.block_operations if special deletion needed
   "new-resource": {
       "keys": ["name", "workspace"],
       "method_args": lambda args: self._get_generic_args(args),
       "name_key": "name",
   }
   ```

4. Create template YAML in `templates/new-resource.yml`

### Working with Parameters

**Pipeline Parameters Merging**

- `params-file` is loaded first
- Individual `params` override values from `params-file`
- Both are merged into a single temporary file passed to `tw`

**Environment Variable Interpolation**

- Supports Unix (`$VAR`, `${VAR}`), Windows (`%VAR%`), PowerShell (`$env:VAR`)
- Checked in `SeqeraPlatform._check_env_vars()`
- Raises `EnvironmentError` if variable not found

### Testing Patterns

**Unit Tests** (`tests/unit/`)

- Use pytest with pytest-mock for mocking
- Mock subprocess calls to `tw` CLI
- Test individual functions in isolation

**E2E Tests** (`tests/e2e/`)

- Requires real Seqera Platform instance
- Uses actual YAML configurations
- Tests full workflow from YAML to resource creation

**Common Test Pattern**

```python
def test_something(mocker):
    # Mock subprocess to avoid real CLI calls
    mock_popen = mocker.patch("subprocess.Popen")
    mock_popen.return_value.communicate.return_value = (b"output", None)
    mock_popen.return_value.returncode = 0

    # Test your code
    sp = SeqeraPlatform()
    result = sp.some_method()
    assert result == "expected"
```

### Debugging

**VSCode Launch Configuration**
Use the setup from `.github/CONTRIBUTING.md` to debug with breakpoints:

- Set Python path to `.venv/bin/python`
- Program: `${workspaceFolder}/seqerakit/cli.py`
- Args: `["-l", "debug", "your-test.yml"]`

**Enable Debug Logging**

```bash
seqerakit your-config.yml --log-level DEBUG
```

**Dry Run Mode**

```bash
# See what commands would be executed without running them
seqerakit your-config.yml --dryrun
```

## Critical Implementation Details

### JSON Output Mode

When `--json` flag is used:

- All `tw` commands include `-o json`
- JSON is printed to stdout only
- Logs go to stderr
- Each resource creation outputs a single JSON object
- Can be piped: `seqerakit -j file.yml | jq`

### Verbose Flag Handling

The `--verbose` flag has special handling:

- Added to most `tw` commands for detailed output
- **Exception**: Temporarily removed during overwrite operations to avoid JSON parsing conflicts
- See `cli.py` lines 86-91 for implementation

### Workspace Resolution

- Workspace format: `organization/workspace` or just `workspace` (for user workspace)
- Omit `workspace` key for user/personal workspace operations
- Always include `workspace` for organization workspaces

### Special Characters in Commands

- Arguments with spaces are automatically quoted via `shlex.quote()`
- Shell constructs (`|`, `>`, `&`, etc.) are passed through
- Special variables like `$TW_AGENT_WORK` are escaped differently

## Important Files Reference

- `seqerakit/cli.py:66` - BlockParser class orchestrates resource creation
- `seqerakit/cli.py:208` - Main CLI entry point
- `seqerakit/seqeraplatform.py:24` - SeqeraPlatform wrapper class
- `seqerakit/seqeraplatform.py:218` - Dynamic method dispatch implementation
- `seqerakit/helper.py:60` - YAML parsing entry point
- `seqerakit/overwrite.py:22` - Overwrite/on_exists logic
- `seqerakit/pipelines.py` - Pipeline parameter merging logic
- `seqerakit/computeenvs.py` - Compute environment JSON config handling

## Common Gotchas

1. **Duplicate Names**: Each resource name must be unique within a block. Helper validates this.

2. **on_exists Precedence**: Global CLI flag overrides block-level settings. Check `cli.py:115-141`.

3. **Empty Arguments**: Empty args are filtered out in `_check_empty_args()` to avoid malformed commands.

4. **Environment Variables**: Must be set before running. Interpolation happens in `_check_env_vars()`.

5. **Overwrite vs Delete**: `--overwrite` is deprecated; use `--on-exists=overwrite`. `--delete` recursively deletes resources.

6. **tw CLI Version**: Requires `tw >= 0.11.0`. Check with `tw --version`.
