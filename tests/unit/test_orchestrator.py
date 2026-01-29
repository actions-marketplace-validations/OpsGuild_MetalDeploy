from unittest.mock import Mock, patch

import pytest
from fabric import Connection

from src import orchestrator
from src.config import config


@pytest.fixture
def mock_conn_class():
    with patch("src.orchestrator.Connection") as mock:
        yield mock


@pytest.fixture
def mock_conn():
    conn = Mock(spec=Connection)
    conn.run.return_value = Mock(stdout="test-host", ok=True)
    conn.cd.return_value.__enter__ = Mock(return_value=None)
    conn.cd.return_value.__exit__ = Mock(return_value=None)
    return conn


def test_handle_connection_flow(mock_conn_class, mock_conn, monkeypatch, tmp_path):
    # Setup
    monkeypatch.setattr(config, "REMOTE_HOST", "1.2.3.4")
    monkeypatch.setattr(config, "ENV_FILES_GENERATE", True)
    monkeypatch.setattr(config, "DEPLOYMENT_TYPE", "baremetal")

    github_output = tmp_path / "output"
    monkeypatch.setenv("GITHUB_OUTPUT", str(github_output))

    mock_conn_class.return_value = mock_conn

    # Mocking all dependencies
    with (
        patch("src.orchestrator.setup_ssh_key"),
        patch("src.orchestrator.setup_git_auth"),
        patch("src.orchestrator.install_dependencies"),
        patch("src.orchestrator.clone_repo"),
        patch("src.orchestrator.generate_env_files"),
        patch("src.orchestrator.deploy"),
    ):
        orchestrator.handle_connection()

    # Verify outputs
    content = github_output.read_text()
    assert "remote_hostname=test-host" in content
    assert "deployment_status=success" in content


def test_deploy_routing(monkeypatch, mock_conn):
    # 1. Test custom deploy command
    monkeypatch.setattr(config, "DEPLOY_COMMAND", "echo hello")
    with patch("src.orchestrator.run_command") as mock_run:
        orchestrator.deploy(mock_conn)
        assert "echo hello" in mock_run.call_args[0][1]

    # 2. Test barefoot routing
    monkeypatch.setattr(config, "DEPLOY_COMMAND", None)
    monkeypatch.setattr(config, "DEPLOYMENT_TYPE", "baremetal")
    with patch("src.orchestrator.deploy_baremetal") as mock_bm:
        orchestrator.deploy(mock_conn)
        mock_bm.assert_called_once()

    # 3. Test docker routing
    monkeypatch.setattr(config, "DEPLOYMENT_TYPE", "docker")
    with patch("src.orchestrator.deploy_docker") as mock_dk:
        orchestrator.deploy(mock_conn)
        mock_dk.assert_called_once()

    # 4. Test k8s routing
    monkeypatch.setattr(config, "DEPLOYMENT_TYPE", "k8s")
    with patch("src.orchestrator.deploy_k8s") as mock_k8s:
        orchestrator.deploy(mock_conn)
        mock_k8s.assert_called_once()
