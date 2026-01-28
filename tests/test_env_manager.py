import os
from unittest.mock import Mock, patch

import pytest
from fabric import Connection

from src.config import config
from src.env_manager import (
    create_env_file,
    detect_file_patterns,
    determine_file_structure,
    generate_env_files,
    parse_all_in_one_secret,
)


@pytest.fixture
def mock_conn():
    conn = Mock(spec=Connection)
    conn.run.return_value = Mock(stdout="", ok=True)
    conn.cd.return_value.__enter__ = Mock(return_value=None)
    conn.cd.return_value.__exit__ = Mock(return_value=None)
    return conn


def test_parse_formats():
    assert parse_all_in_one_secret("K1=V1\nK2=V2", "env") == {"K1": "V1", "K2": "V2"}
    assert parse_all_in_one_secret('{"K1": "V1"}', "json") == {"K1": "V1"}
    assert parse_all_in_one_secret("K1: V1", "yaml") == {"K1": "V1"}


def test_pattern_detection():
    # Variable names must end with _ or have more parts to trigger regex correctly
    env_vars = {"ENV_APP_PORT": "80", "ENV_DATABASE_URL": "...", "ENV_REDIS_HOST": "..."}
    patterns = detect_file_patterns(env_vars, "nested")
    assert ".env.app" in patterns
    assert ".env.database" in patterns
    assert ".env.redis" in patterns


def test_structure_nested(monkeypatch):
    monkeypatch.setattr(config, "ENV_FILES_PATH", None)
    paths = determine_file_structure("nested", [".env.app"], "prod", "/app")
    assert paths[".env.app"] == "/app/.envs/prod/.env.app"


def test_root_mega_file_creation(mock_conn, monkeypatch):
    test_secrets = {
        "ENV_APP_V1": "val1",
        "ENV_DB_V2": "val2",
        "ENV_FILES_GENERATE": "true",
        "ENV_FILES_CREATE_ROOT": "true",
        "ENV_FILES_STRUCTURE": "flat",
        "ENV_FILES_PATTERNS": "",
    }

    with patch.dict(os.environ, test_secrets, clear=False):
        config.load()
        # Force these values and a predictable subdir
        config.ENV_FILES_GENERATE = True
        config.ENV_FILES_CREATE_ROOT = True
        config.ENV_FILES_STRUCTURE = "flat"
        config.ENV_FILES_PATTERNS = []
        config.GIT_SUBDIR = "/testing"

        with patch("src.env_manager.create_env_file") as mock_create:
            generate_env_files(mock_conn)

            # We expect .env.app, .env.db and root .env
            # (plus maybe .env.files based on the shared ENV_ prefix bug)
            assert mock_create.call_count >= 3

            # Look for the root .env in our testing subdir
            root_calls = [c for c in mock_create.call_args_list if c[0][1] == "/testing/.env"]
            assert len(root_calls) == 1
            merged_vars = root_calls[0][0][2]
            assert "V1" in merged_vars
            assert "V2" in merged_vars


def test_heredoc_escaping(mock_conn):
    env_vars = {"KEY": "val$with$dollars"}
    create_env_file(mock_conn, ".env", env_vars)
    found_secure_cat = False
    for call in mock_conn.run.call_args_list:
        cmd = call[0][0]
        if "cat >" in cmd and "<< 'EOF'" in cmd:
            found_secure_cat = True
            assert "KEY=val$with$dollars" in cmd
    assert found_secure_cat
