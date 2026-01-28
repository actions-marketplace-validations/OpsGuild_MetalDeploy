import os
from fabric import Connection
from src import config
from src.connection import setup_ssh_key, run_command, install_dependencies
from src.git_ops import setup_git_auth, clone_repo
from src.env_manager import generate_env_files
from src.providers.utils import fix_database_permissions
from src.providers.baremetal import deploy_baremetal
from src.providers.docker import deploy_docker, install_docker
from src.providers.k8s import deploy_k8s, install_kubectl, install_helm, install_k3s

def deploy(conn):
    """Main deploy function that routes to the appropriate deployment method"""
    fix_database_permissions(conn)
    if config.DEPLOY_COMMAND:
        with conn.cd(config.GIT_SUBDIR):
            print(f"======= Running deploy command: {config.DEPLOY_COMMAND} =======")
            result = run_command(conn, f"{config.DEPLOY_COMMAND}; EXIT_CODE=$?; if [ $EXIT_CODE -ne 0 ]; then echo 'Command failed with exit code:' $EXIT_CODE; exit $EXIT_CODE; fi")
            if "Command failed with exit code:" in result.stdout:
                for line in result.stdout.split("\n"):
                    if "Command failed with exit code:" in line:
                        exit_code = line.split("exit code:")[-1].strip()
                        raise ValueError(f"Deploy command failed with exit code: {exit_code}")
        print("======= Deploy command completed =======")
        return

    if config.DEPLOYMENT_TYPE == "baremetal":
        deploy_baremetal(conn)
    elif config.DEPLOYMENT_TYPE == "docker":
        deploy_docker(conn)
    elif config.DEPLOYMENT_TYPE == "k8s":
        deploy_k8s(conn)
    else:
        raise ValueError(f"Invalid deployment_type: {config.DEPLOYMENT_TYPE}")

def handle_connection():
    """Handle the SSH connection and orchestrate the deployment"""
    setup_ssh_key()
    setup_git_auth()
    conn_kwargs = {"host": config.REMOTE_HOST, "user": config.REMOTE_USER}
    if config.REMOTE_PASSWORD:
        conn_kwargs["connect_kwargs"] = {"password": config.REMOTE_PASSWORD, "look_for_keys": False, "allow_agent": False}
    elif config.SSH_KEY_PATH:
        conn_kwargs["connect_kwargs"] = {"key_filename": config.SSH_KEY_PATH}
    
    conn = Connection(**conn_kwargs)
    result = conn.run("hostname", hide=True)
    hostname = result.stdout.strip()
    print(f"======= Connected to {config.REMOTE_HOST}, hostname: {hostname} =======")

    if os.getenv("GITHUB_OUTPUT"):
        with open(os.getenv("GITHUB_OUTPUT"), "a") as f:
            f.write(f"remote_hostname={hostname}\n")

    install_dependencies(conn)
    if config.DEPLOYMENT_TYPE in ["docker", "k8s"]:
        install_docker(conn)
    if config.DEPLOYMENT_TYPE == "k8s":
        install_kubectl(conn)
        install_helm(conn)
        install_k3s(conn)

    clone_repo(conn)
    if config.ENV_FILES_GENERATE:
        generate_env_files(conn)

    deploy(conn)

    if os.getenv("GITHUB_OUTPUT"):
        with open(os.getenv("GITHUB_OUTPUT"), "a") as f:
            f.write("deployment_status=success\n")

    # Cleanup
    for path in [config.SSH_KEY_PATH, config.GIT_SSH_KEY_PATH]:
        if path and os.path.exists(path):
            try: os.unlink(path)
            except OSError: pass
