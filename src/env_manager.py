import base64
import json
import os
import re
from typing import Dict, List

import yaml

from src import config
from src.connection import run_command


def parse_all_in_one_secret(
    secret_content: str, format_hint: str = "auto", strip_quotes: bool = True
) -> Dict[str, str]:
    """Parse all-in-one secret with multiple format support"""
    if not secret_content:
        return {}

    secret_content = secret_content.strip()

    # Check if the content is a file path (common in Jenkins/CI)
    if os.path.isfile(secret_content):
        try:
            with open(secret_content, "r") as f:
                secret_content = f.read().strip()
        except Exception:
            pass  # Fallback to treating as literal string

    # Pre-process content to handle escaped newlines for JSON/YAML
    processed_content = secret_content.replace("\\n", "\n")

    if format_hint == "auto":
        # Check if it's a JSON blob
        if processed_content.startswith("{") and processed_content.endswith("}"):
            try:
                parsed = json.loads(processed_content)
                if isinstance(parsed, dict):
                    return {str(k): str(v) for k, v in parsed.items()}
            except Exception:
                pass

        # Check if it looks like YAML (contains keys with colons)
        if ":" in processed_content:
            try:
                parsed = yaml.safe_load(processed_content)
                # Only return if it's a dict with more than one item or looks like a mapping
                if isinstance(parsed, dict) and (
                    len(parsed) > 1 or any(":" in line for line in processed_content.splitlines())
                ):
                    return {str(k): str(v) for k, v in parsed.items()}
            except Exception:
                pass

        # Default to ENV if it has equals sign
        if "=" in secret_content:
            format_hint = "env"

    if format_hint == "json":
        try:
            parsed = json.loads(processed_content)
            if isinstance(parsed, dict):
                return {str(k): str(v) for k, v in parsed.items()}
        except Exception:
            pass

    if format_hint == "yaml":
        try:
            parsed = yaml.safe_load(processed_content)
            if isinstance(parsed, dict):
                return {str(k): str(v) for k, v in parsed.items()}
        except Exception:
            pass

    if format_hint == "env":
        # Remove comment lines first to clean up the block
        lines = secret_content.splitlines()
        clean_content = "\n".join([line for line in lines if not line.strip().startswith("#")])

        env_vars = {}
        # Regex to find all KEY= pairs.
        # It looks for valid keys at the start of the string or after a delimiter (space, comma, newline)
        key_matches = list(re.finditer(r"(?:^|[\s,])([A-Z0-9_]+)=", clean_content))

        if not key_matches:
            # If no KEY= patterns found, return empty
            return {}

        for i in range(len(key_matches)):
            key = key_matches[i].group(1)
            # Value starts after the '='
            val_start = key_matches[i].end()
            # Value ends where the next key starts, or at the end of the content
            val_end = key_matches[i + 1].start() if i + 1 < len(key_matches) else len(clean_content)

            raw_value = clean_content[val_start:val_end].strip()

            # Post-process the value:
            # 1. Strip trailing delimiters (commas/spaces)
            # 2. Handle quoting: only if strip_quotes is True
            value = raw_value.rstrip(" ,")

            if strip_quotes and (
                (value.startswith('"') and value.endswith('"'))
                or (value.startswith("'") and value.endswith("'"))
            ):
                # Strip outside quotes but keep internal content (including newlines/escapes)
                value = value[1:-1]

            env_vars[key] = value

        return env_vars

    return {}


def merge_raw_env(base_content: str, overrides: Dict[str, str]) -> str:
    """Merge overrides into base_content while preserving comments and formatting"""
    if not base_content:
        return "\n".join([f"{k}={v}" for k, v in overrides.items()])

    lines = base_content.splitlines()
    result_lines = []
    processed_keys = set()

    for line in lines:
        stripped = line.strip()
        # Preserve comments and empty lines
        if not stripped or stripped.startswith("#"):
            result_lines.append(line)
            continue

        # Look for KEY=VALUE
        if "=" in stripped:
            key = stripped.split("=", 1)[0].strip()
            if key in overrides:
                # Replace the line with the override
                result_lines.append(f"{key}={overrides[key]}")
                processed_keys.add(key)
                continue

        result_lines.append(line)

    # Append new keys that weren't in the base content
    for k, v in overrides.items():
        if k not in processed_keys:
            # If the last line isn't empty, add a separator if this is the first new key
            if not processed_keys and result_lines and result_lines[-1].strip():
                result_lines.append("")
            result_lines.append(f"{k}={v}")
            processed_keys.add(k)

    return "\n".join(result_lines)


