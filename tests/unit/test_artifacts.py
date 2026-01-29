from unittest.mock import MagicMock, patch

import pytest

from src import config
from src.connection import copy_artifacts


@pytest.fixture
def mock_conn():
    conn = MagicMock()
    conn.run.return_value = MagicMock(ok=True, stdout="")
    return conn


def test_copy_artifacts_no_config(mock_conn, monkeypatch):
    monkeypatch.setattr(config, "COPY_ARTIFACTS", [])
    copy_artifacts(mock_conn)
    mock_conn.put.assert_not_called()


def test_copy_artifacts_local_missing(mock_conn, monkeypatch, capsys):
    monkeypatch.setattr(config, "COPY_ARTIFACTS", [("missing_local", "/remote")])
    copy_artifacts(mock_conn)
    mock_conn.put.assert_not_called()
    assert "not found, skipping" in capsys.readouterr().out


def test_copy_artifacts_success(mock_conn, monkeypatch, tmp_path):
    # Create a dummy local file
    local_file = tmp_path / "test.txt"
    local_file.write_text("content")

    # Configure artifacts
    monkeypatch.setattr(config, "COPY_ARTIFACTS", [(str(local_file), "/app/test.txt")])
    monkeypatch.setattr(config, "GIT_DIR", "/app")

    with patch("tarfile.open") as mock_tar_open, patch(
        "src.connection.run_command"
    ) as mock_run_cmd:
        mock_tar = MagicMock()
        mock_tar_open.return_value.__enter__.return_value = mock_tar

        copy_artifacts(mock_conn)

        # Verify tarball creation
        mock_tar.add.assert_called_with(str(local_file), arcname="test.txt")

        # Verify upload
        assert mock_conn.put.called

        # Verify extraction logic runs
        calls = [str(c) for c in mock_run_cmd.mock_calls]
        assert any("mkdir -p /app" in c for c in calls)
        assert any("rm -rf /app/test.txt" in c for c in calls)
        assert any("tar -xzf" in c and "-C /app" in c for c in calls)
        assert any("rm /tmp/" in c for c in calls)
