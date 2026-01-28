# Manual Usage Guide

MetalDeploy can be run manually on any machine with Python installed. This is useful for testing, one-off deployments, or when you prefer a CLI-based workflow.

## Prerequisites

- **Python 3.9+**
- **Poetry** (recommended) or **pip**
- **SSH Access** to your remote server

## Installation

### Method 1: One-Liner Installer (Recommended)

The easiest way to install MetalDeploy is via the official installation script:

```bash
curl -sSL https://raw.githubusercontent.com/OpsGuild/MetalDeploy/main/scripts/install.sh | bash
```

This will clone the repository to `~/.metal-deploy` and install a `metaldeploy` command in `~/.local/bin`.

### Method 2: Manual Clone

1. Clone the repository:
   ```bash
   git clone https://github.com/OpsGuild/MetalDeploy.git
   cd MetalDeploy
   ```

2. Install dependencies:
   ```bash
   # Using Poetry (recommended)
   poetry install

   # Or using pip
   pip install fabric invoke pyyaml
   ```

## Running the CLI

After installation, you can run MetalDeploy using the `metaldeploy` command from any directory.

### Basic Usage

```bash
metaldeploy \
  --host 1.2.3.4 \
  --user root \
  --ssh-key ~/.ssh/id_rsa \
  --git-url https://github.com/myuser/myrepo.git \
  --type baremetal \
  --env prod
```

### Usage without Global Installation

If you prefer not to install it globally, you can run the script directly from the cloned repository:
```bash
python main.py --help
```

### Available Arguments

| Argument | Description | Default |
|----------|-------------|---------|
| `--host` | Remote host IP or domain | `127.0.0.1` |
| `--user` | SSH remote user | `root` |
| `--password` | SSH password (if not using keys) | - |
| `--ssh-key` | Path to SSH private key | - |
| `--type` | `baremetal`, `docker`, or `k8s` | `baremetal` |
| `--env` | `dev`, `staging`, `prod` | `dev` |
| `--dir` | Remote deployment directory | `/root` or `/home/{user}` |
| `--command` | Custom deployment command | - |
| `--git-url` | Git repository URL | - |
| `--git-auth` | `token`, `ssh`, or `none` | `none` |
| `--registry` | `ghcr`, `dockerhub`, or `ecr` | `ghcr` |
| `--gen-env` | Enable `.env` file generation | `false` |
| `--sudo` | Use `sudo` for commands | `false` |

### Environment Variables

The CLI also respects all environment variables supported by the GitHub Action. CLI arguments will take priority over environment variables.

```bash
export REMOTE_HOST="1.2.3.4"
export SSH_KEY="$(cat ~/.ssh/id_rsa)"
metaldeploy --type docker
```
