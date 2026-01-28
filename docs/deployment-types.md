# Deployment Types

The `deployment_type` parameter determines how your application is deployed to the remote server. MetalDeploy supports three deployment types, each optimized for different use cases. **By default, MetalDeploy uses `baremetal` deployment**, which provides direct server deployment without containerization overhead.

**Important:** If you provide `deploy_command`, MetalDeploy will run that command first (in the repository directory) and skip the deployment-type-specific flow. This works for all deployment types, so you can override docker/k8s/baremetal behavior with a custom command when needed.

## 1. Baremetal Deployment (Default)

Baremetal deployment is the default deployment type and deploys your application directly to the server without Docker or Kubernetes. This is perfect for:
- Simple applications that don't require containerization
- Applications with system-level dependencies
- When you want full control over the deployment process
- Fast deployments without container overhead
- Legacy applications that aren't containerized

**How it works:**
1. The action clones your repository to the remote server
2. It then executes your deployment command in the repository directory
3. The deployment command can be specified explicitly or auto-detected

**Usage:**
```yaml
deployment_type: baremetal  # This is the default, so you can omit it
deploy_command: make deploy  # Optional: custom command to run
```

**Default Behavior (Command Resolution Order):**
1. If `deploy_command` is specified, runs that exact command
2. Otherwise, looks for `deploy.sh` in the repository root and runs it (with execute permissions)
3. If no `deploy.sh` exists, looks for `Makefile` and runs `make {environment}` (e.g., `make dev`, `make staging`, `make prod`)
4. If none of the above are found, the deployment will fail with an error asking you to specify `deploy_command`

**Example with explicit command:**
```yaml
- name: Deploy with MetalDeploy
  uses: OpsGuild/MetalDeploy@v1
  with:
    deployment_type: baremetal  # Optional since it's the default
    deploy_command: "npm install && npm run build && pm2 restart app"
    environment: prod
```

**Example with auto-detection (using Makefile):**
```yaml
- name: Deploy with MetalDeploy
  uses: OpsGuild/MetalDeploy@v1
  with:
    # deployment_type defaults to baremetal
    environment: staging
    # Will automatically run: make staging
```

**Example with deploy.sh script:**
```yaml
- name: Deploy with MetalDeploy
  uses: OpsGuild/MetalDeploy@v1
  with:
    environment: prod
    # Will automatically run: ./deploy.sh
```

**Best Practices:**
- Create a `deploy.sh` script for complex deployments with multiple steps
- Use a `Makefile` if you have multiple environments and want to keep commands organized
- Use `deploy_command` for simple one-off deployments or when you need dynamic commands

## 2. Docker Deployment

Docker deployment uses Docker Compose to deploy containerized applications. This is ideal for:
- Applications that are already containerized
- Multi-container applications (web, database, cache, etc.)
- Applications that need isolated environments
- Microservices architectures
- Applications requiring consistent runtime environments

**How it works:**
1. The action automatically installs Docker and Docker Compose if not already present
2. It clones your repository to the remote server
3. It authenticates with your Docker registry (GHCR, Docker Hub, or ECR)
4. It runs `docker compose up --build -d` to build and start your containers
5. Optionally uses Docker Compose profiles to deploy specific service sets

**Usage:**
```yaml
deployment_type: docker
profile: production  # Optional: use Docker Compose profiles
registry_type: ghcr  # or dockerhub, ecr
```

**Example with GitHub Container Registry (GHCR):**
```yaml
- name: Deploy with MetalDeploy
  uses: OpsGuild/MetalDeploy@v1
  with:
    deployment_type: docker
    git_token: ${{ secrets.GITHUB_TOKEN }}
    git_user: ${{ github.actor }}  # Default, can be omitted
    registry_type: ghcr  # Uses git_user and git_token for auth
    profile: production  # Optional: deploy only services with this profile
```

**Example with Docker Hub:**
```yaml
- name: Deploy with MetalDeploy
  uses: OpsGuild/MetalDeploy@v1
  with:
    deployment_type: docker
    registry_type: dockerhub
    registry_username: ${{ secrets.DOCKERHUB_USERNAME }}
    registry_password: ${{ secrets.DOCKERHUB_PASSWORD }}
    profile: production
```

**Example with AWS ECR:**
```yaml
- name: Deploy with MetalDeploy
  uses: OpsGuild/MetalDeploy@v1
  with:
    deployment_type: docker
    registry_type: ecr
    aws_region: us-east-1
    aws_account_id: ${{ secrets.AWS_ACCOUNT_ID }}
    # Requires AWS credentials configured on the remote server
```

