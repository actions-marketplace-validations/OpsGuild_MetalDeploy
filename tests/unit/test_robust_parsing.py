from src.env_manager import parse_all_in_one_secret


def test_robust_parsing_edge_cases():
    """Verify that the parser handles multi-line, collapsed, and quoted values correctly."""

    # Complex case with:
    # 1. Multi-line PEM key (Firebase style)
    # 2. Collapsed space-separated keys
    # 3. Collapsed comma-separated keys
    # 4. Quoted values with spaces
    # 5. Values with internal '='

    complex_secret = """
# Whorkaz Configuration
NODE_ENV=production,PORT=3000
CORS_ORIGIN="*"
DB_URL="postgres://user:pass@host:5432/db?ssl=true"

FIREBASE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\\nMIIEvQIBADANBgkqhkiG9w0BAQEFA\\n-----END PRIVATE KEY-----\\n"
# Another comment
LOG_LEVEL=DEBUG, TIMEOUT=5000 KEY4=VAL4
"""

    parsed = parse_all_in_one_secret(complex_secret, format_hint="env")

    assert parsed["NODE_ENV"] == "production"
    assert parsed["PORT"] == "3000"
    assert parsed["CORS_ORIGIN"] == "*"
    assert parsed["DB_URL"] == "postgres://user:pass@host:5432/db?ssl=true"
    assert "BEGIN PRIVATE KEY" in parsed["FIREBASE_PRIVATE_KEY"]
    assert "END PRIVATE KEY" in parsed["FIREBASE_PRIVATE_KEY"]
    assert "\\n" in parsed["FIREBASE_PRIVATE_KEY"]
    assert parsed["LOG_LEVEL"] == "DEBUG"
    assert parsed["TIMEOUT"] == "5000"
    assert parsed["KEY4"] == "VAL4"


def test_user_firebase_key_handling():
    """Specific test for the user's reported Firebase private key issue."""
    firebase_block = 'FIREBASE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\\nMIIEvQIA...\\n-----END PRIVATE KEY-----\\n"'
    parsed = parse_all_in_one_secret(firebase_block, format_hint="env")

    # It should strip the outside quotes but keep the internal ones
    assert parsed["FIREBASE_PRIVATE_KEY"].startswith("-----BEGIN PRIVATE KEY-----")
    assert parsed["FIREBASE_PRIVATE_KEY"].endswith("-----END PRIVATE KEY-----\\n")


def test_collapsed_mixed_delimiters():
    """Test mixed spaces and commas on a single line."""
    content = "A=1,B=2 C=3 , D=4"
    parsed = parse_all_in_one_secret(content, format_hint="env")

    assert parsed["A"] == "1"
    assert parsed["B"] == "2"
    assert parsed["C"] == "3"
    assert parsed["D"] == "4"


def test_empty_or_no_keys():
    """Ensure it doesn't crash on invalid input."""
    assert parse_all_in_one_secret("", format_hint="env") == {}
    assert parse_all_in_one_secret("just some text without equals", format_hint="env") == {}
    assert parse_all_in_one_secret("# only comments", format_hint="env") == {}
