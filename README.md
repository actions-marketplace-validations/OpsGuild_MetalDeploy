# MetalDeploy Action

A comprehensive GitHub Action for deploying applications to baremetal servers via SSH. This action supports three deployment modes: baremetal (direct to server), Docker, and Kubernetes.

## Features

- 🔐 **Secure SSH Authentication** - Support for SSH keys or password authentication
- 🎯 **Multiple Deployment Types** - Choose between baremetal (default), Docker, or Kubernetes deployments
- 🐳 **Docker Support** - Automatic Docker and Docker Compose installation
- ☸️ **Kubernetes Support** - Automatic k3s, kubectl, and helm installation
- 🔧 **Auto Dependency Installation** - Installs git and other required tools
- 🏷️ **Registry Support** - Supports GHCR, Docker Hub, and AWS ECR
- 🌿 **Branch Management** - Automatic branch switching based on environment
- ⚡ **Smart Defaults** - Automatically uses current repository and GitHub actor for Git operations
- 📝 **Environment File Generation** - Automatically create `.env` files from GitHub secrets and variables
- 🔒 **All-in-One Secret Support** - Store multiple variables in single secrets with multiple formats (ENV, JSON, YAML)
- 🏗️ **Flexible File Structures** - Support single, flat, nested, auto, and custom file organization
- 🎛️ **Priority System** - Environment-specific secrets override base secrets automatically
- 🏗️ **Jenkins Compatible** - Fully compatible with Jenkins via pre-built GHCR image and Jenkinsfile

## Quick Links

- [Deployment Types](docs/deployment-types.md) - Baremetal, Docker, and Kubernetes details
- [Git Authentication](docs/git-auth.md) - Token, SSH, and No-Auth methods
- [Environment File Generation](docs/env-generation.md) - Dynamic `.env` creation from secrets
- [Jenkins Integration](docs/jenkins.md) - Using MetalDeploy outside of GitHub Actions
- [Installation & Requirements](docs/installation.md) - What gets installed on your server

## Default Values

MetalDeploy provides smart defaults to minimize configuration:

- **`git_url`**: Defaults to `${{ github.repositoryUrl }}` - automatically uses the current repository
- **`git_user`**: Defaults to `${{ github.actor }}` - automatically uses the GitHub user triggering the workflow
- **`deployment_type`**: Defaults to `baremetal` - direct server deployment without containers
- **`git_auth_method`**: Defaults to `none` - no authentication (for public repos)
- **`environment`**: Defaults to `dev` - development environment
- **`remote_user`**: Defaults to `root` - root user on remote server
- **`registry_type`**: Defaults to `ghcr` - GitHub Container Registry

## Usage

### Basic Example

```yaml
- name: Deploy with MetalDeploy
  uses: OpsGuild/MetalDeploy@v1
  with:
    git_auth_method: token
    git_token: ${{ secrets.GITHUB_TOKEN }}
    remote_host: ${{ secrets.REMOTE_HOST }}
    ssh_key: ${{ secrets.SSH_PRIVATE_KEY }}
    environment: prod
```

### Advanced Example with Docker

```yaml
- name: Deploy with MetalDeploy
  uses: OpsGuild/MetalDeploy@v1
  with:
    remote_host: ${{ secrets.REMOTE_HOST }}
    ssh_key: ${{ secrets.SSH_PRIVATE_KEY }}
    deployment_type: docker
    environment: prod
    registry_type: dockerhub
    registry_username: ${{ secrets.DOCKERHUB_USERNAME }}
    registry_password: ${{ secrets.DOCKERHUB_PASSWORD }}
```

## Inputs & Outputs

For a full list of inputs and outputs, please see the [Action Metadata](action.yml).

## Documentation

Comprehensive documentation can be found in the [docs/](docs/) directory:

- [Deployment Types](docs/deployment-types.md): Detailed information about each deployment strategy.
- [Git Authentication](docs/git-auth.md): How to configure repository access.
- [Environment File Generation](docs/env-generation.md): Securely manage your application settings.
- [Jenkins Integration](docs/jenkins.md): How to use this action in a Jenkins pipeline.
- [Installation & Requirements](docs/installation.md): Details about server setup and dependencies.

## Development & Testing

See [tests/README.md](tests/README.md) for details on the test suite and local development.

## License

MIT License - see [LICENSE](LICENSE) file for details

## Support

For issues and feature requests, please open an issue on the [GitHub repository](https://github.com/OpsGuild/MetalDeploy).
