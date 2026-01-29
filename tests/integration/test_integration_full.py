import pytest

from src.config import config
from src.env_manager import generate_env_files


@pytest.fixture
def clean_remote_dir(integration_conn):
    """Fixture to provide clean directories for each test."""
    base_dir = "/opt/metaldeploy_tests"
    integration_conn.run(f"mkdir -p {base_dir}")

    def _clean(subdir):
        target = f"{base_dir}/{subdir}"
        integration_conn.run(f"rm -rf {target} && mkdir -p {target} && chmod 777 {target}")
        return target

    return _clean


def assert_file_content(conn, path, expected_substrings, forbidden_substrings=None):
    """Helper to assert file existence and content."""
    assert conn.run(f"test -f {path}", warn=True).ok, f"File not found: {path}"
    content = conn.run(f"cat {path}", hide=True).stdout
    for sub in expected_substrings:
        assert sub in content, f"Substring '{sub}' not found in {path}. Content:\n{content}"
    if forbidden_substrings:
        for sub in forbidden_substrings:
            assert (
                sub not in content
            ), f"Forbidden substring '{sub}' found in {path}. Content:\n{content}"


@pytest.mark.integration
def test_ssh_connection(integration_conn):
    """Test basic SSH connectivity."""
    result = integration_conn.run("whoami", hide=True)
    assert result.stdout.strip() == "root"


# ------------------------------------------------------------------------------
# HYPER-EXHAUSTIVE PERMUTATION TESTS
# ------------------------------------------------------------------------------


@pytest.mark.integration
def test_env_exhaustive_multi_env_nested(integration_conn, clean_remote_dir, monkeypatch):
    """
    1. Structure: NESTED
    2. Environments: DEV, STAGING, PROD (Coexistence)
    3. Formats: Standard .env blobs
    """
    target_dir = clean_remote_dir("multi_env_nested")
    monkeypatch.setattr(config, "ENV_FILES_GENERATE", True)
    monkeypatch.setattr(config, "ENV_FILES_STRUCTURE", "nested")
    monkeypatch.setattr(config, "GIT_SUBDIR", target_dir)

    for env in ["dev", "staging", "prod"]:
        monkeypatch.setattr(config, "ENVIRONMENT", env)
        generate_env_files(integration_conn)

    # Assert dev structure
    assert_file_content(integration_conn, f"{target_dir}/.envs/dev/.env.app", ["PORT=8000"])
    # Assert staging structure
    assert_file_content(integration_conn, f"{target_dir}/.envs/staging/.env.app", ["PORT=3000"])
    # Assert prod structure
    assert_file_content(
        integration_conn,
        f"{target_dir}/.envs/prod/.env.app",
        ["PORT=9000", "SECRET=prod-exclusive-secret"],
    )


@pytest.mark.integration
def test_env_exhaustive_flat_staging(integration_conn, clean_remote_dir, monkeypatch):
    """
    1. Structure: FLAT
    2. Environment: STAGING
    3. Behavior: Files at root
    """
    target_dir = clean_remote_dir("flat_staging")
    monkeypatch.setattr(config, "ENV_FILES_GENERATE", True)
    monkeypatch.setattr(config, "ENV_FILES_STRUCTURE", "flat")
    monkeypatch.setattr(config, "ENVIRONMENT", "staging")
    monkeypatch.setattr(config, "GIT_SUBDIR", target_dir)

    generate_env_files(integration_conn)

    assert_file_content(integration_conn, f"{target_dir}/.env.app", ["PORT=3000"])
    assert_file_content(
        integration_conn, f"{target_dir}/.env.database", ["DB_URL=postgres://db:5432"]
    )


@pytest.mark.integration
def test_env_exhaustive_single_prod(integration_conn, clean_remote_dir, monkeypatch):
    """
    1. Structure: SINGLE
    2. Environment: PROD
    3. Behavior: All in one .env file
    """
    target_dir = clean_remote_dir("single_prod")
    monkeypatch.setattr(config, "ENV_FILES_GENERATE", True)
    monkeypatch.setattr(config, "ENV_FILES_STRUCTURE", "single")
    monkeypatch.setattr(config, "ENVIRONMENT", "prod")
    monkeypatch.setattr(config, "GIT_SUBDIR", target_dir)

    generate_env_files(integration_conn)

    assert_file_content(
        integration_conn,
        f"{target_dir}/.env",
        ["APP_PORT=9000", "DATABASE_DB_USER=prod-json-admin", "REDIS_HOST=redis-prod-yaml-cluster"],
        forbidden_substrings=["FILES_GENERATE", "FILES_STRUCTURE", "FILES_FORMAT"],
    )


