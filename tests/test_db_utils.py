from unittest.mock import Mock, patch, MagicMock
from fabric import Connection
import pytest
from src.config import config
from src.providers import utils

@pytest.fixture
def mock_conn():
    conn = Mock(spec=Connection)
    conn.run.return_value = Mock(stdout="", ok=True)
    conn.cd.return_value.__enter__ = Mock(return_value=None)
    conn.cd.return_value.__exit__ = Mock(return_value=None)
    return conn

def test_detect_db_postgres(mock_conn, monkeypatch):
    monkeypatch.setattr(config, "GIT_SUBDIR", "/app")
    
    def mock_run(cmd, **kwargs):
        if "test -f" in cmd:
            if "docker-compose.yml" in cmd: return Mock(stdout="exists")
            return Mock(stdout="not exists")
        if "grep" in cmd:
            if "postgres" in cmd: return Mock(stdout="image: postgres")
            return Mock(stdout="")
        return Mock(stdout="")
        
    mock_conn.run.side_effect = mock_run
    dbs = utils.detect_database_type(mock_conn)
    assert "postgres" in dbs

def test_detect_db_multiple(mock_conn, monkeypatch):
    monkeypatch.setattr(config, "GIT_SUBDIR", "/app")
    
    def mock_run(cmd, **kwargs):
        if "test -f" in cmd:
            if "docker-compose.yml" in cmd: return Mock(stdout="exists")
            return Mock(stdout="not exists")
        if "grep" in cmd:
            if "postgres" in cmd or "redis" in cmd: return Mock(stdout="match")
            return Mock(stdout="")
        return Mock(stdout="")
        
    mock_conn.run.side_effect = mock_run
    dbs = utils.detect_database_type(mock_conn)
    assert "postgres" in dbs
    assert "redis" in dbs

def test_fix_permissions_logic(mock_conn, monkeypatch):
    monkeypatch.setattr(config, "GIT_SUBDIR", "/app")
    
    def mock_run(cmd, **kwargs):
        if "test -f" in cmd: return Mock(stdout="exists")
        if "grep" in cmd: return Mock(stdout="postgres")
        if "find" in cmd: return Mock(stdout="./pgdata")
        return Mock(stdout="")
        
    mock_conn.run.side_effect = mock_run
    
    with patch("src.providers.utils.run_command") as mock_run_cmd:
        utils.fix_database_permissions(mock_conn)
        assert mock_run_cmd.called
        args = mock_run_cmd.call_args[0][1]
        assert "chown -R 999:999" in args
        assert "./pgdata" in args
