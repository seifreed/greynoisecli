<p align="center">
  <img src="https://img.shields.io/badge/greynoisecli-GreyNoise%20API%20client-blue?style=for-the-badge" alt="greynoisecli">
</p>

<h1 align="center">greynoisecli</h1>

<p align="center">
  <strong>Typed Python client and command-line interface for the GreyNoise API</strong>
</p>

<p align="center">
  <a href="https://pypi.org/project/greynoisecli/"><img src="https://img.shields.io/pypi/v/greynoisecli?style=flat-square&logo=pypi&logoColor=white" alt="PyPI Version"></a>
  <a href="https://pypi.org/project/greynoisecli/"><img src="https://img.shields.io/pypi/pyversions/greynoisecli?style=flat-square&logo=python&logoColor=white" alt="Python Versions"></a>
  <a href="https://github.com/seifreed/greynoisecli/actions/workflows/ci.yml"><img src="https://img.shields.io/github/actions/workflow/status/seifreed/greynoisecli/ci.yml?style=flat-square&logo=github&label=CI" alt="CI Status"></a>
  <img src="https://img.shields.io/badge/python-3.14-blue?style=flat-square&logo=python&logoColor=white" alt="Python 3.14">
  <img src="https://img.shields.io/badge/typing-strict-brightgreen?style=flat-square" alt="Strict typing">
  <img src="https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey?style=flat-square" alt="Supported platforms">
</p>

<p align="center">
  <a href="https://github.com/seifreed/greynoisecli/stargazers"><img src="https://img.shields.io/github/stars/seifreed/greynoisecli?style=flat-square" alt="GitHub Stars"></a>
  <a href="https://github.com/seifreed/greynoisecli/issues"><img src="https://img.shields.io/github/issues/seifreed/greynoisecli?style=flat-square" alt="GitHub Issues"></a>
  <a href="https://buymeacoffee.com/seifreed"><img src="https://img.shields.io/badge/Buy%20Me%20a%20Coffee-support-yellow?style=flat-square&logo=buy-me-a-coffee&logoColor=white" alt="Buy Me a Coffee"></a>
</p>

---

## Overview

