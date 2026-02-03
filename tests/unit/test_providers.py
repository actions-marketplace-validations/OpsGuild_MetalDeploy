from unittest.mock import Mock, patch

import pytest
from fabric import Connection

from src.config import config
from src.providers import baremetal, docker, k8s


@pytest.fixture
def mock_conn():
    conn = Mock(spec=Connection)
    conn.run.return_value = Mock(stdout="", ok=True)
    conn.cd.return_value.__enter__ = Mock(return_value=None)
    conn.cd.return_value.__exit__ = Mock(return_value=None)
    return conn


class TestBaremetal:
    def test_deploy_sh_flow(self, mock_conn):
        def mock_run(cmd, **kwargs):
            if "test -f deploy.sh" in cmd:
                return Mock(ok=True)
            return Mock(ok=False)

        mock_conn.run.side_effect = mock_run

        with patch("src.providers.baremetal.run_command") as mock_run_cmd:
            baremetal.deploy_baremetal(mock_conn)
            assert "./deploy.sh" in mock_run_cmd.call_args[0][1]

    def test_makefile_fallback(self, mock_conn, monkeypatch):
        monkeypatch.setattr(config, "ENVIRONMENT", "staging")

        # deploy.sh no, Makefile yes
        def mock_run(cmd, **kwargs):
            if "test -f deploy.sh" in cmd:
                return Mock(ok=False)
            if "test -f Makefile" in cmd:
                return Mock(ok=True)
            return Mock(ok=False)

        mock_conn.run.side_effect = mock_run

        with patch("src.providers.baremetal.run_command") as mock_run_cmd:
            baremetal.deploy_baremetal(mock_conn)
            assert "make staging" in mock_run_cmd.call_args[0][1]


class TestDocker:
    def test_docker_login_ghcr(self, mock_conn, monkeypatch):
        monkeypatch.setattr(config, "GIT_USER", "u")
        monkeypatch.setattr(config, "GIT_TOKEN", "t")
        docker.docker_login(mock_conn, registry_type="ghcr")
        assert "docker login ghcr.io" in mock_conn.run.call_args[0][0]

    def test_deploy_docker_with_profile(self, mock_conn, monkeypatch):
        monkeypatch.setattr(config, "PROFILE", "api")
        monkeypatch.setattr(config, "GIT_SUBDIR", "/app")
        with patch("src.providers.docker.docker_login"), patch(
            "src.providers.docker.run_command"
        ) as mock_run:
            docker.deploy_docker(mock_conn)
            assert "--profile api" in mock_run.call_args[0][1]


class TestK8s:
    def test_k3s_installation(self, mock_conn):
        mock_conn.run.side_effect = [
            Mock(stdout=""),  # which k3s -> not found
            Mock(ok=True),  # curl k3s sh
            Mock(ok=True),  # systemctl enable
            Mock(ok=True),  # systemctl start
            Mock(ok=True),  # echo KUBECONFIG
        ]
        with patch("src.providers.k8s.run_command"):
            k8s.install_k3s(mock_conn)
        assert mock_conn.run.call_count >= 3

    def test_k8s_deploy_namespace_creation(self, mock_conn, monkeypatch):
        monkeypatch.setattr(config, "K8S_NAMESPACE", "custom-ns")
        monkeypatch.setattr(config, "K8S_MANIFEST_PATH", "k8s/")
        monkeypatch.setattr(config, "GIT_SUBDIR", "/app")

        mock_conn.run.side_effect = [
            Mock(ok=True),  # test -d k8s
            Mock(ok=True),  # create namespace
            Mock(ok=True),  # apply -f k8s/
        ]

        with patch("src.providers.k8s.docker_login"):
            k8s.deploy_k8s(mock_conn)

        calls = [str(call) for call in mock_conn.run.call_args_list]
        assert any("kubectl create namespace custom-ns" in c for c in calls)
        assert any("kubectl apply -f k8s/" in c for c in calls)
