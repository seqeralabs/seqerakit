# <img src="assets/seqerakit.svg" width=50 alt="seqerakit logo"> seqerakit

`seqerakit` is a Python wrapper for the [Seqera Platform CLI](https://github.com/seqeralabs/tower-cli). It can be leveraged to automate the creation of all of the entities in Seqera Platform via a simple configuration file in YAML format.

The key features are:

- **Simple configuration**: All of the command-line options available when using the Seqera Platform CLI can be defined in simple YAML format.
- **Infrastructure as Code**: Enable users to manage and provision their infrastructure specifications.
- **Automation**: End-to-end creation of entities within Seqera Platform, all the way from adding an Organization to launching pipeline(s) within that Organization.

## Prerequisites

You will need to have an account on Seqera Platform (see [Plans and pricing](https://seqera.io/pricing/)).

## Installation

`seqerakit` requires the following dependencies:

1. [Seqera Platform CLI (`>=0.9.2`)](https://github.com/seqeralabs/tower-cli#1-installation)

2. [Python (`>=3.8`)](https://www.python.org/downloads/)

3. [PyYAML](https://pypi.org/project/PyYAML/)

### uv (Recommended)

[uv](https://docs.astral.sh/uv/) is a fast Python package manager that handles dependencies and virtual environments automatically. To install `seqerakit` with uv:

1. [Install uv](https://docs.astral.sh/uv/getting-started/installation/)

2. Run seqerakit directly (this will automatically install seqerakit and its dependencies):

```console
uv run seqerakit --help
```

Or install it globally:

```console
uv tool install seqerakit
seqerakit --help
```

**Note**: You will still need to install the [Seqera Platform CLI](https://github.com/seqeralabs/tower-cli#1-installation) separately.

### Conda

You can install `seqerakit` and its dependencies via Conda. Ensure that you have the correct channels configured:

```console
conda config --add channels bioconda
conda config --add channels conda-forge
conda config --set channel_priority strict
```

You can then create a conda environment with `seqerakit` installed using the following:

```console
conda create -n seqerakit seqerakit
conda activate seqerakit
```

### Pip

If you already have [Seqera Platform CLI](https://github.com/seqeralabs/tower-cli#1-installation) and Python installed on your system, you can install `seqerakit` directly from [PyPI](https://pypi.org/project/seqerakit/):

```console
pip install seqerakit
```

You can force overwrite the installation to use the latest changes with the command below:

```console
pip install --upgrade --force-reinstall seqerakit
```

### Local development installation

You can install the development branch of `seqerakit` on your local machine to test feature updates of the tool. Before proceeding, ensure that you have [Python](https://www.python.org/downloads/) and [Git](https://git-scm.com/downloads) installed on your system.

#### Using uv (Recommended)

1. Clone the repository and navigate to it:

```bash
git clone https://github.com/seqeralabs/seqera-kit.git
cd seqera-kit
git checkout dev
```

2. Run seqerakit directly from the source (uv will handle dependencies automatically):

```bash
uv run seqerakit --help
```

#### Using pip

1. To install directly from pip:

```bash
pip install git+https://github.com/seqeralabs/seqera-kit.git@dev
```

2. Alternatively, you may clone the repository locally and install manually:

```bash
git clone https://github.com/seqeralabs/seqera-kit.git
cd seqera-kit
git checkout dev
pip install .
```

You can verify your installation with:

```bash
pip show seqerakit
```

## Configuration

Create a Seqera Platform access token using the [Seqera Platform](https://seqera.io/) web interface via the **Your Tokens** page in your profile.

`seqerakit` reads this token from the environment variable `TOWER_ACCESS_TOKEN`. Please export it into your terminal as shown below:

```bash
export TOWER_ACCESS_TOKEN=<Your access token>
```

For Enterprise installations of Seqera Platform, you will also need to configure the API endpoint that will be used to connect to the Platform. You can do so by exporting the following environment variable:

```bash
export TOWER_API_ENDPOINT=<Tower API URL>
```

By default, this is set to `https://api.cloud.seqera.io` to connect to Seqera Platform Cloud.

## Usage

To confirm the installation of `seqerakit`, configuration of the Seqera Platform CLI and connection to the Platform is working as expected. This will run the `tw info` command under the hood:

```bash
seqerakit --info
```

Use the `--help` or `-h` parameter to list the available commands and their associated options:

```bash
seqerakit --help
```

Use `--version` or `-v` to retrieve the current version of your seqerakit installation:

```bash
seqerakit --version
```

### Input

`seqerakit` supports input through either file paths to YAMLs or directly from standard input (stdin).

#### Using File Path

```bash
seqerakit /path/to/file.yaml
```

#### Using stdin

```console
$ cat file.yaml | seqerakit -
```

See the [Defining your YAML file using CLI options](#defining-your-yaml-file-using-cli-options) section for guidance on formatting your input YAML file(s).

### Dryrun

To print the commands that would executed with `tw` when using a YAML file, you can run `seqerakit` with the `--dryrun` flag:

```bash
seqerakit file.yaml --dryrun
```

To capture the details of the created resources, you can use the `--json` command-line flag to output the results as JSON to `stdout`. This is equivalent to using the `-o json` flag with the `tw` CLI.

For example:

```bash
seqerakit -j examples/yaml/e2e/launch.yml
```

This command internally runs the following `tw` command:

```bash
INFO:root: Running command: tw -o json launch --name hello --workspace $SEQERA_ORGANIZATION_NAME/$SEQERA_WORKSPACE_NAME hello
```

The output will look like this:

```json
{
  "workflowId": "1wfhRp5ioFIyrs",
  "workflowUrl": "https://tower.nf/orgs/orgName/workspaces/workspaceName/watch/1wfhRp5ioFIyrs",
  "workspaceId": 12345678,
  "workspaceRef": "[orgName / workspaceName]"
}
```

This JSON output can be piped into other tools for further processing. Note that logs will still be written to `stderr`, allowing you to monitor the tool's progress in real-time.

If you prefer to suppress the JSON output and focus only on the logs:

```bash
seqerakit -j examples/yaml/e2e/launch.yml > /dev/null
```

This will still log:

```bash
INFO:root: Running command: tw -o json launch --name hello --workspace $SEQERA_ORGANIZATION_NAME/$SEQERA_WORKSPACE_NAME hello
```

Each execution of the `tw` CLI generates a single JSON object. To combine multiple JSON objects into one, you can use a tool like `jq`:

```bash
seqerakit -j launch/*.yml | jq --slurp > launched-pipelines.json
```

This command will merge the individual JSON objects from each `tw` command into a single JSON array and save it to `launched-pipelines.json`.

### Recursively delete

Instead of adding or creating resources, you can recursively delete resources in your YAML file by specifying the `--delete` flag:

```bash
seqerakit file.yaml --delete
```

For example, if you have a YAML file that defines an Organization -> Workspace -> Team -> Credentials -> Compute Environment that have already been created, with the `--delete` flag, `seqerakit` will recursively delete the Compute Environment -> Credentials -> Team -> Workspace -> Organization.

### Using `tw` specific CLI options

`tw` specific CLI options can be specified with the `--cli=` flag:

```bash
seqerakit file.yaml --cli="--arg1 --arg2"
```

You can find the full list of options by running `tw -h`.

The Seqera Platform CLI expects to connect to a Seqera Platform instance that is secured by a TLS certificate. If your Seqera Platform Enterprise instance does not present a certificate, you will need to qualify and run your `tw` commands with the `--insecure` flag.

To use `tw` specific CLI options such as `--insecure`, use the `--cli=` flag, followed by the options you would like to use enclosed in double quotes.

For example:

```bash
seqerakit file.yaml --cli="--insecure"
```

For Seqera Platform Enterprise, to use an SSL certificate that is not accepted by the default Java certificate authorities and specify a custom `cacerts` store as accepted by the `tw` CLI, you can specify the `-Djavax.net.ssl.trustStore=/absolute/path/to/cacerts` option enclosed in double quotes to `seqerakit` as you would to `tw`, preceded by `--cli=`.

For example:

```bash
seqerakit hello-world-config.yml --cli="-Djavax.net.ssl.trustStore=/absolute/path/to/cacerts"
```

<b>Note</b>: Use of `--verbose` option for the `tw` CLI is currently not supported by `seqerakit`. Supplying `--cli="--verbose"` will raise an error.

## Specify targets

When using a YAML file as input that defines multiple resources, you can use the `--targets` flag to specify which resources to create. This flag takes a comma-separated list of resource names.

For example, given a YAML file that defines the following resources:

```yaml
workspaces:
  - name: 'showcase'
    organization: 'seqerakit_automation'
---
compute-envs:
  - name: 'compute-env'
    type: 'aws-batch forge'
    workspace: 'seqerakit/test'
---
pipelines:
  - name: 'hello-world-test-seqerakit'
    url: 'https://github.com/nextflow-io/hello'
    workspace: 'seqerakit/test'
    compute-env: 'compute-env'
```

You can target the creation of `pipelines` only by running:

```bash
seqerakit test.yml --targets pipelines
```

This will process only the pipelines block from the YAML file and ignore other blocks such as `workspaces` and `compute-envs`.

### Multiple Targets

You can also specify multiple resources to create by separating them with commas. For example, to create both workspaces and pipelines, run:

```bash
seqerakit test.yml --targets workspaces,pipelines
```

## YAML Configuration Options

There are several options that can be provided in your YAML configuration file, that are handled specially by seqerakit and/or are not exposed as `tw` CLI options.

### 1. Pipeline parameters using `params` and `params-file`

To specify pipeline parameters, you may either use `params:` to specify a list of parameters, or use `params-file:` to point to a parameters file.

For example, to specify pipeline parameters within your YAML:

```yaml
params:
  outdir: 's3://path/to/outdir'
  fasta: 's3://path/to/reference.fasta'
```

Alternatively, to specify a file containing pipeline parameters:

```yaml
params-file: '/path/to/my/parameters.yaml'
```

Optionally, you may provide both:

```yaml
params-file: '/path/to/my/parameters.yaml'
params:
  outdir: 's3://path/to/outdir'
  fasta: 's3://path/to/reference.fasta'
```

**Note**: If duplicate parameters are provided, the parameters provided as key-value pairs inside the `params` nested dictionary of the YAML file will take precedence **over** values in the provided `params-file`.

### 2. `on_exists` Functionality

For every entity defined in your YAML file, you can specify how to handle cases where the entity already exists using the `on_exists` parameter with one of three options:

- `fail` (default): Raise an error if the entity already exists
- `ignore`: Skip creation if the entity already exists
- `overwrite`: Delete the existing entity and create a new one based on the YAML configuration

Example usage in YAML:

```yaml
workspaces:
  - name: 'showcase'
    organization: 'seqerakit_automation'
    on_exists: 'overwrite'  # Will delete and recreate if exists
```

```yaml
credentials:
  - name: 'github_credentials'
    workspace: 'seqerakit_automation/showcase'
    on_exists: 'ignore'  # Will skip if already exists
```

When using the `overwrite` option, `seqerakit` will first check if the entity exists, and if so, it will invoke a `tw <subcommand> delete` command before attempting to create it based on the options defined in the YAML file:

```console
DEBUG:root: on_exists is set to 'overwrite' for organizations

DEBUG:root: Running command: tw -o json organizations list
DEBUG:root: The attempted organizations resource already exists. Overwriting.

DEBUG:root: Running command: tw organizations delete --name $SEQERA_ORGANIZATION_NAME
DEBUG:root: Running command: tw organizations add --name $SEQERA_ORGANIZATION_NAME --full-name $SEQERA_ORGANIZATION_NAME --description 'Example of an organization'
```

> **Note**: For backward compatibility, the `overwrite: True|False` parameter is still supported but deprecated. It will be mapped to `on_exists: 'overwrite'|'fail'` respectively.

### 3. Specifying JSON configuration files with `file-path`

The Seqera Platform CLI allows export and import of entities through JSON configuration files for pipelines and compute environments. To use these files to add a pipeline or compute environment to a workspace, use the `file-path` key to specify a path to a JSON configuration file.

An example of the `file-path` option is provided in the [compute-envs.yml](./templates/compute-envs.yml) template:

```yaml
compute-envs:
  - name: 'my_aws_compute_environment' # required
    workspace: 'my_organization/my_workspace' # required
    credentials: 'my_aws_credentials' # required
    wait: 'AVAILABLE' # optional
    file-path: './compute-envs/my_aws_compute_environment.json' # required
    overwrite: True
```
### 4. Using personal or user workspaces
To create resources such as pipelines, compute environments, credentials, secrets, etc. in your user workspace, omit the `workspace` key in your YAML file.

```yaml
compute-envs:
  - name: 'my_aws_compute_environment'
    type: 'aws-batch forge'
    file-path: './compute-envs/my_aws_compute_environment.json'
```
The above YAML will create the compute environment in your user workspace.

## Quick start

You must provide a YAML file that defines the options for each of the entities you would like to create in Seqera Platform.

You will need to have an account on Seqera Platform (see [Plans and pricing](https://seqera.io/pricing/)). You will also need access to a Workspace and a pre-defined Compute Environment where you can launch a pipeline.

### Launch via YAML

1. Create a YAML file called `hello-world-config.yml` with the contents below, and customise the `<YOUR_WORKSPACE>` and `<YOUR_COMPUTE_ENVIRONMENT>` entries as required:

   ```yaml # noqa
   launch:
     - name: 'hello-world' # Workflow name
       workspace: '<YOUR_WORKSPACE>' # Workspace name
       compute-env: '<YOUR_COMPUTE_ENVIRONMENT>' # Compute environment
       revision: 'master' # Pipeline revision
       pipeline: 'https://github.com/nextflow-io/hello' # Pipeline URL
   ```

2. Launch the pipeline with `seqerakit`:

   ```bash
   seqerakit hello-world-config.yml
   ```

3. Login to your Seqera Platform instance and check the Runs page in the appropriate Workspace for the pipeline you just launched!

### Launch via a Python script

You can also launch the same pipeline via a Python script. This will essentially allow you to extend the functionality on offer within the Seqera Platform CLI by leveraging the flexibility and customisation options available in Python.

1. Download the [`launch_hello_world.py`](./examples/python/launch_hello_world.py) Python script and customise the `<YOUR_WORKSPACE>` and `<YOUR_COMPUTE_ENVIRONMENT>` entries as required.

2. Launch the pipeline with `seqerakit`:

```bash
   python launch_hello_world.py
```

3. Login to your Seqera Platform instance and check the Runs page in the appropriate Workspace for the pipeline you just launched!

## Defining your YAML file using CLI options

All available options to provide as definitions in your YAML file can be determined by running the Seqera Platform CLI help command for your desired entity.

1. Retrieve CLI Options

To obtain a list of available CLI options for defining your YAML file, use the help command of the Seqera Platform CLI. For instance, if you want to configure a pipeline to be added to the Launchpad, you can view the options as follows:

```console
$ tw pipelines add -h

Usage: tw pipelines add [OPTIONS] PIPELINE_URL

Add a workspace pipeline.

Parameters:
*     PIPELINE_URL                         Nextflow pipeline URL.

Options:
* -n, --name=<name>                        Pipeline name.
  -w, --workspace=<workspace>              Workspace numeric identifier (TOWER_WORKSPACE_ID as default) or workspace reference as OrganizationName/WorkspaceName
  -d, --description=<description>          Pipeline description.
      --labels=<labels>[,<labels>...]      List of labels seperated by coma.
  -c, --compute-env=<computeEnv>           Compute environment name.
      --work-dir=<workDir>                 Path where the pipeline scratch data is stored.
  -p, --profile=<profile>[,<profile>...]   Comma-separated list of one or more configuration profile names you want to use for this pipeline execution.
      --params-file=<paramsFile>           Pipeline parameters in either JSON or YML format.
      --revision=<revision>                A valid repository commit Id, tag or branch name.
  ...
```

2. Define Key-Value Pairs in YAML

Translate each CLI option into a key-value pair in the YAML file. The structure of your YAML file should reflect the hierarchy and format of the CLI options. For instance:

```yaml
pipelines:
  - name: 'my_first_pipeline'
    url: 'https://github.com/username/my_pipeline'
    workspace: 'my_organization/my_workspace'
    description: 'My test pipeline'
    labels: 'yeast,test_data'
    compute-env: 'my_compute_environment'
    work-dir: 's3://my_bucket'
    profile: 'test'
    params-file: '/path/to/params.yaml'
    revision: '1.0'
```

In this example:

- `name`, `url`, `workspace`, etc., are the keys derived from the CLI options.
- The corresponding values are user-defined

### Using environment variables

You can also use environment variables to define the values for your YAML file. This is useful if you want to avoid hardcoding values in your YAML file or if you want to use the same YAML file for multiple Seqera Platform workspaces.

To use environment variables, you can prefix the value with `$` and the name of the environment variable. For example:

```sh
export PIPELINE_URL='https://github.com/nextflow/hello'
export WORKSPACE='my_workspace'
export COMPUTE_ENV='my_compute_environment'
```

```yaml
pipelines:
  - name: 'my_first_pipeline'
    url: '$PIPELINE_URL'
    workspace: '$WORKSPACE'
    compute-env: '$COMPUTE_ENV'
```

In addition, you can provide environment variables in the form of a file. To do this, you can use the `--env-file` flag. For example:

```bash
seqerakit --env-file /path/to/env.yaml
```

The environment variables in the file should be in the form of key-value pairs in YAML format, with the key being the name of the environment variable and the value being the value you want to use.

```yaml
# env.yaml
WORKSPACE: 'my_workspace'
COMPUTE_ENV: 'my_compute_environment'
```

Values in the provided environment file will override any existing environment variables.

### Best Practices:

- Ensure that the indentation and structure of the YAML file are correct - YAML is sensitive to formatting.
- Use quotes around strings that contain special characters or spaces.
- When listing multiple values (`labels`, `instance-types`, `allow-buckets`, etc), separate them with commas as shown above.
- For complex configurations, refer to the [Templates](./templates/) provided in this repository.

## Templates

We have provided template YAML files for each of the entities that can be created on Seqera Platform. These can be found in the [`templates/`](https://github.com/seqeralabs/blob/main/seqera-kit/templates) directory and should form a good starting point for you to add your own customization:

- [organizations.yml](./templates/organizations.yml)
- [members.yml](./templates/members.yml)
- [teams.yml](./templates/teams.yml)
- [workspaces.yml](./templates/workspaces.yml)
- [participants.yml](./templates/participants.yml)
- [credentials.yml](./templates/credentials.yml)
- [secrets.yml](./templates/secrets.yml)
- [compute-envs.yml](./templates/compute-envs.yml)
- [actions.yml](./templates/actions.yml)
- [datasets.yml](./templates/datasets.yml)
- [labels.yml](./templates/labels.yml)
- [pipelines.yml](./templates/pipelines.yml)
- [launch.yml](./templates/launch.yml)
- [data-links.yml](./templates/data-links.yml)
- [studios.yml](./templates/studios.yml)

## Real world example

Please see [`seqerakit-e2e.yml`](./examples/yaml/seqerakit-e2e.yml) for an end-to-end example that highlights how you can use `seqerakit` to create everything sequentially in Seqera Platform all the way from creating a new Organization to launching a pipeline.

You can modify this YAML to similarly create Seqera Platform resources end-to-end for your setup. This YAML encodes environment variables to protect sensitive keys, usernames, and passwords that are required to create or add certain resources (i.e. credentials, compute environments). Prior to running it with `seqerakit examples/yaml/seqerakit-e2e.yml`, you will have to set the following environment variables:

```console
$TOWER_GITHUB_PASSWORD
$DOCKERHUB_PASSWORD
$AWS_ACCESS_KEY_ID
$AWS_SECRET_ACCESS_KEY
$AWS_ASSUME_ROLE_ARN
$AZURE_BATCH_KEY
$AZURE_STORAGE_KEY
$GOOGLE_KEY
$SENTIEON_LICENSE_BASE64
```

## Contributions and Support

If you would like to contribute to `seqerakit`, please see the [contributing guidelines](./.github/CONTRIBUTING.md).

For further information or help, please don't hesitate to create an [issue](https://github.com/seqeralabs/seqera-kit/issues) in this repository.

## Credits

`seqerakit` was written by [Esha Joshi](https://github.com/ejseqera), [Adam Talbot](https://github.com/adamrtalbot) and [Harshil Patel](https://github.com/drpatelh) from the Scientific Development Team at [Seqera Labs](https://seqera.io/).
