# Contributing

Contributions of all kinds are welcome. In particular, pull requests are appreciated. The authors will endeavour to help walk you through any issues in the pull request discussion, so please feel free to open a pull request even if you are new to such things.

### Issues

The easiest contribution to make is to file an issue. It is beneficial if you perform a cursory search of existing issues and it is also helpful, but not necessary, if you can provide clear instruction for how to reproduce a problem. If you have resolved an issue yourself please consider contributing to this repository so others can benefit from your work.

### Documentation

Contributing to documentation is the easiest way to get started. Providing simple clear or helpful documentation for new users is critical. Anything that you as a new user found hard to understand, or difficult to work out, are excellent places to begin. Contributions to more detailed and descriptive error messages is especially appreciated. To contribute to the documentation please fork the project into your own repository, make changes there, and then submit a pull request.

### Code

Code contributions are always welcome, from simple bug fixes, to new features. To contribute code please fork the project into your own repository, make changes there, run the pre-commit hooks provided, add tests for bugs/new features, and then submit a pull request. If you are fixing a known issue please add the issue number to the PR message. If you are fixing a new issue feel free to file an issue and then reference it in the PR. You can browse open issues, or consult the project roadmap, for potential code contributions. Fixes for issues tagged with 'help wanted' are especially appreciated.

## Contribution workflow

### Github Workflow

Follow the [Github flow](https://docs.github.com/en/get-started/quickstart/github-flow) for development workflow by forking, opening a new branch and editing the code or documentation before opening a pull request.

### Developing Locally

Install the dependencies locally before prior to development. You can use a virtual environment but we recommend using a conda environment as this can come with an appropriate version of the Seqera Platform CLI. To install, you can create and activate a conda environment using:

```console
conda env create -f environment.yml
conda activate seqerakit
```

Or [install tw-cli from GitHub](https://github.com/seqeralabs/tower-cli?tab=readme-ov-file#getting-started).

You can then install the local repository for development using the `pip -e` command which will install it in place without copying it to your `PYTHONPATH`. Using `--no-deps` will ignore dependencies which have already been installed via Conda. This assumes the current working directory is a clone of this repository.

```console
pip install -e . --no-deps
```

You can then develop the code before committing changes and opening a pull request.

#### uv workflow

1. [Install uv](https://docs.astral.sh/uv/getting-started/installation/)
2. `uv run seqerakit -h`

##### Publishing

1. [uv publish](https://docs.astral.sh/uv/guides/publish/)

### pre-commit

We use [pre-commit](https://pre-commit.com/) which runs [Black](https://github.com/psf/black) and [Ruff](https://github.com/astral-sh/ruff) to ensure code consistency during development. Install pre-commit and configure with `pre-commit install` which will now run before every commit ensuring code consistency.

## Appendix

### Debugging

You can debug in VSCode for stepping through code and monitoring errors. To do so, set the Python path to the Conda environment you created earlier and add the following to the `.vscode/launch.json` folder:

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: Current File",
      "type": "python",
      "request": "launch",
      "program": "${workspaceFolder}/seqerakit/cli.py",
      "args": ["-l", "debug", "example.yml"], // Change to your specific commands you wish to run
      "cwd": "${workspaceFolder}"
    }
  ]
}
```

You may need additional settings based on your set-up. A more complete example may look like below:

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: Current File",
      "type": "python",
      "request": "launch",
      "program": "${workspaceFolder}/seqerakit/cli.py",
      "console": "integratedTerminal",
      "purpose": ["debugging"],
      "justMyCode": true,
      "args": ["-l", "debug", "example.yml"],
      "console": "integratedTerminal",
      "internalConsoleOptions": "openOnSessionStart",
      "env": {
        "PYTHONPATH": "${workspaceFolder}"
      },
      "preLaunchTask": "pipInstall"
    }
  ]
}
```

With an additional `.vscode/tasks.json`:

```json
{
  "version": "2.0.0",
  "tasks": [
    {
      "label": "pipInstall",
      "type": "shell",
      "osx": {
        "command": "pip install -e ."
      },
      "windows": {
        "command": "pip install -e ."
      },
      "linux": {
        "command": "pip install -e ."
      },
      "problemMatcher": [],
      "options": {
        "cwd": "${workspaceFolder}"
      }
    }
  ]
}
```

After this, press "Run > Start Debugging" (F5) to run the code. To stop the code mid flow, add breakpoints, print statements, assertions, etc.
