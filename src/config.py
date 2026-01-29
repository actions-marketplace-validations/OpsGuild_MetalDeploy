import os


class Config:
    def __init__(self, overrides=None):
        self.load(overrides)

    def load(self, overrides=None):
        overrides = overrides or {}

        # Helper to get Boolean environment variables
        def get_bool_env(name, default="false"):
            val = overrides.get(name) or os.getenv(name, default)
            return str(val).lower() == "true"

        def get_env(name, default=None):
            return overrides.get(name) or os.getenv(name, default)

        # Configuration from environment variables
        self.GIT_URL_ENV = get_env("GIT_URL", "").strip()
        if not self.GIT_URL_ENV and get_env("GITHUB_REPOSITORY"):
            github_repo = get_env("GITHUB_REPOSITORY")
            self.GIT_URL = f"https://github.com/{github_repo}.git"
        else:
            self.GIT_URL = self.GIT_URL_ENV

        self.GIT_AUTH_METHOD = get_env("GIT_AUTH_METHOD", "none").lower()
        self.GIT_TOKEN = get_env("GIT_TOKEN", "")
        self.GIT_USER = get_env("GIT_USER", "").strip() or get_env("GITHUB_ACTOR", "")
        self.GIT_SSH_KEY = get_env("GIT_SSH_KEY")

        self.DEPLOYMENT_TYPE = get_env("DEPLOYMENT_TYPE", "baremetal").lower()
        self.ENVIRONMENT = get_env("ENVIRONMENT", "dev")
        self.REMOTE_USER = get_env("REMOTE_USER", "root")
        self.REMOTE_HOST = get_env("REMOTE_HOST", "127.0.0.1")

        if get_env("REMOTE_DIR"):
            self.REMOTE_DIR = get_env("REMOTE_DIR")
        elif self.REMOTE_USER == "root":
            self.REMOTE_DIR = "/root"
        else:
            self.REMOTE_DIR = f"/home/{self.REMOTE_USER}"

        self.SSH_KEY = get_env("SSH_KEY")
        self.REMOTE_PASSWORD = get_env("REMOTE_PASSWORD")
        self.REGISTRY_TYPE = get_env("REGISTRY_TYPE", "ghcr")
        self.PROFILE = get_env("PROFILE")
        self.DEPLOY_COMMAND = get_env("DEPLOY_COMMAND")
        self.K8S_MANIFEST_PATH = get_env("K8S_MANIFEST_PATH")
        self.K8S_NAMESPACE = get_env("K8S_NAMESPACE", "default")
        self.USE_SUDO = get_bool_env("USE_SUDO")

        self.PROJECT_NAME = self.GIT_URL.split("/")[-1].split(".")[0] if self.GIT_URL else ""
        self.GIT_DIR = (
            os.path.join(self.REMOTE_DIR, self.PROJECT_NAME)
            if self.PROJECT_NAME
            else self.REMOTE_DIR
        )
        self.GIT_SUBDIR = os.path.join(self.GIT_DIR, "")

        # Environment file generation configuration
        self.ENV_FILES_GENERATE = get_bool_env("ENV_FILES_GENERATE")
        self.ENV_FILES_STRUCTURE = os.getenv("ENV_FILES_STRUCTURE", "auto").lower()
        self.ENV_FILES_PATH = os.getenv("ENV_FILES_PATH")
        env_patterns = os.getenv("ENV_FILES_PATTERNS")
        self.ENV_FILES_PATTERNS = env_patterns.split(",") if env_patterns else []
        self.ENV_FILES_CREATE_ROOT = get_bool_env("ENV_FILES_CREATE_ROOT", "false")
        self.ENV_FILES_FORMAT = os.getenv("ENV_FILES_FORMAT", "auto").lower()

        # Build Artifacts
        artifacts = get_env("COPY_ARTIFACTS")
        self.COPY_ARTIFACTS = []
        workspace = get_env("GITHUB_WORKSPACE", ".")
        if artifacts:
            for item in artifacts.split(","):
                if ":" in item:
                    local, remote = item.split(":", 1)
                    local_path = local.strip()
                    # Resolve relative path against workspace if not absolute
                    if not os.path.isabs(local_path):
                        local_path = os.path.abspath(os.path.join(workspace, local_path))
                    self.COPY_ARTIFACTS.append((local_path, remote.strip()))

        # Global state for temporary files
        self.SSH_KEY_PATH = None
        self.GIT_SSH_KEY_PATH = None
        self.AUTH_GIT_URL = None


config = Config()
