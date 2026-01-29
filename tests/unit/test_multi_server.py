from unittest.mock import MagicMock, patch

import pytest

from src import orchestrator
from src.config import config


@pytest.fixture
def mock_executor():
    with patch("concurrent.futures.ProcessPoolExecutor") as mock_pool:
        executor_instance = MagicMock()
        mock_pool.return_value.__enter__.return_value = executor_instance
        yield executor_instance


def test_single_host_direct_call(monkeypatch):
    """Test that single host bypasses the executor."""
    monkeypatch.setattr(config, "REMOTE_HOST", "1.1.1.1")

    # We must patch where it's used. Since handle_connection is in src.orchestrator,
    # and it calls deploy_single_host which is also in src.orchestrator,
    # patching src.orchestrator.deploy_single_host should work.
    # However, to be safe and avoid network usage if it fails, we also mock Connection.

    with patch("src.orchestrator.deploy_single_host") as mock_single:
        orchestrator.handle_connection()
        mock_single.assert_called_once()

    # Check with Executor mocked - should NOT be called
    with patch("concurrent.futures.ProcessPoolExecutor") as mock_pool, patch(
        "src.orchestrator.deploy_single_host"
    ) as mock_single:
        orchestrator.handle_connection()
        mock_pool.assert_not_called()
        mock_single.assert_called_once()


def test_multi_host_distribution(monkeypatch, mock_executor):
    """Test that multiple hosts spawn multiple workers with correct overrides."""
    monkeypatch.setattr(config, "REMOTE_HOST", "h1, h2,   h3")
    monkeypatch.setattr(
        config, "REMOTE_USER", "u1, u2"
    )  # Short list, should reuse last (u2 for h3)

    # Mock future to avoid actual execution waiting
    mock_future = MagicMock()
    mock_future.result.return_value = None
    mock_executor.submit.return_value = mock_future

    with patch("concurrent.futures.as_completed") as mock_as_completed:
        # as_completed yields futures.
        # In handle_connection: for future in as_completed(futures): ...
        # We need it to yield the mock_future objects we submitted.
        # Since logic submits multiple times, submit returns same mock_future?
        # Better: make submit return a unique mock for each call?

        f1, f2, f3 = MagicMock(), MagicMock(), MagicMock()
        f1.result.return_value = None
        f2.result.return_value = None
        f3.result.return_value = None
        mock_executor.submit.side_effect = [f1, f2, f3]

        mock_as_completed.return_value = [f1, f2, f3]

        orchestrator.handle_connection()

    assert mock_executor.submit.call_count == 3

    # Inspect calls
    calls = mock_executor.submit.call_args_list

    # Call 1: h1, u1
    args1, _ = calls[0]
    assert args1[1]["REMOTE_HOST"] == "h1"
    assert args1[1]["REMOTE_USER"] == "u1"

    # Call 2: h2, u2
    args2, _ = calls[1]
    assert args2[1]["REMOTE_HOST"] == "h2"
    assert args2[1]["REMOTE_USER"] == "u2"

    # Call 3: h3, u2 (re-use last user)
    args3, _ = calls[2]
    assert args3[1]["REMOTE_HOST"] == "h3"
    assert args3[1]["REMOTE_USER"] == "u2"


def test_worker_reloads_config(monkeypatch):
    """Test that the worker function reloads config."""
    # We can't easily test cross-process state here, but we can verify the function calls config.load
    with patch.object(config, "load") as mock_load, patch(
        "src.orchestrator.deploy_single_host"
    ) as mock_deploy:
        overrides = {"REMOTE_HOST": "test-host"}
        orchestrator.deploy_worker(overrides)

        mock_load.assert_called_with(overrides)
        mock_deploy.assert_called_once()
