# Server Installation & Requirements

MetalDeploy automatically installs dependencies based on the deployment type. It only installs what's needed, checking if tools are already present before installing to save time.

## What Gets Installed

### All Deployments

These tools are installed for every deployment type:

- **Git**: Version control system for cloning repositories
- **Python 3 and pip**: Required for running the deployment script and some build tools
- **Build tools**: Essential compilation tools including:
  - `build-essential`: GCC compiler and make utilities
  - `libssl-dev`: OpenSSL development libraries
  - `libffi-dev`: Foreign Function Interface library

**Installation Method:** Uses `apt-get` package manager (Ubuntu/Debian)

### Docker Deployments

For `deployment_type: docker` or `deployment_type: k8s`, the following are installed:

- **Docker**: Container runtime engine
  - Installed from Docker's official repository
  - Latest stable version
  - Docker daemon is enabled and started automatically
- **Docker Compose**: Multi-container orchestration tool
  - Version 1.29.2 (stable)
  - Installed to `/usr/local/bin/docker-compose`
  - Made executable automatically

**Installation Method:** Official Docker installation script and direct download

**Post-Installation:**
- Current user is added to the `docker` group (requires logout/login to take effect)
- Docker service is enabled to start on boot
- Docker daemon is started immediately

### Kubernetes Deployments

For `deployment_type: k8s` only, the following are additionally installed:

- **kubectl**: Kubernetes command-line tool
  - Latest stable version from Kubernetes official releases
  - Installed to `/usr/local/bin/kubectl`
  - Used to interact with the k3s cluster

- **Helm**: Kubernetes package manager
  - Latest version from official Helm installation script
  - Used for deploying Helm charts (if needed)

- **k3s**: Lightweight Kubernetes distribution
  - Installed via official k3s installation script
  - Traefik ingress controller is disabled by default
  - Automatically enabled and started as a systemd service
  - kubeconfig is configured at `/etc/rancher/k3s/k3s.yaml`
  - Environment variable `KUBECONFIG` is set in `.bashrc`

**Installation Method:** Official installation scripts from respective projects

**Post-Installation:**
- k3s service is enabled to start on boot
- k3s service is started immediately
- KUBECONFIG environment variable is configured

### Installation Behavior

- **Idempotent**: The action checks if tools are already installed before attempting installation
- **Non-destructive**: Existing installations are not modified or removed
- **Fast**: Skips installation if tools are already present
- **Automatic**: No manual intervention required

**Note:** All installations require sudo/root access. The action handles this automatically.

## Sudo Usage

By default, the action doesnt use `sudo` for commands. You can enable this by setting `use_sudo: true`:

```yaml
use_sudo: true  # Run commands with sudo
```

**Note:** Some system-level commands (like `apt-get`, `systemctl`, `usermod`) will still use sudo regardless of this setting. Deployment commands (like `docker compose`, `make`, custom scripts) will respect the `use_sudo: true` setting.

This is useful when:
- Your SSH user already has necessary permissions
- You're using a non-root user with proper group memberships (e.g., docker group)
- You want to avoid password prompts for sudo

## Supported Server Types

This action supports the following server operating systems:

### Linux Distributions

- **Ubuntu** (all LTS and current versions)
- **Debian** (9+)
- Any other Debian/Ubuntu-based distributions that use:
  - `apt-get` package manager
  - `systemd` for service management
  - Standard Linux command-line tools

### Server Requirements

- SSH access (port 22 or custom port)
- Internet connectivity for package installation
- Sufficient disk space for dependencies and your application
- Root or sudo access for system-level operations

**Note:** The action is optimized for Ubuntu/Debian systems. Other Linux distributions may work but are not officially tested.
