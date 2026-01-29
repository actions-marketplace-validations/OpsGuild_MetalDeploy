from src.env_manager import detect_file_patterns


def test_detect_patterns_generic_app():
    """Test generic ENV_APP detection with prod environment."""
    # Scenario: ENV_APP is defined (no suffix), environment is prod
    env_vars = {"ENV_APP": "PORT=8000", "ENV_FILES_GENERATE": "true"}
    environment = "prod"
    patterns = detect_file_patterns(env_vars, "auto", environment)
    # Should detect .env.app
    assert ".env.app" in patterns
    assert len(patterns) == 1


def test_detect_patterns_prod_app():
    """Test environment specific ENV_PROD_APP detection (prior fix)."""
    env_vars = {"ENV_PROD_APP": "PORT=9000", "ENV_FILES_GENERATE": "true"}
    environment = "prod"
    patterns = detect_file_patterns(env_vars, "auto", environment)
    assert ".env.app" in patterns


def test_detect_patterns_mixed():
    """Test mixture of generic and specific vars."""
    env_vars = {
        "ENV_APP": "COMMON=1",
        "ENV_PROD_DATABASE": "DB_HOST=localhost",
        "ENV_REDIS": "redis",  # Should detect .env.redis
    }
    environment = "prod"
    patterns = detect_file_patterns(env_vars, "auto", environment)
    assert ".env.redis" in patterns


def test_detect_patterns_ignore_config():
    """Ensure ENV_FILES_ config vars don't become files."""
    env_vars = {"ENV_FILES_STRUCTURE": "auto"}
    patterns = detect_file_patterns(env_vars, "auto", "prod")
    # Should default to .env.app if nothing else found, or empty?
    # Logic returns [".env.app"] if patterns is empty.
    assert patterns == [".env.app"]