def detect_file_patterns(
    all_env_vars: Dict[str, str], structure: str, environment: str = ""
) -> List[str]:
    """Auto-detect file patterns from variable names"""
    if structure == "single":
        return [".env"]

    patterns = set()
    env_upper = (environment or "").upper()

    for var_name in all_env_vars.keys():
        if var_name.startswith("ENV_FILES_"):
            continue

        # Determine if it's environment-specific
        matched_env = ""
        # Dynamic check for current environment + common fallbacks
        env_candidates = list(set([env_upper, "PROD", "STAGING", "DEV", "TEST", "PRODUCTION"]))
        for env in env_candidates:
            if not env:
                continue
            if var_name.startswith(f"ENV_{env}_"):
                matched_env = env
                break
            # Handle exact match like ENV_PROD_APP (blob)
            if var_name == f"ENV_{env}":
                matched_env = env
                break

        # If it's for another environment, skip it
        if matched_env and matched_env != env_upper:
            continue

        # Extract component name
        suffix = ""
        if matched_env:
            # Strip ENV_{ENV}_ or ENV_{ENV}
            for prefix in [f"ENV_{matched_env}_", f"ENV_{matched_env}"]:
                if var_name.startswith(prefix):
                    suffix = var_name[len(prefix) :]
                    break
        elif var_name.startswith("ENV_"):
            # Strip ENV_
            suffix = var_name[4:]
        else:
            # This is a direct variable (no prefix) from a blob, it goes to the primary .env
            continue

        # Clean up leading underscores if any (e.g. _REDIS)
        suffix = suffix.lstrip("_")

        if suffix:
            filename = suffix.split("_")[0].lower()
            if filename:
                patterns.add(f".env.{filename}")
        else:
            pass

    return sorted(list(patterns)) or [".env.app"]


def determine_file_structure(
    structure: str, patterns: List[str], environment: str, base_path: str
) -> Dict[str, str]:
    """Determine file paths based on structure preference"""
    file_paths = {}

    if structure == "auto":
        # Heuristic: multiple patterns or presence of env-specific vars -> nested
        has_env_specific = False
        if environment:
            env_upper = environment.upper()
            for var_name in os.environ:
                if var_name.startswith(f"ENV_{env_upper}_"):
                    has_env_specific = True
                    break

        if len(patterns) > 1 or has_env_specific:
            structure = "nested"
        else:
            structure = "flat"

    dir_base = base_path
    use_default_envs = True
    if config.ENV_FILES_PATH:
        # Join relative path with base_path, keep absolute path as is
        if os.path.isabs(config.ENV_FILES_PATH):
            dir_base = config.ENV_FILES_PATH
        else:
            dir_base = os.path.join(base_path, config.ENV_FILES_PATH)
        use_default_envs = False

    if structure == "single":
        file_paths[".env"] = os.path.join(dir_base, ".env")
    elif structure == "flat":
        for pattern in patterns:
            file_paths[pattern] = os.path.join(dir_base, pattern)
    elif structure == "nested":
        if use_default_envs:
            env_dir = os.path.join(dir_base, ".envs", environment)
        else:
            env_dir = os.path.join(dir_base, environment)

        for pattern in patterns:
            file_paths[pattern] = os.path.join(env_dir, pattern)

    return file_paths


