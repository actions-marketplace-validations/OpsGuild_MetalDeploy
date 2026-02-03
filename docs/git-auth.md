# Git Authentication Methods

The action supports three methods for authenticating with Git repositories. The authentication method determines how the action clones your repository on the remote server.

## 1. Token Authentication

Uses HTTPS with a GitHub Personal Access Token or GitHub Actions token. This is the recommended method for most private repository use cases.

```yaml
git_auth_method: token
git_token: ${{ secrets.GITHUB_TOKEN }}
git_user: ${{ github.actor }}  # Defaults to ${{ github.actor }}, can be omitted
```

**How it works:**
- The action embeds the token in the Git URL: `https://{git_user}:{git_token}@github.com/owner/repo.git`
- This allows authenticated access to private repositories
- The token is only used during the clone operation

**Use when:**
- Using GitHub Actions (can use `GITHUB_TOKEN` which is automatically available)
- You have a Personal Access Token with repository access
- You prefer HTTPS over SSH
- You want the simplest setup

**Note:** `git_user` defaults to `${{ github.actor }}` (the GitHub username triggering the workflow), so you typically don't need to specify it unless you're using a different account's token.

## 2. SSH Authentication

Uses SSH keys for Git operations. This method is useful when you have deploy keys configured or prefer SSH-based authentication.

```yaml
git_auth_method: ssh
git_ssh_key: ${{ secrets.GIT_SSH_KEY }}
# Or use the same key as server SSH:
# git_ssh_key: ${{ secrets.SSH_PRIVATE_KEY }}
```

**How it works:**
- The action creates a temporary SSH key file on the remote server
- It configures Git to use this key for authentication
- Automatically converts HTTPS URLs to SSH format (e.g., `https://github.com/user/repo.git` → `git@github.com:user/repo.git`)
- The key is cleaned up after the deployment
- Keys can be provided **raw** or **base64-encoded**; the action will auto-detect and decode if needed

**Use when:**
- You have deploy keys set up in your repository
- You prefer SSH authentication over HTTPS
- You want to use the same SSH key for both server access and Git operations
- Your organization requires SSH for Git access

**Setting up Deploy Keys:**
1. Generate an SSH key pair: `ssh-keygen -t ed25519 -C "deploy@yourproject"`
2. Add the public key to your repository: Settings → Deploy keys → Add deploy key
3. Store the private key in GitHub Secrets as `GIT_SSH_KEY`

**Note:** The action automatically converts HTTPS URLs to SSH format (e.g., `https://github.com/user/repo.git` → `git@github.com:user/repo.git`)

## 3. No Authentication (Default)

For public repositories that don't require authentication. This is the simplest method but only works for public repositories.

```yaml
git_auth_method: none  # This is the default
```

**How it works:**
- The action clones the repository using standard Git commands without authentication
- Works exactly like cloning a public repository locally: `git clone https://github.com/user/repo.git`

**Use when:**
- Repository is public and doesn't require authentication
- You want the simplest possible configuration
- You're deploying open-source applications

**Limitations:**
- Cannot access private repositories
- Cannot access repositories that require authentication even for public access
- May hit rate limits for large repositories or frequent deployments

## Branch Management

MetalDeploy automatically manages Git branches based on your environment setting. This ensures you're always deploying the correct code for each environment.

**Branch Selection Logic:**
- **Production environments** (`prod` or `production`): Automatically uses `main` or `master` branch (whichever exists in the repository)
- **Other environments** (e.g., `dev`, `staging`, `test`): Uses the branch matching the environment name

**How it works:**
1. The action clones or updates the repository on the remote server
2. It checks which branch to use based on the `environment` parameter
3. It switches to the appropriate branch (stashing any local changes if needed)
4. It pulls the latest changes from the remote branch
5. It then proceeds with the deployment

**Example:**
```yaml
environment: prod      # Will use 'main' or 'master' branch
environment: staging    # Will use 'staging' branch
environment: dev        # Will use 'dev' branch
```

**Important Notes:**
- The branch must exist in your remote repository
- If you're using `prod` or `production`, the action will look for `origin/main` first, then `origin/master`
- If the target branch doesn't exist, the deployment will fail
- Any uncommitted changes on the remote server will be stashed before switching branches
