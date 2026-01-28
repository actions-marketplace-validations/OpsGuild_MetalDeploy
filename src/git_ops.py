import base64
import os
import tempfile
from invoke import Responder
from src import config
from src.connection import run_command

def setup_git_auth():
    """Setup Git authentication based on GIT_AUTH_METHOD"""
    if config.GIT_AUTH_METHOD == "token":
        if not config.GIT_TOKEN or not config.GIT_USER:
            raise ValueError("GIT_TOKEN and GIT_USER are required when git_auth_method is 'token'")
        prefix = f"https://{config.GIT_USER}:{config.GIT_TOKEN}@"
        suffix = config.GIT_URL.split("https://")[-1] if "https://" in config.GIT_URL else config.GIT_URL
        config.AUTH_GIT_URL = prefix + suffix
    elif config.GIT_AUTH_METHOD == "ssh":
        if not config.GIT_SSH_KEY:
            if config.SSH_KEY:
                git_ssh_key = config.SSH_KEY
            else:
                raise ValueError("GIT_SSH_KEY or SSH_KEY is required when git_auth_method is 'ssh'")
        else:
            git_ssh_key = config.GIT_SSH_KEY

        try:
            decoded_key = base64.b64decode(git_ssh_key).decode("utf-8")
            if "BEGIN" in decoded_key and "PRIVATE KEY" in decoded_key:
                key_content = decoded_key
            else:
                key_content = git_ssh_key
        except Exception:
            key_content = git_ssh_key

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".pem") as f:
            f.write(key_content)
            config.GIT_SSH_KEY_PATH = f.name
        os.chmod(config.GIT_SSH_KEY_PATH, 0o600)

        if config.GIT_URL.startswith("https://"):
            url_parts = config.GIT_URL.replace("https://", "").replace("http://", "")
            if "/" in url_parts:
                domain, path = url_parts.split("/", 1)
                config.AUTH_GIT_URL = f"git@{domain}:{path}"
            else:
                config.AUTH_GIT_URL = config.GIT_URL
        else:
            config.AUTH_GIT_URL = config.GIT_URL
    elif config.GIT_AUTH_METHOD == "none":
        config.AUTH_GIT_URL = config.GIT_URL
    else:
        raise ValueError(
            f"Invalid git_auth_method: {config.GIT_AUTH_METHOD}. Must be 'token', 'ssh', or 'none'"
        )

def clone_repo(conn):
    """Clone the Git repository to the remote server"""
    promptpass = Responder(
        pattern=r"Are you sure you want to continue connecting " r"\(yes/no/\[fingerprint\]\)\?",
        response="yes\n",
    )

    conn.run(f"mkdir -p {config.REMOTE_DIR}", warn=True)

    if config.GIT_AUTH_METHOD == "ssh" and config.GIT_SSH_KEY_PATH:
        conn.put(config.GIT_SSH_KEY_PATH, "/tmp/git_deploy_key")
        conn.run("chmod 600 /tmp/git_deploy_key")

        ssh_config = """
Host github.com
    IdentityFile /tmp/git_deploy_key
    StrictHostKeyChecking no
    UserKnownHostsFile /dev/null
"""
        conn.run("mkdir -p ~/.ssh", warn=True)
        conn.run(f'echo "{ssh_config}" >> ~/.ssh/config')
        conn.run("chmod 600 ~/.ssh/config")

    result = conn.run(
        f'test -d {config.GIT_DIR} && echo "exists" || echo "not exists"',
        hide=True,
    )

    if "not exists" in result.stdout:
        print("======= Cloning the repository =======")
        with conn.cd(config.REMOTE_DIR):
            if config.GIT_AUTH_METHOD == "ssh":
                conn.run(
                    f"GIT_SSH_COMMAND='ssh -i /tmp/git_deploy_key -o StrictHostKeyChecking=no' git clone {config.AUTH_GIT_URL} {config.PROJECT_NAME}",
                    pty=True,
                    watchers=[promptpass],
                )
            else:
                conn.run(
                    f"git clone {config.AUTH_GIT_URL} {config.PROJECT_NAME}",
                    pty=True,
                    watchers=[promptpass],
                )
    else:
        git_check = conn.run(
            f'test -d {config.GIT_DIR}/.git && echo "git_repo" || echo "not_git_repo"',
            hide=True,
        )
        if "not_git_repo" in git_check.stdout:
            print(f"======= Directory {config.GIT_DIR} exists but is not a git repository =======")
            with conn.cd(config.GIT_DIR):
                conn.run("git init", warn=False)
                conn.run(f"git remote add origin {config.AUTH_GIT_URL}", warn=False)
                if config.GIT_AUTH_METHOD == "ssh":
                    conn.run(
                        "GIT_SSH_COMMAND='ssh -i /tmp/git_deploy_key -o StrictHostKeyChecking=no' git fetch origin",
                        pty=True,
                        watchers=[promptpass],
                    )
                else:
                    conn.run("git fetch origin", pty=True, watchers=[promptpass])
                conn.run(
                    "git branch -M main 2>/dev/null || git branch -M master 2>/dev/null || true",
                    warn=False,
                )
                conn.run(
                    "git checkout -b main origin/main 2>/dev/null || git checkout -b master origin/master 2>/dev/null || true",
                    warn=False,
                )
        else:
            print(f"======= Repository already exists at {config.GIT_DIR}, skipping clone =======")

    conn.run(f"git config --global --add safe.directory {config.GIT_DIR}")
    run_command(conn, f"chown -R $(whoami) {config.GIT_DIR}", force_sudo=True)

    with conn.cd(config.GIT_SUBDIR):
        if config.ENVIRONMENT in ["prod", "production"]:
            result = conn.run("git branch -r", hide=True)
            remote_branches = [line.strip() for line in result.stdout.strip().splitlines()]

            if "origin/main" in remote_branches:
                branch_name = "main"
            elif "origin/master" in remote_branches:
                branch_name = "master"
            else:
                raise Exception("Neither 'origin/main' nor 'origin/master' found in repo")
        else:
            branch_name = config.ENVIRONMENT

        current_branch = conn.run("git rev-parse --abbrev-ref HEAD", hide=True).stdout.strip()

        if current_branch != branch_name:
            conn.run("git stash", warn=True)
            conn.run(f"git checkout {branch_name}")

        if config.GIT_AUTH_METHOD == "ssh":
            conn.run(
                f"GIT_SSH_COMMAND='ssh -i /tmp/git_deploy_key -o StrictHostKeyChecking=no' git fetch origin && git reset --hard origin/{branch_name}"
            )
        else:
            conn.run(f"git fetch origin && git reset --hard origin/{branch_name}")

    print(f"=== Repository cloned & checked out to {branch_name} branch =======")
