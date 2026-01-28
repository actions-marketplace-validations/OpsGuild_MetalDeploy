import os

class Config:
    def __init__(self):
        self.load()

    def load(self):
        # Helper to get Boolean environment variables
        def get_bool_env(name, default="false"):
            return os.getenv(name, default).lower() == "true"

        # Configuration from environment variables
        self.GIT_URL_ENV = os.getenv("GIT_URL", "").strip()
        if not self.GIT_URL_ENV and os.getenv("GITHUB_REPOSITORY"):
            github_repo = os.getenv("GITHUB_REPOSITORY")
            self.GIT_URL = f"https://github.com/{github_repo}.git"
        else:
            self.GIT_URL = self.GIT_URL_ENV

        self.GIT_AUTH_METHOD = os.getenv("GIT_AUTH_METHOD", "token").lower()
        self.GIT_TOKEN = os.getenv("GIT_TOKEN", "")
        self.GIT_USER = os.getenv("GIT_USER", "").strip() or os.getenv("GITHUB_ACTOR", "")
        self.GIT_SSH_KEY = os.getenv("GIT_SSH_KEY")

        self.DEPLOYMENT_TYPE = os.getenv("DEPLOYMENT_TYPE", "baremetal").lower()
        self.ENVIRONMENT = os.getenv("ENVIRONMENT", "dev")
        self.REMOTE_USER = os.getenv("REMOTE_USER", "root")
        self.REMOTE_HOST = os.getenv("REMOTE_HOST", "127.0.0.1")

        if os.getenv("REMOTE_DIR"):
            self.REMOTE_DIR = os.getenv("REMOTE_DIR")
        elif self.REMOTE_USER == "root":
            self.REMOTE_DIR = "/root"
        else:
            self.REMOTE_DIR = f"/home/{self.REMOTE_USER}"

        self.SSH_KEY = os.getenv("SSH_KEY")
        self.REMOTE_PASSWORD = os.getenv("REMOTE_PASSWORD")
        self.REGISTRY_TYPE = os.getenv("REGISTRY_TYPE", "ghcr")
        self.PROFILE = os.getenv("PROFILE")
        self.DEPLOY_COMMAND = os.getenv("DEPLOY_COMMAND")
        self.K8S_MANIFEST_PATH = os.getenv("K8S_MANIFEST_PATH")
        self.K8S_NAMESPACE = os.getenv("K8S_NAMESPACE", "default")
        self.USE_SUDO = get_bool_env("USE_SUDO")

        self.PROJECT_NAME = self.GIT_URL.split("/")[-1].split(".")[0] if self.GIT_URL else ""
        self.GIT_DIR = os.path.join(self.REMOTE_DIR, self.PROJECT_NAME) if self.PROJECT_NAME else self.REMOTE_DIR
        self.GIT_SUBDIR = os.path.join(self.GIT_DIR, "")

        # Environment file generation configuration
        self.ENV_FILES_GENERATE = get_bool_env("ENV_FILES_GENERATE")
        self.ENV_FILES_STRUCTURE = os.getenv("ENV_FILES_STRUCTURE", "auto").lower()
        self.ENV_FILES_PATH = os.getenv("ENV_FILES_PATH")
        self.ENV_FILES_PATTERNS = os.getenv("ENV_FILES_PATTERNS", ".env.app,.env.database").split(",")
        self.ENV_FILES_CREATE_ROOT = get_bool_env("ENV_FILES_CREATE_ROOT", "false")
        self.ENV_FILES_FORMAT = os.getenv("ENV_FILES_FORMAT", "auto").lower()

        # Global state for temporary files
        self.SSH_KEY_PATH = None
        self.GIT_SSH_KEY_PATH = None
        self.AUTH_GIT_URL = None

config = Config()
