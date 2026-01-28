from unittest.mock import Mock, patch, MagicMock
from fabric import Connection
import pytest
from src.config import config
from src import git_ops

@pytest.fixture
def mock_conn():
    conn = MagicMock(spec=Connection)
    conn.run.return_value = Mock(stdout="", ok=True)
    conn.cd.return_value.__enter__ = Mock(return_value=None)
    conn.cd.return_value.__exit__ = Mock(return_value=None)
    return conn

def test_git_auth_token_setup(monkeypatch):
    monkeypatch.setattr(config, "GIT_AUTH_METHOD", "token")
    monkeypatch.setattr(config, "GIT_TOKEN", "token123")
    monkeypatch.setattr(config, "GIT_USER", "user123")
    monkeypatch.setattr(config, "GIT_URL", "https://github.com/org/repo.git")
    git_ops.setup_git_auth()
    assert config.AUTH_GIT_URL == "https://user123:token123@github.com/org/repo.git"

def test_git_auth_ssh_conversion(monkeypatch):
    monkeypatch.setattr(config, "GIT_AUTH_METHOD", "ssh")
    monkeypatch.setattr(config, "GIT_SSH_KEY", "-----BEGIN PRIVATE KEY-----")
    monkeypatch.setattr(config, "GIT_URL", "https://github.com/org/repo.git")
    with patch("src.git_ops.tempfile.NamedTemporaryFile") as mock_tmp, patch("os.chmod"):
        mock_tmp.return_value.__enter__.return_value.name = "/tmp/key"
        git_ops.setup_git_auth()
        assert config.AUTH_GIT_URL == "git@github.com:org/repo.git"

def test_clone_new_repository(mock_conn, monkeypatch):
    monkeypatch.setattr(config, "GIT_DIR", "/app/repo")
    monkeypatch.setattr(config, "REMOTE_DIR", "/app")
    monkeypatch.setattr(config, "PROJECT_NAME", "repo")
    monkeypatch.setattr(config, "GIT_SUBDIR", "/app/repo")
    monkeypatch.setattr(config, "ENVIRONMENT", "main")
    
    mock_conn.run.side_effect = [
        Mock(ok=True), # mkdir
        Mock(stdout="not exists"), # dir check
        Mock(ok=True), # git clone
        Mock(ok=True), # safe.directory
        Mock(ok=True), # chown
        Mock(stdout="main"), # rev-parse (current branch)
        Mock(ok=True), # fetch & reset
    ]
    
    git_ops.clone_repo(mock_conn)
    assert any("git clone" in str(call) for call in mock_conn.run.call_args_list)

def test_clone_existing_needs_checkout(mock_conn, monkeypatch):
    monkeypatch.setattr(config, "ENVIRONMENT", "staging")
    monkeypatch.setattr(config, "GIT_DIR", "/app/repo")
    monkeypatch.setattr(config, "GIT_SUBDIR", "/app/repo")
    
    mock_conn.run.side_effect = [
        Mock(ok=True), # mkdir
        Mock(stdout="exists"), # dir exists
        Mock(stdout="git_repo"), # is git repo
        Mock(ok=True), # safe.directory
        Mock(ok=True), # chown
        Mock(stdout="main"), # rev-parse -> we are on main, but env is staging
        Mock(ok=True), # git stash
        Mock(ok=True), # git checkout staging
        Mock(ok=True), # fetch & reset
    ]
    
    git_ops.clone_repo(mock_conn)
    calls = [str(call) for call in mock_conn.run.call_args_list]
    assert any("git checkout staging" in c for c in calls)
    assert any("git stash" in c for c in calls)

def test_clone_ssh_auth_flow(mock_conn, monkeypatch):
    monkeypatch.setattr(config, "GIT_AUTH_METHOD", "ssh")
    monkeypatch.setattr(config, "GIT_SSH_KEY_PATH", "/tmp/key")
    monkeypatch.setattr(config, "PROJECT_NAME", "repo")
    monkeypatch.setattr(config, "GIT_DIR", "/app/repo")
    
    mock_conn.run.side_effect = [
        Mock(ok=True), # mkdir
        Mock(ok=True), # chmod key
        Mock(ok=True), # mkdir .ssh
        Mock(ok=True), # echo config
        Mock(ok=True), # chmod config
        Mock(stdout="not exists"), # dir check
        Mock(ok=True), # git clone
        Mock(ok=True), # safe.directory
        Mock(ok=True), # chown
        Mock(stdout="dev"), # rev-parse
        Mock(ok=True), # fetch & reset
    ]
    
    git_ops.clone_repo(mock_conn)
    # Check if key was put to remote
    assert mock_conn.put.called
    # Check if GIT_SSH_COMMAND was used
    clone_call = [c for c in mock_conn.run.call_args_list if "git clone" in str(c)][0]
    assert "GIT_SSH_COMMAND" in clone_call[0][0]
