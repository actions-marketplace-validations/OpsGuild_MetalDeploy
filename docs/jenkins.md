# Jenkins Integration

While MetalDeploy is primarily designed as a GitHub Action, it is fully compatible with Jenkins using the provided `Dockerfile.jenkins` and `Jenkinsfile`.

## Using the Pre-built Image (Recommended)

You can use the pre-built image directly from GitHub Container Registry without needing to clone the repository or build the image yourself.

To use it in a Jenkins pipeline:

```groovy
pipeline {
    agent {
        docker {
            image "ghcr.io/opsguild/metal-deploy:latest"
            // Mount docker socket if performing docker/k8s deployments
            args '-v /var/run/docker.sock:/var/run/docker.sock'
        }
    }
    stages {
        stage('Deploy') {
            steps {
                script {
                    // Auto-map parameters
                    def paramEnv = params.collect { k, v -> "${k}=${v}" }
                    withEnv(paramEnv) {
                        sh "python main.py"
                    }
                }
            }
        }
    }
}
```

## Manual Build (Optional)

If you prefer to build the environment yourself, the `Dockerfile.jenkins` is provided in the repository root.

## Required Environment Variables

When running in Jenkins, you must map your Jenkins credentials and parameters to the environment variables expected by the script:

| Variable | Jenkins Mapping Example |
|----------|-------------------------|
| `GIT_URL` | `${params.GIT_URL}` |
| `GIT_AUTH_METHOD` | `'token'`, `'ssh'`, or `'none'` |
| `GIT_TOKEN` | Jenkins Secret Text credential |
| `SSH_KEY` | Jenkins SSH User Private Key credential |
| `REMOTE_HOST` | `${params.REMOTE_HOST}` |

## Full Jenkinsfile Example

A comprehensive `Jenkinsfile` is included in the repository root, demonstrating how to use parameters for flexible deployments.

## Environment File Generation in Jenkins

MetalDeploy's powerful `.env` generation also works in Jenkins. Simply define environment variables starting with `ENV_` in your `Jenkinsfile` or pipeline configuration.

```groovy
pipeline {
    agent { /* ... */ }
    environment {
        ENV_FILES_GENERATE = 'true'
        // This will create a .env.app file on the remote server
        ENV_APP_DEBUG = 'false'
        // This will create/override production specific variables
        ENV_PROD_APP_SECRET = credentials('my-app-secret')
    }
    stages {
        stage('Deploy') {
            steps {
                sh "python main.py"
            }
        }
    }
}
```

## Automatic Variable Mapping

To avoid manually mapping every parameter (especially for many `ENV_` variables), you can use this snippet in your `Jenkinsfile` to automatically inject all parameters into the environment:

```groovy
stage('Deploy') {
    steps {
        script {
            // Collect all parameters into an environment-compatible format
            def paramEnv = params.collect { k, v -> "${k}=${v}" }

            withEnv(paramEnv) {
                sh "python main.py"
            }
        }
    }
}
```

This ensures that any parameter you add to the Jenkins job UI (like `ENV_DATABASE_URL`) is immediately available to the deployment script.
