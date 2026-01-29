import base64
import os
import tempfile

from src import config


def setup_ssh_key():
    """Setup SSH key file from environment variable (supports raw or base64 encoded)"""
    if config.SSH_KEY:
        try:
            decoded_key = base64.b64decode(config.SSH_KEY).decode("utf-8")
            if "BEGIN" in decoded_key and "PRIVATE KEY" in decoded_key:
                key_content = decoded_key
            else:
                key_content = config.SSH_KEY
        except Exception:
            key_content = config.SSH_KEY

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".pem") as f:
            f.write(key_content)
            config.SSH_KEY_PATH = f.name
        os.chmod(config.SSH_KEY_PATH, 0o600)


def run_command(conn, command: str, force_sudo: bool = False, use_shell_profile: bool = True):
    """Run a command on the remote host with environment setup and sudo support"""
    use_sudo_for_this = config.USE_SUDO or force_sudo

    if not use_sudo_for_this and not use_shell_profile:
        return conn.run(command, warn=False)

    if not use_shell_profile:
        # Just sudo without the expensive profile loading
        # Wrap in bash -c to ensure sudo applies to the entire pipeline/batch
        escaped_command = command.replace("'", "'\"'\"'")
        return conn.run(f"sudo bash -c '{escaped_command}'", warn=False)

    if config.REMOTE_USER == "root":
        home_dir = "/root"
    else:
        home_dir = f"/home/{config.REMOTE_USER}"

    escaped_command = command.replace("'", "'\"'\"'")

    # Wrap command in bash that sources the profile to make functions available
    wrapped_command = (
        f"bash -l -c '"
        f'export PS1="$ "; '
        f"set +e; "
        f"if [ -f {home_dir}/.bashrc ]; then "
        f"  source {home_dir}/.bashrc 2>/dev/null; "
        f"fi; "
        f"if [ -f {home_dir}/.bash_profile ]; then "
        f"  source {home_dir}/.bash_profile 2>/dev/null; "
        f"fi; "
        f"if [ -f {home_dir}/.profile ]; then "
        f"  source {home_dir}/.profile 2>/dev/null; "
        f"fi; "
        f"set -e; "
        f"{escaped_command}"
        f"'"
    )

    if config.REMOTE_PASSWORD:
        escaped_pwd = config.REMOTE_PASSWORD.replace("'", "'\"'\"'")
        full_command = f"printf '%s\\n' '{escaped_pwd}' | sudo -S {wrapped_command}"
        return conn.run(full_command, pty=False, warn=False)
    else:
        return conn.run(f"sudo {wrapped_command}", warn=False)


def install_dependencies(conn):
    """Install required system dependencies"""
    deps = [
        "git",
        "python3-pip",
        "python3-dev",
        "build-essential",
        "libssl-dev",
        "libffi-dev",
    ]
    missing = []
    for dep in deps:
        result = conn.run(f"which {dep}", warn=True, hide=True)
        if not result.stdout.strip():
            missing.append(dep)

    if missing:
        print(f"======= Installing dependencies: {', '.join(missing)} =======")
        run_command(conn, "apt-get update", force_sudo=True)
        run_command(conn, f"apt-get install -y {' '.join(missing)}", force_sudo=True)
        print("======= Dependencies installed =======")
    else:
        print("======= All dependencies already installed =======")


def copy_artifacts(conn):
    """
    Copy build artifacts from local to remote using compression.
    Format: local_path:remote_path
    """
    if not config.COPY_ARTIFACTS:
        return

    print(f"======= Copying {len(config.COPY_ARTIFACTS)} artifacts =======")
    import tarfile

    for local_path, remote_path in config.COPY_ARTIFACTS:
        # Resolve remote path
        if not remote_path.startswith("/"):
            remote_path = os.path.join(config.GIT_DIR, remote_path)

        # Check if local path exists
        if not os.path.exists(local_path):
            print(f"⚠️ Warning: Local artifact '{local_path}' not found, skipping.")
            continue

        print(f"📦 Processing: {local_path} -> {remote_path}")

        # Create a temporary tarball
        with tempfile.NamedTemporaryFile(suffix=".tar.gz", delete=False) as tmp_tar:
            tmp_tar_path = tmp_tar.name

        try:
            # Compress
            with tarfile.open(tmp_tar_path, "w:gz") as tar:
                arcname = os.path.basename(remote_path)
                tar.add(local_path, arcname=arcname)

            # Upload
            remote_tmp = f"/tmp/{os.path.basename(tmp_tar_path)}"
            conn.put(tmp_tar_path, remote_tmp)

            # Ensure parent of destination exists
            remote_parent = os.path.dirname(remote_path)
            # Create parent if needed
            run_command(conn, f"mkdir -p {remote_parent}")

            # Remove existing target to be safe (overwrite)
            run_command(conn, f"rm -rf {remote_path}")

            run_command(conn, f"tar -xzf {remote_tmp} -C {remote_parent}")

            # Cleanup remote tmp
            run_command(conn, f"rm {remote_tmp}")

        finally:
            # Cleanup local tmp
            if os.path.exists(tmp_tar_path):
                os.unlink(tmp_tar_path)

    print("======= Artifacts copied =======")
