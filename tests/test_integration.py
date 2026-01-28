from unittest.mock import MagicMock, Mock, patch

import pytest
from fabric import Connection

from src import orchestrator
from src.config import config


@pytest.fixture
def mock_conn():
    conn = MagicMock(spec=Connection)
    conn.run.return_value = Mock(stdout="test-node", ok=True)
    conn.cd.return_value.__enter__ = Mock(return_value=None)
    conn.cd.return_value.__exit__ = Mock(return_value=None)
    return conn


def test_full_baremetal_flow(mock_conn, monkeypatch, tmp_path):
    # Integration-like test for the whole orchestrator
    github_output = tmp_path / "github_output"
    monkeypatch.setenv("GITHUB_OUTPUT", str(github_output))

    monkeypatch.setattr(config, "DEPLOYMENT_TYPE", "baremetal")
    monkeypatch.setattr(config, "REMOTE_HOST", "my-server")
    monkeypatch.setattr(config, "GIT_URL", "https://github.com/org/repo")

    with patch("src.orchestrator.Connection", return_value=mock_conn), patch(
        "src.orchestrator.setup_ssh_key"
    ), patch("src.orchestrator.setup_git_auth"), patch(
        "src.orchestrator.install_dependencies"
    ), patch(
        "src.orchestrator.clone_repo"
    ), patch(
        "src.orchestrator.deploy"
    ) as mock_deploy:
        orchestrator.handle_connection()

        assert mock_deploy.called
        output = github_output.read_text()
        assert "deployment_status=success" in output
        assert "remote_hostname=test-node" in output


def test_config_reload_behavior(monkeypatch):
    # Test that config.load() correctly updates the config instance
    monkeypatch.setenv("ENV_FILES_STRUCTURE", "flat")
    config.load()
    assert config.ENV_FILES_STRUCTURE == "flat"

    monkeypatch.setenv("ENV_FILES_STRUCTURE", "nested")
    config.load()
    assert config.ENV_FILES_STRUCTURE == "nested"
