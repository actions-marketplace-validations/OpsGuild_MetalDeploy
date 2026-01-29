import json
import os
from unittest.mock import Mock, patch

import pytest
from fabric import Connection

from src.config import config
from src.env_manager import (
    create_env_file,
    detect_environment_secrets,
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
            assert "APP_V1" in merged_vars
            assert "DB_V2" in merged_vars


def test_heredoc_escaping(mock_conn):
    env_vars = {"KEY": "val$with$dollars"}
    # We need to mock run_command because create_env_file now uses it
    with patch("src.env_manager.run_command") as mock_run_cmd:
        create_env_file(mock_conn, ".env", env_vars)

        found_base64_tee = False
        for call in mock_run_cmd.call_args_list:
            cmd = call[0][1]
            if "base64 -d" in cmd and "tee" in cmd:
                found_base64_tee = True
                # The content should be base64 encoded
                # KEY=val$with$dollars -> S0VZPXZhbCR3aXRoJGRvbGxhcnM=
                assert "S0VZPXZhbCR3aXRoJGRvbGxhcnM=" in cmd
        assert found_base64_tee


def test_mixed_blob_and_raw_bucketing(mocker):
    """Regression test for user's mixed secret setup (toJSON blob + raw block)."""
    # Setup: ENV_BLOB has a JSON with an 'ENV' key containing raw vars
    mock_json = json.dumps({"ENV": "A=1\nB=2", "ENV_APP": "C=3", "OTHER_UNRELATED": "ignored"})

    # Isolate os.environ to avoid pollution from other tests
    mocker.patch(
        "os.environ", {"ENV_BLOB": mock_json, "ENV_FILES_GENERATE": "true", "ENVIRONMENT": "dev"}
    )

    # Patch the config object directly
    from src.env_manager import config

    mocker.patch.object(config, "ENVIRONMENT", "dev")
    mocker.patch.object(config, "ENV_FILES_STRUCTURE", "single")
    mocker.patch.object(config, "ENV_FILES_GENERATE", True)

    result = detect_environment_secrets()

    # Must correctly parse both from the raw block (A, B) and structured blob (APP_C)
    assert ".env" in result
    assert result[".env"]["A"] == "1"
    assert result[".env"]["B"] == "2"
    assert "APP_C" in result[".env"]
    assert "OTHER_UNRELATED" not in result[".env"]
