# Environment File Generation

MetalDeploy includes powerful environment file generation capabilities that automatically create `.env` files from GitHub secrets and variables. This enables secure management of environment configurations without storing them in your repository.

## Features

- ✅ **Multiple Format Support** - ENV format (KEY=VALUE), JSON, YAML, and auto-detection
- ✅ **Flexible File Structures** - Single `.env` file, flat `.env.*` files, or nested `.envs/{environment}/` organization
- ✅ **Priority System** - Environment-specific secrets override base secrets automatically
- ✅ **All-in-One Secret Support** - Store multiple variables in single secrets
- ✅ **Strict Filtering** - Only processes keys starting with `ENV_` or the literal `ENV` to ensure security
- ✅ **Secure Handling** - Files created with `0o600` permissions, no secret logging
- ✅ **Secrets & Variables** - Supports both GitHub Secrets (encrypted) and GitHub Variables (plaintext)

## How it Works

1. **Discovery**: The action scans environment variables starting with `ENV_` or a literal `ENV`.
2. **Bucketing**:
    - **Literal `ENV`**: Treated as a non-prefixed global blob. Its contents go directly into the `.env` file without prefixes.
    - **`ENV_COMPONENT_...`**: Treated as part of a specific component (e.g., `ENV_APP_...` goes to `.env.app`).
    - **`ENV_ENVIRONMENT_...`**: Identifies prefixes matching common environments (`PROD`, `STAGING`, `DEV`, `TEST`) **plus** your current `environment` input.
3. **Strict Filtering**: MetalDeploy **only** processes secrets that start with `ENV_` or the literal `ENV`. Other secrets (like `STRIPE_KEY` or `GITHUB_TOKEN`) are ignored for security unless specifically prefixed.

## Priority System (Last one wins)

The priority system ensures that specific overrides always take precedence:

1. **Base Variables** (Lowest)
   Individual secrets or raw blocks are loaded first.
2. **Explicit Workflow `env:` Variables** (Medium)
   Variables you map directly in your workflow's `env:` block win over the blob.
3. **Environment Overrides** (Highest)
   Secrets matching your `environment` input (e.g. `ENV_PROD_...`) win last.

## Workflow Structure Example

Here is exactly how the `env:` block looks alongside the `with:` block in a GitHub Action:

```yaml
- name: Deploy to Staging
  uses: ./
  env:
    # MANUAL OVERRIDES GO HERE
    ENV_APP_PORT: 9090 # This wins over any other PORT setting
  with:
    env_files_generate: 'true'
    environment: 'staging'
    remote_host: ${{ secrets.REMOTE_HOST }}
    # ... other inputs ...
```

## Usage Example: Bulk Secret Injection

For the simplest setup, pass all secrets in one go:

- uses: ./
  with:
    env_files_generate: 'true'

**Security Check**: Only secrets you have named with the `ENV_` prefix in your repository settings will be processed. All other private secrets remain untouched.
