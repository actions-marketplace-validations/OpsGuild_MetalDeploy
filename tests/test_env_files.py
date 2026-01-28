#!/usr/bin/env python3
"""
Test script for environment file generation functionality.
This script simulates different scenarios and tests the parsing logic.
"""

import os
import sys
from unittest.mock import patch

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(__file__))

from deploy import (  # noqa: E402
    detect_environment_secrets,
    detect_file_patterns,
    determine_file_structure,
    merge_env_vars_by_priority,
    parse_all_in_one_secret,
)


def test_parse_all_in_one_secret():
    """Test multi-format parsing"""
    print("Testing parse_all_in_one_secret...")

    # Test ENV format
    env_content = """DEBUG=false
SECRET_KEY=abc123
DATABASE_URL=postgresql://localhost:5432/db"""

    result = parse_all_in_one_secret(env_content, "env")
    assert result["DEBUG"] == "false"
    assert result["SECRET_KEY"] == "abc123"
    assert result["DATABASE_URL"] == "postgresql://localhost:5432/db"
    print("✅ ENV format parsing works")

    # Test JSON format
    json_content = """{"DEBUG": false, "SECRET_KEY": "abc123"}"""
    result = parse_all_in_one_secret(json_content, "json")
    assert result["DEBUG"] == "False"
    assert result["SECRET_KEY"] == "abc123"
    print("✅ JSON format parsing works")

    # Test YAML format
    yaml_content = """DEBUG: false
SECRET_KEY: abc123
DATABASE:
  HOST: localhost
  PORT: 5432"""

    result = parse_all_in_one_secret(yaml_content, "yaml")
    assert result["DEBUG"] == "False"
    assert result["SECRET_KEY"] == "abc123"
    assert result["DATABASE"] == "{'HOST': 'localhost', 'PORT': 5432}"
    print("✅ YAML format parsing works")


def test_detect_file_patterns():
    """Test pattern detection"""
    print("Testing detect_file_patterns...")

    env_vars = {
        "ENV_APP_DEBUG": "false",
        "ENV_APP_SECRET": "abc123",
        "ENV_DATABASE_HOST": "localhost",
        "ENV_REDIS_URL": "redis://localhost:6379",
        "ENV_PROD_APP_OVERRIDE": "true",
        "ENV_SOME_OTHER_VAR": "value",
    }

    patterns = detect_file_patterns(env_vars, "auto")
    assert ".env.app" in patterns
    assert ".env.database" in patterns
    assert ".env.redis" in patterns
    print("✅ Pattern detection works")

    # Test single mode
    patterns = detect_file_patterns(env_vars, "single")
    assert patterns == [".env"]
    print("✅ Single mode detection works")


def test_determine_file_structure():
    """Test file structure determination"""
    print("Testing determine_file_structure...")

    patterns = [".env.app", ".env.database"]

    # Test flat mode
    file_paths = determine_file_structure("flat", patterns, "prod", "/app")
    assert file_paths[".env.app"] == "/app/.env.app"
    assert file_paths[".env.database"] == "/app/.env.database"
    print("✅ Flat mode works")

    # Test nested mode
    file_paths = determine_file_structure("nested", patterns, "prod", "/app")
    assert file_paths[".env.app"] == "/app/.envs/prod/.env.app"
    assert file_paths[".env.database"] == "/app/.envs/prod/.env.database"
    print("✅ Nested mode works")

    # Test single mode
    file_paths = determine_file_structure("single", patterns, "prod", "/app")
    assert file_paths[".env"] == "/app/.env"
    print("✅ Single mode works")


def test_custom_path_with_auto_mode():
    """Test custom path with auto mode"""
    print("Testing custom path with auto mode...")

    patterns = [".env.app", ".env.database"]

    # Test custom path with auto mode
    file_paths = determine_file_structure("auto", patterns, "prod", "/app")
    assert file_paths[".env.app"] == "/app/.envs/prod/.env.app"
    assert file_paths[".env.database"] == "/app/.envs/prod/.env.database"

    # Test with custom base path
    with patch("deploy.ENV_FILES_PATH", "/custom/profiles"):
        file_paths = determine_file_structure("auto", patterns, "prod", "/app")
        assert file_paths[".env.app"] == "/custom/profiles/prod/.env.app"
        assert file_paths[".env.database"] == "/custom/profiles/prod/.env.database"

    print("✅ Custom path with auto mode works")


def test_merge_env_vars_by_priority():
    """Test priority system"""
    print("Testing merge_env_vars_by_priority...")

    all_env_vars = {
        "ENV_APP_DEBUG": "false",
        "ENV_APP_SECRET": "base_secret",
        "ENV_PROD_APP_SECRET": "prod_secret",
        "ENV_PROD_APP": "DEBUG=true\nSECRET_KEY=prod_override",
    }

    # Test merging for .env.app
    result = merge_env_vars_by_priority(all_env_vars, "prod", ".env.app")

    # Should have base DEBUG, overridden SECRET_KEY from ENV_PROD_APP_SECRET
    # and all variables from ENV_PROD_APP all-in-one secret
    assert result["DEBUG"] == "true"  # From ENV_PROD_APP
    assert "SECRET_KEY" in result  # From ENV_PROD_APP
    print("✅ Priority merging works")


def test_detect_environment_secrets():
    """Test full environment detection"""
    print("Testing detect_environment_secrets...")

    # Mock environment variables
    test_env = {
        "ENV_FILES_GENERATE": "true",
        "ENV_FILES_STRUCTURE": "auto",
        "ENVIRONMENT": "prod",
        "GIT_SUBDIR": "/app",
        "ENV_FILES_FORMAT": "auto",
        "ENV_APP_DEBUG": "false",
        "ENV_APP_SECRET": "base_secret",
        "ENV_DATABASE_HOST": "localhost",
        "ENV_PROD_APP_SECRET": "prod_secret",
        "ENV_PROD_APP": """DEBUG=true
SECRET_KEY=prod_abc123
DATABASE_URL=postgresql://localhost:5432/proddb""",
        "ENV_PROD_DATABASE": """HOST=prod-host
PORT=5432""",
    }

    with patch.dict(os.environ, test_env):
        with patch("deploy.ENV_FILES_STRUCTURE", "auto"), patch(
            "deploy.ENVIRONMENT", "prod"
        ), patch("deploy.GIT_SUBDIR", "/app"), patch("deploy.ENV_FILES_FORMAT", "auto"), patch(
            "deploy.ENV_FILES_PATTERNS", [".env.app", ".env.database"]
        ):
            result = detect_environment_secrets()

            assert ".env.app" in result
            assert ".env.database" in result

            # Check that env_app has merged variables
            app_vars = result[".env.app"]
            assert "DEBUG" in app_vars
            assert "SECRET_KEY" in app_vars
            assert "DATABASE_URL" in app_vars

            # Check that env_database has prod-specific variables
            db_vars = result[".env.database"]
            assert "HOST" in db_vars
            assert db_vars["HOST"] == "prod-host"

            print("✅ Full environment detection works")


def run_all_tests():
    """Run all tests"""
    print("🧪 Running environment file generation tests...\n")

    try:
        test_parse_all_in_one_secret()
        print()
        test_detect_file_patterns()
        print()
        test_determine_file_structure()
        print()
        test_merge_env_vars_by_priority()
        print()
        test_detect_environment_secrets()
        print()
        print("🎉 All tests passed!")
        return True
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