@pytest.mark.integration
def test_env_exhaustive_auto_dev(integration_conn, clean_remote_dir, monkeypatch):
    """
    1. Structure: AUTO (should behave like nested if multiple folders exist)
    2. Environment: DEV
    """
    target_dir = clean_remote_dir("auto_dev")
    monkeypatch.setattr(config, "ENV_FILES_GENERATE", True)
    monkeypatch.setattr(config, "ENV_FILES_STRUCTURE", "auto")
    monkeypatch.setattr(config, "ENVIRONMENT", "dev")
    monkeypatch.setattr(config, "GIT_SUBDIR", target_dir)

    generate_env_files(integration_conn)

    # Auto on empty dir defaults to nested-like logic
    assert_file_content(integration_conn, f"{target_dir}/.envs/dev/.env.app", ["PORT=8000"])


@pytest.mark.integration
def test_env_exhaustive_custom_path_relative(integration_conn, clean_remote_dir, monkeypatch):
    """
    1. Path: Custom Relative (my_configs)
    2. Structure: FLAT
    """
    target_dir = clean_remote_dir("custom_path_rel")
    monkeypatch.setattr(config, "ENV_FILES_GENERATE", True)
    monkeypatch.setattr(config, "ENV_FILES_STRUCTURE", "flat")
    monkeypatch.setattr(config, "ENV_FILES_PATH", "my_configs")
    monkeypatch.setattr(config, "ENVIRONMENT", "dev")
    monkeypatch.setattr(config, "GIT_SUBDIR", target_dir)

    generate_env_files(integration_conn)

    assert_file_content(integration_conn, f"{target_dir}/my_configs/.env.app", ["PORT=8000"])


@pytest.mark.integration
def test_env_exhaustive_custom_path_absolute(integration_conn, clean_remote_dir, monkeypatch):
    """
    1. Path: Custom Absolute (/tmp/metaldeploy_abs)
    """
    clean_remote_dir("custom_path_abs")
    abs_path = "/opt/metaldeploy_tests/custom_path_abs"
    # No need to recreate abs_path since clean_remote_dir already did it

    monkeypatch.setattr(config, "ENV_FILES_GENERATE", True)
    monkeypatch.setattr(config, "ENV_FILES_STRUCTURE", "flat")
    monkeypatch.setattr(config, "ENV_FILES_PATH", abs_path)
    monkeypatch.setattr(config, "ENVIRONMENT", "dev")
    monkeypatch.setattr(config, "GIT_SUBDIR", "/tmp/random_cwd_for_abs_test")
    integration_conn.run("mkdir -p /tmp/random_cwd_for_abs_test")

    generate_env_files(integration_conn)

    assert_file_content(integration_conn, f"{abs_path}/.env.app", ["PORT=8000"])


@pytest.mark.integration
def test_env_exhaustive_json_yaml_formats(integration_conn, clean_remote_dir, monkeypatch):
    """
    Verify JSON and YAML parsing correctness in output.
    """
    target_dir = clean_remote_dir("formats_parsing")
    monkeypatch.setattr(config, "ENV_FILES_GENERATE", True)
    monkeypatch.setattr(config, "ENV_FILES_STRUCTURE", "flat")
    monkeypatch.setattr(config, "ENVIRONMENT", "prod")
    monkeypatch.setattr(config, "GIT_SUBDIR", target_dir)

    generate_env_files(integration_conn)

    # DATABASE was JSON in .env.test
    assert_file_content(
        integration_conn, f"{target_dir}/.env.database", ["DB_USER=prod-json-admin"]
    )
    # REDIS was YAML in .env.test
    assert_file_content(
        integration_conn, f"{target_dir}/.env.redis", ["HOST=redis-prod-yaml-cluster"]
    )


