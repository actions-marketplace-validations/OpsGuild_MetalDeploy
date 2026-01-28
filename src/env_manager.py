import json
import os
import re
from typing import Dict, List
import yaml
from fabric import Connection
from src import config

def parse_all_in_one_secret(secret_content: str, format_hint: str = "auto") -> Dict[str, str]:
    """Parse all-in-one secret with multiple format support"""
    if format_hint == "auto":
        content = secret_content.strip()
        if content.startswith("{") and content.endswith("}"):
            format_hint = "json"
        elif (content.startswith(("key:", "value:", "-", " {")) or ":" in content) and "\n" in content:
            format_hint = "yaml"
        elif "=" in content and "\n" in content:
            format_hint = "env"

    try:
        if format_hint == "json":
            parsed = json.loads(secret_content)
            return {str(k): str(v) for k, v in parsed.items()}
        elif format_hint == "yaml":
            parsed = yaml.safe_load(secret_content) or {}
            return {str(k): str(v) for k, v in parsed.items()}
        elif format_hint == "env":
            env_vars = {}
            for line in secret_content.strip().split("\n"):
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    env_vars[key.strip()] = value.strip()
            return env_vars
    except Exception:
        env_vars = {}
        for line in secret_content.strip().split("\n"):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                env_vars[key.strip()] = value.strip()
        return env_vars
    return {}

def detect_file_patterns(all_env_vars: Dict[str, str], structure: str) -> List[str]:
    """Auto-detect file patterns from variable names"""
    if structure == "single":
        return [".env"]

    patterns = set()
    for var_name in all_env_vars.keys():
        match = re.match(r"^ENV_[A-Z0-9_]*_([A-Z]+)_", var_name)
        if match:
            filename = match.group(1).lower()
            patterns.add(f".env.{filename}")
            continue
        match = re.match(r"^ENV_([A-Z]+)_", var_name)
        if match:
            filename = match.group(1).lower()
            patterns.add(f".env.{filename}")

    return sorted(list(patterns)) or [".env.app"]

def determine_file_structure(structure: str, patterns: List[str], environment: str, base_path: str) -> Dict[str, str]:
    """Determine file paths based on structure preference"""
    file_paths = {}
    if structure == "auto":
        structure = "flat" if len(patterns) == 1 else "nested"

    custom_base = base_path
    if config.ENV_FILES_PATH and structure in ["auto", "nested"]:
        custom_base = config.ENV_FILES_PATH

    if structure == "single":
        file_paths[".env"] = os.path.join(custom_base, ".env")
    elif structure == "flat":
        for pattern in patterns:
            file_paths[pattern] = os.path.join(custom_base, pattern)
    elif structure == "nested":
        env_dir = os.path.join(custom_base, environment) if config.ENV_FILES_PATH else os.path.join(custom_base, ".envs", environment)
        for pattern in patterns:
            file_paths[pattern] = os.path.join(env_dir, pattern)
    elif structure == "custom":
        custom_path = config.ENV_FILES_PATH or base_path
        for pattern in patterns:
            file_paths[pattern] = os.path.join(custom_path, pattern)

    return file_paths

def merge_env_vars_by_priority(all_env_vars: Dict[str, str], environment: str, pattern: str) -> Dict[str, str]:
    """Merge environment variables with proper priority"""
    merged = {}
    file_pattern = pattern.replace(".env.", "").upper()
    for var_name, value in all_env_vars.items():
        if var_name.startswith(f"ENV_{file_pattern}_"):
            key = var_name.split("_", 2)[-1]
            merged[key] = value
    env_prefix = f"ENV_{environment.upper()}_{file_pattern}_"
    for var_name, value in all_env_vars.items():
        if var_name.startswith(env_prefix):
            key = var_name.split("_", 3)[-1]
            merged[key] = value
    all_in_one_key = f"ENV_{environment.upper()}_{file_pattern}"
    if all_in_one_key in all_env_vars:
        parsed = parse_all_in_one_secret(all_env_vars[all_in_one_key], config.ENV_FILES_FORMAT)
        merged.update(parsed)
    base_all_in_one_key = f"ENV_{file_pattern}"
    if base_all_in_one_key in all_env_vars:
        parsed = parse_all_in_one_secret(all_env_vars[base_all_in_one_key], config.ENV_FILES_FORMAT)
        for key, value in parsed.items():
            if key not in merged:
                merged[key] = value
    return merged

def detect_environment_secrets() -> Dict[str, Dict[str, str]]:
    """Auto-detect and parse environment-specific secrets with priority system"""
    all_env_vars = {k: v for k, v in os.environ.items() if k.startswith("ENV_")}
    if not all_env_vars:
        return {}
    patterns = detect_file_patterns(all_env_vars, config.ENV_FILES_STRUCTURE)
    if config.ENV_FILES_PATTERNS and config.ENV_FILES_STRUCTURE != "auto":
        patterns = [p.strip() for p in config.ENV_FILES_PATTERNS if p.strip()]
    result = {}
    for pattern in patterns:
        merged_vars = merge_env_vars_by_priority(all_env_vars, config.ENVIRONMENT, pattern)
        if merged_vars:
            result[pattern] = merged_vars
    return result

def create_env_file(conn, file_path: str, env_vars: Dict[str, str]) -> None:
    """Create .env file with secure permissions (0o600)"""
    if not env_vars:
        return
    dir_path = os.path.dirname(file_path)
    if dir_path and dir_path != file_path:
        conn.run(f"mkdir -p {dir_path}")
    env_content = "\n".join([f"{k}={v}" for k, v in env_vars.items()])
    conn.run(f"cat > \"{file_path}\" << 'EOF'\n{env_content}\nEOF")
    conn.run(f'chmod 600 "{file_path}"')

def generate_env_files(conn) -> None:
    """Main function to generate environment files from secrets"""
    if not config.ENV_FILES_GENERATE:
        return
    print("🔧 Generating environment files from secrets...")
    env_file_data = detect_environment_secrets()
    if not env_file_data:
        print("ℹ\ufe0f  No environment variables found to generate files")
        return
    all_merged_vars = {}
    for pattern, env_vars in env_file_data.items():
        file_paths = determine_file_structure(config.ENV_FILES_STRUCTURE, [pattern], config.ENVIRONMENT, config.GIT_SUBDIR)
        file_path = file_paths.get(pattern)
        if file_path:
            print(f"📝 Creating {file_path} with {len(env_vars)} variables")
            create_env_file(conn, file_path, env_vars)
            if config.ENV_FILES_CREATE_ROOT:
                 all_merged_vars.update(env_vars)
    if config.ENV_FILES_CREATE_ROOT and all_merged_vars:
        root_env_path = os.path.join(config.GIT_SUBDIR, ".env")
        print(f"📝 Creating combined root {root_env_path} with {len(all_merged_vars)} variables")
        create_env_file(conn, root_env_path, all_merged_vars)
    print("✅ Environment files generated successfully")
