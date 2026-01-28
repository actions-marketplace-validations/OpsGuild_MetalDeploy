from src import config
from src.connection import run_command

def detect_database_type(conn):
    """Detect which database is being used in the deployment"""
    databases = []
    with conn.cd(config.GIT_SUBDIR):
        db_patterns = {
            "postgres": ["postgres", "postgresql", "postgres:"],
            "mariadb": ["mariadb", "mariadb:"],
            "mysql": ["mysql", "mysql:"],
            "mongodb": ["mongo", "mongodb", "mongo:"],
            "redis": ["redis", "redis:"],
        }
        compose_files = ["docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml"]
        for compose_file in compose_files:
            check = conn.run(f"test -f {compose_file} && echo 'exists' || echo 'not exists'", hide=True, warn=True)
            if "exists" in check.stdout:
                for db_type, patterns in db_patterns.items():
                    if db_type in databases: continue
                    for pattern in patterns:
                        result = conn.run(f"grep -i '{pattern}' {compose_file} 2>/dev/null | head -1 || true", hide=True, warn=True)
                        if result.stdout.strip():
                            databases.append(db_type)
                            break
        if config.DEPLOYMENT_TYPE == "k8s":
            manifest_paths = ["k8s", "manifests", "kubernetes"]
            for path in manifest_paths:
                check = conn.run(f"test -d {path} && echo 'exists' || echo 'not exists'", hide=True, warn=True)
                if "exists" in check.stdout:
                    for db_type, patterns in db_patterns.items():
                        if db_type in databases: continue
                        for pattern in patterns:
                            result = conn.run(f"grep -ri '{pattern}' {path}/ 2>/dev/null | head -1 || true", hide=True, warn=True)
                            if result.stdout.strip():
                                databases.append(db_type)
                                break
    return databases

def get_database_volume_paths(conn, db_type):
    """Extract actual volume paths from docker-compose files"""
    paths = []
    with conn.cd(config.GIT_SUBDIR):
        compose_files = ["docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml"]
        for compose_file in compose_files:
            check = conn.run(f"test -f {compose_file} && echo 'exists' || echo 'not exists'", hide=True, warn=True)
            if "exists" not in check.stdout: continue
            volume_result = conn.run(f"grep -iE '\\s+-\\s+.*{db_type}.*:/' {compose_file} 2>/dev/null || true", hide=True, warn=True)
            for line in volume_result.stdout.strip().split("\n"):
                line = line.strip()
                if ":/" in line:
                    parts = line.split(":/")
                    if len(parts) > 0:
                        local_path = parts[0].strip().lstrip("-").strip()
                        if local_path and (local_path.startswith("./") or local_path.startswith("/")):
                            if local_path not in paths: paths.append(local_path)
    return paths

def fix_database_permissions(conn):
    """Fix database data directory permissions dynamically"""
    databases = detect_database_type(conn)
    if not databases: return
    db_configs = {
        "postgres": ("postgres", "999", "999", "700"),
        "mariadb": ("mariadb", "999", "999", "750"),
        "mysql": ("mysql", "999", "999", "750"),
        "mongodb": ("mongodb", "999", "999", "755"),
        "redis": ("redis", "999", "999", "755"),
    }
    with conn.cd(config.GIT_SUBDIR):
        for db_type in databases:
            if db_type not in db_configs: continue
            dir_name, user_id, group_id, perms = db_configs[db_type]
            volume_paths = get_database_volume_paths(conn, db_type)
            existing_dirs = conn.run(f"find . -type d -name '*{dir_name}*' -path '*/data/*' -o -type d -name '*{dir_name}*' -path '*/volumes/*' 2>/dev/null | head -10 || true", hide=True, warn=True)
            for existing_dir in existing_dirs.stdout.strip().split("\n"):
                if existing_dir.strip() and existing_dir.strip() not in volume_paths:
                    volume_paths.append(existing_dir.strip())
            if not volume_paths: continue
            print(f"======= Fixing {db_type.upper()} data directory permissions =======")
            for path in volume_paths:
                if not path.strip(): continue
                normalized_path = path.lstrip("./")
                full_path = f"./{normalized_path}" if not normalized_path.startswith("/") else normalized_path
                run_command(conn, f"bash -c 'mkdir -p {full_path} || true && chown -R {user_id}:{group_id} {full_path} || true && chmod -R {perms} {full_path} || true'")
