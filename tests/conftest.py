import os

# Load .env.test from root into environment
env_test_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env.test")
if os.path.exists(env_test_path):
    with open(env_test_path, "r") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                value = value.strip()
                # Strip surrounding quotes if present
                if (value.startswith('"') and value.endswith('"')) or (
                    value.startswith("'") and value.endswith("'")
                ):
                    value = value[1:-1]
                # Unescape \n to real newlines for blobs
                os.environ[key.strip()] = value.replace("\\n", "\n")
