import concurrent.futures
import multiprocessing
import os

from fabric import Connection

from src import config
from src.connection import copy_artifacts, install_dependencies, run_command, setup_ssh_key
from src.env_manager import generate_env_files
from src.git_ops import clone_repo, setup_git_auth
from src.providers.baremetal import deploy_baremetal
from src.providers.docker import deploy_docker, install_docker
from src.providers.k8s import deploy_k8s, install_helm, install_k3s, install_kubectl
from src.providers.utils import fix_database_permissions


def deploy(conn):
    """Main deploy function that routes to the appropriate deployment method"""
    fix_database_permissions(conn)
    if config.DEPLOY_COMMAND:
        with conn.cd(config.GIT_SUBDIR):
            print(f"======= Running deploy command: {config.DEPLOY_COMMAND} =======")
            result = run_command(
                conn,
                f"{config.DEPLOY_COMMAND}; EXIT_CODE=$?; if [ $EXIT_CODE -ne 0 ]; then echo 'Command failed with exit code:' $EXIT_CODE; exit $EXIT_CODE; fi",
            )
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


def deploy_single_host():
    """Logic for deploying to a single host (run inside worker or directly)"""
    setup_ssh_key()
    setup_git_auth()
    conn_kwargs = {"host": config.REMOTE_HOST, "user": config.REMOTE_USER}
    if config.REMOTE_PASSWORD:
        conn_kwargs["connect_kwargs"] = {
            "password": config.REMOTE_PASSWORD,
            "look_for_keys": False,
            "allow_agent": False,
        }
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

    copy_artifacts(conn)

    deploy(conn)

    if os.getenv("GITHUB_OUTPUT"):
        with open(os.getenv("GITHUB_OUTPUT"), "a") as f:
            f.write("deployment_status=success\n")

    # Cleanup
    for path in [config.SSH_KEY_PATH, config.GIT_SSH_KEY_PATH]:
        if path and os.path.exists(path):
            try:
                os.unlink(path)
            except OSError:
                pass


def deploy_worker(overrides):
    """Worker entry point for multiprocessing"""
    try:
        # Reload config with this worker's specific overrides
        config.load(overrides)
        deploy_single_host()
    except Exception as e:
        # Ensure the exception is pickleable by stripping complex objects
        # Fabric/Invoke exceptions might contain locks or sockets
        raise RuntimeError(f"Worker failed: {str(e)}") from None


def handle_connection():
    """Handle the SSH connection and orchestrate the deployment (supports multi-host)"""
    hosts = [h.strip() for h in config.REMOTE_HOST.split(",") if h.strip()]

    if len(hosts) <= 1:
        return deploy_single_host()

    print(f"🚀 Detected {len(hosts)} target hosts: {hosts}")

    def parse_list(val):
        return [v.strip() for v in (val or "").split(",") if v.strip()]

    users = parse_list(config.REMOTE_USER)
    passwords = parse_list(config.REMOTE_PASSWORD)
    keys = parse_list(config.SSH_KEY)

    # Prepare configuration overrides for each host
    deployment_configs = []

    def get_val(lst, index, default=None):
        if not lst:
            return default
        if index < len(lst):
            return lst[index]
        return lst[-1]  # Reuse last value if list is shorter than hosts

    for i, host in enumerate(hosts):
        overrides = {
            "REMOTE_HOST": host,
            "REMOTE_USER": get_val(users, i, config.REMOTE_USER),
            "REMOTE_PASSWORD": get_val(passwords, i, config.REMOTE_PASSWORD),
            "SSH_KEY": get_val(keys, i, config.SSH_KEY),
        }
        overrides = {k: v for k, v in overrides.items() if v is not None}
        deployment_configs.append(overrides)

    # Run in parallel
    ctx = multiprocessing.get_context("spawn")

    with concurrent.futures.ProcessPoolExecutor(mp_context=ctx) as executor:
        futures = {
            executor.submit(deploy_worker, cfg): cfg["REMOTE_HOST"] for cfg in deployment_configs
        }

        for future in concurrent.futures.as_completed(futures):
            host = futures[future]
            try:
                future.result()
                print(f"✅ Deployment to {host} succeeded")
            except Exception as e:
                print(f"❌ Deployment to {host} failed: {e}")
                raise e