@pytest.mark.integration
def test_env_exhaustive_create_root_aggregated(integration_conn, clean_remote_dir, monkeypatch):
    """
    Flag: ENV_FILES_CREATE_ROOT=true
    """
    target_dir = clean_remote_dir("create_root_agg")
    monkeypatch.setattr(config, "ENV_FILES_GENERATE", True)
    monkeypatch.setattr(config, "ENV_FILES_STRUCTURE", "nested")
    monkeypatch.setattr(config, "ENV_FILES_CREATE_ROOT", True)
    monkeypatch.setattr(config, "ENVIRONMENT", "dev")
    monkeypatch.setattr(config, "GIT_SUBDIR", target_dir)

    generate_env_files(integration_conn)

    # Both nested and root combined file should exist
    assert_file_content(integration_conn, f"{target_dir}/.envs/dev/.env.app", ["PORT=8000"])
    assert_file_content(
        integration_conn,
        f"{target_dir}/.env",
        ["APP_PORT=8000", "DATABASE_DB_USER=json-admin"],
        forbidden_substrings=["FILES_GENERATE", "FILES_STRUCTURE", "FILES_FORMAT"],
    )


@pytest.mark.integration
def test_env_exhaustive_explicit_patterns(integration_conn, clean_remote_dir, monkeypatch):
    """
    Flag: ENV_FILES_PATTERNS (Explicit list)
    """
    target_dir = clean_remote_dir("explicit_patterns")
    monkeypatch.setattr(config, "ENV_FILES_GENERATE", True)
    monkeypatch.setattr(config, "ENV_FILES_STRUCTURE", "flat")
    monkeypatch.setattr(config, "ENV_FILES_PATTERNS", [".env.only_app", ".env.only_db"])
    monkeypatch.setattr(config, "ENVIRONMENT", "dev")
    monkeypatch.setattr(config, "GIT_SUBDIR", target_dir)

    # We need variables matching ONLY_APP and ONLY_DB
    monkeypatch.setenv("ENV_ONLY_APP_VAR", "app_val")
    monkeypatch.setenv("ENV_ONLY_DB_VAR", "db_val")

    generate_env_files(integration_conn)

    assert_file_content(integration_conn, f"{target_dir}/.env.only_app", ["VAR=app_val"])
    assert_file_content(integration_conn, f"{target_dir}/.env.only_db", ["VAR=db_val"])


@pytest.mark.integration
def test_env_exhaustive_file_path_secret(integration_conn, clean_remote_dir, monkeypatch, tmp_path):
    """
    Verify reading secrets from a file path (Jenkins/CI style).
    """
    target_dir = clean_remote_dir("file_path_secret")

    # Create a local secret file
    secret_file = tmp_path / "jenkins_secret.json"
    secret_content = '{"FILE_DB_USER": "file-user-admin", "FILE_DB_PASS": "file-secret-pass"}'
    secret_file.write_text(secret_content)

    monkeypatch.setattr(config, "ENV_FILES_GENERATE", True)
    monkeypatch.setattr(config, "ENV_FILES_STRUCTURE", "flat")
    monkeypatch.setattr(config, "ENVIRONMENT", "dev")
    monkeypatch.setattr(config, "GIT_SUBDIR", target_dir)

    # Point the environment variable to the local file path
    monkeypatch.setenv("ENV_DATABASE", str(secret_file))

    generate_env_files(integration_conn)

    # Verify JSON from file
    assert_file_content(
        integration_conn,
        f"{target_dir}/.env.database",
        ["DB_USER=file-user-admin", "DB_PASS=file-secret-pass"],
    )

    # 2. Test YAML from file
    yaml_file = tmp_path / "jenkins_secret.yaml"
    yaml_file.write_text("HOST: yaml-file-host\nPORT: 6379")
    monkeypatch.setenv("ENV_REDIS", str(yaml_file))

    # 3. Test standard .env from file
    env_file = tmp_path / "jenkins_secret.env"
    env_file.write_text("S3_BUCKET=file-bucket\nS3_REGION=us-east-1")
    monkeypatch.setenv("ENV_S3", str(env_file))

    generate_env_files(integration_conn)

    # Verify YAML from file
    assert_file_content(
        integration_conn, f"{target_dir}/.env.redis", ["HOST=yaml-file-host", "PORT=6379"]
    )

    # Verify .env from file
    assert_file_content(
        integration_conn, f"{target_dir}/.env.s3", ["BUCKET=file-bucket", "REGION=us-east-1"]
    )