**Requirements:**
- Your repository must have a `docker-compose.yml`, `docker-compose.yaml`, `compose.yml`, or `compose.yaml` file
- Your Docker images must be available in the specified registry
- The remote server must have internet access to pull images

**Docker Compose Profiles:**
Profiles allow you to deploy specific subsets of services defined in your `docker-compose.yml`. For example:
```yaml
services:
  web:
    profiles: ["production"]
  worker:
    profiles: ["production", "staging"]
  dev-tools:
    profiles: ["dev"]
```
When you specify `profile: production`, only services with the `production` profile will be deployed.

## 3. Kubernetes Deployment

Kubernetes deployment uses k3s (a lightweight Kubernetes distribution) to deploy containerized applications. This is ideal for:
- Production-grade container orchestration
- Applications requiring high availability and scaling
- Complex multi-service applications
- Applications that need service discovery and load balancing
- Teams familiar with Kubernetes

**How it works:**
1. The action automatically installs k3s, kubectl, and helm if not already present
2. It installs Docker (required by k3s for container runtime)
3. It clones your repository to the remote server
4. It authenticates with your Docker registry
5. It creates the specified Kubernetes namespace (if it doesn't exist)
6. It applies all Kubernetes manifests from the specified path

**k3s Overview:**
k3s is a certified Kubernetes distribution designed for resource-constrained environments. It's perfect for:
- Single-node Kubernetes clusters
- Edge computing deployments
- Development and testing environments
- Small to medium production workloads

**Usage:**
```yaml
deployment_type: k8s
k8s_manifest_path: k8s/  # Optional: auto-detected if not specified
k8s_namespace: production  # Optional: defaults to 'default'
registry_type: ghcr  # Required for pulling container images
```

**Default Behavior (Manifest Path Resolution):**
The action will automatically search for Kubernetes manifests in this order:
1. If `k8s_manifest_path` is specified, uses that path
2. Otherwise, looks for directories: `k8s/`, `manifests/`, or `kubernetes/`
3. If no directory found, looks for files: `k8s.yaml`, `k8s.yml`, `deployment.yaml`, or `deployment.yml`
4. If nothing is found, the deployment will fail with an error

**Example with directory of manifests:**
```yaml
- name: Deploy with MetalDeploy
  uses: OpsGuild/MetalDeploy@v1
  with:
    deployment_type: k8s
    k8s_manifest_path: k8s/  # Directory containing YAML files
    k8s_namespace: production
    registry_type: ghcr
    git_token: ${{ secrets.GITHUB_TOKEN }}
```

**Example with single manifest file:**
```yaml
- name: Deploy with MetalDeploy
  uses: OpsGuild/MetalDeploy@v1
  with:
    deployment_type: k8s
    k8s_manifest_path: deployment.yaml  # Single file
    k8s_namespace: staging
```

**Example with auto-detection:**
```yaml
- name: Deploy with MetalDeploy
  uses: OpsGuild/MetalDeploy@v1
  with:
    deployment_type: k8s
    # Will automatically find k8s/, manifests/, or kubernetes/ directory
    k8s_namespace: production
```

**Requirements:**
- Your repository should have Kubernetes manifest files (YAML) in a `k8s/`, `manifests/`, or `kubernetes/` directory, or a single manifest file
- Your container images must be available in the specified registry
- The remote server must have sufficient resources (RAM, CPU) for k3s and your workloads
- At least 512MB RAM recommended for k3s alone

**Namespace Management:**
- The action automatically creates the namespace if it doesn't exist
- All resources are deployed to the specified namespace
- Use different namespaces for different environments (dev, staging, prod)

**k3s Configuration:**
- k3s is installed with Traefik disabled (you can use your own ingress controller)
- kubeconfig is automatically configured at `/etc/rancher/k3s/k3s.yaml`
- The action sets `KUBECONFIG` environment variable for kubectl commands

## Registry Types

### GitHub Container Registry (GHCR)

Uses `git_user` and `git_token` for authentication.

```yaml
registry_type: ghcr
```

### Docker Hub

Requires `registry_username` and `registry_password`.

```yaml
registry_type: dockerhub
registry_username: ${{ secrets.DOCKERHUB_USERNAME }}
registry_password: ${{ secrets.DOCKERHUB_PASSWORD }}
```

### AWS ECR

Requires `aws_region` and `aws_account_id`. The action will use AWS CLI to authenticate.

```yaml
registry_type: ecr
aws_region: us-east-1
aws_account_id: 123456789012
```
