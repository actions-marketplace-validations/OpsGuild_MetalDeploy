import argparse
import os
import sys

# Ensure src is in the python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.config import config  # noqa: E402
from src.orchestrator import handle_connection  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description="MetalDeploy - SSH Deployment Tool")

    # Common SSH/Host configuration
    parser.add_argument("--host", help="Remote host IP or domain")
    parser.add_argument("--user", help="Remote SSH user")
    parser.add_argument("--password", help="SSH password")
    parser.add_argument("--ssh-key", help="Path to SSH private key")

    # Deployment configuration
    parser.add_argument("--type", choices=["baremetal", "docker", "k8s"], help="Deployment type")
    parser.add_argument("--env", help="Environment (dev, staging, prod)")
    parser.add_argument("--dir", help="Remote deployment directory")
    parser.add_argument("--command", help="Custom deployment command")

    # Git configuration
    parser.add_argument("--git-url", help="Git repository URL")
    parser.add_argument("--git-auth", choices=["token", "ssh", "none"], help="Git auth method")

    # Registry configuration
    parser.add_argument(
        "--registry", choices=["ghcr", "dockerhub", "ecr"], help="Docker registry type"
    )

    # Env files
    parser.add_argument("--gen-env", action="store_true", help="Generate .env files")
    parser.add_argument("--sudo", action="store_true", help="Use sudo for commands")

    args = parser.parse_args()

    # Map CLI arguments to Config keys
    overrides = {}
    if args.host:
        overrides["REMOTE_HOST"] = args.host
    if args.user:
        overrides["REMOTE_USER"] = args.user
    if args.password:
        overrides["REMOTE_PASSWORD"] = args.password
    if args.ssh_key:
        overrides["SSH_KEY"] = args.ssh_key
    if args.type:
        overrides["DEPLOYMENT_TYPE"] = args.type
    if args.env:
        overrides["ENVIRONMENT"] = args.env
    if args.dir:
        overrides["REMOTE_DIR"] = args.dir
    if args.command:
        overrides["DEPLOY_COMMAND"] = args.command
    if args.git_url:
        overrides["GIT_URL"] = args.git_url
    if args.git_auth:
        overrides["GIT_AUTH_METHOD"] = args.git_auth
    if args.registry:
        overrides["REGISTRY_TYPE"] = args.registry
    if args.gen_env:
        overrides["ENV_FILES_GENERATE"] = "true"
    if args.sudo:
        overrides["USE_SUDO"] = "true"

    # Reload config with overrides
    config.load(overrides)

    try:
        handle_connection()
    except Exception as e:
        print(f"❌ Deployment failed: {e}")
        if os.getenv("GITHUB_OUTPUT"):
            with open(os.getenv("GITHUB_OUTPUT"), "a") as f:
                f.write("deployment_status=failed\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