def merge_env_vars_by_priority(
    all_env_vars: Dict[str, str], environment: str, pattern: str
) -> Dict[str, str]:
    """Merge environment variables with proper priority"""
    merged = {}
    env_upper = (environment or "").upper()

    # 1. Handle Global File (.env) - Retain Component Prefixes to avoid collisions
    if pattern == ".env":
        # Base variables (ENV_X)
        for k, v in all_env_vars.items():
            if k.startswith("ENV_"):
                # Skip internal configuration and raw blobs
                if k.startswith("ENV_FILES_") or k == "ENV":
                    continue

                # Skip environment-specific ones
                env_candidates = [env_upper, "PROD", "STAGING", "DEV", "TEST", "PRODUCTION"]
                if any(k.startswith(f"ENV_{e}_") for e in env_candidates if e):
                    continue

                key = k[4:]  # e.g. APP or APP_PORT
                parsed = parse_all_in_one_secret(v, config.ENV_FILES_FORMAT)
                if parsed:
                    # If it's a component-level blob (e.g. ENV_APP), prefix its contents
                    # e.g. ENV_APP -> BASE_URL becomes APP_BASE_URL
                    # Unless it's already an individual var (key has underscore)
                    if "_" in key:
                        merged[key] = v
                    else:
                        for pk, pv in parsed.items():
                            p_key = pk if pk.startswith(f"{key.upper()}_") else f"{key}_{pk}"
                            merged[p_key] = pv
                else:
                    merged[key] = v

        # Environment-specific overrides (ENV_PROD_X)
        prefix = f"ENV_{env_upper}_"
        for k, v in all_env_vars.items():
            if k.startswith(prefix):
                key = k[len(prefix) :]
                parsed = parse_all_in_one_secret(v, config.ENV_FILES_FORMAT)
                if parsed:
                    if "_" in key:
                        merged[key] = v
                    else:
                        for pk, pv in parsed.items():
                            p_key = pk if pk.startswith(f"{key.upper()}_") else f"{key}_{pk}"
                            merged[p_key] = pv
                else:
                    merged[key] = v
        return merged

    # 2. Handle Patterned Files (.env.component) - Clean keys
    file_base = pattern.replace(".env.", "").upper()

    # Priority stages:
    # A. Base Individual (ENV_APP_PORT)
    # B. Base Blob (ENV_APP)
    # C. Env Individual (ENV_PROD_APP_PORT)
    # D. Env Blob (ENV_PROD_APP)

    # A. Prefix search (e.g. ENV_APP_...)
    base_prefix = f"ENV_{file_base}_"
    for k, v in all_env_vars.items():
        if k.startswith(base_prefix):
            key = k[len(base_prefix) :]
            merged[key] = v

    # B. Component Blob (e.g. ENV_APP)
    base_blob_key = f"ENV_{file_base}"
    if base_blob_key in all_env_vars:
        parsed = parse_all_in_one_secret(all_env_vars[base_blob_key], config.ENV_FILES_FORMAT)
        if parsed:
            # Strip component prefix if present to stay consistent with A/C
            for pk, pv in parsed.items():
                p_key = pk[len(f"{file_base}_") :] if pk.startswith(f"{file_base}_") else pk
                merged[p_key] = pv
        elif all_env_vars[base_blob_key].strip():
            merged[file_base] = all_env_vars[base_blob_key]

    # C. Env Specific Individual (e.g. ENV_PROD_APP_...)
    env_prefix = f"ENV_{env_upper}_{file_base}_"
    for k, v in all_env_vars.items():
        if k.startswith(env_prefix):
            key = k[len(env_prefix) :]
            merged[key] = v

    # D. Env Specific Blob (e.g. ENV_PROD_APP)
    comp_env_key = f"ENV_{env_upper}_{file_base}"
    if comp_env_key in all_env_vars:
        parsed = parse_all_in_one_secret(all_env_vars[comp_env_key], config.ENV_FILES_FORMAT)
        if parsed:
            for pk, pv in parsed.items():
                p_key = pk[len(f"{file_base}_") :] if pk.startswith(f"{file_base}_") else pk
                merged[p_key] = pv
        elif all_env_vars[comp_env_key].strip():
            merged[file_base] = all_env_vars[comp_env_key]

    return merged


