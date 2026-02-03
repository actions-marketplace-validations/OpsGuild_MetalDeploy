import os

from src import config
from src.connection import run_command


def docker_login(conn, registry_type=None):
    """Login to Docker registry"""
    if not registry_type:
        print("No registry type provided, skipping Docker login.")
        return
    registry_type = registry_type.lower()
    if registry_type == "ghcr":
        username, password = config.GIT_USER, config.GIT_TOKEN
        if not username or not password:
            raise ValueError("GIT_USER and GIT_TOKEN must be set for GHCR")
        print("Logging in to GHCR...")
        conn.run(f"echo '{password}' | docker login ghcr.io -u {username} --password-stdin")
    elif registry_type == "dockerhub":
        username, password = os.getenv("REGISTRY_USERNAME"), os.getenv("REGISTRY_PASSWORD")
        if not username or not password:
            raise ValueError("REGISTRY_USERNAME and REGISTRY_PASSWORD must be set")
        print("Logging in to Docker Hub...")
        conn.run(f"echo '{password}' | docker login -u {username} --password-stdin")
    elif registry_type == "ecr":
        aws_region, aws_account_id = os.getenv("AWS_REGION"), os.getenv("AWS_ACCOUNT_ID")
        if not aws_region or not aws_account_id:
            raise ValueError("AWS_REGION and AWS_ACCOUNT_ID must be set for ECR login.")
        print("Logging in to AWS ECR...")
        cmd = f"aws ecr get-login-password --region {aws_region} | docker login --username AWS --password-stdin {aws_account_id}.dkr.ecr.{aws_region}.amazonaws.com"
        conn.run(cmd)
    else:
        raise ValueError(f"Unsupported registry_type: {registry_type}")


def install_docker(conn):
    """Install Docker and Docker Compose if not already installed"""
    result = conn.run("which docker", warn=True, hide=True)
    if result.stdout.strip():
        print("======= Docker already installed =======")
        return
    run_command(conn, "apt-get update", force_sudo=True)
    run_command(
        conn,
        "apt-get install -y apt-transport-https ca-certificates curl software-properties-common",
        force_sudo=True,
    )
    run_command(
        conn,
        "bash -c 'curl -fsSL https://download.docker.com/linux/ubuntu/gpg | apt-key add -'",
        force_sudo=True,
    )
    run_command(
        conn,
        'add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable"',
        force_sudo=True,
    )
    run_command(conn, "apt-get update", force_sudo=True)
    run_command(conn, "apt-get install -y docker-ce", force_sudo=True)
    run_command(
        conn,
        'curl -L "https://github.com/docker/compose/releases/download/1.29.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose',
        force_sudo=True,
    )
    run_command(conn, "chmod +x /usr/local/bin/docker-compose", force_sudo=True)
    run_command(conn, "usermod -aG docker ${USER}", force_sudo=True)
    run_command(conn, "systemctl enable docker", force_sudo=True)
    run_command(conn, "systemctl start docker", force_sudo=True)
    print("======= Docker installed =======")


def deploy_docker(conn):
    """Deploy using Docker Compose"""
    with conn.cd(config.GIT_SUBDIR):
        docker_login(conn, registry_type=config.REGISTRY_TYPE)
        if config.PROFILE:
            print(f"======= Deploying with Docker Compose profile: {config.PROFILE} =======")
            run_command(conn, f"docker compose --profile {config.PROFILE} up --build -d")
        else:
            print("======= Deploying with Docker Compose =======")
            run_command(conn, "docker compose up --build -d")
    print("======= Docker deployment completed =======")
