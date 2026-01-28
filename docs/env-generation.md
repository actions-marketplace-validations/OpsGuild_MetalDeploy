# Environment File Generation

MetalDeploy includes powerful environment file generation capabilities that automatically create `.env` files from GitHub secrets and variables. This enables secure management of environment configurations without storing them in your repository.

## Features

- ✅ **Multiple Format Support** - ENV format (KEY=VALUE), JSON, YAML, and auto-detection
- ✅ **Flexible File Structures** - Single `.env` file, flat `.env.*` files, or nested `.envs/{environment}/` organization
- ✅ **Priority System** - Environment-specific secrets override base secrets automatically
- ✅ **All-in-One Secret Support** - Store multiple variables in single secrets
- ✅ **Secure Handling** - Files created with `0o600` permissions, no secret logging
- ✅ **Secrets & Variables** - Supports both GitHub Secrets (encrypted) and GitHub Variables (plaintext)

## Configuration

| Input | Description | Default |
|-------|-------------|---------|
| `env_files_generate` | Enable environment file generation | `false` |
| `env_files_structure` | File structure: `single`, `flat`, `nested`, `auto`, `custom` | `auto` |
| `env_files_path` | Custom path (when `structure=custom`) | - |
| `env_files_patterns` | Comma-separated patterns (`.env.app,.env.database`) | `.env.app,.env.database` |
| `env_files_create_root` | Also create a combined `.env` file in project root | `false` |
| `env_files_format` | Format for parsing: `auto`, `env`, `json`, `yaml` | `auto` |

## How it Works

1. **Discovery**: The action scans all environment variables starting with `ENV_`. It treats GitHub Secrets and GitHub Variables exactly the same.
2. **Bucketing**:
    - If `env_files_patterns` is provided, the action **only** looks for variables matching those specific buckets (e.g., `env_files_patterns: .env.app` only processes `ENV_APP_...` variables).
    - If `env_files_structure` is `auto` (and patterns are default), it automatically discovers all buckets based on your variable prefixes (e.g., `ENV_REDIS_URL` automatically creates a `.env.redis` file).
3. **Generation**: Files are generated on the remote server with secure permissions.

## Secret Naming Convention

### Individual Variables

```bash
# Base (environment-agnostic)
ENV_APP_DEBUG=false
ENV_APP_SECRET_KEY=base-key
ENV_DATABASE_HOST=localhost

# Environment-specific (higher priority)
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

## Usage Examples

### Example 1: Single .env File

```yaml
# GitHub Secrets:
# ENV_APP_DEBUG=false
# ENV_APP_SECRET_KEY=abc123
# ENV_DATABASE_HOST=localhost

- uses: ./
  with:
    env_files_generate: 'true'
    env_files_structure: 'single'
    environment: 'prod'
```

**Result**: Creates `/project/.env` with all variables merged.

### Example 2: Flat Mode with Individual Secrets

```yaml
# GitHub Secrets:
# ENV_APP_DEBUG=false
# ENV_APP_SECRET_KEY=abc123
# ENV_DATABASE_HOST=localhost
# ENV_REDIS_URL=redis://localhost:6379

- uses: ./
  with:
    env_files_generate: 'true'
    env_files_structure: 'flat'
    env_files_patterns: '.env.app,.env.database,.env.redis'
    environment: 'prod'
```

**Result**: Creates `.env.app`, `.env.database`, and `.env.redis` in project root. Use `env_files_path` to override base directory.

### Example 3: Nested Mode with Priority System

```yaml
# GitHub Secrets:
# ENV_APP_DEBUG=true
# ENV_PROD_APP_SECRET_KEY=prod-secret
# ENV_PROD_APP="DEBUG=false\nDATABASE_URL=postgresql://..."

- uses: ./
  with:
    env_files_generate: 'true'
    env_files_structure: 'nested'
    environment: 'prod'
```

**Result**: Creates `.envs/prod/.env.app` with merged variables:
- `DEBUG=false` (from ENV_PROD_APP)
- `SECRET_KEY=prod-secret` (from ENV_PROD_APP_SECRET_KEY)
- `DATABASE_URL=...` (from ENV_PROD_APP)

**With `env_files_create_root: true`:**
Also creates a single `/project/.env` file containing ALL variables merged together.

## File Structure Examples

### Single Mode
```
project/
├── .env          # All variables in one file
├── app.py
└── requirements.txt
```

### Flat Mode
```
project/
├── .env.app       # APP_* variables
├── .env.database  # DATABASE_* variables
├── .env.redis     # REDIS_* variables
└── app.py
```

### Nested Mode
```
project/
├── .envs/
│   ├── dev/
│   │   ├── .env.app
│   │   └── .env.database
│   └── prod/
│       ├── .env.app
│       └── .env.database
└── app.py
```

## Priority System

The priority system ensures proper variable overriding:

1. **Base secrets** (lowest priority):
   ```
   ENV_APP_DEBUG=false
   ENV_DATABASE_HOST=localhost
   ```

2. **Environment-specific secrets** (higher priority):
   ```
   ENV_PROD_APP_SECRET_KEY=prod-secret
   ENV_PROD_DATABASE_HOST=prod-host
   ```

3. **All-in-one environment-specific** (highest priority):
   ```
   ENV_PROD_APP="DEBUG=false\nSECRET_KEY=prod-override"
   ```

4. **All-in-one base** (fallback):
   ```
   ENV_APP="DEBUG=true\nVERSION=1.0"
   ```