def detect_environment_secrets() -> Dict[str, str]:
    """Auto-detect secrets and return raw file content mapped by pattern"""
    # 1. Get Base Template (ENV)
    base_template = os.environ.get("ENV") or ""

    # 2. Collect Overrides (ENV_...)
    # We group variables by their intended file pattern
    raw_overrides = {}
    for k, v in os.environ.items():
        if k.startswith("ENV_") and not k.startswith("ENV_FILES_"):
            raw_overrides[k] = v

    structure = config.ENV_FILES_STRUCTURE
    if structure == "single":
        patterns = [".env"]
    else:
        patterns = detect_file_patterns(raw_overrides, structure, config.ENVIRONMENT)
        if config.ENV_FILES_PATTERNS and structure != "auto":
            patterns = [p.strip() for p in config.ENV_FILES_PATTERNS if p.strip()]

    result = {}

    for pattern in patterns:
        # Merge individual vars for this pattern
        # Note: merge_env_vars_by_priority already handles prefixes and blobs
        # and returns a final flattened dict of KEY:VALUE
        overrides = merge_env_vars_by_priority(raw_overrides, config.ENVIRONMENT, pattern)

        if pattern == ".env":
            # For the main .env, we use the base template
            result[pattern] = merge_raw_env(base_template, overrides)
        else:
            # For patterned files, we just generate the KV pairs (or we could support ENV_{COMP})
            # Check if there's a component-specific base template (e.g. ENV_APP)
            comp_base_key = f"ENV_{pattern.replace('.env.', '').upper()}"
            comp_base = ""
            if comp_base_key in raw_overrides:
                comp_base = raw_overrides[comp_base_key]
                # If it's a blob, we don't want to use it as a 'raw template' if it looks like JSON
                if comp_base.strip().startswith("{"):
                    comp_base = ""

            result[pattern] = merge_raw_env(comp_base, overrides)

    return result


def create_env_file(conn, file_path: str, env_content: str) -> None:
    """Create .env file with secure permissions (0o600) via run_command (supports sudo)"""
    if not env_content:
        return
    dir_path = os.path.dirname(file_path)
    # Use base64 to avoid shell character/newline mangling issues
    encoded = base64.b64encode(env_content.encode("utf-8")).decode("utf-8")

    # Batch commands into one SSH round-trip and skip expensive shell profile sourcing
    batch_cmd = (
        f'mkdir -p "{dir_path}" && '
        f'echo "{encoded}" | base64 -d | tee "{file_path}" > /dev/null && '
        f'chmod 600 "{file_path}"'
    )
    run_command(conn, batch_cmd, use_shell_profile=False)


def generate_env_files(conn) -> None:
    """Main function to generate environment files from secrets"""
    if not config.ENV_FILES_GENERATE:
        return

    print("🔧 Generating environment files from secrets...")
    try:
        all_env_vars = {
            k: v
            for k, v in os.environ.items()
            if (k.startswith("ENV_") or k == "ENV") and not k.startswith("ENV_FILES_")
        }
        env_file_data = detect_environment_secrets()
        if not env_file_data:
            print("ℹ\ufe0f  No environment variables found to generate files")
            return

        # Determine paths for ALL patterns together to allow proper auto-detection (nested vs flat)
        file_paths = determine_file_structure(
            config.ENV_FILES_STRUCTURE,
            list(env_file_data.keys()),
            config.ENVIRONMENT,
            config.GIT_SUBDIR,
        )

        for pattern, env_content in env_file_data.items():
            file_path = file_paths.get(pattern)
            if file_path:
                print(f"📝 Creating {file_path} (formatted content preserved)")
                create_env_file(conn, file_path, env_content)

        if config.ENV_FILES_CREATE_ROOT:
            # Generate the root file as if it were 'single' structure to ensure consistent prefixing
            root_vars = merge_env_vars_by_priority(all_env_vars, config.ENVIRONMENT, ".env")
            root_env_path = os.path.join(config.GIT_SUBDIR, ".env")
            if root_vars:
                # For root mega-file, we also try to use the ENV template
                base_template = os.environ.get("ENV") or ""
                root_content = merge_raw_env(base_template, root_vars)
                print(f"📝 Creating combined root {root_env_path}")
                create_env_file(conn, root_env_path, root_content)

        print("✅ Environment files generated successfully")

    except Exception as e:
        print(f"⚠\ufe0f  Error processing environment logic: {e}")
        import traceback

        traceback.print_exc()
        print("   Continuing deployment without environment files...")