**greynoisecli** provides library and CLI access to all 68 operations registered
from the current [GreyNoise API reference](https://docs.greynoise.io/reference/getcommunityip).
It supports structured queries, JSON request bodies, formatted responses, and
streaming downloads without adding an SDK-specific abstraction for every
endpoint.

### Key Features

| Feature | Description |
|---------|-------------|
| **Complete API Surface** | 68 registered GreyNoise operations exposed by OpenAPI `operationId` and CLI name |
| **CLI + Library** | Use the same endpoint registry from a terminal or Python application |
| **Structured Requests** | Path parameters, repeatable query values, inline JSON, and `@file` bodies |
| **Multiple Outputs** | Automatic output plus JSON, Rich table, and TOON 4.1 formats |
| **Streaming Downloads** | Stream PCAP, database, and other binary responses directly to disk |
| **Atomic Files** | Replace output files only after the complete response has been received |
| **Typed API** | Strictly typed public models and client methods for Python 3.14 |
| **Secure Defaults** | Verified HTTPS by default, strict JSON handling, and terminal-safe structured output |

### Supported Outputs

```text
JSON responses    Pretty JSON, Rich tables, TOON 4.1
Text responses    Original text
Binary responses  Original bytes or streamed files
Library access    Parsed JSON values or raw response bytes
```

---

## Installation

### From PyPI (Recommended)

```bash
python3.14 -m pip install greynoisecli
```

### From GitHub

```bash
python3.14 -m pip install "git+https://github.com/seifreed/greynoisecli.git"
```

### From Source

```bash
git clone https://github.com/seifreed/greynoisecli.git
cd greynoisecli
python3.14 -m venv .venv
```

Activate the environment on Linux or macOS:

```bash
source .venv/bin/activate
```

Or on Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

Then install the package:

```bash
python -m pip install -e .
```

---

## Configuration

Set the API key in the environment.

Linux or macOS:

```bash
export GREYNOISE="your-api-key"
```

Windows PowerShell:

```powershell
$env:GREYNOISE = "your-api-key"
```

Alternatively, create `greynoise/config.toml` below `$XDG_CONFIG_HOME`,
`%APPDATA%`, or `~/.config`:

```toml
[greynoise]
api_key = "your-api-key"
```

Use `GREYNOISE_CONFIG` or the global `--config` option to select another file.
The environment variable takes precedence over the configuration file.

---

## Quick Start

```bash
# List every supported operation
greynoise operations

# Query the Community API
greynoise get-community-ip 8.8.8.8

# Query IP context with an optional parameter
greynoise v3-ip 8.8.8.8 --query quick=true

# Run a GNQL query and render a table
greynoise gnql-v3-query \
  --query "query=classification:malicious" \
  --query size=10 \
  --format table
```

---

## Usage

### Command Line Interface

Every OpenAPI `operationId` is available in kebab case. Path parameters are
positional, query parameters use repeatable `--query NAME=VALUE` options, and
request bodies use `--data` with inline JSON or `@filename`.

```bash
# Send a JSON request body
greynoise v3-multi-ip \
  --data '{"ips":["8.8.8.8","1.1.1.1"],"quick":true}'

# Export compact TOON for LLM context
greynoise gnql-v3-query \
  --query "query=classification:malicious" \
  --format toon \
  --output results.toon

# Stream a PCAP response
greynoise get-session-pcap SESSION_ID --output capture.pcap

# Select another documented response media type
greynoise post-psychic-model-download \
  --accept application/vnd.maxmind.maxmind-db \
  --output model.mmdb
```

Run `greynoise COMMAND --help` to see an operation's HTTP method, path, and
available options.

### Main Options

| Option | Description |
|--------|-------------|
| `--config FILE` | Read the API key from a specific TOML file |
| `--timeout SECONDS` | Set the request timeout |
| `-q, --query NAME=VALUE` | Add a query parameter; repeat for multiple values |
| `--data JSON\|@FILE` | Send an inline or file-backed JSON body |
| `--format auto\|json\|table\|toon` | Select response formatting |
| `--accept MEDIA_TYPE` | Override the requested response media type |
| `-o, --output FILE` | Write the complete response atomically to a file |

---

## Python Library

`GreyNoiseClient.call` accepts either an OpenAPI `operationId` or its CLI name,
so every registered operation shares one predictable interface.

```python
from greynoisecli import ResponseOptions, create_client

client = create_client()  # GREYNOISE or the configuration file

community = client.call(
    "getCommunityIP",
    path={"ip": "8.8.8.8"},
)
print(community.json())

results = client.call(
    "gnql-v3-query",
    query={"query": "classification:malicious", "size": 10},
)
print(results.json())

with open("model.mmdb", "wb") as output:
    client.stream(
        "postPsychicModelDownload",
        ResponseOptions(
            accept="application/vnd.maxmind.maxmind-db",
            output=output,
        ),
        body={"model": "internet_scanner_intelligence"},
    )
```

Use `GreyNoiseClient(api_key="...")` when the caller already manages secrets.
For an endpoint added after this package release, `GreyNoiseClient.request` can
call its HTTP method and path directly.

---

## Development

Install the package and the development dependency group declared in the same
`pyproject.toml` file:

```bash
python3.14 -m pip install -e . --group dev
```

Run the project gates:

```bash
pytest --cov --cov-branch
black --check .
ruff check .
mypy .
bandit -r .
pip-audit
```

See [ARCHITECTURE.md](ARCHITECTURE.md) for module responsibilities and the
dependency rule.

---

## CI and Releases

CI runs the complete test, quality, and security gates on `ubuntu-latest`,
`windows-latest`, and `macos-latest`. The same matrix must pass before a tagged
release can be built.

Releases are published from tags that match the version in `pyproject.toml`:

```bash
# First update project.version in pyproject.toml and commit it.
git tag -a v0.1.0 -m "greynoisecli 0.1.0"
git push origin v0.1.0
```

The release workflow builds both the source distribution and wheel, then
publishes them to PyPI with OIDC. It does not use a PyPI password or API token.

Before the first release, configure a pending Trusted Publisher in PyPI with:

| Setting | Value |
|---------|-------|
| PyPI project | `greynoisecli` |
| Owner | `seifreed` |
| Repository | `greynoisecli` |
| Workflow | `release.yml` |
| Environment | `pypi` |

Create the matching `pypi` environment in GitHub and restrict it to release
tags before pushing the first version tag.

---

## Requirements

- Python 3.14
- Windows, Linux, or macOS on x64 or ARM
- A GreyNoise API key for authenticated operations
- See [pyproject.toml](pyproject.toml) for the single runtime and development dependency declaration

---

## Contributing

1. Fork the repository.
2. Create a feature branch: `git switch -c feature/amazing-feature`.
3. Add tests and run every quality and security gate.
4. Commit and push the branch.
5. Open a pull request.

---

## Support the Project

If this project is useful in your workflows, you can support development:

<a href="https://buymeacoffee.com/seifreed" target="_blank">
  <img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="Buy Me A Coffee" height="50">
</a>

---

**Attribution**

- Author: **Marc Rivero Lopez** | [@seifreed](https://github.com/seifreed)
- Repository: [github.com/seifreed/greynoisecli](https://github.com/seifreed/greynoisecli)

---

<p align="center">
  <sub>Built for practical GreyNoise threat-intelligence workflows</sub>
</p>
