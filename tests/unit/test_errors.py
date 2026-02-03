from unittest.mock import Mock, patch

import pytest
from fabric import Connection

from src import git_ops, orchestrator, providers
from src.config import config


@pytest.fixture
def mock_conn():
    conn = Mock(spec=Connection)
    conn.run.return_value = Mock(stdout="", ok=True)
    conn.cd.return_value.__enter__ = Mock(return_value=None)
    conn.cd.return_value.__exit__ = Mock(return_value=None)
    return conn


class TestErrorScenarios:
    def test_ssh_connection_failure(self, monkeypatch):
        monkeypatch.setattr(config, "REMOTE_HOST", "bad-host")
        # Set auth method to none to avoid early exit in setup_git_auth
        monkeypatch.setattr(config, "GIT_AUTH_METHOD", "none")
        with patch("src.orchestrator.Connection", side_effect=Exception("SSH Timeout")):
            with patch("src.orchestrator.setup_ssh_key"):
                # Use handle_connection to trigger the Connection call
                with pytest.raises(Exception, match="SSH Timeout"):
                    orchestrator.handle_connection()

    def test_git_clone_failure(self, mock_conn, monkeypatch):
        monkeypatch.setattr(config, "GIT_AUTH_METHOD", "none")
        monkeypatch.setattr(config, "REMOTE_DIR", "/app")
        # dir check -> not exists, then clone -> fails
        mock_conn.run.side_effect = [
            Mock(ok=True),  # mkdir
            Mock(stdout="not exists"),
            Exception("Git clone failed"),
        ]
        with pytest.raises(Exception, match="Git clone failed"):
            git_ops.clone_repo(mock_conn)

    def test_baremetal_deploy_script_fail(self, mock_conn, monkeypatch):
        monkeypatch.setattr(config, "GIT_SUBDIR", "/app")
        # deploy.sh exists, but run_command (which we'll mock) fails
        mock_conn.run.side_effect = [
            Mock(ok=True),  # test -f deploy.sh
            Mock(ok=True),  # chmod +x
        ]
        with patch("src.providers.baremetal.run_command") as mock_run:
            mock_run.return_value = Mock(stdout="Command failed with exit code: 1")
            with pytest.raises(ValueError, match="deploy.sh failed with exit code: 1"):
                providers.baremetal.deploy_baremetal(mock_conn)

    def test_docker_login_missing_creds(self, mock_conn, monkeypatch):
        monkeypatch.setattr(config, "GIT_USER", None)
        with pytest.raises(ValueError, match="GIT_USER and GIT_TOKEN must be set"):
            providers.docker.docker_login(mock_conn, registry_type="ghcr")

    def test_missing_k8s_manifests(self, mock_conn, monkeypatch):
        monkeypatch.setattr(config, "GIT_SUBDIR", "/app")
        monkeypatch.setattr(config, "K8S_MANIFEST_PATH", None)
        # All manifest directory/file checks return False
        mock_conn.run.return_value = Mock(ok=False)

        with patch("src.providers.k8s.docker_login"):
            with pytest.raises(ValueError, match="No k8s_manifest_path specified"):
                providers.k8s.deploy_k8s(mock_conn)

    def test_unsupported_registry(self, mock_conn):
        with pytest.raises(ValueError, match="Unsupported registry_type"):
            providers.docker.docker_login(mock_conn, registry_type="unknown")
