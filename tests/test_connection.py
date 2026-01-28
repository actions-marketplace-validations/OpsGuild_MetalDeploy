import base64
import os
from unittest.mock import Mock

import pytest
from fabric import Connection

from src.config import config
from src.connection import install_dependencies, run_command, setup_ssh_key


@pytest.fixture
def mock_conn():
    conn = Mock(spec=Connection)
    conn.run.return_value = Mock(stdout="", ok=True)
    return conn


def test_setup_ssh_key_raw(monkeypatch):
    key = "raw-ssh-key-content"
    monkeypatch.setattr(config, "SSH_KEY", key)
    setup_ssh_key()
    assert config.SSH_KEY_PATH is not None
    with open(config.SSH_KEY_PATH, "r") as f:
        assert f.read() == key
    os.unlink(config.SSH_KEY_PATH)


def test_setup_ssh_key_base64(monkeypatch):
    key = "-----BEGIN PRIVATE KEY-----\ntest\n-----END PRIVATE KEY-----"
    b64_key = base64.b64encode(key.encode()).decode()
    monkeypatch.setattr(config, "SSH_KEY", b64_key)
    setup_ssh_key()
    assert config.SSH_KEY_PATH is not None
    with open(config.SSH_KEY_PATH, "r") as f:
        assert f.read() == key
    os.unlink(config.SSH_KEY_PATH)


def test_run_command_sudo_wrapping(mock_conn, monkeypatch):
    monkeypatch.setattr(config, "USE_SUDO", True)
    monkeypatch.setattr(config, "REMOTE_USER", "deploy")
    run_command(mock_conn, "test-cmd")

    call_args = mock_conn.run.call_args[0][0]
    assert "sudo" in call_args
    assert "bash -l -c" in call_args
    assert "source /home/deploy/.bashrc" in call_args


def test_run_command_password_sudo(mock_conn, monkeypatch):
    monkeypatch.setattr(config, "USE_SUDO", True)
    monkeypatch.setattr(config, "REMOTE_PASSWORD", "mypass")
    run_command(mock_conn, "test-cmd")

    call_args = mock_conn.run.call_args[0][0]
    assert "printf '%s\\n' 'mypass' | sudo -S" in call_args


def test_install_dependencies_missing(mock_conn):
    # Mocking 'which' results: git exists, others don't
    mock_conn.run.side_effect = [
        Mock(stdout="/usr/bin/git"),  # git
        Mock(stdout=""),  # pip
        Mock(stdout=""),  # dev
        Mock(stdout=""),  # build-essential
        Mock(stdout=""),  # libssl
        Mock(stdout=""),  # libffi
        Mock(ok=True),  # apt update
        Mock(ok=True),  # apt install
    ]
    install_dependencies(mock_conn)
    # 6 'which' calls + 2 installations = 8 calls
    assert mock_conn.run.call_count >= 8
