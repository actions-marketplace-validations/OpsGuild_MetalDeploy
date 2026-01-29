# Environment File Generation

MetalDeploy includes powerful environment file generation capabilities that automatically create `.env` files from GitHub secrets and variables. This enables secure management of environment configurations without storing them in your repository.

## Features

- ✅ **Multiple Format Support** - ENV format (KEY=VALUE), JSON, YAML, and auto-detection
- ✅ **Flexible File Structures** - Single `.env` file, flat `.env.*` files, or nested `.envs/{environment}/` organization
- ✅ **Priority System** - Environment-specific secrets override base secrets automatically
- ✅ **All-in-One Secret Support** - Store multiple variables in single secrets
- ✅ **Global Literal Blob** - Support for a literal `ENV` secret for non-prefixed global dumps
- ✅ **Secure Handling** - Files created with `0o604` permissions, no secret logging
- ✅ **Secrets & Variables** - Supports both GitHub Secrets (encrypted) and GitHub Variables (plaintext)

## Configuration

| Input | Description | Default |
|-------|-------------|---------|
| `env_files_generate` | Enable environment file generation | `false` |
| `env_files_structure` | File structure: `single`, `flat`, `nested`, `auto`, `custom` | `auto` |
| `env_files_path` | Custom path (when `structure=custom`) | - |
| `env_files_patterns` | Comma-separated patterns (`.env.app,.env.database`) | - |
| `env_files_create_root` | Also create a combined `.env` file in project root | `false` |
| `env_files_format` | Format for parsing: `auto`, `env`, `json`, `yaml` | `auto` |

## How it Works

1. **Discovery**: The action scans environment variables starting with `ENV_` or a literal `ENV` secret.
2. **Bucketing**:
    - **Literal `ENV`**: Treated as a non-prefixed global blob. Its contents go directly into the `.env` file without any modifications.
    - **`ENV_COMPONENT_...`**: Treated as part of a specific component (e.g., `ENV_APP_...` goes to `.env.app`).
    - **`ENV_ENVIRONMENT_...`**: Automatically identifies prefixes matching common environments (`PROD`, `STAGING`, `DEV`, `TEST`) **plus** your current `environment` input.
3. **Generation**: Files are generated on the remote server with secure permissions.

## Secret Naming Convention

### Literal Global Blob (No Prefix)
If you want to dump a list of variables without any prefixing or component logic, use the literal secret name `ENV`.

```bash
# GitHub Secret: ENV
PORT=8080
DEBUG=true
```
**Result**: `.env` contains `PORT=8080` and `DEBUG=true`.

### Individual Variables

```bash
# Base (environment-agnostic)
ENV_APP_DEBUG=false
ENV_APP_SECRET_KEY=base-key
ENV_DATABASE_HOST=localhost

# Environment-specific (higher priority)
# If environment input is 'prod', this will override base values
ENV_PROD_APP_SECRET_KEY=prod-secret
ENV_PROD_DATABASE_HOST=prod-host
```

### All-in-One Variables

```bash
# Environment-specific all-in-one (highest priority)
ENV_PROD_APP="
DEBUG=false
SECRET_KEY=prod-secret
DATABASE_URL=postgresql://prod-host:5432/db
"

# Base all-in-one (fallback)
ENV_APP="
DEBUG=true
SECRET_KEY=dev-secret
"
```

## Priority System

The priority system ensures proper variable overriding (last one wins):

1. **Literal `ENV`** (Lowest priority - Base Layer)
2. **Base Component secrets** (e.g., `ENV_APP_...`)
3. **Base All-in-one secrets** (e.g., `ENV_APP="..."`)
4. **Env-specific Component secrets** (e.g., `ENV_PROD_APP_...`)
5. **Env-specific All-in-one secrets** (Highest priority - `ENV_PROD_APP="..."`)

## Usage Examples

### Example 1: Custom Environment Names
MetalDeploy automatically supports your custom environment names for prefixes.

```yaml
- uses: ./
  with:
    env_files_generate: 'true'
    environment: 'qa' # Custom environment name
```
**Secrets**:
- `ENV_APP_PORT=8080` (Base)
- `ENV_QA_APP_PORT=9090` (Overrides base because environment is 'qa')

**Result**: `.env.app` will have `PORT=9090`.

### Example 2: Single Mode
```yaml
- uses: ./
  with:
    env_files_generate: 'true'
    env_files_structure: 'single'
```
**Result**: Creates `/project/.env` with all variables merged. Component variables are prefixed (e.g., `APP_PORT`, `DB_HOST`) to prevent collisions, while literal `ENV` variables remain un-prefixed.
