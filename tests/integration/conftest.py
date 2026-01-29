import os
import subprocess
import time

import pytest
from fabric import Connection


@pytest.fixture(scope="session")
def ssh_container():
    """Spin up the Docker container with SSH server."""
    import socket

    docker_compose_file = os.path.join(os.path.dirname(__file__), "docker-compose.yml")
    tests_dir = os.path.dirname(__file__)

    # Start container with output capture
    print("🐳 Starting SSH container...")
    result = subprocess.run(
        ["docker", "compose", "-f", docker_compose_file, "up", "-d"],
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
        cwd=tests_dir,
    )

    if result.returncode != 0:
        print(f"❌ Docker compose failed: {result.stderr}")
        pytest.fail(f"Failed to start Docker container: {result.stderr}")

    # Give container time to fully start sshd
    time.sleep(5)

    # Connection parameters
    host = "127.0.0.1"
    port = 2222
    user = "root"
    password = "root"

    # Wait for SSH to be ready with socket check first
    retries = 30
    ready = False

    for i in range(retries):
        try:
            # Check if port is listening
            with socket.create_connection((host, port), timeout=2):
                pass

            # Verify SSH actually works
            conn = Connection(
                host=host,
                port=port,
                user=user,
                connect_kwargs={
                    "password": password,
                    "look_for_keys": False,
                    "allow_agent": False,
                },
            )
            conn.run("echo 'SSH Ready'", hide=True)
            conn.close()
            ready = True
            print("✅ SSH Container Ready")
            break
        except Exception as e:
            if i < retries - 1:
                time.sleep(1)
            else:
                print(f"Final connection attempt failed: {e}")

    if not ready:
        # Capture logs before failing
        logs = subprocess.run(
            ["docker", "logs", "tests-ssh-server-1"],
            capture_output=True,
            text=True,
            stdin=subprocess.DEVNULL,
        )
        print(f"Container logs:\n{logs.stdout}")
        subprocess.run(
            ["docker", "compose", "-f", docker_compose_file, "down"],
            check=False,
            stdin=subprocess.DEVNULL,
            cwd=tests_dir,
        )
        pytest.fail("Could not connect to SSH container after 30 retries")

    yield {"host": host, "port": port, "user": user, "password": password}

    # Teardown
    print("🛑 Stopping SSH container...")
    subprocess.run(
        ["docker", "compose", "-f", docker_compose_file, "down"],
        check=False,
        stdin=subprocess.DEVNULL,
        cwd=tests_dir,
    )


@pytest.fixture
def integration_conn(ssh_container):
    """Provide a fabric connection to the container."""
    return Connection(
        host=ssh_container["host"],
        port=ssh_container["port"],
        user=ssh_container["user"],
        connect_kwargs={
            "password": ssh_container["password"],
            "look_for_keys": False,
            "allow_agent": False,
        },
    )
